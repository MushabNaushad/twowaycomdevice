#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 03: BPSK with Symbol Synchronization Test Runner
Verifies timing clock recovery and steady-state 0 BER across clock timing offsets.
"""

import sys
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class BPSKSymbolSyncTester(gr.top_block):
    def __init__(self, test_bytes, epsilon=1.0, sym_bw=0.045, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("BPSK_Symbol_Sync_Tester", catch_exceptions=True)
        
        self.BPSK_CONST = digital.constellation_bpsk().base()
        flush_bytes = [0x00] * 50
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
        
        # Channel with clock timing offset (epsilon)
        self.channel = channels.channel_model(
            noise_voltage=0.0,
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
        
        # Symbol Synchronizer (Mueller and Müller / Gardner)
        self.symbol_sync = digital.symbol_sync_cc(
            digital.TED_MUELLER_AND_MULLER,
            sps,
            sym_bw,
            1.0,   # damping
            1.0,   # ted_gain
            1.5,   # max_deviation
            1,     # osps (1 sample per symbol output)
            self.BPSK_CONST,
            digital.IR_MMSE_8TAP,
            128,
            []
        )
        
        self.decoder = digital.constellation_decoder_cb(self.BPSK_CONST)
        self.sink = blocks.vector_sink_b(1)
        
        self.connect(self.src, self.mod, self.channel, self.agc, self.rx_filter, self.symbol_sync, self.decoder, self.sink)

def evaluate_sync(rx_bits, tx_bits, discard_transient=100):
    """
    Evaluates timing lock and steady-state BER after discarding initial PLL acquisition transient.
    """
    rx_b = np.array(rx_bits)
    tx_b = np.array(tx_bits)
    
    corr = np.correlate(2 * rx_b - 1, 2 * tx_b - 1, mode='full')
    best_lag = np.argmax(corr) - len(tx_b) + 1
    
    # Align
    aligned_rx = rx_b[best_lag : best_lag + len(tx_b)]
    if len(aligned_rx) < len(tx_b):
        return 1.0, 0, len(aligned_rx)
        
    # Evaluate steady state (post-transient)
    steady_rx = aligned_rx[discard_transient:]
    steady_tx = tx_b[discard_transient:]
    
    errors = np.sum(steady_rx != steady_tx)
    steady_ber = errors / float(len(steady_tx))
    return steady_ber, errors, len(steady_tx)

def run_test():
    print("==================================================")
    print(" [PHY2 Stage 03] Running BPSK Symbol Sync Test")
    print("==================================================")
    
    np.random.seed(100)
    test_bytes = [int(x) for x in np.random.randint(0, 256, 400)] # 3200 bits
    tx_bits = []
    for b in test_bytes:
        for i in range(7, -1, -1):
            tx_bits.append((b >> i) & 1)
            
    epsilons = [1.0, 1.0005, 0.9995]
    all_passed = True
    
    for eps in epsilons:
        tb = BPSKSymbolSyncTester(test_bytes, epsilon=eps, sym_bw=0.045)
        tb.run()
        rx_bits = list(tb.sink.data())
        
        ber, errs, count = evaluate_sync(rx_bits, tx_bits, discard_transient=100)
        print(f"Timing Offset (epsilon): {eps:7.4f} | Steady-State BER: {ber:7.5f} ({errs}/{count} errors)")
        
        if ber > 0.0001:
            all_passed = False
            print(f"[FAIL] Symbol sync failed to maintain steady-state lock for epsilon={eps}")
            
    if all_passed:
        print("[PASS] Symbol Synchronizer successfully tracked and locked all timing offsets with 0 steady-state error!")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(run_test())
