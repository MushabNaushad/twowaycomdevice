#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 - Master Test Suite Orchestrator
Executes and validates all 10 incremental physical layer test stages and the adapted original transceiver
for both BPSK and QPSK modulation schemes under active channel impairments.
"""

import sys
import os
import argparse
import subprocess
import time

TEST_STAGES = [
    ("Stage 01: Baseband Constellation Loopback", "PHY2/test_01_bpsk_loopback/run_test.py"),
    ("Stage 02: RRC Pulse Shaping & AWGN Channel", "PHY2/test_02_bpsk_rrc_awgn/run_test.py"),
    ("Stage 03: Symbol Timing Recovery (Clock Drift)", "PHY2/test_03_bpsk_symbol_sync/run_test.py"),
    ("Stage 04: Costas Loop Carrier Phase Recovery", "PHY2/test_04_bpsk_costas_loop/run_test.py"),
    ("Stage 05: FLL Band-Edge Frequency Acquisition", "PHY2/test_05_bpsk_fll_band_edge/run_test.py"),
    ("Stage 06: Adaptive Linear Equalizer (Multipath ISI)", "PHY2/test_06_bpsk_linear_equalizer/run_test.py"),
    ("Stage 07: Preamble & Access Code Frame Sync", "PHY2/test_07_bpsk_preamble_access_code/run_test.py"),
    ("Stage 08: Full Packet Engine & CRC32 Verification", "PHY2/test_08_bpsk_packet_crc32/run_test.py"),
    ("Stage 09: CDP Modular Transceiver Architecture", "PHY2/test_09_bpsk_cdp_transceiver/run_test.py"),
    ("Stage 10: Multi-Impairment High-Volume Stress Test", "PHY2/test_10_bpsk_end_to_end_stress/run_test.py"),
    ("Adapted Original Transceiver Validation", "PHY2/adapted_original/run_original_test.py"),
]

def run_all(mod_type='ALL'):
    print("================================================================================")
    print(f"      PHY2 MASTER TEST SUITE VALIDATION (Modulation: {mod_type.upper()})        ")
    print("================================================================================")
    
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    results = []
    overall_start = time.time()
    
    for idx, (title, script_path) in enumerate(TEST_STAGES, 1):
        full_path = os.path.join(workspace_dir, script_path)
        print(f"\n[{idx:02d}/{len(TEST_STAGES):02d}] Executing {title}...")
        t0 = time.time()
        
        proc = subprocess.run(
            [sys.executable, full_path, "--mod", mod_type],
            cwd=workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        elapsed = time.time() - t0
        passed = (proc.returncode == 0)
        results.append((title, passed, elapsed, proc.stdout))
        
        status_str = "\033[92m[PASS]\033[0m" if passed else "\033[91m[FAIL]\033[0m"
        print(f"       Result: {status_str} (Elapsed: {elapsed:.2f}s)")
        if not passed:
            print("       Output Tail:\n" + "\n".join(proc.stdout.strip().splitlines()[-10:]))
            
    total_time = time.time() - overall_start
    all_passed = all(r[1] for r in results)
    
    print("\n================================================================================")
    print("                               TEST SUMMARY MATRIX                              ")
    print("================================================================================")
    for idx, (title, passed, elapsed, _) in enumerate(results, 1):
        status = "PASS" if passed else "FAIL"
        print(f" {idx:02d}. {title:58s} | {status:4s} | {elapsed:5.2f}s")
    print("--------------------------------------------------------------------------------")
    pass_count = sum(1 for r in results if r[1])
    print(f" Total Passed: {pass_count}/{len(results)} stages | Total Time: {total_time:.2f}s")
    
    if all_passed:
        print("\033[92m >>> ALL PHY2 TEST STAGES & ADAPTED TRANSCEIVERS PASSED WITH 0 REGRESSIONS! <<<\033[0m")
    else:
        print("\033[91m >>> SOME TESTS FAILED. PLEASE REVIEW LOGS ABOVE. <<<\033[0m")
    print("================================================================================")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PHY2 Master Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_all(args.mod))
