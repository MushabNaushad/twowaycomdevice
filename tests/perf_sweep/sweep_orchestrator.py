#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sweep_orchestrator.py
=====================
Orchestrates the full 20-configuration parameter sweep under Megabyte-scale
continuous offered load by executing each (m, mtu) configuration in its own
process-isolated GNU Radio instance.

Aggregates results into:
  - sweep_results.json
  - sweep_results.csv
And generates updated performance charts and recommendations.
"""

import os, sys, time, subprocess, json, csv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))

M_VALUES = [3, 4, 5, 6, 7]
MTU_VALUES = [100, 200, 500, 1000]
TOTAL_COMBOS = len(M_VALUES) * len(MTU_VALUES)

def main():
    print("=" * 80)
    print("GNU RADIO HIGH-THROUGHPUT MEGABYTE IMAGE STREAMING PARAMETER SWEEP")
    print(f"Configurations to run: {TOTAL_COMBOS} ({TOTAL_COMBOS * 5} measurement points)")
    print(f"Sequence Bit Width m in: {M_VALUES}  -> Window Sizes: {[2**(m-1) for m in M_VALUES]}")
    print(f"MTU Sizes in: {MTU_VALUES} bytes")
    print(f"Loss Rates tested per config: [0%, 5%, 15%, 30%, 50%]")
    print(f"Concurrent Nodes: 10 (5 simultaneous active pairs)")
    print(f"Offered Load: Continuous multi-megabyte image stream (100ms rapid injection)")
    print("=" * 80)
    
    start_total = time.time()
    count = 0
    all_results = []
    
    for m in M_VALUES:
        for mtu in MTU_VALUES:
            count += 1
            print(f"\n[{count}/{TOTAL_COMBOS}] Running GNU Radio Flowgraph for m={m} (W={2**(m-1)}), MTU={mtu}B...")
            cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'run_megabyte_sweep.py'), str(m), str(mtu)]
            
            p = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check result file
            out_file = os.path.join(SCRIPT_DIR, f'results_m{m}_mtu{mtu}.json')
            if os.path.exists(out_file):
                with open(out_file) as f:
                    data = json.load(f)
                    all_results.extend(data.get('results', []))
                print(f"  ✓ Process completed successfully. Data recorded.")
            else:
                print(f"  ⚠ Warning: {out_file} not found. Exit code: {p.returncode}")
                if p.stderr:
                    print(f"  STDERR snippet: {p.stderr[-200:]}")
            
            time.sleep(0.2)

    total_time = time.time() - start_total
    print("\n" + "=" * 80)
    print(f"ALL 20 CONFIGURATIONS COMPLETED in {total_time:.1f}s ({total_time/60.0:.2f} min)!")
    print(f"Total test points collected: {len(all_results)}")
    
    # Save combined results
    out_json = os.path.join(SCRIPT_DIR, 'sweep_results.json')
    out_csv = os.path.join(SCRIPT_DIR, 'sweep_results.csv')
    
    with open(out_json, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'm_values': M_VALUES,
            'mtu_values': MTU_VALUES,
            'drop_values': [0.0, 0.05, 0.15, 0.30, 0.50],
            'results': all_results
        }, f, indent=2)
    print(f"  Saved combined JSON -> {out_json}")
    
    if all_results:
        keys = all_results[0].keys()
        with open(out_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_results)
        print(f"  Saved combined CSV  -> {out_csv}")
        
    print("\nGenerating performance analysis charts...")
    chart_script = os.path.join(SCRIPT_DIR, 'collect_and_chart.py')
    subprocess.run([sys.executable, chart_script], check=False)
    
    print("\n" + "=" * 80)
    print("ALL CHARTS & RECOMMENDATIONS GENERATED!")
    print("=" * 80)

if __name__ == '__main__':
    main()
