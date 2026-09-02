# PHY4: Dual-Mode Physical Layer (Pluto TX & BladeRF RX)

PHY4 provides a complete, production-ready SDR physical layer suite tailored for **Pluto SDR Transmission** and **BladeRF SDR Reception**, featuring parallel **BPSK and QPSK** modulation, **Correlation Estimator frame sync**, and **Linear Adaptive Equalizer**.

---

## Directory Organization

```
PHY4/
├── gui_flowgraph/             # [Folder 1] Purely Interactive GUI Flowgraph (No Headless Scripts)
│   ├── cdp_transceiver_pluto_bladerf.grc  # Complete GRC Flowgraph file
│   ├── cdp_transceiver_pluto_bladerf.py   # Compiled Qt GUI Python program
│   └── README.md                          # Documentation & usage guide
│
├── hardware_sweep_runner/     # [Folder 2] Headless Hardware Optimization & Sweep Engine
│   ├── optimize_hardware.py               # Live hardware sweeper for 50k / 10k / 1k trials
│   ├── run_hardware_calibration.py        # Shortcut calibration runner
│   ├── sdr_hardware_helper.py             # SDR hardware TX/RX driver wrapper
│   ├── top_50000_low_ber_candidates.json  # Top 50,000 prioritized candidates
│   ├── top_50000_low_ber_candidates.csv   # Top 50,000 candidate spreadsheet
│   ├── results/                           # Target directory for hardware sweep outputs
│   └── README.md                          # Hardware optimizer documentation
│
├── optimal_parameters.txt     # Summary of optimal DSP parameters for BPSK & QPSK
├── optimal_parameters.json    # JSON formatted optimal parameter specifications
├── top_50000_low_ber_candidates.json # Prioritized candidates dataset
└── top_50000_low_ber_candidates.csv  # Spreadsheet candidate dataset
```

---

## Architecture Highlights
1. **Transmitter**: Pluto SDR (`iio_pluto_sink`) configured for URI `ip:192.168.1.10`.
2. **Receiver**: Nuand bladeRF (`soapy_bladerf_source`, `driver=bladerf`).
3. **All 3 Receivers in GRC**: BladeRF (Active), Adalm-Pluto (Present/Disabled), RTL-SDR (Present/Disabled).
4. **Parallel Modulations**: Simultaneous parallel branches for BPSK and QPSK.
5. **Advanced Synchronization & Equalization**:
   - $y \cdot y'$ Timing Error Detector (`TED_SIGNAL_TIMES_SLOPE_ML`) in Symbol Sync.
   - Frequency recovery with `digital.fll_band_edge_cc`.
   - Frame alignment via `digital.corr_est_cc`.
   - Multi-path compensation via 11-tap `digital.linear_equalizer` (CMA algorithm).
