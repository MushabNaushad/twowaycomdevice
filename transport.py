#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Transport Layer (SR-ARQ)
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import pdu
import pmt
from gnuradio import zeromq
import os
import threading
import transport_epy_block_0 as epy_block_0  # embedded python block
import transport_epy_block_1 as epy_block_1  # embedded python block
import transport_epy_block_2 as epy_block_2  # embedded python block



class transport(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Transport Layer (SR-ARQ)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Transport Layer (SR-ARQ)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "transport")

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
        self.tl_zmq_tx_port = tl_zmq_tx_port = int(os.environ.get('TL_ZMQ_TX_PORT', '52001'))
        self.tl_zmq_rx_port = tl_zmq_rx_port = int(os.environ.get('TL_ZMQ_RX_PORT', '52002'))
        self.tl_rto_ms = tl_rto_ms = int(os.environ.get('TL_RTO_MS', '500'))
        self.tl_role = tl_role = os.environ.get('TL_ROLE', 'initiator')
        self.tl_mtu = tl_mtu = int(os.environ.get('TL_MTU', '200'))
        self.tl_max_retries = tl_max_retries = int(os.environ.get('TL_MAX_RETRIES', '10'))
        self.tl_m = tl_m = int(os.environ.get('TL_M', '4'))
        self.tl_local_port = tl_local_port = int(os.environ.get('TL_LOCAL_PORT', '0'))
        self.tl_local_addr = tl_local_addr = int(os.environ.get('TL_LOCAL_ADDR', '0'))
        self.samp_rate = samp_rate = 32000

        ##################################################
        # Blocks
        ##################################################

        self.zeromq_push_msg_sink_0 = zeromq.push_msg_sink("tcp://127.0.0.1:" + str(tl_zmq_rx_port), 100, True)
        self.zeromq_pull_msg_source_0 = zeromq.pull_msg_source("tcp://127.0.0.1:" + str(tl_zmq_tx_port), 100, True)
        self.pdu_pdu_filter_0_0 = pdu.pdu_filter(pmt.intern("dst_addr"), pmt.from_uint64(0), False)
        self.pdu_pdu_filter_0 = pdu.pdu_filter(pmt.intern("dst_addr"), pmt.from_uint64(tl_local_addr), False)
        self.epy_block_2 = epy_block_2.blk()
        self.epy_block_1 = epy_block_1.blk(m=tl_m, rto_ms=tl_rto_ms, node_role=tl_role, mtu_bytes=tl_mtu, local_addr=tl_local_addr, local_port=tl_local_port, max_retries=tl_max_retries)
        self.epy_block_0 = epy_block_0.blk()


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.epy_block_0, 'pdus'), (self.pdu_pdu_filter_0, 'pdus'))
        self.msg_connect((self.epy_block_0, 'pdus'), (self.pdu_pdu_filter_0_0, 'pdus'))
        self.msg_connect((self.epy_block_1, 'pdu_out'), (self.epy_block_2, 'pdus'))
        self.msg_connect((self.epy_block_1, 'app_out'), (self.zeromq_push_msg_sink_0, 'in'))
        self.msg_connect((self.pdu_pdu_filter_0, 'pdus'), (self.epy_block_1, 'pdu_in'))
        self.msg_connect((self.pdu_pdu_filter_0_0, 'pdus'), (self.epy_block_1, 'pdu_in'))
        self.msg_connect((self.zeromq_pull_msg_source_0, 'out'), (self.epy_block_1, 'app_in'))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "transport")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_tl_zmq_tx_port(self):
        return self.tl_zmq_tx_port

    def set_tl_zmq_tx_port(self, tl_zmq_tx_port):
        self.tl_zmq_tx_port = tl_zmq_tx_port

    def get_tl_zmq_rx_port(self):
        return self.tl_zmq_rx_port

    def set_tl_zmq_rx_port(self, tl_zmq_rx_port):
        self.tl_zmq_rx_port = tl_zmq_rx_port

    def get_tl_rto_ms(self):
        return self.tl_rto_ms

    def set_tl_rto_ms(self, tl_rto_ms):
        self.tl_rto_ms = tl_rto_ms

    def get_tl_role(self):
        return self.tl_role

    def set_tl_role(self, tl_role):
        self.tl_role = tl_role

    def get_tl_mtu(self):
        return self.tl_mtu

    def set_tl_mtu(self, tl_mtu):
        self.tl_mtu = tl_mtu

    def get_tl_max_retries(self):
        return self.tl_max_retries

    def set_tl_max_retries(self, tl_max_retries):
        self.tl_max_retries = tl_max_retries
        self.epy_block_1.max_retries = self.tl_max_retries

    def get_tl_m(self):
        return self.tl_m

    def set_tl_m(self, tl_m):
        self.tl_m = tl_m
        self.epy_block_1.m = self.tl_m

    def get_tl_local_port(self):
        return self.tl_local_port

    def set_tl_local_port(self, tl_local_port):
        self.tl_local_port = tl_local_port
        self.epy_block_1.local_port = self.tl_local_port

    def get_tl_local_addr(self):
        return self.tl_local_addr

    def set_tl_local_addr(self, tl_local_addr):
        self.tl_local_addr = tl_local_addr
        self.epy_block_1.local_addr = self.tl_local_addr
        self.pdu_pdu_filter_0.set_val(pmt.from_uint64(self.tl_local_addr))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate




def main(top_block_cls=transport, options=None):

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
