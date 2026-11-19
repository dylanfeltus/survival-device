#!/usr/bin/env bash
set -euo pipefail

# Launch the curses UI on the 2.8" SPI TFT.
#
# How it works: the kernel driver (fbtft fb_ili9341, via overlays/survival-tft-zero2w.dts)
# exposes the panel as a framebuffer (/dev/fbN). We map a Linux text console onto that
# framebuffer and run scripts/ui.py on it. No X11/Wayland needed.
#
# Usage (as root, or from a systemd unit bound to the tty; see docs/wiring.md):
#   sudo scripts/ui-tft.sh            # console 1 -> TFT framebuffer, then run the UI there
# Env overrides:
#   TFT_FB=/dev/fb1     framebuffer to use (default: auto-detect by driver name)
#   TFT_TTY=1           virtual console number to map/run on
#   TFT_FONT=...        console font for setfont (e.g. a Terminus 6x12 font for more text)
#
# Falls back to running the UI in the current terminal if no TFT framebuffer is found.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TTY_NUM="${TFT_TTY:-1}"

find_tft_fb() {
  local n name
  for d in /sys/class/graphics/fb*; do
    [ -e "$d/name" ] || continue
    name="$(cat "$d/name" 2>/dev/null || true)"
    # fbtft names it "fb_ili9341"; DRM tiny/mipi-dbi drivers include the panel name too.
    case "$name" in
      *ili9341*|*mipi-dbi*|*mi0283qt*) n="${d##*/fb}"; echo "/dev/fb${n}"; return 0 ;;
    esac
  done
  return 1
}

FB="${TFT_FB:-$(find_tft_fb || true)}"

if [ -z "$FB" ] || [ ! -e "$FB" ]; then
  echo "[ui-tft] No TFT framebuffer found (is the overlay loaded? see docs/wiring.md)."
  echo "[ui-tft] Running the UI in this terminal instead."
  exec python3 "${ROOT_DIR}/scripts/ui.py"
fi

FB_NUM="${FB##*/fb}"
echo "[ui-tft] Using ${FB} ($(cat /sys/class/graphics/fb${FB_NUM}/name 2>/dev/null)), console tty${TTY_NUM}"

# Map the console onto the TFT. Alternative: add "fbcon=map:<n>" to the kernel cmdline
# (extraargs= in /boot/orangepiEnv.txt or /boot/armbianEnv.txt) so it happens at boot.
if command -v con2fbmap >/dev/null 2>&1; then
  con2fbmap "$TTY_NUM" "$FB_NUM" || echo "[ui-tft] con2fbmap failed (need root?)"
else
  echo "[ui-tft] con2fbmap not found (sudo apt install fbset) - relying on fbcon=map: from the kernel cmdline"
fi

if [ -n "${TFT_FONT:-}" ] && command -v setfont >/dev/null 2>&1; then
  setfont -C "/dev/tty${TTY_NUM}" "$TFT_FONT" || true
fi

export TERM=linux
if [ "$(tty 2>/dev/null || true)" = "/dev/tty${TTY_NUM}" ]; then
  exec python3 "${ROOT_DIR}/scripts/ui.py"
elif command -v openvt >/dev/null 2>&1; then
  exec openvt -c "$TTY_NUM" -s -f -w -- env TERM=linux python3 "${ROOT_DIR}/scripts/ui.py"
else
  exec python3 "${ROOT_DIR}/scripts/ui.py" <"/dev/tty${TTY_NUM}" >"/dev/tty${TTY_NUM}" 2>&1
fi
