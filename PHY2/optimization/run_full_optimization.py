#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Full Optimization Orchestrator (Legacy Alias)
Delegates to run_ultra_deep_optimization.py.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from PHY2.optimization.run_ultra_deep_optimization import run

if __name__ == '__main__':
    sys.exit(run())
