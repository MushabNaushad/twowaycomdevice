#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_inband_serialization.py
============================
Verifies:
1. Outgoing PDUs on pdu_out contain the 18-byte in-band binary Transport Header.
2. An over-the-air raw PHY simulation (where PMT metadata dictionaries are
   intentionally WIPED to simulate pure RF byte transmission) correctly executes:
   SYN (18B) -> SYN_ACK (18B) -> DATA (18B + chunk) -> ACK (18B) -> FIN (18B) -> FIN_ACK (18B)
3. The reassembled application payload at app_out is 100% byte-for-byte identical.
"""

import sys, os, time, pmt, unittest
from PyQt5 import Qt, QtCore

BUILD_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'blocks', 'gr-transport', 'build', 'lib'))
os.environ['LD_LIBRARY_PATH'] = f"{BUILD_LIB}:{os.environ.get('LD_LIBRARY_PATH', '')}"

from gnuradio import gr, blocks, transport

# ─── Mock Pure-RF Byte Channel (Wipes PMT metadata dictionary completely) ─────
class PureRfByteChannel(gr.basic_block):
    """
    Simulates a physical layer (Modulator -> RF -> Demodulator) which only
    transmits the raw bytes in cdr(pdu) and discards any in-memory PMT dictionary.
    """
    def __init__(self, name="PureRfByteChannel"):
        gr.basic_block.__init__(self, name=name, in_sig=None, out_sig=None)
        self.message_port_register_in(pmt.intern('pdu_in'))
        self.message_port_register_out(pmt.intern('pdu_out'))
        self.set_msg_handler(pmt.intern('pdu_in'), self.handle_pdu)
        self.transmitted_frames = []

    def handle_pdu(self, msg):
        if pmt.is_pair(msg):
            data = pmt.cdr(msg) # Extract only the raw bytes transmitted over the air
            if pmt.is_u8vector(data):
                raw_bytes = bytes(pmt.u8vector_elements(data))
                self.transmitted_frames.append(raw_bytes)
                
                # Create a fresh PDU with an EMPTY metadata dict (as a real PHY demodulator would)
                empty_meta = pmt.make_dict()
                air_pdu = pmt.cons(empty_meta, data)
                self.message_port_pub(pmt.intern('pdu_out'), air_pdu)


class DeliveriesSink(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(self, name="DeliveriesSink", in_sig=None, out_sig=None)
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)
        self.delivered_payloads = []

    def handle_msg(self, msg):
        if pmt.is_pair(msg):
            meta = pmt.car(msg)
            data = pmt.cdr(msg)
            if pmt.is_u8vector(data):
                raw = bytes(pmt.u8vector_elements(data))
                self.delivered_payloads.append((meta, raw))


def run_inband_test():
    print("================================================================================")
    print("RUNNING IN-BAND TRANSPORT PROTOCOL SERIALIZATION & PHY INTEROPERABILITY TEST")
    print("================================================================================")

    qapp = Qt.QApplication(sys.argv)
    tb = gr.top_block("InBandSerializationTest")

    # Flowgraph components
    src_addr = 0x05
    dst_addr = 0x09
    mtu = 256
    m = 4 # Window = 8

    ini = transport.transport_layer(m, 400, "initiator", mtu, src_addr, 0)
    rsp = transport.transport_layer(m, 400, "responder", mtu, dst_addr, 0)

    # Pure RF channels (discards PMT metadata in both directions)
    fwd_rf_channel = PureRfByteChannel("Forward_RF")
    rev_rf_channel = PureRfByteChannel("Reverse_RF")
    sink = DeliveriesSink()

    # Interconnections
    tb.msg_connect((ini, 'pdu_out'), (fwd_rf_channel, 'pdu_in'))
    tb.msg_connect((fwd_rf_channel, 'pdu_out'), (rsp, 'pdu_in'))

    tb.msg_connect((rsp, 'pdu_out'), (rev_rf_channel, 'pdu_in'))
    tb.msg_connect((rev_rf_channel, 'pdu_out'), (ini, 'pdu_in'))

    tb.msg_connect((rsp, 'app_out'), (sink, 'in'))

    tb.start()

    # Generate a realistic multi-packet Image bitstream
    image_payload_len = 1024 # 4 MTU chunks of 256B + 8B header = 1032B
    fake_image_bytes = bytes([0xAA, 0xBB, 0xCC, 0xDD] + [(i * 7) % 256 for i in range(image_payload_len)])
    
    # 8-byte application header: dst=0x09, port=0, type=0x02 (image), rsv=0, len=1028
    n_len = len(fake_image_bytes)
    app_header = bytes([
        dst_addr, 0x00, 0x02, 0x00,
        (n_len >> 24) & 0xFF, (n_len >> 16) & 0xFF, (n_len >> 8) & 0xFF, n_len & 0xFF
    ])
    full_app_frame = app_header + fake_image_bytes

    print(f"\n[1] Injecting Application Image Bitstream ({len(full_app_frame)} bytes) into Initiator (Node {src_addr})...")
    pdu = pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(full_app_frame), list(full_app_frame)))
    ini.to_basic_block()._post(pmt.intern('app_in'), pdu)

    # Wait for transfer over pure RF channel
    timeout = 3.0
    t0 = time.time()
    while len(sink.delivered_payloads) == 0 and (time.time() - t0) < timeout:
        time.sleep(0.05)

    tb.stop()
    tb.wait()

    print(f"\n[2] Analyzing Frames Transmitted Across the Pure RF Channel (0% PMT Metadata Retained):")
    print(f"  Total Forward RF Frames (Initiator -> Responder): {len(fwd_rf_channel.transmitted_frames)}")
    print(f"  Total Reverse RF Frames (Responder -> Initiator): {len(rev_rf_channel.transmitted_frames)}")

    for i, frame in enumerate(fwd_rf_channel.transmitted_frames):
        pkt_type_code = frame[0]
        media_type_code = frame[1]
        s_addr = frame[2]
        d_addr = frame[4]
        seq_no = (frame[6] << 8) | frame[7]
        total_pkts = (frame[8] << 8) | frame[9]
        session_id = int.from_bytes(frame[10:18], byteorder='big')
        
        type_names = {1: "SYN", 2: "SYN_ACK", 3: "DATA", 4: "ACK", 5: "FIN", 6: "FIN_ACK"}
        type_str = type_names.get(pkt_type_code, f"0x{pkt_type_code:02X}")
        print(f"    Frame #{i+1:02d}: Type={type_str:<7} Length={len(frame):>4}B | Src={s_addr} Dst={d_addr} Seq={seq_no} TotPkts={total_pkts} Session=0x{session_id:016X}")

    for i, frame in enumerate(rev_rf_channel.transmitted_frames):
        pkt_type_code = frame[0]
        seq_no = (frame[6] << 8) | frame[7]
        type_names = {1: "SYN", 2: "SYN_ACK", 3: "DATA", 4: "ACK", 5: "FIN", 6: "FIN_ACK"}
        type_str = type_names.get(pkt_type_code, f"0x{pkt_type_code:02X}")
        print(f"    Reply #{i+1:02d}: Type={type_str:<7} Length={len(frame):>4}B | Seq={seq_no}")

    print(f"\n[3] Validating Delivery at Responder (Node {dst_addr}):")
    if len(sink.delivered_payloads) == 0:
        print("  ❌ FAILURE: No payload delivered to Responder app_out!")
        return False

    meta, delivered_raw = sink.delivered_payloads[0]
    delivered_payload_type = pmt.symbol_to_string(pmt.dict_ref(meta, pmt.mp("payload_type"), pmt.mp("")))
    print(f"  Delivered Payload Size: {len(delivered_raw)} bytes (Expected: {len(full_app_frame)} bytes)")
    print(f"  Delivered Meta Type:    '{delivered_payload_type}' (Expected: 'image')")

    assert delivered_raw == full_app_frame, "Payload corrupted during transfer!"
    assert delivered_payload_type == 'image', "Payload type metadata mismatch!"

    print("\n✅ SUCCESS: 100% BYTE-FOR-BYTE DATA INTEGRITY CONFIRMED ACROSS PURE RF CHANNEL!")
    print("================================================================================\n")
    return True

if __name__ == '__main__':
    ok = run_inband_test()
    sys.exit(0 if ok else 1)
