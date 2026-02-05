#!/bin/bash

show_help() {
  echo "🔧 Usage: $0 [algorithms] [repeats]"
  echo
  echo "  algorithms : Comma-separated list of KEM algorithms to benchmark"
  echo "               (default: full list of supported algorithms)"
  echo "  repeats    : Number of repetitions per algorithm (default: 50)"
  echo
  echo "📌 Examples:"
  echo "  $0                            → run full benchmark (default set, 50 times)"
  echo "  $0 mlkem512,x25519_mlkem512  → only for two algorithms, 50 repetitions"
  echo "  $0 mlkem768,mlkem1024 100    → two algorithms, 100 repetitions"
  echo
  echo "  $0 --help                    → show this help message"
  echo
  exit 0
}

compute_stats() {
  local file=$1
  local name=$2
  echo "=== Stadistics to $name ==="
  mapfile -t values < <(sort -n "$file")
  local n=${#values[@]}
  if (( n == 0 )); then
    echo "$file has not  data to process "
    return
  fi

  local sum=0
  local sum2=0
  for v in "${values[@]}"; do
    sum=$(awk -v a="$sum" -v b="$v" 'BEGIN{printf "%f", a + b}')
    sum2=$(awk -v a="$sum2" -v b="$v" 'BEGIN{printf "%f", a + (b)^2}')
  done

  # Calcular media y std sin redondear para CV
  local mean_raw
  local std_raw
  mean_raw=$(awk -v sum="$sum" -v n="$n" 'BEGIN{print sum/n}')
  std_raw=$(awk -v sum="$sum" -v sum2="$sum2" -v n="$n" 'BEGIN{
    print sqrt((sum2 - (sum^2)/n)/(n > 1 ? n - 1 : 1))
  }')

  local mean=$(awk -v m="$mean_raw" 'BEGIN{printf "%.3f", m}')
  local std=$(awk -v s="$std_raw" 'BEGIN{printf "%.3f", s}')
  local cv=$(awk -v s="$std_raw" -v m="$mean_raw" 'BEGIN{printf "%.2f", s/m*100}')

  local min=${values[0]}
  local max=${values[$((n-1))]}

  local median
  if (( n % 2 == 1 )); then
    median=${values[$((n/2))]}
  else
    local a=${values[$((n/2-1))]}
    local b=${values[$((n/2))]}
    median=$(awk -v a="$a" -v b="$b" 'BEGIN{printf "%.3f", (a + b)/2}')
  fi

  percentile() {
    local p=$1
    local pos=$(awk -v p="$p" -v n="$n" 'BEGIN{print p/100*(n-1)}')
    local idx=${pos%.*}
    local frac=$(awk -v pos="$pos" -v idx="$idx" 'BEGIN{print pos - idx}')
    local a=${values[$idx]}
    local b=${values[$((idx+1))]:-$a}
    awk -v a="$a" -v b="$b" -v f="$frac" 'BEGIN{printf "%.3f", a + f*(b - a)}'
  }

  local p50=$median
  local p90=$(percentile 90)
  local p95=$(percentile 95)
  local p99=$(percentile 99)

  local throughput=$(awk -v m="$mean_raw" 'BEGIN{printf "%.0f", 1000/m}')

  printf "Count      : %d\n" "$n"
  printf "Min        : %.3f ms\n" "$min"
  printf "Max        : %.3f ms\n" "$max"
  printf "Mean       : %.3f ms\n" "$mean"
  printf "Std Dev    : %.3f ms\n" "$std"
  printf "CV         : %.2f %%\n" "$cv"
  printf "Median(p50): %.3f ms\n" "$p50"
  printf "p90        : %.3f ms\n" "$p90"
  printf "p95        : %.3f ms\n" "$p95"
  printf "p99        : %.3f ms\n" "$p99"
  printf "Throughput : %s ops/s\n" "$throughput"
}


# Read arguments
if [[ -n "$1" ]]; then
    IFS=',' read -r -a ALGS <<< "$1"
else
    ALGS=("${DEFAULT_ALGS[@]}")
fi

if [[ -n "$2" ]]; then
    REPEATS="$2"
else
    REPEATS="$DEFAULT_REPEATS"
fi

# Help flag
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  show_help
fi



# Primitives Algorithm
ALGS=(   "X25519" "X448" "ECP-521" "mlkem512" "x25519_mlkem512" "mlkem768"  "x448_mlkem768"  "mlkem1024" "p521_mlkem1024"   "hqc128" "x25519_hqc128" "hqc192" "x448_hqc192"  "hqc256" "p521_hqc256")
#ALGS=(   "mlkem512"  "mlkem768" "mlkem1024" )

REPEATS=50

# Ruta al binario de OpenSSL 
OPENSSL_BIN="openssl"

# Comprobamos si existe el binario
if [[ ! -x "$OPENSSL_BIN" ]]; then
    echo "❌ Not found OpenSSL in path: $OPENSSL_BIN"
    exit 1
fi


for alg in "${ALGS[@]}"; do
    echo "⚙️  Executing ${REPEATS} times benchmark for: $alg"

    # Borra o crea los ficheros de datos
      keyfile=$(mktemp)
      encfile=$(mktemp)
      decfile=$(mktemp)

     # Inicializa sumas a cero
    sum_keygen=0
    sum_encaps=0
    sum_decaps=0

    for i in $(seq 1 $REPEATS); do
        printf "Run %3d/%3d: " "$i" "$REPEATS"
        # Ejecuta el benchmark, coge solo la última línea y la parsea
        summary=$(
          "$OPENSSL_BIN" speed -elapsed -mlock -seconds 10 "$alg" 2>&1 \
          | tail -n1
        )

        # extrae las cadenas “0.000024s”…
        read -r _ keygen_s encaps_s decaps_s _ <<< "$summary"

        # convierte a ms
        keygen_ms=$(awk "BEGIN{printf \"%.3f\", ${keygen_s%s}*1000}")
        encaps_ms=$(awk "BEGIN{printf \"%.3f\", ${encaps_s%s}*1000}")
        decaps_ms=$(awk "BEGIN{printf \"%.3f\", ${decaps_s%s}*1000}")

        sum_keygen=$(awk "BEGIN{print $sum_keygen + $keygen_ms}")
        sum_encaps=$(awk "BEGIN{print $sum_encaps + $encaps_ms}")
        sum_decaps=$(awk "BEGIN{print $sum_decaps + $decaps_ms}")

        # Mostramos el resultado
        echo "  keygen : $keygen_ms ms encaps: $encaps_ms ms decaps: $decaps_ms ms" 

        echo "$keygen_ms" >> "$keyfile"
        echo "$encaps_ms" >> "$encfile"
        echo "$decaps_ms" >> "$decfile"

    done

    # Calcula medias
    avg_keygen=$(awk "BEGIN{printf \"%.3f\", $sum_keygen/$REPEATS}")
    avg_encaps=$(awk "BEGIN{printf \"%.3f\", $sum_encaps/$REPEATS}")
    avg_decaps=$(awk "BEGIN{printf \"%.3f\", $sum_decaps/$REPEATS}")

    echo "  keygen encaps decaps  " 
    echo "  $keygen_ms $encaps_ms $decaps_ms" 


    echo "✅ Finished $REPEATS executions for: $alg"
    echo "--------------------------------------------"
   
     # Estadísticas detalladas
      compute_stats "$keyfile" "keygen"
      compute_stats "$encfile" "encaps"
      compute_stats "$decfile" "decaps"

      rm -f "$keyfile" "$encfile" "$decfile"
    echo
   
done




