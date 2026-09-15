"""
Embedded Python Block: PacketDeframerRX with ACK generation
"""
import numpy as np
from gnuradio import gr
import pmt
import zlib

class PacketDeframerRX(gr.sync_block):
    STATE_SYNC = 0
    STATE_HEADER = 1
    STATE_PAYLOAD_CRC = 2

    def __init__(self, my_id="A", peer_id="B", max_bit_errors=1, max_payload_len=512):
        gr.sync_block.__init__(
            self,
            name="Packet Deframer RX",
            in_sig=[np.uint8],
            out_sig=None
        )
        self.my_id = str(my_id)
        self.peer_id = str(peer_id)
        self.max_bit_errors = max_bit_errors
        self.max_payload_len = max_payload_len
        self.sync_target = 0x1ACFFC1D

        self.state = self.STATE_SYNC
        self.shift_reg = 0
        self.bit_buf = 0
        self.bit_count = 0
        self.byte_buf = bytearray()
        self.payload_len = 0
        self.target_bytes = 0

        # Message port to feed ACK back to TX
        self.message_port_register_out(pmt.intern("ack_out"))

    def work(self, input_items, output_items):
        in_bits = input_items[0]

        for bit in in_bits:
            b = int(bit) & 1

            if self.state == self.STATE_SYNC:
                self.shift_reg = ((self.shift_reg << 1) | b) & 0xFFFFFFFF
                xor_diff = self.shift_reg ^ self.sync_target
                if bin(xor_diff).count('1') <= self.max_bit_errors:
                    self.state = self.STATE_HEADER
                    self.bit_buf = 0
                    self.bit_count = 0
                    self.byte_buf = bytearray()
                    self.target_bytes = 2

            elif self.state == self.STATE_HEADER:
                self.bit_buf = (self.bit_buf << 1) | b
                self.bit_count += 1
                if self.bit_count == 8:
                    self.byte_buf.append(self.bit_buf)
                    self.bit_buf = 0
                    self.bit_count = 0
                    if len(self.byte_buf) == self.target_bytes:
                        self.payload_len = int.from_bytes(self.byte_buf, 'big')
                        if 0 < self.payload_len <= self.max_payload_len:
                            self.state = self.STATE_PAYLOAD_CRC
                            self.byte_buf = bytearray()
                            self.target_bytes = self.payload_len + 4
                        else:
                            self.state = self.STATE_SYNC

            elif self.state == self.STATE_PAYLOAD_CRC:
                self.bit_buf = (self.bit_buf << 1) | b
                self.bit_count += 1
                if self.bit_count == 8:
                    self.byte_buf.append(self.bit_buf)
                    self.bit_buf = 0
                    self.bit_count = 0
                    if len(self.byte_buf) == self.target_bytes:
                        payload = bytes(self.byte_buf[:self.payload_len])
                        rx_crc = int.from_bytes(self.byte_buf[self.payload_len:], 'big')

                        if rx_crc == zlib.crc32(payload):
                            msg_str = payload.decode('utf-8', errors='replace')
                            self._handle_valid_packet(msg_str)

                        self.state = self.STATE_SYNC
                        self.shift_reg = 0

        return len(in_bits)

    def _handle_valid_packet(self, raw_str):
        # Format expectation: SRC>DST:MESSAGE
        if ">" not in raw_str or ":" not in raw_str:
            return

        header, message = raw_str.split(":", 1)
        src, dst = header.split(">", 1)

        # 1. Reject self-reception (TX bleed)
        if src == self.my_id:
            return

        # 2. Reject messages directed to other stations
        if dst != self.my_id:
            return

        # 3. Handle packet
        if message.startswith("ACK_"):
            print(f"\n>>> [SUCCESS] Peer received: {message[4:]}", flush=True)
        else:
            print(f"\n========================================", flush=True)
            print(f"[RX FROM {src}]: {message}", flush=True)
            print(f"========================================", flush=True)

            # Auto-respond with ACK (Sent 1x to avoid channel clutter)
            ack_payload = f"{self.my_id}>{self.peer_id}:ACK_{message}"
            self.message_port_pub(pmt.intern("ack_out"), pmt.intern(ack_payload))