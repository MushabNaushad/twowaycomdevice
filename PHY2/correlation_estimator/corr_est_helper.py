#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Correlation Estimator Helper
Generates modulated training sequences and constructs matched digital.corr_est_cc
and digital.linear_equalizer blocks for BPSK and QPSK transceivers.
"""

import math
import numpy as np
from gnuradio import digital

def get_training_symbols(mod_type='BPSK', preamble_size=32):
    """
    Returns reference symbol sequences for training the equalizer and correlation estimator.
    """
    mod = mod_type.upper()
    if mod == 'BPSK':
        # Alternating BPSK bits [0, 1, 0, 1...] -> [-1, +1, -1, +1...]
        num_symbols = max(4, min(preamble_size * 8, 64))
        return [(-1.0 if (i % 2 == 0) else 1.0) + 0j for i in range(num_symbols)]
    else: # QPSK
        # Alternating QPSK symbols [00, 11, 00, 11] -> [-1-1j, +1+1j, ...] / sqrt(2)
        num_symbols = max(4, min(preamble_size * 4, 64))
        points = [(-1.0 - 1.0j) / math.sqrt(2), (1.0 + 1.0j) / math.sqrt(2)]
        return [points[i % 2] for i in range(num_symbols)]

def create_corr_est_and_equalizer(mod_type='BPSK', constellation=None, sps=4, step_size=0.001, num_taps=11, preamble_size=32, threshold=0.8):
    """
    Constructs matched (corr_est_cc, linear_equalizer) blocks.
    """
    if constellation is None:
        if mod_type.upper() == 'BPSK':
            constellation = digital.constellation_bpsk().base()
        else:
            constellation = digital.constellation_rect(
                [-1-1j, -1+1j, 1+1j, 1-1j],
                [0, 1, 3, 2],
                4, 2, 2, 1, 1
            ).base()
            
    symbols = get_training_symbols(mod_type, preamble_size)
    mark_delay = len(symbols) - 1
    
    # 1. Correlation Estimator (runs at 1 sps after symbol sync or sps before sync)
    corr_est = digital.corr_est_cc(symbols, 1, mark_delay, threshold)
    
    # 2. Adaptive Algorithm (CMA or LMS)
    adpt_alg = digital.adaptive_algorithm_cma(constellation, step_size, 1).base()
    
    # 3. Adaptive Linear Equalizer triggering on 'corr_est' tag
    equalizer = digital.linear_equalizer(num_taps, 1, adpt_alg, True, symbols, 'corr_est')
    
    return corr_est, equalizer
