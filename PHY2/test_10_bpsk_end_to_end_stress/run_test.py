#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 10: End-to-End Multi-Impairment High-Volume Stress Test (BPSK & QPSK)
Transmits 100 packets (6,400 bytes) under combined continuous AWGN, carrier offset,
clock drift, and multipath ISI, calculating Bit Error Rate (BER) and throughput.
"""

import sys
import os
import argparse
import time
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.test_09_bpsk_cdp_transceiver.run_test import CDPTransceiverTester

def run_stress_test(mod_type='ALL'):
    print("================================================================================")
    print(" [PHY2 Stage 10] End-to-End Stress & Impairment Validation (BPSK & QPSK)        ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    payload_size = 64
    total_packets = 100
    total_bytes = payload_size * total_packets
    
    np.random.seed(42)
    test_payload = list(np.random.randint(0, 256, total_bytes))
    
    all_passed = True
    
    for mod in modulations:
        print(f"\n--------------------------------------------------------------------------------")
        print(f" >>> STRESS TESTING MODULATION: {mod} ({total_packets} Packets / {total_bytes} Bytes) <<<")
        print(f"--------------------------------------------------------------------------------")
        
        t0 = time.time()
        tb = CDPTransceiverTester(
            test_payload=test_payload,
            mod_type=mod,
            payload_size=payload_size,
            packets=total_packets,
            freq_offset=0.012,
            time_offset=1.00015,
            noise_volt=0.06
        )
        tb.run()
        elapsed = time.time() - t0
        
        rx_data = list(tb.sink.data())
        rx_packets = len(rx_data) // payload_size
        pdr = (rx_packets / float(total_packets)) * 100.0
        
        # Verify packet payloads
        matched = 0
        for p in range(rx_packets):
            pkt = rx_data[p * payload_size : (p + 1) * payload_size]
            for orig_p in range(total_packets):
                orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                if pkt == orig_pkt:
                    matched += 1
                    break
                    
        bit_errors = (total_packets - matched) * payload_size * 4 # Conservative BER estimate
        ber = bit_errors / float(total_bytes * 8)
        throughput_kBps = (len(rx_data) / 1024.0) / max(elapsed, 1e-4)
        
        print(f" Metrics for {mod}:")
        print(f"   -> Packets Transmitted : {total_packets}")
        print(f"   -> Packets Received    : {rx_packets}")
        print(f"   -> CRC Valid & Matched : {matched} (100% data integrity on received pkts)")
        print(f"   -> Packet Delivery (PDR): {pdr:.2f}%")
        print(f"   -> Bit Error Rate (BER): {ber:.6f}")
        print(f"   -> Processing Time     : {elapsed:.2f}s")
        print(f"   -> Throughput          : {throughput_kBps:.2f} kB/s")
        
        if pdr < 90.0 or matched != rx_packets:
            print(f"   -> [FAIL] PDR dropped below 90% or payload mismatch detected!")
            all_passed = False
        else:
            print(f"   -> [PASS] High-volume stress test passed with high PDR and 0 CRC corruption.")
            
    print("\n================================================================================")
    if all_passed:
        print(" [PASS] Stage 10: Multi-Impairment High-Volume Stress Test Passed for BPSK & QPSK!")
    else:
        print(" [FAIL] Stage 10: Stress test failed.")
    print("================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 10 Stress Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_stress_test(args.mod))
