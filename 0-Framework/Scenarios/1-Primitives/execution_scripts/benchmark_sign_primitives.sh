#!/bin/bash

show_help() {
  echo "🔧 Usage: $0 [algorithms] [repeats]"
  echo
  echo "  algorithms : Comma-separated list of SIGNATURE algorithms to benchmark"
  echo "               (default: full list of supported algorithms)"
  echo "  repeats    : Number of repetitions per algorithm (default: 50)"
  echo
  echo "📌 Examples:"
  echo "  $0                            → run full benchmark (default set, 50 times)"
  echo "  $0 ed25519,ecdsap384          → only for two algorithms, 50 repetitions"
  echo "  $0 ed25519,ecdsap384 100      → two algorithms, 100 repetitions"
  echo
  echo "  $0 --help                     → show this help message"
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


# Help flag
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  show_help
fi

# Read arguments
if [[ -n "$1" ]]; then
    IFS=',' read -r -a ALGS <<< "$1"
    echo $1
else
   ALGS=("ed25519" "ecdsap384" "ecdsap521")
fi

if [[ -n "$2" ]]; then
    REPEATS="$2"
else
    REPEATS="50"
fi




OPENSSL_BIN="openssl"


echo "📍 Benchmarking the following algorithms: ${ALGS[*]}"
echo "🔁 Repetitions per algorithm: $REPEATS"

if [[ ! -x "$OPENSSL_BIN" ]]; then
  echo "❌ Not found OpenSSL in path:: $OPENSSL_BIN"
  exit 1
fi

for alg in "${ALGS[@]}"; do  
  echo "⚙️  Executing $REPEATS times benchmark for: $alg"

  signfile=$(mktemp)
  verifyfile=$(mktemp)

  for i in $(seq 1 $REPEATS); do
    printf "Run %3d/%3d: " "$i" "$REPEATS"
    # Ejecuta el benchmark y captura la línea resumen
    summary=$("$OPENSSL_BIN" speed -elapsed -mlock -seconds 10 "$alg" 2>&1 | tail -n1)

    # Extrae ops/s de sign (campo NF-1) y verify (campo NF)
    sign_per_s=$(awk '{print $(NF-1)}' <<< "$summary")
    verify_per_s=$(awk '{print $NF}'    <<< "$summary")

    # Calcula el tiempo por operación en segundos con 8 dígitos
    sign_s=$(awk -v v="$sign_per_s"   'BEGIN{printf "%.8f", 1/v}')
    verify_s=$(awk -v v="$verify_per_s" 'BEGIN{printf "%.8f", 1/v}')

    # Convierte a milisegundos para guardar
    sign_ms=$(awk -v s="$sign_s"   'BEGIN{printf "%.3f", s*1000}')
    verify_ms=$(awk -v s="$verify_s" 'BEGIN{printf "%.3f", s*1000}')

    echo "  sign: $sign_ms ms   verify: $verify_ms ms"

    echo "$sign_ms" >> "$signfile"
    echo "$verify_ms" >> "$verifyfile"
  done

  echo
  echo "✅ Finished $REPEATS executions for: $alg"
  echo "--------------------------------------------"
  compute_stats "$signfile" "sign ($alg)"
  compute_stats "$verifyfile" "verify ($alg)"
  echo

  rm -f "$signfile" "$verifyfile"
done




