#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Optimization Suite - Master Ultra-Deep High-Resolution Optimization Orchestrator
Executes high-density multi-slice Cartesian grid sweeps, evaluates fine-grained metrics,
determines pinpointed optimal parameters, renders multi-slice parametric charts, and updates the interactive dashboard.
Supports multi-core parallel scaling (--workers N) for high-performance workstations.
"""

import sys
import os
import time
import argparse

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.optimization.deep_cartesian_sweep import execute_ultra_deep_optimization
from PHY2.optimization.plot_deep_analysis import render_deep_analysis_plots
from PHY2.dashboard.build_dashboard import build_master_dashboard

def run(workers=None, output_dir=None, skip_plots=False):
    t0 = time.time()
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Execute Ultra-Deep Multi-Slice Grid
    print(f"[INFO] Launching Ultra-Deep Optimization Grid...")
    execute_ultra_deep_optimization(output_dir, workers=workers)
    
    # 2. Render all multi-slice plots & deep dashboard
    if not skip_plots:
        print(f"[INFO] Generating multi-slice plots and SVG figures...")
        render_deep_analysis_plots(output_dir)
        
    # 3. Update master interactive dashboard
    print(f"[INFO] Updating master interactive dashboard...")
    build_master_dashboard()
    
    elapsed = time.time() - t0
    print(f"\n================================================================================")
    print(f" >>> ULTRA-DEEP OPTIMIZATION & MULTI-SLICE PLOTS COMPLETED IN {elapsed:.2f}s! <<<")
    print(f" Results saved to: {output_dir}")
    print(f"   -> deep_sweep_results.json & csv (Full 0.005..1.000 Range)")
    print(f"   -> pinpoint_optimal_parameters.json")
    print(f"   -> deep_dashboard.html")
    print(f"   -> PHY2/dashboard/index.html (Interactive Dashboard Synchronized)")
    print(f"================================================================================")
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Ultra-Deep Physical Layer Optimizer")
    parser.add_argument('--workers', type=int, default=None, help="Number of parallel CPU worker processes (default: auto)")
    parser.add_argument('--output-dir', type=str, default=None, help="Directory to store optimization results")
    parser.add_argument('--skip-plots', action='store_true', help="Skip SVG chart rendering")
    args = parser.parse_args()
    
    sys.exit(run(workers=args.workers, output_dir=args.output_dir, skip_plots=args.skip_plots))
