# Application Layer Bitstream Format

## Overview

This document defines the **bitstream format** used by the application layer when
communicating with the `transport_layer` GNU Radio block over the `app_in` /
`app_out` message ports.

All data delivered to `app_in` — whether a UTF-8 text message, a JPEG/PNG image,
or a raw PCM/MP3 audio clip — is wrapped in this common frame before being handed
to the transport layer for packetization and transmission.  
On the receiving side, the transport layer reassembles the bitstream and delivers
the **identical byte sequence** (header included) on `app_out`, so the receiving
application can parse the type and length fields independently.

---

## Frame Structure

```
 Byte offset │ Size │ Field
─────────────┼──────┼───────────────────────────────────────
     0 – 1   │  2 B │ Magic Number  (0xAB 0xCD)
       2     │  1 B │ Data Type     (see table below)
       3     │  1 B │ Reserved      (must be 0x00)
     4 – 7   │  4 B │ Payload Length (uint32, big-endian)
     8 – N   │  N B │ Raw Payload Bytes
```

**Total header size: 8 bytes.**

---

## Field Definitions

### Magic Number (bytes 0–1)

| Byte 0 | Byte 1 |
|--------|--------|
| `0xAB` | `0xCD` |

The receiver checks this field first. Any frame where bytes 0–1 do not match
`0xAB 0xCD` is discarded at the application layer.

---

### Data Type (byte 2)

| Code   | Type   | Expected Encoding |
|--------|--------|-------------------|
| `0x01` | Text   | UTF-8 encoded string |
| `0x02` | Image  | JPEG or PNG raw bytes |
| `0x03` | Audio  | PCM (raw 16-bit LE) or MP3 bytes |

Values `0x04`–`0xFF` are reserved for future use.  
The transport layer reads this byte and stores it as the `payload_type` key in
the PMT metadata dictionary included in the **SYN** control frame, so the remote
node knows the incoming data type before any DATA frames arrive.

---

### Reserved (byte 3)

Must be set to `0x00` by the sender. Reserved for future flags
(e.g., compression, encryption indicators).

---

### Payload Length (bytes 4–7)

A 32-bit unsigned integer in **network byte order (big-endian)** giving the
number of raw payload bytes that follow the header.

```
PayloadLength = N  (does NOT include the 8-byte header itself)
Total frame size = 8 + N bytes
```

---

### Raw Payload (bytes 8–N+7)

| Type   | Payload content |
|--------|-----------------|
| Text   | UTF-8 encoded string, no null terminator required |
| Image  | Complete JPEG or PNG file bytes |
| Audio  | Complete MP3 file bytes, or interleaved 16-bit PCM samples |

---

## Byte-Level Example — Text Message "Hello"

```
AB CD 01 00 00 00 00 05 48 65 6C 6C 6F
│  │  │  │  └──────────────┘  └───────────────────┘
│  │  │  │     Length = 5       "Hello" in ASCII/UTF-8
│  │  │  └── Reserved = 0x00
│  │  └───── Type = 0x01 (Text)
│  └──────── Magic byte 1 = 0xCD
└─────────── Magic byte 0 = 0xAB
```

---

## Integration Notes

### Sender Side (`app_in` port)

```python
import pmt, struct

payload = b"Hello"
header  = bytes([0xAB, 0xCD, 0x01, 0x00]) + struct.pack(">I", len(payload))
frame   = header + payload

meta    = pmt.make_dict()
data    = pmt.init_u8vector(len(frame), list(frame))
pdu     = pmt.cons(meta, data)
# post pdu to app_in
```

### Receiver Side (`app_out` port)

The `app_out` port delivers a PMT pair where:
- `pmt::car(msg)` — metadata dict with keys:
  - `"payload_type"` → PMT symbol (`"text"`, `"image"`, or `"audio"`)
  - `"session_id"`   → PMT uint64
- `pmt::cdr(msg)` — u8vector of the **complete bitstream** (header + payload).

---

## Transport Layer Internal Behaviour

When `handle_app_in()` receives the frame it:

1. Validates magic bytes `0xAB 0xCD`. Drops the frame on mismatch.
2. Reads byte 2 to extract `payload_type` → stored as `d_payload_type_pmt`.
3. Reads bytes 4–7 (big-endian uint32) to verify declared length vs. actual
   vector length. Drops on mismatch.
4. Packetizes the entire frame (header + payload) into MTU-sized chunks in
   `d_tx_buffer[]`.
5. Advertises `payload_type` and `total_packets` in the **SYN** PDU so the
   remote node can pre-allocate its reassembly buffer.

---

## Constraints

| Parameter | Value |
|-----------|-------|
| Header size | 8 bytes (fixed) |
| Max payload (theoretical) | 2³² − 1 bytes |
| Minimum valid frame | 8 bytes (`PayloadLength = 0`) |
