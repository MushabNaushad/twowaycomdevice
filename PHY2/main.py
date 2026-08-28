#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Unified Master Control Center & Interactive Workflow Orchestrator
Single entry-point to:
1. Select operating mode (Software Simulation vs Actual Physical SDR Hardware).
2. Choose physical SDR target (Adalm-Pluto, bladeRF, RTL-SDR).
3. Run, skip, or launch Software/Hardware web dashboards.
4. Apply pinpointed/custom optimized parameters to the copied GRC flowgraph (cdp_transeciever_hw.grc).
5. Run and validate the adapted/copied transceiver separately under channel impairments.
6. Run centralized regression test suites across all stages.
"""

import sys
import os
import subprocess
import time
import argparse
import json

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def clear_screen():
    # Only clear if running in an interactive TTY
    if sys.stdout.isatty():
        os.system('clear' if os.name == 'posix' else 'cls')

def print_header():
    print(f"{CYAN}{BOLD}================================================================================{RESET}")
    print(f"{CYAN}{BOLD}           PHY2 MASTER PHYSICAL LAYER CONTROL & OPTIMIZATION CENTER             {RESET}")
    print(f"{CYAN}{BOLD}   (SDR Transceivers, 0.001-Step Sweeper, Web Dashboards, & GRC Flowgraphs)    {RESET}")
    print(f"{CYAN}{BOLD}================================================================================{RESET}")

def print_menu():
    print(f"\n{BOLD}Select an action from the menu below:{RESET}\n")
    print(f"  {CYAN}{BOLD}[1]{RESET} 🧪 {BOLD}Software Simulation & Parameter Optimization Sweep{RESET}")
    print(f"      {DIM}Run full 0.001-step Cartesian sweep (with live progress bar) or launch dashboard{RESET}\n")
    
    print(f"  {CYAN}{BOLD}[2]{RESET} 📡 {BOLD}Hardware Mode: Physical SDR Transceiver Execution{RESET}")
    print(f"      {DIM}Target actual physical SDRs (Adalm-Pluto, bladeRF, RTL-SDR) & calibrate RF{RESET}\n")
    
    print(f"  {CYAN}{BOLD}[3]{RESET} 📊 {BOLD}Launch Web Dashboards Directly{RESET}")
    print(f"      {DIM}Open Software Simulation or Hardware SDR web dashboards instantly{RESET}\n")
    
    print(f"  {CYAN}{BOLD}[4]{RESET} ⚙️  {BOLD}Apply Optimized Parameters to Hardware GRC Flowgraph{RESET}")
    print(f"      {DIM}Update 'cdp_transeciever_hw.grc' with auto/custom values & recompile with grcc{RESET}\n")
    
    print(f"  {CYAN}{BOLD}[5]{RESET} 🔬 {BOLD}Test Adapted / Copied Transceiver Flowgraph Separately{RESET}")
    print(f"      {DIM}Run standalone test of your copied flowgraph with custom/optimal parameters{RESET}\n")
    
    print(f"  {CYAN}{BOLD}[6]{RESET} 🛡️  {BOLD}Run Centralized Automated Test Suite (7 Stages){RESET}")
    print(f"      {DIM}Full regression verification across FLL, Equalizer, Preamble, CRC32, etc.{RESET}\n")
    
    print(f"  {RED}{BOLD}[0]{RESET} 🚪 {BOLD}Exit{RESET}\n")
    print(f"{CYAN}--------------------------------------------------------------------------------{RESET}")

def run_software_flow():
    print(f"\n{CYAN}{BOLD}>>> [1] SOFTWARE SIMULATION & PARAMETER OPTIMIZATION <<< {RESET}\n")
    print(f"  {GREEN}{BOLD}[1]{RESET} ⚡ {BOLD}Fast Focused Sweep (~12,000 trials, ~5-8s){RESET}  [RECOMMENDED]")
    print(f"      {DIM}Sweeps high-probability optimal zone (FLL: 0.01..0.10, Costas: 0.01..0.15, Sym: 0.005..0.15){RESET}\n")
    
    print(f"  {CYAN}{BOLD}[2]{RESET} 🌐 {BOLD}Standard Exploration Sweep (~52,000 trials, ~20-25s){RESET}")
    print(f"      {DIM}Broader search space across noise, carrier offsets, and clock drift{RESET}\n")
    
    print(f"  {MAGENTA}{BOLD}[3]{RESET} 🔬 {BOLD}Exhaustive Deep Sweep (700,000+ trials){RESET}")
    print(f"      {DIM}Dense 0.001-step Cartesian grid across the entire 0.001..1.000 multidimensional space{RESET}\n")
    
    print(f"  {YELLOW}{BOLD}[4]{RESET} 🛠️  {BOLD}Custom Range Sweep{RESET}")
    print(f"      {DIM}Enter your own custom Min/Max/Step for FLL, Costas, and Symbol Sync loop bandwidths{RESET}\n")
    
    print(f"  {CYAN}{BOLD}[5]{RESET} 📊 {BOLD}Launch Software Web Dashboard Directly{RESET}")
    print(f"      {DIM}View existing simulation results in the web browser without re-running sweeps{RESET}\n")
    
    print(f"  {BOLD}[B]{RESET} 🔙 Back to Main Menu")
    
    choice = input(f"\nEnter choice {BOLD}[1-5/B]{RESET} (default 1): ").strip().upper()
    if choice == 'B':
        return
        
    env = dict(os.environ, HOME=WORKSPACE_ROOT)
    
    if choice == '5':
        cmd = [sys.executable, os.path.join(WORKSPACE_ROOT, "PHY2/run_dashboard.py"), "--mode", "software"]
        subprocess.run(cmd, env=env)
        return
        
    preset = 'fast'
    custom_config = None
    if choice == '2':
        preset = 'standard'
    elif choice == '3':
        preset = 'exhaustive'
    elif choice == '4':
        preset = 'custom'
        print(f"\n{BOLD}Enter Custom Sweep Parameters:{RESET}")
        try:
            f_min = float(input("  FLL Loop BW Min [0.010 rad/sym]: ").strip() or 0.010)
            f_max = float(input("  FLL Loop BW Max [0.100 rad/sym]: ").strip() or 0.100)
            f_step = float(input("  FLL Step Size   [0.010 rad/sym]: ").strip() or 0.010)
            
            c_min = float(input("  Costas BW Min   [0.020 rad/sym]: ").strip() or 0.020)
            c_max = float(input("  Costas BW Max   [0.120 rad/sym]: ").strip() or 0.120)
            c_step = float(input("  Costas Step Size[0.005 rad/sym]: ").strip() or 0.005)
            
            s_min = float(input("  SymSync BW Min  [0.005 rad/sym]: ").strip() or 0.005)
            s_max = float(input("  SymSync BW Max  [0.150 rad/sym]: ").strip() or 0.150)
            s_step = float(input("  SymSync Step    [0.002 rad/sym]: ").strip() or 0.002)
            
            custom_config = {
                "fll": (f_min, f_max, f_step),
                "costas": (c_min, c_max, c_step),
                "sym": (s_min, s_max, s_step),
                "preambles": [16, 32, 64]
            }
            import tempfile
            custom_cfg_path = os.path.join(WORKSPACE_ROOT, 'PHY2/optimization/results/custom_config.json')
            with open(custom_cfg_path, 'w') as f:
                json.dump(custom_config, f)
        except ValueError as e:
            print(f"{RED}[ERROR] Invalid numeric input: {e}. Using fast preset.{RESET}")
            preset = 'fast'

    # Run sweep with live progress bar
    opt_script = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/run_ultra_deep_optimization.py")
    cmd = [sys.executable, opt_script, "--preset", preset]
    if preset == 'custom' and custom_config:
        cmd.extend(['--custom-config', custom_cfg_path])
    t0 = time.time()
    res = subprocess.run(cmd, env=env)
    elapsed = time.time() - t0
    mins, secs = divmod(int(elapsed), 60)
    time_str = f"{mins}m {secs:02d}s" if mins > 0 else f"{elapsed:.2f}s"
    
    print(f"\n{GREEN}{BOLD}[SUCCESS] Simulation Completed! Actual Ran Time: {elapsed:.2f}s ({time_str}){RESET}")
    
    launch_dash = input(f"\n{BOLD}Launch Software Web Dashboard now? [Y/n]: {RESET}").strip().lower()
    if launch_dash != 'n':
        dash_cmd = [sys.executable, os.path.join(WORKSPACE_ROOT, "PHY2/run_dashboard.py"), "--mode", "software"]
        subprocess.run(dash_cmd, env=env)

def run_hardware_flow():
    print(f"\n{CYAN}{BOLD}>>> [2] ACTUAL PHYSICAL SDR HARDWARE MODE <<< {RESET}\n")
    print("Select your connected physical SDR hardware:")
    print("  [1] 📡 Analog Devices Adalm-Pluto SDR (Full-Duplex IIO, 70 MHz - 6 GHz)")
    print("  [2] ⚡ Nuand bladeRF (Micro-USB 3.0, 47 MHz - 3.8 GHz)")
    print("  [3] 📻 RTL-SDR v4 (USB Direct Sampling Receiver, 500 kHz - 1.76 GHz)")
    print("  [B] Back to Main Menu")
    
    hw_choice = input(f"\nSelect SDR Hardware {BOLD}[1/2/3/B]{RESET} (default 1): ").strip().upper()
    if hw_choice == 'B':
        return
        
    hw_map = {'1': 'pluto', '2': 'bladerf', '3': 'rtlsdr'}
    hw_target = hw_map.get(hw_choice, 'pluto')
    
    print(f"\nAction for physical {hw_target.upper()} SDR:")
    print("  [1] 🎯 Run Live Hardware Sweep on Top 50,000 Lowest-BER Candidates (from Simulation)")
    print("  [2] ⚡ Fast Hardware Calibration on Top 1,000 Candidates (~1-2m Quick Run)")
    print("  [3] 📊 Launch Hardware SDR Web Dashboard Directly (from existing calibration)")
    print("  [4] 🔄 Re-extract / Refresh Top 50,000 Lowest-BER Candidates from Simulation Dataset")
    print("  [B] Back")
    
    act_choice = input(f"\nEnter choice {BOLD}[1-4/B]{RESET} (default 1): ").strip().upper()
    if act_choice == 'B':
        return
        
    env = dict(os.environ, HOME=WORKSPACE_ROOT)
    
    if act_choice == '4':
        ext_script = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/extract_top_candidates.py")
        subprocess.run([sys.executable, ext_script], env=env)
        return
        
    if act_choice == '3':
        cmd = [sys.executable, os.path.join(WORKSPACE_ROOT, "PHY2/run_dashboard.py"), "--mode", "hardware", "--hw", hw_target]
        subprocess.run(cmd, env=env)
        return
        
    top_n = 50000 if act_choice == '1' else 1000
    hw_opt_script = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/optimize_hardware_sdr.py")
    cmd = [sys.executable, hw_opt_script, "--hw", hw_target, "--top-n", str(top_n)]
    
    t0 = time.time()
    res = subprocess.run(cmd, env=env)
    elapsed = time.time() - t0
    
    launch_dash = input(f"\n{BOLD}Hardware sweep completed! Launch Hardware SDR Dashboard now? [Y/n]: {RESET}").strip().lower()
    if launch_dash != 'n':
        dash_cmd = [sys.executable, os.path.join(WORKSPACE_ROOT, "PHY2/run_dashboard.py"), "--mode", "hardware", "--hw", hw_target]
        subprocess.run(dash_cmd, env=env)

def run_dashboard_flow():
    print(f"\n{CYAN}{BOLD}>>> [3] LAUNCH WEB DASHBOARD DIRECTLY <<< {RESET}\n")
    print("  [1] 🧪 Software Simulation Dashboard (BER vs SymSync curves, 2D Heatmap, CSV Table)")
    print("  [2] 📡 Hardware SDR Dashboard (Actual physical SDR targets & RF controls)")
    print("  [B] Back to Main Menu")
    
    dash_choice = input(f"\nSelect Dashboard {BOLD}[1/2/B]{RESET} (default 1): ").strip().upper()
    if dash_choice == 'B':
        return
        
    mode = "hardware" if dash_choice == '2' else "software"
    cmd = [sys.executable, os.path.join(WORKSPACE_ROOT, "PHY2/run_dashboard.py"), "--mode", mode]
    env = dict(os.environ, HOME=WORKSPACE_ROOT)
    subprocess.run(cmd, env=env)

def run_grc_applier_flow():
    print(f"\n{CYAN}{BOLD}>>> [4] APPLY OPTIMIZED PARAMETERS TO HARDWARE GRC FLOWGRAPH <<< {RESET}\n")
    print("Target file: PHY2/adapted_original/cdp_transeciever_hw.grc\n")
    print("  [1] Auto-apply pinpointed optimal parameters for BPSK (FLL=0.0314, Costas=0.0628, Sym=0.025, Pre=32)")
    print("  [2] Auto-apply pinpointed optimal parameters for QPSK (FLL=0.0314, Costas=0.0628, Sym=0.055, Pre=32)")
    print("  [3] Enter custom transceiver parameters interactively in terminal")
    print("  [B] Back to Main Menu")
    
    app_choice = input(f"\nEnter choice {BOLD}[1/2/3/B]{RESET} (default 1): ").strip().upper()
    if app_choice == 'B':
        return
        
    applier_script = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/apply_optimal_parameters.py")
    env = dict(os.environ, HOME=WORKSPACE_ROOT)
    
    if app_choice == '1':
        cmd = [sys.executable, applier_script, "--auto", "--mod", "BPSK"]
    elif app_choice == '2':
        cmd = [sys.executable, applier_script, "--auto", "--mod", "QPSK"]
    else:
        cmd = [sys.executable, applier_script]
        
    subprocess.run(cmd, env=env)
    input(f"\n{BOLD}Press Enter to return to main menu...{RESET}")

def run_adapted_transceiver_flow():
    print(f"\n{CYAN}{BOLD}>>> [5] TEST ADAPTED/COPIED TRANSCEIVER SEPARATELY <<< {RESET}\n")
    print("Select modulation to evaluate:")
    print("  [1] BPSK (Binary Phase Shift Keying)")
    print("  [2] QPSK (Quadrature Phase Shift Keying)")
    print("  [3] BOTH (BPSK + QPSK full validation)")
    print("  [B] Back to Main Menu")
    
    mod_in = input(f"\nEnter choice {BOLD}[1/2/3/B]{RESET} (default 3): ").strip().upper()
    if mod_in == 'B':
        return
        
    mod_map = {'1': 'BPSK', '2': 'QPSK', '3': 'ALL'}
    mod_val = mod_map.get(mod_in, 'ALL')
    
    test_script = os.path.join(WORKSPACE_ROOT, "PHY2/adapted_original/run_original_test.py")
    env = dict(os.environ, HOME=WORKSPACE_ROOT)
    cmd = [sys.executable, test_script, "--mod", mod_val]
    
    subprocess.run(cmd, env=env)
    input(f"\n{BOLD}Press Enter to return to main menu...{RESET}")

def run_all_tests_flow():
    print(f"\n{CYAN}{BOLD}>>> [6] RUN CENTRALIZED AUTOMATED TEST SUITE <<< {RESET}\n")
    runner_script = os.path.join(WORKSPACE_ROOT, "PHY2/run_all_tests.py")
    env = dict(os.environ, HOME=WORKSPACE_ROOT)
    subprocess.run([sys.executable, runner_script, "--hw", "sim", "--mod", "ALL"], env=env)
    input(f"\n{BOLD}Press Enter to return to main menu...{RESET}")

def interactive_loop():
    while True:
        clear_screen()
        print_header()
        print_menu()
        try:
            choice = input(f"{BOLD}Enter option [0-6]: {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{YELLOW}Exiting PHY2 Master Control Center.{RESET}")
            break
            
        if choice == '0':
            print(f"\n{GREEN}{BOLD}Thank you for using PHY2. Goodbye!{RESET}\n")
            break
        elif choice == '1':
            run_software_flow()
        elif choice == '2':
            run_hardware_flow()
        elif choice == '3':
            run_dashboard_flow()
        elif choice == '4':
            run_grc_applier_flow()
        elif choice == '5':
            run_adapted_transceiver_flow()
        elif choice == '6':
            run_all_tests_flow()
        else:
            print(f"\n{YELLOW}Invalid choice '{choice}'. Please select an option between 0 and 6.{RESET}")
            time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="PHY2 Master Physical Layer Control Center")
    parser.add_argument("--menu", action="store_true", help="Launch interactive menu (default)")
    parser.add_argument("--mode", type=str, choices=["software", "hardware"], help="Directly execute in software or hardware mode")
    parser.add_argument("--hw", type=str, default="pluto", choices=["pluto", "bladerf", "rtlsdr"], help="Physical SDR hardware target")
    parser.add_argument("--skip-sweep", action="store_true", help="Skip running the sweep before opening dashboard")
    parser.add_argument("--apply-opt", type=str, choices=["BPSK", "QPSK"], help="Apply optimal parameters to GRC and exit")
    parser.add_argument("--test-adapted", action="store_true", help="Run standalone test of adapted flowgraph and exit")
    parser.add_argument("--test-all", action="store_true", help="Run centralized test suite and exit")
    args = parser.parse_args()

    env = dict(os.environ, HOME=WORKSPACE_ROOT)

    # CLI shortcuts
    if args.apply_opt:
        applier = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/apply_optimal_parameters.py")
        sys.exit(subprocess.run([sys.executable, applier, "--auto", "--mod", args.apply_opt], env=env).returncode)
    elif args.test_adapted:
        tester = os.path.join(WORKSPACE_ROOT, "PHY2/adapted_original/run_original_test.py")
        sys.exit(subprocess.run([sys.executable, tester, "--mod", "ALL"], env=env).returncode)
    elif args.test_all:
        test_all_script = os.path.join(WORKSPACE_ROOT, "PHY2/run_all_tests.py")
        sys.exit(subprocess.run([sys.executable, test_all_script, "--hw", "sim", "--mod", "ALL"], env=env).returncode)
    elif args.mode:
        dash_script = os.path.join(WORKSPACE_ROOT, "PHY2/run_dashboard.py")
        cmd = [sys.executable, dash_script, "--mode", args.mode, "--hw", args.hw]
        if args.skip_sweep: cmd.append("--skip-sweep")
        sys.exit(subprocess.run(cmd, env=env).returncode)
    else:
        # Default: Interactive Menu
        interactive_loop()

if __name__ == "__main__":
    main()
