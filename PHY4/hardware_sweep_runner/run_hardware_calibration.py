#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY4 Hardware Calibration Shortcut Launcher
Runs automated parameter calibration across connected SDRs:
  - Pluto SDR Transmitter (ip:192.168.1.10)
  - Nuand bladeRF Receiver (or selectable)
"""

import sys
import os
import subprocess
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPT_SCRIPT = os.path.join(SCRIPT_DIR, "optimize_hardware.py")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY4 Hardware Calibration Shortcut")
    parser.add_argument('--top-n', type=int, default=1000, help="Candidates count: 1000 (fast ~2m), 10000 (standard ~15m), 50000 (full sweep)")
    parser.add_argument('--tx', type=str, default='pluto', choices=['pluto', 'bladerf', 'sim'], help="Transmitter target")
    parser.add_argument('--rx', type=str, default='bladerf', choices=['bladerf', 'pluto', 'rtlsdr', 'sim'], help="Receiver target")
    parser.add_argument('--uri', type=str, default='ip:192.168.1.10', help="Pluto IP URI")
    parser.add_argument('--freq', type=float, default=433.98e6, help="RF Center Frequency")
    args = parser.parse_args()

    cmd = [
        sys.executable, OPT_SCRIPT,
        '--tx-hw', args.tx,
        '--rx-hw', args.rx,
        '--uri', args.uri,
        '--freq', str(args.freq),
        '--top-n', str(args.top_n)
    ]
    sys.exit(subprocess.run(cmd).returncode)
