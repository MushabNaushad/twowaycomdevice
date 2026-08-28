#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Dashboard Server & Simulation/Hardware Execution Orchestrator
Before launching the web dashboard:
1. Automatically executes software simulation or hardware validation based on selected mode.
2. Updates and validates the CSV and JSON optimization datasets.
3. Builds the dedicated zero-dependency HTML dashboard (Software or Hardware).
4. Outputs rich debug information directly to the terminal.
5. Opens the dashboard in the default web browser.
"""

import sys
import os
import time
import argparse
import subprocess
import webbrowser
import http.server
import socketserver
import threading

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)
DASH_DIR = os.path.join(WORKSPACE_ROOT, "PHY2/dashboard")
SW_HTML = os.path.join(DASH_DIR, "software_dashboard.html")
HW_HTML = os.path.join(DASH_DIR, "hardware_dashboard.html")
INDEX_HTML = os.path.join(DASH_DIR, "index.html")

SW_DATA = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/results/deep_sweep_results.json")
HW_DATA = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/results/hardware_optimization_results.json")

def print_debug(tag, msg, color=CYAN):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {color}[{tag}]{RESET} {msg}")

def print_banner(mode):
    print(f"\n{CYAN}{BOLD}================================================================================{RESET}")
    print(f"{CYAN}{BOLD}     PHY2 {mode.upper()} DASHBOARD SERVER & AUTOMATED PIPELINE EXECUTION            {RESET}")
    print(f"{CYAN}{BOLD}================================================================================{RESET}\n")

def run_software_pipeline(run_sweep=False, preset="fast", workers=None):
    if not os.path.exists(SW_DATA):
        print_debug("WARNING", f"No simulation dataset found at {SW_DATA}.", YELLOW)
        print(f"\n{YELLOW}{BOLD}[NOTICE] For optimal dashboard fidelity, you can run the parameter simulation first via:{RESET}")
        print(f"         {CYAN}python3 main.py -> Option [1]{RESET} (or {CYAN}python3 PHY2/run_dashboard.py --run-sweep{RESET})\n")
    else:
        print_debug("SW-PIPELINE", f"Found existing dataset at {SW_DATA} ({os.path.getsize(SW_DATA):,} bytes). Ready!", GREEN)

    if run_sweep:
        print_debug("SW-SWEEP", f"Executing Parameter Optimization Simulation (Preset: {preset.upper()})...", YELLOW)
        sweep_script = os.path.join(WORKSPACE_ROOT, "PHY2/optimization/run_ultra_deep_optimization.py")
        env = dict(os.environ, HOME=WORKSPACE_ROOT)
        cmd = [sys.executable, sweep_script, "--preset", preset]
        if workers: cmd.extend(["--workers", str(workers)])
        
        t0 = time.time()
        res = subprocess.run(cmd, env=env)
        if res.returncode != 0:
            print_debug("ERROR", "Software simulation sweep failed!", RED)
            sys.exit(1)
        print_debug("SW-SWEEP", f"Parameter simulation completed in {time.time()-t0:.2f}s!", GREEN)

    print_debug("BUILDER", "Compiling Software HTML Dashboard...", CYAN)
    builder_script = os.path.join(WORKSPACE_ROOT, "PHY2/dashboard/build_dashboard.py")
    try:
        subprocess.run([sys.executable, builder_script], check=True)
    except subprocess.CalledProcessError as e:
        print_debug("ERROR", f"Dashboard builder failed with code {e.returncode}", RED)
        sys.exit(1)
    return SW_HTML

def run_hardware_pipeline(hw_target="pluto", run_sweep=False):
    print_debug("HW-PIPELINE", f"Initiating Actual SDR Hardware Pipeline for target: {hw_target.upper()}...", CYAN)
    
    print_debug("HW-CHECK", f"Checking physical SDR hardware connection ({hw_target})...", YELLOW)
    from PHY2.hardware.sdr_blocks_helper import create_sdr_source_sink
    try:
        create_sdr_source_sink(hw_type=hw_target, uri="ip:192.168.2.1", cf=433.98e6, tx_gain=20.0, rx_gain=20.0)
        print_debug("HW-CHECK", f"Physical SDR Hardware ({hw_target}) detected and online!", GREEN)
    except Exception as e:
        print_debug("HW-ERROR", f"PHYSICAL SDR HARDWARE ERROR: {e}", RED)
        print(f"\n{RED}{BOLD}[CRITICAL HARDWARE ERROR] Physical SDR Hardware '{hw_target}' is not detected.{RESET}")
        print(f"{YELLOW}Please connect your actual physical {hw_target.upper()} SDR via USB/Ethernet.{RESET}\n")
        raise

    if not os.path.exists(HW_DATA):
        print_debug("WARNING", f"No previous hardware calibration dataset found at {HW_DATA}.", YELLOW)
        print(f"\n{YELLOW}{BOLD}[NOTICE] It is recommended to run live SDR calibration before viewing the dashboard.{RESET}\n")

    if run_sweep:
        print_debug("HW-SWEEP", f"Executing Live SDR Hardware Parameter Sweep on {hw_target.upper()}...", YELLOW)
        hw_opt_script = os.path.join(WORKSPACE_ROOT, "PHY2/hardware/optimize_hardware_sdr.py")
        env = dict(os.environ, HOME=WORKSPACE_ROOT)
        try:
            subprocess.run([sys.executable, hw_opt_script, "--hw", hw_target], env=env, check=True)
        except subprocess.CalledProcessError as e:
            print_debug("ERROR", f"Hardware sweep failed with code {e.returncode}", RED)
            sys.exit(1)
        print_debug("HW-SWEEP", "Actual SDR hardware parameter sweep completed!", GREEN)

    print_debug("BUILDER", "Compiling Hardware SDR HTML Dashboard...", CYAN)
    builder_script = os.path.join(WORKSPACE_ROOT, "PHY2/dashboard/build_dashboard.py")
    try:
        subprocess.run([sys.executable, builder_script], check=True)
    except subprocess.CalledProcessError as e:
        print_debug("ERROR", f"Dashboard builder failed with code {e.returncode}", RED)
        sys.exit(1)
    return HW_HTML

def start_local_server(port, directory):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        def log_message(self, format, *args):
            pass # Keep terminal clean

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", port), QuietHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server

def main():
    parser = argparse.ArgumentParser(description="PHY2 Master Dashboard Orchestrator")
    parser.add_argument("--mode", type=str, default="auto", choices=["auto", "software", "hardware"],
                        help="Dashboard mode: software (simulation) or hardware (actual SDRs)")
    parser.add_argument("--hw", type=str, default="pluto", choices=["pluto", "bladerf", "rtlsdr"],
                        help="Actual SDR Hardware target for hardware mode (default: pluto)")
    parser.add_argument("--run-sweep", action="store_true", help="Run simulation/calibration sweep before opening dashboard")
    parser.add_argument("--preset", type=str, default="fast", choices=["fast", "standard", "exhaustive"],
                        help="Simulation preset when --run-sweep is enabled (default: fast)")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel CPU worker processes for simulation sweep")
    parser.add_argument("--port", type=int, default=8000, help="HTTP server port (default: 8000)")
    parser.add_argument("--no-server", action="store_true", help="Open local file directly without HTTP server")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    # Determine mode
    mode = args.mode
    cwd = os.getcwd()
    if mode == "auto":
        if "hardware" in cwd:
            mode = "hardware"
        else:
            mode = "software"

    print_banner(mode)
    print_debug("INIT", f"Working Directory: {cwd}")
    print_debug("INIT", f"Selected Mode: {mode.upper()} | SDR Target: {args.hw.upper()}")

    target_html = None
    if mode == "software":
        target_html = run_software_pipeline(run_sweep=args.run_sweep, preset=args.preset, workers=args.workers)
    else:
        target_html = run_hardware_pipeline(hw_target=args.hw, run_sweep=args.run_sweep)

    target_filename = os.path.basename(target_html)
    url = f"file://{target_html}"

    if not args.no_server:
        port = args.port
        server_started = False
        for p in range(port, port + 20):
            try:
                start_local_server(p, DASH_DIR)
                port = p
                server_started = True
                break
            except OSError:
                continue
        if server_started:
            url = f"http://localhost:{port}/{target_filename}"
            print_debug("SERVER", f"Dashboard HTTP server running at: {BOLD}{url}{RESET}", GREEN)
        else:
            print_debug("SERVER", "Could not bind HTTP port, using direct file URI.", YELLOW)

    print("\n" + "=" * 80)
    print(f"{GREEN}{BOLD} >>> DASHBOARD READY: {url} <<<{RESET}")
    print("=" * 80 + "\n")

    if not args.no_browser:
        print_debug("BROWSER", f"Launching default browser: {url}...")
        webbrowser.open(url)

    if not args.no_server:
        print_debug("STATUS", "Press Ctrl+C to terminate dashboard server.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print_debug("SHUTDOWN", "Dashboard server terminated.", YELLOW)

    return 0

if __name__ == "__main__":
    sys.exit(main())
