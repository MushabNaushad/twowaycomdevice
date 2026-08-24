#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_folder_sync_end2end.py
===========================
End-to-End Automated Test for Hot-Folder File Transfers over Radio (including 10MB+ files):
1. Starts GNU Radio test_socket_sync flowgraph in subprocess.
2. Starts FolderSyncDaemon for Node 1 and Node 2.
3. Copies sample files (Text, Image, PDF, Audio, and 10MB Large Image) into tx/ folders.
4. Verifies files are transferred over simulated radio channel and written to rx/.
5. Validates 100% SHA-256 hash match for all files.
"""

import sys, os, time, shutil, subprocess, hashlib

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SAMPLE_DIR = os.path.join(ROOT_DIR, 'sample_data')
TRANSFERS_DIR = os.path.join(ROOT_DIR, 'transfers')

sys.path.insert(0, os.path.join(ROOT_DIR, 'apps'))
from folder_sync_daemon import FolderSyncDaemon, sha256_bytes

def sha256_file(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def clean_dir(d):
    if os.path.exists(d):
        for item in os.listdir(d):
            p = os.path.join(d, item)
            if os.path.isfile(p): os.remove(p)
            elif os.path.isdir(p): shutil.rmtree(p)
    os.makedirs(d, exist_ok=True)

def run_end2end_test():
    print("=" * 80)
    print("END-TO-END HOT-FOLDER MULTI-MEGABYTE FILE TRANSMISSION TEST (10MB+ Support)")
    print("=" * 80)

    # 1. Clean transfer directories
    n1_tx_n2 = os.path.join(TRANSFERS_DIR, 'node_1', 'tx', 'node_2')
    n1_rx = os.path.join(TRANSFERS_DIR, 'node_1', 'rx')
    n1_sent = os.path.join(TRANSFERS_DIR, 'node_1', 'tx_sent')
    
    n2_tx_n1 = os.path.join(TRANSFERS_DIR, 'node_2', 'tx', 'node_1')
    n2_rx = os.path.join(TRANSFERS_DIR, 'node_2', 'rx')
    n2_sent = os.path.join(TRANSFERS_DIR, 'node_2', 'tx_sent')

    clean_dir(n1_tx_n2)
    clean_dir(n1_rx)
    clean_dir(n1_sent)
    clean_dir(n2_tx_n1)
    clean_dir(n2_rx)
    clean_dir(n2_sent)

    # 2. Launch GNU Radio Flowgraph in subprocess
    runner_sh = os.path.join(ROOT_DIR, 'tests', 'run_socket_sync.sh')
    py_script = os.path.join(ROOT_DIR, 'tests', 'test_socket_sync.py')
    gr_log_path = os.path.join(ROOT_DIR, 'tests', 'gr_flowgraph.log')
    gr_log_file = open(gr_log_path, 'w')

    print("\n[1] Starting GNU Radio ZeroMQ Flowgraph...")
    gr_proc = subprocess.Popen(
        [runner_sh, py_script],
        stdout=gr_log_file,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    time.sleep(2.0) # Allow sockets and GNU Radio FSM to initialize

    # 3. Start Node 1 and Node 2 Folder Sync Daemons
    print("\n[2] Starting Hot-Folder Sync Daemons:")
    daemon1 = FolderSyncDaemon(node_id=1, tx_port=52001, rx_port=52002, poll_interval=0.2)
    daemon2 = FolderSyncDaemon(node_id=2, tx_port=52003, rx_port=52004, poll_interval=0.2)

    daemon1.start()
    daemon2.start()
    time.sleep(0.5)

    test_files = [
        'sample_memo.txt',
        'sample_document.pdf',
        'sample_photo.png',
        'sample_voice.wav',
        'sample_large_10mb.jpg'
    ]

    all_passed = True
    results = []

    # 4. Transmit Files from Node 1 -> Node 2
    print("\n[3] Testing Forward Transfer (Node 1 -> Node 2):")
    for fname in test_files:
        src_file = os.path.join(SAMPLE_DIR, fname)
        dst_file_expected = os.path.join(n2_rx, f"from_node_1_{fname}")
        orig_hash = sha256_file(src_file)
        file_size = os.path.getsize(src_file)
        mb_str = f"{file_size/(1024*1024):.2f} MB" if file_size >= 1024*1024 else f"{file_size/1024:.1f} KB"

        print(f"\n  ---> Dropping '{fname}' ({mb_str}, {file_size:,} bytes) into node_1/tx/node_2/...")
        shutil.copy2(src_file, os.path.join(n1_tx_n2, fname))

        # Wait for delivery
        timeout = 25.0 # up to 25s for 10MB across ARQ window
        t0 = time.time()
        delivered = False
        while time.time() - t0 < timeout:
            if os.path.exists(dst_file_expected) and os.path.getsize(dst_file_expected) == file_size:
                delivered = True
                break
            time.sleep(0.1)

        if delivered:
            recv_hash = sha256_file(dst_file_expected)
            hash_match = (orig_hash == recv_hash)
            elapsed = time.time() - t0
            rate_kb = (file_size / 1024) / elapsed if elapsed > 0 else 0
            print(f"  ✓ RECEIVED '{fname}' at Node 2 in {elapsed:.2f}s ({rate_kb:.1f} KB/s)! Hash Match: {hash_match}")
            results.append((fname, "Node 1 -> Node 2", file_size, elapsed, hash_match))
            if not hash_match: all_passed = False
        else:
            print(f"  ❌ TIMEOUT: '{fname}' was not received at Node 2 within {timeout}s!")
            results.append((fname, "Node 1 -> Node 2", file_size, 0, False))
            all_passed = False

        time.sleep(1.5)

    # 5. Transmit Reverse 10MB File from Node 2 -> Node 1
    print("\n[4] Testing Reverse Multi-Megabyte Transfer (Node 2 -> Node 1):")
    rev_files = ['sample_large_10mb.jpg']
    for fname in rev_files:
        src_file = os.path.join(SAMPLE_DIR, fname)
        dst_file_expected = os.path.join(n1_rx, f"from_node_2_{fname}")
        orig_hash = sha256_file(src_file)
        file_size = os.path.getsize(src_file)
        mb_str = f"{file_size/(1024*1024):.2f} MB"

        print(f"\n  ---> Dropping '{fname}' ({mb_str}) into node_2/tx/node_1/...")
        shutil.copy2(src_file, os.path.join(n2_tx_n1, fname))

        timeout = 25.0
        t0 = time.time()
        delivered = False
        while time.time() - t0 < timeout:
            if os.path.exists(dst_file_expected) and os.path.getsize(dst_file_expected) == file_size:
                delivered = True
                break
            time.sleep(0.1)

        if delivered:
            recv_hash = sha256_file(dst_file_expected)
            hash_match = (orig_hash == recv_hash)
            elapsed = time.time() - t0
            rate_kb = (file_size / 1024) / elapsed if elapsed > 0 else 0
            print(f"  ✓ RECEIVED '{fname}' at Node 1 in {elapsed:.2f}s ({rate_kb:.1f} KB/s)! Hash Match: {hash_match}")
            results.append((fname, "Node 2 -> Node 1", file_size, elapsed, hash_match))
            if not hash_match: all_passed = False
        else:
            print(f"  ❌ TIMEOUT: '{fname}' was not received at Node 1 within {timeout}s!")
            results.append((fname, "Node 2 -> Node 1", file_size, 0, False))
            all_passed = False

        time.sleep(1.5)

    # 6. Stop Daemons and Flowgraph
    print("\n[5] Stopping Daemons & GNU Radio Process...")
    daemon1.stop()
    daemon2.stop()
    gr_proc.terminate()
    try: gr_proc.wait(timeout=2.0)
    except: gr_proc.kill()
    gr_log_file.close()

    # 7. Results Summary
    print("\n" + "=" * 85)
    print(" HOT-FOLDER MULTI-MEGABYTE FILE TRANSMISSION TEST RESULTS")
    print("=" * 85)
    print(f" {'Filename':<24} | {'Direction':<16} | {'Size':>12} | {'Time':>7} | {'Integrity (SHA-256)'}")
    print("-" * 85)
    for fname, direction, sz, elapsed, ok in results:
        status_str = "✅ 100% MATCH" if ok else "❌ FAILED"
        sz_str = f"{sz/(1024*1024):.2f} MB" if sz >= 1024*1024 else f"{sz:,} B"
        print(f" {fname:<24} | {direction:<16} | {sz_str:>12} | {elapsed:>6.2f}s | {status_str}")
    print("=" * 85)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED: 100% RELIABLE 10MB+ MULTI-MEGABYTE FILE TRANSMISSION CONFIRMED!")
    else:
        print("\n❌ SOME TRANSFERS FAILED.")

    return all_passed

if __name__ == '__main__':
    ok = run_end2end_test()
    sys.exit(0 if ok else 1)
