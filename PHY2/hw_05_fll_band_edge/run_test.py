#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 05: FLL Band-Edge Frequency Recovery Test Runner (BPSK & QPSK)
Verifies wide-range coarse carrier frequency acquisition across large frequency offsets and noise.
"""

import sys
import argparse
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class FLLTester(gr.top_block):
    def __init__(self, test_bytes, mod_type='BPSK', freq_offset=0.015, noise_volt=0.01,
                 fll_bw=0.0314, costas_bw=0.0628, sym_bw=0.045, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("FLL_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        flush_bytes = [0x00] * 60
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
            
        # Modulator
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
        
        # Channel with large carrier offset and noise
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=freq_offset,
            epsilon=1.0,
            taps=[1.0],
            noise_seed=42,
            block_tags=False
        )
        
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, fll_bw)
        
        # Matched Filter
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        # Symbol Sync
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
        
        # Costas Loop
        self.costas = digital.costas_loop_cc(costas_bw, self.arity, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_dec = digital.diff_decoder_bb(self.diff_mod, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        self.sink = blocks.vector_sink_b(1)
        
        self.connect(self.src, self.mod, self.channel, self.agc, self.fll, self.rx_filter,
                     self.symbol_sync, self.costas, self.decoder, self.diff_dec)
                     
        if self.bps > 1:
            self.connect(self.diff_dec, self.mapper, self.unpacker, self.sink)
        else:
            self.connect(self.diff_dec, self.sink)

def evaluate_fll(rx_bits, tx_bits, discard_transient=200):
    rx_b = np.array(rx_bits)
    tx_b = np.array(tx_bits)
    
    if len(rx_b) < len(tx_b) + discard_transient:
        return {'steady_ber': 1.0, 'steady_errors': len(tx_b)}
        
    corr = np.correlate(2 * rx_b - 1, 2 * tx_b - 1, mode='full')
    lag = np.argmax(corr) - len(tx_b) + 1
    aligned = rx_b[lag : lag + len(tx_b)]
    
    if len(aligned) == len(tx_b):
        steady_rx = aligned[discard_transient:]
        steady_tx = tx_b[discard_transient:]
        errs = np.sum(steady_rx != steady_tx)
        ber = errs / float(len(steady_tx))
        return {'steady_ber': ber, 'steady_errors': int(errs)}
        
    return {'steady_ber': 1.0, 'steady_errors': len(tx_b)}

def run_test(mod_type='ALL'):
    print("================================================================================")
    print(" [PHY2 Stage 05] FLL Band-Edge Frequency Recovery Test (BPSK & QPSK)            ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    np.random.seed(42)
    test_bytes = [0x55] * 20 + list(np.random.randint(0, 256, 300))
    
    test_offsets = [
        ("Moderate Positive Offset (+1.5% samp_rate)", +0.015),
        ("Moderate Negative Offset (-1.5% samp_rate)", -0.015),
        ("Large Carrier Offset (+2.5% samp_rate)",    +0.025),
    ]
    
    all_passed = True
    
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} ---")
        tx_bits = []
        for b in test_bytes:
            for i in range(7, -1, -1):
                tx_bits.append((b >> i) & 1)
                
        for desc, fo in test_offsets:
            tb = FLLTester(test_bytes, mod_type=mod, freq_offset=fo, noise_volt=0.01)
            tb.run()
            res = evaluate_fll(tb.sink.data(), tx_bits)
            
            print(f"  {desc}")
            print(f"    Steady-State BER: {res['steady_ber']:.6f} ({res['steady_errors']} errors)")
            
            if res['steady_ber'] < 0.05:
                print(f"    -> [PASS] Frequency locked successfully.")
            else:
                print(f"    -> [FAIL] Frequency lock failed!")
                all_passed = False
                
    print("\n================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 05 Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_test(args.mod))
