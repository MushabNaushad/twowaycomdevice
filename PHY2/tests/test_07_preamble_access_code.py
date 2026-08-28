#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 07: Hardware Preamble & Access Code Frame Sync Test
Throws RuntimeError if requested physical SDR hardware is not connected.
"""

import sys
import os
import time
import math
import argparse
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes
from PHY2.hardware.sdr_blocks_helper import create_sdr_source_sink

class Stage07FrameSyncTransceiver(gr.top_block):
    def __init__(self, test_payload, mod_type='BPSK', payload_size=64, packets=10, preamble_size=32, hw_type='sim', uri='ip:192.168.2.1', cf=433.98e6, gain=20.0):
        super().__init__("Stage07_FrameSync_Transceiver", catch_exceptions=True)
        self.mod_type = mod_type.upper()
        sps = 4
        alpha = 0.35
        samp_rate = 1000000 if hw_type != 'sim' else 32000
        
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.bps = 1
            self.costas_order = 2
            self.diff_mod = 2
            self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
            self.preamble_bytes = [0x55] * preamble_size
            num_syms = preamble_size * 8
            self.training_symbols = [(-1.0 if (i % 2 == 0) else 1.0) + 0j for i in range(num_syms)]
        else:
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j], [0, 1, 3, 2], 4, 2, 2, 1, 1
            ).base()
            self.bps = 2
            self.costas_order = 4
            self.diff_mod = 4
            self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
            self.preamble_bytes = [0x33, 0xCC] * (preamble_size // 2)
            num_syms = preamble_size * 4
            pts = [(-1.0 - 1.0j) / math.sqrt(2), (1.0 + 1.0j) / math.sqrt(2)]
            self.training_symbols = [pts[i % 2] for i in range(num_syms)]
            
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0, 1)
        self.src = blocks.vector_source_b(test_payload, False)
        self.s2ts_payload = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, payload_size, 'packet_len')
        self.formatter = digital.protocol_formatter_bb(self.hdr, 'packet_len')
        
        self.preamble_src = blocks.vector_source_b(self.preamble_bytes * packets, False)
        self.s2ts_preamble = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, preamble_size, 'packet_len')
        self.mux = blocks.tagged_stream_mux(gr.sizeof_char * 1, 'packet_len', 0)
        
        self.mod = digital.generic_mod(
            constellation=self.constellation, differential=True, samples_per_symbol=sps,
            pre_diff_code=True, excess_bw=alpha, verbose=False, log=False, truncate=False
        )
        
        if hw_type in ['pluto', 'bladerf', 'rtlsdr']:
            self.hw_src, self.hw_snk, self.active_hw = create_sdr_source_sink(
                hw_type=hw_type, uri=uri, cf=cf, samp_rate=samp_rate, tx_gain=gain, rx_gain=gain + 10
            )
            self.use_rf = True
        else:
            self.channel = channels.channel_model(
                noise_voltage=0.01, frequency_offset=0.005, epsilon=1.0001, taps=[1.0]
            )
            self.use_rf = False
            
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, 0.0314)
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, 32 * sps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        self.symbol_sync = digital.symbol_sync_cc(
            self.ted_type, sps, 0.025, 1.0, 1.0, 1.5, 1, self.constellation, digital.IR_MMSE_8TAP, 128, []
        )
        
        mark_delay = len(self.training_symbols) - 1
        self.corr_est = digital.corr_est_cc(self.training_symbols, 1, mark_delay, 0.8)
        adpt_alg = digital.adaptive_algorithm_cma(self.constellation, 0.001, 1).base()
        self.equalizer = digital.linear_equalizer(11, 1, adpt_alg, True, self.training_symbols, 'corr_est')
        
        self.costas = digital.costas_loop_cc(0.0628, self.costas_order, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(self.diff_mod, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        self.correlator = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code, 2, 'packet_len')
        self.repack = blocks.repack_bits_bb(1, 8, 'packet_len', False, gr.GR_MSB_FIRST)
        self.sink = blocks.vector_sink_b()
        
        self.connect(self.preamble_src, self.s2ts_preamble, (self.mux, 0))
        self.connect(self.src, self.s2ts_payload)
        self.connect(self.s2ts_payload, self.formatter, (self.mux, 1))
        self.connect(self.s2ts_payload, (self.mux, 2))
        
        if self.use_rf:
            self.connect(self.mux, self.mod, self.hw_snk)
            self.connect(self.hw_src, self.agc, self.fll, self.rx_filter, self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
        else:
            self.connect(self.mux, self.mod, self.channel, self.agc, self.fll, self.rx_filter, self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
            
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.correlator)
        else:
            self.connect(self.diff_decoder, self.correlator)
            
        self.connect(self.correlator, self.repack, self.sink)

def run_stage_07(hw_type='sim', mod_type='ALL', uri='ip:192.168.2.1', freq=433.98e6, gain=20.0):
    mods = ['BPSK', 'QPSK'] if mod_type == 'ALL' else [mod_type]
    all_passed = True
    packets = 10
    payload_size = 64
    payload = [int((p * 23 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    for m in mods:
        tb = Stage07FrameSyncTransceiver(test_payload=payload, mod_type=m, payload_size=payload_size, packets=packets, hw_type=hw_type, uri=uri, cf=freq, gain=gain)
        tb.run()
        rx = list(tb.sink.data())
        if len(rx) < 64:
            all_passed = False
    return all_passed

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stage 07 Hardware Frame Sync Test Runner")
    parser.add_argument('--hw', type=str, default='sim', choices=['sim', 'pluto', 'bladerf', 'rtlsdr'])
    parser.add_argument('--mod', type=str, default='ALL', choices=['ALL', 'BPSK', 'QPSK'])
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1')
    parser.add_argument('--freq', type=float, default=433.98e6)
    parser.add_argument('--gain', type=float, default=20.0)
    args = parser.parse_args()
    
    res = run_stage_07(args.hw, args.mod, args.uri, args.freq, args.gain)
    sys.exit(0 if res else 1)
