#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Transmitter Test 02
# Author: mushab404
# GNU Radio version: 3.10.9.2

from PyQt5 import Qt
from gnuradio import qtgui
import os
import sys
sys.path.append(os.environ.get('GRC_HIER_PATH', os.path.expanduser('~/.grc_gnuradio')))

from PyQt5 import QtCore
from gnuradio import blocks
import numpy
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from transeciever_soft import transeciever_soft  # grc-generated hier_block
import sip



class test_02(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Transmitter Test 02", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Transmitter Test 02")
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

        self.settings = Qt.QSettings("GNU Radio", "test_02")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Variables
        ##################################################
        self.sync_delay = sync_delay = 0
        self.samp_rate = samp_rate = 32000
        self.fll_bw = fll_bw = 0.001
        self.costas_bw = costas_bw = 0.001
        self.ch_gain = ch_gain = 50

        ##################################################
        # Blocks
        ##################################################

        self._sync_delay_range = qtgui.Range(0, 200, 1, 0, 200)
        self._sync_delay_win = qtgui.RangeWidget(self._sync_delay_range, self.set_sync_delay, "Sync Delay", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._sync_delay_win)
        self._costas_bw_range = qtgui.Range(0.001, 0.1, 0.001, 0.001, 200)
        self._costas_bw_win = qtgui.RangeWidget(self._costas_bw_range, self.set_costas_bw, "Costas loop Bandwidth", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._costas_bw_win)
        self.transeciever_soft_0 = transeciever_soft(
            ADDR="192.168.1.1",
            CH_GAIN=30,
            SDR_CF='433M',
            alpha=0.45,
            costas_bw=2 * 3.1415926 * 0.01,
            fll_loop_bw=(2 * 3.1415926 * 0.001),
            frequency_offset=0,
            nfilts=32,
            noise_volt=0,
            samp_rate=32000,
            sps=4,
            time_offset=1,
        )
        self.qtgui_time_sink_x_0 = qtgui.time_sink_f(
            1024, #size
            samp_rate, #samp_rate
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0.set_update_time(0.10)
        self.qtgui_time_sink_x_0.set_y_axis(-1, 1)

        self.qtgui_time_sink_x_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0.enable_tags(True)
        self.qtgui_time_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0.enable_grid(False)
        self.qtgui_time_sink_x_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0.enable_stem_plot(False)


        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_time_sink_x_0_win)
        self.number_sink = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.number_sink.set_update_time(0.10)
        self.number_sink.set_title("Current BER")

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        units = ['', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.number_sink.set_min(i, -1)
            self.number_sink.set_max(i, 1)
            self.number_sink.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.number_sink.set_label(i, "Data {0}".format(i))
            else:
                self.number_sink.set_label(i, labels[i])
            self.number_sink.set_unit(i, units[i])
            self.number_sink.set_factor(i, factor[i])

        self.number_sink.enable_autoscale(False)
        self._number_sink_win = sip.wrapinstance(self.number_sink.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._number_sink_win)
        self._fll_bw_range = qtgui.Range(0.001, 0.1, 0.001, 0.001, 200)
        self._fll_bw_win = qtgui.RangeWidget(self._fll_bw_range, self.set_fll_bw, "FLL band edge: Loop Bandwidth", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._fll_bw_win)
        self._ch_gain_range = qtgui.Range(10, 65, 1, 50, 200)
        self._ch_gain_win = qtgui.RangeWidget(self._ch_gain_range, self.set_ch_gain, "Channel Gain", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._ch_gain_win)
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(8)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_char*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_sub_xx_0 = blocks.sub_ff(1)
        self.blocks_moving_average_xx_0 = blocks.moving_average_ff(int(10e5), (10e-5), 4000, 1)
        self.blocks_delay_0 = blocks.delay(gr.sizeof_char*1, sync_delay)
        self.blocks_copy_0 = blocks.copy(gr.sizeof_char*1)
        self.blocks_copy_0.set_enabled(True)
        self.blocks_char_to_float_0_0 = blocks.char_to_float(1, 1)
        self.blocks_char_to_float_0 = blocks.char_to_float(1, 1)
        self.blocks_abs_xx_0 = blocks.abs_ff(1)
        self.analog_random_source_x_0 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 256, 1000))), True)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_copy_0, 0))
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))
        self.connect((self.blocks_abs_xx_0, 0), (self.blocks_moving_average_xx_0, 0))
        self.connect((self.blocks_char_to_float_0, 0), (self.blocks_sub_xx_0, 1))
        self.connect((self.blocks_char_to_float_0, 0), (self.qtgui_time_sink_x_0, 0))
        self.connect((self.blocks_char_to_float_0_0, 0), (self.blocks_sub_xx_0, 0))
        self.connect((self.blocks_copy_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_delay_0, 0), (self.blocks_char_to_float_0_0, 0))
        self.connect((self.blocks_moving_average_xx_0, 0), (self.number_sink, 0))
        self.connect((self.blocks_sub_xx_0, 0), (self.blocks_abs_xx_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.transeciever_soft_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.blocks_delay_0, 0))
        self.connect((self.transeciever_soft_0, 0), (self.blocks_char_to_float_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "test_02")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sync_delay(self):
        return self.sync_delay

    def set_sync_delay(self, sync_delay):
        self.sync_delay = sync_delay
        self.blocks_delay_0.set_dly(int(self.sync_delay))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.qtgui_time_sink_x_0.set_samp_rate(self.samp_rate)

    def get_fll_bw(self):
        return self.fll_bw

    def set_fll_bw(self, fll_bw):
        self.fll_bw = fll_bw

    def get_costas_bw(self):
        return self.costas_bw

    def set_costas_bw(self, costas_bw):
        self.costas_bw = costas_bw

    def get_ch_gain(self):
        return self.ch_gain

    def set_ch_gain(self, ch_gain):
        self.ch_gain = ch_gain




def main(top_block_cls=test_02, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

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
