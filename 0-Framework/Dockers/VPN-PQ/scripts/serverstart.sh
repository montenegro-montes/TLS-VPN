#!/bin/bash
set -euo pipefail  # Fail on error, undefined vars, and pipeline errors

cd /etc/openvpn || {
    echo "❌ Failed to change to /etc/openvpn"
    exit 1
}

echo "📁 Working directory: $(pwd)"

# 1. Export LD_PRELOAD and prepare SSLKEYLOGFILE if needed
if [ -n "${LD_PRELOAD:-}" ]; then
    echo "📄 Initial contents of /sslkeys:"
    ls -l /sslkeys || echo "⚠️  Could not list /sslkeys (might not be mounted)"

    echo "🔐 LD_PRELOAD is set to: $LD_PRELOAD"
    export LD_PRELOAD

    if [ -n "${SSLKEYLOGFILE:-}" ]; then
        echo "📝 Preparing SSL key log file at: $SSLKEYLOGFILE"
        mkdir -p "$(dirname "$SSLKEYLOGFILE")"
        touch "$SSLKEYLOGFILE"
        chmod 666 "$SSLKEYLOGFILE"
    else
        echo "⚠️  SSLKEYLOGFILE is not defined even though LD_PRELOAD is"
    fi
else
    echo "⚠️  LD_PRELOAD is not defined. TLS secrets will not be captured."
fi

# 2. Debug useful env vars
echo "🌍 Environment variables:"
env | grep -E 'LD_PRELOAD|TLS_GROUPS|OQSIGALG|SSLKEYLOGFILE' || true

# 3. Default signature algorithm
if [ -z "${OQSIGALG:-}" ]; then
   OQSSIGALG="mldsa65"
   echo "ℹ️  OQSIGALG not set. Defaulting to: $OQSSIGALG"
fi

# 4. Generate certificates if missing
if [ ! -f ca_cert.crt ]; then
    echo "📜 CA certificate missing. Generating it using signature algorithm: $OQSSIGALG"
    createcerts_and_config.sh "$OQSSIGALG"
fi

# 5. Start OpenVPN
if [ -z "${TLS_GROUPS:-}" ]; then
    echo "🚀 Starting OpenVPN without --tls-groups"
    openvpn --config server.config
else
    echo "🚀 Starting OpenVPN with --tls-groups $TLS_GROUPS"
    openvpn --config server.config --tls-groups "$TLS_GROUPS"
fi
