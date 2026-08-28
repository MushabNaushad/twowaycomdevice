# PHY2 - Stage 07: Hardware Preamble & Access Code Frame Sync

## Objective
Implement frame synchronization using a hardware-ready training preamble and 64-bit access code (sync word) across BPSK and QPSK on live SDR hardware (Pluto SDR, bladeRF, RTL-SDR).

---

## Architecture
```
[ Vector Source ] → [ Tagged Stream Mux (Preamble + Access Code + Payload) ] → [ Generic Modulator ] → [ SDR HW Sink ]
                                                                                                            ↓
[ Packet Sink ] ← [ Correlate Access Code ] ← [ Diff Decoder ] ← [ Decoder ] ← [ Costas Loop ] ← [ SDR HW Source ]
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
