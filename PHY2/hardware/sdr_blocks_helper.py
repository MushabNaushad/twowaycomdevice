#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 SDR Hardware Blocks Helper
Provides unified instantiation and configuration for Adalm-Pluto, Nuand bladeRF,
RTL-SDR, and simulated channel loopbacks in GNU Radio flowgraphs.
Throws explicit RuntimeError exceptions when physical SDR hardware is requested but not connected.
"""

import sys
from gnuradio import gr, blocks, channels

def create_sdr_source_sink(hw_type='sim', uri='ip:192.168.2.1', cf=433.98e6, samp_rate=1e6, tx_gain=20, rx_gain=30):
    """
    Constructs hardware SDR Source and Sink blocks based on specified hardware target.
    Supported hw_type: 'pluto', 'bladerf', 'rtlsdr', 'sim' / 'loopback'.
    
    Raises RuntimeError if physical hardware ('pluto', 'bladerf', 'rtlsdr') is requested
    but the device is not connected or reachable.
    """
    hw = hw_type.lower()
    
    if hw == 'pluto':
        try:
            from gnuradio import iio
            pluto_uri = uri if uri else iio.get_pluto_uri()
            if not pluto_uri:
                raise RuntimeError("No Adalm-Pluto SDR detected on USB or network URI.")
                
            # Pluto Source
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
            raise RuntimeError(
                f"[HARDWARE ERROR] Adalm-Pluto SDR is NOT connected or reachable at URI '{uri}'.\n"
                f"Underlying error: {e}\n"
                f"Please plug in your Adalm-Pluto SDR via USB or verify network connection."
            ) from e
            
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
            raise RuntimeError(
                f"[HARDWARE ERROR] Nuand bladeRF is NOT connected or detected ('bladerf=0').\n"
                f"Underlying error: {e}\n"
                f"Please verify the bladeRF USB 3.0 connection and permissions."
            ) from e
            
    elif hw == 'rtlsdr':
        try:
            import osmosdr
            src = osmosdr.source("rtl=0")
            src.set_sample_rate(int(samp_rate))
            src.set_center_freq(int(cf), 0)
            src.set_gain(rx_gain, 0)
            return src, None, 'rtlsdr'
        except Exception as e:
            raise RuntimeError(
                f"[HARDWARE ERROR] RTL-SDR receiver is NOT connected or detected ('rtl=0').\n"
                f"Underlying error: {e}\n"
                f"Please plug in your RTL-SDR dongle via USB."
            ) from e
            
    elif hw in ['sim', 'loopback']:
        # Simulation Loopback Channel with RF impairments
        chan = channels.channel_model(
            noise_voltage=0.03,
            frequency_offset=0.005,
            epsilon=1.0001,
            taps=[1.0, 0.15, 0.05],
            noise_seed=42
        )
        return chan, chan, 'sim'
    else:
        raise ValueError(f"Unknown hardware target '{hw_type}'. Supported: 'pluto', 'bladerf', 'rtlsdr', 'sim'.")
