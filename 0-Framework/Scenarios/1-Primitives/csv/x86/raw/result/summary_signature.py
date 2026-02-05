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


def summarize_signature_file(input_csv: str) -> None:
    # Leer CSV
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"[ERROR] No se puede leer '{input_csv}': {e}")
        sys.exit(1)

    # Comprobar columnas requeridas
    required_cols = ["signature", "sign", "verify"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print("[ERROR] Faltan columnas requeridas en el CSV:")
        print(f"  Esperadas: {required_cols}")
        print(f"  Faltan: {missing}")
        sys.exit(1)

    sig_order = df["signature"].unique()
    g = df.groupby("signature")

    rows = []
    for sig in sig_order:
        sub = g.get_group(sig)

        sign_vals   = sub["sign"]
        verify_vals = sub["verify"]

        row = {
            "signature": sig,

            "sign_mean":   sign_vals.mean(),
            "sign_sd":     sign_vals.std(),
            "sign_cv(%)":  cv_percent(sign_vals),
            "sign_median": sign_vals.median(),
            "sign_iqr":    iqr(sign_vals),
            "sign_outliers(%)": outlier_percent(sign_vals),

            "verify_mean":   verify_vals.mean(),
            "verify_sd":     verify_vals.std(),
            "verify_cv(%)":  cv_percent(verify_vals),
            "verify_median": verify_vals.median(),
            "verify_iqr":    iqr(verify_vals),
            "verify_outliers(%)": outlier_percent(verify_vals),
        }
        rows.append(row)

    summary = pd.DataFrame(rows)

    # Formato de salida (medidas con 3 decimales; % con 2)
    mean_like_cols = [
        "sign_mean", "sign_sd", "sign_median", "sign_iqr",
        "verify_mean", "verify_sd", "verify_median", "verify_iqr",
    ]
    pct_cols = [
        "sign_cv(%)", "verify_cv(%)",
        "sign_outliers(%)", "verify_outliers(%)",
    ]

    summary[mean_like_cols] = summary[mean_like_cols].applymap(
        lambda x: f"{x:.3f}"
    )
    summary[pct_cols] = summary[pct_cols].applymap(
        lambda x: f"{x:.2f}"
    )

    # Guardar archivo
    output_csv = auto_output_name(input_csv)
    summary.to_csv(output_csv, index=False)
    print(f"Summary saved to: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera resumen de firmas (mean, SD, CV, median, IQR, % outliers Tukey)."
    )
    parser.add_argument("input_csv", help="CSV RAW con columnas: signature, sign, verify")
    args = parser.parse_args()

    summarize_signature_file(args.input_csv)
