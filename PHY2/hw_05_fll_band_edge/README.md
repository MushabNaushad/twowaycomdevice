# PHY2 - Stage 05: Hardware FLL Band-Edge Frequency Recovery

## Objective
Implement wide-range coarse carrier frequency acquisition using the Frequency-Locked Loop (FLL) Band-Edge block (`digital.fll_band_edge_cc`), extending carrier pull-in range for large frequency offsets up to $\pm 5\%$ of sampling rate across live SDR hardware (Pluto SDR, bladeRF, RTL-SDR).

---

## Architecture
```
[ Vector Source ] → [ Generic Modulator (BPSK/QPSK) ] → [ SDR HW Sink / Channel ]
                                                                ↓
[ Vector Sink ] ← [ Decoder ] ← [ Costas Loop ] ← [ Symbol Sync ] ← [ RRC ] ← [ FLL Band-Edge ] ← [ AGC ] ← [ SDR HW Source ]
```

---

## Hardware Execution Commands

```bash
# 1. Run on physical Pluto SDR:
python3 run_test.py --hw pluto --uri ip:192.168.2.1 --mod ALL

# 2. Run on physical bladeRF:
python3 run_test.py --hw bladerf --mod ALL

# 3. Run in simulated hardware mode (pre-check):
python3 run_test.py --hw sim --mod ALL
```
