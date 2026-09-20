import numpy as np
from gnuradio import gr
import pmt
import struct

class AdaptiveHeaderGenerator(gr.basic_block):
    """
    Constructs the BPSK Header frame and emits the current MCS 
    to switch the transmitter modulation selector.
    """
    def __init__(self, preamble_len=8, default_mcs=0):
        gr.basic_block.__init__(
            self,
            name="Adaptive Header Generator",
            in_sig=[],
            out_sig=[]
        )
        self.preamble_len = max(1, int(preamble_len))
        self.current_mcs = 1 if default_mcs == 1 else 0

        self.sync_word = 0x1ACFFC1D
        self.postamble = bytes([0x55, 0x55])

        # Message Ports
        self.message_port_register_in(pmt.intern("len_in"))
        self.message_port_register_in(pmt.intern("mcs_in"))
        self.message_port_register_out(pmt.intern("header_out"))
        self.message_port_register_out(pmt.intern("mcs_out"))  # <--- Connects to TX Selector o_index

        self.set_msg_handler(pmt.intern("len_in"), self.handle_len)
        self.set_msg_handler(pmt.intern("mcs_in"), self.handle_mcs)

    def handle_mcs(self, msg):
        val = None
        if pmt.is_integer(msg):
            val = pmt.to_long(msg)
        elif pmt.is_symbol(msg) or pmt.is_string(msg):
            s = pmt.symbol_to_string(msg) if pmt.is_symbol(msg) else pmt.symbol_name(msg)
            val = 1 if s.upper() == "QPSK" else 0
        elif pmt.is_pair(msg):
            cdr = pmt.cdr(msg)
            if pmt.is_integer(cdr):
                val = pmt.to_long(cdr)

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

        preamble = bytes([0xAA] * self.preamble_len)
        sync_bytes = struct.pack("!I", self.sync_word)
        mcs_byte = struct.pack("!B", self.current_mcs)
        len_bytes = struct.pack("!H", total_len)

        header = preamble + sync_bytes + mcs_byte + len_bytes + self.postamble

        # 1. Output the header PDU
        out_vec = pmt.init_u8vector(len(header), list(header))
        self.message_port_pub(pmt.intern("header_out"), pmt.cons(pmt.PMT_NIL, out_vec))

        # 2. Output MCS index to switch the payload selector
        self.message_port_pub(pmt.intern("mcs_out"), pmt.from_long(self.current_mcs))
