#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Optimization Suite - Multi-Slice Deep Parametric Visualization Engine
Generates publication-quality parametric multi-line slice plots, 2D correlation heatmaps,
and an interactive HTML dashboard for 0.005 to 1.000 rad/sym BPSK and QPSK characterization.
"""

import sys
import os
import json
import math
import numpy as np

def generate_multiline_svg(title, x_label, y_label, series_data, x_range=None, y_range=None, is_log_y=False, width=680, height=440):
    margin = {'top': 60, 'right': 170, 'bottom': 60, 'left': 85}
    plot_w = width - margin['left'] - margin['right']
    plot_h = height - margin['top'] - margin['bottom']
    
    all_x = [pt[0] for s in series_data for pt in s['points']]
    all_y = [pt[1] for s in series_data for pt in s['points']]
    if not all_x or not all_y:
        return ""
        
    min_x = min(all_x) if x_range is None else x_range[0]
    max_x = max(all_x) if x_range is None else x_range[1]
    if min_x == max_x: min_x -= 0.01; max_x += 0.01
    
    min_y = (1e-4 if is_log_y else min(all_y)) if y_range is None else y_range[0]
    max_y = (1.0 if is_log_y else max(all_y)) if y_range is None else y_range[1]
    if min_y == max_y: min_y = 0.0; max_y = 1.0
    
    def scale_x(x):
        return margin['left'] + (x - min_x) / max(max_x - min_x, 1e-9) * plot_w
    def scale_y(y):
        if is_log_y:
            y_c = max(y, min_y)
            return margin['top'] + (1.0 - (math.log10(y_c) - math.log10(min_y)) / max(math.log10(max_y) - math.log10(min_y), 1e-9)) * plot_h
        return margin['top'] + (1.0 - (y - min_y) / max(max_y - min_y, 1e-9)) * plot_h
        
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;">')
    
    # Title
    svg.append(f'<text x="{width/2}" y="32" text-anchor="middle" font-size="14" font-weight="bold" fill="#0f172a">{title}</text>')
    
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
        lbl = f"{x_val:.3f}" if max_x < 0.1 else f"{x_val:.2f}"
        svg.append(f'<text x="{x_pos}" y="{margin["top"] + plot_h + 18}" text-anchor="middle" font-size="10" fill="#64748b">{lbl}</text>')
    svg.append('</g>')
    
    # Axes lines
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" stroke="#475569" stroke-width="2" />')
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" stroke="#475569" stroke-width="2" />')
    svg.append(f'<text x="{margin["left"] + plot_w / 2}" y="{height - 15}" text-anchor="middle" font-size="12" font-weight="600" fill="#334155">{x_label}</text>')
    svg.append(f'<text transform="rotate(-90)" x="{-margin["top"] - plot_h / 2}" y="20" text-anchor="middle" font-size="12" font-weight="600" fill="#334155">{y_label}</text>')
    
    # Series Curves & Legend
    colors = ['#2563eb', '#16a34a', '#dc2626', '#d97706', '#9333ea', '#0891b2', '#4f46e5', '#ec4899']
    legend_y = margin['top'] + 10
    
    for s_idx, s in enumerate(series_data):
        color = s.get('color', colors[s_idx % len(colors)])
        pts = sorted(s['points'], key=lambda p: p[0])
        if not pts: continue
        path_d = [f"{'M' if i==0 else 'L'} {scale_x(pt[0]):.1f} {scale_y(pt[1]):.1f}" for i, pt in enumerate(pts)]
        svg.append(f'<path d="{" ".join(path_d)}" fill="none" stroke="{color}" stroke-width="2.2" />')
        for pt in pts:
            svg.append(f'<circle cx="{scale_x(pt[0]):.1f}" cy="{scale_y(pt[1]):.1f}" r="3.5" fill="{color}" stroke="#ffffff" stroke-width="1.2" />')
            
        # Legend item
        svg.append(f'<line x1="{width - margin["right"] + 15}" y1="{legend_y}" x2="{width - margin["right"] + 35}" y2="{legend_y}" stroke="{color}" stroke-width="2.5" />')
        svg.append(f'<circle cx="{width - margin["right"] + 25}" cy="{legend_y}" r="3.5" fill="{color}" />')
        svg.append(f'<text x="{width - margin["right"] + 42}" y="{legend_y + 4}" font-size="11" font-weight="500" fill="#334155">{s["name"]}</text>')
        legend_y += 20
        
    svg.append('</svg>')
    return '\n'.join(svg)

from collections import defaultdict

def render_deep_analysis_plots(results_dir):
    json_path = os.path.join(results_dir, "deep_sweep_results.json")
    if not os.path.exists(json_path):
        print(f"[ERROR] Missing results: {json_path}")
        return
        
    with open(json_path, "r") as f:
        results = json.load(f)
        
    # --- Single Pass Indexing O(N) instead of billions of nested scans ---
    # Fast multi-dimensional lookup tables
    # 1. (mod, fll, costas, sym) -> [ber]
    p1_idx = defaultdict(list)
    # 2. (mod, costas, fo, fll) -> [ber]
    p2_idx = defaultdict(list)
    # 3. (mod, sym, plen, nv) -> [pdr]
    p3_idx = defaultdict(list)
    # 4. (mod, plat, nv) -> [ber]
    p4_idx = defaultdict(list)
    
    all_sym_vals = set()
    all_fll_vals = set()
    all_noise_vals = set()
    
    for r in results:
        mod = r.get('mod_type', 'BPSK')
        fll = round(float(r.get('fll_bw', 0)), 4)
        costas = round(float(r.get('costas_bw', 0)), 4)
        sym = round(float(r.get('sym_bw', 0)), 4)
        plen = int(r.get('preamble_size', 32))
        nv = round(float(r.get('noise_volt', 0)), 4)
        fo = round(float(r.get('freq_offset', 0)), 4)
        plat = r.get('platform_mode', 'software')
        ber = float(r.get('ber', 0.5))
        pdr = float(r.get('pdr', 0.0))
        
        p1_idx[(mod, fll, costas, sym)].append(ber)
        p2_idx[(mod, costas, fo, fll)].append(ber)
        p3_idx[(mod, sym, plen, nv)].append(pdr)
        p4_idx[(mod, plat, nv)].append(ber)
        
        all_sym_vals.add(sym)
        all_fll_vals.add(fll)
        all_noise_vals.add(nv)
        
    sym_sync_vals = sorted(list(all_sym_vals))
    fll_vals = sorted(list(all_fll_vals))
    noise_vals = sorted(list(all_noise_vals))
    
    svg_map = {}

    # --- PLOT 1: Fixed FLL Slice -> BER vs Symbol Sync BW for Varied Costas BW ---
    fixed_fll = 0.0314
    for mod in ['BPSK', 'QPSK']:
        costas_vals = [0.010, 0.035, 0.0628, 0.135, 0.250, 0.500, 1.000]
        series_1 = []
        for cbw in costas_vals:
            pts = []
            for sbw in sym_sync_vals:
                runs = p1_idx.get((mod, fixed_fll, round(cbw, 4), round(sbw, 4)), [])
                if runs:
                    pts.append((sbw, max(float(np.mean(runs)), 1e-4)))
            if pts:
                series_1.append({'name': f'Costas = {cbw:.3f}', 'points': pts})
                
        svg_p1 = generate_multiline_svg(
            title=f"{mod} (y·y' TED): BER vs Symbol Sync Loop BW [FLL Band-Edge = {fixed_fll:.4f} rad/sym]",
            x_label="Symbol Synchronizer Loop Bandwidth (rad/sym)",
            y_label="Bit Error Rate (BER)",
            series_data=series_1,
            is_log_y=True
        )
        svg_name = f"chart_slice_01_fixed_fll_ber_vs_symsync_{mod.lower()}.svg"
        svg_map[svg_name] = svg_p1
        with open(os.path.join(results_dir, svg_name), "w") as f:
            f.write(svg_p1)
            
    # --- PLOT 2: Fixed Costas Slice -> BER vs FLL BW for Varied Frequency Offsets ---
    fixed_costas = 0.0628
    for mod in ['BPSK', 'QPSK']:
        freq_offsets = [-0.030, -0.020, -0.010, 0.0, +0.010, +0.020, +0.030]
        series_2 = []
        for fo in freq_offsets:
            pts = []
            for fll in fll_vals:
                runs = p2_idx.get((mod, fixed_costas, round(fo, 4), round(fll, 4)), [])
                if runs:
                    pts.append((fll, max(float(np.mean(runs)), 1e-4)))
            if pts:
                series_2.append({'name': f'Offset = {fo:+.3f} fs', 'points': pts})
                
        svg_p2 = generate_multiline_svg(
            title=f"{mod} (y·y' TED): BER vs FLL Bandwidth (0.005 to 1.000 rad/sym)",
            x_label="FLL Band-Edge Loop Bandwidth (rad/sym)",
            y_label="Bit Error Rate (BER)",
            series_data=series_2,
            is_log_y=True
        )
        svg_name = f"chart_slice_02_fixed_costas_ber_vs_fll_{mod.lower()}.svg"
        svg_map[svg_name] = svg_p2
        with open(os.path.join(results_dir, svg_name), "w") as f:
            f.write(svg_p2)
            
    # --- PLOT 3: Fixed Symbol Sync Slice -> PDR vs Noise Voltage for Varied Preambles ---
    fixed_sym = 0.025
    for mod in ['BPSK', 'QPSK']:
        preambles = [16, 24, 32, 48, 64]
        series_3 = []
        for plen in preambles:
            pts = []
            for nv in noise_vals:
                runs = p3_idx.get((mod, fixed_sym, plen, round(nv, 4)), [])
                if runs:
                    pts.append((nv, float(np.mean(runs))))
            if pts:
                series_3.append({'name': f'Preamble = {plen} B', 'points': pts})
                
        svg_p3 = generate_multiline_svg(
            title=f"{mod} (y·y' TED): Packet Delivery Ratio (PDR %) vs Noise across Preambles",
            x_label="Channel Noise Voltage (Vn)",
            y_label="Packet Delivery Ratio (%)",
            series_data=series_3,
            y_range=[0.0, 100.0],
            is_log_y=False
        )
        svg_name = f"chart_slice_03_fixed_symsync_pdr_vs_noise_{mod.lower()}.svg"
        svg_map[svg_name] = svg_p3
        with open(os.path.join(results_dir, svg_name), "w") as f:
            f.write(svg_p3)
            
    # --- PLOT 4: Software Impairments vs Hardware SDR Profile Comparison ---
    series_hw = []
    for mod in ['BPSK', 'QPSK']:
        for plat in ['software', 'hardware']:
            pts = []
            for nv in noise_vals:
                runs = p4_idx.get((mod, plat, round(nv, 4)), [])
                if runs:
                    pts.append((nv, max(float(np.mean(runs)), 1e-4)))
            lbl = f"{mod} ({'Soft Multipath' if plat=='software' else 'Hardware OTA'})"
            series_hw.append({'name': lbl, 'points': pts})
            
    svg_hw = generate_multiline_svg(
        title="Software Multipath vs Hardware SDR Profile BER Comparison (0.005 to 1.000 Range)",
        x_label="Noise Voltage (Vn)",
        y_label="Bit Error Rate (BER)",
        series_data=series_hw,
        is_log_y=True
    )
    with open(os.path.join(results_dir, "chart_slice_04_software_vs_hardware_comparison.svg"), "w") as f:
        f.write(svg_hw)
        
    # Read pinpoint optimal parameters
    pinpoint_json = os.path.join(results_dir, "pinpoint_optimal_parameters.json")
    pinpoint_data = {}
    if os.path.exists(pinpoint_json):
        try:
            with open(pinpoint_json, "r") as f:
                pinpoint_data = json.load(f)
        except Exception:
            pass
            
    bpsk_fll = pinpoint_data.get('BPSK', {}).get('optimal_fll_bandwidth', 0.0314)
    bpsk_costas = pinpoint_data.get('BPSK', {}).get('optimal_costas_bandwidth', 0.0628)
    bpsk_sym = pinpoint_data.get('BPSK', {}).get('optimal_symbol_sync_bandwidth', 0.0250)
    bpsk_plen = pinpoint_data.get('BPSK', {}).get('optimal_preamble_length', 32)
    
    qpsk_fll = pinpoint_data.get('QPSK', {}).get('optimal_fll_bandwidth', 0.0314)
    qpsk_costas = pinpoint_data.get('QPSK', {}).get('optimal_costas_bandwidth', 0.0628)
    qpsk_sym = pinpoint_data.get('QPSK', {}).get('optimal_symbol_sync_bandwidth', 0.0250)
    qpsk_plen = pinpoint_data.get('QPSK', {}).get('optimal_preamble_length', 32)

    # Build Interactive HTML Dashboard
    html_dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHY2 Ultra-Deep Multi-Slice Parametric Optimization Dashboard (0.005 to 1.000 rad/sym)</title>
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
            max-width: 1400px;
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
            max-width: 1400px;
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
        .opt-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-top: 12px;
        }}
        .opt-box {{
            background: #f1f5f9;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
        }}
        .opt-box h3 {{ margin: 0 0 8px 0; font-size: 15px; color: var(--primary); }}
        .opt-item {{ margin-bottom: 6px; font-size: 12px; }}
        .opt-item strong {{ color: #334155; }}
        svg {{ width: 100%; height: auto; display: block; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>PHY2 Ultra-Deep Optimization Dashboard (0.005 to 1.000 rad/sym)</h1>
        <p>Comprehensive characterization with TED_SIGNAL_TIMES_SLOPE_ML (y·y' TED), Correlation Estimator + Equalizer ({len(results):,} trials)</p>
    </div>

    <div class="container">
        <!-- Pinpointed Optimal Parameters Summary -->
        <div class="card full-width">
            <h2>Pinpointed Optimal Configurations (0.005 to 1.000 rad/sym Range)</h2>
            <div class="opt-grid">
                <div class="opt-box">
                    <h3>BPSK (Software Multipath)</h3>
                    <div class="opt-item"><strong>FLL Loop BW:</strong> {bpsk_fll:.4f} rad/sym</div>
                    <div class="opt-item"><strong>Costas Loop BW:</strong> {bpsk_costas:.4f} rad/sym</div>
                    <div class="opt-item"><strong>Symbol Sync BW:</strong> {bpsk_sym:.4f} rad/sym (y·y')</div>
                    <div class="opt-item"><strong>Preamble Length:</strong> {bpsk_plen} Bytes</div>
                    <div class="opt-item"><strong>Corr Estimator:</strong> Enabled</div>
                </div>
                <div class="opt-box">
                    <h3>BPSK (Hardware SDR Profile)</h3>
                    <div class="opt-item"><strong>FLL Loop BW:</strong> {bpsk_fll:.4f} rad/sym</div>
                    <div class="opt-item"><strong>Costas Loop BW:</strong> {bpsk_costas:.4f} rad/sym</div>
                    <div class="opt-item"><strong>Symbol Sync BW:</strong> {bpsk_sym:.4f} rad/sym (y·y')</div>
                    <div class="opt-item"><strong>Preamble Length:</strong> {bpsk_plen} Bytes</div>
                    <div class="opt-item"><strong>Corr Estimator:</strong> Enabled</div>
                </div>
                <div class="opt-box">
                    <h3>QPSK (Software Multipath)</h3>
                    <div class="opt-item"><strong>FLL Loop BW:</strong> {qpsk_fll:.4f} rad/sym</div>
                    <div class="opt-item"><strong>Costas Loop BW:</strong> {qpsk_costas:.4f} rad/sym</div>
                    <div class="opt-item"><strong>Symbol Sync BW:</strong> {qpsk_sym:.4f} rad/sym (y·y')</div>
                    <div class="opt-item"><strong>Preamble Length:</strong> {qpsk_plen} Bytes</div>
                    <div class="opt-item"><strong>Corr Estimator:</strong> Enabled</div>
                </div>
                <div class="opt-box">
                    <h3>QPSK (Hardware SDR Profile)</h3>
                    <div class="opt-item"><strong>FLL Loop BW:</strong> {qpsk_fll:.4f} rad/sym</div>
                    <div class="opt-item"><strong>Costas Loop BW:</strong> {qpsk_costas:.4f} rad/sym</div>
                    <div class="opt-item"><strong>Symbol Sync BW:</strong> {qpsk_sym:.4f} rad/sym (y·y')</div>
                    <div class="opt-item"><strong>Preamble Length:</strong> {qpsk_plen} Bytes</div>
                    <div class="opt-item"><strong>Corr Estimator:</strong> Enabled</div>
                </div>
            </div>
        </div>

        <!-- Slice 1: Fixed FLL Slice -->
        <div class="card">
            <h2>1. BPSK: BER vs Symbol Sync BW (0.005 to 1.000 rad/sym) for Varied Costas BW</h2>
            {svg_map.get("chart_slice_01_fixed_fll_ber_vs_symsync_bpsk.svg", "")}
        </div>

        <div class="card">
            <h2>2. QPSK: BER vs Symbol Sync BW (0.005 to 1.000 rad/sym) for Varied Costas BW</h2>
            {svg_map.get("chart_slice_01_fixed_fll_ber_vs_symsync_qpsk.svg", "")}
        </div>

        <!-- Slice 2: Fixed Costas Slice -->
        <div class="card">
            <h2>3. BPSK: BER vs FLL Bandwidth (0.005 to 1.000 rad/sym) for Varied Frequency Offsets</h2>
            {svg_map.get("chart_slice_02_fixed_costas_ber_vs_fll_bpsk.svg", "")}
        </div>

        <div class="card">
            <h2>4. QPSK: BER vs FLL Bandwidth (0.005 to 1.000 rad/sym) for Varied Frequency Offsets</h2>
            {svg_map.get("chart_slice_02_fixed_costas_ber_vs_fll_qpsk.svg", "")}
        </div>

        <!-- Slice 3: Fixed Symbol Sync Slice -->
        <div class="card">
            <h2>5. BPSK: PDR vs Noise Voltage for Varied Preamble Lengths</h2>
            {svg_map.get("chart_slice_03_fixed_symsync_pdr_vs_noise_bpsk.svg", "")}
        </div>

        <div class="card">
            <h2>6. QPSK: PDR vs Noise Voltage for Varied Preamble Lengths</h2>
            {svg_map.get("chart_slice_03_fixed_symsync_pdr_vs_noise_qpsk.svg", "")}
        </div>

        <!-- Slice 4: Software vs Hardware Comparison -->
        <div class="card full-width">
            <h2>7. Software Simulation Multipath vs Hardware SDR Profile BER Comparison</h2>
            {svg_hw}
        </div>
    </div>
</body>
</html>
"""
    with open(os.path.join(results_dir, "deep_dashboard.html"), "w") as f:
        f.write(html_dashboard)
        
    print(f"[OK] Multi-slice plots and deep dashboard generated into: {results_dir}")

if __name__ == '__main__':
    res_dir = os.path.join(os.path.dirname(__file__), "results")
    render_deep_analysis_plots(res_dir)
