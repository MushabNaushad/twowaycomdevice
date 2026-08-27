# PHY2 - Physical Layer Ultra-Deep Optimization Suite

## Overview
The `optimization/` suite provides non-GRC, headless, high-throughput DSP simulation and empirical parameter optimization across both Software Multipath channels and Hardware SDR Profiles over the full **0.005 to 1.000 rad/sym** range for FLL, Costas, and Symbol Sync loops.

---

## Components
- `deep_cartesian_sweep.py`: High-density multi-core Cartesian optimizer (15,484 trials) sweeping:
  - FLL Band-Edge Loop Bandwidth ($0.005$ to $1.000\text{ rad/sym}$)
  - Costas Loop Bandwidth ($0.005$ to $1.000\text{ rad/sym}$)
  - Symbol Synchronizer Loop Bandwidth ($0.005$ to $1.000\text{ rad/sym}$, $y \cdot y'$ TED)
  - Preamble Lengths ($16$ to $64\text{ bytes}$)
  - AWGN Noise Voltage ($V_n = 0.0$ to $0.50$)
  - Carrier Frequency Offsets ($\Delta f = -0.030$ to $+0.030$)
  - Clock Drift ($\epsilon = 0.9992$ to $1.0008$)
  - Channels: Software Multipath (with delay spread) & Hardware SDR Profiles
- `plot_deep_analysis.py`: Standalone SVG multi-slice parametric plotting engine and interactive HTML dashboard generator.
- `run_ultra_deep_optimization.py`: Master CLI orchestrator executing sweeps and dashboard generation.

---

## Usage
Run the ultra-deep optimization suite:
```bash
python3 PHY2/optimization/run_ultra_deep_optimization.py
```

---

## Generated Outputs (`results/`)
- `pinpoint_optimal_parameters.json`: Machine-readable optimal configurations for Software and Hardware profiles across BPSK and QPSK.
- `deep_sweep_results.json` & `deep_sweep_results.csv`: Complete raw measurement matrix of 15,484 trials.
- `chart_slice_01_fixed_fll_ber_vs_symsync_bpsk.svg` & `qpsk.svg`: BER vs Symbol Sync BW (0.005 to 1.000 range).
- `chart_slice_02_fixed_costas_ber_vs_fll_bpsk.svg` & `qpsk.svg`: BER vs FLL BW across Frequency Offsets.
- `chart_slice_03_fixed_symsync_pdr_vs_noise_bpsk.svg` & `qpsk.svg`: PDR (%) vs Noise across Preamble Lengths.
- `chart_slice_04_software_vs_hardware_comparison.svg`: Software vs Hardware profile direct BER comparison.
- `deep_dashboard.html`: Interactive browser dashboard embedding all multi-slice charts and optimal value matrices.
