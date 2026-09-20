import numpy as np
from gnuradio import gr
import pmt

class HeaderRecoveryBlock(gr.sync_block):
    """
    Correlates for CCSDS 32-bit ASM (0x1ACFFC1D) on an unpacked bit stream.
    Decodes MCS and Payload Length, and outputs:
      - 'len_out'     : Payload byte length (connects to Unpacked Payload Decoder)
      - 'mcs_out'     : 0 for BPSK, 1 for QPSK (connects to Selector o_index)
      - 'header_data' : Dict with payload_symbols (connects to Header/Payload Demux)
    """
    CCSDS_ASM = 0x1ACFFC1D

    def __init__(self):
        gr.sync_block.__init__(
            self,
            name="Header Recovery & MCS Decoder",
            in_sig=[np.uint8],
            out_sig=[]
        )
        # Message output ports
        self.message_port_register_out(pmt.intern("len_out"))
        self.message_port_register_out(pmt.intern("mcs_out"))
        self.message_port_register_out(pmt.intern("header_data"))

        self.shift_reg = 0
        self.state = "SEARCH_SYNC"
        self.header_bits = []
        self.header_len_bits = 8 + 16  # 1 byte MCS (8 bits) + 2 bytes Length (16 bits)

    def work(self, input_items, output_items):
        in_bits = input_items[0]

        for b in in_bits:
            bit = int(b) & 0x01

            if self.state == "SEARCH_SYNC":
                self.shift_reg = ((self.shift_reg << 1) & 0xFFFFFFFF) | bit
                if self.shift_reg == self.CCSDS_ASM:
                    self.state = "READ_HEADER"
                    self.header_bits = []

            elif self.state == "READ_HEADER":
                self.header_bits.append(bit)
                if len(self.header_bits) == self.header_len_bits:
                    # 1. Convert bit list to bytes
                    hdr_bytes = bytearray()
                    for i in range(0, self.header_len_bits, 8):
                        byte_val = 0
                        for j in range(8):
                            byte_val = (byte_val << 1) | self.header_bits[i + j]
                        hdr_bytes.append(byte_val)

                    # 2. Extract fields
                    mcs_id = hdr_bytes[0]
                    payload_len = (hdr_bytes[1] << 8) | hdr_bytes[2]
                    selected_mcs = 1 if mcs_id == 1 else 0

                    # 3. Calculate payload symbols for Header/Payload Demux
                    # (BPSK = 8 syms/byte; QPSK = 4 syms/byte)
                    syms = (payload_len * 8) if (selected_mcs == 0) else (payload_len * 4)
                    demux_info = pmt.make_dict()
                    demux_info = pmt.dict_add(demux_info, pmt.intern("payload_symbols"), pmt.from_long(syms))

                    # ---------------- Publish Outputs ----------------
                    # 1. Total payload byte length to Decoder Sink
                    self.message_port_pub(pmt.intern("len_out"), pmt.from_long(payload_len))

                    # 2. Modulation index (0 or 1) to Selector
                    self.message_port_pub(pmt.intern("mcs_out"), pmt.from_long(selected_mcs))

                    # 3. Symbol count dict to Header/Payload Demux
                    self.message_port_pub(pmt.intern("header_data"), demux_info)

                    # Reset state for next frame
                    self.shift_reg = 0
                    self.state = "SEARCH_SYNC"

        return len(in_bits)
