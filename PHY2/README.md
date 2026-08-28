# PHY2 - SDR Physical Layer Transceiver & Multi-Slice Optimization Suite

## Quick Start (Single Unified Program)
Run the **PHY2 Master Interactive Control Center** to access all tools, hardware selections, dashboard views, parameter updates, and standalone transceiver tests from a single menu:

```bash
python3 PHY2/main.py
# (or from the project root: python3 main.py)
```

```
================================================================================
           PHY2 MASTER PHYSICAL LAYER CONTROL & OPTIMIZATION CENTER             
================================================================================

  [1] 🧪 Software Simulation & Parameter Optimization Sweep
      Run full 0.001-step Cartesian sweep (with live progress bar) or launch dashboard

  [2] 📡 Hardware Mode: Physical SDR Transceiver Execution
      Target actual physical SDRs (Adalm-Pluto, bladeRF, RTL-SDR) & calibrate RF

  [3] 📊 Launch Web Dashboards Directly
      Open Software Simulation or Hardware SDR web dashboards instantly

  [4] ⚙️  Apply Optimized Parameters to Hardware GRC Flowgraph
      Update 'cdp_transeciever_hw.grc' with auto/custom values & recompile with grcc

  [5] 🔬 Test Adapted / Copied Transceiver Flowgraph Separately
      Run standalone test of your copied flowgraph with custom/optimal parameters

  [6] 🛡️  Run Centralized Automated Test Suite (7 Stages)
      Full regression verification across FLL, Equalizer, Preamble, CRC32, etc.

  [0] 🚪 Exit
```

---

## Overview
**PHY2** is a modular, high-reliability Physical Layer architecture and automated parameter optimization engine built specifically for physical SDR hardware transceivers (Adalm-Pluto, bladeRF, RTL-SDR) and high-fidelity simulated channels.

### Core DSP Architecture
- **Timing Error Detector (TED)**: Maximum Likelihood signal times derivative ($y \cdot y'$) timing recovery (`digital.TED_SIGNAL_TIMES_SLOPE_ML`).
- **Coarse Carrier Acquisition**: Frequency-Locked Loop (`digital.fll_band_edge_cc`) capturing large offsets up to $\pm 2.5\%$ sample rate.
- **Fine Carrier Lock**: Costas Loop (`digital.costas_loop_cc`) for residual frequency and phase tracking.
- **Frame Sync & Training**: Correlation Estimator (`digital.corr_est_cc`) tagging start-of-frame on arbitrary preamble lengths ($2$ to $64$ Bytes).
- **Channel Equalization**: Adaptive Linear Equalizer (`digital.linear_equalizer` with 11-tap CMA).
- **Packet Engine**: IEEE 802.3 32-bit CRC validation with tagged stream formatting.

---

## Operating Modes

| Mode | Target Domain | Execution & Hardware Behavior |
|:---|:---|:---|
| **Software Mode** (`--mode software`) | **Simulated Channel** | Runs deep Cartesian parameter simulation over simulated multipath, Rayleigh fading, AWGN noise, carrier offset, and clock drift with real-time progress bar. |
| **Hardware Mode** (`--mode hardware`) | **Actual Physical SDRs** | Connects directly to physical SDR hardware (**Adalm-Pluto**, **bladeRF**, **RTL-SDR**) via USB / IIO Ethernet. Throws an explicit `RuntimeError` if physical SDR is not detected. |

---

## Directory Structure

```
PHY2/
├── main.py                            # Master Interactive Control Center (Single entry-point for all workflows)
├── run_dashboard.py                   # Master Dashboard Server (Automated pipeline execution & browser launcher)
├── run_all_tests.py                   # Centralized Test Suite Runner (Executes all 7 stages in simulation)
├── run_all_hardware_tests.py          # Centralized Hardware Test Runner (Pluto, BladeRF, RTL-SDR)
├── dashboard/                         # Dedicated Zero-Dependency Web Dashboards
│   ├── software_dashboard.html        # Software Simulation Dashboard (63,000+ records)
│   ├── hardware_dashboard.html        # Hardware Actual SDR Dashboard (Top hardware selector & RF config)
│   ├── index.html                     # Default dashboard view
│   └── build_dashboard.py             # Master dashboard compilation script
├── hardware/                          # Hardware Transceivers, Applier, and Calibration
│   ├── apply_optimal_parameters.py    # GRC Flowgraph Parameter Applier (Auto/Manual + grcc compilation)
│   ├── run_dashboard.py               # Hardware dashboard convenience launcher
│   ├── optimize_hardware_sdr.py       # Live SDR hardware parameter sweep runner
│   ├── sdr_blocks_helper.py           # Unified Hardware Source/Sink Block Constructor (Explicit Disconnect Error)
│   ├── cdp_transceiver_pluto.grc      # Adalm-Pluto SDR Transceiver Flowgraph
│   ├── cdp_transceiver_bladerf.grc    # Nuand bladeRF Transceiver Flowgraph
│   ├── cdp_receiver_rtlsdr.grc        # RTL-SDR Receiver Flowgraph
│   └── cdp_transceiver_multi_hardware.grc # Universal Multi-Hardware GRC Flowgraph
├── optimization/                      # Master Optimization Engine (0.001..1.000 Full Range)
│   ├── run_dashboard.py               # Software dashboard convenience launcher
│   ├── run_ultra_deep_optimization.py # Master Cartesian grid optimizer runner (Multi-core parallel)
│   ├── deep_cartesian_sweep.py        # 0.001-step simulation engine with live terminal progress bar
│   ├── plot_deep_analysis.py          # Multi-slice SVG chart generator
│   └── results/                       # deep_sweep_results.csv, json, and optimal parameter files
├── adapted_original/                  # User Original Flowgraphs & Adapted Transceiver
│   ├── cdp_transeciever_hw.grc        # Original Hardware Transceiver GRC (Target for parameter updates)
│   ├── cdp_transeciever_soft.grc      # Original Software Transceiver GRC
│   ├── adapted_transceiver.py         # Parametric topblock (y·y' TED, 2..64 bytes preambles)
│   └── run_original_test.py           # Standalone validation runner
├── correlation_estimator/             # Training sequences & correlation estimator DSP helpers
│   └── corr_est_helper.py
└── tests/                             # Centralized Test Orchestration (Stages 05 - 10)
    ├── run_all_tests.py               # Centralized test suite runner
    ├── test_05_fll_band_edge.py       # Stage 05 test
    ├── test_06_linear_equalizer.py    # Stage 06 test
    ├── test_07_preamble_access_code.py# Stage 07 test
    ├── test_08_packet_crc32.py        # Stage 08 test
    ├── test_09_cdp_transceiver.py     # Stage 09 test
    ├── test_10_end_to_end_stress.py   # Stage 10 test
    └── test_adapted_original.py       # Adapted original transceiver test
```

---

## 1. Single Program Workflows (`python3 main.py`)

### A. Run Software Simulation & Dashboard
```bash
python3 PHY2/main.py
# Select [1] -> [1] to run sweep or [1] -> [2] to skip sweep and launch dashboard
```

### B. Run Actual Physical SDR Hardware Mode
```bash
python3 PHY2/main.py
# Select [2] -> Select SDR ([1] Pluto, [2] bladeRF, [3] RTL-SDR) -> Run or Launch Dashboard
```

### C. Apply Optimal Parameters to Your Copied GRC Flowgraph
```bash
python3 PHY2/main.py
# Select [4] -> Select [1] Auto BPSK or [2] Auto QPSK or [3] Custom Values
```
Updates `PHY2/adapted_original/cdp_transeciever_hw.grc` and invokes `grcc` to compile.

### D. Test Your Copied Transceiver Flowgraph Separately
```bash
python3 PHY2/main.py
# Select [5] -> Select Modulation ([1] BPSK, [2] QPSK, [3] BOTH)
```
Executes standalone test under noise, carrier offsets, and clock drift.

---

## 2. Pinpointed Optimal Values Reference

| Parameter | BPSK ($y \cdot y'$ TED) | QPSK ($y \cdot y'$ TED) | Safe Operating Range | DSP Function & Rationale |
|:---|:---:|:---:|:---:|:---|
| **Timing Error Detector (TED)** | `TED_SIGNAL_TIMES_SLOPE_ML` | `TED_SIGNAL_TIMES_SLOPE_ML` | — | Signal times derivative ($y \cdot y'$) maximum likelihood timing recovery. |
| **FLL Band-Edge Loop BW** | **`0.0314 rad/sym`** ($2\pi 	imes 0.005$) | **`0.0314 rad/sym`** | `0.001 .. 1.000` | Wideband carrier acquisition capturing up to $\pm 2.5\%$ frequency offsets. |
| **Costas Loop BW** | **`0.0628 rad/sym`** ($2\pi 	imes 0.010$) | **`0.0628 rad/sym`** | `0.001 .. 1.000` | Fast phase acquisition and residual carrier locking. |
| **Symbol Sync Loop BW** | **`0.0250 rad/sym`** | **`0.0550 rad/sym`** | `0.001 .. 1.000` | High-Q jitter suppression and clock drift tracking. |
| **Correlation Estimator** | Enabled (Tag `'corr_est'`) | Enabled (Tag `'corr_est'`) | — | Symbol timing sync & equalizer training trigger. |
| **Preamble Length** | **`16` to `32` Bytes** (`0x55`) | **`32` Bytes** (`0x33, 0xCC`) | `2 .. 64` Bytes | Rich clock transition density for reliable timing lock. |
| **Linear Equalizer** | 11 Taps (CMA step `0.001`) | 11 Taps (CMA step `0.001`) | — | Removes multipath inter-symbol interference. |
| **Average PDR / BER** | **90.0% / $2.22 	imes 10^{-3}$** | **90.0% / $2.22 	imes 10^{-3}$** | — | 100% CRC integrity across noise and offsets. |
