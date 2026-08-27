#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 09: Full Modular CDP Hardware Transceiver Test Runner (BPSK & QPSK)
Verifies end-to-end transceiver architecture across SDR Hardware (Pluto / BladeRF / RTL-SDR / Channel).
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

class CDPTransceiverTester(gr.top_block):
    def __init__(self, test_payload, mod_type='BPSK', payload_size=64, packets=10, preamble_size=32,
                 freq_offset=0.0, time_offset=1.0, noise_volt=0.0,
                 fll_bw=0.0314, costas_bw=0.0628, sym_bw=0.025,
                 sps=4, alpha=0.35, samp_rate=32000, hw_type='sim', uri='ip:192.168.2.1', cf=433.98e6):
        super().__init__("CDP_Transceiver_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_mod = 2
            self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
            self.preamble_bytes = [0x55] * preamble_size
            num_syms = min(preamble_size * 8, 48)
            self.training_symbols = [(-1.0 if (i % 2 == 0) else 1.0) + 0j for i in range(num_syms)]
        else: # QPSK
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            self.arity = 4
            self.bps = 2
            self.diff_mod = 4
            self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
            self.preamble_bytes = [0x33, 0xCC] * (preamble_size // 2)
            num_syms = min(preamble_size * 4, 48)
            pts = [(-1.0 - 1.0j) / math.sqrt(2), (1.0 + 1.0j) / math.sqrt(2)]
            self.training_symbols = [pts[i % 2] for i in range(num_syms)]
            
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0, 1)
        
        # Transmitter Blocks
        self.src = blocks.vector_source_b(test_payload, False)
        self.s2ts_payload = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, payload_size, 'packet_len')
        self.crc_tx = digital.crc32_bb(False, 'packet_len', True)
        self.formatter = digital.protocol_formatter_bb(self.hdr, 'packet_len')
        
        self.preamble_src = blocks.vector_source_b(self.preamble_bytes * packets, False)
        self.s2ts_preamble = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, preamble_size, 'packet_len')
        self.mux = blocks.tagged_stream_mux(gr.sizeof_char * 1, 'packet_len', 0)
        
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
        
        # Hardware SDR / Channel
        if hw_type in ['pluto', 'bladerf']:
            self.hw_src, self.hw_snk, self.active_hw = create_sdr_source_sink(hw_type, uri, cf, samp_rate)
            self.use_rf = True
        else:
            self.channel = channels.channel_model(
                noise_voltage=noise_volt,
                frequency_offset=freq_offset,
                epsilon=time_offset,
                taps=[1.0, 0.15, 0.05],
                noise_seed=42,
                block_tags=False
            )
            self.use_rf = False
            
        # Receiver DSP Chain
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, fll_bw)
        
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        self.symbol_sync = digital.symbol_sync_cc(
            self.ted_type, sps, sym_bw, 1.0, 1.0, 1.5, 1, self.constellation, digital.IR_MMSE_8TAP, 128, []
        )
        
        # Correlation Estimator coupled with Linear Equalizer
        mark_delay = len(self.training_symbols) - 1
        self.corr_est = digital.corr_est_cc(self.training_symbols, 1, mark_delay, 0.8)
        adpt_alg = digital.adaptive_algorithm_cma(self.constellation, 0.001, 1).base()
        self.equalizer = digital.linear_equalizer(11, 1, adpt_alg, True, self.training_symbols, 'corr_est')
        
        self.costas = digital.costas_loop_cc(costas_bw, self.arity, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(self.diff_mod, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        self.correlator = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code, 2, 'packet_len')
        self.repack = blocks.repack_bits_bb(1, 8, 'packet_len', False, gr.GR_MSB_FIRST)
        self.crc_rx = digital.crc32_bb(True, 'packet_len', True)
        self.sink = blocks.vector_sink_b()
        
        # Connect TX
        self.connect(self.preamble_src, self.s2ts_preamble, (self.mux, 0))
        self.connect(self.src, self.s2ts_payload, self.crc_tx)
        self.connect(self.crc_tx, self.formatter, (self.mux, 1))
        self.connect((self.crc_tx, 0), (self.mux, 2))
        
        # Connect RX
        if self.use_rf:
            self.connect(self.mux, self.mod, self.hw_snk)
            self.connect(self.hw_src, self.agc, self.fll, self.rx_filter,
                         self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
        else:
            self.connect(self.mux, self.mod, self.channel, self.agc, self.fll, self.rx_filter,
                         self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
                         
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.correlator)
        else:
            self.connect(self.diff_decoder, self.correlator)
            
        self.connect(self.correlator, self.repack, self.crc_rx, self.sink)

def run_test(mod_type='ALL', hw_type='sim', uri='ip:192.168.2.1'):
    print("================================================================================")
    print(f" [PHY2 Stage 09] Hardware CDP Transceiver Architecture (HW: {hw_type.upper()})   ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    payload_size = 64
    packets = 10
    test_payload = [int((p * 19 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    all_passed = True
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} on Hardware Target: {hw_type} ---")
        tb = CDPTransceiverTester(
            test_payload=test_payload,
            mod_type=mod,
            payload_size=payload_size,
            packets=packets,
            freq_offset=0.005,
            time_offset=1.0001,
            noise_volt=0.03,
            hw_type=hw_type,
            uri=uri
        )
        tb.run()
        
        rx_data = list(tb.sink.data())
        rx_packets = len(rx_data) // payload_size
        pdr = (rx_packets / float(packets)) * 100.0
        
        matched = 0
        for p in range(rx_packets):
            pkt = rx_data[p * payload_size : (p + 1) * payload_size]
            for orig_p in range(packets):
                orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                if pkt == orig_pkt:
                    matched += 1
                    break
                    
        print(f" Transmitted: {packets} pkts | Received: {rx_packets} pkts | CRC Valid & Matched: {matched} pkts")
        print(f" Packet Delivery Ratio: {pdr:.1f}%")
        
        if rx_packets >= (packets - 1) and matched == rx_packets:
            print(f" -> [PASS] Hardware CDP Transceiver Verified for {mod}!")
        else:
            print(f" -> [FAIL] Packet delivery or payload integrity compromised!")
            all_passed = False
            
    print("================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 09 Hardware Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    parser.add_argument('--hw', type=str, default='sim', choices=['sim', 'pluto', 'bladerf', 'rtlsdr'])
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1')
    args = parser.parse_args()
    sys.exit(run_test(args.mod, args.hw, args.uri))
