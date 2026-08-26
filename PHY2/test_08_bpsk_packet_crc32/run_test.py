#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 08: Full Packet Engine with Protocol Formatter & CRC32 Test Runner (BPSK & QPSK)
Verifies packet framing, header generation, multiplexing, CRC32 verification, and PDU extraction
under active channel impairments.
"""

import sys
import argparse
import math
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class PacketEngineTester(gr.top_block):
    def __init__(self, test_payload, mod_type='BPSK', payload_size=32, num_packets=6, preamble_len=32,
                 freq_offset=0.005, noise_volt=0.02, time_offset=1.0001, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("Packet_Engine_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_mod = 2
            self.ted_type = digital.TED_MUELLER_AND_MULLER
            self.preamble_bytes = [0x55] * preamble_len
        else: # QPSK
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            self.arity = 4
            self.bps = 2
            self.diff_mod = 4
            self.ted_type = digital.TED_GARDNER
            self.preamble_bytes = [0x33, 0xCC] * (preamble_len // 2)
            
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0, 1)
        
        # Transmitter Blocks
        self.src = blocks.vector_source_b(test_payload, False)
        self.s2ts_payload = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, payload_size, 'packet_len')
        self.crc_tx = digital.crc32_bb(False, 'packet_len', True)
        self.formatter = digital.protocol_formatter_bb(self.hdr, 'packet_len')
        
        self.preamble_src = blocks.vector_source_b(self.preamble_bytes * num_packets, False)
        self.s2ts_preamble = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, preamble_len, 'packet_len')
        
        self.mux = blocks.tagged_stream_mux(gr.sizeof_char * 1, 'packet_len', 0)
        
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
        
        # Channel with Impairments
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=freq_offset,
            epsilon=time_offset,
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
            self.ted_type, sps, 0.045, 1.0, 1.0, 1.5, 1, self.constellation, digital.IR_MMSE_8TAP, 128, []
        )
        self.costas = digital.costas_loop_cc(0.0628, self.arity, False)
        self.dec = digital.constellation_decoder_cb(self.constellation)
        self.diff_dec = digital.diff_decoder_bb(self.diff_mod, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
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
        self.connect(self.mux, self.mod, self.channel, self.agc, self.fll, self.rx_filter, self.sync, self.costas, self.dec, self.diff_dec)
        
        if self.bps > 1:
            self.connect(self.diff_dec, self.mapper, self.unpacker, self.correlator)
        else:
            self.connect(self.diff_dec, self.correlator)
            
        # RX Deframer Connections
        self.connect(self.correlator, self.repack, self.crc_rx, self.sink)

def run_test(mod_type='ALL'):
    print("================================================================================")
    print(" [PHY2 Stage 08] Running Packet Engine & CRC32 Test (BPSK & QPSK Impairments)   ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    payload_size = 32
    num_packets = 6 # 1 warmup + 5 data packets
    np.random.seed(2024)
    
    test_payload = [int((p * 13 + i) % 256) for p in range(num_packets) for i in range(payload_size)]
    all_passed = True
    
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} ---")
        tb = PacketEngineTester(test_payload, mod_type=mod, payload_size=payload_size, num_packets=num_packets, preamble_len=32)
        tb.run()
        
        rx_bytes = list(tb.sink.data())
        received_packets = len(rx_bytes) // payload_size
        
        print(f" Transmitted Packets : {num_packets}")
        print(f" Received CRC-Valid  : {received_packets}")
        print(f" Received Data Size  : {len(rx_bytes)} bytes")
        
        matched_packets = 0
        for p in range(received_packets):
            rx_p = rx_bytes[p*payload_size : (p+1)*payload_size]
            for orig_p in range(num_packets):
                tx_p = test_payload[orig_p*payload_size : (orig_p+1)*payload_size]
                if rx_p == tx_p:
                    matched_packets += 1
                    break
                    
        print(f" Bit-Exact Match Pkts: {matched_packets} / {num_packets}")
        
        if received_packets >= 5 and matched_packets == received_packets:
            print(f" -> [OK] 100% CRC32 and framing integrity verified for {mod}.")
        else:
            print(f" -> [FAIL] Packet integrity failed for {mod}!")
            all_passed = False
            
    print("\n================================================================================")
    if all_passed:
        print(" [PASS] Stage 08: Packet Engine & CRC32 Passed for BPSK & QPSK!")
    else:
        print(" [FAIL] Stage 08: Packet Engine failed.")
    print("================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 08 Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_test(args.mod))
