# Transport Layer Parameter Tuning & Concurrency Analysis

## Executive Summary

A complete, live **GNU Radio parameter sweep** was conducted on the Selective-Repeat ARQ (`gr-transport`) implementation to tune the protocol's core operational parameters:
- **Sequence Bit Width ($m$)**: Swept across $m \in \{3, 4, 5, 6, 7\}$, yielding sliding window sizes $W = 2^{m-1} \in \{4, 8, 16, 32, 64\}$ frames and sequence number spaces $2^m \in \{8, 16, 32, 64, 128\}$.
- **Maximum Transmission Unit ($\text{MTU}$)**: Swept across $\text{MTU} \in \{100, 200, 500, 1000\}\text{ bytes/frame}$.
- **Channel Drop Probability ($p_{\text{loss}}$)**: Tested across 5 channel conditions: $0\%$ (clean), $5\%$ (light loss), $15\%$ (moderate loss), $30\%$ (heavy loss), and $50\%$ (extreme loss).
- **Concurrency & Topology**: **10 simultaneous nodes** configured as 5 concurrent transmitting pairs $(\text{Node } 1 \to 6, 2 \to 7, 3 \to 8, 4 \to 9, 5 \to 10)$ sharing a single broadcast channel.
- **Total Test Matrix**: **20 configurations $\times$ 5 channel conditions = 100 empirical measurement points**.

Raw data is archived in [`sweep_results.json`](file:///home/methalabeywickrama/Documents/CDP%20Project/twowaycomdevice/tests/perf_sweep/sweep_results.json) and [`sweep_results.csv`](file:///home/methalabeywickrama/Documents/CDP%20Project/twowaycomdevice/tests/perf_sweep/sweep_results.csv).

---

## Key Protocol Discovery & Architectural Bounds

Through C++ source analysis (`transport_layer_impl.cc`) and empirical verification, a critical architectural constraint was identified:

> [!IMPORTANT]
> **Sequence Space Buffer Invariant**:
> In `packetize()`, the buffer vector `d_tx_buffer` is allocated with size $2^m$. Chunks are indexed as $\text{slot} = \text{packet\_idx} \pmod{2^m}$.
> If the total number of packets $N = \lceil \text{Payload} / \text{MTU} \rceil > 2^m$, later chunks overwrite earlier slots before initial frames have been acknowledged, causing buffer corruption.
>
> **Design Rule**: For any payload of size $L$ and frame size $M$, $m$ must satisfy:
> $$m \ge \left\lceil \log_2 \left( \left\lceil \frac{L}{M} \right\rceil \right) \right\rceil$$

---

## Visual Analytics

### 1. Throughput Heatmap ($m \times \text{MTU}$ across Channel Loss Rates)
![Throughput Heatmap](/home/methalabeywickrama/.gemini/antigravity-ide/brain/eae16320-db04-45c9-b5e7-0025288582e0/chart_01_throughput_heatmap.png)

### 2. Throughput Curves vs Channel Loss Rate
![Throughput Curves](/home/methalabeywickrama/.gemini/antigravity-ide/brain/eae16320-db04-45c9-b5e7-0025288582e0/chart_02_throughput_vs_drop.png)

### 3. Delivery Success Rate Matrix
![Delivery Success Rate](/home/methalabeywickrama/.gemini/antigravity-ide/brain/eae16320-db04-45c9-b5e7-0025288582e0/chart_03_success_rate.png)

### 4. Protocol Overhead Ratio
![Protocol Overhead](/home/methalabeywickrama/.gemini/antigravity-ide/brain/eae16320-db04-45c9-b5e7-0025288582e0/chart_04_overhead.png)

### 5. MTU Sensitivity ($m=5, W=16$)
![MTU Sensitivity](/home/methalabeywickrama/.gemini/antigravity-ide/brain/eae16320-db04-45c9-b5e7-0025288582e0/chart_05_mtu_effect.png)

### 6. Recommended Tuning per Channel State
![Recommended Tuning](/home/methalabeywickrama/.gemini/antigravity-ide/brain/eae16320-db04-45c9-b5e7-0025288582e0/chart_06_recommendations.png)

---

## Recommended Parameter Settings

| Channel Condition | Packet Drop ($p_{\text{loss}}$) | Recommended $m$ | Window ($W$) | Recommended MTU | Measured Throughput | Success Rate | Rationale |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Clean Channel** | $0\%$ | **$m=4$ / $m=5$** | $8 - 16$ | **$1000\text{ B}$** | $\sim 0.75\text{ kB/s}$ | **$100\%$** | Large MTU minimizes frame overhead and preamble/header transmissions. |
| **Light Loss** | $5\%$ | **$m=4$ / $m=5$** | $8 - 16$ | **$500\text{ B} - 1000\text{ B}$** | $\sim 0.73\text{ kB/s}$ | **$100\%$** | Moderate window prevents pipeline stalls while absorbing rare dropped ACKs. |
| **Moderate Loss** | $15\%$ | **$m=5$ / $m=7$** | $16 - 64$ | **$500\text{ B}$** | $\sim 1.10\text{ kB/s}$ | **$100\%$** | $W \ge 16$ keeps the transmitter busy during selective-repeat retransmissions. |
| **Heavy Loss** | $30\%$ | **$m=5$** | **$16$** | **$200\text{ B}$** | $\sim 0.71\text{ kB/s}$ | **$100\%$** | Smaller MTU reduces collision/retransmission penalty per corrupted packet. |
| **Extreme Loss** | $\ge 50\%$ | **$m=4$** | **$8$** | **$100\text{ B} - 200\text{ B}$** | $\sim 0.15\text{ kB/s}$ | $\sim 20-40\%$ | Smaller window prevents flood of unacknowledged frames on an overloaded bus. |

---

## Key Conclusions

1. **Window Size ($W = 2^{m-1}$)**:
   - On low-loss channels ($0-5\%$), increasing $W$ beyond $8$ yields diminishing returns since round-trip delay is low.
   - On moderate-to-high loss channels ($15-30\%$), $W \ge 16$ ($m \ge 5$) is essential to keep the pipe saturated while waiting for selective ACKs.
   - For extreme loss ($>40\%$), excessively large windows ($W=64$) cause retransmission storms; $W=8..16$ is optimal.

2. **MTU Size**:
   - Larger MTU ($500\text{B} - 1000\text{B}$) provides higher throughput on clean channels due to reduced framing and synchronization overhead.
   - Smaller MTU ($200\text{B}$) is significantly more resilient in contested, lossy environments ($30\%$ loss) because losing a single frame wastes less channel time.
