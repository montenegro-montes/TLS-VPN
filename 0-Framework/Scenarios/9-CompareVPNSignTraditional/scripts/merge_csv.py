#!/usr/bin/env python3
import sys
import csv
import os

if len(sys.argv) < 3 or len(sys.argv) > 4:
    print(f"Usage: {sys.argv[0]} <signature_alg> <tag> [--vpn]")
    sys.exit(1)

sig_alg = sys.argv[1]
tag = sys.argv[2]
use_vpn = len(sys.argv) == 4 and sys.argv[3] == '--vpn'

prefix = "vpn" if use_vpn else "tls"


outfile = f"{sig_alg}_{prefix}_{tag}.csv"
suffix = '_vpn.csv' if use_vpn else '_handshakes.csv'

# Seleccionar KEMs según la firma
if sig_alg == "ed25519":
    kem_list = [
        "x25519",
        "x25519_mlkem512",
        "mlkem512",
        "x25519_hqc128",
        "hqc128"
    ]
elif sig_alg == "secp384r1":
    kem_list = [
        "x448",
        "x448_mlkem768",
        "mlkem768",
        "x448_hqc192",
        "hqc192"
    ]
elif sig_alg == "secp521r1":
    kem_list = [
        "p521",
        "p521_mlkem1024",
        "mlkem1024",
        "p521_hqc256",
        "hqc256"
    ]
else:
    print(f"❌ Unsupported signature algorithm: {sig_alg}")
    sys.exit(1)


# Inicializamos salida
data = []
max_len = 0

for kem in kem_list:
    fname = f"{sig_alg}-{kem}{suffix}"
    try:
        with open(fname) as f:
            lines = f.read().splitlines()[2:]  # Saltar cabeceras
            values = [float(x) for x in lines]
            data.append(values)
            max_len = max(max_len, len(values))
    except FileNotFoundError:
        print(f"⚠️  Not found: {fname}")
        data.append([])
    except Exception as e:
        print(f"❌ Error reading {fname}: {e}")
        data.append([])

# Escribir el CSV combinado
with open(outfile, "w", newline="") as fout:
    writer = csv.writer(fout)
    writer.writerow(kem_list)
    for i in range(max_len):
        row = []
        for kem_values in data:
            row.append(f"{kem_values[i]:.2f}" if i < len(kem_values) else "")
        writer.writerow(row)


print(f"✅ File generated: {outfile}")
