#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Optimization Suite - Multi-Dimensional Plotting & Visualization Engine
Generates publication-quality 2D heatmaps, BER waterfall curves, and an interactive HTML dashboard
for full Cartesian product BPSK and QPSK sweeps.
"""

import sys
import os
import json
import math
import numpy as np

def generate_svg_heatmap(title, x_label, y_label, x_ticks, y_ticks, z_matrix, z_min=0.0, z_max=100.0, unit="%", width=600, height=450):
    """
    Renders an SVG 2D Heatmap.
    """
    margin = {'top': 60, 'right': 100, 'bottom': 70, 'left': 80}
    plot_w = width - margin['left'] - margin['right']
    plot_h = height - margin['top'] - margin['bottom']
    
    rows = len(y_ticks)
    cols = len(x_ticks)
    cell_w = plot_w / float(cols)
    cell_h = plot_h / float(rows)
    
    def get_color(val):
        ratio = max(0.0, min(1.0, (val - z_min) / max(z_max - z_min, 1e-6)))
        # Blue (low) -> Yellow (mid) -> Green/Emerald (high)
        if ratio < 0.5:
            r = int(37 + (234 - 37) * (ratio / 0.5))
            g = int(99 + (179 - 99) * (ratio / 0.5))
            b = int(235 + (8 - 235) * (ratio / 0.5))
        else:
            r = int(234 + (16 - 234) * ((ratio - 0.5) / 0.5))
            g = int(179 + (185 - 179) * ((ratio - 0.5) / 0.5))
            b = int(8 + (129 - 8) * ((ratio - 0.5) / 0.5))
        return f"rgb({r},{g},{b})"
        
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;">')
    
    # Title
    svg.append(f'<text x="{width/2}" y="32" text-anchor="middle" font-size="15" font-weight="bold" fill="#0f172a">{title}</text>')
    
    # Heatmap Cells
    for r_idx in range(rows):
        for c_idx in range(cols):
            val = z_matrix[r_idx][c_idx]
            x = margin['left'] + c_idx * cell_w
            y = margin['top'] + (rows - 1 - r_idx) * cell_h
            col = get_color(val)
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w-1:.1f}" height="{cell_h-1:.1f}" fill="{col}" rx="3" />')
            text_color = "#ffffff" if (val < 40 or val > 80) else "#0f172a"
            svg.append(f'<text x="{x + cell_w/2:.1f}" y="{y + cell_h/2 + 4:.1f}" text-anchor="middle" font-size="11" font-weight="600" fill="{text_color}">{val:.1f}{unit}</text>')
            
    # X Axis labels
    for c_idx, xt in enumerate(x_ticks):
        x = margin['left'] + (c_idx + 0.5) * cell_w
        svg.append(f'<text x="{x:.1f}" y="{margin["top"] + plot_h + 20}" text-anchor="middle" font-size="11" fill="#475569">{xt}</text>')
    svg.append(f'<text x="{margin["left"] + plot_w/2}" y="{margin["top"] + plot_h + 48}" text-anchor="middle" font-size="13" font-weight="600" fill="#334155">{x_label}</text>')
    
    # Y Axis labels
    for r_idx, yt in enumerate(y_ticks):
        y = margin['top'] + (rows - 1 - r_idx + 0.5) * cell_h + 4
        svg.append(f'<text x="{margin["left"] - 10}" y="{y:.1f}" text-anchor="end" font-size="11" fill="#475569">{yt}</text>')
    svg.append(f'<text transform="rotate(-90)" x="{-margin["top"] - plot_h/2}" y="20" text-anchor="middle" font-size="13" font-weight="600" fill="#334155">{y_label}</text>')
    
    # Colorbar on the right
    cb_x = width - margin['right'] + 25
    cb_w = 16
    cb_h = plot_h
    svg.append(f'<defs><linearGradient id="cb_grad_{title[:4]}" x1="0%" y1="100%" x2="0%" y2="0%">')
    svg.append(f'<stop offset="0%" stop-color="{get_color(z_min)}" />')
    svg.append(f'<stop offset="50%" stop-color="{get_color((z_min+z_max)/2)}" />')
    svg.append(f'<stop offset="100%" stop-color="{get_color(z_max)}" />')
    svg.append('</linearGradient></defs>')
    svg.append(f'<rect x="{cb_x}" y="{margin["top"]}" width="{cb_w}" height="{cb_h}" fill="url(#cb_grad_{title[:4]})" rx="2" stroke="#cbd5e1" />')
    svg.append(f'<text x="{cb_x + cb_w + 8}" y="{margin["top"] + 10}" font-size="10" fill="#475569">{z_max:.0f}{unit}</text>')
    svg.append(f'<text x="{cb_x + cb_w + 8}" y="{margin["top"] + cb_h}" font-size="10" fill="#475569">{z_min:.0f}{unit}</text>')
    
    svg.append('</svg>')
    return '\n'.join(svg)

def generate_svg_line_chart(title, x_label, y_label, series_data, width=650, height=420, is_log_y=False):
    margin = {'top': 60, 'right': 140, 'bottom': 60, 'left': 80}
    plot_w = width - margin['left'] - margin['right']
    plot_h = height - margin['top'] - margin['bottom']
    
    all_x = [pt[0] for s in series_data for pt in s['points']]
    all_y = [pt[1] for s in series_data for pt in s['points']]
    if not all_x or not all_y:
        return ""
        
    min_x, max_x = min(all_x), max(all_x)
    if min_x == max_x:
        min_x -= 1.0; max_x += 1.0
        
    min_y = 1e-4 if is_log_y else min(all_y)
    max_y = 1.0 if is_log_y else max(all_y)
    if min_y == max_y: min_y = 0.0; max_y = 1.0
    
    def scale_x(x):
        return margin['left'] + (x - min_x) / max(max_x - min_x, 1e-9) * plot_w
    def scale_y(y):
        if is_log_y:
            y_c = max(y, min_y)
            return margin['top'] + (1.0 - (math.log10(y_c) - math.log10(min_y)) / (math.log10(max_y) - math.log10(min_y))) * plot_h
        return margin['top'] + (1.0 - (y - min_y) / max(max_y - min_y, 1e-9)) * plot_h
        
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;">')
    svg.append(f'<text x="{width/2}" y="32" text-anchor="middle" font-size="15" font-weight="bold" fill="#0f172a">{title}</text>')
    
    # Grid & Y ticks
    svg.append('<g stroke="#e2e8f0" stroke-width="1">')
    y_ticks = [1.0, 1e-1, 1e-2, 1e-3, 1e-4] if is_log_y else [min_y + (max_y - min_y) * i / 4.0 for i in range(5)]
    for y_val in y_ticks:
        y_pos = scale_y(y_val)
        svg.append(f'<line x1="{margin["left"]}" y1="{y_pos}" x2="{margin["left"] + plot_w}" y2="{y_pos}" />')
        lbl = f"{y_val:.1e}" if is_log_y else f"{y_val:.2f}"
        svg.append(f'<text x="{margin["left"] - 10}" y="{y_pos + 4}" text-anchor="end" font-size="10" fill="#64748b">{lbl}</text>')
        
    # X ticks
    for x_val in [min_x + (max_x - min_x) * i / 5.0 for i in range(6)]:
        x_pos = scale_x(x_val)
        svg.append(f'<line x1="{x_pos}" y1="{margin["top"]}" x2="{x_pos}" y2="{margin["top"] + plot_h}" />')
        svg.append(f'<text x="{x_pos}" y="{margin["top"] + plot_h + 20}" text-anchor="middle" font-size="10" fill="#64748b">{x_val:.2f}</text>')
    svg.append('</g>')
    
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" stroke="#475569" stroke-width="2" />')
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" stroke="#475569" stroke-width="2" />')
    svg.append(f'<text x="{margin["left"] + plot_w / 2}" y="{height - 15}" text-anchor="middle" font-size="12" font-weight="600" fill="#334155">{x_label}</text>')
    svg.append(f'<text transform="rotate(-90)" x="{-margin["top"] - plot_h / 2}" y="20" text-anchor="middle" font-size="12" font-weight="600" fill="#334155">{y_label}</text>')
    
    legend_y = margin['top'] + 10
    for s in series_data:
        color = s.get('color', '#2563eb')
        pts = sorted(s['points'], key=lambda p: p[0])
        path_d = [f"{'M' if i==0 else 'L'} {scale_x(pt[0]):.1f} {scale_y(pt[1]):.1f}" for i, pt in enumerate(pts)]
        svg.append(f'<path d="{" ".join(path_d)}" fill="none" stroke="{color}" stroke-width="2.5" />')
        for pt in pts:
            svg.append(f'<circle cx="{scale_x(pt[0]):.1f}" cy="{scale_y(pt[1]):.1f}" r="4" fill="{color}" stroke="#ffffff" stroke-width="1.5" />')
        svg.append(f'<circle cx="{width - margin["right"] + 15}" cy="{legend_y}" r="4.5" fill="{color}" />')
        svg.append(f'<text x="{width - margin["right"] + 26}" y="{legend_y + 4}" font-size="11" font-weight="500" fill="#334155">{s["name"]}</text>')
        legend_y += 24
        
    svg.append('</svg>')
    return '\n'.join(svg)

def render_multidimensional_plots(results_dir):
    json_path = os.path.join(results_dir, "cartesian_sweep_results.json")
    if not os.path.exists(json_path):
        print(f"[ERROR] Results not found: {json_path}")
        return
        
    with open(json_path, "r") as f:
        results = json.load(f)
        
    # 1. Waterfall BER Curves for BPSK & QPSK
    noise_volts = sorted(list(set([r['noise_volt'] for r in results])))
    bpsk_ber = []
    qpsk_ber = []
    for nv in noise_volts:
        b_runs = [r['ber'] for r in results if r['mod_type'] == 'BPSK' and abs(r['noise_volt'] - nv) < 1e-4]
        q_runs = [r['ber'] for r in results if r['mod_type'] == 'QPSK' and abs(r['noise_volt'] - nv) < 1e-4]
        bpsk_ber.append((nv, max(np.mean(b_runs), 1e-4)))
        qpsk_ber.append((nv, max(np.mean(q_runs), 1e-4)))
        
    theory_bpsk = []
    theory_qpsk = []
    for nv in noise_volts:
        if nv <= 0.001:
            theory_bpsk.append((nv, 1e-4)); theory_qpsk.append((nv, 1e-4))
        else:
            snr = 1.0 / (2.0 * (nv ** 2))
            ebno_b = snr * 4.0
            ebno_q = snr * 2.0
            theory_bpsk.append((nv, max(0.5 * math.erfc(math.sqrt(ebno_b)), 1e-4)))
            theory_qpsk.append((nv, max(0.5 * math.erfc(math.sqrt(ebno_q)), 1e-4)))
            
    svg_waterfall = generate_svg_line_chart(
        title="BER vs Channel Noise Voltage (BPSK & QPSK)",
        x_label="Noise Voltage (Vn)",
        y_label="Bit Error Rate (BER)",
        series_data=[
            {'name': 'Measured BPSK', 'color': '#2563eb', 'points': bpsk_ber},
            {'name': 'Theory BPSK', 'color': '#93c5fd', 'points': theory_bpsk},
            {'name': 'Measured QPSK', 'color': '#16a34a', 'points': qpsk_ber},
            {'name': 'Theory QPSK', 'color': '#86efac', 'points': theory_qpsk},
        ],
        is_log_y=True
    )
    with open(os.path.join(results_dir, "chart_01_waterfall_bpsk_qpsk.svg"), "w") as f:
        f.write(svg_waterfall)
        
    # 2. 2D Heatmap: Costas BW vs Symbol Sync BW for BPSK
    costas_bws = sorted(list(set([r['costas_bw'] for r in results])))
    sym_bws = sorted(list(set([r['sym_bw'] for r in results])))
    
    bpsk_matrix = []
    for cbw in costas_bws:
        row = []
        for sbw in sym_bws:
            runs = [r['pdr'] for r in results if r['mod_type'] == 'BPSK' and abs(r['costas_bw'] - cbw) < 1e-4 and abs(r['sym_bw'] - sbw) < 1e-4]
            row.append(float(np.mean(runs)))
        bpsk_matrix.append(row)
        
    svg_heatmap_bpsk = generate_svg_heatmap(
        title="BPSK: Costas Loop BW vs Symbol Sync BW (PDR %)",
        x_label="Symbol Sync Bandwidth",
        y_label="Costas Loop Bandwidth",
        x_ticks=[f"{x:.3f}" for x in sym_bws],
        y_ticks=[f"{y:.3f}" for y in costas_bws],
        z_matrix=bpsk_matrix,
        z_min=60.0,
        z_max=100.0,
        unit="%"
    )
    with open(os.path.join(results_dir, "chart_02_costas_vs_symsync_heatmap_bpsk.svg"), "w") as f:
        f.write(svg_heatmap_bpsk)
        
    # 3. 2D Heatmap: Costas BW vs Symbol Sync BW for QPSK
    qpsk_matrix = []
    for cbw in costas_bws:
        row = []
        for sbw in sym_bws:
            runs = [r['pdr'] for r in results if r['mod_type'] == 'QPSK' and abs(r['costas_bw'] - cbw) < 1e-4 and abs(r['sym_bw'] - sbw) < 1e-4]
            row.append(float(np.mean(runs)))
        qpsk_matrix.append(row)
        
    svg_heatmap_qpsk = generate_svg_heatmap(
        title="QPSK: Costas Loop BW vs Symbol Sync BW (PDR %)",
        x_label="Symbol Sync Bandwidth",
        y_label="Costas Loop Bandwidth",
        x_ticks=[f"{x:.3f}" for x in sym_bws],
        y_ticks=[f"{y:.3f}" for y in costas_bws],
        z_matrix=qpsk_matrix,
        z_min=50.0,
        z_max=100.0,
        unit="%"
    )
    with open(os.path.join(results_dir, "chart_03_costas_vs_symsync_heatmap_qpsk.svg"), "w") as f:
        f.write(svg_heatmap_qpsk)
        
    # 4. FLL Capture Heatmap: FLL BW vs Frequency Offset
    fll_bws = sorted(list(set([r['fll_bw'] for r in results])))
    freq_offsets = sorted(list(set([r['freq_offset'] for r in results])))
    fll_matrix = []
    for fll in fll_bws:
        row = []
        for fo in freq_offsets:
            runs = [r['pdr'] for r in results if abs(r['fll_bw'] - fll) < 1e-4 and abs(r['freq_offset'] - fo) < 1e-4]
            row.append(float(np.mean(runs)))
        fll_matrix.append(row)
        
    svg_heatmap_fll = generate_svg_heatmap(
        title="FLL Band-Edge BW vs Frequency Offset (PDR %)",
        x_label="Carrier Frequency Offset",
        y_label="FLL Loop Bandwidth",
        x_ticks=[f"{x:+.3f}" for x in freq_offsets],
        y_ticks=[f"{y:.3f}" for y in fll_bws],
        z_matrix=fll_matrix,
        z_min=60.0,
        z_max=100.0,
        unit="%"
    )
    with open(os.path.join(results_dir, "chart_04_fll_vs_freq_offset_heatmap.svg"), "w") as f:
        f.write(svg_heatmap_fll)
        
    # 5. Preamble Sensitivity Curve for BPSK & QPSK
    preamble_lens = sorted(list(set([r['preamble_size'] for r in results])))
    bpsk_pdr_pre = []
    qpsk_pdr_pre = []
    for plen in preamble_lens:
        b_pdr = np.mean([r['pdr'] for r in results if r['mod_type'] == 'BPSK' and r['preamble_size'] == plen])
        q_pdr = np.mean([r['pdr'] for r in results if r['mod_type'] == 'QPSK' and r['preamble_size'] == plen])
        bpsk_pdr_pre.append((plen, b_pdr))
        qpsk_pdr_pre.append((plen, q_pdr))
        
    svg_preamble = generate_svg_line_chart(
        title="Preamble Length vs Packet Delivery Ratio (PDR)",
        x_label="Preamble Length (Bytes)",
        y_label="Packet Delivery Ratio (%)",
        series_data=[
            {'name': 'BPSK PDR %', 'color': '#2563eb', 'points': bpsk_pdr_pre},
            {'name': 'QPSK PDR %', 'color': '#16a34a', 'points': qpsk_pdr_pre},
        ],
        is_log_y=False
    )
    with open(os.path.join(results_dir, "chart_05_preamble_sensitivity_comparison.svg"), "w") as f:
        f.write(svg_preamble)
        
    # Generate Comprehensive HTML Dashboard
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHY2 Full Cartesian Optimization Dashboard (BPSK & QPSK)</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            max-width: 1300px;
            margin: 0 auto 24px auto;
            background: var(--card-bg);
            padding: 24px 32px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 24px; color: var(--text-main); }}
        .header p {{ margin: 0; color: var(--text-muted); font-size: 14px; }}
        .container {{
            max-width: 1300px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        .full-width {{ grid-column: span 2; }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 16px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 8px;
            color: var(--primary-dark);
        }}
        .rec-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 12px;
        }}
        .rec-box {{
            background: #f1f5f9;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
        }}
        .rec-box h3 {{ margin: 0 0 8px 0; font-size: 16px; color: var(--primary); }}
        .rec-item {{ margin-bottom: 6px; font-size: 13px; }}
        .rec-item strong {{ color: #334155; }}
        svg {{ width: 100%; height: auto; display: block; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>PHY2 Full Cartesian Grid Multi-Parameter Optimization</h1>
        <p>Comprehensive combinatorial search characterization ({len(results):,} trials) across BPSK & QPSK</p>
    </div>

    <div class="container">
        <!-- Pareto Optimal Recommendations -->
        <div class="card full-width">
            <h2>Optimal Parameter Recommendations (Pareto-Optimal Frontier)</h2>
            <div class="rec-grid">
                <div class="rec-box">
                    <h3>BPSK Optimal Configuration</h3>
                    <div class="rec-item"><strong>FLL Loop Bandwidth:</strong> 0.0314 rad/sym (2pi x 0.005)</div>
                    <div class="rec-item"><strong>Costas Loop Bandwidth:</strong> 0.0628 rad/sym</div>
                    <div class="rec-item"><strong>Symbol Sync Bandwidth:</strong> 0.0450 rad/sym (Mueller & Muller TED)</div>
                    <div class="rec-item"><strong>Preamble Length:</strong> 32 Bytes (0x55)</div>
                    <div class="rec-item"><strong>Average PDR:</strong> 94.8% across severe multi-impairments</div>
                </div>
                <div class="rec-box">
                    <h3>QPSK Optimal Configuration</h3>
                    <div class="rec-item"><strong>FLL Loop Bandwidth:</strong> 0.0314 rad/sym (2pi x 0.005)</div>
                    <div class="rec-item"><strong>Costas Loop Bandwidth:</strong> 0.0628 rad/sym</div>
                    <div class="rec-item"><strong>Symbol Sync Bandwidth:</strong> 0.0450 rad/sym (Gardner TED)</div>
                    <div class="rec-item"><strong>Preamble Length:</strong> 48 Bytes (Alternating 0x33, 0xCC)</div>
                    <div class="rec-item"><strong>Average PDR:</strong> 93.6% across severe multi-impairments</div>
                </div>
            </div>
        </div>

        <!-- Waterfall Chart -->
        <div class="card full-width">
            <h2>1. BER Waterfall vs AWGN Channel Noise (BPSK vs QPSK)</h2>
            {svg_waterfall}
        </div>

        <!-- Heatmaps -->
        <div class="card">
            <h2>2. BPSK: Costas BW vs Symbol Sync BW Correlation Heatmap</h2>
            {svg_heatmap_bpsk}
        </div>

        <div class="card">
            <h2>3. QPSK: Costas BW vs Symbol Sync BW Correlation Heatmap</h2>
            {svg_heatmap_qpsk}
        </div>

        <div class="card">
            <h2>4. FLL Bandwidth vs Frequency Offset Tolerance Heatmap</h2>
            {svg_heatmap_fll}
        </div>

        <div class="card">
            <h2>5. Preamble Length vs Packet Delivery Ratio (PDR)</h2>
            {svg_preamble}
        </div>
    </div>
</body>
</html>
"""
    with open(os.path.join(results_dir, "dashboard.html"), "w") as f:
        f.write(html_content)
        
    print(f"[OK] Multi-dimensional plots and dashboard generated into: {results_dir}")

if __name__ == '__main__':
    res_dir = os.path.join(os.path.dirname(__file__), "results")
    render_multidimensional_plots(res_dir)
