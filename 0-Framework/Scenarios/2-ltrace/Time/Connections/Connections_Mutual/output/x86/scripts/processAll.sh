
python3 crypto_percent_calcv2.py ../Traditional/handshake/ed25519_tls_x86mutual2000.csv ../Traditional/kem_x86_benchmark_raw.csv ../Traditional/signature_x86_signatures_raw.csv
python3 crypto_percent_calcv2.py ../Traditional/handshake/secp384r1_tls_x86mutual2000.csv ../Traditional/kem_x86_benchmark_raw.csv ../Traditional/signature_x86_signatures_raw.csv
python3 crypto_percent_calcv2.py ..//Traditional/handshake/secp521r1_tls_x86mutual2000.csv ../Traditional/kem_x86_benchmark_raw.csv ../Traditional/signature_x86_signatures_raw.csv

( head -n 1 ed25519_summary.csv; tail -n +2 -q ed25519_summary.csv secp384r1_summary.csv secp521r1_summary.csv ) > ../crypto_x86_Traditional.csv

rm ed25519_summary.csv
rm secp384r1_summary.csv
rm secp521r1_summary.csv


python3 crypto_percent_calcv2.py ../PQ/handshake/mldsa44_tls_x86PQ.csv ../PQ/kem_x86_benchmark_raw.csv ../PQ/signature_x86_PQ_signatures_raw.csv
python3 crypto_percent_calcv2.py ../PQ/handshake/mldsa65_tls_x86PQ.csv ../PQ/kem_x86_benchmark_raw.csv ../PQ/signature_x86_PQ_signatures_raw.csv
python3 crypto_percent_calcv2.py ../PQ/handshake/mldsa87_tls_x86PQ.csv ../PQ/kem_x86_benchmark_raw.csv ../PQ/signature_x86_PQ_signatures_raw.csv

( head -n 1 mldsa44_summary.csv; tail -n +2 -q mldsa44_summary.csv mldsa65_summary.csv mldsa87_summary.csv ) > ../crypto_x86_PQ.csv

rm mldsa44_summary.csv
rm mldsa65_summary.csv
rm mldsa87_summary.csv