#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Interactive Dashboard Builder
Generates a standalone, self-contained, publication-grade web dashboard
with live multi-parameter range filtering, interactive search, sortable paginated CSV data table,
instant CSV export, and high-resolution parametric chart galleries.
"""

import sys
import os
import json
import csv

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def build_master_dashboard():
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(dashboard_dir, exist_ok=True)
    
    # Load dataset
    ultra_fine_json = os.path.join(dashboard_dir, "../adapted_original/results/ultra_fine_sweep_results.json")
    if not os.path.exists(ultra_fine_json):
        print(f"[ERROR] Missing dataset: {ultra_fine_json}")
        return 1
        
    with open(ultra_fine_json, "r") as f:
        records = json.load(f)
        
    charts_dir = os.path.join(dashboard_dir, "../adapted_original/results")
    
    # Load SVGs
    svg_files = {
        'chart_01': "chart_01_costas_bw_ber_slice_bpsk.svg",
        'chart_02': "chart_02_costas_bw_ber_slice_qpsk.svg",
        'chart_03': "chart_03_symsync_bw_ber_slice_bpsk.svg",
        'chart_04': "chart_04_symsync_bw_ber_slice_qpsk.svg",
        'chart_05': "chart_05_fll_bw_carrier_offset_slice_bpsk.svg",
        'chart_06': "chart_06_fll_bw_carrier_offset_slice_qpsk.svg",
        'chart_07': "chart_07_ber_waterfall_awgn_theory.svg",
        'chart_08': "chart_08_pdr_preamble_sensitivity_bpsk.svg",
        'chart_09': "chart_09_pdr_preamble_sensitivity_qpsk.svg",
        'chart_10_bpsk': "chart_10_timing_drift_tracking_bpsk.svg",
        'chart_10_qpsk': "chart_10_timing_drift_tracking_qpsk.svg",
        'chart_13': "chart_13_software_vs_hardware_profile_comparison.svg"
    }
    
    svg_content = {}
    for k, fname in svg_files.items():
        fpath = os.path.join(charts_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r") as sf:
                svg_content[k] = sf.read()
        else:
            svg_content[k] = f"<p class='text-muted'>Chart {fname} not found.</p>"
            
    # Convert records to compact JSON string
    records_json = json.dumps(records)
    
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
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --success: #16a34a;
            --warning: #d97706;
            --danger: #dc2626;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            max-width: 1560px;
            margin: 0 auto 24px auto;
            background: var(--card-bg);
            padding: 28px 36px;
            border-radius: 14px;
            border: 1px solid var(--border);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 26px; color: var(--text-main); }}
        .header p {{ margin: 0; color: var(--text-muted); font-size: 15px; }}
        .container {{
            max-width: 1560px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .kpi-title {{ font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; margin-bottom: 6px; }}
        .kpi-value {{ font-size: 22px; font-weight: 700; color: var(--primary); }}
        .kpi-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}
        
        .card {{
            background: var(--card-bg);
            border-radius: 14px;
            padding: 24px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 18px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 12px;
            color: var(--primary-dark);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        /* Filter Controls */
        .filter-panel {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            background: #f1f5f9;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .filter-group label {{
            font-size: 12px;
            font-weight: 600;
            color: #334155;
        }}
        .filter-group select, .filter-group input {{
            padding: 8px 12px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 13px;
            background: #ffffff;
            color: #0f172a;
        }}
        .slider-wrap {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .slider-wrap input[type=range] {{
            flex: 1;
        }}
        .slider-val {{
            font-size: 12px;
            font-weight: 600;
            color: var(--primary);
            min-width: 45px;
        }}
        
        .btn {{
            padding: 9px 16px;
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
        .btn-secondary {{ background: #e2e8f0; color: #334155; }}
        .btn-secondary:hover {{ background: #cbd5e1; }}
        
        /* Table */
        .table-responsive {{
            overflow-x: auto;
            max-height: 480px;
            border: 1px solid var(--border);
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}
        th {{
            background: #f8fafc;
            padding: 10px 14px;
            border-bottom: 2px solid var(--border);
            color: #334155;
            font-weight: 600;
            position: sticky;
            top: 0;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{ background: #f1f5f9; }}
        td {{
            padding: 9px 14px;
            border-bottom: 1px solid #f1f5f9;
            color: #1e293b;
        }}
        tr:hover td {{ background: #f8fafc; }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-bpsk {{ background: #dbeafe; color: #1e40af; }}
        .badge-qpsk {{ background: #f3e8ff; color: #6b21a8; }}
        .badge-pass {{ background: #dcfce7; color: #166534; }}
        
        /* Pagination */
        .pagination {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 14px;
            font-size: 13px;
            color: var(--text-muted);
        }}
        .page-btns {{
            display: flex;
            gap: 6px;
        }}
        
        /* Chart Grid */
        .chart-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .full-width {{ grid-column: span 2; }}
        svg {{ width: 100%; height: auto; display: block; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>PHY2 Physical Layer Interactive Analytics & Parameter Explorer</h1>
        <p>Real-Time Parameter Sweeper, Faceted Multi-Range Filter, and Hardware SDR Validation Matrix (y·y' TED)</p>
    </div>

    <div class="container">
        <!-- KPI Summary Cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Evaluated Configurations</div>
                <div class="kpi-value" id="kpi-total">{len(records):,}</div>
                <div class="kpi-sub">0.005 to 1.000 rad/sym bandwidth spans</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">BPSK Optimal Tuning</div>
                <div class="kpi-value">FLL 0.0314 | Costas 0.0628</div>
                <div class="kpi-sub">SymSync 0.0250 | PDR 90.0% to 95.0%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">QPSK Optimal Tuning</div>
                <div class="kpi-value">FLL 0.0314 | Costas 0.0628</div>
                <div class="kpi-sub">SymSync 0.1150 | PDR 90.0% to 95.0%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Hardware Tolerance</div>
                <div class="kpi-value">±2.5% fs Offset</div>
                <div class="kpi-sub">Clock Drift: 0.9992 .. 1.0008 (±800 ppm)</div>
            </div>
        </div>

        <!-- Faceted Search & Filter Panel with CSV Search -->
        <div class="card">
            <h2>
                <span>Searchable Parameter Explorer & Data Filter</span>
                <div>
                    <button class="btn btn-secondary" onclick="resetFilters()">Reset Filters</button>
                    <button class="btn btn-primary" onclick="exportFilteredCSV()">Export Filtered CSV</button>
                </div>
            </h2>

            <div class="filter-panel">
                <!-- Search Box -->
                <div class="filter-group">
                    <label>Free Text Search</label>
                    <input type="text" id="search-box" placeholder="Search parameters..." oninput="applyFilters()">
                </div>

                <!-- Modulation Selector -->
                <div class="filter-group">
                    <label>Modulation Scheme</label>
                    <select id="filter-mod" onchange="applyFilters()">
                        <option value="ALL">All Modulations</option>
                        <option value="BPSK">BPSK</option>
                        <option value="QPSK">QPSK</option>
                    </select>
                </div>

                <!-- Platform / Profile Selector -->
                <div class="filter-group">
                    <label>Target Channel Profile</label>
                    <select id="filter-platform" onchange="applyFilters()">
                        <option value="ALL">All Profiles</option>
                        <option value="software">Software Multipath</option>
                        <option value="hardware">Hardware SDR Profile</option>
                    </select>
                </div>

                <!-- Preamble Selector -->
                <div class="filter-group">
                    <label>Preamble Length (Bytes)</label>
                    <select id="filter-preamble" onchange="applyFilters()">
                        <option value="ALL">All Lengths</option>
                        <option value="16">16 Bytes</option>
                        <option value="24">24 Bytes</option>
                        <option value="32">32 Bytes</option>
                        <option value="48">48 Bytes</option>
                        <option value="64">64 Bytes</option>
                    </select>
                </div>

                <!-- Costas BW Max Slider -->
                <div class="filter-group">
                    <label>Costas Loop BW Max: <span id="val-costas" class="slider-val">1.000</span></label>
                    <div class="slider-wrap">
                        <input type="range" id="filter-costas" min="0.005" max="1.000" step="0.005" value="1.000" oninput="updateSliderVal('costas'); applyFilters();">
                    </div>
                </div>

                <!-- SymSync BW Max Slider -->
                <div class="filter-group">
                    <label>SymSync Loop BW Max: <span id="val-sym" class="slider-val">1.000</span></label>
                    <div class="slider-wrap">
                        <input type="range" id="filter-sym" min="0.005" max="1.000" step="0.005" value="1.000" oninput="updateSliderVal('sym'); applyFilters();">
                    </div>
                </div>

                <!-- Noise Voltage Max Slider -->
                <div class="filter-group">
                    <label>Max Noise Volt (Vn): <span id="val-noise" class="slider-val">0.50</span></label>
                    <div class="slider-wrap">
                        <input type="range" id="filter-noise" min="0.00" max="0.50" step="0.02" value="0.50" oninput="updateSliderVal('noise'); applyFilters();">
                    </div>
                </div>

                <!-- Min PDR Filter -->
                <div class="filter-group">
                    <label>Min PDR (%): <span id="val-pdr" class="slider-val">0.0%</span></label>
                    <div class="slider-wrap">
                        <input type="range" id="filter-pdr" min="0" max="100" step="5" value="0" oninput="updateSliderVal('pdr'); applyFilters();">
                    </div>
                </div>
            </div>

            <!-- Table -->
            <div class="table-responsive">
                <table id="data-table">
                    <thead>
                        <tr>
                            <th onclick="sortTable('mod_type')">Modulation ↕</th>
                            <th onclick="sortTable('fll_bw')">FLL BW ↕</th>
                            <th onclick="sortTable('costas_bw')">Costas BW ↕</th>
                            <th onclick="sortTable('sym_bw')">SymSync BW ↕</th>
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
                        <!-- Rows rendered by JavaScript -->
                    </tbody>
                </table>
            </div>

            <!-- Pagination Bar -->
            <div class="pagination">
                <div id="results-count">Showing 0 of 0 records</div>
                <div class="page-btns">
                    <button class="btn btn-secondary" onclick="prevPage()">« Previous</button>
                    <span id="page-num" style="align-self: center; font-weight: 600; margin: 0 8px;">Page 1</span>
                    <button class="btn btn-secondary" onclick="nextPage()">Next »</button>
                </div>
            </div>
        </div>

        <!-- Comprehensive Publication Chart Galleries -->
        <div class="card">
            <h2>Multi-Slice Parametric Visualizations (0.005 to 1.000 rad/sym)</h2>
            <div class="chart-grid">
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 01: BPSK - BER vs Costas Loop BW (0.005..1.000)</h3>
                    {svg_content['chart_01']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 02: QPSK - BER vs Costas Loop BW (0.005..1.000)</h3>
                    {svg_content['chart_02']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 03: BPSK - BER vs Symbol Sync BW (0.005..1.000)</h3>
                    {svg_content['chart_03']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 04: QPSK - BER vs Symbol Sync BW (0.005..1.000)</h3>
                    {svg_content['chart_04']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 05: BPSK - FLL Carrier Acquisition Range</h3>
                    {svg_content['chart_05']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 06: QPSK - FLL Carrier Acquisition Range</h3>
                    {svg_content['chart_06']}
                </div>
                <div class="full-width">
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 07: BER Waterfall vs Noise Voltage with Theoretical Shannon Bounds</h3>
                    {svg_content['chart_07']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 08: BPSK - PDR (%) vs Noise across Preambles</h3>
                    {svg_content['chart_08']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 09: QPSK - PDR (%) vs Noise across Preambles</h3>
                    {svg_content['chart_09']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 10: Sampling Clock Drift Tracking Stability (BPSK)</h3>
                    {svg_content['chart_10_bpsk']}
                </div>
                <div>
                    <h3 style="font-size:14px; color:#1e40af; margin-top:0;">Chart 13: Software Multipath vs Hardware Profile Comparison</h3>
                    {svg_content['chart_13']}
                </div>
            </div>
        </div>
    </div>

    <!-- JavaScript Data Engine -->
    <script>
        const rawData = {records_json};
        let filteredData = [...rawData];
        let currentPage = 1;
        const pageSize = 25;
        let currentSortCol = 'pdr';
        let sortAsc = false;

        function updateSliderVal(name) {{
            if (name === 'costas') document.getElementById('val-costas').innerText = parseFloat(document.getElementById('filter-costas').value).toFixed(3);
            if (name === 'sym') document.getElementById('val-sym').innerText = parseFloat(document.getElementById('filter-sym').value).toFixed(3);
            if (name === 'noise') document.getElementById('val-noise').innerText = parseFloat(document.getElementById('filter-noise').value).toFixed(2);
            if (name === 'pdr') document.getElementById('val-pdr').innerText = document.getElementById('filter-pdr').value + '%';
        }}

        function applyFilters() {{
            const search = document.getElementById('search-box').value.toLowerCase();
            const mod = document.getElementById('filter-mod').value;
            const platform = document.getElementById('filter-platform').value;
            const preamble = document.getElementById('filter-preamble').value;
            const maxCostas = parseFloat(document.getElementById('filter-costas').value);
            const maxSym = parseFloat(document.getElementById('filter-sym').value);
            const maxNoise = parseFloat(document.getElementById('filter-noise').value);
            const minPdr = parseFloat(document.getElementById('filter-pdr').value);

            filteredData = rawData.filter(r => {{
                if (mod !== 'ALL' && r.mod_type !== mod) return false;
                if (platform !== 'ALL' && r.platform_mode !== platform) return false;
                if (preamble !== 'ALL' && r.preamble_size !== parseInt(preamble)) return false;
                if (r.costas_bw > maxCostas + 1e-4) return false;
                if (r.sym_bw > maxSym + 1e-4) return false;
                if (r.noise_volt > maxNoise + 1e-4) return false;
                if (r.pdr < minPdr - 1e-4) return false;
                
                if (search) {{
                    const str = `${{r.mod_type}} ${{r.fll_bw}} ${{r.costas_bw}} ${{r.sym_bw}} ${{r.preamble_size}} ${{r.platform_mode}} ${{r.pdr}} ${{r.ber}}`.toLowerCase();
                    if (!str.includes(search)) return false;
                }}
                return true;
            }});

            currentPage = 1;
            sortData();
            renderTable();
        }}

        function resetFilters() {{
            document.getElementById('search-box').value = '';
            document.getElementById('filter-mod').value = 'ALL';
            document.getElementById('filter-platform').value = 'ALL';
            document.getElementById('filter-preamble').value = 'ALL';
            document.getElementById('filter-costas').value = 1.000;
            document.getElementById('filter-sym').value = 1.000;
            document.getElementById('filter-noise').value = 0.50;
            document.getElementById('filter-pdr').value = 0;
            updateSliderVal('costas');
            updateSliderVal('sym');
            updateSliderVal('noise');
            updateSliderVal('pdr');
            applyFilters();
        }}

        function sortTable(col) {{
            if (currentSortCol === col) {{
                sortAsc = !sortAsc;
            }} else {{
                currentSortCol = col;
                sortAsc = false;
            }}
            sortData();
            renderTable();
        }}

        function sortData() {{
            filteredData.sort((a, b) => {{
                let vA = a[currentSortCol];
                let vB = b[currentSortCol];
                if (typeof vA === 'string') {{
                    return sortAsc ? vA.localeCompare(vB) : vB.localeCompare(vA);
                }}
                return sortAsc ? vA - vB : vB - vA;
            }});
        }}

        function renderTable() {{
            const tbody = document.getElementById('table-body');
            tbody.innerHTML = '';
            const total = filteredData.length;
            const start = (currentPage - 1) * pageSize;
            const end = Math.min(start + pageSize, total);
            const pageRecords = filteredData.slice(start, end);

            for (const r of pageRecords) {{
                const tr = document.createElement('tr');
                const modBadge = r.mod_type === 'BPSK' ? 'badge-bpsk' : 'badge-qpsk';
                const pdrColor = r.pdr >= 85 ? 'color:#16a34a; font-weight:600;' : (r.pdr >= 50 ? 'color:#d97706;' : 'color:#dc2626;');
                tr.innerHTML = `
                    <td><span class="badge ${{modBadge}}">${{r.mod_type}}</span></td>
                    <td>${{r.fll_bw.toFixed(4)}}</td>
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
            const totalPages = Math.ceil(filteredData.length / pageSize);
            if (currentPage < totalPages) {{
                currentPage++;
                renderTable();
            }}
        }}

        function exportFilteredCSV() {{
            if (!filteredData.length) {{
                alert("No records to export!");
                return;
            }}
            const headers = ["Modulation", "FLL_BW", "Costas_BW", "SymSync_BW", "Preamble_Bytes", "Noise_Volt", "Freq_Offset", "Time_Offset", "Platform", "PDR_Percent", "BER"];
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

        // Initial Load
        sortData();
        renderTable();
    </script>
</body>
</html>
"""
    output_html = os.path.join(dashboard_dir, "index.html")
    with open(output_html, "w") as f:
        f.write(html_content)
        
    print(f"[OK] Master interactive dashboard successfully built at: {output_html}")
    return 0

if __name__ == '__main__':
    sys.exit(build_master_dashboard())
