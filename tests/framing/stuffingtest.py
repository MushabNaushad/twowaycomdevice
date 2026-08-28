#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: stuffingtest
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import DLC
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
from gnuradio import gr, pdu
from gnuradio import pdu
import threading



class stuffingtest(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "stuffingtest", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("stuffingtest")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "stuffingtest")

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

        self.pdu_tagged_stream_to_pdu_1 = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'packet_len')
        self.pdu_tagged_stream_to_pdu_0 = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'packet_len')
        self.pdu_random_pdu_0 = pdu.random_pdu(1, 2, 0xFF, 1)
        self.pdu_pdu_to_tagged_stream_1 = pdu.pdu_to_tagged_stream(gr.types.byte_t, 'packet_len')
        self.blocks_vector_source_x_0 = blocks.vector_source_b((1,0,1,1,0,1,0,1,1,1,1,1,1,0,1,1,0), False, 1, [])
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_char*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_stream_to_tagged_stream_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, 17, "packet_len")
        self.blocks_repack_bits_bb_0 = blocks.repack_bits_bb(8, 1, "packet_len", False, gr.GR_MSB_FIRST)
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.intern("TEST"), 10000)
        self.blocks_message_debug_0_1_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_message_debug_0_1 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_message_debug_0_0_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_message_debug_0_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_message_debug_0 = blocks.message_debug(True, gr.log_levels.info)
        self.DLC_removeFlags_0 = DLC.removeFlags(flag)
        self.DLC_deStuffing_0 = DLC.deStuffing(126)
        self.DLC_bitStuffing_0 = DLC.bitStuffing(126)
        self.DLC_addFlags_0 = DLC.addFlags(flag, True)
        self.DLC_CRCGen_0 = DLC.CRCGen(8)
        self.DLC_CRCCheck_0 = DLC.CRCCheck(8)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.DLC_CRCCheck_0, 'out'), (self.pdu_pdu_to_tagged_stream_1, 'pdus'))
        self.msg_connect((self.DLC_CRCGen_0, 'out'), (self.DLC_bitStuffing_0, 'in'))
        self.msg_connect((self.DLC_addFlags_0, 'out'), (self.DLC_removeFlags_0, 'pdu_in'))
        self.msg_connect((self.DLC_bitStuffing_0, 'out'), (self.DLC_addFlags_0, 'in'))
        self.msg_connect((self.DLC_deStuffing_0, 'out'), (self.DLC_CRCCheck_0, 'in'))
        self.msg_connect((self.DLC_deStuffing_0, 'out'), (self.blocks_message_debug_0_0, 'print'))
        self.msg_connect((self.DLC_removeFlags_0, 'pdu_out'), (self.DLC_deStuffing_0, 'in'))
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.pdu_random_pdu_0, 'generate'))
        self.msg_connect((self.pdu_random_pdu_0, 'pdus'), (self.DLC_CRCGen_0, 'in'))
        self.msg_connect((self.pdu_tagged_stream_to_pdu_1, 'pdus'), (self.blocks_message_debug_0_1, 'print'))
        self.connect((self.blocks_repack_bits_bb_0, 0), (self.pdu_tagged_stream_to_pdu_1, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0, 0), (self.pdu_tagged_stream_to_pdu_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.blocks_stream_to_tagged_stream_0, 0))
        self.connect((self.blocks_vector_source_x_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.pdu_pdu_to_tagged_stream_1, 0), (self.blocks_repack_bits_bb_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "stuffingtest")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)

    def get_flag(self):
        return self.flag

    def set_flag(self, flag):
        self.flag = flag




def main(top_block_cls=stuffingtest, options=None):

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
