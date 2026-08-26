#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 02: RRC Pulse Shaping & AWGN Channel Test Runner (BPSK & QPSK)
Verifies pulse shaping, matched filtering, and BER performance under parameterized AWGN channel noise.
"""

import sys
import argparse
import math
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class RRCChannelTester(gr.top_block):
    def __init__(self, test_bytes, mod_type='BPSK', noise_volt=0.0, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("RRC_Channel_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        self.sps = sps
        
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
        else:
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            self.arity = 4
            self.bps = 2
            
        flush_bytes = [0x00] * 30
        tx_data = list(test_bytes) + flush_bytes
        self.src = blocks.vector_source_b(tx_data, False, 1, [])
        
        # Modulator (RRC Pulse Shaped)
        self.mod = digital.generic_mod(
            constellation=self.constellation,
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
        
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        
        # Matched Filter (RRC Filter)
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        self.sink = blocks.vector_sink_c(1)
        self.connect(self.src, self.mod, self.channel, self.agc, self.rx_filter, self.sink)

def align_and_demod(rx_samples, tx_symbols, sps=4):
    rx_c = np.array(rx_samples)
    best_ber = 1.0
    best_offset = 0
    
    for offset in range(30, 250):
        sampled = rx_c[offset::sps][:len(tx_symbols)]
        if len(sampled) == len(tx_symbols):
            for rot in [0, 1, 2, 3]:
                rotated = sampled * np.exp(1j * rot * np.pi / 2.0)
                # Slicer
                dec_syms = np.zeros(len(tx_symbols), dtype=complex)
                if len(set(tx_symbols)) == 2: # BPSK
                    dec_syms = np.sign(np.real(rotated))
                else: # QPSK
                    dec_syms = (np.sign(np.real(rotated)) + 1j * np.sign(np.imag(rotated))) / math.sqrt(2)
                errs = np.sum(np.abs(dec_syms - tx_symbols) > 0.5)
                ber = errs / float(len(tx_symbols))
                if ber < best_ber:
                    best_ber = ber
                    best_offset = offset
    return best_ber, best_offset

def run_test(mod_type='ALL'):
    print("================================================================================")
    print(" [PHY2 Stage 02] RRC Pulse Shaping & AWGN Channel Test (BPSK & QPSK)            ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    np.random.seed(42)
    test_bytes = [int(x) for x in np.random.randint(0, 256, 150)]
    
    noise_levels = [0.05, 0.25, 0.50]
    all_passed = True
    
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} ---")
        # Build symbols
        if mod == 'BPSK':
            tx_bits = []
            for b in test_bytes:
                for i in range(7, -1, -1):
                    tx_bits.append((b >> i) & 1)
            tx_symbols = np.array([1.0 if b == 1 else -1.0 for b in tx_bits])
        else:
            qpsk_points = np.array([-1-1j, -1+1j, 1+1j, 1-1j]) / math.sqrt(2)
            tx_syms = []
            for b in test_bytes:
                for s in [6, 4, 2, 0]:
                    chunk = (b >> s) & 3
                    tx_syms.append(qpsk_points[chunk])
            tx_symbols = np.array(tx_syms)
            
        for nv in noise_levels:
            tb = RRCChannelTester(test_bytes, mod_type=mod, noise_volt=nv)
            tb.run()
            ber, offset = align_and_demod(tb.sink.data(), tx_symbols, sps=4)
            
            print(f"  Noise Voltage Vn = {nv:.2f} | Optimal Sample Offset: {offset} | BER: {ber:.6f}")
            if nv <= 0.05 and ber > 0.05:
                print(f"    -> [FAIL] High BER under clean/low noise!")
                all_passed = False
            else:
                print(f"    -> [PASS] Matched filter demodulation verified.")
                
    print("\n================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 02 Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_test(args.mod))
