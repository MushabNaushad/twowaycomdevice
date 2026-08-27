# PHY2 - Stage 05: BPSK with FLL Band-Edge Frequency Recovery

## Objective
Implement wide-range coarse carrier frequency acquisition using the Frequency-Locked Loop (FLL) Band-Edge block (`digital.fll_band_edge_cc`), extending carrier pull-in range for large frequency offsets up to $\pm 5\%$ of sampling rate.

## Flowgraph Architecture
```
[ Vector Source ]
       ↓
[ Constellation Modulator ] (BPSK, sps=4, alpha=0.35)
       ↓
[ Channel Model ] (Large Frequency Offset |Δf| > 0.02)
       ↓
[ Analog AGC ]
       ↓
[ FLL Band-Edge ] (sps=4, alpha=0.35, size=2*sps+1, w=fll_loop_bw) -> Coarse Frequency Pull-In
       ↓
[ RRC Filter ] -> Matched Filtering
       ↓
[ Symbol Synchronizer ] -> Timing Recovery
       ↓
[ Costas Loop ] -> Residual Fine Carrier Phase Lock
       ↓
[ Constellation Decoder ]
       ↓
[ Vector Sink ]
```

## Mathematical Principle
The FLL band-edge discriminator filters the signal through two band-edge filters centered at $(1 \pm \alpha) / (2 \cdot sps)$:
$$e_k = |y_{\text{upper}}(k)|^2 - |y_{\text{lower}}(k)|^2$$
When frequency offset is zero, the upper and lower transition band energies are equal ($e_k = 0$). Any carrier offset imbalances the band energy, providing an unbiased error signal for 2nd-order loop frequency acquisition.

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: 0.0 Steady-State BER across large frequency offsets.
