#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY3 Hardware Optimization Control Center
Dedicated master control hub for physical SDR parameter optimization (BPSK & QPSK)
directly implementing the user's original CDP transeciever flow diagram.
"""

import sys
import os
import subprocess
import time

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header():
    print(f"\n{CYAN}{BOLD}================================================================================{RESET}")
    print(f"{CYAN}{BOLD}          PHY3 SDR HARDWARE LIVE OPTIMIZATION CONTROL CENTER                   {RESET}")
    print(f"{CYAN}{BOLD}================================================================================{RESET}")
    print(f"  • Target Flowgraph : {BOLD}PHY3/cdp_transeciever_hw.grc{RESET} (Original Flow Diagram)")
    print(f"  • Modulations      : {BOLD}BPSK & QPSK{RESET}")
    print(f"  • Signal Chain     : {BOLD}y·y' TED + Correlation Estimator + Adaptive Linear Equalizer{RESET}")
    print(f"  • SDR Hardware     : {BOLD}Adalm-Pluto SDR, Nuand bladeRF, RTL-SDR{RESET}")
    print(f"{CYAN}================================================================================{RESET}\n")

def run_hardware_optimization_interactive():
    print(f"\n{CYAN}{BOLD}>>> SELECT CONNECTED PHYSICAL SDR HARDWARE <<<{RESET}")
    print("  [1] 📡 Analog Devices Adalm-Pluto SDR (Full-Duplex IIO, 70 MHz - 6 GHz)")
    print("  [2] ⚡ Nuand bladeRF (USB 3.0, 47 MHz - 3.8 GHz)")
    print("  [3] 📻 RTL-SDR v4 (USB Direct Sampling Receiver, 500 kHz - 1.76 GHz)")
    print("  [4] 💻 Loopback Simulation Mode (RF Impairment Channel)")
    print("  [B] Back to Main Menu")
    
    hw_choice = input(f"\nSelect Hardware {BOLD}[1-4/B]{RESET} (default 1): ").strip().upper()
    if hw_choice == 'B':
        return
    hw_map = {'1': 'pluto', '2': 'bladerf', '3': 'rtlsdr', '4': 'sim'}
    hw_target = hw_map.get(hw_choice, 'pluto')
    
    print(f"\n{CYAN}{BOLD}>>> SELECT MODULATION SCHEME <<<{RESET}")
    print("  [1] 🔄 Both BPSK & QPSK (Comprehensive)")
    print("  [2] 🔵 BPSK Only")
    print("  [3] 🟢 QPSK Only")
    
    mod_choice = input(f"Select Modulation {BOLD}[1-3]{RESET} (default 1): ").strip()
    mod_map = {'1': 'all', '2': 'BPSK', '3': 'QPSK'}
    mod_selected = mod_map.get(mod_choice, 'all')
    
    print(f"\n{CYAN}{BOLD}>>> SELECT SWEEP PROFILE <<<{RESET}")
    print("  [1] 🎯 Full Sweep on Top 50,000 Lowest-BER Candidate Combinations")
    print("  [2] ⚡ Fast Calibration on Top 1,000 Candidates (~1-2 min)")
    print("  [3] 🔬 Quick Sanity Check on Top 50 Candidates (~5 sec)")
    
    sweep_choice = input(f"Select Sweep Depth {BOLD}[1-3]{RESET} (default 2): ").strip()
    top_n_map = {'1': 50000, '2': 1000, '3': 50}
    top_n = top_n_map.get(sweep_choice, 1000)
    
    opt_script = os.path.join(WORKSPACE_ROOT, "PHY3/optimize_hardware.py")
    cmd = [
        sys.executable, opt_script,
        "--hw", hw_target,
        "--mod", mod_selected,
        "--top-n", str(top_n)
    ]
    
    env = dict(os.environ, HOME=WORKSPACE_ROOT)
    t0 = time.time()
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[INFO] Optimization interrupted by user.{RESET}")
        return
        
    elapsed = time.time() - t0
    mins, secs = divmod(int(elapsed), 60)
    time_str = f"{mins}m {secs:02d}s" if mins > 0 else f"{elapsed:.2f}s"
    print(f"\n{GREEN}{BOLD}[SUCCESS] Hardware Optimization Completed in {time_str}!{RESET}")
    
    # Rebuild dashboard with new data
    from PHY3.dashboard.build_dashboard import build_hardware_dashboard
    build_hardware_dashboard()
    
    launch = input(f"\n{BOLD}Launch Hardware Web Dashboard now? [Y/n]: {RESET}").strip().lower()
    if launch != 'n':
        dash_script = os.path.join(WORKSPACE_ROOT, "PHY3/run_dashboard.py")
        subprocess.run([sys.executable, dash_script], env=env)

def main_menu():
    while True:
        print_header()
        print(f"  {BOLD}[1]{RESET} 🎯 Run Live Hardware Parameter Optimization (Pluto / bladeRF / RTL-SDR / Sim)")
        print(f"  {BOLD}[2]{RESET} 🛠️ Apply Optimal Parameters to Hardware GRC (cdp_transeciever_hw.grc)")
        print(f"  {BOLD}[3]{RESET} 📊 Launch Hardware SDR Web Dashboard")
        print(f"  {BOLD}[4]{RESET} 🔬 Quick Transceiver Smoke Test (BPSK & QPSK)")
        print(f"  {BOLD}[Q]{RESET} Exit")
        
        choice = input(f"\n{BOLD}Select an option [1-4/Q]: {RESET}").strip().upper()
        
        if choice == '1':
            run_hardware_optimization_interactive()
        elif choice == '2':
            mod = input(f"\nApply parameters for which modulation? {BOLD}[BPSK/QPSK]{RESET} (default QPSK): ").strip().upper()
            if not mod: mod = 'QPSK'
            from PHY3.apply_optimal_parameters import apply_parameters_to_grc
            apply_parameters_to_grc(mod_type=mod)
            input("\nPress Enter to return to main menu...")
        elif choice == '3':
            dash_script = os.path.join(WORKSPACE_ROOT, "PHY3/run_dashboard.py")
            env = dict(os.environ, HOME=WORKSPACE_ROOT)
            subprocess.run([sys.executable, dash_script], env=env)
        elif choice == '4':
            from PHY3.cdp_hardware_transceiver import test_hardware_transceiver
            print("\nRunning smoke test across BPSK and QPSK (10 packets each)...")
            for m in ['BPSK', 'QPSK']:
                res = test_hardware_transceiver(mod_type=m, hw_type='sim')
                print(f"  • {m:4s} -> TX: {res['transmitted_packets']} | RX: {res['received_packets']} | Verified: {res['matched_packets']} | PDR: {res['pdr']:.1f}%")
            input("\nPress Enter to return to main menu...")
        elif choice == 'Q':
            print(f"\n{GREEN}Exiting PHY3 Hardware Suite. Goodbye!{RESET}\n")
            break
        else:
            print(f"\n{YELLOW}Invalid choice. Please select 1, 2, 3, 4, or Q.{RESET}")

if __name__ == '__main__':
    main_menu()
