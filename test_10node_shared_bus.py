import pmt, random
from gnuradio import gr

class blk(gr.basic_block):
    """Shared broadcast bus with configurable loss.
    Every PDU received  on pdu_in is forwarded to pdu_out with probability
    (1 - p_drop). All  10 node pdu_out ports feed into pdu_in; the single
    pdu_out is connected  to all 20 node pdu_in ports."""

    def __init__(self, p_drop=0.1):
        gr.basic_block.__init__(
            self,
            name='Shared  Bus',
            in_sig=None,
            out_sig=None
        )
        self.p_drop = p_drop
        self.message_port_register_in(pmt.intern('pdu_in'))
        self.message_port_register_out(pmt.intern('pdu_out'))
        self.set_msg_handler(pmt.intern('pdu_in'),  self.handle_msg)

    def handle_msg(self, msg):
        if random.random()  >= self.p_drop:
            self.message_port_pub(pmt.intern('pdu_out'),  msg)
