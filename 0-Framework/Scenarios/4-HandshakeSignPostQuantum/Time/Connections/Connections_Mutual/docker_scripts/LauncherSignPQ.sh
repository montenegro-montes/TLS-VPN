#!/bin/bash

#!/usr/bin/env bash
set -euo pipefail

###############################################################################
#  COMMAND LINE PARAMETERS
#
#  Usage: ./Launcher.sh [tls|quic] [mutual|single] [capture|captureKey|nocapture] [numExecutions] [none|simple|stable|unstable] [loss-percent] [delay-ms]
###############################################################################

PROTOCOL=${1:-tls}
AUTH_MODE=${2:-single}
CAPTURE_MODE=${3:-nocapture}
NUM_RUNS=${4:-100}
NETWORK_PROFILE=${5:-none}
LOSS_PERC=${6:-0}
DELAY_MS=${7:-0}

USAGE="Usage: $0 [tls|quic] [mutual|single] [capture|captureKey|nocapture] [numExecutions] [none|simple|stable|unstable] [loss-percent] [delay-ms]"

MUTUAL_AUTHENTICATION=false
os=""
###############################################################################
#  Input Validation
###############################################################################

# 1) Protocol
if [[ "$PROTOCOL" != "tls" && "$PROTOCOL" != "quic" ]]; then
    echo "$USAGE"
    exit 1
fi

# 2) Mutual authentication mode
if [[ "$AUTH_MODE" != "mutual" && "$AUTH_MODE" != "single" ]]; then
    echo "Invalid authentication mode: must be 'mutual' or 'single'."
    echo "$USAGE"
    exit 1
fi

# 3) Packet capture mode
if [[ "$CAPTURE_MODE" != "capture" && "$CAPTURE_MODE" != "captureKey" && "$CAPTURE_MODE" != "nocapture" ]]; then
    echo "Invalid capture mode: must be 'capture', 'captureKey', or 'nocapture'."
    echo "$USAGE"
    exit 1
fi

# 4) Network profile
if [[ "$NETWORK_PROFILE" != "none" && "$NETWORK_PROFILE" != "simple" && "$NETWORK_PROFILE" != "stable" && "$NETWORK_PROFILE" != "unstable" ]]; then
    echo "Invalid network profile: must be 'none', 'simple', 'stable', or 'unstable'."
    echo "$USAGE"
    exit 1
fi

# 5) Packet loss percentage (0–100)
if ! [[ "$LOSS_PERC" =~ ^[0-9]+$ ]] || (( LOSS_PERC < 0 || LOSS_PERC > 100 )); then
    echo "Invalid loss-percent: must be an integer between 0 and 100."
    echo "$USAGE"
    exit 1
fi

# 6) Delay in milliseconds (>= 0)
if ! [[ "$DELAY_MS" =~ ^[0-9]+$ ]] || (( DELAY_MS < 0 )); then
    echo "Invalid delay-ms: must be a non-negative integer."
    echo "$USAGE"
    exit 1
fi



###############################################################################
#  CONFIGURATION
###############################################################################


if [[ "$CAPTURE_MODE" == "captureKey" ]]; then
  NUM_RUNS=1
fi

if [[ "$AUTH_MODE" == "mutual" ]]; then
   MUTUAL_AUTHENTICATION=true  
fi

 IMAGE_NAME="uma-tls_quic-pq-34" 
 SERVER="servidor"
 CLIENT="cliente"
 #SUPPORTED_SIG_ALGS=(ed25519)
 # KEMS_L1=(x25519)



  SIG_L1=("mldsa44" )
  SIG_L3=("mldsa65")
  SIG_L5=("mldsa87")
  KEMS_L1=(x25519 x25519_mlkem512 mlkem512 x25519_hqc128 hqc128)
  KEMS_L3=(x448 x448_mlkem768 mlkem768 x448_hqc192 hqc192)
  KEMS_L5=(P-521 p521_mlkem1024 mlkem1024 p521_hqc256 hqc256)

# Recoger el parámetro de línea de comandos
 USE_TLS=$([[ "$PROTOCOL" == "tls" ]] && echo true || echo false)
 



echo "*************************************"
echo "Parameters valid. Starting with:"
echo "  Protocol:        $PROTOCOL"
echo "  Auth Mode:       $AUTH_MODE"
echo "  Capture Mode:    $CAPTURE_MODE"
echo "  Network Profile: $NETWORK_PROFILE"
echo "  Loss %:          $LOSS_PERC"
echo "  Delay (ms):      $DELAY_MS"
echo "  Executions:      $NUM_RUNS"

echo "  Signature L1:    ${SIG_L1[*]}   "
echo "  KEMS Level 1:    ${KEMS_L1[*]}"
echo "  Signature L3:    ${SIG_L3[*]}   "
echo "  KEMS Level 3:    ${KEMS_L3[*]}"
echo "  Signature L5:    ${SIG_L5[*]}   "
echo "  KEMS Level 5:    ${KEMS_L5[*]}"
echo "*************************************"

###############################################################################
#  Function: detect_platform
#    
###############################################################################

detect_platform() {
    os="$(uname -s)"
    case "$os" in
        Linux)
            echo "Runnig on Linux" ;;
        Darwin)
            echo "Runnig on macOS" ;;
        *)
            echo "Runnig on: $os" ;;
    esac
}

###############################################################################
#  Function: launch_edgeshark
#    
###############################################################################
launch_edgeshark() {
    # 1) Variables
    URL="https://github.com/siemens/edgeshark/raw/main/deployments/wget/docker-compose-localhost.yaml"
    COMPOSE_FILE="./docker-compose-localhost.yaml"  # ruta fija

    # 2) Descargar (si ha cambiado) el fichero de Compose
    mkdir -p "$(dirname "$COMPOSE_FILE")"
    wget -q --no-cache -O "$COMPOSE_FILE" "$URL"

    # 3) Comprobar si hay contenedores levantados
    #    --quiet -q return  IDs; if it is empty, there is no runnig container
    if [ -z "$(docker compose -f "$COMPOSE_FILE" ps -q)" ]; then
        echo "$(date '+%F %T') → No active containers. Running stack..." 
        docker compose -f "$COMPOSE_FILE" up -d 
    else
        echo "$(date '+%F %T') → It is runnig. Nothing to do." 
    fi
}
###############################################################################
#  Function: lauch_Wireshark
#    
###############################################################################

lauch_Wireshark_mac(){

     if [ -d "/Applications/Wireshark.app" ]; then
                    echo "Wireshark is installed, perfect!!!"

                    if ps aux | grep -i wireshark | grep -v grep > /dev/null; then         
                        echo "Wireshark is running."
                        # Espera a que el usuario esté listo
                        read -n 1 -s -r -p "Please save Wireshark data to run another experiment..."
                        echo ""
                        echo "Running now ... "
                        open -a Wireshark

                    else
                        echo "Wireshark is NOT running. Running now ... "
                        open -a Wireshark
                    fi 
            else
                echo "Wireshark is not installed in /Applications."
                exit 1
            fi

            # Espera a que el usuario esté listo
            read -n 1 -s -r -p "Configure Wireshark and press any key when you are ready to continue..."
            echo ""
}

###############################################################################
#  Function: lauch_Wireshark
#    
###############################################################################

launch_wireshark_linux() {
    # Check if the 'wireshark' command is available
    if command -v wireshark >/dev/null 2>&1; then
        echo "Wireshark is installed, perfect!!!"

        # Check if Wireshark is already running (as the current user)
        if pgrep -u "$USER" -x wireshark >/dev/null 2>&1; then
            echo "Wireshark is already running."
        else
            echo "Wireshark is NOT running. Starting now..."
            # Launch Wireshark in the background
            wireshark 
            # Give it a moment to start
            sleep 1
        fi

        # Wait for the user to save or inspect captures before proceeding
        read -n 1 -s -r -p "Please save Wireshark data to run another experiment, then press any key to continue..."
        echo ""
        read -n 1 -s -r -p "Configure Wireshark and press any key when you are ready to continue..."
        echo ""

    else
        echo "Wireshark is not installed. Please install it (e.g. Ubuntu/Debian: sudo apt install wireshark) and try again."
        exit 1
    fi
}
###############################################################################
#  Function: cleaning
#    
###############################################################################

cleaning(){
    docker kill $SERVER &>/dev/null || true
    docker kill $CLIENT &>/dev/null || true

    sleep 1
    docker container prune -f
    docker volume rm cert || true
    docker network rm localNet || true
    sleep 1
}

detect_platform

cleaning

echo ""
echo "*************************************"
echo "***NETWORK AND VOLUMEN **************"
echo "*************************************"

# Crear red si no existe
if ! docker network inspect localNet >/dev/null 2>&1; then
    docker network create localNet
    echo "✅ Red localNet created."
else
    echo "ℹ️  Red localNet already exists; it won’t be created."
fi

# Crear volumen si no existe
if ! docker volume inspect cert >/dev/null 2>&1; then
    docker volume create cert
    echo "✅ Volumen cert created."
else
    echo "ℹ️  Volumen cert already exists; it won’t be created."
fi

echo "*************************************"



if [[ "$CAPTURE_MODE" == "capture" || "$CAPTURE_MODE" == "captureKey" ]]; then
    echo ""
    echo "Launching edgeshark"
    launch_edgeshark
 fi   

for LEVEL in L1 L3 L5; do

    # Use indirect variable reference
    SIG_VAR="SIG_$LEVEL"
    KEM_VAR="KEMS_$LEVEL"

    eval "SIGS=(\"\${${SIG_VAR}[@]}\")"
    eval "KEMS=(\"\${${KEM_VAR}[@]}\")"

    LOG_FILE="${LEVEL}.log"


    for SIG_ALG in "${SIGS[@]}"; do
        echo "📄 Starting tests for $LEVEL (SIG: $SIG_ALG)"

        echo " ==> Creating Certs and Keys"
        docker run --rm -v cert:/cert -e CERT_PATH=/cert/ -e SIG_ALG=$SIG_ALG -it $IMAGE_NAME doCert.sh

        
        for KEM in "${KEMS[@]}"; do
            echo ""
            echo "****************"
            echo "  -> KEM: $KEM"


            
                echo ""
                echo "    Executing docker Server..."

                docker rm -f $SERVER $CLIENT 2>/dev/null

                if [[ "$CAPTURE_MODE" == "captureKey" ]]; then    
                    SSL_DIR="$HOME/captures/sslkeys"
                    mkdir -p "$SSL_DIR"
                    SSLKEY_NAME="sslkeys_server_${SIG_ALG}_${KEM}.log"
                    SSLKEY_PATH="/sslkeys"

                    docker run --cap-add=NET_ADMIN  \
                      --name $SERVER  \
                      --network localNet  \
                      -v cert:/cert   \
                      -v "$SSL_DIR":/sslkeys \
                      -e TC_DELAY=0ms  \
                      -e TC_LOSS=0% \
                      -e CERT_PATH=/cert/ \
                      -e KEM_ALG=$KEM  \
                      -e SIG_ALG=$SIG_ALG \
                      -e USE_TLS=$USE_TLS \
                      -e SSLKEYLOGFILE=$SSLKEY_PATH \
                      -e MUTUAL=$MUTUAL_AUTHENTICATION \
                      -d $IMAGE_NAME perftestServerTlsQuic.sh 
                else
                     docker run --cap-add=NET_ADMIN  \
                      --name $SERVER  \
                      --network localNet  \
                      -v cert:/cert   \
                      -e TC_DELAY=0ms  \
                      -e TC_LOSS=0% \
                      -e CERT_PATH=/cert/ \
                      -e KEM_ALG=$KEM  \
                      -e SIG_ALG=$SIG_ALG \
                      -e USE_TLS=$USE_TLS \
                      -e MUTUAL=$MUTUAL_AUTHENTICATION \
                      -d $IMAGE_NAME perftestServerTlsQuic.sh 
                fi 

                sleep 3    

                echo "    Buscando IP.. "
                IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' servidor)
                echo "    IP..  $IP"

                
                if [[ "$CAPTURE_MODE" == "capture" || "$CAPTURE_MODE" == "captureKey" ]]; then
                    echo ""
                    echo "Launching Wireshark"

                    if [[ "$os" == "Darwin" ]]; then
                        lauch_Wireshark_mac
                    else
                        launch_wireshark_linux
                    fi    
                fi   


                ############################################################################
                #  NETWORK IMPAIRMENTS (Pumba)
                ############################################################################
                PUMBA_PIDS_SERVER=()
                case "$NETWORK_PROFILE" in
                  simple)
                    [[ "$LOSS_PERC" != "0" ]] && {
                      echo "   ↳ Applying static loss: ${LOSS_PERC}%"
                      ./pumba netem --duration 1h --interface $NETIF \
                        loss --percent "$LOSS_PERC" "$SERVER" & PUMBA_PIDS_SERVER+=($!)
                    }
                    [[ "$DELAY_MS" != "0" ]] && {
                      echo "   ↳ Applying fixed delay: ${DELAY_MS} ms"
                      ./pumba netem --duration 1h --interface $NETIF \
                        delay --time "$DELAY_MS" --jitter 0 "$SERVER" & PUMBA_PIDS_SERVER+=($!)
                    }
                    ;;
                  stable|unstable)
                    args=("${STABLE_GEMODEL[@]}")
                    [[ "$NETWORK_PROFILE" == "unstable" ]] && args=("${UNSTABLE_GEMODEL[@]}")
                    echo "   ↳ Applying ${PROFILE} network profile (loss-gemodel pg${args[0]} pb${args[1]} h${args[2]} k${args[3]})"
                    ./pumba netem --duration 1h --interface $NETIF \
                      loss-gemodel --pg "${args[0]}" --pb "${args[1]}" \
                      --one-h "${args[2]}" --one-k "${args[3]}" "$SERVER" & PUMBA_PIDS_SERVER+=($!)
                    ;;
                esac
               

                sleep 2
                echo "    Executing docker Client... $IP"

                SSL_DIR="$HOME/captures/sslkeys"
                mkdir -p "$SSL_DIR"

                SSLKEY_NAME="sslkeys_${SIG_ALG}_${KEM}.log"
                SSLKEY_PATH="/sslkeys/$SSLKEY_NAME"  # Esta ruta es dentro del contenedor


                docker create --cap-add=NET_ADMIN \
                    --network localNet \
                    --name $CLIENT  \
                    -v cert:/cert \
                    -v "$SSL_DIR":/sslkeys \
                    -e DOCKER_HOST=$IP \
                    -e TC_DELAY=0ms  \
                    -e TC_LOSS=0% \
                    -e CERT_PATH=/cert/ \
                    -e KEM_ALG=$KEM \
                    -e SIG_ALG=$SIG_ALG \
                    -e USE_TLS=$USE_TLS \
                    -e NUM_RUNS=$NUM_RUNS \
                    -e MUTUAL=$MUTUAL_AUTHENTICATION \
                    -e SSLKEYLOGFILE="$SSLKEY_PATH" \
                    $IMAGE_NAME sleep infinity

                

                docker start $CLIENT

                echo "     Docker $CLIENT executed ... "
                #sleep 2    

                ############################################################################
                #  NETWORK IMPAIRMENTS (Pumba)
                ############################################################################
                PUMBA_PIDS_CLIENT=()
                case "$NETWORK_PROFILE" in
                  simple)
                    [[ "$DELAY_MS" != "0" ]] && {
                      echo "   ↳ Applying fixed delay: ${DELAY_MS} ms"
                      ./pumba netem --duration 1h --interface $NETIF \
                        delay --time "$DELAY_MS" --jitter 0 "$CLIENT" & PUMBA_PIDS_CLIENT+=($!)
                    }
                    ;;
                esac
                #sleep 3

                echo ""
                echo "**************************"
                echo "     Executing test  ... "

                docker exec -it "$CLIENT" ./perftestClientTlsQuic.sh 2>&1 | tee -a "$LOG_FILE"


                echo "     Waiting  ... "
                sleep 3


             echo "   Shutting down server and impairments..."
            
             docker kill $SERVER &>/dev/null || true
             docker kill $CLIENT &>/dev/null || true
             #for pid in "${PUMBA_PIDS[@]}"; do kill -9 "$pid" &>/dev/null || true; done
        done
      done  

done

sleep 3

cleaning
echo "✅  Cleanup complete. Tests finished."


