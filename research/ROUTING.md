# Routing the one-board OpenAIO

State on 2026-10-15 (merged to main from `feat/one-board`, PR #25). Start here before routing.

## What the board file holds

| Item | Value |
|---|---|
| File | `hardware/OpenAIO.kicad_pcb`, one project with `OpenAIO.kicad_sch` |
| Base layout | Left, outline 57.7-93.1 x 43.2-78.6 mm, all routing of 8fa8d7b kept (1630 mm of track, 1348 vias) |
| Core layout | Right, outline 103.05-126.15 x 43.45-63.65 mm, all routing kept (490 mm, 218 vias) |
| New parts | Parked in a row under the Core at y 68.5 (Cmts.User note): U28 DPS368 + C114/C115 (I2C0 baro), C117/C118 (RP2354 pins 44/53/54), C116 (U3 VIN 100 nF), D10 (buzzer flyback) |
| Stackup | 8L HDI 1+6+1, 0.997 mm, 1 oz all layers (OpenAIO-Whoop) |
| Vias | All vias are still through vias (edit form). DRC reports them as `items_not_allowed` warnings |
| LGA | J90 and J91 deleted. Their 46 nets are now direct links between the two layouts |

## DRC at hand-over

`kicad-cli pcb drc --schematic-parity --refill-zones hardware/OpenAIO.kicad_pcb`

| Type | Count | What it is |
|---|---|---|
| unconnected | 51 | The former LGA links: `+3.3V` 10, `GND` 9, `+4v5` 3, `+5V` 3, `+BATT` 2, `+10V`, `MOTOR1-4`, `UART0/1`, `PU0RX`, `SPI0` + `SD_CS`, `USB_D+/-`, `SWDIO/SWCLK`, `CURR`, `LED_STRIP`, `BUZZER-`, plus the new parts |
| via_dangling | 25 | The Core's escape vias that went down to J91 (`MOTOR1-4`, `UART0/1`, `PU0RX`, `SPI0`, `SD_CS`, `USB_D+/-`, `SWD`, `CURR`, `+4v5`, `+5V`, `+BATT`, `BUZZER-`, `LED_STRIP`) plus Base vias that went up to J90. Use them as the start of each link or delete them |
| track_width | 7 | Core leftovers: `+BATT` 0.10 on In2 at (105.7-106.9, 59.9-60.3) (VBAT sense feed, no room to widen), `USB_D-` 0.10 at (110.1-110.3, 58.6-61.0), `/IMU/SPI1.MOSI` 0.083 at (115.25, 51.94) |
| clearance | 3 | X1.3 to the SPI0.MOSI via 0.085 at (110.47, 50.38); J48.1 to a GND via 0.086 at (120.62, 60.41); C36 (now `+3.3V`) to C79 (`+3V3`) 0.10 of 0.15 at (75.6, 73.5) on B.Cu |
| USB diff pair | 3 | The USB route ends where J90 was; reroute the pair to the RP2354 |
| parity | 114 | 77 "no pad for pin" (unused pads removed on purpose in the two-board layout) and 37 footprint-filter notes. No net or value mismatch |

Warnings worth knowing: `items_not_allowed` 199 (through vias), `lib_footprint_mismatch` 199
(instances differ from the library: removed pads, kept on purpose; never "Update footprints
from library" on U13-U20), `courtyards_overlap` 72 (0.2 mm body rule, as before).

## Putting the Core into the Base

The Core sat over the J90 land. Moving every Core item by **(-34.232, +8.374) mm** puts it
exactly where the hat was (Core outline onto 68.82-91.92 x 51.82-72.02). Delete the Core's
Edge.Cuts after the move; the Base outline is the board.

A dry run of that move (Core items moved, nothing deleted, DRC) gives:

| Layer | clearance | shorts | hole clearance | hole to hole |
|---|---|---|---|---|
| F.Cu | 703 | 240 | 304 | 276 |
| B.Cu | 136 | 111 | 34 | |
| In2.Cu | 119 | 45 | 47 | |
| In3.Cu to In5.Cu | 40 | 2 | 13 | |

Plus 77 courtyard overlaps. Almost all of it is through vias, from both layouts, and the
Base's F.Cu escape copper under the old land. In this order:

1. On the Base, delete the J90 escape copper inside the land field (F.Cu stubs and the vias
   that only served J90 pads; DRC lists them as `track_dangling` / `via_dangling`).
2. Move the Core (select all its items, Move Exactly). The courtyard check shows which Base
   F.Cu parts still sit under it.
3. Run `hdi_via_pass.py` (fab form). Microvias only use L1-L2 and L7-L8, so most via
   conflicts on the inner layers turn into buried-via conflicts on In1-In6, far fewer.
4. Re-route the Core's In2/In3 signals around the Base's In2 routing and the phase copper on
   In1-In4, then the 46 links.
5. Place the new parts: U28/C114/C115 near the I2C0 pull-ups R11/R12; C117/C118 at U2 pins
   44, 53, 54; C116 at U3 pins 3/5 (TI 9.2.2.6); D10 at J29/J33.

## Vias: edit form and fab form

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY hardware/tools/hdi_via_pass.py hardware/OpenAIO.kicad_pcb --dry-run   # report
$KPY hardware/tools/hdi_via_pass.py hardware/OpenAIO.kicad_pcb             # fab form: microvia/buried stacks
$KPY hardware/tools/hdi_via_pass.py hardware/OpenAIO.kicad_pcb --collapse  # edit form: one via per stack
```

KiCad closed for every script. Net class sizes: microvia 0.25/0.10, via 0.33/0.15. DRC is only
meaningful in the fab form.

## Layer plan

Today the layers are used as the two layouts were routed, not as on the Whoop:

| Layer | Base | Core |
|---|---|---|
| F.Cu | parts, power pours | parts |
| In1-In4 | phase-node copper per power stage, In2 most signals | In1 GND, In2/In3 signals and `+3.3V`, In4 GND |
| In5 | `+BATT`, `+10V` | none |
| In6 | GND | none |
| B.Cu | parts, `+BATT` pours | J91 only (deleted) |

The Whoop plan (L2/L7 solid GND, no tracks; power on L4/L5; sensitive signals on L3 between GND
and a quiet plane, noisy on L6) is the target when the layers are re-planned. The Whoop
layer-use DRC rules are not in this board's `.kicad_dru` yet because they would flag the
kept routing everywhere.

## Owner decisions from the 2026-10-15 schematic review

Not changed in the schematic; each needs your call. Full findings:
`research/review-2026-10/schematic-review-2026-10-15.json`.

| Item | Risk | Options |
|---|---|---|
| DOY180N03T is 30 V on a 25.2 V bus (26.1 V LiHV) | Turn-off overshoot at 6S | 40 V FET in the same 3.3 x 3.3 footprint, RC snubber pads (DNP), or limit to 5S |
| No bulk capacitor or TVS on `+BATT` | Hot-plug ringing above 38 V (buck) and 42 V (INA186) | README now requires the external capacitor; optional pads for it at U24 |
| 0201 BEMF top resistors (12) and R1 VBAT divider at 23 V | 0201 working voltage is about 25 V | 0402 10k / 100k, or two 0201 in series |
| Low-side gate 15R, no fast turn-off | Miller turn-on at 6S | 4.7R on the low side, or a diode across it; scope first boards |
| Video pass-through has no clamp | AC-coupled cameras lose sync | Test cameras; add coupling cap + Schottky clamp if needed |
| No USB ESD | User-facing connector | Low-capacitance 2-line array at USB1 |
| U23 TLV75533 (500 mA, X2SON) for the radio rail | Margin | TLV76733 1 A, WSON 2x2 |
| Crystal CL unknown with 20 pF caps | Clock accuracy | Confirm CL; 15 pF if CL = 10 pF |
| Blackbox is microSD, not NOR | Board area, a socket on a 35 mm board | Keep, or replace with a 16 MB NOR as on OpenAIO-Whoop (new circuit) |
