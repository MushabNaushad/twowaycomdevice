#!/usr/bin/env python3
"""
_single_run.py — single (m, mtu, drop, payload_bytes) sweep run.

Exact pattern: gr.top_block + Qt.QWidget, QApplication.exec_(), QTimer for
injection and polling — matches GRC-generated test_addressing.py and test_10node.py.

Arguments: m mtu drop payload_bytes
Output: one JSON line on stdout when done.
"""
import sys, os, time, pmt, threading, json, random, signal

from PyQt5 import Qt, QtCore
from gnuradio import qtgui, blocks, gr, transport

PAIRS      = [(1,6),(2,7),(3,8),(4,9),(5,10)]
m          = int(sys.argv[1])   if len(sys.argv) > 1 else 4
mtu        = int(sys.argv[2])   if len(sys.argv) > 2 else 200
DROP       = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
PAYLOAD_B  = int(sys.argv[4])   if len(sys.argv) > 4 else 20*1024
RTO_MS     = 600
TIMEOUT_S  = 90.0

# ── EPY blocks ────────────────────────────────────────────────────────────────
class SharedBus(gr.basic_block):
    def __init__(self, p=0.0):
        gr.basic_block.__init__(self, 'SharedBus', in_sig=None, out_sig=None)
        self.p = p; self.total_in = 0; self._lk = threading.Lock()
        self.message_port_register_in(pmt.intern('pdu_in'))
        self.message_port_register_out(pmt.intern('pdu_out'))
        self.set_msg_handler(pmt.intern('pdu_in'), self._h)
    def _h(self, msg):
        with self._lk: self.total_in += 1
        if random.random() >= self.p:
            self.message_port_pub(pmt.intern('pdu_out'), msg)

class Collector(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(self, 'Collector', in_sig=None, out_sig=None)
        self.n = 0; self._lk = threading.Lock()
        self.message_port_register_in(pmt.intern('msg_in'))
        self.set_msg_handler(pmt.intern('msg_in'), self._h)
    def _h(self, _):
        with self._lk: self.n += 1

class NullSink(gr.basic_block):
    def __init__(self, t=''):
        gr.basic_block.__init__(self, f'NS{t}', in_sig=None, out_sig=None)
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), lambda _: None)

# ── Flowgraph ─────────────────────────────────────────────────────────────────
class SweepFG(gr.top_block, Qt.QWidget):
    def __init__(self):
        gr.top_block.__init__(self, 'SweepFG', catch_exceptions=True)
        Qt.QWidget.__init__(self)
        qtgui.util.check_set_qss()
        self.setWindowTitle('SweepFG')
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

        src = blocks.null_source(gr.sizeof_gr_complex)
        thr = blocks.throttle(gr.sizeof_gr_complex, 1000, True)
        snk = blocks.null_sink(gr.sizeof_gr_complex)
        self.connect((src,0),(thr,0)); self.connect((thr,0),(snk,0))

        self.bus  = SharedBus(DROP)
        self.coll = Collector()
        payload   = bytes([i%256 for i in range(PAYLOAD_B)])
        n         = len(payload)
        ini_blocks = {}

        for sa, da in PAIRS:
            ini = transport.transport_layer(m, RTO_MS, 'initiator', mtu, sa, 0)
            rsp = transport.transport_layer(m, RTO_MS, 'responder', mtu, da, 0)
            ns  = NullSink(str(sa))
            hdr = bytes([da,0,0x01,0,(n>>24)&0xFF,(n>>16)&0xFF,(n>>8)&0xFF,n&0xFF])
            raw = hdr + payload
            msg = pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(raw), list(raw)))
            strobe = blocks.message_strobe(msg, 30000)  # 30s period, fires once after 30s
            ini_blocks[sa] = (ini, strobe)

            self.msg_connect((strobe, 'strobe'), (ini, 'app_in'))
            self.msg_connect((ini, 'pdu_out'), (self.bus, 'pdu_in'))
            self.msg_connect((rsp, 'pdu_out'), (self.bus, 'pdu_in'))
            self.msg_connect((self.bus, 'pdu_out'), (ini, 'pdu_in'))
            self.msg_connect((self.bus, 'pdu_out'), (rsp, 'pdu_in'))
            self.msg_connect((rsp, 'app_out'), (self.coll, 'msg_in'))
            self.msg_connect((ini, 'app_out'), (ns, 'in'))

        self._ini_blocks = ini_blocks
        self._t0 = None

    def inject_all(self):
        """Called once by QTimer after flowgraph is running."""
        self._t0 = time.perf_counter()
        for sa, (ini, _) in self._ini_blocks.items():
            da = dict(PAIRS)[sa]
            n  = PAYLOAD_B
            pl = bytes([i%256 for i in range(n)])
            hdr = bytes([da,0,0x01,0,(n>>24)&0xFF,(n>>16)&0xFF,(n>>8)&0xFF,n&0xFF])
            raw = hdr + pl
            msg = pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(raw), list(raw)))
            ini.to_basic_block()._post(pmt.intern('app_in'), msg)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    qapp = Qt.QApplication(sys.argv)

    fg = SweepFG()
    fg.start()
    fg.show()

    t0 = [time.perf_counter()]

    # Inject 500ms after start to give GR scheduler time to warm up
    def do_inject():
        t0[0] = time.perf_counter()
        fg.inject_all()

    Qt.QTimer.singleShot(500, do_inject)

    def poll():
        elapsed = time.perf_counter() - t0[0]
        done    = fg.coll.n >= len(PAIRS)
        timeout = elapsed >= TIMEOUT_S and t0[0] != time.perf_counter()  # only after inject

        if done or (elapsed > TIMEOUT_S and elapsed < TIMEOUT_S + 5):
            delivered = fg.coll.n
            tput = (delivered * PAYLOAD_B / elapsed / 1024) if elapsed > 0 else 0
            n_frames = -(-PAYLOAD_B // mtu)
            window   = 2 ** (m - 1)
            min_pdus = len(PAIRS) * (2 + n_frames + -(-n_frames // window) + 2)
            overhead = fg.bus.total_in / min_pdus if min_pdus > 0 else 0

            result = {
                'm': m, 'window': window, 'mtu_bytes': mtu,
                'drop_prob': DROP, 'payload_bytes': PAYLOAD_B,
                'n_frames_per_session': n_frames,
                'session_time_s': round(elapsed, 3),
                'throughput_kbps': round(tput, 2),
                'delivery_count': delivered,
                'success_rate': round(delivered / len(PAIRS), 3),
                'completed': done,
                'bus_total_pdus': fg.bus.total_in,
                'overhead_ratio': round(overhead, 3),
                'retransmit_events': 0, 'busy_drop_events': 0,
                'stale_sid_events': 0, 'session_abandon_events': 0,
            }
            print(json.dumps(result), flush=True)
            poll_timer.stop()
            fg.stop()
            fg.wait()
            qapp.quit()

    poll_timer = Qt.QTimer()
    poll_timer.timeout.connect(poll)
    poll_timer.start(200)

    # Qt keepalive
    ka = Qt.QTimer(); ka.start(500); ka.timeout.connect(lambda: None)

    signal.signal(signal.SIGINT, lambda *_: (fg.stop(), fg.wait(), qapp.quit()))
    signal.signal(signal.SIGTERM, lambda *_: (fg.stop(), fg.wait(), qapp.quit()))

    qapp.exec_()


if __name__ == '__main__':
    main()
