import re
import csv
import sys
from collections import defaultdict
from itertools import zip_longest

if len(sys.argv) != 3:
    print(f"Uso: {sys.argv[0]} <archivo_logs> <tag>")
    sys.exit(1)

log_file = sys.argv[1]

tag = sys.argv[2]

# Leer archivo
with open(log_file, 'r') as f:
    content = f.read()

pattern = re.compile(
    r"Running .*?with SIG_ALG=(\w+) and KEM_ALG=([-\w]+)\s+(.*?)(?=Running|\Z)",
    re.DOTALL
)

execution_pattern = re.compile(r"Execution \d+ - (TLS|QUIC)", re.IGNORECASE)
handshake_pattern = re.compile(r"Handshake duration: ([\d.]+) ms")

resultados = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
orden_kems = defaultdict(lambda: defaultdict(list))

for match in pattern.finditer(content):
    sig_alg = match.group(1)
    kem_alg = match.group(2)
    block = match.group(3)

    current_protocolo = None

    for line in block.splitlines():
        exec_match = execution_pattern.search(line)
        if exec_match:
            current_protocolo = exec_match.group(1).upper()
            continue

        hs_match = handshake_pattern.search(line)
        if hs_match and current_protocolo:
            duration = float(hs_match.group(1))
            if kem_alg not in orden_kems[current_protocolo][sig_alg]:
                orden_kems[current_protocolo][sig_alg].append(kem_alg)
            resultados[current_protocolo][sig_alg][kem_alg].append(duration)

# Guardar los CSVs
for protocolo, firmas in resultados.items():
    for sig_alg, kem_dict in firmas.items():
        kems = orden_kems[protocolo][sig_alg]
        rows = list(zip_longest(*(kem_dict[kem] for kem in kems), fillvalue=""))

        filename = f"{sig_alg}_{protocolo.lower()}_{tag}.csv"

        print(filename)
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(kems)
            writer.writerows(rows)

print("CSV creados por cada SIG_ALG y protocolo (TLS/QUIC), columnas por KEM_ALG en orden de aparición.")