import numpy as np
from gnuradio import gr
import pmt
import struct
import zlib

class UnpackedPayloadDecoderSink(gr.sync_block):
    """
    Accepts an unpacked bit stream (np.uint8 values: 0 or 1).
    Collects bits, packs them into bytes (MSB-first), validates CRC32,
    and prints the message to stdout.
    
    Length control:
      - 'len_in' message port (connect from Header Recovery Block 'len_out')
      - OR 'packet_len' stream tag
    """
    def __init__(self, length_tag_key="packet_len"):
        gr.sync_block.__init__(
            self,
            name="Unpacked Payload Decoder & CRC Sink",
            in_sig=[np.uint8],
            out_sig=[]
        )
        self.length_tag_key = str(length_tag_key)
        self.bit_buf = []
        self.expected_payload_bytes = 0

        # Message port to receive the expected payload byte length
        self.message_port_register_in(pmt.intern("len_in"))
        self.set_msg_handler(pmt.intern("len_in"), self.handle_len)

    def handle_len(self, msg):
        """Receives the total payload byte length (data + 4 bytes CRC)."""
        if pmt.is_integer(msg):
            self.expected_payload_bytes = pmt.to_long(msg)
        elif pmt.is_pair(msg):
            cdr = pmt.cdr(msg)
            if pmt.is_integer(cdr):
                self.expected_payload_bytes = pmt.to_long(cdr)

    def process_packet(self, raw_bytes):
        if len(raw_bytes) < 4:
            print(f"[RX PAYLOAD] Frame too short ({len(raw_bytes)} bytes, min 4 for CRC).")
            return

        # Suffix is 4-byte CRC32
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
                print(f"Message (hex): {payload.hex(' ')}")
                print("============================================================\n")
            except UnicodeDecodeError:
                print("\n==================== [PAYLOAD RECEIVED] ====================")
                print(f"Status       : CRC VALID (0x{rx_crc:08X})")
                print(f"Payload Size : {len(payload)} bytes (binary data)")
                print(f"Message (hex): {payload.hex(' ')}")
                print("============================================================\n")
        else:
            print("\n-------------------- [CRC ERROR] --------------------")
            print(f"Status       : CRC MISMATCH!")
            print(f"Expected CRC : 0x{calc_crc:08X}")
            print(f"Received CRC : 0x{rx_crc:08X}")
            print(f"Total Bytes  : {len(raw_bytes)} bytes")
            print("-----------------------------------------------------\n")

    def work(self, input_items, output_items):
        in_bits = input_items[0]
        nread = self.nitems_read(0)
        tags = self.get_tags_in_window(0, 0, len(in_bits))

        # Check for stream tag length override
        for tag in tags:
            tag_name = pmt.to_python(tag.key)
            if tag_name == self.length_tag_key:
                val = int(pmt.to_python(tag.value))
                self.expected_payload_bytes = val

        for b in in_bits:
            self.bit_buf.append(int(b) & 0x01)

            # Check if we have accumulated all bits for the expected frame
            if self.expected_payload_bytes > 0:
                needed_bits = self.expected_payload_bytes * 8
                if len(self.bit_buf) >= needed_bits:
                    target_bits = self.bit_buf[:needed_bits]
                    self.bit_buf = self.bit_buf[needed_bits:]

                    # Pack 8 unpacked bits into 1 byte (MSB-first)
                    packed = bytearray()
                    for i in range(0, needed_bits, 8):
                        byte_val = 0
                        for j in range(8):
                            byte_val = (byte_val << 1) | target_bits[i + j]
                        packed.append(byte_val)

                    self.process_packet(packed)
                    self.expected_payload_bytes = 0

        return len(in_bits)
