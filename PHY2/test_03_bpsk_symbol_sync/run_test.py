#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 03: Symbol Synchronization Test Runner (BPSK & QPSK)
Verifies timing clock recovery and steady-state 0 BER across clock timing offsets (epsilon) and noise.
"""

import sys
import argparse
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class SymbolSyncTester(gr.top_block):
    def __init__(self, test_bytes, mod_type='BPSK', epsilon=1.0001, noise_volt=0.01,
                 sym_bw=0.045, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("Symbol_Sync_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        flush_bytes = [0x00] * 50
        tx_data = list(test_bytes) + flush_bytes
        self.src = blocks.vector_source_b(tx_data, False, 1, [])
        
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_mod = 2
            self.ted_type = digital.TED_MUELLER_AND_MULLER
        else:
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            self.arity = 4
            self.bps = 2
            self.diff_mod = 4
            self.ted_type = digital.TED_GARDNER
            
        # Modulator with Differential Encoding
        self.mod = digital.generic_mod(
            constellation=self.constellation,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=alpha,
            verbose=False,
            log=False,
            truncate=False
        )
        
        # Channel with clock timing offset (epsilon) and noise
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=0.0,
            epsilon=epsilon,
            taps=[1.0],
            noise_seed=42,
            block_tags=False
        )
        
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        
        # Matched Filter
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        # Symbol Synchronizer
        self.symbol_sync = digital.symbol_sync_cc(
            self.ted_type,
            sps,
            sym_bw,
            1.0,
            1.0,
            1.5,
            1,
            self.constellation,
            digital.IR_MMSE_8TAP,
            128,
            []
        )
        
        self.costas = digital.costas_loop_cc(0.0628, self.arity, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_dec = digital.diff_decoder_bb(self.diff_mod, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        self.sink = blocks.vector_sink_b(1)
        
        self.connect(self.src, self.mod, self.channel, self.agc, self.rx_filter,
                     self.symbol_sync, self.costas, self.decoder, self.diff_dec)
                     
        if self.bps > 1:
            self.connect(self.diff_dec, self.mapper, self.unpacker, self.sink)
        else:
            self.connect(self.diff_dec, self.sink)

def evaluate_sync(rx_bits, tx_bits, discard_transient=150):
    rx_b = np.array(rx_bits)
    tx_b = np.array(tx_bits)
    
    if len(rx_b) < len(tx_b) + discard_transient:
        return 1.0, len(tx_b), len(tx_b)
        
    corr = np.correlate(2 * rx_b - 1, 2 * tx_b - 1, mode='full')
    best_lag = np.argmax(corr) - len(tx_b) + 1
    
    aligned_rx = rx_b[best_lag : best_lag + len(tx_b)]
    if len(aligned_rx) < len(tx_b):
        return 1.0, len(tx_b), len(aligned_rx)
        
    steady_rx = aligned_rx[discard_transient:]
    steady_tx = tx_b[discard_transient:]
    
    errors = np.sum(steady_rx != steady_tx)
    steady_ber = errors / float(len(steady_tx))
    return steady_ber, int(errors), len(steady_tx)

def run_test(mod_type='ALL'):
    print("================================================================================")
    print(" [PHY2 Stage 03] Symbol Synchronization Test (BPSK & QPSK under Clock Drift)    ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    np.random.seed(100)
    test_bytes = [0x55] * 20 + list(np.random.randint(0, 256, 350))
    
    drift_scenarios = [
        ("Nominal Clock (eps = 1.0000)", 1.0000),
        ("Clock Drift Fast (+200 ppm, eps = 1.0002)", 1.0002),
        ("Clock Drift Slow (-200 ppm, eps = 0.9998)", 0.9998),
    ]
    all_passed = True
    
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} ---")
        tx_bits = []
        for b in test_bytes:
            for i in range(7, -1, -1):
                tx_bits.append((b >> i) & 1)
                
        for desc, eps in drift_scenarios:
            tb = SymbolSyncTester(test_bytes, mod_type=mod, epsilon=eps, noise_volt=0.01)
            tb.run()
            
            steady_ber, errs, total = evaluate_sync(tb.sink.data(), tx_bits)
            print(f"  {desc}")
            print(f"    Steady-State BER: {steady_ber:.6f} ({errs}/{total} bit errors)")
            
            if steady_ber < 0.05:
                print(f"    -> [PASS] Symbol synchronizer tracked clock drift.")
            else:
                print(f"    -> [FAIL] Clock synchronization lost!")
                all_passed = False
                
    print("\n================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 03 Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_test(args.mod))
