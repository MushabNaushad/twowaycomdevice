# Transport Layer Addressing — Handoff Notes

## What Was Done

The two magic bytes (`0xAB 0xCD`) in the transport layer application bitstream header have been
repurposed as **address** (byte 0) and **port** (byte 1). Lower layers already handle frame
detection and synchronization, so the magic bytes were redundant.

### New Header Format (bytes 0–7)

| Byte | Old meaning          | New meaning                           |
|------|----------------------|---------------------------------------|
| 0    | Magic `0xAB`         | `dst_addr` — destination node address |
| 1    | Magic `0xCD`         | `dst_port` — destination service port |
| 2    | Data type            | Data type (unchanged)                 |
| 3    | Reserved             | Reserved (unchanged)                  |
| 4–7  | Payload length uint32 BE | Payload length (unchanged)        |

### Addressing Rules

- `dst_addr = 0x00` → broadcast (accepted by every node)
- `dst_port  = 0x00` → any port (accepted on any port)
- Node with `local_addr = 0x00` → promiscuous (accepts all destinations)
- Address filtering occurs only at SYN time (session-establishment gate)
- Once a session is live, the existing `session_id` mechanism provides uniqueness

### New PMT Metadata Keys (present on every outgoing PDU)

| Key        | Type   | Description                    |
|------------|--------|--------------------------------|
| `src_addr` | uint64 | Sender node address            |
| `src_port` | uint64 | Sender service port            |
| `dst_addr` | uint64 | Destination node address       |
| `dst_port` | uint64 | Destination service port       |

---

## Files Modified

### `blocks/gr-transport/lib/transport_layer_impl.h`
- Removed `APP_MAGIC_0` / `APP_MAGIC_1` constants
- Added `APP_ADDR_BCAST = 0x00` and `APP_PORT_ANY = 0x00` constants
- Added `const uint8_t d_local_addr` and `const uint8_t d_local_port` members
- Added `uint8_t d_dst_addr` and `uint8_t d_dst_port` session-state fields
- Constructor now accepts `uint8_t local_addr = 0x00, uint8_t local_port = 0x00`

### `blocks/gr-transport/lib/transport_layer_impl.cc`
- Updated file header comment (byte 0–1 description and PMT key list)
- Factory `make()` and constructor accept `local_addr`, `local_port`
- Initializer list seeds `d_local_addr`, `d_local_port`, `d_dst_addr`, `d_dst_port`
- `handle_app_in`: reads `frame[0]` -> `d_dst_addr`, `frame[1]` -> `d_dst_port` (no more magic check)
- `fsm_idle`: added address/port filter — checks dst_addr/dst_port against local_addr/local_port;
  drops mismatched SYNs; saves peer address as d_dst_addr/d_dst_port for outgoing reply frames
- `build_meta`: appends src_addr, src_port, dst_addr, dst_port to every PDU metadata dict
- `try_deliver_rx_buffer`: adds src/dst addr+port to app_out metadata
- `reset_state`: resets d_dst_addr and d_dst_port to 0

### `blocks/gr-transport/include/transport/transport_layer.h`
- Updated docstring to describe address/port scheme
- Added `local_addr` and `local_port` params to `make()` (defaults `0x00`)

### `blocks/gr-transport/grc/transport_transport_layer.block.yml`
- `make:` template updated to pass `${local_addr}` and `${local_port}`
- Added GRC parameters: `local_addr` (Local Address, int, default 0) and `local_port` (Local Port, int, default 0)

### `test_transport.grc`
- Initiator: `local_addr=1`, `local_port=1`
- Responder: `local_addr=2`, `local_port=1`
- Strobe message: `[2, 1, 1, 0, 0, 0, 0, 17]` + `"Hello from Strobe"`
  (dst_addr=2, dst_port=1, type=text, payload_len=17)

### `test_transport.py`
- `transport_transport_layer_0`: `transport.transport_layer(4, 500, "initiator", 200, 1, 1)`
- `transport_transport_layer_1`: `transport.transport_layer(4, 500, "responder", 200, 2, 1)`
- Strobe bytes updated to match above

---

## What Still Needs to Be Done (on a configured laptop)

### 1. Build and install

```bash
cd blocks/gr-transport/build
cmake ..
make -j$(nproc)
sudo make install
sudo ldconfig
```

With conda/venv:

```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$CONDA_PREFIX
make -j$(nproc) && make install
```

### 2. Verify compilation

Check that no compiler errors or warnings appear, particularly around the `static_cast<uint64_t>` casts used when building PMT values from `uint8_t` fields.

### 3. Run the test flowgraph

```bash
python3 test_transport.py
```

Expected log output:
```
transport_layer ready: role=initiator addr=1 port=1 m=4 ...
transport_layer ready: role=responder  addr=2 port=1 m=4 ...
app_in: dst=2:1 type=text frame=25B packets=1 session=...
IDLE->SYN_RCVD: SYN received from 1:1 — type=text total_pkts=1 session=...
... (data transfer) ...
RX_ACTIVE: reassembly complete — 25 bytes -> app_out
```

### 4. (Optional) Test address filtering

Set responder's `local_addr=3` (mismatch) and verify the SYN is silently dropped.
Expected DEBUG log on responder: `"IDLE: SYN not for us — dst=2:1 local=3:1 — dropping"`

---

## Gotchas

- Any existing flowgraph sending `[0xAB, 0xCD, ...]` will now be seen as dst_addr=171, dst_port=205.
  **Update all message sources** to the new header format.
- `local_addr=0` / `local_port=0` means wildcard — fully backward-compatible with old behaviour.
- `APP_ADDR_BCAST` and `APP_PORT_ANY` are both `0x00` by design.
