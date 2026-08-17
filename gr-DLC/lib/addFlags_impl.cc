/* -*- c++ -*- */
/*
 * Copyright 2026 maduwage.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "addFlags_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace DLC {


addFlags::sptr addFlags::make(uint8_t flag, bool bothEnds)
{
    return gnuradio::make_block_sptr<addFlags_impl>(flag, bothEnds);
}


/*
 * The private constructor
 */
addFlags_impl::addFlags_impl(uint8_t flag, bool bothEnds)
    : gr::block("addFlags",
                gr::io_signature::make(0,0,0),
                gr::io_signature::make(0,0,0)),
    d_flag(flag),
    d_bothEnds(bothEnds)
{
    message_port_register_in(pmt::mp("in"));
    message_port_register_out(pmt::mp("out"));
    set_msg_handler(pmt::mp("in"),
    boost::bind(&addFlags_impl::process_packet, this, boost::placeholders::_1));
}

/*
 * Our virtual destructor.
 */
addFlags_impl::~addFlags_impl() {}

void addFlags_impl::process_packet(pmt::pmt_t msg)
{
    // 1. Separate the PDU into metadata and data
    pmt::pmt_t meta = pmt::car(msg);
    pmt::pmt_t pmt_data = pmt::cdr(msg);

    // 2. Extract the raw UNPACKED bits from the PMT data vector
    // 'len' now represents the number of incoming bits, not packed bytes
    size_t len;
    const uint8_t* raw_data = (const uint8_t*)pmt::uniform_vector_elements(pmt_data, len);

    // 3. Create a temporary vector to hold all bits before packing
    std::vector<uint8_t> unpacked_bits;

    // Prepend the opening flag (Convert d_flag byte into 8 bits, MSB first)
    for (int i = 7; i >= 0; --i) {
        unpacked_bits.push_back((d_flag >> i) & 1);
    }

    // Insert the actual payload (which is already unpacked bits)
    // We bitwise AND with 1 just to be strictly safe that values are only 0 or 1
    for (size_t i = 0; i < len; ++i) {
        unpacked_bits.push_back(raw_data[i] & 1);
    }

    // Append the closing flag if requested
    if (d_bothEnds) {
        for (int i = 7; i >= 0; --i) {
            unpacked_bits.push_back((d_flag >> i) & 1);
        }
    }

    // 4. Pad with 0s until the total bit count is a multiple of 8
    while (unpacked_bits.size() % 8 != 0) {
        unpacked_bits.push_back(0);
    }

    // 5. Pack the array of bits into an array of bytes
    std::vector<uint8_t> packed_bytes;
    for (size_t i = 0; i < unpacked_bits.size(); i += 8) {
        uint8_t current_byte = 0;
        for (int j = 0; j < 8; ++j) {
            // Shift the bit into the correct position (MSB first)
            current_byte |= (unpacked_bits[i + j] << (7 - j));
        }
        packed_bytes.push_back(current_byte);
    }

    // 6. Convert the C++ packed byte vector back into a PMT u8vector
    pmt::pmt_t new_pmt_data = pmt::init_u8vector(packed_bytes.size(), packed_bytes.data());

    // 7. Repack the PDU pair and publish
    message_port_pub(pmt::mp("out"), pmt::cons(meta, new_pmt_data));
}

} /* namespace DLC */
} /* namespace gr */
