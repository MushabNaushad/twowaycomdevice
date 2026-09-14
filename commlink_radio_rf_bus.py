import pmt, random
from gnuradio import gr

class multi_node_rf_bus(gr.basic_block):
    def __init__(self, drop_prob=0.0):
        gr.basic_block.__init__(self, name="Shared RF Broadcast Bus", in_sig=[], out_sig=[])
        self.drop_prob = drop_prob
        for i in range(1, 6):
            self.message_port_register_in(pmt.intern(f"pdu_in_{i}"))
            self.message_port_register_out(pmt.intern(f"pdu_out_{i}"))
        
        self.message_port_register_out(pmt.intern("mon_out"))

        self.set_msg_handler(pmt.intern("pdu_in_1"), self.handle_1)
        self.set_msg_handler(pmt.intern("pdu_in_2"), self.handle_2)
        self.set_msg_handler(pmt.intern("pdu_in_3"), self.handle_3)
        self.set_msg_handler(pmt.intern("pdu_in_4"), self.handle_4)
        self.set_msg_handler(pmt.intern("pdu_in_5"), self.handle_5)

    def set_drop_prob(self, p):
        self.drop_prob = p

    def _route(self, msg, src_id):
        if not pmt.is_pair(msg): return
        data = pmt.cdr(msg)
        if not pmt.is_u8vector(data): return
        raw = bytes(pmt.u8vector_elements(data))
        if len(raw) < 18: return

        types = {1:'SYN', 2:'SYN_ACK', 3:'DATA', 4:'ACK', 5:'FIN', 6:'FIN_ACK'}
        pkt_type = types.get(raw[0], f'0x{raw[0]:02X}')
        src_addr = raw[2]
        dst_addr = raw[4]
        seq = (raw[6] << 8) | raw[7]
        tot = (raw[8] << 8) | raw[9]
        sid = int.from_bytes(raw[10:18], 'big')

        if random.random() < self.drop_prob:
            print(f"  [RF AIR DROP] Node {src_id}->{dst_addr} Type={pkt_type} Seq={seq} (DROPPED)", flush=True)
            return

        print(f"  [RF AIR BUS] Node {src_id}->Node {dst_addr} Type={pkt_type:<7} | Seq={seq}/{tot} (Length={len(raw)}B)", flush=True)
        air_pdu = pmt.cons(pmt.make_dict(), data)

        for dst_id in range(1, 6):
            if dst_id != src_id:
                self.message_port_pub(pmt.intern(f"pdu_out_{dst_id}"), air_pdu)

        self.message_port_pub(pmt.intern("mon_out"), air_pdu)

    def handle_1(self, msg): self._route(msg, 1)
    def handle_2(self, msg): self._route(msg, 2)
    def handle_3(self, msg): self._route(msg, 3)
    def handle_4(self, msg): self._route(msg, 4)
    def handle_5(self, msg): self._route(msg, 5)
