#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Hardware Test Runner
Executes the centralized hardware test suite across all stages.
"""

import sys
import os
import argparse

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PHY2.tests.run_all_tests import run_suite

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Master Hardware Test Runner")
    parser.add_argument('--hw', type=str, default='sim', choices=['sim', 'pluto', 'bladerf', 'rtlsdr'])
    parser.add_argument('--mod', type=str, default='ALL', choices=['ALL', 'BPSK', 'QPSK'])
    parser.add_argument('--stage', type=int, default=None)
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1')
    parser.add_argument('--freq', type=float, default=433.98e6)
    parser.add_argument('--gain', type=float, default=20.0)
    args = parser.parse_args()
    
    sys.exit(run_suite(
        hw_type=args.hw,
        mod_filter=args.mod,
        stage_filter=args.stage,
        uri=args.uri,
        freq=args.freq,
        gain=args.gain
    ))
