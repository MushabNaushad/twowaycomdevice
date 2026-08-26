#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 09: CDP Modular Transceiver Test Runner (BPSK & QPSK)
Verifies complete parameterized PHY transceiver with differential encoding/decoding
under active channel impairments (noise voltage, frequency offset, clock drift).
"""

import sys
import argparse
import math
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class CDPTransceiverTester(gr.top_block):
    def __init__(self, test_payload, mod_type='BPSK', payload_size=64, packets=10, preamble_size=32,
                 freq_offset=0.0, time_offset=1.0, noise_volt=0.0,
                 fll_bw=0.0314, costas_bw=0.0628, sym_bw=0.045,
                 sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("CDP_Transceiver_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_mod = 2
            self.ted_type = digital.TED_MUELLER_AND_MULLER
            self.preamble_bytes = [0x55] * preamble_size
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
            self.preamble_bytes = [0x33, 0xCC] * (preamble_size // 2)
            
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0, 1)
        
        # Transmitter Blocks
        self.src = blocks.vector_source_b(test_payload, False)
        self.s2ts_payload = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, payload_size, 'packet_len')
        self.crc_tx = digital.crc32_bb(False, 'packet_len', True)
        self.formatter = digital.protocol_formatter_bb(self.hdr, 'packet_len')
        
        self.preamble_src = blocks.vector_source_b(self.preamble_bytes * packets, False)
        self.s2ts_preamble = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, preamble_size, 'packet_len')
        
        self.mux = blocks.tagged_stream_mux(gr.sizeof_char * 1, 'packet_len', 0)
        
        # Modulator with Differential Encoding
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
        
        # Channel Model with Impairments
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
            self.ted_type, sps, sym_bw, 1.0, 1.0, 1.5, 1, self.constellation, digital.IR_MMSE_8TAP, 128, []
        )
        
        self.costas = digital.costas_loop_cc(costas_bw, self.arity, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(self.diff_mod, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
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
                     self.symbol_sync, self.costas, self.decoder, self.diff_decoder)
                     
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.correlator)
        else:
            self.connect(self.diff_decoder, self.correlator)
            
        self.connect(self.correlator, self.repack, self.crc_rx, self.sink)

def run_test(mod_type='ALL'):
    print("================================================================================")
    print(" [PHY2 Stage 09] Running CDP Transceiver Test (BPSK & QPSK with Impairments)   ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    payload_size = 64
    packets = 10
    test_payload = [int((p * 19 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    test_cases = [
        ("Moderate Impairments (fo=0.005, eps=1.0001, nv=0.03)", 0.005, 1.0001, 0.03),
        ("Heavy Carrier Offset (fo=0.015, eps=1.0000, nv=0.02)", 0.015, 1.0000, 0.02),
        ("Severe Multi-Impairment (fo=-0.010, eps=0.9998, nv=0.08)", -0.010, 0.9998, 0.08),
    ]
    
    all_passed = True
    
    for mod in modulations:
        print(f"\n>>> Testing Modulation: {mod} <<<")
        for desc, fo, to, nv in test_cases:
            tb = CDPTransceiverTester(
                test_payload=test_payload,
                mod_type=mod,
                payload_size=payload_size,
                packets=packets,
                freq_offset=fo,
                time_offset=to,
                noise_volt=nv
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
                        
            print(f"  {desc}")
            print(f"    -> Transmitted: {packets} pkts | Received: {rx_packets} pkts | CRC Valid & Matched: {matched} pkts | PDR: {pdr:.1f}%")
            
            if rx_packets < (packets - 1) or matched != rx_packets:
                print(f"    -> [FAIL] Packet delivery or payload integrity compromised!")
                all_passed = False
            else:
                print(f"    -> [OK] Verified.")
                
    if all_passed:
        print("\n================================================================================")
        print(" [PASS] Stage 09: CDP Transceiver verified for BPSK & QPSK across all impairments!")
        print("================================================================================")
        return 0
    else:
        print("\n================================================================================")
        print(" [FAIL] Stage 09 verification failed.")
        print("================================================================================")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 09 Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_test(args.mod))
