import numpy as np
from gnuradio import gr
import pmt

class ChannelEstimatorSNR(gr.sync_block):
    """
    Estimates SNR from complex symbols and outputs recommended MCS (0 or 1).
    Uses a dual-threshold hysteresis to avoid ping-ponging.
    """
    def __init__(self, snr_low_thresh_db=7.0, snr_high_thresh_db=10.0, avg_samples=2000):
        gr.sync_block.__init__(
            self,
            name="Channel Estimator & MCS Decision",
            in_sig=[np.complex64],
            out_sig=[]
        )
        self.low_thresh = float(snr_low_thresh_db)
        self.high_thresh = float(snr_high_thresh_db)
        self.avg_samples = int(avg_samples)

        self.current_mcs = 0  # Default BPSK
        self.symbol_buf = []

        self.message_port_register_out(pmt.intern("tx_mcs_feedback"))

    def work(self, input_items, output_items):
        symbols = input_items[0]
        self.symbol_buf.extend(symbols)

        while len(self.symbol_buf) >= self.avg_samples:
            chunk = np.array(self.symbol_buf[:self.avg_samples], dtype=np.complex64)
            self.symbol_buf = self.symbol_buf[self.avg_samples:]

            # Normalize signal power
            sig_power = np.mean(np.abs(chunk)**2)
            if sig_power < 1e-6:
                continue

            # Hard-decision slicing on BPSK/QPSK coordinates (+-1, +-1j)
            ref_i = np.sign(chunk.real)
            ref_q = np.sign(chunk.imag)
            ref_symbols = (ref_i + 1j * ref_q) / np.sqrt(2)

            # Error Vector Magnitude (EVM) noise estimate
            error = chunk - ref_symbols
            noise_power = np.mean(np.abs(error)**2)

            if noise_power > 0:
                snr_linear = sig_power / noise_power
                snr_db = 10.0 * np.log10(max(snr_linear, 1e-3))
            else:
                snr_db = 30.0

            # Hysteresis switching logic
            new_mcs = self.current_mcs
            if self.current_mcs == 0 and snr_db > self.high_thresh:
                new_mcs = 1  # Upgrade to QPSK
            elif self.current_mcs == 1 and snr_db < self.low_thresh:
                new_mcs = 0  # Downgrade to BPSK

            if new_mcs != self.current_mcs:
                self.current_mcs = new_mcs
                self.message_port_pub(pmt.intern("tx_mcs_feedback"), pmt.from_long(self.current_mcs))

        return len(symbols)
