/* -*- c++ -*- */
/*
 * Copyright 2026 MethalMindiya.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TRANSPORT_TRANSPORT_LAYER_H
#define INCLUDED_TRANSPORT_TRANSPORT_LAYER_H

#include <gnuradio/transport/api.h>
#include <gnuradio/block.h>

namespace gr {
  namespace transport {

    /*!
     * \brief <+description of block+>
     * \ingroup transport
     *
     */
    class TRANSPORT_API transport_layer : virtual public gr::block
    {
     public:
      typedef std::shared_ptr<transport_layer> sptr;

      /*!
       * \brief Return a shared_ptr to a new instance of transport::transport_layer.
       *
       * To avoid accidental use of raw pointers, transport::transport_layer's
       * constructor is in a private implementation
       * class. transport::transport_layer::make is the public interface for
       * creating new instances.
       */
      static sptr make();
    };

  } // namespace transport
} // namespace gr

#endif /* INCLUDED_TRANSPORT_TRANSPORT_LAYER_H */
