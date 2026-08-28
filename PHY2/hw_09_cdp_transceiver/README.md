# PHY2 - Stage 09: CDP Modular Hardware Transceiver

## Objective
Establish the complete modular CDP Hardware Transceiver supporting BPSK & QPSK matching the architectural flowgraph pattern of the production CDP hardware transceiver (`PHY2/hardware/cdp_transceiver_pluto.grc`), equipped with Differential Encoding / Decoding to permanently resolve carrier phase ambiguity on live SDR hardware (Pluto SDR, bladeRF, RTL-SDR).

---

## Flowgraph Architecture
```
TX SECTION:
[ Vector Source ] ──> [ Stream to Tagged Stream ] ──> [ CRC32 Generator ] ──┬──> [ Tagged Stream Mux (Input 2) ]
                                                                              ├──> [ Protocol Formatter ] ──> [ Tagged Stream Mux (Input 1) ]
[ Preamble Source ] ──> [ Stream to Tagged Stream ] ─────────────────────────┴──> [ Tagged Stream Mux (Input 0) ]
                                                                                            ↓
                                                                      [ Constellation Modulator (Diff=True) ]
                                                                                            ↓
                                                                             [ SDR Hardware Sink (Pluto/BladeRF) ]
                                                                                            ↓ (RF / OTA)
RX SECTION:                                                                  [ SDR Hardware Source (Pluto/BladeRF/RTL-SDR) ]
                                                                                            ↓
[ Packet Sink ] ← [ CRC32 Checker ] ← [ Repack ] ← [ Correlate Access Code ] ← [ Diff Decoder ] ← [ Decoder ] ← [ Costas ] ← [ Equalizer ] ← [ Corr Est ] ← [ Symbol Sync ] ← [ RRC ] ← [ FLL ] ← [ AGC ]
```

---

## Hardware Execution Commands

```bash
# 1. Run full transceiver on physical Adalm-Pluto SDR:
python3 run_test.py --hw pluto --uri ip:192.168.2.1 --mod QPSK

# 2. Run full transceiver on physical bladeRF:
python3 run_test.py --hw bladerf --mod BPSK

# 3. Run receive-only station with RTL-SDR:
python3 run_test.py --hw rtlsdr --mod BPSK

# 4. Run automated loopback pre-check:
python3 run_test.py --hw sim --mod ALL
```
