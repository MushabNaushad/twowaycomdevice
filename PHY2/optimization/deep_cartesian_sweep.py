#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Optimization Suite - Ultra-Deep Software & Hardware Parameter Optimizer
Executes high-density Cartesian trials across 0.005 to 1.000 rad/sym loop bandwidths
for FLL Band-Edge, Costas Loop, and Symbol Synchronizer across BPSK & QPSK.
Uses digital.TED_SIGNAL_TIMES_SLOPE_ML (y·y' TED) and Correlation Estimator + Adaptive Equalizer.
"""

import sys
import os
import time
import math
import json
import csv
import gc
import itertools
from multiprocessing import Pool, cpu_count
import subprocess
import argparse
import numpy as np

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, WORKSPACE_ROOT)

# Configure GNU Radio buffer allocation to use POSIX mmap tmpfile instead of SysV IPC shmget.
# Must happen BEFORE importing gnuradio.
os.environ['HOME'] = WORKSPACE_ROOT
os.environ['GR_CONF_VMCIRCBUF_DEFAULT_FACTORY'] = 'gr::vmcircbuf_mmap_tmpfile_factory'
os.environ['GR_CONF_vmcircbuf_default_factory'] = 'gr::vmcircbuf_mmap_tmpfile_factory'

# Write proper GNU Radio .conf prefs (INI format - what GR actually reads)
gnuradio_prefs_dir = os.path.join(WORKSPACE_ROOT, '.gnuradio')
os.makedirs(gnuradio_prefs_dir, exist_ok=True)
conf_file = os.path.join(gnuradio_prefs_dir, 'config.conf')
try:
    with open(conf_file, 'w') as f:
        f.write('[DEFAULT]\n')
        f.write('vmcircbuf_default_factory = gr::vmcircbuf_mmap_tmpfile_factory\n')
except Exception:
    pass

from gnuradio import gr, digital, blocks, filter, channels, analog
from gnuradio.filter import firdes

def cleanup_stale_ipc():
    """Release any orphaned System V IPC shared memory segments."""
    try:
        res = subprocess.run(['ipcs', '-m'], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit() and ('dest' in line or '0x00000000' in line):
                shmid = parts[1]
                subprocess.run(['ipcrm', '-m', shmid], capture_output=True)
    except Exception:
        pass

cleanup_stale_ipc()

class DeepTransceiverTrial(gr.top_block):
    def __init__(self,
                 test_payload,
                 mod_type='BPSK',
                 payload_size=64,
                 packets=10,
                 preamble_size=32,
                 sps=4,
                 alpha=0.35,
                 samp_rate=32000,
                 fll_bw=0.0314,
                 costas_bw=0.0628,
                 sym_bw=0.025,
                 noise_volt=0.0,
                 freq_offset=0.0,
                 time_offset=1.0,
                 multipath_taps=[1.0, 0.15, 0.05]):
        super().__init__("Deep_Transceiver_Trial", catch_exceptions=True)
        
        self.mod_type = mod_type.upper()
        self.ted_type = digital.TED_SIGNAL_TIMES_SLOPE_ML
        
        if self.mod_type == 'BPSK':
            self.constellation = digital.constellation_bpsk().base()
            self.arity = 2
            self.bps = 1
            self.diff_mod = 2
            self.costas_order = 2
            self.preamble_bytes = [0x55] * preamble_size
            num_syms = max(4, min(preamble_size * 8, 48))
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
            qpsk_pattern = [0x33, 0xCC] * (preamble_size // 2)
            if preamble_size % 2 != 0:
                qpsk_pattern.append(0x33)
            self.preamble_bytes = qpsk_pattern if qpsk_pattern else [0x33, 0xCC]
            num_syms = max(4, min(preamble_size * 4, 48))
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
        
        # Channel Model with Impairments
        self.channel = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=freq_offset,
            epsilon=time_offset,
            taps=multipath_taps,
            noise_seed=42
        )
        
        # Receiver DSP Chain
        self.agc = analog.agc_cc(1e-2, 1.0, 1.0)
        self.fll = digital.fll_band_edge_cc(sps, alpha, 2 * sps + 1, fll_bw)
        
        ntaps = 32 * sps
        rcc_taps = firdes.root_raised_cosine(1.0, samp_rate, samp_rate / sps, alpha, ntaps)
        self.rx_filter = filter.fir_filter_ccf(1, rcc_taps)
        
        # y·y' Timing Error Detector
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
        
        # Correlation Estimator + Linear Adaptive Equalizer
        mark_delay = len(self.training_symbols) - 1
        self.corr_est = digital.corr_est_cc(self.training_symbols, 1, mark_delay, 0.8)
        adpt_alg = digital.adaptive_algorithm_cma(self.constellation, 0.001, 1).base()
        self.equalizer = digital.linear_equalizer(11, 1, adpt_alg, True, self.training_symbols, 'corr_est')
        
        # Costas Loop
        self.costas = digital.costas_loop_cc(costas_bw, self.costas_order, False)
        
        # Decoder & Repacking
        self.decoder = digital.constellation_decoder_cb(self.constellation)
        self.diff_decoder = digital.diff_decoder_bb(self.diff_mod)
        
        if self.bps > 1:
            self.mapper = digital.map_bb([0, 1, 3, 2])
            self.unpacker = blocks.unpack_k_bits_bb(self.bps)
            
        self.correlator = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code, 2, 'packet_len')
        self.repack = blocks.repack_bits_bb(1, 8, 'packet_len', False, gr.GR_MSB_FIRST)
        self.crc_rx = digital.crc32_bb(True, 'packet_len', True)
        self.packet_sink = blocks.vector_sink_b()
        
        # Connect Graph
        self.connect(self.preamble_src, self.s2ts_preamble, (self.mux, 0))
        self.connect(self.src, self.s2ts_payload, self.crc_tx)
        self.connect(self.crc_tx, self.formatter, (self.mux, 1))
        self.connect((self.crc_tx, 0), (self.mux, 2))
        
        self.connect(self.mux, self.mod, self.channel, self.agc, self.fll, self.rx_filter,
                     self.symbol_sync, self.corr_est, self.equalizer, self.costas, self.decoder, self.diff_decoder)
                     
        if self.bps > 1:
            self.connect(self.diff_decoder, self.mapper, self.unpacker, self.correlator)
        else:
            self.connect(self.diff_decoder, self.correlator)
            
        self.connect(self.correlator, self.repack, self.crc_rx, self.packet_sink)

def run_deep_trial_worker(args):
    mod_type, fll_bw, costas_bw, sym_bw, plen, nv, fo, to, platform_mode, packets, payload_size = args
    test_payload = [int((p * 23 + i) % 256) for p in range(packets) for i in range(payload_size)]
    
    multipath = [1.0, 0.20, 0.08] if platform_mode == 'software' else [1.0, 0.05]
    
    t0 = time.time()
    pdr = 0.0
    matched_count = 0
    received_packets = 0
    tb = None
    try:
        tb = DeepTransceiverTrial(
            test_payload=test_payload,
            mod_type=mod_type,
            payload_size=payload_size,
            packets=packets,
            preamble_size=plen,
            fll_bw=fll_bw,
            costas_bw=costas_bw,
            sym_bw=sym_bw,
            noise_volt=nv,
            freq_offset=fo,
            time_offset=to,
            multipath_taps=multipath
        )
        tb.run()
        rx_bytes = list(tb.packet_sink.data())
        received_packets = len(rx_bytes) // payload_size
        pdr = (received_packets / float(packets)) * 100.0
        
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
    except Exception:
        pdr = 0.0
        matched_count = 0
        received_packets = 0
    finally:
        if tb is not None:
            try:
                tb.stop()
                tb.wait()
                tb.disconnect_all()
            except Exception:
                pass
            del tb
        
    elapsed = time.time() - t0
    lost = max(0, packets - matched_count)  # Guard against negative
    lost_ber = (lost / float(packets)) * 0.5
    
    if nv > 0.0:
        snr = 1.0 / (2.0 * (nv ** 2))
        ebno = snr * (4.0 if mod_type == 'BPSK' else 2.0)
        theory_ber = 0.5 * math.erfc(math.sqrt(max(ebno, 0.0)))
        ber = max(theory_ber, lost_ber)
    else:
        ber = lost_ber
        
    return {
        'mod_type': mod_type,
        'fll_bw': round(float(fll_bw), 4),
        'costas_bw': round(float(costas_bw), 4),
        'sym_bw': round(float(sym_bw), 4),
        'preamble_size': int(plen),
        'noise_volt': round(float(nv), 4),
        'freq_offset': round(float(fo), 4),
        'time_offset': round(float(to), 6),
        'platform_mode': platform_mode,
        'pdr': float(pdr),
        'ber': float(ber),
        'matched_packets': int(matched_count),
        'total_packets': int(packets),
        'elapsed_sec': float(elapsed)
    }

def generate_range_steps(min_val, max_val, step_val):
    vals = []
    curr = min_val
    while curr <= max_val + (step_val * 0.1):
        vals.append(round(curr, 4))
        curr += step_val
    return vals

def worker_init():
    """Initialize each worker process with correct env vars."""
    os.environ['HOME'] = WORKSPACE_ROOT
    os.environ['GR_CONF_VMCIRCBUF_DEFAULT_FACTORY'] = 'gr::vmcircbuf_mmap_tmpfile_factory'
    os.environ['GR_CONF_vmcircbuf_default_factory'] = 'gr::vmcircbuf_mmap_tmpfile_factory'

def execute_ultra_deep_optimization(output_dir, workers=None, preset="fast", custom_config=None):
    os.makedirs(output_dir, exist_ok=True)
    cleanup_stale_ipc()
    
    print("================================================================================")
    print(f"  PHY2 PARAMETER OPTIMIZATION SWEEPER [PRESET: {preset.upper()}]                ")
    print("================================================================================")
    
    modulations = ['BPSK', 'QPSK']
    
    if preset == "fast":
        # ~12,000 Focused Trials (High-probability optimal zone, ~5-8s execution)
        fll_vals = [0.020, 0.0314, 0.050, 0.0628]
        costas_vals = generate_range_steps(0.020, 0.120, 0.005) # 21 values
        sym_vals = generate_range_steps(0.005, 0.140, 0.002)    # 68 values
        preambles = [16, 32, 64]
        noise_volts = [0.0, 0.03, 0.08]
        freq_offsets = [-0.010, 0.0, +0.010]
        time_offsets = [0.9999, 1.0, 1.0001]
        
        grid_core = list(itertools.product(
            modulations, fll_vals, costas_vals, sym_vals, [32], [0.0], [0.0], [1.0], ['software'], [5], [32]
        ))
        grid_preamble = list(itertools.product(
            modulations, [0.0314, 0.0628], [0.0628], [0.025, 0.055], preambles, noise_volts, [0.005], [1.0001], ['software'], [5], [32]
        ))
        grid_drift = list(itertools.product(
            modulations, [0.0314], [0.0628], [0.025, 0.055], [32], [0.03], freq_offsets, time_offsets, ['software'], [5], [32]
        ))
        combined_trials = list(set(grid_core + grid_preamble + grid_drift))

    elif preset == "standard":
        # ~52,000 Trials (Broader exploration, ~20-25s execution)
        fll_vals = [0.010, 0.020, 0.0314, 0.040, 0.050, 0.0628, 0.080, 0.100] # 8 values
        costas_vals = generate_range_steps(0.010, 0.200, 0.005) # 39 values
        sym_vals = generate_range_steps(0.002, 0.160, 0.002)    # 80 values
        preambles = [4, 8, 16, 24, 32, 48, 64]
        noise_volts = [0.0, 0.02, 0.05, 0.08, 0.15, 0.25]
        freq_offsets = [-0.020, -0.010, 0.0, +0.010, +0.020]
        time_offsets = [0.9995, 0.9999, 1.0, 1.0001, 1.0005]
        
        grid_core = list(itertools.product(
            modulations, fll_vals, costas_vals, sym_vals, [32], [0.0], [0.0], [1.0], ['software'], [5], [32]
        ))
        grid_preamble = list(itertools.product(
            modulations, [0.0314, 0.0628, 0.100], [0.030, 0.0628, 0.100], [0.025, 0.055], preambles, noise_volts, [0.005], [1.0001], ['software'], [5], [32]
        ))
        grid_drift = list(itertools.product(
            modulations, [0.0314, 0.0628], [0.0628], [0.025, 0.055, 0.115], [32], [0.03], freq_offsets, time_offsets, ['software'], [5], [32]
        ))
        combined_trials = list(set(grid_core + grid_preamble + grid_drift))

    elif preset == "custom" and custom_config:
        f_min, f_max, f_step = custom_config.get("fll", (0.01, 0.10, 0.01))
        c_min, c_max, c_step = custom_config.get("costas", (0.02, 0.15, 0.01))
        s_min, s_max, s_step = custom_config.get("sym", (0.005, 0.15, 0.002))
        
        fll_vals = generate_range_steps(f_min, f_max, f_step)
        costas_vals = generate_range_steps(c_min, c_max, c_step)
        sym_vals = generate_range_steps(s_min, s_max, s_step)
        preambles = custom_config.get("preambles", [16, 32, 64])
        
        combined_trials = list(itertools.product(
            modulations, fll_vals, costas_vals, sym_vals, preambles, [0.0], [0.0], [1.0], ['software'], [5], [32]
        ))
    else:
        # Exhaustive Full Cartesian Grid (700,000+ Trials)
        steps_001 = [round(i * 0.001, 4) for i in range(1, 1001)]
        fll_dense = [0.001, 0.005, 0.010, 0.020, 0.0314, 0.040, 0.050, 0.0628, 0.080, 0.100, 0.150, 0.200, 0.300, 0.500, 1.000]
        costas_dense = [
            0.001, 0.005, 0.010, 0.020, 0.030, 0.040, 0.050, 0.055, 0.060, 0.0628, 0.070, 0.080, 0.090, 0.100,
            0.120, 0.150, 0.200, 0.250, 0.350, 0.500, 0.750, 1.000
        ]
        preambles_all  = [2, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64]
        noise_volts    = [0.0, 0.02, 0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.50]
        freq_offsets   = [-0.030, -0.020, -0.010, 0.0, +0.010, +0.020, +0.030]
        time_offsets   = [0.9990, 0.9995, 0.9999, 1.0, 1.0001, 1.0005, 1.0010]
        platforms      = ['software', 'hardware']
        
        grid_001_sym = list(itertools.product(
            modulations, fll_dense, costas_dense, steps_001, [32], [0.0], [0.0], [1.0], ['software'], [5], [32]
        ))
        grid_001_costas = list(itertools.product(
            modulations, [0.0314, 0.040, 0.100], steps_001, [0.010, 0.025, 0.055, 0.115], [32], [0.0], [0.0], [1.0], ['software'], [5], [32]
        ))
        grid_001_fll = list(itertools.product(
            modulations, steps_001, [0.050, 0.0628, 0.100], [0.025], [32], [0.02], [-0.010, 0.0, +0.010], [1.0], ['software'], [5], [32]
        ))
        grid_preamble_noise = list(itertools.product(
            modulations, [0.0314, 0.040, 0.100], [0.050, 0.0628], [0.025, 0.115], preambles_all, noise_volts, [0.005], [1.0001], platforms, [5], [32]
        ))
        grid_hw_drift = list(itertools.product(
            modulations, [0.0314, 0.100], [0.0628], [0.010, 0.025, 0.055, 0.115, 0.250], [32], [0.03], [0.005], time_offsets, platforms, [5], [32]
        ))
        combined_trials = list(set(grid_001_sym + grid_001_costas + grid_001_fll + grid_preamble_noise + grid_hw_drift))
    
    total_trials = len(combined_trials)
    SEGMENT_SIZE = 50000
    num_segments = math.ceil(total_trials / float(SEGMENT_SIZE))
    
    print(f"Total Unique Parameter Trials Generated: {total_trials:,}")
    if num_segments > 1:
        print(f"Executing in {num_segments} sequential segments (Maximum {SEGMENT_SIZE:,} trials per segment)...")
    
    num_workers = workers if workers is not None else max(1, min(cpu_count(), 8))
    print(f"Launching parallel execution on {num_workers} CPU workers with process recycling...")
    
    def render_progress_bar(current, total, t_start, seg_info="", bar_length=30):
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
        seg_tag = f" {seg_info}" if seg_info else ""
        sys.stdout.write(f"\r[{ts}] [\033[96mPROGRESS\033[0m]{seg_tag} [{bar}] \033[92m{percent:5.1f}%\033[0m ({current:,}/{total:,}) | \033[93m{rate:6.1f} trials/s\033[0m | Elapsed: {el_str} | ETA: {eta_str}  ")
        sys.stdout.flush()

    def merge_and_save_dataset(out_dir, new_records):
        csv_path = os.path.join(out_dir, "deep_sweep_results.csv")
        json_path = os.path.join(out_dir, "deep_sweep_results.json")
        records_map = {}
        
        # 1. Load existing records (to append / update, not replace)
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    existing = json.load(f)
                for r in existing:
                    key = (
                        r['mod_type'],
                        f"{float(r['fll_bw']):.4f}",
                        f"{float(r['costas_bw']):.4f}",
                        f"{float(r['sym_bw']):.4f}",
                        int(r.get('preamble_size', 32)),
                        f"{float(r.get('noise_volt', 0.0)):.4f}",
                        f"{float(r.get('freq_offset', 0.0)):.4f}",
                        f"{float(r.get('time_offset', 1.0)):.6f}",
                        r.get('platform_mode', 'software')
                    )
                    records_map[key] = r
            except Exception as e:
                print(f"\n[WARN] Notice reading existing JSON dataset: {e}")

        # 2. Merge newly simulated records
        for r in new_records:
            key = (
                r['mod_type'],
                f"{float(r['fll_bw']):.4f}",
                f"{float(r['costas_bw']):.4f}",
                f"{float(r['sym_bw']):.4f}",
                int(r.get('preamble_size', 32)),
                f"{float(r.get('noise_volt', 0.0)):.4f}",
                f"{float(r.get('freq_offset', 0.0)):.4f}",
                f"{float(r.get('time_offset', 1.0)):.6f}",
                r.get('platform_mode', 'software')
            )
            records_map[key] = r

        merged = list(records_map.values())
        
        # 3. Write cumulative CSV
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                'mod_type', 'fll_bw', 'costas_bw', 'sym_bw', 'preamble_size',
                'noise_volt', 'freq_offset', 'time_offset', 'platform_mode',
                'pdr', 'ber', 'matched_packets', 'total_packets', 'elapsed_sec'
            ])
            writer.writeheader()
            writer.writerows(merged)
            
        # 4. Write cumulative JSON
        with open(json_path, "w") as f:
            json.dump(merged, f, indent=2)
            
        # Also sync to adapted_original results
        adapted_dir = os.path.join(out_dir, "../../adapted_original/results")
        if os.path.exists(adapted_dir):
            try:
                with open(os.path.join(adapted_dir, "ultra_fine_sweep_results.json"), "w") as f:
                    json.dump(merged, f, indent=2)
                with open(os.path.join(adapted_dir, "ultra_fine_sweep_results.csv"), "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'mod_type', 'fll_bw', 'costas_bw', 'sym_bw', 'preamble_size',
                        'noise_volt', 'freq_offset', 'time_offset', 'platform_mode',
                        'pdr', 'ber', 'matched_packets', 'total_packets', 'elapsed_sec'
                    ])
                    writer.writeheader()
                    writer.writerows(merged)
            except Exception:
                pass
                
        return merged

    all_current_results = []
    chunk_size = 100
    update_step = 100
    overall_completed = 0
    
    t_start = time.time()
    render_progress_bar(0, total_trials, t_start)
    
    for seg_idx in range(num_segments):
        seg_trials = combined_trials[seg_idx * SEGMENT_SIZE : (seg_idx + 1) * SEGMENT_SIZE]
        seg_tag = f"[Seg {seg_idx+1}/{num_segments}]" if num_segments > 1 else ""
        
        with Pool(processes=num_workers, initializer=worker_init, maxtasksperchild=50) as pool:
            for idx, res in enumerate(pool.imap_unordered(run_deep_trial_worker, seg_trials, chunksize=chunk_size), start=1):
                all_current_results.append(res)
                overall_completed += 1
                if overall_completed % update_step == 0 or overall_completed == total_trials:
                    render_progress_bar(overall_completed, total_trials, t_start, seg_info=seg_tag)
                    
        # Incremental persist after each segment finishes:
        merge_and_save_dataset(output_dir, all_current_results)
        
        # Aggressive cleanup between segments to prevent IPC exhaustion
        gc.collect()
        cleanup_stale_ipc()
                
    sys.stdout.write("\n")
    sys.stdout.flush()
    t_exec = time.time() - t_start
    mins, secs = divmod(int(t_exec), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        time_str = f"{hours}h {mins:02d}m {secs:02d}s"
    elif mins > 0:
        time_str = f"{mins}m {secs:02d}s"
    else:
        time_str = f"{t_exec:.2f}s"
        
    sim_rate = len(all_current_results) / max(t_exec, 0.001)
    
    # Merge and get final accumulated dataset
    all_cumulative_records = merge_and_save_dataset(output_dir, all_current_results)
    
    print("\n" + "=" * 80)
    print(f" \033[92m\033[1m>>> SIMULATION EXECUTION COMPLETED SUCCESSFULLY! <<<\033[0m")
    print(f"  • \033[1mActual Ran Time (This Run)\033[0m  : \033[96m\033[1m{t_exec:.2f} seconds ({time_str})\033[0m")
    print(f"  • \033[1mNew Trials Evaluated\033[0m        : \033[93m\033[1m{len(all_current_results):,} parameter combinations\033[0m")
    print(f"  • \033[1mTotal Cumulative Dataset\033[0m    : \033[92m\033[1m{len(all_cumulative_records):,} total records preserved in CSV/JSON\033[0m")
    print(f"  • \033[1mAverage Throughput\033[0m          : \033[92m{sim_rate:.1f} trials/second\033[0m across {num_workers} CPU workers")
    print(f"  • \033[1mFinished Timestamp\033[0m          : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    # Save sweep metadata
    metadata = {
        "preset": preset,
        "new_trials": len(all_current_results),
        "cumulative_trials": len(all_cumulative_records),
        "elapsed_sec": round(t_exec, 2),
        "formatted_runtime": time_str,
        "throughput_trials_per_sec": round(sim_rate, 1),
        "workers": num_workers,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(os.path.join(output_dir, "sweep_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
            
    # Rank & Pinpoint Global Optimal Parameters (Using cumulative dataset)
    optimal_pinpoint = {}
    for mod in modulations:
        mod_runs = [r for r in all_cumulative_records if r['mod_type'] == mod]
        config_map = {}
        for r in mod_runs:
            key = (r['fll_bw'], r['costas_bw'], r['sym_bw'], r['preamble_size'])
            if key not in config_map: config_map[key] = []
            config_map[key].append(r)
            
        ranked = []
        for (fll, costas, sym, plen), runs in config_map.items():
            avg_pdr = np.mean([x['pdr'] for x in runs])
            avg_ber = np.mean([x['ber'] for x in runs])
            score = avg_pdr - (avg_ber * 100.0) - (plen * 0.02)
            ranked.append({
                'fll_bw': fll,
                'costas_bw': costas,
                'sym_bw': sym,
                'preamble_size': plen,
                'avg_pdr': float(avg_pdr),
                'avg_ber': float(avg_ber),
                'score': float(score)
            })
        ranked.sort(key=lambda x: -x['score'])
        if not ranked:
            optimal_pinpoint[mod] = {'modulation': mod, 'ted_type': 'TED_SIGNAL_TIMES_SLOPE_ML', 'optimal_fll_bandwidth': 0.0314, 'optimal_costas_bandwidth': 0.0628, 'optimal_symbol_sync_bandwidth': 0.025, 'optimal_preamble_length': 32, 'average_pdr': '0.0%', 'average_ber': '0.50000'}
            continue
        best = ranked[0]
        optimal_pinpoint[mod] = {
            'modulation': mod,
            'ted_type': 'TED_SIGNAL_TIMES_SLOPE_ML (y·y\')',
            'optimal_fll_bandwidth': best['fll_bw'],
            'optimal_costas_bandwidth': best['costas_bw'],
            'optimal_symbol_sync_bandwidth': best['sym_bw'],
            'optimal_preamble_length': best['preamble_size'],
            'average_pdr': f"{best['avg_pdr']:.1f}%",
            'average_ber': f"{best['avg_ber']:.5f}",
            'top_5_configurations': ranked[:5]
        }
        
    with open(os.path.join(output_dir, "pinpoint_optimal_parameters.json"), "w") as f:
        json.dump(optimal_pinpoint, f, indent=2)
        
    print("\n================================================================================")
    print("      PINPOINTED OPTIMAL VALUES SUMMARY (0.005 TO 1.000 FULL RANGE)             ")
    print("================================================================================")
    for mod in modulations:
        p = optimal_pinpoint[mod]
        print(f"  [{mod}]")
        print(f"    -> TED Algorithm         : {p['ted_type']}")
        print(f"    -> FLL Band-Edge Loop BW : {p['optimal_fll_bandwidth']:.4f} rad/sym")
        print(f"    -> Costas Loop BW        : {p['optimal_costas_bandwidth']:.4f} rad/sym")
        print(f"    -> Symbol Sync Loop BW   : {p['optimal_symbol_sync_bandwidth']:.4f} rad/sym")
        print(f"    -> Preamble Length       : {p['optimal_preamble_length']} Bytes")
        print(f"    -> Average PDR / BER     : {p['average_pdr']} / {p['average_ber']}")
    print("================================================================================")
    
    return all_cumulative_records, optimal_pinpoint

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Ultra-Deep Cartesian Sweeper")
    parser.add_argument('--workers', type=int, default=None, help="Number of CPU workers")
    parser.add_argument('--output-dir', type=str, default=None, help="Results output directory")
    args = parser.parse_args()
    
    out_d = args.output_dir if args.output_dir else os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    execute_ultra_deep_optimization(out_d, workers=args.workers)
