#!/usr/bin/env python3
"""
collect_and_chart.py
====================
Merges all results_m{m}_mtu{mtu}.json files into sweep_results.json,
then generates all 6 charts + a printed recommendations table.

Run after run_sweep_all.sh completes:
    python3 tests/perf_sweep/collect_and_chart.py
"""
import glob, json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Load and merge ───────────────────────────────────────────────────────────
def load_all():
    files = sorted(glob.glob(os.path.join(OUT_DIR, 'results_m*.json')))
    if not files:
        print(f'ERROR: No results_m*.json files found in {OUT_DIR}')
        sys.exit(1)

    all_results = []
    m_set = set(); mtu_set = set(); drop_set = set()

    for f in files:
        with open(f) as fp:
            d = json.load(fp)
        for r in d['results']:
            all_results.append(r)
            m_set.add(r['m']); mtu_set.add(r['mtu_bytes']); drop_set.add(r['drop_prob'])

    m_vals   = sorted(m_set)
    mtu_vals = sorted(mtu_set)
    drop_vals= sorted(drop_set)
    print(f'Loaded {len(all_results)} rows from {len(files)} files')
    print(f'  m={m_vals}  mtu={mtu_vals}  drop={drop_vals}')

    merged = {'sweep_config': {
                'files_loaded': len(files),
                'm_values': m_vals, 'mtu_values': mtu_vals, 'drop_values': drop_vals},
              'results': all_results}
    with open(os.path.join(OUT_DIR, 'sweep_results.json'), 'w') as f:
        json.dump(merged, f, indent=2)
    print(f'Merged → sweep_results.json')
    return all_results, m_vals, mtu_vals, drop_vals


def get(results, m, mtu, drop, field, default=0):
    matches = [r for r in results
               if r['m'] == m and r['mtu_bytes'] == mtu
               and abs(r['drop_prob'] - drop) < 1e-6]
    if not matches: return default
    return sum(r.get(field, default) for r in matches) / len(matches)


# ─── Plot style ───────────────────────────────────────────────────────────────
STYLE = {
    'figure.facecolor': '#0f1117', 'axes.facecolor': '#1a1d2e',
    'axes.edgecolor': '#3a3f5c', 'axes.labelcolor': '#c8cce8',
    'axes.titlecolor': '#e0e4ff', 'xtick.color': '#9096b8',
    'ytick.color': '#9096b8', 'text.color': '#c8cce8',
    'grid.color': '#2a2f4a', 'grid.alpha': 0.4,
    'font.family': 'DejaVu Sans', 'font.size': 10,
    'axes.titlesize': 12, 'axes.labelsize': 10,
}
plt.rcParams.update(STYLE)
CMAP_HEAT = mcolors.LinearSegmentedColormap.from_list(
    'dh', ['#1a1d2e', '#2b4a8f', '#4fc38a', '#f5c542', '#e05c5c'])
CMAP_GOOD = mcolors.LinearSegmentedColormap.from_list(
    'dg', ['#1a1d2e', '#1a4a2e', '#4fc38a'])

def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  Saved: {name}')


# ─── Chart 1: Throughput heatmap m×mtu per drop rate ─────────────────────────
def chart_heatmap(results, m_vals, mtu_vals, drop_vals):
    drops = [d for d in drop_vals if d in [0.0, 0.15, 0.30, 0.50]] or drop_vals[:4]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    fig.suptitle('Throughput (kB/s) — m × MTU per Drop Rate',
                 fontsize=15, color='#e0e4ff', fontweight='bold')
    axes_flat = axes.flatten()
    all_vals = [get(results,m,mtu,d,'throughput_kbps')
                for d in drops for m in m_vals for mtu in mtu_vals]
    vmax = max(all_vals) if all_vals else 1

    for ax_idx, drop in enumerate(drops[:4]):
        ax = axes_flat[ax_idx]
        Z  = np.array([[get(results,m,mtu,drop,'throughput_kbps')
                        for mtu in mtu_vals] for m in m_vals])
        im = ax.imshow(Z, cmap=CMAP_HEAT, aspect='auto', vmin=0, vmax=vmax)
        fig.colorbar(im, ax=ax, shrink=0.85).set_label('kB/s', color='#9096b8')
        ax.set_xticks(range(len(mtu_vals)))
        ax.set_xticklabels([f'{v}B' for v in mtu_vals])
        ax.set_yticks(range(len(m_vals)))
        ax.set_yticklabels([f'm={m} W={2**(m-1)}' for m in m_vals])
        ax.set_xlabel('MTU (bytes/frame)'); ax.set_ylabel('m')
        ax.set_title(f'Drop = {drop:.0%}')
        for i in range(len(m_vals)):
            for j in range(len(mtu_vals)):
                v = Z[i,j]
                ax.text(j, i, f'{v:.0f}', ha='center', va='center',
                        color='white' if v < vmax*0.7 else '#0f1117',
                        fontsize=9, fontweight='bold')
    save(fig, 'chart_01_throughput_heatmap.png')


# ─── Chart 2: Throughput vs drop_prob ────────────────────────────────────────
def chart_tput_vs_drop(results, m_vals, mtu_vals, drop_vals):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle('Throughput vs Drop Probability', fontsize=15,
                 color='#e0e4ff', fontweight='bold')
    pal = plt.cm.plasma(np.linspace(0.15, 0.9, len(m_vals)))

    ax = axes[0]
    for i, m in enumerate(m_vals):
        best_mtu = max(mtu_vals, key=lambda mtu:
                       get(results, m, mtu, 0.0, 'throughput_kbps'))
        ys = [get(results,m,best_mtu,d,'throughput_kbps') for d in drop_vals]
        ax.plot(drop_vals, ys, 'o-', color=pal[i], linewidth=2,
                label=f'm={m} W={2**(m-1)} mtu={best_mtu}B', markersize=6)
    ax.set_xlabel('Drop Probability'); ax.set_ylabel('Throughput (kB/s)')
    ax.set_title('Best MTU per m'); ax.legend(fontsize=8); ax.grid(True)

    ax2 = axes[1]
    for i, m in enumerate(m_vals):
        ys_all = [[get(results,m,mtu,d,'throughput_kbps')
                   for d in drop_vals] for mtu in mtu_vals]
        y_mean = np.mean(ys_all, axis=0)
        y_min  = np.min(ys_all, axis=0)
        y_max  = np.max(ys_all, axis=0)
        c = pal[i]
        ax2.plot(drop_vals, y_mean, 'o-', color=c, linewidth=2,
                 label=f'm={m} W={2**(m-1)}', markersize=5)
        ax2.fill_between(drop_vals, y_min, y_max, color=c, alpha=0.15)
    ax2.set_xlabel('Drop Probability'); ax2.set_ylabel('Throughput (kB/s)')
    ax2.set_title('Mean ± Range Across MTU'); ax2.legend(fontsize=8); ax2.grid(True)
    save(fig, 'chart_02_throughput_vs_drop.png')


# ─── Chart 3: Success rate heatmap ───────────────────────────────────────────
def chart_success(results, m_vals, mtu_vals, drop_vals):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle('Delivery Success Rate', fontsize=15,
                 color='#e0e4ff', fontweight='bold')
    for ax_idx, (ax, use_best) in enumerate(zip(axes, [False, True])):
        Z = np.zeros((len(m_vals), len(drop_vals)))
        for i, m in enumerate(m_vals):
            for j, drop in enumerate(drop_vals):
                rates = [get(results,m,mtu,drop,'success_rate') for mtu in mtu_vals]
                Z[i,j] = max(rates) if use_best else np.mean(rates)
        im = ax.imshow(Z, cmap=CMAP_GOOD, aspect='auto', vmin=0, vmax=1)
        fig.colorbar(im, ax=ax, shrink=0.85).set_label('Success Rate', color='#9096b8')
        ax.set_xticks(range(len(drop_vals)))
        ax.set_xticklabels([f'{d:.0%}' for d in drop_vals])
        ax.set_yticks(range(len(m_vals)))
        ax.set_yticklabels([f'm={m} W={2**(m-1)}' for m in m_vals])
        ax.set_xlabel('Drop Probability')
        ax.set_title('Best MTU' if use_best else 'Avg over MTU')
        for i in range(len(m_vals)):
            for j in range(len(drop_vals)):
                ax.text(j, i, f'{Z[i,j]:.0%}', ha='center', va='center',
                        color='white' if Z[i,j]<0.6 else '#0f1117',
                        fontsize=9, fontweight='bold')
    save(fig, 'chart_03_success_rate.png')


# ─── Chart 4: Overhead ratio ─────────────────────────────────────────────────
def chart_overhead(results, m_vals, mtu_vals, drop_vals):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle('Protocol Overhead vs Drop Rate', fontsize=15,
                 color='#e0e4ff', fontweight='bold')
    pal = plt.cm.plasma(np.linspace(0.15, 0.9, len(m_vals)))

    ax = axes[0]
    for i, m in enumerate(m_vals):
        ys = [np.mean([get(results,m,mtu,d,'overhead_ratio') for mtu in mtu_vals])
              for d in drop_vals]
        ax.plot(drop_vals, ys, 'o-', color=pal[i], linewidth=2,
                label=f'm={m} W={2**(m-1)}', markersize=6)
    ax.axhline(1.0, color='#9096b8', linestyle='--', linewidth=1,
               label='Ideal (1.0)')
    ax.set_xlabel('Drop Probability'); ax.set_ylabel('Overhead Ratio')
    ax.set_title('PDUs sent / Minimum required')
    ax.legend(fontsize=8); ax.grid(True)

    ax2 = axes[1]
    for i, m in enumerate(m_vals):
        pal2 = plt.cm.viridis(np.linspace(0.2, 0.9, len(mtu_vals)))
        for j, mtu in enumerate(mtu_vals):
            ys = [get(results,m,mtu,d,'overhead_ratio') for d in drop_vals]
            ax2.plot(drop_vals, ys, '.-', color=pal2[j], linewidth=1.5,
                     label=f'm={m} mtu={mtu}B', alpha=0.7, markersize=5)
    ax2.set_xlabel('Drop Probability'); ax2.set_ylabel('Overhead Ratio')
    ax2.set_title('All (m, mtu) combinations')
    ax2.grid(True)
    save(fig, 'chart_04_overhead.png')


# ─── Chart 5: MTU effect ─────────────────────────────────────────────────────
def chart_mtu_effect(results, m_vals, mtu_vals, drop_vals):
    m_show = 5 if 5 in m_vals else m_vals[len(m_vals)//2]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle(f'MTU Effect (m={m_show}, W={2**(m_show-1)})',
                 fontsize=15, color='#e0e4ff', fontweight='bold')
    pal = plt.cm.viridis(np.linspace(0.2, 0.9, len(mtu_vals)))
    ax = axes[0]
    for j, mtu in enumerate(mtu_vals):
        ys = [get(results,m_show,mtu,d,'throughput_kbps') for d in drop_vals]
        ax.plot(drop_vals, ys, 'o-', color=pal[j], linewidth=2,
                label=f'{mtu}B/frame', markersize=6)
    ax.set_xlabel('Drop Probability'); ax.set_ylabel('Throughput (kB/s)')
    ax.set_title('Throughput vs Loss per MTU')
    ax.legend(fontsize=8); ax.grid(True)
    ax2 = axes[1]
    for j, mtu in enumerate(mtu_vals):
        ys = [get(results,m_show,mtu,d,'success_rate') for d in drop_vals]
        ax2.plot(drop_vals, ys, 'o-', color=pal[j], linewidth=2,
                 label=f'{mtu}B/frame', markersize=6)
    ax2.set_xlabel('Drop Probability'); ax2.set_ylabel('Success Rate')
    ax2.set_title('Success Rate vs Loss per MTU')
    ax2.legend(fontsize=8); ax2.grid(True)
    save(fig, 'chart_05_mtu_effect.png')


# ─── Chart 6: Recommendations ────────────────────────────────────────────────
def chart_recommendations(results, m_vals, mtu_vals, drop_vals):
    conditions = [
        ('Clean\n(0%)',    0.00), ('Light\n(5%)',   0.05),
        ('Moderate\n(15%)',0.15), ('Heavy\n(30%)',  0.30),
        ('Extreme\n(50%)', 0.50),
    ]
    best_cfgs = []; best_tputs = []; fallback_tputs = []
    for label, drop in conditions:
        cands = [(get(results,m,mtu,drop,'throughput_kbps'), m, mtu)
                 for m in m_vals for mtu in mtu_vals
                 if get(results,m,mtu,drop,'success_rate') >= 0.6]
        if cands:
            bt, bm, bmtu = max(cands)
            best_cfgs.append(f'm={bm}\nW={2**(bm-1)}\nmtu={bmtu}B')
            best_tputs.append(bt)
        else:
            best_cfgs.append('No reliable\nconfig'); best_tputs.append(0)
        all_t = [get(results,m,mtu,drop,'throughput_kbps')
                 for m in m_vals for mtu in mtu_vals]
        fallback_tputs.append(max(all_t) if all_t else 0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 7), constrained_layout=True)
    fig.suptitle('Recommended Configuration per Channel Condition',
                 fontsize=15, color='#e0e4ff', fontweight='bold')
    x = np.arange(len(conditions)); w = 0.55
    colors = ['#4fc38a' if t > 0 else '#e05c5c' for t in best_tputs]
    ax = axes[0]
    ax.bar(x, fallback_tputs, w, color='#3a3f5c', edgecolor='#2a2f4a',
           linewidth=1.2, alpha=0.4, label='Best possible (any success)')
    bars = ax.bar(x, best_tputs, w, color=colors, edgecolor='#2a2f4a', linewidth=1.2)
    for bar, cfg, tpt in zip(bars, best_cfgs, best_tputs):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                cfg, ha='center', va='bottom', fontsize=8, color='#e0e4ff')
        if tpt > 0:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()/2,
                    f'{tpt:.0f}\nkB/s', ha='center', va='center',
                    fontsize=9, color='white', fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels([c[0] for c in conditions])
    ax.set_ylabel('Throughput (kB/s)')
    ax.set_title('Best Config with ≥60% Success Rate')
    ax.legend(fontsize=8); ax.grid(True, axis='y')

    ax2 = axes[1]
    top3 = sorted([(get(results,m,mtu,0.0,'throughput_kbps'),m,mtu)
                   for m in m_vals for mtu in mtu_vals], reverse=True)[:3]
    p3 = plt.cm.plasma(np.linspace(0.2, 0.8, 3))
    for ci, (_, m, mtu) in enumerate(top3):
        ys = [get(results,m,mtu,d,'success_rate')*100 for d in drop_vals]
        ax2.plot(drop_vals, ys, 'o-', color=p3[ci], linewidth=2.5,
                 label=f'm={m} mtu={mtu}B', markersize=7)
    ax2.axhline(60, color='#f5c542', linestyle='--', linewidth=1, label='60% threshold')
    ax2.axhline(80, color='#9096b8', linestyle='--', linewidth=1, label='80% threshold')
    ax2.set_xlabel('Drop Probability'); ax2.set_ylabel('Success Rate (%)')
    ax2.set_title('Success Rate for Top-3 Throughput Configs')
    ax2.legend(fontsize=8); ax2.grid(True); ax2.set_ylim(-5, 105)
    save(fig, 'chart_06_recommendations.png')


# ─── Recommendations table ───────────────────────────────────────────────────
def print_table(results, m_vals, mtu_vals, drop_vals):
    conditions = [
        ('Clean    (0%)',    0.00), ('Light    (5%)',    0.05),
        ('Moderate (15%)',   0.15), ('Heavy    (30%)',   0.30),
        ('Extreme  (50%)',   0.50),
    ]
    print('\n' + '═'*70)
    print('  PARAMETER RECOMMENDATIONS')
    print('═'*70)
    print(f"  {'Channel':<18} {'m':>4} {'MTU':>7} {'Window':>7} {'Tput':>10} {'Success':>8}")
    print('  ' + '─'*66)
    for label, drop in conditions:
        best = None
        for m in m_vals:
            for mtu in mtu_vals:
                sr  = get(results, m, mtu, drop, 'success_rate')
                tpt = get(results, m, mtu, drop, 'throughput_kbps')
                if sr >= 0.6:
                    if best is None or tpt > best[0]:
                        best = (tpt, m, mtu, sr)
        if best:
            tpt, m, mtu, sr = best
            print(f"  {label:<18} {m:>4} {mtu:>6}B {2**(m-1):>7}  {tpt:>8.1f} kB/s  {sr:>6.0%}")
        else:
            print(f"  {label:<18} {'—':>4} {'—':>7} {'—':>7}  {'N/A':>10}  {'<60%':>7}")
    print('═'*70 + '\n')


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    results, m_vals, mtu_vals, drop_vals = load_all()
    print('\nGenerating charts...')
    chart_heatmap(results, m_vals, mtu_vals, drop_vals)
    chart_tput_vs_drop(results, m_vals, mtu_vals, drop_vals)
    chart_success(results, m_vals, mtu_vals, drop_vals)
    chart_overhead(results, m_vals, mtu_vals, drop_vals)
    chart_mtu_effect(results, m_vals, mtu_vals, drop_vals)
    chart_recommendations(results, m_vals, mtu_vals, drop_vals)
    print_table(results, m_vals, mtu_vals, drop_vals)
    print(f'All charts written to: {OUT_DIR}')

if __name__ == '__main__':
    main()
