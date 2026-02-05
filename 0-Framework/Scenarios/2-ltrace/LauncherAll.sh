#!/bin/bash

echo "🚀 Starting scenario batch execution..."

# --- Scenario 1 ---
echo "🔹 Signature Traditional, KEM traditional, hybrid and post-quantum"
(
  cd Time/Connections/Connections_Mutual/docker_scripts || exit 1
  ./LauncherSignTraditionalv2.sh tls mutual nocapture 2000 none 0 0

)

# --- Scenario 2 ---
echo "🔹 Signature PQ, KEM traditional, hybrid and post-quantum"
(
  cd Time/Connections/Connections_Mutual/docker_scripts || exit 1
  ./LauncherSignPQv2.sh tls mutual nocapture 2000  none 0 0
)




echo "✅ All scenarios executed."




 --- Process Time results ---
echo "🛠️  Processing Time results..."
(
  cd Time || exit 1
  ./processAll.sh
)

echo "🏁 All processing complete."