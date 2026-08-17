/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_BITSTUFFING_IMPL_H
#define INCLUDED_DLC_BITSTUFFING_IMPL_H

#include <gnuradio/DLC/bitStuffing.h>
#include <pmt/pmt.h> // REQUIRED for pmt::pmt_t
#include <cstdint>   // REQUIRED for uint8_t

namespace gr {
namespace DLC {

class bitStuffing_impl : public bitStuffing
{
private:
    uint8_t d_flag;

    void stuff_bits(pmt::pmt_t msg);

public:
    bitStuffing_impl(uint8_t flag);
    ~bitStuffing_impl();

    // Required overrides if inheriting from gr::block
    void forecast(int noutput_items, gr_vector_int& ninput_items_required);
    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items);
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_BITSTUFFING_IMPL_H */