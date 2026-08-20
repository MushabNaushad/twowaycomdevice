#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: CDP transeciever
# Author: mushab404
# GNU Radio version: 3.10.9.2

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import blocks
import numpy
from gnuradio import channels
from gnuradio.filter import firdes
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import sip



class cdp_transeciever(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "CDP transeciever ", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("CDP transeciever ")
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

        self.settings = Qt.QSettings("GNU Radio", "cdp_transeciever")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Variables
        ##################################################
        self.sps = sps = 4
        self.samp_rate = samp_rate = 32000
        self.pi = pi = 3.1415926
        self.nfilts = nfilts = 32
        self.alpha = alpha = 0.45
        self.QPSK_CONST = QPSK_CONST = digital.constellation_rect([-1-1j, -1+1j, 1+1j, 1-1j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.time_offset = time_offset = 1
        self.rcc_taps = rcc_taps = firdes.root_raised_cosine(1, samp_rate,samp_rate/float(sps), alpha, (nfilts*sps))
        self.noise_volt = noise_volt = 0.5
        self.frequency_offset = frequency_offset = 0.025
        self.fll_loop_bw = fll_loop_bw = 2 * pi * 0.001
        self.costas_bw = costas_bw = 2 * pi * 0.01
        self.adpt_alg = adpt_alg = digital.adaptive_algorithm_cma( QPSK_CONST, .0001, 1).base()

        ##################################################
        # Blocks
        ##################################################

        self._noise_volt_range = qtgui.Range(0, 1, 0.1, 0.5, 200)
        self._noise_volt_win = qtgui.RangeWidget(self._noise_volt_range, self.set_noise_volt, "Channel : Noise Voltage", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._noise_volt_win)
        self._frequency_offset_range = qtgui.Range(-0.1, 0.1, 0.001, 0.025, 200)
        self._frequency_offset_win = qtgui.RangeWidget(self._frequency_offset_range, self.set_frequency_offset, "Channel: Frequency offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._frequency_offset_win)
        self._time_offset_range = qtgui.Range(0.999, 1.001, 0.000001, 1, 200)
        self._time_offset_win = qtgui.RangeWidget(self._time_offset_range, self.set_time_offset, "Channel: Time Offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._time_offset_win)
        self.qtgui_time_sink_x_0_1_0 = qtgui.time_sink_f(
            1024, #size
            samp_rate, #samp_rate
            "RX", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0_1_0.set_update_time(0.10)
        self.qtgui_time_sink_x_0_1_0.set_y_axis(-1, 1)

        self.qtgui_time_sink_x_0_1_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0_1_0.enable_tags(True)
        self.qtgui_time_sink_x_0_1_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0_1_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0_1_0.enable_grid(False)
        self.qtgui_time_sink_x_0_1_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0_1_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0_1_0.enable_stem_plot(False)


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
                self.qtgui_time_sink_x_0_1_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0_1_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0_1_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0_1_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0_1_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0_1_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0_1_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_1_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0_1_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_time_sink_x_0_1_0_win)
        self.qtgui_const_sink_x_0_1_0 = qtgui.const_sink_c(
            1024, #size
            "Costas", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_0_1_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0_1_0.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_0_1_0.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_0_1_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_0_1_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0_1_0.enable_grid(False)
        self.qtgui_const_sink_x_0_1_0.enable_axis_labels(True)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_0_1_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_0_1_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_0_1_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_0_1_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_0_1_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_0_1_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_0_1_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_0_1_0_win = sip.wrapinstance(self.qtgui_const_sink_x_0_1_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_const_sink_x_0_1_0_win)
        self.fft_filter_xxx_0 = filter.fft_filter_ccc(1, rcc_taps, 1)
        self.fft_filter_xxx_0.declare_sample_delay(0)
        self.digital_symbol_sync_xx_0 = digital.symbol_sync_cc(
            digital.TED_SIGNAL_TIMES_SLOPE_ML,
            sps,
            (alpha / 10),
            1.0,
            1.0,
            1.5,
            1,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.digital_map_bb_0 = digital.map_bb([0,1,3,2])
        self.digital_linear_equalizer_0 = digital.linear_equalizer(11, 1, adpt_alg, True, [ ], 'corr_est')
        self.digital_fll_band_edge_cc_0 = digital.fll_band_edge_cc(sps, alpha, (2* sps +1), fll_loop_bw)
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(costas_bw, QPSK_CONST.arity(), False)
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=QPSK_CONST,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=alpha,
            verbose=False,
            log=False,
            truncate=False)
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(QPSK_CONST)
        self.channels_channel_model_0 = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=0.0,
            epsilon=1.0,
            taps=[1.0],
            noise_seed=0,
            block_tags=False)
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(2)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_char*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_skiphead_0 = blocks.skiphead(gr.sizeof_gr_complex*1, int(samp_rate))
        self.blocks_char_to_float_0 = blocks.char_to_float(1, 1)
        self.analog_random_source_x_0 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 256, 1000))), True)
        self.analog_agc_xx_0 = analog.agc_cc((1e-4), 1.0, 1.0, 65536)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_agc_xx_0, 0), (self.digital_fll_band_edge_cc_0, 0))
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_char_to_float_0, 0), (self.qtgui_time_sink_x_0_1_0, 0))
        self.connect((self.blocks_skiphead_0, 0), (self.fft_filter_xxx_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.blocks_char_to_float_0, 0))
        self.connect((self.channels_channel_model_0, 0), (self.analog_agc_xx_0, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.channels_channel_model_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.qtgui_const_sink_x_0_1_0, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.digital_map_bb_0, 0))
        self.connect((self.digital_fll_band_edge_cc_0, 0), (self.blocks_skiphead_0, 0))
        self.connect((self.digital_linear_equalizer_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.digital_map_bb_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))
        self.connect((self.digital_symbol_sync_xx_0, 0), (self.digital_linear_equalizer_0, 0))
        self.connect((self.fft_filter_xxx_0, 0), (self.digital_symbol_sync_xx_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "cdp_transeciever")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_rcc_taps(firdes.root_raised_cosine(1, self.samp_rate, self.samp_rate/float(self.sps), self.alpha, (self.nfilts*self.sps)))
        self.digital_symbol_sync_xx_0.set_sps(self.sps)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_rcc_taps(firdes.root_raised_cosine(1, self.samp_rate, self.samp_rate/float(self.sps), self.alpha, (self.nfilts*self.sps)))
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.qtgui_time_sink_x_0_1_0.set_samp_rate(self.samp_rate)

    def get_pi(self):
        return self.pi

    def set_pi(self, pi):
        self.pi = pi
        self.set_costas_bw(2 * self.pi * 0.01)
        self.set_fll_loop_bw(2 * self.pi * 0.001)

    def get_nfilts(self):
        return self.nfilts

    def set_nfilts(self, nfilts):
        self.nfilts = nfilts
        self.set_rcc_taps(firdes.root_raised_cosine(1, self.samp_rate, self.samp_rate/float(self.sps), self.alpha, (self.nfilts*self.sps)))

    def get_alpha(self):
        return self.alpha

    def set_alpha(self, alpha):
        self.alpha = alpha
        self.set_rcc_taps(firdes.root_raised_cosine(1, self.samp_rate, self.samp_rate/float(self.sps), self.alpha, (self.nfilts*self.sps)))
        self.digital_symbol_sync_xx_0.set_loop_bandwidth((self.alpha / 10))

    def get_QPSK_CONST(self):
        return self.QPSK_CONST

    def set_QPSK_CONST(self, QPSK_CONST):
        self.QPSK_CONST = QPSK_CONST
        self.digital_constellation_decoder_cb_0.set_constellation(self.QPSK_CONST)

    def get_time_offset(self):
        return self.time_offset

    def set_time_offset(self, time_offset):
        self.time_offset = time_offset

    def get_rcc_taps(self):
        return self.rcc_taps

    def set_rcc_taps(self, rcc_taps):
        self.rcc_taps = rcc_taps
        self.fft_filter_xxx_0.set_taps(self.rcc_taps)

    def get_noise_volt(self):
        return self.noise_volt

    def set_noise_volt(self, noise_volt):
        self.noise_volt = noise_volt
        self.channels_channel_model_0.set_noise_voltage(self.noise_volt)

    def get_frequency_offset(self):
        return self.frequency_offset

    def set_frequency_offset(self, frequency_offset):
        self.frequency_offset = frequency_offset

    def get_fll_loop_bw(self):
        return self.fll_loop_bw

    def set_fll_loop_bw(self, fll_loop_bw):
        self.fll_loop_bw = fll_loop_bw
        self.digital_fll_band_edge_cc_0.set_loop_bandwidth(self.fll_loop_bw)

    def get_costas_bw(self):
        return self.costas_bw

    def set_costas_bw(self, costas_bw):
        self.costas_bw = costas_bw
        self.digital_costas_loop_cc_0.set_loop_bandwidth(self.costas_bw)

    def get_adpt_alg(self):
        return self.adpt_alg

    def set_adpt_alg(self, adpt_alg):
        self.adpt_alg = adpt_alg




def main(top_block_cls=cdp_transeciever, options=None):

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
