#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Optimization Suite - Master Ultra-Deep High-Resolution Optimization Orchestrator
Executes high-density multi-slice Cartesian grid sweeps, evaluates fine-grained metrics,
determines pinpointed optimal parameters, and renders multi-slice parametric charts.
"""

import sys
import os
import time

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.optimization.deep_cartesian_sweep import execute_ultra_deep_optimization
from PHY2.optimization.plot_deep_analysis import render_deep_analysis_plots

def run():
    t0 = time.time()
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # 1. Execute Ultra-Deep Multi-Slice Grid
    execute_ultra_deep_optimization(results_dir)
    
    # 2. Render all multi-slice plots & deep dashboard
    render_deep_analysis_plots(results_dir)
    
    elapsed = time.time() - t0
    print(f"\n================================================================================")
    print(f" >>> ULTRA-DEEP OPTIMIZATION & MULTI-SLICE PLOTS COMPLETED IN {elapsed:.2f}s! <<<")
    print(f" Results saved to: {results_dir}")
    print(f"   -> deep_sweep_results.json & csv")
    print(f"   -> pinpoint_optimal_parameters.json")
    print(f"   -> chart_slice_01_fixed_fll_ber_vs_symsync_bpsk.svg & qpsk.svg")
    print(f"   -> chart_slice_02_fixed_costas_ber_vs_fll_bpsk.svg & qpsk.svg")
    print(f"   -> chart_slice_03_fixed_symsync_pdr_vs_noise_bpsk.svg & qpsk.svg")
    print(f"   -> chart_slice_04_software_vs_hardware_comparison.svg")
    print(f"   -> deep_dashboard.html")
    print(f"================================================================================")
    return 0

if __name__ == '__main__':
    sys.exit(run())
