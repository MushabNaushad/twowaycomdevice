/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_REMOVEFLAGS_IMPL_H
#define INCLUDED_DLC_REMOVEFLAGS_IMPL_H

#include <gnuradio/DLC/removeFlags.h>
#include <pmt/pmt.h>
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

    void handle_msg(pmt::pmt_t msg);

public:
    removeFlags_impl(uint8_t flag);
    ~removeFlags_impl();
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_REMOVEFLAGS_IMPL_H */
