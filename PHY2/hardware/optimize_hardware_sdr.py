#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 SDR Hardware Live Optimization Engine
Executes automated parameter optimization sweeps directly across physical SDR Hardware
(Adalm-Pluto SDR, Nuand bladeRF, RTL-SDR) or hardware emulation profiles over the range 0.005 to 1.000 rad/sym.
Supports BPSK and QPSK with digital.TED_SIGNAL_TIMES_SLOPE_ML (y·y' TED) and Correlation Estimator.
"""

import sys
import os
import time
import math
import json
import csv
import argparse
import itertools
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes
from PHY2.hardware.sdr_blocks_helper import create_sdr_source_sink

class HardwareLiveTransceiverTrial(gr.top_block):
    def __init__(self,
                 test_payload,
                 mod_type='BPSK',
                 payload_size=64,
                 packets=10,
                 preamble_size=32,
                 sps=4,
                 alpha=0.35,
                 samp_rate=1000000,
                 fll_bw=0.0314,
                 costas_bw=0.0628,
                 sym_bw=0.025,
                 hw_type='sim',
                 uri='ip:192.168.2.1',
                 cf=433.98e6,
                 tx_gain=20,
                 rx_gain=30):
        super().__init__("Hardware_Live_Transceiver_Trial", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_mod = 2
            self.costas_order = 2
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
            self.costas_order = 4
            self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
            self.preamble_bytes = [0x33, 0xCC] * (preamble_size // 2)
            num_syms = min(preamble_size * 4, 48)
            pts = [(-1.0 - 1.0j) / math.sqrt(2), (1.0 + 1.0j) / math.sqrt(2)]
            self.training_symbols = [pts[i % 2] for i in range(num_syms)]
            
        self.hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0, 1)
        
        # Transmitter
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
        
        # Physical SDR Hardware Blocks / Channel
        if hw_type in ['pluto', 'bladerf']:
            self.hw_src, self.hw_snk, self.active_hw = create_sdr_source_sink(
                hw_type=hw_type, uri=uri, cf=cf, samp_rate=samp_rate, tx_gain=tx_gain, rx_gain=rx_gain
            )
            self.use_rf = True
        else:
            self.channel = channels.channel_model(
                noise_voltage=0.03,
                frequency_offset=0.005,
                epsilon=1.0001,
                taps=[1.0, 0.12, 0.04],
                noise_seed=42
            )
            self.use_rf = False
            
        # Receiver Chain
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
        
        self.costas = digital.costas_loop_cc(costas_bw, self.costas_order, False)
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(self.diff_mod, digital.DIFF_DIFFERENTIAL)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        self.correlator = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code, 2, 'packet_len')
        self.repack = blocks.repack_bits_bb(1, 8, 'packet_len', False, gr.GR_MSB_FIRST)
        self.crc_rx = digital.crc32_bb(True, 'packet_len', True)
        self.packet_sink = blocks.vector_sink_b()
        
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
            
        self.connect(self.correlator, self.repack, self.crc_rx, self.packet_sink)

def run_hardware_optimization(hw_type='sim', uri='ip:192.168.2.1', cf=433.98e6, tx_gain=20, rx_gain=30):
    print("================================================================================")
    print(f"   PHY2 SDR HARDWARE PARAMETER OPTIMIZATION (HW TARGET: {hw_type.upper()})      ")
    print("================================================================================")
    
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    
    modulations = ['BPSK', 'QPSK']
    
    # 0.005 to 1.000 range values
    costas_vals = [0.005, 0.015, 0.035, 0.0628, 0.100, 0.165, 0.250, 0.400, 0.600, 0.800, 1.000]
    sym_vals    = [0.005, 0.015, 0.025, 0.045, 0.075, 0.115, 0.180, 0.300, 0.500, 0.750, 1.000]
    fll_vals    = [0.005, 0.015, 0.0314, 0.055, 0.100, 0.190, 0.350, 0.600, 1.000]
    preambles   = [16, 32, 48]
    
    payload_size = 64
    packets = 10
    test_payload = [int((p * 37 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    # Slice Grid for Hardware Evaluation
    grid = list(itertools.product(modulations, fll_vals, costas_vals, [0.025], [32])) + \
           list(itertools.product(modulations, [0.0314], [0.0628], sym_vals, [32])) + \
           list(itertools.product(modulations, [0.0314], [0.0628], [0.025], preambles))
    grid = list(set(grid))
    
    print(f"Total Hardware Configuration Trials: {len(grid)} on target '{hw_type}'...")
    all_results = []
    t0 = time.time()
    
    for idx, (mod, fll, costas, sym, plen) in enumerate(grid, 1):
        try:
            tb = HardwareLiveTransceiverTrial(
                test_payload=test_payload,
                mod_type=mod,
                payload_size=payload_size,
                packets=packets,
                preamble_size=plen,
                fll_bw=fll,
                costas_bw=costas,
                sym_bw=sym,
                hw_type=hw_type,
                uri=uri,
                cf=cf,
                tx_gain=tx_gain,
                rx_gain=rx_gain
            )
            tb.run()
            rx_bytes = list(tb.packet_sink.data())
            rx_pkts = len(rx_bytes) // payload_size
            pdr = (rx_pkts / float(packets)) * 100.0
            
            matched = 0
            for p in range(rx_pkts):
                pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
                for orig_p in range(packets):
                    orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                    if pkt == orig_pkt:
                        matched += 1
                        break
        except Exception as e:
            pdr = 0.0
            matched = 0
            rx_pkts = 0
            
        lost = packets - matched
        ber = (lost / float(packets)) * 0.5
        all_results.append({
            'mod_type': mod,
            'fll_bw': fll,
            'costas_bw': costas,
            'sym_bw': sym,
            'preamble_size': plen,
            'hw_type': hw_type,
            'pdr': float(pdr),
            'ber': float(ber),
            'matched_packets': int(matched),
            'total_packets': int(packets)
        })
        
    elapsed = time.time() - t0
    print(f"[OK] Completed {len(all_results)} Hardware Trials in {elapsed:.2f}s ({len(all_results)/max(elapsed, 1e-4):.1f} sims/sec)")
    
    # Save Hardware JSON & CSV
    with open(os.path.join(results_dir, "hardware_optimization_results.json"), "w") as f:
        json.dump(all_results, f, indent=2)
        
    with open(os.path.join(results_dir, "hardware_optimization_results.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Modulation", "FLL_BW", "Costas_BW", "SymSync_BW", "PreambleSize", "HW_Target", "PDR", "BER", "MatchedPkts", "TotalPkts"])
        for r in all_results:
            writer.writerow([r['mod_type'], r['fll_bw'], r['costas_bw'], r['sym_bw'], r['preamble_size'], r['hw_type'], r['pdr'], r['ber'], r['matched_packets'], r['total_packets']])
            
    # Pinpoint optimal hardware parameters
    opt_hw = {}
    for mod in modulations:
        mod_runs = [r for r in all_results if r['mod_type'] == mod]
        ranked = sorted(mod_runs, key=lambda x: (-x['pdr'], x['ber'], x['preamble_size']))
        best = ranked[0]
        opt_hw[mod] = {
            'modulation': mod,
            'hw_target': hw_type,
            'ted_type': 'TED_SIGNAL_TIMES_SLOPE_ML (y·y\')',
            'optimal_fll_bandwidth': best['fll_bw'],
            'optimal_costas_bandwidth': best['costas_bw'],
            'optimal_symbol_sync_bandwidth': best['sym_bw'],
            'optimal_preamble_length': best['preamble_size'],
            'pdr': f"{best['pdr']:.1f}%",
            'ber': f"{best['ber']:.5f}"
        }
        
    with open(os.path.join(results_dir, "optimal_hardware_parameters.json"), "w") as f:
        json.dump(opt_hw, f, indent=2)
        
    print("\n================================================================================")
    print(f"        PINPOINTED HARDWARE OPTIMAL VALUES ({hw_type.upper()})                 ")
    print("================================================================================")
    for mod in modulations:
        p = opt_hw[mod]
        print(f"  [{mod}]")
        print(f"    -> TED Algorithm         : {p['ted_type']}")
        print(f"    -> FLL Band-Edge Loop BW : {p['optimal_fll_bandwidth']:.4f} rad/sym")
        print(f"    -> Costas Loop BW        : {p['optimal_costas_bandwidth']:.4f} rad/sym")
        print(f"    -> Symbol Sync Loop BW   : {p['optimal_symbol_sync_bandwidth']:.4f} rad/sym")
        print(f"    -> Preamble Length       : {p['optimal_preamble_length']} Bytes")
        print(f"    -> PDR / BER             : {p['pdr']} / {p['ber']}")
    print("================================================================================")
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Hardware SDR Optimizer")
    parser.add_argument('--hw', type=str, default='sim', choices=['sim', 'pluto', 'bladerf', 'rtlsdr'])
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1')
    parser.add_argument('--freq', type=float, default=433.98e6)
    parser.add_argument('--tx-gain', type=float, default=20.0)
    parser.add_argument('--rx-gain', type=float, default=30.0)
    args = parser.parse_args()
    sys.exit(run_hardware_optimization(args.hw, args.uri, args.freq, args.tx_gain, args.rx_gain))
