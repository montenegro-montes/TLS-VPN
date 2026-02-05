#!/bin/bash

echo "🚀 Starting scenario batch execution..."


# --- Scenario 1 ---
echo "🔹 Signature tradictional, KEM post-quantum - compare ARM vs x86"
(
  cd csv || exit 1
  python3 analyze_levels_Platforms.py mldsa44_tls_armPQ.csv mldsa44_tls_x86PQ.csv 
  python3 analyze_levels_Platforms.py mldsa65_tls_armPQ.csv mldsa65_tls_x86PQ.csv 
  python3 analyze_levels_Platforms.py mldsa87_tls_armPQ.csv mldsa87_tls_x86PQ.csv 
)



echo "✅ All scenarios executed."




