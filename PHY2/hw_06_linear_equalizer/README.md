# PHY2 - Stage 06: Hardware Correlation Estimator + Adaptive Equalizer

## Objective
Implement a hardware-ready frame synchronizer and multipath equalizer by coupling the Correlation Estimator (`digital.corr_est_cc`) directly with the 11-tap Adaptive Linear Equalizer (`digital.linear_equalizer`), utilizing modulated training sequences to trigger CMA/LMS equalizer convergence and cancel Intersymbol Interference (ISI) on physical SDR hardware.

---

## Architecture
```
[ Vector Source ] → [ Generic Modulator ] → [ SDR HW Sink / Channel ]
                                                    ↓
[ Vector Sink ] ← [ Decoder ] ← [ Costas Loop ] ← [ Linear Equalizer (CMA) ] ← [ Corr Estimator ] ← [ Symbol Sync ] ← [ RRC ] ← [ FLL ] ← [ AGC ] ← [ SDR HW Source ]
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
