#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Transport Layer Test
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import DLC
from gnuradio import blocks
import pmt
from gnuradio import blocks, gr
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import transport
import threading



class test_transport(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Transport Layer Test", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Transport Layer Test")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test_transport")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 32000
        self.flag = flag = 126

        ##################################################
        # Blocks
        ##################################################

        self.transport_transport_layer_1 = transport.transport_layer(4, 500, "responder", 200, 0, 0)
        self.transport_transport_layer_0 = transport.transport_layer(4, 500, "initiator", 200, 0, 0)
        self.digital_crc32_async_bb_0_0 = digital.crc32_async_bb(True)
        self.digital_crc32_async_bb_0 = digital.crc32_async_bb(False)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, 1000, True, 0 if "auto" == "auto" else max( int(float(0.1) * 1000) if "auto" == "time" else int(0.1), 1) )
        self.blocks_null_source_0 = blocks.null_source(gr.sizeof_gr_complex*1)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(25, [2, 1, 1, 0, 0, 0, 0, 17] + [ord(c) for c in "Hello from Strobe"])), 2000)
        self.blocks_message_debug_0 = blocks.message_debug(True, gr.log_levels.info)
        self.DLC_removeFlags_0_0 = DLC.removeFlags(flag)
        self.DLC_removeFlags_0 = DLC.removeFlags(flag)
        self.DLC_deStuffing_0_0 = DLC.deStuffing(126)
        self.DLC_deStuffing_0 = DLC.deStuffing(126)
        self.DLC_bitStuffing_0_0 = DLC.bitStuffing(126)
        self.DLC_bitStuffing_0 = DLC.bitStuffing(126)
        self.DLC_addFlags_0_0 = DLC.addFlags(flag, True)
        self.DLC_addFlags_0 = DLC.addFlags(flag, True)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.DLC_addFlags_0, 'out'), (self.DLC_removeFlags_0, 'pdu_in'))
        self.msg_connect((self.DLC_addFlags_0_0, 'out'), (self.DLC_removeFlags_0_0, 'pdu_in'))
        self.msg_connect((self.DLC_bitStuffing_0, 'out'), (self.DLC_addFlags_0, 'in'))
        self.msg_connect((self.DLC_bitStuffing_0_0, 'out'), (self.DLC_addFlags_0_0, 'in'))
        self.msg_connect((self.DLC_deStuffing_0, 'out'), (self.digital_crc32_async_bb_0_0, 'in'))
        self.msg_connect((self.DLC_deStuffing_0_0, 'out'), (self.transport_transport_layer_0, 'pdu_in'))
        self.msg_connect((self.DLC_removeFlags_0, 'pdu_out'), (self.DLC_deStuffing_0, 'in'))
        self.msg_connect((self.DLC_removeFlags_0_0, 'pdu_out'), (self.DLC_deStuffing_0_0, 'in'))
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.transport_transport_layer_0, 'app_in'))
        self.msg_connect((self.digital_crc32_async_bb_0, 'out'), (self.DLC_bitStuffing_0, 'in'))
        self.msg_connect((self.digital_crc32_async_bb_0_0, 'out'), (self.transport_transport_layer_1, 'pdu_in'))
        self.msg_connect((self.transport_transport_layer_0, 'app_out'), (self.blocks_message_debug_0, 'print_pdu'))
        self.msg_connect((self.transport_transport_layer_0, 'pdu_out'), (self.digital_crc32_async_bb_0, 'in'))
        self.msg_connect((self.transport_transport_layer_1, 'pdu_out'), (self.DLC_bitStuffing_0_0, 'in'))
        self.msg_connect((self.transport_transport_layer_1, 'app_out'), (self.blocks_message_debug_0, 'print_pdu'))
        self.connect((self.blocks_null_source_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.blocks_null_sink_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test_transport")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

    def get_flag(self):
        return self.flag

    def set_flag(self, flag):
        self.flag = flag




def main(top_block_cls=test_transport, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
