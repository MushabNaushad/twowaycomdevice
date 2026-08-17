/* -*- c++ -*- */
/*
 * Copyright 2026 maduwage.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_ADDFLAGS_IMPL_H
#define INCLUDED_DLC_ADDFLAGS_IMPL_H

#include <gnuradio/DLC/addFlags.h>

namespace gr {
namespace DLC {

class addFlags_impl : public addFlags
{
private:
    uint8_t d_flag;
    bool d_bothEnds;

    void process_packet(pmt::pmt_t msg);

public:
    addFlags_impl(uint8_t flag, bool bothEnds);
    ~addFlags_impl();

    // Where all the action really happens
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_ADDFLAGS_IMPL_H */
