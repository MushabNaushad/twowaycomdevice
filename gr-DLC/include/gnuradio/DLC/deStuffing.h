/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_DESTUFFING_H
#define INCLUDED_DLC_DESTUFFING_H

#include <gnuradio/DLC/api.h>
#include <gnuradio/block.h>

namespace gr {
namespace DLC {

/*!
 * \brief <+description of block+>
 * \ingroup DLC
 *
 */
class DLC_API deStuffing : virtual public gr::block
{
public:
    typedef std::shared_ptr<deStuffing> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of DLC::deStuffing.
     *
     * To avoid accidental use of raw pointers, DLC::deStuffing's
     * constructor is in a private implementation
     * class. DLC::deStuffing::make is the public interface for
     * creating new instances.
     */
    static sptr make(uint8_t flag = 0b01111110);
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_DESTUFFING_H */
