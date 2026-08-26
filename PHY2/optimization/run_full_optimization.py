#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Optimization Suite - Master Full Optimization Orchestrator
Executes the full Cartesian product parameter grid across BPSK and QPSK, evaluates metrics,
determines Pareto-optimal parameter sets, and renders multi-dimensional heatmaps and dashboards.
"""

import sys
import os
import time

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.optimization.full_cartesian_sweep import execute_cartesian_optimization
from PHY2.optimization.plot_multidimensional import render_multidimensional_plots

def run():
    t0 = time.time()
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # 1. Execute Cartesian Grid Sweeps
    execute_cartesian_optimization(results_dir)
    
    # 2. Render all multi-dimensional plots & dashboard
    render_multidimensional_plots(results_dir)
    
    elapsed = time.time() - t0
    print(f"\n================================================================================")
    print(f" >>> FULL CARTESIAN OPTIMIZATION COMPLETED IN {elapsed:.2f} SECONDS! <<<")
    print(f" Output Directory: {results_dir}")
    print(f"   -> cartesian_sweep_results.json & csv")
    print(f"   -> optimal_parameters_bpsk.json")
    print(f"   -> optimal_parameters_qpsk.json")
    print(f"   -> chart_01_waterfall_bpsk_qpsk.svg")
    print(f"   -> chart_02_costas_vs_symsync_heatmap_bpsk.svg")
    print(f"   -> chart_03_costas_vs_symsync_heatmap_qpsk.svg")
    print(f"   -> chart_04_fll_vs_freq_offset_heatmap.svg")
    print(f"   -> chart_05_preamble_sensitivity_comparison.svg")
    print(f"   -> dashboard.html")
    print(f"================================================================================")
    return 0

if __name__ == '__main__':
    sys.exit(run())
