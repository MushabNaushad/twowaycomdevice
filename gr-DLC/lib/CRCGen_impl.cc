/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "CRCGen_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace DLC {

CRCGen::sptr CRCGen::make(int scheme)
{
    return gnuradio::make_block_sptr<CRCGen_impl>(scheme);
}

/*
 * The private constructor
 */
CRCGen_impl::CRCGen_impl(int scheme)
    : gr::block("CRCGen",
                gr::io_signature::make(0, 0, 0),
                gr::io_signature::make(0, 0, 0)),
      d_scheme(scheme)
{
    message_port_register_in(pmt::mp("in"));
    message_port_register_out(pmt::mp("out"));
    set_msg_handler(pmt::mp("in"),
                    boost::bind(&CRCGen_impl::generate_crc, this, boost::placeholders::_1));
}

/*
 * Our virtual destructor.
 */
CRCGen_impl::~CRCGen_impl() {}

void CRCGen_impl::generate_crc(pmt::pmt_t msg)
{
    pmt::pmt_t meta = pmt::car(msg);
    pmt::pmt_t pmt_data = pmt::cdr(msg);

    size_t len;
    const uint8_t* in_data = pmt::u8vector_elements(pmt_data, len);

    std::vector<uint8_t> out_buffer;

    // Unpack bytes to bits (MSB first)
    for (size_t i = 0; i < len; i++) {
        for (int b = 7; b >= 0; b--) {
            out_buffer.push_back((in_data[i] >> b) & 1);
        }
    }

    uint64_t poly = 0;
    if (d_scheme == 8) poly = 0x07;
    else if (d_scheme == 10) poly = 0x233;
    else if (d_scheme == 16) poly = 0x1021;
    else if (d_scheme == 32) poly = 0x04C11DB7;

    uint64_t crc = 0;
    for (uint8_t bit : out_buffer) {
        uint64_t top_bit = (crc >> (d_scheme - 1)) & 1;
        if (top_bit ^ bit) {
            crc = ((crc << 1) ^ poly) & ((1ULL << d_scheme) - 1);
        } else {
            crc = (crc << 1) & ((1ULL << d_scheme) - 1);
        }
    }

    // Append CRC to out_buffer
    for (int b = d_scheme - 1; b >= 0; b--) {
        out_buffer.push_back((crc >> b) & 1);
    }

    pmt::pmt_t new_data = pmt::init_u8vector(out_buffer.size(), out_buffer.data());
    pmt::pmt_t new_pdu = pmt::cons(meta, new_data);
    
    message_port_pub(pmt::mp("out"), new_pdu);
}

} /* namespace DLC */
} /* namespace gr */
