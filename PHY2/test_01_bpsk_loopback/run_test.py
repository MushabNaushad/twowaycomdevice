#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 01: Pure Baseband BPSK Loopback Test Runner
Verifies 100% bit-exact transmission and reception across pure BPSK constellation mapping.
"""

import sys
import numpy as np
from gnuradio import gr, digital, blocks

class BPSKLoopbackTester(gr.top_block):
    def __init__(self, test_bytes):
        super().__init__("BPSK_Loopback_Tester", catch_exceptions=True)
        
        self.BPSK_CONST = digital.constellation_bpsk().base()
        
        # Source & Bit Slicing
        self.src = blocks.vector_source_b(list(test_bytes), False, 1, [])
        self.unpack = blocks.unpack_k_bits_bb(8)
        
        # Modulator: Map bit 0 -> -1, bit 1 -> +1
        self.chunks_to_syms = digital.chunks_to_symbols_bc(self.BPSK_CONST.points(), 1)
        
        # Demodulator: Slicer / Constellation Decoder
        self.decoder = digital.constellation_decoder_cb(self.BPSK_CONST)
        self.pack = blocks.pack_k_bits_bb(8)
        
        # Sink
        self.sink = blocks.vector_sink_b(1)
        
        # Connections
        self.connect(self.src, self.unpack, self.chunks_to_syms, self.decoder, self.pack, self.sink)

def run_test():
    print("==================================================")
    print(" [PHY2 Stage 01] Running Pure BPSK Loopback Test")
    print("==================================================")
    
    # Test vector: Diverse pattern including all byte values 0x00 - 0xFF
    test_data = bytes([i % 256 for i in range(512)])
    tb = BPSKLoopbackTester(test_data)
    tb.run()
    
    rx_data = bytes(tb.sink.data())
    
    print(f"Transmitted Bytes : {len(test_data)}")
    print(f"Received Bytes    : {len(rx_data)}")
    
    if test_data == rx_data:
        print("[PASS] 100% Bit-Exact Match! Pure BPSK baseband loopback verified.")
        return 0
    else:
        diff_count = sum(1 for a, b in zip(test_data, rx_data) if a != b)
        print(f"[FAIL] Data mismatch! {diff_count} differing bytes.")
        return 1

if __name__ == "__main__":
    sys.exit(run_test())
