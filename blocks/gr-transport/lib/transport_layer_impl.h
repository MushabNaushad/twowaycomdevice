/* -*- c++ -*- */
/*
 * Copyright 2026 MethalMindiya.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TRANSPORT_TRANSPORT_LAYER_IMPL_H
#define INCLUDED_TRANSPORT_TRANSPORT_LAYER_IMPL_H

#include <gnuradio/transport/transport_layer.h>

namespace gr {
  namespace transport {

    class transport_layer_impl : public transport_layer
    {
     private:
      // Nothing to declare in this block.

     public:
      transport_layer_impl();
      ~transport_layer_impl();

      // Where all the action really happens
      void forecast (int noutput_items, gr_vector_int &ninput_items_required);

      int general_work(int noutput_items,
           gr_vector_int &ninput_items,
           gr_vector_const_void_star &input_items,
           gr_vector_void_star &output_items);

    };

  } // namespace transport
} // namespace gr

#endif /* INCLUDED_TRANSPORT_TRANSPORT_LAYER_IMPL_H */
