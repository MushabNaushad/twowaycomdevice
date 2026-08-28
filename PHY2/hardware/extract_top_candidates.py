#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Hardware Candidate Extractor
Extracts the top 50,000 parameter combinations with the lowest Bit Error Rate (BER)
and highest Packet Delivery Rate (PDR) from the simulation dataset for physical SDR hardware execution.
"""

import os
import sys
import json
import csv
import argparse
import time
import numpy as np

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, WORKSPACE_ROOT)

DEFAULT_INPUT_JSON = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/results/deep_sweep_results.json")
DEFAULT_OUTPUT_JSON = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/top_50000_low_ber_candidates.json")
DEFAULT_OUTPUT_CSV = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/top_50000_low_ber_candidates.csv")

def extract_top_candidates(input_json=None, output_json=None, output_csv=None, top_n=50000):
    t0 = time.time()
    input_json = input_json or DEFAULT_INPUT_JSON
    output_json = output_json or DEFAULT_OUTPUT_JSON
    output_csv = output_csv or DEFAULT_OUTPUT_CSV

    if not os.path.exists(input_json):
        raise FileNotFoundError(f"Simulation dataset not found at: {input_json}. Run simulation sweeps first!")

    print("=" * 80)
    print(f"       PHY2 TOP CANDIDATE EXTRACTOR (TOP {top_n:,} LOWEST BER CANDIDATES)       ")
    print("=" * 80)
    print(f"Loading simulation dataset from: {input_json} ...")

    with open(input_json, 'r') as f:
        records = json.load(f)

    print(f"Loaded {len(records):,} simulation records. Aggregating unique transceiver configurations...")

    # Group by tunable DSP parameters: (mod_type, fll_bw, costas_bw, sym_bw, preamble_size)
    config_map = {}
    for r in records:
        key = (
            r['mod_type'],
            round(float(r['fll_bw']), 4),
            round(float(r['costas_bw']), 4),
            round(float(r['sym_bw']), 4),
            int(r.get('preamble_size', 32))
        )
        if key not in config_map:
            config_map[key] = []
        config_map[key].append(r)

    print(f"Aggregated {len(config_map):,} unique DSP configurations. Computing BER & stability scores...")

    ranked_candidates = []
    for (mod, fll, costas, sym, plen), runs in config_map.items():
        bers = [x['ber'] for x in runs]
        pdrs = [x['pdr'] for x in runs]
        avg_ber = float(np.mean(bers))
        avg_pdr = float(np.mean(pdrs))
        min_ber = float(np.min(bers))
        max_noise_pass = max([x.get('noise_volt', 0.0) for x in runs if x['ber'] == 0.0 or x['pdr'] >= 80.0], default=0.0)
        
        # Composite score: higher is better
        # Prioritize 0-BER, 100% PDR, noise resilience, and preamble compactness
        score = ((1.0 - avg_ber) * 1000.0) + (avg_pdr * 10.0) + (max_noise_pass * 50.0) - (plen * 0.05)
        
        ranked_candidates.append({
            'rank': 0,
            'mod_type': mod,
            'fll_bw': fll,
            'costas_bw': costas,
            'sym_bw': sym,
            'preamble_size': plen,
            'avg_ber': round(avg_ber, 6),
            'min_ber': round(min_ber, 6),
            'avg_pdr': round(avg_pdr, 2),
            'max_noise_tolerance': round(max_noise_pass, 3),
            'composite_score': round(score, 4),
            'tested_scenarios': len(runs)
        })

    # Sort strictly: lowest avg_ber -> highest avg_pdr -> highest noise tolerance -> shortest preamble
    ranked_candidates_all = list(ranked_candidates)
    
    # Filter out broken configs that received almost nothing
    ranked_candidates = [c for c in ranked_candidates if c['avg_pdr'] >= 50.0]
    if len(ranked_candidates) < top_n:
        # If not enough, include lower PDR candidates too
        low_pdr = [c for c in ranked_candidates_all if c['avg_pdr'] < 50.0]
        low_pdr.sort(key=lambda x: (-x['composite_score'],))
        ranked_candidates.extend(low_pdr[:top_n - len(ranked_candidates)])
    
    ranked_candidates.sort(key=lambda x: (-x['composite_score'],))

    # Slice top N candidates and assign 1-based ranks
    selected_candidates = ranked_candidates[:top_n]
    for i, cand in enumerate(selected_candidates, 1):
        cand['rank'] = i

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    # Save to JSON
    with open(output_json, 'w') as f:
        json.dump(selected_candidates, f, indent=2)

    # Save to CSV
    fieldnames = [
        'rank', 'mod_type', 'fll_bw', 'costas_bw', 'sym_bw', 'preamble_size',
        'avg_ber', 'min_ber', 'avg_pdr', 'max_noise_tolerance', 'composite_score', 'tested_scenarios'
    ]
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_candidates)

    # Also mirror to optimization results directory
    opt_csv = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/results", os.path.basename(output_csv))
    opt_json = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/results", os.path.basename(output_json))
    os.makedirs(os.path.dirname(opt_json), exist_ok=True)
    with open(opt_json, 'w') as f:
        json.dump(selected_candidates, f, indent=2)
    with open(opt_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_candidates)

    elapsed = time.time() - t0
    bpsk_count = sum(1 for x in selected_candidates if x['mod_type'] == 'BPSK')
    qpsk_count = sum(1 for x in selected_candidates if x['mod_type'] == 'QPSK')

    print("\n" + "=" * 80)
    print(f" \033[92m\033[1m>>> TOP {len(selected_candidates):,} CANDIDATES EXTRACTED SUCCESSFULLY IN {elapsed:.2f}s! <<<\033[0m")
    print(f"  • \033[1mBPSK Configurations\033[0m : \033[96m{bpsk_count:,}\033[0m")
    print(f"  • \033[1mQPSK Configurations\033[0m : \033[96m{qpsk_count:,}\033[0m")
    print(f"  • \033[1mOutput JSON File\033[0m    : \033[93m{output_json}\033[0m")
    print(f"  • \033[1mOutput CSV File\033[0m     : \033[93m{output_csv}\033[0m")
    print("=" * 80 + "\n")
    
    return selected_candidates

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract top lowest-BER candidates for SDR Hardware runs")
    parser.add_argument('--input', type=str, default=DEFAULT_INPUT_JSON, help="Input simulation JSON path")
    parser.add_argument('--output-json', type=str, default=DEFAULT_OUTPUT_JSON, help="Output JSON path")
    parser.add_argument('--output-csv', type=str, default=DEFAULT_OUTPUT_CSV, help="Output CSV path")
    parser.add_argument('--top-n', type=int, default=50000, help="Number of top configurations to extract (default: 50000)")
    args = parser.parse_args()

    extract_top_candidates(args.input, args.output_json, args.output_csv, args.top_n)
