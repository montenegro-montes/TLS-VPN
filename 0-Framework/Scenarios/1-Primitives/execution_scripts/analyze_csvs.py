import os
import csv
import statistics

RESULTS_DIR = "results"
SUMMARY_FILE = os.path.join(RESULTS_DIR, "summary.csv")

def analyze_csv(file_path):
    values = []

    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        lines = list(reader)

        # Skip header and warm-up
        for row in lines[2:]:
            try:
                value = float(row[1].strip())
                values.append(value)
            except (ValueError, IndexError):
                continue  # skip bad or empty lines

    if len(values) == 0:
        return None, None

    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    cv = (stdev / mean) * 100 if mean != 0 else 0.0

    return round(mean, 2), round(cv, 2)

# Scan all CSVs and process them
results = []
for filename in os.listdir(RESULTS_DIR):
    if filename.endswith("_timing.csv"):
        alg = filename.replace("_timing.csv", "")
        file_path = os.path.join(RESULTS_DIR, filename)
        mean, cv = analyze_csv(file_path)
        if mean is not None:
            results.append((alg, mean, cv))
            print(f"🔹 {alg:10s} → Mean = {mean:.2f} ms | CV = {cv:.2f}%")
        else:
            print(f"⚠️  {alg:10s} → No valid data")

# Save to summary.csv
with open(SUMMARY_FILE, "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Algorithm", "Mean(ms)", "CV(%)"])
    writer.writerows(results)

print(f"\n✅ Summary saved to: {SUMMARY_FILE}")
