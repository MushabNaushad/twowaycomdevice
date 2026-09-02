# PHY4 GUI Transceiver (Pluto TX & BladeRF RX)

This folder contains the graphical, interactive GNU Radio flowgraph configured for **Pluto SDR Transmitter** and **BladeRF SDR Receiver** with parallel **BPSK and QPSK** paths.

## Files
- `cdp_transceiver_pluto_bladerf.grc`: GNU Radio Companion (GRC) flowgraph file.
- `cdp_transceiver_pluto_bladerf.py`: Compiled Python script with full Qt GUI interface.

## Hardware Setup
- **Transmitter**: Analog Devices Adalm-Pluto SDR connected at `ip:192.168.1.10` (or local USB).
- **Receiver**: Nuand bladeRF SDR (USB 3.0, `driver=bladerf`).
- **Alternate Receivers**: Adalm-Pluto and RTL-SDR receiver blocks are included in the `.grc` file (simply toggle enable/disable in GRC to switch receiver hardware).

## Key DSP Features
- **Parallel Modulations**: Simultaneous support for BPSK and QPSK transmission & reception.
- **Timing Synchronization**: Symbol Synchronizer using timing error detector `TED_SIGNAL_TIMES_SLOPE_ML` ($y \cdot y'$ TED).
- **Channel Equalization**: Correlation Estimator (`digital.corr_est_cc`) coupled to an 11-tap Linear Adaptive Equalizer (`digital.linear_equalizer`) with CMA algorithm.
- **Packet Engine**: Access code correlator, 8-bit repack, CRC32 error validation, and PDU message debugging.

## How to Launch
To launch the interactive Qt GUI flowgraph:
```bash
python3 cdp_transceiver_pluto_bladerf.py
```
Or open in GNU Radio Companion:
```bash
gnuradio-companion cdp_transceiver_pluto_bladerf.grc
```
