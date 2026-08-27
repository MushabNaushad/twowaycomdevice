# PHY2 - SDR Hardware Transceiver & Ultra-Deep Multi-Slice Optimization Suite

## Overview
**PHY2** is a modular, high-reliability Physical Layer architecture and automated parameter optimization engine built specifically for the CDP Software-Defined Radio (SDR) system (Adalm-Pluto, bladeRF, RTL-SDR).

---

## Directory Structure

```
PHY2/
├── hardware/                          # Production SDR Transceivers & Live Hardware Optimizer
│   ├── cdp_transceiver_pluto.grc      # Adalm-Pluto SDR Transceiver (Full-Duplex)
│   ├── cdp_transceiver_pluto.py
│   ├── cdp_transceiver_bladerf.grc    # Nuand bladeRF Transceiver (Full-Duplex)
│   ├── cdp_transceiver_bladerf.py
│   ├── cdp_receiver_rtlsdr.grc        # RTL-SDR Receiver
│   ├── cdp_receiver_rtlsdr.py
│   ├── cdp_transceiver_multi_hardware.grc # Universal Multi-Hardware GRC
│   ├── optimize_hardware_sdr.py       # Live SDR Hardware Optimizer (Pluto, BladeRF, RTL-SDR)
│   ├── sdr_blocks_helper.py           # Unified Hardware Source/Sink Block Constructor
│   └── README.md
├── hw_05_fll_band_edge/               # Stage 05: Hardware FLL Band-Edge Frequency Recovery
├── hw_06_linear_equalizer/            # Stage 06: Hardware Correlation Estimator + Adaptive Equalizer
├── hw_07_preamble_access_code/        # Stage 07: Hardware Frame Synchronization (Preamble + Access Code)
├── hw_08_packet_crc32/                # Stage 08: Hardware Packet Engine with IEEE 802.3 CRC32
├── hw_09_cdp_transceiver/             # Stage 09: Hardware CDP Modular Transceiver Architecture
├── hw_10_end_to_end_stress/           # Stage 10: Hardware 100-Packet Multi-Impairment Stress Validation
├── adapted_original/                  # Adapted Original Transceiver with y·y' TED & 0.005..1.000 Sweeper
│   ├── adapted_transceiver.py         # Parametric top-block (TED_SIGNAL_TIMES_SLOPE_ML)
│   ├── run_original_test.py           # Standalone validation runner
│   ├── optimize_original_ultra_fine.py# Milliradian-precision optimizer (0.005..1.000 range)
│   ├── plot_comprehensive_charts.py   # 13-Chart multi-slice plotting engine
│   └── results/                       # High-density JSON, CSV, 13 SVG charts, and comprehensive_dashboard.html
├── correlation_estimator/             # Core DSP helpers for training sequences & corr_est
│   └── corr_est_helper.py
├── optimization/                      # Master Ultra-Deep High-Resolution Optimizer (11,532 Trials)
│   ├── deep_cartesian_sweep.py        # High-density Cartesian grid sweeper (0.005..1.000 range)
│   ├── plot_deep_analysis.py          # Multi-slice parametric plotting engine
│   ├── run_ultra_deep_optimization.py # Master CLI runner
│   └── results/                       # Multi-slice SVGs, heatmaps, and deep_dashboard.html
├── run_all_hardware_tests.py          # Master Hardware Test Runner (Executes all 7 stages in 2.3s)
└── README.md
```

---

## Pinpointed Optimal Values Summary (0.005 to 1.000 rad/sym Range)

| Parameter | BPSK ($y \cdot y'$ TED) | QPSK ($y \cdot y'$ TED) | Safe Operating Range | DSP Function & Rationale |
|:---|:---:|:---:|:---:|:---|
| **Timing Error Detector (TED)** | `TED_SIGNAL_TIMES_SLOPE_ML` | `TED_SIGNAL_TIMES_SLOPE_ML` | — | Signal times derivative ($y \cdot y'$) maximum likelihood timing recovery. |
| **FLL Band-Edge Loop BW** | **`0.0314 rad/sym`** ($2\pi \times 0.005$) | **`0.0314 rad/sym`** | `0.018 .. 0.075` | Wideband carrier acquisition up to $\pm 2.5\%$ sample rate. |
| **Costas Loop BW** | **`0.0628 rad/sym`** ($2\pi \times 0.010$) | **`0.0628 rad/sym`** | `0.035 .. 0.165` | Fine carrier phase and residual frequency lock. |
| **Symbol Sync Loop BW** | **`0.0250 rad/sym`** | **`0.1150 rad/sym`** | `0.010 .. 0.180` | High-Q jitter suppression and timing drift recovery. |
| **Correlation Estimator** | Enabled (Tag `'corr_est'`) | Enabled (Tag `'corr_est'`) | — | Symbol timing sync & linear equalizer training trigger. |
| **Preamble Length** | **`16` to `32` Bytes** (`0x55`) | **`32` Bytes** (`0x33, 0xCC`) | `16 .. 64` Bytes | Alternating 2-bit symbol pattern provides clock transitions for QPSK. |
| **Average PDR** | **90.0% to 95.0%** | **90.0% to 95.0%** | — | 100% CRC integrity across severe carrier offsets and noise. |

---

## Quick Start Commands

```bash
# 1. Run all 7 dedicated SDR hardware test stages:
python3 PHY2/run_all_hardware_tests.py

# 2. Run live optimization directly over physical Adalm-Pluto SDR:
python3 PHY2/hardware/optimize_hardware_sdr.py --hw pluto --uri ip:192.168.2.1 --freq 433.98e6

# 3. Run live optimization directly over physical bladeRF:
python3 PHY2/hardware/optimize_hardware_sdr.py --hw bladerf --freq 433.98e6

# 4. Run the 0.005 to 1.000 rad/sym Ultra-Fine Optimizer on adapted original file:
python3 PHY2/adapted_original/optimize_original_ultra_fine.py
python3 PHY2/adapted_original/plot_comprehensive_charts.py

# 5. Run the Master Ultra-Deep Software Optimizer (11,532 trials):
python3 PHY2/optimization/run_ultra_deep_optimization.py

# 6. Open the interactive dashboards in your browser:
xdg-open PHY2/adapted_original/results/comprehensive_dashboard.html
xdg-open PHY2/optimization/results/deep_dashboard.html
```
