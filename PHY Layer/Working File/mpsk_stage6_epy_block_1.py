import time
import struct
import zlib
import numpy as np
from gnuradio import gr

class blk(gr.sync_block):
    """
    Packet Transmitter Source Block:
    Constructs [Preamble + CCSDS Sync + Length + Payload + CRC32] frames.
    Sends `repeat_count` packets back-to-back, pauses for `time_interval` seconds,
    and repeats indefinitely.
    """
    def __init__(self, 
                 message="Hello QPSK World!", 
                 preamble_size=32, 
                 repeat_count=5, 
                 time_interval=2.0):
        gr.sync_block.__init__(
            self,
            name='Packet TX Source',
            in_sig=None,
            out_sig=[np.uint8]
        )
        self.message = str(message)
        self.preamble_size = max(0, int(preamble_size))
        self.repeat_count = max(1, int(repeat_count))
        self.time_interval = max(0.0, float(time_interval))

        # Standard CCSDS 32-bit Attached Sync Marker (ASM): 0x1ACFFC1D
        self.sync_word = bytes([0x1A, 0xCF, 0xFC, 0x1D])
        
        self.running = True
        self.burst_count = 0
        self.buffer = bytearray()
        self.packet = self._build_packet()

    def _build_packet(self):
        payload = self.message.encode('utf-8')
        # Alternating 10101010 bit pattern (0xAA) for symbol clock recovery
        preamble = bytes([0xAA] * self.preamble_size)
        length_header = struct.pack('>H', len(payload))
        crc = struct.pack('>I', zlib.crc32(payload) & 0xFFFFFFFF)
        return preamble + self.sync_word + length_header + payload + crc

    def _sleep_interruptible(self, seconds):
        """Sleeps in small slices to allow GRC to stop immediately without hanging."""
        start = time.time()
        while (time.time() - start) < seconds and self.running:
            time.sleep(0.02)

    def work(self, input_items, output_items):
        out = output_items[0]
        n_req = len(out)

        # When the burst buffer is completely drained
        if len(self.buffer) == 0:
            if not self.running:
                return -1

            # Pause between bursts after the first burst has been sent
            if self.burst_count > 0 and self.time_interval > 0:
                self._sleep_interruptible(self.time_interval)
                if not self.running:
                    return -1

            # Queue repeat_count packets back-to-back
            for _ in range(self.repeat_count):
                self.buffer.extend(self.packet)
            self.burst_count += 1

        n_to_send = min(n_req, len(self.buffer))
        out[:n_to_send] = np.frombuffer(self.buffer[:n_to_send], dtype=np.uint8)
        del self.buffer[:n_to_send]

        return n_to_send

    def stop(self):
        self.running = False
        return True

    # GRC runtime parameter callbacks
    def set_message(self, message):
        self.message = str(message)
        self.packet = self._build_packet()

    def set_preamble_size(self, preamble_size):
        self.preamble_size = max(0, int(preamble_size))
        self.packet = self._build_packet()

    def set_repeat_count(self, repeat_count):
        self.repeat_count = max(1, int(repeat_count))

    def set_time_interval(self, time_interval):
        self.time_interval = max(0.0, float(time_interval))