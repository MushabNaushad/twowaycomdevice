#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 08: Full BPSK Packet Engine with Protocol Formatter & CRC32 Test Runner
Verifies packet framing, header generation, multiplexing, CRC32 verification, and PDU extraction.
"""

import sys
import math
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class BPSKPacketEngineTester(gr.top_block):
    def __init__(self, test_payload, payload_size=32, num_packets=5, preamble_len=32, freq_offset=0.0, noise_volt=0.0, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("BPSK_Packet_Engine_Tester", catch_exceptions=True)
        
        self.BPSK_CONST = digital.constellation_bpsk().base()
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0)
        
        # Transmitter Blocks
        self.src = blocks.vector_source_b(test_payload, False)
        self.s2ts_payload = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, payload_size, 'packet_len')
        self.crc_tx = digital.crc32_bb(False, 'packet_len', True)
        self.formatter = digital.protocol_formatter_bb(self.hdr, 'packet_len')
        
        self.preamble_src = blocks.vector_source_b([0x55] * preamble_len * num_packets, False)
        self.s2ts_preamble = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, preamble_len, 'packet_len')
        
        self.mux = blocks.tagged_stream_mux(gr.sizeof_char * 1, 'packet_len', 0)
        
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
        
        # Channel
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=freq_offset,
            epsilon=1.0,
            taps=[1.0],
            noise_seed=42,
            block_tags=False
        )
        
        # Receiver Blocks
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, 2 * math.pi * 0.005)
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        self.sync = digital.symbol_sync_cc(
            digital.TED_MUELLER_AND_MULLER, sps, 0.045, 1.0, 1.0, 1.5, 1, self.BPSK_CONST, digital.IR_MMSE_8TAP, 128, []
        )
        self.costas = digital.costas_loop_cc(0.0628, 2, False)
        self.dec = digital.constellation_decoder_cb(self.BPSK_CONST)
        
        # Packet Deframer & CRC32 Checker
        self.correlator = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code, 2, 'packet_len')
        self.repack = blocks.repack_bits_bb(1, 8, 'packet_len', False, gr.GR_MSB_FIRST)
        self.crc_rx = digital.crc32_bb(True, 'packet_len', True)
        self.sink = blocks.vector_sink_b()
        
        # TX Connections
        self.connect(self.preamble_src, self.s2ts_preamble, (self.mux, 0))
        self.connect(self.src, self.s2ts_payload, self.crc_tx)
        self.connect(self.crc_tx, self.formatter, (self.mux, 1))
        self.connect((self.crc_tx, 0), (self.mux, 2))
        
        # PHY & Channel Connections
        self.connect(self.mux, self.mod, self.channel, self.agc, self.fll, self.rx_filter, self.sync, self.costas, self.dec)
        
        # RX Deframer Connections
        self.connect(self.dec, self.correlator, self.repack, self.crc_rx, self.sink)

def run_test():
    print("==================================================")
    print(" [PHY2 Stage 08] Running BPSK Packet & CRC32 Test")
    print("==================================================")
    
    payload_size = 32
    num_packets = 6 # 1 warmup + 5 data packets
    np.random.seed(2024)
    
    test_payload = [int((p * 13 + i) % 256) for p in range(num_packets) for i in range(payload_size)]
    
    tb = BPSKPacketEngineTester(test_payload, payload_size=payload_size, num_packets=num_packets, preamble_len=32)
    tb.run()
    
    rx_bytes = list(tb.sink.data())
    received_packets = len(rx_bytes) // payload_size
    
    print(f"Transmitted Total Packets : {num_packets} ({len(test_payload)} bytes)")
    print(f"Received CRC-Valid Packets: {received_packets} ({len(rx_bytes)} bytes)")
    
    # Check packet matching
    matched_count = 0
    for p in range(received_packets):
        pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
        for orig_p in range(num_packets):
            orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
            if pkt == orig_pkt:
                matched_count += 1
                break
                
    print(f"Exact Content Verified    : {matched_count} / {received_packets} packets")
    
    if received_packets >= (num_packets - 1) and matched_count == received_packets:
        print("[PASS] Packet Engine successfully framed, transmitted, decoded, and verified CRC32 checksums!")
        return 0
    else:
        print("[FAIL] Packet delivery or CRC verification failure!")
        return 1

if __name__ == "__main__":
    sys.exit(run_test())
