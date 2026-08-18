/* -*- c++ -*- */
/*
 * Copyright 2026 Commlink.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_DLC_CRCGEN_H
#define INCLUDED_DLC_CRCGEN_H

#include <gnuradio/DLC/api.h>
#include <gnuradio/block.h>

namespace gr {
namespace DLC {

/*!
 * \brief <+description of block+>
 * \ingroup DLC
 *
 */
class DLC_API CRCGen : virtual public gr::block
{
public:
    typedef std::shared_ptr<CRCGen> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of DLC::CRCGen.
     *
     * To avoid accidental use of raw pointers, DLC::CRCGen's
     * constructor is in a private implementation
     * class. DLC::CRCGen::make is the public interface for
     * creating new instances.
     */
    static sptr make(int scheme = 16);
};

} // namespace DLC
} // namespace gr

#endif /* INCLUDED_DLC_CRCGEN_H */
