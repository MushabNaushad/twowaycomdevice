# PHY2 - Stage 07: BPSK with Preamble and Access Code Frame Synchronization

## Objective
Implement frame synchronization using a hardware-ready training preamble and 64-bit access code (sync word). Handle byte alignment and resolve the $180^\circ$ Costas phase ambiguity at the packet layer.

## Flowgraph Architecture
```
[ Vector Source ] -> [Preamble (0x55) | Access Code (0xE15AE893...) | Payload | Postamble]
       ↓
[ Constellation Modulator ] (BPSK)
       ↓
[ Channel Model ] (Frequency Offsets & Noise)
       ↓
[ Analog AGC ]
       ↓
[ FLL Band-Edge ]
       ↓
[ RRC Filter ]
       ↓
[ Symbol Synchronizer ]
       ↓
[ Costas Loop ]
       ↓
[ Constellation Decoder ]
       ↓
[ Correlate Access Code Tag (Normal & Inverted) ] -> Emits 'sync_pos' / 'sync_neg'
       ↓
[ Vector Sink / Payload Extractor ]
```

## Mathematical Principle
Cross-correlation of the demodulated bit stream $b_n$ with the sync word $s_k$:
$$C(n) = \sum_{k=0}^{L-1} (2b_{n+k}-1) \cdot (2s_k-1)$$
When $C(n) \ge L - \text{threshold}$, a frame start tag is asserted at bit index $n + L$. If $C(n) \le -(L - \text{threshold})$, an inverted-phase frame start tag is asserted.

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: 100% exact payload recovery with dual-polarity ambiguity resolution.
