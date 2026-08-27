#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Terminal Interactive Plotter & CLI Dynamic Analyzer
Allows users to dynamically change parameters from the terminal, plot BER vs Symbol Sync
with multiple Costas lines, customize FLL loop bandwidth, select Costas ranges, display 2D heatmaps,
and inspect/export CSV data directly from the terminal or in the browser!
"""

import sys
import os
import json
import math
import argparse
import subprocess

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "optimization/results/deep_sweep_results.json"))
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "adapted_original/results/ultra_fine_sweep_results.json"))

def load_data():
    if not os.path.exists(DATA_PATH):
        print(f"[ERROR] Dataset not found at: {DATA_PATH}")
        sys.exit(1)
    with open(DATA_PATH, "r") as f:
        return json.load(f)

# ANSI Colors for Rich Terminal Graphics
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_MAGENTA = "\033[95m"
C_RED = "\033[91m"
C_BLUE = "\033[94m"
C_WHITE = "\033[97m"

LINE_COLORS = [C_CYAN, C_GREEN, C_YELLOW, C_MAGENTA, C_RED, C_BLUE, C_WHITE]

def render_terminal_ascii_plot(mod_type, fll_bw, selected_costas, records, width=80, height=22):
    """
    Renders high-resolution ANSI multi-line terminal plot of Log10(BER) vs Symbol Sync Loop BW.
    """
    all_sym = sorted(list(set(r['sym_bw'] for r in records)))
    
    # Filter series
    series_data = []
    for idx, cbw in enumerate(selected_costas):
        pts = []
        for sbw in all_sym:
            matches = [
                r for r in records
                if r['mod_type'] == mod_type
                and abs(r['fll_bw'] - fll_bw) < 0.005
                and abs(r['costas_bw'] - cbw) < 0.005
                and abs(r['sym_bw'] - sbw) < 0.005
            ]
            if matches:
                avg_ber = sum(r['ber'] for r in matches) / len(matches)
                log_ber = math.log10(max(avg_ber, 1e-4))
                pts.append((sbw, log_ber))
        if pts:
            series_data.append((cbw, LINE_COLORS[idx % len(LINE_COLORS)], pts))
            
    if not series_data:
        print(f"{C_RED}[WARN] No matching simulation records for FLL={fll_bw:.4f} rad/sym with selected Costas values.{C_RESET}")
        return

    # Canvas buffer
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Range bounds
    y_min, y_max = -4.0, 0.0 # 10^-4 to 10^0
    x_min, x_max = 0.0, 1.0

    def map_x(x):
        return int(max(0, min(width - 1, ((x - x_min) / (x_max - x_min)) * (width - 1))))
    def map_y(y):
        return int(max(0, min(height - 1, ((y_max - y) / (y_max - y_min)) * (height - 1))))

    # Draw grid horizontal lines
    for exp in [-4, -3, -2, -1, 0]:
        y_idx = map_y(exp)
        for x in range(width):
            grid[y_idx][x] = '·'

    # Plot points and lines
    line_chars = ['●', '▲', '■', '◆', '★', '▼', '✦']
    for idx, (cbw, color, pts) in enumerate(series_data):
        char = line_chars[idx % len(line_chars)]
        for i in range(len(pts)):
            px = map_x(pts[i][0])
            py = map_y(pts[i][1])
            grid[py][px] = f"{color}{char}{C_RESET}"
            # Linear line interpolation between consecutive points
            if i > 0:
                prev_x = map_x(pts[i-1][0])
                prev_y = map_y(pts[i-1][1])
                dx = px - prev_x
                dy = py - prev_y
                steps = max(abs(dx), abs(dy))
                if steps > 1:
                    for s in range(1, steps):
                        ix = int(prev_x + s * dx / steps)
                        iy = int(prev_y + s * dy / steps)
                        if grid[iy][ix] == '·' or grid[iy][ix] == ' ':
                            grid[iy][ix] = f"{color}─{C_RESET}"

    # Print Header
    print(f"\n{C_BOLD}{C_CYAN}================================================================================{C_RESET}")
    print(f" {C_BOLD}{mod_type} (y·y' TED): BER vs Symbol Sync Loop Bandwidth{C_RESET}")
    print(f" {C_YELLOW}Fixed FLL Band-Edge Loop BW = {fll_bw:.4f} rad/sym{C_RESET} | {len(series_data)} Costas Lines")
    print(f"{C_BOLD}{C_CYAN}================================================================================{C_RESET}")

    # Print Grid with Y-axis labels
    for y in range(height):
        # Determine y-label
        y_val = y_max - (y / (height - 1)) * (y_max - y_min)
        if abs(y_val - round(y_val)) < 0.12:
            lbl = f"10^{int(round(y_val)):2d} │ "
        else:
            lbl = "      │ "
        row_str = "".join(grid[y])
        print(f"{C_WHITE}{lbl}{C_RESET}{row_str}")

    # X-axis
    print("      └─" + "─" * width)
    print("        " + f"0.0{' ' * (width // 2 - 4)}0.5{' ' * (width // 2 - 4)}1.0  (rad/sym)")
    print(f"        {C_BOLD}Symbol Synchronizer Loop Bandwidth (rad/sym){C_RESET}\n")

    # Legend
    print(f"{C_BOLD}Active Costas Loop Bandwidth Lines:{C_RESET}")
    for idx, (cbw, color, pts) in enumerate(series_data):
        char = line_chars[idx % len(line_chars)]
        min_ber = min(p[1] for p in pts)
        print(f"  {color}{char} Costas = {cbw:.4f} rad/sym{C_RESET} (Best BER: 10^{min_ber:.2f} = {10**min_ber:.2e})")
    print("--------------------------------------------------------------------------------\n")

def render_terminal_heatmap(mod_type, fll_bw, records, metric='ber'):
    """
    Renders a 2D ANSI color terminal heatmap of Costas vs Symbol Sync.
    """
    all_costas = sorted(list(set(r['costas_bw'] for r in records)), reverse=True)
    all_sym = sorted(list(set(r['sym_bw'] for r in records)))

    print(f"\n{C_BOLD}{C_MAGENTA}================================================================================{C_RESET}")
    print(f" {C_BOLD}2D PARAMETRIC HEATMAP ({mod_type}): Costas Loop BW vs Symbol Sync Loop BW{C_RESET}")
    print(f" Metric: {C_YELLOW}{metric.upper()}{C_RESET} | Fixed FLL Band-Edge BW = {fll_bw:.4f} rad/sym")
    print(f"{C_BOLD}{C_MAGENTA}================================================================================{C_RESET}")

    # Print top X header
    header = "Costas \\ Sym │ "
    for sbw in all_sym[::2]:
        header += f"{sbw:.2f} "
    print(header)
    print("─" * len(header))

    for cbw in all_costas[::2]:
        row_str = f" {cbw:10.4f} │ "
        for sbw in all_sym[::2]:
            matches = [
                r for r in records
                if r['mod_type'] == mod_type
                and abs(r['fll_bw'] - fll_bw) < 0.005
                and abs(r['costas_bw'] - cbw) < 0.005
                and abs(r['sym_bw'] - sbw) < 0.005
            ]
            if matches:
                if metric == 'ber':
                    val = matches[0]['ber']
                    if val <= 0.001:
                        c = f"{C_GREEN} █ {C_RESET}"
                    elif val <= 0.01:
                        c = f"{C_CYAN} ▓ {C_RESET}"
                    elif val <= 0.05:
                        c = f"{C_YELLOW} ▒ {C_RESET}"
                    else:
                        c = f"{C_RED} ░ {C_RESET}"
                else: # pdr
                    val = matches[0]['pdr']
                    if val >= 90:
                        c = f"{C_GREEN} █ {C_RESET}"
                    elif val >= 75:
                        c = f"{C_CYAN} ▓ {C_RESET}"
                    elif val >= 50:
                        c = f"{C_YELLOW} ▒ {C_RESET}"
                    else:
                        c = f"{C_RED} ░ {C_RESET}"
            else:
                c = " · "
            row_str += c
        print(row_str)
        
    print("─" * len(header))
    print(f"Legend: {C_GREEN}█ Best (BER≤10^-3 / PDR≥90%){C_RESET} | {C_CYAN}▓ Good{C_RESET} | {C_YELLOW}▒ Moderate{C_RESET} | {C_RED}░ High Loss{C_RESET}\n")

def export_terminal_csv(records, filename="phy2_terminal_export.csv"):
    with open(filename, "w") as f:
        f.write("Modulation,FLL_BW,Costas_BW,SymSync_BW,Preamble_Size,Noise_Volt,Freq_Offset,Time_Offset,Platform,PDR,BER\n")
        for r in records:
            f.write(f"{r['mod_type']},{r['fll_bw']},{r['costas_bw']},{r['sym_bw']},{r['preamble_size']},{r['noise_volt']},{r['freq_offset']},{r['time_offset']},{r['platform_mode']},{r['pdr']},{r['ber']}\n")
    print(f"{C_GREEN}[OK] Exported {len(records):,} records to CSV: {filename}{C_RESET}")

def interactive_repl():
    records = load_data()
    print(f"\n{C_BOLD}{C_CYAN}================================================================================{C_RESET}")
    print(f"      {C_BOLD}PHY2 PHYSICAL LAYER DYNAMIC INTERACTIVE TERMINAL PLOTTER{C_RESET}          ")
    print(f"{C_BOLD}{C_CYAN}================================================================================{C_RESET}")
    print(f"Loaded {len(records):,} high-density simulation trials spanning 0.005..1.000 rad/sym.")
    print("\nCommands:")
    print("  mod [BPSK|QPSK]                     : Switch modulation scheme")
    print("  fll <value>                         : Set FLL Band-Edge Loop BW (e.g. 'fll 0.0314')")
    print("  costas <min> <max>                  : Set Costas Loop BW range (e.g. 'costas 0.005 0.5')")
    print("  costas_lines <c1,c2,...>            : Set exact Costas line values")
    print("  plot                                : Draw dynamic BER vs Symbol Sync multi-line graph")
    print("  heatmap [ber|pdr]                   : Draw 2D Parametric Heatmap")
    print("  csv [limit]                         : View CSV table rows")
    print("  export [filename]                   : Export dataset to CSV")
    print("  browser                             : Open interactive web dashboard in browser")
    print("  help / quit                         : Display help or exit")
    print("--------------------------------------------------------------------------------")

    current_mod = "BPSK"
    current_fll = 0.0314
    current_costas_min = 0.005
    current_costas_max = 1.000
    all_costas = sorted(list(set(r['costas_bw'] for r in records)))
    current_costas_lines = [0.010, 0.035, 0.0628, 0.135, 0.250, 0.500, 1.000]

    # Initial plot
    render_terminal_ascii_plot(current_mod, current_fll, current_costas_lines, records)

    while True:
        try:
            line = input(f"{C_BOLD}{C_CYAN}PHY2 ({current_mod} | FLL={current_fll:.4f}) > {C_RESET}").strip()
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

        elif cmd == 'mod':
            if len(parts) > 1 and parts[1].upper() in ['BPSK', 'QPSK']:
                current_mod = parts[1].upper()
                print(f"{C_GREEN}-> Set modulation to {current_mod}{C_RESET}")
                render_terminal_ascii_plot(current_mod, current_fll, current_costas_lines, records)
            else:
                print(f"{C_RED}Usage: mod [BPSK|QPSK]{C_RESET}")

        elif cmd == 'fll':
            if len(parts) > 1:
                try:
                    val = float(parts[1])
                    current_fll = val
                    print(f"{C_GREEN}-> Set FLL Band-Edge Loop BW to {current_fll:.4f} rad/sym{C_RESET}")
                    render_terminal_ascii_plot(current_mod, current_fll, current_costas_lines, records)
                except ValueError:
                    print(f"{C_RED}Invalid float value for FLL.{C_RESET}")
            else:
                print(f"Current FLL: {current_fll:.4f} rad/sym")

        elif cmd == 'costas':
            if len(parts) >= 3:
                try:
                    c_min, c_max = float(parts[1]), float(parts[2])
                    current_costas_min, current_costas_max = c_min, c_max
                    current_costas_lines = [c for c in all_costas if c_min - 1e-4 <= c <= c_max + 1e-4]
                    if len(current_costas_lines) > 8:
                        step = max(1, len(current_costas_lines) // 7)
                        current_costas_lines = current_costas_lines[::step]
                    print(f"{C_GREEN}-> Selected {len(current_costas_lines)} Costas lines between {c_min:.4f} and {c_max:.4f}{C_RESET}")
                    render_terminal_ascii_plot(current_mod, current_fll, current_costas_lines, records)
                except ValueError:
                    print(f"{C_RED}Usage: costas <min> <max>{C_RESET}")
            else:
                print(f"Current Costas Range: {current_costas_min:.4f} .. {current_costas_max:.4f}")

        elif cmd == 'costas_lines':
            if len(parts) > 1:
                try:
                    vals = [float(x.strip()) for x in parts[1].split(',')]
                    current_costas_lines = vals
                    print(f"{C_GREEN}-> Set custom Costas lines: {current_costas_lines}{C_RESET}")
                    render_terminal_ascii_plot(current_mod, current_fll, current_costas_lines, records)
                except ValueError:
                    print(f"{C_RED}Usage: costas_lines 0.010,0.035,0.0628,0.135{C_RESET}")

        elif cmd in ['plot', 'graph']:
            render_terminal_ascii_plot(current_mod, current_fll, current_costas_lines, records)

        elif cmd == 'heatmap':
            metric = parts[1].lower() if len(parts) > 1 and parts[1].lower() in ['ber', 'pdr'] else 'ber'
            render_terminal_heatmap(current_mod, current_fll, records, metric)

        elif cmd == 'csv':
            limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 15
            print(f"\n{C_BOLD}Mod     FLL_BW  Costas_BW SymSync_BW Preamble Noise  Offset Drift    Profile  PDR%   BER{C_RESET}")
            print("─" * 86)
            matches = [r for r in records if r['mod_type'] == current_mod and abs(r['fll_bw'] - current_fll) < 0.005]
            for r in matches[:limit]:
                print(f"{r['mod_type']:<7} {r['fll_bw']:<7.4f} {r['costas_bw']:<9.4f} {r['sym_bw']:<10.4f} {r['preamble_size']:<8} {r['noise_volt']:<6.2f} {r['freq_offset']:<7.3f} {r['time_offset']:<8.6f} {r['platform_mode']:<8} {r['pdr']:<6.1f} {r['ber']:.2e}")
            print(f"─" * 86)
            print(f"Showing {min(limit, len(matches))} of {len(matches)} matching rows.\n")

        elif cmd == 'export':
            fn = parts[1] if len(parts) > 1 else "phy2_filtered_data.csv"
            export_terminal_csv(records, fn)

        elif cmd in ['browser', 'dash', 'dashboard']:
            html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dashboard/index.html"))
            print(f"{C_GREEN}-> Opening interactive dashboard: {html_path}{C_RESET}")
            try:
                subprocess.Popen(["xdg-open", html_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"{C_YELLOW}Could not open browser automatically: {e}. Open file://{html_path} manually.{C_RESET}")

        elif cmd in ['help', 'h', '?']:
            print("\nAvailable commands:")
            print("  mod [BPSK|QPSK]                     : Switch modulation scheme")
            print("  fll <value>                         : Set FLL Band-Edge Loop BW")
            print("  costas <min> <max>                  : Set Costas Loop BW range")
            print("  costas_lines <c1,c2,...>            : Set exact Costas line values")
            print("  plot                                : Draw dynamic BER vs Symbol Sync multi-line graph")
            print("  heatmap [ber|pdr]                   : Draw 2D Parametric Heatmap")
            print("  csv [limit]                         : View CSV table rows")
            print("  export [filename]                   : Export dataset to CSV")
            print("  browser                             : Open interactive web dashboard in browser")
            print("  quit                                : Exit interactive prompt\n")
        else:
            print(f"{C_RED}Unknown command '{cmd}'. Type 'help' for command list.{C_RESET}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Terminal Interactive Plotter & Analyzer")
    parser.add_argument('--mod', type=str, default='BPSK', choices=['BPSK', 'QPSK'])
    parser.add_argument('--fll', type=float, default=0.0314, help="FLL Band-Edge Loop BW")
    parser.add_argument('--costas-min', type=float, default=0.005, help="Costas BW Min")
    parser.add_argument('--costas-max', type=float, default=1.000, help="Costas BW Max")
    parser.add_argument('--costas-lines', type=str, default=None, help="Comma-separated Costas BW lines")
    parser.add_argument('--heatmap', action='store_true', help="Render 2D Heatmap")
    parser.add_argument('--export-csv', type=str, default=None, help="Export dataset to CSV file")
    parser.add_argument('--interactive', '-i', action='store_true', help="Launch interactive terminal REPL")
    args = parser.parse_args()

    if args.interactive or len(sys.argv) == 1:
        interactive_repl()
    else:
        records = load_data()
        all_costas = sorted(list(set(r['costas_bw'] for r in records)))
        if args.costas_lines:
            lines = [float(x.strip()) for x in args.costas_lines.split(',')]
        else:
            lines = [c for c in all_costas if args.costas_min - 1e-4 <= c <= args.costas_max + 1e-4]
            if len(lines) > 8:
                step = max(1, len(lines) // 7)
                lines = lines[::step]
                
        if args.heatmap:
            render_terminal_heatmap(args.mod, args.fll, records)
        else:
            render_terminal_ascii_plot(args.mod, args.fll, lines, records)
            
        if args.export_csv:
            export_terminal_csv(records, args.export_csv)
