<!-- This file fills in as the board gets drawn. It ships mostly empty and that
     is fine. A planned repo does not carry it at all (README is the write-up
     until a design exists); it comes back from the template when someone
     claims the board, with the Repo table filled and the rest landing as the
     design settles. Do not save it all for the end.

     Keep the section order identical in every OpenDrone repo, so a reader and an
     agent find the same thing in the same place anywhere. Delete a section that
     does not apply rather than leaving it empty. Target 150 lines: if a section
     grows past a screen, the detail belongs in the schematic, not here. State
     current fact only. No plans, no TODOs, no history outside Revisions. -->

# OpenAIO

All-in-one board for toothpick-class FPV, 2-6S: 4x AM32 ESC, power, pads and
ExpressLRS 2.4 GHz receiver on 25.5 x 25.5 mm, with the flight controller
(MCU, IMU, baro, OSD, blackbox) on the shared OpenFC-Core module, reflowed onto
this board as a 54 pad LGA (J1). The ESC and RX sheets come from OpenESC-20x20
and OpenRX-Lite, the pads from OpenFC-Lite-Mini, wired on the root sheet.

## Repo

| | |
|---|---|
| Maintainer | @stancoene |
| Status | See the `status-*` topic on the repo. Never written here. |
| Designed in | KiCad 10 |
| KiCad project | `hardware/OpenAIO.kicad_pro` |
| Root schematic | `hardware/OpenAIO.kicad_sch`. Sub-sheets: `fc_power`, `fc_pads` (OpenFC-Lite-Mini), `esc_channel` x4 (OpenESC-20x20), `rx_esp32c3_sx1281` (OpenRX-Lite). The core is the symbol `lib:OpenDrone-Core`, J1, on the root |
| Board | `hardware/OpenAIO.kicad_pcb`, 6 layers, 1.6 mm, 2 oz outer |
| Core module | OpenFC-Core, one symbol and one footprint (`OpenDrone-Core_LGA_land`) copied into `lib` by that repo's `tools/sync_to.py`; never edit them here |
| Local library | `hardware/lib.kicad_sym`, `hardware/lib.pretty/`, `hardware/lib.3dshapes/`, nickname `lib`. Seeded with the OpenFC-Lite-Mini local library so the copied sheets resolve; the lib tables also alias `components`, `4in1ESC` and `OpenRX-Shared` onto the catalogue for the same reason |
| Shared library | [OpenDrone-hw/KiCad-Library](https://github.com/OpenDrone-hw/KiCad-Library), one checkout per machine, nickname `OpenDrone`, resolved through the KiCad path variable `OPENDRONE_LIB` (Preferences > Configure Paths) |
| Design rules | `hardware/OpenAIO.kicad_dru`: canonical block plus 2 oz outer copper (0.16 mm clearance and track) |
| Fab config | `hardware/fabrication-toolkit-options.json` |
| Board setup | 6 layers, 1.6 mm, 2 oz outer, 0.16 mm clearance and track, via 0.35 on 0.20 drill |
| License | CERN-OHL-S-2.0 |

<!-- Mechanical repos: replace the KiCad rows with the CAD tool -->

## Rules

Identical in every OpenDrone board repo. Do not edit here; edit the template.

- **Never text-edit** `.kicad_sch`, `.kicad_pcb` or `.kicad_dru`. Use KiCad, or
  kicad-skip / the pcbnew API for scripted changes. `.kicad_pro` is JSON and may
  be edited directly for metadata.
- **Metadata yes, connections no.** An agent may write BOM and documentation
  fields (MPN, Manufacturer, LCSC, Cost, Datasheet, text variables). An agent
  may not change nets, wiring, routing, placement, footprint assignment, or any
  value that changes the circuit.
- **Close KiCad before any write to a KiCad file.** KiCad caches library tables
  at process start and overwrites files on save.
- **Reuse before you draw.** Check the `OpenDrone` library and its
  `PARTS-USED.md` first. If the part is there we have already sourced,
  footprinted and shipped it: place it from `OpenDrone`. Draw a new part into
  `lib` only when the catalogue has nothing that fits, imported with
  `easyeda2kicad` from its LCSC number. Pulling a newer catalogue is a
  deliberate, reviewed commit: `git submodule update --remote
  hardware/KiCad-Library`, then DRC.
- **One person holds a board layout at a time.** KiCad files do not merge. Say
  on Discord that you are taking it. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **ERC and DRC clean before every pull request.** Commands below.

## Environment

```sh
# schematic and board checks
kicad-cli sch erc --exit-code-violations hardware/OpenAIO.kicad_sch
kicad-cli pcb drc --schematic-parity --refill-zones --exit-code-violations hardware/OpenAIO.kicad_pcb

# netlist, for scripted analysis
kicad-cli sch export netlist --format kicadsexpr -o /tmp/OpenAIO.net hardware/OpenAIO.kicad_sch
```

On macOS `kicad-cli` is at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, and `pcbnew` imports
only under KiCad's bundled Python. Shared scripts (renders, STEP export,
packaging art) live in `OpenDrone-Scripts`.

## Architecture

One board. The flight controller is not designed here: it is the OpenFC-Core
module, placed as J1 (`lib:OpenDrone-Core`, footprint
`OpenDrone-Core_LGA_land`, 54 pads of 1.0 mm on a 2.0 mm grid, 15 x 15 mm)
and reflowed onto the top side like any other part. Everything the core needs
from this board crosses that land: `+4v5` and `+BATT` in, `MOTOR1..4` out to
the four `esc_channel` sheets, `UART0`/`UART1` and `PIOUART0`/`PIOUART1` to
the RX sheet and the pads, `CURR` from the current sense amplifier,
`10V_ENABLE` to the power sheet, `BUZZER-`, `LED_STRIP`, `VIDEO_IN`/`OUT`,
USB `D+`/`D-` to the Type-C. Pad names are the core's net names; the pin map
and the layout rules of the module are in the OpenFC-Core repo. The core's
symbol and footprint are copied here by `OpenFC-Core/hardware/tools/sync_to.py`
and are not edited in this repo.

## Voltage envelope

2S-6S, 6.0 to 25.2 V. The ceiling is the MOSFET: DOY180N03T is 30 V VDSS, the
same part and the same NSG2065Q topology OpenESC-20x20 flies at 6S. The 40 V
SP40N01GHNK that takes OpenESC-30x30 to 8S is PDFN-8L 5x6 and four channels of
it do not fit on 25.5 mm, so 6S is the ceiling here, not 8S.

At the bottom of the range the +10V gate rail is not regulated: the buck runs
in pass-through and the drivers see roughly +BATT, which at 2S is about 5.9 V,
above the NSG2065Q 4.5 V UVLO and inside its 5-20 V supply range. The board
runs, but gate drive is about half, so continuous current at 2S is not the 6S
figure. Measure both before either goes in the README table.

## Key parts

| Function | Ref | Part | LCSC | Note |
|---|---|---|---|---|
| <MCU> | U1 | | | |
| | | | | |

## Power

```
<ASCII tree: source, each regulator with its part and output, and what each
rail feeds. One block, no prose.>
```

## Connectors and I/O

| Connector | Ref | Part | Function |
|---|---|---|---|
| | | | |

<Pinout table or pin map, only where the pinout is not visible from the
schematic sheet name.>

## Firmware

<Which firmware, which target, how it gets on the board the first time. Link
upstream. Do not restate upstream documentation.>

## Layout rules

- Nothing may stand under J1 on the top side: the core's bottom is flat
  copper on the land. Bottom side parts under it are fine.
- J1 keeps every pad, unused ones stay open; delete pads per instance only for
  routing room. Ground pads tie into the plane.
- Move the core only by moving J1; never edit the footprint here.

## Revisions

| Rev | Date | Change |
|---|---|---|
| <rev1> | <YYYY-MM-DD> | First release. |
