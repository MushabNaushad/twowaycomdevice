#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# Author: maduwage
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import blocks
import pmt
from gnuradio import blocks, gr
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



class Tranport_DLC_test(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Not titled yet")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "Tranport_DLC_test")

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
        self.CRCpoly = CRCpoly = 0x4C11DB7

        ##################################################
        # Blocks
        ##################################################

        self.transport_transport_layer_0_0 = transport.transport_layer(4, 500, "initiator", 200)
        self.transport_transport_layer_0 = transport.transport_layer(4, 500, "initiator", 200)
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(25, [171, 205, 1, 0, 0, 0, 0, 17] + [ord(c) for c in "Hello from Strobe"])), 2000)
        self.blocks_message_debug_0_1_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_message_debug_0_1 = blocks.message_debug(True, gr.log_levels.info)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.transport_transport_layer_0, 'app_in'))
        self.msg_connect((self.transport_transport_layer_0, 'app_out'), (self.blocks_message_debug_0_1, 'print_pdu'))
        self.msg_connect((self.transport_transport_layer_0, 'pdu_out'), (self.transport_transport_layer_0_0, 'pdu_in'))
        self.msg_connect((self.transport_transport_layer_0_0, 'app_out'), (self.blocks_message_debug_0_1_0, 'print_pdu'))
        self.msg_connect((self.transport_transport_layer_0_0, 'pdu_out'), (self.transport_transport_layer_0, 'pdu_in'))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "Tranport_DLC_test")
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

    def get_CRCpoly(self):
        return self.CRCpoly

    def set_CRCpoly(self, CRCpoly):
        self.CRCpoly = CRCpoly




def main(top_block_cls=Tranport_DLC_test, options=None):

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
