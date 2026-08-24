# PHY2 - Stage 06: BPSK with Adaptive Linear Equalizer

## Objective
Implement an adaptive linear equalizer (`digital.linear_equalizer`) utilizing the Constant Modulus Algorithm (CMA) to cancel Intersymbol Interference (ISI) caused by frequency-selective multipath channels.

## Flowgraph Architecture
```
[ Vector Source ]
       ↓
[ Constellation Modulator ] (BPSK)
       ↓
[ Channel Model ] (Multipath Taps [1.0, 0.25, 0.1]) -> Generates ISI
       ↓
[ Analog AGC ]
       ↓
[ FLL Band-Edge ]
       ↓
[ RRC Filter ]
       ↓
[ Symbol Synchronizer ] (osps=1)
       ↓
[ Linear Equalizer ] (11 Taps, CMA adaptive algorithm, step_size=0.001) -> ISI Cancellation
       ↓
[ Costas Loop ]
       ↓
[ Constellation Decoder ]
       ↓
[ Vector Sink ]
```

## Mathematical Principle
The equalizer FIR filter weights $\mathbf{w}_k$ are updated via gradient descent on the constant-modulus dispersion cost function:
$$J(\mathbf{w}) = \mathbb{E}\left[(|y_k|^2 - R_2)^2\right]$$
where $R_2 = \frac{\mathbb{E}[|s|^4]}{\mathbb{E}[|s|^2]} = 1.0$ for BPSK/QPSK. The weight update rule is:
$$\mathbf{w}_{k+1} = \mathbf{w}_k - \mu \cdot e_k \cdot \mathbf{x}_k^*, \quad e_k = y_k (|y_k|^2 - 1)$$

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: 0.0 Steady-State BER across single-path and multipath channel profiles.
