#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Hardware Transceiver Parameter Updater
Applies optimal or custom parameters directly to the hardware GRC flowgraph (cdp_transeciever_hw.grc)
and recompiles it into executable Python with grcc.

Supports:
1. Automatic mode (--auto): Loads optimal parameters (FLL, Costas, SymSync, Preamble) from optimization results.
2. Manual CLI flags (--fll, --costas, --sym, --preamble, --cf, --gain, --addr, --mod).
3. Interactive terminal prompts when run without arguments.
"""

import sys
import os
import json
import re
import argparse
import subprocess
import time

# Terminal Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
RESULTS_JSON = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/results/pinpoint_optimal_parameters.json")
FALLBACK_JSON = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/results/optimal_hardware_parameters.json")

GRC_FILES = [
    os.path.join(WORKSPACE_ROOT, "PHY2/adapted_original/cdp_transeciever_hw.grc"),
    os.path.join(WORKSPACE_ROOT, "PHY2/hardware/cdp_transceiver_multi_hardware.grc"),
    os.path.join(WORKSPACE_ROOT, "PHY2/hardware/cdp_transceiver_pluto.grc")
]

def print_banner():
    print(f"{CYAN}{BOLD}================================================================================{RESET}")
    print(f"{CYAN}{BOLD}       PHY2 HARDWARE TRANSCEIVER GRC PARAMETER OPTIMIZATION APPLIER            {RESET}")
    print(f"{CYAN}{BOLD}================================================================================{RESET}")

def load_optimal_parameters(mod_type="BPSK"):
    json_path = RESULTS_JSON if os.path.exists(RESULTS_JSON) else FALLBACK_JSON
    if not os.path.exists(json_path):
        print(f"{YELLOW}[WARN] Optimal parameters JSON not found at {json_path}. Using standard optimal defaults.{RESET}")
        if mod_type.upper() == "BPSK":
            return {"fll_bw": 0.0314, "costas_bw": 0.0628, "sym_bw": 0.0250, "preamble_size": 32}
        else:
            return {"fll_bw": 0.0314, "costas_bw": 0.0628, "sym_bw": 0.0550, "preamble_size": 32}
            
    with open(json_path, "r") as f:
        data = json.load(f)
    
    if isinstance(data, list):
        candidates = [d for d in data if d.get("mod_type") == mod_type]
        if candidates:
            return candidates[0]
        return data[0]
    elif isinstance(data, dict):
        if mod_type in data:
            return data[mod_type]
        return data
    return {"fll_bw": 0.0314, "costas_bw": 0.0628, "sym_bw": 0.0250, "preamble_size": 32}

def update_grc_variable(content, var_name, new_val):
    # Match standard GRC YAML variable block
    pattern = rf"(- name: {re.escape(var_name)}\s+id: variable\s+parameters:\s+comment: [^\n]*\s+value: )([^\n]+)"
    replacement = rf"\g<1>'{new_val}'"
    new_content, count = re.subn(pattern, replacement, content)
    return new_content, count > 0

def apply_parameters_to_grc(grc_path, params):
    if not os.path.exists(grc_path):
        print(f"{YELLOW}[WARN] GRC file not found: {grc_path}{RESET}")
        return False
        
    print(f"[{time.strftime('%H:%M:%S')}] {CYAN}[DEBUG]{RESET} Reading GRC file: {os.path.basename(grc_path)}")
    with open(grc_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    updated = False
    substitutions = [
        ("fll_loop_bw", f"{params['fll_bw']:.4f}"),
        ("fll_bw", f"{params['fll_bw']:.4f}"),
        ("costas_bw", f"{params['costas_bw']:.4f}"),
        ("sym_bw", f"{params['sym_bw']:.4f}"),
        ("preamble_size", str(int(params["preamble_size"]))),
    ]
    
    if "cf" in params and params["cf"]:
        substitutions.append(("SDR_CF", str(params["cf"])))
    if "gain" in params and params["gain"]:
        substitutions.append(("CH_GAIN", str(params["gain"])))
    if "addr" in params and params["addr"]:
        substitutions.append(("ADDR", f'"{params["addr"]}"'))
        
    for var_name, val in substitutions:
        content, success = update_grc_variable(content, var_name, val)
        if success:
            print(f"  -> Variable {GREEN}{var_name}{RESET} updated to: {YELLOW}{val}{RESET}")
            updated = True
            
    if updated:
        with open(grc_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{GREEN}[OK] Successfully updated {os.path.basename(grc_path)}{RESET}")
        
        # Compile with grcc if available
        try:
            print(f"[{time.strftime('%H:%M:%S')}] {CYAN}[DEBUG]{RESET} Compiling {os.path.basename(grc_path)} with grcc...")
            res = subprocess.run(
                ["grcc", "-o", os.path.dirname(grc_path), grc_path],
                capture_output=True, text=True, timeout=15
            )
            if res.returncode == 0:
                print(f"{GREEN}[OK] Compiled {os.path.basename(grc_path)} to Python!{RESET}")
            else:
                print(f"{YELLOW}[WARN] grcc note: {res.stderr.strip()}{RESET}")
        except Exception as e:
            print(f"{YELLOW}[WARN] grcc invocation skipped: {e}{RESET}")
    return updated

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="PHY2 Hardware GRC Parameter Applier")
    parser.add_argument("--auto", action="store_true", help="Automatically load optimal parameters from optimization results")
    parser.add_argument("--mod", type=str, default="BPSK", choices=["BPSK", "QPSK"], help="Modulation scheme (BPSK/QPSK)")
    parser.add_argument("--fll", type=float, default=None, help="FLL Band-Edge Loop BW (rad/sym)")
    parser.add_argument("--costas", type=float, default=None, help="Costas Loop BW (rad/sym)")
    parser.add_argument("--sym", type=float, default=None, help="Symbol Sync Loop BW (rad/sym)")
    parser.add_argument("--preamble", type=int, default=None, help="Preamble length in bytes (2..64)")
    parser.add_argument("--cf", type=float, default=433.98e6, help="SDR RF Center Frequency (Hz)")
    parser.add_argument("--gain", type=float, default=20.0, help="SDR Channel Gain (dB)")
    parser.add_argument("--addr", type=str, default="ip:192.168.2.1", help="SDR IP/URI address")
    parser.add_argument("--grc", type=str, default=None, help="Specific GRC file to update")
    args = parser.parse_args()

    params = {}
    
    if args.auto:
        print(f"[{time.strftime('%H:%M:%S')}] {CYAN}[DEBUG]{RESET} Auto-loading optimal parameters for {args.mod}...")
        opt = load_optimal_parameters(args.mod)
        params["fll_bw"] = float(opt.get("fll_bw", 0.0314))
        params["costas_bw"] = float(opt.get("costas_bw", 0.0628))
        params["sym_bw"] = float(opt.get("sym_bw", 0.0250))
        params["preamble_size"] = int(opt.get("preamble_size", 32))
        params["cf"] = args.cf
        params["gain"] = args.gain
        params["addr"] = args.addr
    elif args.fll is not None and args.costas is not None and args.sym is not None:
        params["fll_bw"] = args.fll
        params["costas_bw"] = args.costas
        params["sym_bw"] = args.sym
        params["preamble_size"] = args.preamble if args.preamble else 32
        params["cf"] = args.cf
        params["gain"] = args.gain
        params["addr"] = args.addr
    else:
        # Interactive terminal prompt
        print(f"\n{BOLD}Enter transceiver parameters (Press Enter to accept defaults/optimal):{RESET}")
        opt = load_optimal_parameters(args.mod)
        
        fll_in = input(f"  FLL Band-Edge Loop BW [{opt.get('fll_bw', 0.0314):.4f} rad/sym]: ").strip()
        params["fll_bw"] = float(fll_in) if fll_in else float(opt.get("fll_bw", 0.0314))
        
        costas_in = input(f"  Costas Loop BW [{opt.get('costas_bw', 0.0628):.4f} rad/sym]: ").strip()
        params["costas_bw"] = float(costas_in) if costas_in else float(opt.get("costas_bw", 0.0628))
        
        sym_in = input(f"  Symbol Sync Loop BW [{opt.get('sym_bw', 0.0250):.4f} rad/sym]: ").strip()
        params["sym_bw"] = float(sym_in) if sym_in else float(opt.get("sym_bw", 0.0250))
        
        pre_in = input(f"  Preamble Length [{opt.get('preamble_size', 32)} Bytes]: ").strip()
        params["preamble_size"] = int(pre_in) if pre_in else int(opt.get("preamble_size", 32))
        
        cf_in = input(f"  SDR Center Frequency [{args.cf/1e6:.2f} MHz]: ").strip()
        params["cf"] = float(cf_in) * 1e6 if cf_in else args.cf
        
        gain_in = input(f"  SDR Channel Gain [{args.gain:.1f} dB]: ").strip()
        params["gain"] = float(gain_in) if gain_in else args.gain
        
        addr_in = input(f"  SDR Device IP/URI [{args.addr}]: ").strip()
        params["addr"] = addr_in if addr_in else args.addr

    print(f"\n{BOLD}PARAMETERS TO APPLY:{RESET}")
    print(f"  • Modulation Scheme         : {args.mod}")
    print(f"  • FLL Band-Edge Loop BW     : {params['fll_bw']:.4f} rad/sym")
    print(f"  • Costas Loop BW            : {params['costas_bw']:.4f} rad/sym")
    print(f"  • Symbol Sync Loop BW       : {params['sym_bw']:.4f} rad/sym")
    print(f"  • Preamble Length           : {params['preamble_size']} Bytes")
    print(f"  • SDR Center Frequency      : {params['cf']/1e6:.2f} MHz")
    print(f"  • SDR Gain                  : {params['gain']:.1f} dB")
    print(f"  • SDR URI Address           : {params['addr']}")
    print("-" * 80)

    target_files = [args.grc] if args.grc else GRC_FILES
    for grc in target_files:
        apply_parameters_to_grc(grc, params)
        
    print(f"\n{GREEN}{BOLD}>>> COMPLETED GRC HARDWARE FLOWGRAPH UPDATE SUCCESSFULLY! <<<{RESET}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
