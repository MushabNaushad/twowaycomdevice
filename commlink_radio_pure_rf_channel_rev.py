import pmt, random
from gnuradio import gr

class blk(gr.basic_block):
    """Pure-RF Physical Channel: Strips PMT metadata dict to test 100% in-band transport."""
    def __init__(self, p_drop=0.0):
        gr.basic_block.__init__(self, name='Pure RF Channel (2->1)', in_sig=None, out_sig=None)
        self.p_drop = p_drop
        self.message_port_register_in(pmt.intern('pdu_in'))
        self.message_port_register_out(pmt.intern('pdu_out'))
        self.set_msg_handler(pmt.intern('pdu_in'), self.handle_msg)

    def set_p_drop(self, p):
        self.p_drop = p

    def handle_msg(self, msg):
        if not pmt.is_pair(msg):
            return
        data = pmt.cdr(msg)
        if not pmt.is_u8vector(data):
            return
        raw = bytes(pmt.u8vector_elements(data))
        if len(raw) < 18:
            return
        types = {1:'SYN', 2:'SYN_ACK', 3:'DATA', 4:'ACK', 5:'FIN', 6:'FIN_ACK'}
        pkt_type = types.get(raw[0], f'0x{raw[0]:02X}')
        seq = (raw[6] << 8) | raw[7]
        
        if random.random() < self.p_drop:
            print(f"  [RF DROP 2->1] Type={pkt_type:<7} Length={len(raw):>4}B | Seq={seq}", flush=True)
            return
        
        air_pdu = pmt.cons(pmt.make_dict(), data)
        self.message_port_pub(pmt.intern('pdu_out'), air_pdu)
