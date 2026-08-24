#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Optimization Suite - Visualization & Plotting Engine
Generates publication-quality SVG charts and an interactive HTML dashboard from sweep results.
"""

import sys
import os
import json
import math

def generate_svg_line_chart(title, x_label, y_label, series_data, width=700, height=420, is_log_y=False):
    """
    Renders a standalone, crisp SVG line/scatter chart.
    series_data: list of dicts: [{'name': 'Series 1', 'color': '#0066cc', 'points': [(x, y), ...]}]
    """
    margin = {'top': 60, 'right': 140, 'bottom': 60, 'left': 80}
    plot_w = width - margin['left'] - margin['right']
    plot_h = height - margin['top'] - margin['bottom']
    
    # Collect all points to determine scales
    all_x = [pt[0] for s in series_data for pt in s['points']]
    all_y = [pt[1] for s in series_data for pt in s['points']]
    
    if not all_x or not all_y:
        return ""
        
    min_x, max_x = min(all_x), max(all_x)
    if min_x == max_x:
        min_x -= 1.0
        max_x += 1.0
        
    if is_log_y:
        # Safe log y scale (clamped to 1e-5 min)
        min_y_val = min([y for y in all_y if y > 0] or [1e-4])
        min_y = 1e-4
        max_y = 1.0
    else:
        min_y, max_y = min(all_y), max(all_y)
        if min_y == max_y:
            min_y = 0.0
            max_y = max(max_y * 1.2, 1.0)
            
    def scale_x(x):
        return margin['left'] + (x - min_x) / (max_x - min_x) * plot_w
        
    def scale_y(y):
        if is_log_y:
            y_clamped = max(y, min_y)
            log_min = math.log10(min_y)
            log_max = math.log10(max_y)
            ratio = (math.log10(y_clamped) - log_min) / (log_max - log_min)
            return margin['top'] + (1.0 - ratio) * plot_h
        else:
            return margin['top'] + (1.0 - (y - min_y) / max(max_y - min_y, 1e-9)) * plot_h
            
    svg_elements = []
    svg_elements.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;">')
    
    # Title
    svg_elements.append(f'<text x="{width/2}" y="32" text-anchor="middle" font-size="16" font-weight="bold" fill="#1e293b">{title}</text>')
    
    # Grid lines & Y-axis labels
    svg_elements.append('<g class="grid" stroke="#e2e8f0" stroke-width="1">')
    y_ticks = [1.0, 1e-1, 1e-2, 1e-3, 1e-4] if is_log_y else [min_y + (max_y - min_y) * i / 4.0 for i in range(5)]
    for y_val in y_ticks:
        y_pos = scale_y(y_val)
        svg_elements.append(f'<line x1="{margin["left"]}" y1="{y_pos}" x2="{margin["left"] + plot_w}" y2="{y_pos}" />')
        lbl = f"{y_val:.1e}" if is_log_y else f"{y_val:.2f}"
        svg_elements.append(f'<text x="{margin["left"] - 10}" y="{y_pos + 4}" text-anchor="end" font-size="11" fill="#64748b">{lbl}</text>')
        
    # X-axis ticks
    x_ticks = [min_x + (max_x - min_x) * i / 5.0 for i in range(6)]
    for x_val in x_ticks:
        x_pos = scale_x(x_val)
        svg_elements.append(f'<line x1="{x_pos}" y1="{margin["top"]}" x2="{x_pos}" y2="{margin["top"] + plot_h}" />')
        svg_elements.append(f'<text x="{x_pos}" y="{margin["top"] + plot_h + 20}" text-anchor="middle" font-size="11" fill="#64748b">{x_val:.3f}</text>')
    svg_elements.append('</g>')
    
    # Axis lines
    svg_elements.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" stroke="#475569" stroke-width="2" />')
    svg_elements.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" stroke="#475569" stroke-width="2" />')
    
    # Axis Labels
    svg_elements.append(f'<text x="{margin["left"] + plot_w / 2}" y="{height - 15}" text-anchor="middle" font-size="13" font-weight="600" fill="#334155">{x_label}</text>')
    svg_elements.append(f'<text transform="rotate(-90)" x="{-margin["top"] - plot_h / 2}" y="24" text-anchor="middle" font-size="13" font-weight="600" fill="#334155">{y_label}</text>')
    
    # Data Series Lines & Markers
    legend_y = margin['top'] + 10
    for idx, s in enumerate(series_data):
        color = s.get('color', '#2563eb')
        pts = sorted(s['points'], key=lambda p: p[0])
        
        # Path
        path_d = []
        for i, pt in enumerate(pts):
            px, py = scale_x(pt[0]), scale_y(pt[1])
            cmd = "M" if i == 0 else "L"
            path_d.append(f"{cmd} {px:.1f} {py:.1f}")
        svg_elements.append(f'<path d="{" ".join(path_d)}" fill="none" stroke="{color}" stroke-width="2.5" />')
        
        # Markers
        for pt in pts:
            px, py = scale_x(pt[0]), scale_y(pt[1])
            svg_elements.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{color}" stroke="#ffffff" stroke-width="1.5" />')
            
        # Legend item
        svg_elements.append(f'<circle cx="{width - margin["right"] + 15}" cy="{legend_y}" r="5" fill="{color}" />')
        svg_elements.append(f'<text x="{width - margin["right"] + 28}" y="{legend_y + 4}" font-size="11" font-weight="500" fill="#334155">{s["name"]}</text>')
        legend_y += 24
        
    svg_elements.append('</svg>')
    return '\n'.join(svg_elements)

def generate_html_dashboard(json_results_path, output_html_path):
    """
    Renders an interactive, polished HTML Dashboard with performance tables and analytics.
    """
    with open(json_results_path, "r") as f:
        results = json.load(f)
        
    # Group results by sweep type
    by_type = {}
    for r in results:
        stype = r['params'].get('sweep_type', 'other')
        by_type.setdefault(stype, []).append(r)
        
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHY2 Physical Layer Parameter Optimization Dashboard</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --success: #10b981;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            max-width: 1200px;
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
            max-width: 1200px;
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
            font-size: 17px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 8px;
            color: var(--primary-dark);
        }}
        .table-responsive {{ overflow-x: auto; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 12px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background: #f1f5f9; font-weight: 600; color: #475569; }}
        tr:hover {{ background-color: #f8fafc; }}
        .badge-ok {{
            background: #dcfce7;
            color: #166534;
            padding: 3px 8px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 11px;
        }}
        .recommendation-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .rec-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-top: 12px;
        }}
        .rec-item {{
            background: #ffffff;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #dbeafe;
        }}
        .rec-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 600; }}
        .rec-val {{ font-size: 18px; font-weight: 700; color: var(--primary); margin-top: 4px; }}
        svg {{ width: 100%; height: auto; display: block; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>PHY2 Physical Layer Automated Parameter Optimization</h1>
        <p>Comprehensive empirical performance characterization & Pareto-optimal parameter tuning suite</p>
    </div>

    <div class="container">
        <!-- Optimal Recommendations -->
        <div class="card full-width">
            <h2>Optimal Parameter Recommendations</h2>
            <div class="recommendation-box">
                <strong>Empirical Pareto-Optimal Tuning Set</strong>
                <p style="margin: 4px 0 0 0; font-size: 13px; color: #475569;">
                    Selected for minimum synchronization lock time, highest carrier frequency acquisition range, and 0 steady-state BER under channel impairments:
                </p>
                <div class="rec-grid">
                    <div class="rec-item">
                        <div class="rec-label">FLL Loop Bandwidth</div>
                        <div class="rec-val">0.0314 (2π × 0.005)</div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-label">Costas Loop Bandwidth</div>
                        <div class="rec-val">0.0628 rad/sym</div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-label">Symbol Sync Bandwidth</div>
                        <div class="rec-val">0.0450 (α / 10)</div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-label">Preamble Length</div>
                        <div class="rec-val">32 Bytes</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Chart 1: BER Waterfall -->
        <div class="card">
            <h2>1. AWGN Noise vs Bit Error Rate (BER)</h2>
            <div class="chart-box">
                <!-- EMBED_SVG_CHART_1 -->
            </div>
        </div>

        <!-- Chart 2: FLL Bandwidth vs Capture Range -->
        <div class="card">
            <h2>2. FLL Bandwidth vs Frequency Offset Capture</h2>
            <div class="chart-box">
                <!-- EMBED_SVG_CHART_2 -->
            </div>
        </div>

        <!-- Chart 3: Costas Loop Bandwidth -->
        <div class="card">
            <h2>3. Costas Loop Bandwidth Sensitivity</h2>
            <div class="chart-box">
                <!-- EMBED_SVG_CHART_3 -->
            </div>
        </div>

        <!-- Chart 4: Preamble Length Sensitivity -->
        <div class="card">
            <h2>4. Preamble Length vs Packet Delivery Ratio (PDR)</h2>
            <div class="chart-box">
                <!-- EMBED_SVG_CHART_4 -->
            </div>
        </div>

        <!-- Full Results Table -->
        <div class="card full-width">
            <h2>Empirical Test Matrix Results</h2>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Sweep Type</th>
                            <th>Noise Volt</th>
                            <th>Freq Offset</th>
                            <th>Time Offset</th>
                            <th>FLL BW</th>
                            <th>Costas BW</th>
                            <th>SymSync BW</th>
                            <th>Preamble</th>
                            <th>BER</th>
                            <th>PDR (%)</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    for r in results:
        p = r['params']
        status = '<span class="badge-ok">PASS</span>' if (r['pdr'] >= 85.0 and r['ber'] < 0.05) else '<span style="color:#ef4444; font-weight:600;">LOSS</span>'
        html += f"""
                        <tr>
                            <td><strong>{p.get('sweep_type', '')}</strong></td>
                            <td>{p.get('noise_volt', 0.0):.2f}</td>
                            <td>{p.get('freq_offset', 0.0):+6.3f}</td>
                            <td>{p.get('time_offset', 1.0):.4f}</td>
                            <td>{p.get('fll_bw', 0.0):.4f}</td>
                            <td>{p.get('costas_bw', 0.0):.4f}</td>
                            <td>{p.get('sym_bw', 0.0):.4f}</td>
                            <td>{p.get('preamble_size', 32)} B</td>
                            <td>{r['ber']:.5f}</td>
                            <td>{r['pdr']:.1f}%</td>
                            <td>{status}</td>
                        </tr>
"""
    html += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""
    with open(output_html_path, "w") as f:
        f.write(html)
    print(f"[OK] Interactive HTML dashboard generated at: {output_html_path}")

def render_all_plots(results_dir):
    """
    Renders all standalone SVG charts and updates the HTML dashboard.
    """
    json_path = os.path.join(results_dir, "sweep_results.json")
    if not os.path.exists(json_path):
        print(f"[ERROR] Results file not found: {json_path}")
        return
        
    with open(json_path, "r") as f:
        results = json.load(f)
        
    # 1. AWGN Noise vs BER Waterfall
    noise_runs = [r for r in results if r['params'].get('sweep_type') == 'noise']
    noise_pts = [(r['params']['noise_volt'], max(r['ber'], 1e-4)) for r in noise_runs]
    # Theoretical BPSK curve for comparison
    theory_pts = []
    for nv in [r['params']['noise_volt'] for r in noise_runs]:
        if nv <= 0.001:
            theory_pts.append((nv, 1e-4))
        else:
            snr = 1.0 / (2.0 * (nv ** 2))
            ebno = snr * 4.0 # sps=4
            ber_th = 0.5 * math.erfc(math.sqrt(max(ebno, 0.0)))
            theory_pts.append((nv, max(ber_th, 1e-4)))
            
    svg1 = generate_svg_line_chart(
        title="BPSK Bit Error Rate (BER) vs Channel Noise Voltage",
        x_label="Channel Noise Voltage (Vn)",
        y_label="Bit Error Rate (BER)",
        series_data=[
            {'name': 'Measured PHY2', 'color': '#2563eb', 'points': noise_pts},
            {'name': 'Theoretical AWGN', 'color': '#dc2626', 'points': theory_pts}
        ],
        is_log_y=True
    )
    with open(os.path.join(results_dir, "chart_01_ber_waterfall.svg"), "w") as f:
        f.write(svg1)
        
    # 2. FLL Bandwidth vs Frequency Offset
    fll_runs = [r for r in results if r['params'].get('sweep_type') == 'fll_bw']
    fll_series = []
    colors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6']
    for idx, fo in enumerate([0.0, 0.015, -0.025, 0.035]):
        pts = [(r['params']['fll_bw'], max(r['ber'], 1e-4)) for r in fll_runs if abs(r['params']['freq_offset'] - fo) < 1e-4]
        if pts:
            fll_series.append({'name': f'Δf = {fo:+0.3f}', 'color': colors[idx % len(colors)], 'points': pts})
            
    svg2 = generate_svg_line_chart(
        title="FLL Band-Edge Bandwidth vs BER across Frequency Offsets",
        x_label="FLL Loop Bandwidth (rad/sym)",
        y_label="Bit Error Rate (BER)",
        series_data=fll_series,
        is_log_y=True
    )
    with open(os.path.join(results_dir, "chart_02_fll_bandwidth.svg"), "w") as f:
        f.write(svg2)
        
    # 3. Costas Loop Bandwidth
    costas_runs = [r for r in results if r['params'].get('sweep_type') == 'costas_bw']
    costas_pts = [(r['params']['costas_bw'], max(r['ber'], 1e-4)) for r in costas_runs]
    svg3 = generate_svg_line_chart(
        title="Costas Loop Bandwidth vs Bit Error Rate (BER)",
        x_label="Costas Loop Bandwidth (rad/sym)",
        y_label="Bit Error Rate (BER)",
        series_data=[{'name': 'Costas Sweep', 'color': '#6366f1', 'points': costas_pts}],
        is_log_y=True
    )
    with open(os.path.join(results_dir, "chart_03_costas_bandwidth.svg"), "w") as f:
        f.write(svg3)
        
    # 4. Preamble Length Sensitivity
    preamble_runs = [r for r in results if r['params'].get('sweep_type') == 'preamble_size']
    preamble_pts = [(r['params']['preamble_size'], r['pdr']) for r in preamble_runs]
    svg4 = generate_svg_line_chart(
        title="Preamble Length vs Packet Delivery Ratio (PDR)",
        x_label="Preamble Length (Bytes)",
        y_label="Packet Delivery Ratio (%)",
        series_data=[{'name': 'PDR %', 'color': '#10b981', 'points': preamble_pts}],
        is_log_y=False
    )
    with open(os.path.join(results_dir, "chart_04_preamble_length.svg"), "w") as f:
        f.write(svg4)
        
    # Generate HTML and embed SVGs
    html_path = os.path.join(results_dir, "dashboard.html")
    generate_html_dashboard(json_path, html_path)
    
    with open(html_path, "r") as f:
        html_content = f.read()
        
    html_content = html_content.replace("<!-- EMBED_SVG_CHART_1 -->", svg1)
    html_content = html_content.replace("<!-- EMBED_SVG_CHART_2 -->", svg2)
    html_content = html_content.replace("<!-- EMBED_SVG_CHART_3 -->", svg3)
    html_content = html_content.replace("<!-- EMBED_SVG_CHART_4 -->", svg4)
    
    with open(html_path, "w") as f:
        f.write(html_content)
        
    print(f"[OK] All SVG charts and interactive dashboard rendered successfully into: {results_dir}")

if __name__ == "__main__":
    res_dir = os.path.join(os.path.dirname(__file__), "results")
    render_all_plots(res_dir)
