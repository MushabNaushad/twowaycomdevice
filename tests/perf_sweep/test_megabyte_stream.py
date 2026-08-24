#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_megabyte_stream.py
=======================
Tests multi-megabyte continuous image / data transfer across 5 concurrent node pairs.
Measures true saturation throughput and channel efficiency.
"""

import sys, os, time, pmt, threading, json
from PyQt5 import Qt, QtCore
from gnuradio import qtgui, blocks, gr, transport

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST10N_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'test_10node')
sys.path.insert(0, TEST10N_DIR)
os.chdir(TEST10N_DIR)

import test_10node_shared_bus as shared_bus

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

class MegabyteFlowGraph(gr.top_block, Qt.QWidget):
    def __init__(self, m=5, mtu=1000, drop_prob=0.0, rto_ms=600, chunk_bytes=16384, strobe_ms=100):
        gr.top_block.__init__(self, f'Mega_m{m}_mtu{mtu}', catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle('Megabyte Transfer')
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
            'Bus Drop Prob', 'counter_slider', float, QtCore.Qt.Horizontal
        )
        self.top_grid_layout.addWidget(self._drop_prob_win, 0, 0, 1, 2)
        
        self.blocks_throttle = blocks.throttle(gr.sizeof_gr_complex * 1, 1000, True, 0)
        self.blocks_null_src = blocks.null_source(gr.sizeof_gr_complex * 1)
        self.blocks_null_snk = blocks.null_sink(gr.sizeof_gr_complex * 1)
        self.connect((self.blocks_null_src, 0), (self.blocks_throttle, 0))
        self.connect((self.blocks_throttle, 0), (self.blocks_null_snk, 0))
        
        self.shared_bus = shared_bus.blk(p_drop=drop_prob)
        self.deliveries = []
        
        # 5 active pairs
        self.pairs = [(1, 6), (2, 7), (3, 8), (4, 9), (5, 10)]
        payload_data = bytes([i % 256 for i in range(chunk_bytes)])
        n = len(payload_data)
        
        for src_addr, dst_addr in self.pairs:
            hdr = bytes([dst_addr, 0, 2, 0, (n >> 24) & 0xFF, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
            raw = list(hdr + payload_data)
            pdu = pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(raw), raw))
            
            # Rapid strobe simulating continuous stream / image packets
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

def test():
    qapp = Qt.QApplication(sys.argv)
    # 16 KB image chunks with MTU=1000, m=5 (W=16, seq_space=32 >= 16 pkts)
    tb = MegabyteFlowGraph(m=5, mtu=1000, drop_prob=0.0, chunk_bytes=16384, strobe_ms=100)
    tb.start()
    tb.show()
    
    t0 = time.perf_counter()
    
    def finish():
        elapsed = time.perf_counter() - t0
        total_bytes = sum(d['bytes'] for d in tb.deliveries)
        total_kb = total_bytes / 1024.0
        total_mb = total_bytes / (1024.0 * 1024.0)
        tput_kBps = total_kb / elapsed
        tput_kbps = tput_kBps * 8.0
        
        print(f"\n==================================================")
        print(f"MEGABYTE STREAMING TEST RESULTS (Clean Channel)")
        print(f"Elapsed Time: {elapsed:.2f} seconds")
        print(f"Total Transferred: {total_bytes:,} bytes ({total_kb:.1f} KB / {total_mb:.3f} MB)")
        print(f"Deliveries Count: {len(tb.deliveries)} chunks (16 KB each)")
        print(f"Throughput: {tput_kBps:.2f} kB/s ({tput_kbps:.2f} kbps)")
        print(f"==================================================\n")
        
        tb.stop()
        tb.wait()
        qapp.quit()

    Qt.QTimer.singleShot(4000, finish)
    qapp.exec_()

if __name__ == '__main__':
    test()
