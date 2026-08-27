#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 - Master Hardware Suite Orchestrator
Executes and validates all dedicated SDR hardware stages (hw_05 to hw_10)
and the adapted original transceiver for both BPSK and QPSK modulation schemes.
"""

import sys
import os
import argparse
import subprocess
import time

HW_STAGES = [
    ("Stage 05: Hardware FLL Band-Edge Frequency Recovery", "PHY2/hw_05_fll_band_edge/run_test.py"),
    ("Stage 06: Hardware Correlation Estimator + Adaptive Equalizer", "PHY2/hw_06_linear_equalizer/run_test.py"),
    ("Stage 07: Hardware Preamble & Access Code Frame Sync", "PHY2/hw_07_preamble_access_code/run_test.py"),
    ("Stage 08: Hardware Packet Engine & CRC32 Verification", "PHY2/hw_08_packet_crc32/run_test.py"),
    ("Stage 09: Hardware CDP Transceiver Architecture", "PHY2/hw_09_cdp_transceiver/run_test.py"),
    ("Stage 10: Hardware Multi-Packet High-Volume Stress Test", "PHY2/hw_10_end_to_end_stress/run_test.py"),
    ("Adapted Original Transceiver (y·y' TED)", "PHY2/adapted_original/run_original_test.py"),
]

def run_all(mod_type='ALL'):
    print("================================================================================")
    print(f"      PHY2 MASTER HARDWARE SUITE VALIDATION (Modulation: {mod_type.upper()})    ")
    print("================================================================================")
    
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    results = []
    overall_start = time.time()
    
    for idx, (title, script_path) in enumerate(HW_STAGES, 1):
        full_path = os.path.join(workspace_dir, script_path)
        print(f"\n[{idx:02d}/{len(HW_STAGES):02d}] Executing {title}...")
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
    print("                           HARDWARE TEST SUMMARY MATRIX                         ")
    print("================================================================================")
    for idx, (title, passed, elapsed, _) in enumerate(results, 1):
        status = "PASS" if passed else "FAIL"
        print(f" {idx:02d}. {title:60s} | {status:4s} | {elapsed:5.2f}s")
    print("--------------------------------------------------------------------------------")
    pass_count = sum(1 for r in results if r[1])
    print(f" Total Passed: {pass_count}/{len(results)} stages | Total Time: {total_time:.2f}s")
    
    if all_passed:
        print("\033[92m >>> ALL HARDWARE STAGES & ADAPTED TRANSCEIVERS PASSED WITH 0 REGRESSIONS! <<<\033[0m")
    else:
        print("\033[91m >>> SOME TESTS FAILED. PLEASE REVIEW LOGS ABOVE. <<<\033[0m")
    print("================================================================================")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PHY2 Master Hardware Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_all(args.mod))
