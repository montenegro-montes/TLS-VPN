#!/bin/bash


    # Constant
  CONTAINER_NAME="uma-primitives-benchmark"
  IMAGE_NAME="uma-tls_quic-pq-34"
  TARGET_PATH="/opt/oqssa/bin"


usage() {
  echo ""
  echo "📘 Usage:"
  echo "  $0                  → Show interactive menu"
  echo "  $0 [script.sh]      → Run script directly in container"
  echo "  $0 -h | --help      → Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 benchmark_kem_primitives.sh"
  echo "  $0 --help"
  echo ""
  exit 0
}


show_menu() {
    echo "╔════════════════════════════════════════╗"
    echo "║      Benchmark Primitives              ║"
    echo "╠════════════════════════════════════════╣"
    echo "║ 1️⃣  KEM                                 ║"
    echo "║ 2️⃣  SIGNATURES  Traditional             ║"
    echo "║ 3️⃣  SIGNATURES  PQ                      ║"
    echo "║ 4️⃣  SIGNATURES  KeyGen                  ║"
    echo "║ 5️⃣  Exit                                ║"
    echo "╚════════════════════════════════════════╝"
}

###############################
#
# Docker Check
#
###############################

docker_installedAndRunning() {
  # Check if Docker is installed
  if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker is not installed or not in PATH."
    echo "   Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
  fi

  echo "🐳 Docker is installed. Proceeding with container execution..."

  # Optional: Check Docker daemon is running
  if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is installed but the daemon is not running."

    echo "✅ Running docker."
    docker desktop start

  fi
}


docker_installedAndRunning

execute (){

    local SCRIPT_NAME="$1"
    # Parámetros de aislamiento
    CPUSET="2"                 # pin a CPU 2
    CPUS="1.0"                 # hasta 1 CPU entera
    CPU_SHARES="2048"          # prioridad alta vs otros contenedores
    PIDS_LIMIT="64"            # máximo 64 procesos
    IPC_LOCK_CAP="IPC_LOCK"    # permitir mlock
    NETWORK_MODE="none"        # sin red


    # Check local script 
    if [[ ! -x "$SCRIPT_NAME" ]]; then
        echo "❌ Script $SCRIPT_NAME does not found ."
        exit 1
    fi



    # ¿Ya existe el contenedor?
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "🔄 Container ${CONTAINER_NAME} already exists. Starting..."
        docker start "$CONTAINER_NAME" >/dev/null
    else
        echo "🚀 Creating new container ${CONTAINER_NAME} with isolation flags..."
        docker run -dit \
          --name "$CONTAINER_NAME" \
          --cpuset-cpus="$CPUSET" \
          --cpus="$CPUS" \
          --cpu-shares="$CPU_SHARES" \
          --pids-limit="$PIDS_LIMIT" \
          --cap-add="$IPC_LOCK_CAP" \
          --network="$NETWORK_MODE" \
          "$IMAGE_NAME" \
          bash
    fi

    # Crear carpeta destino si no existe
    echo "📁 Ensuring target directory in the container..."
    docker exec "$CONTAINER_NAME" mkdir -p "$TARGET_PATH"

    # Copiar el script
    echo "📤 Copying $SCRIPT_NAME to container..."
    docker cp "$SCRIPT_NAME" "$CONTAINER_NAME:$TARGET_PATH/"

    # Ejecutar
    echo "▶️ Executing the benchmark script inside the container..."
    docker exec -it "$CONTAINER_NAME" bash -c "cd $TARGET_PATH && bash $SCRIPT_NAME ${@:2}"

    # Opcional: si quieres eliminar el contenedor al terminar
    echo "🧹 Cleaning up container..."
    docker rm -f "$CONTAINER_NAME"
}

# =====================
# Help or direct execution
# =====================
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
fi

if [[ -n "$1" ]]; then
    if [[ -f "$1" && -x "$1" ]]; then
        execute "$1"
        exit 0
    else
        echo "❌ Error: '$1' is not a valid executable script file."
        usage
    fi
fi

# =====================
# Main Menu Loop
# =====================
while true; do
    show_menu
    echo ""
    read -p "👉 Please enter your choice [1-5]: " choice
    echo ""
    case $choice in
        1) execute "benchmark_kem_primitives.sh" ;;
        2) execute "benchmark_sign_primitives.sh" ;;
        3) execute "benchmark_sign_primitives.sh" "mldsa44,mldsa65,mldsa87" ;;
        4) execute "run_keygen.sh" ;;
        5) echo "👋 Goodbye!" ; exit 0 ;;
        *) echo "❌ Invalid option. Please try again." ;;
    esac
    echo ""
done
