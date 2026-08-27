# PHY2 - Stage 10: End-to-End Stress & Multi-Impairment Validation

## Objective
Stress-test the end-to-end transceiver over high packet volumes (100 frames / 6,400 bytes) under concurrent multi-impairments:
- Carrier frequency offset ($\pm 1.8\%$)
- Clock sampling drift ($\epsilon = 0.9997 .. 1.0003$)
- AWGN channel noise ($V_n = 0.05 .. 0.15$)

## Performance Metrics
- **Packet Delivery Ratio (PDR %)**: Ratio of received CRC-valid packets to total transmitted packets.
- **Bit Error Rate (BER)**: Residual payload bit corruption rate (target = 0.0 for delivered packets).
- **Effective Throughput**: Sustained byte processing rate through the PHY layer.

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: PDR $\ge 90\%$, 100% valid CRC on all delivered packets.
