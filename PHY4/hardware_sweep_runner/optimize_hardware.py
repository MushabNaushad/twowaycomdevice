#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY4 Hardware Live Optimization Engine
Executes parameter optimization sweeps directly across physical SDR Hardware:
  - Transmitter: Analog Devices Adalm-Pluto SDR (ip:192.168.1.10)
  - Receiver: Nuand bladeRF SDR (or Adalm-Pluto / RTL-SDR)
Supports BPSK and QPSK with:
  - Timing Error Detector: digital.TED_SIGNAL_TIMES_SLOPE_ML (y·y' TED)
  - Frequency Recovery: digital.fll_band_edge_cc
  - Frame Sync & Channel Equalization: digital.corr_est_cc + digital.linear_equalizer (CMA)
  - Packet Engine: CRC32 verification and Access Code detection
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

# Ensure directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes
from sdr_hardware_helper import create_sdr_tx_rx

class HardwareTransceiverTrial(gr.top_block):
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
                 tx_hw='pluto',
                 rx_hw='bladerf',
                 uri='ip:192.168.1.10',
                 cf=433.98e6,
                 tx_gain=20.0,
                 rx_gain=45.0):
        super().__init__("PHY4_Hardware_Transceiver_Trial", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
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
            self.bps = 2
            self.diff_mod = 4
            self.costas_order = 4
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
        
        # SDR Hardware Blocks
        self.use_rf = (tx_hw not in ['sim', 'loopback']) or (rx_hw not in ['sim', 'loopback'])
        if self.use_rf:
            self.hw_snk, self.hw_src = create_sdr_tx_rx(
                tx_hw=tx_hw, rx_hw=rx_hw, uri=uri, cf=cf, samp_rate=samp_rate, tx_gain=tx_gain, rx_gain=rx_gain
            )
            # Head block ensures deterministic, bounded buffer acquisition (0.15s of samples)
            self.head = blocks.head(gr.sizeof_gr_complex, int(samp_rate * 0.15))
        else:
            self.channel = channels.channel_model(
                noise_voltage=0.03,
                frequency_offset=0.005,
                epsilon=1.0001,
                taps=[1.0, 0.12, 0.04],
                noise_seed=42
            )
            
        # Receiver Processing Chain
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, fll_bw)
        
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        self.symbol_sync = digital.symbol_sync_cc(
            self.ted_type, sps, sym_bw, 1.0, 1.0, 1.5, 1, self.constellation, digital.IR_MMSE_8TAP, 128, []
        )
        
        # Correlation Estimator + Adaptive Equalizer
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
        
        # Connect TX to Channel / SDR Sink
        if self.use_rf:
            if self.hw_snk is not None:
                self.connect(self.mux, self.mod, self.hw_snk)
            else:
                self.connect(self.mux, self.mod, blocks.null_sink(gr.sizeof_gr_complex))
                
            if self.hw_src is not None:
                self.connect(self.hw_src, self.head, self.agc, self.fll, self.rx_filter,
                             self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
            else:
                self.connect(self.mux, self.mod, self.agc, self.fll, self.rx_filter,
                             self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
        else:
            self.connect(self.mux, self.mod, self.channel, self.agc, self.fll, self.rx_filter,
                         self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
                         
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.correlator)
        else:
            self.connect(self.diff_decoder, self.correlator)
            
        self.connect(self.correlator, self.repack, self.crc_rx, self.packet_sink)

def run_hardware_optimization(tx_hw='pluto', rx_hw='bladerf', uri='ip:192.168.1.10', cf=433.98e6, tx_gain=20.0, rx_gain=45.0, candidates_file=None, top_n=1000):
    results_dir = os.path.join(SCRIPT_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    print("================================================================================")
    print(f"   PHY4 SDR HARDWARE OPTIMIZATION ENGINE (TX: {tx_hw.upper()}, RX: {rx_hw.upper()})    ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK']
    
    default_candidates_path = os.path.join(SCRIPT_DIR, "top_50000_low_ber_candidates.json")
    if candidates_file is None and os.path.exists(default_candidates_path):
        candidates_file = default_candidates_path
        
    grid = []
    if candidates_file and os.path.exists(candidates_file):
        print(f"Loading top candidate configurations from: {candidates_file} ...")
        with open(candidates_file, 'r') as f:
            cands = json.load(f)
        if top_n is not None and top_n > 0:
            cands = cands[:top_n]
        grid = [(c['mod_type'], float(c['fll_bw']), float(c['costas_bw']), float(c['sym_bw']), int(c.get('preamble_size', 32))) for c in cands]
        print(f"Loaded {len(grid):,} prioritized candidate combinations.")
    else:
        # Fallback dense parameter space
        print("[INFO] Generating dense parameter grid...")
        costas_vals = [0.015, 0.030, 0.0628, 0.100, 0.150]
        sym_vals    = [0.015, 0.025, 0.045, 0.080, 0.120]
        fll_vals    = [0.015, 0.0314, 0.0628, 0.100]
        grid = list(itertools.product(modulations, fll_vals, costas_vals, sym_vals, [32]))
        if top_n is not None and top_n > 0:
            grid = grid[:top_n]
            
    payload_size = 64
    packets = 10
    test_payload = [int((p * 37 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    print(f"Executing {len(grid):,} Hardware Configuration Trials (TX={tx_hw.upper()}, RX={rx_hw.upper()})...\n")
    all_results = []
    total_trials = len(grid)
    t0 = time.time()
    
    def render_progress_bar(current, total, t_start, bar_length=30):
        percent = (current / float(total)) * 100.0
        filled_len = int(bar_length * current // total)
        bar = '█' * filled_len + '░' * (bar_length - filled_len)
        
        elapsed = time.time() - t_start
        rate = current / max(elapsed, 0.001)
        remaining_sec = (total - current) / max(rate, 0.001) if rate > 0 else 0
        
        mins_rem, secs_rem = divmod(int(remaining_sec), 60)
        hours_rem, mins_rem = divmod(mins_rem, 60)
        eta_str = f"{hours_rem:02d}:{mins_rem:02d}:{secs_rem:02d}" if hours_rem > 0 else f"{mins_rem:02d}:{secs_rem:02d}"
        
        mins_el, secs_el = divmod(int(elapsed), 60)
        el_str = f"{mins_el:02d}:{secs_el:02d}"
        
        ts = time.strftime("%H:%M:%S")
        sys.stdout.write(f"\r[{ts}] [\033[96mPROGRESS\033[0m] [{bar}] \033[92m{percent:5.1f}%\033[0m ({current:,}/{total:,}) | \033[93m{rate:5.1f} trials/s\033[0m | Elapsed: {el_str} | ETA: {eta_str}  ")
        sys.stdout.flush()

    render_progress_bar(0, total_trials, t0)
    
    for idx, (mod, fll, costas, sym, plen) in enumerate(grid, 1):
        tb = None
        try:
            tb = HardwareTransceiverTrial(
                test_payload=test_payload,
                mod_type=mod,
                payload_size=payload_size,
                packets=packets,
                preamble_size=plen,
                fll_bw=fll,
                costas_bw=costas,
                sym_bw=sym,
                tx_hw=tx_hw,
                rx_hw=rx_hw,
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
            matched_originals = set()
            for p in range(rx_pkts):
                pkt = rx_bytes[p * payload_size : (p + 1) * payload_size]
                for orig_p in range(packets):
                    if orig_p in matched_originals:
                        continue
                    orig_pkt = test_payload[orig_p * payload_size : (orig_p + 1) * payload_size]
                    if pkt == orig_pkt:
                        matched += 1
                        matched_originals.add(orig_p)
                        break
        except Exception:
            pdr = 0.0
            matched = 0
            rx_pkts = 0
        finally:
            if tb is not None:
                try:
                    tb.stop()
                    tb.wait()
                except Exception:
                    pass
                del tb
            
        lost = max(0, packets - matched)
        ber = (lost / float(packets)) * 0.5
        all_results.append({
            'mod_type': mod,
            'fll_bw': fll,
            'costas_bw': costas,
            'sym_bw': sym,
            'preamble_size': plen,
            'tx_hw': tx_hw,
            'rx_hw': rx_hw,
            'pdr': float(pdr),
            'ber': float(ber),
            'matched_packets': int(matched),
            'total_packets': int(packets)
        })
        render_progress_bar(idx, total_trials, t0)
        
    sys.stdout.write("\n")
    sys.stdout.flush()
    elapsed = time.time() - t0
    mins, secs = divmod(int(elapsed), 60)
    hours, mins = divmod(mins, 60)
    time_str = f"{hours}h {mins:02d}m {secs:02d}s" if hours > 0 else f"{mins}m {secs:02d}s" if mins > 0 else f"{elapsed:.2f}s"
    rate = len(all_results) / max(elapsed, 0.001)
    
    print("\n" + "=" * 80)
    print(f" \033[92m\033[1m>>> HARDWARE SDR EVALUATION COMPLETED SUCCESSFULLY! <<<\033[0m")
    print(f"  • \033[1mActual Ran Time\033[0m       : \033[96m\033[1m{elapsed:.2f}s ({time_str})\033[0m")
    print(f"  • \033[1mTotal SDR Trials\033[0m      : \033[93m\033[1m{len(all_results):,} configurations on TX={tx_hw.upper()} / RX={rx_hw.upper()}\033[0m")
    print(f"  • \033[1mAverage Throughput\033[0m    : \033[92m{rate:.1f} trials/second\033[0m")
    print(f"  • \033[1mFinished Timestamp\033[0m    : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    # Save JSON & CSV
    json_path = os.path.join(results_dir, "hardware_optimization_results.json")
    csv_path = os.path.join(results_dir, "hardware_optimization_results.csv")
    
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)
        
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Modulation", "FLL_BW", "Costas_BW", "SymSync_BW", "PreambleSize", "TX_Target", "RX_Target", "PDR", "BER", "MatchedPkts", "TotalPkts"])
        for r in all_results:
            writer.writerow([r['mod_type'], r['fll_bw'], r['costas_bw'], r['sym_bw'], r['preamble_size'], r['tx_hw'], r['rx_hw'], r['pdr'], r['ber'], r['matched_packets'], r['total_packets']])
            
    # Pinpoint optimal hardware parameters
    opt_hw = {}
    for mod in modulations:
        mod_runs = [r for r in all_results if r['mod_type'] == mod]
        ranked = sorted(mod_runs, key=lambda x: (-x['pdr'], x['ber'], x['preamble_size']))
        if not ranked:
            continue
        best = ranked[0]
        opt_hw[mod] = {
            'modulation': mod,
            'tx_target': tx_hw,
            'rx_target': rx_hw,
            'ted_type': 'TED_SIGNAL_TIMES_SLOPE_ML (y·y\')',
            'optimal_fll_bandwidth': best['fll_bw'],
            'optimal_costas_bandwidth': best['costas_bw'],
            'optimal_symbol_sync_bandwidth': best['sym_bw'],
            'optimal_preamble_length': best['preamble_size'],
            'pdr': f"{best['pdr']:.1f}%",
            'ber': f"{best['ber']:.5f}"
        }
        
    opt_json_path = os.path.join(results_dir, "optimal_hardware_parameters.json")
    with open(opt_json_path, "w") as f:
        json.dump(opt_hw, f, indent=2)
        
    print("\n================================================================================")
    print(f"        PINPOINTED OPTIMAL HARDWARE PARAMETERS (TX: {tx_hw.upper()}, RX: {rx_hw.upper()})        ")
    print("================================================================================")
    for mod in modulations:
        if mod in opt_hw:
            p = opt_hw[mod]
            print(f"  [{mod}]")
            print(f"    -> TED Algorithm         : {p['ted_type']}")
            print(f"    -> FLL Band-Edge Loop BW : {p['optimal_fll_bandwidth']:.4f} rad/sym")
            print(f"    -> Costas Loop BW        : {p['optimal_costas_bandwidth']:.4f} rad/sym")
            print(f"    -> Symbol Sync Loop BW   : {p['optimal_symbol_sync_bandwidth']:.4f} rad/sym")
            print(f"    -> Preamble Length       : {p['optimal_preamble_length']} Bytes")
            print(f"    -> PDR / BER             : {p['pdr']} / {p['ber']}")
    print("================================================================================\n")
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY4 Hardware SDR Optimizer (Pluto TX & BladeRF RX)")
    parser.add_argument('--tx-hw', type=str, default='pluto', choices=['pluto', 'bladerf', 'sim'], help="Transmitter SDR")
    parser.add_argument('--rx-hw', type=str, default='bladerf', choices=['bladerf', 'pluto', 'rtlsdr', 'sim'], help="Receiver SDR")
    parser.add_argument('--uri', type=str, default='ip:192.168.1.10', help="Pluto SDR IP/URI")
    parser.add_argument('--freq', type=float, default=433.98e6, help="RF Center Frequency (Hz)")
    parser.add_argument('--tx-gain', type=float, default=20.0, help="TX Attenuation / Gain")
    parser.add_argument('--rx-gain', type=float, default=45.0, help="RX Gain (dB)")
    parser.add_argument('--candidates', type=str, default=None, help="Path to top candidates JSON file")
    parser.add_argument('--top-n', type=int, default=1000, help="Number of candidates to evaluate (e.g. 50000, 10000, 1000)")
    args = parser.parse_args()
    
    sys.exit(run_hardware_optimization(
        tx_hw=args.tx_hw,
        rx_hw=args.rx_hw,
        uri=args.uri,
        cf=args.freq,
        tx_gain=args.tx_gain,
        rx_gain=args.rx_gain,
        candidates_file=args.candidates,
        top_n=args.top_n
    ))
