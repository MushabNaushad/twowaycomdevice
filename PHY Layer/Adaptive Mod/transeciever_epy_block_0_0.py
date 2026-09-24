import numpy as np
from gnuradio import gr
import pmt
import struct
import zlib

class AdaptivePayloadGenerator(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(
            self,
            name="Adaptive Payload Generator",
            in_sig=[],
            out_sig=[]
        )
        self.message_port_register_in(pmt.intern("in"))
        self.message_port_register_out(pmt.intern("payload_out"))
        self.message_port_register_out(pmt.intern("len_out"))
        self.set_msg_handler(pmt.intern("in"), self.handle_msg)

    def handle_msg(self, msg):
        raw_bytes = b""
        if pmt.is_symbol(msg):
            raw_bytes = pmt.symbol_to_string(msg).encode('utf-8')
        elif pmt.is_string(msg):
            raw_bytes = pmt.to_python(msg).encode('utf-8')
        elif pmt.is_pair(msg):
            cdr = pmt.cdr(msg)
            if pmt.is_u8vector(cdr):
                raw_bytes = bytes(pmt.u8vector_elements(cdr))
            elif pmt.is_string(cdr) or pmt.is_symbol(cdr):
                raw_bytes = pmt.to_python(cdr).encode('utf-8')
        else:
            return

        if len(raw_bytes) == 0:
            return

        # Append CRC32 (4 bytes, big-endian)
        crc = zlib.crc32(raw_bytes) & 0xFFFFFFFF
        framed_payload = raw_bytes + struct.pack("!I", crc)
        total_len = len(framed_payload)

        print(f"\n[TX] Transmitting: '{raw_bytes.decode('utf-8', errors='replace')}' ({total_len} bytes framed)", flush=True)

        out_vec = pmt.init_u8vector(total_len, list(framed_payload))
        self.message_port_pub(pmt.intern("payload_out"), pmt.cons(pmt.PMT_NIL, out_vec))
        self.message_port_pub(pmt.intern("len_out"), pmt.from_long(total_len))
