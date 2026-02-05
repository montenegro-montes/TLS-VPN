#!/usr/bin/env python3
import re
import sys
import csv
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------
#  REGEX
# ---------------------------------------------------------

# Cabecera que indica algoritmo de firma y KEM
RE_HEADER = re.compile(
    r'Running .* SIG_ALG=(?P<sig>\S+) and KEM_ALG=(?P<kem>\S+)'
)

# Inicio de cada ejecución
RE_EXEC = re.compile(
    r'Execution\s+(?P<exec>\d+)\s*-\s*(?P<proto>\S+)(?:\s+(?P<mode>.*))?'
)

# Funciones de libssl.so.3 u oqsprovider.so en una sola línea
# Ejemplo:
#   libssl.so.3->EVP_PKEY_keygen(...) = 1 <0.000358>
#   oqsprovider.so->OQS_KEM_decaps(...) = 0 <0.003226>
RE_LIB_OQS_FUNC = re.compile(
    r'(?P<lib>libssl\.so\.3|oqsprovider\.so)->(?P<func>[A-Za-z0-9_]+)\(.*<(?P<secs>[0-9.]+)>\s*$'
)

# Llamadas partidas en dos líneas:
#   <... FUNC resumed> ) = 1 <0.003987>
RE_RESUMED_FUNC = re.compile(
    r'<\.\.\. (?P<func>[A-Za-z0-9_]+) resumed>.*<(?P<secs>[0-9.]+)>\s*$'
)

# SSL_connect en una sola línea:
#   openssl->SSL_connect(...) = 1 <0.006580>
RE_SSL_CONNECT_ONE = re.compile(
    r'openssl->SSL_connect\([^)]*\)\s*=\s*1\s*<(?P<secs>[0-9.]+)>\s*$'
)

# SSL_connect "resumed":
#   <... SSL_connect resumed> ) = 1 <0.007061>
RE_SSL_CONNECT_RESUMED = re.compile(
    r'SSL_connect resumed>.*<(?P<secs>[0-9.]+)>\s*$'
)

# Tiempo de handshake que imprime tu script:
#   Handshake duration: 6.78 ms
RE_HS_DURATION = re.compile(
    r'Handshake duration:\s*(?P<ms>[0-9.]+)\s*ms'
)


# ---------------------------------------------------------
#  PARSER
# ---------------------------------------------------------

def parse_log(path: Path):
    """
    Devuelve:
      data[(sig, kem)] = {
          "func_names": set([...]),
          "rows": [
              {
                  "exec_id": int,
                  "proto": str,
                  "mode": str,
                  "ssl_connect_ms": float | None,
                  "handshake_ms": float | None,
                  "func_times": { func_name: total_ms }
              },
              ...
          ]
      }
    """
    data = defaultdict(lambda: {"func_names": set(), "rows": []})

    current_sig = None
    current_kem = None
    current_block_key = None
    current_exec = None   # dict con la ejecución en curso

    # Profundidad de secciones "<unfinished ...>" abiertas (por si lo necesitas más adelante)
    unfinished_depth = 0

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")

            # Detectar aparición de "<unfinished ...>" en cualquier línea
            if "<unfinished ...>" in line:
                unfinished_depth += 1

            # 1) Cabecera con SIG_ALG y KEM_ALG
            m = RE_HEADER.search(line)
            if m:
                # Guardar ejecución anterior del bloque previo (si existe)
                if current_block_key is not None and current_exec is not None:
                    data[current_block_key]["rows"].append(current_exec)
                    current_exec = None

                current_sig = m.group("sig")
                current_kem = m.group("kem")
                current_block_key = (current_sig, current_kem)
                continue

            # Hasta que no haya SIG/KEM, no hacemos nada
            if current_block_key is None:
                continue

            # 2) Nueva ejecución
            m = RE_EXEC.search(line)
            if m:
                # Guardar la ejecución anterior si existía
                if current_exec is not None:
                    data[current_block_key]["rows"].append(current_exec)

                exec_id = int(m.group("exec"))
                proto = m.group("proto")
                mode = (m.group("mode") or "").strip()

                current_exec = {
                    "exec_id": exec_id,
                    "proto": proto,
                    "mode": mode,
                    "ssl_connect_ms": None,
                    "handshake_ms": None,
                    "func_times": defaultdict(float),
                }
                continue

            # Si no hay ejecución abierta, solo podría haber Handshake "huérfano"
            if current_exec is None:
                m = RE_HS_DURATION.search(line)
                if m:
                    # no sabemos a qué ejecución asociarlo si no hay current_exec
                    pass
                continue

            # 3) SSL_connect en una sola línea
            m = RE_SSL_CONNECT_ONE.search(line)
            if m:
                secs = float(m.group("secs"))
                current_exec["ssl_connect_ms"] = secs * 1000.0
                continue

            # 3.b) SSL_connect "resumed"
            m = RE_SSL_CONNECT_RESUMED.search(line)
            if m:
                secs = float(m.group("secs"))
                current_exec["ssl_connect_ms"] = secs * 1000.0
                # Cerramos una sección unfinished si la hubiera
                if unfinished_depth > 0:
                    unfinished_depth -= 1
                continue

            # 4) Funciones de libssl.so.3 u oqsprovider.so en una sola línea
            m = RE_LIB_OQS_FUNC.search(line)
            if m:
                lib = m.group("lib")
                func = m.group("func")
                secs = float(m.group("secs"))
                ms = secs * 1000.0

                # ⚠️ NUEVO: solo contamos funciones de libssl.so.3
                # Todo lo de oqsprovider.so (OQS_KEM_*, EVP_PKEY_*, etc.) se ignora.
                if lib == "oqsprovider.so":
                    continue

                current_exec["func_times"][func] += ms
                data[current_block_key]["func_names"].add(func)
                continue

            # 4.b) Llamadas "resumed" genéricas (EVP_PKEY_keygen, EVP_PKEY_decapsulate, etc.)
            m = RE_RESUMED_FUNC.search(line)
            if m:
                func = m.group("func")
                # SSL_connect ya lo tratamos aparte
                if func != "SSL_connect":
                    secs = float(m.group("secs"))
                    ms = secs * 1000.0
                    current_exec["func_times"][func] += ms
                    data[current_block_key]["func_names"].add(func)

                # Cerramos una sección "<unfinished ...>" si la hubiera
                if unfinished_depth > 0:
                    unfinished_depth -= 1
                continue

            # 5) Tiempo de Handshake duration (script)
            m = RE_HS_DURATION.search(line)
            if m:
                ms = float(m.group("ms"))
                current_exec["handshake_ms"] = ms
                continue

    # Guardar la última ejecución si está abierta
    if current_exec is not None and current_block_key is not None:
        data[current_block_key]["rows"].append(current_exec)

    return data


# ---------------------------------------------------------
#  ESCRITURA A CSV (con coma decimal)
# ---------------------------------------------------------

def write_csvs(data, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    for (sig, kem), info in data.items():
        func_names = sorted(info["func_names"])
        rows = info["rows"]

        if not rows:
            continue

        fname = f"{sig}_{kem}.csv"
        out_path = out_dir / fname

        fieldnames = [
            "exec_id",
            "sig_alg",
            "kem_alg",
            "proto",
            "mode",
            "ssl_connect_ms",
            "handshake_ms",
        ] + func_names

        with out_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for r in rows:
                row = {
                    "exec_id": r["exec_id"],
                    "sig_alg": sig,
                    "kem_alg": kem,
                    "proto": r["proto"],
                    "mode": r["mode"],
                    "ssl_connect_ms": (
                        f"{r['ssl_connect_ms']:.2f}".replace(".", ",")
                        if r["ssl_connect_ms"] is not None
                        else ""
                    ),
                    "handshake_ms": (
                        f"{r['handshake_ms']:.2f}".replace(".", ",")
                        if r["handshake_ms"] is not None
                        else ""
                    ),
                }

                for func in func_names:
                    t = r["func_times"].get(func, 0.0)
                    row[func] = f"{t:.2f}".replace(".", ",")

                writer.writerow(row)

        print(f"[OK] Escrito {out_path} con {len(rows)} ejecuciones.")


# ---------------------------------------------------------
#  MAIN
# ---------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} L1.log [directorio_salida]")
        sys.exit(1)

    log_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path("csv_ltrace")

    data = parse_log(log_path)
    write_csvs(data, out_dir)


if __name__ == "__main__":
    main()
