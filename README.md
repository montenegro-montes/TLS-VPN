# 🐳 Post-Quantum TLS/VPN Test Framework

This framework provides a complete environment to test and benchmark the performance and compatibility of **TLS and VPN protocols (OpenVPN over OpenSSL)** using **classical, hybrid, and post-quantum cryptographic algorithms** inside Docker containers.

It supports multiple test scenarios, including primitive benchmarks, TLS handshakes, and full VPN setup with support for delay and packet loss using real network stress tools.

<p align="center"> <img src="framework.png" alt="Handshake Results" width="450"/><br>
  <em>Figure 1. Performance Evaluation Framework.</em>

</p>

---

## 🚀 Features

- 🔐 Benchmarking TLS/OpenVPN with traditional, hybrid, and post-quantum KEMs and signature algorithms.
- 🐳 Fully containerized with Docker.
- 📦 Includes support tools like **Pumba** (network emulation), **Wireshark** and **Edgeshark**.
- 📈 Automated logging, CSV export, and Python plotting.
- 📂 Modular scenario structure with per-test Launcher scripts.

---

## 📁 Project Structure

```bash
.
├── Applications/              # Pumba and other optional tools
├── Scenarios/                 # All test scenarios (TLS, VPN, etc.)
│   ├── 1-Primitives/          # Cryptographic primitive benchmarking
│   ├── 2-HandshakeSignTraditional/    # TLS mutual handshakes Signature Traditional
│   ├── 3-HandshakeSignPostQuantum/    # TLS mutual handshakes Signature Post-Quantum
│   ├── 4-VPNSignTraditional/ # VPN establishment connectionevaluation Signature Traditional
│   ├── 5-VPNSignPostQuantum/ # VPN establishment connectionevaluation Signature Post-Quantum
│   │   ├── Time/              # Logs, captures, CSVs
│   │   ├── LauncherAll.sh     # Scenario launcher
│   │   └── ...
├── common_Process_scripts/    # Python analysis and plotting
├── frameWork.sh               # Main launcher script (menu-based)
├── processAll.sh              # Batch processor for CSVs
└── README.md
```



## 📦 Requirements

- Docker (Linux/macOS/WSL)
- Python 3.8+
- Wireshark (for packet analysis)
- Pumba (included in `Applications/`)

---

## 🔧 Installation

```bash
git clone https://github.com/<your-username>/post-quantum-tls-vpn-framework.git
cd post-quantum-tls-vpn-framework
chmod +x frameWork.sh
```

---

## 🧪 How to Use

### Launch the menu:

```bash
./frameWork.sh
```

### Menu Overview:

```
╔════════════════════════════════════════╗
║      🐳  Docker & Protocol Menu        ║
╠════════════════════════════════════════╣
║ 1️⃣  Check installation                 ║
║ 2️⃣  Docker administration              ║
║ 3️⃣  Running Scenario                   ║
║ 4️⃣  Exit                               ║
╚════════════════════════════════════════╝
```

### Example Run:

1. Select `1️⃣ Check installation` to verify Docker, Pumba, Wireshark.
2. Select `2️⃣ Docker administration` to build and verify TLS/VPN containers.
3. Select `3️⃣ Running Scenario` to launch a full experiment (e.g., VPN handshake with ML-KEM).
4. Review logs and processed CSVs in each scenario's `Time/` subfolder.

---

## 📊 Results & Analysis

Processed logs and PCAPs are analyzed using Python scripts under `common_Process_scripts/`. Results are saved as:

- 📄 `*.csv`: Raw metrics
- 📈 Plots: Boxplots, performance graphs
- 📜 `*.tex`: LaTeX-ready result files

You can run analysis manually or via automation (`processAll.sh`).

---

## 🧠 Based On

- [OpenSSL + oqsprovider (Open Quantum Safe)](https://github.com/open-quantum-safe/openssl)
- [OpenVPN](https://openvpn.net/)
- [Pumba](https://github.com/alexei-led/pumba) — chaos testing
- Wireshark + TShark

---

## 📜 License

MIT License — feel free to use and modify for your research or experiments.

---
