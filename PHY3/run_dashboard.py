#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY3 Hardware Dashboard Launcher
Rebuilds the hardware SDR dashboard and serves it via a local web server.
"""

import sys
import os
import webbrowser
import http.server
import socketserver
import threading
import argparse

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, WORKSPACE_ROOT)

from PHY3.dashboard.build_dashboard import build_hardware_dashboard

DASH_DIR = os.path.join(os.path.dirname(__file__), "dashboard")

def launch_server(port=8082):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=DASH_DIR, **kwargs)
        def log_message(self, format, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    for p in range(port, port + 20):
        try:
            httpd = socketserver.TCPServer(("", p), QuietHandler)
            print(f"\n================================================================================")
            print(f" 📡 PHY3 HARDWARE SDR DASHBOARD SERVER RUNNING")
            print(f" 🌐 URL: http://localhost:{p}/hardware_dashboard.html")
            print(f" Press Ctrl+C to stop the dashboard server.")
            print(f"================================================================================\n")
            try:
                webbrowser.open(f"http://localhost:{p}/hardware_dashboard.html")
            except Exception:
                pass
            httpd.serve_forever()
            break
        except OSError:
            continue

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PHY3 Hardware SDR Dashboard Launcher")
    parser.add_argument('--port', type=int, default=8082, help="HTTP Server Port (default: 8082)")
    args = parser.parse_args()
    
    build_hardware_dashboard()
    launch_server(port=args.port)
