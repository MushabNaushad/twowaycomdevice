#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY4 SDR Hardware Configuration Helper
Supports Pluto SDR Transmitter and BladeRF / Pluto / RTL-SDR Receivers.
"""

import sys
from gnuradio import gr, blocks, channels

def create_sdr_tx_rx(tx_hw='pluto', rx_hw='bladerf', uri='ip:192.168.1.10', cf=433.98e6, samp_rate=1e6, tx_gain=20.0, rx_gain=45.0):
    """
    Constructs dedicated TX and RX hardware blocks.
    Default configuration:
      - Transmitter: Analog Devices Adalm-Pluto SDR
      - Receiver: Nuand bladeRF SDR
    """
    tx_hw = tx_hw.lower()
    rx_hw = rx_hw.lower()
    
    # -------------------------------------------------------------
    # 1. Transmitter Setup (Pluto SDR by default)
    # -------------------------------------------------------------
    tx_snk = None
    if tx_hw == 'pluto':
        try:
            from gnuradio import iio
            pluto_uri = uri if uri else iio.get_pluto_uri()
            if not pluto_uri:
                raise RuntimeError("No Adalm-Pluto SDR detected on network URI or USB.")
            tx_snk = iio.fmcomms2_sink_fc32(pluto_uri, [True, True], 32768, False)
            tx_snk.set_bandwidth(20000000)
            tx_snk.set_frequency(int(cf))
            tx_snk.set_samplerate(int(samp_rate))
            tx_snk.set_attenuation(0, tx_gain)
        except Exception as e:
            raise RuntimeError(
                f"[TX HARDWARE ERROR] Adalm-Pluto SDR Transmitter is NOT reachable at URI '{uri}'.\n"
                f"Underlying error: {e}\n"
                f"Please verify Pluto SDR USB/Ethernet connection."
            ) from e
    elif tx_hw == 'bladerf':
        try:
            import osmosdr
            tx_snk = osmosdr.sink("bladerf=0")
            tx_snk.set_sample_rate(int(samp_rate))
            tx_snk.set_center_freq(int(cf), 0)
            tx_snk.set_gain(tx_gain, 0)
        except Exception as e:
            raise RuntimeError(
                f"[TX HARDWARE ERROR] Nuand bladeRF transmitter is NOT detected ('bladerf=0').\n"
                f"Underlying error: {e}"
            ) from e
    elif tx_hw in ['sim', 'loopback']:
        tx_snk = None
    else:
        raise ValueError(f"Unsupported TX hardware target: '{tx_hw}'. Supported: 'pluto', 'bladerf', 'sim'.")

    # -------------------------------------------------------------
    # 2. Receiver Setup (BladeRF by default)
    # -------------------------------------------------------------
    rx_src = None
    if rx_hw == 'bladerf':
        try:
            import osmosdr
            rx_src = osmosdr.source("bladerf=0")
            rx_src.set_sample_rate(int(samp_rate))
            rx_src.set_center_freq(int(cf), 0)
            rx_src.set_gain(rx_gain, 0)
        except Exception as e:
            raise RuntimeError(
                f"[RX HARDWARE ERROR] Nuand bladeRF receiver is NOT detected ('bladerf=0').\n"
                f"Underlying error: {e}\n"
                f"Please verify the bladeRF USB 3.0 connection and device permissions."
            ) from e
    elif rx_hw == 'pluto':
        try:
            from gnuradio import iio
            pluto_uri = uri if uri else iio.get_pluto_uri()
            rx_src = iio.fmcomms2_source_fc32(pluto_uri, [True, True], 32768)
            rx_src.set_frequency(int(cf))
            rx_src.set_samplerate(int(samp_rate))
            rx_src.set_gain_mode(0, 'manual')
            rx_src.set_gain(0, rx_gain)
            rx_src.set_quadrature(True)
            rx_src.set_rfdc(True)
            rx_src.set_bbdc(True)
        except Exception as e:
            raise RuntimeError(
                f"[RX HARDWARE ERROR] Adalm-Pluto SDR receiver is NOT reachable at URI '{uri}'.\n"
                f"Underlying error: {e}"
            ) from e
    elif rx_hw == 'rtlsdr':
        try:
            import osmosdr
            rx_src = osmosdr.source("rtl=0")
            rx_src.set_sample_rate(int(samp_rate))
            rx_src.set_center_freq(int(cf), 0)
            rx_src.set_gain(rx_gain, 0)
        except Exception as e:
            raise RuntimeError(
                f"[RX HARDWARE ERROR] RTL-SDR receiver is NOT detected ('rtl=0').\n"
                f"Underlying error: {e}"
            ) from e
    elif rx_hw in ['sim', 'loopback']:
        rx_src = None
    else:
        raise ValueError(f"Unsupported RX hardware target: '{rx_hw}'. Supported: 'bladerf', 'pluto', 'rtlsdr', 'sim'.")

    return tx_snk, rx_src
