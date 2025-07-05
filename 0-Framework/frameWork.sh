#!/bin/bash

# =====================
# VBLES Definitions
# =====================
DOCKER_DIR_TLS="Dockers/TLS-QUIC-PQ"
DOCKER_IMAGE_TLS="uma-tls_quic-pq-34"


DOCKER_DIR_VPN="Dockers/VPN-PQ"
DOCKER_IMAGE_VPN="uma-vpn-pq-34"

DOCKER_DIR="$DOCKER_DIR_TLS"
DOCKER_IMAGE="$DOCKER_IMAGE_TLS"

INSTALL_DIR="./Applications"
PUMBA_BIN="$INSTALL_DIR/pumba"

show_menu() {
    echo "╔════════════════════════════════════════╗"
    echo "║      🐳  Docker & Protocol Menu        ║"
    echo "╠════════════════════════════════════════╣"
    echo "║ 1️⃣  Check installation                  ║"
    echo "║ 2️⃣  Docker administration               ║"
    echo "║ 3️⃣  Running Scenario                    ║"
    echo "║ 4️⃣  Exit                                ║"
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

###############################
#
# WhireShark
#
###############################


wireshark_installedAndRunning() {
  echo "🔍 Checking Wireshark installation..."

  if [[ "$(uname -s)" == "Darwin" ]]; then
    # macOS
    if [ -d "/Applications/Wireshark.app" ]; then
      echo "✅ Wireshark is installed on macOS."

    else
      echo "❌ Wireshark is not installed in /Applications."
      echo "   Download it from https://www.wireshark.org/download.html"
      exit 1
    fi

  else
    # Linux
    if command -v wireshark >/dev/null 2>&1; then
      echo "✅ Wireshark is installed."
    else
      echo "❌ Wireshark is not installed."
      echo "   Try: sudo apt install wireshark"
      exit 1
    fi
  fi

}

###############################
#
# Pumba Check
#
###############################

pumba_check() {


    # 1. Ensure ./Applications exists
    if [ ! -d "$INSTALL_DIR" ]; then
      echo "📁 Creating directory: $INSTALL_DIR"
      mkdir -p "$INSTALL_DIR"
    fi

    # 2. Check if pumba is already installed there
    if [ -f "$PUMBA_BIN" ]; then
      echo "✅ Pumba is at: $PUMBA_BIN"
      "$PUMBA_BIN" --version
 
    else   
        # 3. Detect OS and architecture
        OS=$(uname -s)
        ARCH=$(uname -m)

        case "$OS" in
          Linux)    os_tag="linux" ;;
          Darwin)   os_tag="darwin" ;;
          *) echo "❌ Unsupported OS: $OS"; exit 1 ;;
        esac

        case "$ARCH" in
          x86_64)   arch_tag="amd64" ;;
          arm64|aarch64) arch_tag="arm64" ;;
          *) echo "❌ Unsupported architecture: $ARCH"; exit 1 ;;
        esac

        # 4. Download the right binary
        VERSION="0.11.6"
        FILENAME="pumba_${os_tag}_${arch_tag}"
        URL="https://github.com/alexei-led/pumba/releases/download/${VERSION}/${FILENAME}"

        echo "⬇️ Downloading Pumba from:"
        echo "   $URL"
        curl -L -o "$PUMBA_BIN" "$URL"

        # 5. Make it executable
        chmod +x "$PUMBA_BIN"

        # 6. Done
        echo "✅ Pumba installed at $PUMBA_BIN"
        "$PUMBA_BIN" --version
    fi
      
}
###############################
#
# Docker Menu
#
###############################

docker_menu() {

docker_installedAndRunning

    echo "----------------------------------------"
    echo "🐳 Docker Creation Options"
    echo "1) Build Docker TLS"
    echo "2) Build Docker VPN"
    echo "3) Back to main menu"
    echo "----------------------------------------"
    read -p "👉 Choose an option [1-3]: " docker_choice
    echo ""

      case $docker_choice in
        1)
            echo "✅ Selected Docker TLS ..."

            DOCKER_DIR="$DOCKER_DIR_TLS"
            DOCKER_IMAGE="$DOCKER_IMAGE_TLS"
            docker_install
            ;;
        2)
            echo "✅  Selected Docker VPN ..."
            DOCKER_DIR="$DOCKER_DIR_VPN"
            DOCKER_IMAGE="$DOCKER_IMAGE_VPN"
            docker_install
            ;;
        3)
            return
            ;;
        *)
            echo "❌ Invalid option. Returning to main menu."
            ;;
    esac
}

###############################
#
# Docker Creation
#
###############################

docker_install() {

    docker_installedAndRunning


    if [[ "$DOCKER_IMAGE" == *vpn* ]]; then
      MODE="VPN"
    else
      MODE="TLS"
    fi  
  
    echo "╔════════════════════════════════════════╗"
    echo "║ 🐳  Docker Build Options: $MODE Mode     ║"
    echo "╠════════════════════════════════════════╣"
    echo "║ 1️⃣  Build with cache                    ║"
    echo "║ 2️⃣  Build without cache                 ║"
    echo "║ 3️⃣  Verify installation                 ║"
    echo "║ 4️⃣  Back to previous menu               ║"
    echo "╚════════════════════════════════════════╝"

    read -p "👉 Choose an option [1-4]: " docker_choice
    echo ""

    # Verificar que el directorio y el Dockerfile existen
    if [[ ! -d "$DOCKER_DIR" ]]; then
        echo "❌ Error: Docker directory '$DOCKER_DIR' does not exist."
        return
    fi
    if [[ ! -f "$DOCKER_DIR/Dockerfile" ]]; then
        echo "❌ Error: No Dockerfile found in '$DOCKER_DIR'."
        return
    fi

    case $docker_choice in
        1)
            echo "🔧 Building Docker image with cache..."
            docker build -t "$DOCKER_IMAGE" "$DOCKER_DIR"
            ;;
        2)
            echo "♻️  Building Docker image without cache..."
            docker build --no-cache -t "$DOCKER_IMAGE" "$DOCKER_DIR"
            ;;
        3)  


          if [[ "$MODE" == "TLS" ]]; then
              echo "🔍 Verifying OpenSSL PQ installation and TLS handshake performance..."
              # Set defaults if not already set
              SIG_ALG=${SIG_ALG:-mldsa44}
              KEM_ALG=${KEM_ALG:-mlkem512}
              AUTH=${AUTH:-Single}
              NUM_RUNS=${NUM_RUNS:-1}
              TEST_TIME=${TEST_TIME:-1}

            
              # Crear red si no existe
              if ! docker network inspect localNet >/dev/null 2>&1; then
                  docker network create localNet>/dev/null 2>&1;
                  echo "✅ Red localNet created."
              else
                  echo "ℹ️  Red localNet already exists; it won’t be created."
              fi

              # Crear volumen si no existe
              if ! docker volume inspect cert >/dev/null 2>&1; then
                  docker volume create cert >/dev/null 2>&1;
                  echo "✅ Volumen cert created."
              else
                  echo "ℹ️  Volumen cert already exists; it won’t be created."
              fi

              echo "*************************************"

              echo "🔧 Using:"
              echo "   Signature Algorithm : $SIG_ALG"
              echo "   KEM Group           : $KEM_ALG"
              echo "   Auth Mode           : $AUTH"
              echo "   Runs                : $NUM_RUNS"
              echo



              docker run --rm -v cert:/cert -e CERT_PATH=/cert/ -e SIG_ALG=$SIG_ALG -it $DOCKER_IMAGE_TLS doCert.sh >/dev/null 2>&1;

               docker run --cap-add=NET_ADMIN  \
                      --name aux  \
                      -v cert:/cert   \
                      -e TC_DELAY=0ms  \
                      -e TC_LOSS=0% \
                      -e CERT_PATH=/cert/ \
                      -e KEM_ALG=$KEM  \
                      -e SIG_ALG=$SIG_ALG \
                      -e USE_TLS=true \
                      -e NUM_RUNS=1 \
                      -e MUTUAL=false \
                      -it $DOCKER_IMAGE_TLS perftestServerClientTlsQuic.sh > /tmp/test_output.log >&1

             
              echo "📈 Test Result (sample):"

              # Extrae solo la primera línea que contenga el resultado del handshake
              HANDSHAKE_LINE=$(grep "Handshake duration" /tmp/test_output.log | head -n 1)

              if [ -n "$HANDSHAKE_LINE" ]; then
                echo "$HANDSHAKE_LINE"
                echo
                echo "✅ Installation and test run completed successfully."
              else
                echo "⚠️  No connections result found."
                echo
                echo "❌ Installation verification failed. Check /tmp/test_output.log for details."
              fi

              docker rm -f aux &>/dev/null || true
                  sleep 1
              docker volume rm cert >/dev/null 2>&1 || true
              docker network rm localNet >/dev/null 2>&1|| true
              echo
          else

              OQS_DATA="uma-data-vpn"
              OQS_NETWORK="localNet"
              OQS_SERVER="umavpnserver"
              OQS_CLIENT="umavpnclient"

             
              # Crear red si no existe
              if ! docker network inspect $OQS_NETWORK >/dev/null 2>&1; then
                  docker network create $OQS_NETWORK >/dev/null 2>&1;
                  echo "✅ Red localNet created."
              else
                  echo "ℹ️  Red localNet already exists; it won’t be created."
              fi

              # Crear volumen si no existe
              if ! docker volume inspect $OQS_DATA >/dev/null 2>&1; then
                  docker volume create --name $OQS_DATA >/dev/null 2>&1;
                  echo "✅ Volumen cert created."
              else
                  echo "ℹ️  Volumen cert already exists; it won’t be created."
              fi


               docker run -e OQSSIGALG=$SIG_ALG \
                    -e SERVERFQDN=$OQS_SERVER \
                    -e CLIENTFQDN=$OQS_CLIENT \
                    -v $OQS_DATA:/config/openvpn \
                    --rm $DOCKER_IMAGE_VPN sh \
                    -c "cd /config/openvpn && createcerts_and_config.sh" >/dev/null 2>&1;


                docker run -e TLS_GROUPS=$KEM --rm \
                    --name $OQS_SERVER \
                    --net $OQS_NETWORK \
                    -v $OQS_DATA:/etc/openvpn \
                    -d \
                    --cap-add=NET_ADMIN \
                    --cap-add=MKNOD \
                    --device /dev/net/tun \
                    -e OQSSIGALG=$SIG_ALG \
                    -it $DOCKER_IMAGE_VPN \
                    serverstart.sh >/dev/null 2>&1;

               docker run -e TLS_GROUPS=$KEM --rm \
                    --name $OQS_CLIENT \
                    --net $OQS_NETWORK \
                    -v $OQS_DATA:/etc/openvpn \
                    --cap-add=NET_ADMIN \
                    --cap-add=MKNOD \
                    --device /dev/net/tun -d \
                    -it $DOCKER_IMAGE_VPN \
                    clientstart.sh                >/dev/null 2>&1;
              
                #docker logs $OQS_SERVER  >> "/tmp/test_VPN_output.log"

                RC=0
                    docker logs $OQS_SERVER | grep "Initialization Sequence Completed" >/dev/null 2>&1;
                    if [ $? -ne 0 ]; then
                       echo "Error initializing client."
                       RC=1
                    fi

                    if [ $RC -eq 0 ]; then
                       echo "✅ Test completed successfully"
                    else
                       echo "ℹ️ Test failed."
                    fi

                docker rm -f  $OQS_CLIENT &>/dev/null || true
                docker rm -f  $OQS_SERVER &>/dev/null || true

                sleep 1
                
                docker volume rm $OQS_DATA &>/dev/null || true
                docker network rm $OQS_NETWORK &>/dev/null || true
                 echo
          fi    
             ;;     
        4)
            return
            ;;
        *)
            echo "❌ Invalid option. Returning to main menu."
            ;;
     esac
}


list_scenarios() {
  SCENARIO_DIR="./Scenarios"

  echo
  echo "📂 Available Scenarios:"
  echo "──────────────────────────────"

  if [ ! -d "$SCENARIO_DIR" ]; then
    echo "❌ Scenario directory not found: $SCENARIO_DIR"
    return 1
  fi

  local scenarios=()
  local count=0

  for dir in "$SCENARIO_DIR"/*/; do
    [ -d "$dir" ] || continue
    dirname=$(basename "$dir")
    display_name="${dirname#*-}"  # Elimina el prefijo numérico
    scenarios+=("$dirname")       # Guardamos el nombre real
    echo " $((count + 1))) $display_name"
    count=$((count + 1))
  done

  if [ "$count" -eq 0 ]; then
    echo "⚠️  No scenario folders found in $SCENARIO_DIR"
    return 1
  fi

  # Mostrar opción de volver al menú
  back_option=$((count + 1))
  echo " $back_option) Back to main menu"
  echo

  while true; do
    read -p "👉 Enter the number of the scenario to run [1-$back_option]: " choice

    if [[ "$choice" =~ ^[0-9]+$ ]]; then
      if [ "$choice" -ge 1 ] && [ "$choice" -le "$count" ]; then
        selected_scenario="${scenarios[$((choice - 1))]}"
        echo "✅ You selected: $selected_scenario"
        SCENARIO_PATH="$SCENARIO_DIR/$selected_scenario"

        echo
        echo "⚠️  WARNING: All previous logs in this scenario may be overwritten."
        echo "   Please make a backup before continuing."
        read -p "❓ Are you sure you want to continue? (y/n): " confirm

        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
          echo "❌ Operation cancelled."
          return 1
        fi

        # Ejecutar LauncherAll.sh
        if [ -x "$SCENARIO_PATH/LauncherAll.sh" ]; then
          echo "🚀 Executing LauncherAll.sh in $SCENARIO_PATH"
          (cd "$SCENARIO_PATH" && ./LauncherAll.sh)
          return 0
        else
          echo "❌ LauncherAll.sh not found or not executable in $SCENARIO_PATH"
          return 1
        fi
      elif [ "$choice" -eq "$back_option" ]; then
        echo "↩️  Returning to main menu."
        return 0
      fi
    fi

    echo "❌ Invalid selection. Please enter a number between 1 and $back_option."
  done
}




###############################
#
# Check System
#
###############################

check_system() {
    echo " Verifying test ..."
    
    echo " 1. Docker Installed and running ..."
    docker_installedAndRunning
    echo " 2. Pumba Checking ..."
    pumba_check
    echo " 2. Wireshark Checking ..."
    wireshark_installedAndRunning
    echo
    read -p "🔁 Press Enter to return to the main menu..."

    return   
}


scenarios() {
    echo "🚀 Running TLS handshake test..."
    list_scenarios
}



analyze_results() {
    echo "📊 Analyzing results..."
    # ToDo
}

view_logs() {
    echo "📜 Viewing logs..."
    # ToDo
}

# =====================
# Main Menu Loop
# =====================

while true; do
    show_menu
    echo ""
    read -p "👉 Please enter your choice [1-4]: " choice
    echo ""
    case $choice in
        1) check_system ;;
        2) docker_menu  ;;
        3) scenarios ;;
        4) echo "👋 Goodbye!" ; exit 0 ;;
        *) echo "❌ Invalid option. Please try again." ;;
    esac
    echo ""
done
