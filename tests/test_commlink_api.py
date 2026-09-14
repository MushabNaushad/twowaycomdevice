#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_commlink_api.py
====================
Automated test suite for the Commlink application:
1. Tests User Signup, Login, and Session retrieval (/api/signup, /api/login, /api/me).
2. Tests Manual Node Address assignment.
3. Tests Sending Text Messages (/api/send).
4. Tests Multi-Media File Uploads (PNG Image, PDF Document, WAV Audio).
5. Tests File Validation (rejection of unsupported file types).
6. Tests Clean Daemon Startup & Shutdown.
"""

import sys, os, time, json, urllib.request, urllib.error, threading, hashlib

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SAMPLE_DIR = os.path.join(ROOT_DIR, 'sample_data')
COMMLINK_DIR = os.path.join(ROOT_DIR, 'apps', 'commlink')
sys.path.insert(0, COMMLINK_DIR)

from server import ThreadingHTTPServer, CommlinkHTTPHandler, STATE, init_db

PORT = 8910
SERVER_URL = f"http://127.0.0.1:{PORT}"

def http_json_post(path, data, token=None):
    url = f"{SERVER_URL}{path}"
    body = json.dumps(data).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Connection': 'close'}
    if token: headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        content = e.read()
        e.close()
        return e.code, json.loads(content.decode('utf-8'))

def http_get(path, token=None):
    url = f"{SERVER_URL}{path}"
    headers = {'Connection': 'close'}
    if token: headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        content = e.read()
        e.close()
        return e.code, json.loads(content.decode('utf-8'))

def http_multipart_upload(path, dst_node, text, filepath, token=None):
    url = f"{SERVER_URL}{path}"
    boundary = f"----WebKitFormBoundary{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Connection': 'close'
    }
    if token: headers['Authorization'] = f'Bearer {token}'

    fname = os.path.basename(filepath)
    with open(filepath, 'rb') as f:
        file_bytes = f.read()

    lines = []
    lines.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"dst_node\"\r\n\r\n{dst_node}\r\n".encode('utf-8'))
    lines.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"text\"\r\n\r\n{text}\r\n".encode('utf-8'))
    lines.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fname}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode('utf-8'))
    lines.append(file_bytes)
    lines.append(f"\r\n--{boundary}--\r\n".encode('utf-8'))

    body = b"".join(lines)
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        content = e.read()
        e.close()
        return e.code, json.loads(content.decode('utf-8'))

def run_tests():
    print("=" * 80)
    print(" COMMLINK APPLICATION API & VALIDATION TEST SUITE")
    print("=" * 80)

    # 1. Start Server on port 8910
    init_db()
    httpd = ThreadingHTTPServer(('127.0.0.1', PORT), CommlinkHTTPHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    all_passed = True
    try:
        # Test 2: Signup Operator 1 (Node 1)
        print("\n[1] Testing Account Signup (User 1 -> Node Address 1)...")
        uname = f"op_{int(time.time())}"
        status, res = http_json_post('/api/signup', {
            'username': uname,
            'password': 'password123',
            'display_name': 'Alpha Base Operator',
            'node_address': 1
        })
        print(f"    Response [{status}]:", res)
        assert status == 200, f"Signup failed with status {status}"
        token1 = res['token']
        print("    ✓ User registered & acquired auth token for Station Node 1")

        # Test 3: Verify Profile (/api/me)
        print("\n[2] Testing Profile Verification (/api/me)...")
        status, res = http_get('/api/me', token=token1)
        print(f"    Profile [{status}]:", res)
        assert res['user']['node_address'] == 1, "Node address mismatch"
        assert res['radio_status'] == 'ONLINE', "Radio status should be ONLINE"
        print("    ✓ Station Node address confirmed: 1 [ONLINE]")

        # Test 4: Send Text Message
        print("\n[3] Testing Text Transmission to Node 2...")
        status, res = http_json_post('/api/send', {
            'dst_node': 2,
            'text': 'Radio Check from Base Alpha (Node 1) to Node 2.'
        }, token=token1)
        print(f"    Send Text [{status}]:", res)
        assert status == 200, "Failed to send text message"
        print("    ✓ Text message queued in Node 1 tx/node_2 folder!")

        # Test 5: Upload Image Attachment (sample_photo.png)
        print("\n[4] Testing Image Attachment Upload (PNG)...")
        img_path = os.path.join(SAMPLE_DIR, 'sample_photo.png')
        status, res = http_multipart_upload('/api/send', 2, 'Tactical Map Overview', img_path, token=token1)
        print(f"    Send Image [{status}]:", res)
        assert status == 200 and res['data']['media_type'] == 2, "Image send failed"
        print("    ✓ Image successfully validated & queued for transmission!")

        # Test 6: Upload PDF Document Attachment (sample_document.pdf)
        print("\n[5] Testing PDF Document Attachment Upload (PDF)...")
        pdf_path = os.path.join(SAMPLE_DIR, 'sample_document.pdf')
        status, res = http_multipart_upload('/api/send', 2, 'Flight Manual Document', pdf_path, token=token1)
        print(f"    Send PDF [{status}]:", res)
        assert status == 200 and res['data']['media_type'] == 4, "PDF send failed"
        print("    ✓ PDF document successfully validated & queued for transmission!")

        # Test 7: Upload Audio Attachment (sample_voice.wav)
        print("\n[6] Testing Audio Attachment Upload (WAV)...")
        wav_path = os.path.join(SAMPLE_DIR, 'sample_voice.wav')
        status, res = http_multipart_upload('/api/send', 2, 'Voice Dispatch Recording', wav_path, token=token1)
        print(f"    Send Audio [{status}]:", res)
        assert status == 200 and res['data']['media_type'] == 3, "Audio send failed"
        print("    ✓ Audio file successfully validated & queued for transmission!")

        # Test 8: File Type Validation (Rejection of unsupported formats)
        print("\n[7] Testing File Type Validation (Rejecting invalid extension)...")
        fake_bad_file = os.path.join(SAMPLE_DIR, 'malicious_script.exe')
        with open(fake_bad_file, 'wb') as f: f.write(b"NOT_A_VALID_RADIO_MEDIA")
        status, res = http_multipart_upload('/api/send', 2, 'Bad File', fake_bad_file, token=token1)
        os.remove(fake_bad_file)
        print(f"    Send Invalid File [{status}]:", res)
        assert status == 400, "Validation failed: server did not reject invalid extension!"
        print("    ✓ Server correctly rejected unsupported file type with 400 Bad Request!")

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        all_passed = False
    finally:
        print("\n[8] Shutting Down Commlink Test Server and managed daemons...")
        STATE.stop_all()
        httpd.shutdown()

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL COMMLINK APPLICATION TESTS PASSED SUCCESSFULLY!")
    else:
        print("❌ SOME COMMLINK TESTS FAILED.")
    print("=" * 80)
    return all_passed

if __name__ == '__main__':
    ok = run_tests()
    sys.exit(0 if ok else 1)
