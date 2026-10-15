# Routing the one-board OpenAIO

State on 2026-10-15. Start here before routing.

The board is the owner's hand-routed layout of 2026-08-22: the Base recovered from KiCad local
history (d81e559) and the Core routed by hand (1fe3d21), with only the always-on `+10V` of
9aba717 on top. Both sit side by side in one file on the OpenAIO-Whoop stackup. The later
two-board work (8fa8d7b: Core re-routed for a 46-pad LGA, DFM and circuit changes) is not in
this board.

## What the board file holds

| Item | Value |
|---|---|
| File | `hardware/OpenAIO.kicad_pcb`, one project with `OpenAIO.kicad_sch` |
| Base layout | Left, outline 57.7-93.1 x 43.2-78.6 mm (in footprint U24 `AIO_outline`), all routing kept: 1353 mm of track, 1800 tracks, 1332 vias |
| Core layout | Right, outline 103.05-126.15 x 43.45-63.65 mm, all routing kept: 582 mm, 713 tracks, 245 vias |
| New parts | Parked under the Core at y 68.5 (Cmts.User note): U26 BMP580 barometer, C107 (VDD) and C108 (VDDIO) 100 nF |
| Stackup | 8L HDI 1+6+1, 0.997 mm, 1 oz all layers, ENIG (OpenAIO-Whoop) |
| Vias | All vias are through vias (edit form). DRC reports them as `items_not_allowed` warnings |
| LGA | J90 and J91 deleted. Their nets are now direct links between the two layouts |
| Rule area | `Core layout` over the Core: inside it the 0.09 line standard applies, as the Core was routed (Default class only). Move it with the Core |
| Netclasses | The Base's: VBAT, Phase, Gate, Power, Analog, RF, USB, Default (`OpenAIO.kicad_pro`) |

## DRC at hand-over

`kicad-cli pcb drc --schematic-parity --refill-zones hardware/OpenAIO.kicad_pcb`

| Type | Count | What it is |
|---|---|---|
| errors | 3 | USB1 locating peg: 2 annular width, 1 clearance to R4.2 (0.08 of 0.09) at (63.1, 58.4). The same peg errors the Base had; check the peg against the 0.997 mm board |
| unconnected | 37 | The former LGA links (`GND` 7, `+3.3V` 7, `+4v5`, `+5V`, `+10V`, `+BATT`, `MOTOR1-4`, `UART0_TX/RX`, `UART1_TX/RX`, `SPI0.SCK/MOSI/MISO`, `FLASH_CS`, `USB_D+/-`, `CURR`, `BUZZER-`, `LED_STRIP`) and the new baro on I2C0 |
| parity | 17 | "No pad for pin" on pins left unconnected on purpose. No net or value mismatch |

Warnings worth knowing: `items_not_allowed` 199 (through vias), `solder_mask_bridge` 36,
`track_dangling` 20 (escape stubs to the deleted J90/J91: start of each link, or delete),
`lib_footprint_mismatch` 4 (instances that differ from each other). Courtyards, silk and
dangling vias are at the Base's own severities (ignore).

## Putting the Core into the Base

The Core sat over the J90 land. Moving every Core item by **(-34.232, +8.374) mm** puts it
exactly where the hat was: all 34 J90/J91 pad pairs give this offset. Delete the Core's
Edge.Cuts after the move; the Base outline is the board.

A dry run of that move (Core items moved, nothing deleted, DRC) gives 1057 errors:

| Where | clearance | shorts | hole clearance | hole to hole | crossing |
|---|---|---|---|---|---|
| Through vias (F.Cu-B.Cu) | 250 | 101 | 54 | 130 | |
| F.Cu | 61 | 28 | 46 | | 2 |
| B.Cu | 88 | 53 | 47 | | 2 |
| In2.Cu | 63 | 12 | 40 | | 24 |
| In3.Cu to In5.Cu | 37 | 5 | 12 | | |

Half of it is through vias from both layouts landing on each other; the rest is Base copper
under the old land against the Core's copper on the same layers.
In this order:

1. On the Base, delete the J90 escape copper inside the land field (the `track_dangling`
   stubs and the vias that only served J90 pads).
2. Move the Core and the `Core layout` rule area (select all, Move Exactly).
3. Run `hdi_via_pass.py` (fab form). Microvias only use L1-L2 and L7-L8, so most via
   conflicts on the inner layers turn into buried-via conflicts on In1-In6, far fewer.
4. Re-route what still collides: the Core's B.Cu, In2 and In3 against the Base's B.Cu, In2
   and phase copper, then the links.
5. Place U26/C107/C108 next to the I2C0 pull-ups R11/R12.

## Vias: edit form and fab form

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY hardware/tools/hdi_via_pass.py hardware/OpenAIO.kicad_pcb --dry-run   # report
$KPY hardware/tools/hdi_via_pass.py hardware/OpenAIO.kicad_pcb             # fab form: microvia/buried stacks
$KPY hardware/tools/hdi_via_pass.py hardware/OpenAIO.kicad_pcb --collapse  # edit form: one via per stack
```

KiCad closed for every script. DRC is only meaningful in the fab form.

## Layer use as routed

| Layer | Base | Core |
|---|---|---|
| F.Cu | parts, `+5V`/`+BATT`/phase pours | parts, GND pour |
| In1 | phase copper per power stage | GND |
| In2 | `+BATT`, phase copper, most signals | GND, signals |
| In3 | `+3.3V`, `+3V3`, `+4v5`, `+5V_USB`, phase copper | `+3.3V`, `+10V`, GND, signals |
| In4 | `+3V3`, `+5V`, phase copper | GND |
| In5 | `+BATT`, `+10V` | none |
| In6 | GND | none |
| B.Cu | parts, most Base signal routing, power pours | `+4v5`, GND, J91 escapes (J91 deleted) |

The Whoop plan (L2/L7 solid GND, power on L4/L5) is the target if the layers are re-planned.

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
