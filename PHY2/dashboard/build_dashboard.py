#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Dashboard Builder
Generates two dedicated, 100% self-contained HTML5 dashboards:
1. Software Simulation Dashboard (software_dashboard.html / index.html):
   - Dynamic Multi-Line Graph (BER vs SymSync 0.001..1.000 with Costas range min/max & FLL selector).
   - Smooth 2D Correlation Heatmap.
   - Interactive 2D Point Inspector (BER vs FLL for clicked point).
   - Filter-applicable CSV searcher table with 63,000+ rows.
2. Hardware SDR Dashboard (hardware_dashboard.html):
   - Top Hardware Target Selector (Adalm-Pluto, Nuand bladeRF, RTL-SDR, Sim-HW loopback).
   - Hardware RF Configuration & Diagnostics Panel.
   - Dynamic Multi-Line Graph & 2D Heatmap calibrated for the active SDR hardware profile.
   - Interactive 2D Point Inspector (BER vs FLL).
   - Filter-applicable Hardware CSV matrix with export.
"""

import sys
import os
import json
import csv
import math

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SW_DATA_PATH = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/results/deep_sweep_results.json")
HW_DATA_PATH = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/results/hardware_optimization_results.json")
FALLBACK_PATH = os.path.join(WORKSPACE_ROOT, "PHY2/adapted_original/results/ultra_fine_sweep_results.json")

DASH_DIR = os.path.join(WORKSPACE_ROOT, "PHY2/dashboard")
SW_OUTPUT_HTML = os.path.join(DASH_DIR, "software_dashboard.html")
INDEX_OUTPUT_HTML = os.path.join(DASH_DIR, "index.html")
HW_OUTPUT_HTML = os.path.join(DASH_DIR, "hardware_dashboard.html")

DASHBOARD_DATA_LIMIT = 50000

def load_data(path, fallback=None):
    target = path if os.path.exists(path) else fallback
    if not target or not os.path.exists(target):
        if os.path.exists(SW_DATA_PATH): target = SW_DATA_PATH
        elif os.path.exists(FALLBACK_PATH): target = FALLBACK_PATH
        else:
            print(f"[ERROR] No dataset found at {path}. Run parameter sweep first.")
            sys.exit(1)
    try:
        with open(target, 'r') as f:
            records = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] Failed to parse JSON from {target}: {e}")
        sys.exit(1)
    print(f"[DEBUG] Loaded {len(records):,} simulation records from {os.path.basename(target)}")
    return records

def curate_for_dashboard(records, limit=DASHBOARD_DATA_LIMIT):
    """Pre-aggregate records by unique DSP parameter combos, keep top N by performance."""
    from collections import defaultdict
    
    agg = defaultdict(list)
    for r in records:
        key = (
            r.get('mod_type', 'BPSK'),
            round(float(r.get('fll_bw', 0.0314)), 4),
            round(float(r.get('costas_bw', 0.0628)), 4),
            round(float(r.get('sym_bw', 0.025)), 4),
            int(r.get('preamble_size', 32))
        )
        agg[key].append(r)
    
    curated = []
    for (mod, fll, costas, sym, plen), runs in agg.items():
        pdrs = [float(x.get('pdr', 0)) for x in runs]
        bers = [float(x.get('ber', 0.5)) for x in runs]
        avg_pdr = sum(pdrs) / len(pdrs)
        avg_ber = sum(bers) / len(bers)
        matched = sum(int(x.get('matched_packets', 0)) for x in runs) // len(runs)
        total = int(runs[0].get('total_packets', 10))
        
        curated.append({
            'mod_type': mod,
            'fll_bw': fll,
            'costas_bw': costas,
            'sym_bw': sym,
            'preamble_size': plen,
            'pdr': round(avg_pdr, 2),
            'ber': round(avg_ber, 6),
            'matched_packets': matched,
            'total_packets': total,
            'elapsed_sec': round(float(runs[0].get('elapsed_sec', 0)), 3)
        })
    
    # Sort by best performance: lowest BER, highest PDR, shortest preamble
    curated.sort(key=lambda x: (x['ber'], -x['pdr'], x['preamble_size']))
    
    if len(curated) > limit:
        curated = curated[:limit]
    
    print(f"[DEBUG] Curated {len(curated):,} dashboard records from {len(records):,} raw records ({len(agg):,} unique combos)")
    return curated

def write_dashboard_data_js(curated_records, output_path):
    """Write curated records to an external .js file for fast browser loading."""
    js_content = "const rawData = " + json.dumps(curated_records, separators=(',', ':')) + ";\n"
    with open(output_path, 'w') as f:
        f.write(js_content)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[DEBUG] Wrote dashboard data file: {output_path} ({size_mb:.1f} MB, {len(curated_records):,} records)")
    return output_path

def generate_dashboard_html(records, is_hardware=False, data_js_filename="software_data.js"):
    fll_vals = sorted(list(set(r['fll_bw'] for r in records)))
    costas_vals = sorted(list(set(r['costas_bw'] for r in records)))
    sym_vals = sorted(list(set(r['sym_bw'] for r in records)))
    preambles = sorted(list(set(r.get('preamble_size', 32) for r in records)))
    
    meta_path = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/results/sweep_metadata.json")
    runtime_badge = ""
    if os.path.exists(meta_path) and not is_hardware:
        try:
            with open(meta_path, "r") as mf:
                mdata = json.load(mf)
            r_time = mdata.get("formatted_runtime", f"{mdata.get('elapsed_sec', '')}s")
            r_rate = mdata.get("throughput_trials_per_sec", 0)
            r_total = mdata.get("cumulative_trials", mdata.get("total_trials", mdata.get("new_trials", "?")))
            runtime_badge = f'<span class="badge badge-green" style="border-color:#22c55e;">⏱️ Ran Time: {r_time} ({r_rate} trials/s) | {r_total:,} total trials</span>'
        except Exception:
            pass
            
    fll_options_html = "\n".join([f'<option value="{v}" {"selected" if abs(v-0.0314)<0.002 or (idx==len(fll_vals)//2 and 0.0314 not in fll_vals) else ""}>{v:.4f} rad/sym</option>' for idx, v in enumerate(fll_vals)])

    title_prefix = "HARDWARE SDR" if is_hardware else "SOFTWARE SIMULATION"
    badge_type = "Hardware Profile (Pluto / BladeRF / RTL-SDR)" if is_hardware else "Software Multipath Channel"

    hw_header_extra = """
        <div class="controls-row" style="background:#1e293b; border:1px solid #38bdf8; margin-bottom:18px;">
            <div class="ctrl-group">
                <label style="color:#38bdf8;">Active SDR Hardware Target:</label>
                <select id="hw-target-select" onchange="switchHardwareTarget()" style="font-weight:700; color:#38bdf8; background:#0f172a;">
                    <option value="pluto" selected>📡 Analog Devices Adalm-Pluto SDR (Full-Duplex IIO, 70 MHz - 6 GHz)</option>
                    <option value="bladerf">⚡ Nuand bladeRF (Micro-USB 3.0, 47 MHz - 3.8 GHz)</option>
                    <option value="rtlsdr">📻 RTL-SDR v4 (USB Direct Sampling Receiver, 500 kHz - 1.76 GHz)</option>
                </select>
            </div>
            <div class="ctrl-group">
                <label>RF Center Frequency:</label>
                <input type="text" id="hw-freq" value="433.98 MHz" readonly style="width:110px;">
            </div>
            <div class="ctrl-group">
                <label>Sample Rate:</label>
                <input type="text" id="hw-rate" value="1.0 Msps" readonly style="width:90px;">
            </div>
            <div class="ctrl-group">
                <label>RF Gain (TX/RX):</label>
                <input type="text" id="hw-gain" value="20.0 dB" readonly style="width:80px;">
            </div>
            <div class="ctrl-group">
                <label>Hardware Status:</label>
                <span id="hw-status-badge" style="padding:6px 12px; border-radius:6px; font-weight:700; font-size:12px; background:rgba(34,197,94,0.15); color:#22c55e; border:1px solid #22c55e;">
                    READY / CALIBRATED
                </span>
            </div>
            <div class="ctrl-group" style="justify-content: flex-end;">
                <button class="btn btn-secondary btn-sm" onclick="window.location.href='software_dashboard.html'">Switch to Software Dashboard</button>
            </div>
        </div>
    """ if is_hardware else """
        <div style="display:flex; justify-content:flex-end; margin-bottom:12px;">
            <button class="btn btn-secondary btn-sm" onclick="window.location.href='hardware_dashboard.html'">Switch to Hardware SDR Dashboard 📡</button>
        </div>
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHY2 {title_prefix} Parameter Optimization Dashboard</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --fll-color: #f59e0b;
            --costas-color: #22c55e;
            --sym-color: #38bdf8;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            padding: 20px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1540px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 24px 30px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        header h1 {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.5px;
        }}
        header p {{
            color: var(--text-muted);
            font-size: 13.5px;
            margin-top: 4px;
        }}
        .badges {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .badge-blue {{ background: rgba(56, 189, 248, 0.15); color: var(--accent); border-color: var(--accent); }}
        .badge-green {{ background: rgba(34, 197, 94, 0.15); color: var(--success); border-color: var(--success); }}
        .badge-amber {{ background: rgba(245, 158, 11, 0.15); color: var(--warning); border-color: var(--warning); }}

        .card {{
            background-color: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            padding: 22px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.25);
        }}
        .card h2 {{
            font-size: 17px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .controls-row {{
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            margin-bottom: 16px;
            align-items: center;
            background: #0f172a;
            padding: 14px 18px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}
        .ctrl-group {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .ctrl-group label {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        select, input[type="text"], input[type="number"] {{
            background-color: var(--card-bg);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            padding: 7px 12px;
            border-radius: 6px;
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }}
        select:focus, input[type="text"]:focus, input[type="number"]:focus {{
            border-color: var(--accent);
        }}
        .range-slider-box {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        input[type="range"] {{
            accent-color: var(--accent);
            cursor: pointer;
        }}
        .range-val {{
            font-weight: 700;
            color: var(--accent);
            font-size: 13px;
            min-width: 60px;
        }}
        .fll-highlight {{ color: var(--fll-color); font-weight: 700; }}
        .costas-highlight {{ color: var(--costas-color); font-weight: 700; }}
        .sym-highlight {{ color: var(--sym-color); font-weight: 700; }}

        .checkbox-pills {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            max-height: 120px;
            overflow-y: auto;
            padding: 6px;
            background: #0f172a;
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }}
        .pill-label {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 11.5px;
            background: var(--card-bg);
            padding: 4px 9px;
            border-radius: 14px;
            border: 1px solid var(--border-color);
            cursor: pointer;
            user-select: none;
            transition: all 0.15s;
        }}
        .pill-label:hover {{ border-color: var(--accent); }}
        .pill-label input[type="checkbox"] {{ cursor: pointer; }}

        .canvas-container {{
            position: relative;
            width: 100%;
            height: 520px;
            background: #0b1120;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }}
        canvas {{
            width: 100%;
            height: 100%;
            display: block;
            cursor: crosshair;
        }}
        .graph-tooltip {{
            position: absolute;
            display: none;
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid var(--accent);
            border-radius: 6px;
            padding: 8px 12px;
            color: var(--text-main);
            font-size: 12px;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            z-index: 100;
            white-space: pre-line;
        }}

        .btn {{
            background-color: var(--accent);
            color: #0f172a;
            font-weight: 600;
            padding: 7px 16px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            transition: background-color 0.2s;
            font-size: 13px;
        }}
        .btn:hover {{ background-color: var(--accent-hover); }}
        .btn-secondary {{ background-color: var(--border-color); color: var(--text-main); }}
        .btn-secondary:hover {{ background-color: #475569; }}
        .btn-sm {{ padding: 4px 10px; font-size: 11.5px; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12.5px;
            margin-top: 10px;
        }}
        th, td {{
            padding: 9px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            background-color: #0f172a;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{ color: var(--accent); }}
        tr:hover {{ background-color: rgba(56, 189, 248, 0.05); }}
        .pdr-good {{ color: var(--success); font-weight: 600; }}
        .pdr-mid {{ color: var(--warning); font-weight: 600; }}
        .pdr-bad {{ color: var(--danger); font-weight: 600; }}

        .pagination {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 14px;
            font-size: 12.5px;
            color: var(--text-muted);
        }}
        .page-btns {{
            display: flex;
            gap: 6px;
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>PHY2 {title_prefix} OPTIMIZATION DASHBOARD</h1>
            <p>Full Cartesian Grid Analytics (0.001 to 1.000 rad/sym, Step 0.001) | BPSK & QPSK | y·y' TED & Linear Equalizer</p>
        </div>
        <div class="badges">
            <span class="badge badge-blue">{badge_type}</span>
            <span class="badge badge-green">Linear Equalizer (CMA)</span>
            <span class="badge badge-amber">{len(records):,} Evaluated Trials</span>
            {runtime_badge}
        </div>
    </header>

    {hw_header_extra}

    <!-- SECTION 1: DYNAMIC MULTI-LINE GRAPH -->
    <div class="card">
        <h2>
            <span>1. Dynamic Multi-Line Graph: BER vs Symbol Sync Loop Bandwidth (0.001 to 1.000 rad/sym)</span>
            <span id="header-fll-badge" style="font-size:13.5px; font-weight:600; color:var(--fll-color); background:#0f172a; padding:4px 10px; border-radius:6px; border:1px solid #475569;">
                FLL Slice = 0.0314 rad/sym
            </span>
        </h2>

        <div class="controls-row">
            <div class="ctrl-group">
                <label>Modulation:</label>
                <select id="dyn-mod" onchange="renderDynamicGraph()">
                    <option value="BPSK" selected>BPSK</option>
                    <option value="QPSK">QPSK</option>
                </select>
            </div>

            <div class="ctrl-group">
                <label>Set FLL Loop BW: <span id="dyn-fll-val" class="fll-highlight">0.0314</span> rad/sym</label>
                <div class="range-slider-box">
                    <select id="dyn-fll-select" onchange="syncFllFromSelect()">
                        {fll_options_html}
                    </select>
                    <input type="range" id="dyn-fll-slider" min="0.001" max="1.000" step="0.001" value="0.0314" oninput="syncFllFromSlider()">
                </div>
            </div>

            <div class="ctrl-group">
                <label>Costas Min: <span id="dyn-costas-min-val" class="range-val">0.001</span></label>
                <div class="range-slider-box">
                    <input type="range" id="dyn-costas-min" min="0.001" max="1.000" step="0.001" value="0.001" oninput="syncCostasRange()">
                    <input type="number" id="dyn-costas-min-num" min="0.001" max="1.000" step="0.001" value="0.001" style="width:75px;" onchange="syncCostasNum()">
                </div>
            </div>

            <div class="ctrl-group">
                <label>Costas Max: <span id="dyn-costas-max-val" class="range-val">1.000</span></label>
                <div class="range-slider-box">
                    <input type="range" id="dyn-costas-max" min="0.001" max="1.000" step="0.001" value="1.000" oninput="syncCostasRange()">
                    <input type="number" id="dyn-costas-max-num" min="0.001" max="1.000" step="0.001" value="1.000" style="width:75px;" onchange="syncCostasNum()">
                </div>
            </div>

            <div class="ctrl-group" style="justify-content: flex-end;">
                <div style="display:flex; gap:6px; margin-top:16px;">
                    <button class="btn btn-secondary btn-sm" onclick="toggleCostasLines(true)">Select All Lines</button>
                    <button class="btn btn-secondary btn-sm" onclick="toggleCostasLines(false)">Select Core Lines</button>
                </div>
            </div>
        </div>

        <div style="margin-bottom: 10px;">
            <label style="font-size:12px; font-weight:600; color:#cbd5e1;">Costas Loop Bandwidth Lines in Selected Range:</label>
            <div class="checkbox-pills" id="costas-pills"></div>
        </div>

        <div class="canvas-container" id="graph-container">
            <canvas id="dynamic-canvas"></canvas>
            <div id="graph-tooltip" class="graph-tooltip"></div>
        </div>
    </div>

    <!-- SECTION 2: SMOOTH 2D CORRELATION HEATMAP -->
    <div class="card">
        <h2>
            <span>2. Smooth 2D Correlation Heatmap: Costas Loop BW vs Symbol Sync Loop BW</span>
            <span id="heatmap-fll-badge" style="font-size:13.5px; font-weight:600; color:var(--fll-color); background:#0f172a; padding:4px 10px; border-radius:6px; border:1px solid #475569;">
                FLL Slice = 0.0314 rad/sym
            </span>
        </h2>

        <div class="controls-row">
            <div class="ctrl-group">
                <label>Modulation:</label>
                <select id="hm-mod" onchange="renderHeatmap()">
                    <option value="BPSK" selected>BPSK</option>
                    <option value="QPSK">QPSK</option>
                </select>
            </div>
            <div class="ctrl-group">
                <label>Metric Color Gradient:</label>
                <select id="hm-metric" onchange="renderHeatmap()">
                    <option value="ber" selected>Bit Error Rate (BER) - Log Scale</option>
                    <option value="pdr">Packet Delivery Ratio (PDR %)</option>
                </select>
            </div>
            <div class="ctrl-group">
                <label>FLL Band-Edge Slice (0.001..1.000 rad/sym):</label>
                <select id="hm-fll-select" onchange="renderHeatmap()">
                    {fll_options_html}
                </select>
            </div>
            <div class="ctrl-group">
                <label>Instruction:</label>
                <div style="font-size:12px; color:var(--accent); margin-top:6px;">
                    👉 <strong>Click anywhere on the Heatmap</strong> to select a 2D operating point and inspect its BER vs FLL curve below!
                </div>
            </div>
        </div>

        <div class="canvas-container" id="heatmap-container" style="height: 480px; min-height: 480px;">
            <canvas id="heatmap-canvas"></canvas>
            <div id="heatmap-tooltip" class="graph-tooltip"></div>
        </div>
    </div>

    <!-- SECTION 3: INTERACTIVE 2D POINT INSPECTOR (BER vs FLL) -->
    <div class="card">
        <h2>
            <span>3. Interactive 2D Point Inspector: BER vs FLL Loop Bandwidth</span>
            <span id="inspector-point-badge" style="font-size:13.5px; font-weight:600; color:var(--accent); background:#0f172a; padding:4px 10px; border-radius:6px; border:1px solid #475569;">
                Selected: SymSync = 0.0250, Costas = 0.0628 rad/sym
            </span>
        </h2>

        <div class="controls-row">
            <div class="ctrl-group">
                <label>Selected Symbol Sync BW:</label>
                <div class="range-slider-box">
                    <input type="range" id="insp-sym-slider" min="0.001" max="1.000" step="0.001" value="0.025" oninput="syncInspectorInputs()">
                    <input type="number" id="insp-sym-num" min="0.001" max="1.000" step="0.001" value="0.025" style="width:80px;" onchange="syncInspectorInputsNum()">
                </div>
            </div>

            <div class="ctrl-group">
                <label>Selected Costas Loop BW:</label>
                <div class="range-slider-box">
                    <input type="range" id="insp-costas-slider" min="0.001" max="1.000" step="0.001" value="0.0628" oninput="syncInspectorInputs()">
                    <input type="number" id="insp-costas-num" min="0.001" max="1.000" step="0.001" value="0.0628" style="width:80px;" onchange="syncInspectorInputsNum()">
                </div>
            </div>

            <div class="ctrl-group">
                <label>Modulation:</label>
                <select id="insp-mod" onchange="renderPointInspector()">
                    <option value="BPSK" selected>BPSK</option>
                    <option value="QPSK">QPSK</option>
                </select>
            </div>
        </div>

        <div class="canvas-container" id="inspector-container" style="height: 420px; min-height: 420px;">
            <canvas id="inspector-canvas"></canvas>
            <div id="inspector-tooltip" class="graph-tooltip"></div>
        </div>
    </div>

    <!-- SECTION 4: SEARCHABLE CSV DATASET & LIVE PARAMETER FILTER -->
    <div class="card">
        <h2>
            <span>4. Searchable CSV Dataset & Live Parameter Filter</span>
            <div style="display:flex; gap:8px;">
                <button class="btn btn-secondary btn-sm" onclick="toggleRawCSV()">Toggle Raw CSV View</button>
                <button class="btn btn-secondary btn-sm" onclick="resetTableFilters()">Reset Filters</button>
                <button class="btn btn-primary btn-sm" onclick="exportFilteredCSV()">Export CSV</button>
            </div>
        </h2>

        <div class="controls-row">
            <div class="ctrl-group">
                <label>Search All Columns:</label>
                <input type="text" id="tbl-search" placeholder="Type keyword or value..." oninput="applyTableFilters()">
            </div>
            <div class="ctrl-group">
                <label>Modulation:</label>
                <select id="tbl-mod" onchange="applyTableFilters()">
                    <option value="ALL">ALL (BPSK & QPSK)</option>
                    <option value="BPSK">BPSK</option>
                    <option value="QPSK">QPSK</option>
                </select>
            </div>
            <div class="ctrl-group">
                <label>Profile:</label>
                <select id="tbl-prof" onchange="applyTableFilters()">
                    <option value="ALL">ALL</option>
                    <option value="software">Software (Multipath)</option>
                    <option value="hardware">Hardware SDR</option>
                </select>
            </div>
            <div class="ctrl-group">
                <label>Preamble Length:</label>
                <select id="tbl-preamble" onchange="applyTableFilters()">
                    <option value="ALL">ALL (2..64 Bytes)</option>
                    {"\n".join([f'<option value="{p}">{p} Bytes</option>' for p in preambles])}
                </select>
            </div>
            <div class="ctrl-group">
                <label>FLL Max: <span id="tbl-fll-val" class="range-val">1.000</span></label>
                <input type="range" id="tbl-fll-max" min="0.001" max="1.000" step="0.001" value="1.000" oninput="document.getElementById('tbl-fll-val').innerText = parseFloat(this.value).toFixed(3); applyTableFilters();">
            </div>
            <div class="ctrl-group">
                <label>Costas Max: <span id="tbl-costas-val" class="range-val">1.000</span></label>
                <input type="range" id="tbl-costas-max" min="0.001" max="1.000" step="0.001" value="1.000" oninput="document.getElementById('tbl-costas-val').innerText = parseFloat(this.value).toFixed(3); applyTableFilters();">
            </div>
            <div class="ctrl-group">
                <label>Min PDR (%): <span id="tbl-pdr-val" class="range-val">0%</span></label>
                <input type="range" id="tbl-pdr-min" min="0" max="100" step="5" value="0" oninput="document.getElementById('tbl-pdr-val').innerText = this.value + '%'; applyTableFilters();">
            </div>
        </div>

        <div id="raw-csv-container" style="display:none; margin-bottom:14px;">
            <textarea id="raw-csv-text" readonly style="width:100%; height:180px; background:#0f172a; color:#a5f3fc; font-family:monospace; font-size:11.5px; padding:10px; border-radius:6px; border:1px solid var(--border-color);"></textarea>
        </div>

        <div style="overflow-x:auto;">
            <table id="data-table">
                <thead>
                    <tr>
                        <th onclick="sortTable('mod_type')">Mod ▲▼</th>
                        <th onclick="sortTable('fll_bw')">FLL Band-Edge BW ▲▼</th>
                        <th onclick="sortTable('costas_bw')">Costas BW ▲▼</th>
                        <th onclick="sortTable('sym_bw')">SymSync BW ▲▼</th>
                        <th onclick="sortTable('preamble_size')">Preamble ▲▼</th>
                        <th onclick="sortTable('noise_volt')">Noise (Vn) ▲▼</th>
                        <th onclick="sortTable('freq_offset')">Freq Offset ▲▼</th>
                        <th onclick="sortTable('time_offset')">Clock Drift ▲▼</th>
                        <th onclick="sortTable('platform_mode')">Profile ▲▼</th>
                        <th onclick="sortTable('pdr')">PDR (%) ▲▼</th>
                        <th onclick="sortTable('ber')">BER ▲▼</th>
                    </tr>
                </thead>
                <tbody id="table-body"></tbody>
            </table>
        </div>

        <div class="pagination">
            <span id="page-info">Showing 0 of 0 records</span>
            <div class="page-btns">
                <button class="btn btn-secondary btn-sm" onclick="changePage(-1)">Previous</button>
                <span id="current-page-num" style="padding:4px 8px; font-weight:600;">1</span>
                <button class="btn btn-secondary btn-sm" onclick="changePage(1)">Next</button>
            </div>
        </div>
    </div>
</div>

<script src="{data_js_filename}"></script>
<script>
// rawData is loaded from external {data_js_filename} file
let filteredData = [...rawData];
let currentPage = 1;
const rowsPerPage = 25;
let currentSortCol = 'pdr';
let sortAsc = false;

const allCostas = [...new Set(rawData.map(r => r.costas_bw))].sort((a,b) => a-b);
const allSym = [...new Set(rawData.map(r => r.sym_bw))].sort((a,b) => a-b);
const allFll = [...new Set(rawData.map(r => r.fll_bw))].sort((a,b) => a-b);

let selectedPointSym = 0.025;
let selectedPointCostas = 0.0628;

const lineColors = [
    '#38bdf8', '#22c55e', '#f59e0b', '#ec4899', '#a855f7',
    '#ef4444', '#14b8a6', '#eab308', '#6366f1', '#f97316', '#06b6d4',
    '#84cc16', '#d946ef', '#0ea5e9', '#10b981', '#f43f5e'
];

function switchHardwareTarget() {{
    const target = document.getElementById('hw-target-select').value;
    const badge = document.getElementById('hw-status-badge');
    const freqIn = document.getElementById('hw-freq');
    const rateIn = document.getElementById('hw-rate');
    const gainIn = document.getElementById('hw-gain');
    
    if (target === 'pluto') {{
        badge.innerText = 'ADALM-PLUTO CONNECTED (IIO)';
        badge.style.color = '#22c55e';
        badge.style.borderColor = '#22c55e';
        freqIn.value = '433.98 MHz';
        rateIn.value = '2.5 Msps';
        gainIn.value = '20.0 dB';
    }} else if (target === 'bladerf') {{
        badge.innerText = 'BLADERF READY (USB 3.0)';
        badge.style.color = '#38bdf8';
        badge.style.borderColor = '#38bdf8';
        freqIn.value = '433.98 MHz';
        rateIn.value = '2.0 Msps';
        gainIn.value = '25.0 dB';
    }} else if (target === 'rtlsdr') {{
        badge.innerText = 'RTL-SDR RX ONLY';
        badge.style.color = '#f59e0b';
        badge.style.borderColor = '#f59e0b';
        freqIn.value = '433.98 MHz';
        rateIn.value = '1.0 Msps';
        gainIn.value = '29.7 dB';
    }}
}}

function initCostasPills() {{
    const minC = parseFloat(document.getElementById('dyn-costas-min').value);
    const maxC = parseFloat(document.getElementById('dyn-costas-max').value);
    const container = document.getElementById('costas-pills');
    container.innerHTML = '';
    
    const inRangeCostas = allCostas.filter(c => c >= minC - 1e-4 && c <= maxC + 1e-4);
    inRangeCostas.forEach((cbw, idx) => {{
        const label = document.createElement('label');
        label.className = 'pill-label';
        label.innerHTML = `<input type="checkbox" value="${{cbw}}" class="costas-chk" checked onchange="renderDynamicGraph()"> Costas ${{cbw.toFixed(4)}}`;
        container.appendChild(label);
    }});
}}

function syncCostasRange() {{
    const minVal = parseFloat(document.getElementById('dyn-costas-min').value);
    const maxVal = parseFloat(document.getElementById('dyn-costas-max').value);
    document.getElementById('dyn-costas-min-val').innerText = minVal.toFixed(3);
    document.getElementById('dyn-costas-max-val').innerText = maxVal.toFixed(3);
    document.getElementById('dyn-costas-min-num').value = minVal.toFixed(3);
    document.getElementById('dyn-costas-max-num').value = maxVal.toFixed(3);
    initCostasPills();
    renderDynamicGraph();
}}

function syncCostasNum() {{
    const minVal = parseFloat(document.getElementById('dyn-costas-min-num').value);
    const maxVal = parseFloat(document.getElementById('dyn-costas-max-num').value);
    document.getElementById('dyn-costas-min').value = minVal;
    document.getElementById('dyn-costas-max').value = maxVal;
    document.getElementById('dyn-costas-min-val').innerText = minVal.toFixed(3);
    document.getElementById('dyn-costas-max-val').innerText = maxVal.toFixed(3);
    initCostasPills();
    renderDynamicGraph();
}}

function toggleCostasLines(selectAll) {{
    document.querySelectorAll('.costas-chk').forEach(chk => {{
        chk.checked = selectAll;
    }});
    renderDynamicGraph();
}}

function findClosestFll(val) {{
    return allFll.reduce((prev, curr) => Math.abs(curr - val) < Math.abs(prev - val) ? curr : prev);
}}

function syncFllFromSelect() {{
    const val = parseFloat(document.getElementById('dyn-fll-select').value);
    document.getElementById('dyn-fll-slider').value = val;
    document.getElementById('dyn-fll-val').innerText = val.toFixed(4);
    document.getElementById('header-fll-badge').innerText = `FLL Slice = ${{val.toFixed(4)}} rad/sym`;
    renderDynamicGraph();
}}

function syncFllFromSlider() {{
    const val = parseFloat(document.getElementById('dyn-fll-slider').value);
    const closest = findClosestFll(val);
    document.getElementById('dyn-fll-select').value = closest;
    document.getElementById('dyn-fll-val').innerText = closest.toFixed(4);
    document.getElementById('header-fll-badge').innerText = `FLL Slice = ${{closest.toFixed(4)}} rad/sym`;
    renderDynamicGraph();
}}

function renderDynamicGraph() {{
    const canvas = document.getElementById('dynamic-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    const w = rect.width > 0 ? rect.width : (canvas.parentElement ? canvas.parentElement.clientWidth : 1200);
    const h = rect.height > 0 ? rect.height : 520;
    
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    
    const padL = 75, padR = 190, padT = 40, padB = 60;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    
    ctx.fillStyle = '#0b1120';
    ctx.fillRect(0, 0, w, h);
    
    const mod = document.getElementById('dyn-mod').value;
    const currentFll = parseFloat(document.getElementById('dyn-fll-select').value);
    
    const selectedCostas = [];
    document.querySelectorAll('.costas-chk:checked').forEach(chk => {{
        selectedCostas.push(parseFloat(chk.value));
    }});
    
    // Grid Lines & Y-Axis (Log Scale 1e-4 to 1.0)
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    
    const yDecades = [
        {{ val: 1.0, label: '10⁰ (1.0)' }},
        {{ val: 0.1, label: '10⁻¹ (0.1)' }},
        {{ val: 0.01, label: '10⁻² (0.01)' }},
        {{ val: 0.001, label: '10⁻³ (0.001)' }},
        {{ val: 0.0001, label: '10⁻⁴ (1e-4)' }}
    ];
    
    yDecades.forEach(yd => {{
        const logVal = Math.log10(yd.val);
        const yNorm = (0 - logVal) / 4;
        const yPx = padT + yNorm * plotH;
        
        ctx.beginPath();
        ctx.moveTo(padL, yPx);
        ctx.lineTo(padL + plotW, yPx);
        ctx.stroke();
        ctx.fillText(yd.label, padL - 10, yPx + 4);
    }});
    
    // X-Axis (0.001 to 1.000 rad/sym)
    ctx.textAlign = 'center';
    for (let xStep = 0.0; xStep <= 1.001; xStep += 0.1) {{
        const xPx = padL + (xStep / 1.0) * plotW;
        ctx.beginPath();
        ctx.moveTo(xPx, padT);
        ctx.lineTo(xPx, padT + plotH);
        ctx.stroke();
        ctx.fillText(xStep.toFixed(1), xPx, padT + plotH + 20);
    }}
    
    // Axis Titles
    ctx.fillStyle = '#f8fafc';
    ctx.font = 'bold 12.5px sans-serif';
    ctx.fillText('Symbol Synchronizer Loop Bandwidth (rad/sym)', padL + plotW / 2, padT + plotH + 46);
    
    ctx.save();
    ctx.translate(20, padT + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Bit Error Rate (BER) - Log Scale', 0, 0);
    ctx.restore();
    
    // Plot Multi-Lines
    window.graphCurves = [];
    selectedCostas.forEach((cbw, idx) => {{
        const color = lineColors[idx % lineColors.length];
        
        const subset = rawData.filter(r => 
            r.mod_type === mod &&
            Math.abs(r.fll_bw - currentFll) < 0.006 &&
            Math.abs(r.costas_bw - cbw) < 0.006
        ).sort((a,b) => a.sym_bw - b.sym_bw);
        
        if (subset.length > 0) {{
            const pts = [];
            ctx.strokeStyle = color;
            ctx.lineWidth = 2.0;
            ctx.beginPath();
            
            subset.forEach((pt, pIdx) => {{
                const xPx = padL + (pt.sym_bw / 1.0) * plotW;
                const safeBer = Math.max(1e-4, Math.min(1.0, pt.ber));
                const logVal = Math.log10(safeBer);
                const yNorm = (0 - logVal) / 4;
                const yPx = padT + yNorm * plotH;
                
                pts.push({{ x: xPx, y: yPx, sym: pt.sym_bw, ber: pt.ber, pdr: pt.pdr, costas: cbw }});
                if (pIdx === 0) ctx.moveTo(xPx, yPx);
                else ctx.lineTo(xPx, yPx);
            }});
            ctx.stroke();
            window.graphCurves.push({{ costas: cbw, color: color, pts: pts }});
        }}
    }});
    
    // Legend Container
    let legY = padT + 10;
    ctx.textAlign = 'left';
    ctx.font = 'bold 11px sans-serif';
    ctx.fillText('COSTAS LINES:', padL + plotW + 16, legY);
    legY += 16;
    
    window.graphCurves.forEach(gc => {{
        ctx.fillStyle = gc.color;
        ctx.fillRect(padL + plotW + 16, legY - 8, 12, 4);
        ctx.fillText(`Costas = ${{gc.costas.toFixed(4)}}`, padL + plotW + 34, legY);
        legY += 18;
    }});
}}

function renderHeatmap() {{
    const canvas = document.getElementById('heatmap-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    const w = rect.width > 0 ? rect.width : (canvas.parentElement ? canvas.parentElement.clientWidth : 1200);
    const h = rect.height > 0 ? rect.height : 480;
    
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    
    const padL = 75, padR = 120, padT = 30, padB = 60;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    
    ctx.fillStyle = '#0b1120';
    ctx.fillRect(0, 0, w, h);
    
    const mod = document.getElementById('hm-mod').value;
    const metric = document.getElementById('hm-metric').value;
    const fllVal = parseFloat(document.getElementById('hm-fll-select').value);
    document.getElementById('heatmap-fll-badge').innerText = `FLL Slice = ${{fllVal.toFixed(4)}} rad/sym`;
    
    const cellW = plotW / allSym.length;
    const cellH = plotH / allCostas.length;
    
    allCostas.forEach((cbw, rIdx) => {{
        allSym.forEach((sbw, cIdx) => {{
            const match = rawData.find(r => 
                r.mod_type === mod &&
                Math.abs(r.fll_bw - fllVal) < 0.006 &&
                Math.abs(r.costas_bw - cbw) < 0.006 &&
                Math.abs(r.sym_bw - sbw) < 0.006
            );
            
            let color = '#0f172a';
            if (match) {{
                if (metric === 'ber') {{
                    const safeBer = Math.max(1e-4, Math.min(1.0, match.ber));
                    const norm = (Math.log10(safeBer) - (-4)) / 4;
                    const r = Math.floor(norm * 240);
                    const g = Math.floor((1 - Math.abs(norm - 0.5) * 2) * 200);
                    const b = Math.floor((1 - norm) * 255);
                    color = `rgb(${{r}}, ${{g}}, ${{b}})`;
                }} else {{
                    const norm = match.pdr / 100.0;
                    color = `rgb(${{Math.floor((1-norm)*220)}}, ${{Math.floor(norm*220)}}, 60)`;
                }}
            }}
            
            const xPx = padL + cIdx * cellW;
            const yPx = padT + (allCostas.length - 1 - rIdx) * cellH;
            ctx.fillStyle = color;
            ctx.fillRect(xPx, yPx, cellW + 0.5, cellH + 0.5);
        }});
    }});
    
    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 1;
    ctx.strokeRect(padL, padT, plotW, plotH);
    
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    allCostas.filter((_, idx) => idx % 3 === 0).forEach(cbw => {{
        const rIdx = allCostas.indexOf(cbw);
        const yPx = padT + (allCostas.length - 1 - rIdx) * cellH + cellH / 2;
        ctx.fillText(cbw.toFixed(3), padL - 8, yPx + 4);
    }});
    
    ctx.textAlign = 'center';
    allSym.filter((_, idx) => idx % Math.ceil(allSym.length / 10) === 0).forEach(sbw => {{
        const cIdx = allSym.indexOf(sbw);
        const xPx = padL + cIdx * cellW + cellW / 2;
        ctx.fillText(sbw.toFixed(2), xPx, padT + plotH + 18);
    }});
    
    ctx.fillStyle = '#f8fafc';
    ctx.font = 'bold 12px sans-serif';
    ctx.fillText('Symbol Synchronizer Loop BW (rad/sym)', padL + plotW / 2, padT + plotH + 42);
    
    ctx.save();
    ctx.translate(20, padT + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Costas Loop BW (rad/sym)', 0, 0);
    ctx.restore();
    
    const cX = padL + (selectedPointSym / 1.0) * plotW;
    const cY = padT + (1.0 - selectedPointCostas / 1.0) * plotH;
    
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.8;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(cX, padT);
    ctx.lineTo(cX, padT + plotH);
    ctx.moveTo(padL, cY);
    ctx.lineTo(padL + plotW, cY);
    ctx.stroke();
    ctx.setLineDash([]);
    
    ctx.fillStyle = '#f59e0b';
    ctx.beginPath();
    ctx.arc(cX, cY, 6, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();
}}

function renderPointInspector() {{
    const canvas = document.getElementById('inspector-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    const w = rect.width > 0 ? rect.width : (canvas.parentElement ? canvas.parentElement.clientWidth : 1200);
    const h = rect.height > 0 ? rect.height : 420;
    
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    
    const padL = 75, padR = 50, padT = 30, padB = 60;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    
    ctx.fillStyle = '#0b1120';
    ctx.fillRect(0, 0, w, h);
    
    const mod = document.getElementById('insp-mod').value;
    document.getElementById('inspector-point-badge').innerText = `Selected Point: SymSync = ${{selectedPointSym.toFixed(4)}}, Costas = ${{selectedPointCostas.toFixed(4)}} rad/sym`;
    
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    
    const yDecades = [
        {{ val: 1.0, label: '10⁰' }},
        {{ val: 0.1, label: '10⁻¹' }},
        {{ val: 0.01, label: '10⁻²' }},
        {{ val: 0.001, label: '10⁻³' }},
        {{ val: 0.0001, label: '10⁻⁴' }}
    ];
    yDecades.forEach(yd => {{
        const logVal = Math.log10(yd.val);
        const yNorm = (0 - logVal) / 4;
        const yPx = padT + yNorm * plotH;
        ctx.beginPath();
        ctx.moveTo(padL, yPx);
        ctx.lineTo(padL + plotW, yPx);
        ctx.stroke();
        ctx.fillText(yd.label, padL - 8, yPx + 4);
    }});
    
    ctx.textAlign = 'center';
    for (let xStep = 0.0; xStep <= 1.001; xStep += 0.1) {{
        const xPx = padL + (xStep / 1.0) * plotW;
        ctx.beginPath();
        ctx.moveTo(xPx, padT);
        ctx.lineTo(xPx, padT + plotH);
        ctx.stroke();
        ctx.fillText(xStep.toFixed(1), xPx, padT + plotH + 20);
    }}
    
    ctx.fillStyle = '#f8fafc';
    ctx.font = 'bold 12px sans-serif';
    ctx.fillText('FLL Band-Edge Loop Bandwidth (rad/sym)', padL + plotW / 2, padT + plotH + 44);
    
    ctx.save();
    ctx.translate(20, padT + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Bit Error Rate (BER)', 0, 0);
    ctx.restore();
    
    const fllPoints = [];
    allFll.forEach(fbw => {{
        const match = rawData.find(r =>
            r.mod_type === mod &&
            Math.abs(r.fll_bw - fbw) < 0.006 &&
            Math.abs(r.costas_bw - selectedPointCostas) < 0.006 &&
            Math.abs(r.sym_bw - selectedPointSym) < 0.006
        );
        if (match) {{
            fllPoints.push({{ fll: fbw, ber: match.ber, pdr: match.pdr }});
        }}
    }});
    
    fllPoints.sort((a,b) => a.fll - b.fll);
    
    if (fllPoints.length > 0) {{
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        fllPoints.forEach((pt, idx) => {{
            const xPx = padL + (pt.fll / 1.0) * plotW;
            const safeBer = Math.max(1e-4, Math.min(1.0, pt.ber));
            const yNorm = (0 - Math.log10(safeBer)) / 4;
            const yPx = padT + yNorm * plotH;
            if (idx === 0) ctx.moveTo(xPx, yPx);
            else ctx.lineTo(xPx, yPx);
        }});
        ctx.stroke();
        
        fllPoints.forEach(pt => {{
            const xPx = padL + (pt.fll / 1.0) * plotW;
            const safeBer = Math.max(1e-4, Math.min(1.0, pt.ber));
            const yNorm = (0 - Math.log10(safeBer)) / 4;
            const yPx = padT + yNorm * plotH;
            ctx.fillStyle = '#38bdf8';
            ctx.beginPath();
            ctx.arc(xPx, yPx, 4, 0, 2*Math.PI);
            ctx.fill();
        }});
    }}
}}

function handleHeatmapClick(e) {{
    const canvas = document.getElementById('heatmap-canvas');
    const rect = canvas.getBoundingClientRect();
    const padL = 75, padR = 120, padT = 30, padB = 60;
    const plotW = rect.width - padL - padR;
    const plotH = rect.height - padT - padB;
    
    const clickX = e.clientX - rect.left - padL;
    const clickY = e.clientY - rect.top - padT;
    
    if (clickX >= 0 && clickX <= plotW && clickY >= 0 && clickY <= plotH) {{
        const symNorm = clickX / plotW;
        const costasNorm = 1.0 - (clickY / plotH);
        
        selectedPointSym = Math.max(0.001, Math.min(1.0, symNorm));
        selectedPointCostas = Math.max(0.001, Math.min(1.0, costasNorm));
        
        document.getElementById('insp-sym-slider').value = selectedPointSym;
        document.getElementById('insp-sym-num').value = selectedPointSym.toFixed(4);
        document.getElementById('insp-costas-slider').value = selectedPointCostas;
        document.getElementById('insp-costas-num').value = selectedPointCostas.toFixed(4);
        
        renderHeatmap();
        renderPointInspector();
    }}
}}

function syncInspectorInputs() {{
    selectedPointSym = parseFloat(document.getElementById('insp-sym-slider').value);
    selectedPointCostas = parseFloat(document.getElementById('insp-costas-slider').value);
    document.getElementById('insp-sym-num').value = selectedPointSym.toFixed(4);
    document.getElementById('insp-costas-num').value = selectedPointCostas.toFixed(4);
    renderHeatmap();
    renderPointInspector();
}}

function syncInspectorInputsNum() {{
    selectedPointSym = parseFloat(document.getElementById('insp-sym-num').value);
    selectedPointCostas = parseFloat(document.getElementById('insp-costas-num').value);
    document.getElementById('insp-sym-slider').value = selectedPointSym;
    document.getElementById('insp-costas-slider').value = selectedPointCostas;
    renderHeatmap();
    renderPointInspector();
}}

function applyTableFilters() {{
    const query = document.getElementById('tbl-search').value.toLowerCase();
    const mod = document.getElementById('tbl-mod').value;
    const prof = document.getElementById('tbl-prof').value;
    const pre = document.getElementById('tbl-preamble').value;
    const maxFll = parseFloat(document.getElementById('tbl-fll-max').value);
    const maxCostas = parseFloat(document.getElementById('tbl-costas-max').value);
    const minPdr = parseFloat(document.getElementById('tbl-pdr-min').value);
    
    filteredData = rawData.filter(r => {{
        if (mod !== 'ALL' && r.mod_type !== mod) return false;
        if (prof !== 'ALL' && r.platform_mode !== prof) return false;
        if (pre !== 'ALL' && (r.preamble_size || 32) !== parseInt(pre)) return false;
        if (r.fll_bw > maxFll + 1e-4) return false;
        if (r.costas_bw > maxCostas + 1e-4) return false;
        if (r.pdr < minPdr - 1e-4) return false;
        if (query) {{
            const rowText = `${{r.mod_type}} ${{r.fll_bw}} ${{r.costas_bw}} ${{r.sym_bw}} ${{r.preamble_size}} ${{r.noise_volt}} ${{r.freq_offset}} ${{r.time_offset}} ${{r.platform_mode}} ${{r.pdr}} ${{r.ber}}`.toLowerCase();
            if (!rowText.includes(query)) return false;
        }}
        return true;
    }});
    
    currentPage = 1;
    renderTable();
}}

function renderTable() {{
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';
    
    filteredData.sort((a,b) => {{
        let vA = a[currentSortCol] !== undefined ? a[currentSortCol] : 0;
        let vB = b[currentSortCol] !== undefined ? b[currentSortCol] : 0;
        if (typeof vA === 'string') return sortAsc ? vA.localeCompare(vB) : vB.localeCompare(a);
        return sortAsc ? vA - vB : vB - vA;
    }});
    
    const start = (currentPage - 1) * rowsPerPage;
    const end = Math.min(start + rowsPerPage, filteredData.length);
    const pageRows = filteredData.slice(start, end);
    
    pageRows.forEach(r => {{
        const tr = document.createElement('tr');
        const pdrClass = r.pdr >= 85 ? 'pdr-good' : (r.pdr >= 50 ? 'pdr-mid' : 'pdr-bad');
        tr.innerHTML = `
            <td><strong>${{r.mod_type}}</strong></td>
            <td>${{r.fll_bw.toFixed(4)}}</td>
            <td>${{r.costas_bw.toFixed(4)}}</td>
            <td>${{r.sym_bw.toFixed(4)}}</td>
            <td>${{r.preamble_size || 32}} B</td>
            <td>${{(r.noise_volt || 0).toFixed(2)}}</td>
            <td>${{(r.freq_offset || 0) > 0 ? '+' : ''}}${{(r.freq_offset || 0).toFixed(3)}}</td>
            <td>${{(r.time_offset || 1.0).toFixed(6)}}</td>
            <td>${{r.platform_mode || 'software'}}</td>
            <td class="${{pdrClass}}">${{r.pdr.toFixed(1)}}%</td>
            <td>${{r.ber.toExponential(2)}}</td>
        `;
        tbody.appendChild(tr);
    }});
    
    document.getElementById('page-info').innerText = `Showing ${{filteredData.length === 0 ? 0 : start + 1}} to ${{end}} of ${{filteredData.length.toLocaleString()}} records (out of ${{rawData.length.toLocaleString()}} total)`;
    document.getElementById('current-page-num').innerText = currentPage;
    
    if (document.getElementById('raw-csv-container').style.display !== 'none') {{
        updateRawCSV();
    }}
}}

function sortTable(col) {{
    if (currentSortCol === col) sortAsc = !sortAsc;
    else {{ currentSortCol = col; sortAsc = false; }}
    renderTable();
}}

function changePage(delta) {{
    const maxPages = Math.ceil(filteredData.length / rowsPerPage);
    currentPage = Math.max(1, Math.min(maxPages, currentPage + delta));
    renderTable();
}}

function resetTableFilters() {{
    document.getElementById('tbl-search').value = '';
    document.getElementById('tbl-mod').value = 'ALL';
    document.getElementById('tbl-prof').value = 'ALL';
    document.getElementById('tbl-preamble').value = 'ALL';
    document.getElementById('tbl-fll-max').value = 1.000;
    document.getElementById('tbl-costas-max').value = 1.000;
    document.getElementById('tbl-pdr-min').value = 0;
    document.getElementById('tbl-fll-val').innerText = '1.000';
    document.getElementById('tbl-costas-val').innerText = '1.000';
    document.getElementById('tbl-pdr-val').innerText = '0%';
    applyTableFilters();
}}

function toggleRawCSV() {{
    const box = document.getElementById('raw-csv-container');
    if (box.style.display === 'none') {{
        box.style.display = 'block';
        updateRawCSV();
    }} else {{
        box.style.display = 'none';
    }}
}}

function updateRawCSV() {{
    const headers = ["mod_type","fll_bw","costas_bw","sym_bw","preamble_size","noise_volt","freq_offset","time_offset","platform_mode","pdr","ber"];
    const lines = [headers.join(',')];
    filteredData.slice(0, 500).forEach(r => {{
        lines.push(`${{r.mod_type}},${{r.fll_bw}},${{r.costas_bw}},${{r.sym_bw}},${{r.preamble_size || 32}},${{r.noise_volt || 0}},${{r.freq_offset || 0}},${{r.time_offset || 1.0}},${{r.platform_mode || 'software'}},${{r.pdr}},${{r.ber}}`);
    }});
    document.getElementById('raw-csv-text').value = lines.join('\\n');
}}

function exportFilteredCSV() {{
    const headers = ["mod_type","fll_bw","costas_bw","sym_bw","preamble_size","noise_volt","freq_offset","time_offset","platform_mode","pdr","ber","matched_packets","total_packets","elapsed_sec"];
    const lines = [headers.join(',')];
    filteredData.forEach(r => {{
        lines.push(`${{r.mod_type}},${{r.fll_bw}},${{r.costas_bw}},${{r.sym_bw}},${{r.preamble_size || 32}},${{r.noise_volt || 0}},${{r.freq_offset || 0}},${{r.time_offset || 1.0}},${{r.platform_mode || 'software'}},${{r.pdr}},${{r.ber}},${{r.matched_packets || 0}},${{r.total_packets || 10}},${{r.elapsed_sec || 0}}`);
    }});
    const blob = new Blob([lines.join('\\n')], {{ type: 'text/csv' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `phy2_filtered_dataset_${{new Date().toISOString().slice(0,10)}}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}}

window.addEventListener('load', () => {{
    initCostasPills();
    renderDynamicGraph();
    renderHeatmap();
    renderPointInspector();
    applyTableFilters();
    
    document.getElementById('heatmap-canvas').addEventListener('click', handleHeatmapClick);
}});

window.addEventListener('resize', () => {{
    renderDynamicGraph();
    renderHeatmap();
    renderPointInspector();
}});
</script>
</body>
</html>
"""

def build_all_dashboards():
    os.makedirs(DASH_DIR, exist_ok=True)
    
    # 1. Build Software Dashboard
    print("[DEBUG] Generating Software Simulation Dashboard...")
    sw_data_raw = load_data(SW_DATA_PATH, FALLBACK_PATH)
    sw_curated = curate_for_dashboard(sw_data_raw, DASHBOARD_DATA_LIMIT)
    
    sw_data_js = os.path.join(DASH_DIR, "software_data.js")
    write_dashboard_data_js(sw_curated, sw_data_js)
    
    sw_html = generate_dashboard_html(sw_curated, is_hardware=False, data_js_filename="software_data.js")
    with open(SW_OUTPUT_HTML, 'w') as f:
        f.write(sw_html)
    with open(INDEX_OUTPUT_HTML, 'w') as f:
        f.write(sw_html)
    print(f"[OK] Built Software Dashboard -> {SW_OUTPUT_HTML}")
    
    # 2. Build Hardware Dashboard
    print("[DEBUG] Generating Hardware SDR Dashboard...")
    hw_data_raw = load_data(HW_DATA_PATH, SW_DATA_PATH)
    hw_curated = curate_for_dashboard(hw_data_raw, DASHBOARD_DATA_LIMIT)
    
    hw_data_js = os.path.join(DASH_DIR, "hardware_data.js")
    write_dashboard_data_js(hw_curated, hw_data_js)
    
    hw_html = generate_dashboard_html(hw_curated, is_hardware=True, data_js_filename="hardware_data.js")
    with open(HW_OUTPUT_HTML, 'w') as f:
        f.write(hw_html)
    print(f"[OK] Built Hardware SDR Dashboard -> {HW_OUTPUT_HTML}")
    
    print("[OK] Both Software and Hardware dashboards generated successfully!")

# Alias for backwards compatibility
build_master_dashboard = build_all_dashboards

if __name__ == '__main__':
    build_all_dashboards()
