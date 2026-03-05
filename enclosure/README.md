# Survival AI Device Enclosure

Rugged 3D-printable case for Orange Pi Zero 2W + Waveshare 2.8" LCD + UPS HAT B  
**Design aesthetic:** Pip-Boy inspired tactical field device — chunky, functional, survival-ready.

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

### Step 2: Install Batteries & UPS HAT
1. Place 2× 18650 batteries in the bottom shell compartment (side-by-side)
2. Secure battery holder (if using separate holder)
3. Mount UPS HAT B on standoffs above batteries
4. Secure with M2.5 screws (do NOT overtighten — PCBs are fragile)

### Step 3: Install Orange Pi Zero 2W
1. Connect Orange Pi to UPS HAT via GPIO/pogo pins
2. Align carefully — pins are delicate
3. Press gently until fully seated
4. Verify USB-C, HDMI, and USB ports align with side cutouts

### Step 4: Install LCD HAT
1. Connect Waveshare LCD HAT to Orange Pi GPIO header
2. Use spacers if needed to prevent strain on pins
3. Secure with M2.5 screws to PCB standoffs
4. Verify LCD active area aligns with top shell window

### Step 5: Install Rotary Encoder (KY-040)
1. Thread encoder shaft through hole in top shell
2. Secure encoder body to underside of top shell with hot glue or double-sided tape
3. Route wires to Orange Pi GPIO pins (connect before closing case)
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
1. **Power test:** Connect USB-C power, verify LEDs light up
2. **Display test:** Boot device, check LCD displays correctly
3. **Port access:** Verify all USB/HDMI ports are accessible with cables
4. **Encoder test:** Rotate knob, confirm input response
5. **Thermal test:** Run device for 30 minutes, check for overheating (ventilation should prevent this)

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
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
| **Weight (loaded)** | ~220g (with batteries & electronics) |

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
