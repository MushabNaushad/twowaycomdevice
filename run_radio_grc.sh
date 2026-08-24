#!/bin/bash
# ==============================================================================
# GRC Execution Wrapper for Commlink Flowgraph
# ==============================================================================
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$DIR/blocks/gr-transport/build/lib:$LD_LIBRARY_PATH"

if [ -n "$1" ]; then
    python3 "$1"
else
    python3 "$DIR/commlink_radio.py"
fi
