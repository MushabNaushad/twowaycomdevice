import numpy as np
from gnuradio import gr
import pmt

class custom_transport_layer(gr.basic_block):
    def __init__(self):
        # gr.basic_block with no stream inputs or outputs
        gr.basic_block.__init__(
            self,
            name='Transport Layer (ACK/ARQ)',
            in_sig=None,
            out_sig=None
        )

        # 1. Register Message Ports
        self.message_port_register_in(pmt.intern("app_in"))    # From App
        self.message_port_register_in(pmt.intern("radio_in"))  # From Receiver
        self.message_port_register_out(pmt.intern("radio_out"))# To Transmitter
        self.message_port_register_out(pmt.intern("app_out"))  # To App

        # 2. Bind Message Handlers (Callbacks)
        self.set_msg_handler(pmt.intern("app_in"), self.handle_app_input)
        self.set_msg_handler(pmt.intern("radio_in"), self.handle_radio_input)

        # State Variables
        self.seq_num = 0

    def handle_app_input(self, msg):
        """Triggers when your app sends data to be transmitted."""
        # Extract payload from incoming PDU
        meta = pmt.car(msg)
        payload_pmt = pmt.cdr(msg)
        raw_bytes = bytes(pmt.u8vector_elements(payload_pmt))

        # TODO: Add your Header (Sync Word, Address, Seq Num) and CRC
        formatted_packet = bytearray([0xAA, 0x01, self.seq_num]) + bytearray(raw_bytes)

        # Convert back to PDU format
        out_meta = pmt.make_dict()
        out_payload = pmt.init_u8vector(len(formatted_packet), list(formatted_packet))
        pdu_out = pmt.cons(out_meta, out_payload)

        # Publish to radio output port
        self.message_port_pub(pmt.intern("radio_out"), pdu_out)

    def handle_radio_input(self, msg):
        """Triggers when demodulated data arrives from the radio."""
        meta = pmt.car(msg)
        payload_pmt = pmt.cdr(msg)
        received_bytes = bytes(pmt.u8vector_elements(payload_pmt))

        # TODO: Verify CRC, check Packet Type (DATA vs ACK), process logic
        pass