#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_validate.py  — Quick validation run: m=4, mtu=200
3s strobe  |  15s per phase  |  5 phases = 76s total
Writes: tests/perf_sweep/results_m4_mtu200.json
"""
import sys, os, time, pmt, threading, json, random, signal

from PyQt5 import Qt, QtCore
from gnuradio import qtgui, blocks, gr, transport

PAIRS             = [(1,6),(2,7),(3,8),(4,9),(5,10)]
m, mtu            = 4, 200
DROP_VALUES       = [0.0, 0.05, 0.15, 0.30, 0.50]
PAYLOAD_B         = 8 * 1024
RTO_MS            = 600
STROBE_PERIOD_MS  = 3000    # fire every 3s
PHASE_DURATION_MS = 15000   # 15s per phase → 5 phases = 75s total
SETTLE_MS         = 1000

OUT_DIR  = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(OUT_DIR, f'results_m{m}_mtu{mtu}.json')

_current_phase = 0
_phase_start_t = {}
_phase_bus_in  = {}
_deliveries    = []
_bus_ref       = [None]
_qapp_ref      = [None]
_fg_ref        = [None]
_t0            = 0.0


# ── EPY blocks ────────────────────────────────────────────────────────────────
class SharedBus(gr.basic_block):
    def __init__(self, p_drop=0.0):
        gr.basic_block.__init__(self, 'SharedBus', in_sig=None, out_sig=None)
        self.p_drop   = p_drop
        self.total_in = 0
        self._lk      = threading.Lock()
        self.message_port_register_in(pmt.intern('pdu_in'))
        self.message_port_register_out(pmt.intern('pdu_out'))
        self.set_msg_handler(pmt.intern('pdu_in'), self.handle_msg)

    def handle_msg(self, msg):
        with self._lk:
            self.total_in += 1
        if random.random() >= self.p_drop:
            self.message_port_pub(pmt.intern('pdu_out'), msg)

    def snapshot(self):
        with self._lk:
            return self.total_in


class Collector(gr.basic_block):
    def __init__(self, node_addr):
        gr.basic_block.__init__(self, f'Coll_{node_addr}', in_sig=None, out_sig=None)
        self._node = node_addr
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)

    def handle_msg(self, _):
        ts = time.perf_counter()
        _deliveries.append((ts, self._node, _current_phase))
        print(f'  DELIVERY node={self._node} phase={_current_phase} '
              f't={ts - _t0:.2f}s', flush=True)


class NullSink(gr.basic_block):
    def __init__(self, t=''):
        gr.basic_block.__init__(self, f'NS_{t}', in_sig=None, out_sig=None)
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), lambda _: None)


# ── Flowgraph ─────────────────────────────────────────────────────────────────
def _make_pdu(da, payload):
    n   = len(payload)
    hdr = bytes([da, 0, 0x01, 0,
                 (n >> 24) & 0xFF, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
    raw = hdr + payload
    return pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(raw), list(raw)))


class SweepFG(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, f'Sweep_m{m}_mtu{mtu}', catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle(f'Sweep m={m} mtu={mtu} — running, do not close')
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException:
            pass
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
        self.settings = Qt.QSettings('gnuradio/flowgraphs', 'SweepFG')
        self.flowgraph_started = threading.Event()

        # ── Stream keepalive ─────────────────────────────────────────────────
        src = blocks.null_source(gr.sizeof_gr_complex)
        thr = blocks.throttle(gr.sizeof_gr_complex, 1000, True)
        snk = blocks.null_sink(gr.sizeof_gr_complex)
        self.connect((src, 0), (thr, 0))
        self.connect((thr, 0), (snk, 0))

        # ── Shared bus ────────────────────────────────────────────────────────
        bus = SharedBus(p_drop=0.0)
        _bus_ref[0] = bus

        # ── 5 pairs ───────────────────────────────────────────────────────────
        payload = bytes([i % 256 for i in range(PAYLOAD_B)])
        for sa, da in PAIRS:
            ini    = transport.transport_layer(m, RTO_MS, 'initiator', mtu, sa, 0)
            rsp    = transport.transport_layer(m, RTO_MS, 'responder', mtu, da, 0)
            coll   = Collector(da)
            ns     = NullSink(str(sa))
            strobe = blocks.message_strobe(_make_pdu(da, payload), STROBE_PERIOD_MS)

            self.msg_connect((strobe, 'strobe'), (ini, 'app_in'))
            self.msg_connect((ini,    'pdu_out'), (bus, 'pdu_in'))
            self.msg_connect((rsp,    'pdu_out'), (bus, 'pdu_in'))
            self.msg_connect((bus,    'pdu_out'), (ini, 'pdu_in'))
            self.msg_connect((bus,    'pdu_out'), (rsp, 'pdu_in'))
            self.msg_connect((rsp,    'app_out'), (coll, 'in'))
            self.msg_connect((ini,    'app_out'), (ns,   'in'))

    def closeEvent(self, event):
        """Prevent accidental window closure during test."""
        event.ignore()


# ── Phase management ──────────────────────────────────────────────────────────
def _phase_start(phase_idx):
    global _current_phase
    _current_phase            = phase_idx
    _phase_start_t[phase_idx] = time.perf_counter()
    _phase_bus_in[phase_idx]  = _bus_ref[0].snapshot()
    _bus_ref[0].p_drop        = DROP_VALUES[phase_idx]

    elapsed = time.perf_counter() - _t0
    print(f'\n[Phase {phase_idx}] drop={DROP_VALUES[phase_idx]:.0%}  '
          f'elapsed={elapsed:.1f}s  '
          f'(runs until t={elapsed + PHASE_DURATION_MS/1000:.0f}s)', flush=True)

    next_ms = PHASE_DURATION_MS
    if phase_idx + 1 < len(DROP_VALUES):
        Qt.QTimer.singleShot(next_ms, lambda pi=phase_idx+1: _phase_start(pi))
    else:
        Qt.QTimer.singleShot(next_ms, _finalize)


def _finalize():
    bus = _bus_ref[0]
    n_frames = -(-PAYLOAD_B // mtu)
    window   = 2 ** (m - 1)

    print(f'\n=== Finalizing at t={time.perf_counter()-_t0:.1f}s ===', flush=True)
    results = []
    for ph_idx, drop in enumerate(DROP_VALUES):
        ph_s = _phase_start_t.get(ph_idx, 0.0)
        ph_e = (  _phase_start_t.get(ph_idx + 1, time.perf_counter())
               if ph_idx + 1 < len(DROP_VALUES)
               else time.perf_counter() )
        ph_d = max(ph_e - ph_s, 0.001)

        ph_dels  = [d for d in _deliveries if d[2] == ph_idx]
        delivered = len(ph_dels)

        bus_s    = _phase_bus_in.get(ph_idx, 0)
        bus_e    = (_phase_bus_in.get(ph_idx+1, bus.snapshot())
                   if ph_idx+1 < len(DROP_VALUES) else bus.snapshot())
        bus_pdus = bus_e - bus_s

        n_fires  = max(1, int(ph_d / (STROBE_PERIOD_MS / 1000)))
        n_inject = len(PAIRS) * n_fires
        tput     = delivered * PAYLOAD_B / ph_d / 1024 if ph_d > 0 else 0
        min_pdus = n_inject * (2 + n_frames + -(-n_frames // window) + 2)
        overhead = bus_pdus / min_pdus if min_pdus > 0 else 0

        results.append({
            'm': m, 'window': window, 'mtu_bytes': mtu, 'drop_prob': drop,
            'payload_bytes': PAYLOAD_B, 'n_frames_per_session': n_frames,
            'phase_duration_s': round(ph_d, 2), 'injections': n_inject,
            'delivery_count': delivered,
            'success_rate': round(min(1.0, delivered / max(1, len(PAIRS))), 3),
            'throughput_kbps': round(tput, 2),
            'bus_total_pdus': bus_pdus, 'overhead_ratio': round(overhead, 3),
        })
        print(f'  ph{ph_idx} drop={drop:.0%}: {delivered}/{n_inject} injections  '
              f'{tput:.1f} kB/s  bus_pdus={bus_pdus}', flush=True)

    with open(OUT_FILE, 'w') as f:
        json.dump({'m': m, 'mtu': mtu, 'results': results}, f, indent=2)
    print(f'\nSaved: {OUT_FILE}', flush=True)

    _fg_ref[0].stop()
    _fg_ref[0].wait()
    _qapp_ref[0].quit()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global _t0
    qapp = Qt.QApplication(sys.argv)
    _qapp_ref[0] = qapp

    fg = SweepFG()
    _fg_ref[0] = fg
    fg.start()
    fg.flowgraph_started.set()
    fg.show()   # must show — GR scheduler needs active Qt window

    _t0 = time.perf_counter()

    def sig_handler(*_):
        _fg_ref[0].stop(); _fg_ref[0].wait(); qapp.quit()
    signal.signal(signal.SIGINT,  sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # Keepalive timer
    ka = Qt.QTimer()
    ka.start(500)
    ka.timeout.connect(lambda: None)

    # Phase 0 starts after settle
    Qt.QTimer.singleShot(SETTLE_MS, lambda: _phase_start(0))

    total_s = SETTLE_MS/1000 + len(DROP_VALUES) * PHASE_DURATION_MS/1000
    print(f'Started. m={m} mtu={mtu}  '
          f'strobe={STROBE_PERIOD_MS//1000}s  '
          f'phase={PHASE_DURATION_MS//1000}s×{len(DROP_VALUES)}  '
          f'total≈{total_s:.0f}s', flush=True)

    qapp.exec_()
    print('qapp.exec_() returned.', flush=True)


if __name__ == '__main__':
    main()
