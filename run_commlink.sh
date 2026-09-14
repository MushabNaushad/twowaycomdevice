#!/bin/bash
# ==============================================================================
# Commlink Two-Way Radio Full Stack Launcher (Visual GRC Integrated)
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$DIR/blocks/gr-transport/build/lib:$LD_LIBRARY_PATH"
export PYTHONPATH="$DIR/blocks/gr-transport/build/python:$PYTHONPATH"

# Pre-compile GRC flowgraph so Python script is always updated
grcc "$DIR/commlink_radio.grc" 2>/dev/null || true

PORT=8080
HEADLESS=false

for arg in "$@"; do
    if [ "$arg" == "--headless" ] || [ "$arg" == "-h" ]; then
        HEADLESS=true
    elif [[ "$arg" =~ ^[0-9]+$ ]]; then
        PORT=$arg
    fi
done

echo "================================================================================"
echo " 🚀 LAUNCHING COMMLINK TWO-WAY RADIO FULL STACK"
echo "    Web GUI URL    : http://localhost:$PORT"
echo "    GRC Flowgraph  : commlink_radio.grc"
echo "    Visual GRC Mode: $([ "$HEADLESS" = true ] && echo 'Disabled (Headless)' || echo 'Enabled (Opening GNU Radio Companion)')"
echo "================================================================================"

# Clean up any lingering processes on radio ports
fuser -k 52001/tcp 52002/tcp 52003/tcp 52004/tcp 52005/tcp 52006/tcp 52007/tcp 52008/tcp 52009/tcp 52010/tcp "$PORT/tcp" 2>/dev/null || true
sleep 0.3

# 0. Clean slate: purge old database messages & clear transfer directories for easy diagnosis
echo "[0/2] Cleaning previous session data (database messages & transfer folders)..."
python3 -c "
import sqlite3, os, shutil
db_path = '$DIR/apps/commlink/data/commlink.db'
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.execute('DELETE FROM messages')
        conn.commit()
        conn.close()
    except Exception as e:
        pass
" 2>/dev/null || true

# Rebuild fresh folder hierarchy for all 5 stations (Nodes 1-5)
for i in 1 2 3 4 5; do
    rm -rf "$DIR/transfers/node_$i/rx" "$DIR/transfers/node_$i/tx_sent" "$DIR/transfers/node_$i/tx"
    mkdir -p "$DIR/transfers/node_$i/rx" "$DIR/transfers/node_$i/tx_sent" "$DIR/transfers/node_$i/tx/broadcast"
    for j in 1 2 3 4 5; do
        if [ "$i" -ne "$j" ]; then
            mkdir -p "$DIR/transfers/node_$i/tx/node_$j"
        fi
    done
done

# Trap termination signals to ensure clean shutdown
cleanup() {
    echo ""
    echo "[Commlink Launcher] Shutting down Commlink server, managed daemons, and GRC..."
    kill "$SERVER_PID" 2>/dev/null
    kill "$GRC_PID" 2>/dev/null
    wait "$SERVER_PID" 2>/dev/null
    wait "$GRC_PID" 2>/dev/null
    echo "[Commlink Launcher] All processes stopped cleanly."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start Commlink Web Application Server in background
echo "[1/2] Starting Commlink Web Application Server & Hot-Folder Daemons..."
python3 "$DIR/apps/commlink/server.py" "$PORT" &
SERVER_PID=$!

sleep 1.0

# 2. Open browser
if command -v xdg-open > /dev/null; then
    xdg-open "http://localhost:$PORT" 2>/dev/null &
elif command -v sensible-browser > /dev/null; then
    sensible-browser "http://localhost:$PORT" 2>/dev/null &
fi

# 3. Launch GNU Radio Companion Flowgraph
if [ "$HEADLESS" = true ]; then
    echo "[2/2] Running GNU Radio Transport Flowgraph headlessly..."
    python3 "$DIR/commlink_radio.py" &
    GRC_PID=$!
    echo ""
    echo "✨ COMMLINK SYSTEM ACTIVE!"
    echo "   Access in browser: http://localhost:$PORT"
    echo "   Press Ctrl+C to exit."
    echo ""
    wait "$SERVER_PID"
else
    echo "[2/2] Opening GNU Radio Companion (commlink_radio.grc)..."
    echo "      👉 Click 'Execute (F6)' in GRC to start the radio channel!"
    echo ""
    echo "✨ COMMLINK SYSTEM ACTIVE!"
    echo "   Access in browser: http://localhost:$PORT"
    echo "   Press Ctrl+C or close GNU Radio Companion to exit."
    echo ""
    gnuradio-companion "$DIR/commlink_radio.grc" &
    GRC_PID=$!
    wait "$GRC_PID"
fi
