#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Interactive Matplotlib Plotter & Dynamic Parameter Explorer
Provides:
1. Full Matplotlib GUI with Interactive Sliders, Radio Buttons, and Checkboxes:
   - FLL Band-Edge Loop Bandwidth slider (0.005 to 1.000 rad/sym) with real-time value display.
   - Costas Loop Bandwidth range slider & line selection checkboxes.
   - Modulation selection (BPSK / QPSK).
   - Side-by-side Dual Visualizations:
     * Subplot 1: BER vs Symbol Synchronizer Loop Bandwidth with Costas Multi-Lines.
     * Subplot 2: 2D Parametric Stability Heatmap (Costas vs Symbol Sync) at current FLL Band-Edge slice.
2. Terminal-Controlled Dynamic Matplotlib Mode:
   - Interactive REPL in terminal that updates the open Matplotlib GUI window in real time.
3. Headless / Save-to-File Mode for remote execution.
"""

import sys
import os
import json
import math
import argparse

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "optimization/results/deep_sweep_results.json"))
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "adapted_original/results/ultra_fine_sweep_results.json"))

def load_data():
    if not os.path.exists(DATA_PATH):
        print(f"[ERROR] Dataset not found at: {DATA_PATH}")
        print("Please run 'python3 PHY2/optimization/run_ultra_deep_optimization.py' to generate the dataset.")
        sys.exit(1)
    with open(DATA_PATH, "r") as f:
        return json.load(f)

# ANSI Colors for Terminal
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_MAGENTA = "\033[95m"
C_RED = "\033[91m"
C_BLUE = "\033[94m"
C_WHITE = "\033[97m"

class MatplotlibInteractiveExplorer:
    def __init__(self, records):
        self.records = records
        self.all_fll = sorted(list(set(r['fll_bw'] for r in records)))
        self.all_costas = sorted(list(set(r['costas_bw'] for r in records)))
        self.all_sym = sorted(list(set(r['sym_bw'] for r in records)))

        self.current_mod = 'BPSK'
        self.current_fll = 0.0314 if 0.0314 in self.all_fll else self.all_fll[len(self.all_fll)//2]
        self.current_costas_max = 1.000
        self.default_costas = [0.001, 0.005, 0.010, 0.025, 0.0628, 0.135, 0.250, 0.500, 0.850, 1.000]
        self.active_costas = [c for c in self.all_costas if any(abs(c - d) < 0.006 for d in self.default_costas)]
        self.heatmap_metric = 'ber'

        self.fig = None
        self.ax_curve = None
        self.ax_heatmap = None

    def find_closest_fll(self, val):
        return min(self.all_fll, key=lambda f: abs(f - val))

    def get_curve_series(self, mod, fll_val, costas_list):
        closest_fll = self.find_closest_fll(fll_val)
        series = []
        for cbw in costas_list:
            pts = []
            for sbw in self.all_sym:
                matches = [
                    r for r in self.records
                    if r['mod_type'] == mod
                    and abs(r['fll_bw'] - closest_fll) < 0.006
                    and abs(r['costas_bw'] - cbw) < 0.006
                    and abs(r['sym_bw'] - sbw) < 0.006
                ]
                if matches:
                    avg_ber = sum(r['ber'] for r in matches) / len(matches)
                    avg_pdr = sum(r['pdr'] for r in matches) / len(matches)
                    pts.append((sbw, max(avg_ber, 1e-4), avg_pdr))
            if pts:
                series.append((cbw, pts))
        return closest_fll, series

    def get_heatmap_matrix(self, mod, fll_val, metric='ber'):
        closest_fll = self.find_closest_fll(fll_val)
        grid = []
        for cbw in self.all_costas:
            row = []
            for sbw in self.all_sym:
                matches = [
                    r for r in self.records
                    if r['mod_type'] == mod
                    and abs(r['fll_bw'] - closest_fll) < 0.006
                    and abs(r['costas_bw'] - cbw) < 0.006
                    and abs(r['sym_bw'] - sbw) < 0.006
                ]
                if matches:
                    val = matches[0]['ber'] if metric == 'ber' else matches[0]['pdr']
                    row.append(max(val, 1e-4) if metric == 'ber' else val)
                else:
                    row.append(1.0 if metric == 'ber' else 0.0)
            grid.append(row)
        return closest_fll, grid

    def update_plots(self):
        if not self.fig:
            return

        import matplotlib.pyplot as plt
        import numpy as np

        # 1. Update Curve Subplot
        self.ax_curve.clear()
        closest_fll, series = self.get_curve_series(self.current_mod, self.current_fll, self.active_costas)

        colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(series))))
        markers = ['o', 's', '^', 'v', 'D', 'p', '*', 'h', 'x']

        for idx, (cbw, pts) in enumerate(series):
            x_vals = [p[0] for p in pts]
            y_vals = [p[1] for p in pts]
            color = colors[idx % len(colors)]
            marker = markers[idx % len(markers)]
            self.ax_curve.semilogy(
                x_vals, y_vals,
                label=f'Costas = {cbw:.4f} rad/sym',
                color=color,
                marker=marker,
                markersize=5,
                linewidth=1.8,
                alpha=0.9
            )

        self.ax_curve.set_title(
            f"{self.current_mod} (y·y' TED): BER vs Symbol Sync Loop BW\n"
            f"FLL Band-Edge Loop Bandwidth = {closest_fll:.4f} rad/sym",
            fontsize=11, fontweight='bold', color='#0f172a', pad=10
        )
        self.ax_curve.set_xlabel("Symbol Synchronizer Loop Bandwidth (rad/sym)", fontsize=10, fontweight='semibold')
        self.ax_curve.set_ylabel("Bit Error Rate (BER) - Log Scale", fontsize=10, fontweight='semibold')
        self.ax_curve.set_ylim(1e-4, 1.0)
        self.ax_curve.set_xlim(0.0, 1.0)
        self.ax_curve.grid(True, which='both', linestyle='--', alpha=0.5)
        self.ax_curve.legend(loc='upper right', fontsize=8, framealpha=0.9)

        # 2. Update Heatmap Subplot
        self.ax_heatmap.clear()
        _, grid = self.get_heatmap_matrix(self.current_mod, self.current_fll, self.heatmap_metric)
        grid_arr = np.array(grid)

        if self.heatmap_metric == 'ber':
            display_data = np.log10(np.clip(grid_arr, 1e-4, 1.0))
            cmap = 'viridis_r'
            cb_label = 'Log10(BER)'
            vmin, vmax = -4, 0
        else:
            display_data = grid_arr
            cmap = 'RdYlGn'
            cb_label = 'Packet Delivery Ratio (%)'
            vmin, vmax = 0, 100

        im = self.ax_heatmap.imshow(
            display_data,
            origin='lower',
            aspect='auto',
            extent=[min(self.all_sym), max(self.all_sym), min(self.all_costas), max(self.all_costas)],
            cmap=cmap,
            vmin=vmin,
            vmax=vmax
        )

        self.ax_heatmap.set_title(
            f"2D Parametric Stability Heatmap ({self.current_mod})\n"
            f"FLL Band-Edge Slice = {closest_fll:.4f} rad/sym",
            fontsize=11, fontweight='bold', color='#0f172a', pad=10
        )
        self.ax_heatmap.set_xlabel("Symbol Sync Loop Bandwidth (rad/sym)", fontsize=10, fontweight='semibold')
        self.ax_heatmap.set_ylabel("Costas Loop Bandwidth (rad/sym)", fontsize=10, fontweight='semibold')

        self.fig.canvas.draw_idle()

    def launch_gui(self):
        try:
            import matplotlib
            import matplotlib.pyplot as plt
            from matplotlib.widgets import Slider, RadioButtons, Button, CheckButtons
        except ImportError:
            print(f"{C_RED}[ERROR] Matplotlib is not installed.{C_RESET}")
            print("To run the matplotlib GUI, install it on your target machine: pip install matplotlib")
            return False

        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
        self.fig = plt.figure(figsize=(15, 8.5))
        self.fig.canvas.manager.set_window_title("PHY2 Interactive Matplotlib Dynamic Plotter & Parameter Explorer")

        # Subplots
        self.ax_curve = self.fig.add_axes([0.07, 0.38, 0.42, 0.54])
        self.ax_heatmap = self.fig.add_axes([0.55, 0.38, 0.40, 0.54])

        # Interactive Widgets Axes
        ax_fll_slider = self.fig.add_axes([0.15, 0.22, 0.70, 0.03])
        ax_costas_slider = self.fig.add_axes([0.15, 0.16, 0.70, 0.03])
        ax_mod_radio = self.fig.add_axes([0.07, 0.02, 0.12, 0.10])
        ax_metric_radio = self.fig.add_axes([0.22, 0.02, 0.16, 0.10])
        ax_btn_reset = self.fig.add_axes([0.42, 0.04, 0.12, 0.06])
        ax_btn_save = self.fig.add_axes([0.56, 0.04, 0.12, 0.06])
        ax_btn_dash = self.fig.add_axes([0.70, 0.04, 0.14, 0.06])

        # Widgets
        self.slider_fll = Slider(
            ax=ax_fll_slider,
            label='FLL Band-Edge BW: ',
            valmin=0.001,
            valmax=1.000,
            valinit=self.current_fll,
            valstep=0.001,
            color='#38bdf8'
        )

        self.slider_costas = Slider(
            ax=ax_costas_slider,
            label='Costas BW Max: ',
            valmin=0.001,
            valmax=1.000,
            valinit=1.000,
            valstep=0.001,
            color='#22c55e'
        )

        self.radio_mod = RadioButtons(ax_mod_radio, ('BPSK', 'QPSK'), active=0)
        self.radio_metric = RadioButtons(ax_metric_radio, ('BER (Log Scale)', 'PDR (%)'), active=0)
        self.btn_reset = Button(ax_btn_reset, 'Reset Core Lines', color='#e2e8f0', hovercolor='#cbd5e1')
        self.btn_save = Button(ax_btn_save, 'Save PNG Plot', color='#e2e8f0', hovercolor='#cbd5e1')
        self.btn_dash = Button(ax_btn_dash, 'Launch Web Dashboard', color='#38bdf8', hovercolor='#0284c7')

        # Callbacks
        def on_fll_change(val):
            self.current_fll = self.find_closest_fll(val)
            self.update_plots()

        def on_costas_change(val):
            self.current_costas_max = val
            self.active_costas = [c for c in self.all_costas if c <= val + 1e-4]
            self.update_plots()

        def on_mod_change(label):
            self.current_mod = label
            self.update_plots()

        def on_metric_change(label):
            self.heatmap_metric = 'ber' if 'BER' in label else 'pdr'
            self.update_plots()

        def on_reset(event):
            self.active_costas = [c for c in self.all_costas if any(abs(c - d) < 0.006 for d in self.default_costas)]
            self.slider_costas.set_val(1.000)
            self.update_plots()

        def on_save(event):
            fn = f"phy2_plot_{self.current_mod}_fll_{self.current_fll:.4f}.png"
            self.fig.savefig(fn, dpi=300)
            print(f"{C_GREEN}[OK] Saved high-resolution plot to {fn}{C_RESET}")

        def on_dash(event):
            import subprocess
            html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dashboard/index.html"))
            subprocess.Popen(["xdg-open", html_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.slider_fll.on_changed(on_fll_change)
        self.slider_costas.on_changed(on_costas_change)
        self.radio_mod.on_clicked(on_mod_change)
        self.radio_metric.on_clicked(on_metric_change)
        self.btn_reset.on_clicked(on_reset)
        self.btn_save.on_clicked(on_save)
        self.btn_dash.on_clicked(on_dash)

        self.update_plots()
        plt.show()
        return True

    def run_terminal_repl(self):
        print(f"\n{C_BOLD}{C_CYAN}================================================================================{C_RESET}")
        print(f"      {C_BOLD}PHY2 MATPLOTLIB INTERACTIVE TERMINAL CONTROLLER & ANALYZER{C_RESET}        ")
        print(f"{C_BOLD}{C_CYAN}================================================================================{C_RESET}")
        print(f"Loaded {len(self.records):,} trials across 0.005..1.000 rad/sym full bandwidth range.")
        print(f"Available FLL Loop Bandwidth Values: {self.all_fll}")
        print("\nTerminal Commands:")
        print("  mod [BPSK|QPSK]                     : Switch modulation scheme")
        print("  fll <value>                         : Set FLL Band-Edge Loop BW (0.005..1.000)")
        print("  costas <min> <max>                  : Set Costas Loop BW range (0.005..1.000)")
        print("  costas_lines <c1,c2,...>            : Set exact Costas line values")
        print("  gui                                 : Open interactive Matplotlib GUI window with sliders")
        print("  save [filename.png]                 : Render and save high-resolution plot to PNG")
        print("  heatmap [ber|pdr]                   : Switch heatmap metric")
        print("  csv [limit]                         : View CSV records in terminal")
        print("  export [filename.csv]               : Export filtered records to CSV")
        print("  browser                             : Open zero-dependency web dashboard")
        print("  help / quit                         : Display help or exit")
        print("--------------------------------------------------------------------------------")

        while True:
            try:
                line = input(f"{C_BOLD}{C_CYAN}PHY2 ({self.current_mod} | FLL={self.current_fll:.4f} rad/sym) > {C_RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting interactive plotter.")
                break

            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()

            if cmd in ['q', 'quit', 'exit']:
                print("Exiting interactive plotter.")
                break

            elif cmd == 'gui':
                print(f"{C_GREEN}-> Launching Matplotlib Interactive GUI Window...{C_RESET}")
                self.launch_gui()

            elif cmd == 'mod':
                if len(parts) > 1 and parts[1].upper() in ['BPSK', 'QPSK']:
                    self.current_mod = parts[1].upper()
                    print(f"{C_GREEN}-> Modulation set to: {self.current_mod}{C_RESET}")
                else:
                    print(f"{C_RED}Usage: mod [BPSK|QPSK]{C_RESET}")

            elif cmd == 'fll':
                if len(parts) > 1:
                    try:
                        val = float(parts[1])
                        self.current_fll = self.find_closest_fll(val)
                        print(f"{C_GREEN}-> FLL Band-Edge Loop BW set to: {self.current_fll:.4f} rad/sym{C_RESET}")
                    except ValueError:
                        print(f"{C_RED}Invalid float for FLL.{C_RESET}")
                else:
                    print(f"Current FLL Band-Edge Loop BW: {self.current_fll:.4f} rad/sym")

            elif cmd == 'costas':
                if len(parts) >= 3:
                    try:
                        c_min, c_max = float(parts[1]), float(parts[2])
                        self.active_costas = [c for c in self.all_costas if c_min - 1e-4 <= c <= c_max + 1e-4]
                        print(f"{C_GREEN}-> Selected {len(self.active_costas)} Costas lines between {c_min:.4f} and {c_max:.4f}{C_RESET}")
                    except ValueError:
                        print(f"{C_RED}Usage: costas <min> <max>{C_RESET}")

            elif cmd == 'costas_lines':
                if len(parts) > 1:
                    try:
                        vals = [float(x.strip()) for x in parts[1].split(',')]
                        self.active_costas = vals
                        print(f"{C_GREEN}-> Set custom Costas lines: {self.active_costas}{C_RESET}")
                    except ValueError:
                        print(f"{C_RED}Usage: costas_lines 0.010,0.035,0.0628,0.135{C_RESET}")

            elif cmd == 'save':
                fn = parts[1] if len(parts) > 1 else f"phy2_{self.current_mod}_fll_{self.current_fll:.4f}.png"
                self.save_figure(fn)

            elif cmd == 'csv':
                limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 15
                print(f"\n{C_BOLD}Mod     FLL_BW  Costas_BW SymSync_BW Preamble Noise  Offset Drift    Profile  PDR%   BER{C_RESET}")
                print("─" * 86)
                matches = [r for r in self.records if r['mod_type'] == self.current_mod and abs(r['fll_bw'] - self.current_fll) < 0.006]
                for r in matches[:limit]:
                    print(f"{r['mod_type']:<7} {r['fll_bw']:<7.4f} {r['costas_bw']:<9.4f} {r['sym_bw']:<10.4f} {r['preamble_size']:<8} {r['noise_volt']:<6.2f} {r['freq_offset']:<7.3f} {r['time_offset']:<8.6f} {r['platform_mode']:<8} {r['pdr']:<6.1f} {r['ber']:.2e}")
                print(f"─" * 86)
                print(f"Showing {min(limit, len(matches))} of {len(matches)} matching rows.\n")

            elif cmd == 'export':
                fn = parts[1] if len(parts) > 1 else "phy2_filtered_export.csv"
                self.export_csv(fn)

            elif cmd in ['browser', 'dash', 'dashboard']:
                import subprocess
                html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dashboard/index.html"))
                print(f"{C_GREEN}-> Opening interactive dashboard: {html_path}{C_RESET}")
                subprocess.Popen(["xdg-open", html_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            else:
                print(f"{C_RED}Unknown command '{cmd}'. Type 'help' for command list or 'gui' to launch GUI.{C_RESET}")

    def save_figure(self, filename="phy2_plot.png"):
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

            closest_fll, series = self.get_curve_series(self.current_mod, self.current_fll, self.active_costas)
            colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(series))))
            for idx, (cbw, pts) in enumerate(series):
                ax1.semilogy([p[0] for p in pts], [p[1] for p in pts], label=f'Costas = {cbw:.4f}', color=colors[idx % len(colors)], linewidth=2)

            ax1.set_title(f"{self.current_mod} BER vs Symbol Sync Loop BW\nFLL Band-Edge Loop BW = {closest_fll:.4f} rad/sym", fontweight='bold')
            ax1.set_xlabel("Symbol Sync Loop BW (rad/sym)")
            ax1.set_ylabel("BER (Log Scale)")
            ax1.set_ylim(1e-4, 1.0)
            ax1.set_xlim(0.0, 1.0)
            ax1.grid(True, which='both', linestyle='--')
            ax1.legend(loc='upper right', fontsize=8)

            _, grid = self.get_heatmap_matrix(self.current_mod, self.current_fll, 'ber')
            im = ax2.imshow(np.log10(np.clip(grid, 1e-4, 1.0)), origin='lower', aspect='auto', extent=[0.0, 1.0, 0.0, 1.0], cmap='viridis_r', vmin=-4, vmax=0)
            ax2.set_title(f"2D Parametric Heatmap ({self.current_mod})\nFLL Band-Edge Slice = {closest_fll:.4f} rad/sym", fontweight='bold')
            ax2.set_xlabel("Symbol Sync Loop BW (rad/sym)")
            ax2.set_ylabel("Costas Loop BW (rad/sym)")
            fig.colorbar(im, ax=ax2, label="Log10(BER)")

            fig.tight_layout()
            fig.savefig(filename, dpi=300)
            plt.close(fig)
            print(f"{C_GREEN}[OK] Saved high-resolution figure to {filename}{C_RESET}")
        except Exception as e:
            print(f"{C_RED}[ERROR] Failed to save figure: {e}{C_RESET}")

    def export_csv(self, filename="phy2_filtered_data.csv"):
        with open(filename, "w") as f:
            f.write("Modulation,FLL_Band_Edge_BW,Costas_BW,SymSync_BW,Preamble_Size,Noise_Volt,Freq_Offset,Time_Offset,Platform,PDR,BER\n")
            for r in self.records:
                f.write(f"{r['mod_type']},{r['fll_bw']},{r['costas_bw']},{r['sym_bw']},{r['preamble_size']},{r['noise_volt']},{r['freq_offset']},{r['time_offset']},{r['platform_mode']},{r['pdr']},{r['ber']}\n")
        print(f"{C_GREEN}[OK] Exported {len(self.records):,} records to {filename}{C_RESET}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Matplotlib Interactive Plotter & Analyzer")
    parser.add_argument('--gui', action='store_true', help="Launch Matplotlib Interactive GUI with Sliders")
    parser.add_argument('--mod', type=str, default='BPSK', choices=['BPSK', 'QPSK'])
    parser.add_argument('--fll', type=float, default=0.0314, help="FLL Band-Edge Loop BW")
    parser.add_argument('--costas-min', type=float, default=0.001, help="Costas BW Min")
    parser.add_argument('--costas-max', type=float, default=1.000, help="Costas BW Max")
    parser.add_argument('--save', type=str, default=None, help="Save figure to file and exit")
    parser.add_argument('--export-csv', type=str, default=None, help="Export dataset to CSV file")
    args = parser.parse_args()

    records = load_data()
    explorer = MatplotlibInteractiveExplorer(records)
    explorer.current_mod = args.mod
    explorer.current_fll = explorer.find_closest_fll(args.fll)
    explorer.active_costas = [c for c in explorer.all_costas if args.costas_min - 1e-4 <= c <= args.costas_max + 1e-4]

    if args.save:
        explorer.save_figure(args.save)
    elif args.export_csv:
        explorer.export_csv(args.export_csv)
    elif args.gui:
        explorer.launch_gui()
    else:
        # Default to interactive terminal REPL which can also trigger GUI
        explorer.run_terminal_repl()
