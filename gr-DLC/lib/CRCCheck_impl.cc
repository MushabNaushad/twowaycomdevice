/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "CRCCheck_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace DLC {

CRCCheck::sptr CRCCheck::make(int scheme)
{
    return gnuradio::make_block_sptr<CRCCheck_impl>(scheme);
}

/*
 * The private constructor
 */
CRCCheck_impl::CRCCheck_impl(int scheme)
    : gr::block("CRCCheck",
                gr::io_signature::make(0, 0, 0),
                gr::io_signature::make(0, 0, 0)),
      d_scheme(scheme)
{
    message_port_register_in(pmt::mp("in"));
    message_port_register_out(pmt::mp("out"));
    set_msg_handler(pmt::mp("in"),
                    boost::bind(&CRCCheck_impl::check_crc, this, boost::placeholders::_1));
}

/*
 * Our virtual destructor.
 */
CRCCheck_impl::~CRCCheck_impl() {}

void CRCCheck_impl::check_crc(pmt::pmt_t msg)
{
    pmt::pmt_t meta = pmt::car(msg);
    pmt::pmt_t pmt_data = pmt::cdr(msg);

    size_t len;
    const uint8_t* in_data = pmt::u8vector_elements(pmt_data, len);

    if (len < static_cast<size_t>(d_scheme)) {
        return; // Too short to even contain CRC
    }

    size_t data_len = len - d_scheme;

    uint64_t poly = 0;
    if (d_scheme == 8) poly = 0x07;
    else if (d_scheme == 10) poly = 0x233;
    else if (d_scheme == 16) poly = 0x1021;
    else if (d_scheme == 32) poly = 0x04C11DB7;

    uint64_t crc = 0;
    for (size_t i = 0; i < data_len; i++) {
        uint8_t bit = in_data[i] & 1;
        uint64_t top_bit = (crc >> (d_scheme - 1)) & 1;
        if (top_bit ^ bit) {
            crc = ((crc << 1) ^ poly) & ((1ULL << d_scheme) - 1);
        } else {
            crc = (crc << 1) & ((1ULL << d_scheme) - 1);
        }
    }

    // Extract received CRC
    uint64_t received_crc = 0;
    for (int i = 0; i < d_scheme; i++) {
        received_crc = (received_crc << 1) | (in_data[data_len + i] & 1);
    }

    if (crc == received_crc) {
        // Pack bits to bytes (MSB first)
        std::vector<uint8_t> out_buffer;
        
        for (size_t i = 0; i < data_len; i += 8) {
            uint8_t byte = 0;
            for (size_t b = 0; b < 8; b++) {
                if (i + b < data_len) {
                    byte |= ((in_data[i + b] & 1) << (7 - b));
                }
            }
            out_buffer.push_back(byte);
        }

        pmt::pmt_t new_data = pmt::init_u8vector(out_buffer.size(), out_buffer.data());
        pmt::pmt_t new_pdu = pmt::cons(meta, new_data);
        
        message_port_pub(pmt::mp("out"), new_pdu);
    }
}

} /* namespace DLC */
} /* namespace gr */
