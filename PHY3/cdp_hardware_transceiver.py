#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY3 CDP Hardware Transceiver
Direct programmatic implementation of the user's original GNU Radio flow diagram
(CDP transeciever.grc) parameterized for hardware optimization across BPSK and QPSK.
Supports Adalm-Pluto, bladeRF, RTL-SDR, and simulated channel loopback.
"""

import sys
import os
import math

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

os.environ['HOME'] = WORKSPACE_ROOT
os.environ['GR_CONF_VMCIRCBUF_DEFAULT_FACTORY'] = 'gr::vmcircbuf_mmap_tmpfile_factory'
os.environ['GR_CONF_vmcircbuf_default_factory'] = 'gr::vmcircbuf_mmap_tmpfile_factory'

from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

# Import local SDR hardware helper
sys.path.insert(0, os.path.dirname(__file__))
from sdr_blocks_helper import create_sdr_source_sink

class CDPHardwareTransceiver(gr.top_block):
    """
    Parametric hardware transceiver implementing the exact signal chain from CDP transeciever.grc.
    Supports BPSK and QPSK with y·y' TED (digital.TED_SIGNAL_TIMES_SLOPE_ML), Correlation Estimator,
    and Adaptive Linear Equalizer (CMA).
    """
    def __init__(self,
                 test_payload,
                 mod_type='QPSK',
                 payload_size=64,
                 packets=10,
                 preamble_size=32,
                 sps=4,
                 alpha=0.45,
                 samp_rate=1000000,
                 nfilts=32,
                 fll_loop_bw=0.0314,
                 costas_bw=0.0628,
                 sym_bw=0.025,
                 adpt_alg_step=0.0001,
                 hw_type='pluto',
                 uri='ip:192.168.2.1',
                 cf=433.98e6,
                 tx_gain=20.0,
                 rx_gain=30.0):
        super().__init__("CDP_Hardware_Transceiver", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        self.sps = sps
        self.alpha = alpha
        self.samp_rate = samp_rate
        self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
        
        # 1. Modulation & Constellation Setup
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_modulus = 2
            self.costas_order = 2
            self.map_table = [0, 1]
            self.preamble_bytes = [0x55] * preamble_size
            num_syms = max(4, min(preamble_size * 8, 48))
            self.training_symbols = [(-1.0 if (i % 2 == 0) else 1.0) + 0j for i in range(num_syms)]
        else:  # QPSK (Matching original QPSK_CONST rect mapping)
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            self.arity = 4
            self.bps = 2
            self.diff_modulus = 4
            self.costas_order = 4
            self.map_table = [0, 1, 3, 2]
            qpsk_pattern = [0x33, 0xCC] * (preamble_size // 2)
            if preamble_size % 2 != 0:
                qpsk_pattern.append(0x33)
            self.preamble_bytes = qpsk_pattern if qpsk_pattern else [0x33, 0xCC]
            num_syms = max(4, min(preamble_size * 4, 48))
            pts = [(-1.0 - 1.0j) / math.sqrt(2), (1.0 + 1.0j) / math.sqrt(2)]
            self.training_symbols = [pts[i % 2] for i in range(num_syms)]
            
        # 2. Header and Adaptive Algorithm Setup
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0, 1)
        self.adpt_alg = digital.adaptive_algorithm_cma(self.constellation, adpt_alg_step, 1).base()
        
        # 3. Filter Taps
        ntaps = nfilts * sps
        self.rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / float(sps), alpha, ntaps)
        
        # 4. Transmitter Signal Chain
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
        self.tag_gate = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        
        # 5. Hardware Interface / RF Layer
        self.hw_type = hw_type.lower()
        if self.hw_type in ['pluto', 'bladerf']:
            self.hw_src, self.hw_snk, self.active_hw = create_sdr_source_sink(
                hw_type=self.hw_type, uri=uri, cf=cf, samp_rate=samp_rate, tx_gain=tx_gain, rx_gain=rx_gain
            )
            self.use_rf = True
        elif self.hw_type == 'rtlsdr':
            self.hw_src, _, self.active_hw = create_sdr_source_sink(
                hw_type='rtlsdr', uri=uri, cf=cf, samp_rate=samp_rate, tx_gain=tx_gain, rx_gain=rx_gain
            )
            self.hw_snk = None
            self.use_rf = True
        else:  # 'sim' / 'loopback'
            self.channel = channels.channel_model(
                noise_voltage=0.03,
                frequency_offset=0.005,
                epsilon=1.0001,
                taps=[1.0, 0.12, 0.04],
                noise_seed=42
            )
            self.use_rf = False
            
        # 6. Receiver DSP Signal Chain (Matching CDP transeciever.grc)
        self.dc_blocker = filter.dc_blocker_cc(32, True)
        self.agc = analog.agc_cc(1e-4, 1.0, 1.0, 65536)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, fll_loop_bw)
        self.rx_filter = filter.fft_filter_ccc(1, self.rcc_taps, 1)
        
        # Symbol Synchronizer with y·y' Timing Error Detector
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
        
        # Correlation Estimator coupled with Linear Adaptive Equalizer
        mark_delay = len(self.training_symbols) - 1
        self.corr_est = digital.corr_est_cc(self.training_symbols, 1, mark_delay, 0.8)
        self.corr_null = blocks.null_sink(gr.sizeof_gr_complex)  # Prevent buffer fill / deadlock on Port 1
        self.equalizer = digital.linear_equalizer(11, 1, self.adpt_alg, True, self.training_symbols, 'corr_est')
        
        self.costas = digital.costas_loop_cc(costas_bw, self.costas_order, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(self.diff_modulus)
        
        if self.bps > 1:
            self.mapper = digital.map_bb(self.map_table)
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        self.correlator = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code, 2, 'packet_len')
        self.repack = blocks.repack_bits_bb(1, 8, 'packet_len', False, gr.GR_MSB_FIRST)
        self.crc_rx = digital.crc32_bb(True, 'packet_len', True)
        self.packet_sink = blocks.vector_sink_b()
        
        # 7. Connecting Graph
        # TX Connections
        self.connect(self.preamble_src, self.s2ts_preamble, (self.mux, 0))
        self.connect(self.src, self.s2ts_payload, self.crc_tx)
        self.connect(self.crc_tx, self.formatter, (self.mux, 1))
        self.connect((self.crc_tx, 0), (self.mux, 2))
        self.connect(self.mux, self.mod, self.tag_gate)
        
        # TX -> RF / Channel
        if self.use_rf and self.hw_snk is not None:
            self.connect(self.tag_gate, self.hw_snk)
        elif not self.use_rf:
            self.connect(self.tag_gate, self.channel)
            
        # RF / Channel -> RX
        rx_in = self.hw_src if self.use_rf else self.channel
        self.connect(rx_in, self.dc_blocker, self.agc, self.fll, self.rx_filter,
                     self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
        self.connect((self.corr_est, 1), self.corr_null)
        
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.correlator)
        else:
            self.connect(self.diff_decoder, self.correlator)
            
        self.connect(self.correlator, self.repack, self.crc_rx, self.packet_sink)

def test_hardware_transceiver(mod_type='QPSK', hw_type='sim', uri='ip:192.168.2.1', packets=10):
    """Utility function to test transceiver operation."""
    payload_size = 64
    test_payload = [int((p * 23 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    tb = CDPHardwareTransceiver(
        test_payload=test_payload,
        mod_type=mod_type,
        payload_size=payload_size,
        packets=packets,
        hw_type=hw_type,
        uri=uri
    )
    tb.run()
    rx_bytes = list(tb.packet_sink.data())
    received_packets = len(rx_bytes) // payload_size
    pdr = (received_packets / float(packets)) * 100.0
    
    matched_count = 0
    matched_originals = set()
    for p in range(received_packets):
        pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
        for orig_p in range(packets):
            if orig_p in matched_originals:
                continue
            orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
            if pkt == orig_pkt:
                matched_count += 1
                matched_originals.add(orig_p)
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
    print("Testing PHY3 CDP Hardware Transceiver (BPSK & QPSK)...")
    for m in ['BPSK', 'QPSK']:
        res = test_hardware_transceiver(mod_type=m, hw_type='sim')
        print(f"Modulation: {res['mod_type']:4s} | TX Pkts: {res['transmitted_packets']:2d} | RX Pkts: {res['received_packets']:2d} | Verified: {res['matched_packets']:2d} | PDR: {res['pdr']:5.1f}%")
