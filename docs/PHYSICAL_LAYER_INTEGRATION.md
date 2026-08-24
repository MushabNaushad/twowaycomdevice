# Physical Layer (PHY) & Transport Layer Integration Guide

This document specifies the exact in-band binary transport protocol frame format for developers implementing or integrating the physical layer (`CDP transeciever.grc`, preamble detectors, framing, QPSK/BPSK modulators, and SDRs).

---

## 1. Architectural Overview

The Transport Layer (`gr-transport`) is fully **in-band**. It does NOT rely on GNU Radio PMT in-memory dictionaries for over-the-air signaling. Every packet pushed to `pdu_out` is a self-contained binary frame with an **18-byte Transport Protocol Header**.

```
+-------------------------------------------------------------------------------+
|                             Application Layer                                 |
|   (Injects [8B Application Header] + [Raw Payload: Text / Image / Audio])     |
+-------------------------------------------------------------------------------+
                                      │ (app_in)
                                      ▼
+-------------------------------------------------------------------------------+
|                       Transport Layer (gr-transport)                          |
|   - Performs Selective-Repeat ARQ / Sliding Window                            |
|   - Handles Connection State Machine: SYN -> SYN_ACK -> DATA -> ACK -> FIN    |
|   - Prepends 18-Byte Binary Transport Header to all Control & DATA frames     |
+-------------------------------------------------------------------------------+
                                      │ (pdu_out)
                                      ▼
+-------------------------------------------------------------------------------+
|                       Physical Layer (CDP Transceiver)                        |
|   - Reads PDU bytes from cdr(pdu)                                             |
|   - Adds Preamble, Sync Word / Flags, and CRC (e.g. 0x7E or Barker 13)        |
|   - Modulates (QPSK / BPSK / FSK) -> DAC -> RF Antenna Transmit               |
+-------------------------------------------------------------------------------+
```

---

## 2. The 18-Byte Binary Transport Header Format

Every frame output on `pdu_out` (both control frames and data chunks) has the following fixed 18-byte big-endian binary header:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| pkt_type (1B) | media_type(1B)|  src_addr (1B)|  src_port (1B)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  dst_addr (1B)|  dst_port (1B)|       seq_no (2B, BE)         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      total_packets (2B, BE)   |                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               +
|                    session_id (8B, Big-Endian)                |
|                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Data Payload Chunk (Bytes 18..N, only in DATA frames)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Byte-by-Byte Field Specification

| Offset (Bytes) | Field Name | Data Type | Description |
| :---: | :---: | :---: | :--- |
| **0** | `pkt_type` | `uint8` | `0x01` = **SYN**<br>`0x02` = **SYN_ACK**<br>`0x03` = **DATA**<br>`0x04` = **ACK**<br>`0x05` = **FIN**<br>`0x06` = **FIN_ACK** |
| **1** | `media_type` | `uint8` | `0x01` = **Text**<br>`0x02` = **Image** (JPEG/PNG/Bitmap)<br>`0x03` = **Audio** (PCM/Opus)<br>`0x00` = Generic / None |
| **2** | `src_addr` | `uint8` | Transmitting Node Address (`0x01 .. 0xFE`) |
| **3** | `src_port` | `uint8` | Transmitting Service Port (`0x00` = default) |
| **4** | `dst_addr` | `uint8` | Target Node Address (`0x01 .. 0xFE`, or `0x00` = Broadcast) |
| **5** | `dst_port` | `uint8` | Target Service Port (`0x00` = any) |
| **6–7** | `seq_no` | `uint16_be` | Modular sequence number (`0 .. 2^m - 1`) for DATA and ACK frames |
| **8–9** | `total_packets` | `uint16_be` | Total number of data packets in this session (carried in SYN) |
| **10–17** | `session_id` | `uint64_be` | Unique 64-bit random session nonce to isolate sessions |

---

## 3. Frame Sizes over the Physical Layer

| Frame Type | Header Size | Payload Size | Total Over-The-Air Bytes |
| :--- | :---: | :---: | :---: |
| **SYN** | 18 Bytes | 0 Bytes | **18 Bytes** |
| **SYN_ACK** | 18 Bytes | 0 Bytes | **18 Bytes** |
| **DATA** | 18 Bytes | $1 .. \text{MTU}$ Bytes | **$18 + \text{MTU}$ Bytes** (e.g. 518B for 500B MTU) |
| **ACK** | 18 Bytes | 0 Bytes | **18 Bytes** |
| **FIN** | 18 Bytes | 0 Bytes | **18 Bytes** |
| **FIN_ACK** | 18 Bytes | 0 Bytes | **18 Bytes** |

---

## 4. How Physical Layer Blocks Should Process PDUs

### Transmission Path (TX):
```
[gr-transport (pdu_out)]
          │  PDU: cons(dict, u8vector[18 + payload_len])
          ▼
[pdu_to_tagged_stream]  (Converts PDU byte vector to tagged byte stream)
          │
          ▼
[Preamble & Sync Inserter] (e.g. Barker code / 0x7E Flag)
          │
          ▼
[Modulator: QPSK / BPSK] (Symbols -> Complex IQ)
          │
          ▼
[SDR Sink: bladeRF / USRP / HackRF]
```

### Reception Path (RX):
```
[SDR Source: bladeRF / USRP / HackRF]
          │
          ▼
[Carrier / Timing Sync & Demodulator] (IQ -> Demodulated Bits/Bytes)
          │
          ▼
[Sync Word Detector / Correlator & Deframer] (Detects start of frame)
          │
          ▼
[tagged_stream_to_pdu] (Assembles recovered bytes into a PDU: cons(empty_dict, u8vector))
          │
          ▼
[gr-transport (pdu_in)] (Parses 18-byte in-band header directly from u8vector)
```

---

## 5. C++ / Python Decoder Reference for PHY Developers

To inspect, log, or route packets in your PHY blocks without GNU Radio PMT dictionaries:

### Python Example:
```python
def parse_transport_frame(frame_bytes):
    if len(frame_bytes) < 18:
        return None # Corrupt / runt frame
    
    pkt_types = {1: "SYN", 2: "SYN_ACK", 3: "DATA", 4: "ACK", 5: "FIN", 6: "FIN_ACK"}
    media_types = {1: "text", 2: "image", 3: "audio"}
    
    pkt_type   = pkt_types.get(frame_bytes[0], "UNKNOWN")
    media_type = media_types.get(frame_bytes[1], "unknown")
    src_addr   = frame_bytes[2]
    dst_addr   = frame_bytes[4]
    seq_no     = (frame_bytes[6] << 8) | frame_bytes[7]
    total_pkts = (frame_bytes[8] << 8) | frame_bytes[9]
    session_id = int.from_bytes(frame_bytes[10:18], byteorder='big')
    payload    = frame_bytes[18:] if pkt_type == "DATA" else b""
    
    return {
        "pkt_type": pkt_type,
        "media_type": media_type,
        "src_addr": src_addr,
        "dst_addr": dst_addr,
        "seq_no": seq_no,
        "total_pkts": total_pkts,
        "session_id": session_id,
        "payload_len": len(payload)
    }
```
