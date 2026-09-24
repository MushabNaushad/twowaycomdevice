import numpy as np
from gnuradio import gr
import pmt

class HeaderRecoveryBlock(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name="Header Recovery & MCS Decoder",
            in_sig=[np.uint8],
            out_sig=[]
        )
        self.message_port_register_out(pmt.intern("len_out"))
        self.message_port_register_out(pmt.intern("mcs_out"))
        self.message_port_register_out(pmt.intern("header_data"))
        self.bit_buf = []

    def work(self, input_items, output_items):
        in_bits = input_items[0]
        for b in in_bits:
            self.bit_buf.append(int(b) & 1)

            # 33 bits: 1 trailing sync bit + 32 metadata bits
            if len(self.bit_buf) == 33:
                # Discard index 0 (the boundary sync bit)
                meta_bits = self.bit_buf[1:]
                
                raw_bytes = bytearray()
                for i in range(0, 32, 8):
                    byte_val = 0
                    for j in range(8):
                        byte_val = (byte_val << 1) | meta_bits[i + j]
                    raw_bytes.append(byte_val)

                b0, b1, b2, b3 = raw_bytes[0], raw_bytes[1], raw_bytes[2], raw_bytes[3]
                valid = False

                # Case 1: Normal phase
                if ((b0 + b1 + b2) & 0xFF) == b3:
                    valid = True
                # Case 2: Inverted 180 deg phase
                elif (((~b0 & 0xFF) + (~b1 & 0xFF) + (~b2 & 0xFF)) & 0xFF) == (~b3 & 0xFF):
                    b0, b1, b2 = (~b0) & 0xFF, (~b1) & 0xFF, (~b2) & 0xFF
                    valid = True

                if valid:
                    selected_mcs = 1 if b0 == 1 else 0
                    payload_len = (b1 << 8) | b2
                    syms = (payload_len * 8) if selected_mcs == 0 else (payload_len * 4)

                    print(f"[RX] Header Valid! MCS={selected_mcs} ({'QPSK' if selected_mcs==1 else 'BPSK'}), Payload={payload_len} bytes ({syms} syms)", flush=True)

                    demux_info = pmt.make_dict()
                    demux_info = pmt.dict_add(demux_info, pmt.intern("payload_symbols"), pmt.from_long(syms))

                    self.message_port_pub(pmt.intern("header_data"), demux_info)
                    self.message_port_pub(pmt.intern("len_out"), pmt.from_long(payload_len))
                    self.message_port_pub(
                        pmt.intern("mcs_out"),
                        pmt.cons(pmt.PMT_NIL, pmt.from_long(selected_mcs))
                    )
                else:
                    print(f"[RX] Header Checksum Failed (Raw: {list(raw_bytes)})", flush=True)

                self.bit_buf.clear()

        return len(in_bits)
