# Wiring — Orange Pi Zero 2W

Pin-by-pin wiring from the Orange Pi Zero 2W 40-pin header to:

- the 2.8" red-PCB SPI TFT with resistive touch (probably ILI9341 + XPT2046),
- the round SPI TFT on a blue breakout (probably GC9A01, 240×240),
- the rotary encoder module (CLK / DT / SW / + / GND).

The SeenGreat Pi Zero UPS HAT (B) needs no wires: it sits under the board on spring pogo pins.

> **Read this first**
> - All signal pins are **3.3 V logic**. Never connect a module's `+`/`VCC` to 5 V if that
>   same rail also pulls up a GPIO line (the encoder in particular).
> - Rows marked ⚠️ are assumptions that this repo could not confirm from a datasheet or
>   source. Check them against the silkscreen on *your* boards before powering on.
> - **The I2C and SPI bus numbers are not the Raspberry Pi ones.** The header *positions*
>   for power, I2C and SPI match a Raspberry Pi. The Linux device numbers do not (see
>   [Bus numbers](#bus-numbers-differ-from-a-raspberry-pi)).

## Sources

The header table was taken from Orange Pi's own `wiringOP` source
(`orangepi-xunlong/wiringOP`, branch `next`: `physToGpio_ZERO_2_W` in `wiringPi/wiringPi.c`
and `physNames_ZERO_2_W` in `gpio/readall.c`). The SPI1/I2C1 pin functions were
cross-checked against `sun50i-h616.dtsi` and the overlays in Orange Pi's 6.1 kernel tree
(`orangepi-xunlong/linux-orangepi`, branch `orange-pi-6.1-sun50iw9`). On the board,
`gpio readall` (from wiringOP) prints the same table, so you can check against it.

GPIO numbers follow the Allwinner convention **bank × 32 + pin**: PC=2, PH=7, PI=8.
For example, PI12 = 8×32+12 = **268**. With libgpiod they are the line *offsets* on the main
pin controller (`gpiodetect` label `300b000.pinctrl`), which is what `config/default.json`
uses. ⚠️ Newer kernels can give that chip a non-zero *sysfs* base (e.g. 512+), so the
`/sys/class/gpio` numbers would shift. The libgpiod offsets do not.

## 40-pin header reference (Orange Pi Zero 2W)

| Function | GPIO | Pin | Pin | GPIO | Function |
|---|---|:-:|:-:|---|---|
| 3.3V | — | 1 | 2 | — | 5V ⚡UPS |
| PI8 TWI1-SDA ⚡UPS | 264 | 3 | 4 | — | 5V ⚡UPS |
| PI7 TWI1-SCL ⚡UPS | 263 | 5 | 6 | — | GND ⚡UPS |
| PI13 PWM3 | 269 | 7 | 8 | 224 | PH0 UART0-TX (debug console) |
| GND | — | 9 | 10 | 225 | PH1 UART0-RX (debug console) |
| PH2 UART5-TX | 226 | 11 | 12 | 257 | PI1 |
| PH3 UART5-RX | 227 | 13 | 14 | — | GND |
| PI5 UART2-TX | 261 | 15 | 16 | 270 | PI14 PWM4 |
| 3.3V | — | 17 | 18 | 228 | **PH4 → TFT DC** |
| **PH7 SPI1-MOSI** | 231 | 19 | 20 | — | GND |
| **PH8 SPI1-MISO** | 232 | 21 | 22 | 262 | **PI6 → TFT RESET** |
| **PH6 SPI1-SCLK** | 230 | 23 | 24 | 229 | **PH5 SPI1-CS0 → TFT CS** |
| GND | — | 25 | 26 | 233 | **PH9 SPI1-CS1 → round CS** |
| PI10 TWI2-SDA | 266 | 27 | 28 | 265 | PI9 TWI2-SCL |
| **PI0 → round DC** | 256 | 29 | 30 | — | GND |
| **PI15 → round RST** | 271 | 31 | 32 | 267 | PI11 PWM1 |
| **PI12 → encoder CLK** | 268 | 33 | 34 | — | GND |
| **PI2 → encoder DT** | 258 | 35 | 36 | 76 | PC12 |
| **PI16 → encoder SW** | 272 | 37 | 38 | 260 | PI4 → touch T_CS (optional) |
| GND | — | 39 | 40 | 259 | PI3 → touch T_IRQ (optional) |

⚡UPS = shared with the UPS HAT through its pogo pins. ⚠️ **TODO (verify): which header pins
the SeenGreat HAT's pogo pins actually touch.** At minimum it needs 5V and GND to power the
board, and SDA/SCL (pins 3/5) so the INA219 can be read over I2C. Do not wire anything else
to pins 3/5 (I2C devices with *different* addresses could share the bus, but nothing in this
build needs to).

Pins left free: 7, 11, 12, 13, 15, 16, 27, 28, 32, 36. Pins 8/10 (UART0) are kept free as the
serial debug console.

## 2.8" SPI TFT (red PCB, jumper wires)

The 14-pin label set `VCC GND CS RESET DC SDI(MOSI) SCK LED SDO(MISO) T_CLK T_CS T_DIN T_DO T_IRQ`
is the common layout of the red 2.8" 240×320 ILI9341 + XPT2046 module. ⚠️ **TODO (verify):**
the same PCB is also sold with other controllers (e.g. ST7789). Check the listing or the
marking on the flex cable. If it isn't an ILI9341, change `compatible` in
`overlays/survival-tft-zero2w.dts`.

| TFT pin | Header pin | Orange Pi signal | GPIO | Notes |
|---|:-:|---|---|---|
| VCC | 17 (or 1) | 3.3V | — | ⚠️ Many of these boards carry a 3.3 V regulator with a solder jumper (often `J1`) to bypass it. 3.3 V is the conservative choice. Check your board before using 5 V. |
| GND | 20 (or 25) | GND | — | |
| CS | 24 | PH5 SPI1-CS0 | 229 | kernel driver, `reg = <0>` |
| RESET | 22 | PI6 | 262 | active low |
| DC (a.k.a. RS / D/C) | 18 | PH4 | 228 | |
| SDI (MOSI) | 19 | PH7 SPI1-MOSI | 231 | shared with round display + touch |
| SCK | 23 | PH6 SPI1-SCLK | 230 | shared with round display + touch |
| LED (backlight) | 17 (3.3V) | 3.3V | — | ⚠️ always-on. To switch/PWM it, use a free pin (e.g. 32 PI11 PWM1) and check the board has a backlight transistor before driving it from a GPIO. |
| SDO (MISO) | — | *leave unconnected* | — | The display is write-only here. Several reports say this module's SDO does not tri-state cleanly, which can break touch reads on the shared MISO line. |
| T_CLK | 23 | PH6 SPI1-SCLK | 230 | shared |
| T_CS | 38 | PI4 | 260 | ⚠️ optional, see [Touch](#touch-optional) |
| T_DIN | 19 | PH7 SPI1-MOSI | 231 | shared |
| T_DO | 21 | PH8 SPI1-MISO | 232 | only device driving MISO |
| T_IRQ | 40 | PI3 | 259 | ⚠️ optional, active low (pen down) |

### Touch (optional)

The UI is driven by the rotary encoder, so touch is wired but **not enabled by default**.
SPI1 only has two hardware chip selects (CS0 = TFT, CS1 = round display), so touch needs a
GPIO chip select. The overlay contains a commented sketch (`cs-gpios` + `ti,ads7846`).
⚠️ TODO: it is unverified whether the sun6i SPI driver honours `cs-gpios` on your kernel.
If you don't enable touch, keep T_CS from floating low: tie T_CS to 3.3 V instead of pin 38,
or keep PI4 driven high.

## Round SPI TFT (blue breakout, probably GC9A01 240×240)

⚠️ **TODO (verify):** controller and pin labels. Common round 1.28" GC9A01 breakouts are
labelled `VCC GND SCL SDA DC CS RST` (some add `BLK`/`BL`). Despite the I2C-style names,
`SCL`/`SDA` are the **SPI clock / MOSI**.

| Round pin | Header pin | Orange Pi signal | GPIO | Notes |
|---|:-:|---|---|---|
| VCC | 1 (or 17) | 3.3V | — | ⚠️ check whether your breakout has its own regulator |
| GND | 25 (or 30) | GND | — | |
| SCL / CLK | 23 | PH6 SPI1-SCLK | 230 | shared |
| SDA / DIN | 19 | PH7 SPI1-MOSI | 231 | shared |
| CS | 26 | PH9 SPI1-CS1 | 233 | `/dev/spidev1.1` (userspace) |
| DC | 29 | PI0 | 256 | `status_display.dc_line` |
| RST | 31 | PI15 | 271 | `status_display.rst_line` |
| BLK / BL (if present) | 1 / 17 | 3.3V | — | always on (or leave open if the board pulls it up) |

Driven by `scripts/status_display.py` through spidev, so no kernel driver is needed. Turn it
on with `"status_display": {"enabled": true}` in `config/default.json`. It shows battery %,
voltage, charging and power mode from `data/runtime/state.json`.

## Rotary encoder module (CLK, DT, SW, +, GND)

| Encoder pin | Header pin | Orange Pi signal | GPIO | Notes |
|---|:-:|---|---|---|
| CLK (A) | 33 | PI12 | 268 | `encoder.clk_line` |
| DT (B) | 35 | PI2 | 258 | `encoder.dt_line` |
| SW (push) | 37 | PI16 | 272 | `encoder.sw_line`, active low |
| + | 17 (or 1) | **3.3V** | — | **Not 5 V**: the module's pull-ups go to `+`, so 5 V would put 5 V on the GPIOs. |
| GND | 34 (or 39) | GND | — | |

The code also requests internal pull-ups (libgpiod bias), because many modules have no pull-up
on SW. ⚠️ Bias support depends on libgpiod ≥ 1.5 and the kernel. If SW reads stuck low or
floating, add a 10 kΩ resistor from SW to 3.3 V. If rotation is backwards, set
`encoder.invert: true`. If one click moves two steps, set `encoder.steps_per_detent: 2`.

Test it: `python3 scripts/hw_input.py` prints `cw`, `ccw` and `press`.

## Bus numbers differ from a Raspberry Pi

| | Raspberry Pi | Orange Pi Zero 2W |
|---|---|---|
| I2C on pins 3/5 | `/dev/i2c-1` | controller **`i2c1` @ `0x05002400`** (PI7/PI8). The board DTS defines **no i2c aliases** and other I2C controllers are already enabled (`r_i2c`, and `i2c3` for the on-board AC200), so the `/dev/i2c-N` number depends on probe order. **Run `i2cdetect -l`** and look for `5002400.i2c`. `config/default.json` uses `"ina219_i2c_bus": "auto"`, which finds it through sysfs. |
| SPI on pins 19/21/23/24/26 | `/dev/spidev0.0`, `0.1` | controller **`spi1` @ `0x05011000`**. Orange Pi's overlays alias it as `spi1`, so it shows up as **`/dev/spidev1.0`** / **`/dev/spidev1.1`**. (`spi0` is the on-board SPI flash.) |

Check the UPS HAT: `sudo i2cdetect -y <N>` should show **`43`**.

## Enabling I2C and SPI (device-tree overlays)

Overlay names confirmed in Orange Pi's 6.1 kernel tree (`arch/arm64/boot/dts/allwinner/overlay/Makefile`):

| Need | Overlay (prefix `sun50i-h616-`) | Notes |
|---|---|---|
| I2C on pins 3/5 (UPS HAT INA219) | `pi-i2c1` | enables `i2c1` with `i2c1_pi_pins` (PI7/PI8) |
| SPI1 as two raw spidev devices (bring-up test only) | `spi1-cs0-cs1-spidev` | **don't** combine with our TFT overlay |
| 2.8" TFT + round display | `overlays/survival-tft-zero2w.dts` (this repo) | fbtft ILI9341 on CS0, spidev on CS1 |

**Orange Pi Debian/Ubuntu image.** Edit `/boot/orangepiEnv.txt`, then reboot:

```
overlay_prefix=sun50i-h616
overlays=pi-i2c1
user_overlays=survival-tft-zero2w
```

Copy the compiled `survival-tft-zero2w.dtbo` to `/boot/overlay-user/`. ⚠️ TODO: confirm the
file name and keys on your image (`cat /boot/orangepiEnv.txt`). `orangepi-config`, if present,
can toggle the stock overlays.

**Armbian.** Edit `/boot/armbianEnv.txt`. ⚠️ TODO: Armbian's overlay names can differ from
Orange Pi's, so list them with `ls /boot/dtb/allwinner/overlay/ | grep -E 'i2c|spi'` and pick the
one for I2C1 on the **PI** pins. Install the TFT overlay with
`sudo armbian-add-overlay overlays/survival-tft-zero2w.dts` (it compiles and registers it).

After rebooting:

```bash
ls /dev/i2c-* /dev/spidev*            # expect an i2c adapter for 5002400.i2c and /dev/spidev1.1
i2cdetect -l                           # find the bus number for 5002400.i2c
sudo i2cdetect -y <N>                  # expect 43 (INA219 on the UPS HAT)
cat /sys/class/graphics/fb*/name       # expect fb_ili9341 (TFT); HDMI may own fb0
gpiodetect                             # expect a chip labelled 300b000.pinctrl
python3 scripts/power_profile.py       # battery_source should be "ina219"
```

## Running the UI on the TFT

The TFT is a plain Linux framebuffer, so the existing curses UI runs on a text console mapped
onto it:

```bash
sudo apt install fbset kbd            # con2fbmap, setfont, openvt
sudo scripts/ui-tft.sh                # maps tty1 -> TFT framebuffer, runs scripts/ui.py there
```

To map the console at boot instead, add `fbcon=map:<n>` (n = TFT framebuffer number) to
`extraargs=` in the env file. With an 8×16 console font, 320×240 gives 40×15 characters. A
6×12 Terminus font (`TFT_FONT=...`) fits about 53×20.

Example systemd units (adjust paths and user):

```ini
# /etc/systemd/system/surv-power.service
[Unit]
Description=Survival device battery monitor
[Service]
ExecStart=/home/orangepi/survival-device/scripts/power_daemon.sh 30
Restart=always
[Install]
WantedBy=multi-user.target

# /etc/systemd/system/surv-status.service   (round display, optional)
[Unit]
Description=Survival device round status display
After=surv-power.service
[Service]
ExecStart=/usr/bin/python3 /home/orangepi/survival-device/scripts/status_display.py
Restart=on-failure
[Install]
WantedBy=multi-user.target
```

The power daemon runs as root so its safe shutdown at critical battery is allowed. Other
users need to be in the `i2c` / `gpio` / `spi` groups (names vary by image) to reach
`/dev/i2c-*`, `/dev/gpiochip*` and `/dev/spidev*`.
