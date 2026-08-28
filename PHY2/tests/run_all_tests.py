#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Test Suite Orchestrator
Executes all physical SDR hardware stages, modular transceiver tests, and stress benchmarks.
Supports live hardware execution (--hw pluto, --hw bladerf, --hw rtlsdr, --hw sim).
"""

import sys
import os
import time
import argparse

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.tests.test_05_fll_band_edge import run_stage_05
from PHY2.tests.test_06_linear_equalizer import run_stage_06
from PHY2.tests.test_07_preamble_access_code import run_stage_07
from PHY2.tests.test_08_packet_crc32 import run_stage_08
from PHY2.tests.test_09_cdp_transceiver import run_stage_09
from PHY2.tests.test_10_end_to_end_stress import run_stage_10
from PHY2.tests.test_adapted_original import run_stage_adapted_original

TEST_STAGES = [
    ("Stage 05: Hardware FLL Band-Edge Frequency Recovery", run_stage_05, 5),
    ("Stage 06: Hardware Correlation Estimator + Adaptive Equalizer", run_stage_06, 6),
    ("Stage 07: Hardware Preamble & Access Code Frame Sync", run_stage_07, 7),
    ("Stage 08: Hardware Packet Engine & CRC32 Verification", run_stage_08, 8),
    ("Stage 09: Hardware CDP Transceiver Architecture", run_stage_09, 9),
    ("Stage 10: Hardware Multi-Packet High-Volume Stress Test", run_stage_10, 10),
    ("Adapted Original Transceiver (y·y' TED)", run_stage_adapted_original, 11)
]

def run_suite(hw_type='sim', mod_filter='ALL', stage_filter=None, uri='ip:192.168.2.1', freq=433.98e6, gain=20.0):
    print("================================================================================")
    print(f"      PHY2 MASTER CENTRALIZED TEST SUITE (HW: {hw_type.upper()}, MOD: {mod_filter})      ")
    print("================================================================================")
    
    results = []
    t_start = time.time()
    
    for idx, (name, test_func, stage_num) in enumerate(TEST_STAGES, 1):
        if stage_filter is not None and stage_num != stage_filter:
            continue
            
        print(f"\n[{idx:02d}/{len(TEST_STAGES):02d}] Executing {name}...")
        t0 = time.time()
        try:
            passed = test_func(hw_type=hw_type, mod_type=mod_filter, uri=uri, freq=freq, gain=gain)
        except TypeError:
            try:
                passed = test_func(hw_type=hw_type, mod_type=mod_filter)
            except TypeError:
                passed = test_func()
        except Exception as e:
            print(f"       [ERROR] Stage failed with exception: {e}")
            passed = False
            
        elapsed = time.time() - t0
        res_str = "[PASS]" if passed else "[FAIL]"
        print(f"       Result: {res_str} (Elapsed: {elapsed:.2f}s)")
        results.append((name, passed, elapsed))
        
    t_total = time.time() - t_start
    
    print("\n================================================================================")
    print("                         CENTRALIZED TEST SUMMARY MATRIX                        ")
    print("================================================================================")
    pass_count = 0
    for idx, (name, passed, elapsed) in enumerate(results, 1):
        status = "PASS" if passed else "FAIL"
        if passed: pass_count += 1
        print(f" {idx:02d}. {name:<65} | {status} | {elapsed:5.2f}s")
        
    print("--------------------------------------------------------------------------------")
    print(f" Total Passed: {pass_count}/{len(results)} stages | Total Time: {t_total:.2f}s")
    
    if pass_count == len(results):
        print(" >>> ALL SELECTED HARDWARE STAGES & TRANSCEIVERS PASSED WITH 0 REGRESSIONS! <<<")
        print("================================================================================")
        return 0
    else:
        print(" >>> WARNING: ONE OR MORE STAGES FAILED! <<<")
        print("================================================================================")
        return 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Master Centralized Test Suite")
    parser.add_argument('--hw', type=str, default='sim', choices=['sim', 'pluto', 'bladerf', 'rtlsdr'], help="Hardware SDR target")
    parser.add_argument('--mod', type=str, default='ALL', choices=['ALL', 'BPSK', 'QPSK'], help="Modulation scheme")
    parser.add_argument('--stage', type=int, default=None, help="Optional single stage number (5..11)")
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1', help="Pluto SDR URI")
    parser.add_argument('--freq', type=float, default=433.98e6, help="RF Center Frequency")
    parser.add_argument('--gain', type=float, default=20.0, help="RF TX/RX Gain")
    args = parser.parse_args()
    
    sys.exit(run_suite(
        hw_type=args.hw,
        mod_filter=args.mod,
        stage_filter=args.stage,
        uri=args.uri,
        freq=args.freq,
        gain=args.gain
    ))
