# PHY2 - Stage 10: Hardware End-to-End Stress & Multi-Impairment Validation

## Objective
Stress-test the end-to-end transceiver over high packet volumes (100 frames / 6,400 bytes) under concurrent multi-impairments on physical SDR hardware (Pluto SDR, bladeRF, RTL-SDR):
- Carrier frequency offset ($\pm 1.8\%$)
- Clock sampling drift ($\epsilon = 0.9997 .. 1.0003$)
- AWGN channel noise ($V_n = 0.05 .. 0.15$)

---

## Performance Metrics
- **Packet Delivery Ratio (PDR %)**: Ratio of received CRC-valid packets to total transmitted packets ($99.0\%$).
- **Bit Error Rate (BER)**: Residual payload bit corruption rate (0.0 for delivered packets).
- **Effective Throughput**: Sustained byte processing rate through the PHY layer ($>1.0\text{ Mbps}$).

---

## Hardware Execution Commands

```bash
# 1. Run 100-packet stress test on physical Pluto SDR:
python3 run_test.py --hw pluto --uri ip:192.168.2.1 --mod ALL

# 2. Run 100-packet stress test on physical bladeRF:
python3 run_test.py --hw bladerf --mod ALL

# 3. Run in simulated hardware mode:
python3 run_test.py --hw sim --mod ALL
```
