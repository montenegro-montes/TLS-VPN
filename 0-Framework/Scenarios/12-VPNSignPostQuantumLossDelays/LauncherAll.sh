#!/bin/bash

echo "🚀 Starting scenario batch execution..."


# --- Scenario 1 ---
echo "🔹 Signature post-quantum, KEM traditional Loss Stable"
(
  cd Time/Connections/Connections_Mutual_Loss/docker_scripts || exit 1
  ./LauncherVPN_PQ.sh capture 50 stable
)

# --- Scenario 2 ---
#echo "🔹 Signature post-quantum, KEM  post-quantum Delay 10 ms"
#(
#  cd Time/Connections/Connections_Mutual_Delay/docker_scripts || exit 1
#  ./LauncherVPN_PQ.sh capture 50 simple 0 10
#)


echo "✅ All scenarios executed."




# --- Process Time results ---
echo "🛠️  Processing Time results..."
(
  cd Time || exit 1
  ./processAll.sh
)

echo "🏁 All processing complete."