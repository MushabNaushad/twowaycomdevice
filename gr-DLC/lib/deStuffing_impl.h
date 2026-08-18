/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_DESTUFFING_IMPL_H
#define INCLUDED_DLC_DESTUFFING_IMPL_H

#include <gnuradio/DLC/deStuffing.h>

namespace gr {
namespace DLC {

class deStuffing_impl : public deStuffing
{
private:
    uint8_t d_flag;

    void destuff_bits(pmt::pmt_t msg);

public:
    deStuffing_impl(uint8_t flag);
    ~deStuffing_impl();

    // Where all the action really happens
    void forecast(int noutput_items, gr_vector_int& ninput_items_required);

    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items);
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_DESTUFFING_IMPL_H */
