#!/usr/bin/env python3
import sys
import csv

def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 calculate_time.py <kem.csv> <sig.csv> <op_counts> [kem_keygen kem_encaps kem_decaps sign verify]")
        print("Example: python3 calculate_time.py kem.csv sig.csv 1,1,1,2,4")
        sys.exit(1)

    kem_file = sys.argv[1]
    sig_file = sys.argv[2]
    keygen_n, encaps_n, decaps_n, sign_n, verify_n = map(int, sys.argv[3].split(","))

    kems = read_csv(kem_file)
    sigs = read_csv(sig_file)

    header = ["kem"] + [sig["signature"] for sig in sigs]
    rows = []

    for kem in kems:
        row = {"kem": kem["kem"]}
        kem_cost = (
            float(kem["keygen_mean"]) * keygen_n +
            float(kem["encaps_mean"]) * encaps_n +
            float(kem["decaps_mean"]) * decaps_n
        )
        for sig in sigs:
            sig_cost = (
                float(sig["sign_mean"]) * sign_n +
                float(sig["verify_mean"]) * verify_n
            )
            total = round(kem_cost + sig_cost, 3)
            row[sig["signature"]] = total
        rows.append(row)

    with open("kem_signature_values.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    print("✅ Written: kem_signature_values.csv")

if __name__ == "__main__":
    main()
