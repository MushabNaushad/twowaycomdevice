#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Adapted Original Transceiver Test Runner
Evaluates the user's adapted original transceiver across both BPSK and QPSK modulation schemes
under active channel impairments (noise, frequency offset, clock drift).
"""

import sys
import os
import argparse
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.adapted_original.adapted_transceiver import AdaptedOriginalTransceiver

def run_test(mod_type='ALL'):
    print("================================================================================")
    print("               PHY2 ADAPTED ORIGINAL TRANSCEIVER VALIDATION                     ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    payload_size = 64
    packets = 20
    test_payload = [int((p * 29 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    test_scenarios = [
        ("Light Channel Impairments", 0.02, 0.005, 1.0001),
        ("Moderate Carrier Offset",   0.03, 0.015, 1.0002),
        ("Clock Drift & Noise",       0.08, -0.010, 0.9998),
    ]
    all_passed = True
    
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} ---")
        for sc_name, nv, fo, to in test_scenarios:
            tb = AdaptedOriginalTransceiver(
                test_payload=test_payload,
                mod_type=mod,
                payload_size=payload_size,
                packets=packets,
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
                        
            print(f"  Scenario: {sc_name:28s} | Transmitted: {packets:2d} | Received: {received_packets:2d} | Verified: {matched_count:2d} | PDR: {pdr:5.1f}%")
            
            if pdr < 85.0 or matched_count != received_packets:
                all_passed = False
                print(f"    -> [FAIL] PDR dropped below threshold or payload mismatch detected!")
            else:
                print(f"    -> [OK] 100% CRC integrity verified.")
                
    if all_passed:
        print("\n================================================================================")
        print(" [PASS] Adapted Original Transceiver verified for BPSK and QPSK under impairments!")
        print("================================================================================")
        return 0
    else:
        print("\n================================================================================")
        print(" [FAIL] Some test scenarios failed.")
        print("================================================================================")
        return 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Test Adapted Original Transceiver")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'], help="Modulation scheme")
    args = parser.parse_args()
    sys.exit(run_test(args.mod))
