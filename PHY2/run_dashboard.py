#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHY2 Master Dashboard Launcher & Local Server
Launches the interactive PHY2 physical layer dashboard in your local web browser.
Serves over HTTP to ensure 100% offline compatibility, zero CORS issues, and smooth dynamic rendering.
"""

import sys
import os
import http.server
import socketserver
import webbrowser
import threading
import time
import argparse

DASHBOARD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dashboard"))
INDEX_HTML = os.path.join(DASHBOARD_DIR, "index.html")

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)
        
    def log_message(self, format, *args):
        # Silent logging for cleaner CLI output
        pass

def launch_dashboard(port=8080, open_browser=True):
    # Ensure index.html exists
    if not os.path.exists(INDEX_HTML):
        print(f"[INFO] Building dashboard HTML...")
        from PHY2.dashboard.build_dashboard import build_master_dashboard
        build_master_dashboard()

    # Find an open port starting from `port`
    server = None
    actual_port = port
    for p in range(port, port + 50):
        try:
            server = socketserver.TCPServer(("", p), DashboardHandler)
            actual_port = p
            break
        except OSError:
            continue

    if server is None:
        print(f"[ERROR] Could not bind to any port near {port}.")
        sys.exit(1)

    url = f"http://127.0.0.1:{actual_port}/index.html"
    print("================================================================================")
    print("           PHY2 PHYSICAL LAYER INTERACTIVE DASHBOARD SERVER                     ")
    print("================================================================================")
    print(f" >>> Dashboard URL: {url}")
    print(" >>> Serving interactive graphs, dynamic FLL/Costas sliders, and CSV explorer.")
    print(" >>> Press Ctrl+C in this terminal to stop the server.")
    print("================================================================================")

    if open_browser:
        def _open():
            time.sleep(0.5)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Stopping dashboard server.")
        server.server_close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Launch PHY2 Interactive Dashboard")
    parser.add_argument('--port', type=int, default=8080, help="Port to serve dashboard on")
    parser.add_argument('--no-browser', action='store_true', help="Do not automatically open browser")
    args = parser.parse_args()

    launch_dashboard(port=args.port, open_browser=not args.no_browser)
