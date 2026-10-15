# Routing the one-board OpenAIO

State on 2026-10-15, after the owner moved the Core into the Base outline and the board went to 12 layers.
Start here before routing.

## Board

| Item | Value |
|---|---|
| File | `hardware/OpenAIO.kicad_pcb`, one project with `OpenAIO.kicad_sch` |
| Stackup | 12 layers, HDI 1+10+1, about 1.25 mm: 1 oz outer, 0.5 oz inner; 1080 prepreg L1-L2 and L11-L12, H/H 0.135 cores and 1080 alternating inside (inferred from NextPCB's published materials; NextPCB publishes no 12L HDI table, so confirm the build in the quote) |
| Vias | Through 0.35/0.20 where F.Cu and B.Cu copper meet; elsewhere laser microvia 0.25/0.10 (F.Cu-In1.Cu, In10.Cu-B.Cu) stacked on a buried via In1.Cu-In10.Cu, 0.38/0.20 (the 1.0 mm L2-L11 span at NextPCB's 5:1 limit) |
| Core | Moved in by the owner at (-34.326, +8.545) from its side-by-side position |
| Rule area | `Core layout` keeps the Core's 0.09 line standard |

## Layer plan

| Layer | KiCad | Use |
|---|---|---|
| L1 | F.Cu | parts (Core FC on top) |
| L2 | In1.Cu | GND plane (microvia target), Base phase and CSA copper |
| L3 | In2.Cu | Core signals, +3.3V / +10V (was Core In3) |
| L4 | In3.Cu | Core signals (was Core In2) |
| L5 | In4.Cu | Core LGA-era links, +4v5 (was Core B.Cu) |
| L6 | In5.Cu | GND plane, new: separates the Core from the Base |
| L7 | In6.Cu | Base signals, GND, +BATT (was Base In2) |
| L8 | In7.Cu | Base signals, +3V3, +3.3V, +4v5, +5V_USB (was Base In3) |
| L9 | In8.Cu | Base signals, +5V plane (was Base In4) |
| L10 | In9.Cu | Base signals, +BATT and +10V planes (was Base In5) |
| L11 | In10.Cu | GND plane (microvia target) |
| L12 | B.Cu | parts (ESC side), Base signals |

Core and Base tracks no longer share an inner layer. Every buried via still spans L2-L11, so where a Core via and
a Base via land on each other they collide on every inner layer; those are positional and need a via move.

## DRC at hand-over

`kicad-cli pcb drc --refill-zones hardware/OpenAIO.kicad_pcb` (counts at 199 are a report cap):

| Step | Errors | Distinct spots | Unconnected |
|---|---|---|---|
| Owner's 8L board (Core moved in) | 818 | | 80 |
| 12L, layers remapped, vias typed | 1027 | 339 | 64 |
| Vias nudged (`tools/via_nudge.py`, up to 0.5 mm, 92 moved) | 671 | 274 | 63 |
| Widths standardised (`tools/track_widths.py`) | 632 | 243 | 63 |

Pad connectivity of every net is identical to the owner's board after every step. What is left: about 180 via
stacks with no clear spot within 0.5 mm (via on via, via in a track), and the 63 links (GND 20, +BATT 11, +3.3V 6,
+3V3 5, UARTs, SPI0 + FLASH_CS, I2C0, MOTOR3/4, BUZZER-, CURR, USB_D+, the U21 DC-DC feedback).

## Tools

KiCad closed for every script; each prints a report and has `--dry-run`.

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY hardware/tools/via_types.py hardware/OpenAIO.kicad_pcb --buried-drill 0.20   # via type from the layers it joins
$KPY hardware/tools/via_nudge.py hardware/OpenAIO.kicad_pcb 0.25                  # move conflicting vias up to 0.25 mm
$KPY hardware/tools/track_widths.py hardware/OpenAIO.kicad_pcb                    # standard widths where they fit
```

`hdi_via_pass.py` still assumes 8 layers; use `via_types.py`.

## Reroute plan for 12 layers

High current (resistance):

1. **+BATT**: today it is a 382 mm2 plane on L10 and 148 mm2 on L7, now 0.5 oz. Give it two full planes, L9 and
   L10 (move the +5V plane to L8 with +3V3), stitched with through-via arrays at the battery pads (U24.1 via the
   shunt) and at every high-side FET drain. Close the 11 +BATT links first.
2. **Phase nodes**: the current runs in the F.Cu/B.Cu pours; L2 and L7-L9 carry only 2-5 mm2 per phase. Repeat
   the full phase shape on L3-L4 under each half-bridge with via arrays (L3-L4 are Core layers only under the
   Core, free under the ESCs). Each phase net also carries
   17-24 mm of 0.10 mm track to its BEMF divider (R47/R50/... top resistors), bootstrap cap (C40-C63) and driver
   VS pin: move the top divider resistor next to the phase pour so the switch-node track is under 3 mm.
3. **GND return**: L2, L6 and L11 are planes; tie them with via arrays along each half-bridge and at the shunt
   ground (Kelvin taps stay single tracks).
4. **Netclasses**: the Base patterns `/ESC?/Motor?` and `/ESC?/GH?` match no net; phase nets (`/[1-4][ABC]`) and
   gates (`Net-(Q*-G)`) sit in Default. Fix the patterns once the phase copper is planes (Phase clearance 0.12).
5. **+10V / +4v5 / +5V**: the 88 power tracks that had no room for 0.30 mm; route them as pours on their plane
   layer instead of tracks.

Signal length:

6. **LED_STRIP**: 114 mm, 12 vias to four corner pads; one pad pair is enough electrically, or a daisy chain
   corner to corner on L12.
7. **USB_D+/-**: 28-30 mm with 6-8 vias; with the Core over the Base, route the pair on L3 straight from USB1 to U2
   (target under 15 mm, two vias each, 90 ohm on L3 over L2).
8. **I2C0, UART1, FLASH_CS** (20-24 mm, 5-9 vias): the RP2354 sits at the board centre; the SD socket (Card1) and
   the ESP32-C3 (U22) are at opposite edges. Route them on L3/L4 with one via pair each.
9. **RX SPI** (U21 to U22, 15-18 mm): place U21 SX1281 next to U22 or route the four lines as a group on L4.
10. **GPIO remap** (firmware config.h only, no new parts): MOTOR1-4 are GPIO22-25 on U2 pins 34-37 (one side);
    keep them. Swap UART0 and PIOUART0 pins if the SH-6 (U12) lands closer to pins 2-3 than 4-5 after the Core
    move; put LED_STRIP on a PIO pin on the side facing the strip pads. Check the Betaflight target
    (`research/review-2026-10/firmware/`) after any swap.
11. **Via stacks**: 180 stacks still sit on other vias. With the layers now separated, most can become a single
    microvia + short L3/L4 jog instead of a full buried via; run `via_nudge.py` again after each routing session.

## Known circuit issues kept on purpose

The owner chose the 2026-08-22 circuit plus the always-on `+10V` only (2026-10-15). These
were fixed on the two-board branch and are open here:

| Issue | Effect | Fix on the two-board branch |
|---|---|---|
| LED strip driven through Q2/R14, which inverts | WS2812 data is inverted; the strip does not work with stock Betaflight | `cdb8534`: TXU0101 non-inverting buffer |
| ESC MCUs on `+3V3` | On USB alone the AT32s run with no gate drive | `05537a3`: TLV75533 `+3V3_ESC` from `+5V` |
| No SWD test pads for the RP2354A (`SWDIO`/`SWCLK` unconnected) | USB BOOTSEL only | TP31/TP32 |

Firmware status of each: `research/review-2026-10/firmware/ISSUES.md`. The reviews in
`research/review-2026-10/` were done on 8fa8d7b; their part references and some findings do
not match this board.

## Owner decisions from the 2026-10-15 schematic review

Found on the 8fa8d7b circuit; each applies to this board too. Not changed. Full findings:
`research/review-2026-10/schematic-review-2026-10-15.json`.

| Item | Risk | Options |
|---|---|---|
| DOY180N03T is 30 V on a 25.2 V bus (26.1 V LiHV) | Turn-off overshoot at 6S | 40 V FET in the same 3.3 x 3.3 footprint, RC snubber pads (DNP), or limit to 5S |
| Bulk capacitance is the external electrolytic at the battery lead | Hot-plug ringing without it | The README requires it; no TVS on `+BATT` |
| 0201 BEMF top resistors (12) and R1 VBAT divider at 23 V | 0201 working voltage is about 25 V | 0402 10k / 100k, or two 0201 in series |
| Low-side gate 15R, no fast turn-off | Miller turn-on at 6S | 4.7R on the low side, or a diode across it; scope first boards |
| Video pass-through has no clamp | AC-coupled cameras lose sync | Test cameras; add coupling cap + Schottky clamp if needed |
| No USB ESD | User-facing connector | Low-capacitance 2-line array at USB1 |
| U23 TLV75533 (500 mA, X2SON) for the radio rail | Margin | TLV76733 1 A, WSON 2x2 |
| Crystal CL unknown with 20 pF caps | Clock accuracy | Confirm CL; 15 pF if CL = 10 pF |
| Blackbox is microSD, not NOR | Board area, a socket on a 35 mm board | Keep, or replace with a 16 MB NOR as on OpenAIO-Whoop (new circuit) |
