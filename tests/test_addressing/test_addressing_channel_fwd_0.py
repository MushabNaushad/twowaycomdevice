import numpy as np
from gnuradio import gr
import pmt, random

class blk(gr.basic_block):
    """Lossy PDU channel — drops each PDU with probability p_drop.
    p_drop is read live from the module-level variable so a QT Range
    slider can update it at runtime."""

    def __init__(self, p_drop=0.2):
        gr.basic_block.__init__(
            self,
            name='Lossy Channel',
            in_sig=None,
            out_sig=None
        )
        self.p_drop = p_drop
        self.message_port_register_in(pmt.intern('pdu_in'))
        self.message_port_register_out(pmt.intern('pdu_out'))
        self.set_msg_handler(pmt.intern('pdu_in'), self.handle_msg)

    def set_p_drop(self, p):
        self.p_drop = p

    def handle_msg(self, msg):
        if random.random() >= self.p_drop:
            self.message_port_pub(pmt.intern('pdu_out'), msg)
        # else: packet is silently dropped
