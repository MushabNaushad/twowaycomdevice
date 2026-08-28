#!/usr/bin/env python3
import sys, os, subprocess
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
master_script = os.path.join(root, "run_dashboard.py")
cmd = [sys.executable, master_script, "--mode", "software"] + sys.argv[1:]
sys.exit(subprocess.run(cmd).returncode)
