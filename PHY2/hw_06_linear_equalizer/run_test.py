#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 06: Hardware Correlation Estimator + Adaptive Linear Equalizer Test Runner (BPSK & QPSK)
Verifies multipath equalization across SDR Hardware (Pluto / BladeRF / RTL-SDR / Channel).
"""

import sys
import os
import argparse
import math
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes
from PHY2.hardware.sdr_blocks_helper import create_sdr_source_sink

class HardwareEqualizerTester(gr.top_block):
    def __init__(self, num_symbols=50000, mod_type='BPSK', sps=4, alpha=0.35, samp_rate=32000,
                 hw_type='sim', uri='ip:192.168.2.1', cf=433.98e6):
        super().__init__("Hardware_Equalizer_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.bps = 1
            self.costas_order = 2
            self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
            self.preamble_bytes = [0x55] * 32
            num_syms = 32 * 8
            self.training_symbols = [(-1.0 if (i % 2 == 0) else 1.0) + 0j for i in range(num_syms)]
        else: # QPSK
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            self.bps = 2
            self.costas_order = 4
            self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
            self.preamble_bytes = [0x33, 0xCC] * 16
            num_syms = 32 * 4
            pts = [(-1.0 - 1.0j) / math.sqrt(2), (1.0 + 1.0j) / math.sqrt(2)]
            self.training_symbols = [pts[i % 2] for i in range(num_syms)]
            
        np.random.seed(42)
        tx_bytes = list(np.random.randint(0, 256, num_symbols // 8, dtype=np.uint8))
        
        # Transmitter
        self.src = blocks.vector_source_b(tx_bytes, False)
        self.unpack_tx = blocks.unpack_k_bits_bb(8)
        self.tx_dump = blocks.vector_sink_b(1)
        self.connect(self.src, self.unpack_tx, self.tx_dump)
        
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
        
        # Hardware SDR / Multipath Channel
        if hw_type in ['pluto', 'bladerf']:
            self.hw_src, self.hw_snk, self.active_hw = create_sdr_source_sink(hw_type, uri, cf, samp_rate)
            self.use_rf = True
        else:
            self.channel = channels.channel_model(
                noise_voltage=0.02,
                frequency_offset=0.005,
                epsilon=1.0,
                taps=[1.0, 0.25, 0.10]
            )
            self.use_rf = False
            
        # Receiver DSP Chain
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, 0.0314)
        
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        self.symbol_sync = digital.symbol_sync_cc(
            self.ted_type, sps, 0.025, 1.0, 1.0, 1.5, 1, self.constellation, digital.IR_MMSE_8TAP, 128, []
        )
        
        # Correlation Estimator coupled with Linear Equalizer
        mark_delay = len(self.training_symbols) - 1
        self.corr_est = digital.corr_est_cc(self.training_symbols, 1, mark_delay, 0.8)
        adpt_alg = digital.adaptive_algorithm_cma(self.constellation, 0.001, 1).base()
        self.equalizer = digital.linear_equalizer(11, 1, adpt_alg, True, self.training_symbols, 'corr_est')
        
        self.costas = digital.costas_loop_cc(0.0628, self.costas_order, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(2 if self.bps==1 else 4, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        self.sink = blocks.vector_sink_b(1)
        
        # Connections
        if self.use_rf:
            self.connect(self.src, self.mod, self.hw_snk)
            self.connect(self.hw_src, self.agc, self.fll, self.rx_filter,
                         self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
        else:
            self.connect(self.src, self.mod, self.channel, self.agc, self.fll, self.rx_filter,
                         self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
                         
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.sink)
        else:
            self.connect(self.diff_decoder, self.sink)

def run_test(mod_type='ALL', hw_type='sim', uri='ip:192.168.2.1'):
    print("================================================================================")
    print(f" [PHY2 Stage 06] Hardware Corr Estimator + Adaptive Equalizer (HW: {hw_type.upper()}) ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    all_passed = True
    
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} on Hardware Target: {hw_type} ---")
        tb = HardwareEqualizerTester(mod_type=mod, hw_type=hw_type, uri=uri)
        tb.run()
        
        tx_bits = list(tb.tx_dump.data())
        rx_bits = list(tb.sink.data())
        
        tx_arr = np.array(tx_bits[5000:15000], dtype=float) * 2 - 1
        rx_arr = np.array(rx_bits[5000:15000], dtype=float) * 2 - 1
        
        corr = np.correlate(rx_arr, tx_arr, mode='full')
        best_lag = np.argmax(np.abs(corr)) - (len(tx_arr) - 1)
        is_inverted = corr[best_lag + len(tx_arr) - 1] < 0
        
        start_tx = 6000
        start_rx = start_tx + best_lag
        eval_len = 10000
        
        if 0 <= start_rx and start_rx + eval_len <= len(rx_bits):
            tx_sub = np.array(tx_bits[start_tx : start_tx + eval_len])
            rx_sub = np.array(rx_bits[start_rx : start_rx + eval_len])
            if is_inverted:
                rx_sub = 1 - rx_sub
            errs = int(np.sum(tx_sub != rx_sub))
            ber = errs / float(eval_len)
        else:
            errs = eval_len
            ber = 1.0
            
        print(f" Transmitted Bits : {len(tx_bits)} | Received Bits: {len(rx_bits)}")
        print(f" Steady-State BER : {ber:.6f} ({errs} errors / {eval_len} bits)")
        
        if ber <= 0.05:
            print(f" -> [PASS] Hardware Corr Estimator + Adaptive Equalizer Verified for {mod}!")
        else:
            print(f" -> [FAIL] High BER ({ber:.4f}) indicates multipath distortion.")
            all_passed = False
            
    print("================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 06 Hardware Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    parser.add_argument('--hw', type=str, default='sim', choices=['sim', 'pluto', 'bladerf', 'rtlsdr'])
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1')
    args = parser.parse_args()
    sys.exit(run_test(args.mod, args.hw, args.uri))
