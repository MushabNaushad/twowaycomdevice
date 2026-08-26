# PHY2 - Adapted Original Transceiver Suite

## Overview
This directory contains the user's original CDP software and hardware flowgraphs adapted with external parameter bindings to support both **BPSK** and **QPSK** modulation with full channel impairment simulation and parameter optimization.

---

## Files in this Directory
- `adapted_transceiver.py`: Parametric class wrapper exposing all loop bandwidths, modulation types, and channel impairment parameters.
- `run_original_test.py`: Standalone validation script testing BPSK and QPSK across channel noise, carrier frequency offsets, and clock drift.
- `optimize_original.py`: Parallel multi-core Cartesian grid optimizer evaluating hundreds of combinations on the original transceiver model.
- `cdp_transeciever_soft.grc`: Original software flowgraph.
- `cdp_transeciever_hw.grc`: Original hardware flowgraph.

---

## Usage
1. **Run test on original transceiver (BPSK & QPSK under impairments)**:
   ```bash
   python3 run_original_test.py
   ```
2. **Run full parameter optimization sweep**:
   ```bash
   python3 optimize_original.py
   ```
