/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_CRCGEN_IMPL_H
#define INCLUDED_DLC_CRCGEN_IMPL_H

#include <gnuradio/DLC/CRCGen.h>

namespace gr {
namespace DLC {

class CRCGen_impl : public CRCGen
{
private:
    int d_scheme;
    void generate_crc(pmt::pmt_t msg);

public:
    CRCGen_impl(int scheme);
    ~CRCGen_impl();
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_CRCGEN_IMPL_H */
