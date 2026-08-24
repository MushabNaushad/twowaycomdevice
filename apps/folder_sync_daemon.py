#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
folder_sync_daemon.py
=====================
Standalone Hot-Folder Synchronization Daemon for CDP Two-Way Radio.
Interfaces with GNU Radio via UDP Socket PDU.

Features:
- TX: Monitors transfers/node_<ID>/tx/ for new files, constructs File Envelope,
      and pushes to GNU Radio Socket PDU via UDP. Moves sent files to tx_sent/.
- RX: Receives reassembled bitstream from GNU Radio via UDP, unpacks File Envelope,
      and saves files into transfers/node_<ID>/rx/ with sender node prefix.
"""

import sys, os, time, socket, threading, argparse, hashlib, shutil

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

class FolderSyncDaemon:
    def __init__(self, node_id: int, tx_port: int, rx_port: int, base_dir: str = None, poll_interval: float = 0.5):
        self.node_id = node_id
        self.tx_port = tx_port
        self.rx_port = rx_port
        self.poll_interval = poll_interval
        self.running = False
        
        if base_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(script_dir)
            self.node_dir = os.path.join(root_dir, 'transfers', f'node_{node_id}')
        else:
            self.node_dir = base_dir

        self.tx_dir = os.path.join(self.node_dir, 'tx')
        self.sent_dir = os.path.join(self.node_dir, 'tx_sent')
        self.rx_dir = os.path.join(self.node_dir, 'rx')

        # Ensure directory structure exists
        os.makedirs(self.tx_dir, exist_ok=True)
        os.makedirs(self.sent_dir, exist_ok=True)
        os.makedirs(self.rx_dir, exist_ok=True)

        self.tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.rx_socket.bind(('127.0.0.1', self.rx_port))
        self.rx_socket.settimeout(0.5)

        self.sent_history = []
        self.received_history = []

    def start(self):
        self.running = True
        print("=" * 75)
        print(f" HOT-FOLDER SYNC DAEMON [Node {self.node_id}] ACTIVE")
        print(f"   Node Directory : {self.node_dir}")
        print(f"   TX Target Port : 127.0.0.1:{self.tx_port} (-> GNU Radio app_in)")
        print(f"   RX Listen Port : 127.0.0.1:{self.rx_port} (<- GNU Radio app_out)")
        print(f"   Monitoring     : {self.tx_dir}")
        print("=" * 75)

        self.tx_thread = threading.Thread(target=self._tx_loop, name=f"TX-Node{self.node_id}", daemon=True)
        self.rx_thread = threading.Thread(target=self._rx_loop, name=f"RX-Node{self.node_id}", daemon=True)

        self.tx_thread.start()
        self.rx_thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'tx_thread'): self.tx_thread.join(timeout=1.0)
        if hasattr(self, 'rx_thread'): self.rx_thread.join(timeout=1.0)
        try: self.tx_socket.close()
        except: pass
        try: self.rx_socket.close()
        except: pass
        print(f"[Node {self.node_id}] Daemon stopped.")

    # ─── TX File Scanner ────────────────────────────────────────────────────────
    def _tx_loop(self):
        while self.running:
            try:
                self._scan_and_send()
            except Exception as e:
                print(f"[TX Error Node {self.node_id}]: {e}")
            time.sleep(self.poll_interval)

    def _scan_and_send(self):
        if not os.path.exists(self.tx_dir):
            return

        for entry in os.listdir(self.tx_dir):
            subpath = os.path.join(self.tx_dir, entry)
            if not os.path.isdir(subpath):
                continue

            # Determine destination address from folder name
            if entry == "broadcast":
                dst_addr = 0
            elif entry.startswith("node_"):
                try:
                    dst_addr = int(entry.replace("node_", ""))
                except ValueError:
                    continue
            else:
                continue

            for fname in os.listdir(subpath):
                filepath = os.path.join(subpath, fname)
                if not os.path.isfile(filepath):
                    continue

                # Wait 50ms to ensure file write is complete if copied externally
                try:
                    init_size = os.path.getsize(filepath)
                    time.sleep(0.05)
                    if os.path.getsize(filepath) != init_size:
                        continue # File is still being written
                except OSError:
                    continue

                with open(filepath, "rb") as f:
                    file_bytes = f.read()

                ext = os.path.splitext(fname)[1].lower()
                media_type = 0x01 if ext in ['.txt', '.json', '.csv', '.log'] else \
                             0x02 if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif'] else \
                             0x03 if ext in ['.wav', '.mp3', '.opus', '.pcm'] else 0x04 # PDF / Generic

                # Construct File Envelope: [fname_len (1B)] + [fname_utf8] + [file_bytes]
                fname_bytes = fname.encode('utf-8')
                envelope = bytes([len(fname_bytes)]) + fname_bytes + file_bytes

                # Construct 8-Byte Application Header: [dst_addr, src_addr, media_type, 0x00, len_be32]
                n_len = len(envelope)
                app_hdr = bytes([
                    dst_addr, self.node_id, media_type, 0x00,
                    (n_len >> 24) & 0xFF, (n_len >> 16) & 0xFF,
                    (n_len >> 8)  & 0xFF, n_len & 0xFF
                ])

                full_pdu = app_hdr + envelope
                file_hash = sha256_bytes(file_bytes)

                # Transmit over UDP to GNU Radio Socket PDU
                self.tx_socket.sendto(full_pdu, ('127.0.0.1', self.tx_port))

                ts_str = time.strftime('%Y%m%d_%H%M%S')
                print(f"📤 [TX Node {self.node_id}] Sent '{fname}' ({len(file_bytes)}B, Type=0x{media_type:02X}) -> Target Node {dst_addr}")
                print(f"    SHA-256: {file_hash[:16]}... PDU size: {len(full_pdu)}B")

                self.sent_history.append({
                    'filename': fname,
                    'dst': dst_addr,
                    'size': len(file_bytes),
                    'sha256': file_hash,
                    'time': time.time()
                })

                # Move sent file to archive
                archive_name = f"{ts_str}_{fname}"
                dest_path = os.path.join(self.sent_dir, archive_name)
                shutil.move(filepath, dest_path)

    # ─── RX File Ingestion ──────────────────────────────────────────────────────
    def _rx_loop(self):
        while self.running:
            try:
                data, addr = self.rx_socket.recvfrom(65536)
                if data:
                    self._handle_received_pdu(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[RX Error Node {self.node_id}]: {e}")

    def _handle_received_pdu(self, raw: bytes):
        if len(raw) < 9:
            print(f"⚠ [RX Node {self.node_id}] Received runt packet ({len(raw)}B) — dropped")
            return

        # 1. Parse 8-Byte Application Header [dst_addr, src_addr, media_type, rsv, len_u32]
        dst_addr   = raw[0]
        src_addr   = raw[1]
        media_type = raw[2]
        app_len    = int.from_bytes(raw[4:8], byteorder='big')

        # 2. Parse File Envelope
        fname_len  = raw[8]
        if len(raw) < 9 + fname_len:
            print(f"⚠ [RX Node {self.node_id}] Invalid envelope — dropped")
            return

        fname = raw[9 : 9 + fname_len].decode('utf-8', errors='replace')
        file_bytes = raw[9 + fname_len :]
        file_hash = sha256_bytes(file_bytes)

        out_fname = f"from_node_{src_addr}_{fname}"
        out_path = os.path.join(self.rx_dir, out_fname)

        with open(out_path, "wb") as f:
            f.write(file_bytes)

        type_names = {1: "Text", 2: "Image", 3: "Audio", 4: "PDF/Doc"}
        type_desc = type_names.get(media_type, f"0x{media_type:02X}")

        print(f"📥 [RX Node {self.node_id}] Received '{out_fname}' ({len(file_bytes)}B, {type_desc}) from Node {src_addr}")
        print(f"    Saved -> {out_path}")
        print(f"    SHA-256: {file_hash[:16]}...")

        self.received_history.append({
            'filename': out_fname,
            'orig_filename': fname,
            'src': src_addr,
            'size': len(file_bytes),
            'sha256': file_hash,
            'time': time.time(),
            'path': out_path
        })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Hot-Folder Sync Daemon for CDP Two-Way Radio")
    parser.add_argument('--node', type=int, default=1, help="Node Address ID (e.g. 1)")
    parser.add_argument('--tx-port', type=int, default=52001, help="UDP target port to GNU Radio app_in")
    parser.add_argument('--rx-port', type=int, default=52002, help="UDP listen port from GNU Radio app_out")
    parser.add_argument('--dir', type=str, default=None, help="Custom transfers root directory")
    args = parser.parse_args()

    daemon = FolderSyncDaemon(node_id=args.node, tx_port=args.tx_port, rx_port=args.rx_port, base_dir=args.dir)
    daemon.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping daemon...")
        daemon.stop()
