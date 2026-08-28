#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: PHY2 Test 05: BPSK FLL Band-Edge
# Author: mushab404
# Description: PHY2 Stage 05: BPSK with FLL Band-Edge Frequency Recovery
# GNU Radio version: 3.10.12.0

from gnuradio import analog
from gnuradio import blocks
from gnuradio import channels
from gnuradio.filter import firdes
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import threading




class bpsk_fll_band_edge(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "PHY2 Test 05: BPSK FLL Band-Edge", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.sps = sps = 4
        self.samp_rate = samp_rate = 32000
        self.nfilts = nfilts = 32
        self.alpha = alpha = 0.35
        self.sym_bw = sym_bw = 0.045
        self.rcc_taps = rcc_taps = firdes.root_raised_cosine(1.0, samp_rate,samp_rate/sps, alpha, (nfilts*sps))
        self.frequency_offset = frequency_offset = 0.025
        self.fll_loop_bw = fll_loop_bw = 2 * 3.14159265 * 0.005
        self.costas_bw = costas_bw = 0.0628
        self.BPSK_CONST = BPSK_CONST = digital.constellation_rect([-1+0j, 1+0j], [0, 1],
        2, 2, 2, 1, 1).base()

        ##################################################
        # Blocks
        ##################################################

        self.fft_filter_xxx_0 = filter.fft_filter_ccc(1, rcc_taps, 1)
        self.fft_filter_xxx_0.declare_sample_delay(0)
        self.digital_symbol_sync_xx_0 = digital.symbol_sync_cc(
            digital.TED_MUELLER_AND_MULLER,
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
        self.digital_fll_band_edge_cc_0 = digital.fll_band_edge_cc(sps, alpha, (2*sps+1), fll_loop_bw)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(costas_bw, 2, False)
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=BPSK_CONST,
            differential=False,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=alpha,
            verbose=False,
            log=False,
            truncate=False)
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(BPSK_CONST)
        self.channels_channel_model_0 = channels.channel_model(
            noise_voltage=0.0,
            frequency_offset=0.0,
            epsilon=1.0,
            taps=[1.0],
            noise_seed=0,
            block_tags=False)
        self.blocks_vector_source_x_0 = blocks.vector_source_b([0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x20, 0x57, 0x6F, 0x72, 0x6C, 0x64, 0x21], False, 1, [])
        self.blocks_vector_sink_x_0 = blocks.vector_sink_b(1, 1024)
        self.analog_agc_xx_0 = analog.agc_cc((1e-2), 1.0, 1.0, 65536)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_agc_xx_0, 0), (self.digital_fll_band_edge_cc_0, 0))
        self.connect((self.blocks_vector_source_x_0, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.channels_channel_model_0, 0), (self.analog_agc_xx_0, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.blocks_vector_sink_x_0, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.channels_channel_model_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_fll_band_edge_cc_0, 0), (self.fft_filter_xxx_0, 0))
        self.connect((self.digital_symbol_sync_xx_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.fft_filter_xxx_0, 0), (self.digital_symbol_sync_xx_0, 0))


    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_rcc_taps(firdes.root_raised_cosine(1.0, self.samp_rate, self.samp_rate/self.sps, self.alpha, (self.nfilts*self.sps)))
        self.digital_symbol_sync_xx_0.set_sps(self.sps)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_rcc_taps(firdes.root_raised_cosine(1.0, self.samp_rate, self.samp_rate/self.sps, self.alpha, (self.nfilts*self.sps)))

    def get_nfilts(self):
        return self.nfilts

    def set_nfilts(self, nfilts):
        self.nfilts = nfilts
        self.set_rcc_taps(firdes.root_raised_cosine(1.0, self.samp_rate, self.samp_rate/self.sps, self.alpha, (self.nfilts*self.sps)))

    def get_alpha(self):
        return self.alpha

    def set_alpha(self, alpha):
        self.alpha = alpha
        self.set_rcc_taps(firdes.root_raised_cosine(1.0, self.samp_rate, self.samp_rate/self.sps, self.alpha, (self.nfilts*self.sps)))

    def get_sym_bw(self):
        return self.sym_bw

    def set_sym_bw(self, sym_bw):
        self.sym_bw = sym_bw
        self.digital_symbol_sync_xx_0.set_loop_bandwidth(self.sym_bw)

    def get_rcc_taps(self):
        return self.rcc_taps

    def set_rcc_taps(self, rcc_taps):
        self.rcc_taps = rcc_taps
        self.fft_filter_xxx_0.set_taps(self.rcc_taps)

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

    def get_BPSK_CONST(self):
        return self.BPSK_CONST

    def set_BPSK_CONST(self, BPSK_CONST):
        self.BPSK_CONST = BPSK_CONST
        self.digital_constellation_decoder_cb_0.set_constellation(self.BPSK_CONST)




def main(top_block_cls=bpsk_fll_band_edge, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    tb.wait()


if __name__ == '__main__':
    main()
