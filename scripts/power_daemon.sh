#!/usr/bin/env bash
set -euo pipefail

# Battery-awareness loop.
# Writes data/runtime/state.json for the UI, chat.py and the round status display,
# logs low/critical transitions, and performs a safe shutdown when the battery stays
# critical (and is not charging) for battery_shutdown_confirm_reads readings.
#
# Battery source: INA219 on the SeenGreat Pi Zero UPS HAT (B) at 0x43 (configurable),
# falling back to sysfs power_supply nodes. See config/default.json "ina219_*" and
# "battery_*" keys. If the chip is not found, the daemon keeps running and logs a hint.
#
# Usage: scripts/power_daemon.sh [interval_seconds] [--dry-run]
# Run as root (e.g. from a systemd unit) so the shutdown command is allowed.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CFG="${ROOT_DIR}/config/default.json"
STATE="${ROOT_DIR}/data/runtime/state.json"
LOGFILE="${ROOT_DIR}/logs/power-daemon.log"
INTERVAL_SECONDS="${1:-30}"
shift || true

mkdir -p "$(dirname "$LOGFILE")" "$(dirname "$STATE")"

exec python3 "${ROOT_DIR}/scripts/power_profile.py" \
  --daemon \
  --config "$CFG" \
  --state "$STATE" \
  --log "$LOGFILE" \
  --interval "$INTERVAL_SECONDS" \
  "$@"
