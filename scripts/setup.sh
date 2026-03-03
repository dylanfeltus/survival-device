#!/usr/bin/env bash
set -euo pipefail

# Production-safe, fail-soft setup script for first-boot provisioning.
# Designed for Orange Pi and generic Debian/Ubuntu systems.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_PATH="${ROOT_DIR}/config/default.json"

log() { printf "[INFO] %s\n" "$*"; }
warn() { printf "[WARN] %s\n" "$*"; }

have_root() {
  if [ "$EUID" -ne 0 ]; then
    warn "Not running as root. Some ops (GPIO/display permissions, package installs) may require sudo."
    return 1
  fi
  return 0
}

install_deps() {
  log "Installing base dependencies..."
  if command -v apt-get >/dev/null 2>&1; then
    if have_root; then
      apt-get update
      apt-get install -y python3 python3-pip python3-venv python3-dev git ca-certificates \
        i2c-tools usbutils ffmpeg procps
    else
      warn "Skipping apt-get install (non-root). Install packages manually or run with sudo."
    fi
  elif command -v apk >/dev/null 2>&1; then
    if have_root; then
      apk add --no-cache python3 py3-pip git ca-certificates i2c-tools usbutils ffmpeg procps
    else
      warn "Skipping apk install (non-root). Install packages manually or run with sudo."
    fi
  elif command -v dnf >/dev/null 2>&1; then
    if have_root; then
      dnf install -y python3 python3-pip git ca-certificates i2c-tools usbutils ffmpeg procps
    else
      warn "Skipping dnf install (non-root)."
    fi
  else
    warn "No supported package manager found. Install python3 + ffmpeg manually."
  fi

  # Python deps (best effort; offline-safe: do not fail hard if not reachable)
  if python3 -m pip --version >/dev/null 2>&1; then
    python3 -m pip install --upgrade pip || true
    python3 -m pip install numpy tqdm >/dev/null 2>&1 || true
  else
    warn "pip unavailable; continuing with stdlib-only mode."
  fi
}

ensure_dirs() {
  mkdir -p "${ROOT_DIR}/data/sources" "${ROOT_DIR}/data/index" "${ROOT_DIR}/logs" "${ROOT_DIR}/models"
  log "Created runtime directories under ${ROOT_DIR}"
}

check_gpio_display_audio() {
  log "Verifying hardware interfaces..."
  if ls /dev/gpiochip* >/dev/null 2>&1; then
    log "GPIO detected: $(ls /dev/gpiochip* | tr '\n' ' ')"
  else
    warn "No /dev/gpiochip* found. GPIO checks skipped for this environment."
  fi

  if [ -e /dev/fb0 ]; then
    log "Framebuffer detected: /dev/fb0"
  else
    warn "No /dev/fb0 found. Framebuffer checks skipped."
  fi

  if ls /dev/snd/* >/dev/null 2>&1; then
    log "Audio device detected under /dev/snd"
  else
    warn "No /dev/snd devices found. Audio checks skipped."
  fi

  if command -v i2cdetect >/dev/null 2>&1; then
    log "I2C controllers:"
    i2cdetect -l 2>/dev/null || true
  else
    warn "i2cdetect missing; install i2c-tools for battery/solar peripheral checks."
  fi
}

health_checks() {
  log "Running health checks..."
  python3 --version | sed 's/^/[HEALTH] /'
  python3 - <<'PY'
import importlib.util
print('[HEALTH] python3 json: ok')
print('[HEALTH] numpy:', 'yes' if importlib.util.find_spec('numpy') else 'missing')
print('[HEALTH] tqdm:', 'yes' if importlib.util.find_spec('tqdm') else 'missing')
PY

  if command -v free >/dev/null 2>&1; then
    free -h
  else
    vm_stat 2>/dev/null | head -n 5 || true
  fi
  uptime || true

  if [ -r /proc/uptime ]; then
    awk '{printf("[HEALTH] uptime_seconds=%s\n",$1)}' /proc/uptime
  fi

  if command -v lsusb >/dev/null 2>&1; then
    lsusb | head -n 5
  fi

  if command -v uname >/dev/null 2>&1; then
    uname -a
  fi
}

model_placeholders() {
  local conf_path="$1"
  local llama_model
  local embed_model
  llama_model="$(python3 - <<PY
import json
from pathlib import Path
cfg=Path(r"$conf_path")
print(json.loads(cfg.read_text()).get('model_path',''))
PY
)"
  embed_model="$(python3 - <<PY
import json
from pathlib import Path
cfg=Path(r"$conf_path")
print(json.loads(cfg.read_text()).get('embedding_model_path',''))
PY
)"

  log "Model placeholders from config:"
  echo "  model_path=${llama_model}"
  echo "  embedding_model_path=${embed_model}"

  if [ -n "${llama_model}" ] && [ -e "${llama_model}" ]; then
    ls -lh "${llama_model}"
  else
    warn "LLM model not present at configured path. Provision before production use."
  fi

  if [ -n "${embed_model}" ] && [ -e "${embed_model}" ]; then
    if [ -d "${embed_model}" ]; then
      du -sh "${embed_model}"
    else
      ls -lh "${embed_model}"
    fi
  else
    warn "Embedding model directory not present; fallback deterministic embeddings will be used."
  fi
}

main() {
  log "Starting Survival AI v1 setup"
  install_deps
  ensure_dirs
  check_gpio_display_audio
  model_placeholders "${CONFIG_PATH}"
  health_checks
  log "Setup complete. Next step: add source docs under data/sources then run ingest_booklist.py"
}

main "$@"
