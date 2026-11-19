# Survival AI Device Enclosure

Rugged 3D-printable case for the real build stack:
Orange Pi Zero 2W (4GB) + SeenGreat Pi Zero UPS HAT (B) with a flat LiPo pouch cell +
jumper-wired red-PCB 2.8" SPI TFT + small round SPI TFT + rotary encoder.  
**Design aesthetic:** Pip-Boy inspired tactical field device — chunky, functional, survival-ready.

> ⚠️ **Status: the SCAD geometry has not been updated for this stack yet.** `surv-ai-case.scad`
> still models the original concept: a Waveshare 2.8" LCD HAT, 2×18650 cells, and no round
> display. Its battery bay, LCD window/standoffs and encoder hole need re-measuring against the
> real parts (see the `TODO` block at the top of the file). The assembly order below already
> describes the real stack. Wiring is in [`../docs/wiring.md`](../docs/wiring.md).

---

## 📐 What's Included

- `surv-ai-case.scad` — OpenSCAD parametric design file
- `assembly-diagram.txt` — Visual assembly guide
- This README

---

## 🖨️ Print Settings

### Recommended Settings
| Setting | Value | Notes |
|---------|-------|-------|
| **Material** | PETG or PLA | PETG preferred for durability & temperature resistance |
| **Layer Height** | 0.2mm | Good balance of strength and print time |
| **Perimeters** | 3 | Ensures strong walls (2.5mm design thickness) |
| **Infill** | 20% | Gyroid or grid pattern |
| **Supports** | Yes | For port cutouts and overhangs |
| **Brim/Raft** | Optional | Brim recommended for bed adhesion |
| **Print Speed** | 50-60mm/s | Slower = better quality for functional parts |

### Color Suggestions (for tactical look)
- **Primary:** Olive Drab, Forest Green, Desert Tan, Black
- **Accent:** Orange, Safety Yellow (for visibility in field conditions)

### Before Printing
1. Open `surv-ai-case.scad` in OpenSCAD (free download: openscad.org)
2. Set `PRINT_PART = "bottom"` at top of file
3. Render (F6) — this may take 1-2 minutes
4. Export STL: **File → Export → Export as STL**
5. Repeat for `PRINT_PART = "top"`
6. Slice both STLs in your slicer (Cura, PrusaSlicer, etc.)

### Print Orientation
- **Bottom shell:** Print as-is (flat side down)
- **Top shell:** Already oriented upside-down in the file (flat side down)

---

## 🔩 Hardware BOM (Non-Printed Parts)

| Qty | Part | Spec | Purpose | Source |
|-----|------|------|---------|--------|
| 4 | M3 heat-set inserts | OD: 4.5mm, Length: 4-5mm | Bottom shell screw bosses | Amazon, McMaster |
| 4 | M3 screws | 10mm length, button head | Shell assembly | Hardware store |
| 8 | M2.5 screws | 6mm length | PCB mounting | Electronics supplier |
| 1 | Silicone gasket material | 2mm thick (optional) | Weatherproofing seal | Amazon |
| 1 | Clear acrylic sheet | 0.5mm thick (optional) | LCD screen protector | Local plastics supplier |

**Heat-set insert installation:**  
Use a soldering iron set to 200-220°C (for PLA) or 240-260°C (for PETG). Press insert slowly until flush with surface. Let cool before removing iron.

---

## 🔧 Assembly Instructions

### Step 1: Prepare Printed Parts
1. Remove all support material carefully
2. Test-fit components — file or sand any tight spots
3. Clean screw holes with M3 tap (optional, but recommended)
4. Install M3 heat-set inserts in the 4 corner bosses of the **bottom shell**

### Step 2: Install the LiPo pouch cell & SeenGreat UPS HAT (B)
1. Lay the flat 3.7 V LiPo pouch cell in the bottom shell. Pad it with foam tape, never
   clamp or puncture it, and keep it away from screw tips and sharp edges
2. Mount the SeenGreat Pi Zero UPS HAT (B) on its standoffs with the **power switch OFF**
3. Plug the cell into the HAT's 2-pin battery connector (⚠️ check polarity on the silkscreen)
4. Leave the HAT's USB-C input and solar terminal block reachable through side cutouts.
   The case has no separate MPPT controller: it's built into the HAT

### Step 3: Install Orange Pi Zero 2W (on the pogo pins)
1. Solder or press-fit the 40-pin header first (the board ships without one)
2. Set the Pi on top of the HAT so its spring **pogo pins** touch the underside of the header
3. Fasten the standoffs. Their height sets the pogo-pin compression: too tall and the
   contact is intermittent (the INA219 battery monitor drops out), too short and the pins bend
4. Switch the HAT ON and check the Pi boots from battery before closing anything
5. Verify the HAT's USB-C and the Pi's ports align with side cutouts

### Step 4: Install the displays (jumper-wired)
1. The 2.8" red-PCB SPI TFT is **not a HAT**: mount it behind the top-shell window
   (standoffs/clips through its corner holes) and wire it with jumper wires per
   `docs/wiring.md`. Leave its SDO/MISO pin unconnected
2. Mount the small round SPI TFT (blue breakout) behind its own round window
   (⚠️ needs a new cutout in the SCAD, TODO)
3. Keep the shared SPI wires (SCK/MOSI/MISO) short and bundled. Long jumpers may need a lower
   `spi-max-frequency` in the overlay
4. Verify the TFT's active area aligns with the top shell window

### Step 5: Install Rotary Encoder (CLK/DT/SW/+/GND module)
1. Thread encoder shaft through hole in top shell
2. Secure encoder body to underside of top shell with hot glue or double-sided tape
3. Wire CLK/DT/SW to the header pins in `docs/wiring.md`. Power `+` from **3.3 V, not 5 V**
4. Attach encoder knob to shaft (press-fit or set screw)

### Step 6: Final Assembly
1. Route all wires neatly — avoid pinching at shell interface
2. Align top shell to bottom shell (use alignment pins)
3. Insert 4× M3 screws through top shell into heat-set inserts
4. Tighten in diagonal pattern (like lug nuts) for even pressure
5. Don't overtighten — plastic can crack

### Step 7: Optional Weatherproofing
- Cut silicone gasket strip to fit shell interface perimeter
- Apply thin bead of silicone sealant around LCD window bezel
- Conformal coating on PCBs (spray before assembly)
- Add clear acrylic sheet over LCD window for scratch protection

---

## 🧪 Testing

After assembly:
1. **Power test:** Connect USB-C to the UPS HAT, verify LEDs light up. Unplug and check it stays up on battery
2. **Battery monitor:** `python3 scripts/power_profile.py` reports `"battery_source": "ina219"` (if not, check standoff height / pogo contact)
3. **Display test:** Boot device, check the 2.8" TFT (`./scripts/test-display.sh`) and the round status display
3. **Port access:** Verify all USB/HDMI ports are accessible with cables
4. **Encoder test:** Rotate knob, confirm input response
5. **Thermal test:** Run device for 30 minutes, check for overheating (ventilation should prevent this)

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| **Battery % missing / INA219 not found** | Pogo pins not making contact: check standoff height and that the header is flush; confirm `i2cdetect` shows `43` |
| **LCD doesn't fit window** | Adjust `lcd_active_width` / `lcd_active_height` variables in .scad file |
| **Ports don't align** | Check Orange Pi orientation — may be 180° rotated |
| **Case won't close** | Check for wire pinching, component interference, or warped print |
| **Screws strip threads** | Use heat-set inserts (essential for PETG), don't overtighten |
| **Overheating** | Ensure ventilation slots are clear; consider adding heatsink to SoC |

---

## 🔄 Modifications

The OpenSCAD file is fully parametric. Common tweaks:

### Make it bigger/smaller
Adjust `case_length`, `case_width`, `case_height` at top of file.

### Change wall thickness
Modify `wall_thickness` variable (2mm minimum recommended).

### Add more ventilation
Increase `vent_array()` count in top/bottom shell modules.

### Customize port layout
Reposition port cutout `translate()` coordinates to match your board revision.

### Add mounting holes
Add MOLLE clip mounting points, belt clip, or tripod mount threads.

---

## 📏 Dimensions Reference

| Component | Dimensions (L × W × H) |
|-----------|------------------------|
| **External Case** | 75 × 65 × 52 mm |
| **Internal Cavity** | 70 × 60 × 47 mm |
| **Weight (empty)** | ~80g (PLA), ~85g (PETG) |
| **Weight (loaded)** | TODO: weigh with pouch cell & electronics (old ~220g figure assumed 2×18650) |

---

## 🌧️ Weatherproofing Tips

For true field use:
1. **Conformal coating:** Spray PCBs with MG Chemicals 422B or similar before assembly
2. **Gasket seal:** Use 2mm silicone sheet between shells (cut window for LCD)
3. **Port plugs:** 3D print or use rubber plugs for unused ports
4. **Lanyard attachment:** Use paracord through lanyard hole — adds drop protection
5. **Screen protector:** Adhere clear polycarbonate or acrylic over LCD window

**IP Rating (with modifications):** IP54 achievable (dust-protected, splash-resistant)

---

## 📦 Print Time Estimate

- **Bottom shell:** 6-8 hours (0.2mm layers)
- **Top shell:** 4-6 hours (0.2mm layers)
- **Total:** ~12-14 hours

**Filament usage:** ~120-150g total

---

## 🧰 Tools Needed for Assembly

- Soldering iron (for heat-set inserts)
- Small Phillips screwdriver
- Needle-nose pliers
- Wire cutters/strippers
- Multimeter (for electrical testing)
- Hot glue gun (optional, for encoder mounting)
- Files or sandpaper (for cleanup)

---

## 📝 Design Notes

### Why These Choices?

**2.5mm walls:** Strong enough for drops, thin enough for reasonable print time.

**Screw assembly (not snap-fit):** Field-repairable. Snap tabs break; screws don't.

**Ventilation on all sides:** Passive cooling for Orange Pi SoC under load.

**Rounded edges:** Comfort during extended holding, less likely to snag on gear.

**Visible screw bosses:** Embraces the "tactical field device" aesthetic — function over form.

**Heat-set inserts:** Allows disassembly 50+ times without thread wear.

---

## 🔓 License

Open source hardware design. Do whatever you want with it.  
Attribution appreciated but not required.

---

## 🐛 Issues / Improvements

If you modify this design or find issues, document them:
- Adjust tolerances for your printer (± 0.2mm typical)
- Test fit components before full assembly
- Share improvements (better cooling, mounting options, etc.)

**This is version 1.0** — a starting point, not a final product. Iterate and improve!

---

## 💡 Future Enhancements (Ideas)

- Integrated solar panel mounting points
- Radiation shielding compartment (aluminum tape)
- Emergency whistle integrated into vent slots
- Magnetic mount for vehicle/metal surface attachment
- Waterproof membrane buttons (TPU overmold)
- Tritium vial slots for low-light visibility
- Integrated compass bezel ring

---

**Happy printing! Stay alive out there. 🏕️**
