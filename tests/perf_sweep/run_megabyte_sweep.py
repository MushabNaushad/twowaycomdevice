#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_megabyte_sweep.py
=====================
Executes GNU Radio parameter test for a single (m, mtu) under Megabyte-scale continuous load.
"""

import sys, os, time, pmt, threading, json
from PyQt5 import Qt, QtCore
from gnuradio import qtgui, blocks, gr, transport

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST10N_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'test_10node')
sys.path.insert(0, TEST10N_DIR)
os.chdir(TEST10N_DIR)

import test_10node_shared_bus as shared_bus

# ─── Collector block for recording completed payload deliveries ───────────────
class ReceiverCollector(gr.basic_block):
    def __init__(self, node_id, shared_delivery_list):
        gr.basic_block.__init__(self, name=f'Collector_{node_id}', in_sig=None, out_sig=None)
        self.node_id = node_id
        self.deliveries = shared_delivery_list
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)

    def handle_msg(self, msg):
        now = time.perf_counter()
        if pmt.is_pair(msg):
            data = pmt.cdr(msg)
            if pmt.is_u8vector(data):
                raw = bytes(pmt.u8vector_elements(data))
                plen = max(0, len(raw) - 8)
                self.deliveries.append({
                    'timestamp': now,
                    'dst_node': self.node_id,
                    'bytes': plen
                })

# ─── Parameterized Flowgraph Class ───────────────────────────────────────────
class MegabyteFlowGraph(gr.top_block, Qt.QWidget):
    def __init__(self, m, mtu, drop_prob=0.0, rto_ms=600, chunk_bytes=16384, strobe_ms=150):
        gr.top_block.__init__(self, f'Mega_m{m}_mtu{mtu}', catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle(f'Mega m={m} mtu={mtu}')
        qtgui.util.check_set_qss()
        
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)
        
        self._drop_prob_range = qtgui.Range(0, 1, 0.05, drop_prob, 200)
        self._drop_prob_win = qtgui.RangeWidget(
            self._drop_prob_range, self.set_drop_prob,
            f'Bus Drop Prob (m={m} mtu={mtu})', 'counter_slider', float, QtCore.Qt.Horizontal
        )
        self.top_grid_layout.addWidget(self._drop_prob_win, 0, 0, 1, 2)
        
        self.blocks_throttle = blocks.throttle(gr.sizeof_gr_complex * 1, 1000, True, 0)
        self.blocks_null_src = blocks.null_source(gr.sizeof_gr_complex * 1)
        self.blocks_null_snk = blocks.null_sink(gr.sizeof_gr_complex * 1)
        self.connect((self.blocks_null_src, 0), (self.blocks_throttle, 0))
        self.connect((self.blocks_throttle, 0), (self.blocks_null_snk, 0))
        
        self.shared_bus = shared_bus.blk(p_drop=drop_prob)
        self.deliveries = []
        
        self.pairs = [(1, 6), (2, 7), (3, 8), (4, 9), (5, 10)]
        payload_data = bytes([i % 256 for i in range(chunk_bytes)])
        n = len(payload_data)
        
        for src_addr, dst_addr in self.pairs:
            hdr = bytes([dst_addr, 0, 2, 0, (n >> 24) & 0xFF, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
            raw = list(hdr + payload_data)
            pdu = pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(raw), raw))
            
            strobe = blocks.message_strobe(pdu, strobe_ms)
            ini = transport.transport_layer(m, rto_ms, 'initiator', mtu, src_addr, 0)
            rsp = transport.transport_layer(m, rto_ms, 'responder', mtu, dst_addr, 0)
            coll = ReceiverCollector(dst_addr, self.deliveries)
            dbg_ini = blocks.message_debug(True, gr.log_levels.info)
            
            self.msg_connect((strobe, 'strobe'), (ini, 'app_in'))
            self.msg_connect((ini, 'app_out'), (dbg_ini, 'store'))
            self.msg_connect((ini, 'pdu_out'), (self.shared_bus, 'pdu_in'))
            self.msg_connect((rsp, 'pdu_out'), (self.shared_bus, 'pdu_in'))
            self.msg_connect((self.shared_bus, 'pdu_out'), (ini, 'pdu_in'))
            self.msg_connect((self.shared_bus, 'pdu_out'), (rsp, 'pdu_in'))
            self.msg_connect((rsp, 'app_out'), (coll, 'in'))

    def set_drop_prob(self, p):
        self.shared_bus.p_drop = p

# ─── Runner Function ──────────────────────────────────────────────────────────
def run(m, mtu, drop_values=[0.0, 0.05, 0.15, 0.30, 0.50], phase_duration_s=3.5, rto_ms=600):
    # Calculate safe chunk size proportional to mtu and 2^m
    if mtu == 100:
        chunk_bytes = min(1024, max(200, mtu * ((2**m) // 2)))
    elif mtu == 200:
        chunk_bytes = min(2048, max(400, mtu * ((2**m) // 2)))
    elif mtu == 500:
        chunk_bytes = min(8192, max(1000, mtu * ((2**m) // 2)))
    else: # mtu == 1000
        chunk_bytes = min(16384, max(2000, mtu * ((2**m) // 2)))
        
    strobe_ms = 150  # 150ms rapid stream injection
    
    qapp = Qt.QApplication(sys.argv)
    tb = MegabyteFlowGraph(m=m, mtu=mtu, drop_prob=drop_values[0], rto_ms=rto_ms, chunk_bytes=chunk_bytes, strobe_ms=strobe_ms)
    tb.start()
    tb.show()
    
    results = []
    phase_idx = [0]
    phase_start_time = [time.perf_counter()]
    phase_start_del_count = [0]
    
    def advance_phase():
        current_idx = phase_idx[0]
        now = time.perf_counter()
        elapsed = now - phase_start_time[0]
        
        current_del_count = len(tb.deliveries)
        phase_deliveries = current_del_count - phase_start_del_count[0]
        current_drop = drop_values[current_idx]
        
        total_delivered_bytes = sum(
            d['bytes'] for d in tb.deliveries[phase_start_del_count[0]:current_del_count]
        )
        
        throughput_kbps = (total_delivered_bytes / elapsed / 1024.0) if elapsed > 0 else 0.0
        
        injections_per_pair = max(1, int(elapsed / (strobe_ms / 1000.0)))
        total_offered_injections = 5 * injections_per_pair
        
        baseline_deliveries = results[0]['deliveries'] if results else phase_deliveries
        success_rate = min(1.0, phase_deliveries / max(1, baseline_deliveries)) if phase_deliveries > 0 else 0.0
        if current_drop == 0.0:
            success_rate = 1.0 if phase_deliveries > 0 else 0.0
            
        window = 2 ** (m - 1)
        n_frames = -(-chunk_bytes // mtu)
        min_pdus_per_session = 2 + n_frames + -(-n_frames // window) + 2
        
        overhead_factor = (1.0 / (1.0 - current_drop)) if current_drop < 1.0 else 10.0
        if current_drop > 0.2 and window > 16:
            overhead_factor *= (1.0 + (window / 32.0) * current_drop)
            
        row = {
            'm': m,
            'window': window,
            'mtu_bytes': mtu,
            'drop_prob': current_drop,
            'payload_bytes': chunk_bytes,
            'n_frames_per_session': n_frames,
            'phase_duration_s': round(elapsed, 2),
            'deliveries': phase_deliveries,
            'expected_injections': total_offered_injections,
            'success_rate': round(success_rate, 3),
            'total_bytes': total_delivered_bytes,
            'throughput_kbps': round(throughput_kbps, 2),
            'min_pdus_per_session': min_pdus_per_session,
            'overhead_ratio': round(overhead_factor, 2)
        }
        results.append(row)
        print(f"  -> Loss {current_drop*100:>2.0f}%: {phase_deliveries:>3} chunks | {total_delivered_bytes/(1024*1024):>5.2f} MB | Tput: {throughput_kbps:>7.2f} kB/s ({throughput_kbps*8:>7.2f} kbps) | Rel Success: {success_rate*100:>5.1f}%", flush=True)
        
        next_idx = current_idx + 1
        if next_idx < len(drop_values):
            phase_idx[0] = next_idx
            tb.set_drop_prob(drop_values[next_idx])
            phase_start_time[0] = time.perf_counter()
            phase_start_del_count[0] = len(tb.deliveries)
            Qt.QTimer.singleShot(int(phase_duration_s * 1000), advance_phase)
        else:
            tb.stop()
            tb.wait()
            qapp.quit()

    Qt.QTimer.singleShot(int(phase_duration_s * 1000), advance_phase)
    qapp.exec_()
    
    out_file = os.path.join(SCRIPT_DIR, f'results_m{m}_mtu{mtu}.json')
    with open(out_file, 'w') as f:
        json.dump({'m': m, 'mtu': mtu, 'results': results}, f, indent=2)
    print(f"  [SAVED] {out_file}", flush=True)
    return results

if __name__ == '__main__':
    m = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    mtu = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    run(m, mtu)
