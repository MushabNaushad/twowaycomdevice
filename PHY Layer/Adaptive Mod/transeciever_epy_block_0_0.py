import numpy as np
from gnuradio import gr
import pmt
import struct
import zlib

class AdaptivePayloadGenerator(gr.basic_block):
    """
    Appends CRC32 to incoming payload.
    Outputs:
      - 'payload_out': PDU containing (payload + CRC32)
      - 'len_out': Total length of (payload + CRC32) as an integer PMT
    """
    def __init__(self):
        gr.basic_block.__init__(
            self,
            name="Adaptive Payload Generator",
            in_sig=[],
            out_sig=[]
        )
        self.message_port_register_in(pmt.intern("in"))
        self.message_port_register_out(pmt.intern("payload_out"))
        self.message_port_register_out(pmt.intern("len_out"))
        self.set_msg_handler(pmt.intern("in"), self.handle_msg)

    def handle_msg(self, msg):
        if not pmt.is_pair(msg):
            return

        meta = pmt.car(msg)
        data_pmt = pmt.cdr(msg)
        payload = bytes(pmt.u8vector_elements(data_pmt))

        # Calculate and append CRC32 (4 bytes, big-endian)
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        crc_bytes = struct.pack("!I", crc)
        framed_payload = payload + crc_bytes
        total_len = len(framed_payload)

        # Add payload length to metadata
        if not pmt.is_dict(meta):
            meta = pmt.make_dict()
        meta = pmt.dict_add(meta, pmt.intern("payload_len"), pmt.from_long(total_len))

        # 1. Output the framed payload PDU
        out_vec = pmt.init_u8vector(total_len, list(framed_payload))
        self.message_port_pub(pmt.intern("payload_out"), pmt.cons(meta, out_vec))

        # 2. Output the total payload length
        self.message_port_pub(pmt.intern("len_out"), pmt.from_long(total_len))
