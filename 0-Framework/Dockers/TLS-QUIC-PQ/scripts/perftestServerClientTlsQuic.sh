#!/bin/sh

# ---------------------------
# Set network DELAY and LOSS
# ---------------------------
set -e

#if [ "x$TC_DELAY" == "x" ]; then
if [ -z "$TC_DELAY" ]; then
    TC_DELAY=0ms
fi    

#if [ "x$TC_LOSS" == "x" ]; then
if [ -z "$TC_LOSS" ]; then
    TC_LOSS="0%"
fi 

if [ -z "$DOCKER_HOST" ]; then
    DOCKER_HOST="localhost"
fi 

if [ -z "$USE_TLS" ]; then
    USE_TLS="true"
fi 

if [ -z "$NUM_RUNS" ]; then
    NUM_RUNS=500
fi 


echo "tc"
tc qdisc add dev lo root netem delay $TC_DELAY loss $TC_LOSS

echo "Showing qdisc status for the interface: lo"
tc -s qdisc show dev lo


# ---------------------------
# Set KEM and Signature algorithm
# ---------------------------
# Optionally set KEM to one defined in https://github.com/open-quantum-safe/oqs-provider#algorithms
#if [ "x$KEM_ALG" == "x" ]; then
if [ -z "$KEM_ALG" ]; then
    KEM_ALG=mlkem512
fi
export DEFAULT_GROUPS=$KEM_ALG

# Optionally set SIG to one defined in https://github.com/open-quantum-safe/oqs-provider#algorithms
#if [ "x$SIG_ALG" == "x" ]; then
if [ -z "$SIG_ALG" ]; then
	export SIG_ALG=mldsa44
fi

# Optionally set TEST_TIME
#if [ "x$TEST_TIME" == "x" ]; then
if [ -z "$TEST_TIME" ]; then
	export TEST_TIME=1
fi

# ---------------------------
# Create certificates 
# ---------------------------
# Optionally set server certificate alg to one defined in https://github.com/open-quantum-safe/oqs-provider#algorithms
# The root CA's signature alg remains as set when building the image
#CERT_PATH=/opt/certs

echo "Running $0 with SIG_ALG=$SIG_ALG and KEM_ALG=$KEM_ALG"

#ToDO - Not CERT

# -------------------------------------
# Launch TLS OR QUIC server and Clients
# -------------------------------------
# Start a TLS1.3 test server based on OpenSSL accepting only the specified KEM_ALG
# The env var DEFAULT_GROUPS activates the required Group via the system openssl.cnf:
# we put it on the command line to check for possible typos otherwise silently discarded:

if [ "$USE_TLS" = "true" ]; then
     echo "Ejecutando TLS"
     openssl s_server -cert $CERT_PATH/server.crt -key $CERT_PATH/server.key -groups $DEFAULT_GROUPS -www -tls1_3 -accept :4433&
else 
     echo "Ejecutando QUIC"
     quics_server -groups:$DEFAULT_GROUPS -cert_file:$CERT_PATH/server.crt -key_file:$CERT_PATH/server.key&
fi

# Give server time to come up first:
sleep 1

NUM_RUNS=$NUM_RUNS


        i=1
        while [ $i -le $NUM_RUNS ]
        do
         if [ "$USE_TLS" = "true" ]; then
              echo "Execution $i - TLS "
              openssl s_connection -connect $DOCKER_HOST:4433 -new -verify 1 -CAfile $CERT_PATH/CA.crt
              #openssl s_time -connect  $DOCKER_HOST:4433 -new -time $TEST_TIME -verify 1 -CAfile $CERT_PATH/CA.crt  | grep connections
          else

              echo "Execution $i - QUIC "
              #quics_time -target:$DOCKER_HOST -time:$TEST_TIME  -groups:$KEM_ALG -CAfile:$CERT_PATH/CA.crt
              quics_connection -groups:$KEM_ALG -target:$DOCKER_HOST -CAfile:$CERT_PATH/CA.crt

          fi 
            
          i=$((i + 1))

        done

