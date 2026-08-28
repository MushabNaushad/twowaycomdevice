#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Adapted Original Transceiver Test Runner (y·y' TED)
"""

import sys
import os
import time

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PHY2.adapted_original.adapted_transceiver import AdaptedOriginalTransceiver
from PHY2.hardware.sdr_blocks_helper import create_sdr_source_sink

def run_stage_adapted_original(hw_type='sim', mod_type='ALL', uri='ip:192.168.2.1', freq=433.98e6, gain=20.0):
    if hw_type.lower() != 'sim':
        # Verify SDR Hardware connectivity (raises explicit RuntimeError if disconnected)
        create_sdr_source_sink(hw_type=hw_type, uri=uri, cf=freq, tx_gain=gain, rx_gain=gain)
        
    mods = ['BPSK', 'QPSK'] if mod_type == 'ALL' else [mod_type]
    packets = 20
    payload_size = 64
    payload = [int((p * 17 + i) % 256) for p in range(packets) for i in range(payload_size)]
    all_passed = True
    
    for m in mods:
        tb = AdaptedOriginalTransceiver(
            test_payload=payload,
            mod_type=m,
            payload_size=payload_size,
            packets=packets,
            preamble_size=32,
            fll_loop_bw=0.0314,
            costas_bw=0.0628,
            sym_bw=0.025,
            noise_volt=0.02,
            freq_offset=0.005,
            time_offset=1.0001
        )
        tb.run()
        rx = list(tb.packet_sink.data())
        rx_pkts = len(rx) // payload_size
        pdr = (rx_pkts / float(packets)) * 100.0
        if pdr < 80.0:
            all_passed = False
    return all_passed

if __name__ == '__main__':
    sys.exit(0 if run_stage_adapted_original() else 1)
