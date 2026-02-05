#!/bin/bash

set -euo pipefail

SCRIPTS_DIR="./scripts"
OUTPUT_DIR="./output"
PLATFORMS=("x86" "arm")
SIG_ALGS=("ed25519" "secp384r1" "secp521r1")
ANALYZE_SCRIPT="analyze_levels_Platforms.py"

# 🔄 Limpieza inicial
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# 📦 Función para procesar una plataforma
process_platform() {
    local PLATFORM="$1"
    local PLATFORM_DIR="./platforms/$PLATFORM"

    echo "🚀 Processing platform: $PLATFORM"

    if [[ ! -d "$PLATFORM_DIR" ]]; then
        echo "❌ Directory not found: $PLATFORM_DIR"
        exit 1
    fi

    # Copiar scripts necesarios
    cp "$SCRIPTS_DIR"/* "$PLATFORM_DIR/"

    # Ejecutar análisis
    pushd "$PLATFORM_DIR" > /dev/null
    ./runAll.sh "$PLATFORM"

    # Limpiar scripts temporales
    rm -f ./*.py ./*.sh

    # Mover resultados al directorio raíz
    if [[ "$PLATFORM" == "x86" ]]; then
        mv output "$OLDPWD"
    else
        mv output/* "$OLDPWD/output/"
        rm -rf output
    fi

    popd > /dev/null
    echo "✅ $PLATFORM completed!"
    echo "----------------------------------------"
}

# 🔁 Procesar todas las plataformas
for PLATFORM in "${PLATFORMS[@]}"; do
    process_platform "$PLATFORM"
done

# 🧠 Análisis comparativo de plataformas
echo "📊 Running platform-level analysis..."

cp "$SCRIPTS_DIR/$ANALYZE_SCRIPT" "$OUTPUT_DIR"
pushd "$OUTPUT_DIR" > /dev/null

MODES=("tls" "vpn")

for MODE in "${MODES[@]}"; do
  for SIG in "${SIG_ALGS[@]}"; do
      f_arm="${SIG}_${MODE}_arm.csv"
      f_x86="${SIG}_${MODE}_x86.csv"

      if [[ -f "$f_arm" && -f "$f_x86" ]]; then
          echo "🔍 Comparing $f_arm vs $f_x86"
          python3 "$ANALYZE_SCRIPT" "$f_arm" "$f_x86"
      else
          echo "⚠️  Missing CSV for $SIG in $MODE — skipping"
      fi
  done
done

rm -f "$ANALYZE_SCRIPT"
popd > /dev/null

echo "🎉 All platforms processed and compared successfully!"