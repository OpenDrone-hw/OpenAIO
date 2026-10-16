# OpenAIO board data for layout review

Facts measured from `hardware/OpenAIO.kicad_pcb` and `hardware/OpenAIO.kicad_dru` (KiCad 10, read only). The model
results in Power paths come from `hardware/tools/power_paths_v2.py`, not from a measurement on a built board.

## Board

| Item | Value |
|---|---|
| Outline | 35.4 x 35.4 mm (the outline is drawn inside the `AIO_outline` footprint U24); 25.5 x 25.5 mm mounting pattern |
| Layers | 8 copper, HDI 1+6+1 |
| Thickness | 0.997 mm (stackup sum with mask) |
| Copper | 35 um (1 oz) on all eight layers |
| Finish | ENIG |
| Footprints | 343, all inside the outline |

Stackup, top to bottom, from the board setup:

| Layer | Item | Thickness mm |
|---|---|---|
| F.Cu | copper | 0.035 |
| | prepreg 1080 | 0.077 |
| In1.Cu (L2) | copper | 0.035 |
| | prepreg 1080 | 0.077 |
| In2.Cu (L3) | copper | 0.035 |
| | core FR4 0.20 incl. 1/1 oz | 0.127 |
| In3.Cu (L4) | copper | 0.035 |
| | prepreg 2116 | 0.125 |
| In4.Cu (L5) | copper | 0.035 |
| | core FR4 0.20 incl. 1/1 oz | 0.127 |
| In5.Cu (L6) | copper | 0.035 |
| | prepreg 1080 | 0.077 |
| In6.Cu (L7) | copper | 0.035 |
| | prepreg 1080 | 0.077 |
| B.Cu | copper | 0.035 |

Fab: NextPCB (the stackup follows the OpenAIO-Whoop plan). Capability notes: [NEXTPCB.md](NEXTPCB.md).

## Layers

Zone nets are the fills present on each layer (phase pours `/1A` to `/4C` exist on every layer except L7). Track
counts are for signals plus rails.

| Layer | KiCad | Name | Fills other than phase pours |
|---|---|---|---|
| L1 | F.Cu | L1.Top | GND, +5V, +1.1V |
| L2 | In1.Cu | L2.GND | GND, /CSA+ |
| L3 | In2.Cu | L3.Signal | GND, +BATT, +5V, /CSA+ |
| L4 | In3.Cu | L4.BATT | +BATT, /CSA+ |
| L5 | In4.Cu | L5.Rails | GND, +3.3V, +4v5, +5V, +10V, /CSA+ |
| L6 | In5.Cu | L6.Signal_5V | GND, +4v5, +BATT, /CSA+ |
| L7 | In6.Cu | L7.GND | GND, /CSA+ |
| L8 | B.Cu | L8.Bottom | GND, +3.3V, +5V, +BATT, /CSA+, U4 switch node |

## Via rules

From `OpenAIO.kicad_dru` and the board setup:

| Via | Layers | Size / drill mm | Rule |
|---|---|---|---|
| Microvia | L1-L2 (F.Cu-In1.Cu), L7-L8 (In6.Cu-B.Cu) only | 0.25 / 0.10 (laser hole 0.10 to 0.125, ring 0.075) | any other micro span is an error |
| Buried | L2-L7 (In1.Cu-In6.Cu) only | 0.33 / 0.15 (mechanical hole 0.15 to 0.25, ring 0.09) | any other buried span is an error |
| Through | L1-L8 | 0.33 / 0.15 default, 0.35 / 0.20 for a few | allowed where F.Cu and B.Cu copper meet it |
| Mechanical blind | none | | `disallow blind_via`, severity warning |
| Stacking | microvia on a same-net buried via | hole-to-hole 0 allowed | microvia on microvia is not allowed |
| Same-net via array | | hole-to-hole 0.20 | |
| Microvia to buried via, different nets | | hole-to-hole 0.25 | |

Netclasses (`OpenAIO.kicad_pro`): Default and Gate 0.09 clearance, Analog / RF / USB 0.12, Power and VBAT 0.10,
Phase and VBAT track width 1.0, Power 0.3, USB 0.13 (USB differential pair 0.13 wide, 0.15 gap). `min_clearance`, `min_track_width` 0.09,
`min_via_diameter` 0.33, `min_through_hole_diameter` 0.15, copper to edge 0.20, hole to hole 0.20.

Via counts on the board: 1345 microvias, 520 buried, 567 through, 4 blind (UART1_TX, UART1_RX,
`/RP2354A/LED_STRIP_L`, MOTOR3: the four `items_not_allowed` DRC warnings).

## Parts placement

| Item | Position |
|---|---|
| FETs Q3 to Q26 (DOY180N03T) | 24: the 12 high-side FETs (drain +BATT) are on F.Cu, the 12 low-side FETs (source GND) on B.Cu |
| Q3 to Q8 (ESC1) | left edge, x 60.2 to 62.2 mm, y 63.2 to 70.4 mm |
| Q9 to Q14 (ESC2) | bottom edge, x 66 to 73.1 mm, y 74.2 to 76.2 mm |
| Q15 to Q20 (ESC3) | top edge, x 77.7 to 84.9 mm, y 45.6 to 47.5 mm |
| Q21 to Q26 (ESC4) | right edge, x 88.7 to 90.6 mm, y 51.4 to 58.6 mm |
| Rsense2 | B.Cu, (60.95, 53.77), next to the battery pad |
| U25 INA186A3 | B.Cu, (64.27, 51.11) |
| U2 RP2354A | F.Cu, (76.39, 64.07) |
| U22 ESP32-C3, U21 SX1281 | B.Cu, (79.85, 71.62) and (88.38, 68.47) |
| AE2 chip antenna | B.Cu, (81.75, 76.30) |
| JP1 u.FL | F.Cu, (90.78, 69.28) |
| U8 BMI270 | F.Cu, (82.44, 61.51), rotated 180 degrees |

Coordinates are KiCad board coordinates. The board centre is (75.4, 60.9) mm, where U24 (`AIO_outline`) sits.

## Power paths, model at 40 A per ESC

`$KPY hardware/tools/power_paths_v2.py hardware/OpenAIO.kicad_pcb --esc 40 --temp 45 --hot 10` (161 A battery,
6-step statistics, every via, pour and plane; DC, no skin effect). Copper at 80 C is x1.125. This is a model of
the routed copper, not a measured or rated current of the board.

| Path | R_eff (mOhm) | Loss 45 C (W) | Loss 80 C (W) | Worst spot |
|---|---|---|---|---|
| /CSA+ battery pad to shunt | 0.176 | 4.6 | 5.1 | L8 (62.8, 51.0) 53 A/mm, 1.2 W |
| Shunt Rsense2 0.2 mOhm (ASR-S-3-0.2F) | 0.200 | 5.2 | 5.2 | rating not established here |
| +BATT shunt to 12 high-side FETs | 0.616 | 16.0 | 18.0 | L4 carries 11.9 W; L4 neck (63.9, 53.7) 147 A/mm at the +5V_USB/CC1 vias |
| GND low-side FETs to battery - | 0.268 | 7.0 | 7.8 | L7 (76.9, 46.6) 30 A/mm |
| 12 phases | 0.10-0.14 per FET | 1.5 | 1.7 | even |
| Copper + shunt | | 34.2 | 37.8 | |
| FET conduction, 2 x DOY180N03T per ESC | 1.0 typ, about 1.4 hot | 12.8 | 18 | |

+BATT R_kk per high-side FET: ESC1 0.39-0.93, ESC2 1.10-1.24, ESC3 1.25-1.45, ESC4 1.28-1.42 mOhm. The current
runs from the battery pad down to the shunt at (61, 54) and back up to the far ESCs, mostly on L4. The shunt
position, not plane count, sets this loss. Peak via current: 8.5 A per 0.15 mm via at the shunt (/CSA+ and +BATT
clusters).

## Check state

`kicad-cli pcb drc --schematic-parity --refill-zones` on 2026-10-16:

| Item | Count |
|---|---|
| Errors | 0 |
| Unconnected | 2 (GND zone fragments) |
| Warnings | 21: items_not_allowed 4, connection_width 3, lib_footprint_mismatch 6, solder_mask_bridge 4, copper_sliver 4 |
| Schematic parity | 19 net_conflict (pads missing in the footprint for pins U2.24, USB1.A8, USB1.B8, U6.2, Card1.1, Card1.8, ESC MCU and driver NC pins, U22.4, U22.20) |

`kicad-cli sch erc`: 31 errors (power_pin_not_driven 9, pin_not_driven 16, bus_to_net_conflict 3,
hier_label_mismatch 1 on the `CURR` sheet pin, pin_not_connected 1 on TP10, pin_to_pin 1: U22 VDD_SPI against U7 OUT).

Open items on the board:

- The solder mask bridges: R12.2 to R72.1 and R11.2 (I2C0 pull-ups), C44.2 to R83.1, USB1 locating peg to R4.2
  (accepted by a DRU rule at 0.08 mm).
- The four blind vias above violate the HDI rule set.
- The power-path model assumes 1 oz on all inner layers; confirm the inner copper weight with the fab.
