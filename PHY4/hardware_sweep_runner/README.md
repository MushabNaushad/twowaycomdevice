# PHY4 Hardware Sweep Runner & Parameter Optimizer

This folder contains the automated headless calibration engine designed to sweep the **top 50,000 / 10,000 / 1,000 lowest-BER candidate parameter combinations** directly across live physical SDR hardware to pinpoint optimal real-world parameters.

## Hardware Roles
- **Transmitter**: Analog Devices Adalm-Pluto SDR (`--tx-hw pluto`, URI: `ip:192.168.1.10`)
- **Receiver**: Nuand bladeRF SDR (`--rx-hw bladerf`, `driver=bladerf`)
- **Supported Targets**: Pluto, bladeRF, RTL-SDR, and Simulation loopback.

## Datasets Included
- `top_50000_low_ber_candidates.json`: The top 50,000 prioritized DSP candidates extracted from extensive sweeps.
- `top_50000_low_ber_candidates.csv`: CSV table of candidate parameter combinations.

## How to Run

### 1. Fast Calibration (Top 1,000 Candidates)
```bash
python3 optimize_hardware.py --tx-hw pluto --rx-hw bladerf --uri ip:192.168.1.10 --top-n 1000
```

### 2. Standard Sweep (Top 10,000 Candidates)
```bash
python3 optimize_hardware.py --tx-hw pluto --rx-hw bladerf --uri ip:192.168.1.10 --top-n 10000
```

### 3. Full Exhaustive Sweep (All 50,000 Candidates)
```bash
python3 optimize_hardware.py --tx-hw pluto --rx-hw bladerf --uri ip:192.168.1.10 --top-n 50000
```

### 4. Quick Simulation / Loopback Verification
To verify without physical SDR hardware connected:
```bash
python3 optimize_hardware.py --tx-hw sim --rx-hw sim --top-n 100
```

## Output Results
- `results/hardware_optimization_results.json`: Complete trial-by-trial logs with measured PDR and BER.
- `results/hardware_optimization_results.csv`: Spreadsheet-ready result matrix.
- `results/optimal_hardware_parameters.json`: Automatically pinpointed optimal parameters for BPSK and QPSK.
