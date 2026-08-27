# PHY2 - Master Interactive Dashboard & Analytics Explorer

## Overview
The **PHY2 Interactive Dashboard** is a 100% standalone, zero-external-dependency web application for exploring physical layer parameter sensitivity, bit error rates (BER), packet delivery ratios (PDR), and 2D parametric stability surfaces.

It embeds **15,484 high-density empirical simulation trials** spanning the full **0.005 to 1.000 rad/sym** range across:
- **Frequency Lock Loop (FLL) Band-Edge Bandwidth** ($0.005 \dots 1.000\text{ rad/sym}$)
- **Costas Loop Bandwidth** ($0.005 \dots 1.000\text{ rad/sym}$)
- **Symbol Synchronizer Loop Bandwidth** ($y \cdot y'$ ML TED, $0.005 \dots 1.000\text{ rad/sym}$)
- **Modulation Schemes**: BPSK and QPSK

---

## How to Launch

### Method 1: Master Launcher (Recommended)
```bash
python3 PHY2/run_dashboard.py
```
This script starts a lightweight local Python HTTP server on port 8080 (or the next available port) and automatically opens `http://127.0.0.1:8080/index.html` in your default browser.

### Method 2: Direct File Open
You can also open `PHY2/dashboard/index.html` directly in any modern browser (Chrome, Firefox, Edge, Safari):
```bash
xdg-open PHY2/dashboard/index.html
```

---

## Key Features

1. **Dynamic HTML5 Canvas Multi-Line Graph (BER vs Symbol Sync)**:
   - **FLL Band-Edge Selector**: Change the FLL bandwidth slice ($0.005 \dots 1.000\text{ rad/sym}$) via dropdown or range slider to dynamically recalculate and redraw all Costas curves in real time.
   - **Costas Multi-Line Curves**: Different colored curves for each Costas loop bandwidth.
   - **Costas Range Slider & Checkbox Pills**: Selectively toggle or filter Costas curves.
   - **Smooth Spline Curves & Data Points**: Displays all evaluation points with interactive crosshair tooltips.
2. **Interactive 2D Correlation Heatmap**:
   - 2D parametric stability surface (Costas BW vs SymSync BW).
   - Metric gradient toggle: **Log10(BER)** or **PDR (%)**.
   - FLL slice selector covering $0.005 \dots 1.000\text{ rad/sym}$.
3. **Filterable CSV Matrix Explorer**:
   - Real-time search box matching across all parameters.
   - Range sliders for FLL BW, Costas BW, SymSync BW, and Min PDR.
   - Collapsible Raw CSV text viewer.
   - **Export Filtered CSV** button for one-click downloading.
