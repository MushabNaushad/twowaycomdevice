#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 04: BPSK with Costas Loop Carrier Phase Recovery Test Runner
Verifies carrier frequency/phase acquisition and 180-degree phase ambiguity resolution.
"""

import sys
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class BPSKCostasTester(gr.top_block):
    def __init__(self, test_bytes, freq_offset=0.0, costas_bw=0.0628, sym_bw=0.045, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("BPSK_Costas_Tester", catch_exceptions=True)
        
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
        
        # Channel with carrier frequency offset
        self.channel = channels.channel_model(
            noise_voltage=0.0,
            frequency_offset=freq_offset,
            epsilon=1.0,
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
            digital.TED_MUELLER_AND_MULLER,
            sps,
            sym_bw,
            1.0,
            1.0,
            1.5,
            1,
            self.BPSK_CONST,
            digital.IR_MMSE_8TAP,
            128,
            []
        )
        
        # Costas Loop (Order 2 for BPSK)
        self.costas = digital.costas_loop_cc(costas_bw, 2, False)
        
        self.decoder = digital.constellation_decoder_cb(self.BPSK_CONST)
        self.sink = blocks.vector_sink_b(1)
        
        self.connect(self.src, self.mod, self.channel, self.agc, self.rx_filter, self.symbol_sync, self.costas, self.decoder, self.sink)

def evaluate_costas(rx_bits, tx_bits, discard_transient=120):
    rx_b = np.array(rx_bits)
    tx_b = np.array(tx_bits)
    
    best_err = len(tx_b)
    best_pol = 1
    best_steady_ber = 1.0
    
    # Test both polarities due to BPSK 180-deg phase ambiguity
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
    print(" [PHY2 Stage 04] Running BPSK Costas Loop Test")
    print("==================================================")
    
    np.random.seed(100)
    test_bytes = [int(x) for x in np.random.randint(0, 256, 400)]
    tx_bits = []
    for b in test_bytes:
        for i in range(7, -1, -1):
            tx_bits.append((b >> i) & 1)
            
    freq_offsets = [0.0, 0.002, -0.003, 0.005]
    all_passed = True
    
    for fo in freq_offsets:
        tb = BPSKCostasTester(test_bytes, freq_offset=fo, costas_bw=0.0628)
        tb.run()
        rx_bits = list(tb.sink.data())
        
        ber, errs, count, pol = evaluate_costas(rx_bits, tx_bits, discard_transient=120)
        print(f"Carrier Frequency Offset: {fo:+7.4f} | Steady-State BER: {ber:7.5f} ({errs}/{count} errors, Ambiguity Polarity: {pol:+d})")
        
        if ber > 0.0001:
            all_passed = False
            print(f"[FAIL] Costas loop failed to acquire/lock carrier for freq_offset={fo}")
            
    if all_passed:
        print("[PASS] Costas Loop successfully acquired and corrected carrier frequency and phase offsets with 0 steady-state error!")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(run_test())
