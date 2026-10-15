# Routing the one-board OpenAIO

State on 2026-10-15: 8-layer HDI 1+6+1 on the OpenAIO-Whoop plan and stackup (12 layers was tried the same day and
dropped on cost). The Core sits inside the Base outline (owner's placement). Start here before routing.

## Build and price

| Item | Value |
|---|---|
| Stackup | 8L HDI 1+6+1, 1.0 mm (0.997 with mask), 1 oz on all layers, ENIG: 1080 0.077 / 1080 0.077 / core 0.127 / 2116 0.125 / core 0.127 / 1080 0.077 / 1080 0.077 (OpenAIO-Whoop, NextPCB-confirmed, D123) |
| Through via | 0.35/0.20 (power 0.5/0.3) only where F.Cu and B.Cu copper both connect |
| Microvia | 0.25/0.10, L1-L2 and L7-L8, in pad, filled and capped |
| Buried via | 0.33/0.15, L2-L7 (0.74 mm span at NextPCB's 5:1) |
| Price, NextPCB calculator data in Notion (OpenESC-30x30 panel basis, via-in-pad, 1 oz, rank 2 = stacked) | 20 pcs about 394 USD per order; 250 pcs about 2.88 USD per board; 1000 pcs about 1.60 USD per board; one-time 198 USD |
| Stacked microvias | Owner decision 2026-10-15: microvias stack on their same-net buried via (as OpenAIO-Whoop D124). NextPCB prices that as HDI rank 2: vs staggered (rank 1) +146 USD per 20-piece order, +0.86 USD per board at 250, +0.34 at 1000, +3 to 7 days. Microvia on microvia stays forbidden |

## Layers

| Layer | KiCad | Power | Signals |
|---|---|---|---|
| L1 | F.Cu `L1.Top` | high-side FET +BATT pours, phase pours, /CSA+ at the battery pad | FC parts, short escapes |
| L2 | In1 `L2.GND` | GND plane (microvia target), /CSA+ | none |
| L3 | In2 `L3.Signal` | GND fill | Base signals (from the Base's L2) |
| L4 | In3 `L4.BATT` | +BATT pour over the high-side row, +10V, +4v5 | Core LGA-era links, Base gate and BEMF tracks |
| L5 | In4 `L5.Rails` | +3V3, +3.3V, +4v5, +5V_USB, +10V | Core signals A, Base +3V3-area tracks |
| L6 | In5 `L6.Signal_5V` | +5V pour | Core signals B |
| L7 | In6 `L7.GND` | GND plane (microvia target), /CSA+ corridor | none |
| L8 | B.Cu `L8.Bottom` | low-side FET GND pours, phase pours | ESC parts, most Base routing |

The same table is on Cmts.User right of the outline; Route > Set Layer Pair offers Micro L1-L2, Buried L2-L7 and
Micro L7-L8. Today's tracks were packed onto these layers by origin; 6 segments collide (L4).

## Power paths

`$KPY hardware/tools/power_paths.py hardware/OpenAIO.kicad_pcb --esc 15` (15 A per ESC, 61 A battery, 45 C,
copper and vias only; FET RDS(on) not included):

| Path | 8L before the 12L work | 12L (dropped) | 8L now |
|---|---|---|---|
| Battery + pad to shunt Rsense2 (/CSA+) | 0.857 mOhm | 1.085 | **0.431** (corridor on all layers) |
| Shunt (part) | 0.200 | 0.200 | 0.200 |
| +BATT shunt to 12 high-side FETs | 0.107 | 0.147 | **0.090** |
| GND 12 low-side FETs to battery - | 0.266 | 0.305 | **0.234** |
| Phase, motor pad to FETs (each) | 0.048 | 0.052 | **0.048** |
| Loss at 61 A, copper + shunt | 5.4 W | 6.6 W | **3.6 W** |

Full +BATT planes were modelled and are worse (0.28-0.35 mOhm): every buried via perforates every inner plane, so
shaped pours with via arrays in the FET pads carry the current, not plane count.

## DRC at hand-over

| | Errors | Distinct spots | Unconnected |
|---|---|---|---|
| 8L now | about 425-455 (DRC spread) | 212 | 77 |

Pad connectivity of every net is identical to the owner's board. What is left: about 190 via stacks that sit on
another via or a track with no clear spot within 0.5 mm, and 77 unconnected: the Base-Core links (GND 20, +BATT 11,
UARTs, SPI0, I2C0, MOTOR3/4, BUZZER-, CURR, USB_D+), islands of the rail pours on L5 (+3.3V 7, +10V 5, +3V3 2),
and U26/C107/C108 still parked off the board.

## Reroute plan

Power first:

1. **Shunt**: move Rsense2 beside the battery + pad (U24.1). The corridor gives 0.43 mOhm; beside the pad it
   would be about 0.2 (another ~0.9 W at 61 A). Keep the Kelvin taps to U25 as a pair.
2. **+BATT (L4 + L1)**: close the 11 +BATT links; microvia + buried via arrays in every high-side drain pad (Q3,
   Q5, Q7, ...) into the L4 pour.
3. **GND (L2 + L7 + L8)**: close the 20 GND links; via arrays in every low-side source pad.
4. **Rails (L5)**: one region per rail: +3.3V under the FC, +3V3 under the radio and SD, +4v5 and +10V as strips;
   that removes the 14 rail islands. +5V stays on L6.
5. **Phase**: the BEMF taps run 17-24 mm of 0.10 mm switch-node track per phase; place each top divider resistor
   at the phase pour (under 3 mm). Optional: repeat the phase pour on L4 under each half-bridge.
6. **Netclasses**: phase (`/[1-4][ABC]`) and gate (`Net-(Q*-G)`) nets match no class pattern; fix the patterns
   once the phase copper is pours.

Signals:

7. Base signals on L3, Core signals on L5/L6, FC escapes on L1; the 6 colliding segments on L4 first.
8. **LED_STRIP** 114 mm and 12 vias: daisy-chain the corner pads. **USB_D+/-** about 29 mm: route as a pair on L3
   over L2, target under 15 mm. **I2C0, UART1, SD CS** 20-24 mm: one via pair each. **RX SPI** 15-18 mm: U21
   next to U22.
9. **GPIO** (config.h only): keep MOTOR1-4 on GPIO22-25; swap UART0/PIOUART0 or move LED_STRIP to a PIO pin only
   if it shortens a route.
10. **U26 BMP580** with C107/C108 next to R11/R12.

Vias:

11. Microvias stay stacked on their buried via (owner decision, rank 2). Run
    `tools/via_types.py --buried-size 0.33/0.15` and `tools/via_nudge.py` after each session.

## Tools

KiCad closed for every script; each has `--dry-run` or only reads.

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY hardware/tools/via_types.py hardware/OpenAIO.kicad_pcb --buried-size 0.33/0.15
$KPY hardware/tools/via_nudge.py hardware/OpenAIO.kicad_pcb 0.25
$KPY hardware/tools/track_widths.py hardware/OpenAIO.kicad_pcb
$KPY hardware/tools/power_paths.py hardware/OpenAIO.kicad_pcb --esc 15
```

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
