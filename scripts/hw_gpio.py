#!/usr/bin/env python3
"""Tiny GPIO helper on top of libgpiod's Python bindings (v1.x or v2.x).

Used by the rotary encoder (hw_input.py) and the round status display
(status_display.py). Optional: everything that imports this degrades gracefully when
`gpiod` is not installed (e.g. on a desktop dev machine).

Install on the device:  sudo apt install python3-libgpiod   (or: pip install gpiod)

Line numbers are *offsets on the GPIO chip*, not physical header pins. On the Allwinner
H616/H618 main pin controller ("300b000.pinctrl") the offset is bank*32 + pin, e.g.
PI12 = 8*32 + 12 = 268. These match the GPIO numbers in Orange Pi's wiringOP tables
(see docs/wiring.md). Check with `gpiodetect` / `gpioinfo` on the board.
"""

from __future__ import annotations

import glob
from typing import Dict, Iterable, List

try:
    import gpiod  # type: ignore

    GPIOD_AVAILABLE = True
except Exception:  # pragma: no cover - depends on the host
    gpiod = None
    GPIOD_AVAILABLE = False

DEFAULT_CHIP_LABEL = "300b000.pinctrl"  # H616/H618 main PIO (not r_pio @ 7022000)


class GpioUnavailable(RuntimeError):
    pass


def _is_v2() -> bool:
    return GPIOD_AVAILABLE and hasattr(gpiod, "request_lines")


def _chip_label(path: str) -> str:
    if _is_v2():
        with gpiod.Chip(path) as chip:
            return chip.get_info().label
    chip = gpiod.Chip(path)
    try:
        label = chip.label
        return label() if callable(label) else str(label)
    finally:
        chip.close()


def resolve_chip(spec: str = "auto", label: str = DEFAULT_CHIP_LABEL) -> str:
    """Return a /dev/gpiochipN path. spec: "auto", "gpiochip0" or "/dev/gpiochip0"."""
    if not GPIOD_AVAILABLE:
        raise GpioUnavailable("python gpiod bindings not installed (sudo apt install python3-libgpiod)")
    if spec and spec != "auto":
        return spec if spec.startswith("/dev/") else f"/dev/{spec}"
    for path in sorted(glob.glob("/dev/gpiochip*")):
        try:
            if _chip_label(path) == label:
                return path
        except Exception:
            continue
    raise GpioUnavailable(f"no GPIO chip labelled {label!r} (check `gpiodetect`, set gpio_chip in config)")


class GpioLines:
    """Request a handful of input/output lines on one chip."""

    def __init__(
        self,
        chip: str,
        inputs: Iterable[int] = (),
        outputs: Iterable[int] = (),
        pull_up_inputs: bool = True,
        consumer: str = "survival-device",
    ) -> None:
        if not GPIOD_AVAILABLE:
            raise GpioUnavailable("python gpiod bindings not installed")
        self.inputs: List[int] = [int(x) for x in inputs]
        self.outputs: List[int] = [int(x) for x in outputs]
        self._v2 = _is_v2()
        self._req = None
        self._lines: Dict[int, object] = {}
        self._chip = None

        if self._v2:
            from gpiod.line import Bias, Direction, Value  # type: ignore

            self._Value = Value
            config = {}
            if self.inputs:
                config[tuple(self.inputs)] = gpiod.LineSettings(
                    direction=Direction.INPUT,
                    bias=Bias.PULL_UP if pull_up_inputs else Bias.AS_IS,
                )
            if self.outputs:
                config[tuple(self.outputs)] = gpiod.LineSettings(
                    direction=Direction.OUTPUT, output_value=Value.INACTIVE
                )
            self._req = gpiod.request_lines(chip, consumer=consumer, config=config)
        else:
            self._chip = gpiod.Chip(chip)
            flags = 0
            if pull_up_inputs and hasattr(gpiod, "LINE_REQ_FLAG_BIAS_PULL_UP"):
                flags = gpiod.LINE_REQ_FLAG_BIAS_PULL_UP  # libgpiod >= 1.5
            for off in self.inputs:
                line = self._chip.get_line(off)
                line.request(consumer=consumer, type=gpiod.LINE_REQ_DIR_IN, flags=flags)
                self._lines[off] = line
            for off in self.outputs:
                line = self._chip.get_line(off)
                line.request(consumer=consumer, type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])
                self._lines[off] = line

    def get(self, offset: int) -> int:
        if self._v2:
            return 1 if self._req.get_value(offset) == self._Value.ACTIVE else 0
        return int(self._lines[offset].get_value())

    def set(self, offset: int, value: int) -> None:
        if self._v2:
            self._req.set_value(offset, self._Value.ACTIVE if value else self._Value.INACTIVE)
        else:
            self._lines[offset].set_value(1 if value else 0)

    def close(self) -> None:
        try:
            if self._req is not None:
                self._req.release()
            for line in self._lines.values():
                line.release()
            if self._chip is not None:
                self._chip.close()
        except Exception:
            pass


def open_lines(
    cfg: Dict,
    inputs: Iterable[int] = (),
    outputs: Iterable[int] = (),
    pull_up_inputs: bool = True,
    consumer: str = "survival-device",
) -> GpioLines:
    chip = resolve_chip(str(cfg.get("gpio_chip", "auto")), str(cfg.get("gpio_chip_label", DEFAULT_CHIP_LABEL)))
    return GpioLines(chip, inputs=inputs, outputs=outputs, pull_up_inputs=pull_up_inputs, consumer=consumer)


__all__ = ["GPIOD_AVAILABLE", "GpioUnavailable", "GpioLines", "open_lines", "resolve_chip"]


if __name__ == "__main__":  # quick diagnostics
    import sys

    if not GPIOD_AVAILABLE:
        print("gpiod not installed")
        sys.exit(1)
    for p in sorted(glob.glob("/dev/gpiochip*")):
        try:
            print(p, _chip_label(p))
        except Exception as exc:
            print(p, f"error: {exc}")
