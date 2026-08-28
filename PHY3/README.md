# PHY3 — Physical SDR Hardware Optimization Suite

A specialized hardware parameter optimizer built directly upon the user's original GNU Radio flow diagram (`cdp_transeciever_hw.grc`) for **BPSK** and **QPSK**.

---

## 📁 Folder Structure

```
PHY3/
├── cdp_transeciever_hw.grc      # Direct copy of the user's original hardware flow diagram
├── cdp_hardware_transceiver.py  # Python transceiver matching the original GRC flow graph
├── sdr_blocks_helper.py         # Unified SDR block interface (Pluto / bladeRF / RTL-SDR / Sim)
├── optimize_hardware.py         # Live hardware optimization engine (sweeps candidate grids)
├── apply_optimal_parameters.py  # Injects pinpointed optimal values into the GRC file
├── run_dashboard.py             # Launches the standalone Hardware SDR Web Dashboard
├── main.py                      # Central interactive CLI menu
├── dashboard/
│   ├── build_dashboard.py       # Rebuilds the HTML5 Hardware Web Dashboard
│   ├── hardware_dashboard.html  # Interactive Hardware Dashboard
│   └── hardware_data.js         # External fast-loading dataset
└── results/
    ├── hardware_optimization_results.json # Cumulative trial dataset
    ├── hardware_optimization_results.csv  # CSV export
    └── optimal_hardware_parameters.json   # Pinpointed optimal parameters for BPSK & QPSK
```

---

## 🚀 Quick Start

### 1. Launch Interactive Control Center
```bash
python3 PHY3/main.py
```

### 2. Run Direct Command Line Sweeps

#### Adalm-Pluto SDR (Full-Duplex IIO)
```bash
# Top 1,000 fast calibration (both BPSK & QPSK)
python3 PHY3/optimize_hardware.py --hw pluto --top-n 1000

# Full sweep on top 50,000 lowest-BER candidates
python3 PHY3/optimize_hardware.py --hw pluto --top-n 50000 --mod all
```

#### Nuand bladeRF (USB 3.0)
```bash
python3 PHY3/optimize_hardware.py --hw bladerf --top-n 1000 --mod QPSK
```

#### RTL-SDR Receiver (RX Only)
```bash
python3 PHY3/optimize_hardware.py --hw rtlsdr --top-n 1000 --mod BPSK
```

#### Emulation Mode (Simulation with RF Impairments)
```bash
python3 PHY3/optimize_hardware.py --hw sim --top-n 50
```

---

## 🛠️ Applying Optimal Parameters to GRC

To automatically update `PHY3/cdp_transeciever_hw.grc` with the optimal parameters found from the hardware sweep:

```bash
# Apply QPSK optimal parameters
python3 PHY3/apply_optimal_parameters.py QPSK

# Apply BPSK optimal parameters
python3 PHY3/apply_optimal_parameters.py BPSK
```

---

## 📊 Viewing the Hardware Dashboard

```bash
python3 PHY3/run_dashboard.py
```
Open **`http://localhost:8082/hardware_dashboard.html`** in your browser.
