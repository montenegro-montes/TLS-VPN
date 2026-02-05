#!/usr/bin/env python3
import pandas as pd
import argparse
import os
import sys

def auto_output_name(input_csv: str) -> str:
    """
    Genera el nombre del CSV de salida a partir del de entrada:
    - Si contiene 'raw' -> reemplaza por 'summary'
    - Si contiene 'summary' -> antepone 'summary_'
    - Si no, añade '_summary' antes de la extensión.
    """
    dir_name = os.path.dirname(input_csv)
    base = os.path.basename(input_csv)
    lower = base.lower()

    if "raw" in lower:
        new_base = lower.replace("raw", "summary")
    elif "summary" in lower:
        new_base = "summary_" + base
    else:
        name, ext = os.path.splitext(base)
        new_base = f"{name}_summary{ext}"

    return os.path.join(dir_name, new_base)


def cv_percent(series: pd.Series) -> float:
    m = series.mean()
    s = series.std()
    if m == 0:
        return 0.0
    return (s / m) * 100.0


def iqr(series: pd.Series) -> float:
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    return q3 - q1


def outlier_percent(series: pd.Series) -> float:
    """
    Porcentaje de outliers según la regla de Tukey (1.5 * IQR).
    Outlier si x < Q1 - 1.5*IQR o x > Q3 + 1.5*IQR.
    """
    # Asegura numérico y elimina NaN
    s = pd.to_numeric(series, errors="coerce").dropna()
    n = len(s)
    if n == 0:
        return 0.0

    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr_val = q3 - q1
    lower = q1 - 1.5 * iqr_val
    upper = q3 + 1.5 * iqr_val

    outliers = ((s < lower) | (s > upper)).sum()
    return (outliers / n) * 100.0


def summarize_kem_file(input_csv: str) -> None:
    # Leer CSV
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"[ERROR] No se puede leer '{input_csv}': {e}")
        sys.exit(1)

    # Comprobar columnas requeridas
    required_cols = ["kem", "keygen", "encaps", "decaps"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print("[ERROR] Faltan columnas requeridas en el CSV:")
        print(f"  Esperadas: {required_cols}")
        print(f"  Faltan: {missing}")
        sys.exit(1)

    # Mantener orden de aparición de los KEM
    kem_order = df["kem"].unique()
    g = df.groupby("kem")

    # Construir el summary explícitamente
    rows = []
    for kem in kem_order:
        sub = g.get_group(kem)

        keygen = sub["keygen"]
        encaps = sub["encaps"]
        decaps = sub["decaps"]

        row = {
            "kem": kem,

            "keygen_mean":   keygen.mean(),
            "keygen_sd":     keygen.std(),
            "keygen_cv(%)":  cv_percent(keygen),
            "keygen_median": keygen.median(),
            "keygen_iqr":    iqr(keygen),
            "keygen_outliers(%)": outlier_percent(keygen),

            "encaps_mean":   encaps.mean(),
            "encaps_sd":     encaps.std(),
            "encaps_cv(%)":  cv_percent(encaps),
            "encaps_median": encaps.median(),
            "encaps_iqr":    iqr(encaps),
            "encaps_outliers(%)": outlier_percent(encaps),

            "decaps_mean":   decaps.mean(),
            "decaps_sd":     decaps.std(),
            "decaps_cv(%)":  cv_percent(decaps),
            "decaps_median": decaps.median(),
            "decaps_iqr":    iqr(decaps),
            "decaps_outliers(%)": outlier_percent(decaps),
        }
        rows.append(row)

    summary = pd.DataFrame(rows)

    # Formato: medias / SD / mediana / IQR con 3 decimales, CV y outliers con 2
    mean_like_cols = [
        "keygen_mean", "keygen_sd", "keygen_median", "keygen_iqr",
        "encaps_mean", "encaps_sd", "encaps_median", "encaps_iqr",
        "decaps_mean", "decaps_sd", "decaps_median", "decaps_iqr",
    ]
    pct_cols = [
        "keygen_cv(%)", "encaps_cv(%)", "decaps_cv(%)",
        "keygen_outliers(%)", "encaps_outliers(%)", "decaps_outliers(%)",
    ]

    summary[mean_like_cols] = summary[mean_like_cols].applymap(
        lambda x: f"{x:.3f}"
    )
    summary[pct_cols] = summary[pct_cols].applymap(
        lambda x: f"{x:.2f}"
    )

    # Guardar
    output_csv = auto_output_name(input_csv)
    summary.to_csv(output_csv, index=False)
    print(f"Summary saved to: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera resumen KEM (mean, SD, CV, median, IQR, % outliers Tukey)."
    )
    parser.add_argument(
        "input_csv",
        help="Archivo CSV RAW con columnas: kem, keygen, encaps, decaps"
    )
    args = parser.parse_args()

    summarize_kem_file(args.input_csv)
