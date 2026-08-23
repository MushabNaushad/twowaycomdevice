#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: 10-Node Transport Layer Addressing Test
# Description: 10-node transport layer addressing test on a shared broadcast bus
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
import test_10node_debug_node1 as debug_node1  # embedded python block
import test_10node_debug_node10 as debug_node10  # embedded python block
import test_10node_debug_node2 as debug_node2  # embedded python block
import test_10node_debug_node3 as debug_node3  # embedded python block
import test_10node_debug_node4 as debug_node4  # embedded python block
import test_10node_debug_node5 as debug_node5  # embedded python block
import test_10node_debug_node6 as debug_node6  # embedded python block
import test_10node_debug_node7 as debug_node7  # embedded python block
import test_10node_debug_node8 as debug_node8  # embedded python block
import test_10node_debug_node9 as debug_node9  # embedded python block
import test_10node_shared_bus as shared_bus  # embedded python block
import threading



class test_10node(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "10-Node Transport Layer Addressing Test", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("10-Node Transport Layer Addressing Test")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test_10node")

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
        self.strobe_period_ms = strobe_period_ms = 8000
        self.drop_prob = drop_prob = 0.1

        ##################################################
        # Blocks
        ##################################################

        self._drop_prob_range = qtgui.Range(0, 1, 0.05, 0.1, 200)
        self._drop_prob_win = qtgui.RangeWidget(self._drop_prob_range, self.set_drop_prob, "Bus Drop Prob", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._drop_prob_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.strobe_node9 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [4, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 9!"])), strobe_period_ms)
        self.strobe_node8 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [3, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 8!"])), strobe_period_ms)
        self.strobe_node7 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [2, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 7!"])), strobe_period_ms)
        self.strobe_node6 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [1, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 6!"])), strobe_period_ms)
        self.strobe_node5 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [10, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 5!"])), strobe_period_ms)
        self.strobe_node4 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [9, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 4!"])), strobe_period_ms)
        self.strobe_node3 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [8, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 3!"])), strobe_period_ms)
        self.strobe_node2 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [7, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 2!"])), strobe_period_ms)
        self.strobe_node10 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 20, [5, 0, 1, 0, 0, 0,  0, 20] + [ord(c) for c in "Hello from Node 10!"])), strobe_period_ms)
        self.strobe_node1 = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(8 + 19, [6, 0, 1, 0, 0, 0,  0, 19] + [ord(c) for c in "Hello from Node 1!"])), strobe_period_ms)
        self.shared_bus = shared_bus.blk(p_drop=drop_prob)
        self.rsp_node9 = transport.transport_layer(4, 600, "responder", 200, 9, 0)
        self.rsp_node8 = transport.transport_layer(4, 600, "responder", 200, 8, 0)
        self.rsp_node7 = transport.transport_layer(4, 600, "responder", 200, 7, 0)
        self.rsp_node6 = transport.transport_layer(4, 600, "responder", 200, 6, 0)
        self.rsp_node5 = transport.transport_layer(4, 600, "responder", 200, 5, 0)
        self.rsp_node4 = transport.transport_layer(4, 600, "responder", 200, 4, 0)
        self.rsp_node3 = transport.transport_layer(4, 600, "responder", 200, 3, 0)
        self.rsp_node2 = transport.transport_layer(4, 600, "responder", 200, 2, 0)
        self.rsp_node10 = transport.transport_layer(4, 600, "responder", 200, 10, 0)
        self.rsp_node1 = transport.transport_layer(4, 600, "responder", 200, 1, 0)
        self.ini_node9 = transport.transport_layer(4, 600, "initiator", 200, 9, 0)
        self.ini_node8 = transport.transport_layer(4, 600, "initiator", 200, 8, 0)
        self.ini_node7 = transport.transport_layer(4, 600, "initiator", 200, 7, 0)
        self.ini_node6 = transport.transport_layer(4, 600, "initiator", 200, 6, 0)
        self.ini_node5 = transport.transport_layer(4, 600, "initiator", 200, 5, 0)
        self.ini_node4 = transport.transport_layer(4, 600, "initiator", 200, 4, 0)
        self.ini_node3 = transport.transport_layer(4, 600, "initiator", 200, 3, 0)
        self.ini_node2 = transport.transport_layer(4, 600, "initiator", 200, 2, 0)
        self.ini_node10 = transport.transport_layer(4, 600, "initiator", 200, 10, 0)
        self.ini_node1 = transport.transport_layer(4, 600, "initiator", 200, 1, 0)
        self.debug_node9 = debug_node9.blk(label="Node 9 RX")
        self.debug_node8 = debug_node8.blk(label="Node 8 RX")
        self.debug_node7 = debug_node7.blk(label="Node 7 RX")
        self.debug_node6 = debug_node6.blk(label="Node 6 RX")
        self.debug_node5 = debug_node5.blk(label="Node 5 RX")
        self.debug_node4 = debug_node4.blk(label="Node 4 RX")
        self.debug_node3 = debug_node3.blk(label="Node 3 RX")
        self.debug_node2 = debug_node2.blk(label="Node 2 RX")
        self.debug_node10 = debug_node10.blk(label="Node 10 RX")
        self.debug_node1 = debug_node1.blk(label="Node 1 RX")
        self.debug_ini_node9 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node8 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node7 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node6 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node5 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node4 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node3 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node2 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node10 = blocks.message_debug(True, gr.log_levels.info)
        self.debug_ini_node1 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, 1000, True, 0 if "auto" == "auto" else max( int(float(0.1) * 1000) if "auto" == "time" else int(0.1), 1) )
        self.blocks_null_source_0 = blocks.null_source(gr.sizeof_gr_complex*1)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_gr_complex*1)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.ini_node1, 'app_out'), (self.debug_ini_node1, 'store'))
        self.msg_connect((self.ini_node1, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node10, 'app_out'), (self.debug_ini_node10, 'store'))
        self.msg_connect((self.ini_node10, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node2, 'app_out'), (self.debug_ini_node2, 'store'))
        self.msg_connect((self.ini_node2, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node3, 'app_out'), (self.debug_ini_node3, 'store'))
        self.msg_connect((self.ini_node3, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node4, 'app_out'), (self.debug_ini_node4, 'store'))
        self.msg_connect((self.ini_node4, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node5, 'app_out'), (self.debug_ini_node5, 'store'))
        self.msg_connect((self.ini_node5, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node6, 'app_out'), (self.debug_ini_node6, 'store'))
        self.msg_connect((self.ini_node6, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node7, 'app_out'), (self.debug_ini_node7, 'store'))
        self.msg_connect((self.ini_node7, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node8, 'app_out'), (self.debug_ini_node8, 'store'))
        self.msg_connect((self.ini_node8, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.ini_node9, 'app_out'), (self.debug_ini_node9, 'store'))
        self.msg_connect((self.ini_node9, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node1, 'app_out'), (self.debug_node1, 'in'))
        self.msg_connect((self.rsp_node1, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node10, 'app_out'), (self.debug_node10, 'in'))
        self.msg_connect((self.rsp_node10, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node2, 'app_out'), (self.debug_node2, 'in'))
        self.msg_connect((self.rsp_node2, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node3, 'app_out'), (self.debug_node3, 'in'))
        self.msg_connect((self.rsp_node3, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node4, 'app_out'), (self.debug_node4, 'in'))
        self.msg_connect((self.rsp_node4, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node5, 'app_out'), (self.debug_node5, 'in'))
        self.msg_connect((self.rsp_node5, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node6, 'app_out'), (self.debug_node6, 'in'))
        self.msg_connect((self.rsp_node6, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node7, 'app_out'), (self.debug_node7, 'in'))
        self.msg_connect((self.rsp_node7, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node8, 'app_out'), (self.debug_node8, 'in'))
        self.msg_connect((self.rsp_node8, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.rsp_node9, 'app_out'), (self.debug_node9, 'in'))
        self.msg_connect((self.rsp_node9, 'pdu_out'), (self.shared_bus, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node1, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node10, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node2, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node3, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node4, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node5, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node6, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node7, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node8, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.ini_node9, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node1, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node10, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node2, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node3, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node4, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node5, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node6, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node7, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node8, 'pdu_in'))
        self.msg_connect((self.shared_bus, 'pdu_out'), (self.rsp_node9, 'pdu_in'))
        self.msg_connect((self.strobe_node1, 'strobe'), (self.ini_node1, 'app_in'))
        self.msg_connect((self.strobe_node10, 'strobe'), (self.ini_node10, 'app_in'))
        self.msg_connect((self.strobe_node2, 'strobe'), (self.ini_node2, 'app_in'))
        self.msg_connect((self.strobe_node3, 'strobe'), (self.ini_node3, 'app_in'))
        self.msg_connect((self.strobe_node4, 'strobe'), (self.ini_node4, 'app_in'))
        self.msg_connect((self.strobe_node5, 'strobe'), (self.ini_node5, 'app_in'))
        self.msg_connect((self.strobe_node6, 'strobe'), (self.ini_node6, 'app_in'))
        self.msg_connect((self.strobe_node7, 'strobe'), (self.ini_node7, 'app_in'))
        self.msg_connect((self.strobe_node8, 'strobe'), (self.ini_node8, 'app_in'))
        self.msg_connect((self.strobe_node9, 'strobe'), (self.ini_node9, 'app_in'))
        self.connect((self.blocks_null_source_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.blocks_null_sink_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "test_10node")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_strobe_period_ms(self):
        return self.strobe_period_ms

    def set_strobe_period_ms(self, strobe_period_ms):
        self.strobe_period_ms = strobe_period_ms
        self.strobe_node1.set_period(self.strobe_period_ms)
        self.strobe_node2.set_period(self.strobe_period_ms)
        self.strobe_node3.set_period(self.strobe_period_ms)
        self.strobe_node4.set_period(self.strobe_period_ms)
        self.strobe_node5.set_period(self.strobe_period_ms)
        self.strobe_node6.set_period(self.strobe_period_ms)
        self.strobe_node7.set_period(self.strobe_period_ms)
        self.strobe_node8.set_period(self.strobe_period_ms)
        self.strobe_node9.set_period(self.strobe_period_ms)
        self.strobe_node10.set_period(self.strobe_period_ms)

    def get_drop_prob(self):
        return self.drop_prob

    def set_drop_prob(self, drop_prob):
        self.drop_prob = drop_prob
        self.shared_bus.p_drop = self.drop_prob




def main(top_block_cls=test_10node, options=None):

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
