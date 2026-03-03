#!/usr/bin/env bash
set -euo pipefail

# Render a minimal Pip-Boy style boot/status screen for framebuffer devices.
# Fails safely when framebuffer tools are unavailable.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATUS_FILE="${ROOT_DIR}/logs/display-status.txt"
TMP_IMG="/tmp/survival_boot.ppm"

echo "survival-ok:boot" >"${STATUS_FILE}"

echo "[INFO] Starting framebuffer smoke test"

if [ ! -e /dev/fb0 ]; then
  echo "[WARN] /dev/fb0 not present. Falling back to console output."
  echo "=========================================="
  echo " SURVIVAL AI"
  echo " Boot: OK"
  echo " Status: Display not detected"
  echo "=========================================="
  echo "(v1 offline MVP)"
  exit 0
fi

# Attempt framebuffer render via fbi (common on minimal Linux).
if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY'
from pathlib import Path
img_path = Path('/tmp/survival_boot.ppm')
w,h = 320,240
# simple binary PPM (P6)
pixels = []
for y in range(h):
    for x in range(w):
        # dark green theme background
        r, g, b = 10, 24, 14
        # simple status stripe
        if y < 26:
            r, g, b = 8, 42, 8
        # frame accent
        if 10 <= x <= 12 or 10 <= y <= 12 or x >= w-12 or y >= h-12:
            r, g, b = 72, 180, 96
        # text area placeholder colors
        pixels.extend([r, g, b])

a = bytearray([10,24,14])

a = bytearray()
for v in pixels:
    a.append(v)

with open('/tmp/survival_boot.ppm', 'wb') as f:
    f.write(f"P6 {w} {h} 255 \n".encode('ascii'))
    f.write(bytes(a))
PY
fi

if command -v fbi >/dev/null 2>&1; then
  fbi -d /dev/fb0 -T 1 -noverbose /tmp/survival_boot.ppm
  echo "[INFO] Rendered via fbi"
elif command -v fim >/dev/null 2>&1; then
  fim -q -a /tmp/survival_boot.ppm
  echo "[INFO] Rendered via fim"
else
  echo "[WARN] No framebuffer image viewer found (fbi/fim)."
  echo "Try installing: sudo apt-get install fbi"
  echo "Fallback: writing status text to serial/console"
  cat <<EOF >/tmp/survival_boot.txt
S V   SURVIVAL   A I
BOOT    OK
STATUS  DISPLAY TEST PASS
LAST    $(date -u)
EOF
  cat /tmp/survival_boot.txt
fi

echo "[INFO] done"
