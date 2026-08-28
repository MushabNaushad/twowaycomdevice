# PHY2 - Adapted Original Transceiver Suite

## Overview
This directory contains the user's original CDP flowgraphs adapted with external parameter bindings to support both **BPSK** and **QPSK** modulation with `digital.TED_SIGNAL_TIMES_SLOPE_ML` ($y \cdot y'$ TED), Correlation Estimator (`corr_est_cc`) + Adaptive Linear Equalizer, and comprehensive 0.005 to 1.000 rad/sym bandwidth sweeps.

---

## Files in this Directory
- `adapted_transceiver.py`: Parametric class wrapper exposing all loop bandwidths, modulation types, and channel impairment parameters using $y \cdot y'$ TED.
- `run_original_test.py`: Standalone validation script testing BPSK and QPSK across channel noise, carrier frequency offsets, and clock drift.
- `optimize_original_ultra_fine.py`: Parallel multi-core optimizer evaluating loop bandwidths across 0.005 to 1.000 rad/sym with milliradian precision.
- `plot_comprehensive_charts.py`: Visualizer rendering standalone SVG charts and master interactive dashboard.
- `cdp_transeciever_soft.grc`: Original software flowgraph.
- `cdp_transeciever_hw.grc`: Original hardware flowgraph.
- `results/`: Contains high-density JSON/CSV datasets, SVG charts, and `comprehensive_dashboard.html`.

---

## Pinpointed Optimal Parameters (0.005 to 1.000 Range)

| Parameter | BPSK ($y \cdot y'$ TED) | QPSK ($y \cdot y'$ TED) | Safe Range |
|:---|:---:|:---:|:---:|
| **FLL Band-Edge Loop BW** | `0.0314 rad/sym` | `0.0314 rad/sym` | `0.005 .. 1.000` |
| **Costas Loop BW** | `0.0628 rad/sym` | `0.0628 rad/sym` | `0.005 .. 1.000` |
| **Symbol Sync Loop BW** | `0.0250 rad/sym` | `0.1150 rad/sym` | `0.005 .. 1.000` |
| **Correlation Estimator** | Enabled (Threshold 0.8) | Enabled (Threshold 0.8) | — |
| **Preamble Length** | `16` to `32` Bytes (`0x55`) | `32` Bytes (`0x33, 0xCC`) | `16 .. 64` Bytes |

---

## Usage Commands

```bash
# 1. Run validation test on original transceiver:
python3 PHY2/adapted_original/run_original_test.py

# 2. Run the 0.005 to 1.000 rad/sym full-range optimization & chart generator:
python3 PHY2/adapted_original/optimize_original_ultra_fine.py
python3 PHY2/adapted_original/plot_comprehensive_charts.py

# 3. Launch interactive web dashboard:
python3 PHY2/run_dashboard.py
```
