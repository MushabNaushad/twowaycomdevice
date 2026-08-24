# PHY2 - Physical Layer Automated Optimization Suite

## Overview
The `optimization/` suite provides non-GRC, headless, high-throughput DSP simulation and empirical parameter optimization for the PHY2 transceiver.

## Components
- `param_sweep.py`: Headless multidimensional parameter sweeper testing:
  - FLL Band-Edge Loop Bandwidth ($0.002$ to $0.080\text{ rad/sym}$)
  - Costas Loop Bandwidth ($0.010$ to $0.160\text{ rad/sym}$)
  - Symbol Synchronizer Loop Bandwidth ($0.010$ to $0.140\text{ rad/sym}$)
  - Preamble Length ($8$ to $64\text{ bytes}$)
  - AWGN Channel Noise Voltage ($V_n = 0.0$ to $0.8$)
  - Carrier Frequency Offsets ($\Delta f = -0.035$ to $+0.035$)
  - Clock Drift ($\epsilon = 0.9995$ to $1.0005$)
- `ber_calculator.py`: Precision Bit Error Rate (BER), cross-correlation lag alignment, and Packet Delivery Ratio (PDR) calculator.
- `plot_results.py`: Standalone SVG line/scatter plotter and interactive HTML dashboard generator.
- `run_auto_optimization.py`: Master orchestrator running the parameter grid, determining Pareto-optimal values, and generating visual artifacts.

## Usage
Run the complete automated parameter optimization suite:
```bash
python3 run_auto_optimization.py
```

## Generated Outputs (`results/`)
- `optimal_parameters.json`: Machine-readable optimal configuration.
- `sweep_results.json` & `sweep_results.csv`: Raw measurement matrix.
- `chart_01_ber_waterfall.svg`: BER vs AWGN Noise Voltage with theoretical comparison.
- `chart_02_fll_bandwidth.svg`: Capture range vs FLL loop bandwidth.
- `chart_03_costas_bandwidth.svg`: BER vs Costas loop bandwidth.
- `chart_04_preamble_length.svg`: PDR % vs preamble length.
- `dashboard.html`: Interactive browser dashboard embedding all charts and tables.
