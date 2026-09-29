import numpy as np
from gnuradio import gr
import pmt

class SyncWordInserter(gr.basic_block):
    """
    Prepends raw (unencoded) Preamble and CCSDS Sync Word (0x1ACFFC1D)
    AFTER differential encoding.
    """
    def __init__(self, preamble_bytes=4):
        gr.basic_block.__init__(
            self,
            name="Sync Word Inserter (Post-Diff)",
            in_sig=[np.uint8],
            out_sig=[np.uint8]
        )
        self.preamble_bytes = max(1, int(preamble_bytes))
        self.sync_word = 0x1ACFFC1D
        
        # Prevent double packet_len tag propagation
        self.set_tag_propagation_policy(gr.TPP_DONT)

        # 1. Build unencoded preamble bits (0xAA -> 10101010)
        preamble_bits = []
        for _ in range(self.preamble_bytes):
            for i in range(7, -1, -1):
                preamble_bits.append((0xAA >> i) & 1)

        # 2. Build unencoded 32-bit sync word bits
        sync_bits = [(self.sync_word >> i) & 1 for i in range(31, -1, -1)]

        self.prefix_bits = np.array(preamble_bits + sync_bits, dtype=np.uint8)
        self.prefix_len = len(self.prefix_bits)

    def general_work(self, input_items, output_items):
        in0 = input_items[0]
        out = output_items[0]
        nin = len(in0)

        if nin == 0:
            return 0

        tags = self.get_tags_in_window(0, 0, nin)
        tag_offset = None
        tag_val = None
        for tag in tags:
            if pmt.to_python(tag.key) == "packet_len":
                tag_offset = tag.offset - self.nitems_read(0)
                tag_val = pmt.to_python(tag.value)
                break

        if tag_offset is not None and tag_offset == 0:
            total_out = self.prefix_len + nin
            if len(out) < total_out:
                return 0

            out[:self.prefix_len] = self.prefix_bits
            out[self.prefix_len:total_out] = in0

            new_tag_val = tag_val + self.prefix_len
            self.add_item_tag(0, self.nitems_written(0), pmt.intern("packet_len"), pmt.from_long(new_tag_val))

            self.consume(0, nin)
            return total_out
        else:
            n_copy = min(len(out), nin)
            out[:n_copy] = in0[:n_copy]
            self.consume(0, n_copy)
            return n_copy
