#!/usr/bin/env python3
import os
import csv
import statistics

RESULTS_DIR = "results"
SUMMARY_FILE = os.path.join(RESULTS_DIR, "summary.csv")

def outlier_percent(values):
    """
    Calcula el porcentaje de outliers según la regla de Tukey (1.5 * IQR)
    """
    if len(values) == 0:
        return 0.0

    # Cuartiles para el IQR
    try:
        q1, q3 = statistics.quantiles(values, n=4, method="inclusive")[0], \
                 statistics.quantiles(values, n=4, method="inclusive")[2]
        iqr = q3 - q1
    except Exception:
        # Si algo raro pasa con quantiles, dejamos IQR a 0
        iqr = 0.0
    
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    
    # Outliers
    outliers = [v for v in values if v < lower or v > upper]
    return (len(outliers) / len(values)) * 100 if len(values) > 0 else 0.0

def analyze_csv(file_path):
    values = []

    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        lines = list(reader)

        # Saltar cabecera y warm-up (primeras 2 líneas)
        for row in lines[2:]:
            try:
                value = float(row[1].strip())
                values.append(value)
            except (ValueError, IndexError):
                continue  # saltar líneas vacías o rotas

    if len(values) == 0:
        return None

    # Estadísticos básicos
    mean = statistics.mean(values)
    median = statistics.median(values)

    if len(values) > 1:
        stdev = statistics.stdev(values)
    else:
        stdev = 0.0

    # Cuartiles para el IQR
    try:
        q1, q3 = statistics.quantiles(values, n=4, method="inclusive")[0], \
                 statistics.quantiles(values, n=4, method="inclusive")[2]
        iqr = q3 - q1
    except Exception:
        # Si algo raro pasa con quantiles, dejamos IQR a 0
        iqr = 0.0

    cv = (stdev / mean) * 100 if mean != 0 else 0.0
    outliers_pct = outlier_percent(values)

    return mean, stdev, cv, median, iqr, outliers_pct

# Procesar todos los *_timing.csv del directorio
results = []
for filename in os.listdir(RESULTS_DIR):
    if filename.endswith("_timing.csv"):
        alg = filename.replace("_timing.csv", "")
        file_path = os.path.join(RESULTS_DIR, filename)
        stats = analyze_csv(file_path)
        if stats is not None:
            mean, stdev, cv, median, iqr, outliers_pct = stats
            results.append((
                alg,
                f"{mean:.3f}",
                f"{stdev:.3f}",
                f"{cv:.2f}",
                f"{median:.3f}",
                f"{iqr:.3f}",
                f"{outliers_pct:.2f}",
            ))
            print(
                f"🔹 {alg:15s} → "
                f"Mean = {mean:.3f} ms | "
                f"SD = {stdev:.3f} ms | "
                f"CV = {cv:.2f}% | "
                f"Median = {median:.3f} ms | "
                f"IQR = {iqr:.3f} ms | "
                f"Outliers = {outliers_pct:.2f}%"
            )
        else:
            print(f"⚠️  {alg:15s} → No valid data")

# Guardar summary.csv
with open(SUMMARY_FILE, "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Algorithm", "Mean(ms)", "SD(ms)", "CV(%)", "Median(ms)", "IQR(ms)", "Outliers(%)"])
    writer.writerows(results)

print(f"\n✅ Summary saved to: {SUMMARY_FILE}")
