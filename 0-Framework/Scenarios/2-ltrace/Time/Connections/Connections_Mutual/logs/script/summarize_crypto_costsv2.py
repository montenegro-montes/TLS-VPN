#!/usr/bin/env python3
import sys
import csv
import statistics as stats
from pathlib import Path
from collections import defaultdict

# ORDEN FIJO DE SALIDA PARA EL RESUMEN
OUTPUT_ORDER_TR = [
    ("ed25519",   "x25519"),
    ("ed25519",   "mlkem512"),
    ("ed25519",   "x25519_mlkem512"),
    ("ed25519",   "hqc128"),
    ("ed25519",   "x25519_hqc128"),

    ("secp384r1", "x448"),
    ("secp384r1", "mlkem768"),
    ("secp384r1", "x448_mlkem768"),
    ("secp384r1", "hqc192"),
    ("secp384r1", "x448_hqc192"),

    ("secp521r1", "P-521"),
    ("secp521r1", "mlkem1024"),
    ("secp521r1", "p521_mlkem1024"),
    ("secp521r1", "hqc256"),
    ("secp521r1", "p521_hqc256"),
]

OUTPUT_ORDER_PQ = [
    ("mldsa44",   "x25519"),
    ("mldsa44",   "mlkem512"),
    ("mldsa44",   "x25519_mlkem512"),
    ("mldsa44",   "hqc128"),
    ("mldsa44",   "x25519_hqc128"),

    ("mldsa65", "x448"),
    ("mldsa65", "mlkem768"),
    ("mldsa65", "x448_mlkem768"),
    ("mldsa65", "hqc192"),
    ("mldsa65", "x448_hqc192"),

    ("mldsa87", "P-521"),
    ("mldsa87", "mlkem1024"),
    ("mldsa87", "p521_mlkem1024"),
    ("mldsa87", "hqc256"),
    ("mldsa87", "p521_hqc256"),
]

# Columnas que NO son primitivas criptográficas
NON_CRYPTO_COLS = {
    "exec_id",
    "sig_alg",
    "kem_alg",
    "proto",
    "mode",
    "ssl_connect_ms",
    "handshake_ms",
}

def parse_decimal(value):
    """
    Convierte '12,345678' o '12.345678' a float.
    Devuelve 0.0 si está vacío.
    """
    if value is None:
        return 0.0
    value = value.strip()
    if value == "":
        return 0.0
    value = value.replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0

def compute_stats(values):
    """
    Devuelve (mean, sd, median, q1, q3, iqr, min_v, max_v)
    """
    if not values:
        return (0.0,) * 8

    values_sorted = sorted(values)
    n = len(values_sorted)

    mean_v = stats.fmean(values_sorted)
    sd_v = stats.stdev(values_sorted) if n > 1 else 0.0
    median_v = stats.median(values_sorted)

    try:
        qs = stats.quantiles(values_sorted, n=4, method="inclusive")
        q1 = qs[0]
        q3 = qs[2]
    except Exception:
        q1 = values_sorted[n // 4]
        q3 = values_sorted[(3 * n) // 4]

    iqr = q3 - q1
    min_v = values_sorted[0]
    max_v = values_sorted[-1]

    return mean_v, sd_v, median_v, q1, q3, iqr, min_v, max_v

def process_directory(csv_dir: Path, tipo, out_csv: Path):
    data = defaultdict(lambda: {
        "ssl_connect": [],
        "handshake": [],
        "crypto_sum": [],
        "crypto_pct": [],
    })

    for csv_path in sorted(csv_dir.glob("*.csv")):
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

            crypto_cols = [
                col for col in fieldnames
                if col not in NON_CRYPTO_COLS and not col.startswith("OQS_")
            ]

            for row in reader:
                sig = row.get("sig_alg", "").strip()
                kem = row.get("kem_alg", "").strip()
                if not sig or not kem:
                    continue

                ssl_ms = parse_decimal(row.get("ssl_connect_ms"))
                if ssl_ms <= 0.0:
                    # si no hay SSL_connect, no contamos esta ejecución
                    continue

                handshake_ms = parse_decimal(row.get("handshake_ms"))

                crypto_sum = 0.0
                for col in crypto_cols:
                    crypto_sum += parse_decimal(row.get(col))

                crypto_pct = (crypto_sum / ssl_ms) * 100.0 if ssl_ms > 0 else 0.0

                key = (sig, kem)
                data[key]["ssl_connect"].append(ssl_ms)
                data[key]["handshake"].append(handshake_ms)
                data[key]["crypto_sum"].append(crypto_sum)
                data[key]["crypto_pct"].append(crypto_pct)

    # --- CSV RESUMEN ---
    with out_csv.open("w", newline="", encoding="utf-8") as f_out:
        fieldnames = [
            "sig_alg",
            "kem_alg",
            "n_exec",

            # SSL stats
            "mean_ssl_connect_ms",
            "sd_ssl_connect_ms",
            "median_ssl_connect_ms",
            "q1_ssl_connect_ms",
            "q3_ssl_connect_ms",
            "iqr_ssl_connect_ms",
            "min_ssl_connect_ms",
            "max_ssl_connect_ms",

            # Handshake (medida externa)
            "mean_handshake_ms",
            "sd_handshake_ms",
            "median_handshake_ms",
            "q1_handshake_ms",
            "q3_handshake_ms",
            "iqr_handshake_ms",
            "min_handshake_ms",
            "max_handshake_ms",

            # Crypto stats
            "mean_crypto_ms",
            "sd_crypto_ms",
            "median_crypto_ms",
            "q1_crypto_ms",
            "q3_crypto_ms",
            "iqr_crypto_ms",
            "min_crypto_ms",
            "max_crypto_ms",

            # Percentages
            "mean_crypto_pct",
            "mean_crypto_pct_min",
            "mean_crypto_pct_max",
        ]

        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        if (tipo=="TR"):
            OUTPUT_ORDER = OUTPUT_ORDER_TR
        else: 
            OUTPUT_ORDER = OUTPUT_ORDER_PQ
        
        threshold = 1000.0  # ms

        for (sig, kem) in OUTPUT_ORDER:
            if (sig, kem) not in data:
                continue  # si ese par no existe en el directorio, se salta

            vals = data[(sig, kem)]

            ssl_list    = vals["ssl_connect"]
            hs_list     = vals["handshake"]
            crypto_list = vals["crypto_sum"]
            pct_list    = vals["crypto_pct"]

            # Empaquetamos por ejecución para filtrar todo junto
            combined = list(zip(ssl_list, hs_list, crypto_list, pct_list))
            if not combined:
                continue

            # Filtramos:
            #  - ssl > 0
            #  - ssl <= threshold
            filtered = [
                (ssl, hs, crypto, pct)
                for (ssl, hs, crypto, pct) in combined
                if ssl is not None and ssl > 0 and ssl <= threshold
            ]

            original_size = len(combined)
            n_exec = len(filtered)

            if n_exec == 0:
                print(f"⚠️ (sig={sig}, kem={kem}) sin datos válidos tras filtrar > 0 y <= {threshold} ms, se omite.")
                continue

            dropped = original_size - n_exec
            if dropped > 0:
                print(f"🚫 (sig={sig}, kem={kem}) removed extremes > {threshold} ms: {dropped} samples dropped")
            print(f"✅ (sig={sig}, kem={kem}) remaining samples: {n_exec}")

            # Desempaquetamos listas limpias
            ssl_clean    = [x[0] for x in filtered]
            hs_clean     = [x[1] for x in filtered]
            crypto_clean = [x[2] for x in filtered]
            pct_clean    = [x[3] for x in filtered]

            # Estadísticos
            mean_ssl, sd_ssl, median_ssl, q1_ssl, q3_ssl, iqr_ssl, min_ssl, max_ssl = compute_stats(ssl_clean)
            mean_hs, sd_hs, median_hs, q1_hs, q3_hs, iqr_hs, min_hs, max_hs        = compute_stats(hs_clean)
            mean_crypto, sd_crypto, median_crypto, q1_crypto, q3_crypto, iqr_crypto, min_crypto, max_crypto = compute_stats(crypto_clean)

            # Porcentajes (ya filtrados)
            mean_pct = stats.fmean(pct_clean) if pct_clean else 0.0
            min_pct  = min(pct_clean) if pct_clean else 0.0
            max_pct  = max(pct_clean) if pct_clean else 0.0    
        
        

            def fmt(x):
                return f"{x:.2f}".replace(".", ",")

            writer.writerow({
                "sig_alg": sig,
                "kem_alg": kem,
                "n_exec": n_exec,

                "mean_ssl_connect_ms": fmt(mean_ssl),
                "sd_ssl_connect_ms": fmt(sd_ssl),
                "median_ssl_connect_ms": fmt(median_ssl),
                "q1_ssl_connect_ms": fmt(q1_ssl),
                "q3_ssl_connect_ms": fmt(q3_ssl),
                "iqr_ssl_connect_ms": fmt(iqr_ssl),
                "min_ssl_connect_ms": fmt(min_ssl),
                "max_ssl_connect_ms": fmt(max_ssl),

                "mean_handshake_ms": fmt(mean_hs),
                "sd_handshake_ms": fmt(sd_hs),
                "median_handshake_ms": fmt(median_hs),
                "q1_handshake_ms": fmt(q1_hs),
                "q3_handshake_ms": fmt(q3_hs),
                "iqr_handshake_ms": fmt(iqr_hs),
                "min_handshake_ms": fmt(min_hs),
                "max_handshake_ms": fmt(max_hs),

                "mean_crypto_ms": fmt(mean_crypto),
                "sd_crypto_ms": fmt(sd_crypto),
                "median_crypto_ms": fmt(median_crypto),
                "q1_crypto_ms": fmt(q1_crypto),
                "q3_crypto_ms": fmt(q3_crypto),
                "iqr_crypto_ms": fmt(iqr_crypto),
                "min_crypto_ms": fmt(min_crypto),
                "max_crypto_ms": fmt(max_crypto),

                "mean_crypto_pct": fmt(mean_pct),
                "mean_crypto_pct_min": fmt(min_pct),
                "mean_crypto_pct_max": fmt(max_pct),
            })

    print(f"[OK] Resumen escrito en: {out_csv}")

def main():
    if len(sys.argv) < 3:
        print(f"Uso: {sys.argv[0]} directorio_csv TR|PQ [salida.csv]")
        sys.exit(1)

    csv_dir = Path(sys.argv[1])
    tipo = sys.argv[2].upper()
    out_csv = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("ltrace_crypto_summary.csv")

    if tipo not in ("TR", "PQ"):
        
        print("❌ ERROR: tipo debe ser TR o PQ")
        sys.exit(1)

    process_directory(csv_dir, tipo, out_csv)

if __name__ == "__main__":
    main()
