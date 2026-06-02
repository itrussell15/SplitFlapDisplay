// Flap Generator for splitflap design based on: https://github.com/adamgmakes/SplitFlapDisplay
//
// Flap generator created by Richard Garsthagen (the.anykey@gmail.com)
// License under creative commons: https://creativecommons.org/licenses/by-nc-sa/4.0/
//
// MODIFIED FOR CUSTOMIZABLE LAYOUT
// Configure rows, columns, and starting character to fit your build plate

$fn=180; // Quality of render

layers = 3;
layerheight = 0.16;
fontsize = 28;
blackmargin = 3;

// USE [F6] to render the flaps

// ============================================================================
// CUSTOMIZABLE LAYOUT PARAMETERS
// ============================================================================

// Grid dimensions - ADJUST THESE TO FIT YOUR PRINTER
grid_rows = 4;           // Number of rows (e.g., 4, 5, 6, 8)
grid_cols = 6;           // Number of columns (e.g., 4, 5, 6, 8)

// Starting character index (0-63)
// Use this to create multiple plates:
//   Plate 1: start_char = 0   (chars 0-15 for 4x4 grid)
//   Plate 2: start_char = 16  (chars 16-31)
//   Plate 3: start_char = 32  (chars 32-47)
//   Plate 4: start_char = 48  (chars 48-63)
start_char = 0;

// Spacing between flaps (mm) - adjust if flaps are too close/far
x_spacing = 34;          // Horizontal spacing (34mm is safe, 32mm is tight)
y_spacing = 43;          // Vertical spacing (43mm is safe, 40mm is tight)

// ============================================================================
// GENERATION CONTROL
// ============================================================================

// Make the individual color layer
//MakeFlaps(0);

// Show Preview of all the flaps - NOT FOR PRINTING
// PreviewFlaps();

// Generate flaps for export
MakeFlaps(0);



// Fonts to use
fonts = ["Consolas:style=bold", "Apple Symbols", "Arial Unicode MS"];
charFont = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1,1,0,0,1,0,0,0,1,1,1,0,0];

// 64 Characters you want to use (indices 0-63)
// Note: Use actual Unicode characters or \uXXXX escapes (single backslash)
// For quotes: use "'" for single quote, "\"" for double quote
chars = [
"A", "B", "C", "D", "E", "F", "G", "H",  // 0-7
"I", "J", "K", "L", "M", "N", "O", "P",  // 8-15
"Q", "R", "S", "T", "U", "V", "W", "X",  // 16-23
"Y", "Z", "0", "1", "2", "3", "4", "5",  // 24-31
"6", "7", "8", "9", "?", "!", "@", "#",  // 32-39
"$", "&", "[", "]", "-", "+", "=", ":",  // 40-47
"%",
"'",
"\u2709", // Message
"\u2605", // Star
"\u2600", // Sun 
"\u2191", // Down Arrow
"\u2193", // Up Arrow
"\u00B0", // Degree
"\u263A", // Empty Smiley
"\u263B", // Filled Smiley
"♥",
"\u266B", // Music Note
"\u2614", // Umbrella
"\u26A1", // Lightning
" ", // 
" "  // 
];

// Flap Color layer, to generate as individual colors for each flap background
flapColor = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0];

// Color layer, to generate as individual colors
charColorLayer = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1];

// Per Character Font Size overwrite
// Index 37 (@) is reduced by 4 points to fit better
// Index 52-53 (arrows) are increased by 5 points for visibility
charSizeOffset = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,5,0,0,0,0,0,0,0,0,0,0,0];

// Per Character Y Position overwrite -> default is centered (0 = centered)
// Positive values move DOWN, negative values move UP
// Only adjust if character appears visually off-center when printed
charYposOffset = [
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  // 0-15: A-P (all centered)
    -3.5,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  // 16: Q (descender), 17-31: R-Z, 0-5
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  // 32-47: 6-9, ?, !, @, #, $, &, [, ], -, +, =, :
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0   // 48-63: %, ', ", €, ", ↑, ↓, ₿, °, ☺, ., ♥, spaces
    // 48:% 49:' 50:" 51:€ 52:" 53:↑ 54:↓ 55:₿ 56:° 57:☺ 58:. 59:♥ 60-63:spaces
];

// NOTE: If special characters (€, ↑, ↓, ₿, °, ☺) appear off-center,
// adjust their positions above. Indices:
// 51 = € (Euro), 53 = ↑ (Up arrow), 54 = ↓ (Down arrow)
// 55 = ₿ (Bitcoin), 56 = ° (Degree), 57 = ☺ (Smiley)

colors = ["black", "white", "red", "green", "yellow"];

// Calculate total flaps and validate
total_flaps = grid_rows * grid_cols;
end_char = start_char + total_flaps - 1;

module PreviewFlaps(){
    // Preview the current grid configuration
    for ( y = [0 : grid_rows-1] ){
        for ( x = [0 : grid_cols-1] ){
            char_idx = start_char + (y*grid_cols)+x;
            if (char_idx < 64) {
                translate([34+(x*x_spacing), 22+(y*y_spacing), 0])
                flapPreview(char_idx);
            }
        }
    }
    
    // Show build plate outline (for reference)
    plate_width = grid_cols * x_spacing + 20;
    plate_height = grid_rows * y_spacing + 30;
    color("gray", 0.2)
    translate([plate_width/2, plate_height/2 - 10, -1])
    cube([plate_width, plate_height, 1], center=true);
}

module MakeFlaps(part){
    for ( y = [0 : grid_rows-1] ){
        for ( x = [0 : grid_cols-1] ){
            char_idx = start_char + (y*grid_cols)+x;
            
            // Only generate if within valid character range
            if (char_idx < 64) {
                translate([17+(x*x_spacing), 22+(y*y_spacing), 0]) {
                    // Handle wrap-around for first and last characters
                    if (char_idx == 0) {
                        // First character: previous is 63, next is 1
                        flap(63, char_idx, char_idx+1, part);
                    } else if (char_idx == 63) {
                        // Last character: previous is 62, next is 0
                        flap(char_idx-1, char_idx, 0, part);
                    } else {
                        // Normal case: previous, current, next
                        flap(char_idx-1, char_idx, char_idx+1, part);
                    }
                }
            }
        }
    }
}

module flapPreview(c1){
     difference(){ 
         union(){
         color(colors[flapColor[c1]])
         linear_extrude(h=(layers*layerheight))
         import("flap.dxf");
         
         color(colors[flapColor[c1]])
             difference(){
             linear_extrude(h=(layers*layerheight))
             rotate([0,0,180])
             import("flap.dxf");

             translate([0,-21.16+(blackmargin/2),(layerheight*layers)/2])            
             cube([34,blackmargin,layerheight*layers], center=true);
         }

         // black margin
             color(colors[0])
             translate([0,0,layerheight*2])
             difference(){
                linear_extrude(h=(layerheight))
                 rotate([0,0,180])
                 import("flap.dxf");
                 translate([-17,-21.16+blackmargin,0])            
                 cube([34,21.16-blackmargin,layerheight]);
         }
         
         }
         charPreview(c1);
     }
    charPreview(c1); 
}

module flap(c1,c2,c3, part){
    //print flaps with character cutout
    
     difference(){ 
     union(){
     if (flapColor[c3]==part) {
         
         if (flapColor[c3] != 0) {
         color(colors[flapColor[c3]])
         translate([0,0,0])
             difference(){
                 linear_extrude(h=(layerheight))
                 import("flap.dxf");
                 translate([0,21.16-(blackmargin/2),layerheight/2])            
                 cube([34,blackmargin,layerheight], center=true);
                 
             }
         }
         else {
             color(colors[0])
             translate([0,0,0])
             linear_extrude(h=(layerheight))
             import("flap.dxf");
         } 
         
         
     }
     
     if (part==0){  // Always generate middle layer black
      color(colors[0])
      translate([0,0,layerheight])
      linear_extrude(h=(layerheight))
      import("flap.dxf");
     }
     
     if (flapColor[c2]==part) {
         color(colors[flapColor[c2]])
         translate([0,0,layerheight*2])
         linear_extrude(h=(layerheight))
         import("flap.dxf");
     }
     
     if (flapColor[c1]==part) {
         color(colors[flapColor[c1]])
         linear_extrude(h=(layerheight))
         rotate([0,0,180])
         import("flap.dxf");
     }
         
     if (part==0){
      color(colors[0])
      translate([0,0,layerheight])
      linear_extrude(h=(layerheight))
      rotate([0,0,180])
      import("flap.dxf");
      
      
      //top layer bottom margin
      color(colors[0])
             translate([0,0,layerheight*2])
             difference(){
                linear_extrude(h=(layerheight))
                 rotate([0,0,180])
                 import("flap.dxf");
                 translate([-17,-21.16+blackmargin,0])            
                 cube([34,21.16-blackmargin,layerheight]);
         }
      
      //bottom layer bottom margin
      color(colors[0])
             translate([0,0,0])
             difference(){
                linear_extrude(h=(layerheight))
                 import("flap.dxf");
                translate([-17,-21.16+blackmargin,0])            
                 cube([34,21.16-blackmargin,layerheight]);
         }
         
         
      
     }
     
     if (flapColor[c2]==part) {
         if (flapColor[c2] != 0) {
         color(colors[flapColor[c2]])
         translate([0,0,layerheight*2])
             difference(){
                 linear_extrude(h=(layerheight))
                 rotate([0,0,180])
                 import("flap.dxf");
                 translate([0,-21.16+(blackmargin/2),layerheight/2])            
                 cube([34,blackmargin,layerheight], center=true);
                 
             }
         }
         else {
             color(colors[0])
             translate([0,0,layerheight*2])
             linear_extrude(h=(layerheight))
             rotate([0,0,180])
             import("flap.dxf");
         } 
     
         
     }
     }
     char1(c1);
     char2(c2);
     char3(c3);
     }
    

    //print just the characters
    if (charColorLayer[c1] == part) { char1(c1); }
    if (charColorLayer[c2] == part) { char2(c2); }
    if (charColorLayer[c3] == part) { char3(c3); }

}

module charPreview(c){
difference(){
     color(colors[charColorLayer[c]])
     translate([0,charYposOffset[c],layerheight*(layers-1)])
     linear_extrude(h=layerheight)
     text(chars[c], size=fontsize+charSizeOffset[c], font=fonts[charFont[c]], halign="center", valign="center");
     
     translate([-20,-0.25,layerheight*(layers-1)])
     cube([50,0.5,layerheight]);
}
}

module char1(c){
 difference(){
     color(colors[charColorLayer[c]])
     translate([0,-charYposOffset[c],0])
     linear_extrude(h=layerheight)
     rotate([180,0,0])
     text(chars[c], size=fontsize+charSizeOffset[c], font=fonts[charFont[c]], halign="center", valign="center");
     
     translate([-20,-0.25,0])
     cube([50,20,layerheight]);
 }
}

module char2(c){
difference(){
     color(colors[charColorLayer[c]])
     translate([0,charYposOffset[c],layerheight*(layers-1)])
     linear_extrude(h=layerheight)
     text(chars[c], size=fontsize+charSizeOffset[c], font=fonts[charFont[c]], halign="center", valign="center");
     
     translate([-20,-0.25,layerheight*(layers-1)])
     cube([50,0.5,layerheight]);
     
}
}

module char3(c){
 difference(){
     color(colors[charColorLayer[c]])
     translate([0,-charYposOffset[c],0])
     linear_extrude(h=layerheight)
     rotate([180,0,0])
     text(chars[c], size=fontsize+charSizeOffset[c], font=fonts[charFont[c]], halign="center", valign="center");
     
     translate([-20,-20+0.25,0])
     cube([50,20,layerheight]);
 }
}





// ============================================================================
// BUILD PLATE SIZE REFERENCE
// ============================================================================
// 
// Common printer bed sizes and recommended max grid dimensions:
//
// 180x180mm (Prusa Mini, etc):
//   - 4x4 grid (16 flaps): ~136x172mm ✓
//   - 5x4 grid (20 flaps): ~170x172mm ✓
//
// 220x220mm (Ender 3, etc):
//   - 5x5 grid (25 flaps): ~170x215mm ✓
//   - 6x4 grid (24 flaps): ~204x172mm ✓
//   - 6x5 grid (30 flaps): ~204x215mm ✓
//
// 250x250mm:
//   - 6x5 grid (30 flaps): ~204x215mm ✓
//   - 7x5 grid (35 flaps): ~238x215mm ✓
//
// 300x300mm:
//   - 8x6 grid (48 flaps): ~272x258mm ✓
//   - 8x7 grid (56 flaps): ~272x301mm (tight on Y)
//
// Formula for estimating plate size:
//   Width  ≈ (grid_cols × x_spacing) + 20mm margin
//   Height ≈ (grid_rows × y_spacing) + 30mm margin
//
// ============================================================================

// Display current configuration in console
echo(str("Grid: ", grid_rows, " rows × ", grid_cols, " cols"));
echo(str("Total flaps: ", total_flaps));
echo(str("Characters: ", start_char, " to ", min(end_char, 63)));
echo(str("Plate size estimate: ", grid_cols * x_spacing + 20, "mm × ", grid_rows * y_spacing + 30, "mm"));

if (end_char >= 64) {
    echo("WARNING: end_char exceeds 63! Some flaps will not be generated.");
    echo(str("Reduce grid size or start_char. Max start_char for this grid: ", 64 - total_flaps));
}
