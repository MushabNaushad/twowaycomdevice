#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 10: Hardware Multi-Packet High-Volume Stress Test Runner (BPSK & QPSK)
Transmits high-volume multi-packet bursts across SDR Hardware (Pluto / BladeRF / RTL-SDR / Channel).
"""

import sys
import os
import time
import argparse
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.hw_09_cdp_transceiver.run_test import CDPTransceiverTester

def run_stress_test(mod_type='ALL', hw_type='sim', uri='ip:192.168.2.1'):
    print("================================================================================")
    print(f" [PHY2 Stage 10] Hardware High-Volume Stress Test (HW: {hw_type.upper()})        ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    payload_size = 64
    packets = 100
    test_payload = [int((p * 37 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    all_passed = True
    for mod in modulations:
        print(f"\n>>> Stress Testing Modulation: {mod} on Hardware Target: {hw_type} <<<")
        t0 = time.time()
        
        tb = CDPTransceiverTester(
            test_payload=test_payload,
            mod_type=mod,
            payload_size=payload_size,
            packets=packets,
            freq_offset=0.005,
            time_offset=1.0001,
            noise_volt=0.04,
            hw_type=hw_type,
            uri=uri
        )
        tb.run()
        elapsed = time.time() - t0
        
        rx_data = list(tb.sink.data())
        rx_packets = len(rx_data) // payload_size
        pdr = (rx_packets / float(packets)) * 100.0
        
        matched_packets = 0
        for p in range(rx_packets):
            pkt = rx_data[p * payload_size : (p + 1) * payload_size]
            for orig_p in range(packets):
                orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                if pkt == orig_pkt:
                    matched_packets += 1
                    break
                    
        throughput_bps = (len(rx_data) * 8.0) / max(elapsed, 1e-4)
        print(f"  Execution Time        : {elapsed:.3f} s")
        print(f"  Transmitted Packets   : {packets} ({packets * payload_size} bytes)")
        print(f"  Received Valid Packets: {rx_packets} ({len(rx_data)} bytes)")
        print(f"  CRC Matched Packets   : {matched_packets} / {rx_packets}")
        print(f"  Packet Delivery Ratio : {pdr:.1f}%")
        print(f"  Payload Throughput    : {throughput_bps / 1000.0:.2f} kbps")
        
        if pdr >= 85.0 and matched_packets == rx_packets:
            print(f"  -> [PASS] Hardware High-Volume Stress Test Verified for {mod}!")
        else:
            print(f"  -> [FAIL] Packet delivery ratio or CRC integrity failed under stress.")
            all_passed = False
            
    print("================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 10 Hardware Stress Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    parser.add_argument('--hw', type=str, default='sim', choices=['sim', 'pluto', 'bladerf', 'rtlsdr'])
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1')
    args = parser.parse_args()
    sys.exit(run_stress_test(args.mod, args.hw, args.uri))
