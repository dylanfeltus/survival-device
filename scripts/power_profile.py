#!/usr/bin/env python3
"""Simple battery/profile helper for low-power safety behavior.

This module is intentionally conservative and dependency-light so it can run on tiny boards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class PowerState:
    percent: Optional[int]
    plugged_in: bool
    low: bool
    critical: bool
    recommended_mode: str


def read_battery_percent(paths: tuple[Path, ...]) -> Optional[int]:
    for p in paths:
        if not p.exists():
            continue
        try:
            raw = p.read_text(encoding="utf-8").strip()
            if not raw:
                continue
            val = int(float(raw))
            return max(0, min(100, val))
        except Exception:
            continue
    return None


def read_battery_charged(paths: tuple[Path, ...]) -> Optional[bool]:
    # Common AC/charger states: 1 = online/charging
    for p in paths:
        if not p.exists():
            continue
        try:
            raw = p.read_text(encoding="utf-8").strip()
            if raw in {"", "N/A"}:
                continue
            return raw not in {"0", "no", "off", "discharging"}
        except Exception:
            continue
    return None


def assess(cfg: Dict[str, Any]) -> PowerState:
    if not cfg.get("battery_monitor_enabled", False):
        return PowerState(percent=None, plugged_in=False, low=False, critical=False, recommended_mode="normal")

    capacity = read_battery_percent((
        Path("/sys/class/power_supply/BAT0/capacity"),
        Path("/sys/class/power_supply/battery/capacity"),
        Path("/sys/class/power_supply/axp20x-battery/capacity"),
    ))

    plug = read_battery_charged((
        Path("/sys/class/power_supply/BAT0/online"),
        Path("/sys/class/power_supply/axp20x-battery/online"),
        Path("/sys/class/power_supply/usb/online"),
    ))

    if capacity is None:
        return PowerState(percent=None, plugged_in=bool(plug), low=False, critical=False, recommended_mode="normal")

    warn = int(cfg.get("battery_warn_pct", 20))
    critical = int(cfg.get("battery_critical_pct", 8))

    low = capacity <= warn
    critical = capacity <= critical

    mode = "normal"
    if critical and not plug:
        mode = "ultra"
    elif low or critical:
        mode = "reduced"

    return PowerState(
        percent=capacity,
        plugged_in=bool(plug),
        low=low,
        critical=critical,
        recommended_mode=mode,
    )


def dump_state(path: str | Path, state: PowerState) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "battery_pct": state.percent,
        "plugged_in": state.plugged_in,
        "low": state.low,
        "critical": state.critical,
        "recommended_mode": state.recommended_mode,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
