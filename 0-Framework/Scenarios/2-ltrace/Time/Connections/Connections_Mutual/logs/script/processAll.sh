#bin/sh

echo "ARM - Traditional"
python3 parse_ltracev2.py ../arm/logs/Traditional/Mutual/L1.log
python3 parse_ltracev2.py ../arm/logs/Traditional/Mutual/L3.log
python3 parse_ltracev2.py ../arm/logs/Traditional/Mutual/L5.log
python3 summarize_crypto_costsv2.py  ./csv_ltrace/ TR ltrace_crypto_summary_traditional_arm.csv

rm -r ./csv_ltrace/
mv ltrace_crypto_summary_traditional_arm.csv ../arm/ltrace_crypto_summary_traditional_arm.csv


echo "x86 - Traditional"
python3 parse_ltracev2.py ../x86/logs/Traditional/Mutual/L1.log
python3 parse_ltracev2.py ../x86/logs/Traditional/Mutual/L3.log
python3 parse_ltracev2.py ../x86/logs/Traditional/Mutual/L5.log
python3 summarize_crypto_costsv2.py ./csv_ltrace/ TR ltrace_crypto_summary_traditional_x86.csv

rm -r ./csv_ltrace/
mv ltrace_crypto_summary_traditional_x86.csv ../x86/ltrace_crypto_summary_traditional_x86.csv


echo "ARM - PQ"
python3 parse_ltracev2.py ../arm/logs/PQ/Mutual/L1.log
python3 parse_ltracev2.py ../arm/logs/PQ/Mutual/L3.log
python3 parse_ltracev2.py ../arm/logs/PQ/Mutual/L5.log
python3 summarize_crypto_costsv2.py ./csv_ltrace/ PQ ltrace_crypto_summary_PQ_arm.csv

rm -r ./csv_ltrace/
mv ltrace_crypto_summary_PQ_arm.csv ../arm/ltrace_crypto_summary_PQ_arm.csv


echo "X86 - PQ"
python3 parse_ltracev2.py ../x86/logs/PQ/Mutual/L1.log
python3 parse_ltracev2.py ../x86/logs/PQ/Mutual/L3.log
python3 parse_ltracev2.py ../x86/logs/PQ/Mutual/L5.log
python3 summarize_crypto_costsv2.py ./csv_ltrace/ PQ ltrace_crypto_summary_PQ_x86.csv

rm -r ./csv_ltrace/
mv ltrace_crypto_summary_PQ_x86.csv ../x86/trace_crypto_summary_PQ_x86.csv
