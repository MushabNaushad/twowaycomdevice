/* -*- c++ -*- */
/*
 * Copyright 2026 maduwage.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_ADDFLAGS_H
#define INCLUDED_DLC_ADDFLAGS_H

#include <gnuradio/DLC/api.h>
#include <gnuradio/block.h>

namespace gr {
namespace DLC {

/*!
 * \brief <+description of block+>
 * \ingroup DLC
 *
 */
class DLC_API addFlags : virtual public gr::block
{
public:
    typedef std::shared_ptr<addFlags> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of DLC::addFlags.
     *
     * To avoid accidental use of raw pointers, DLC::addFlags's
     * constructor is in a private implementation
     * class. DLC::addFlags::make is the public interface for
     * creating new instances.
     */
    static sptr make(uint8_t flag = 0b01111110, bool bothEnds = true);
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_ADDFLAGS_H */
