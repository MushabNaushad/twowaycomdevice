#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 01: Baseband Constellation Loopback Test Runner (BPSK & QPSK)
Verifies 100% bit-exact transmission and reception across baseband constellation mapping for BPSK and QPSK.
"""

import sys
import argparse
import numpy as np
from gnuradio import gr, digital, blocks

class BasebandLoopbackTester(gr.top_block):
    def __init__(self, test_bytes, mod_type='BPSK'):
        super().__init__("Baseband_Loopback_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.bps = 1
        else:
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            self.bps = 2
            
        self.src = blocks.vector_source_b(list(test_bytes), False, 1, [])
        self.unpack = blocks.unpack_k_bits_bb(8)
        self.pack_chunks = blocks.pack_k_bits_bb(self.bps)
        
        # Modulator
        self.chunks_to_syms = digital.chunks_to_symbols_bc(self.constellation.points(), 1)
        
        # Demodulator / Slicer
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.unpack_syms = blocks.unpack_k_bits_bb(self.bps)
        self.pack = blocks.pack_k_bits_bb(8)
        
        self.sink = blocks.vector_sink_b(1)
        
        self.connect(self.src, self.unpack, self.pack_chunks, self.chunks_to_syms,
                     self.decoder, self.unpack_syms, self.pack, self.sink)

def run_test(mod_type='ALL'):
    print("================================================================================")
    print(" [PHY2 Stage 01] Baseband Modulation Loopback Test (BPSK & QPSK)                ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    test_data = bytes([i % 256 for i in range(512)])
    all_passed = True
    
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} ---")
        tb = BasebandLoopbackTester(test_data, mod_type=mod)
        tb.run()
        
        rx_data = bytes(tb.sink.data())
        print(f" Transmitted Bytes : {len(test_data)}")
        print(f" Received Bytes    : {len(rx_data)}")
        
        if test_data == rx_data:
            print(f" -> [PASS] 100% Bit-Exact Match! Baseband {mod} loopback verified.")
        else:
            diff_count = sum(1 for a, b in zip(test_data, rx_data) if a != b)
            print(f" -> [FAIL] Data mismatch for {mod}! {diff_count} differing bytes.")
            all_passed = False
            
    print("\n================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 01 Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_test(args.mod))
