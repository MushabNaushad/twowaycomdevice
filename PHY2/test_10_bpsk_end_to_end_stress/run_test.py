#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 10: End-to-End Stress & Multi-Impairment Validation Test Runner
Evaluates sustained transmission resilience across 100 packets under severe multi-impairment stress.
"""

import sys
import os
import time
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.test_09_bpsk_cdp_transceiver.run_test import CDPTransceiverTester

def run_test():
    print("==================================================")
    print(" [PHY2 Stage 10] Running End-to-End Stress Test")
    print("==================================================")
    
    payload_size = 64
    packets = 100 # 6,400 payload bytes across 100 frames
    np.random.seed(4242)
    
    test_payload = [int((p * 19 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    stress_profiles = [
        ("Moderate Noise (Vn=0.15)", 0.0, 1.0, 0.15),
        ("Combined Clock & Freq Drift", 0.015, 1.0003, 0.05),
        ("Full Multi-Impairment Stress", -0.018, 0.9997, 0.12),
    ]
    all_passed = True
    
    for name, fo, to, nv in stress_profiles:
        start_time = time.time()
        tb = CDPTransceiverTester(test_payload, payload_size=payload_size, packets=packets,
                                  freq_offset=fo, time_offset=to, noise_volt=nv)
        tb.run()
        elapsed = time.time() - start_time
        
        rx_bytes = list(tb.sink.data())
        received_packets = len(rx_bytes) // payload_size
        pdr = (received_packets / float(packets)) * 100.0
        
        # Verify packet payloads
        matched_count = 0
        for p in range(received_packets):
            pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
            for orig_p in range(packets):
                orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                if pkt == orig_pkt:
                    matched_count += 1
                    break
                    
        delivered_bytes = received_packets * payload_size
        throughput = delivered_bytes / max(elapsed, 1e-4)
        
        print(f"Profile: {name:30s}")
        print(f"  -> Packets Delivered: {received_packets}/{packets} ({pdr:5.1f}%) | Time: {elapsed:.2f}s | Throughput: {throughput:6.0f} B/s")
        print(f"  -> CRC-Valid & Matched: {matched_count}/{received_packets} packets")
        
        if pdr < 90.0 or matched_count != received_packets:
            all_passed = False
            print(f"  -> [FAIL] PDR dropped below 90% threshold or payload corruption detected!")
        else:
            print(f"  -> [OK] Stress criteria passed.")
            
    if all_passed:
        print("[PASS] Full End-to-End Stress Test successfully validated across all multi-impairment profiles!")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(run_test())
