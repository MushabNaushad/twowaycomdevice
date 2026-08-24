#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Optimization Suite - BER & Performance Calculator
Calculates Bit Error Rate (BER), Packet Delivery Ratio (PDR), and lock metrics from raw bit/byte streams.
"""

import numpy as np

def calculate_ber(tx_bits, rx_bits, allow_inversion=True, discard_transient=0):
    """
    Computes Bit Error Rate (BER) by cross-correlating tx and rx bit sequences.
    
    Args:
        tx_bits: list or 1D array of ground truth bits (0 or 1)
        rx_bits: list or 1D array of received demodulated bits (0 or 1)
        allow_inversion: if True, tests both normal and inverted polarities (Costas 180-deg ambiguity)
        discard_transient: number of initial bits to ignore (PLL lock time)
        
    Returns:
        dict with keys:
            'ber': float (0.0 to 1.0)
            'bit_errors': int
            'compared_bits': int
            'best_lag': int
            'polarity': +1 or -1
    """
    tx_b = np.array(tx_bits, dtype=np.int8)
    rx_b = np.array(rx_bits, dtype=np.int8)
    
    if len(tx_b) == 0 or len(rx_b) == 0:
        return {'ber': 1.0, 'bit_errors': len(tx_b), 'compared_bits': len(tx_b), 'best_lag': 0, 'polarity': 1}
        
    best_ber = 1.0
    best_err = len(tx_b)
    best_lag = 0
    best_pol = 1
    compared_bits = max(len(tx_b) - discard_transient, 1)
    
    polarities = [1, -1] if allow_inversion else [1]
    
    for pol in polarities:
        test_rx = rx_b if pol == 1 else (1 - rx_b)
        # Convert {0, 1} to {-1, +1} for cross-correlation
        tx_bipolar = 2 * tx_b - 1
        rx_bipolar = 2 * test_rx - 1
        
        corr = np.correlate(rx_bipolar, tx_bipolar, mode='full')
        lag = np.argmax(corr) - len(tx_b) + 1
        
        if lag < 0 or (lag + len(tx_b)) > len(test_rx):
            # Check partial slice
            start_rx = max(0, lag)
            end_rx = min(len(test_rx), lag + len(tx_b))
            start_tx = start_rx - lag
            end_tx = start_tx + (end_rx - start_rx)
            aligned_rx = test_rx[start_rx:end_rx]
            aligned_tx = tx_b[start_tx:end_tx]
        else:
            aligned_rx = test_rx[lag : lag + len(tx_b)]
            aligned_tx = tx_b
            
        if len(aligned_rx) > discard_transient:
            eval_rx = aligned_rx[discard_transient:]
            eval_tx = aligned_tx[discard_transient:]
            errs = int(np.sum(eval_rx != eval_tx))
            ber = errs / float(len(eval_tx))
            if ber < best_ber:
                best_ber = ber
                best_err = errs
                best_lag = lag
                best_pol = pol
                compared_bits = len(eval_tx)
                
    return {
        'ber': float(best_ber),
        'bit_errors': int(best_err),
        'compared_bits': int(compared_bits),
        'best_lag': int(best_lag),
        'polarity': int(best_pol)
    }

def calculate_packet_metrics(tx_payload_bytes, rx_payload_bytes, payload_size=64):
    """
    Computes packet-level metrics: Packet Delivery Ratio (PDR), Packet Error Rate (PER).
    """
    total_tx_pkts = len(tx_payload_bytes) // payload_size
    total_rx_pkts = len(rx_payload_bytes) // payload_size
    
    if total_tx_pkts == 0:
        return {'pdr': 0.0, 'per': 1.0, 'matched_pkts': 0, 'tx_pkts': 0, 'rx_pkts': 0}
        
    matched_pkts = 0
    for p in range(total_rx_pkts):
        rx_pkt = rx_payload_bytes[p * payload_size : (p + 1) * payload_size]
        for orig_p in range(total_tx_pkts):
            tx_pkt = tx_payload_bytes[orig_p * payload_size : (orig_p + 1) * payload_size]
            if rx_pkt == tx_pkt:
                matched_pkts += 1
                break
                
    pdr = (matched_pkts / float(total_tx_pkts)) * 100.0
    per = 1.0 - (matched_pkts / float(total_tx_pkts))
    
    return {
        'pdr': float(pdr),
        'per': float(per),
        'matched_pkts': int(matched_pkts),
        'tx_pkts': int(total_tx_pkts),
        'rx_pkts': int(total_rx_pkts)
    }
