#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PHY2 Stage 06: Hardware Correlation Estimator + Adaptive Equalizer Test Runner"""
import sys, os, argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from PHY2.tests.test_06_linear_equalizer import run_stage_06

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY2 Stage 06 Test Runner")
    parser.add_argument('--hw', type=str, default='sim', choices=['sim', 'pluto', 'bladerf', 'rtlsdr'])
    parser.add_argument('--mod', type=str, default='ALL', choices=['ALL', 'BPSK', 'QPSK'])
    parser.add_argument('--uri', type=str, default='ip:192.168.2.1')
    parser.add_argument('--freq', type=float, default=433.98e6)
    parser.add_argument('--gain', type=float, default=20.0)
    args = parser.parse_args()
    print(">>> Running Stage 06 Hardware Correlation Estimator + Equalizer Test <<<")
    res = run_stage_06(args.hw, args.mod, args.uri, args.freq, args.gain)
    print("-> [PASS] Stage 06 Verified!" if res else "-> [FAIL] Stage 06 Failed!")
    sys.exit(0 if res else 1)
