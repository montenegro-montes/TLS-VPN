#!/bin/bash

set -euo pipefail

###############################################################################
#  COMMAND LINE PARAMETERS
#
#  Usage: ./Launcher.sh  [capture|captureKey|nocapture] numRuns [none|simple|stable|unstable] [loss-percent] [delay-ms]
###############################################################################

CAPTURE_MODE=${1:-nocapture}
NUM_RUNS=${2:-10}
NETWORK_PROFILE=${3:-none}
LOSS_PERC=${4:-0}
DELAY_MS=${5:-0}

USAGE="Usage: $0 [capture|captureKey|nocapture] [none|simple|stable|unstable] [loss-percent] [delay-ms]"

os=""
###############################################################################
#  Input Validation
###############################################################################

# 1) Packet capture mode
if [[ "$CAPTURE_MODE" != "capture" && "$CAPTURE_MODE" != "captureKey" && "$CAPTURE_MODE" != "nocapture" ]]; then
    echo "Invalid capture mode: must be 'capture', 'captureKey', or 'nocapture'."
    echo "$USAGE"
    exit 1
fi

# 2) Network profile
if [[ "$NETWORK_PROFILE" != "none" && "$NETWORK_PROFILE" != "simple" && "$NETWORK_PROFILE" != "stable" && "$NETWORK_PROFILE" != "unstable" ]]; then
    echo "Invalid network profile: must be 'none', 'simple', 'stable', or 'unstable'."
    echo "$USAGE"
    exit 1
fi

# 3) Packet loss percentage (0–100)
if ! [[ "$LOSS_PERC" =~ ^[0-9]+$ ]] || (( LOSS_PERC < 0 || LOSS_PERC > 100 )); then
    echo "Invalid loss-percent: must be an integer between 0 and 100."
    echo "$USAGE"
    exit 1
fi

# 4) Delay in milliseconds (>= 0)
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


 OQS_DATA="uma-data-vpn"
 OQS_NETWORK="localNet"
 OQS_SERVER="umavpnserver"
 OQS_CLIENT="umavpnclient"
 OQS_OPENVPN_DOCKERIMAGE="uma-vpn-pq-34"
 RC=0

 

  SIG_L1=("mldsa44")
  SIG_L3=("mldsa65")
  SIG_L5=("mldsa87")
  
  KEMS_L1=(x25519  mlkem512  hqc128)
  KEMS_L3=(x448  mlkem768  hqc192)
  KEMS_L5=(P-521  mlkem1024  hqc256)

  



echo "*************************************"
echo "Parameters valid. Starting with:"
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
             # Wait for the user to save or inspect captures before proceeding
             read -n 1 -s -r -p "Please save Wireshark data to run another experiment..."
             echo ""
             echo "Running now ... "
             wireshark &
        else
            echo "Wireshark is NOT running. Starting now..."
            # Launch Wireshark in the background
            wireshark &
            # Give it a moment to start
            sleep 1
        fi

    else
        echo "Wireshark is not installed. Please install it (e.g. Ubuntu/Debian: sudo apt install wireshark) and try again."
        exit 1
    fi 
    
    read -n 1 -s -r -p "Configure Wireshark and press any key when you are ready to continue..."
    echo ""

  
}
###############################################################################
#  Function: cleaning
#    
###############################################################################

cleaning(){
    docker kill $OQS_SERVER &>/dev/null || true
    docker kill $OQS_CLIENT &>/dev/null || true

    sleep 1
    docker container prune -f
    docker volume rm $OQS_DATA || true
    docker network rm $OQS_NETWORK || true
    sleep 1
}

detect_platform

cleaning

echo ""
echo "*************************************"
echo "***NETWORK AND VOLUMEN **************"
echo "*************************************"

# Crear red si no existe
if ! docker network inspect $OQS_NETWORK >/dev/null 2>&1; then
    docker network create $OQS_NETWORK
    echo "✅ Red localNet created."
else
    echo "ℹ️  Red localNet already exists; it won’t be created."
fi

# Crear volumen si no existe
if ! docker volume inspect $OQS_DATA >/dev/null 2>&1; then
    docker volume create --name $OQS_DATA
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



        echo ""
        echo " ==> Creating Certs and Keys"
        docker run -e OQSSIGALG=$SIG_ALG \
                    -e SERVERFQDN=$OQS_SERVER \
                    -e CLIENTFQDN=$OQS_CLIENT \
                    -v $OQS_DATA:/config/openvpn \
                    --rm $OQS_OPENVPN_DOCKERIMAGE sh \
                    -c "cd /config/openvpn && createcerts_and_config.sh"


        
        for KEM in "${KEMS[@]}"; do


            echo ""
            echo "    Executing docker Server..."

            docker rm -f $OQS_SERVER $OQS_CLIENT 2>/dev/null

            
            if [[ "$CAPTURE_MODE" == "captureKey" ]]; then
                SSL_DIR="./sslkeys"
                mkdir -p "$SSL_DIR"
                SSLKEY_NAME="sslkeys_serverVPN_${SIG_ALG}_${KEM}.log"
                SSLKEY_PATH="/sslkeys/$SSLKEY_NAME"

                docker run -e TLS_GROUPS=$KEM --rm \
                    --name $OQS_SERVER \
                    --net $OQS_NETWORK \
                    -v $OQS_DATA:/etc/openvpn \
                    -v "$SSL_DIR":/sslkeys \
                    -d \
                    --cap-add=NET_ADMIN \
                    --cap-add=MKNOD \
                    --device /dev/net/tun \
                    -e OQSSIGALG=$SIG_ALG \
                    -e SSLKEYLOGFILE=$SSLKEY_PATH \
                    -e LD_PRELOAD=/ldkeylog.so \
                    $OQS_OPENVPN_DOCKERIMAGE \
                    serverstart.sh 

            else
                docker run -e TLS_GROUPS=$KEM --rm \
                    --name $OQS_SERVER \
                    --net $OQS_NETWORK \
                    -v $OQS_DATA:/etc/openvpn \
                    -d \
                    --cap-add=NET_ADMIN \
                    --cap-add=MKNOD \
                    --device /dev/net/tun \
                    -e OQSSIGALG=$SIG_ALG \
                    $OQS_OPENVPN_DOCKERIMAGE \
                    serverstart.sh 
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
                    loss --percent "$LOSS_PERC" "$OQS_SERVER" & PUMBA_PIDS_SERVER+=($!)
                }
                [[ "$DELAY_MS" != "0" ]] && {
                  echo "   ↳ Applying fixed delay: ${DELAY_MS} ms"
                  ./pumba netem --duration 1h --interface $NETIF \
                    delay --time "$DELAY_MS" --jitter 0 "$OQS_SERVER" & PUMBA_PIDS_SERVER+=($!)
                }
                ;;
              stable|unstable)
                args=("${STABLE_GEMODEL[@]}")
                [[ "$NETWORK_PROFILE" == "unstable" ]] && args=("${UNSTABLE_GEMODEL[@]}")
                echo "   ↳ Applying ${PROFILE} network profile (loss-gemodel pg${args[0]} pb${args[1]} h${args[2]} k${args[3]})"
                ./pumba netem --duration 1h --interface $NETIF \
                  loss-gemodel --pg "${args[0]}" --pb "${args[1]}" \
                  --one-h "${args[2]}" --one-k "${args[3]}" "$OQS_SERVER" & PUMBA_PIDS_SERVER+=($!)
                ;;
            esac
           

            sleep 2

            if [[ "$CAPTURE_MODE" == "capture" || "$CAPTURE_MODE" == "captureKey" ]]; then
                    echo ""
                    echo "Launching Wireshark"

                    if [[ "$os" == "Darwin" ]]; then
                        lauch_Wireshark_mac
                    else
                        launch_wireshark_linux
                    fi    
            fi   


        
                for (( i=1; i<=NUM_RUNS; i++ )); do
                      
                   
                   
                    echo ""
                    echo "****************"
                    echo "  -> [$i/$NUM_RUNS] $SIG_ALG-$KEM"
                    

                    sleep 3    

                    echo "    Buscando IP.. "
                    IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $OQS_SERVER)
                    echo "    IP..  $IP"

                   
                    echo "    Executing docker Client... $IP"

                    docker run -e TLS_GROUPS=$KEM --rm \
                    --name $OQS_CLIENT \
                    --net $OQS_NETWORK \
                    -v $OQS_DATA:/etc/openvpn \
                    --cap-add=NET_ADMIN \
                    --cap-add=MKNOD \
                    --device /dev/net/tun -d \
                    $OQS_OPENVPN_DOCKERIMAGE \
                    clientstart.sh

                    echo "     Docker $OQS_CLIENT executed ... "
                    #sleep 2    

                    # Allow time to start up
                    sleep 3
                    echo "Startup completed, checking initialization worked OK"
                    # Check that initialization went OK for both server and client:

                    #docker logs $OQS_SERVER | grep "Peer Connection Initiated"
                    docker logs $OQS_SERVER | grep "Initialization Sequence Completed"
                    if [ $? -ne 0 ]; then
                       echo "Error initializing server."
                       RC=1
                    fi
                    #docker logs $OQS_CLIENT | grep "Peer Connection Initiated"
                    docker logs $OQS_CLIENT | grep "Initialization Sequence Completed"
                    if [ $? -ne 0 ]; then
                       echo "Error initializing client."
                       RC=1
                    fi

                    if [ $RC -eq 0 ]; then
                       echo " ✅ Test completed successfully"
                    else
                       echo " ℹ️ Test failed."
                    fi
                    

                    ############################################################################
                    #  NETWORK IMPAIRMENTS (Pumba)
                    ############################################################################
                    PUMBA_PIDS_CLIENT=()
                    case "$NETWORK_PROFILE" in
                      simple)
                        [[ "$DELAY_MS" != "0" ]] && {
                          echo "   ↳ Applying fixed delay: ${DELAY_MS} ms"
                          ./pumba netem --duration 1h --interface $NETIF \
                            delay --time "$DELAY_MS" --jitter 0 "$OQS_CLIENT" & PUMBA_PIDS_CLIENT+=($!)
                        }
                        ;;
                    esac
                    #sleep 3

                    #echo ""
                    #echo "**************************"
                    #echo "     Executing test  ... "


                    #echo "     Waiting  ... "
                    #sleep 3


                    #docker logs $OQS_SERVER  >> "server.logs"
                    #docker logs $OQS_CLIENT  >> "client.logs"

                    sleep 1
                    docker kill $OQS_CLIENT &>/dev/null || true

                 done
   
         echo "   Shutting down server and impairments..."
        
         docker kill $OQS_SERVER &>/dev/null || true
         #for pid in "${PUMBA_PIDS[@]}"; do kill -9 "$pid" &>/dev/null || true; done
    done

  done
done

sleep 3

cleaning
echo "✅  Cleanup complete. Tests finished."


