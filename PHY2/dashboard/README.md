# Physical Layer Simulation & Optimization Dashboard

This directory contains the web dashboards for exploring parameter sweeps and optimization results across BPSK and QPSK schemes.

## Files

- `build_dashboard.py`: Compiles the simulation dataset into standalone HTML and JS data files.
- `software_dashboard.html`: Interactive multi-line plots, correlation heatmaps, point inspector, and data table for software simulations.
- `hardware_dashboard.html`: Calibrated dashboard view for physical SDR hardware profiles (Adalm-Pluto, bladeRF, RTL-SDR).
- `software_data.js` / `hardware_data.js`: Serialized data files loaded by the dashboards.

## Usage

To rebuild the dashboards from the latest sweep results:
```bash
python3 build_dashboard.py
```

To launch the dashboard server in your browser:
```bash
python3 ../run_dashboard.py
```
