#!/usr/bin/env bash
# run_sweep_all.sh — Run all 20 (m, mtu) parameter combinations sequentially.
# Must be run from a GNOME/desktop terminal (not an IDE subprocess).
#
# Usage:
#   cd /path/to/twowaycomdevice
#   bash tests/perf_sweep/run_sweep_all.sh
#
# Each run opens a small window and closes it automatically.
# Total time: ~212s × 20 = ~71 minutes.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

M_VALUES=(3 4 5 6 7)
MTU_VALUES=(100 200 500 1000)

total=$(( ${#M_VALUES[@]} * ${#MTU_VALUES[@]} ))
run=0

echo "============================================================"
echo "  Transport Layer Parameter Sweep — $total combinations"
echo "  strobe=6s  phase=42s×5  payload=8KB  pairs=5"
echo "  Estimated total time: ~71 minutes"
echo "  Output: $SCRIPT_DIR"
echo "============================================================"
echo ""

for m in "${M_VALUES[@]}"; do
  for mtu in "${MTU_VALUES[@]}"; do
    run=$(( run + 1 ))
    out="$SCRIPT_DIR/results_m${m}_mtu${mtu}.json"

    if [ -f "$out" ]; then
      echo "[$run/$total] m=$m mtu=$mtu  SKIPPING (results already exist)"
      continue
    fi

    echo "[$run/$total] m=$m mtu=$mtu  (window=$((2**(m-1))))  starting..."
    python3 "$SCRIPT_DIR/run_sweep_fg.py" "$m" "$mtu"
    echo "  ✓  Saved: $out"
    echo ""
    sleep 2  # let the OS release GR resources before next run
  done
done

echo "All runs complete. Collecting results..."
python3 "$SCRIPT_DIR/collect_and_chart.py"
echo "Done. Check $SCRIPT_DIR for charts and report."
