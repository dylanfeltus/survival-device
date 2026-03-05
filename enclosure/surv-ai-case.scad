// ============================================================================
// SURVIVAL AI DEVICE ENCLOSURE
// Rugged 3D-printable case for Orange Pi Zero 2W + Waveshare LCD + UPS HAT
// Pip-Boy inspired tactical field device aesthetic
// ============================================================================

// ============================================================================
// RENDER SELECTOR - Comment/uncomment to choose what to render
// ============================================================================
PRINT_PART = "assembly"; // Options: "top", "bottom", "assembly"

// ============================================================================
// GLOBAL SETTINGS
// ============================================================================
$fn = 60; // Smooth curves - increase for final export

// ============================================================================
// DIMENSIONAL PARAMETERS - All measurements in mm
// ============================================================================

// Case dimensions
case_length = 75;           // External length (X axis)
case_width = 65;            // External width (Y axis) 
case_height = 52;           // Total external height (Z axis)
wall_thickness = 2.5;       // Sturdy walls for field use
corner_radius = 2;          // Rounded edges for comfort
split_height = 26;          // Where top/bottom shells meet

// PCB dimensions
pcb_length = 65;            // Orange Pi / UPS HAT length
pcb_width_pi = 30;          // Orange Pi width
pcb_width_lcd = 56;         // LCD HAT width (widest component)
pcb_thickness = 1.6;        // Standard PCB thickness

// Component clearances
component_clearance = 3;    // Space above components
bottom_clearance = 2;       // Space below solder joints
gpio_pin_height = 8;        // GPIO header height
standoff_diameter = 5;      // PCB mounting post diameter
standoff_hole_dia = 2.5;    // M2.5 hole for PCB mounting screws

// Battery dimensions
battery_diameter = 18.5;    // 18650 battery diameter (+ tolerance)
battery_length = 65.5;      // 18650 battery length (+ tolerance)
battery_holder_height = 21; // Total height of battery holder assembly

// LCD display
lcd_active_width = 57;      // Visible display width
lcd_active_height = 43;     // Visible display height
lcd_bezel_overlap = 1;      // Bezel covers edge of screen

// Rotary encoder
encoder_shaft_dia = 7;      // Shaft hole diameter (6mm + tolerance)
encoder_body_size = 12;     // Body clearance

// Port cutouts (micro-HDMI, USB-C, USB 2.0)
port_hdmi_width = 7;
port_hdmi_height = 3.5;
port_usbc_width = 9;
port_usbc_height = 3.5;
port_usb2_width = 8;
port_usb2_height = 4;

// Ventilation
vent_width = 3;             // Individual slot width
vent_length = 20;           // Slot length
vent_spacing = 5;           // Space between slots

// Assembly hardware
screw_hole_dia = 3.2;       // M3 screw clearance hole
screw_head_dia = 6;         // M3 screw head counterbore
screw_head_depth = 2;       // Counterbore depth
heat_set_dia = 4.5;         // M3 heat-set insert hole
boss_diameter = 8;          // Screw boss diameter

// ============================================================================
// UTILITY MODULES
// ============================================================================

// Rounded rectangle for case shells
module rounded_rect(x, y, z, r) {
    hull() {
        translate([r, r, 0])
            cylinder(h=z, r=r);
        translate([x-r, r, 0])
            cylinder(h=z, r=r);
        translate([r, y-r, 0])
            cylinder(h=z, r=r);
        translate([x-r, y-r, 0])
            cylinder(h=z, r=r);
    }
}

// Screw boss with heat-set insert hole
module screw_boss(height, insert=true) {
    difference() {
        cylinder(d=boss_diameter, h=height);
        if (insert) {
            translate([0, 0, -0.1])
                cylinder(d=heat_set_dia, h=height+0.2);
        }
    }
}

// Ventilation slot array
module vent_array(num_slots, vertical=false) {
    for (i = [0:num_slots-1]) {
        translate([0, i * vent_spacing, 0])
            if (vertical) {
                cube([vent_width, vent_length, wall_thickness*2]);
            } else {
                cube([vent_length, vent_width, wall_thickness*2]);
            }
    }
}

// PCB standoff post
module pcb_standoff(height) {
    difference() {
        cylinder(d=standoff_diameter, h=height);
        translate([0, 0, height-3])
            cylinder(d=standoff_hole_dia, h=3.2);
    }
}

// ============================================================================
// BOTTOM SHELL
// ============================================================================
module bottom_shell() {
    difference() {
        // Main body
        union() {
            // Outer shell
            rounded_rect(case_length, case_width, split_height, corner_radius);
            
            // Screw bosses at corners
            translate([6, 6, 0])
                screw_boss(split_height-2, insert=true);
            translate([case_length-6, 6, 0])
                screw_boss(split_height-2, insert=true);
            translate([6, case_width-6, 0])
                screw_boss(split_height-2, insert=true);
            translate([case_length-6, case_width-6, 0])
                screw_boss(split_height-2, insert=true);
            
            // PCB standoffs for UPS HAT (above batteries)
            translate([case_length/2 - pcb_length/2 + 3, case_width/2 - pcb_width_pi/2 + 3, battery_holder_height + 1]) {
                translate([2.5, 2.5, 0]) pcb_standoff(3);
                translate([60, 2.5, 0]) pcb_standoff(3);
                translate([2.5, 25, 0]) pcb_standoff(3);
                translate([60, 25, 0]) pcb_standoff(3);
            }
        }
        
        // Hollow interior
        translate([wall_thickness, wall_thickness, 2])
            cube([case_length - wall_thickness*2, 
                  case_width - wall_thickness*2, 
                  split_height]);
        
        // Battery compartment
        translate([case_length/2 - battery_length/2, case_width/2 - battery_diameter, 2]) {
            // Battery 1
            rotate([0, 90, 0])
                cylinder(d=battery_diameter, h=battery_length);
            // Battery 2
            translate([0, battery_diameter, 0])
                rotate([0, 90, 0])
                    cylinder(d=battery_diameter, h=battery_length);
        }
        
        // Port cutouts on side (USB-C, HDMI, USB 2.0)
        // These are positioned where the Orange Pi ports would be
        port_z = battery_holder_height + 4;
        
        // USB-C power port
        translate([case_length - wall_thickness - 0.5, case_width/2 - 15, port_z])
            cube([wall_thickness*2, port_usbc_width, port_usbc_height]);
        
        // Micro-HDMI port
        translate([case_length - wall_thickness - 0.5, case_width/2 - 5, port_z])
            cube([wall_thickness*2, port_hdmi_width, port_hdmi_height]);
        
        // USB 2.0 port
        translate([case_length - wall_thickness - 0.5, case_width/2 + 5, port_z])
            cube([wall_thickness*2, port_usb2_width, port_usb2_height]);
        
        // Ventilation slots on sides
        translate([-0.1, 8, 8])
            rotate([0, 90, 0])
                vent_array(4, vertical=true);
        
        translate([case_length - vent_width + 0.1, case_width - 8 - vent_length, 8])
            rotate([0, 90, 0])
                vent_array(4, vertical=true);
        
        // Bottom ventilation slots
        translate([10, -0.1, 8])
            rotate([90, 0, 90])
                vent_array(3);
        
        // Screw holes for assembly
        translate([6, 6, split_height-8])
            cylinder(d=screw_hole_dia, h=10);
        translate([case_length-6, 6, split_height-8])
            cylinder(d=screw_hole_dia, h=10);
        translate([6, case_width-6, split_height-8])
            cylinder(d=screw_hole_dia, h=10);
        translate([case_length-6, case_width-6, split_height-8])
            cylinder(d=screw_hole_dia, h=10);
        
        // Lanyard loop hole
        translate([case_length - 8, case_width - 8, split_height - 6])
            rotate([0, 90, 0])
                cylinder(d=5, h=10);
    }
    
    // Alignment pins for top shell
    translate([case_length/2 - 15, wall_thickness + 1, split_height - 0.1]) {
        cylinder(d=3, h=2);
    }
    translate([case_length/2 + 15, case_width - wall_thickness - 1, split_height - 0.1]) {
        cylinder(d=3, h=2);
    }
}

// ============================================================================
// TOP SHELL
// ============================================================================
module top_shell() {
    difference() {
        union() {
            // Main body
            rounded_rect(case_length, case_width, case_height - split_height, corner_radius);
            
            // Screw bosses (receiving holes from bottom)
            translate([6, 6, 0]) {
                difference() {
                    cylinder(d=boss_diameter, h=8);
                    translate([0, 0, -0.1])
                        cylinder(d=screw_hole_dia, h=10);
                    translate([0, 0, 6])
                        cylinder(d=screw_head_dia, h=3);
                }
            }
            translate([case_length-6, 6, 0]) {
                difference() {
                    cylinder(d=boss_diameter, h=8);
                    translate([0, 0, -0.1])
                        cylinder(d=screw_hole_dia, h=10);
                    translate([0, 0, 6])
                        cylinder(d=screw_head_dia, h=3);
                }
            }
            translate([6, case_width-6, 0]) {
                difference() {
                    cylinder(d=boss_diameter, h=8);
                    translate([0, 0, -0.1])
                        cylinder(d=screw_hole_dia, h=10);
                    translate([0, 0, 6])
                        cylinder(d=screw_head_dia, h=3);
                }
            }
            translate([case_length-6, case_width-6, 0]) {
                difference() {
                    cylinder(d=boss_diameter, h=8);
                    translate([0, 0, -0.1])
                        cylinder(d=screw_hole_dia, h=10);
                    translate([0, 0, 6])
                        cylinder(d=screw_head_dia, h=3);
                }
            }
        }
        
        // Hollow interior
        translate([wall_thickness, wall_thickness, -0.1])
            cube([case_length - wall_thickness*2, 
                  case_width - wall_thickness*2, 
                  case_height - split_height]);
        
        // LCD display window with bezel
        translate([case_length/2 - lcd_active_width/2, 
                   case_width/2 - lcd_active_height/2 - 3,
                   -0.1]) {
            // Main viewing window
            cube([lcd_active_width, lcd_active_height, wall_thickness + 0.2]);
            
            // Beveled edge for better viewing angle
            translate([-1, -1, wall_thickness - 0.5])
                cube([lcd_active_width + 2, lcd_active_height + 2, 1]);
        }
        
        // Rotary encoder shaft hole
        translate([case_length/2 + 22, case_width/2 + 19, -0.1])
            cylinder(d=encoder_shaft_dia, h=wall_thickness + 0.2);
        
        // Encoder body clearance on inside
        translate([case_length/2 + 22, case_width/2 + 19, wall_thickness - 0.5])
            cylinder(d=encoder_body_size, h=10);
        
        // Ventilation slots on top (decorative + functional)
        translate([10, 8, -0.1])
            vent_array(3);
        
        translate([case_length - 10 - vent_length, case_width - 8 - vent_width*3 - vent_spacing*2, -0.1])
            vent_array(3);
        
        // Alignment pin holes (matching bottom shell pins)
        translate([case_length/2 - 15, wall_thickness + 1, -0.1]) {
            cylinder(d=3.2, h=2.5);
        }
        translate([case_length/2 + 15, case_width - wall_thickness - 1, -0.1]) {
            cylinder(d=3.2, h=2.5);
        }
    }
    
    // Internal ribs for LCD support
    translate([case_length/2 - pcb_length/2, case_width/2 - pcb_width_lcd/2, 2]) {
        translate([0, 0, 0]) cube([3, 3, 8]);
        translate([pcb_length - 3, 0, 0]) cube([3, 3, 8]);
        translate([0, pcb_width_lcd - 3, 0]) cube([3, 3, 8]);
        translate([pcb_length - 3, pcb_width_lcd - 3, 0]) cube([3, 3, 8]);
    }
}

// ============================================================================
// ASSEMBLY VIEW
// ============================================================================
module assembly() {
    // Bottom shell
    color("ForestGreen", 0.8)
        bottom_shell();
    
    // Top shell (separated for visualization)
    color("DarkOliveGreen", 0.8)
        translate([0, 0, split_height + 10])
            top_shell();
    
    // Visualization of internal components (not for printing)
    color("Navy", 0.3) {
        // Batteries
        translate([case_length/2 - battery_length/2, case_width/2 - battery_diameter, 3]) {
            rotate([0, 90, 0])
                cylinder(d=battery_diameter - 0.5, h=battery_length);
            translate([0, battery_diameter, 0])
                rotate([0, 90, 0])
                    cylinder(d=battery_diameter - 0.5, h=battery_length);
        }
        
        // UPS HAT
        translate([case_length/2 - pcb_length/2, case_width/2 - pcb_width_pi/2, battery_holder_height + 2])
            cube([pcb_length, pcb_width_pi, pcb_thickness]);
        
        // Orange Pi Zero 2W
        translate([case_length/2 - pcb_length/2, case_width/2 - pcb_width_pi/2, battery_holder_height + 7])
            cube([pcb_length, pcb_width_pi, pcb_thickness]);
        
        // LCD HAT
        translate([case_length/2 - pcb_length/2, case_width/2 - pcb_width_lcd/2, battery_holder_height + 17])
            cube([pcb_length, pcb_width_lcd, pcb_thickness]);
    }
}

// ============================================================================
// RENDER SELECTION
// ============================================================================
if (PRINT_PART == "top") {
    rotate([180, 0, 0])  // Flip for printing
        top_shell();
} else if (PRINT_PART == "bottom") {
    bottom_shell();
} else if (PRINT_PART == "assembly") {
    assembly();
}

// ============================================================================
// PRINT INSTRUCTIONS
// ============================================================================
// To export STL files for printing:
// 1. Set PRINT_PART = "bottom" and render (F6), then export STL
// 2. Set PRINT_PART = "top" and render (F6), then export STL
// 3. Print both parts with supports for overhangs
// 4. Install M3 heat-set inserts in bottom shell screw bosses
// 5. Assemble with M3 x 10mm screws
// ============================================================================
