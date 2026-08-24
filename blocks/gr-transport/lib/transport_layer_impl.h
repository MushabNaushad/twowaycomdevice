/* -*- c++ -*- */
/*
 * Copyright 2026 MethalMindiya.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TRANSPORT_TRANSPORT_LAYER_IMPL_H
#define INCLUDED_TRANSPORT_TRANSPORT_LAYER_IMPL_H

#include <gnuradio/transport/transport_layer.h>
#include <pmt/pmt.h>

#include <boost/asio.hpp>
#include <boost/system/error_code.hpp>

#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <random>
#include <string>
#include <thread>
#include <vector>

namespace gr {
  namespace transport {

    // -----------------------------------------------------------------------
    // Finite-State Machine states
    // -----------------------------------------------------------------------
    enum class NodeState {
        IDLE,       ///< Default — listening; both roles start here
        SYN_SENT,   ///< Initiator: SYN sent, awaiting SYN_ACK
        SYN_RCVD,   ///< Responder: SYN_ACK sent, awaiting first DATA
        TX_ACTIVE,  ///< Initiator: SR-ARQ sliding window in progress
        RX_ACTIVE,  ///< Responder: buffering/reassembling DATA frames
        FIN_SENT,   ///< Initiator: FIN sent, awaiting FIN_ACK
    };

    // -----------------------------------------------------------------------
    // Transport protocol packet types (encoded in byte 0 of transport header)
    // -----------------------------------------------------------------------
    static constexpr uint8_t  PKT_TYPE_NONE    = 0x00;
    static constexpr uint8_t  PKT_TYPE_SYN     = 0x01;
    static constexpr uint8_t  PKT_TYPE_SYN_ACK = 0x02;
    static constexpr uint8_t  PKT_TYPE_DATA    = 0x03;
    static constexpr uint8_t  PKT_TYPE_ACK     = 0x04;
    static constexpr uint8_t  PKT_TYPE_FIN     = 0x05;
    static constexpr uint8_t  PKT_TYPE_FIN_ACK = 0x06;

    static constexpr size_t   TRANSPORT_HDR_SIZE = 18;  ///< Fixed transport header length (bytes)

    struct TransportHeader {
        uint8_t  pkt_type;       ///< 0x01=SYN, 0x02=SYN_ACK, 0x03=DATA, 0x04=ACK, 0x05=FIN, 0x06=FIN_ACK
        uint8_t  payload_type;   ///< 0x01=text, 0x02=image, 0x03=audio, 0x00=none
        uint8_t  src_addr;
        uint8_t  src_port;
        uint8_t  dst_addr;
        uint8_t  dst_port;
        uint16_t seq_no;
        uint16_t total_packets;
        uint64_t session_id;
    };

    // -----------------------------------------------------------------------
    // Application bitstream header constants (see docs/APP_BITSTREAM_FORMAT.md)
    // -----------------------------------------------------------------------
    // Addressing wildcard values (used in address / port filter)
    static constexpr uint8_t  APP_ADDR_BCAST    = 0x00;  ///< Accepted by any node (broadcast)
    static constexpr uint8_t  APP_PORT_ANY       = 0x00;  ///< Accepted on any service port

    // Maximum SYN / FIN retransmit attempts before the session is abandoned
    static constexpr int      MAX_CTRL_RETRIES   = 10;
    static constexpr uint8_t  APP_TYPE_TEXT  = 0x01;
    static constexpr uint8_t  APP_TYPE_IMAGE = 0x02;
    static constexpr uint8_t  APP_TYPE_AUDIO = 0x03;
    static constexpr size_t   APP_HDR_SIZE   = 8;    ///< Fixed header length (bytes)

    // -----------------------------------------------------------------------
    // Transport layer implementation
    // -----------------------------------------------------------------------
    class transport_layer_impl : public transport_layer
    {
     private:
      // --- Protocol constants (set at construction, immutable) -----------
      const int d_m;              ///< Sequence-number bits (4)
      const int d_seq_space;      ///< 2^m  — total sequence number space (16)
      const int d_window_size;    ///< 2^(m-1) — max window size (8, SR constraint)
      const int d_mtu_bytes;      ///< Max DATA payload bytes per packet
      const int d_rto_ms;         ///< Retransmission timeout (ms)
      const std::string d_role;   ///< "initiator" or "responder"
      const uint8_t d_local_addr;  ///< This node's address (0x00 = promiscuous/broadcast)
      const uint8_t d_local_port;  ///< This node's service port (0x00 = any)

      // --- FSM state (protected by d_mutex) ------------------------------
      NodeState d_state;

      // --- Session metadata ----------------------------------------------
      uint64_t    d_session_id;         ///< Random nonce agreed during handshake
      uint8_t     d_dst_addr;           ///< Destination address for the current session
      uint8_t     d_dst_port;           ///< Destination port for the current session
      int         d_ctrl_retries;       ///< SYN / FIN retransmit attempt counter
      pmt::pmt_t  d_payload_type_pmt;   ///< PMT symbol: "text", "image", "audio"

      // --- TX sliding window state (initiator) ---------------------------
      int d_send_base;           ///< Absolute index of oldest unACK'd packet
      int d_next_seq_abs;        ///< Absolute index of next packet to send
      int d_total_packets_tx;    ///< Total DATA frames for this session
      std::vector<pmt::pmt_t> d_all_tx_packets; ///< Complete list of all packet chunks in session
      std::vector<pmt::pmt_t> d_tx_buffer; ///< [slot] = active in-flight u8vector chunk; slot = abs%SEQ_SPACE
      std::vector<bool>       d_acked;     ///< [slot] = true when ACK received

      // --- RX sliding window state (responder) ---------------------------
      int d_rcv_base;            ///< Modular seq_no of next expected in-order frame
      int d_total_packets_rx;    ///< Total expected DATA frames
      int d_packets_delivered;   ///< Count of in-order packets delivered to app
      std::vector<pmt::pmt_t> d_rx_buffer;  ///< [slot] = out-of-order buffered chunk
      std::vector<bool>       d_received;   ///< [slot] = true when frame is buffered
      std::vector<uint8_t>    d_reassembled_data; ///< Growing reassembly buffer

      // --- Boost.Asio timer infrastructure -------------------------------
      /// One timer per sequence slot + one extra slot (d_seq_space-1) for
      /// SYN and FIN retransmits. Total: d_seq_space timers.
      boost::asio::io_context  d_io_ctx;
      boost::asio::executor_work_guard<boost::asio::io_context::executor_type>
                               d_work_guard;
      std::thread              d_io_thread;  ///< Runs d_io_ctx.run()
      std::vector<std::shared_ptr<boost::asio::steady_timer>> d_timers;

      // --- Thread safety -------------------------------------------------
      std::mutex d_mutex; ///< Guards all state between scheduler & io_thread

      // --- PRNG for session IDs ------------------------------------------
      std::mt19937_64 d_rng;

      // -----------------------------------------------------------------------
      // Message handlers (called by GNU Radio scheduler)
      // -----------------------------------------------------------------------
      /// Entry point for PDUs arriving from the PHY/MAC layer.
      void handle_pdu_in(pmt::pmt_t msg);
      /// Entry point for application bitstream PDUs (initiator only).
      void handle_app_in(pmt::pmt_t msg);

      // -----------------------------------------------------------------------
      // FSM state handlers (called from handle_pdu_in, mutex held by caller)
      // -----------------------------------------------------------------------
      void fsm_idle     (pmt::pmt_t meta, pmt::pmt_t data, const std::string& pkt_type);
      void fsm_syn_sent (pmt::pmt_t meta, pmt::pmt_t data, const std::string& pkt_type);
      void fsm_syn_rcvd (pmt::pmt_t meta, pmt::pmt_t data, const std::string& pkt_type);
      void fsm_tx_active(pmt::pmt_t meta, pmt::pmt_t data, const std::string& pkt_type);
      void fsm_rx_active(pmt::pmt_t meta, pmt::pmt_t data, const std::string& pkt_type);
      void fsm_fin_sent (pmt::pmt_t meta, pmt::pmt_t data, const std::string& pkt_type);

      // -----------------------------------------------------------------------
      // Window management (called with d_mutex held)
      // -----------------------------------------------------------------------
      /// Slide the send window forward over consecutive ACK'd slots.
      /// Sends next buffered packet per slot advanced; triggers FIN when done.
      void advance_send_window();

      /// Deliver contiguous in-order received packets to app_out.
      /// Sends FIN_ACK and resets state when all packets are delivered.
      void try_deliver_rx_buffer();

      // -----------------------------------------------------------------------
      // Packetization (called with d_mutex held)
      // -----------------------------------------------------------------------
      /// Fragment raw bytes into MTU-sized chunks; populate d_tx_buffer[].
      void packetize(const std::vector<uint8_t>& raw);

      // -----------------------------------------------------------------------
      // Retransmission timers (timer callbacks run on d_io_thread)
      // -----------------------------------------------------------------------
      /// Arm (or re-arm) the RTO timer for the given sequence slot.
      void start_timer(int slot);
      /// Cancel the RTO timer for the given sequence slot.
      void cancel_timer(int slot);
      /// Timer expiry callback — retransmits the unACK'd packet.
      void on_timeout(int slot, const boost::system::error_code& ec);

      // -----------------------------------------------------------------------
      // Send helpers (may be called from either thread)
      // -----------------------------------------------------------------------
      /// Build a PMT metadata dictionary for a control or data frame.
      pmt::pmt_t build_meta(const std::string& pkt_type,
                             int seq_no,
                             uint64_t session_id,
                             int total_packets = 0,
                             const std::string& payload_type_str = "");

      /// Transmit a zero-payload control frame (SYN, SYN_ACK, ACK, FIN, FIN_ACK).
      void send_ctrl_frame(const std::string& pkt_type,
                           uint64_t session_id,
                           int seq_no           = -1,
                           int total_packets    = 0,
                           const std::string& payload_type_str = "");

      /// Transmit the DATA frame stored at the given window slot.
      /// Caller must hold d_mutex.
      void send_data_packet_locked(int slot);

      /// Publish a PMT cons pair to the pdu_out message port.
      void send_pdu(pmt::pmt_t meta, pmt::pmt_t data);

      // -----------------------------------------------------------------------
      // Binary Transport Header Helpers
      // -----------------------------------------------------------------------
      static std::vector<uint8_t> serialize_transport_header(
          uint8_t pkt_type,
          uint8_t payload_type,
          uint8_t src_addr,
          uint8_t src_port,
          uint8_t dst_addr,
          uint8_t dst_port,
          uint16_t seq_no,
          uint16_t total_packets,
          uint64_t session_id);

      static bool deserialize_transport_header(
          const uint8_t* buf,
          size_t len,
          TransportHeader& out_hdr);

      static std::string pkt_type_to_string(uint8_t type_code);
      static uint8_t string_to_pkt_type(const std::string& type_str);
      static std::string payload_type_to_string(uint8_t type_code);
      static uint8_t string_to_payload_type(const std::string& type_str);

      // -----------------------------------------------------------------------
      // Utility (called with d_mutex held)
      // -----------------------------------------------------------------------
      /// Reset all session state and return FSM to IDLE.
      void reset_state();
      /// Generate a random 64-bit session identifier.
      uint64_t generate_session_id();

     public:
      transport_layer_impl(int m,
                           int rto_ms,
                           const std::string& node_role,
                           int mtu_bytes,
                           uint8_t local_addr = 0x00,
                           uint8_t local_port = 0x00);
      ~transport_layer_impl();
    };

  } // namespace transport
} // namespace gr

#endif /* INCLUDED_TRANSPORT_TRANSPORT_LAYER_IMPL_H */

