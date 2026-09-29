import sys
import struct
import zlib
import datetime
import numpy as np
from gnuradio import gr

class blk(gr.sync_block):
    """
    Packet Receiver & Decoder Sink:
    Detects CCSDS sync marker (0x1ACFFC1D), verifies CRC32,
    and logs both VALID packets and CRC ERRORS to console and disk.
    """
    def __init__(self, filename="rx_output.txt", max_payload_len=512):
        gr.sync_block.__init__(
            self,
            name='Packet RX Decoder',
            in_sig=[np.uint8],
            out_sig=None
        )
        self.filename = filename
        self.max_payload_len = int(max_payload_len)
        
        # Standard CCSDS 32-bit Attached Sync Marker (ASM): 0x1ACFFC1D
        self.sync_word = bytes([0x1A, 0xCF, 0xFC, 0x1D])
        self.buffer = bytearray()
        
        # Performance counters
        self.total_frames = 0
        self.valid_count = 0
        self.error_count = 0
        
        self.log_file = open(self.filename, "a", buffering=1, encoding="utf-8")

    def work(self, input_items, output_items):
        in0 = input_items[0]
        if len(in0) == 0:
            return 0

        self.buffer.extend(in0.tobytes())

        while True:
            # 1. Search for sync word
            sync_idx = self.buffer.find(self.sync_word)
            if sync_idx == -1:
                # Keep last 3 bytes in case marker spans across work() buffer chunks
                if len(self.buffer) > 3:
                    del self.buffer[:-3]
                break

            # Discard preceding noise/preamble
            del self.buffer[:sync_idx]

            # 2. Wait until Sync (4B) + Length Header (2B) have arrived
            if len(self.buffer) < 6:
                break

            payload_len = struct.unpack('>H', self.buffer[4:6])[0]

            # 3. Guard against corrupted length fields
            # If bit errors hit length header and report an impossible size,
            # drop sync marker and continue scanning rather than hanging.
            if payload_len > self.max_payload_len:
                del self.buffer[:4]
                continue

            total_pkt_len = 4 + 2 + payload_len + 4  # Sync + Len + Payload + CRC32

            # 4. Wait for full frame arrival
            if len(self.buffer) < total_pkt_len:
                break

            # 5. Extract fields and compute CRC
            self.total_frames += 1
            payload = self.buffer[6:6 + payload_len]
            rx_crc = struct.unpack('>I', self.buffer[6 + payload_len:total_pkt_len])[0]
            calc_crc = zlib.crc32(payload) & 0xFFFFFFFF
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            if rx_crc == calc_crc:
                self.valid_count += 1
                text = payload.decode('utf-8', errors='replace')
                log_entry = (
                    f"[{timestamp}] Frame #{self.total_frames} [VALID] | "
                    f"Len: {payload_len}B | CRC: 0x{rx_crc:08X} | "
                    f"Data: {text}\n"
                )
            else:
                self.error_count += 1
                # Format first 16 bytes as hex for quick RF inspection
                hex_preview = ' '.join(f'{b:02X}' for b in payload[:16])
                if len(payload) > 16:
                    hex_preview += ' ...'
                corrupted_text = payload.decode('latin1', errors='replace')
                
                log_entry = (
                    f"[{timestamp}] Frame #{self.total_frames} [CRC ERROR] | "
                    f"Len: {payload_len}B | Expected CRC: 0x{calc_crc:08X} | "
                    f"Got CRC: 0x{rx_crc:08X} | "
                    f"Raw: [{hex_preview}] | "
                    f"Corrupted Text: {repr(corrupted_text)}\n"
                )

            # Output to terminal
            sys.stdout.write(log_entry)
            sys.stdout.flush()

            # Output to file
            self.log_file.write(log_entry)
            self.log_file.flush()

            # Advance buffer past this packet
            del self.buffer[:total_pkt_len]

        return len(in0)

    def stop(self):
        if self.log_file and not self.log_file.closed:
            per = (self.error_count / self.total_frames * 100.0) if self.total_frames > 0 else 0.0
            summary = (
                f"\n--- Demodulation Session Summary ---\n"
                f"Total Frames Detected: {self.total_frames}\n"
                f"Valid Packets:        {self.valid_count}\n"
                f"CRC Failures:         {self.error_count}\n"
                f"Packet Error Rate:    {per:.2f}%\n"
                f"------------------------------------\n"
            )
            sys.stdout.write(summary)
            sys.stdout.flush()
            self.log_file.write(summary)
            self.log_file.close()
        return True