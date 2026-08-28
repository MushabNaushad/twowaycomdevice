#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Adapted Original Transceiver Test Runner
Evaluates the user's adapted original transceiver across BPSK and QPSK modulation schemes
under active channel impairments with y·y' ML Timing Error Detector.
"""

import sys
import os
import argparse
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.adapted_original.adapted_transceiver import AdaptedOriginalTransceiver

def run_test(mod_type='ALL', fll_bw=0.0314, costas_bw=0.0628, sym_bw=0.025):
    print("================================================================================")
    print("               PHY2 ADAPTED ORIGINAL TRANSCEIVER VALIDATION                     ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    payload_size = 64
    packets = 20
    test_payload = [int((p * 29 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    test_scenarios = [
        ("Light Channel Impairments", 0.02, 0.005, 1.0001),
        ("Moderate Carrier Offset",   0.03, 0.010, 1.0001),
        ("Clock Drift & Noise",       0.05, -0.008, 0.9998),
    ]
    all_passed = True
    
    import time
    t_global = time.time()
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} ---")
        for sc_name, nv, fo, to in test_scenarios:
            cur_sym_bw = 0.1150 if mod == 'QPSK' and sym_bw == 0.025 else sym_bw
            t_sc = time.time()
            tb = AdaptedOriginalTransceiver(
                test_payload=test_payload,
                mod_type=mod,
                payload_size=payload_size,
                packets=packets,
                fll_loop_bw=fll_bw,
                costas_bw=costas_bw,
                sym_bw=cur_sym_bw,
                noise_volt=nv,
                freq_offset=fo,
                time_offset=to
            )
            tb.run()
            sc_elapsed = time.time() - t_sc
            
            rx_bytes = list(tb.packet_sink.data())
            received_packets = len(rx_bytes) // payload_size
            pdr = (received_packets / float(packets)) * 100.0
            
            status = "\033[92m[PASS]\033[0m" if pdr >= 75.0 else "\033[91m[FAIL]\033[0m"
            if pdr < 75.0: all_passed = False
            print(f" Scenario: {sc_name:<28} | Noise: {nv:4.2f} | Offset: {fo:+6.3f} | Drift: {to:6.4f} | PDR: {pdr:5.1f}% {status} (Ran: {sc_elapsed:.3f}s)")
            
    total_elapsed = time.time() - t_global
    print("================================================================================")
    print(f" Actual Ran Time: \033[96m\033[1m{total_elapsed:.2f} seconds\033[0m ({len(modulations) * len(test_scenarios)} scenarios evaluated)")
    if all_passed:
        print(" \033[92m\033[1m>>> ALL ADAPTED ORIGINAL SCENARIOS PASSED WITH HIGH PDR! <<<\033[0m")
    else:
        print(" \033[91m\033[1m>>> ONE OR MORE ADAPTED ORIGINAL SCENARIOS FAILED! <<<\033[0m")
    print("================================================================================")
    return all_passed

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Adapted Original Transceiver Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['ALL', 'BPSK', 'QPSK'])
    parser.add_argument('--fll', type=float, default=0.0314, help="FLL Band-Edge Loop BW")
    parser.add_argument('--costas', type=float, default=0.0628, help="Costas Loop BW")
    parser.add_argument('--sym', type=float, default=0.025, help="Symbol Sync Loop BW")
    args = parser.parse_args()
    
    sys.exit(0 if run_test(args.mod, args.fll, args.costas, args.sym) else 1)
