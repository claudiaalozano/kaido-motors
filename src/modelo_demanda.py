"""Modelo SARIMAX del Anexo 4: entrenamiento y test separados del notebook.

Ejecutar desde la raíz del proyecto:
    python src/modelo_demanda.py

Al importar el archivo no se entrena nada. El notebook llama a evaluar_modelo()
y utiliza sus resultados para mostrar tablas y gráficos.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
VARIABLES_BASE = [
    "paro",
    "confianza_consumidor",
    "dias_laborables",
    "semana_santa",
    "adelanto_compras",
    "caida_tras_adelanto"
]


def cargar_datos(segmento="MSUV"):
    """Prepara el mismo mercado mensual y las mismas variables que el anexo."""
    mercado = pd.read_csv(
        DATA_DIR / "mercado_mensual.csv", keep_default_na=False, na_values=[""]
    )
    macro = pd.read_csv(
        DATA_DIR / "macro_mensual.csv", keep_default_na=False, na_values=[""]
    )

    for tabla in (mercado, macro):
        anio = 2000 + tabla["anio"].str[1:].astype(int)
        tabla["fecha"] = pd.to_datetime(
            dict(year=anio, month=tabla["mes"], day=1)
        )

    y = (
        mercado.loc[mercado["segmento"] == segmento]
        .groupby("fecha")["unidades"].sum()
        .asfreq("MS")
    )
    X = macro.set_index("fecha")[VARIABLES_BASE].asfreq("MS")
    return y, X


def entrenar_modelo(y_entrenamiento, X_entrenamiento, orden=(1, 0, 0)):
    """Entrena SARIMAX con el orden indicado."""
    return sm.tsa.SARIMAX(
        np.log(y_entrenamiento),
        exog=X_entrenamiento,
        order=orden,
        seasonal_order=(0, 1, 1, 12),
    ).fit(disp=False, maxiter=1000)


def evaluar_modelo(y, X, ultimo_anio_entrenamiento=2011):
    """Entrena hasta A011 y evalúa doce meses de A012.

    Es una validación condicional: usa las variables económicas reales de A012,
    igual que el ejemplo. Las ventas de A012 no intervienen en el entrenamiento.
    La referencia copia los últimos doce meses de ventas del entrenamiento.
    """
    if not y.index.equals(X.index):
        raise ValueError("y y X deben tener los mismos meses, en el mismo orden.")
    if y.isna().any() or (y <= 0).any():
        raise ValueError("El modelo en logaritmos requiere ventas positivas sin nulos.")

    is_train = y.index.year <= ultimo_anio_entrenamiento
    y_test = y[~is_train]
    if len(y_test) != 12 or is_train.sum() < 12:
        raise ValueError("Esta evaluación necesita doce meses de test y al menos doce de entrenamiento.")

    modelo = entrenar_modelo(y[is_train], X[is_train])
    prevision = np.exp(modelo.forecast(12, exog=X[~is_train]))
    comparacion = pd.DataFrame({
        "real": y_test,
        "prevision": prevision.round(0),
    })
    referencia = pd.Series(
        y[is_train].iloc[-12:].to_numpy(), index=y_test.index, name="referencia"
    )

    errores = comparacion.copy()
    errores["error_sarimax"] = (
        errores["real"] - errores["prevision"]
    ).abs()
    errores["error_referencia"] = (errores["real"] - referencia).abs()

    metricas = pd.DataFrame({
        "WAPE (%)": [
            errores["error_sarimax"].sum() / y_test.sum() * 100,
            errores["error_referencia"].sum() / y_test.sum() * 100,
        ]
    }, index=["SARIMAX", "Referencia estacional"])

    return {
        "modelo": modelo,
        "prevision": prevision,
        "comparacion": comparacion,
        "referencia": referencia,
        "errores": errores,
        "metricas": metricas,
        "is_train": is_train,
        "ha_convergido": bool(modelo.mle_retvals["converged"]),
    }

def prever_modelo(y, X, X_futuro):
    """Entrena con todo el histórico y calcula la previsión futura."""
    modelo = entrenar_modelo(y, X)

    prevision = np.exp(
        modelo.forecast(
            steps=len(X_futuro),
            exog=X_futuro
        )
    )

    return prevision


def main():
    print("Cargando mercado del SUV medio...", flush=True)
    y, X = cargar_datos()
    print("Entrenando hasta A011 y evaluando A012...", flush=True)
    resultado = evaluar_modelo(y, X)
    print("\n¿Ha convergido?", resultado["ha_convergido"])
    print(resultado["metricas"].round(1).to_string())


if __name__ == "__main__":
    main()
