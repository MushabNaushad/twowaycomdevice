#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Stage 07: Preamble and Access Code Frame Sync Test Runner (BPSK & QPSK)
Verifies frame synchronization, preamble acquisition, and exact payload recovery
under active channel impairments (frequency offset, noise voltage, timing drift).
"""

import sys
import argparse
import numpy as np
from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

class FrameSyncTester(gr.top_block):
    def __init__(self, tx_bytes, mod_type='BPSK', freq_offset=0.008, noise_volt=0.02, time_offset=1.0001, sps=4, alpha=0.35, samp_rate=32000):
        super().__init__("Frame_Sync_Tester", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        self.access_code = digital.packet_utils.default_access_code
        self.inv_access_code = ''.join('1' if c == '0' else '0' for c in self.access_code)
        
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_mod = 2
            self.ted_type = digital.TED_MUELLER_AND_MULLER
        else:
            self.constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            self.arity = 4
            self.bps = 2
            self.diff_mod = 4
            self.ted_type = digital.TED_GARDNER
            
        self.src = blocks.vector_source_b(list(tx_bytes), False, 1, [])
        
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
        
        # Channel with Impairments
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=freq_offset,
            epsilon=time_offset,
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
            self.ted_type,
            sps,
            0.045,
            1.0,
            1.0,
            1.5,
            1,
            self.constellation,
            digital.IR_MMSE_8TAP,
            128,
            []
        )
        
        # Costas Loop
        self.costas = digital.costas_loop_cc(0.0628, self.arity, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(self.diff_mod, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        # Dual Correlators
        self.corr_pos = digital.correlate_access_code_tag_bb(self.access_code, 2, 'sync_pos')
        self.corr_neg = digital.correlate_access_code_tag_bb(self.inv_access_code, 2, 'sync_neg')
        self.sink = blocks.vector_sink_b(1)
        
        self.connect(self.src, self.mod, self.channel, self.agc, self.fll, self.rx_filter,
                     self.symbol_sync, self.costas, self.decoder, self.diff_decoder)
                     
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.corr_pos, self.corr_neg, self.sink)
        else:
            self.connect(self.diff_decoder, self.corr_pos, self.corr_neg, self.sink)

def build_packet(payload_bytes, mod_type='BPSK', preamble_len=32):
    access_code = digital.packet_utils.default_access_code
    ac_bits = [int(c) for c in access_code]
    
    # Unpack payload into bits
    payload_bits = []
    for b in payload_bytes:
        for i in range(7, -1, -1):
            payload_bits.append((b >> i) & 1)
            
    # Preamble bits
    if mod_type == 'BPSK':
        preamble_bits = [0, 1] * (preamble_len * 4)
    else:
        preamble_bytes = [0x33, 0xCC] * (preamble_len // 2)
        preamble_bits = []
        for b in preamble_bytes:
            for i in range(7, -1, -1):
                preamble_bits.append((b >> i) & 1)
                
    flush_bits = [0] * 256
    all_bits = preamble_bits + ac_bits + payload_bits + flush_bits
    
    tx_bytes = []
    for i in range(0, len(all_bits), 8):
        byte_val = 0
        chunk = all_bits[i:i+8]
        for b in chunk:
            byte_val = (byte_val << 1) | b
        if len(chunk) < 8:
            byte_val <<= (8 - len(chunk))
        tx_bytes.append(byte_val)
        
    return tx_bytes, len(payload_bytes)

def run_test(mod_type='ALL'):
    print("================================================================================")
    print(" [PHY2 Stage 07] Preamble & Access Code Frame Sync Test (BPSK & QPSK)           ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK'] if mod_type.upper() == 'ALL' else [mod_type.upper()]
    payload = list(b"CDP_FRAME_SYNC_TEST_PACKET_VERIFIED_1234567890")
    all_passed = True
    
    for mod in modulations:
        print(f"\n--- Testing Modulation: {mod} ---")
        tx_bytes, payload_len = build_packet(payload, mod_type=mod, preamble_len=32)
        
        tb = FrameSyncTester(tx_bytes, mod_type=mod, freq_offset=0.008, noise_volt=0.02, time_offset=1.0001)
        tb.run()
        
        tags = tb.sink.tags()
        rx_bits = list(tb.sink.data())
        
        import pmt
        sync_pos_found = any(pmt.symbol_to_string(t.key) == 'sync_pos' for t in tags)
        sync_neg_found = any(pmt.symbol_to_string(t.key) == 'sync_neg' for t in tags)
        
        print(f" Tags Detected : sync_pos={sync_pos_found}, sync_neg={sync_neg_found}")
        
        # Extract payload from first sync tag
        recovered_payload = None
        for t in tags:
            tag_name = pmt.symbol_to_string(t.key)
            if tag_name in ['sync_pos', 'sync_neg']:
                offset = t.offset
                start_bit = offset
                end_bit = start_bit + payload_len * 8
                if end_bit <= len(rx_bits):
                    extracted_bits = rx_bits[start_bit:end_bit]
                    if tag_name == 'sync_neg':
                        extracted_bits = [1 - b for b in extracted_bits]
                    rec_bytes = []
                    for i in range(0, len(extracted_bits), 8):
                        bv = 0
                        for b in extracted_bits[i:i+8]:
                            bv = (bv << 1) | b
                        rec_bytes.append(bv)
                    recovered_payload = rec_bytes
                    break
                    
        if recovered_payload is not None and bytes(recovered_payload) == bytes(payload):
            print(f" -> [PASS] Frame sync and payload verified for {mod}!")
            print(f"    Payload: {bytes(recovered_payload).decode('latin-1')}")
        else:
            print(f" -> [FAIL] Frame synchronization failed for {mod}!")
            all_passed = False
            
    print("\n================================================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 07 Test Runner")
    parser.add_argument('--mod', type=str, default='ALL', choices=['BPSK', 'QPSK', 'ALL'])
    args = parser.parse_args()
    sys.exit(run_test(args.mod))
