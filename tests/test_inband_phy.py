#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: In-Band Transport Protocol Header Test (Pure RF Simulation)
# Author: MethalMindiya
# Description: In-Band Transport Protocol Serialization Verification on Pure-RF Channel
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
import test_inband_phy_app_image_generator as app_image_generator  # embedded python block
import test_inband_phy_pure_rf_channel_fwd as pure_rf_channel_fwd  # embedded python block
import test_inband_phy_pure_rf_channel_rev as pure_rf_channel_rev  # embedded python block
import threading



class test_inband_phy(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "In-Band Transport Protocol Header Test (Pure RF Simulation)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("In-Band Transport Protocol Header Test (Pure RF Simulation)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test_inband_phy")

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
        self.src_addr = src_addr = 5
        self.rto_ms = rto_ms = 400
        self.mtu = mtu = 256
        self.m = m = 4
        self.dst_addr = dst_addr = 9
        self.drop_prob = drop_prob = 0.0

        ##################################################
        # Blocks
        ##################################################

        self._drop_prob_range = qtgui.Range(0, 0.5, 0.05, 0.0, 250)
        self._drop_prob_win = qtgui.RangeWidget(self._drop_prob_range, self.set_drop_prob, "Channel Loss Rate (p_drop)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._drop_prob_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.transport_responder = transport.transport_layer(m, rto_ms, 'responder', mtu, dst_addr, 0)
        self.transport_initiator = transport.transport_layer(m, rto_ms, 'initiator', mtu, src_addr, 0)
        self.pure_rf_channel_rev = pure_rf_channel_rev.blk(p_drop=drop_prob)
        self.pure_rf_channel_fwd = pure_rf_channel_fwd.blk(p_drop=drop_prob)
        self.blocks_throttle = blocks.throttle( gr.sizeof_gr_complex*1, 1000, True, 0 if "auto" == "auto" else max( int(float(0.1) * 1000) if "auto" == "time" else int(0.1), 1) )
        self.blocks_null_src = blocks.null_source(gr.sizeof_gr_complex*1)
        self.blocks_null_snk = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.blocks_message_debug_rx = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_message_debug_ini_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_message_debug_ini = blocks.message_debug(True, gr.log_levels.info)
        self.app_strobe = blocks.message_strobe(pmt.intern('TRIGGER'), 2000)
        self.app_image_generator = app_image_generator.blk(dst_addr=dst_addr, payload_len=1024)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.app_image_generator, 'app_out'), (self.transport_initiator, 'app_in'))
        self.msg_connect((self.app_strobe, 'strobe'), (self.app_image_generator, 'trig'))
        self.msg_connect((self.pure_rf_channel_fwd, 'pdu_out'), (self.transport_responder, 'pdu_in'))
        self.msg_connect((self.pure_rf_channel_rev, 'pdu_out'), (self.transport_initiator, 'pdu_in'))
        self.msg_connect((self.transport_initiator, 'app_out'), (self.blocks_message_debug_ini, 'store'))
        self.msg_connect((self.transport_initiator, 'pdu_out'), (self.blocks_message_debug_ini_0, 'print_pdu'))
        self.msg_connect((self.transport_initiator, 'pdu_out'), (self.pure_rf_channel_fwd, 'pdu_in'))
        self.msg_connect((self.transport_responder, 'app_out'), (self.blocks_message_debug_rx, 'store'))
        self.msg_connect((self.transport_responder, 'pdu_out'), (self.pure_rf_channel_rev, 'pdu_in'))
        self.connect((self.blocks_null_src, 0), (self.blocks_throttle, 0))
        self.connect((self.blocks_throttle, 0), (self.blocks_null_snk, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test_inband_phy")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_src_addr(self):
        return self.src_addr

    def set_src_addr(self, src_addr):
        self.src_addr = src_addr

    def get_rto_ms(self):
        return self.rto_ms

    def set_rto_ms(self, rto_ms):
        self.rto_ms = rto_ms

    def get_mtu(self):
        return self.mtu

    def set_mtu(self, mtu):
        self.mtu = mtu

    def get_m(self):
        return self.m

    def set_m(self, m):
        self.m = m

    def get_dst_addr(self):
        return self.dst_addr

    def set_dst_addr(self, dst_addr):
        self.dst_addr = dst_addr
        self.app_image_generator.dst_addr = self.dst_addr

    def get_drop_prob(self):
        return self.drop_prob

    def set_drop_prob(self, drop_prob):
        self.drop_prob = drop_prob
        self.pure_rf_channel_fwd.p_drop = self.drop_prob
        self.pure_rf_channel_rev.p_drop = self.drop_prob




def main(top_block_cls=test_inband_phy, options=None):

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
