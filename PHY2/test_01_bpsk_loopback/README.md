# PHY2 - Stage 01: Pure Baseband BPSK Loopback

## Objective
Establish the foundational baseband modulation and demodulation stage with binary phase-shift keying (BPSK). Verify 100% bit-exact transmission without channel impairments.

## Flowgraph Architecture
```
[ Vector Source (bytes) ]
           ↓
[ Unpack K Bits (8 bits/byte) ]
           ↓
[ Chunks to Symbols / Constellation Modulator ] -> BPSK Symbol Mapping (0 -> -1, 1 -> +1)
           ↓
[ Constellation Decoder / Slicer ] -> Maps complex symbol back to binary decision
           ↓
[ Pack K Bits (8 bits/byte) ]
           ↓
[ Vector Sink (bytes) ]
```

## Mathematical Principle
For BPSK modulation, each bit $b_k \in \{0, 1\}$ is mapped to a constellation point $s_k \in \{-1, +1\}$ on the complex plane:
$$s_k = 2 b_k - 1$$
The receiver makes minimum distance decisions:
$$\hat{b}_k = \begin{cases} 1, & \text{Re}(y_k) \ge 0 \\ 0, & \text{Re}(y_k) < 0 \end{cases}$$

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: `Transmitted Bytes == Received Bytes` with 0 Bit Error Rate.
