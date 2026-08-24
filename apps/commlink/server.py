#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Commlink Backend Server
=======================
Self-contained multi-threaded HTTP + SSE Server for the Commlink Two-Way Radio GUI.
Manages:
- User accounts and sessions (SQLite database)
- Active Node Address configuration
- Automated FolderSyncDaemon lifecycle (starts on user login, terminates on exit)
- Real-time RX directory monitoring and Server-Sent Events (SSE) live updates
- REST APIs for messaging, file attachment uploads, and media streaming
"""

import sys, os, time, json, sqlite3, hashlib, secrets, mimetypes, threading, signal, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

def parse_multipart(body: bytes, content_type: str):
    if 'boundary=' not in content_type:
        return {}, {}
    boundary = content_type.split('boundary=')[1].split(';')[0].strip().strip('"\'')
    boundary_bytes = ('--' + boundary).encode('utf-8')
    parts = body.split(boundary_bytes)
    fields = {}
    files = {}
    for part in parts:
        if not part or part.startswith(b'--'):
            continue
        if b'\r\n\r\n' in part:
            header_raw, content = part.split(b'\r\n\r\n', 1)
            if content.endswith(b'\r\n'):
                content = content[:-2]
            header_str = header_raw.decode('utf-8', errors='replace')
            name = None
            filename = None
            for line in header_str.split('\r\n'):
                if line.lower().startswith('content-disposition:'):
                    for item in line.split(';'):
                        item = item.strip()
                        if item.startswith('name='):
                            name = item[5:].strip('"\'')
                        elif item.startswith('filename='):
                            filename = item[9:].strip('"\'')
            if filename is not None:
                files[name] = {'filename': filename, 'bytes': content}
            elif name:
                fields[name] = content.decode('utf-8', errors='replace')
    return fields, files

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
COMMLINK_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(COMMLINK_DIR, 'static')
DATA_DIR = os.path.join(COMMLINK_DIR, 'data')
TRANSFERS_DIR = os.path.join(ROOT_DIR, 'transfers')

sys.path.insert(0, os.path.join(ROOT_DIR, 'apps'))
from folder_sync_daemon import FolderSyncDaemon, sha256_bytes

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRANSFERS_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, 'commlink.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            node_address INTEGER NOT NULL,
            created_at REAL NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user TEXT NOT NULL,
            src_node INTEGER NOT NULL,
            dst_node INTEGER NOT NULL,
            media_type INTEGER NOT NULL,
            filename TEXT,
            content TEXT,
            file_path TEXT,
            file_size INTEGER DEFAULT 0,
            sha256 TEXT,
            is_outgoing INTEGER NOT NULL,
            timestamp REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL DAEMON & SSE EVENT MANAGER (Multi-Node Support: Nodes 1-5)
# ─────────────────────────────────────────────────────────────────────────────
class AppStateManager:
    def __init__(self):
        self.daemons = {}
        self.active_node = None
        self.sse_clients = []
        self.lock = threading.RLock()
        self.rx_thread = None
        self.running = True

    @property
    def is_online(self) -> bool:
        return bool(self.daemons and any(d.running for d in self.daemons.values()))

    def ensure_all_node_folders(self):
        for node_id in range(1, 6):
            node_dir = os.path.join(TRANSFERS_DIR, f"node_{node_id}")
            os.makedirs(os.path.join(node_dir, "rx"), exist_ok=True)
            os.makedirs(os.path.join(node_dir, "tx_sent"), exist_ok=True)
            for target_id in range(1, 6):
                if target_id != node_id:
                    os.makedirs(os.path.join(node_dir, "tx", f"node_{target_id}"), exist_ok=True)
            os.makedirs(os.path.join(node_dir, "tx", "broadcast"), exist_ok=True)

    def start_all_nodes(self):
        with self.lock:
            self.ensure_all_node_folders()
            for node_id in range(1, 6):
                if node_id not in self.daemons or not self.daemons[node_id].running:
                    tx_port = 52000 + (node_id * 2) - 1
                    rx_port = 52000 + (node_id * 2)
                    d = FolderSyncDaemon(node_id=node_id, tx_port=tx_port, rx_port=rx_port, poll_interval=0.2)
                    d.start()
                    self.daemons[node_id] = d

            if self.rx_thread is None or not self.rx_thread.is_alive():
                self.rx_thread = threading.Thread(target=self._rx_monitor_loop, daemon=True)
                self.rx_thread.start()

    def set_active_node(self, node_id: int):
        with self.lock:
            self.active_node = node_id
            self.start_all_nodes()
            tx_port = 52000 + (node_id * 2) - 1
            rx_port = 52000 + (node_id * 2)
            self.broadcast_event('status', {'node': node_id, 'status': 'ONLINE', 'tx_port': tx_port, 'rx_port': rx_port})

    def stop_all(self):
        self.running = False
        with self.lock:
            for node_id, d in list(self.daemons.items()):
                try:
                    d.stop()
                except Exception as e:
                    pass
            self.daemons.clear()

    def broadcast_event(self, event_type: str, data: dict):
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        with self.lock:
            dead_clients = []
            for client_queue in self.sse_clients:
                try:
                    client_queue.put_nowait(msg)
                except:
                    dead_clients.append(client_queue)
            for dc in dead_clients:
                if dc in self.sse_clients:
                    self.sse_clients.remove(dc)

    def _rx_monitor_loop(self):
        seen_files = set()
        while self.running:
            try:
                # Scan all active node RX directories (1..5)
                for node_id in range(1, 6):
                    rx_dir = os.path.join(TRANSFERS_DIR, f"node_{node_id}", "rx")
                    if os.path.exists(rx_dir):
                        for fname in os.listdir(rx_dir):
                            fpath = os.path.join(rx_dir, fname)
                            if not os.path.isfile(fpath): continue
                            
                            # Check if file has already been processed
                            if fpath not in seen_files:
                                try:
                                    sz = os.path.getsize(fpath)
                                    time.sleep(0.05)
                                    if os.path.getsize(fpath) != sz: continue
                                except OSError:
                                    continue

                                seen_files.add(fpath)
                                self._ingest_received_file(node_id, fname, fpath)
            except Exception as e:
                print(f"[RX Monitor Error]: {e}")
            time.sleep(0.3)

    def _ingest_received_file(self, target_node: int, fname: str, fpath: str):
        # Filename format: from_node_<src_addr>_<orig_fname>
        src_node = 0
        orig_fname = fname
        if fname.startswith("from_node_"):
            parts = fname.split("_", 3)
            if len(parts) >= 4:
                try:
                    src_node = int(parts[2])
                    orig_fname = parts[3]
                except ValueError:
                    pass

        with open(fpath, "rb") as f:
            file_bytes = f.read()

        file_size = len(file_bytes)
        file_hash = sha256_bytes(file_bytes)
        ext = os.path.splitext(orig_fname)[1].lower()

        media_type = 0x01 if ext in ['.txt', '.json', '.csv', '.log'] else \
                     0x02 if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'] else \
                     0x03 if ext in ['.wav', '.mp3', '.opus', '.pcm', '.ogg'] else 0x04

        content_text = ""
        if media_type == 0x01: # Text message
            try:
                content_text = file_bytes.decode('utf-8', errors='replace')
            except:
                content_text = f"[Text File: {orig_fname}]"

        conn = get_db()
        cur = conn.cursor()
        
        # Check users registered under this destination node
        cur.execute('SELECT username FROM users WHERE node_address = ?', (target_node,))
        rows = cur.fetchall()
        user_list = [r[0] for r in rows]
        if not user_list:
            user_list = [f"station_{target_node}"]

        for uname in user_list:
            cur.execute('''
                INSERT INTO messages (owner_user, src_node, dst_node, media_type, filename, content, file_path, file_size, sha256, is_outgoing, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            ''', (uname, src_node, target_node, media_type, orig_fname, content_text, fpath, file_size, file_hash, time.time()))
            msg_id = cur.lastrowid
            
            # Broadcast live SSE update to UI
            self.broadcast_event('new_message', {
                'id': msg_id,
                'owner_user': uname,
                'src_node': src_node,
                'dst_node': target_node,
                'media_type': media_type,
                'filename': orig_fname,
                'content': content_text,
                'file_size': file_size,
                'sha256': file_hash,
                'is_outgoing': False,
                'timestamp': time.time()
            })
        conn.commit()
        conn.close()
        print(f"[Commlink RX Ingest] '{orig_fname}' ({file_size}B) from Node {src_node} -> Node {target_node} stored & broadcast!")

STATE = AppStateManager()

# ─────────────────────────────────────────────────────────────────────────────
# HTTP REQUEST HANDLER
# ─────────────────────────────────────────────────────────────────────────────
class CommlinkHTTPHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code: int, data: dict):
        payload = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Connection', 'close')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def get_auth_user(self):
        auth_header = self.headers.get('Authorization', '')
        token = ''
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        else:
            cookie_header = self.headers.get('Cookie', '')
            for c in cookie_header.split(';'):
                if 'commlink_token=' in c:
                    token = c.split('commlink_token=')[1].strip()

        if not token:
            qs = parse_qs(urlparse(self.path).query)
            token = qs.get('token', [''])[0]

        if not token:
            return None

        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            SELECT u.username, u.display_name, u.node_address
            FROM sessions s
            JOIN users u ON s.username = u.username
            WHERE s.token = ?
        ''', (token,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {'username': row[0], 'display_name': row[1], 'node_address': row[2]}
        return None

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Server-Sent Events (SSE) Live Feed
        if path == '/api/events':
            import queue
            client_queue = queue.Queue(maxsize=50)
            with STATE.lock:
                STATE.sse_clients.append(client_queue)

            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Initial status ping
            init_msg = f"event: status\ndata: {json.dumps({'node': STATE.active_node, 'status': 'ONLINE' if STATE.is_online else 'OFFLINE'})}\n\n"
            self.wfile.write(init_msg.encode('utf-8'))
            self.wfile.flush()

            try:
                while STATE.running:
                    try:
                        msg = client_queue.get(timeout=2.0)
                        self.wfile.write(msg.encode('utf-8'))
                        self.wfile.flush()
                    except queue.Empty:
                        # Keep-alive heartbeat
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except (ConnectionResetError, BrokenPipeError):
                pass
            finally:
                with STATE.lock:
                    if client_queue in STATE.sse_clients:
                        STATE.sse_clients.remove(client_queue)
            return

        # 2. Authenticated Profile Info
        if path == '/api/me':
            user = self.get_auth_user()
            if not user:
                return self.send_json(401, {'error': 'Unauthorized'})
            STATE.set_active_node(user['node_address'])
            return self.send_json(200, {
                'user': user,
                'radio_status': 'ONLINE' if STATE.is_online else 'IDLE'
            })

        # 3. Known Contacts List
        if path == '/api/contacts':
            user = self.get_auth_user()
            if not user:
                return self.send_json(401, {'error': 'Unauthorized'})

            conn = get_db()
            cur = conn.cursor()
            cur.execute('SELECT username, display_name, node_address FROM users WHERE node_address != ?', (user['node_address'],))
            contacts = []
            registered_addrs = set()
            for r in cur.fetchall():
                contacts.append({'username': r[0], 'display_name': r[1], 'node_address': r[2]})
                registered_addrs.add(r[2])
            conn.close()

            # Always populate standard nodes 1..5 in the channel list
            for i in range(1, 6):
                if i != user['node_address'] and i not in registered_addrs:
                    contacts.append({'username': f'station_{i}', 'display_name': f'Radio Station {i}', 'node_address': i})

            contacts.sort(key=lambda c: c['node_address'])
            return self.send_json(200, {'contacts': contacts})

        # 4. Message History with Destination Node
        if path == '/api/messages':
            user = self.get_auth_user()
            if not user:
                return self.send_json(401, {'error': 'Unauthorized'})

            qs = parse_qs(parsed.query)
            dst_node_str = qs.get('dst', [''])[0]
            if not dst_node_str:
                return self.send_json(400, {'error': 'Missing dst query parameter'})

            try:
                target_node = int(dst_node_str)
            except ValueError:
                return self.send_json(400, {'error': 'Invalid dst node ID'})

            conn = get_db()
            cur = conn.cursor()
            cur.execute('''
                SELECT id, src_node, dst_node, media_type, filename, content, file_size, sha256, is_outgoing, timestamp
                FROM messages
                WHERE owner_user = ? AND ((src_node = ? AND dst_node = ?) OR (src_node = ? AND dst_node = ?) OR dst_node = 0)
                ORDER BY timestamp ASC
            ''', (user['username'], user['node_address'], target_node, target_node, user['node_address']))
            
            msgs = []
            for r in cur.fetchall():
                msgs.append({
                    'id': r[0],
                    'src_node': r[1],
                    'dst_node': r[2],
                    'media_type': r[3],
                    'filename': r[4],
                    'content': r[5],
                    'file_size': r[6],
                    'sha256': r[7],
                    'is_outgoing': bool(r[8]),
                    'timestamp': r[9]
                })
            conn.close()
            return self.send_json(200, {'messages': msgs})

        # 5. Media Stream/Download Endpoint
        if path.startswith('/api/media/'):
            try:
                msg_id = int(path.split('/')[-1])
            except ValueError:
                return self.send_json(400, {'error': 'Invalid message ID'})

            conn = get_db()
            cur = conn.cursor()
            cur.execute('SELECT filename, file_path FROM messages WHERE id = ?', (msg_id,))
            row = cur.fetchone()
            conn.close()

            if not row or not row[1] or not os.path.exists(row[1]):
                return self.send_json(404, {'error': 'File not found on radio storage'})

            fname, fpath = row[0], row[1]
            mime_type, _ = mimetypes.guess_type(fname)
            if not mime_type: mime_type = 'application/octet-stream'

            file_size = os.path.getsize(fpath)
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Content-Disposition', f'inline; filename="{fname}"')
            self.end_headers()

            with open(fpath, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
            return

        # 6. Static File Serving
        if path == '/' or path == '':
            path = '/index.html'

        static_file = os.path.join(STATIC_DIR, path.lstrip('/'))
        if os.path.exists(static_file) and os.path.isfile(static_file):
            mime_type, _ = mimetypes.guess_type(static_file)
            if not mime_type: mime_type = 'text/plain'

            with open(static_file, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_json(404, {'error': 'Not Found'})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Sign Up Endpoint
        if path == '/api/signup':
            body = self._read_json_body()
            username = body.get('username', '').strip().lower()
            password = body.get('password', '').strip()
            display_name = body.get('display_name', '').strip()
            node_addr = body.get('node_address', 0)

            if not username or not password or not display_name or not (1 <= node_addr <= 254):
                return self.send_json(400, {'error': 'Invalid registration fields. Node address must be 1..254.'})

            pw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute('''
                    INSERT INTO users (username, password_hash, display_name, node_address, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, pw_hash, display_name, node_addr, time.time()))
                token = secrets.token_hex(24)
                cur.execute('INSERT INTO sessions (token, username, created_at) VALUES (?, ?, ?)', (token, username, time.time()))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                return self.send_json(409, {'error': 'Username already registered.'})
            conn.close()

            STATE.set_active_node(node_addr)
            return self.send_json(200, {
                'token': token,
                'user': {'username': username, 'display_name': display_name, 'node_address': node_addr}
            })

        # 2. Login Endpoint
        if path == '/api/login':
            body = self._read_json_body()
            username = body.get('username', '').strip().lower()
            password = body.get('password', '').strip()

            pw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            conn = get_db()
            cur = conn.cursor()
            cur.execute('SELECT username, display_name, node_address FROM users WHERE username = ? AND password_hash = ?', (username, pw_hash))
            row = cur.fetchone()
            if not row:
                conn.close()
                return self.send_json(401, {'error': 'Invalid username or password.'})

            token = secrets.token_hex(24)
            cur.execute('INSERT INTO sessions (token, username, created_at) VALUES (?, ?, ?)', (token, username, time.time()))
            conn.commit()
            conn.close()

            STATE.set_active_node(row[2])
            return self.send_json(200, {
                'token': token,
                'user': {'username': row[0], 'display_name': row[1], 'node_address': row[2]}
            })

        # 3. Logout Endpoint
        if path == '/api/logout':
            user = self.get_auth_user()
            if user:
                conn = get_db()
                cur = conn.cursor()
                cur.execute('DELETE FROM sessions WHERE username = ?', (user['username'],))
                conn.commit()
                conn.close()
            return self.send_json(200, {'message': 'Logged out successfully'})

        # 4. Send Message / Attachment Endpoint
        if path == '/api/send':
            user = self.get_auth_user()
            if not user:
                return self.send_json(401, {'error': 'Unauthorized'})

            # Parse multipart or JSON
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type:
                return self._handle_multipart_send(user)
            else:
                body = self._read_json_body()
                return self._handle_json_send(user, body)

        # 5. Clear Channel / Chat History & Staged Files Endpoint
        if path == '/api/chat/clear':
            user = self.get_auth_user()
            if not user:
                return self.send_json(401, {'error': 'Unauthorized'})
            
            body = self._read_json_body()
            target_node = int(body.get('dst_node', 0))
            src_node = user['node_address']

            # Clear messages from database
            conn = get_db()
            cur = conn.cursor()
            if target_node == 0:
                cur.execute('DELETE FROM messages WHERE owner_user = ? AND dst_node = 0', (user['username'],))
            else:
                cur.execute('''
                    DELETE FROM messages 
                    WHERE owner_user = ? AND ((src_node = ? AND dst_node = ?) OR (src_node = ? AND dst_node = ?))
                ''', (user['username'], src_node, target_node, target_node, src_node))
            conn.commit()
            conn.close()

            # Clean folder files for this node channel
            dst_folder = "broadcast" if target_node == 0 else f"node_{target_node}"
            tx_path = os.path.join(TRANSFERS_DIR, f"node_{src_node}", "tx", dst_folder)
            if os.path.exists(tx_path):
                for f in os.listdir(tx_path):
                    try: os.remove(os.path.join(tx_path, f))
                    except: pass

            rx_path = os.path.join(TRANSFERS_DIR, f"node_{src_node}", "rx")
            if os.path.exists(rx_path):
                for f in os.listdir(rx_path):
                    if target_node == 0 or f"from_node_{target_node}_" in f:
                        try: os.remove(os.path.join(rx_path, f))
                        except: pass

            print(f"[Commlink] Cleared chat history and folders for Node {src_node} <-> Channel {target_node}")
            return self.send_json(200, {'message': 'Chat history and staged files cleared.'})

        self.send_json(404, {'error': 'Not Found'})

    def _read_json_body(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            return json.loads(raw.decode('utf-8'))
        except:
            return {}

    def _handle_json_send(self, user: dict, body: dict):
        dst_node = body.get('dst_node', 0)
        text_content = body.get('text', '').strip()

        if not text_content or not (0 <= dst_node <= 254):
            return self.send_json(400, {'error': 'Missing text content or invalid destination node'})

        src_node = user['node_address']
        ts = time.time()
        fname = f"msg_{int(ts*1000)}.txt"
        file_bytes = text_content.encode('utf-8')
        file_size = len(file_bytes)
        file_hash = sha256_bytes(file_bytes)

        # Target TX Directory
        dst_folder = "broadcast" if dst_node == 0 else f"node_{dst_node}"
        tx_dir = os.path.join(TRANSFERS_DIR, f"node_{src_node}", "tx", dst_folder)
        os.makedirs(tx_dir, exist_ok=True)
        tx_fpath = os.path.join(tx_dir, fname)

        with open(tx_fpath, "wb") as f:
            f.write(file_bytes)

        # Store in database
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO messages (owner_user, src_node, dst_node, media_type, filename, content, file_path, file_size, sha256, is_outgoing, timestamp)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, 1, ?)
        ''', (user['username'], src_node, dst_node, fname, text_content, tx_fpath, file_size, file_hash, ts))
        msg_id = cur.lastrowid
        conn.commit()
        conn.close()

        msg_obj = {
            'id': msg_id,
            'src_node': src_node,
            'dst_node': dst_node,
            'media_type': 1,
            'filename': fname,
            'content': text_content,
            'file_size': file_size,
            'sha256': file_hash,
            'is_outgoing': True,
            'timestamp': ts
        }
        STATE.broadcast_event('new_message', msg_obj)
        print(f"[Commlink TX Text] User '{user['username']}' (Node {src_node}) -> Node {dst_node}: '{text_content[:40]}...'")
        return self.send_json(200, {'message': 'Sent', 'data': msg_obj})

    def _handle_multipart_send(self, user: dict):
        length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(length)
        content_type = self.headers.get('Content-Type', '')

        fields, files = parse_multipart(raw_body, content_type)

        dst_node_str = fields.get('dst_node', '0')
        text_content = fields.get('text', '').strip()
        file_item = files.get('file')

        try:
            dst_node = int(dst_node_str)
        except ValueError:
            return self.send_json(400, {'error': 'Invalid destination node ID'})

        if not file_item or not file_item.get('bytes'):
            return self.send_json(400, {'error': 'No attachment provided'})

        fname = os.path.basename(file_item['filename'])
        file_bytes = file_item['bytes']
        file_size = len(file_bytes)

        if file_size > 50 * 1024 * 1024:
            return self.send_json(400, {'error': 'File exceeds maximum limit of 50 MB'})

        ext = os.path.splitext(fname)[1].lower()
        allowed_exts = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.pdf', '.wav', '.mp3', '.ogg', '.opus', '.txt', '.json', '.csv']
        if ext not in allowed_exts:
            return self.send_json(400, {'error': f"Unsupported file type '{ext}'. Allowed: Images, PDFs, Audio, Text."})

        media_type = 0x01 if ext in ['.txt', '.json', '.csv'] else \
                     0x02 if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'] else \
                     0x03 if ext in ['.wav', '.mp3', '.opus', '.ogg'] else 0x04 # PDF / Doc

        src_node = user['node_address']
        ts = time.time()
        file_hash = sha256_bytes(file_bytes)

        # Write to node tx directory
        dst_folder = "broadcast" if dst_node == 0 else f"node_{dst_node}"
        tx_dir = os.path.join(TRANSFERS_DIR, f"node_{src_node}", "tx", dst_folder)
        os.makedirs(tx_dir, exist_ok=True)
        tx_fpath = os.path.join(tx_dir, fname)

        with open(tx_fpath, "wb") as f:
            f.write(file_bytes)

        # Store in database
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO messages (owner_user, src_node, dst_node, media_type, filename, content, file_path, file_size, sha256, is_outgoing, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ''', (user['username'], src_node, dst_node, media_type, fname, text_content, tx_fpath, file_size, file_hash, ts))
        msg_id = cur.lastrowid
        conn.commit()
        conn.close()

        msg_obj = {
            'id': msg_id,
            'src_node': src_node,
            'dst_node': dst_node,
            'media_type': media_type,
            'filename': fname,
            'content': text_content,
            'file_size': file_size,
            'sha256': file_hash,
            'is_outgoing': True,
            'timestamp': ts
        }
        STATE.broadcast_event('new_message', msg_obj)
        print(f"[Commlink TX Attachment] User '{user['username']}' (Node {src_node}) -> Node {dst_node}: '{fname}' ({file_size}B)")
        return self.send_json(200, {'message': 'Sent', 'data': msg_obj})

# ─────────────────────────────────────────────────────────────────────────────
# SERVER ENTRYPOINT & GRACEFUL LIFECYCLE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
def run_server(port=8080):
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, CommlinkHTTPHandler)

    def shutdown_signal(sig, frame):
        print("\n[Commlink] Gracefully shutting down server and managed radio daemons...")
        STATE.stop_all()
        threading.Thread(target=httpd.shutdown).start()

    signal.signal(signal.SIGINT, shutdown_signal)
    signal.signal(signal.SIGTERM, shutdown_signal)

    print("=" * 80)
    print(" 🚀 COMMLINK TWO-WAY RADIO APPLICATION SERVER STARTED")
    print(f"    Web Interface : http://localhost:{port}")
    print(f"    Transfers Dir : {TRANSFERS_DIR}")
    print(f"    Database      : {DB_PATH}")
    print("=" * 80)

    try:
        httpd.serve_forever()
    finally:
        STATE.stop_all()
        print("[Commlink] All radio daemons and background threads closed cleanly.")

if __name__ == '__main__':
    port = 8080
    if len(sys.argv) > 1:
        try: port = int(sys.argv[1])
        except: pass
    run_server(port)
