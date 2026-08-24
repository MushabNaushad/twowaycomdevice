# PHY2 - SDR Hardware Transceiver Suite

## Overview
This directory contains production-ready GNU Radio flowgraphs and Python scripts configured for direct over-the-air (OTA) and cabled RF operation with real SDR hardware:
- **Analog Devices ADALM-PLUTO (Pluto SDR)**
- **Nuand bladeRF / bladeRF 2.0 micro**
- **RTL-SDR (RTL2832U)**
- **HackRF One / LimeSDR / USRP**

---

## Hardware Flowgraph Inventory

| Flowgraph File | Supported Hardware | Operating Mode | Features |
|:---|:---|:---:|:---|
| [`cdp_transceiver_pluto.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/cdp_transceiver_pluto.grc) | **Adalm-Pluto SDR** | Full-Duplex Transceiver | Uses `iio_pluto_sink` & `iio_pluto_source`, IP URI entry, TX attenuation, RX gain, differential BPSK, live constellation display, PDU deframing & message debug. |
| [`cdp_transceiver_bladerf.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/cdp_transceiver_bladerf.grc) | **Nuand bladeRF** | Full-Duplex Transceiver | Uses `soapy_bladerf_sink` & `soapy_bladerf_source`, center frequency range, TX/RX gain sliders, differential BPSK, live constellation sink. |
| [`cdp_receiver_rtlsdr.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/cdp_receiver_rtlsdr.grc) | **RTL-SDR** | Dedicated Receiver | Uses `soapy_rtlsdr_source`, center frequency range, RF gain slider, full BPSK demodulator, CRC32 checker & PDU output. |
| [`cdp_transceiver_multi_hardware.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/cdp_transceiver_multi_hardware.grc) | **Universal Multi-Hardware** | Toggleable Front-End | Includes Pluto SDR, bladeRF, and RTL-SDR blocks side-by-side. Enable/disable whichever SDR device is physically connected directly inside GRC. |

---

## Incremental Hardware Flowgraphs in Test Stages

For each test stage, dedicated hardware flowgraphs are available to test directly with your physical SDR:
- [`PHY2/test_07_bpsk_preamble_access_code/bpsk_preamble_access_code_hardware.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/test_07_bpsk_preamble_access_code/bpsk_preamble_access_code_hardware.grc)
- [`PHY2/test_08_bpsk_packet_crc32/bpsk_packet_crc32_hardware.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/test_08_bpsk_packet_crc32/bpsk_packet_crc32_hardware.grc)
- [`PHY2/test_09_bpsk_cdp_transceiver/cdp_transceiver_bpsk_hardware.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/test_09_bpsk_cdp_transceiver/cdp_transceiver_bpsk_hardware.grc)

---

## Operating Instructions

### 1. Running with Adalm-Pluto SDR
1. Connect your Pluto SDR via USB (or Ethernet/WiFi).
2. Launch the Pluto transceiver in GNU Radio Companion:
   ```bash
   gnuradio-companion "PHY2/hardware/cdp_transceiver_pluto.grc"
   ```
   Or execute directly in Python:
   ```bash
   python3 "PHY2/hardware/cdp_transceiver_pluto.py"
   ```
3. Set the Pluto URI in the GUI (e.g., `ip:192.168.2.1` or `usb:x.x.x`).
4. Adjust `Center Frequency`, `TX Attenuation`, and `RX Gain` as needed.

### 2. Running with bladeRF
```bash
gnuradio-companion "PHY2/hardware/cdp_transceiver_bladerf.grc"
```

### 3. Running with RTL-SDR Receiver
```bash
gnuradio-companion "PHY2/hardware/cdp_receiver_rtlsdr.grc"
```

### 4. Running the Universal Multi-Hardware Transceiver
```bash
gnuradio-companion "PHY2/hardware/cdp_transceiver_multi_hardware.grc"
```
In GRC, simply click on the hardware source/sink you wish to use (Pluto, BladeRF, RTL-SDR, or Channel Model) and press `E` (Enable) or `D` (Disable).
