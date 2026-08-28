# Hardware SDR Live Optimization Dashboard

This directory contains the standalone web dashboard for visualizing physical SDR hardware live optimization trials.

## Files

- `build_dashboard.py`: Generates the HTML5 dashboard and external data file from live hardware test records.
- `hardware_dashboard.html`: Live hardware performance dashboard with BER vs Symbol Sync curves, 2D stability heatmaps, and trial table.
- `hardware_data.js`: Curated dataset generated from `../results/hardware_optimization_results.json`.

## Usage

To rebuild the dashboard after hardware runs:
```bash
python3 build_dashboard.py
```

To view the dashboard:
```bash
python3 ../run_dashboard.py
```
