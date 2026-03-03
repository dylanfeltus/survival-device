#!/usr/bin/env bash
set -euo pipefail

# Basic battery-awareness loop.
# Writes a tiny runtime state file for UI + chat to consume.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CFG="${ROOT_DIR}/config/default.json"
STATE="${ROOT_DIR}/data/runtime/state.json"
LOGFILE="${ROOT_DIR}/logs/power-daemon.log"
INTERVAL_SECONDS="${1:-30}"

mkdir -p "$(dirname "$LOGFILE")" "$(dirname "$STATE")"

echo "Starting power daemon. interval=${INTERVAL_SECONDS}s" | tee -a "$LOGFILE"

while true; do
  stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mode="normal"

  if command -v python3 >/dev/null 2>&1; then
    mode=$(python3 - <<PY
import json
from pathlib import Path
from scripts.power_profile import assess, dump_state

cfg = {}
try:
    cfg = json.loads(Path("$CFG").read_text())
except Exception:
    cfg = {}

state = assess(cfg)
dump_state("$STATE", state)
print(state.recommended_mode)
PY
)
  fi

  echo "[$stamp] mode=$mode" >> "$LOGFILE"

  # Optional integration point:
  # - if mode=ultra, we could pause UI updates or force low FPS.
  if [ "$mode" = "ultra" ]; then
    echo "[$stamp] recommend_power_mode=ultra -> enforce aggressive power limits" >> "$LOGFILE"
  elif [ "$mode" = "reduced" ]; then
    echo "[$stamp] recommend_power_mode=reduced -> lowering compute/context" >> "$LOGFILE"
  fi

  sleep "$INTERVAL_SECONDS"
done
