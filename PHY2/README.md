# PHY2 - SDR Hardware Transceiver & Ultra-Deep Multi-Slice Optimization Suite

## Overview
**PHY2** is a modular, high-reliability Physical Layer architecture and automated parameter optimization engine built specifically for the CDP Software-Defined Radio (SDR) system (Adalm-Pluto, bladeRF, RTL-SDR).

---

## Directory Structure

```
PHY2/
├── run_dashboard.py                   # Master Dashboard Server (Launches interactive web dashboard)
├── interactive_plotter.py             # Master Terminal Dynamic Plotter & REPL Analyzer
├── run_all_tests.py                   # Master Test Suite Runner (Delegates to centralized tests)
├── run_all_hardware_tests.py          # Master Hardware Runner (Sim, Pluto, BladeRF, RTL-SDR)
├── dashboard/                         # 100% Zero-Dependency Standalone Dynamic Analytics
│   ├── index.html                     # Standalone HTML5 Canvas multi-line dynamic graphing & CSV matrix
│   ├── build_dashboard.py             # Builder script that embeds full-range sweep data
│   └── README.md
├── tests/                             # Centralized Test Suite Orchestration
│   ├── run_all_tests.py               # Master centralized test runner with CLI argument parsing
│   ├── test_05_fll_band_edge.py       # Centralized Stage 05 runner
│   ├── test_06_linear_equalizer.py    # Centralized Stage 06 runner
│   ├── test_07_preamble_access_code.py# Centralized Stage 07 runner
│   ├── test_08_packet_crc32.py        # Centralized Stage 08 runner
│   ├── test_09_cdp_transceiver.py     # Centralized Stage 09 runner
│   ├── test_10_end_to_end_stress.py   # Centralized Stage 10 runner
│   └── test_adapted_original.py       # Centralized adapted transceiver test runner
├── hardware/                          # Production SDR Transceivers & Live Hardware Optimizer
│   ├── cdp_transceiver_pluto.grc      # Adalm-Pluto SDR Transceiver (Full-Duplex)
│   ├── cdp_transceiver_pluto.py
│   ├── cdp_transceiver_bladerf.grc    # Nuand bladeRF Transceiver (Full-Duplex)
│   ├── cdp_transceiver_bladerf.py
│   ├── cdp_receiver_rtlsdr.grc        # RTL-SDR Receiver
│   ├── cdp_receiver_rtlsdr.py
│   ├── cdp_transceiver_multi_hardware.grc # Universal Multi-Hardware GRC
│   ├── optimize_hardware_sdr.py       # Live SDR Hardware Optimizer (Pluto, BladeRF, RTL-SDR)
│   ├── sdr_blocks_helper.py           # Unified Hardware Source/Sink Block Constructor (Explicit Disconnect Error)
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
│   ├── optimize_original_ultra_fine.py# Milliradian-precision optimizer (0.005..1.000 full range)
│   ├── plot_comprehensive_charts.py   # Multi-slice plotting engine
│   └── results/                       # 15,484-trial JSON, CSV, SVG charts, and comprehensive_dashboard.html
├── correlation_estimator/             # Core DSP helpers for training sequences & corr_est
│   └── corr_est_helper.py
├── optimization/                      # Master Ultra-Deep High-Resolution Optimizer (15,484 Trials)
│   ├── deep_cartesian_sweep.py        # High-density Cartesian grid sweeper (0.005..1.000 full range)
│   ├── plot_deep_analysis.py          # Multi-slice parametric plotting engine
│   ├── run_ultra_deep_optimization.py # Master CLI runner
│   └── results/                       # Multi-slice SVGs, heatmaps, deep_sweep_results.csv, and deep_dashboard.html
└── README.md
```

---

## Pinpointed Optimal Values Summary (0.005 to 1.000 rad/sym Full Range)

| Parameter | BPSK ($y \cdot y'$ TED) | QPSK ($y \cdot y'$ TED) | Safe Operating Range | DSP Function & Rationale |
|:---|:---:|:---:|:---:|:---|
| **Timing Error Detector (TED)** | `TED_SIGNAL_TIMES_SLOPE_ML` | `TED_SIGNAL_TIMES_SLOPE_ML` | — | Signal times derivative ($y \cdot y'$) maximum likelihood timing recovery. |
| **FLL Band-Edge Loop BW** | **`0.0314 rad/sym`** ($2\pi \times 0.005$) | **`0.0314 rad/sym`** | `0.005 .. 1.000` | Wideband carrier acquisition up to $\pm 2.5\%$ sample rate. |
| **Costas Loop BW** | **`0.0628 rad/sym`** ($2\pi \times 0.010$) | **`0.0628 rad/sym`** | `0.005 .. 1.000` | Fine carrier phase and residual frequency lock. |
| **Symbol Sync Loop BW** | **`0.0250 rad/sym`** | **`0.1150 rad/sym`** | `0.005 .. 1.000` | High-Q jitter suppression and timing drift recovery. |
| **Correlation Estimator** | Enabled (Tag `'corr_est'`) | Enabled (Tag `'corr_est'`) | — | Symbol timing sync & linear equalizer training trigger. |
| **Preamble Length** | **`16` to `32` Bytes** (`0x55`) | **`32` Bytes** (`0x33, 0xCC`) | `16 .. 64` Bytes | Alternating 2-bit symbol pattern provides clock transitions for QPSK. |
| **Average PDR** | **90.0% to 95.0%** | **90.0% to 95.0%** | — | 100% CRC integrity across severe carrier offsets and noise. |

---

## Interactive Dashboards & Plotting Tools

### 1. Standalone Dynamic Web Dashboard
Launch the web server and open the browser:
```bash
python3 PHY2/run_dashboard.py
```
- **Live Dynamic Plotter**: BER vs Symbol Sync with Costas Multi-Lines, FLL range slider ($0.005 \dots 1.000\text{ rad/sym}$), Costas range slider & line checkboxes.
- **2D Correlation Heatmap**: Costas vs Symbol Sync stability field with Log10(BER) and PDR % color gradient modes and FLL slice selector.
- **Full CSV Matrix**: 15,484 records with instant search, multi-range filtering, raw CSV text view, and one-click CSV export.

### 2. Terminal Dynamic REPL Plotter
Run the interactive terminal plotter:
```bash
python3 PHY2/interactive_plotter.py
```
Type commands dynamically:
- `fll 0.0314`: Sets FLL Band-Edge loop bandwidth across $0.005 \dots 1.000\text{ rad/sym}$.
- `costas 0.01 0.25`: Sets Costas loop bandwidth range.
- `costas_lines 0.010,0.035,0.0628,0.135,0.250`: Sets exact Costas line values.
- `mod BPSK` or `mod QPSK`: Switches modulation scheme.
- `plot`: Draws the dynamic multi-line curve.
- `heatmap ber` or `heatmap pdr`: Displays the 2D parametric stability surface.
- `csv 20`: Views CSV records.
- `export my_data.csv`: Exports filtered dataset to CSV.
- `browser`: Launches the web dashboard.

---

## Running Automated Validation Tests

```bash
# 1. Run all 7 stages + adapted transceiver in simulation:
python3 PHY2/tests/run_all_tests.py --hw sim --mod ALL

# 2. Run on physical Adalm-Pluto SDR (Throws RuntimeError if not connected):
python3 PHY2/tests/run_all_tests.py --hw pluto --uri ip:192.168.2.1 --mod ALL

# 3. Run full-range parameter sweep (0.005..1.000 rad/sym across FLL, Costas, SymSync):
python3 PHY2/optimization/run_ultra_deep_optimization.py
```
