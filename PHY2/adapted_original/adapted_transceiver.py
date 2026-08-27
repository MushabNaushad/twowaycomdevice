#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Adapted Original Transceiver
Parametric adapter for the user's original CDP Transceiver architecture.
Includes Correlation Estimator (digital.corr_est_cc) coupled with Adaptive Linear Equalizer.
Supports both BPSK and QPSK modulation schemes.
"""

import sys
import math
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class AdaptedOriginalTransceiver(gr.top_block):
    def __init__(self,
                 test_payload,
                 mod_type='QPSK',
                 payload_size=64,
                 packets=15,
                 preamble_size=48,
                 sps=4,
                 alpha=0.35,
                 samp_rate=32000,
                 nfilts=32,
                 fll_loop_bw=0.0100,
                 costas_bw=0.0628,
                 sym_bw=0.0250,
                 noise_volt=0.05,
                 freq_offset=0.005,
                 time_offset=1.0001,
                 adpt_alg_step=0.0001):
        super().__init__("Adapted_Original_Transceiver", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        self.sps = sps
        self.alpha = alpha
        self.samp_rate = samp_rate
        
        # 1. Setup Constellation, Modulation, & Ted Selection (y·y' TED)
        self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_modulus = 2
            self.map_table = [0, 1]
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
            self.diff_modulus = 4
            self.map_table = [0, 1, 3, 2]
            self.preamble_bytes = [0x33, 0xCC] * (preamble_size // 2)
            num_syms = min(preamble_size * 4, 48)
            pts = [(-1.0 - 1.0j) / math.sqrt(2), (1.0 + 1.0j) / math.sqrt(2)]
            self.training_symbols = [pts[i % 2] for i in range(num_syms)]
            
        # 2. Header and Adaptive Algorithm
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0, 1)
        self.adpt_alg = digital.adaptive_algorithm_cma(self.constellation, adpt_alg_step, 1).base()
        
        # 3. Filter Taps
        ntaps = nfilts * sps
        self.rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / float(sps), alpha, ntaps)
        
        # 4. Transmitter Blocks
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
        
        # 5. Channel Model with Impairments
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=freq_offset,
            epsilon=time_offset,
            taps=[1.0],
            noise_seed=42,
            block_tags=False
        )
        
        # 6. Receiver Blocks (matching original architecture with Correlation Estimator)
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0, 65536)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, fll_loop_bw)
        self.rx_filter = filter.fft_filter_ccc(1, self.rcc_taps, 1)
        
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
        
        # Correlation Estimator coupled with Linear Equalizer
        mark_delay = len(self.training_symbols) - 1
        self.corr_est = digital.corr_est_cc(self.training_symbols, 1, mark_delay, 0.8)
        self.equalizer = digital.linear_equalizer(11, 1, self.adpt_alg, True, self.training_symbols, 'corr_est')
        
        self.costas = digital.costas_loop_cc(costas_bw, self.arity, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(self.diff_modulus, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb(self.map_table)
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
        
        # Deframing and CRC Checker
        self.correlator = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code, 2, 'packet_len')
        self.repack = blocks.repack_bits_bb(1, 8, 'packet_len', False, gr.GR_MSB_FIRST)
        self.crc_rx = digital.crc32_bb(True, 'packet_len', True)
        self.packet_sink = blocks.vector_sink_b()
        
        # 7. Wiring Flowgraph
        # TX
        self.connect(self.preamble_src, self.s2ts_preamble, (self.mux, 0))
        self.connect(self.src, self.s2ts_payload, self.crc_tx)
        self.connect(self.crc_tx, self.formatter, (self.mux, 1))
        self.connect((self.crc_tx, 0), (self.mux, 2))
        self.connect(self.mux, self.mod, self.channel)
        
        # RX (Channel -> AGC -> FLL -> RX Filter -> Symbol Sync -> Corr Est -> Equalizer -> Costas -> Decoder)
        self.connect(self.channel, self.agc, self.fll, self.rx_filter,
                     self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
                     
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.correlator)
        else:
            self.connect(self.diff_decoder, self.correlator)
            
        self.connect(self.correlator, self.repack, self.crc_rx, self.packet_sink)

def test_transceiver(mod_type='QPSK', noise_volt=0.05, freq_offset=0.005, time_offset=1.0001, packets=15):
    payload_size = 64
    test_payload = [int((p * 17 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    tb = AdaptedOriginalTransceiver(
        test_payload=test_payload,
        mod_type=mod_type,
        payload_size=payload_size,
        packets=packets,
        noise_volt=noise_volt,
        freq_offset=freq_offset,
        time_offset=time_offset
    )
    tb.run()
    
    rx_bytes = list(tb.packet_sink.data())
    received_packets = len(rx_bytes) // payload_size
    pdr = (received_packets / float(packets)) * 100.0
    
    matched_count = 0
    for p in range(received_packets):
        pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
        for orig_p in range(packets):
            orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
            if pkt == orig_pkt:
                matched_count += 1
                break
                
    return {
        'mod_type': mod_type,
        'transmitted_packets': packets,
        'received_packets': received_packets,
        'matched_packets': matched_count,
        'pdr': pdr,
        'crc_valid_bytes': len(rx_bytes)
    }

if __name__ == '__main__':
    for m in ['BPSK', 'QPSK']:
        res = test_transceiver(mod_type=m)
        print(f"Modulation: {res['mod_type']:4s} | TX Pkts: {res['transmitted_packets']:2d} | RX Pkts: {res['received_packets']:2d} | Verified: {res['matched_packets']:2d} | PDR: {res['pdr']:5.1f}%")
