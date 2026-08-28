#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    while True:
        print("\n" + "=" * 60)
        print("         CDP PHYSICAL & TRANSPORT LAYER CONTROL")
        print("=" * 60)
        print("  [1] Hardware Optimization & SDR Transceiver (PHY3)")
        print("  [2] Software Simulation Parameter Sweeper (PHY2)")
        print("  [3] Launch Hardware Dashboard")
        print("  [4] Launch Software Dashboard")
        print("  [5] Run System Tests")
        print("  [q] Quit")
        print("=" * 60)
        
        choice = input("\nSelect an option [1-5/q]: ").strip().lower()
        
        env = dict(os.environ, HOME=ROOT_DIR)
        
        if choice == '1':
            cmd = [sys.executable, os.path.join(ROOT_DIR, "PHY3/main.py")]
            subprocess.run(cmd, env=env)
        elif choice == '2':
            cmd = [sys.executable, os.path.join(ROOT_DIR, "PHY2/main.py")]
            subprocess.run(cmd, env=env)
        elif choice == '3':
            cmd = [sys.executable, os.path.join(ROOT_DIR, "PHY3/run_dashboard.py")]
            subprocess.run(cmd, env=env)
        elif choice == '4':
            cmd = [sys.executable, os.path.join(ROOT_DIR, "PHY2/run_dashboard.py")]
            subprocess.run(cmd, env=env)
        elif choice == '5':
            cmd = [sys.executable, os.path.join(ROOT_DIR, "PHY3/cdp_hardware_transceiver.py")]
            subprocess.run(cmd, env=env)
            input("\nPress Enter to return to main menu...")
        elif choice in ['q', 'exit']:
            print("\nExiting. Goodbye.\n")
            break
        else:
            print("\nInvalid choice. Please select 1-5 or q.")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--hw':
            cmd = [sys.executable, os.path.join(ROOT_DIR, "PHY3/main.py")] + sys.argv[2:]
            sys.exit(subprocess.run(cmd).returncode)
        elif sys.argv[1] == '--sim':
            cmd = [sys.executable, os.path.join(ROOT_DIR, "PHY2/main.py")] + sys.argv[2:]
            sys.exit(subprocess.run(cmd).returncode)
    main()
