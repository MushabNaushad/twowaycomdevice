#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY3 Optimal Parameter Applier
Reads pinpointed optimal parameters from hardware optimization sweeps
and updates variables in PHY3/cdp_transeciever_hw.grc and standalone configurations.
"""

import sys
import os
import json
import re

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
GRC_PATH = os.path.join(os.path.dirname(__file__), "cdp_transeciever_hw.grc")
OPTIMAL_JSON = os.path.join(RESULTS_DIR, "optimal_hardware_parameters.json")

def apply_parameters_to_grc(mod_type='QPSK', grc_target=GRC_PATH):
    if not os.path.exists(OPTIMAL_JSON):
        print(f"[ERROR] Optimal parameters file not found: {OPTIMAL_JSON}")
        print("Please run hardware optimization first (python3 PHY3/optimize_hardware.py)")
        return False
        
    with open(OPTIMAL_JSON, 'r') as f:
        params = json.load(f)
        
    mod_key = mod_type.upper()
    if mod_key not in params:
        available = list(params.keys())
        if not available:
            print(f"[ERROR] No optimal parameters found in {OPTIMAL_JSON}")
            return False
        mod_key = available[0]
        print(f"[INFO] Using {mod_key} parameters (requested: {mod_type})")
        
    opt = params[mod_key]
    print("================================================================================")
    print(f"       APPLYING OPTIMAL {mod_key} PARAMETERS TO HARDWARE GRC FLOWGRAPH          ")
    print("================================================================================")
    print(f"  • Modulation Scheme    : {opt.get('modulation', mod_key)}")
    print(f"  • SDR Hardware Target  : {opt.get('hw_type', 'pluto').upper()}")
    print(f"  • FLL Loop Bandwidth   : {opt['fll_loop_bw']:.4f} rad/sym")
    print(f"  • Costas Loop Bandwidth: {opt['costas_bw']:.4f} rad/sym")
    print(f"  • Symbol Sync Bandwidth: {opt['sym_bw']:.4f} rad/sym (y·y' TED)")
    print(f"  • Preamble Length      : {opt['preamble_size']} Bytes")
    print(f"  • Historical Avg PDR   : {opt.get('pdr', 0)}%")
    print(f"  • Historical Avg BER   : {opt.get('ber', 0.5):.5f}")
    print("================================================================================")
    
    if not os.path.exists(grc_target):
        print(f"[ERROR] Target GRC file not found: {grc_target}")
        return False
        
    with open(grc_target, 'r') as f:
        content = f.read()
        
    # Helper to replace variable block parameter value in YAML GRC
    def update_var(grc_text, var_name, new_val_str):
        # Match variable block
        pattern = rf"(- name: {var_name}\s+id: variable\s+parameters:\s+comment: ''\s+value: )'?[^'\n]+'?"
        if re.search(pattern, grc_text):
            return re.sub(pattern, rf"\g<1>'{new_val_str}'", grc_text)
        # Fallback simpler match
        pattern2 = rf"(name: {var_name}[\s\S]*?value:\s*)'?[^'\n]+'?"
        return re.sub(pattern2, rf"\g<1>'{new_val_str}'", grc_text)
        
    updated = content
    updated = update_var(updated, 'fll_loop_bw', f"{opt['fll_loop_bw']:.4f}")
    updated = update_var(updated, 'costas_bw', f"{opt['costas_bw']:.4f}")
    updated = update_var(updated, 'sym_bw', f"{opt['sym_bw']:.4f}")
    updated = update_var(updated, 'preamble_size', f"{int(opt['preamble_size'])}")
    
    with open(grc_target, 'w') as f:
        f.write(updated)
        
    print(f"[SUCCESS] Updated {os.path.basename(grc_target)} with optimal {mod_key} parameters!\n")
    return True

if __name__ == '__main__':
    mod = sys.argv[1] if len(sys.argv) > 1 else 'QPSK'
    apply_parameters_to_grc(mod_type=mod)
