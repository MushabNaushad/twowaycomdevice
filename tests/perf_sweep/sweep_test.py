#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sweep_test.py — Transport Layer Parameter Sweep  (subprocess-safe edition)
==========================================================================
Each (m, mtu) combination runs in its own subprocess to avoid GNURadio
block-registry corruption that causes segfaults when top_blocks are
repeatedly constructed and destroyed in a single long-lived process.

The orchestrator (this file when run without arguments) forks a child
for each (m, mtu) pair.  Each child runs only the drop-prob inner loop,
writes its rows to stdout as JSON lines, and exits.  The orchestrator
collects stdout, accumulates results, and writes the CSV and JSON.

Usage
-----
  python3 tests/perf_sweep/sweep_test.py
"""

import csv
import io
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Parameter grid
# ─────────────────────────────────────────────────────────────────────────────
M_VALUES         = [3, 4, 5, 6, 7]
MTU_VALUES       = [100, 200, 500, 1000]
DROP_VALUES      = [0.0, 0.05, 0.15, 0.30, 0.50]
PAYLOAD_BYTES    = 20 * 1024
NUM_PAIRS        = 5
RTO_MS           = 600
MAX_RETRIES      = 10
SCENARIO_TIMEOUT = 90.0
SETTLE_TIME      = 1.5

OUT_DIR  = os.path.dirname(os.path.abspath(__file__))
CSV_PATH  = os.path.join(OUT_DIR, "sweep_results.csv")
JSON_PATH = os.path.join(OUT_DIR, "sweep_results.json")

PAIRS = [(1, 6), (2, 7), (3, 8), (4, 9), (5, 10)]

# ─────────────────────────────────────────────────────────────────────────────
# Child mode — runs only when called with "--child m mtu"
# Imports GNURadio only in child process.
# ─────────────────────────────────────────────────────────────────────────────
def child_main(m: int, mtu: int):
    """
    Run the drop-prob sweep for a single (m, mtu) combination.
    Prints each result row as a JSON line to stdout.
    All GNURadio log output goes to stderr (captured by orchestrator separately).
    """
    import re
    import pmt
    from gnuradio import blocks, gr, transport
    import random

    # ── Tee stderr so we can parse GR log output ──────────────────────────
    class _TeeSink:
        def __init__(self, orig):
            self._orig = orig
            self._buf  = io.StringIO()
            self._lk   = threading.Lock()
        def write(self, d):
            self._orig.write(d)
            with self._lk:
                self._buf.write(d)
        def flush(self):
            self._orig.flush()
        def getvalue(self):
            with self._lk:
                return self._buf.getvalue()
        def clear(self):
            with self._lk:
                self._buf = io.StringIO()

    _tee = _TeeSink(sys.stderr)
    sys.stderr = _tee

    _RETX_RE    = re.compile(r"rto.*retransmit|data timeout|syn timeout|fin timeout", re.I)
    _BUSY_RE    = re.compile(r"already in progress", re.I)
    _STALE_RE   = re.compile(r"stale session", re.I)
    _ABANDON_RE = re.compile(r"retry limit.*exceeded|abandon", re.I)

    def count_log(text):
        lines = text.splitlines()
        return {
            "retransmit_events":      sum(1 for l in lines if _RETX_RE.search(l)),
            "busy_drop_events":       sum(1 for l in lines if _BUSY_RE.search(l)),
            "stale_sid_events":       sum(1 for l in lines if _STALE_RE.search(l)),
            "session_abandon_events": sum(1 for l in lines if _ABANDON_RE.search(l)),
        }

    def make_pdu(dst_addr, payload):
        n   = len(payload)
        hdr = bytes([dst_addr & 0xFF, 0, 0x01, 0x00,
                     (n>>24)&0xFF, (n>>16)&0xFF, (n>>8)&0xFF, n&0xFF])
        raw = hdr + payload
        return pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(raw), list(raw)))

    # ── EPY blocks ────────────────────────────────────────────────────────
    class SharedBus(gr.basic_block):
        def __init__(self, p_drop=0.0):
            gr.basic_block.__init__(self, "SharedBus", in_sig=None, out_sig=None)
            self.p_drop = p_drop
            self._in = self._fwd = self._drp = 0
            self._lk = threading.Lock()
            self.message_port_register_in(pmt.intern("pdu_in"))
            self.message_port_register_out(pmt.intern("pdu_out"))
            self.set_msg_handler(pmt.intern("pdu_in"), self._h)
        def _h(self, msg):
            with self._lk:
                self._in += 1
                if random.random() < self.p_drop:
                    self._drp += 1; return
                self._fwd += 1
            self.message_port_pub(pmt.intern("pdu_out"), msg)
        def stats(self):
            with self._lk:
                return {"total_in": self._in, "dropped": self._drp, "forwarded": self._fwd}
        def reset(self):
            with self._lk:
                self._in = self._fwd = self._drp = 0

    class ResultCollector(gr.basic_block):
        def __init__(self, addr, lst):
            gr.basic_block.__init__(self, f"RC{addr}", in_sig=None, out_sig=None)
            self._lst = lst; self._lk = threading.Lock()
            self.message_port_register_in(pmt.intern("app_out"))
            self.set_msg_handler(pmt.intern("app_out"), self._h)
        def _h(self, _):
            with self._lk:
                self._lst.append(time.perf_counter())

    class NullSink(gr.basic_block):
        def __init__(self, tag=""):
            gr.basic_block.__init__(self, f"NS{tag}", in_sig=None, out_sig=None)
            self.message_port_register_in(pmt.intern("in"))
            self.set_msg_handler(pmt.intern("in"), lambda _: None)

    # ── Build flowgraph ────────────────────────────────────────────────────
    tb  = gr.top_block(f"sweep_m{m}_mtu{mtu}", catch_exceptions=True)
    src = blocks.null_source(gr.sizeof_gr_complex)
    thr = blocks.throttle(gr.sizeof_gr_complex, 1000, True)
    snk = blocks.null_sink(gr.sizeof_gr_complex)
    tb.connect((src, 0), (thr, 0)); tb.connect((thr, 0), (snk, 0))

    bus = SharedBus(0.0)
    ini_blocks = {}
    rsp_blocks = {}
    results_list = []

    for src_addr, dst_addr in PAIRS:
        ini = transport.transport_layer(m, RTO_MS, "initiator", mtu, src_addr, 0)
        rsp = transport.transport_layer(m, RTO_MS, "responder", mtu, dst_addr, 0)
        rc  = ResultCollector(dst_addr, results_list)
        ns  = NullSink(f"ini{src_addr}")
        ini_blocks[src_addr] = ini
        rsp_blocks[dst_addr] = rsp
        tb.msg_connect((ini, "pdu_out"), (bus, "pdu_in"))
        tb.msg_connect((rsp, "pdu_out"), (bus, "pdu_in"))
        tb.msg_connect((bus, "pdu_out"), (ini, "pdu_in"))
        tb.msg_connect((bus, "pdu_out"), (rsp, "pdu_in"))
        tb.msg_connect((rsp, "app_out"), (rc, "app_out"))
        tb.msg_connect((ini, "app_out"), (ns, "in"))

    tb.start()
    time.sleep(0.5)

    payload = bytes([i % 256 for i in range(PAYLOAD_BYTES)])
    n_frames = -(-PAYLOAD_BYTES // mtu)
    window   = 2 ** (m - 1)

    # ── Sweep drop_prob ────────────────────────────────────────────────────
    for drop in DROP_VALUES:
        bus.p_drop = drop
        bus.reset()
        results_list.clear()
        _tee.clear()

        t_start = time.perf_counter()

        threads = [threading.Thread(target=lambda sa=sa, da=da: (
            ini_blocks[sa].to_basic_block()._post(
                pmt.intern("app_in"), make_pdu(da, payload))
        )) for sa, da in PAIRS]
        for t in threads: t.start()
        for t in threads: t.join()

        # Wait for deliveries
        deadline = time.perf_counter() + SCENARIO_TIMEOUT
        while len(results_list) < NUM_PAIRS and time.perf_counter() < deadline:
            time.sleep(0.05)
        t_elapsed = time.perf_counter() - t_start

        delivered       = len(results_list)
        completed       = delivered >= NUM_PAIRS
        delivered_bytes = delivered * PAYLOAD_BYTES
        throughput_kbps = (delivered_bytes / t_elapsed / 1024) if t_elapsed > 0 else 0

        bs = bus.stats()
        min_pdus = NUM_PAIRS * (2 + n_frames + -(-n_frames // window) + 2)
        overhead  = bs["total_in"] / min_pdus if min_pdus > 0 else 0

        row = {
            "m":                     m,
            "window":                window,
            "mtu_bytes":             mtu,
            "drop_prob":             drop,
            "payload_bytes":         PAYLOAD_BYTES,
            "n_frames_per_session":  n_frames,
            "session_time_s":        round(t_elapsed, 3),
            "throughput_kbps":       round(throughput_kbps, 2),
            "delivery_count":        delivered,
            "success_rate":          round(delivered / NUM_PAIRS, 3),
            "completed":             completed,
            "bus_total_pdus":        bs["total_in"],
            "bus_dropped_pdus":      bs["dropped"],
            "bus_forwarded_pdus":    bs["forwarded"],
            "overhead_ratio":        round(overhead, 3),
            **count_log(_tee.getvalue()),
        }
        # Emit result to stdout for orchestrator to collect
        sys.stdout.write(json.dumps(row) + "\n")
        sys.stdout.flush()

        time.sleep(SETTLE_TIME)

    tb.stop()
    tb.wait()


# ─────────────────────────────────────────────────────────────────────────────
# CSV helpers
# ─────────────────────────────────────────────────────────────────────────────
CSV_FIELDS = [
    "m", "window", "mtu_bytes", "drop_prob",
    "payload_bytes", "n_frames_per_session",
    "session_time_s", "throughput_kbps",
    "delivery_count", "success_rate", "completed",
    "bus_total_pdus", "bus_dropped_pdus", "bus_forwarded_pdus",
    "overhead_ratio",
    "retransmit_events", "busy_drop_events",
    "stale_sid_events", "session_abandon_events",
]

def write_csv_header():
    with open(CSV_PATH, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()

def append_csv(row):
    with open(CSV_PATH, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=CSV_FIELDS,
                       extrasaction="ignore").writerow(row)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator — forks one subprocess per (m, mtu) pair
# ─────────────────────────────────────────────────────────────────────────────
def orchestrator_main():
    total_combos = len(M_VALUES) * len(MTU_VALUES) * len(DROP_VALUES)
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"  Transport Layer Parameter Sweep")
    print(f"  m={M_VALUES}  mtu={MTU_VALUES}  drop={DROP_VALUES}")
    print(f"  Payload={PAYLOAD_BYTES//1024} KB  Pairs={NUM_PAIRS}  Combos={total_combos}")
    print(f"  Results → {OUT_DIR}")
    print(f"╚══════════════════════════════════════════════════════════════╝\n")

    write_csv_header()
    all_results = []
    run_idx     = 0
    script_path = os.path.abspath(__file__)

    for m in M_VALUES:
        for mtu in MTU_VALUES:
            print(f"  ┌─ Subprocess: m={m} (window={2**(m-1)})  mtu={mtu} B", flush=True)
            proc = subprocess.Popen(
                [sys.executable, script_path, "--child", str(m), str(mtu)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Stream stdout line-by-line (each line = one JSON result)
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue

                run_idx += 1
                pct = run_idx / total_combos * 100
                all_results.append(row)
                append_csv(row)

                status = "✓" if row["completed"] else "⏱"
                print(f"  │  [{run_idx:3d}/{total_combos}] {pct:5.1f}%  "
                      f"drop={row['drop_prob']:.0%}  "
                      f"→ {row['throughput_kbps']:7.1f} kB/s  "
                      f"delivered={row['delivery_count']}/{NUM_PAIRS}  "
                      f"retx={row['retransmit_events']:3d}  {status}", flush=True)

            proc.wait()
            if proc.returncode not in (0, -11):   # -11 = SIGSEGV (acceptable on teardown)
                stderr_out = proc.stderr.read()
                if stderr_out.strip():
                    print(f"  │  [stderr] {stderr_out[:200]}")
            print(f"  └─ Done (exit {proc.returncode})\n", flush=True)

    # Write full JSON
    with open(JSON_PATH, "w") as f:
        json.dump({
            "sweep_config": {
                "timestamp":     datetime.now().isoformat(),
                "m_values":      M_VALUES,
                "mtu_values":    MTU_VALUES,
                "drop_values":   DROP_VALUES,
                "payload_bytes": PAYLOAD_BYTES,
                "num_pairs":     NUM_PAIRS,
                "rto_ms":        RTO_MS,
            },
            "results": all_results,
        }, f, indent=2)

    print(f"\n  💾 JSON → {JSON_PATH}")
    print(f"  💾 CSV  → {CSV_PATH}")
    print(f"\n  Run sweep_charts.py to generate charts.")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        child_main(int(sys.argv[2]), int(sys.argv[3]))
    else:
        orchestrator_main()
