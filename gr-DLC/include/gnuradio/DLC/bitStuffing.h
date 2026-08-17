/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_BITSTUFFING_H
#define INCLUDED_DLC_BITSTUFFING_H

#include <gnuradio/DLC/api.h>
#include <gnuradio/block.h>

namespace gr {
namespace DLC {

/*!
 * \brief <+description of block+>
 * \ingroup DLC
 *
 */
class DLC_API bitStuffing : virtual public gr::block
{
public:
    typedef std::shared_ptr<bitStuffing> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of DLC::bitStuffing.
     *
     * To avoid accidental use of raw pointers, DLC::bitStuffing's
     * constructor is in a private implementation
     * class. DLC::bitStuffing::make is the public interface for
     * creating new instances.
     */
    static sptr make(uint8_t flag = 0b01111110);
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_BITSTUFFING_H */
