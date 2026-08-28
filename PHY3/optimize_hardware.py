#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY3 Hardware Optimization Suite
Executes live hardware parameter optimization directly across connected physical SDRs
(Adalm-Pluto SDR, Nuand bladeRF, RTL-SDR) using the exact signal chain from CDP transeciever.grc.
Supports BPSK and QPSK characterization over 0.005 to 1.000 rad/sym loop bandwidths.
"""

import sys
import os
import time
import math
import json
import csv
import argparse
import itertools
import gc
import numpy as np

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

os.environ['HOME'] = WORKSPACE_ROOT
os.environ['GR_CONF_VMCIRCBUF_DEFAULT_FACTORY'] = 'gr::vmcircbuf_mmap_tmpfile_factory'
os.environ['GR_CONF_vmcircbuf_default_factory'] = 'gr::vmcircbuf_mmap_tmpfile_factory'

from PHY3.cdp_hardware_transceiver import CDPHardwareTransceiver

def run_hardware_optimization(hw_type='pluto',
                              mod_type='all',
                              uri='ip:192.168.2.1',
                              cf=433.98e6,
                              tx_gain=20.0,
                              rx_gain=30.0,
                              candidates_file=None,
                              top_n=None):
    """
    Runs automated hardware parameter optimization on the connected physical SDR.
    """
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    
    print("================================================================================")
    print(f"       PHY3 SDR HARDWARE LIVE OPTIMIZATION ENGINE ({hw_type.upper()})           ")
    print("================================================================================")
    
    selected_mods = ['BPSK', 'QPSK'] if mod_type.lower() == 'all' else [mod_type.upper()]
    
    # 1. Candidate Grid Determination
    default_candidates = [
        os.path.join(WORKSPACE_ROOT, "PHY2/hardware/top_50000_low_ber_candidates.json"),
        os.path.join(WORKSPACE_ROOT, "PHY3/results/top_candidates.json")
    ]
    
    if candidates_file is None:
        for cand_path in default_candidates:
            if os.path.exists(cand_path):
                candidates_file = cand_path
                break
                
    grid = []
    if candidates_file and not os.path.exists(candidates_file):
        print(f"\033[93m[WARNING] Candidates file not found: {candidates_file}. Falling back to calibrated hardware grid.\033[0m")
        candidates_file = None

    if candidates_file and os.path.exists(candidates_file):
        print(f"Loading top candidate configurations from: {candidates_file} ...")
        try:
            with open(candidates_file, 'r') as f:
                cands = json.load(f)
            # Filter by selected modulations
            cands = [c for c in cands if c.get('mod_type', 'BPSK').upper() in selected_mods]
            if top_n is not None and top_n > 0:
                cands = cands[:top_n]
            grid = [(c['mod_type'], float(c['fll_bw']), float(c['costas_bw']), float(c['sym_bw']), int(c.get('preamble_size', 32))) for c in cands]
            print(f"Loaded {len(grid):,} prioritized candidate combinations.")
        except Exception as e:
            print(f"[WARN] Could not parse candidates file ({e}). Falling back to calibrated hardware grid.")
            candidates_file = None

    if not grid:
        # Calibrated dense hardware grid
        costas_vals = [0.005, 0.015, 0.035, 0.0628, 0.100, 0.165, 0.250, 0.400, 0.600, 0.800, 1.000]
        sym_vals    = [0.005, 0.015, 0.025, 0.045, 0.075, 0.115, 0.180, 0.300, 0.500, 0.750, 1.000]
        fll_vals    = [0.005, 0.015, 0.0314, 0.055, 0.100, 0.190, 0.350, 0.600, 1.000]
        preambles   = [16, 32, 48]
        
        grid = list(itertools.product(selected_mods, fll_vals, costas_vals, [0.025], [32])) + \
               list(itertools.product(selected_mods, [0.0314], [0.0628], sym_vals, [32])) + \
               list(itertools.product(selected_mods, [0.0314], [0.0628], [0.025], preambles))
        grid = list(set(grid))
        if top_n is not None and top_n > 0:
            grid = grid[:top_n]
            
    payload_size = 64
    packets = 10
    test_payload = [int((p * 37 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    print(f"Hardware Target: '{hw_type.upper()}' | Total Configurations to Evaluate: {len(grid):,}")
    print(f"Carrier Frequency: {cf/1e6:.2f} MHz | TX Gain: {tx_gain} dB | RX Gain: {rx_gain} dB")
    
    all_results = []
    total_trials = len(grid)
    t0 = time.time()
    
    def render_progress_bar(current, total, t_start, bar_length=30):
        percent = (current / float(total)) * 100.0
        filled_len = int(bar_length * current // total)
        bar = '█' * filled_len + '░' * (bar_length - filled_len)
        elapsed = time.time() - t_start
        rate = current / max(elapsed, 0.001)
        remaining_sec = (total - current) / max(rate, 0.001) if rate > 0 else 0
        mins_rem, secs_rem = divmod(int(remaining_sec), 60)
        mins_el, secs_el = divmod(int(elapsed), 60)
        sys.stdout.write(f"\r[\033[96mHW PROGRESS\033[0m] [{bar}] \033[92m{percent:5.1f}%\033[0m ({current:,}/{total:,}) | \033[93m{rate:4.1f} trials/s\033[0m | Elapsed: {mins_el:02d}:{secs_el:02d} | ETA: {mins_rem:02d}:{secs_rem:02d}  ")
        sys.stdout.flush()
        
    for trial_idx, (m_type, f_bw, c_bw, s_bw, p_len) in enumerate(grid, start=1):
        tb = None
        t_trial_start = time.time()
        pdr = 0.0
        matched = 0
        rx_pkts = 0
        
        try:
            tb = CDPHardwareTransceiver(
                test_payload=test_payload,
                mod_type=m_type,
                payload_size=payload_size,
                packets=packets,
                preamble_size=p_len,
                fll_loop_bw=f_bw,
                costas_bw=c_bw,
                sym_bw=s_bw,
                hw_type=hw_type,
                uri=uri,
                cf=cf,
                tx_gain=tx_gain,
                rx_gain=rx_gain
            )
            tb.run()
            
            rx_bytes = list(tb.packet_sink.data())
            rx_pkts = len(rx_bytes) // payload_size
            pdr = (rx_pkts / float(packets)) * 100.0
            
            matched_originals = set()
            for p in range(rx_pkts):
                pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
                for orig_p in range(packets):
                    if orig_p in matched_originals:
                        continue
                    orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                    if pkt == orig_pkt:
                        matched += 1
                        matched_originals.add(orig_p)
                        break
        except KeyboardInterrupt:
            print("\n[USER] Optimization cancelled by user.")
            break
        except Exception as e:
            # Physical hardware disconnection or driver error
            pdr = 0.0
            matched = 0
            rx_pkts = 0
        finally:
            if tb is not None:
                try:
                    tb.stop()
                    tb.wait()
                    tb.disconnect_all()
                except Exception:
                    pass
                del tb
                
        elapsed_trial = time.time() - t_trial_start
        lost = max(0, packets - matched)
        ber = (lost / float(packets)) * 0.5
        
        all_results.append({
            'mod_type': m_type,
            'hw_type': hw_type,
            'fll_bw': round(float(f_bw), 4),
            'costas_bw': round(float(c_bw), 4),
            'sym_bw': round(float(s_bw), 4),
            'preamble_size': int(p_len),
            'cf_mhz': round(float(cf / 1e6), 2),
            'tx_gain': float(tx_gain),
            'rx_gain': float(rx_gain),
            'pdr': round(float(pdr), 2),
            'ber': round(float(ber), 6),
            'matched_packets': int(matched),
            'total_packets': int(packets),
            'elapsed_sec': round(float(elapsed_trial), 4)
        })
        
        if trial_idx % 5 == 0 or trial_idx == total_trials:
            render_progress_bar(trial_idx, total_trials, t0)
            
    sys.stdout.write("\n")
    sys.stdout.flush()
    total_elapsed = time.time() - t0
    
    # 2. Incremental Merge & Save Results
    json_path = os.path.join(results_dir, "hardware_optimization_results.json")
    csv_path = os.path.join(results_dir, "hardware_optimization_results.csv")
    
    records_map = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                existing = json.load(f)
            for r in existing:
                key = (
                    r.get('mod_type', 'BPSK'),
                    r.get('hw_type', hw_type),
                    f"{float(r.get('fll_bw', 0)):.4f}",
                    f"{float(r.get('costas_bw', 0)):.4f}",
                    f"{float(r.get('sym_bw', 0)):.4f}",
                    int(r.get('preamble_size', 32))
                )
                records_map[key] = r
        except Exception:
            pass
            
    for r in all_results:
        key = (
            r['mod_type'],
            r['hw_type'],
            f"{float(r['fll_bw']):.4f}",
            f"{float(r['costas_bw']):.4f}",
            f"{float(r['sym_bw']):.4f}",
            int(r['preamble_size'])
        )
        records_map[key] = r
        
    merged_results = list(records_map.values())
    
    with open(json_path, 'w') as f:
        json.dump(merged_results, f, indent=2)
        
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['mod_type', 'hw_type', 'fll_bw', 'costas_bw', 'sym_bw', 'preamble_size',
                         'cf_mhz', 'tx_gain', 'rx_gain', 'pdr', 'ber', 'matched_packets', 'total_packets', 'elapsed_sec'])
        for r in merged_results:
            writer.writerow([
                r.get('mod_type', 'BPSK'),
                r.get('hw_type', hw_type),
                r.get('fll_bw', 0),
                r.get('costas_bw', 0),
                r.get('sym_bw', 0),
                r.get('preamble_size', 32),
                r.get('cf_mhz', cf/1e6),
                r.get('tx_gain', tx_gain),
                r.get('rx_gain', rx_gain),
                r.get('pdr', 0),
                r.get('ber', 0.5),
                r.get('matched_packets', 0),
                r.get('total_packets', 10),
                r.get('elapsed_sec', 0)
            ])
            
    # 3. Pinpoint Optimal Parameters per Modulation
    optimal_params = {}
    for mod in selected_mods:
        mod_runs = [r for r in merged_results if r.get('mod_type') == mod and r.get('hw_type') == hw_type]
        if not mod_runs:
            mod_runs = [r for r in merged_results if r.get('mod_type') == mod]
        if not mod_runs:
            continue
            
        # Rank by lowest BER, highest PDR, shortest preamble
        ranked = sorted(mod_runs, key=lambda x: (float(x['ber']), -float(x['pdr']), int(x['preamble_size'])))
        best = ranked[0]
        optimal_params[mod] = {
            'modulation': mod,
            'hw_type': hw_type,
            'fll_loop_bw': best['fll_bw'],
            'costas_bw': best['costas_bw'],
            'sym_bw': best['sym_bw'],
            'preamble_size': best['preamble_size'],
            'pdr': best['pdr'],
            'ber': best['ber'],
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
    opt_json_path = os.path.join(results_dir, "optimal_hardware_parameters.json")
    with open(opt_json_path, 'w') as f:
        json.dump(optimal_params, f, indent=2)
        
    print(f"\n================================================================================")
    print(f" >>> PHY3 HARDWARE OPTIMIZATION COMPLETED ({total_elapsed:.2f}s) <<<")
    print(f"  • New Trials Completed      : {len(all_results):,}")
    print(f"  • Cumulative Dataset Size   : {len(merged_results):,} records")
    print(f"  • Results Saved To          : {results_dir}")
    print(f"================================================================================")
    for mod, opt in optimal_params.items():
        print(f"  [{mod}] -> FLL: {opt['fll_loop_bw']:.4f} rad/sym | Costas: {opt['costas_bw']:.4f} rad/sym | SymSync: {opt['sym_bw']:.4f} rad/sym | Preamble: {opt['preamble_size']} B | PDR: {opt['pdr']}% | BER: {opt['ber']:.5f}")
    print("================================================================================\n")
    
    return merged_results, optimal_params

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY3 SDR Hardware Live Optimizer")
    parser.add_argument('--hw', type=str, default='pluto', choices=['pluto', 'bladerf', 'rtlsdr', 'sim'],
                        help="SDR Hardware target (default: pluto)")
    parser.add_argument('--mod', type=str, default='all', choices=['BPSK', 'QPSK', 'all'],
                        help="Modulation scheme to optimize (default: all)")
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1', help="Adalm-Pluto network URI or USB ID")
    parser.add_argument('--cf', type=float, default=433.98e6, help="RF Center Frequency in Hz (default: 433.98 MHz)")
    parser.add_argument('--tx-gain', type=float, default=20.0, help="TX Gain in dB (default: 20.0)")
    parser.add_argument('--rx-gain', type=float, default=30.0, help="RX Gain in dB (default: 30.0)")
    parser.add_argument('--candidates', type=str, default=None, help="Path to top candidate JSON file")
    parser.add_argument('--top-n', type=int, default=None, help="Number of top candidates to evaluate")
    args = parser.parse_args()
    
    run_hardware_optimization(
        hw_type=args.hw,
        mod_type=args.mod,
        uri=args.uri,
        cf=args.cf,
        tx_gain=args.tx_gain,
        rx_gain=args.rx_gain,
        candidates_file=args.candidates,
        top_n=args.top_n
    )
