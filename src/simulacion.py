"""Simulación de un año de la cadena de suministro (sección 7 y 9.3 del caso).

Para cada segmento y escenario se simula A013 mes a mes, muchas veces:

1. La demanda real de cada mes es la demanda del escenario con un error al
   azar (lognormal, con el sigma del modelo).
2. El planificador solo conoce la previsión del escenario CENTRAL. Cada mes
   compara lo vendido con lo previsto y revisa la previsión (suavizado con
   alpha_revision, limitado a limite_revision).
3. Cada mes t se decide la llegada de t+3 (lo de t+1 y t+2 ya viene en camino):
       S^_{t+2} = S_t + L_{t+1} + L_{t+2} - D^_{t+1} - D^_{t+2}
       L_{t+3}  = max(0, D^_{t+3} + SS - S^_{t+2}),   SS = z * sigma * sqrt(3)
4. Ventas = min(demanda, stock + llegadas). Si faltan coches, una parte se
   cubre con transfers (fraccion_transfer, como mucho limite_transfer_demanda
   de la demanda del mes) y el resto son ventas perdidas.
5. El stock se vende del más viejo al más nuevo (FIFO) y se sigue su edad para
   calcular el coste del stock, el VM según la antigüedad y los coches >90 días.

Supuestos propios (documentarlos en el resumen):
- Edad del stock inicial: los coches de 0-90 días cuentan con 1 mes, los de
  91-180 con 4 meses y los de más de 180 con 7 meses.
- Si un mes se agota el stock, el planificador estima la demanda como
  ventas x (1 + incremento_demanda_censurada_max), sin pasar de la real.
- Coste del stock para la marca: 2 EUR/día (60 EUR/mes) por coche hasta
  los 180 días; los coches vendidos en el mes cuentan medio mes.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DATA_DIR = RAIZ / "data"
EDAD_MAX = 30                       # meses de antigüedad que se siguen
COSTE_DIA_MARCA = 2.0               # EUR por coche y día, hasta 180 días


def cargar_supuestos():
    with open(RAIZ / "config" / "supuestos.json", encoding="utf-8") as f:
        return json.load(f)


def cargar_economia():
    """Euros por coche de cada segmento (tarifa A013 y VM real según antigüedad)."""
    seg = pd.read_csv(DATA_DIR / "segmentos.csv", keep_default_na=False,
                      na_values=[""]).set_index("segmento")
    eco = pd.DataFrame(index=seg.index)
    eco["beneficio_bruto"] = seg["beneficio_bruto_marca_eur"]
    ingreso_marca = seg["pff_medio"] * (
        1 - seg["margen_conc_base_pct"] - seg["margen_conc_var_pct"])
    eco["coste_coche"] = ingreso_marca - seg["beneficio_bruto_marca_eur"]
    eco["prima_co2"] = seg["prima_co2_eur"]
    eco["vm_0_90"] = seg["vm_real_0_90_eur"]
    eco["vm_91_180"] = seg["vm_real_91_180_eur"]
    # CSUV no tiene coches de más de 180 días: usamos el de 91-180
    eco["vm_mas_180"] = seg["vm_real_mas_180_eur"].fillna(seg["vm_real_91_180_eur"])
    eco["cvp_real"] = seg["cvp_real_eur"]
    return eco


def stock_inicial_por_edad():
    """Stock de diciembre de A012 repartido por meses de antigüedad."""
    st = pd.read_csv(DATA_DIR / "stock_mensual.csv", keep_default_na=False, na_values=[""])
    dic = st[(st["anio"] == "A012") & (st["mes"] == 12)].set_index("segmento")
    edades = {}
    for s, fila in dic.iterrows():
        v = np.zeros(EDAD_MAX)
        v[1] = fila["s_0_90"]
        v[4] = fila["s_91_180"]
        v[7] = fila["s_mas_180"]
        edades[s] = v
    return edades


def _vender_fifo(stock_edad, cantidad):
    """Saca 'cantidad' coches empezando por los más viejos.

    stock_edad: (n_sim, EDAD_MAX). Devuelve los coches vendidos por edad.
    """
    vendidos = np.zeros_like(stock_edad)
    pendiente = cantidad.astype(float).copy()
    for edad in range(EDAD_MAX - 1, -1, -1):
        sale = np.minimum(stock_edad[:, edad], pendiente)
        vendidos[:, edad] = sale
        stock_edad[:, edad] -= sale
        pendiente -= sale
    return vendidos


def simular_segmento(segmento, demanda_escenario, prevision_central, escenario,
                     stock_edad0, en_camino_mes, sigma_rel, z, eco, sup,
                     n_sim=None, rng=None):
    """Simula A013 para un segmento. Devuelve un diccionario de resultados.

    demanda_escenario: 12 valores, demanda media del escenario que ocurre.
    prevision_central: 12 valores, la previsión con la que se planifica.
    """
    n = n_sim or sup["simulaciones"]
    rng = rng or np.random.default_rng(sup["seed"])
    alpha = sup["alpha_revision"]
    lim_bajo, lim_alto = sup["limite_revision"]
    dias = sup["dias_mes"]

    d_media = np.asarray(demanda_escenario, dtype=float)
    d_plan = np.asarray(prevision_central, dtype=float)
    # La previsión hace falta hasta t+3 del último pedido (mes 12): se alarga con el último valor
    d_plan_ext = np.r_[d_plan, np.repeat(d_plan[-1], 3)]

    # 1. Demanda real: lognormal con media la del escenario
    sigma = sigma_rel * escenario.get("sigma_factor", 1.0)
    ruido = rng.normal(0, sigma, size=(n, 12))
    demanda = d_media * np.exp(ruido - sigma ** 2 / 2)

    # 2. Llegadas: enero y febrero ya vienen en camino; el resto se decide
    llegadas = np.zeros((n, 15))
    llegadas[:, 0:2] = en_camino_mes * sup["factor_en_camino"]

    stock_edad = np.tile(stock_edad0, (n, 1)).astype(float)
    factor_prev = np.ones(n)        # revisión de la previsión (1 = la central tal cual)

    def pedir(t):
        """Pedido decidido al cierre del mes t (0 = diciembre A012) para el mes t+3."""
        d_hat = factor_prev[:, None] * d_plan_ext[None, t:t + 3]   # meses t+1, t+2, t+3
        s_t = stock_edad.sum(axis=1)
        s1 = np.maximum(0, s_t + llegadas[:, t] - d_hat[:, 0])
        s2 = np.maximum(0, s1 + llegadas[:, t + 1] - d_hat[:, 1])
        ss = z * sigma_rel * d_hat[:, 2] * np.sqrt(3)
        llegadas[:, t + 2] = np.maximum(0, d_hat[:, 2] + ss - s2)

    pedir(0)   # en diciembre de A012 se decide la llegada de marzo

    # Interrupción de suministro: se pierde un mes de llegadas de un segmento
    mes_int = None
    if escenario.get("segmento_interrupcion") == segmento:
        mes_int = escenario["mes_interrupcion"]

    reg = {k: np.zeros((n, 12)) for k in
           ["ventas", "transfers", "perdidas", "stock_fin", "coste_stock", "vm", "llegadas"]}
    vendidos_mas_90 = np.zeros(n)

    vm_edad = np.where(np.arange(EDAD_MAX) < 3, eco["vm_0_90"],
                       np.where(np.arange(EDAD_MAX) < 6, eco["vm_91_180"], eco["vm_mas_180"]))
    cuenta_coste = (np.arange(EDAD_MAX) < 6).astype(float)   # hasta 180 días

    for m in range(12):
        if mes_int is not None and m + 1 == mes_int:
            llegadas[:, m] = 0
        stock_edad[:, 0] += llegadas[:, m]
        reg["llegadas"][:, m] = llegadas[:, m]

        disponible = stock_edad.sum(axis=1)
        ventas = np.minimum(demanda[:, m], disponible)
        vendidos = _vender_fifo(stock_edad, ventas)

        falta = demanda[:, m] - ventas
        transfers = np.minimum(sup["fraccion_transfer"] * falta,
                               sup["limite_transfer_demanda"] * demanda[:, m])
        perdidas = falta - transfers

        reg["ventas"][:, m] = ventas + transfers
        reg["transfers"][:, m] = transfers
        reg["perdidas"][:, m] = perdidas
        reg["vm"][:, m] = vendidos @ vm_edad + transfers * eco["vm_0_90"]
        vendidos_mas_90 += vendidos[:, 3:].sum(axis=1)
        reg["coste_stock"][:, m] = COSTE_DIA_MARCA * (
            dias * (stock_edad @ cuenta_coste) + dias / 2 * (vendidos @ cuenta_coste))
        reg["stock_fin"][:, m] = stock_edad.sum(axis=1)

        # Revisión de la previsión con lo que se ha visto este mes
        agotado = ventas >= disponible - 1e-9
        observada = np.where(
            agotado,
            np.minimum(demanda[:, m], ventas * (1 + sup["incremento_demanda_censurada_max"])),
            ventas)
        ratio = observada / max(d_plan[m], 1e-9)
        factor_prev = np.clip((1 - alpha) * factor_prev + alpha * ratio, lim_bajo, lim_alto)

        # Envejece el stock un mes
        stock_edad[:, 1:] = stock_edad[:, :-1].copy()
        stock_edad[:, 0] = 0

        if m + 1 <= 9:          # se decide la llegada de m+4 (hasta diciembre)
            pedir(m + 1)

    # Cuentas del año
    extra_por_coche = eco["prima_co2"] * escenario.get("prima_co2", False) \
        + escenario.get("arancel_pct_coste", 0.0) * eco["coste_coche"]
    ventas_ano = reg["ventas"].sum(axis=1)
    coste_transfer = reg["transfers"].sum(axis=1) * 0.2 * eco["beneficio_bruto"]
    vm_total = reg["vm"].sum(axis=1)
    cvp_total = ventas_ano * (eco["beneficio_bruto"] - extra_por_coche) - vm_total - coste_transfer
    coste_stock = reg["coste_stock"].sum(axis=1)

    return {
        "ventas": ventas_ano,
        "llegadas": reg["llegadas"].sum(axis=1),
        "stock_medio": reg["stock_fin"].mean(axis=1),
        "meses_stock": reg["stock_fin"].mean(axis=1) / np.maximum(demanda.mean(axis=1), 1e-9),
        "mas_90_fin": stock_edad[:, 3:].sum(axis=1),
        "coste_stock": coste_stock,
        "perdidas": reg["perdidas"].sum(axis=1),
        "perdidas_eur": reg["perdidas"].sum(axis=1) * eco["cvp_real"],
        "transfers": reg["transfers"].sum(axis=1),
        "transfers_eur": coste_transfer,
        "vm": vm_total,
        "cvp": cvp_total,
        "margen_neto": cvp_total - coste_stock,
        "llegadas_mes": reg["llegadas"],     # (n_sim, 12): el plan de producción
    }


def coste_de_equivocarse(res):
    """Lo que cuesta el plan por exceso y por defecto (para elegir z)."""
    return res["coste_stock"] + res["perdidas_eur"] + res["transfers_eur"]


def resumir(res):
    """Media y percentiles 5 y 95 de cada resultado."""
    filas = {}
    for k, v in res.items():
        if k == "llegadas_mes":
            continue
        filas[k] = {"media": v.mean(), "p5": np.percentile(v, 5), "p95": np.percentile(v, 95)}
    return pd.DataFrame(filas).T


# --------------------------------------------------------------------------
# Funciones para el notebook
# --------------------------------------------------------------------------

def _datos_segmento(s, inicio):
    return dict(stock_edad0=stock_inicial_por_edad()[s],
                en_camino_mes=inicio.loc[s, "en_camino_mes"],
                sigma_rel=inicio.loc[s, "sigma_rel"])


def elegir_z(demanda, escenarios, inicio):
    """Para cada segmento, la z que minimiza el coste de equivocarse en el central.

    demanda: {escenario: DataFrame mes x segmento}. inicio: tabla con
    en_camino_mes y sigma_rel por segmento.
    Devuelve (z elegida por segmento, tabla de costes medios en EUR por z).
    """
    sup, eco = cargar_supuestos(), cargar_economia()
    central = demanda["central"]
    costes = {}
    for s in central.columns:
        costes[s] = {}
        for z in sup["z_candidatos"]:
            r = simular_segmento(s, central[s], central[s], escenarios["central"],
                                 z=z, eco=eco.loc[s], sup=sup, **_datos_segmento(s, inicio))
            costes[s][z] = coste_de_equivocarse(r).mean()
    costes = pd.DataFrame(costes).T
    costes.columns.name = "z"
    return costes.idxmin(axis=1), costes


def simular_escenarios(demanda, escenarios, inicio, z):
    """Simula los tres escenarios con el plan pensado para el central.

    Devuelve:
      tabla5: resultados medios por escenario y segmento (más el TOTAL),
      rangos: percentiles 5 y 95 de ventas y margen,
      plan:   llegadas mensuales medianas por segmento en el escenario central
              (el plan de producción que se propone al comité).
    """
    sup, eco = cargar_supuestos(), cargar_economia()
    filas, rangos, plan = [], [], {}
    for nombre, esc in escenarios.items():
        tot = None
        for s in demanda[nombre].columns:
            r = simular_segmento(s, demanda[nombre][s], demanda["central"][s], esc,
                                 z=z[s], eco=eco.loc[s], sup=sup, **_datos_segmento(s, inicio))
            fila = {k: v.mean() for k, v in r.items()
                    if k not in ("llegadas_mes", "meses_stock")}
            fila["demanda_media_mes"] = demanda[nombre][s].mean()
            filas.append({"escenario": nombre, "segmento": s, **fila})
            rangos.append({"escenario": nombre, "segmento": s,
                           "ventas_p5": np.percentile(r["ventas"], 5),
                           "ventas_p95": np.percentile(r["ventas"], 95),
                           "margen_p5": np.percentile(r["margen_neto"], 5),
                           "margen_p95": np.percentile(r["margen_neto"], 95)})
            if nombre == "central":
                plan[s] = np.median(r["llegadas_mes"], axis=0)
            # para el total, sumamos simulación a simulación
            sim_tot = {k: r[k] for k in ("ventas", "margen_neto")}
            tot = sim_tot if tot is None else {k: tot[k] + sim_tot[k] for k in tot}
        rangos.append({"escenario": nombre, "segmento": "TOTAL",
                       "ventas_p5": np.percentile(tot["ventas"], 5),
                       "ventas_p95": np.percentile(tot["ventas"], 95),
                       "margen_p5": np.percentile(tot["margen_neto"], 5),
                       "margen_p95": np.percentile(tot["margen_neto"], 95)})

    df = pd.DataFrame(filas)
    total = df.groupby("escenario").sum(numeric_only=True).reset_index()
    total["segmento"] = "TOTAL"
    df = pd.concat([df, total], ignore_index=True)
    df["meses_de_stock"] = df["stock_medio"] / df["demanda_media_mes"]

    nombres = {
        "ventas": "Coches vendidos", "llegadas": "Coches fabricados (llegadas A013)",
        "stock_medio": "Stock medio en la red (coches)", "meses_de_stock": "Stock medio (meses de venta)",
        "mas_90_fin": "Coches >90 días a fin de año", "coste_stock": "Coste del stock (EUR)",
        "perdidas": "Ventas perdidas (coches)", "perdidas_eur": "Ventas perdidas (EUR de CVP)",
        "transfers": "Transfers (coches)", "transfers_eur": "Transfers (EUR)",
        "vm": "Gasto comercial VM (EUR)", "cvp": "Margen de la marca CVP (EUR)",
        "margen_neto": "CVP menos coste del stock (EUR)",
    }
    tabla5 = (df.set_index(["segmento", "escenario"])[list(nombres)]
              .rename(columns=nombres).stack().unstack("escenario")
              [["pesimista", "central", "optimista"]])
    plan = pd.DataFrame(plan, index=pd.date_range("2013-01-01", periods=12, freq="MS")).round(0)
    return tabla5, pd.DataFrame(rangos), plan
