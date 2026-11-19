#!/usr/bin/env python3
"""Battery/profile helper for low-power safety behavior.

This module is intentionally conservative and dependency-light so it can run on tiny boards.

Battery source priority:
  1. INA219 on the SeenGreat Pi Zero UPS HAT (B) (default I2C address 0x43), read via
     raw /dev/i2c-N ioctls (no smbus dependency).
  2. Generic Linux power_supply sysfs nodes (laptops, PMIC boards).
  3. Unknown -> percent=None, recommended_mode="normal" (never blocks the app).

Run directly for diagnostics:
  python3 scripts/power_profile.py            # print one reading as JSON
  python3 scripts/power_profile.py --daemon   # loop, write data/runtime/state.json,
                                              # warn/critical logging + safe shutdown
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent

# INA219 register map (TI INA219 datasheet; same constants as Adafruit_INA219).
INA219_REG_SHUNT_VOLTAGE = 0x01  # signed 16-bit, LSB = 10 uV
INA219_REG_BUS_VOLTAGE = 0x02    # bits 15..3 = voltage, LSB = 4 mV
I2C_SLAVE = 0x0703               # linux/i2c-dev.h

# On the Allwinner H616/H618 (Orange Pi Zero 2W), header pins 3/5 (PI8/PI7) are the
# "i2c1" controller at 0x05002400. The board DTS defines no i2c aliases, so the
# /dev/i2c-N number depends on probe order -> "auto" looks the controller up in sysfs.
DEFAULT_I2C_CONTROLLER = "5002400.i2c"

# Approximate resting (open-circuit) voltage -> state-of-charge curve for a single
# 3.7 V nominal LiPo/Li-ion cell. This is a generic approximation, not a SeenGreat or
# cell-vendor spec. Under load the voltage sags (reads low); while charging it rises
# (reads high). Override with "battery_voltage_curve" in config if you characterise
# your own cell.
DEFAULT_LIPO_CURVE: List[Tuple[float, int]] = [
    (3.27, 0),
    (3.61, 5),
    (3.69, 10),
    (3.71, 15),
    (3.73, 20),
    (3.75, 25),
    (3.77, 30),
    (3.79, 35),
    (3.80, 40),
    (3.82, 45),
    (3.84, 50),
    (3.85, 55),
    (3.87, 60),
    (3.91, 65),
    (3.95, 70),
    (3.98, 75),
    (4.02, 80),
    (4.08, 85),
    (4.11, 90),
    (4.15, 95),
    (4.20, 100),
]

POGO_HINT = (
    "The UPS HAT reaches the Pi only through spring pogo pins under the 40-pin header. "
    "If the INA219 is missing, check that the standoffs are the right height so every "
    "pogo pin is compressed against its header solder joint (too tall = no contact, "
    "too short = bent pins), that the header is soldered/pressed fully flush, and that "
    "the I2C overlay is enabled (see README 'Hardware bring-up')."
)


@dataclass
class PowerState:
    percent: Optional[int]
    plugged_in: bool
    low: bool
    critical: bool
    recommended_mode: str
    voltage_v: Optional[float] = None
    charging: Optional[bool] = None
    current_ma: Optional[float] = None
    source: str = "none"
    note: str = ""


# ---------------------------------------------------------------------------
# Generic sysfs fallback (unchanged behavior from v1)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# INA219 (SeenGreat Pi Zero UPS HAT (B))
# ---------------------------------------------------------------------------

def _parse_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, int):
        return value
    return int(str(value), 0)  # accepts "0x43" and "67"


def resolve_i2c_bus(cfg: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """Return (bus_number, note). bus may be an int or "auto" in config."""
    value = cfg.get("ina219_i2c_bus", "auto")
    if str(value).strip().lower() != "auto":
        try:
            return _parse_int(value, -1), ""
        except ValueError:
            return None, f"invalid ina219_i2c_bus={value!r}"

    controller = str(cfg.get("ina219_i2c_controller", DEFAULT_I2C_CONTROLLER))
    base = Path("/sys/bus/i2c/devices")
    if not base.exists():
        return None, "no /sys/bus/i2c (I2C not available on this host)"
    for entry in sorted(base.glob("i2c-*")):
        try:
            target = os.path.realpath(entry)
        except OSError:
            continue
        if controller in target:
            try:
                return int(entry.name.split("-", 1)[1]), ""
            except ValueError:
                continue
    return None, (
        f"no I2C adapter for controller {controller} (is the I2C overlay enabled?). "
        "Set ina219_i2c_bus to the number shown by `i2cdetect -l`."
    )


def _i2c_read_u16(fd: int, reg: int) -> int:
    os.write(fd, bytes([reg]))
    data = os.read(fd, 2)
    if len(data) != 2:
        raise OSError(f"short read from register 0x{reg:02x}")
    return (data[0] << 8) | data[1]  # INA219 registers are MSB first


def read_ina219(cfg: Dict[str, Any]) -> Tuple[Optional[Dict[str, float]], str]:
    """Read bus voltage (V) and shunt voltage (mV) from the INA219.

    Uses only registers that are valid at the chip's power-on defaults
    (continuous shunt+bus conversion), so no calibration write is needed and we never
    reconfigure a chip the HAT firmware/hardware may rely on.
    Returns (reading or None, note).
    """
    try:
        import fcntl  # Linux only
    except ImportError:
        return None, "fcntl unavailable (not Linux)"

    bus, note = resolve_i2c_bus(cfg)
    if bus is None:
        return None, note

    try:
        addr = _parse_int(cfg.get("ina219_address", "0x43"), 0x43)
    except ValueError:
        return None, f"invalid ina219_address={cfg.get('ina219_address')!r}"

    dev = f"/dev/i2c-{bus}"
    if not Path(dev).exists():
        return None, f"{dev} does not exist (enable the I2C overlay, check ina219_i2c_bus)"

    try:
        fd = os.open(dev, os.O_RDWR)
    except PermissionError:
        return None, f"permission denied on {dev} (add your user to the 'i2c' group or run the daemon as root)"
    except OSError as exc:
        return None, f"cannot open {dev}: {exc}"

    try:
        fcntl.ioctl(fd, I2C_SLAVE, addr)
        bus_raw = _i2c_read_u16(fd, INA219_REG_BUS_VOLTAGE)
        shunt_raw = _i2c_read_u16(fd, INA219_REG_SHUNT_VOLTAGE)
    except OSError as exc:
        return None, f"INA219 not responding at 0x{addr:02x} on {dev}: {exc}. {POGO_HINT}"
    finally:
        os.close(fd)

    if shunt_raw & 0x8000:
        shunt_raw -= 1 << 16
    voltage_v = ((bus_raw >> 3) * 4) / 1000.0
    shunt_mv = shunt_raw * 0.01
    if bus_raw & 0x01:
        note = "INA219 math overflow flag set (reading may be invalid)"
    return {"voltage_v": voltage_v, "shunt_mv": shunt_mv, "bus": float(bus)}, note


def lipo_percent(voltage_v: float, curve: Optional[List[Tuple[float, int]]] = None) -> int:
    pts = sorted(curve or DEFAULT_LIPO_CURVE)
    if voltage_v <= pts[0][0]:
        return pts[0][1]
    if voltage_v >= pts[-1][0]:
        return pts[-1][1]
    for (v0, p0), (v1, p1) in zip(pts, pts[1:]):
        if v0 <= voltage_v <= v1:
            if v1 == v0:
                return p1
            return int(round(p0 + (p1 - p0) * (voltage_v - v0) / (v1 - v0)))
    return pts[-1][1]


def _curve_from_cfg(cfg: Dict[str, Any]) -> Optional[List[Tuple[float, int]]]:
    raw = cfg.get("battery_voltage_curve")
    if not isinstance(raw, list) or len(raw) < 2:
        return None
    try:
        return [(float(v), int(p)) for v, p in raw]
    except Exception:
        return None


def _ina219_state(cfg: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    reading, note = read_ina219(cfg)
    if reading is None:
        return None, note

    voltage = reading["voltage_v"]
    if voltage < 2.5:
        # A floating/absent cell or a bad pogo contact usually reads ~0 V.
        return None, f"INA219 bus voltage {voltage:.2f} V is implausible for a LiPo (battery disconnected?)"

    shunt_mv = reading["shunt_mv"]
    # TODO(verify on hardware): which shunt-voltage sign means "charging" depends on how
    # the HAT routes the INA219 shunt; confirm by plugging/unplugging USB-C and watching
    # `python3 scripts/power_profile.py`. Flip ina219_charging_sign if it is inverted.
    sign = 1.0 if str(cfg.get("ina219_charging_sign", "positive")).lower().startswith("pos") else -1.0
    threshold = float(cfg.get("ina219_charge_threshold_mv", 0.2))
    charging = (shunt_mv * sign) > threshold

    current_ma: Optional[float] = None
    shunt_ohms = float(cfg.get("ina219_shunt_ohms", 0) or 0)
    if shunt_ohms > 0:
        current_ma = round(shunt_mv / shunt_ohms * sign, 1)

    return {
        "percent": lipo_percent(voltage, _curve_from_cfg(cfg)),
        "voltage_v": round(voltage, 3),
        "charging": charging,
        "current_ma": current_ma,
    }, note


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------

def _classify(percent: int, plugged: bool, cfg: Dict[str, Any]) -> Tuple[bool, bool, str]:
    warn = int(cfg.get("battery_warn_pct", 20))
    crit = int(cfg.get("battery_critical_pct", 8))
    low = percent <= warn
    critical = percent <= crit
    mode = "normal"
    if critical and not plugged:
        mode = "ultra"
    elif low or critical:
        mode = "reduced"
    return low, critical, mode


def assess(cfg: Dict[str, Any]) -> PowerState:
    if not cfg.get("battery_monitor_enabled", False):
        return PowerState(percent=None, plugged_in=False, low=False, critical=False, recommended_mode="normal")

    notes: List[str] = []
    if cfg.get("ina219_enabled", True):
        ina, note = _ina219_state(cfg)
        if note:
            notes.append(note)
        if ina is not None:
            plugged = bool(ina["charging"])
            low, critical, mode = _classify(ina["percent"], plugged, cfg)
            return PowerState(
                percent=ina["percent"],
                plugged_in=plugged,
                low=low,
                critical=critical,
                recommended_mode=mode,
                voltage_v=ina["voltage_v"],
                charging=ina["charging"],
                current_ma=ina["current_ma"],
                source="ina219",
                note="; ".join(notes),
            )

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
        return PowerState(
            percent=None, plugged_in=bool(plug), low=False, critical=False,
            recommended_mode="normal", source="none", note="; ".join(notes),
        )

    low, critical, mode = _classify(capacity, bool(plug), cfg)
    return PowerState(
        percent=capacity,
        plugged_in=bool(plug),
        low=low,
        critical=critical,
        recommended_mode=mode,
        charging=plug,
        source="sysfs",
        note="; ".join(notes),
    )


def state_payload(state: PowerState) -> Dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "battery_pct": state.percent,
        "battery_v": state.voltage_v,
        "charging": state.charging,
        "current_ma": state.current_ma,
        "plugged_in": state.plugged_in,
        "low": state.low,
        "critical": state.critical,
        "recommended_mode": state.recommended_mode,
        "power_mode": state.recommended_mode,
        "battery_source": state.source,
        "note": state.note,
    }


def dump_state(path: str | Path, state: PowerState) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(state_payload(state), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, out)  # atomic, so UI/status readers never see a half-written file


# ---------------------------------------------------------------------------
# Daemon: periodic state file + warn/critical logging + safe shutdown
# ---------------------------------------------------------------------------

def _log(logfile: Optional[Path], msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    if logfile:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        with logfile.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def _shutdown_command(cfg: Dict[str, Any]) -> List[str]:
    cmd = cfg.get("battery_shutdown_command") or ["systemctl", "poweroff"]
    cmd = [str(c) for c in cmd]
    if hasattr(os, "geteuid") and os.geteuid() != 0 and shutil.which("sudo"):
        cmd = ["sudo", "-n"] + cmd  # non-interactive; fails cleanly without NOPASSWD
    return cmd


def run_daemon(cfg_path: Path, state_path: Path, logfile: Optional[Path], interval: float, dry_run: bool) -> int:
    critical_streak = 0
    last_note = None
    last_level = None
    _log(logfile, f"power daemon started interval={interval}s state={state_path}")

    while True:
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

        state = assess(cfg)
        dump_state(state_path, state)

        if state.note and state.note != last_note:
            _log(logfile, f"battery monitor: {state.note}")
        last_note = state.note

        level = "critical" if state.critical else "low" if state.low else "ok"
        if state.percent is not None and level != last_level:
            _log(
                logfile,
                f"battery {level}: {state.percent}% v={state.voltage_v} charging={state.charging} "
                f"mode={state.recommended_mode}",
            )
        last_level = level

        if state.critical and not state.charging:
            critical_streak += 1
        else:
            critical_streak = 0

        needed = int(cfg.get("battery_shutdown_confirm_reads", 3))
        if (
            cfg.get("battery_shutdown_enabled", True)
            and state.source == "ina219"  # only act on a real, plausible reading
            and critical_streak >= max(1, needed)
        ):
            cmd = _shutdown_command(cfg)
            _log(logfile, f"battery critical for {critical_streak} reads, shutting down safely: {' '.join(cmd)}")
            if dry_run:
                _log(logfile, "dry-run: shutdown skipped")
                critical_streak = 0
            else:
                try:
                    subprocess.run(["sync"], check=False)
                    proc = subprocess.run(cmd, check=False)
                    if proc.returncode != 0:
                        _log(logfile, f"shutdown command failed (code={proc.returncode}); run the daemon as root")
                except Exception as exc:
                    _log(logfile, f"shutdown command failed: {exc}")

        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Battery monitor (INA219 / sysfs)")
    parser.add_argument("--config", default=str(ROOT_DIR / "config" / "default.json"))
    parser.add_argument("--daemon", action="store_true", help="Loop forever, write state file, handle critical shutdown")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--state", default=str(ROOT_DIR / "data" / "runtime" / "state.json"))
    parser.add_argument("--log", default=str(ROOT_DIR / "logs" / "power-daemon.log"))
    parser.add_argument("--dry-run", action="store_true", help="Never actually shut down")
    args = parser.parse_args()

    if args.daemon:
        return run_daemon(Path(args.config), Path(args.state), Path(args.log), args.interval, args.dry_run)

    try:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    print(json.dumps(state_payload(assess(cfg)), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
