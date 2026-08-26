#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Adapted Original Transceiver Optimizer
Runs combinatorial parameter sweeps on the user's original architecture to find optimal settings for BPSK and QPSK.
"""

import sys
import os
import time
import json
import itertools
from multiprocessing import Pool, cpu_count
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.adapted_original.adapted_transceiver import AdaptedOriginalTransceiver

def evaluate_trial(args):
    mod_type, fll_bw, costas_bw, sym_bw, plen, nv, fo, to, packets, payload_size = args
    test_payload = [int((p * 29 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    t0 = time.time()
    try:
        tb = AdaptedOriginalTransceiver(
            test_payload=test_payload,
            mod_type=mod_type,
            payload_size=payload_size,
            packets=packets,
            preamble_size=plen,
            fll_loop_bw=fll_bw,
            costas_bw=costas_bw,
            sym_bw=sym_bw,
            noise_volt=nv,
            freq_offset=fo,
            time_offset=to
        )
        tb.run()
        rx_bytes = list(tb.packet_sink.data())
        received_packets = len(rx_bytes) // payload_size
        pdr = (received_packets / float(packets)) * 100.0
        
        matched_count = 0
        for p in range(received_packets):
            pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
            for orig_p in range(packets):
                orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                if pkt == orig_pkt:
                    matched_count += 1
                    break
    except Exception as e:
        pdr = 0.0
        matched_count = 0
        received_packets = 0
        
    elapsed = time.time() - t0
    lost = packets - matched_count
    ber = (lost / float(packets)) * 0.5
    
    return {
        'mod_type': mod_type,
        'fll_bw': fll_bw,
        'costas_bw': costas_bw,
        'sym_bw': sym_bw,
        'preamble_size': plen,
        'noise_volt': nv,
        'freq_offset': fo,
        'time_offset': to,
        'pdr': pdr,
        'ber': ber,
        'matched_packets': matched_count,
        'total_packets': packets,
        'elapsed_sec': elapsed
    }

def run_optimization():
    print("================================================================================")
    print("        OPTIMIZING ADAPTED ORIGINAL TRANSCEIVER (BPSK & QPSK)                   ")
    print("================================================================================")
    
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)
    
    modulations = ['BPSK', 'QPSK']
    fll_bws = [0.010, 0.0314, 0.060]
    costas_bws = [0.030, 0.0628, 0.100]
    sym_bws = [0.025, 0.045, 0.080]
    preamble_lens = [32, 48]
    noise_volts = [0.02, 0.08]
    freq_offsets = [0.005, 0.015]
    time_offsets = [1.0001]
    
    grid = list(itertools.product(
        modulations, fll_bws, costas_bws, sym_bws, preamble_lens, noise_volts, freq_offsets, time_offsets, [15], [64]
    ))
    
    print(f"Total Combinatorial Grid Trials: {len(grid)} across {cpu_count()} CPU cores...")
    t0 = time.time()
    
    with Pool(processes=min(cpu_count(), 8)) as pool:
        results = pool.map(evaluate_trial, grid)
        
    total_elapsed = time.time() - t0
    print(f"[OK] Completed {len(results)} simulations in {total_elapsed:.2f}s ({len(results)/max(total_elapsed, 1e-4):.1f} sims/sec)")
    
    # Save results
    json_path = os.path.join(output_dir, "original_sweep_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
        
    # Analyze best parameters for each modulation
    best_results = {}
    for mod in modulations:
        mod_runs = [r for r in results if r['mod_type'] == mod]
        # Sort by highest average PDR and lowest BER
        best = sorted(mod_runs, key=lambda x: (-x['pdr'], x['ber'], x['preamble_size']))[0]
        best_results[mod] = best
        print(f"\n--- Best Parameters for {mod} ---")
        print(f"  FLL BW: {best['fll_bw']:.4f} | Costas BW: {best['costas_bw']:.4f} | Sym BW: {best['sym_bw']:.4f} | Preamble: {best['preamble_size']} B | PDR: {best['pdr']:.1f}%")
        
    with open(os.path.join(output_dir, "best_original_parameters.json"), "w") as f:
        json.dump(best_results, f, indent=2)
        
    print(f"\n[OK] Results saved to: {output_dir}")
    return 0

if __name__ == '__main__':
    sys.exit(run_optimization())
