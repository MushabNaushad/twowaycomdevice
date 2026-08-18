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
#include <string>

namespace gr {
  namespace transport {

    /*!
     * \brief Connection-oriented Selective-Repeat ARQ transport layer block.
     *
     * This is a **pure message-passing** GNU Radio block (no stream I/O).
     * It implements a full connection-oriented transport protocol over a
     * half-duplex PDU link with:
     *
     *   - Three-phase operation: SYN/SYN-ACK handshake → SR-ARQ sliding
     *     window data transfer → FIN/FIN-ACK teardown.
     *   - Selective-Repeat windowing with sequence number space 2^m and
     *     maximum window size 2^(m-1) (SR constraint satisfied by design).
     *   - Per-packet retransmission timers via Boost.Asio on a dedicated
     *     background thread (non-blocking, flowgraph-safe).
     *   - Application bitstream header parsing (see docs/APP_BITSTREAM_FORMAT.md)
     *     to auto-detect payload type (text / image / audio).
     *
     * \ingroup transport
     *
     * Message Ports
     * -------------
     * Inputs:
     *   - pdu_in  (message) : PDUs arriving from the physical / MAC layer.
     *   - app_in  (message) : Raw application bitstream PDU from the local app.
     *                         [initiator role only]
     *
     * Outputs:
     *   - pdu_out (message) : PDUs to be sent to the physical / MAC layer.
     *   - app_out (message) : Reassembled application bitstream delivered to
     *                         the local application. [responder role only]
     */
    class TRANSPORT_API transport_layer : virtual public gr::block
    {
     public:
      typedef std::shared_ptr<transport_layer> sptr;

      /*!
       * \brief Construct a transport_layer block.
       *
       * \param m          Number of sequence-number bits (1–8). Sequence space
       *                   = 2^m, maximum window = 2^(m-1). Default: 4.
       * \param rto_ms     Retransmission timeout in milliseconds. Default: 500.
       * \param node_role  Either "initiator" (sends data) or "responder"
       *                   (receives data). Default: "initiator".
       * \param mtu_bytes  Maximum payload bytes per DATA frame. Default: 200.
       */
      static sptr make(int m            = 4,
                       int rto_ms       = 500,
                       const std::string& node_role = "initiator",
                       int mtu_bytes    = 200);
    };

  } // namespace transport
} // namespace gr

#endif /* INCLUDED_TRANSPORT_TRANSPORT_LAYER_H */
