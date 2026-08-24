#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Commlink Multi-Node Radio Transport Flowgraph (Nodes 1-5)
# Author: MethalMindiya
# Description: Multi-Node ZeroMQ Radio Transport Flowgraph for Commlink GUI Application
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import blocks
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
from gnuradio import zeromq
import commlink_radio_rf_bus as rf_bus  # embedded python block
import threading



class commlink_radio(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Commlink Multi-Node Radio Transport Flowgraph (Nodes 1-5)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Commlink Multi-Node Radio Transport Flowgraph (Nodes 1-5)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "commlink_radio")

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
        self.rto_ms = rto_ms = 400
        self.mtu = mtu = 1000
        self.m = m = 6
        self.drop_prob = drop_prob = 0.0

        ##################################################
        # Blocks
        ##################################################

        self._drop_prob_range = qtgui.Range(0, 0.5, 0.05, 0.0, 250)
        self._drop_prob_win = qtgui.RangeWidget(self._drop_prob_range, self.set_drop_prob, "RF Loss Rate (p_drop)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._drop_prob_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.zmq_push_n5 = zeromq.push_msg_sink('tcp://127.0.0.1:52010', 100, True)
        self.zmq_push_n4 = zeromq.push_msg_sink('tcp://127.0.0.1:52008', 100, True)
        self.zmq_push_n3 = zeromq.push_msg_sink('tcp://127.0.0.1:52006', 100, True)
        self.zmq_push_n2 = zeromq.push_msg_sink('tcp://127.0.0.1:52004', 100, True)
        self.zmq_push_n1 = zeromq.push_msg_sink('tcp://127.0.0.1:52002', 100, True)
        self.zmq_pull_n5 = zeromq.pull_msg_source('tcp://127.0.0.1:52009', 100, True)
        self.zmq_pull_n4 = zeromq.pull_msg_source('tcp://127.0.0.1:52007', 100, True)
        self.zmq_pull_n3 = zeromq.pull_msg_source('tcp://127.0.0.1:52005', 100, True)
        self.zmq_pull_n2 = zeromq.pull_msg_source('tcp://127.0.0.1:52003', 100, True)
        self.zmq_pull_n1 = zeromq.pull_msg_source('tcp://127.0.0.1:52001', 100, True)
        self.transport_n5 = transport.transport_layer(m, rto_ms, "responder", mtu, 5, 0)
        self.transport_n4 = transport.transport_layer(m, rto_ms, "responder", mtu, 4, 0)
        self.transport_n3 = transport.transport_layer(m, rto_ms, "responder", mtu, 3, 0)
        self.transport_n2 = transport.transport_layer(m, rto_ms, "responder", mtu, 2, 0)
        self.transport_n1 = transport.transport_layer(m, rto_ms, "initiator", mtu, 1, 0)
        self.rf_bus = rf_bus.multi_node_rf_bus(drop_prob=drop_prob)
        self.blocks_throttle = blocks.throttle( gr.sizeof_char*1, 32000, True, 0 if "auto" == "auto" else max( int(float(0.1) * 32000) if "auto" == "time" else int(0.1), 1) )
        self.blocks_null_src = blocks.null_source(gr.sizeof_char*1)
        self.blocks_null_snk = blocks.null_sink(gr.sizeof_char*1)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.rf_bus, 'pdu_out_1'), (self.transport_n1, 'pdu_in'))
        self.msg_connect((self.rf_bus, 'pdu_out_2'), (self.transport_n2, 'pdu_in'))
        self.msg_connect((self.rf_bus, 'pdu_out_3'), (self.transport_n3, 'pdu_in'))
        self.msg_connect((self.rf_bus, 'pdu_out_4'), (self.transport_n4, 'pdu_in'))
        self.msg_connect((self.rf_bus, 'pdu_out_5'), (self.transport_n5, 'pdu_in'))
        self.msg_connect((self.transport_n1, 'pdu_out'), (self.rf_bus, 'pdu_in_1'))
        self.msg_connect((self.transport_n1, 'app_out'), (self.zmq_push_n1, 'in'))
        self.msg_connect((self.transport_n2, 'pdu_out'), (self.rf_bus, 'pdu_in_2'))
        self.msg_connect((self.transport_n2, 'app_out'), (self.zmq_push_n2, 'in'))
        self.msg_connect((self.transport_n3, 'pdu_out'), (self.rf_bus, 'pdu_in_3'))
        self.msg_connect((self.transport_n3, 'app_out'), (self.zmq_push_n3, 'in'))
        self.msg_connect((self.transport_n4, 'pdu_out'), (self.rf_bus, 'pdu_in_4'))
        self.msg_connect((self.transport_n4, 'app_out'), (self.zmq_push_n4, 'in'))
        self.msg_connect((self.transport_n5, 'pdu_out'), (self.rf_bus, 'pdu_in_5'))
        self.msg_connect((self.transport_n5, 'app_out'), (self.zmq_push_n5, 'in'))
        self.msg_connect((self.zmq_pull_n1, 'out'), (self.transport_n1, 'app_in'))
        self.msg_connect((self.zmq_pull_n2, 'out'), (self.transport_n2, 'app_in'))
        self.msg_connect((self.zmq_pull_n3, 'out'), (self.transport_n3, 'app_in'))
        self.msg_connect((self.zmq_pull_n4, 'out'), (self.transport_n4, 'app_in'))
        self.msg_connect((self.zmq_pull_n5, 'out'), (self.transport_n5, 'app_in'))
        self.connect((self.blocks_null_src, 0), (self.blocks_throttle, 0))
        self.connect((self.blocks_throttle, 0), (self.blocks_null_snk, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "commlink_radio")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

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

    def get_drop_prob(self):
        return self.drop_prob

    def set_drop_prob(self, drop_prob):
        self.drop_prob = drop_prob
        self.rf_bus.drop_prob = self.drop_prob




def main(top_block_cls=commlink_radio, options=None):

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
