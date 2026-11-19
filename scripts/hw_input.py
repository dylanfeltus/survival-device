#!/usr/bin/env python3
"""Rotary encoder (CLK, DT, SW) input for the survival device UI.

Produces simple events on a queue that ui.py consumes:
  "cw"    - one detent clockwise
  "ccw"   - one detent counter-clockwise
  "press" - push button pressed (debounced)

Polls the lines in a background thread with a quadrature state table. Polling is used
instead of edge events because it behaves the same on libgpiod v1 and v2; at the
default 1 ms period it costs a few percent of one Cortex-A53 core.

Config lives under "encoder" in config/default.json (see docs/wiring.md for pins).

Diagnostics on the device:
  python3 scripts/hw_input.py      # prints events as you turn/press the knob
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from hw_gpio import GpioUnavailable, open_lines

# Index = (previous_state << 2) | current_state, state = (CLK << 1) | DT.
# +1 / -1 for valid single-step transitions, 0 for no change or an invalid (bounced) jump.
_QUAD_TABLE = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)


class RotaryEncoder:
    def __init__(self, cfg: Dict[str, Any], events: Optional["queue.Queue[str]"] = None) -> None:
        self.cfg = cfg
        self.events: "queue.Queue[str]" = events or queue.Queue()
        self.clk = int(cfg.get("clk_line"))
        self.dt = int(cfg.get("dt_line"))
        self.sw = cfg.get("sw_line")
        self.sw = int(self.sw) if self.sw is not None else None
        self.steps_per_detent = max(1, int(cfg.get("steps_per_detent", 4)))
        self.poll_s = max(0.0002, float(cfg.get("poll_ms", 1)) / 1000.0)
        self.invert = bool(cfg.get("invert", False))
        self.debounce_s = float(cfg.get("button_debounce_ms", 30)) / 1000.0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        inputs = [self.clk, self.dt] + ([self.sw] if self.sw is not None else [])
        # Pull-ups: KY-040-style modules usually have them on CLK/DT but often not on SW.
        self.lines = open_lines(cfg, inputs=inputs, pull_up_inputs=True, consumer="surv-encoder")

    def _state(self) -> int:
        return (self.lines.get(self.clk) << 1) | self.lines.get(self.dt)

    def _run(self) -> None:
        prev = self._state()
        acc = 0
        btn_stable = self.lines.get(self.sw) if self.sw is not None else 1
        btn_last = btn_stable
        btn_changed_at = time.monotonic()

        while not self._stop.is_set():
            cur = self._state()
            if cur != prev:
                acc += _QUAD_TABLE[(prev << 2) | cur]
                prev = cur
                if abs(acc) >= self.steps_per_detent:
                    cw = acc > 0
                    if self.invert:
                        cw = not cw
                    self.events.put("cw" if cw else "ccw")
                    acc = 0

            if self.sw is not None:
                raw = self.lines.get(self.sw)
                now = time.monotonic()
                if raw != btn_last:
                    btn_last = raw
                    btn_changed_at = now
                elif raw != btn_stable and now - btn_changed_at >= self.debounce_s:
                    btn_stable = raw
                    if btn_stable == 0:  # active low (switch to GND)
                        self.events.put("press")

            time.sleep(self.poll_s)

    def start(self) -> "RotaryEncoder":
        self._thread = threading.Thread(target=self._run, name="rotary-encoder", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        self.lines.close()

    def poll(self) -> Optional[str]:
        try:
            return self.events.get_nowait()
        except queue.Empty:
            return None


def start_encoder_from_config(root_cfg: Dict[str, Any]) -> tuple[Optional[RotaryEncoder], str]:
    """Start the encoder if enabled. Returns (encoder or None, status message)."""
    enc_cfg = root_cfg.get("encoder") or {}
    if not enc_cfg.get("enabled", False):
        return None, "encoder disabled in config"
    try:
        return RotaryEncoder(enc_cfg).start(), "encoder started"
    except GpioUnavailable as exc:
        return None, f"encoder unavailable: {exc}"
    except Exception as exc:  # wrong chip/lines, permissions (add user to 'gpio' group?)
        return None, f"encoder failed to start: {exc}"


if __name__ == "__main__":
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "default.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.setdefault("encoder", {})["enabled"] = True
    enc, msg = start_encoder_from_config(cfg)
    print(msg)
    if enc is None:
        sys.exit(1)
    print("Turn / press the knob (Ctrl+C to quit)")
    try:
        while True:
            ev = enc.events.get()
            print(ev, flush=True)
    except KeyboardInterrupt:
        enc.stop()
