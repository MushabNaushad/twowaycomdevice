import pmt, ctypes, os
from gnuradio import gr

try:
    so = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'blocks', 'gr-transport', 'build', 'lib', 'libgnuradio-transport.so'))
    if os.path.exists(so):
        ctypes.CDLL(so, mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

class blk(gr.basic_block):
    """Generates a multi-chunk Image bitstream with the 8-byte application header."""
    def __init__(self, dst_addr=9, payload_len=1024):
        gr.basic_block.__init__(self, name='App Image Gen', in_sig=None, out_sig=None)
        self.dst_addr = dst_addr
        self.payload_len = payload_len
        self.seq_num = 0
        self.message_port_register_in(pmt.intern('trig'))
        self.message_port_register_out(pmt.intern('app_out'))
        self.set_msg_handler(pmt.intern('trig'), self.handle_trig)

    def handle_trig(self, msg):
        self.seq_num += 1
        img_data = bytes([(i + self.seq_num) % 256 for i in range(self.payload_len)])
        n = len(img_data)
        # 8-Byte Application Header: [dst_addr, port, type=0x02(image), rsv=0, len_u32]
        hdr = bytes([self.dst_addr, 0x00, 0x02, 0x00, (n >> 24) & 0xFF, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
        full_frame = list(hdr + img_data)
        pdu = pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(full_frame), full_frame))
        print(f"\n[APP TX] Injecting Image Stream #{self.seq_num} ({len(full_frame)}B) to Node {self.dst_addr}", flush=True)
        self.message_port_pub(pmt.intern('app_out'), pdu)
