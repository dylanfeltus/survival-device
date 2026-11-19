#!/usr/bin/env python3
"""Optional status loop for the small round SPI TFT (GC9A01, 240x240).

Shows battery %, voltage, charging and power mode, read from data/runtime/state.json
(written by scripts/power_daemon.sh), so this script never touches I2C itself.

Usage:
  python3 scripts/status_display.py                 # loop forever on the hardware
  python3 scripts/status_display.py --once          # draw one frame and exit
  python3 scripts/status_display.py --preview out.png   # render to PNG, no hardware

Dependencies (device only): python3-pil (Pillow), python3-spidev or `pip install spidev`,
python3-libgpiod. Missing dependencies -> clear message, exit code 0 (feature is optional).

Hardware config: "status_display" in config/default.json, wiring in docs/wiring.md.

TODO(verify): the blue round breakout is *probably* a GC9A01 240x240; confirm from the
seller listing / silkscreen. The init sequence below is transcribed from Adafruit's
Adafruit_GC9A01A driver (which itself comes from the manufacturer's sample code). If
the panel stays blank or shows noise, compare it with the demo code for your module.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT_DIR / "data" / "runtime" / "state.json"
WIDTH = HEIGHT = 240

# (command, [data bytes], delay_ms after) -- from Adafruit_GC9A01A.cpp initcmd[]
GC9A01_INIT = [
    (0xEF, [], 0), (0xEB, [0x14], 0), (0xFE, [], 0), (0xEF, [], 0), (0xEB, [0x14], 0),
    (0x84, [0x40], 0), (0x85, [0xFF], 0), (0x86, [0xFF], 0), (0x87, [0xFF], 0),
    (0x88, [0x0A], 0), (0x89, [0x21], 0), (0x8A, [0x00], 0), (0x8B, [0x80], 0),
    (0x8C, [0x01], 0), (0x8D, [0x01], 0), (0x8E, [0xFF], 0), (0x8F, [0xFF], 0),
    (0xB6, [0x00, 0x00], 0),
    (0x36, [0x40 | 0x08], 0),          # MADCTL: MX | BGR
    (0x3A, [0x05], 0),                 # COLMOD: 16-bit RGB565
    (0x90, [0x08, 0x08, 0x08, 0x08], 0), (0xBD, [0x06], 0), (0xBC, [0x00], 0),
    (0xFF, [0x60, 0x01, 0x04], 0),
    (0xC3, [0x13], 0), (0xC4, [0x13], 0), (0xC9, [0x22], 0),
    (0xBE, [0x11], 0), (0xE1, [0x10, 0x0E], 0), (0xDF, [0x21, 0x0C, 0x02], 0),
    (0xF0, [0x45, 0x09, 0x08, 0x08, 0x26, 0x2A], 0),
    (0xF1, [0x43, 0x70, 0x72, 0x36, 0x37, 0x6F], 0),
    (0xF2, [0x45, 0x09, 0x08, 0x08, 0x26, 0x2A], 0),
    (0xF3, [0x43, 0x70, 0x72, 0x36, 0x37, 0x6F], 0),
    (0xED, [0x1B, 0x0B], 0), (0xAE, [0x77], 0), (0xCD, [0x63], 0),
    (0xE8, [0x34], 0),
    (0x62, [0x18, 0x0D, 0x71, 0xED, 0x70, 0x70, 0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70], 0),
    (0x63, [0x18, 0x11, 0x71, 0xF1, 0x70, 0x70, 0x18, 0x13, 0x71, 0xF3, 0x70, 0x70], 0),
    (0x64, [0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07], 0),
    (0x66, [0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0x00, 0x00, 0x00], 0),
    (0x67, [0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98], 0),
    (0x74, [0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00], 0),
    (0x98, [0x3E, 0x07], 0),
    (0x35, [], 0),                     # TEON
    (0x21, [], 0),                     # INVON
    (0x11, [], 150),                   # SLPOUT
    (0x29, [], 150),                   # DISPON
]

GREEN = (40, 255, 90)
DIM = (0, 110, 40)
WARN = (255, 200, 0)
CRIT = (255, 60, 40)
BLACK = (0, 0, 0)


def load_cfg() -> Dict[str, Any]:
    try:
        return json.loads((ROOT_DIR / "config" / "default.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_state(max_age_s: float) -> Dict[str, Any]:
    try:
        st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"_stale": True}
    try:
        ts = datetime.fromisoformat(str(st.get("ts")))
        st["_stale"] = (datetime.now(timezone.utc) - ts).total_seconds() > max_age_s
    except Exception:
        st["_stale"] = True
    return st


# ---------------------------------------------------------------------------
# Rendering (Pillow)
# ---------------------------------------------------------------------------

def _font(size: int):
    from PIL import ImageFont

    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def _center(draw, y: int, text: str, font, fill) -> None:
    try:
        left, _top, right, _bottom = draw.textbbox((0, 0), text, font=font)
        w = right - left
    except AttributeError:  # very old Pillow
        w = draw.textsize(text, font=font)[0]
    draw.text(((WIDTH - w) // 2, y), text, font=font, fill=fill)


def render(state: Dict[str, Any], warn_pct: int, crit_pct: int):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    d = ImageDraw.Draw(img)
    pct = state.get("battery_pct")
    stale = state.get("_stale", True)

    if pct is None or stale:
        d.ellipse((6, 6, WIDTH - 7, HEIGHT - 7), outline=DIM, width=4)
        _center(d, 80, "BATT", _font(28), DIM)
        _center(d, 120, "NO DATA" if stale else "--%", _font(26), WARN)
        _center(d, 165, "power daemon?" if stale else "INA219?", _font(16), DIM)
        return img

    pct = int(pct)
    color = CRIT if pct <= crit_pct else WARN if pct <= warn_pct else GREEN
    # Background ring + battery arc (starts at 12 o'clock, clockwise).
    d.arc((6, 6, WIDTH - 7, HEIGHT - 7), 0, 360, fill=DIM, width=10)
    if pct > 0:
        d.arc((6, 6, WIDTH - 7, HEIGHT - 7), -90, -90 + int(360 * pct / 100), fill=color, width=10)

    charging = state.get("charging")
    _center(d, 52, "CHARGING" if charging else "BATTERY", _font(18), GREEN if charging else DIM)
    _center(d, 80, f"{pct}%", _font(56), color)
    volts = state.get("battery_v")
    if volts is not None:
        _center(d, 145, f"{float(volts):.2f} V", _font(20), DIM)
    mode = str(state.get("power_mode") or state.get("recommended_mode") or "normal").upper()
    _center(d, 175, mode, _font(20), CRIT if mode == "ULTRA" else WARN if mode == "REDUCED" else GREEN)
    return img


def to_rgb565(img) -> bytes:
    raw = img.convert("RGB").tobytes()
    out = bytearray(len(raw) // 3 * 2)
    j = 0
    for i in range(0, len(raw), 3):
        r, g, b = raw[i], raw[i + 1], raw[i + 2]
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out[j] = v >> 8
        out[j + 1] = v & 0xFF
        j += 2
    return bytes(out)


# ---------------------------------------------------------------------------
# GC9A01 over spidev + GPIO (DC, RST)
# ---------------------------------------------------------------------------

class GC9A01:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        import spidev  # type: ignore

        from hw_gpio import open_lines

        self.dc = int(cfg.get("dc_line"))
        self.rst = cfg.get("rst_line")
        self.rst = int(self.rst) if self.rst is not None else None
        outputs = [self.dc] + ([self.rst] if self.rst is not None else [])
        self.gpio = open_lines(cfg, outputs=outputs, consumer="surv-status-tft")
        self.spi = spidev.SpiDev()
        self.spi.open(int(cfg.get("spi_bus", 1)), int(cfg.get("spi_device", 1)))
        self.spi.mode = 0
        self.spi.max_speed_hz = int(cfg.get("spi_speed_hz", 24_000_000))
        self._init()

    def _write(self, data: bytes) -> None:
        if hasattr(self.spi, "writebytes2"):
            self.spi.writebytes2(data)
        else:
            for i in range(0, len(data), 4096):
                self.spi.writebytes(list(data[i:i + 4096]))

    def command(self, cmd: int, data: Tuple[int, ...] | list = ()) -> None:
        self.gpio.set(self.dc, 0)
        self._write(bytes([cmd]))
        if data:
            self.gpio.set(self.dc, 1)
            self._write(bytes(data))

    def _init(self) -> None:
        if self.rst is not None:
            self.gpio.set(self.rst, 1)
            time.sleep(0.01)
            self.gpio.set(self.rst, 0)
            time.sleep(0.01)
            self.gpio.set(self.rst, 1)
            time.sleep(0.12)
        else:
            self.command(0x01)  # SWRESET
            time.sleep(0.15)
        for cmd, data, delay_ms in GC9A01_INIT:
            self.command(cmd, data)
            if delay_ms:
                time.sleep(delay_ms / 1000.0)

    def show(self, frame565: bytes) -> None:
        self.command(0x2A, [0, 0, 0, WIDTH - 1])   # CASET
        self.command(0x2B, [0, 0, 0, HEIGHT - 1])  # RASET
        self.command(0x2C)                         # RAMWR
        self.gpio.set(self.dc, 1)
        self._write(frame565)

    def close(self) -> None:
        try:
            self.command(0x28)  # DISPOFF
            self.spi.close()
        finally:
            self.gpio.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Round GC9A01 status display")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--preview", metavar="PNG", help="Render one frame to a PNG instead of the panel")
    parser.add_argument("--force", action="store_true", help="Run even if status_display.enabled is false")
    args = parser.parse_args()

    cfg = load_cfg()
    sd_cfg = cfg.get("status_display") or {}
    refresh = float(sd_cfg.get("refresh_s", 10))
    warn_pct = int(cfg.get("battery_warn_pct", 20))
    crit_pct = int(cfg.get("battery_critical_pct", 8))
    max_age = max(90.0, refresh * 3)

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("[status_display] Pillow not installed (sudo apt install python3-pil); skipping.")
        return 0

    if args.preview:
        render(load_state(max_age), warn_pct, crit_pct).save(args.preview)
        print(f"[status_display] preview written to {args.preview}")
        return 0

    if not sd_cfg.get("enabled", False) and not args.force:
        print("[status_display] disabled in config (status_display.enabled=false); use --force to try anyway.")
        return 0

    try:
        panel = GC9A01(sd_cfg)
    except ImportError as exc:
        print(f"[status_display] missing dependency ({exc}); skipping.")
        return 0
    except Exception as exc:
        print(f"[status_display] could not open the round display: {exc}")
        return 1

    last: Optional[bytes] = None
    try:
        while True:
            frame = to_rgb565(render(load_state(max_age), warn_pct, crit_pct))
            if frame != last:  # only push over SPI when something changed
                panel.show(frame)
                last = frame
            if args.once:
                break
            time.sleep(refresh)
    except KeyboardInterrupt:
        pass
    finally:
        if not args.once:
            panel.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
