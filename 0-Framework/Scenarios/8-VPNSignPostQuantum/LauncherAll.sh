#!/bin/bash

echo "🚀 Starting scenario batch execution..."


# --- Scenario 1 ---
echo "🔹 Signature post-quantum, KEM post-quantum"
(
  cd Time/Connections/Connections_CaptureKey_Mutual/docker_scripts || exit 1
  ./LauncherVPN_PQ.sh captureKey 
  mv sslkeys ../

)

# --- Scenario 2 ---
echo "🔹 Signature post-quantum, KEM  post-quantum"
(
  cd Time/Connections/Connections_Mutual/docker_scripts || exit 1
  ./LauncherVPN_PQ.sh capture 50
)


echo "✅ All scenarios executed."




# --- Process Time results ---
echo "🛠️  Processing Time results..."
(
  cd Time || exit 1
  ./processAll.sh
)

echo "🏁 All processing complete."