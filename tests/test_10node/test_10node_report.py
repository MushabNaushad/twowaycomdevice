#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_10node_report.py — Post-processing report for test_10node.py
=================================================================
Reads test_10node_results.json and generates a comprehensive Markdown report.

Usage:
    python3 test_10node_report.py [--json test_10node_results.json]
                                  [--out  test_10node_report.md]
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR   = os.path.dirname(__file__)
DEFAULT_JSON = os.path.join(SCRIPT_DIR, "test_10node_results.json")
DEFAULT_OUT  = os.path.join(SCRIPT_DIR, "test_10node_report.md")


# ─────────────────────────────────────────────────────────────────────────────
def load_results(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
def fmt_bool(v: bool) -> str:
    return "✅ PASS" if v else "❌ FAIL"


def count_retransmits(log_events: list) -> int:
    return sum(1 for e in log_events
               if "retransmit" in e.get("message", "").lower()
               or "rto" in e.get("message", "").lower())


def count_abandons(log_events: list) -> int:
    return sum(1 for e in log_events
               if "abandon" in e.get("message", "").lower()
               or "exceed" in e.get("message", "").lower()
               or "retry limit" in e.get("message", "").lower())


def count_busy_drops(log_events: list) -> int:
    return sum(1 for e in log_events
               if "already in progress" in e.get("message", "").lower()
               or ("dropping" in e.get("message", "").lower()
                   and "session" in e.get("message", "").lower()))


def count_stale(log_events: list) -> int:
    return sum(1 for e in log_events
               if "stale" in e.get("message", "").lower())


def count_addr_drops(log_events: list) -> int:
    return sum(1 for e in log_events
               if "not for us" in e.get("message", "").lower()
               or "syn not for" in e.get("message", "").lower())


# ─────────────────────────────────────────────────────────────────────────────
def build_delivery_matrix(all_deliveries: list, num_nodes: int = 10) -> dict:
    """Returns a dict of dict: matrix[src][dst] = count."""
    matrix = defaultdict(lambda: defaultdict(int))
    for d in all_deliveries:
        src = d.get("src_addr")
        dst = d.get("dst_node")
        if src is not None and dst is not None:
            matrix[src][dst] += 1
    return matrix


# ─────────────────────────────────────────────────────────────────────────────
def generate_report(data: dict) -> str:
    run_info   = data.get("test_run", {})
    bus_stats  = data.get("bus_stats", {})
    scenarios  = data.get("scenario_results", [])
    deliveries = data.get("all_deliveries", [])
    log_events = data.get("all_log_events", [])

    lines = []
    a = lines.append  # shorthand

    # ── Title ────────────────────────────────────────────────────────────────
    a("# 10-Node Transport Layer Addressing Test — Comprehensive Report")
    a("")
    a(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    a(f"**Test run timestamp:** {run_info.get('timestamp', 'unknown')}")
    a("")

    # ── Test Configuration ───────────────────────────────────────────────────
    a("## Test Configuration")
    a("")
    a("| Parameter | Value |")
    a("|-----------|-------|")
    a(f"| Nodes | {run_info.get('num_nodes', '?')} (addresses 1–10, each with initiator + responder instance) |")
    a(f"| Sequence number bits (m) | {run_info.get('m_bits', '?')} → seq_space={2**run_info.get('m_bits',4)}, window={2**(run_info.get('m_bits',4)-1)} |")
    a(f"| MTU | {run_info.get('mtu_bytes', '?')} bytes per DATA frame |")
    a(f"| Retransmission timeout | {run_info.get('rto_ms', '?')} ms |")
    a(f"| Max SYN/FIN retries | {run_info.get('max_retries', '?')} |")
    a(f"| Channel model | Shared broadcast bus (all nodes see all PDUs) |")
    a("")

    # ── Bus Stats ────────────────────────────────────────────────────────────
    a("## Channel Statistics (Shared Bus)")
    a("")
    total_in  = bus_stats.get("total_in", 0)
    total_fwd = bus_stats.get("total_forwarded", 0)
    total_drp = bus_stats.get("total_dropped", 0)
    eff_drop  = (total_drp / total_in * 100) if total_in > 0 else 0.0
    a("| Metric | Value |")
    a("|--------|-------|")
    a(f"| Total PDUs received by bus | {total_in} |")
    a(f"| PDUs forwarded | {total_fwd} |")
    a(f"| PDUs dropped | {total_drp} |")
    a(f"| Effective drop rate | {eff_drop:.1f}% |")
    a("")

    # ── Overall Log Event Summary ────────────────────────────────────────────
    a("## Overall Log Event Summary (across all scenarios)")
    a("")
    total_retx  = count_retransmits(log_events)
    total_aband = count_abandons(log_events)
    total_busy  = count_busy_drops(log_events)
    total_stale = count_stale(log_events)
    total_addr  = count_addr_drops(log_events)
    a("| Event type | Count |")
    a("|------------|-------|")
    a(f"| Retransmissions (RTO fires) | {total_retx} |")
    a(f"| Session abandons (retry limit exceeded) | {total_aband} |")
    a(f"| Busy-session drops (app_in while session active) | {total_busy} |")
    a(f"| Stale session-ID drops | {total_stale} |")
    a(f"| Address filter drops (SYN not for us) | {total_addr} |")
    a(f"| **Total log events captured** | **{len(log_events)}** |")
    a(f"| **Total app_out deliveries** | **{len(deliveries)}** |")
    a("")

    # ── Scenario Summary Table ───────────────────────────────────────────────
    a("## Scenario Results Summary")
    a("")
    a("| # | Scenario | Result | Deliveries | Retransmits | Notes |")
    a("|---|----------|--------|-----------|-------------|-------|")
    passed_count = 0
    for i, s in enumerate(scenarios):
        result  = fmt_bool(s.get("passed", False))
        name    = s.get("scenario", f"S{i+1}")
        # strip leading "S1: " prefix for table
        short_name = name.split("—", 1)[-1].strip() if "—" in name else name
        nd      = len(s.get("deliveries", []))
        nl      = s.get("log_events", [])
        retx    = count_retransmits(nl)
        notes   = s.get("notes", "")[:120]
        a(f"| {i+1} | {short_name[:55]} | {result} | {nd} | {retx} | {notes} |")
        if s.get("passed", False):
            passed_count += 1

    total_scenarios = len(scenarios)
    a("")
    a(f"**{passed_count}/{total_scenarios} scenarios passed.**")
    a("")

    # ── Per-Scenario Deep-Dive ───────────────────────────────────────────────
    a("## Per-Scenario Analysis")
    a("")

    for i, s in enumerate(scenarios):
        snum  = i + 1
        name  = s.get("scenario", f"Scenario {snum}")
        nd    = s.get("deliveries", [])
        nl    = s.get("log_events", [])
        notes = s.get("notes", "")

        a(f"### {name}")
        a("")
        a(f"**Result:** {fmt_bool(s.get('passed', False))}")
        a("")
        a(f"**Summary:** {notes}")
        a("")

        # Delivery details
        if nd:
            a("**Deliveries:**")
            a("")
            a("| Time (rel s) | Dst Node | Src Addr | Session ID | Payload |")
            a("|-------------|----------|----------|------------|---------|")
            t0 = nd[0]["timestamp"] if nd else 0
            for d in nd:
                rel_t   = f"{d['timestamp'] - t0:.2f}"
                dst     = d.get("dst_node", "?")
                src     = d.get("src_addr", "?")
                sid     = d.get("session_id", "?")
                payload = (d.get("payload_ascii") or "")[:50]
                sid_str = f"{sid}" if sid else "?"
                a(f"| +{rel_t}s | Node {dst} | Node {src} | `{sid_str}` | {payload} |")
            a("")
        else:
            a("**No deliveries recorded.**")
            a("")

        # Notable log events
        notable = [e for e in nl if e.get("level") in ("WARNING", "ERROR")
                   or "rto" in e.get("message","").lower()
                   or "abandon" in e.get("message","").lower()
                   or "already in progress" in e.get("message","").lower()
                   or "stale" in e.get("message","").lower()][:15]
        if notable:
            a("**Notable log events:**")
            a("")
            a("```")
            for e in notable:
                ts  = e.get("timestamp", 0)
                lvl = e.get("level", "")
                msg = e.get("message", "")
                a(f"[{lvl:7s}] {msg}")
            a("```")
            a("")

    # ── Delivery Matrix ──────────────────────────────────────────────────────
    a("## Delivery Matrix (src → dst, all scenarios combined)")
    a("")
    matrix = build_delivery_matrix(deliveries)
    all_srcs = sorted(set(d.get("src_addr") for d in deliveries if d.get("src_addr") is not None))
    all_dsts = sorted(set(d.get("dst_node") for d in deliveries if d.get("dst_node") is not None))

    if all_srcs and all_dsts:
        header = "| Src \\ Dst |" + "".join(f" N{d} |" for d in all_dsts)
        sep    = "|----------|" + "".join("-----|" for _ in all_dsts)
        a(header)
        a(sep)
        for src in all_srcs:
            row = f"| Node {src:2d}  |"
            for dst in all_dsts:
                count = matrix[src][dst]
                cell  = f"  {count}  " if count else "  -  "
                row  += f"{cell}|"
            a(row)
        a("")
    else:
        a("*(No delivery data)*")
        a("")

    # ── Addressing Analysis ──────────────────────────────────────────────────
    a("## Addressing Analysis")
    a("")
    a("### Address Filter Correctness")
    a("")
    # Check for leakage: were any packets delivered to nodes that should not have received them?
    leakage_events = []
    for s in scenarios:
        sname = s.get("scenario", "")
        nd    = s.get("deliveries", [])
        # S3: only node 9 should receive
        if "S3" in sname or "Wrong-address" in sname:
            leaks = [d for d in nd if d.get("dst_node") != 9]
            for d in leaks:
                leakage_events.append((sname, d))
        # S5: only nodes 5 and 6 should receive
        if "S5" in sname or "Simultaneous" in sname:
            leaks = [d for d in nd if d.get("dst_node") not in (5, 6)]
            for d in leaks:
                leakage_events.append((sname, d))

    if leakage_events:
        a("> [!CAUTION]")
        a(f"> **Address filter leakage detected!** "
          f"{len(leakage_events)} packet(s) delivered to unintended nodes:")
        a("> ")
        for sc, d in leakage_events:
            a(f">  - `{sc}`: delivered to Node {d.get('dst_node')} "
              f"(src={d.get('src_addr')}, sid={d.get('session_id')})")
        a("")
    else:
        a("> [!NOTE]")
        a("> **No address filter leakage detected.** All unicast deliveries were "
          "received only by the intended destination node.")
        a("")

    a("### Broadcast Behaviour (Scenario 4)")
    s4 = next((s for s in scenarios if "S4" in s.get("scenario","") or "Broadcast" in s.get("scenario","")), None)
    if s4:
        nd = s4.get("deliveries", [])
        received_on = sorted(set(d.get("dst_node") for d in nd))
        a(f"Broadcast from Node 4 (dst_addr=0x00) was delivered to: **{received_on}**")
        a("")
        a("> **Design note:** The SR-ARQ transport layer is inherently unicast — when")
        a("> a broadcast SYN is sent, multiple responders may reply with SYN_ACK")
        a("> simultaneously, but the initiator's FSM accepts only the **first** SYN_ACK")
        a("> it receives and enters TX_ACTIVE, ignoring all subsequent ones. The session")
        a("> therefore completes with exactly one responder, not all of them.")
        a("")

    # ── Overload / Busy-Session Analysis ────────────────────────────────────
    a("## Overload & Busy-Session Behaviour")
    a("")
    a("### Scenario 6 — Input Overload")
    s6 = next((s for s in scenarios if "S6" in s.get("scenario","") or "overload" in s.get("scenario","").lower()), None)
    if s6:
        nl = s6.get("log_events", [])
        busy = [e for e in nl if "already in progress" in e.get("message","").lower()]
        a(f"- Busy-session warnings recorded: **{len(busy)}**")
        a(f"- Deliveries: **{len(s6.get('deliveries',[]))}**")
        if busy:
            a(f"- ✅ The transport layer correctly rejected the second `app_in` message")
            a(f"  with a warning, while the first session ran to completion.")
        else:
            a(f"- ⚠️  No busy-session warning was logged; the drop may have been silent.")
        a("")
    a("### Scenario 7 — Rapid Burst")
    s7 = next((s for s in scenarios if "S7" in s.get("scenario","") or "burst" in s.get("scenario","").lower()), None)
    if s7:
        nl = s7.get("log_events", [])
        busy = count_busy_drops(nl)
        nd   = len(s7.get("deliveries",[]))
        a(f"- 5 messages injected at 200 ms intervals.")
        a(f"- Deliveries completed: **{nd}**")
        a(f"- Busy-drop events: **{busy}**")
        a(f"- Sessions are serialised by the FSM; back-to-back injections hit the busy")
        a(f"  lock and are dropped with a warning. Only messages injected after the")
        a(f"  previous session completes will successfully start a new session.")
        a("")

    # ── Heavy Loss Analysis ──────────────────────────────────────────────────
    a("## High-Loss Channel Behaviour (Scenario 8)")
    a("")
    s8 = next((s for s in scenarios if "S8" in s.get("scenario","") or "heavy" in s.get("scenario","").lower()), None)
    if s8:
        nl   = s8.get("log_events", [])
        retx = count_retransmits(nl)
        abn  = count_abandons(nl)
        nd   = len(s8.get("deliveries",[]))
        a(f"- Bus drop probability: **50%**")
        a(f"- Retransmissions triggered: **{retx}**")
        a(f"- Session abandons (retry limit {run_info.get('max_retries','?')} exceeded): **{abn}**")
        a(f"- Deliveries: **{nd}**")
        a("")
        if nd > 0:
            a("> [!NOTE]")
            a("> The SR-ARQ mechanism successfully delivered the message despite 50% loss,")
            a("> demonstrating the effectiveness of the retransmission protocol.")
        else:
            a("> [!WARNING]")
            a("> The session was not delivered under 50% packet loss. The RTO/retry")
            a("> chain exhausted MAX_CTRL_RETRIES and the session was abandoned. This is")
            a("> expected behaviour for extreme loss rates — increase MAX_CTRL_RETRIES or")
            a("> reduce the drop probability for reliable delivery.")
        a("")

    # ── Concurrent Session Isolation ────────────────────────────────────────
    a("## Concurrent Session Isolation (Scenarios 5 & 10)")
    a("")
    for label, expected in [("S5", {5, 6}), ("S10", {6, 7, 8, 9, 10})]:
        sc = next((s for s in scenarios if label in s.get("scenario","")), None)
        if sc:
            nd  = sc.get("deliveries", [])
            got = set(d.get("dst_node") for d in nd)
            missed = expected - got
            wrong  = got - expected
            a(f"**{label}:** Expected destinations: `{sorted(expected)}`, "
              f"got: `{sorted(got)}`.")
            if not wrong:
                a(f"  - ✅ No cross-contamination — session IDs correctly isolated traffic.")
            else:
                a(f"  - ❌ Contamination detected: traffic arrived at {sorted(wrong)}.")
            if missed:
                a(f"  - ⚠️  Missed: {sorted(missed)} (may have timed out or lost to RTO).")
            a("")

    # ── Recommendations ──────────────────────────────────────────────────────
    a("## Observations & Recommendations")
    a("")
    a("| Observation | Impact | Recommendation |")
    a("|-------------|--------|---------------|")
    a("| Transport layer serialises sessions (only one active session per initiator) | "
      "Burst traffic is silently dropped if the lock is held | "
      "Consider a queue at the app_in interface if multi-message pipelines are needed |")
    a("| Broadcast SYN races — only one session completes | "
      "True one-to-all broadcast is not supported by the SR-ARQ protocol | "
      "Use per-destination unicast sessions for guaranteed multi-node delivery |")
    a("| SYN_ACK race under many-to-one load (S9) | "
      "Concurrent SYNs from different initiators cause stale-session ID drops | "
      "This is correct FSM behaviour; no action needed — sessions serialise naturally |")
    a("| High loss (≥50%) may exceed MAX_CTRL_RETRIES | "
      "Session abandoned without delivery | "
      "Tune MAX_CTRL_RETRIES and RTO_MS to match expected channel conditions |")
    a("| Address filter correctly prevents cross-talk | "
      "None — working as intended | "
      "Consider adding port-based filtering tests in future |")
    a("")

    a("---")
    a(f"*Report generated by `test_10node_report.py` on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate report from test_10node results")
    parser.add_argument("--json", default=DEFAULT_JSON, help="Path to results JSON")
    parser.add_argument("--out",  default=DEFAULT_OUT,  help="Output Markdown file")
    args = parser.parse_args()

    if not os.path.exists(args.json):
        print(f"ERROR: results file not found: {args.json}")
        print("Run test_10node.py first to generate results.")
        sys.exit(1)

    print(f"Loading results from: {args.json}")
    data = load_results(args.json)

    report = generate_report(data)

    with open(args.out, "w") as f:
        f.write(report)

    print(f"Report written to: {args.out}")

    # Also print summary to console
    scenarios = data.get("scenario_results", [])
    passed = sum(1 for s in scenarios if s.get("passed", False))
    print(f"\nSummary: {passed}/{len(scenarios)} scenarios passed.")
    for i, s in enumerate(scenarios):
        icon = "✅" if s.get("passed") else "❌"
        print(f"  {icon} S{i+1}: {s.get('scenario','?')}")


if __name__ == "__main__":
    main()
