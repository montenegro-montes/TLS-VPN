#!/usr/bin/env python3

import pandas as pd
import numpy as np
import argparse
import os

def normalizar_firma(sig_alg):
    equivalencias = {
        'secp384r1': 'ecdsap384',
        'secp521r1': 'ecdsap521'
    }
    return equivalencias.get(sig_alg, sig_alg)

def normalizar_kem(kem_name):
    equivalencias = {
        'p-521': 'ecp-521'
    }
    return equivalencias.get(kem_name.lower(), kem_name.lower())

import numpy as np

def compute_stats(arr):
    """
    Devuelve dict con mean, sd, median, q1, q3, iqr, min, max.
    Si arr está vacío (o todo NaN), devuelve todo 0.0.
    """
    arr = np.asarray(arr, dtype=float)
    # quitar NaN
    arr = arr[~np.isnan(arr)]

    if arr.size == 0:
        return dict(
            mean=0.0, sd=0.0, median=0.0,
            q1=0.0, q3=0.0, iqr=0.0,
            min=0.0, max=0.0
        )

    mean = float(np.mean(arr))
    sd   = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    median = float(np.median(arr))
    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1
    min_v = float(np.min(arr))
    max_v = float(np.max(arr))

    return dict(
        mean=mean, sd=sd, median=median,
        q1=q1, q3=q3, iqr=iqr,
        min=min_v, max=max_v
    )


def fmt2(x):
    try:
        # Admite valores como "5,32" o "5.329481"
        return f"{float(str(x).replace(',', '.')):.2f}"
    except Exception:
        return str(x)    

def calcular_crypto_percent(handshake_csv, kem_csv, firma_csv, output_prefix=None):
    print(f"📥 Leyendo archivo de handshake: {handshake_csv}")

    # Firma a partir del nombre del fichero
    sig_alg = os.path.basename(handshake_csv).split('_')[0]
    sig_alg_normalizado = normalizar_firma(sig_alg)
    if output_prefix is None:
        output_prefix = sig_alg

    # 1ª línea = nombres de los KEM
    with open(handshake_csv, 'r') as f:
        kem_names_line = f.readline().strip()
        kem_names = kem_names_line.split(',')

    # El resto: tiempos de handshake (en ms)
    handshake_df = pd.read_csv(handshake_csv, skiprows=1, names=kem_names)

    print(f"🔐 Algoritmo de firma detectado: {sig_alg} (normalizado: {sig_alg_normalizado})")
    print(f"🔑 KEMs encontrados: {kem_names}\n")

    # CSV de primitivas KEM
    print(f"📥 Leyendo archivo de primitivas KEM: {kem_csv}")
    kem_df = pd.read_csv(kem_csv)
    kem_df['kem'] = kem_df['kem'].apply(normalizar_kem).str.lower()
    normalized_kem_names = [normalizar_kem(k).lower() for k in kem_names]
    kem_groups = {k: df for k, df in kem_df.groupby('kem')}

    # CSV de firma
    print(f"📥 Leyendo archivo de firma: {firma_csv}")
    firma_df = pd.read_csv(firma_csv)
    firma_group = firma_df.groupby('signature')
    if sig_alg_normalizado not in firma_group.groups:
        print(f"❌ Error: la firma '{sig_alg_normalizado}' no está en {firma_csv}")
        return

    firma_vals = firma_group.get_group(sig_alg_normalizado)[['sign', 'verify']].reset_index(drop=True)
    print(f"▶️ Firma: {sig_alg_normalizado} - {len(firma_vals)} muestras de firma\n")

    resultados = []

    for orig_kem, kem in zip(kem_names, normalized_kem_names):

        if kem not in kem_groups:
            print(f"⚠️ KEM '{orig_kem}' no encontrado en primitivas, se omite.")
            continue

        kem_vals = kem_groups[kem][['keygen', 'encaps', 'decaps']].reset_index(drop=True)

        # Columna del CSV de handshake que corresponde a este KEM
        if orig_kem in handshake_df.columns:
            handshake_col = orig_kem
        elif kem in handshake_df.columns:
            handshake_col = kem
        else:
            print(f"❌ KEM '{orig_kem}' no encontrado como columna en el CSV de handshake.")
            continue


        # --- 1) Estadísticos de handshake sobre TODAS las ejecuciones ---
        handshake_vals = handshake_df[handshake_col].values.astype(float)

        # Filtramos tiempos > 0 por seguridad
        handshake_vals = handshake_vals[handshake_vals > 0]
        if handshake_vals.size == 0:
            print(f"⚠️ Columna {handshake_col} sin datos > 0, se omite.")
            continue

        # --- Filtrado de extremos (> 1000 ms) ------------------------------------
        threshold = 1000  # ms
        original_size = handshake_vals.size

        hs_all = handshake_vals[handshake_vals <= threshold]
        dropped = original_size - hs_all.size

        if dropped > 0:
            print(f"🚫 Removed extremes > {threshold} ms: {dropped} samples dropped en {handshake_col}")
        print(f"✅ Remaining samples for {handshake_col}: {hs_all.size}")

        if hs_all.size == 0:
            print(f"⚠️ Columna {handshake_col} sin datos tras filtrar > {threshold} ms, se omite.")
            continue

        # Estadísticos finales
        stats_ssl = compute_stats(hs_all)
        n_exec_handshake = int(hs_all.size)

        # --- 2) Crypto y porcentaje sobre las N muestras comunes ---

        # Número de muestras que podemos alinear entre:
        #   - primitivas KEM
        #   - primitivas de firma
        #   - handshake (usamos las primeras N)
        n_ratio = min(len(kem_vals), len(firma_vals), len(hs_all))

        if n_ratio == 0:
            print(f"⚠️ No hay muestras comunes para {orig_kem}, se omite.")
            continue

        hs_for_ratio = hs_all[:n_ratio]

        crypto_total = (
            kem_vals.loc[:n_ratio-1, 'keygen'].values +
            # Si quisieras añadir encaps, descoméntalo:
            # kem_vals.loc[:n_ratio-1, 'encaps'].values +
            kem_vals.loc[:n_ratio-1, 'decaps'].values +
            1 * firma_vals.loc[:n_ratio-1, 'sign'].values +
            3 * firma_vals.loc[:n_ratio-1, 'verify'].values
        ).astype(float)

        # Evitar divisiones por cero
        mask = hs_for_ratio > 0
        hs_for_ratio = hs_for_ratio[mask]
        crypto_total = crypto_total[mask]

        if hs_for_ratio.size == 0:
            print(f"⚠️ Todas las muestras alineadas de handshake son 0 para {orig_kem}, se omite.")
            continue

        crypto_percent = 100.0 * crypto_total / hs_for_ratio

        stats_crypto = compute_stats(crypto_total)
        mean_pct = float(np.mean(crypto_percent))
        min_pct  = float(np.min(crypto_percent))
        max_pct  = float(np.max(crypto_percent))

        resultados.append({
            'sig_alg': sig_alg,
            'kem_alg': orig_kem,
            # número de ejecuciones de TLS usadas para las estadísticas externas
            'n_exec': n_exec_handshake,

            'mean_ssl_connect_ms': fmt2(stats_ssl['mean']),
            'sd_ssl_connect_ms': fmt2(stats_ssl['sd']),
            'median_ssl_connect_ms': fmt2(stats_ssl['median']),
            'q1_ssl_connect_ms': fmt2(stats_ssl['q1']),
            'q3_ssl_connect_ms': fmt2(stats_ssl['q3']),
            'iqr_ssl_connect_ms': fmt2(stats_ssl['iqr']),
            'min_ssl_connect_ms': fmt2(stats_ssl['min']),
            'max_ssl_connect_ms': fmt2(stats_ssl['max']),

            'mean_crypto_ms': fmt2(stats_crypto['mean']),
            'sd_crypto_ms': fmt2(stats_crypto['sd']),
            'median_crypto_ms': fmt2(stats_crypto['median']),
            'q1_crypto_ms': fmt2(stats_crypto['q1']),
            'q3_crypto_ms': fmt2(stats_crypto['q3']),
            'iqr_crypto_ms': fmt2(stats_crypto['iqr']),
            'min_crypto_ms': fmt2(stats_crypto['min']),
            'max_crypto_ms': fmt2(stats_crypto['max']),

            'mean_crypto_pct': fmt2(mean_pct),
            'mean_crypto_pct_min': fmt2(min_pct),
            'mean_crypto_pct_max': fmt2(max_pct),
        })

    if not resultados:
        print("❌ No hay datos válidos para generar el CSV.")
        return

    cols = [
        'sig_alg', 'kem_alg', 'n_exec',
        'mean_ssl_connect_ms', 'sd_ssl_connect_ms', 'median_ssl_connect_ms',
        'q1_ssl_connect_ms', 'q3_ssl_connect_ms', 'iqr_ssl_connect_ms',
        'min_ssl_connect_ms', 'max_ssl_connect_ms',
        'mean_crypto_ms', 'sd_crypto_ms', 'median_crypto_ms',
        'q1_crypto_ms', 'q3_crypto_ms', 'iqr_crypto_ms',
        'min_crypto_ms', 'max_crypto_ms',
        'mean_crypto_pct', 'mean_crypto_pct_min', 'mean_crypto_pct_max'
    ]

    resultados_df = pd.DataFrame(resultados)[cols]

    csv_filename = f"{output_prefix}_summary.csv"
    resultados_df.to_csv(csv_filename, index=False)
    print(f"\n✅ Resultados exportados en CSV: {csv_filename}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calcula el Crypto % por KEM con estadísticas completas a partir de archivos CSV."
    )
    parser.add_argument('handshake_csv', help='Archivo CSV con los tiempos de handshake (2000 ejecuciones, en ms)')
    parser.add_argument('kem_csv', help='Archivo CSV con las medidas de primitivas KEM')
    parser.add_argument('firma_csv', help='Archivo CSV con las medidas de firma')
    parser.add_argument('--output_prefix', default=None,
                        help='Prefijo para el CSV de salida (por defecto usa el nombre de la firma)')

    args = parser.parse_args()
    calcular_crypto_percent(args.handshake_csv, args.kem_csv, args.firma_csv, args.output_prefix)
