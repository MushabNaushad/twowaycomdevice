# PHY2 - Stage 03: BPSK with Symbol Synchronization

## Objective
Implement closed-loop timing recovery using GNU Radio's `digital.symbol_sync_cc` to synchronize symbol sampling phase and compensate for fractional clock drift ($\epsilon \ne 1.0$).

## Flowgraph Architecture
```
[ Vector Source ]
       ↓
[ Constellation Modulator ] (BPSK, sps=4, alpha=0.35)
       ↓
[ Channel Model ] (Clock Offset epsilon=1.0005)
       ↓
[ Analog AGC ] (Gain normalization)
       ↓
[ RRC Filter ] (Matched filter)
       ↓
[ Symbol Synchronizer ] (TED: Mueller & Müller / ML, loop_bw=0.045, osps=1)
       ↓
[ Constellation Decoder ]
       ↓
[ Vector Sink ]
```

## Mathematical Principle
The timing error detector (TED) estimates the fractional timing error $\tau_k$. The loop filter updates the sampling phase:
$$\tau_{k+1} = \tau_k + 2\zeta \omega_n e_k + \omega_n^2 \sum_{i=0}^k e_i$$
where $\omega_n$ is normalized loop bandwidth (`sym_bw`) and $\zeta=1.0$ is the critical damping factor.

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: 0.0 Steady-State BER across $\epsilon \in \{0.9995, 1.0, 1.0005\}$.
