# PHY2 - Stage 02: BPSK with RRC Pulse Shaping & AWGN Channel

## Objective
Introduce Root-Raised Cosine (RRC) pulse shaping at the transmitter and matched filtering at the receiver with samples-per-symbol $sps=4$ and excess bandwidth $\alpha=0.35$. Characterize Bit Error Rate (BER) performance across varying noise voltages ($V_n$).

## Flowgraph Architecture
```
[ Vector Source (bytes) ]
           ↓
[ Constellation Modulator ] -> RRC Pulse Shaping (sps=4, alpha=0.35)
           ↓
[ Channel Model ] -> AWGN Noise Injection (noise_voltage)
           ↓
[ Analog AGC ] -> Dynamic Gain Normalization (rate=1e-2, ref=1.0)
           ↓
[ FFT / FIR Matched Filter ] -> RRC Rx Filter (rcc_taps, ntaps=32*sps)
           ↓
[ Constellation Decoder / Slicer ] -> Maps sampled complex symbols to bits
           ↓
[ Vector Sink (complex samples / decoded bytes) ]
```

## Mathematical Principle
The overall raised cosine channel response satisfies the Nyquist criterion for zero Intersymbol Interference (ISI):
$$H_{RC}(f) = H_{TX\_RRC}(f) \cdot H_{RX\_RRC}(f)$$
The theoretical Bit Error Rate under AWGN is given by:
$$P_b = Q\left(\sqrt{\frac{2 E_b}{N_0}}\right) = \frac{1}{2} \text{erfc}\left(\sqrt{\frac{E_b}{N_0}}\right)$$

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: 0.0 BER on clean channel, with monotonic BER degradation as noise voltage increases.
