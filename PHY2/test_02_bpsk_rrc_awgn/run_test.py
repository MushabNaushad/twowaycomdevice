#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 02: BPSK with RRC Pulse Shaping & AWGN Channel Test Runner
Verifies pulse shaping, matched filtering, optimal sampling phase alignment, and BER performance under AWGN.
"""

import sys
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class BPSKRRCChannelTester(gr.top_block):
    def __init__(self, test_bytes, noise_volt=0.0, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("BPSK_RRC_Channel_Tester", catch_exceptions=True)
        
        self.sps = sps
        self.BPSK_CONST = digital.constellation_bpsk().base()
        
        # Source with trailing flush bytes to ensure all payload symbols exit filter pipeline
        flush_bytes = [0x00] * 30
        tx_data = list(test_bytes) + flush_bytes
        self.src = blocks.vector_source_b(tx_data, False, 1, [])
        
        # Modulator (RRC Pulse Shaped)
        self.mod = digital.generic_mod(
            constellation=self.BPSK_CONST,
            differential=False,
            samples_per_symbol=sps,
            pre_diff_code=False,
            excess_bw=alpha,
            verbose=False,
            log=False,
            truncate=False
        )
        
        # AWGN Channel
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=0.0,
            epsilon=1.0,
            taps=[1.0],
            noise_seed=42,
            block_tags=False
        )
        
        # AGC for amplitude normalization
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        
        # Matched Filter (RRC Filter)
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        # Complex output sink for sample analysis
        self.sink = blocks.vector_sink_c(1)
        
        # Connections
        self.connect(self.src, self.mod, self.channel, self.agc, self.rx_filter, self.sink)

def align_and_demod(rx_samples, tx_bits, sps=4):
    """
    Finds optimal sampling phase and filter delay using minimum BER search.
    """
    rx_real = np.real(np.array(rx_samples))
    best_ber = 1.0
    best_offset = 0
    
    # Search delay window around combined filter delay (ntaps ~ 150)
    for offset in range(50, 350):
        sampled = rx_real[offset::sps][:len(tx_bits)]
        if len(sampled) == len(tx_bits):
            for pol in [1, -1]:
                dec = (pol * sampled > 0).astype(int)
                errors = np.sum(dec != tx_bits)
                ber = errors / float(len(tx_bits))
                if ber < best_ber:
                    best_ber = ber
                    best_offset = offset
                    
    return best_ber, best_offset

def run_test():
    print("==================================================")
    print(" [PHY2 Stage 02] Running BPSK RRC & AWGN Test")
    print("==================================================")
    
    np.random.seed(42)
    # Generate 150 bytes = 1200 bits
    test_bytes = [int(x) for x in np.random.randint(0, 256, 150)]
    
    # Extract ground truth bits
    tx_bits = []
    for b in test_bytes:
        for i in range(7, -1, -1):
            tx_bits.append((b >> i) & 1)
            
    noise_levels = [0.0, 0.2, 0.5, 0.8]
    results = {}
    
    for nv in noise_levels:
        tb = BPSKRRCChannelTester(test_bytes, noise_volt=nv)
        tb.run()
        rx_samples = tb.sink.data()
        ber, offset = align_and_demod(rx_samples, tx_bits, sps=4)
        results[nv] = ber
        print(f"Noise Voltage: {nv:4.2f} | Measured BER: {ber:7.5f} | Optimal Sample Offset: {offset}")
    
    # Assertions
    if results[0.0] == 0.0:
        print("[PASS] Clean channel achieved 0.0 BER with RRC matched filtering!")
    else:
        print(f"[FAIL] Clean channel had non-zero BER: {results[0.0]}")
        return 1
        
    if results[0.2] <= results[0.5] <= results[0.8] or results[0.2] < 0.05:
        print("[PASS] AWGN noise curve verified successfully!")
        return 0
    else:
        print("[FAIL] Unexpected BER behavior under AWGN.")
        return 1

if __name__ == "__main__":
    sys.exit(run_test())
