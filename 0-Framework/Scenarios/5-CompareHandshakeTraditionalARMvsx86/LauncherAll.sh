#!/bin/bash

echo "🚀 Starting scenario batch execution..."


# --- Scenario 1 ---
echo "🔹 Signature tradictional, KEM post-quantum - compare ARM vs x86"
(
  cd csv || exit 1
  python3 analyze_levels_Platforms.py ed25519_tls_arm.csv ed25519_tls_x86.csv 
  python3 analyze_levels_Platforms.py secp384r1_tls_arm.csv secp384r1_tls_x86.csv 
  python3 analyze_levels_Platforms.py secp521r1_tls_arm.csv secp521r1_tls_x86.csv 
)



echo "✅ All scenarios executed."




