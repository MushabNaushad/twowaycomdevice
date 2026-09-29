# Transport Layer — Decomposed Architecture with Built-in Blocks & Env Vars

> **Revision:** Three focused Python Embedded Blocks + built-in `pdu` blocks for everything that can be offloaded. All tunable parameters driven by environment variables via GRC `variable` blocks.

---

## Part 1 — What CAN vs. CANNOT be handed off to built-in blocks

### What CAN be fully offloaded

| Built-in Block | Replaces what was in the Python FSM block |
|---|---|
| `pdu.pdu_filter` | The `dst_addr` / `dst_port` address filter inside `_fsm_idle()` — drop frames not addressed to this node |
| `pdu.pdu_set` | Stamping a fixed `src_addr` / `src_port` key onto every outgoing PDU's metadata dict |
| `pdu.pdu_remove` | Stripping a metadata key (e.g. removing an internal routing tag before it reaches the PHY) |
| `pdu.pdu_lambda` | Stateless transformations on metadata fields (e.g. mapping a numeric `pkt_type` byte to a symbol string) |

### What CANNOT be offloaded — must stay in Python

| Concern | Why no built-in equivalent exists |
|---|---|
| Binary header serialization / deserialization | No GR block reads/writes custom fixed-layout binary headers inside a PDU payload |
| SR-ARQ FSM (SYN/SYN_ACK/DATA/ACK/FIN/FIN_ACK) | Requires persistent state across messages — no stateful ARQ block exists in stock GR |
| Sliding window management | Same — index tracking, slot bookkeeping, window advance logic all require mutable state |
| Per-slot retransmission timers | `threading.Timer` or Boost.Asio; no built-in block manages per-slot RTO |
| Session ID generation + session guard | No built-in block generates/validates a 64-bit random session nonce |
| Packet reassembly | No built-in block accumulates chunks and reconstructs an ordered byte stream |
| Packetization (MTU chunking) | No built-in block fragments an arbitrary byte blob at a configurable MTU boundary |

---

## Part 2 — The three-block decomposition

Instead of one giant monolithic block, split responsibility across **three Python Embedded Blocks** + two built-in blocks:

```
PHY/DLC out
    |
    v
[Block 1: RX Header Parser]   (Python Embedded - stateless)
    |  strips binary header, promotes fields to PMT metadata dict
    v
[pdu.pdu_filter]              (built-in "PDU Filter")
    |  key="dst_addr", value=pmt.from_uint64(local_addr)
    v
[Block 2: SR-ARQ FSM Core]    (Python Embedded - stateful)  <-- app_in
    |  pdu_out (metadata-only, no binary header yet)          --> app_out
    v
[Block 3: TX Header Serializer] (Python Embedded - stateless)
    |  reads metadata dict, prepends 18-byte binary header
    v
PHY/DLC in
```

> [!NOTE]
> The FSM core now speaks **pure PMT metadata** on its `pdu_out` — it never touches binary bytes for outgoing frames. Block 3 owns all header serialization. This makes each block unit-testable independently.

---

## Part 3 — Environment variable configuration

### Step 3a — Add a top-level import block

In GRC, add an **`Import`** block (search: "Import") with:
```python
import os
```

### Step 3b — Add GRC `variable` blocks for every parameter

Add one `Variable` block per parameter below. The expression column is the GRC "Value" field:

| Variable name (GRC ID) | GRC Value expression | Env var | Default |
|---|---|---|---|
| `tl_m` | `int(os.environ.get('TL_M', '4'))` | `TL_M` | `4` |
| `tl_rto_ms` | `int(os.environ.get('TL_RTO_MS', '500'))` | `TL_RTO_MS` | `500` |
| `tl_mtu` | `int(os.environ.get('TL_MTU', '200'))` | `TL_MTU` | `200` |
| `tl_local_addr` | `int(os.environ.get('TL_LOCAL_ADDR', '0'))` | `TL_LOCAL_ADDR` | `0` |
| `tl_local_port` | `int(os.environ.get('TL_LOCAL_PORT', '0'))` | `TL_LOCAL_PORT` | `0` |
| `tl_role` | `os.environ.get('TL_ROLE', 'initiator')` | `TL_ROLE` | `'initiator'` |
| `tl_max_retries` | `int(os.environ.get('TL_MAX_RETRIES', '10'))` | `TL_MAX_RETRIES` | `10` |

To run with custom settings:
```bash
TL_LOCAL_ADDR=5 TL_ROLE=initiator TL_MTU=256 python3 my_flowgraph.py
TL_LOCAL_ADDR=9 TL_ROLE=responder python3 my_flowgraph.py
```

---

## Part 4 — Block 1: RX Header Parser

**Purpose:** Stateless. Reads 18 bytes from the front of every incoming PDU payload and exposes each field as a PMT metadata key. The rest of the flowgraph (including `pdu_filter`) can now act on named metadata.

Add a Python Embedded Block. Replace its code with:

```python
"""
Block 1: RX Header Parser
Strips the 18-byte binary transport header from incoming PDU payloads and
promotes every field into the PMT metadata dictionary.

Ports:  In: pdus  Out: pdus
"""
import struct, pmt
from gnuradio import gr

HDR_FMT  = ">BBBBBBHHQ"
HDR_SIZE = struct.calcsize(HDR_FMT)  # 18

PKT_STR   = {0x01:"SYN",0x02:"SYN_ACK",0x03:"DATA",
             0x04:"ACK",0x05:"FIN",0x06:"FIN_ACK"}
MEDIA_STR = {0x01:"text",0x02:"image",0x03:"audio"}

class blk(gr.sync_block):
    """RX Header Parser - stateless 18-byte binary header deserializer."""

    def __init__(self):
        gr.sync_block.__init__(self, name="RX Header Parser",
                               in_sig=None, out_sig=None)
        self.message_port_register_in(pmt.intern("pdus"))
        self.message_port_register_out(pmt.intern("pdus"))
        self.set_msg_handler(pmt.intern("pdus"), self.handle)

    def handle(self, msg):
        if not pmt.is_pair(msg): return
        in_meta = pmt.car(msg)
        in_data = pmt.cdr(msg)
        if not pmt.is_u8vector(in_data): return
        raw = bytes(pmt.u8vector_elements(in_data))
        if len(raw) < HDR_SIZE: return

        fields   = struct.unpack_from(HDR_FMT, raw)
        pkt_type = fields[0]
        if not (0x01 <= pkt_type <= 0x06): return  # not a transport frame

        meta = in_meta if pmt.is_dict(in_meta) else pmt.make_dict()
        for k, v in [
            ("pkt_type",    pmt.intern(PKT_STR.get(pkt_type, "UNKNOWN"))),
            ("pkt_type_raw",pmt.from_uint64(pkt_type)),
            ("media_type",  pmt.intern(MEDIA_STR.get(fields[1], "unknown"))),
            ("src_addr",    pmt.from_uint64(fields[2])),
            ("src_port",    pmt.from_uint64(fields[3])),
            ("dst_addr",    pmt.from_uint64(fields[4])),
            ("dst_port",    pmt.from_uint64(fields[5])),
            ("seq_no",      pmt.from_uint64(fields[6])),
            ("total_pkts",  pmt.from_uint64(fields[7])),
            ("session_id",  pmt.from_uint64(fields[8])),
        ]:
            meta = pmt.dict_add(meta, pmt.intern(k), v)

        payload  = raw[HDR_SIZE:]
        out_data = pmt.init_u8vector(len(payload), list(payload))
        self.message_port_pub(pmt.intern("pdus"), pmt.cons(meta, out_data))

    def work(self, input_items, output_items):
        return 0
```

---

## Part 5 — Built-in `pdu.pdu_filter` for address filtering

After Block 1's output, wire in a **`PDU Filter`** (search: "PDU Filter") built-in block:

| Property | Value |
|---|---|
| **Key** | `dst_addr` |
| **Value** | `pmt.from_uint64(tl_local_addr)` *(references the GRC variable)* |
| **Invert** | `False` |

This drops any PDU whose `dst_addr` field doesn't match `tl_local_addr` — **zero Python required**.

> [!TIP]
> To also accept broadcast frames (`dst_addr=0`), wire a **second** `pdu_filter` with `value=pmt.from_uint64(0)` in parallel — both outputs connect to Block 2's `pdu_in`. GNU Radio message ports accept multiple input connections and merge them automatically.

---

## Part 6 — Block 2: SR-ARQ FSM Core

**Purpose:** All stateful ARQ logic. Receives pre-parsed PDUs (metadata in `car`, payload bytes in `cdr`). Emits outgoing frames as metadata-only PDUs — Block 3 serializes those.

Add a Python Embedded Block. Replace its code with:

```python
"""
Block 2: SR-ARQ FSM Core
Stateful SR-ARQ engine. Input PDUs must already have header fields in PMT
metadata (i.e. pass through Block 1 first). Output PDUs carry metadata only
(no binary header) - Block 3 serializes them.

Ports:
  Inputs : pdu_in, app_in
  Outputs: pdu_out, app_out
"""
import os, struct, threading
import pmt
from gnuradio import gr

PKT_SYN=0x01; PKT_SYN_ACK=0x02; PKT_DATA=0x03
PKT_ACK=0x04; PKT_FIN=0x05;     PKT_FIN_ACK=0x06
MEDIA_CODE = {"text":0x01,"image":0x02,"audio":0x03}
MEDIA_STR  = {0x01:"text",0x02:"image",0x03:"audio"}
PKT_CODE   = {"SYN":PKT_SYN,"SYN_ACK":PKT_SYN_ACK,"DATA":PKT_DATA,
              "ACK":PKT_ACK,"FIN":PKT_FIN,"FIN_ACK":PKT_FIN_ACK}
PKT_STR    = {v:k for k,v in PKT_CODE.items()}
IDLE="IDLE"; SYN_SENT="SYN_SENT"; SYN_RCVD="SYN_RCVD"
TX_ACTIVE="TX_ACTIVE"; RX_ACTIVE="RX_ACTIVE"; FIN_SENT="FIN_SENT"


class blk(gr.sync_block):
    """
    SR-ARQ FSM Core

    All parameters read from environment variables by default.
    Pass GRC variable names (tl_m, tl_rto_ms, etc.) as block parameters
    to override the env-var defaults at flowgraph level.

    Env vars: TL_M, TL_RTO_MS, TL_ROLE, TL_MTU, TL_LOCAL_ADDR,
              TL_LOCAL_PORT, TL_MAX_RETRIES
    """

    def __init__(self,
                 m=int(os.environ.get('TL_M','4')),
                 rto_ms=int(os.environ.get('TL_RTO_MS','500')),
                 node_role=os.environ.get('TL_ROLE','initiator'),
                 mtu_bytes=int(os.environ.get('TL_MTU','200')),
                 local_addr=int(os.environ.get('TL_LOCAL_ADDR','0')),
                 local_port=int(os.environ.get('TL_LOCAL_PORT','0')),
                 max_retries=int(os.environ.get('TL_MAX_RETRIES','10'))):

        gr.sync_block.__init__(self, name="SR-ARQ FSM Core",
                               in_sig=None, out_sig=None)

        assert node_role in ("initiator","responder"), \
            "TL_ROLE must be 'initiator' or 'responder'"
        assert 1 <= m <= 8,   "TL_M must be 1..8"
        assert mtu_bytes > 0, "TL_MTU must be > 0"

        self.m            = m
        self.seq_space    = 1 << m
        self.win_size     = 1 << (m - 1)
        self.rto_s        = rto_ms / 1000.0
        self.role         = node_role
        self.mtu          = mtu_bytes
        self.local_addr   = local_addr & 0xFF
        self.local_port   = local_port & 0xFF
        self.max_retries  = max_retries

        self.message_port_register_in (pmt.intern("pdu_in"))
        self.message_port_register_in (pmt.intern("app_in"))
        self.message_port_register_out(pmt.intern("pdu_out"))
        self.message_port_register_out(pmt.intern("app_out"))
        self.set_msg_handler(pmt.intern("pdu_in"), self.handle_pdu_in)
        self.set_msg_handler(pmt.intern("app_in"), self.handle_app_in)

        self._lock   = threading.Lock()
        self._timers = [None] * self.seq_space
        self._reset_state()

    # ── State reset ─────────────────────────────────────────────────────
    def _reset_state(self):
        self._cancel_all_timers()
        self.state = IDLE; self.session_id = 0
        self.dst_addr = 0; self.dst_port = 0
        self.ctrl_retries = 0; self.media_code = 0x00
        self.all_tx_pkts  = []
        self.tx_buf   = [None]  * self.seq_space
        self.acked    = [False] * self.seq_space
        self.send_base = 0; self.next_seq_abs = 0; self.total_tx = 0
        self.rx_buf         = [None]  * self.seq_space
        self.received       = [False] * self.seq_space
        self.rcv_base = 0; self.total_rx = 0
        self.pkts_delivered = 0; self.reassembled = bytearray()

    # ── Timers ──────────────────────────────────────────────────────────
    def _start_timer(self, slot):
        self._cancel_timer(slot)
        t = threading.Timer(self.rto_s, self._on_timeout, args=[slot])
        t.daemon = True; self._timers[slot] = t; t.start()

    def _cancel_timer(self, slot):
        if self._timers[slot]:
            self._timers[slot].cancel(); self._timers[slot] = None

    def _cancel_all_timers(self):
        if not hasattr(self, "_timers"): return
        for i in range(len(self._timers)): self._cancel_timer(i)

    def _on_timeout(self, slot):
        ctrl = self.seq_space - 1
        with self._lock:
            if slot == ctrl:
                if self.state == SYN_SENT:
                    self.ctrl_retries += 1
                    if self.ctrl_retries > self.max_retries:
                        gr.log.error("FSM: SYN retry limit exceeded - aborting")
                        self._reset_state(); return
                    gr.log.warn(f"FSM: SYN RTO retry {self.ctrl_retries}/{self.max_retries}")
                    self._emit_ctrl(PKT_SYN, total_pkts=self.total_tx, media=self.media_code)
                    self._start_timer(ctrl)
                elif self.state == FIN_SENT:
                    self.ctrl_retries += 1
                    if self.ctrl_retries > self.max_retries:
                        gr.log.warn("FSM: FIN retry limit exceeded - closing anyway")
                        self._reset_state(); return
                    gr.log.warn(f"FSM: FIN RTO retry {self.ctrl_retries}/{self.max_retries}")
                    self._emit_ctrl(PKT_FIN)
                    self._start_timer(ctrl)
            else:
                if self.state == TX_ACTIVE and not self.acked[slot]:
                    gr.log.warn(f"FSM: DATA RTO slot={slot}")
                    self._emit_data(slot); self._start_timer(slot)

    # ── app_in handler ───────────────────────────────────────────────────
    def handle_app_in(self, msg):
        if not pmt.is_pair(msg): return
        d = pmt.cdr(msg)
        if not pmt.is_u8vector(d): return
        frame = bytes(pmt.u8vector_elements(d))
        if len(frame) < 8:
            gr.log.error("FSM app_in: frame too short"); return
        dst_addr, dst_port, type_byte, _ = struct.unpack_from(">BBBB", frame, 0)
        declared_len = struct.unpack_from(">I", frame, 4)[0]
        if len(frame) != 8 + declared_len:
            gr.log.error("FSM app_in: length mismatch"); return
        with self._lock:
            if self.state != IDLE:
                gr.log.warn("FSM app_in: session active - dropping"); return
            self.dst_addr = dst_addr & 0xFF; self.dst_port = dst_port & 0xFF
            self.media_code = type_byte & 0xFF
            self._packetize(frame)
            self.session_id   = int.from_bytes(os.urandom(8), "big")
            self.state        = SYN_SENT; self.ctrl_retries = 0
            self._emit_ctrl(PKT_SYN, total_pkts=self.total_tx, media=self.media_code)
            self._start_timer(self.seq_space - 1)

    # ── pdu_in handler ───────────────────────────────────────────────────
    def handle_pdu_in(self, msg):
        if not pmt.is_pair(msg): return
        meta = pmt.car(msg); data = pmt.cdr(msg)
        if not pmt.is_dict(meta): return
        if not pmt.dict_has_key(meta, pmt.intern("pkt_type")): return

        pkt_str  = pmt.symbol_to_string(
            pmt.dict_ref(meta, pmt.intern("pkt_type"), pmt.intern("")))
        pkt_code = PKT_CODE.get(pkt_str, 0)
        sid      = pmt.to_uint64(
            pmt.dict_ref(meta, pmt.intern("session_id"), pmt.from_uint64(0)))
        payload  = bytes(pmt.u8vector_elements(data)) if pmt.is_u8vector(data) else b""

        def gu(k, d=0):
            return pmt.to_uint64(pmt.dict_ref(meta, pmt.intern(k), pmt.from_uint64(d)))
        def gs(k, d=""):
            return pmt.symbol_to_string(pmt.dict_ref(meta, pmt.intern(k), pmt.intern(d)))

        with self._lock:
            if self.state != IDLE and pkt_code != PKT_SYN:
                if sid != self.session_id: return
            hdr = {"pkt_type":pkt_code, "media_type":MEDIA_CODE.get(gs("media_type"),0),
                   "src_addr":gu("src_addr"), "src_port":gu("src_port"),
                   "dst_addr":gu("dst_addr"), "dst_port":gu("dst_port"),
                   "seq_no":gu("seq_no"), "total_pkts":gu("total_pkts"),
                   "session_id":sid}
            dispatch = {IDLE:self._fsm_idle, SYN_SENT:self._fsm_syn_sent,
                        SYN_RCVD:self._fsm_syn_rcvd, TX_ACTIVE:self._fsm_tx_active,
                        RX_ACTIVE:self._fsm_rx_active, FIN_SENT:self._fsm_fin_sent}
            if self.state in dispatch:
                dispatch[self.state](hdr, payload)

    # ── FSM states ───────────────────────────────────────────────────────
    def _fsm_idle(self, hdr, payload):
        if hdr["pkt_type"] != PKT_SYN: return
        dst = hdr["dst_addr"]  # belt-and-suspenders after pdu_filter
        if self.local_addr != 0 and dst != 0 and dst != self.local_addr: return
        if self.local_port != 0 and hdr["dst_port"] != 0 and hdr["dst_port"] != self.local_port: return
        self.dst_addr=hdr["src_addr"]; self.dst_port=hdr["src_port"]
        self.session_id=hdr["session_id"]; self.total_rx=hdr["total_pkts"]
        self.media_code=hdr["media_type"]
        self.rcv_base=0; self.pkts_delivered=0; self.reassembled=bytearray()
        self.rx_buf=[None]*self.seq_space; self.received=[False]*self.seq_space
        self.state=SYN_RCVD; self._emit_ctrl(PKT_SYN_ACK)

    def _fsm_syn_sent(self, hdr, payload):
        if hdr["pkt_type"] != PKT_SYN_ACK: return
        self._cancel_timer(self.seq_space - 1)
        self.state=TX_ACTIVE; self.send_base=0; self.next_seq_abs=0
        for _ in range(min(self.win_size, self.total_tx)):
            slot=self.next_seq_abs % self.seq_space
            self.tx_buf[slot]=self.all_tx_pkts[self.next_seq_abs]; self.acked[slot]=False
            self._emit_data(slot); self._start_timer(slot); self.next_seq_abs+=1

    def _fsm_syn_rcvd(self, hdr, payload):
        if hdr["pkt_type"]==PKT_SYN: self._emit_ctrl(PKT_SYN_ACK); return
        if hdr["pkt_type"]==PKT_DATA: self.state=RX_ACTIVE; self._fsm_rx_active(hdr, payload)

    def _fsm_tx_active(self, hdr, payload):
        if hdr["pkt_type"]!=PKT_ACK: return
        seq=hdr["seq_no"]
        if self.acked[seq]: return
        self.acked[seq]=True; self._cancel_timer(seq); self._advance_window()

    def _fsm_rx_active(self, hdr, payload):
        if hdr["pkt_type"]!=PKT_DATA: return
        seq=hdr["seq_no"]
        in_win=any(seq==(self.rcv_base+i)%self.seq_space for i in range(self.win_size))
        self._emit_ctrl(PKT_ACK, seq_no=seq)
        if not in_win: return
        if not self.received[seq]: self.received[seq]=True; self.rx_buf[seq]=payload
        self._try_deliver()

    def _fsm_fin_sent(self, hdr, payload):
        if hdr["pkt_type"]!=PKT_FIN_ACK: return
        self._cancel_timer(self.seq_space-1); self._reset_state()

    # ── Window management ─────────────────────────────────────────────────
    def _advance_window(self):
        while self.send_base < self.total_tx and self.acked[self.send_base % self.seq_space]:
            slot=self.send_base%self.seq_space
            self.acked[slot]=False; self.tx_buf[slot]=None; self.send_base+=1
            if self.next_seq_abs < self.total_tx:
                ns=self.next_seq_abs%self.seq_space
                self.tx_buf[ns]=self.all_tx_pkts[self.next_seq_abs]; self.acked[ns]=False
                self._emit_data(ns); self._start_timer(ns); self.next_seq_abs+=1
        if self.send_base >= self.total_tx:
            self.state=FIN_SENT; self.ctrl_retries=0
            self._emit_ctrl(PKT_FIN); self._start_timer(self.seq_space-1)

    def _try_deliver(self):
        while self.pkts_delivered < self.total_rx and self.received[self.rcv_base]:
            self.reassembled.extend(self.rx_buf[self.rcv_base])
            self.received[self.rcv_base]=False; self.rx_buf[self.rcv_base]=None
            self.rcv_base=(self.rcv_base+1)%self.seq_space; self.pkts_delivered+=1
        if self.pkts_delivered == self.total_rx:
            out=bytes(self.reassembled)
            m=pmt.make_dict()
            for k,v in [("payload_type",pmt.intern(MEDIA_STR.get(self.media_code,"unknown"))),
                        ("session_id",pmt.from_uint64(self.session_id)),
                        ("src_addr",pmt.from_uint64(self.dst_addr)),
                        ("src_port",pmt.from_uint64(self.dst_port)),
                        ("dst_addr",pmt.from_uint64(self.local_addr)),
                        ("dst_port",pmt.from_uint64(self.local_port))]:
                m=pmt.dict_add(m, pmt.intern(k), v)
            self.message_port_pub(pmt.intern("app_out"),
                pmt.cons(m, pmt.init_u8vector(len(out), list(out))))
            self._emit_ctrl(PKT_FIN_ACK); self._reset_state()

    # ── Packetization ─────────────────────────────────────────────────────
    def _packetize(self, raw):
        self.all_tx_pkts=[raw[i:i+self.mtu] for i in range(0,len(raw),self.mtu)]
        self.tx_buf=[None]*self.seq_space; self.acked=[False]*self.seq_space
        self.total_tx=len(self.all_tx_pkts); self.send_base=0; self.next_seq_abs=0

    # ── Emit helpers (metadata-only PDUs — Block 3 adds binary header) ──
    def _make_meta(self, pkt_code, seq_no=0, total_pkts=0, media=0):
        m=pmt.make_dict()
        for k,v in [("pkt_type",pmt.intern(PKT_STR.get(pkt_code,"UNKNOWN"))),
                    ("pkt_type_raw",pmt.from_uint64(pkt_code)),
                    ("seq_no",pmt.from_uint64(seq_no)),
                    ("total_pkts",pmt.from_uint64(total_pkts)),
                    ("media_type",pmt.intern(MEDIA_STR.get(media,"unknown"))),
                    ("media_raw",pmt.from_uint64(media)),
                    ("src_addr",pmt.from_uint64(self.local_addr)),
                    ("src_port",pmt.from_uint64(self.local_port)),
                    ("dst_addr",pmt.from_uint64(self.dst_addr)),
                    ("dst_port",pmt.from_uint64(self.dst_port)),
                    ("session_id",pmt.from_uint64(self.session_id))]:
            m=pmt.dict_add(m, pmt.intern(k), v)
        return m

    def _emit_ctrl(self, pkt_code, seq_no=0, total_pkts=0, media=None):
        if media is None: media=self.media_code
        meta=self._make_meta(pkt_code, seq_no=seq_no, total_pkts=total_pkts, media=media)
        self.message_port_pub(pmt.intern("pdu_out"),
            pmt.cons(meta, pmt.init_u8vector(0, [])))

    def _emit_data(self, slot):
        chunk=self.tx_buf[slot]
        if chunk is None: return
        meta=self._make_meta(PKT_DATA, seq_no=slot, total_pkts=self.total_tx, media=self.media_code)
        self.message_port_pub(pmt.intern("pdu_out"),
            pmt.cons(meta, pmt.init_u8vector(len(chunk), list(chunk))))

    def work(self, input_items, output_items):
        return 0
```

---

## Part 7 — Block 3: TX Header Serializer

**Purpose:** Stateless. Reads the PMT metadata dict produced by Block 2 and prepends the 18-byte binary transport header.

Add a Python Embedded Block. Replace its code with:

```python
"""
Block 3: TX Header Serializer
Reads header fields from PMT metadata dict and prepends the 18-byte binary
transport header. Output is a raw-bytes PDU ready for the DLC/PHY chain.

Ports:  In: pdus  Out: pdus
"""
import struct, pmt
from gnuradio import gr

HDR_FMT    = ">BBBBBBHHQ"
PKT_CODE   = {"SYN":0x01,"SYN_ACK":0x02,"DATA":0x03,
              "ACK":0x04,"FIN":0x05,"FIN_ACK":0x06}
MEDIA_CODE = {"text":0x01,"image":0x02,"audio":0x03}


class blk(gr.sync_block):
    """TX Header Serializer - stateless 18-byte binary header serializer."""

    def __init__(self):
        gr.sync_block.__init__(self, name="TX Header Serializer",
                               in_sig=None, out_sig=None)
        self.message_port_register_in(pmt.intern("pdus"))
        self.message_port_register_out(pmt.intern("pdus"))
        self.set_msg_handler(pmt.intern("pdus"), self.handle)

    def handle(self, msg):
        if not pmt.is_pair(msg): return
        meta = pmt.car(msg); data = pmt.cdr(msg)
        if not pmt.is_dict(meta): return

        def gu(k, d=0):
            return pmt.to_uint64(pmt.dict_ref(meta, pmt.intern(k), pmt.from_uint64(d)))
        def gs(k, d=""):
            return pmt.symbol_to_string(pmt.dict_ref(meta, pmt.intern(k), pmt.intern(d)))

        hdr = struct.pack(HDR_FMT,
            PKT_CODE.get(gs("pkt_type"), 0),
            MEDIA_CODE.get(gs("media_type"), 0),
            gu("src_addr") & 0xFF, gu("src_port") & 0xFF,
            gu("dst_addr") & 0xFF, gu("dst_port") & 0xFF,
            gu("seq_no")   & 0xFFFF,
            gu("total_pkts") & 0xFFFF,
            gu("session_id"))

        payload  = bytes(pmt.u8vector_elements(data)) if pmt.is_u8vector(data) else b""
        frame    = hdr + payload
        out_data = pmt.init_u8vector(len(frame), list(frame))
        # Retain metadata so downstream blocks (message_debug, etc.) can inspect it
        self.message_port_pub(pmt.intern("pdus"), pmt.cons(meta, out_data))

    def work(self, input_items, output_items):
        return 0
```

---

## Part 8 — Full wiring in GRC

```
PHY/DLC out
    |
    v
[Block 1: RX Header Parser]       (Python Embedded, no parameters)
    | port: pdus
    v
[pdu.pdu_filter]                  (built-in "PDU Filter")
    | key="dst_addr", value=pmt.from_uint64(tl_local_addr), invert=False
    v                             also wire a second pdu_filter (value=pmt.from_uint64(0))
    v                             in parallel for broadcast acceptance
[Block 2: SR-ARQ FSM Core]        (Python Embedded)
    | params: m=tl_m, rto_ms=tl_rto_ms, node_role=tl_role, mtu_bytes=tl_mtu,
    |         local_addr=tl_local_addr, local_port=tl_local_port, max_retries=tl_max_retries
    | port: app_in <--- [application source]
    | port: app_out ---> [application sink]
    | port: pdu_out
    v
[Block 3: TX Header Serializer]   (Python Embedded, no parameters)
    | port: pdus
    v
PHY/DLC in
```

---

## Part 9 — Optional additional built-in blocks

| Block | Where | Purpose |
|---|---|---|
| `pdu.pdu_set` | After Block 3 | Stamp extra metadata (e.g. `"radio_id"`) without touching Python code |
| `pdu.pdu_remove` | After Block 1 | Strip `"pkt_type_raw"` / `"media_raw"` before passing to consumers |
| `pdu.pdu_lambda` | After Block 1 | Apply stateless transforms to any metadata field |
| `blocks.message_debug` | After Block 1 | Inspect parsed metadata before address filter drops anything |
| `blocks.message_debug` | After Block 2 `pdu_out` | See FSM decisions before serialization |
| `blocks.message_debug` | After Block 3 | Confirm final binary frame hex matches PACKET_STRUCTURE.md |

---

## Part 10 — Quick start with env vars

```bash
# Node A - Initiator, address 5, 256-byte MTU
TL_LOCAL_ADDR=5 TL_ROLE=initiator TL_MTU=256 TL_RTO_MS=750 python3 my_flowgraph.py

# Node B - Responder, address 9
TL_LOCAL_ADDR=9 TL_ROLE=responder python3 my_flowgraph.py

# Tight timing test
TL_RTO_MS=100 TL_MAX_RETRIES=20 TL_M=3 python3 my_flowgraph.py
```

> [!IMPORTANT]
> GRC evaluates `variable` block expressions at **flowgraph generation time** (F5 / run). Env vars must be set **before** launching the process.
