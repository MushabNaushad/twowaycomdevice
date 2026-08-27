#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Zero-Dependency Interactive Dashboard Builder
Generates a standalone, 100% offline interactive dashboard with full FLL, Costas, and Symbol Sync
range sweeps across 0.005 to 1.000 rad/sym.
Prominently displays and dynamically updates the FLL Band-Edge Loop Bandwidth across all plots,
tooltips, heatmaps, and CSV matrix views.
"""

import sys
import os
import json

def build_master_dashboard():
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(dashboard_dir, exist_ok=True)
    
    # Load primary dataset
    deep_json = os.path.join(dashboard_dir, "../optimization/results/deep_sweep_results.json")
    ultra_json = os.path.join(dashboard_dir, "../adapted_original/results/ultra_fine_sweep_results.json")
    
    data_file = deep_json if os.path.exists(deep_json) else ultra_json
    if not os.path.exists(data_file):
        print(f"[ERROR] No dataset found at {deep_json} or {ultra_json}")
        return 1
        
    with open(data_file, "r") as f:
        records = json.load(f)
        
    print(f"Loaded {len(records):,} simulation records from {os.path.basename(data_file)}")
    records_json_str = json.dumps(records)
    
    # Extract distinct sorted values
    fll_vals = sorted(list(set(r['fll_bw'] for r in records)))
    costas_vals = sorted(list(set(r['costas_bw'] for r in records)))
    sym_vals = sorted(list(set(r['sym_bw'] for r in records)))
    
    fll_options_html = "\n".join([f'<option value="{v:.4f}" {"selected" if abs(v-0.0314)<0.002 else ""}>{v:.4f} rad/sym</option>' for v in fll_vals])
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHY2 Physical Layer Interactive Analytics & Parameter Explorer</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --secondary: #475569;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --card-sub: #334155;
            --border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --accent: #38bdf8;
            --fll-color: #f59e0b;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
        }}
        .header {{
            max-width: 1600px;
            margin: 0 auto 20px auto;
            background: var(--card-bg);
            padding: 24px 32px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0 0 6px 0; font-size: 24px; color: var(--text-main); }}
        .header p {{ margin: 0; color: var(--text-muted); font-size: 14px; }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            padding: 18px 20px;
            border-radius: 10px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }}
        .kpi-title {{ font-size: 12px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }}
        .kpi-value {{ font-size: 19px; font-weight: 700; color: var(--accent); }}
        .kpi-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}
        
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 22px 26px;
            border: 1px solid var(--border);
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 18px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
            color: var(--accent);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        /* Interactive Controls Bar */
        .controls-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            align-items: center;
            background: #0f172a;
            padding: 16px 20px;
            border-radius: 8px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
        }}
        .ctrl-group {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .ctrl-group label {{
            font-size: 12px;
            font-weight: 600;
            color: #cbd5e1;
        }}
        .ctrl-group select, .ctrl-group input {{
            padding: 8px 12px;
            border: 1px solid #475569;
            border-radius: 6px;
            font-size: 13px;
            background: #1e293b;
            color: #f8fafc;
        }}
        .ctrl-group select:focus, .ctrl-group input:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        .range-slider-box {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .range-slider-box input[type=range] {{
            width: 150px;
            accent-color: var(--accent);
            cursor: pointer;
        }}
        .range-val {{
            font-size: 12px;
            font-weight: 700;
            color: var(--accent);
            min-width: 55px;
        }}
        .fll-highlight {{
            color: var(--fll-color);
            font-weight: 700;
        }}
        
        /* Checkbox Pills */
        .checkbox-pills {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 6px;
            background: #0f172a;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .pill-label {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: #1e293b;
            border: 1px solid #475569;
            padding: 4px 10px;
            border-radius: 14px;
            font-size: 12px;
            cursor: pointer;
            user-select: none;
            color: #e2e8f0;
            transition: all 0.15s ease;
        }}
        .pill-label:hover {{
            background: #334155;
            border-color: var(--accent);
        }}
        .pill-label input {{ cursor: pointer; }}
        
        /* Buttons */
        .btn {{
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s ease;
        }}
        .btn-primary {{ background: var(--primary); color: #ffffff; }}
        .btn-primary:hover {{ background: var(--primary-dark); }}
        .btn-secondary {{ background: #334155; color: #f8fafc; border: 1px solid #475569; }}
        .btn-secondary:hover {{ background: #475569; }}
        .btn-sm {{ padding: 5px 10px; font-size: 11px; }}
        
        /* Interactive Canvas Container */
        .canvas-container {{
            position: relative;
            width: 100%;
            height: 520px;
            min-height: 520px;
            background: #0b1120;
            border-radius: 8px;
            border: 1px solid var(--border);
            overflow: hidden;
        }}
        canvas {{
            display: block;
            width: 100%;
            height: 100%;
        }}
        .graph-tooltip {{
            position: absolute;
            display: none;
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid var(--accent);
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 12px;
            pointer-events: none;
            color: #f8fafc;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            z-index: 100;
            line-height: 1.5;
        }}
        
        /* CSV Table & Raw View */
        .table-responsive {{
            overflow-x: auto;
            max-height: 440px;
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-top: 10px;
            background: #0b1120;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12.5px;
            text-align: left;
        }}
        th {{
            background: #1e293b;
            padding: 10px 14px;
            border-bottom: 2px solid var(--border);
            color: #e2e8f0;
            font-weight: 600;
            position: sticky;
            top: 0;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{ background: #334155; }}
        td {{
            padding: 8px 14px;
            border-bottom: 1px solid #1e293b;
            color: #cbd5e1;
        }}
        tr:hover td {{ background: #1e293b; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-bpsk {{ background: #1e3a8a; color: #93c5fd; }}
        .badge-qpsk {{ background: #581c87; color: #d8b4fe; }}
        
        .raw-csv-panel {{
            display: none;
            margin-top: 14px;
        }}
        textarea.raw-csv {{
            width: 100%;
            height: 180px;
            font-family: monospace;
            font-size: 12px;
            padding: 12px;
            border: 1px solid #475569;
            border-radius: 6px;
            background: #0b1120;
            color: #38bdf8;
            resize: vertical;
        }}
        
        .pagination {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 12px;
            font-size: 13px;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>PHY2 Physical Layer Interactive Analytics & Parameter Explorer</h1>
            <p>100% Standalone Zero-Dependency Dynamic Plotter with Full FLL Band-Edge, Costas & Symbol Sync Sweeps (0.005..1.000 rad/sym)</p>
        </div>
        <div>
            <button class="btn btn-primary" onclick="exportFilteredCSV()">Export Filtered CSV</button>
        </div>
    </div>

    <div class="container">
        <!-- KPI Summary Cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Evaluated Configurations</div>
                <div class="kpi-value" id="kpi-total">{len(records):,} Trials</div>
                <div class="kpi-sub">0.005 to 1.000 rad/sym full range sweeps</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">BPSK Optimal (y·y' TED)</div>
                <div class="kpi-value">FLL Band-Edge: 0.0314 rad/sym</div>
                <div class="kpi-sub">Costas: 0.0628 | SymSync: 0.0250 | PDR 90-95%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">QPSK Optimal (y·y' TED)</div>
                <div class="kpi-value">FLL Band-Edge: 0.0314 rad/sym</div>
                <div class="kpi-sub">Costas: 0.0628 | SymSync: 0.1150 | PDR 90-95%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Hardware Tolerance</div>
                <div class="kpi-value">±2.5% Carrier Offset</div>
                <div class="kpi-sub">Clock Drift: 0.9992 .. 1.0008 (±800 ppm)</div>
            </div>
        </div>

        <!-- 1. LIVE DYNAMIC INTERACTIVE GRAPH: BER vs Symbol Sync with Costas Lines & FLL Range Slider -->
        <div class="card">
            <h2>
                <span>1. Dynamic Interactive Graph: Bit Error Rate (BER) vs Symbol Sync Loop Bandwidth</span>
                <span id="header-fll-badge" style="font-size:13.5px; font-weight:600; color:var(--fll-color); background:#0f172a; padding:4px 10px; border-radius:6px; border:1px solid #475569;">
                    FLL Band-Edge Loop BW = 0.0314 rad/sym
                </span>
            </h2>

            <div class="controls-row">
                <!-- Modulation Toggle -->
                <div class="ctrl-group">
                    <label>Modulation Scheme:</label>
                    <select id="dyn-mod" onchange="renderDynamicGraph()">
                        <option value="BPSK" selected>BPSK</option>
                        <option value="QPSK">QPSK</option>
                    </select>
                </div>

                <!-- FLL Loop Bandwidth Dropdown & Range Slider -->
                <div class="ctrl-group">
                    <label>Set FLL Band-Edge Loop BW: <span id="dyn-fll-val" class="fll-highlight">0.0314</span> rad/sym</label>
                    <div class="range-slider-box">
                        <select id="dyn-fll-select" onchange="syncFllFromSelect()">
                            {fll_options_html}
                        </select>
                        <input type="range" id="dyn-fll-slider" min="0.005" max="1.000" step="0.005" value="0.0314" oninput="syncFllFromSlider()">
                    </div>
                </div>

                <!-- Costas BW Max Range Slider -->
                <div class="ctrl-group">
                    <label>Costas Loop BW Max: <span id="dyn-costas-max-val" class="range-val">1.000</span> rad/sym</label>
                    <div class="range-slider-box">
                        <input type="range" id="dyn-costas-max" min="0.005" max="1.000" step="0.005" value="1.000" oninput="document.getElementById('dyn-costas-max-val').innerText = parseFloat(this.value).toFixed(3); renderDynamicGraph();">
                    </div>
                </div>

                <!-- Quick Selection Action Buttons -->
                <div class="ctrl-group" style="justify-content: flex-end;">
                    <div style="display:flex; gap:6px; margin-top:16px;">
                        <button class="btn btn-secondary btn-sm" onclick="toggleCostasLines(true)">Select All Lines</button>
                        <button class="btn btn-secondary btn-sm" onclick="toggleCostasLines(false)">Select Core Lines</button>
                    </div>
                </div>
            </div>

            <!-- Costas Lines Checkbox Toggle Pills -->
            <div style="margin-bottom: 10px;">
                <label style="font-size:12px; font-weight:600; color:#cbd5e1;">Select Costas Loop Bandwidths to Display as Lines:</label>
                <div class="checkbox-pills" id="costas-pills">
                    <!-- Checkboxes injected by JS -->
                </div>
            </div>

            <!-- Dynamic Graph Canvas Container with Tooltip -->
            <div class="canvas-container" id="graph-container">
                <canvas id="dynamic-canvas"></canvas>
                <div id="graph-tooltip" class="graph-tooltip"></div>
            </div>
        </div>

        <!-- 2. INTERACTIVE 2D CORRELATION HEATMAP (Costas vs Symbol Sync) -->
        <div class="card">
            <h2>
                <span>2. Interactive 2D Correlation Heatmap: Costas Loop BW vs Symbol Sync Loop BW</span>
                <span id="heatmap-fll-badge" style="font-size:13.5px; font-weight:600; color:var(--fll-color); background:#0f172a; padding:4px 10px; border-radius:6px; border:1px solid #475569;">
                    FLL Band-Edge Slice = 0.0314 rad/sym
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
                    <label>FLL Band-Edge Slice (0.005..1.000 rad/sym):</label>
                    <select id="hm-fll-select" onchange="renderHeatmap()">
                        {fll_options_html}
                    </select>
                </div>
            </div>

            <div class="canvas-container" id="heatmap-container" style="height: 480px; min-height: 480px;">
                <canvas id="heatmap-canvas"></canvas>
                <div id="heatmap-tooltip" class="graph-tooltip"></div>
            </div>
        </div>

        <!-- 3. SEARCHABLE CSV DATA TABLE & LIVE PARAMETER FILTER -->
        <div class="card">
            <h2>
                <span>3. Searchable CSV Dataset & Live Parameter Filter</span>
                <div style="display:flex; gap:8px;">
                    <button class="btn btn-secondary btn-sm" onclick="toggleRawCSV()">Toggle Raw CSV View</button>
                    <button class="btn btn-secondary btn-sm" onclick="resetTableFilters()">Reset Filters</button>
                    <button class="btn btn-primary btn-sm" onclick="exportFilteredCSV()">Export CSV</button>
                </div>
            </h2>

            <!-- Collapsible Raw CSV Display -->
            <div id="raw-csv-panel" class="raw-csv-panel">
                <p style="font-size:12px; color:var(--text-muted); margin:0 0 6px 0;"><strong>Raw CSV Data Output:</strong> (Live synchronized with filters)</p>
                <textarea id="raw-csv-text" class="raw-csv" readonly></textarea>
            </div>

            <!-- Filter Controls -->
            <div class="controls-row">
                <!-- Search Box -->
                <div class="ctrl-group" style="flex: 1; min-width: 180px;">
                    <label>Search Parameters & Columns:</label>
                    <input type="text" id="tbl-search" placeholder="Type BPSK, 0.0314, 0.0628, software..." oninput="applyTableFilters()">
                </div>

                <!-- Mod Filter -->
                <div class="ctrl-group">
                    <label>Modulation:</label>
                    <select id="tbl-mod" onchange="applyTableFilters()">
                        <option value="ALL">All Modulations</option>
                        <option value="BPSK">BPSK</option>
                        <option value="QPSK">QPSK</option>
                    </select>
                </div>

                <!-- Profile Filter -->
                <div class="ctrl-group">
                    <label>Profile:</label>
                    <select id="tbl-platform" onchange="applyTableFilters()">
                        <option value="ALL">All Profiles</option>
                        <option value="software">Software Multipath</option>
                        <option value="hardware">Hardware SDR Profile</option>
                    </select>
                </div>

                <!-- FLL BW Filter -->
                <div class="ctrl-group">
                    <label>FLL Band-Edge BW Max: <span id="tbl-val-fll" class="range-val">1.000</span></label>
                    <div class="range-slider-box">
                        <input type="range" id="tbl-fll" min="0.005" max="1.000" step="0.005" value="1.000" oninput="document.getElementById('tbl-val-fll').innerText = parseFloat(this.value).toFixed(3); applyTableFilters();">
                    </div>
                </div>

                <!-- Costas BW Filter -->
                <div class="ctrl-group">
                    <label>Costas BW Max: <span id="tbl-val-costas" class="range-val">1.000</span></label>
                    <div class="range-slider-box">
                        <input type="range" id="tbl-costas" min="0.005" max="1.000" step="0.005" value="1.000" oninput="document.getElementById('tbl-val-costas').innerText = parseFloat(this.value).toFixed(3); applyTableFilters();">
                    </div>
                </div>

                <!-- SymSync BW Filter -->
                <div class="ctrl-group">
                    <label>SymSync BW Max: <span id="tbl-val-sym" class="range-val">1.000</span></label>
                    <div class="range-slider-box">
                        <input type="range" id="tbl-sym" min="0.005" max="1.000" step="0.005" value="1.000" oninput="document.getElementById('tbl-val-sym').innerText = parseFloat(this.value).toFixed(3); applyTableFilters();">
                    </div>
                </div>

                <!-- Min PDR Filter -->
                <div class="ctrl-group">
                    <label>Min PDR (%): <span id="tbl-val-pdr" class="range-val">0.0%</span></label>
                    <div class="range-slider-box">
                        <input type="range" id="tbl-pdr" min="0" max="100" step="5" value="0" oninput="document.getElementById('tbl-val-pdr').innerText = this.value + '%'; applyTableFilters();">
                    </div>
                </div>
            </div>

            <!-- Table -->
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th onclick="sortTable('mod_type')">Modulation ↕</th>
                            <th onclick="sortTable('fll_bw')">FLL Band-Edge BW (rad/sym) ↕</th>
                            <th onclick="sortTable('costas_bw')">Costas BW (rad/sym) ↕</th>
                            <th onclick="sortTable('sym_bw')">SymSync BW (rad/sym) ↕</th>
                            <th onclick="sortTable('preamble_size')">Preamble ↕</th>
                            <th onclick="sortTable('noise_volt')">Noise (Vn) ↕</th>
                            <th onclick="sortTable('freq_offset')">Freq Offset ↕</th>
                            <th onclick="sortTable('time_offset')">Clock Drift ↕</th>
                            <th onclick="sortTable('platform_mode')">Profile ↕</th>
                            <th onclick="sortTable('pdr')">PDR (%) ↕</th>
                            <th onclick="sortTable('ber')">BER ↕</th>
                        </tr>
                    </thead>
                    <tbody id="table-body">
                        <!-- Injected by JavaScript -->
                    </tbody>
                </table>
            </div>

            <!-- Pagination Bar -->
            <div class="pagination">
                <div id="results-count">Showing 0 - 0 of 0 records</div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <label style="font-size:12px;">Rows per page:</label>
                    <select id="tbl-page-size" onchange="currentPage=1; renderTable();" style="padding:4px 8px; font-size:12px; background:#1e293b; color:#f8fafc; border:1px solid #475569; border-radius:4px;">
                        <option value="25" selected>25</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                        <option value="500">500</option>
                    </select>
                    <button class="btn btn-secondary btn-sm" onclick="prevPage()">« Previous</button>
                    <span id="page-num" style="font-weight:600; margin: 0 4px;">Page 1</span>
                    <button class="btn btn-secondary btn-sm" onclick="nextPage()">Next »</button>
                </div>
            </div>
        </div>
    </div>

    <!-- 100% Zero-Dependency Dynamic Plotter & Interactive Engine -->
    <script>
        const rawData = {records_json_str};
        let filteredData = [...rawData];
        let currentPage = 1;
        let currentSortCol = 'pdr';
        let sortAsc = false;

        // Distinct parameter sets
        const allCostas = [...new Set(rawData.map(r => r.costas_bw))].sort((a,b) => a-b);
        const allSym = [...new Set(rawData.map(r => r.sym_bw))].sort((a,b) => a-b);
        const allFll = [...new Set(rawData.map(r => r.fll_bw))].sort((a,b) => a-b);

        // Core Costas values to check by default
        const defaultCostas = [0.005, 0.010, 0.025, 0.0628, 0.135, 0.250, 0.500, 1.000];
        const lineColors = [
            '#38bdf8', '#22c55e', '#f59e0b', '#ec4899', '#a855f7',
            '#ef4444', '#14b8a6', '#eab308', '#6366f1', '#f97316', '#06b6d4'
        ];

        // 1. Initialize Costas Checkbox Pills
        function initCostasPills() {{
            const container = document.getElementById('costas-pills');
            container.innerHTML = '';
            allCostas.forEach((cbw, idx) => {{
                const isChecked = defaultCostas.some(v => Math.abs(v - cbw) < 0.005) || (idx % 2 === 0);
                const label = document.createElement('label');
                label.className = 'pill-label';
                label.innerHTML = `<input type="checkbox" value="${{cbw}}" class="costas-chk" ${{isChecked ? 'checked' : ''}} onchange="renderDynamicGraph()"> Costas ${{cbw.toFixed(4)}}`;
                container.appendChild(label);
            }});
        }}

        function toggleCostasLines(selectAll) {{
            document.querySelectorAll('.costas-chk').forEach(chk => {{
                if (selectAll) {{
                    chk.checked = true;
                }} else {{
                    const val = parseFloat(chk.value);
                    chk.checked = defaultCostas.some(v => Math.abs(v - val) < 0.005);
                }}
            }});
            renderDynamicGraph();
        }}

        function syncFllFromSelect() {{
            const val = parseFloat(document.getElementById('dyn-fll-select').value);
            document.getElementById('dyn-fll-slider').value = val;
            document.getElementById('dyn-fll-val').innerText = val.toFixed(4);
            document.getElementById('header-fll-badge').innerText = `FLL Band-Edge Loop BW = ${{val.toFixed(4)}} rad/sym`;
            document.getElementById('hm-fll-select').value = val.toFixed(4);
            renderDynamicGraph();
            renderHeatmap();
        }}

        function syncFllFromSlider() {{
            const sliderVal = parseFloat(document.getElementById('dyn-fll-slider').value);
            // Find closest available FLL value
            let closestFll = allFll[0];
            let minDist = 999;
            allFll.forEach(f => {{
                const d = Math.abs(f - sliderVal);
                if (d < minDist) {{ minDist = d; closestFll = f; }}
            }});
            document.getElementById('dyn-fll-select').value = closestFll.toFixed(4);
            document.getElementById('dyn-fll-val').innerText = closestFll.toFixed(4);
            document.getElementById('header-fll-badge').innerText = `FLL Band-Edge Loop BW = ${{closestFll.toFixed(4)}} rad/sym`;
            document.getElementById('hm-fll-select').value = closestFll.toFixed(4);
            renderDynamicGraph();
            renderHeatmap();
        }}

        // 2. Native Dynamic Multi-Line Graph Rendering Engine
        let activeGraphSeries = [];
        let graphPlotBounds = {{ left: 80, right: 30, top: 60, bottom: 60 }};
        let currentGraphFll = 0.0314;

        function renderDynamicGraph() {{
            const canvas = document.getElementById('dynamic-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const container = document.getElementById('graph-container');
            const rect = container ? container.getBoundingClientRect() : {{ width: 1200, height: 520 }};
            const W = rect.width > 100 ? rect.width : 1200;
            const H = rect.height > 100 ? rect.height : 520;

            const dpr = window.devicePixelRatio || 1;
            canvas.width = W * dpr;
            canvas.height = H * dpr;
            ctx.scale(dpr, dpr);

            ctx.clearRect(0, 0, W, H);

            const mod = document.getElementById('dyn-mod').value;
            const fllVal = parseFloat(document.getElementById('dyn-fll-select').value);
            currentGraphFll = fllVal;
            const maxCostas = parseFloat(document.getElementById('dyn-costas-max').value);

            const selectedCostas = Array.from(document.querySelectorAll('.costas-chk:checked'))
                .map(chk => parseFloat(chk.value))
                .filter(v => v <= maxCostas + 1e-4);

            activeGraphSeries = [];

            // Collect series data points
            selectedCostas.forEach((cbw, idx) => {{
                const pts = [];
                allSym.forEach(sbw => {{
                    const matches = rawData.filter(r =>
                        r.mod_type === mod &&
                        Math.abs(r.fll_bw - fllVal) < 0.006 &&
                        Math.abs(r.costas_bw - cbw) < 0.006 &&
                        Math.abs(r.sym_bw - sbw) < 0.006
                    );
                    if (matches.length > 0) {{
                        const avgBer = matches.reduce((acc, cur) => acc + cur.ber, 0) / matches.length;
                        const avgPdr = matches.reduce((acc, cur) => acc + cur.pdr, 0) / matches.length;
                        pts.push({{ x: sbw, y: Math.max(avgBer, 1e-4), pdr: avgPdr }});
                    }}
                }});
                if (pts.length > 0) {{
                    activeGraphSeries.push({{
                        costas_bw: cbw,
                        color: lineColors[idx % lineColors.length],
                        points: pts
                    }});
                }}
            }});

            const pLeft = 80;
            const pRight = W - 220; // Room for interactive legend
            const pTop = 50;
            const pBottom = H - 55;
            graphPlotBounds = {{ left: pLeft, right: pRight, top: pTop, bottom: pBottom, W: W, H: H }};

            // Grid & Axes background
            ctx.fillStyle = '#0b1120';
            ctx.fillRect(pLeft, pTop, Math.max(10, pRight - pLeft), Math.max(10, pBottom - pTop));

            // Log scale Y-axis bounds (10^-4 to 10^0)
            const yMinLog = -4;
            const yMaxLog = 0;
            const xMin = 0.0;
            const xMax = 1.0;

            function mapX(val) {{ return pLeft + ((val - xMin) / (xMax - xMin)) * (pRight - pLeft); }}
            function mapY(val) {{ 
                const logV = Math.log10(Math.max(val, 1e-4));
                return pBottom - ((logV - yMinLog) / (yMaxLog - yMinLog)) * (pBottom - pTop);
            }}

            // Draw Y Grid lines (Decades)
            ctx.lineWidth = 1;
            ctx.strokeStyle = '#1e293b';
            ctx.fillStyle = '#94a3b8';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'right';

            for (let exp = -4; exp <= 0; exp++) {{
                const yPos = mapY(Math.pow(10, exp));
                ctx.beginPath();
                ctx.moveTo(pLeft, yPos);
                ctx.lineTo(pRight, yPos);
                ctx.stroke();
                ctx.fillText(`10^${{exp}}`, pLeft - 10, yPos + 4);
            }}

            // Draw X Grid lines
            ctx.textAlign = 'center';
            for (let xV = 0.0; xV <= 1.05; xV += 0.1) {{
                const xPos = mapX(xV);
                ctx.beginPath();
                ctx.moveTo(xPos, pTop);
                ctx.lineTo(xPos, pBottom);
                ctx.stroke();
                ctx.fillText(xV.toFixed(1), xPos, pBottom + 18);
            }}

            // Prominent Canvas Axis Labels & Title with explicit FLL Band-Edge value
            ctx.fillStyle = '#38bdf8';
            ctx.font = 'bold 13.5px sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText(`${{mod}} (y·y' TED): BER vs Symbol Sync BW`, pLeft, 26);

            ctx.fillStyle = '#f59e0b';
            ctx.font = 'bold 12.5px sans-serif';
            ctx.fillText(`[FLL Band-Edge Loop BW = ${{fllVal.toFixed(4)}} rad/sym]`, pLeft + 360, 26);

            ctx.fillStyle = '#94a3b8';
            ctx.font = '12px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Symbol Synchronizer Loop Bandwidth (rad/sym)', (pLeft + pRight) / 2, H - 18);

            ctx.save();
            ctx.translate(22, (pTop + pBottom) / 2);
            ctx.rotate(-Math.PI / 2);
            ctx.fillText('Bit Error Rate (BER) - Logarithmic Scale', 0, 0);
            ctx.restore();

            // Render Smooth Multi-Line Curves
            activeGraphSeries.forEach(series => {{
                if (series.points.length < 2) return;

                ctx.strokeStyle = series.color;
                ctx.lineWidth = 2.4;
                ctx.beginPath();

                for (let i = 0; i < series.points.length; i++) {{
                    const cur = series.points[i];
                    const px = mapX(cur.x);
                    const py = mapY(cur.y);

                    if (i === 0) {{
                        ctx.moveTo(px, py);
                    }} else {{
                        const prev = series.points[i - 1];
                        const prevX = mapX(prev.x);
                        const prevY = mapY(prev.y);
                        const cpX1 = prevX + (px - prevX) / 2;
                        const cpY1 = prevY;
                        const cpX2 = prevX + (px - prevX) / 2;
                        const cpY2 = py;
                        ctx.bezierCurveTo(cpX1, cpY1, cpX2, cpY2, px, py);
                    }}
                }}
                ctx.stroke();

                // Draw Data Point Markers
                ctx.fillStyle = series.color;
                series.points.forEach(pt => {{
                    const px = mapX(pt.x);
                    const py = mapY(pt.y);
                    ctx.beginPath();
                    ctx.arc(px, py, 3.2, 0, Math.PI * 2);
                    ctx.fill();
                }});
            }});

            // Render Right-Hand Legend
            ctx.textAlign = 'left';
            ctx.font = '11px sans-serif';
            const legLeft = pRight + 20;
            let legTop = pTop + 10;

            ctx.fillStyle = '#e2e8f0';
            ctx.font = 'bold 12px sans-serif';
            ctx.fillText('Costas Loop BW:', legLeft, legTop);
            legTop += 18;

            activeGraphSeries.forEach(series => {{
                ctx.fillStyle = series.color;
                ctx.fillRect(legLeft, legTop - 8, 14, 4);
                ctx.beginPath();
                ctx.arc(legLeft + 7, legTop - 6, 3, 0, Math.PI * 2);
                ctx.fill();

                ctx.fillStyle = '#cbd5e1';
                ctx.font = '11.5px sans-serif';
                ctx.fillText(`Costas = ${{series.costas_bw.toFixed(4)}}`, legLeft + 20, legTop);
                legTop += 20;
            }});
        }}

        // Dynamic Graph Hover Inspector
        const graphContainer = document.getElementById('graph-container');
        const graphTooltip = document.getElementById('graph-tooltip');

        if (graphContainer) {{
            graphContainer.addEventListener('mousemove', (e) => {{
                const rect = graphContainer.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;

                const {{ left, right, top, bottom }} = graphPlotBounds;
                if (mouseX < left || mouseX > right || mouseY < top || mouseY > bottom) {{
                    graphTooltip.style.display = 'none';
                    return;
                }}

                const symVal = 0.0 + ((mouseX - left) / (right - left)) * 1.0;
                let closestSym = allSym[0];
                let minDist = 999;
                allSym.forEach(sbw => {{
                    const d = Math.abs(sbw - symVal);
                    if (d < minDist) {{ minDist = d; closestSym = sbw; }}
                }});

                let infoHtml = `<div style="border-bottom:1px solid #475569; padding-bottom:4px; margin-bottom:4px;">
                    <span style="color:#f59e0b; font-weight:700;">FLL Band-Edge: ${{currentGraphFll.toFixed(4)}} rad/sym</span><br>
                    <strong>SymSync BW: ${{closestSym.toFixed(4)}} rad/sym</strong>
                </div>`;
                let foundAny = false;

                activeGraphSeries.forEach(series => {{
                    const pt = series.points.find(p => Math.abs(p.x - closestSym) < 1e-4);
                    if (pt) {{
                        foundAny = true;
                        infoHtml += `<span style="color:${{series.color}}">■</span> Costas ${{series.costas_bw.toFixed(4)}}: BER <strong>${{pt.y.toExponential(2)}}</strong> (PDR ${{pt.pdr.toFixed(1)}}%)<br>`;
                    }}
                }});

                if (foundAny) {{
                    graphTooltip.innerHTML = infoHtml;
                    graphTooltip.style.display = 'block';
                    graphTooltip.style.left = `${{Math.min(mouseX + 15, rect.width - 260)}}px`;
                    graphTooltip.style.top = `${{Math.min(mouseY + 15, rect.height - 190)}}px`;
                }} else {{
                    graphTooltip.style.display = 'none';
                }}
            }});

            graphContainer.addEventListener('mouseleave', () => {{
                graphTooltip.style.display = 'none';
            }});
        }}

        // 3. Native 2D Correlation Heatmap Canvas Engine
        function renderHeatmap() {{
            const canvas = document.getElementById('heatmap-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const container = document.getElementById('heatmap-container');
            const rect = container ? container.getBoundingClientRect() : {{ width: 1200, height: 480 }};
            const W = rect.width > 100 ? rect.width : 1200;
            const H = rect.height > 100 ? rect.height : 480;

            const dpr = window.devicePixelRatio || 1;
            canvas.width = W * dpr;
            canvas.height = H * dpr;
            ctx.scale(dpr, dpr);

            ctx.clearRect(0, 0, W, H);

            const mod = document.getElementById('hm-mod').value;
            const metric = document.getElementById('hm-metric').value;
            const fllVal = parseFloat(document.getElementById('hm-fll-select').value);
            document.getElementById('heatmap-fll-badge').innerText = `FLL Band-Edge Slice = ${{fllVal.toFixed(4)}} rad/sym`;

            const pLeft = 80;
            const pRight = W - 100;
            const pTop = 40;
            const pBottom = H - 55;

            const numX = allSym.length;
            const numY = allCostas.length;
            const cellW = (pRight - pLeft) / numX;
            const cellH = (pBottom - pTop) / numY;

            function getColor(val) {{
                const r = Math.floor(Math.min(255, Math.max(0, val * 2.2 * 255)));
                const g = Math.floor(Math.min(255, Math.max(0, (1 - val * 0.9) * 255)));
                const b = Math.floor(Math.min(255, Math.max(0, (1 - Math.abs(val - 0.5) * 2) * 160)));
                return `rgb(${{r}}, ${{g}}, ${{b}})`;
            }}

            for (let j = 0; j < numY; j++) {{
                const cbw = allCostas[numY - 1 - j];
                for (let i = 0; i < numX; i++) {{
                    const sbw = allSym[i];
                    const matches = rawData.filter(r =>
                        r.mod_type === mod &&
                        Math.abs(r.fll_bw - fllVal) < 0.006 &&
                        Math.abs(r.costas_bw - cbw) < 0.006 &&
                        Math.abs(r.sym_bw - sbw) < 0.006
                    );

                    let normVal = 1.0;
                    if (matches.length > 0) {{
                        if (metric === 'ber') {{
                            const logB = Math.log10(Math.max(matches[0].ber, 1e-4));
                            normVal = (logB - (-4.0)) / (0.0 - (-4.0));
                        }} else {{
                            normVal = 1.0 - (matches[0].pdr / 100.0);
                        }}
                    }}

                    ctx.fillStyle = getColor(normVal);
                    ctx.fillRect(pLeft + i * cellW, pTop + j * cellH, cellW + 0.5, cellH + 0.5);
                }}
            }}

            // Draw Heatmap Axes Labels
            ctx.fillStyle = '#94a3b8';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            for (let i = 0; i < numX; i += 2) {{
                const xPos = pLeft + i * cellW + cellW / 2;
                ctx.fillText(allSym[i].toFixed(2), xPos, pBottom + 16);
            }}
            ctx.fillText('Symbol Synchronizer Loop Bandwidth (rad/sym)', (pLeft + pRight) / 2, H - 18);

            ctx.textAlign = 'right';
            for (let j = 0; j < numY; j += 2) {{
                const cbw = allCostas[numY - 1 - j];
                const yPos = pTop + j * cellH + cellH / 2 + 4;
                ctx.fillText(cbw.toFixed(3), pLeft - 8, yPos);
            }}

            ctx.save();
            ctx.translate(20, (pTop + pBottom) / 2);
            ctx.rotate(-Math.PI / 2);
            ctx.textAlign = 'center';
            ctx.fillText('Costas Loop Bandwidth (rad/sym)', 0, 0);
            ctx.restore();

            // Draw Colorbar on Right
            const cbLeft = pRight + 25;
            const cbW = 16;
            for (let y = pTop; y <= pBottom; y++) {{
                const frac = (y - pTop) / (pBottom - pTop);
                ctx.fillStyle = getColor(frac);
                ctx.fillRect(cbLeft, y, cbW, 1);
            }}
            ctx.strokeStyle = '#475569';
            ctx.strokeRect(cbLeft, pTop, cbW, pBottom - pTop);

            ctx.fillStyle = '#e2e8f0';
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText(metric === 'ber' ? '10^-4 (Best)' : '100% PDR', cbLeft + cbW + 6, pTop + 8);
            ctx.fillText(metric === 'ber' ? '10^0 (Loss)' : '0% PDR', cbLeft + cbW + 6, pBottom);
        }}

        // 4. Interactive CSV Table Filtering & Pagination Engine
        function applyTableFilters() {{
            const search = document.getElementById('tbl-search').value.toLowerCase();
            const mod = document.getElementById('tbl-mod').value;
            const platform = document.getElementById('tbl-platform').value;
            const maxFll = parseFloat(document.getElementById('tbl-fll').value);
            const maxCostas = parseFloat(document.getElementById('tbl-costas').value);
            const maxSym = parseFloat(document.getElementById('tbl-sym').value);
            const minPdr = parseFloat(document.getElementById('tbl-pdr').value);

            filteredData = rawData.filter(r => {{
                if (mod !== 'ALL' && r.mod_type !== mod) return false;
                if (platform !== 'ALL' && r.platform_mode !== platform) return false;
                if (r.fll_bw > maxFll + 1e-4) return false;
                if (r.costas_bw > maxCostas + 1e-4) return false;
                if (r.sym_bw > maxSym + 1e-4) return false;
                if (r.pdr < minPdr - 1e-4) return false;
                
                if (search) {{
                    const str = `${{r.mod_type}} ${{r.fll_bw}} ${{r.costas_bw}} ${{r.sym_bw}} ${{r.preamble_size}} ${{r.platform_mode}} ${{r.pdr}} ${{r.ber}}`.toLowerCase();
                    if (!str.includes(search)) return false;
                }}
                return true;
            }});

            currentPage = 1;
            sortTableData();
            renderTable();
            updateRawCSVText();
        }}

        function resetTableFilters() {{
            document.getElementById('tbl-search').value = '';
            document.getElementById('tbl-mod').value = 'ALL';
            document.getElementById('tbl-platform').value = 'ALL';
            document.getElementById('tbl-fll').value = 1.000;
            document.getElementById('tbl-costas').value = 1.000;
            document.getElementById('tbl-sym').value = 1.000;
            document.getElementById('tbl-pdr').value = 0;
            document.getElementById('tbl-val-fll').innerText = '1.000';
            document.getElementById('tbl-val-costas').innerText = '1.000';
            document.getElementById('tbl-val-sym').innerText = '1.000';
            document.getElementById('tbl-val-pdr').innerText = '0.0%';
            applyTableFilters();
        }}

        function sortTable(col) {{
            if (currentSortCol === col) {{
                sortAsc = !sortAsc;
            }} else {{
                currentSortCol = col;
                sortAsc = false;
            }}
            sortTableData();
            renderTable();
        }}

        function sortTableData() {{
            filteredData.sort((a, b) => {{
                let vA = a[currentSortCol];
                let vB = b[currentSortCol];
                if (typeof vA === 'string') return sortAsc ? vA.localeCompare(vB) : vB.localeCompare(vA);
                return sortAsc ? vA - vB : vB - vA;
            }});
        }}

        function renderTable() {{
            const tbody = document.getElementById('table-body');
            if (!tbody) return;
            tbody.innerHTML = '';
            const total = filteredData.length;
            const pageSize = parseInt(document.getElementById('tbl-page-size').value);
            const start = (currentPage - 1) * pageSize;
            const end = Math.min(start + pageSize, total);
            const pageRecords = filteredData.slice(start, end);

            for (const r of pageRecords) {{
                const tr = document.createElement('tr');
                const modBadge = r.mod_type === 'BPSK' ? 'badge-bpsk' : 'badge-qpsk';
                const pdrColor = r.pdr >= 85 ? 'color:#22c55e; font-weight:600;' : (r.pdr >= 50 ? 'color:#f59e0b;' : 'color:#ef4444;');
                tr.innerHTML = `
                    <td><span class="badge ${{modBadge}}">${{r.mod_type}}</span></td>
                    <td><strong style="color:var(--fll-color);">${{r.fll_bw.toFixed(4)}}</strong></td>
                    <td>${{r.costas_bw.toFixed(4)}}</td>
                    <td>${{r.sym_bw.toFixed(4)}}</td>
                    <td>${{r.preamble_size}} B</td>
                    <td>${{r.noise_volt.toFixed(2)}}</td>
                    <td>${{r.freq_offset >= 0 ? '+' : ''}}${{r.freq_offset.toFixed(3)}}</td>
                    <td>${{r.time_offset.toFixed(6)}}</td>
                    <td>${{r.platform_mode}}</td>
                    <td style="${{pdrColor}}">${{r.pdr.toFixed(1)}}%</td>
                    <td>${{r.ber.toExponential(2)}}</td>
                `;
                tbody.appendChild(tr);
            }}

            const totalPages = Math.ceil(total / pageSize) || 1;
            document.getElementById('results-count').innerText = `Showing ${{total > 0 ? start + 1 : 0}} - ${{end}} of ${{total.toLocaleString()}} records (out of ${{rawData.length.toLocaleString()}} total)`;
            document.getElementById('page-num').innerText = `Page ${{currentPage}} of ${{totalPages}}`;
        }}

        function prevPage() {{
            if (currentPage > 1) {{
                currentPage--;
                renderTable();
            }}
        }}

        function nextPage() {{
            const pageSize = parseInt(document.getElementById('tbl-page-size').value);
            const totalPages = Math.ceil(filteredData.length / pageSize);
            if (currentPage < totalPages) {{
                currentPage++;
                renderTable();
            }}
        }}

        function toggleRawCSV() {{
            const panel = document.getElementById('raw-csv-panel');
            panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
            if (panel.style.display === 'block') updateRawCSVText();
        }}

        function updateRawCSVText() {{
            const headers = "Modulation,FLL_Band_Edge_BW,Costas_BW,SymSync_BW,Preamble_Size,Noise_Volt,Freq_Offset,Time_Offset,Platform,PDR,BER";
            const sampleRows = filteredData.slice(0, 500).map(r => 
                `${{r.mod_type}},${{r.fll_bw}},${{r.costas_bw}},${{r.sym_bw}},${{r.preamble_size}},${{r.noise_volt}},${{r.freq_offset}},${{r.time_offset}},${{r.platform_mode}},${{r.pdr}},${{r.ber}}`
            );
            document.getElementById('raw-csv-text').value = [headers, ...sampleRows].join('\\n') + (filteredData.length > 500 ? `\\n... (${{filteredData.length - 500}} more filtered rows)` : '');
        }}

        function exportFilteredCSV() {{
            if (!filteredData.length) {{
                alert("No records to export!");
                return;
            }}
            const headers = ["Modulation", "FLL_Band_Edge_BW", "Costas_BW", "SymSync_BW", "Preamble_Bytes", "Noise_Volt", "Freq_Offset", "Time_Offset", "Platform", "PDR_Percent", "BER"];
            const rows = filteredData.map(r => [
                r.mod_type, r.fll_bw, r.costas_bw, r.sym_bw, r.preamble_size,
                r.noise_volt, r.freq_offset, r.time_offset, r.platform_mode, r.pdr, r.ber
            ]);
            let csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\\n");
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `phy2_filtered_data_${{Date.now()}}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}

        function initialRender() {{
            initCostasPills();
            renderDynamicGraph();
            renderHeatmap();
            sortTableData();
            renderTable();
        }}

        window.addEventListener('DOMContentLoaded', initialRender);
        window.addEventListener('load', initialRender);
        window.addEventListener('resize', () => {{
            renderDynamicGraph();
            renderHeatmap();
        }});
        setTimeout(initialRender, 100);
        setTimeout(initialRender, 500);
    </script>
</body>
</html>
"""
    output_html = os.path.join(dashboard_dir, "index.html")
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # Also sync to adapted_original and optimization results folders
    with open(os.path.join(dashboard_dir, "../adapted_original/results/comprehensive_dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(os.path.join(dashboard_dir, "../optimization/results/deep_dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"[OK] Master zero-dependency interactive dashboard successfully built at: {output_html}")
    return 0

if __name__ == '__main__':
    sys.exit(build_master_dashboard())
