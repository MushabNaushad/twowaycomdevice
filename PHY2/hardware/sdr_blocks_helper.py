#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 SDR Hardware Blocks Helper
Provides unified instantiation and configuration for Adalm-Pluto, Nuand bladeRF,
RTL-SDR, and simulated channel loopbacks in GNU Radio flowgraphs.
"""

import sys
from gnuradio import gr, blocks, channels

def create_sdr_source_sink(hw_type='sim', uri='ip:192.168.2.1', cf=433.98e6, samp_rate=1e6, tx_gain=20, rx_gain=30):
    """
    Constructs hardware SDR Source and Sink blocks based on specified hardware target.
    Supported hw_type: 'pluto', 'bladerf', 'rtlsdr', 'sim' / 'loopback'.
    """
    hw = hw_type.lower()
    
    if hw == 'pluto':
        try:
            from gnuradio import iio
            # Pluto Source
            pluto_uri = uri if uri else iio.get_pluto_uri()
            src = iio.fmcomms2_source_fc32(pluto_uri, [True, True], 32768)
            src.set_frequency(int(cf))
            src.set_samplerate(int(samp_rate))
            src.set_gain_mode(0, 'manual')
            src.set_gain(0, rx_gain)
            src.set_quadrature(True)
            src.set_rfdc(True)
            src.set_bbdc(True)
            
            # Pluto Sink
            snk = iio.fmcomms2_sink_fc32(pluto_uri, [True, True], 32768, False)
            snk.set_bandwidth(20000000)
            snk.set_frequency(int(cf))
            snk.set_samplerate(int(samp_rate))
            snk.set_attenuation(0, tx_gain)
            
            return src, snk, 'pluto'
        except Exception as e:
            print(f"[WARN] Pluto SDR initialization fallback ({e}). Using simulated RF channel.")
            
    elif hw == 'bladerf':
        try:
            import osmosdr
            src = osmosdr.source("bladerf=0")
            src.set_sample_rate(int(samp_rate))
            src.set_center_freq(int(cf), 0)
            src.set_gain(rx_gain, 0)
            
            snk = osmosdr.sink("bladerf=0")
            snk.set_sample_rate(int(samp_rate))
            snk.set_center_freq(int(cf), 0)
            snk.set_gain(tx_gain, 0)
            
            return src, snk, 'bladerf'
        except Exception as e:
            print(f"[WARN] BladeRF initialization fallback ({e}). Using simulated RF channel.")
            
    elif hw == 'rtlsdr':
        try:
            import osmosdr
            src = osmosdr.source("rtl=0")
            src.set_sample_rate(int(samp_rate))
            src.set_center_freq(int(cf), 0)
            src.set_gain(rx_gain, 0)
            return src, None, 'rtlsdr'
        except Exception as e:
            print(f"[WARN] RTL-SDR initialization fallback ({e}). Using simulated RF channel.")
            
    # Default: Simulation Loopback Channel with RF impairments
    chan = channels.channel_model(
        noise_voltage=0.03,
        frequency_offset=0.005,
        epsilon=1.0001,
        taps=[1.0, 0.15, 0.05],
        noise_seed=42
    )
    return chan, chan, 'sim'
