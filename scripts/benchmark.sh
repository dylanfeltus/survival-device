#!/usr/bin/env bash
set -euo pipefail

# Simple inference benchmark + power draw hooks.
# On unsupported hosts, power sampling is mocked safely.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_PATH="${ROOT_DIR}/config/default.json"

read_config() {
  local key="$1"
  python3 -c "import json,sys;cfg=json.load(open('$CONFIG_PATH')); print(cfg.get('$key',''))" 2>/dev/null || true
}

INDEX_PATH="${ROOT_DIR}/$(read_config index_path)"
PROMPTS=(
  "What are the first aid steps for minor cuts?"
  "What water purification methods are safe in wilderness?"
  "How should I prepare for a heat emergency?"
)

LOG_DIR="${ROOT_DIR}/logs"
OUTFILE="${LOG_DIR}/benchmark-$(date +%Y%m%d-%H%M%S).log"
RUNS=3

mkdir -p "${LOG_DIR}"

{
  echo "# Survival AI benchmark"
  echo "timestamp: $(date -u)"
  echo "[INFO] Config: ${CONFIG_PATH}"
  echo "[INFO] Index : ${INDEX_PATH}"
  echo "[INFO] model_path: $(read_config model_path)"
  echo
} >>"${OUTFILE}"

drain_power_sample() {
  # Try to collect real power draw; otherwise return synthetic placeholder.
  if [ -r /sys/class/power_supply/BAT0/charge_now ] && [ -r /sys/class/power_supply/BAT0/current_now ]; then
    local c_now v_now
    c_now=$(cat /sys/class/power_supply/BAT0/charge_now 2>/dev/null || echo 0)
    v_now=$(cat /sys/class/power_supply/BAT0/voltage_now 2>/dev/null || echo 0)
    echo "${c_now},${v_now}"
    return
  fi

  # common Orange Pi PMIC/sysfs may expose power elsewhere; keep this hook generic.
  if [ -d /sys/class/hwmon ]; then
    local hw
    hw=$(find /sys/class/hwmon -maxdepth 2 -type f -name 'power1_input' 2>/dev/null | head -n 1)
    if [ -n "$hw" ]; then
      echo "$(cat "$hw" 2>/dev/null || echo 0)"
      return
    fi
  fi

  # Mock value
  awk 'BEGIN{srand(); printf "mock,%.0f", 2000000+rand()*1000000}'
}

for p in "${PROMPTS[@]}"; do
  {
    echo
    echo "===== QUERY: ${p} ====="
  } >>"${OUTFILE}"

  for i in $(seq 1 "$RUNS"); do
    {
      echo "-- run $i --"
    } >>"${OUTFILE}"

    power_before="$(drain_power_sample)"
    start=$(date +%s%3N)
    set +e
    timeout 180 python3 "${ROOT_DIR}/scripts/chat.py" --offline --k 4 "$p" >>"${OUTFILE}" 2>&1
    rc=$?
    set -e
    end=$(date +%s%3N)
    power_after="$(drain_power_sample)"

    if [ "$rc" -ne 0 ]; then
      echo "WARN: chat timed out or failed (code=$rc)" >>"${OUTFILE}"
    fi

    elapsed_ms=$((end - start))
    echo "elapsed_ms=${elapsed_ms}" >>"${OUTFILE}"
    echo "power_before=${power_before}, power_after=${power_after}" >>"${OUTFILE}"
    echo >>"${OUTFILE}"
  done
done

echo "Benchmark complete: ${OUTFILE}"
