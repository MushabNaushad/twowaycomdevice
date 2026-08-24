#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 06: BPSK with Adaptive Linear Equalizer Test Runner
Verifies ISI cancellation and constellation recovery under multipath distortion.
"""

import sys
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class BPSKEqualizerTester(gr.top_block):
    def __init__(self, test_bytes, multipath_taps=[1.0, 0.25, 0.1], step_size=0.001, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("BPSK_Equalizer_Tester", catch_exceptions=True)
        
        self.BPSK_CONST = digital.constellation_bpsk().base()
        flush_bytes = [0x00] * 60
        tx_data = list(test_bytes) + flush_bytes
        self.src = blocks.vector_source_b(tx_data, False, 1, [])
        
        # Modulator
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
        
        # Multipath Channel (creates ISI)
        self.channel = channels.channel_model(
            noise_voltage=0.0,
            frequency_offset=0.0,
            epsilon=1.0,
            taps=multipath_taps,
            noise_seed=42,
            block_tags=False
        )
        
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, 2 * np.pi * 0.005)
        
        # Matched Filter
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        # Symbol Sync (osps=1)
        self.symbol_sync = digital.symbol_sync_cc(
            digital.TED_MUELLER_AND_MULLER,
            sps,
            0.045,
            1.0,
            1.0,
            1.5,
            1,
            self.BPSK_CONST,
            digital.IR_MMSE_8TAP,
            128,
            []
        )
        
        # Adaptive Linear Equalizer (CMA Algorithm)
        self.adpt_alg = digital.adaptive_algorithm_cma(self.BPSK_CONST, step_size, 1).base()
        self.equalizer = digital.linear_equalizer(11, 1, self.adpt_alg, True, [], 'corr_est')
        
        # Costas Loop
        self.costas = digital.costas_loop_cc(0.0628, 2, False)
        
        self.decoder = digital.constellation_decoder_cb(self.BPSK_CONST)
        self.sink = blocks.vector_sink_b(1)
        
        self.connect(self.src, self.mod, self.channel, self.agc, self.fll, self.rx_filter, self.symbol_sync, self.equalizer, self.costas, self.decoder, self.sink)

def evaluate_eq(rx_bits, tx_bits, discard_transient=250):
    rx_b = np.array(rx_bits)
    tx_b = np.array(tx_bits)
    
    best_err = len(tx_b)
    best_pol = 1
    best_steady_ber = 1.0
    
    for pol in [1, -1]:
        test_rx = rx_b if pol == 1 else (1 - rx_b)
        corr = np.correlate(2 * test_rx - 1, 2 * tx_b - 1, mode='full')
        lag = np.argmax(corr) - len(tx_b) + 1
        aligned = test_rx[lag : lag + len(tx_b)]
        
        if len(aligned) == len(tx_b):
            steady_rx = aligned[discard_transient:]
            steady_tx = tx_b[discard_transient:]
            errs = np.sum(steady_rx != steady_tx)
            ber = errs / float(len(steady_tx))
            if errs < best_err:
                best_err = errs
                best_pol = pol
                best_steady_ber = ber
                
    return best_steady_ber, best_err, len(tx_b) - discard_transient, best_pol

def run_test():
    print("==================================================")
    print(" [PHY2 Stage 06] Running Adaptive Equalizer Test")
    print("==================================================")
    
    np.random.seed(100)
    test_bytes = [int(x) for x in np.random.randint(0, 256, 800)] # 6400 bits
    tx_bits = []
    for b in test_bytes:
        for i in range(7, -1, -1):
            tx_bits.append((b >> i) & 1)
            
    channel_profiles = [
        ("Clean Single-Path", [1.0]),
        ("Mild Multipath", [1.0, 0.2]),
        ("Moderate Multipath", [1.0, 0.25, 0.1]),
    ]
    all_passed = True
    
    for name, taps in channel_profiles:
        tb = BPSKEqualizerTester(test_bytes, multipath_taps=taps, step_size=0.001)
        tb.run()
        rx_bits = list(tb.sink.data())
        
        ber, errs, count, pol = evaluate_eq(rx_bits, tx_bits, discard_transient=250)
        print(f"Profile: {name:20s} | Steady-State BER: {ber:7.5f} ({errs}/{count} errors, Pol: {pol:+d})")
        
        if ber > 0.0001:
            all_passed = False
            print(f"[FAIL] Adaptive equalizer failed to converge on profile '{name}'")
            
    if all_passed:
        print("[PASS] Adaptive Linear Equalizer converged and mitigated all multipath ISI with 0 steady-state error!")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(run_test())
