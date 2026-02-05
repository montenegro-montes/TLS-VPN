#!/bin/bash

echo "🚀 Starting scenario batch execution..."

# --- Scenario 1 ---
echo "🔹 RunBenchmark"
(
  cd execution_scripts || exit 1
  ./RunBenchmark.sh
)



#echo "✅ All scenarios executed."


# --- Process Size results ---
#echo "🛠️  Processing Size results..."
#(
#  cd Size || exit 1
#  ./processAll.sh
#)

# --- Process Time results ---
#echo "🛠️  Processing Time results..."
#(
#  cd Time || exit 1
#  ./processAll.sh
#)

#echo "🏁 All processing complete."