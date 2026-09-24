import numpy as np
from gnuradio import gr
import pmt
import struct

class AdaptiveHeaderGenerator(gr.basic_block):
    def __init__(self, default_mcs=0):
        gr.basic_block.__init__(
            self,
            name="Adaptive Header Generator",
            in_sig=[],
            out_sig=[]
        )
        self.current_mcs = 1 if default_mcs == 1 else 0

        self.message_port_register_in(pmt.intern("len_in"))
        self.message_port_register_in(pmt.intern("mcs_in"))
        self.message_port_register_out(pmt.intern("header_out"))
        self.message_port_register_out(pmt.intern("mcs_out"))

        self.set_msg_handler(pmt.intern("len_in"), self.handle_len)
        self.set_msg_handler(pmt.intern("mcs_in"), self.handle_mcs)

    def handle_mcs(self, msg):
        val = None
        if pmt.is_integer(msg):
            val = pmt.to_long(msg)
        elif pmt.is_pair(msg):
            cdr = pmt.cdr(msg)
            if pmt.is_integer(cdr):
                val = pmt.to_long(cdr)
        elif pmt.is_symbol(msg) or pmt.is_string(msg):
            s = pmt.symbol_to_string(msg) if pmt.is_symbol(msg) else pmt.symbol_name(msg)
            val = 1 if s.upper() == "QPSK" else 0

        if val is not None:
            self.current_mcs = 1 if val == 1 else 0

    def handle_len(self, msg):
        total_len = 0
        if pmt.is_integer(msg):
            total_len = pmt.to_long(msg)
        elif pmt.is_pair(msg):
            total_len = pmt.length(pmt.cdr(msg))
        else:
            return

        mcs_byte = struct.pack("!B", self.current_mcs)
        len_bytes = struct.pack("!H", total_len)
        chk = (self.current_mcs + (total_len >> 8) + (total_len & 0xFF)) & 0xFF
        chk_byte = struct.pack("!B", chk)

        # 4 bytes metadata = 32 bits
        metadata_frame = mcs_byte + len_bytes + chk_byte

        out_vec = pmt.init_u8vector(len(metadata_frame), list(metadata_frame))
        self.message_port_pub(pmt.intern("header_out"), pmt.cons(pmt.PMT_NIL, out_vec))
        self.message_port_pub(
            pmt.intern("mcs_out"),
            pmt.cons(pmt.PMT_NIL, pmt.from_long(self.current_mcs))
        )
