# PHY2 - Stage 08: Hardware Packet Engine & CRC32 Verification

## Objective
Implement end-to-end tagged stream packet framing, CRC32 generation, protocol header formatting, stream multiplexing, access code correlation, bit repacking, and CRC32 verification across BPSK and QPSK on live SDR hardware.

---

## Architecture
```
TX PIPELINE:
[ Payload Source ] → [ CRC32 Generator ] → [ Protocol Formatter ] ──┐
[ Preamble Source ] ───────────────────────────────────────────────┼─→ [ Tagged Stream Mux ] → [ Modulator ] → [ SDR HW Sink ]
                                                                    │                                                 ↓
RX PIPELINE:                                                        │                                          [ SDR HW Source ]
[ Packet Sink ] ← [ CRC32 Checker ] ← [ Repack Bits ] ← [ Correlate Access Code ] ← [ Decoder ] ← [ Costas Loop ] ←───────┘
```

---

## Hardware Execution Commands

```bash
# 1. Run on physical Pluto SDR:
python3 run_test.py --hw pluto --uri ip:192.168.2.1 --mod ALL

# 2. Run on physical bladeRF:
python3 run_test.py --hw bladerf --mod ALL

# 3. Run in simulated hardware mode:
python3 run_test.py --hw sim --mod ALL
```
