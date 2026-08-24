#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sweep_charts.py — Transport Layer Sweep — Chart Generator
==========================================================
Reads sweep_results.json (produced by sweep_test.py) and generates
5 chart files plus a printed recommendations table.

Charts produced
---------------
  chart_01_throughput_heatmap.png  — kB/s heatmap: m vs mtu_bytes per drop rate
  chart_02_throughput_vs_drop.png  — throughput curves vs drop_prob per m value
  chart_03_success_rate.png        — delivery success % heatmap: m vs drop_prob
  chart_04_retx_overhead.png       — retransmit events per session vs drop_prob
  chart_05_overhead_ratio.png      — protocol overhead ratio heatmap
  chart_06_recommendations.png     — best config per channel condition (bar chart)

Usage
-----
  python3 tests/perf_sweep/sweep_charts.py
"""

import json
import os

import matplotlib
matplotlib.use("Agg")   # headless — no display required
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
OUT_DIR   = os.path.dirname(__file__)
JSON_PATH = os.path.join(OUT_DIR, "sweep_results.json")

STYLE = {
    "figure.facecolor": "#0f1117",
    "axes.facecolor":   "#1a1d2e",
    "axes.edgecolor":   "#3a3f5c",
    "axes.labelcolor":  "#c8cce8",
    "axes.titlecolor":  "#e0e4ff",
    "xtick.color":      "#9096b8",
    "ytick.color":      "#9096b8",
    "text.color":       "#c8cce8",
    "grid.color":       "#2a2f4a",
    "grid.alpha":       0.4,
    "font.family":      "DejaVu Sans",
    "font.size":        10,
    "axes.titlesize":   12,
    "axes.labelsize":   10,
}
plt.rcParams.update(STYLE)

ACCENT = "#6c8ef5"
GOOD   = "#4fc38a"
WARN   = "#f5c542"
BAD    = "#e05c5c"

CMAP_HEAT   = mcolors.LinearSegmentedColormap.from_list(
    "dark_heat", ["#1a1d2e", "#2b4a8f", "#4fc38a", "#f5c542", "#e05c5c"])
CMAP_GOOD   = mcolors.LinearSegmentedColormap.from_list(
    "dark_good", ["#1a1d2e", "#1a4a2e", "#4fc38a"])
CMAP_RISK   = mcolors.LinearSegmentedColormap.from_list(
    "dark_risk", ["#4fc38a", "#f5c542", "#e05c5c"])

# ─────────────────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────────────────
def load():
    with open(JSON_PATH) as f:
        d = json.load(f)
    results  = d["results"]
    cfg      = d["sweep_config"]
    m_vals   = sorted(set(r["m"]         for r in results))
    mtu_vals = sorted(set(r["mtu_bytes"] for r in results))
    drop_vals= sorted(set(r["drop_prob"] for r in results))
    return results, cfg, m_vals, mtu_vals, drop_vals


def get(results, m, mtu, drop, field):
    for r in results:
        if r["m"] == m and r["mtu_bytes"] == mtu and abs(r["drop_prob"] - drop) < 1e-6:
            return r.get(field, 0)
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Chart 1 — Throughput heatmap: m × mtu for each drop rate
# ─────────────────────────────────────────────────────────────────────────────
def chart_throughput_heatmap(results, m_vals, mtu_vals, drop_vals):
    drop_subset = [d for d in drop_vals if d in [0.0, 0.15, 0.30, 0.50]]
    ncols = 2
    nrows = (len(drop_subset) + 1) // 2

    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(14, 5 * nrows),
                             constrained_layout=True)
    fig.suptitle("Throughput (kB/s)  —  m × MTU  per Drop Rate",
                 fontsize=15, color="#e0e4ff", fontweight="bold")

    axes_flat = axes.flatten() if nrows > 1 else axes

    for ax_idx, drop in enumerate(drop_subset):
        ax = axes_flat[ax_idx]
        Z  = np.zeros((len(m_vals), len(mtu_vals)))
        for i, m in enumerate(m_vals):
            for j, mtu in enumerate(mtu_vals):
                Z[i, j] = get(results, m, mtu, drop, "throughput_kbps")

        im = ax.imshow(Z, cmap=CMAP_HEAT, aspect="auto",
                       vmin=0, vmax=Z.max() + 0.1)
        cbar = fig.colorbar(im, ax=ax, shrink=0.85)
        cbar.set_label("kB/s", color="#9096b8")
        cbar.ax.yaxis.set_tick_params(color="#9096b8")
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#9096b8")

        ax.set_xticks(range(len(mtu_vals)))
        ax.set_xticklabels([f"{v} B" for v in mtu_vals])
        ax.set_yticks(range(len(m_vals)))
        ax.set_yticklabels([f"m={m}  (W={2**(m-1)})" for m in m_vals])
        ax.set_xlabel("MTU (bytes/frame)")
        ax.set_ylabel("m (window size)")
        ax.set_title(f"Drop Prob = {drop:.0%}")

        for i in range(len(m_vals)):
            for j in range(len(mtu_vals)):
                val = Z[i, j]
                ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                        color="white" if val < Z.max() * 0.7 else "#0f1117",
                        fontsize=9, fontweight="bold")

    # Hide unused subplots
    for idx in range(len(drop_subset), len(axes_flat)):
        axes_flat[idx].set_visible(False)

    path = os.path.join(OUT_DIR, "chart_01_throughput_heatmap.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Chart 2 — Throughput vs drop_prob, one line per m (best mtu per m)
# ─────────────────────────────────────────────────────────────────────────────
def chart_throughput_vs_drop(results, m_vals, mtu_vals, drop_vals):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle("Throughput vs Drop Probability",
                 fontsize=15, color="#e0e4ff", fontweight="bold")

    palette = plt.cm.plasma(np.linspace(0.15, 0.9, len(m_vals)))

    # Left: best-mtu line per m
    ax = axes[0]
    for m_idx, m in enumerate(m_vals):
        # Find best mtu at drop=0 for this m
        best_mtu = max(mtu_vals,
                       key=lambda mtu: get(results, m, mtu, 0.0, "throughput_kbps"))
        ys  = [get(results, m, best_mtu, d, "throughput_kbps") for d in drop_vals]
        ax.plot(drop_vals, ys, "o-", color=palette[m_idx], linewidth=2,
                label=f"m={m} W={2**(m-1)} (mtu={best_mtu}B)",
                markersize=6)

    ax.set_xlabel("Drop Probability")
    ax.set_ylabel("Throughput (kB/s)")
    ax.set_title("Best MTU per m, vs Loss Rate")
    ax.legend(fontsize=8)
    ax.grid(True)
    ax.set_xlim(-0.01, 0.52)

    # Right: all (m, mtu) combinations for a fixed drop
    ax2 = axes[1]
    for m_idx, m in enumerate(m_vals):
        ys_all  = [[get(results, m, mtu, d, "throughput_kbps")
                    for d in drop_vals] for mtu in mtu_vals]
        y_mean  = np.mean(ys_all, axis=0)
        y_min   = np.min(ys_all, axis=0)
        y_max   = np.max(ys_all, axis=0)
        c = palette[m_idx]
        ax2.plot(drop_vals, y_mean, "o-", color=c, linewidth=2,
                 label=f"m={m} (W={2**(m-1)})", markersize=5)
        ax2.fill_between(drop_vals, y_min, y_max, color=c, alpha=0.15)

    ax2.set_xlabel("Drop Probability")
    ax2.set_ylabel("Throughput (kB/s)")
    ax2.set_title("Mean ± Range Across All MTU Values")
    ax2.legend(fontsize=8)
    ax2.grid(True)
    ax2.set_xlim(-0.01, 0.52)

    path = os.path.join(OUT_DIR, "chart_02_throughput_vs_drop.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Chart 3 — Delivery success rate heatmap: m × drop_prob
# ─────────────────────────────────────────────────────────────────────────────
def chart_success_rate(results, m_vals, mtu_vals, drop_vals):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle("Delivery Success Rate  (fraction of 5 pairs delivered)",
                 fontsize=15, color="#e0e4ff", fontweight="bold")

    # Left: averaged over all mtu values
    ax = axes[0]
    Z  = np.zeros((len(m_vals), len(drop_vals)))
    for i, m in enumerate(m_vals):
        for j, drop in enumerate(drop_vals):
            rates = [get(results, m, mtu, drop, "success_rate") for mtu in mtu_vals]
            Z[i, j] = np.mean(rates)

    im = ax.imshow(Z, cmap=CMAP_GOOD, aspect="auto", vmin=0, vmax=1)
    fig.colorbar(im, ax=ax, shrink=0.85).set_label("Success Rate", color="#9096b8")
    ax.set_xticks(range(len(drop_vals)))
    ax.set_xticklabels([f"{d:.0%}" for d in drop_vals])
    ax.set_yticks(range(len(m_vals)))
    ax.set_yticklabels([f"m={m} W={2**(m-1)}" for m in m_vals])
    ax.set_xlabel("Drop Probability")
    ax.set_ylabel("m value")
    ax.set_title("Success Rate (avg over MTU values)")
    for i in range(len(m_vals)):
        for j in range(len(drop_vals)):
            ax.text(j, i, f"{Z[i,j]:.0%}", ha="center", va="center",
                    color="white" if Z[i,j] < 0.6 else "#0f1117",
                    fontsize=9, fontweight="bold")

    # Right: best mtu only
    ax2 = axes[1]
    Z2  = np.zeros((len(m_vals), len(drop_vals)))
    for i, m in enumerate(m_vals):
        for j, drop in enumerate(drop_vals):
            rates = [get(results, m, mtu, drop, "success_rate") for mtu in mtu_vals]
            Z2[i, j] = max(rates)

    im2 = ax2.imshow(Z2, cmap=CMAP_GOOD, aspect="auto", vmin=0, vmax=1)
    fig.colorbar(im2, ax=ax2, shrink=0.85).set_label("Success Rate", color="#9096b8")
    ax2.set_xticks(range(len(drop_vals)))
    ax2.set_xticklabels([f"{d:.0%}" for d in drop_vals])
    ax2.set_yticks(range(len(m_vals)))
    ax2.set_yticklabels([f"m={m} W={2**(m-1)}" for m in m_vals])
    ax2.set_xlabel("Drop Probability")
    ax2.set_title("Success Rate (best MTU per m)")
    for i in range(len(m_vals)):
        for j in range(len(drop_vals)):
            ax2.text(j, i, f"{Z2[i,j]:.0%}", ha="center", va="center",
                     color="white" if Z2[i,j] < 0.6 else "#0f1117",
                     fontsize=9, fontweight="bold")

    path = os.path.join(OUT_DIR, "chart_03_success_rate.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Chart 4 — Retransmit overhead per delivered session vs drop_prob
# ─────────────────────────────────────────────────────────────────────────────
def chart_retx_overhead(results, m_vals, mtu_vals, drop_vals):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle("Retransmission Overhead vs Drop Probability",
                 fontsize=15, color="#e0e4ff", fontweight="bold")

    palette = plt.cm.plasma(np.linspace(0.15, 0.9, len(m_vals)))

    # Left: retx events (raw count, averaged over MTU)
    ax = axes[0]
    for m_idx, m in enumerate(m_vals):
        ys = []
        for drop in drop_vals:
            vals = [get(results, m, mtu, drop, "retransmit_events") for mtu in mtu_vals]
            ys.append(np.mean(vals))
        ax.plot(drop_vals, ys, "o-", color=palette[m_idx], linewidth=2,
                label=f"m={m} W={2**(m-1)}", markersize=6)
    ax.set_xlabel("Drop Probability")
    ax.set_ylabel("Retransmit Events (avg over MTU)")
    ax.set_title("Raw Retransmit Count")
    ax.legend(fontsize=8)
    ax.grid(True)

    # Right: protocol overhead ratio
    ax2 = axes[1]
    for m_idx, m in enumerate(m_vals):
        ys = []
        for drop in drop_vals:
            vals = [get(results, m, mtu, drop, "overhead_ratio") for mtu in mtu_vals]
            ys.append(np.mean(vals))
        ax2.plot(drop_vals, ys, "o-", color=palette[m_idx], linewidth=2,
                 label=f"m={m} W={2**(m-1)}", markersize=6)
    ax2.axhline(1.0, color="#9096b8", linestyle="--", linewidth=1,
                label="Ideal (no overhead)")
    ax2.set_xlabel("Drop Probability")
    ax2.set_ylabel("PDUs sent / Theoretical minimum")
    ax2.set_title("Protocol Overhead Ratio (1.0 = perfect)")
    ax2.legend(fontsize=8)
    ax2.grid(True)

    path = os.path.join(OUT_DIR, "chart_04_retx_overhead.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Chart 5 — MTU effect on throughput (fixed m, vary mtu across drop)
# ─────────────────────────────────────────────────────────────────────────────
def chart_mtu_effect(results, m_vals, mtu_vals, drop_vals):
    # Pick m=5 as representative middle value
    m_show = 5 if 5 in m_vals else m_vals[len(m_vals)//2]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle(f"MTU Effect on Throughput (m={m_show}, W={2**(m_show-1)})",
                 fontsize=15, color="#e0e4ff", fontweight="bold")

    palette = plt.cm.viridis(np.linspace(0.2, 0.9, len(mtu_vals)))

    # Left: throughput vs drop_prob per MTU
    ax = axes[0]
    for mtu_idx, mtu in enumerate(mtu_vals):
        ys = [get(results, m_show, mtu, d, "throughput_kbps") for d in drop_vals]
        ax.plot(drop_vals, ys, "o-", color=palette[mtu_idx], linewidth=2,
                label=f"{mtu} B/frame", markersize=6)
    ax.set_xlabel("Drop Probability")
    ax.set_ylabel("Throughput (kB/s)")
    ax.set_title("Throughput vs Loss (per MTU)")
    ax.legend(fontsize=8)
    ax.grid(True)

    # Right: session time vs drop_prob per MTU
    ax2 = axes[1]
    for mtu_idx, mtu in enumerate(mtu_vals):
        ys = [get(results, m_show, mtu, d, "session_time_s") for d in drop_vals]
        ax2.plot(drop_vals, ys, "o-", color=palette[mtu_idx], linewidth=2,
                 label=f"{mtu} B/frame", markersize=6)
    ax2.set_xlabel("Drop Probability")
    ax2.set_ylabel("Session Time (s)")
    ax2.set_title("Session Completion Time vs Loss (per MTU)")
    ax2.legend(fontsize=8)
    ax2.grid(True)

    path = os.path.join(OUT_DIR, "chart_05_mtu_effect.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Chart 6 — Recommendations bar chart
# ─────────────────────────────────────────────────────────────────────────────
def chart_recommendations(results, m_vals, mtu_vals, drop_vals):
    """
    For each channel condition (drop rate bucket), find the (m, mtu) combination
    that maximises throughput while maintaining success_rate >= 0.8.
    """
    conditions = [
        ("Clean\n(0%)",    0.00),
        ("Light\n(5%)",    0.05),
        ("Moderate\n(15%)", 0.15),
        ("Heavy\n(30%)",   0.30),
        ("Extreme\n(50%)", 0.50),
    ]

    best_configs   = []
    best_tputs     = []
    best_labels    = []
    fallback_tputs = []

    for label, drop in conditions:
        # Find best (m, mtu) with success_rate >= 0.8
        candidates = []
        for m in m_vals:
            for mtu in mtu_vals:
                sr  = get(results, m, mtu, drop, "success_rate")
                tpt = get(results, m, mtu, drop, "throughput_kbps")
                if sr >= 0.8:
                    candidates.append((tpt, m, mtu))
        if candidates:
            best_tpt, best_m, best_mtu = max(candidates)
            best_configs.append(f"m={best_m}\nW={2**(best_m-1)}\nmtu={best_mtu}B")
            best_tputs.append(best_tpt)
        else:
            best_configs.append("No config\nreliable")
            best_tputs.append(0)

        # Fallback: best throughput regardless of success rate
        all_tputs = [(get(results, m, mtu, drop, "throughput_kbps"), m, mtu)
                     for m in m_vals for mtu in mtu_vals]
        fallback_tputs.append(max(t for t, _, _ in all_tputs))
        best_labels.append(label)

    fig, axes = plt.subplots(1, 2, figsize=(14, 7), constrained_layout=True)
    fig.suptitle("Recommended Configuration per Channel Condition",
                 fontsize=15, color="#e0e4ff", fontweight="bold")

    x      = np.arange(len(conditions))
    width  = 0.55
    colors = [GOOD if t > 0 else BAD for t in best_tputs]

    ax = axes[0]
    bars = ax.bar(x, best_tputs, width, color=colors, edgecolor="#2a2f4a", linewidth=1.2)
    ax.bar(x, fallback_tputs, width, color="#3a3f5c", edgecolor="#2a2f4a",
           linewidth=1.2, alpha=0.4, label="Best possible (any success rate)")
    for bar, cfg, tpt in zip(bars, best_configs, best_tputs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                cfg, ha="center", va="bottom", fontsize=8, color="#e0e4ff")
        if tpt > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                    f"{tpt:.0f}\nkB/s", ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(best_labels)
    ax.set_ylabel("Throughput (kB/s)")
    ax.set_title("Best Config with ≥80% Success Rate")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y")

    # Right: success rate comparison of top-3 configs across drop rates
    ax2 = axes[1]
    # Pick top-3 configs from the clean-channel ranking
    top3 = []
    for m in m_vals:
        for mtu in mtu_vals:
            tpt = get(results, m, mtu, 0.0, "throughput_kbps")
            top3.append((tpt, m, mtu))
    top3 = sorted(top3, reverse=True)[:3]
    p3   = plt.cm.plasma(np.linspace(0.2, 0.8, 3))
    for ci, (_, m, mtu) in enumerate(top3):
        ys = [get(results, m, mtu, d, "success_rate") * 100 for d in drop_vals]
        ax2.plot(drop_vals, ys, "o-", color=p3[ci], linewidth=2.5,
                 label=f"m={m} mtu={mtu}B", markersize=7)
    ax2.axhline(80, color="#9096b8", linestyle="--", linewidth=1, label="80% threshold")
    ax2.set_xlabel("Drop Probability")
    ax2.set_ylabel("Success Rate (%)")
    ax2.set_title("Success Rate for Top-3 Throughput Configs")
    ax2.legend(fontsize=8)
    ax2.grid(True)
    ax2.set_ylim(-5, 105)

    path = os.path.join(OUT_DIR, "chart_06_recommendations.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Print recommendations table
# ─────────────────────────────────────────────────────────────────────────────
def print_recommendations(results, m_vals, mtu_vals, drop_vals):
    conditions = [
        ("Clean    (0%)",    0.00),
        ("Light    (5%)",    0.05),
        ("Moderate (15%)",   0.15),
        ("Heavy    (30%)",   0.30),
        ("Extreme  (50%)",   0.50),
    ]
    print("\n" + "═" * 68)
    print("  PARAMETER RECOMMENDATIONS")
    print("═" * 68)
    print(f"  {'Channel':<18} {'Rec m':>6} {'Rec MTU':>9} {'Window':>7} {'Tput':>9} {'Success':>8}")
    print("  " + "─" * 64)
    for label, drop in conditions:
        best = None
        for m in m_vals:
            for mtu in mtu_vals:
                sr  = get(results, m, mtu, drop, "success_rate")
                tpt = get(results, m, mtu, drop, "throughput_kbps")
                if sr >= 0.8:
                    if best is None or tpt > best[0]:
                        best = (tpt, m, mtu, sr)
        if best:
            tpt, m, mtu, sr = best
            print(f"  {label:<18} {m:>6} {mtu:>8}B {2**(m-1):>7}  {tpt:>7.1f} kB/s  {sr:>6.0%}")
        else:
            print(f"  {label:<18} {'—':>6} {'—':>9} {'—':>7}  {'N/A':>9}  {'<80%':>6}")
    print("═" * 68 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(JSON_PATH):
        print(f"ERROR: {JSON_PATH} not found. Run sweep_test.py first.")
        return

    print(f"Loading results from: {JSON_PATH}")
    results, cfg, m_vals, mtu_vals, drop_vals = load()
    print(f"  Loaded {len(results)} rows  |  "
          f"m={m_vals}  mtu={mtu_vals}  drop={drop_vals}\n")

    print("Generating charts...")
    chart_throughput_heatmap(results, m_vals, mtu_vals, drop_vals)
    chart_throughput_vs_drop(results, m_vals, mtu_vals, drop_vals)
    chart_success_rate(results, m_vals, mtu_vals, drop_vals)
    chart_retx_overhead(results, m_vals, mtu_vals, drop_vals)
    chart_mtu_effect(results, m_vals, mtu_vals, drop_vals)
    chart_recommendations(results, m_vals, mtu_vals, drop_vals)

    print_recommendations(results, m_vals, mtu_vals, drop_vals)
    print(f"All charts written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
