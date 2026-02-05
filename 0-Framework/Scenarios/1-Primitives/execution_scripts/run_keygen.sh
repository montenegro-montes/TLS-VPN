#!/bin/bash

export LC_NUMERIC=C


DOCKER_IMAGE="uma-tls_quic-pq-34"
CONTAINER_NAME="isolated-bench"
ITERATIONS=51
ALGORITHMS=("ED25519" "SECP384R1" "SECP521R1" "MLDSA44" "MLDSA65" "MLDSA87")

# ⚙️ Container resource constraints
CPUSET="2"
CPUS="1.0"
CPU_SHARES="2048"
PIDS_LIMIT="64"
IPC_LOCK_CAP="IPC_LOCK"
NETWORK_MODE="none"

# 📁 Prepare output folder
mkdir -p results

# 🚀 Start isolated container
echo "🚀 Starting isolated container: $CONTAINER_NAME"
docker run -dit \
  --name "$CONTAINER_NAME" \
  --cpuset-cpus="$CPUSET" \
  --cpus="$CPUS" \
  --cpu-shares="$CPU_SHARES" \
  --pids-limit="$PIDS_LIMIT" \
  --cap-add="$IPC_LOCK_CAP" \
  --network="$NETWORK_MODE" \
  "$DOCKER_IMAGE" \
  bash

# 🧪 Function to benchmark a key generation algorithm
benchmark_algorithm() {
    local alg=$1
    local cmd=$2
    local csv_file="results/${alg}_timing.csv"
    echo "iter,ms" > "$csv_file"

    for i in $(seq 1 $ITERATIONS); do
        echo "🔁 [$alg] Iteration $i/$ITERATIONS"

        # Usar tiempo de ejecución interno de Bash (más preciso que date)
       time_ms=$(docker exec "$CONTAINER_NAME" bash -c "
            start=\$(date +%s%N)
            $cmd
            end=\$(date +%s%N)
            elapsed_ns=\$((end - start))
            awk -v ns=\$elapsed_ns 'BEGIN { printf \"%.3f\", ns / 1000000 }'
        ")

        #time_ms=$(docker exec "$CONTAINER_NAME" bash -c "
        #    start=\$(date +%s%N)
        #    $cmd
        #    end=\$(date +%s%N)
        #    echo \$(( (end - start) / 1000000 ))
        #")
        echo "$i,$time_ms" >> "$csv_file"
    done
}

# 🧬 Execute benchmark for all algorithms
for alg in "${ALGORITHMS[@]}"; do
    case $alg in
        ED25519)
            benchmark_algorithm "$alg" "openssl genpkey -algorithm ED25519 -out /dev/null"
            ;;
        SECP384R1)
            benchmark_algorithm "$alg" "openssl ecparam -name secp384r1 -genkey -noout > /dev/null"
            ;;
        SECP521R1)
            benchmark_algorithm "$alg" "openssl ecparam -name secp521r1 -genkey -noout > /dev/null"
            ;;
        MLDSA44|MLDSA65|MLDSA87)
            benchmark_algorithm "$alg" "openssl genpkey -algorithm $alg -out /dev/null"
            ;;
        *)
            echo "⚠️ Unknown algorithm: $alg"
            ;;
    esac
done

# 📊 Analyze results using Python
echo -e "\n📊 Summary (via Python):"
python3 analyze_csvs.py

# 🧹 Cleanup
echo -e "\n🧹 Stopping and removing container..."
docker stop "$CONTAINER_NAME" >/dev/null
docker rm "$CONTAINER_NAME" >/dev/null

echo "✅ Benchmark completed. Results saved in ./results/"

