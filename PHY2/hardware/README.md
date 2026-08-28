# PHY2 - SDR Hardware Transceiver & Optimization Suite

## Supported SDR Hardware

| Flowgraph / Script | Target SDR | Functionality | Key Features |
|:---|:---|:---|:---|
| [`cdp_transceiver_pluto.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/cdp_transceiver_pluto.grc) | **Adalm-Pluto SDR** | Full-Duplex Transceiver | Uses `iio_pluto_sink` & `iio_pluto_source`, IP URI entry, TX attenuation, RX gain, differential BPSK/QPSK, live constellation display, PDU deframing & message debug. |
| [`cdp_transceiver_bladerf.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/cdp_transceiver_bladerf.grc) | **Nuand bladeRF** | Full-Duplex Transceiver | Uses `soapy_bladerf_sink` & `soapy_bladerf_source`, full RF gain controls, dual BPSK/QPSK, matched filter & Costas recovery. |
| [`cdp_receiver_rtlsdr.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/cdp_receiver_rtlsdr.grc) | **RTL-SDR** | Receive-Only Station | Uses `soapy_rtlsdr_source`, tuner frequency correction (PPM), AGC, matched filter, BPSK/QPSK slicing & CRC32 deframing. |
| [`cdp_transceiver_multi_hardware.grc`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/cdp_transceiver_multi_hardware.grc) | **Multi-Hardware Universal** | Switchable Transceiver | Switch between Pluto SDR, BladeRF, RTL-SDR, and Loopback channel at runtime with clean QT GUI controls. |
| [`optimize_hardware_sdr.py`](file:///home/mushabmna/Documents/CDP_Project/twowaycomdevice/PHY2/hardware/optimize_hardware_sdr.py) | **SDR Hardware Optimizer** | Live Hardware Sweeper | Sweeps loop bandwidths (0.005 to 1.000 rad/sym), gain, and preamble lengths directly over physical SDR hardware. |

---

## Live Hardware Optimization Commands

```bash
# 1. Run live optimization directly over physical Adalm-Pluto SDR:
python3 PHY2/hardware/optimize_hardware_sdr.py --hw pluto --uri ip:192.168.2.1 --freq 433.98e6 --tx-gain 20 --rx-gain 30

# 2. Run live optimization directly over physical Nuand bladeRF:
python3 PHY2/hardware/optimize_hardware_sdr.py --hw bladerf --freq 433.98e6 --tx-gain 20 --rx-gain 30

# 3. Run live optimization using RTL-SDR receiver:
python3 PHY2/hardware/optimize_hardware_sdr.py --hw rtlsdr --freq 433.98e6 --rx-gain 30

# 4. Run hardware emulation optimization (sim pre-check):
python3 PHY2/hardware/optimize_hardware_sdr.py --hw sim
```
