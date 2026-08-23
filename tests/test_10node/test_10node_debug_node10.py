import pmt
from gnuradio import gr

class blk(gr.basic_block):
    """Custom labelled message sink"""

    def __init__(self, label="[MSG]"):
        gr.basic_block.__init__(
            self,
            name="Labelled Debug",
            in_sig=None,
            out_sig=None
        )
        self.label = label
        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self.handle_msg)

    def handle_msg(self, msg):
        print(f"\n{'='*40}")
        print(f"  {self.label}")
        print(f"{'='*40}")
        if pmt.is_pair(msg):
            meta = pmt.car(msg)
            data = pmt.cdr(msg)
            print(f"  Meta : {pmt.to_python(meta)}")
            if pmt.is_u8vector(data):
                raw = bytes(pmt.u8vector_elements(data))
                print(f"  Bytes: {raw.hex(' ')}")
                try:
                    print(f"  ASCII: {raw[8:].decode('ascii', errors='replace')}")
                except:
                    pass
        else:
            print(f"  {pmt.to_python(msg)}")
