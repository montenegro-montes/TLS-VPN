#!/bin/bash

set -e

# Comprobar argumento de tag
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <tag>"
  echo "Example: $0 arm"
  exit 1
fi

TAG="$1"

# Firmas a procesar
SIGNATURES=("ed25519" "secp384r1" "secp521r1")

for SIG_ALG in "${SIGNATURES[@]}"; do

    if ! ls ${SIG_ALG}-*.pcapng > /dev/null 2>&1; then
        echo "⚠️  No pcapng files found for $SIG_ALG — skipping..."
        continue
    fi

    echo "🔍 Searching for .pcapng files for $SIG_ALG..."
    for pcap in ${SIG_ALG}-*.pcapng; do
        echo "🧪 Processing $pcap..."
        python3 analiza_pcap_vpn.py "$pcap"
    done

    echo "📊 Merging CSVs for $SIG_ALG..."
    python3 merge_csv.py "$SIG_ALG" "$TAG"
    python3 merge_csv.py "$SIG_ALG" "$TAG" --vpn

    echo "✅ Done for $SIG_ALG on $TAG"
    echo "-----------------------------------------------"

done

# Crear directorio output y mover resultados
mkdir -p output
mv *_tls_${TAG}.csv output/
mv *_vpn_${TAG}.csv output/

rm *.csv

echo "📁 CSV files moved to ./output/"
echo "🎉 All done!"
