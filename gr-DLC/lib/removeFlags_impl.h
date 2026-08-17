/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_REMOVEFLAGS_IMPL_H
#define INCLUDED_DLC_REMOVEFLAGS_IMPL_H

#include <gnuradio/DLC/removeFlags.h>

#include <cstdint>
#include <vector>

namespace gr {
namespace DLC {

class removeFlags_impl : public removeFlags
{
private:
    uint8_t d_flag;
    uint8_t d_shift_reg;
    bool d_in_frame;
    std::vector<uint8_t> d_pdu_buffer;

public:
    removeFlags_impl(uint8_t flag);
    ~removeFlags_impl();

    // Where all the action really happens
    void forecast(int noutput_items, gr_vector_int& ninput_items_required);

    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items);
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_REMOVEFLAGS_IMPL_H */
