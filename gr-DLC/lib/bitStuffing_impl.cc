/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "bitStuffing_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace DLC {

bitStuffing::sptr bitStuffing::make(uint8_t flag)
{
    return gnuradio::make_block_sptr<bitStuffing_impl>(flag);
}


/*
 * The private constructor
 */
bitStuffing_impl::bitStuffing_impl(uint8_t flag)
    : gr::block("bitStuffing",
                gr::io_signature::make(
                    0 /* min inputs */, 0 /* max inputs */, 0),
                gr::io_signature::make(
                    0 /* min outputs */, 0 /*max outputs */, 0))
{
    message_port_register_in(pmt::mp("in"));
    message_port_register_out(pmt::mp("out"));
    set_msg_handler(pmt::mp("in"),
    boost::bind(&bitStuffing_impl::stuff_bits, this, boost::placeholders::_1));
}


/*
 * Our virtual destructor.
 */
bitStuffing_impl::~bitStuffing_impl() {}

void bitStuffing_impl::forecast(int noutput_items, gr_vector_int& ninput_items_required)
{
    // Not using streaming inputs, so do nothing
}

int bitStuffing_impl::general_work(int noutput_items,
                                   gr_vector_int& ninput_items,
                                   gr_vector_const_void_star& input_items,
                                   gr_vector_void_star& output_items)
{
    // Not using streaming inputs/outputs, so return 0
    return 0;
}

void bitStuffing_impl::stuff_bits(pmt::pmt_t msg)
{
    // 1. Separate the PDU into metadata and data
    pmt::pmt_t meta = pmt::car(msg);
    pmt::pmt_t pmt_data = pmt::cdr(msg);

    // 2. Extract the vector of unpacked bits
    size_t len;
    const uint8_t* in_data = pmt::u8vector_elements(pmt_data, len);

    std::vector<uint8_t> out_buffer;
    
    // 3. Process bits to find 011111
    uint8_t shift_reg = 0; 

    for (size_t i = 0; i < len; i++) {
        uint8_t current_byte = in_data[i];
        
        // Process each of the 8 bits in the packed byte (MSB first)
        for (int b = 7; b >= 0; b--) {
            uint8_t bit = (current_byte >> b) & 0x01;
            out_buffer.push_back(bit);
            
            // Shift left by 1 and add the new bit
            shift_reg = (shift_reg << 1) | bit;

            // Mask to look at only the last 6 bits (0x3F is 00111111 in binary)
            // Check if those 6 bits equal 011111 (which is 0x1F in hex)
            if ((shift_reg & 0x3F) == 0x1F) {
                out_buffer.push_back(0); // Stuff the zero!
                
                // Push the newly stuffed zero into the shift register history
                shift_reg = (shift_reg << 1) | 0;
            }
        }
    }

    // 4. Publish the newly stuffed PDU
    pmt::pmt_t new_data = pmt::init_u8vector(out_buffer.size(), out_buffer.data());
    pmt::pmt_t new_pdu = pmt::cons(meta, new_data);
    
    message_port_pub(pmt::mp("out"), new_pdu);
}



} /* namespace DLC */
} /* namespace gr */
