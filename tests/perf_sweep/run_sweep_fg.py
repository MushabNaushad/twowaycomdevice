#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_sweep_fg.py  m  mtu
=======================
Parameter sweep for one (m, mtu) combination.
Runs from the tests/perf_sweep directory.
Uses the exact GRC-generated pattern including qtgui.RangeWidget which is
required for GR's message scheduler to bind QSocketNotifiers correctly.

Output: results_m{m}_mtu{mtu}.json (same directory)
"""
import sys, os, time, pmt, threading, json, random, signal

# Set CWD to test_10node so EPY modules resolve
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
TEST10N_DIR  = os.path.join(os.path.dirname(SCRIPT_DIR), 'test_10node')
sys.path.insert(0, TEST10N_DIR)
os.chdir(TEST10N_DIR)   # GRC EPY imports require CWD = module directory

from PyQt5 import Qt, QtCore
from gnuradio import qtgui, blocks, gr, transport
import test_10node_shared_bus as shared_bus

PAIRS             = [(1,6),(2,7),(3,8),(4,9),(5,10)]
m                 = int(sys.argv[1])
mtu               = int(sys.argv[2])
DROP_VALUES       = [0.0, 0.05, 0.15, 0.30, 0.50]
PAYLOAD_B         = 8 * 1024   # 8 KB
RTO_MS            = 600
STROBE_PERIOD_MS  = 6000       # fire every 6s
PHASE_DURATION_MS = 42000      # 42s per phase → 7 fires → 35 injections
SETTLE_MS         = 1500

OUT_FILE = os.path.join(SCRIPT_DIR, f'results_m{m}_mtu{mtu}.json')

_current_phase = 0
_phase_start_t = {}
_phase_bus_in  = {}
_deliveries    = []   # list of (timestamp, node_addr, phase_idx)
_bus_obj       = [None]
_qapp_ref      = [None]
_fg_ref        = [None]
_t0            = 0.0


class Collector(gr.basic_block):
    """Receive from rsp.app_out, record delivery with current phase."""
    def __init__(self, node_addr):
        gr.basic_block.__init__(self, f'Coll_{node_addr}', in_sig=None, out_sig=None)
        self._node = node_addr
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)
    def handle_msg(self, _):
        _deliveries.append((time.perf_counter(), self._node, _current_phase))
        elapsed = time.perf_counter() - _t0
        print(f'  DELIVERY node={self._node} phase={_current_phase} '
              f't={elapsed:.2f}s', flush=True)


class NullSink(gr.basic_block):
    def __init__(self, t=''):
        gr.basic_block.__init__(self, f'NS_{t}', in_sig=None, out_sig=None)
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), lambda _: None)


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
        self.setWindowTitle(f'Parameter Sweep  m={m}  mtu={mtu}  — DO NOT CLOSE')
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException:
            pass

        # ── Full Qt widget hierarchy — REQUIRED before any GR blocks ──────────
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
        self.settings = Qt.QSettings('gnuradio/flowgraphs', f'Sweep_m{m}_mtu{mtu}')
        try:
            geom = self.settings.value('geometry')
            if geom:
                self.restoreGeometry(geom)
        except BaseException:
            pass
        self.flowgraph_started = threading.Event()

        # ── Add a qtgui.RangeWidget — needed to bind GR message sockets ───────
        self._drop_range = qtgui.Range(0, 1, 0.05, 0.0, 200)
        self._drop_win   = qtgui.RangeWidget(
            self._drop_range, lambda v: None,
            f'Bus Drop Prob  (m={m} W={2**(m-1)} mtu={mtu}B)',
            'counter_slider', float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._drop_win, 0, 0, 1, 4)

        # ── Status label ───────────────────────────────────────────────────────
        self.status_lbl = Qt.QLabel(
            f'm={m}  window={2**(m-1)}  mtu={mtu}B  payload={PAYLOAD_B//1024}KB\n'
            f'Phase 0/{len(DROP_VALUES)}  Initialising...\n'
            f'DO NOT CLOSE THIS WINDOW — it will close automatically.')
        self.status_lbl.setStyleSheet('font-size: 13px; padding: 16px;')
        self.top_grid_layout.addWidget(self.status_lbl, 1, 0, 1, 4)

        # ── Stream keepalive ─────────────────────────────────────────────────
        self.blocks_null_source = blocks.null_source(gr.sizeof_gr_complex * 1)
        self.blocks_throttle    = blocks.throttle(gr.sizeof_gr_complex * 1, 1000, True, 0)
        self.blocks_null_sink   = blocks.null_sink(gr.sizeof_gr_complex * 1)
        self.connect((self.blocks_null_source, 0), (self.blocks_throttle, 0))
        self.connect((self.blocks_throttle, 0),    (self.blocks_null_sink, 0))

        # ── Shared bus ────────────────────────────────────────────────────────
        self.shared_bus = shared_bus.blk(p_drop=0.0)
        _bus_obj[0] = self.shared_bus

        # ── 5 node pairs ─────────────────────────────────────────────────────
        payload = bytes([i % 256 for i in range(PAYLOAD_B)])
        for sa, da in PAIRS:
            ini    = transport.transport_layer(m, RTO_MS, 'initiator', mtu, sa, 0)
            rsp    = transport.transport_layer(m, RTO_MS, 'responder', mtu, da, 0)
            coll   = Collector(da)
            ns     = NullSink(str(sa))
            strobe = blocks.message_strobe(_make_pdu(da, payload), STROBE_PERIOD_MS)

            self.msg_connect((strobe, 'strobe'),      (ini,              'app_in'))
            self.msg_connect((ini,    'pdu_out'),      (self.shared_bus,  'pdu_in'))
            self.msg_connect((rsp,    'pdu_out'),      (self.shared_bus,  'pdu_in'))
            self.msg_connect((self.shared_bus, 'pdu_out'), (ini,          'pdu_in'))
            self.msg_connect((self.shared_bus, 'pdu_out'), (rsp,          'pdu_in'))
            self.msg_connect((rsp,    'app_out'),      (coll,             'in'))
            self.msg_connect((ini,    'app_out'),      (ns,               'in'))

    def closeEvent(self, event):
        event.ignore()   # prevent accidental closure

    def update_status(self, phase_idx, drop, n_dels):
        elapsed = time.perf_counter() - _t0
        rem     = max(0, SETTLE_MS/1000 + len(DROP_VALUES)*PHASE_DURATION_MS/1000 - elapsed)
        self.status_lbl.setText(
            f'm={m}  window={2**(m-1)}  mtu={mtu}B  payload={PAYLOAD_B//1024}KB\n'
            f'Phase {phase_idx+1}/{len(DROP_VALUES)}  drop={drop:.0%}  '
            f'deliveries: {n_dels}  t={elapsed:.0f}s  '
            f'remaining≈{rem:.0f}s\n'
            f'DO NOT CLOSE THIS WINDOW — it will close automatically.')


# ── Phase management ──────────────────────────────────────────────────────────
def _phase_start(phase_idx):
    global _current_phase
    _current_phase             = phase_idx
    _phase_start_t[phase_idx]  = time.perf_counter()
    _phase_bus_in[phase_idx]   = _bus_obj[0].total_in
    _bus_obj[0].p_drop         = DROP_VALUES[phase_idx]
    _fg_ref[0].update_status(phase_idx, DROP_VALUES[phase_idx], len(_deliveries))

    elapsed = time.perf_counter() - _t0
    print(f'\n[Phase {phase_idx}] drop={DROP_VALUES[phase_idx]:.0%}  '
          f't={elapsed:.1f}s  ends≈t={elapsed+PHASE_DURATION_MS/1000:.0f}s',
          flush=True)

    if phase_idx + 1 < len(DROP_VALUES):
        Qt.QTimer.singleShot(PHASE_DURATION_MS,
                             lambda pi=phase_idx + 1: _phase_start(pi))
    else:
        Qt.QTimer.singleShot(PHASE_DURATION_MS, _finalize)


def _finalize():
    bus = _bus_obj[0]
    n_frames = -(-PAYLOAD_B // mtu)
    window   = 2 ** (m - 1)

    print(f'\n=== Finalize at t={time.perf_counter()-_t0:.1f}s ===', flush=True)
    results = []
    for ph_idx, drop in enumerate(DROP_VALUES):
        ph_s = _phase_start_t.get(ph_idx, 0.0)
        ph_e = (_phase_start_t.get(ph_idx + 1, time.perf_counter())
                if ph_idx + 1 < len(DROP_VALUES)
                else time.perf_counter())
        ph_d = max(ph_e - ph_s, 0.001)

        ph_dels  = [d for d in _deliveries if d[2] == ph_idx]
        delivered = len(ph_dels)

        bus_s    = _phase_bus_in.get(ph_idx, 0)
        bus_e    = (_phase_bus_in.get(ph_idx + 1, bus.total_in)
                   if ph_idx + 1 < len(DROP_VALUES) else bus.total_in)
        bus_pdus = bus_e - bus_s

        n_fires  = max(1, int(ph_d / (STROBE_PERIOD_MS / 1000)))
        n_inject = len(PAIRS) * n_fires
        tput     = delivered * PAYLOAD_B / ph_d / 1024 if ph_d > 0 else 0
        min_pdus = n_inject * (2 + n_frames + -(-n_frames // window) + 2)
        overhead = bus_pdus / min_pdus if min_pdus > 0 else 0

        r = {
            'm': m, 'window': window, 'mtu_bytes': mtu, 'drop_prob': drop,
            'payload_bytes': PAYLOAD_B, 'n_frames_per_session': n_frames,
            'phase_duration_s': round(ph_d, 2), 'injections': n_inject,
            'delivery_count': delivered,
            'success_rate': round(min(1.0, delivered / max(1, len(PAIRS))), 3),
            'throughput_kbps': round(tput, 2),
            'bus_total_pdus': bus_pdus, 'overhead_ratio': round(overhead, 3),
        }
        results.append(r)
        print(f'  ph{ph_idx} drop={drop:.0%}: {delivered}/{n_inject} delivered  '
              f'{tput:.1f} kB/s  bus_pdus={bus_pdus}', flush=True)

    with open(OUT_FILE, 'w') as f:
        json.dump({'m': m, 'mtu': mtu, 'results': results}, f, indent=2)
    print(f'\nSaved → {OUT_FILE}', flush=True)

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
    fg.show()

    _t0 = time.perf_counter()

    def sig_handler(*_):
        _fg_ref[0].stop()
        _fg_ref[0].wait()
        qapp.quit()
    signal.signal(signal.SIGINT,  sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    ka = Qt.QTimer(); ka.start(500); ka.timeout.connect(lambda: None)
    Qt.QTimer.singleShot(SETTLE_MS, lambda: _phase_start(0))

    total_s = SETTLE_MS / 1000 + len(DROP_VALUES) * PHASE_DURATION_MS / 1000
    print(f'\nStarted: m={m} mtu={mtu} window={2**(m-1)}  '
          f'strobe={STROBE_PERIOD_MS//1000}s  '
          f'phase={PHASE_DURATION_MS//1000}s×{len(DROP_VALUES)}  '
          f'total≈{total_s:.0f}s\n', flush=True)

    qapp.exec_()
    print('Exited.', flush=True)


if __name__ == '__main__':
    main()
