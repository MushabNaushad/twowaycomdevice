#!/bin/bash
# ==============================================================================
# Commlink Two-Way Radio Full Stack Launcher
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$DIR/blocks/gr-transport/build/lib:$LD_LIBRARY_PATH"

PORT=8080
if [ -n "$1" ]; then
    PORT=$1
fi

echo "================================================================================"
echo " 🚀 LAUNCHING COMMLINK TWO-WAY RADIO FULL STACK"
echo "    Web GUI URL    : http://localhost:$PORT"
echo "    Radio Flowgraph: commlink_radio.grc"
echo "================================================================================"

# Trap termination signals to ensure clean shutdown
cleanup() {
    echo ""
    echo "[Commlink Launcher] Shutting down Commlink server, radio flowgraph, and managed daemons..."
    kill "$SERVER_PID" 2>/dev/null
    kill "$GR_PID" 2>/dev/null
    wait "$SERVER_PID" 2>/dev/null
    wait "$GR_PID" 2>/dev/null
    echo "[Commlink Launcher] All processes stopped. Clean exit."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Clean up any lingering processes on radio ports
fuser -k 52001/tcp 52002/tcp 52003/tcp 52004/tcp 52005/tcp 52006/tcp 52007/tcp 52008/tcp 52009/tcp 52010/tcp "$PORT/tcp" 2>/dev/null || true
sleep 0.3

# 1. Start GNU Radio Flowgraph in background
echo "[1/2] Starting GNU Radio In-Band Transport Flowgraph (commlink_radio.py)..."
python3 "$DIR/commlink_radio.py" > /dev/null 2>&1 &
GR_PID=$!
sleep 1.0

# 2. Start Commlink Web Application Server in background
echo "[2/2] Starting Commlink Web Application Server & Hot-Folder Daemons..."
python3 "$DIR/apps/commlink/server.py" "$PORT" &
SERVER_PID=$!

sleep 1.2

# 3. Open browser if available
if command -v xdg-open > /dev/null; then
    xdg-open "http://localhost:$PORT" 2>/dev/null &
elif command -v sensible-browser > /dev/null; then
    sensible-browser "http://localhost:$PORT" 2>/dev/null &
fi

echo ""
echo "✨ COMMLINK SYSTEM READY!"
echo "   Access in browser: http://localhost:$PORT"
echo "   Press Ctrl+C to stop all radio processes and servers."
echo ""

# Wait on the server process
wait "$SERVER_PID"
