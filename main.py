#!/usr/bin/env python3
import sys, os, subprocess
root = os.path.dirname(os.path.abspath(__file__))
phy2_main = os.path.join(root, "PHY2/main.py")
sys.exit(subprocess.run([sys.executable, phy2_main] + sys.argv[1:]).returncode)
