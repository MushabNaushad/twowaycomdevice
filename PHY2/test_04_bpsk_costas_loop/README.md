# PHY2 - Stage 04: BPSK with Costas Loop Carrier Phase Recovery

## Objective
Implement carrier frequency and phase tracking using a 2nd-order Costas Loop (`digital.costas_loop_cc(costas_bw, 2)`). Demonstrate carrier lock and handle the $180^\circ$ phase ambiguity.

## Flowgraph Architecture
```
[ Vector Source ]
       ↓
[ Constellation Modulator ] (BPSK)
       ↓
[ Channel Model ] (Carrier Frequency Offset Δf)
       ↓
[ Analog AGC ]
       ↓
[ RRC Filter ]
       ↓
[ Symbol Synchronizer ]
       ↓
[ Costas Loop ] (Order=2, w=costas_bw=0.0628) -> Phase & Fine Frequency Correction
       ↓
[ Constellation Decoder ]
       ↓
[ Vector Sink ]
```

## Mathematical Principle
For BPSK, the Costas error detector is:
$$e_k = \text{Re}(y_k) \cdot \text{Im}(y_k)$$
The 2nd-order loop filter updates the internal phase accumulator:
$$\theta_{k+1} = \theta_k + \omega_k + \alpha e_k, \quad \omega_{k+1} = \omega_k + \beta e_k$$
where $\alpha, \beta$ are loop coefficients derived from `costas_bw`.

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: 0.0 Steady-State BER across carrier frequency offsets.
