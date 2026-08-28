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

def run(workers=None, output_dir=None, skip_plots=False, preset="fast", custom_config=None):
    t0 = time.time()
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Execute Optimization Grid with selected preset
    print(f"[INFO] Launching Optimization Grid [Preset: {preset.upper()}]...")
    execute_ultra_deep_optimization(output_dir, workers=workers, preset=preset, custom_config=custom_config)
    
    # 2. Render all multi-slice plots & deep dashboard
    if not skip_plots:
        print(f"[INFO] Generating multi-slice plots and SVG figures...")
        try:
            render_deep_analysis_plots(output_dir)
        except Exception as e:
            print(f"[WARN] Plot generator note: {e}")
        
    # 3. Update master interactive dashboard
    print(f"[INFO] Updating master interactive dashboard...")
    build_master_dashboard()
    
    elapsed = time.time() - t0
    print(f"\n================================================================================")
    print(f" >>> OPTIMIZATION & DASHBOARD UPDATE COMPLETED IN {elapsed:.2f}s! <<<")
    print(f" Results saved to: {output_dir}")
    print(f"   -> deep_sweep_results.json & csv")
    print(f"   -> pinpoint_optimal_parameters.json")
    print(f"   -> PHY2/dashboard/software_dashboard.html & index.html (Ready)")
    print(f"================================================================================")
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Physical Layer Optimizer")
    parser.add_argument('--preset', type=str, default='fast', choices=['fast', 'standard', 'exhaustive', 'custom'],
                        help="Optimization sweep preset: fast (~12k trials), standard (~45k trials), exhaustive (700k+ trials), custom")
    parser.add_argument('--workers', type=int, default=None, help="Number of parallel CPU worker processes (default: auto)")
    parser.add_argument('--output-dir', type=str, default=None, help="Directory to store optimization results")
    parser.add_argument('--skip-plots', action='store_true', help="Skip SVG chart rendering")
    parser.add_argument('--custom-config', type=str, default=None, help="Path to custom config JSON file")
    args = parser.parse_args()
    
    sys.exit(run(workers=args.workers, output_dir=args.output_dir, skip_plots=args.skip_plots, preset=args.preset, custom_config=args.custom_config))
