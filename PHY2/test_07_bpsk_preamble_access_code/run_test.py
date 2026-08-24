#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 07: BPSK with Preamble and Access Code Test Runner
Verifies frame synchronization, preamble acquisition, and exact payload recovery with dual-polarity ambiguity resolution.
"""

import sys
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class BPSKFrameSyncTester(gr.top_block):
    def __init__(self, tx_bytes, freq_offset=0.01, noise_volt=0.0, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("BPSK_Frame_Sync_Tester", catch_exceptions=True)
        
        self.access_code = digital.packet_utils.default_access_code
        self.inv_access_code = ''.join('1' if c == '0' else '0' for c in self.access_code)
        
        self.BPSK_CONST = digital.constellation_bpsk().base()
        self.src = blocks.vector_source_b(list(tx_bytes), False, 1, [])
        
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
        
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, 2 * np.pi * 0.005)
        
        # Matched Filter
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        # Symbol Sync
        self.symbol_sync = digital.symbol_sync_cc(
            digital.TED_MUELLER_AND_MULLER,
            sps,
            0.045,
            1.0,
            1.0,
            1.5,
            1,
            self.BPSK_CONST,
            digital.IR_MMSE_8TAP,
            128,
            []
        )
        
        # Costas Loop
        self.costas = digital.costas_loop_cc(0.0628, 2, False)
        
        self.decoder = digital.constellation_decoder_cb(self.BPSK_CONST)
        
        # Dual Correlators for normal and inverted access codes
        self.corr_pos = digital.correlate_access_code_tag_bb(self.access_code, 2, 'sync_pos')
        self.corr_neg = digital.correlate_access_code_tag_bb(self.inv_access_code, 2, 'sync_neg')
        
        self.sink = blocks.vector_sink_b(1)
        
        self.connect(self.src, self.mod, self.channel, self.agc, self.fll, self.rx_filter, self.symbol_sync, self.costas, self.decoder, self.corr_pos, self.corr_neg, self.sink)

def build_packet(payload_bytes, preamble_len=16):
    access_code = digital.packet_utils.default_access_code
    ac_bits = [int(c) for c in access_code]
    
    # Unpack payload into bits
    payload_bits = []
    for b in payload_bytes:
        for i in range(7, -1, -1):
            payload_bits.append((b >> i) & 1)
            
    # Preamble bits (0x55 alternating 0, 1)
    preamble_bits = [0, 1] * (preamble_len * 4)
    
    # Flush bits (0x00)
    flush_bits = [0] * 64
    
    all_bits = preamble_bits + ac_bits + payload_bits + flush_bits
    
    # Pack to bytes for transmitter
    tx_bytes = []
    for i in range(0, len(all_bits), 8):
        val = 0
        for j in range(8):
            val = (val << 1) | all_bits[i + j]
        tx_bytes.append(val)
        
    return tx_bytes

def extract_payload(rx_bits, tags, payload_len):
    extracted_packets = []
    for t in tags:
        key = str(t.key)
        offset = t.offset
        
        if 'sync_pos' in key:
            raw = rx_bits[offset : offset + payload_len * 8]
            if len(raw) == payload_len * 8:
                pkt = bytes([sum(raw[i * 8 + j] << (7 - j) for j in range(8)) for i in range(payload_len)])
                extracted_packets.append(('POS', pkt))
        elif 'sync_neg' in key:
            raw = [1 - x for x in rx_bits[offset : offset + payload_len * 8]]
            if len(raw) == payload_len * 8:
                pkt = bytes([sum(raw[i * 8 + j] << (7 - j) for j in range(8)) for i in range(payload_len)])
                extracted_packets.append(('NEG', pkt))
                
    return extracted_packets

def run_test():
    print("==================================================")
    print(" [PHY2 Stage 07] Running Preamble & Access Code Test")
    print("==================================================")
    
    payload = b"Hello CDP Transceiver! Stage 07 Frame Synchronization."
    tx_bytes = build_packet(list(payload), preamble_len=20)
    
    test_conditions = [
        ("Zero Offset", 0.0, 0.0),
        ("Positive Freq Offset", 0.012, 0.0),
        ("Negative Freq Offset", -0.020, 0.0),
        ("Light AWGN Noise", 0.005, 0.15),
    ]
    all_passed = True
    
    for name, fo, nv in test_conditions:
        tb = BPSKFrameSyncTester(tx_bytes, freq_offset=fo, noise_volt=nv)
        tb.run()
        rx_bits = list(tb.sink.data())
        tags = tb.sink.tags()
        
        packets = extract_payload(rx_bits, tags, len(payload))
        print(f"Condition: {name:22s} | Tags: {len(tags)} | Extracted Packets: {len(packets)}")
        
        if len(packets) > 0 and packets[0][1] == payload:
            print(f"  -> [OK] Successfully extracted payload: '{packets[0][1].decode()}' (Pol: {packets[0][0]})")
        else:
            all_passed = False
            print(f"  -> [FAIL] Payload mismatch or frame sync lost!")
            
    if all_passed:
        print("[PASS] Preamble and Access Code Frame Synchronization verified across all conditions!")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(run_test())
