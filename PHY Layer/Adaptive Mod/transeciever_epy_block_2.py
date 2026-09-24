import numpy as np
from gnuradio import gr
import pmt
import struct
import zlib

class UnpackedPayloadDecoderSink(gr.sync_block):
    """
    Collects unpacked payload bits, drops idle noise, validates CRC32,
    and prints decoded messages to stdout.
    """
    def __init__(self, length_tag_key="packet_len"):
        gr.sync_block.__init__(
            self,
            name="Unpacked Payload Decoder & CRC Sink",
            in_sig=[np.uint8],
            out_sig=[]
        )
        self.bit_buf = []
        self.expected_payload_bytes = 0

        self.message_port_register_in(pmt.intern("len_in"))
        self.set_msg_handler(pmt.intern("len_in"), self.handle_len)

    def handle_len(self, msg):
        val = 0
        if pmt.is_integer(msg):
            val = pmt.to_long(msg)
        elif pmt.is_pair(msg):
            cdr = pmt.cdr(msg)
            if pmt.is_integer(cdr):
                val = pmt.to_long(cdr)

        if val > 0:
            self.expected_payload_bytes = val
            self.bit_buf.clear()  # Flush any residual noise bits

    def process_packet(self, raw_bytes):
        if len(raw_bytes) < 4:
            return

        payload = bytes(raw_bytes[:-4])
        rx_crc = struct.unpack("!I", bytes(raw_bytes[-4:]))[0]
        calc_crc = zlib.crc32(payload) & 0xFFFFFFFF

        if rx_crc == calc_crc:
            try:
                text_msg = payload.decode("utf-8")
                print("\n==================== [PAYLOAD RECEIVED] ====================")
                print(f"Status       : CRC VALID (0x{rx_crc:08X})")
                print(f"Payload Size : {len(payload)} bytes")
                print(f"Message (str): {text_msg}")
                print("============================================================\n", flush=True)
            except UnicodeDecodeError:
                print(f"\n[RX PAYLOAD] Binary Data ({len(payload)} bytes), CRC OK (0x{rx_crc:08X})\n", flush=True)
        else:
            print(f"\n[RX PAYLOAD] CRC MISMATCH! Calc: 0x{calc_crc:08X}, Rx: 0x{rx_crc:08X}\n", flush=True)

    def work(self, input_items, output_items):
        in_bits = input_items[0]

        # Drop idle channel noise if no packet length has been set
        if self.expected_payload_bytes == 0:
            return len(in_bits)

        needed_bits = self.expected_payload_bytes * 8
        for b in in_bits:
            self.bit_buf.append(int(b) & 0x01)
            if len(self.bit_buf) == needed_bits:
                packed = bytearray()
                for i in range(0, needed_bits, 8):
                    byte_val = 0
                    for j in range(8):
                        byte_val = (byte_val << 1) | self.bit_buf[i + j]
                    packed.append(byte_val)

                self.process_packet(packed)
                self.expected_payload_bytes = 0
                self.bit_buf.clear()
                break

        return len(in_bits)
