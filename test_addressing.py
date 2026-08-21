#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Transport Layer Addressing + Packet Loss Test
# Description: Transport layer addressing test with simulated packet loss channel
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
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
import test_addressing_channel_fwd as channel_fwd  # embedded python block
import test_addressing_channel_rev as channel_rev  # embedded python block
import test_addressing_epy_block_0 as epy_block_0  # embedded python block
import threading



class test_addressing(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Transport Layer Addressing + Packet Loss Test", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Transport Layer Addressing + Packet Loss Test")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test_addressing")

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
        self.drop_rev = drop_rev = 0.1
        self.drop_fwd = drop_fwd = 0.2

        ##################################################
        # Blocks
        ##################################################

        self._drop_rev_range = qtgui.Range(0, 1, 0.05, 0.1, 200)
        self._drop_rev_win = qtgui.RangeWidget(self._drop_rev_range, self.set_drop_rev, "Rev Drop Prob", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._drop_rev_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._drop_fwd_range = qtgui.Range(0, 1, 0.05, 0.2, 200)
        self._drop_fwd_win = qtgui.RangeWidget(self._drop_fwd_range, self.set_drop_fwd, "Fwd Drop Prob", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._drop_fwd_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.transport_responder = transport.transport_layer(4, 500, "responder", 200, 0, 0)
        self.transport_initiator = transport.transport_layer(4, 500, "initiator", 200, 0, 0)
        self.transport_decoy = transport.transport_layer(4, 600, "responder", 200, 0, 0)
        self.msg_strobe = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(25, [2, 1, 1, 0, 0, 0, 0, 17] + [ord(c) for c in "Hello from Node1"])), 4000)
        self.epy_block_0 = epy_block_0.blk(label="Ack packet checker")
        self.debug_responder = blocks.message_debug(True, gr.log_levels.info)
        self.debug_responder.set_block_alias("1st output")
        self.debug_initiator = blocks.message_debug(True, gr.log_levels.info)
        self.debug_initiator.set_block_alias("2nd output")
        self.debug_decoy = blocks.message_debug(True, gr.log_levels.info)
        self.channel_rev = channel_rev.blk(p_drop=drop_rev)
        self.channel_fwd = channel_fwd.blk(p_drop=drop_fwd)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, 1000, True, 0 if "auto" == "auto" else max( int(float(0.1) * 1000) if "auto" == "time" else int(0.1), 1) )
        self.blocks_null_source_0 = blocks.null_source(gr.sizeof_gr_complex*1)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.blocks_message_debug_0 = blocks.message_debug(True, gr.log_levels.info)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.channel_fwd, 'pdu_out'), (self.transport_decoy, 'pdu_in'))
        self.msg_connect((self.channel_fwd, 'pdu_out'), (self.transport_responder, 'pdu_in'))
        self.msg_connect((self.channel_rev, 'pdu_out'), (self.epy_block_0, 'in'))
        self.msg_connect((self.channel_rev, 'pdu_out'), (self.transport_initiator, 'pdu_in'))
        self.msg_connect((self.msg_strobe, 'strobe'), (self.blocks_message_debug_0, 'print_pdu'))
        self.msg_connect((self.msg_strobe, 'strobe'), (self.transport_initiator, 'app_in'))
        self.msg_connect((self.transport_decoy, 'pdu_out'), (self.channel_rev, 'pdu_in'))
        self.msg_connect((self.transport_decoy, 'app_out'), (self.debug_decoy, 'print_pdu'))
        self.msg_connect((self.transport_initiator, 'pdu_out'), (self.channel_fwd, 'pdu_in'))
        self.msg_connect((self.transport_initiator, 'app_out'), (self.debug_initiator, 'print_pdu'))
        self.msg_connect((self.transport_responder, 'pdu_out'), (self.channel_rev, 'pdu_in'))
        self.msg_connect((self.transport_responder, 'app_out'), (self.debug_responder, 'print_pdu'))
        self.connect((self.blocks_null_source_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.blocks_null_sink_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test_addressing")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_drop_rev(self):
        return self.drop_rev

    def set_drop_rev(self, drop_rev):
        self.drop_rev = drop_rev
        self.channel_rev.p_drop = self.drop_rev

    def get_drop_fwd(self):
        return self.drop_fwd

    def set_drop_fwd(self, drop_fwd):
        self.drop_fwd = drop_fwd
        self.channel_fwd.p_drop = self.drop_fwd




def main(top_block_cls=test_addressing, options=None):

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
