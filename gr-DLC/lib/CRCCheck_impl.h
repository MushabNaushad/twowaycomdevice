/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_CRCCHECK_IMPL_H
#define INCLUDED_DLC_CRCCHECK_IMPL_H

#include <gnuradio/DLC/CRCCheck.h>

namespace gr {
namespace DLC {

class CRCCheck_impl : public CRCCheck
{
private:
    int d_scheme;
    void check_crc(pmt::pmt_t msg);

public:
    CRCCheck_impl(int scheme);
    ~CRCCheck_impl();
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_CRCCHECK_IMPL_H */
