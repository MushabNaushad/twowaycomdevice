#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Adapted Original Transceiver Optimizer (Legacy Alias)
Delegates to the master full-range optimizer (0.005..1.000 rad/sym).
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from PHY2.adapted_original.optimize_original_ultra_fine import run_range_005_to_1_optimization

if __name__ == '__main__':
    run_range_005_to_1_optimization()
