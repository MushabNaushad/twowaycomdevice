/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "deStuffing_impl.h"
#include <gnuradio/io_signature.h>
#include <pmt/pmt.h>

namespace gr {
namespace DLC {

deStuffing::sptr deStuffing::make(uint8_t flag)
{
    return gnuradio::make_block_sptr<deStuffing_impl>(flag);
}


/*
 * The private constructor
 */
deStuffing_impl::deStuffing_impl(uint8_t flag)
    : gr::block("deStuffing",
                gr::io_signature::make(
                    0 /* min inputs */, 0 /* max inputs */, 0),
                gr::io_signature::make(
                    0 /* min outputs */, 0 /*max outputs */, 0))
{
    d_flag = flag;
    // These two lines MUST be here for Python to find the ports
    message_port_register_in(pmt::mp("in"));
    message_port_register_out(pmt::mp("out"));
    
    set_msg_handler(pmt::mp("in"),
    boost::bind(&deStuffing_impl::destuff_bits, this, boost::placeholders::_1));
}

/*
 * Our virtual destructor.
 */
deStuffing_impl::~deStuffing_impl() {}

void deStuffing_impl::forecast(int noutput_items, gr_vector_int& ninput_items_required)
{

}

int deStuffing_impl::general_work(int noutput_items,
                                  gr_vector_int& ninput_items,
                                  gr_vector_const_void_star& input_items,
                                  gr_vector_void_star& output_items)
{
    // Not using streaming inputs/outputs, so return 0
    return 0;
}

void deStuffing_impl::destuff_bits(pmt::pmt_t msg)
{
    // 1. Separate the PDU into metadata and data
    pmt::pmt_t meta = pmt::car(msg);
    pmt::pmt_t pmt_data = pmt::cdr(msg);

    // 2. Extract the vector of unpacked bits
    size_t len;
    const uint8_t* in_data = (const uint8_t*)pmt::uniform_vector_elements(pmt_data, len);

    std::vector<uint8_t> out_buffer;
    
    // 3. Process bits to remove stuffed 0s
    uint8_t shift_reg = 0; 

    for (size_t i = 0; i < len; i++) {
        uint8_t bit = in_data[i] & 0x01; // Ensure it's strictly 0 or 1

        // Check if the PREVIOUS 6 bits formed the 011111 pattern.
        // If they did, the CURRENT bit is the stuffed 0 and must be discarded.
        if ((shift_reg & 0x3F) == 0x1F) {
            
            // Update the shift register with the stuffed bit to match the 
            // state machine of the stuffer, but DO NOT push it to out_buffer.
            shift_reg = (shift_reg << 1) | bit; 
            continue; 
        }

        // Normal bit: push to output and update shift register
        out_buffer.push_back(bit);
        shift_reg = (shift_reg << 1) | bit;
    }

    // 4. Publish the destuffed PDU
    pmt::pmt_t new_data = pmt::init_u8vector(out_buffer.size(), out_buffer.data());
    pmt::pmt_t new_pdu = pmt::cons(meta, new_data);
    
    message_port_pub(pmt::mp("out"), new_pdu);
}

} /* namespace DLC */
} /* namespace gr */
