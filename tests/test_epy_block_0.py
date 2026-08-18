import numpy as np
from gnuradio import gr
import sys

class blk(gr.sync_block):
    """Prints incoming byte stream as ASCII text to the GRC console"""

    def __init__(self):
        gr.sync_block.__init__(
            self,
            name='Print Text to Console',
            in_sig=[np.byte],
            out_sig=None
        )

    def work(self, input_items, output_items):
        in0 = input_items[0]
        if len(in0) > 0:
            # Filter for printable ASCII characters and convert
            text = "".join([chr(c) for c in in0 if 32 <= c <= 126])
            if text:
                print(text, end='', flush=True)
        return len(in0)
