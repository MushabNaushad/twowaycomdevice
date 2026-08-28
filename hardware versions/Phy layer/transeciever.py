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
from gnuradio import blocks, gr
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
from gnuradio import gr, pdu
import sip



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

        self.settings = Qt.QSettings("GNU Radio", "transeciever")

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
        self.samp_rate = samp_rate = 32e3
        self.pi = pi = 3.1415926
        self.nfilts = nfilts = 32
        self.alpha = alpha = 0.45
        self.QPSK_CONST = QPSK_CONST = digital.constellation_rect([-1-1j, -1+1j, 1+1j, 1-1j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.training_seq = training_seq = [1+1j, -1-1j, -1-1j, -1-1j, 1-1j, 1-1j, 1+1j, 1+1j]
        self.time_offset = time_offset = 1.00001
        self.sym_bw = sym_bw = .045
        self.rcc_taps = rcc_taps = firdes.root_raised_cosine(1, samp_rate,samp_rate/float(sps), alpha, (nfilts*sps))
        self.preamble_symbols = preamble_symbols = [1+1j, -1-1j, -1-1j, -1-1j, 1-1j, 1-1j, 1+1j, 1+1j]
        self.preamble_size = preamble_size = 20
        self.postamble_size = postamble_size = 8
        self.payload_size = payload_size = 64
        self.packets = packets = 20
        self.noise_volt = noise_volt = 0.1
        self.hdr = hdr = digital.header_format_default(digital.packet_utils.default_access_code, 0)
        self.frequency_offset = frequency_offset = 0.005
        self.fll_loop_bw = fll_loop_bw = 2 * pi * 0.005
        self.costas_bw = costas_bw = 0.0628
        self.amble = amble = [0xc0, 0xaf]
        self.adpt_alg = adpt_alg = digital.adaptive_algorithm_cma( QPSK_CONST, .0001, 1).base()
        self.SDR_CF = SDR_CF = 433.98e6
        self.CH_GAIN = CH_GAIN = 20
        self.BPSK_CONST = BPSK_CONST = digital.constellation_rect([-1,1], [0, 1],
        2, 2, 1, 1, 1).base()
        self.ADDR = ADDR = "ip:192.168.1.10"

        ##################################################
        # Blocks
        ##################################################

        self._noise_volt_range = qtgui.Range(0, 1, 0.1, 0.1, 200)
        self._noise_volt_win = qtgui.RangeWidget(self._noise_volt_range, self.set_noise_volt, "Channel : Noise Voltage", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._noise_volt_win)
        self._frequency_offset_range = qtgui.Range(-0.1, 0.1, 0.001, 0.005, 200)
        self._frequency_offset_win = qtgui.RangeWidget(self._frequency_offset_range, self.set_frequency_offset, "Channel: Frequency offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._frequency_offset_win)
        self._time_offset_range = qtgui.Range(0.999, 1.001, 0.000001, 1.00001, 200)
        self._time_offset_win = qtgui.RangeWidget(self._time_offset_range, self.set_time_offset, "Channel: Time Offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._time_offset_win)
        self.root_raised_cosine_filter_0 = filter.fir_filter_ccf(
            1,
            firdes.root_raised_cosine(
                1,
                samp_rate,
                (samp_rate/float(sps)),
                alpha,
                (11*sps)))
        self.qtgui_freq_sink_x_1 = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "", #name
            1,
            None # parent
        )
        self.qtgui_freq_sink_x_1.set_update_time(0.10)
        self.qtgui_freq_sink_x_1.set_y_axis((-140), 10)
        self.qtgui_freq_sink_x_1.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_1.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_1.enable_autoscale(False)
        self.qtgui_freq_sink_x_1.enable_grid(False)
        self.qtgui_freq_sink_x_1.set_fft_average(1.0)
        self.qtgui_freq_sink_x_1.enable_axis_labels(True)
        self.qtgui_freq_sink_x_1.enable_control_panel(False)
        self.qtgui_freq_sink_x_1.set_fft_window_normalized(False)



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
                self.qtgui_freq_sink_x_1.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_1.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_1.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_1.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_1.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_1_win = sip.wrapinstance(self.qtgui_freq_sink_x_1.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_freq_sink_x_1_win)
        self.pdu_tagged_stream_to_pdu_0 = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'packet_len')
        self.digital_symbol_sync_xx_0 = digital.symbol_sync_cc(
            digital.TED_SIGNAL_TIMES_SLOPE_ML,
            sps,
            sym_bw,
            1.0,
            1.0,
            1.5,
            1,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.digital_protocol_formatter_bb_0 = digital.protocol_formatter_bb(hdr, 'packet_len')
        self.digital_map_bb_0_0 = digital.map_bb([0,1])
        self.digital_fll_band_edge_cc_0 = digital.fll_band_edge_cc(sps, alpha, (2* sps +1), fll_loop_bw)
        self.digital_diff_decoder_bb_0_0 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.digital_costas_loop_cc_0_0 = digital.costas_loop_cc(costas_bw, BPSK_CONST.arity(), False)
        self.digital_correlate_access_code_xx_ts_0 = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code,
          2, 'packet_len')
        self.digital_constellation_modulator_0_0 = digital.generic_mod(
            constellation=BPSK_CONST,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=alpha,
            verbose=False,
            log=False,
            truncate=False)
        self.digital_constellation_decoder_cb_0_0 = digital.constellation_decoder_cb(BPSK_CONST)
        self.channels_channel_model_0 = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=0.0,
            epsilon=1.0,
            taps=[1.0],
            noise_seed=0,
            block_tags=False)
        self.blocks_vector_source_x_2 = blocks.vector_source_b([p +48 for p in range(packets) for _ in range(payload_size)], False, 1, )
        self.blocks_vector_source_x_0_0_0 = blocks.vector_source_b(amble, True, 1, [])
        self.blocks_vector_source_x_0_0 = blocks.vector_source_b(amble, True, 1, [])
        self.blocks_unpack_k_bits_bb_1 = blocks.unpack_k_bits_bb(8)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_char*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_tagged_stream_mux_0 = blocks.tagged_stream_mux(gr.sizeof_char*1, 'packet_len', 0)
        self.blocks_tag_gate_0 = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        self.blocks_tag_gate_0.set_single_key("")
        self.blocks_stream_to_tagged_stream_0_0_0_0_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, postamble_size, "packet_len")
        self.blocks_stream_to_tagged_stream_0_0_0_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, preamble_size, "packet_len")
        self.blocks_stream_to_tagged_stream_0_0_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, payload_size, "packet_len")
        self.blocks_repack_bits_bb_1 = blocks.repack_bits_bb(1, 8, 'packet_len', True, gr.GR_MSB_FIRST)
        self.blocks_repack_bits_bb_0 = blocks.repack_bits_bb(1, 8, "", False, gr.GR_LSB_FIRST)
        self.blocks_message_debug_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_copy_5 = blocks.copy(gr.sizeof_char*1)
        self.blocks_copy_5.set_enabled(True)
        self.blocks_copy_4 = blocks.copy(gr.sizeof_char*1)
        self.blocks_copy_4.set_enabled(True)
        self.blocks_copy_3_0 = blocks.copy(gr.sizeof_char*1)
        self.blocks_copy_3_0.set_enabled(True)
        self.blocks_copy_3 = blocks.copy(gr.sizeof_char*1)
        self.blocks_copy_3.set_enabled(True)
        self.blocks_copy_2 = blocks.copy(gr.sizeof_gr_complex*1)
        self.blocks_copy_2.set_enabled(True)
        self.blocks_copy_1_2 = blocks.copy(gr.sizeof_gr_complex*1)
        self.blocks_copy_1_2.set_enabled(True)
        self.blocks_copy_1_1 = blocks.copy(gr.sizeof_gr_complex*1)
        self.blocks_copy_1_1.set_enabled(True)
        self.analog_agc_xx_0 = analog.agc_cc((1e-4), 1.0, 1.0, 65536)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.pdu_tagged_stream_to_pdu_0, 'pdus'), (self.blocks_message_debug_0, 'print'))
        self.connect((self.analog_agc_xx_0, 0), (self.digital_fll_band_edge_cc_0, 0))
        self.connect((self.blocks_copy_1_1, 0), (self.analog_agc_xx_0, 0))
        self.connect((self.blocks_copy_1_2, 0), (self.root_raised_cosine_filter_0, 0))
        self.connect((self.blocks_copy_2, 0), (self.digital_costas_loop_cc_0_0, 0))
        self.connect((self.blocks_copy_3, 0), (self.blocks_tagged_stream_mux_0, 2))
        self.connect((self.blocks_copy_3, 0), (self.digital_protocol_formatter_bb_0, 0))
        self.connect((self.blocks_copy_3_0, 0), (self.pdu_tagged_stream_to_pdu_0, 0))
        self.connect((self.blocks_copy_4, 0), (self.blocks_repack_bits_bb_1, 0))
        self.connect((self.blocks_copy_5, 0), (self.blocks_repack_bits_bb_0, 0))
        self.connect((self.blocks_repack_bits_bb_0, 0), (self.blocks_stream_to_tagged_stream_0_0_0, 0))
        self.connect((self.blocks_repack_bits_bb_1, 0), (self.blocks_copy_3_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0_0_0, 0), (self.blocks_copy_3, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0_0_0_0, 0), (self.blocks_tagged_stream_mux_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0_0_0_0_0, 0), (self.blocks_tagged_stream_mux_0, 3))
        self.connect((self.blocks_tag_gate_0, 0), (self.channels_channel_model_0, 0))
        self.connect((self.blocks_tagged_stream_mux_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.digital_constellation_modulator_0_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_1, 0), (self.blocks_copy_5, 0))
        self.connect((self.blocks_vector_source_x_0_0, 0), (self.blocks_stream_to_tagged_stream_0_0_0_0, 0))
        self.connect((self.blocks_vector_source_x_0_0_0, 0), (self.blocks_stream_to_tagged_stream_0_0_0_0_0, 0))
        self.connect((self.blocks_vector_source_x_2, 0), (self.blocks_unpack_k_bits_bb_1, 0))
        self.connect((self.channels_channel_model_0, 0), (self.blocks_copy_1_1, 0))
        self.connect((self.digital_constellation_decoder_cb_0_0, 0), (self.digital_diff_decoder_bb_0_0, 0))
        self.connect((self.digital_constellation_modulator_0_0, 0), (self.blocks_tag_gate_0, 0))
        self.connect((self.digital_correlate_access_code_xx_ts_0, 0), (self.blocks_copy_4, 0))
        self.connect((self.digital_costas_loop_cc_0_0, 0), (self.digital_constellation_decoder_cb_0_0, 0))
        self.connect((self.digital_costas_loop_cc_0_0, 0), (self.qtgui_freq_sink_x_1, 0))
        self.connect((self.digital_diff_decoder_bb_0_0, 0), (self.digital_map_bb_0_0, 0))
        self.connect((self.digital_fll_band_edge_cc_0, 0), (self.blocks_copy_1_2, 0))
        self.connect((self.digital_map_bb_0_0, 0), (self.digital_correlate_access_code_xx_ts_0, 0))
        self.connect((self.digital_protocol_formatter_bb_0, 0), (self.blocks_tagged_stream_mux_0, 1))
        self.connect((self.digital_symbol_sync_xx_0, 0), (self.blocks_copy_2, 0))
        self.connect((self.root_raised_cosine_filter_0, 0), (self.digital_symbol_sync_xx_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "transeciever")
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
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/float(self.sps)), self.alpha, (11*self.sps)))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_rcc_taps(firdes.root_raised_cosine(1, self.samp_rate, self.samp_rate/float(self.sps), self.alpha, (self.nfilts*self.sps)))
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.qtgui_freq_sink_x_1.set_frequency_range(0, self.samp_rate)
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/float(self.sps)), self.alpha, (11*self.sps)))

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
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/float(self.sps)), self.alpha, (11*self.sps)))

    def get_QPSK_CONST(self):
        return self.QPSK_CONST

    def set_QPSK_CONST(self, QPSK_CONST):
        self.QPSK_CONST = QPSK_CONST

    def get_training_seq(self):
        return self.training_seq

    def set_training_seq(self, training_seq):
        self.training_seq = training_seq

    def get_time_offset(self):
        return self.time_offset

    def set_time_offset(self, time_offset):
        self.time_offset = time_offset

    def get_sym_bw(self):
        return self.sym_bw

    def set_sym_bw(self, sym_bw):
        self.sym_bw = sym_bw
        self.digital_symbol_sync_xx_0.set_loop_bandwidth(self.sym_bw)

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
        self.blocks_vector_source_x_2.set_data([p +48 for p in range(self.packets) for _ in range(self.payload_size)], )

    def get_packets(self):
        return self.packets

    def set_packets(self, packets):
        self.packets = packets
        self.blocks_vector_source_x_2.set_data([p +48 for p in range(self.packets) for _ in range(self.payload_size)], )

    def get_noise_volt(self):
        return self.noise_volt

    def set_noise_volt(self, noise_volt):
        self.noise_volt = noise_volt
        self.channels_channel_model_0.set_noise_voltage(self.noise_volt)

    def get_hdr(self):
        return self.hdr

    def set_hdr(self, hdr):
        self.hdr = hdr

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
        self.digital_costas_loop_cc_0_0.set_loop_bandwidth(self.costas_bw)

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

    def get_CH_GAIN(self):
        return self.CH_GAIN

    def set_CH_GAIN(self, CH_GAIN):
        self.CH_GAIN = CH_GAIN

    def get_BPSK_CONST(self):
        return self.BPSK_CONST

    def set_BPSK_CONST(self, BPSK_CONST):
        self.BPSK_CONST = BPSK_CONST
        self.digital_constellation_decoder_cb_0_0.set_constellation(self.BPSK_CONST)

    def get_ADDR(self):
        return self.ADDR

    def set_ADDR(self, ADDR):
        self.ADDR = ADDR




def main(top_block_cls=transeciever, options=None):

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
