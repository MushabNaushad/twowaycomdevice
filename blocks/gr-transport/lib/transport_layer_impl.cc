/* -*- c++ -*- */
/*
 * Copyright 2026 MethalMindiya.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Transport Layer — Selective-Repeat ARQ over GNU Radio PDU message passing.
 *
 * Protocol summary
 * ----------------
 *   PHASE 0  IDLE        : both nodes listen (default RX mode).
 *   PHASE 1  HANDSHAKE   : SYN → SYN_ACK.
 *   PHASE 2  DATA        : SR-ARQ sliding window (window ≤ 2^(m-1), m=4 → W=8).
 *   PHASE 3  TEARDOWN    : FIN → FIN_ACK → both nodes return to IDLE.
 *
 * Application bitstream format (app_in / app_out):
 *   See docs/APP_BITSTREAM_FORMAT.md for the full specification.
 *   Byte 0   : dst_addr — destination node address (0x00 = broadcast)
 *   Byte 1   : dst_port — destination service port  (0x00 = any)
 *   Byte 2   : Data type (0x01=text, 0x02=image, 0x03=audio)
 *   Byte 3   : Reserved (0x00)
 *   Byte 4-7 : Payload length, uint32 big-endian
 *   Byte 8+  : Raw payload
 *
 * PMT metadata keys used on every PDU:
 *   "pkt_type"      — symbol: SYN | SYN_ACK | DATA | ACK | FIN | FIN_ACK
 *   "seq_no"        — uint64: sequence number (0 … 2^m-1)
 *   "session_id"    — uint64: random session nonce
 *   "total_packets" — uint64: total DATA frames (carried in SYN)
 *   "payload_type"  — symbol: "text" | "image" | "audio" (carried in SYN/DATA)
 *   "src_addr"      — uint64: sender's node address (0x00 = broadcast/any)
 *   "src_port"      — uint64: sender's service port  (0x00 = any)
 *   "dst_addr"      — uint64: destination node address (0x00 = broadcast)
 *   "dst_port"      — uint64: destination service port  (0x00 = any)
 *
 * Threading model
 * ---------------
 *   GNU Radio scheduler thread → calls handle_pdu_in / handle_app_in.
 *   Boost.Asio io_thread       → fires RTO timer callbacks (on_timeout).
 *   d_mutex guards all shared FSM / window state between the two threads.
 *   message_port_pub() is thread-safe in GNU Radio and may be called from
 *   either thread without additional locking.
 */

#include <gnuradio/io_signature.h>
#include "transport_layer_impl.h"

#include <gnuradio/logger.h>

#include <algorithm>
#include <chrono>
#include <cstring>
#include <stdexcept>

namespace gr {
  namespace transport {

    // =========================================================================
    // Factory
    // =========================================================================
    transport_layer::sptr
    transport_layer::make(int m, int rto_ms,
                          const std::string& node_role, int mtu_bytes,
                          uint8_t local_addr, uint8_t local_port)
    {
      return gnuradio::make_block_sptr<transport_layer_impl>(
          m, rto_ms, node_role, mtu_bytes, local_addr, local_port);
    }

    // =========================================================================
    // Constructor
    // =========================================================================
    transport_layer_impl::transport_layer_impl(int m, int rto_ms,
                                               const std::string& node_role,
                                               int mtu_bytes,
                                               uint8_t local_addr,
                                               uint8_t local_port)
      : gr::block("transport_layer",
                  gr::io_signature::make(0, 0, 0),   // pure message-passing block
                  gr::io_signature::make(0, 0, 0)),
        d_m(m),
        d_seq_space(1 << m),
        d_window_size(1 << (m - 1)),
        d_mtu_bytes(mtu_bytes),
        d_rto_ms(rto_ms),
        d_role(node_role),
        d_local_addr(local_addr),
        d_local_port(local_port),
        d_state(NodeState::IDLE),
        d_session_id(0),
        d_dst_addr(0),
        d_dst_port(0),
        d_payload_type_pmt(pmt::PMT_NIL),
        d_send_base(0),
        d_next_seq_abs(0),
        d_total_packets_tx(0),
        d_rcv_base(0),
        d_total_packets_rx(0),
        d_packets_delivered(0),
        d_work_guard(boost::asio::make_work_guard(d_io_ctx)),
        d_rng(std::random_device{}())
    {
      // Parameter validation
      if (node_role != "initiator" && node_role != "responder")
          throw std::invalid_argument(
              "transport_layer: node_role must be 'initiator' or 'responder'");
      if (m < 1 || m > 8)
          throw std::invalid_argument(
              "transport_layer: m must be between 1 and 8");
      if (mtu_bytes < 1)
          throw std::invalid_argument(
              "transport_layer: mtu_bytes must be positive");

      // Allocate sliding-window buffers (indexed by seq_no slot = abs % d_seq_space)
      d_tx_buffer.assign(d_seq_space, pmt::PMT_NIL);
      d_acked.assign(d_seq_space, false);
      d_rx_buffer.assign(d_seq_space, pmt::PMT_NIL);
      d_received.assign(d_seq_space, false);

      // Allocate retransmission timers.
      // Slots 0..(d_seq_space-2) → DATA packet timers.
      // Slot  (d_seq_space-1)    → SYN / FIN retransmit timer.
      d_timers.resize(d_seq_space);
      for (int i = 0; i < d_seq_space; ++i)
          d_timers[i] = std::make_shared<boost::asio::steady_timer>(d_io_ctx);

      // Register message ports
      message_port_register_in (pmt::mp("pdu_in"));
      message_port_register_in (pmt::mp("app_in"));
      message_port_register_out(pmt::mp("pdu_out"));
      message_port_register_out(pmt::mp("app_out"));

      // Bind message handlers
      set_msg_handler(pmt::mp("pdu_in"),
          [this](pmt::pmt_t msg){ handle_pdu_in(msg); });
      set_msg_handler(pmt::mp("app_in"),
          [this](pmt::pmt_t msg){ handle_app_in(msg); });

      // Start the Boost.Asio event loop on a dedicated thread.
      // Timer callbacks (on_timeout) will run exclusively on this thread.
      d_io_thread = std::thread([this](){ d_io_ctx.run(); });

      GR_LOG_INFO(d_logger,
          std::string("transport_layer ready: role=") + node_role +
          " addr="       + std::to_string(static_cast<unsigned>(local_addr)) +
          " port="       + std::to_string(static_cast<unsigned>(local_port)) +
          " m="          + std::to_string(m) +
          " seq_space="  + std::to_string(d_seq_space) +
          " window="     + std::to_string(d_window_size) +
          " mtu="        + std::to_string(mtu_bytes) + "B" +
          " rto="        + std::to_string(rto_ms) + "ms");
    }

    // =========================================================================
    // Destructor
    // =========================================================================
    transport_layer_impl::~transport_layer_impl()
    {
      // Cancel all pending timers
      for (int i = 0; i < d_seq_space; ++i) {
          d_timers[i]->cancel();
      }
      // Stop the io_context and join the io_thread
      d_work_guard.reset();
      d_io_ctx.stop();
      if (d_io_thread.joinable())
          d_io_thread.join();
    }

    // =========================================================================
    // APPLICATION LAYER INGRESS  (app_in handler)
    // =========================================================================
    void transport_layer_impl::handle_app_in(pmt::pmt_t msg)
    {
      if (!pmt::is_pair(msg)) {
          GR_LOG_WARN(d_logger, "app_in: not a PDU pair — ignoring");
          return;
      }

      std::lock_guard<std::mutex> lock(d_mutex);

      if (d_role != "initiator") {
          GR_LOG_WARN(d_logger, "app_in: only 'initiator' nodes originate sessions");
          return;
      }
      if (d_state != NodeState::IDLE) {
          GR_LOG_WARN(d_logger, "app_in: session already in progress — dropping");
          return;
      }

      pmt::pmt_t data = pmt::cdr(msg);
      if (!pmt::is_u8vector(data)) {
          GR_LOG_ERROR(d_logger, "app_in: cdr must be a u8vector (application bitstream)");
          return;
      }

      size_t frame_len = 0;
      const uint8_t* frame = pmt::u8vector_elements(data, frame_len);

      // ------------------------------------------------------------------
      // Parse application bitstream header (docs/APP_BITSTREAM_FORMAT.md)
      // ------------------------------------------------------------------
      if (frame_len < APP_HDR_SIZE) {
          GR_LOG_ERROR(d_logger, "app_in: frame too short for 8-byte header ("
                       + std::to_string(frame_len) + " bytes)");
          return;
      }
      // Read destination address and port from app bitstream bytes 0–1
      // (replaces the former magic-byte slot; lower layers handle framing)
      d_dst_addr = frame[0];
      d_dst_port = frame[1];

      // Determine payload type string from type byte
      uint8_t type_byte = frame[2];
      std::string pt_str;
      switch (type_byte) {
          case APP_TYPE_TEXT:  pt_str = "text";    break;
          case APP_TYPE_IMAGE: pt_str = "image";   break;
          case APP_TYPE_AUDIO: pt_str = "audio";   break;
          default:
              GR_LOG_WARN(d_logger, "app_in: unknown type byte 0x"
                          + std::to_string(type_byte) + " — treating as 'unknown'");
              pt_str = "unknown";
      }
      d_payload_type_pmt = pmt::mp(pt_str);

      // Verify declared payload length vs. actual frame length
      uint32_t declared_len =
          (static_cast<uint32_t>(frame[4]) << 24) |
          (static_cast<uint32_t>(frame[5]) << 16) |
          (static_cast<uint32_t>(frame[6]) <<  8) |
          (static_cast<uint32_t>(frame[7]));

      if (frame_len != APP_HDR_SIZE + declared_len) {
          GR_LOG_ERROR(d_logger,
              "app_in: declared length " + std::to_string(declared_len) +
              " does not match actual frame length " + std::to_string(frame_len) +
              " - " + std::to_string(APP_HDR_SIZE) + " = " +
              std::to_string(frame_len - APP_HDR_SIZE));
          return;
      }

      // Packetize the ENTIRE frame (header + payload) for transparent delivery
      std::vector<uint8_t> full_frame(frame, frame + frame_len);
      packetize(full_frame);

      // Open a new session
      d_session_id = generate_session_id();

      GR_LOG_INFO(d_logger,
          "app_in: dst=" + std::to_string(static_cast<unsigned>(d_dst_addr)) +
          ":"            + std::to_string(static_cast<unsigned>(d_dst_port)) +
          " type="       + pt_str +
          " frame="      + std::to_string(frame_len) + "B" +
          " packets="    + std::to_string(d_total_packets_tx) +
          " session="    + std::to_string(d_session_id));

      // Transition → SYN_SENT and send SYN handshake frame
      d_state = NodeState::SYN_SENT;
      send_ctrl_frame("SYN", d_session_id,
                      /*seq_no*/ -1,
                      d_total_packets_tx,
                      pt_str);
      start_timer(d_seq_space - 1);   // Slot reserved for SYN / FIN retransmits
    }

    // =========================================================================
    // PHY LAYER INGRESS  (pdu_in handler — FSM entry point)
    // =========================================================================
    void transport_layer_impl::handle_pdu_in(pmt::pmt_t msg)
    {
      if (!pmt::is_pair(msg)) {
          GR_LOG_WARN(d_logger, "pdu_in: not a PDU pair — ignoring");
          return;
      }

      pmt::pmt_t meta = pmt::car(msg);
      pmt::pmt_t data = pmt::cdr(msg);

      if (!pmt::is_dict(meta)) {
          GR_LOG_WARN(d_logger, "pdu_in: car is not a dict — ignoring");
          return;
      }
      if (!pmt::dict_has_key(meta, pmt::mp("pkt_type"))) {
          GR_LOG_WARN(d_logger, "pdu_in: missing 'pkt_type' key — ignoring");
          return;
      }

      std::string pkt_type = pmt::symbol_to_string(
          pmt::dict_ref(meta, pmt::mp("pkt_type"), pmt::mp("")));

      uint64_t incoming_sid = 0;
      if (pmt::dict_has_key(meta, pmt::mp("session_id")))
          incoming_sid = pmt::to_uint64(
              pmt::dict_ref(meta, pmt::mp("session_id"), pmt::from_uint64(0)));

      std::lock_guard<std::mutex> lock(d_mutex);

      // Session ID guard — reject stale packets from old sessions.
      // Exempt SYN (no session established yet) and IDLE state.
      if (d_state != NodeState::IDLE && pkt_type != "SYN") {
          if (incoming_sid != d_session_id) {
              GR_LOG_WARN(d_logger,
                  "pdu_in: stale session_id " + std::to_string(incoming_sid) +
                  " (current=" + std::to_string(d_session_id) + ") — dropping");
              return;
          }
      }

      // Dispatch to the appropriate FSM handler
      switch (d_state) {
          case NodeState::IDLE:       fsm_idle      (meta, data, pkt_type); break;
          case NodeState::SYN_SENT:   fsm_syn_sent  (meta, data, pkt_type); break;
          case NodeState::SYN_RCVD:   fsm_syn_rcvd  (meta, data, pkt_type); break;
          case NodeState::TX_ACTIVE:  fsm_tx_active (meta, data, pkt_type); break;
          case NodeState::RX_ACTIVE:  fsm_rx_active (meta, data, pkt_type); break;
          case NodeState::FIN_SENT:   fsm_fin_sent  (meta, data, pkt_type); break;
          default: break;
      }
    }

    // =========================================================================
    // FSM STATE HANDLERS
    // =========================================================================

    // -------------------------------------------------------------------------
    // IDLE — listening for SYN from an initiator
    // -------------------------------------------------------------------------
    void transport_layer_impl::fsm_idle(pmt::pmt_t meta, pmt::pmt_t /*data*/,
                                         const std::string& pkt_type)
    {
      if (pkt_type != "SYN") return;   // Ignore everything else in IDLE

      // Extract session parameters from the SYN frame
      uint64_t sid = pmt::to_uint64(
          pmt::dict_ref(meta, pmt::mp("session_id"), pmt::from_uint64(0)));
      int total_pkts = static_cast<int>(pmt::to_uint64(
          pmt::dict_ref(meta, pmt::mp("total_packets"), pmt::from_uint64(0))));
      std::string pt_str = "unknown";
      if (pmt::dict_has_key(meta, pmt::mp("payload_type")))
          pt_str = pmt::symbol_to_string(
              pmt::dict_ref(meta, pmt::mp("payload_type"), pmt::mp("unknown")));

      // --- Address / port filter ----------------------------------------
      // Extract addressing fields from the incoming SYN metadata.
      uint8_t syn_dst_addr = 0x00, syn_dst_port = 0x00;
      uint8_t syn_src_addr = 0x00, syn_src_port = 0x00;
      if (pmt::dict_has_key(meta, pmt::mp("dst_addr")))
          syn_dst_addr = static_cast<uint8_t>(pmt::to_uint64(
              pmt::dict_ref(meta, pmt::mp("dst_addr"), pmt::from_uint64(0))));
      if (pmt::dict_has_key(meta, pmt::mp("dst_port")))
          syn_dst_port = static_cast<uint8_t>(pmt::to_uint64(
              pmt::dict_ref(meta, pmt::mp("dst_port"), pmt::from_uint64(0))));
      if (pmt::dict_has_key(meta, pmt::mp("src_addr")))
          syn_src_addr = static_cast<uint8_t>(pmt::to_uint64(
              pmt::dict_ref(meta, pmt::mp("src_addr"), pmt::from_uint64(0))));
      if (pmt::dict_has_key(meta, pmt::mp("src_port")))
          syn_src_port = static_cast<uint8_t>(pmt::to_uint64(
              pmt::dict_ref(meta, pmt::mp("src_port"), pmt::from_uint64(0))));

      // Accept: dst matches local addr/port, OR either side uses wildcard 0x00
      bool addr_match = (d_local_addr == APP_ADDR_BCAST) ||
                        (syn_dst_addr == APP_ADDR_BCAST)  ||
                        (syn_dst_addr == d_local_addr);
      bool port_match = (d_local_port == APP_PORT_ANY)   ||
                        (syn_dst_port == APP_PORT_ANY)    ||
                        (syn_dst_port == d_local_port);

      if (!addr_match || !port_match) {
          GR_LOG_DEBUG(d_logger,
              "IDLE: SYN not for us — dst=" +
              std::to_string(static_cast<unsigned>(syn_dst_addr)) + ":" +
              std::to_string(static_cast<unsigned>(syn_dst_port)) +
              " local=" +
              std::to_string(static_cast<unsigned>(d_local_addr)) + ":" +
              std::to_string(static_cast<unsigned>(d_local_port)) + " — dropping");
          return;
      }

      // Record the peer's address so reply frames are addressed back correctly
      d_dst_addr = syn_src_addr;
      d_dst_port = syn_src_port;

      // Initialise RX-side session state
      d_session_id        = sid;
      d_total_packets_rx  = total_pkts;
      d_payload_type_pmt  = pmt::mp(pt_str);
      d_rcv_base          = 0;
      d_packets_delivered = 0;
      d_reassembled_data.clear();
      d_received.assign(d_seq_space, false);
      d_rx_buffer.assign(d_seq_space, pmt::PMT_NIL);

      GR_LOG_INFO(d_logger,
          "IDLE→SYN_RCVD: SYN received from " +
          std::to_string(static_cast<unsigned>(d_dst_addr)) + ":" +
          std::to_string(static_cast<unsigned>(d_dst_port)) +
          " — type=" + pt_str +
          " total_pkts=" + std::to_string(total_pkts) +
          " session="    + std::to_string(sid));

      d_state = NodeState::SYN_RCVD;
      send_ctrl_frame("SYN_ACK", d_session_id);
    }

    // -------------------------------------------------------------------------
    // SYN_SENT — waiting for SYN_ACK from the responder
    // -------------------------------------------------------------------------
    void transport_layer_impl::fsm_syn_sent(pmt::pmt_t /*meta*/, pmt::pmt_t /*data*/,
                                             const std::string& pkt_type)
    {
      if (pkt_type != "SYN_ACK") return;

      cancel_timer(d_seq_space - 1);    // Cancel SYN retransmit timer

      GR_LOG_INFO(d_logger, "SYN_SENT→TX_ACTIVE: SYN_ACK received — filling send window");

      d_state        = NodeState::TX_ACTIVE;
      d_send_base    = 0;
      d_next_seq_abs = 0;

      // Fill the initial send window (up to WINDOW_SIZE packets)
      int fill = std::min(d_window_size, d_total_packets_tx);
      for (int i = 0; i < fill; ++i) {
          int slot = d_next_seq_abs % d_seq_space;
          send_data_packet_locked(slot);
          start_timer(slot);
          d_next_seq_abs++;
      }
    }

    // -------------------------------------------------------------------------
    // SYN_RCVD — responder has sent SYN_ACK, waiting for first DATA
    // -------------------------------------------------------------------------
    void transport_layer_impl::fsm_syn_rcvd(pmt::pmt_t meta, pmt::pmt_t data,
                                             const std::string& pkt_type)
    {
      if (pkt_type == "SYN") {
          // Duplicate SYN (initiator did not receive our SYN_ACK) — re-send it
          GR_LOG_INFO(d_logger, "SYN_RCVD: duplicate SYN — re-sending SYN_ACK");
          send_ctrl_frame("SYN_ACK", d_session_id);
          return;
      }
      if (pkt_type == "DATA") {
          // First DATA confirms the initiator entered TX_ACTIVE — we enter RX_ACTIVE
          d_state = NodeState::RX_ACTIVE;
          GR_LOG_INFO(d_logger, "SYN_RCVD→RX_ACTIVE: first DATA frame received");
          fsm_rx_active(meta, data, pkt_type);   // Process immediately
      }
    }

    // -------------------------------------------------------------------------
    // TX_ACTIVE — initiator is sending DATA frames, waiting for ACKs
    // -------------------------------------------------------------------------
    void transport_layer_impl::fsm_tx_active(pmt::pmt_t meta, pmt::pmt_t /*data*/,
                                              const std::string& pkt_type)
    {
      if (pkt_type != "ACK") return;

      int seq_no = static_cast<int>(pmt::to_uint64(
          pmt::dict_ref(meta, pmt::mp("seq_no"), pmt::from_uint64(0))));

      if (d_acked[seq_no]) return;   // Duplicate ACK — already processed

      d_acked[seq_no] = true;
      cancel_timer(seq_no);

      GR_LOG_DEBUG(d_logger,
          "TX_ACTIVE: ACK seq=" + std::to_string(seq_no));

      advance_send_window();
    }

    // -------------------------------------------------------------------------
    // RX_ACTIVE — responder is buffering DATA frames and sending ACKs
    // -------------------------------------------------------------------------
    void transport_layer_impl::fsm_rx_active(pmt::pmt_t meta, pmt::pmt_t data,
                                              const std::string& pkt_type)
    {
      if (pkt_type != "DATA") return;

      int seq_no = static_cast<int>(pmt::to_uint64(
          pmt::dict_ref(meta, pmt::mp("seq_no"), pmt::from_uint64(0))));

      // Validate that seq_no falls within the receive window
      // Window = [d_rcv_base, d_rcv_base + WINDOW_SIZE - 1] mod SEQ_SPACE
      bool in_window = false;
      for (int i = 0; i < d_window_size; ++i) {
          if (seq_no == (d_rcv_base + i) % d_seq_space) {
              in_window = true;
              break;
          }
      }

      if (!in_window) {
          GR_LOG_WARN(d_logger,
              "RX_ACTIVE: seq=" + std::to_string(seq_no) +
              " outside window [" + std::to_string(d_rcv_base) +
              ".." + std::to_string((d_rcv_base + d_window_size - 1) % d_seq_space) +
              "] — sending ACK anyway to unblock sender");
          // Send ACK to help the transmitter advance its window (e.g. if our earlier
          // ACK was lost and this is a retransmit of an already-delivered packet).
          send_ctrl_frame("ACK", d_session_id, seq_no);
          return;
      }

      // Buffer the frame if not already received (handle duplicates silently)
      if (!d_received[seq_no]) {
          if (!pmt::is_u8vector(data)) {
              GR_LOG_ERROR(d_logger, "RX_ACTIVE: DATA cdr is not a u8vector — dropping");
              return;
          }
          d_received[seq_no]  = true;
          d_rx_buffer[seq_no] = data;
          GR_LOG_DEBUG(d_logger,
              "RX_ACTIVE: buffered seq=" + std::to_string(seq_no));
      }

      // Always ACK: the initiator's timer may have fired for this seq_no
      send_ctrl_frame("ACK", d_session_id, seq_no);

      // Try to deliver in-order packets up to app_out
      try_deliver_rx_buffer();
    }

    // -------------------------------------------------------------------------
    // FIN_SENT — initiator sent FIN, waiting for FIN_ACK from responder
    // -------------------------------------------------------------------------
    void transport_layer_impl::fsm_fin_sent(pmt::pmt_t /*meta*/, pmt::pmt_t /*data*/,
                                             const std::string& pkt_type)
    {
      if (pkt_type != "FIN_ACK") return;

      cancel_timer(d_seq_space - 1);
      GR_LOG_INFO(d_logger, "FIN_SENT→IDLE: FIN_ACK received — session closed");
      reset_state();
    }

    // =========================================================================
    // WINDOW MANAGEMENT
    // =========================================================================

    // -------------------------------------------------------------------------
    // advance_send_window
    // -------------------------------------------------------------------------
    void transport_layer_impl::advance_send_window()
    {
      // Slide the base forward over every consecutively ACK'd slot
      while (d_send_base < d_total_packets_tx &&
             d_acked[d_send_base % d_seq_space])
      {
          int slot = d_send_base % d_seq_space;
          d_acked[slot]      = false;
          d_tx_buffer[slot]  = pmt::PMT_NIL;
          d_send_base++;

          // For each slot freed, send the next buffered packet (if any remain)
          if (d_next_seq_abs < d_total_packets_tx) {
              int next_slot = d_next_seq_abs % d_seq_space;
              send_data_packet_locked(next_slot);
              start_timer(next_slot);
              d_next_seq_abs++;
          }
      }

      // Check if ALL packets have now been ACK'd
      if (d_send_base >= d_total_packets_tx) {
          GR_LOG_INFO(d_logger,
              "TX_ACTIVE→FIN_SENT: all " +
              std::to_string(d_total_packets_tx) + " packets ACK'd — sending FIN");
          d_state = NodeState::FIN_SENT;
          send_ctrl_frame("FIN", d_session_id);
          start_timer(d_seq_space - 1);   // FIN retransmit timer
      }
    }

    // -------------------------------------------------------------------------
    // try_deliver_rx_buffer
    // -------------------------------------------------------------------------
    void transport_layer_impl::try_deliver_rx_buffer()
    {
      // Deliver all contiguous in-order frames starting from d_rcv_base
      while (d_packets_delivered < d_total_packets_rx &&
             d_received[d_rcv_base])
      {
          pmt::pmt_t chunk = d_rx_buffer[d_rcv_base];
          size_t chunk_len = 0;
          const uint8_t* bytes = pmt::u8vector_elements(chunk, chunk_len);
          d_reassembled_data.insert(d_reassembled_data.end(), bytes, bytes + chunk_len);

          d_received[d_rcv_base]  = false;
          d_rx_buffer[d_rcv_base] = pmt::PMT_NIL;
          d_rcv_base = (d_rcv_base + 1) % d_seq_space;
          d_packets_delivered++;
      }

      // All packets reassembled — deliver to application and tear down
      if (d_packets_delivered == d_total_packets_rx) {
          GR_LOG_INFO(d_logger,
              "RX_ACTIVE: reassembly complete — " +
              std::to_string(d_reassembled_data.size()) + " bytes → app_out");

          // Publish reassembled bitstream (full frame incl. 8-byte header)
          pmt::pmt_t out_meta = pmt::make_dict();
          out_meta = pmt::dict_add(out_meta, pmt::mp("payload_type"),
                                   d_payload_type_pmt);
          out_meta = pmt::dict_add(out_meta, pmt::mp("session_id"),
                                   pmt::from_uint64(d_session_id));
          // Addressing: from the responder's perspective src = peer (initiator)
          out_meta = pmt::dict_add(out_meta, pmt::mp("src_addr"),
                                   pmt::from_uint64(static_cast<uint64_t>(d_dst_addr)));
          out_meta = pmt::dict_add(out_meta, pmt::mp("src_port"),
                                   pmt::from_uint64(static_cast<uint64_t>(d_dst_port)));
          out_meta = pmt::dict_add(out_meta, pmt::mp("dst_addr"),
                                   pmt::from_uint64(static_cast<uint64_t>(d_local_addr)));
          out_meta = pmt::dict_add(out_meta, pmt::mp("dst_port"),
                                   pmt::from_uint64(static_cast<uint64_t>(d_local_port)));
          pmt::pmt_t out_data = pmt::init_u8vector(
              d_reassembled_data.size(), d_reassembled_data.data());
          message_port_pub(pmt::mp("app_out"), pmt::cons(out_meta, out_data));

          // Acknowledge teardown and return to IDLE
          send_ctrl_frame("FIN_ACK", d_session_id);
          GR_LOG_INFO(d_logger, "RX_ACTIVE→IDLE: FIN_ACK sent — session closed");
          reset_state();
      }
    }

    // =========================================================================
    // PACKETIZATION
    // =========================================================================
    void transport_layer_impl::packetize(const std::vector<uint8_t>& raw)
    {
      d_tx_buffer.assign(d_seq_space, pmt::PMT_NIL);
      d_acked.assign(d_seq_space, false);

      int offset   = 0;
      int pkt_idx  = 0;
      int raw_size = static_cast<int>(raw.size());

      while (offset < raw_size) {
          int chunk_len = std::min(d_mtu_bytes, raw_size - offset);
          int slot      = pkt_idx % d_seq_space;
          d_tx_buffer[slot] = pmt::init_u8vector(
              chunk_len, raw.data() + offset);
          pkt_idx++;
          offset += chunk_len;
      }

      d_total_packets_tx = pkt_idx;
      d_send_base        = 0;
      d_next_seq_abs     = 0;

      GR_LOG_DEBUG(d_logger,
          "packetize: " + std::to_string(raw_size) + "B → " +
          std::to_string(pkt_idx) + " packets (mtu=" +
          std::to_string(d_mtu_bytes) + "B)");
    }

    // =========================================================================
    // TIMER MANAGEMENT
    // =========================================================================
    void transport_layer_impl::start_timer(int slot)
    {
      // Cancel any currently running timer on this slot before re-arming
      d_timers[slot]->cancel();
      d_timers[slot]->expires_after(std::chrono::milliseconds(d_rto_ms));
      d_timers[slot]->async_wait(
          [this, slot](const boost::system::error_code& ec){
              on_timeout(slot, ec);
          });
    }

    void transport_layer_impl::cancel_timer(int slot)
    {
      d_timers[slot]->cancel();
    }

    void transport_layer_impl::on_timeout(int slot,
                                           const boost::system::error_code& ec)
    {
      if (ec == boost::asio::error::operation_aborted)
          return;   // Timer was cancelled — nothing to do

      std::lock_guard<std::mutex> lock(d_mutex);

      // Slot d_seq_space-1 is shared by SYN and FIN retransmits
      if (slot == d_seq_space - 1) {
          if (d_state == NodeState::SYN_SENT) {
              GR_LOG_WARN(d_logger, "RTO: SYN timeout — retransmitting SYN");
              send_ctrl_frame("SYN", d_session_id,
                              /*seq_no*/ -1,
                              d_total_packets_tx,
                              pmt::symbol_to_string(d_payload_type_pmt));
              start_timer(d_seq_space - 1);
          } else if (d_state == NodeState::FIN_SENT) {
              GR_LOG_WARN(d_logger, "RTO: FIN timeout — retransmitting FIN");
              send_ctrl_frame("FIN", d_session_id);
              start_timer(d_seq_space - 1);
          }
          return;
      }

      // DATA packet retransmit
      if (d_state == NodeState::TX_ACTIVE && !d_acked[slot]) {
          GR_LOG_WARN(d_logger,
              "RTO: DATA timeout — retransmitting slot=" + std::to_string(slot));
          send_data_packet_locked(slot);
          start_timer(slot);
      }
    }

    // =========================================================================
    // SEND HELPERS
    // =========================================================================
    pmt::pmt_t transport_layer_impl::build_meta(const std::string& pkt_type,
                                                 int seq_no,
                                                 uint64_t session_id,
                                                 int total_packets,
                                                 const std::string& payload_type_str)
    {
      pmt::pmt_t meta = pmt::make_dict();
      meta = pmt::dict_add(meta, pmt::mp("pkt_type"),   pmt::mp(pkt_type));
      meta = pmt::dict_add(meta, pmt::mp("session_id"), pmt::from_uint64(session_id));
      if (seq_no >= 0)
          meta = pmt::dict_add(meta, pmt::mp("seq_no"),
                               pmt::from_uint64(static_cast<uint64_t>(seq_no)));
      if (total_packets > 0)
          meta = pmt::dict_add(meta, pmt::mp("total_packets"),
                               pmt::from_uint64(static_cast<uint64_t>(total_packets)));
      if (!payload_type_str.empty())
          meta = pmt::dict_add(meta, pmt::mp("payload_type"),
                               pmt::mp(payload_type_str));
      // Addressing fields — present on every outgoing PDU
      meta = pmt::dict_add(meta, pmt::mp("src_addr"),
                           pmt::from_uint64(static_cast<uint64_t>(d_local_addr)));
      meta = pmt::dict_add(meta, pmt::mp("src_port"),
                           pmt::from_uint64(static_cast<uint64_t>(d_local_port)));
      meta = pmt::dict_add(meta, pmt::mp("dst_addr"),
                           pmt::from_uint64(static_cast<uint64_t>(d_dst_addr)));
      meta = pmt::dict_add(meta, pmt::mp("dst_port"),
                           pmt::from_uint64(static_cast<uint64_t>(d_dst_port)));
      return meta;
    }

    void transport_layer_impl::send_ctrl_frame(const std::string& pkt_type,
                                                uint64_t session_id,
                                                int seq_no,
                                                int total_packets,
                                                const std::string& payload_type_str)
    {
      pmt::pmt_t meta = build_meta(pkt_type, seq_no, session_id,
                                   total_packets, payload_type_str);
      // Control frames carry an empty payload
      send_pdu(meta, pmt::make_u8vector(0, 0));
    }

    void transport_layer_impl::send_data_packet_locked(int slot)
    {
      if (pmt::equal(d_tx_buffer[slot], pmt::PMT_NIL)) {
          GR_LOG_ERROR(d_logger,
              "send_data_packet: nil buffer at slot=" + std::to_string(slot));
          return;
      }
      pmt::pmt_t meta = build_meta("DATA",
                                   slot,   // seq_no = slot (modular)
                                   d_session_id,
                                   d_total_packets_tx,
                                   pmt::symbol_to_string(d_payload_type_pmt));
      send_pdu(meta, d_tx_buffer[slot]);
      GR_LOG_DEBUG(d_logger, "DATA sent: slot=" + std::to_string(slot));
    }

    void transport_layer_impl::send_pdu(pmt::pmt_t meta, pmt::pmt_t data)
    {
      // message_port_pub is internally thread-safe in GNU Radio
      message_port_pub(pmt::mp("pdu_out"), pmt::cons(meta, data));
    }

    // =========================================================================
    // UTILITY
    // =========================================================================
    void transport_layer_impl::reset_state()
    {
      // Cancel every running timer
      for (int i = 0; i < d_seq_space; ++i) {
          d_timers[i]->cancel();
      }
      // Reset FSM
      d_state             = NodeState::IDLE;
      d_session_id        = 0;
      d_dst_addr          = 0;
      d_dst_port          = 0;
      d_payload_type_pmt  = pmt::PMT_NIL;
      // TX side
      d_send_base         = 0;
      d_next_seq_abs      = 0;
      d_total_packets_tx  = 0;
      d_tx_buffer.assign(d_seq_space, pmt::PMT_NIL);
      d_acked.assign    (d_seq_space, false);
      // RX side
      d_rcv_base          = 0;
      d_total_packets_rx  = 0;
      d_packets_delivered = 0;
      d_reassembled_data.clear();
      d_rx_buffer.assign(d_seq_space, pmt::PMT_NIL);
      d_received.assign (d_seq_space, false);

      GR_LOG_INFO(d_logger, "FSM reset → IDLE");
    }

    uint64_t transport_layer_impl::generate_session_id()
    {
      return d_rng();
    }

  } /* namespace transport */
} /* namespace gr */
