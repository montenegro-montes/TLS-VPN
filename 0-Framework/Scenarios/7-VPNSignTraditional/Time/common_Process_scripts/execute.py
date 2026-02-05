import subprocess
import os
import argparse
import sys

# Argumentos
parser = argparse.ArgumentParser(description="Process Wireshark captures (.pcapng) and generate VPN analysis CSVs.")
parser.add_argument('--tag', required=True, help='Suffix to append to generated image files, e.g., "_1ms".')
args = parser.parse_args()
tag = args.tag

# Directorios
capture_dir = "capture"
scripts_dir = "process_scripts"
script_name = "analiza_pcap_vpn.py"

# Asegurar que la carpeta 'capture' existe
os.makedirs(capture_dir, exist_ok=True)


#print(f"📌 Current working directory: {os.getcwd()}")


# Mostrar aviso previo
print("📂 Please ensure you have copied your Wireshark capture files (.pcapng) into the 'capture' directory.")
input("[!] Press Enter to exit...")

print("🔍 Starting PCAPNG processing...")

# Obtener lista de capturas
pcap_files = [f for f in os.listdir(capture_dir) if f.endswith(".pcapng")]

# Si no hay archivos, salir
if not pcap_files:
    print("\n❌ No PCAPNG files found in the 'capture' directory.")
    print("📥 Please copy your Wireshark captures (.pcapng) into the 'capture' folder before running this script.")
    sys.exit(1)

# Verificar que el script existe
script_path = os.path.join(scripts_dir, script_name)
if not os.path.isfile(script_path):
    print(f"❌ Script not found: {script_path}")
    sys.exit(1)

# Procesar cada archivo .pcapng
for pcap in pcap_files:
    pcap_path = os.path.join(capture_dir, pcap)
    output_tag = os.path.splitext(os.path.basename(pcap))[0]

    print(f"📁 Processing {pcap_path} -> Tag: {output_tag}...")

    try:
        subprocess.run([
            "python3",
            script_path,
            pcap_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error processing {pcap_path}: {e}")
        continue

print("✅ All PCAPNG files processed.")
