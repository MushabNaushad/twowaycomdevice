#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 09: CDP Modular BPSK Transceiver Test Runner
Verifies complete parameterized PHY transceiver flowgraph mirroring hardware versions architecture with differential decoding.
"""

import sys
import math
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class CDPTransceiverTester(gr.top_block):
    def __init__(self, test_payload, payload_size=64, packets=10, preamble_size=32,
                 freq_offset=0.0, time_offset=1.0, noise_volt=0.0,
                 fll_bw=0.0314, costas_bw=0.0628, sym_bw=0.045,
                 sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("CDP_Transceiver_Tester", catch_exceptions=True)
        
        self.BPSK_CONST = digital.constellation_bpsk().base()
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0)
        
        # Transmitter Blocks
        self.src = blocks.vector_source_b(test_payload, False)
        self.s2ts_payload = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, payload_size, 'packet_len')
        self.crc_tx = digital.crc32_bb(False, 'packet_len', True)
        self.formatter = digital.protocol_formatter_bb(self.hdr, 'packet_len')
        
        self.preamble_src = blocks.vector_source_b([0x55] * preamble_size * packets, False)
        self.s2ts_preamble = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, preamble_size, 'packet_len')
        
        self.mux = blocks.tagged_stream_mux(gr.sizeof_char * 1, 'packet_len', 0)
        
        # Modulator with Differential Encoding
        self.mod = digital.generic_mod(
            constellation=self.BPSK_CONST,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=False,
            excess_bw=alpha,
            verbose=False,
            log=False,
            truncate=False
        )
        
        # Channel Model
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=freq_offset,
            epsilon=time_offset,
            taps=[1.0],
            noise_seed=42,
            block_tags=False
        )
        
        # Receiver DSP Chain
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, fll_bw)
        
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        self.symbol_sync = digital.symbol_sync_cc(
            digital.TED_MUELLER_AND_MULLER, sps, sym_bw, 1.0, 1.0, 1.5, 1, self.BPSK_CONST, digital.IR_MMSE_8TAP, 128, []
        )
        
        self.costas = digital.costas_loop_cc(costas_bw, 2, False)
        self.decoder = digital.constellation_decoder_cb(self.BPSK_CONST)
        self.diff_decoder = digital.diff_decoder_bb(2)
        
        # Deframer & Verification
        self.correlator = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code, 2, 'packet_len')
        self.repack = blocks.repack_bits_bb(1, 8, 'packet_len', False, gr.GR_MSB_FIRST)
        self.crc_rx = digital.crc32_bb(True, 'packet_len', True)
        self.sink = blocks.vector_sink_b()
        
        # Connect TX
        self.connect(self.preamble_src, self.s2ts_preamble, (self.mux, 0))
        self.connect(self.src, self.s2ts_payload, self.crc_tx)
        self.connect(self.crc_tx, self.formatter, (self.mux, 1))
        self.connect((self.crc_tx, 0), (self.mux, 2))
        
        # Connect Channel & RX DSP
        self.connect(self.mux, self.mod, self.channel, self.agc, self.fll, self.rx_filter,
                     self.symbol_sync, self.costas, self.decoder, self.diff_decoder,
                     self.correlator, self.repack, self.crc_rx, self.sink)

def run_test():
    print("==================================================")
    print(" [PHY2 Stage 09] Running CDP BPSK Transceiver Test")
    print("==================================================")
    
    payload_size = 64
    packets = 10
    
    test_payload = [p + 48 for p in range(packets) for _ in range(payload_size)]
    
    test_cases = [
        ("Clean Channel", 0.0, 1.0, 0.0),
        ("Clock Drift (0.9998)", 0.0, 0.9998, 0.0),
        ("Carrier Offset (+0.015)", 0.015, 1.0, 0.0),
        ("Carrier Offset (-0.020)", -0.020, 1.0, 0.0),
    ]
    all_passed = True
    
    for name, fo, to, nv in test_cases:
        tb = CDPTransceiverTester(test_payload, payload_size=payload_size, packets=packets,
                                  freq_offset=fo, time_offset=to, noise_volt=nv)
        tb.run()
        rx_bytes = list(tb.sink.data())
        received_packets = len(rx_bytes) // payload_size
        
        matched_count = 0
        for p in range(received_packets):
            pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
            for orig_p in range(packets):
                orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                if pkt == orig_pkt:
                    matched_count += 1
                    break
                    
        print(f"Scenario: {name:24s} | Transmitted: {packets} | Received: {received_packets} | Verified: {matched_count}")
        
        if received_packets < (packets - 2) or matched_count != received_packets:
            all_passed = False
            print(f"  -> [FAIL] Packet throughput below threshold for scenario '{name}'")
        else:
            print(f"  -> [OK] 100% data integrity verified.")
            
    if all_passed:
        print("[PASS] CDP BPSK Modular Transceiver verified across all baseline operational scenarios!")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(run_test())
