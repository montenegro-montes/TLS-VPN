#!/bin/bash

echo "🚀 Starting scenario batch execution..."

# --- Scenario 1 ---
echo "🔹 Signature Traditional, KEM traditional, hybrid and post-quantum Loss Stable"
(
  cd Time/Connections/Connections_Mutual_Loss/docker_scripts || exit 1
  ./LauncherVPN_Traditional.sh capture 50 stable
)

# --- Scenario 2 ---
#echo "🔹 Signature Traditional, KEM traditional, hybrid and post-quantum Delay 10 ms"
#(
#  cd Time/Connections/Connections_Mutual_Delay/docker_scripts || exit 1
#  ./LauncherVPN_Traditional.sh capture 50 simple 0 10
#)


echo "✅ All scenarios executed."




# --- Process Time results ---
echo "🛠️  Processing Time results..."
(
  cd Time || exit 1
  ./processAll.sh
)

echo "🏁 All processing complete."