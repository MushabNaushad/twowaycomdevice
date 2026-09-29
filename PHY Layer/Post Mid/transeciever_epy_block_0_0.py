"""
Embedded Python Block: PacketFramerTX
"""
import numpy as np
from gnuradio import gr
import pmt
import zlib

class PacketFramerTX(gr.basic_block):
    def __init__(self, my_id="A", peer_id="B", preamble_len=32, postamble_len=16, repeat_count=5):
        gr.basic_block.__init__(
            self,
            name="Packet Framer TX",
            in_sig=None,
            out_sig=None
        )
        self.my_id = str(my_id)
        self.peer_id = str(peer_id)
        self.preamble_len = preamble_len
        self.postamble_len = postamble_len
        self.repeat_count = int(repeat_count)
        self.sync_word = bytes([0x1A, 0xCF, 0xFC, 0x1D])

        self.message_port_register_in(pmt.intern("msg_in"))
        self.set_msg_handler(pmt.intern("msg_in"), self.handle_msg)
        self.message_port_register_out(pmt.intern("pdu_out"))

    def handle_msg(self, msg):
        py_val = pmt.to_python(msg)
        if isinstance(py_val, tuple):
            text = bytes(py_val[1]).decode('utf-8', errors='replace')
        else:
            text = str(py_val)

        if not text:
            return

        # Prepend addresses if user typed raw text without headers
        if not (">" in text and ":" in text):
            text = f"{self.my_id}>{self.peer_id}:{text}"

        payload = text.encode('utf-8')
        is_ack = "ACK_" in text
        repeats = 1 if is_ack else self.repeat_count

        # Framing: [Preamble] + [Sync Word] + [Length] + [Payload] + [CRC32] + [Postamble]
        frame = (
            bytes([0xAA] * self.preamble_len) +
            self.sync_word +
            len(payload).to_bytes(2, 'big') +
            payload +
            zlib.crc32(payload).to_bytes(4, 'big') +
            bytes([0xAA] * self.postamble_len)
        )

        vec = pmt.init_u8vector(len(frame), list(frame))
        pdu = pmt.cons(pmt.PMT_NIL, vec)

        for _ in range(repeats):
            self.message_port_pub(pmt.intern("pdu_out"), pdu)

        if is_ack:
            print(f"[TX] Sent ACK back to {self.peer_id}", flush=True)
        else:
            print(f"[TX] Broadcast message to {self.peer_id} ({repeats}x): {text.split(':', 1)[1]}", flush=True)