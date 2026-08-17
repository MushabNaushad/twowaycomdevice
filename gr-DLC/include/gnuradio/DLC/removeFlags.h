/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_REMOVEFLAGS_H
#define INCLUDED_DLC_REMOVEFLAGS_H

#include <gnuradio/DLC/api.h>
#include <gnuradio/block.h>

#include <cstdint>
#include <memory>

namespace gr {
namespace DLC {

/*!
 * \brief <+description of block+>
 * \ingroup DLC
 *
 */
class DLC_API removeFlags : virtual public gr::block
{
public:
    typedef std::shared_ptr<removeFlags> sptr;

    static sptr make(uint8_t flag);
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_REMOVEFLAGS_H */
