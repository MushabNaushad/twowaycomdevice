#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: CDP transeciever
# Author: mushab404
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import blocks
import numpy
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
from gnuradio import iio
import sip
import threading



class transeciever(gr.top_block, Qt.QWidget):

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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "transeciever")

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
        self.sps = sps = 4
        self.samp_rate = samp_rate = 2.5e6
        self.pi = pi = 3.1415926
        self.nfilts = nfilts = 32
        self.alpha = alpha = 0.45
        self.QPSK_CONST = QPSK_CONST = digital.constellation_rect([-1-1j, -1+1j, 1+1j, 1-1j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.training_seq = training_seq = [1+1j, -1-1j, -1-1j, -1-1j, 1-1j, 1-1j, 1+1j, 1+1j]
        self.sym_bw = sym_bw = .045
        self.rcc_taps = rcc_taps = firdes.root_raised_cosine(1, samp_rate,samp_rate/float(sps), alpha, (nfilts*sps))
        self.preamble_symbols = preamble_symbols = [1+1j, -1-1j, -1-1j, -1-1j, 1-1j, 1-1j, 1+1j, 1+1j]
        self.preamble_size = preamble_size = 20
        self.postamble_size = postamble_size = 8
        self.payload_size = payload_size = 64
        self.packets = packets = 300
        self.hdr = hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0)
        self.fll_loop_bw = fll_loop_bw = 2 * pi * 0.005
        self.costas_bw = costas_bw = 0.0628
        self.amble = amble = [0xc0, 0xaf]
        self.adpt_alg = adpt_alg = digital.adaptive_algorithm_cma( QPSK_CONST, .0001, 1).base()
        self.SDR_CF = SDR_CF = 443e6
        self.CH_GAIN = CH_GAIN = 20
        self.ADDR = ADDR = "ip:192.168.1.10"

        ##################################################
        # Blocks
        ##################################################

        self.qtgui_freq_sink_x_0 = qtgui.freq_sink_c(
            2048, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "", #name
            1,
            None # parent
        )
        self.qtgui_freq_sink_x_0.set_update_time(0.10)
        self.qtgui_freq_sink_x_0.set_y_axis((-140), 10)
        self.qtgui_freq_sink_x_0.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_0.enable_autoscale(False)
        self.qtgui_freq_sink_x_0.enable_grid(False)
        self.qtgui_freq_sink_x_0.set_fft_average(1.0)
        self.qtgui_freq_sink_x_0.enable_axis_labels(True)
        self.qtgui_freq_sink_x_0.enable_control_panel(False)
        self.qtgui_freq_sink_x_0.set_fft_window_normalized(False)



        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_0_win = sip.wrapinstance(self.qtgui_freq_sink_x_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_freq_sink_x_0_win)
        self.iio_pluto_sink_0 = iio.fmcomms2_sink_fc32(ADDR if ADDR else iio.get_pluto_uri(), [True, True], 32768, False)
        self.iio_pluto_sink_0.set_len_tag_key('')
        self.iio_pluto_sink_0.set_bandwidth(20000000)
        self.iio_pluto_sink_0.set_frequency(int(SDR_CF))
        self.iio_pluto_sink_0.set_samplerate(int(samp_rate))
        self.iio_pluto_sink_0.set_attenuation(0, CH_GAIN)
        self.iio_pluto_sink_0.set_filter_params('Auto', '', 0, 0)
        self.digital_protocol_formatter_bb_0 = digital.protocol_formatter_bb(hdr, 'packet_len')
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=QPSK_CONST,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=alpha,
            verbose=False,
            log=False,
            truncate=False)
        self.blocks_vector_source_x_0_0_0 = blocks.vector_source_b(amble, True, 1, [])
        self.blocks_vector_source_x_0_0 = blocks.vector_source_b(amble, True, 1, [])
        self.blocks_unpack_k_bits_bb_1 = blocks.unpack_k_bits_bb(8)
        self.blocks_tagged_stream_mux_0 = blocks.tagged_stream_mux(gr.sizeof_char*1, 'packet_len', 0)
        self.blocks_tag_gate_0 = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        self.blocks_tag_gate_0.set_single_key("")
        self.blocks_stream_to_tagged_stream_0_0_0_0_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, postamble_size, "packet_len")
        self.blocks_stream_to_tagged_stream_0_0_0_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, preamble_size, "packet_len")
        self.blocks_stream_to_tagged_stream_0_0_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, payload_size, "packet_len")
        self.blocks_repack_bits_bb_0 = blocks.repack_bits_bb(1, 8, "", False, gr.GR_LSB_FIRST)
        self.blocks_copy_5 = blocks.copy(gr.sizeof_char*1)
        self.blocks_copy_5.set_enabled(True)
        self.blocks_copy_3 = blocks.copy(gr.sizeof_char*1)
        self.blocks_copy_3.set_enabled(True)
        self.blocks_copy_0 = blocks.copy(gr.sizeof_char*1)
        self.blocks_copy_0.set_enabled(True)
        self.analog_random_source_x_1 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 256, 1000))), True)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_random_source_x_1, 0), (self.blocks_unpack_k_bits_bb_1, 0))
        self.connect((self.blocks_copy_0, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.blocks_copy_3, 0), (self.blocks_tagged_stream_mux_0, 2))
        self.connect((self.blocks_copy_3, 0), (self.digital_protocol_formatter_bb_0, 0))
        self.connect((self.blocks_copy_5, 0), (self.blocks_repack_bits_bb_0, 0))
        self.connect((self.blocks_repack_bits_bb_0, 0), (self.blocks_stream_to_tagged_stream_0_0_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0_0_0, 0), (self.blocks_copy_3, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0_0_0_0, 0), (self.blocks_tagged_stream_mux_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0_0_0_0_0, 0), (self.blocks_tagged_stream_mux_0, 3))
        self.connect((self.blocks_tag_gate_0, 0), (self.iio_pluto_sink_0, 0))
        self.connect((self.blocks_tag_gate_0, 0), (self.qtgui_freq_sink_x_0, 0))
        self.connect((self.blocks_tagged_stream_mux_0, 0), (self.blocks_copy_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_1, 0), (self.blocks_copy_5, 0))
        self.connect((self.blocks_vector_source_x_0_0, 0), (self.blocks_stream_to_tagged_stream_0_0_0_0, 0))
        self.connect((self.blocks_vector_source_x_0_0_0, 0), (self.blocks_stream_to_tagged_stream_0_0_0_0_0, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.blocks_tag_gate_0, 0))
        self.connect((self.digital_protocol_formatter_bb_0, 0), (self.blocks_tagged_stream_mux_0, 1))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "transeciever")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_rcc_taps(firdes.root_raised_cosine(1, self.samp_rate, self.samp_rate/float(self.sps), self.alpha, (self.nfilts*self.sps)))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_rcc_taps(firdes.root_raised_cosine(1, self.samp_rate, self.samp_rate/float(self.sps), self.alpha, (self.nfilts*self.sps)))
        self.iio_pluto_sink_0.set_samplerate(int(self.samp_rate))
        self.qtgui_freq_sink_x_0.set_frequency_range(0, self.samp_rate)

    def get_pi(self):
        return self.pi

    def set_pi(self, pi):
        self.pi = pi
        self.set_fll_loop_bw(2 * self.pi * 0.005)

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

    def get_QPSK_CONST(self):
        return self.QPSK_CONST

    def set_QPSK_CONST(self, QPSK_CONST):
        self.QPSK_CONST = QPSK_CONST

    def get_training_seq(self):
        return self.training_seq

    def set_training_seq(self, training_seq):
        self.training_seq = training_seq

    def get_sym_bw(self):
        return self.sym_bw

    def set_sym_bw(self, sym_bw):
        self.sym_bw = sym_bw

    def get_rcc_taps(self):
        return self.rcc_taps

    def set_rcc_taps(self, rcc_taps):
        self.rcc_taps = rcc_taps

    def get_preamble_symbols(self):
        return self.preamble_symbols

    def set_preamble_symbols(self, preamble_symbols):
        self.preamble_symbols = preamble_symbols

    def get_preamble_size(self):
        return self.preamble_size

    def set_preamble_size(self, preamble_size):
        self.preamble_size = preamble_size
        self.blocks_stream_to_tagged_stream_0_0_0_0.set_packet_len(self.preamble_size)
        self.blocks_stream_to_tagged_stream_0_0_0_0.set_packet_len_pmt(self.preamble_size)

    def get_postamble_size(self):
        return self.postamble_size

    def set_postamble_size(self, postamble_size):
        self.postamble_size = postamble_size
        self.blocks_stream_to_tagged_stream_0_0_0_0_0.set_packet_len(self.postamble_size)
        self.blocks_stream_to_tagged_stream_0_0_0_0_0.set_packet_len_pmt(self.postamble_size)

    def get_payload_size(self):
        return self.payload_size

    def set_payload_size(self, payload_size):
        self.payload_size = payload_size
        self.blocks_stream_to_tagged_stream_0_0_0.set_packet_len(self.payload_size)
        self.blocks_stream_to_tagged_stream_0_0_0.set_packet_len_pmt(self.payload_size)

    def get_packets(self):
        return self.packets

    def set_packets(self, packets):
        self.packets = packets

    def get_hdr(self):
        return self.hdr

    def set_hdr(self, hdr):
        self.hdr = hdr
        self.digital_protocol_formatter_bb_0.set_header_format(self.hdr)

    def get_fll_loop_bw(self):
        return self.fll_loop_bw

    def set_fll_loop_bw(self, fll_loop_bw):
        self.fll_loop_bw = fll_loop_bw

    def get_costas_bw(self):
        return self.costas_bw

    def set_costas_bw(self, costas_bw):
        self.costas_bw = costas_bw

    def get_amble(self):
        return self.amble

    def set_amble(self, amble):
        self.amble = amble
        self.blocks_vector_source_x_0_0.set_data(self.amble, [])
        self.blocks_vector_source_x_0_0_0.set_data(self.amble, [])

    def get_adpt_alg(self):
        return self.adpt_alg

    def set_adpt_alg(self, adpt_alg):
        self.adpt_alg = adpt_alg

    def get_SDR_CF(self):
        return self.SDR_CF

    def set_SDR_CF(self, SDR_CF):
        self.SDR_CF = SDR_CF
        self.iio_pluto_sink_0.set_frequency(int(self.SDR_CF))

    def get_CH_GAIN(self):
        return self.CH_GAIN

    def set_CH_GAIN(self, CH_GAIN):
        self.CH_GAIN = CH_GAIN
        self.iio_pluto_sink_0.set_attenuation(0,self.CH_GAIN)

    def get_ADDR(self):
        return self.ADDR

    def set_ADDR(self, ADDR):
        self.ADDR = ADDR




def main(top_block_cls=transeciever, options=None):

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
