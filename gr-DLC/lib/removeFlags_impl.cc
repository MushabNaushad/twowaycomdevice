/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "removeFlags_impl.h"
#include <gnuradio/io_signature.h>
#include <pmt/pmt.h>

namespace gr {
namespace DLC {

using input_type = uint8_t;

removeFlags::sptr removeFlags::make(uint8_t flag)
{
    return gnuradio::make_block_sptr<removeFlags_impl>(flag);
}

/*
 * The private constructor
 */
removeFlags_impl::removeFlags_impl(uint8_t flag)
    : gr::block("removeFlags",
                gr::io_signature::make(
                    1 /* min inputs */, 1 /* max inputs */, sizeof(input_type)),
                gr::io_signature::make(
                    0 /* min outputs */, 0 /*max outputs */, 0)),
      d_flag(flag),          // CRITICAL: Assign the parameter to the state variable
      d_shift_reg(0),        // Initialize the shift register to zero
      d_in_frame(false)      // Start safely outside of a frame
{
    message_port_register_out(pmt::mp("pdu_out"));
}

/*
 * Our virtual destructor.
 */
removeFlags_impl::~removeFlags_impl() {}

void removeFlags_impl::forecast(int noutput_items, gr_vector_int& ninput_items_required)
{
    // Tell the scheduler we need at least 1 input byte to do any work
    ninput_items_required[0] = 1;
}

int removeFlags_impl::general_work(int noutput_items,
                                   gr_vector_int& ninput_items,
                                   gr_vector_const_void_star& input_items,
                                   gr_vector_void_star& output_items)
{
    auto in = static_cast<const uint8_t*>(input_items[0]);
    int n_input = ninput_items[0];

    // 1. Iterate through each packed byte in the input chunk
    for (int i = 0; i < n_input; i++) {
        uint8_t current_byte = in[i];
        
        // 2. Extract each bit (Assuming MSB-first)
        for (int b = 7; b >= 0; b--) {
            uint8_t bit = (current_byte >> b) & 0x01;
            
            // Shift the new bit into our 8-bit history register
            d_shift_reg = ((d_shift_reg << 1) | bit);

            // Check if the last 8 bits match your flag
            if (d_shift_reg == d_flag) {
                
                if (!d_in_frame) {
                    // --- START FLAG DETECTED ---
                    d_in_frame = true;
                    d_pdu_buffer.clear(); 
                } else {
                    // --- END FLAG DETECTED ---
                    d_in_frame = false;
                    
                    // Remove the 7 bits of the end flag that we accidentally 
                    // stored in the payload buffer before realizing it was a flag.
                    if (d_pdu_buffer.size() >= 7) {
                        d_pdu_buffer.erase(d_pdu_buffer.end() - 7, d_pdu_buffer.end());
                    }

                    // --- PUBLISH UNPACKED PDU ---
                    if (!d_pdu_buffer.empty()) {
                        pmt::pmt_t meta = pmt::make_dict();
                        
                        // d_pdu_buffer already holds unpacked bits, so we just pass it directly
                        pmt::pmt_t pdu_vector = pmt::init_u8vector(d_pdu_buffer.size(), d_pdu_buffer.data());
                        pmt::pmt_t pdu = pmt::cons(meta, pdu_vector);
                        
                        message_port_pub(pmt::mp("pdu_out"), pdu);
                    }
                }
            } 
            else if (d_in_frame) {
                // If we are actively recording a frame, save the unpacked bit.
                d_pdu_buffer.push_back(bit);
            }
        }
    }

    // Tell runtime we consumed all input bytes
    consume_each(n_input);
    return 0;
}

} /* namespace DLC */
} /* namespace gr */