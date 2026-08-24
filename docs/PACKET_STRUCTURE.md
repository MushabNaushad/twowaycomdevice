# Transport Layer In-Band Packet Structure & Hexdump Guide

This document provides a comprehensive reference for the binary packet format used by the **Transport Layer (`gr-transport`)** over physical radio channels, including how to read GNU Radio's message debug hexdumps.

---

## 1. The 18-Byte In-Band Transport Protocol Header

Every frame transmitted over the physical layer (both control frames and data chunks) begins with a fixed **18-byte Big-Endian binary header**:

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

### Field Reference Table

| Byte Offset | Field Name | Type | Description |
| :---: | :---: | :---: | :--- |
| **0** | `pkt_type` | `uint8` | `0x01` = **SYN**<br>`0x02` = **SYN_ACK**<br>`0x03` = **DATA**<br>`0x04` = **ACK**<br>`0x05` = **FIN**<br>`0x06` = **FIN_ACK** |
| **1** | `media_type` | `uint8` | `0x01` = **Text**<br>`0x02` = **Image**<br>`0x03` = **Audio**<br>`0x00` = None / Control |
| **2** | `src_addr` | `uint8` | Transmitter Node ID (`0x01 .. 0xFE`) |
| **3** | `src_port` | `uint8` | Transmitter Service Port (`0x00` = default) |
| **4** | `dst_addr` | `uint8` | Receiver Target Node ID (`0x01 .. 0xFE`, `0x00` = Broadcast) |
| **5** | `dst_port` | `uint8` | Receiver Service Port (`0x00` = any) |
| **6–7** | `seq_no` | `uint16_be` | Modular sequence number (`0 .. 2^m - 1`) for DATA and ACK packets |
| **8–9** | `total_packets` | `uint16_be` | Total number of data packets in this session (carried in SYN) |
| **10–17** | `session_id` | `uint64_be` | 64-bit cryptographic random session nonce to isolate sessions |
| **18+** | `payload` | `bytes` | Raw payload chunk bytes (present only in `DATA` packets) |

---

## 2. Reading GNU Radio Hexdumps

When a packet is received by `blocks_message_debug`, it prints a hexdump where each row shows **16 bytes (`0x10`)**:

```text
0000: 03 02 05 00 09 00 00 03 00 05 e3 94 6b 8b a7 d2 
0010: 41 70 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 
0020: 0e 0f 10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 
0030: 1e 1f 20 21 22 23 24 25 26 27 28 29 2a 2b 2c 2d 
```

### What the 4 Digits Before the Colon Mean:
The 4-digit prefix is the **Hexadecimal Starting Byte Index** for that row:

| Hex Prefix | Decimal Byte Index | Bytes Displayed in this Row |
| :---: | :---: | :--- |
| **`0000:`** | Byte 0 | Bytes 0 to 15 (First 16 bytes of header) |
| **`0010:`** | Byte 16 | Bytes 16 to 31 (Bytes 16-17 of header + First 14 payload bytes) |
| **`0020:`** | Byte 32 | Bytes 32 to 47 (Next 16 payload bytes) |
| **`0030:`** | Byte 48 | Bytes 48 to 63 (Next 16 payload bytes) |
| **`0040:`** | Byte 64 | Bytes 64 to 79 |
| **`...`** | ... | ... |
| **`00f0:`** | Byte 240 | Bytes 240 to 255 |
| **`0100:`** | Byte 256 | Bytes 256 to 271 |
| **`0110:`** | Byte 272 | Bytes 272 to 287 |

---

## 3. What Happens When Packets Have More Than 4 Rows?

Whenever a payload chunk is larger than 46 bytes, the hexdump will have **more than 4 rows**. 

The row counter simply continues counting upwards in **hexadecimal (`+0x10` per row)**:

### Example: A 274-Byte Packet (18B Header + 256B MTU Chunk)
For a 256-byte MTU frame, there are $\lceil 274 / 16 \rceil = \mathbf{18\text{ rows}}$:

```text
0000:  (Bytes 0..15  -> 16B of Header)
0010:  (Bytes 16..31 -> 2B Header + 14B Payload)
0020:  (Bytes 32..47 -> 16B Payload)
0030:  (Bytes 48..63 -> 16B Payload)
0040:  (Bytes 64..79 -> 16B Payload)
...
0090:  (Bytes 144..159)
00a0:  (Bytes 160..175)
00b0:  (Bytes 176..191)
00c0:  (Bytes 192..207)
00d0:  (Bytes 208..223)
00e0:  (Bytes 224..239)
00f0:  (Bytes 240..255)
0100:  (Bytes 256..271)  <-- Notice: 0x0100 = 256 in decimal!
0110:  (Bytes 272..273)  <-- Final 2 bytes of the 274-byte packet
```

### Example: A 1018-Byte Packet (18B Header + 1000B MTU Chunk)
For a 1000-byte MTU frame, there are $\lceil 1018 / 16 \rceil = \mathbf{64\text{ rows}}$, counting all the way from `0000:` up to `03f0:` (`0x03F0` = byte 1008 to 1017).

---

## 4. Control Frame Hexdump Examples

### 1. SYN Frame (18 Bytes):
```text
pdu length = 18 bytes
0000: 01 02 05 00 09 00 00 00 00 05 e3 94 6b 8b a7 d2 
0010: 41 70
```
- `01` = SYN, `02` = Image, `05` = Src 5, `09` = Dst 9, `00 05` = 5 packets, `0xE3946B8BA7D24170` = Session ID.

### 2. ACK Frame (18 Bytes):
```text
pdu length = 18 bytes
0000: 04 00 09 00 05 00 00 03 00 00 e3 94 6b 8b a7 d2 
0010: 41 70
```
- `04` = ACK, `09` = Src 9, `05` = Dst 5, `00 03` = ACKing sequence #3.

### 3. FIN Frame (18 Bytes):
```text
pdu length = 18 bytes
0000: 05 00 05 00 09 00 00 00 00 00 e3 94 6b 8b a7 d2 
0010: 41 70
```
- `05` = FIN, `05` = Src 5, `09` = Dst 9, closing session.
