"""Modelo del mercado en dos niveles: mercado total x peso de cada segmento.

Por qué dos niveles
-------------------
- El mercado TOTAL de los siete segmentos se mueve con la economía (paro,
  confianza), el calendario y los sucesos. Se modeliza en niveles: log(total)
  explicado por las variables + una dummy por mes + error AR(1). Al no usar
  diferencias estacionales, el modelo no arrastra el crecimiento de los
  últimos años (lo que hacía que el SARIMAX del anexo sobreestimase).
- El PESO de cada segmento dentro del total cambia por gustos, no por la
  economía: los SUV ganan peso año tras año y B, C y MD lo pierden. Se
  modeliza como log(peso) = tendencia lineal + estacionalidad, estimada con
  los últimos años.
- Mercado del segmento = total previsto x peso previsto.

Uso (desde la raíz del proyecto):
    python src/modelo_mercado.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parents[1]
DATA_DIR = RAIZ / "data"
SEGMENTOS = ["B", "C", "MD", "SSUV", "CSUV", "MSUV", "S"]
VARIABLES = [
    "paro", "confianza_consumidor",
    "dias_laborables", "semana_santa",
    "adelanto_compras", "caida_tras_adelanto", "subida_iva", "incentivo_publico",
]


def _leer(fichero):
    return pd.read_csv(DATA_DIR / fichero, keep_default_na=False, na_values=[""])


def _fecha(df):
    anio = 2000 + df["anio"].str[1:].astype(int)
    return pd.to_datetime(dict(year=anio, month=df["mes"], day=1))


def cargar_datos():
    """Devuelve el mercado mensual por segmento (columnas) y la macro con A013 vacío."""
    mercado = _leer("mercado_mensual.csv")
    macro = _leer("macro_mensual.csv")
    mercado["fecha"] = _fecha(mercado)
    macro["fecha"] = _fecha(macro)

    P = (mercado.pivot_table(index="fecha", columns="segmento",
                             values="unidades", aggfunc="sum")
         .asfreq("MS")[SEGMENTOS])
    fechas = pd.date_range("2001-01-01", "2013-12-01", freq="MS")
    macro = macro.set_index("fecha")[VARIABLES].reindex(fechas)
    return P, macro


def variables_A013(macro, escenario):
    """Rellena A013 con el calendario y los supuestos del escenario.

    escenario: diccionario como los de config/supuestos.json
    (paro_delta, confianza_delta, meses_caida, incentivo_publico, ...).
    Paro y confianza parten del último dato de A012 (diciembre).
    """
    X = macro.copy()
    cal = _leer("calendario_A013.csv")
    a13 = X.index.year == 2013
    ultimo = X.loc["2012-12-01"]

    X.loc[a13, "dias_laborables"] = cal["dias_laborables"].to_numpy()
    X.loc[a13, "semana_santa"] = cal["semana_santa"].to_numpy()
    X.loc[a13, "paro"] = ultimo["paro"] + escenario.get("paro_delta", 0)
    X.loc[a13, "confianza_consumidor"] = (
        ultimo["confianza_consumidor"] + escenario.get("confianza_delta", 0)
    )
    X.loc[a13, "adelanto_compras"] = 0
    X.loc[a13, "subida_iva"] = 0
    X.loc[a13, "incentivo_publico"] = escenario.get("incentivo_publico", 0)
    meses_caida = escenario.get("meses_caida", 3)
    X.loc[a13, "caida_tras_adelanto"] = (X.index[a13].month <= meses_caida).astype(int)
    return X


def _dummies_mes(fechas):
    d = pd.get_dummies(fechas.month, prefix="m", drop_first=True).astype(float)
    d.index = fechas
    return d


def entrenar_total(total, X, hasta_anio):
    """log(total) = variables + dummies de mes + AR(1), con datos hasta hasta_anio."""
    ent = total.index.year <= hasta_anio
    y = np.log(total[ent])
    Xe = pd.concat([X, _dummies_mes(X.index)], axis=1).loc[y.index]
    # Quita los sucesos que nunca han ocurrido en el entrenamiento (columna de ceros)
    Xe = Xe.loc[:, Xe.std() > 0]

    # Arranque desde la regresión simple: sin esto el optimizador a veces se pierde
    ols = sm.OLS(y, sm.add_constant(Xe)).fit()
    rho = np.corrcoef(ols.resid[1:], ols.resid[:-1])[0, 1]
    inicio = np.r_[ols.params.to_numpy(), rho, ols.mse_resid * (1 - rho ** 2)]

    return sm.tsa.SARIMAX(y, exog=Xe, order=(1, 0, 0), trend="c").fit(
        start_params=inicio, disp=False, maxiter=2000
    )


def prever_total(total, X, anio):
    """Entrena hasta anio-1 y prevé los doce meses de anio."""
    modelo = entrenar_total(total, X, anio - 1)
    fut = X.index.year == anio
    Xf = pd.concat([X, _dummies_mes(X.index)], axis=1).loc[fut, modelo.model.exog_names]
    prev = np.exp(modelo.forecast(12, exog=Xf))
    return pd.Series(prev.to_numpy(), index=X.index[fut]), modelo


def prever_peso(P, segmento, anio, anios_ventana=3):
    """log(peso del segmento) = tendencia + estacionalidad, con los últimos años."""
    total = P.sum(axis=1)
    log_peso = np.log(P[segmento] / total)
    fechas = pd.date_range(P.index[0], f"{anio}-12-01", freq="MS")
    Z = pd.concat(
        [_dummies_mes(fechas), pd.Series(np.arange(len(fechas)), index=fechas, name="t")],
        axis=1,
    )
    Z = sm.add_constant(Z)
    ent = (log_peso.index.year < anio) & (log_peso.index.year >= anio - anios_ventana)
    ajuste = sm.OLS(log_peso[ent], Z.loc[log_peso.index[ent]]).fit()
    fut = fechas.year == anio
    return pd.Series(np.exp(ajuste.predict(Z[fut])).to_numpy(), index=fechas[fut])


def prever_mercado(P, X, anio, anios_ventana=3):
    """Mercado previsto de cada segmento para los doce meses de anio."""
    total = P.sum(axis=1)
    prev_total, modelo = prever_total(total, X, anio)
    pesos = pd.DataFrame({s: prever_peso(P, s, anio, anios_ventana) for s in SEGMENTOS})
    pesos = pesos.div(pesos.sum(axis=1), axis=0)   # que los pesos sumen 1 cada mes
    prev = pesos.mul(prev_total, axis=0)
    return prev, prev_total, modelo


def validar(P, X, anios=(2010, 2011, 2012)):
    """Prevé cada año con los datos anteriores y compara con lo que pasó."""
    filas = []
    for anio in anios:
        prev, _, _ = prever_mercado(P, X, anio)
        real = P.loc[str(anio)]
        for s in SEGMENTOS + ["TOTAL"]:
            p = prev.sum(axis=1) if s == "TOTAL" else prev[s]
            r = real.sum(axis=1) if s == "TOTAL" else real[s]
            filas.append({
                "anio": anio, "segmento": s,
                "sesgo (%)": (p.sum() / r.sum() - 1) * 100,
                "WAPE (%)": (p - r).abs().sum() / r.sum() * 100,
            })
    return pd.DataFrame(filas)


def cargar_escenarios():
    with open(RAIZ / "config" / "supuestos.json", encoding="utf-8") as f:
        return json.load(f)["escenarios"]


def main():
    P, macro = cargar_datos()
    escenarios = cargar_escenarios()

    print("Validación (prevé cada año con los datos anteriores):")
    val = validar(P, variables_A013(macro, escenarios["central"]))
    print(val.pivot(index="segmento", columns="anio", values="sesgo (%)").round(1))

    print("\nPrevisión A013 por escenario (coches):")
    resumen = {}
    for nombre, esc in escenarios.items():
        prev, _, modelo = prever_mercado(P, variables_A013(macro, esc), 2013)
        resumen[nombre] = prev.sum()
    print("Coeficientes del mercado total:")
    print(modelo.params.filter(regex="^(paro|confianza|adelanto|caida|incentivo|subida|ar)").round(3))
    resumen = pd.DataFrame(resumen)
    resumen["A012"] = P.loc["2012"].sum()
    resumen.loc["TOTAL"] = resumen.sum()
    print(resumen.round(0))


if __name__ == "__main__":
    main()
