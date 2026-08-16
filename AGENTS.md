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

All-in-one board for toothpick-class 6S FPV: RP2354A flight controller, 4x AM32
ESC and ExpressLRS 2.4 GHz receiver on 25.5 x 25.5 mm. The design starts from
the manufactured sub-sheets of OpenFC-Lite-Mini, OpenESC-20x20 and OpenRX-Lite,
copied into `hardware/` and wired on the root sheet. It is a two-PCB stack:
the **Base** (ESCs, power, pads, RX) and the **Core** (RP2354A, IMU, OSD,
blackbox), soldered onto the Base as an interior LGA. One schematic, two board
projects; see Architecture.

## Repo

| | |
|---|---|
| Maintainer | @stancoene |
| Status | See the `status-*` topic on the repo. Never written here. |
| Designed in | KiCad 10 |
| Schematic project | `hardware/OpenAIO.kicad_pro`: open this one to edit the schematic. It has no board |
| Root schematic | `hardware/OpenAIO.kicad_sch`. Sub-sheets: `fc_power`, `fc_rp2350a`, `fc_imu`, `fc_osd`, `fc_blackbox`, `fc_pads` (OpenFC-Lite-Mini), `esc_channel` x4 (OpenESC-20x20), `rx_esp32c3_sx1281` (OpenRX-Lite), `core_interface` (the Base<->Core LGA, generated) |
| Boards | `hardware/OpenAIO-Base.kicad_pro` + `.kicad_pcb` (carrier) and `hardware/OpenAIO-Core.kicad_pro` + `.kicad_pcb` (hat), two full KiCad projects in the same directory. Their root schematics `OpenAIO-Base.kicad_sch` and `OpenAIO-Core.kicad_sch` are symlinks to `OpenAIO.kicad_sch`, so both boards see the one schematic. Which footprint lives on which board is decided by the board it was placed on: `.kicad_multiboard.json` + the multiboard plugin, see Environment |
| Local library | `hardware/lib.kicad_sym`, `hardware/lib.pretty/`, `hardware/lib.3dshapes/`, nickname `lib`. Seeded with the OpenFC-Lite-Mini local library so the copied FC sheets resolve; the lib tables also alias `components`, `4in1ESC` and `OpenRX-Shared` onto the catalogue for the same reason |
| Shared library | [OpenDrone-hw/KiCad-Library](https://github.com/OpenDrone-hw/KiCad-Library), one checkout per machine, nickname `OpenDrone`, resolved through the KiCad path variable `OPENDRONE_LIB` (Preferences > Configure Paths) |
| Design rules | `hardware/OpenAIO-Base.kicad_dru`: canonical block plus 2 oz outer copper (0.16 mm clearance and track). `hardware/OpenAIO-Core.kicad_dru`: canonical block, 1 oz line standard 0.09, plus "nothing but J91 on B.Cu". `OpenAIO.kicad_dru` is the schematic project's copy of the canonical block |
| Fab config | `hardware/fabrication-toolkit-options.json` |
| Board setup | Standard: 6 layers, 0.09 mm clearance and track, via 0.35 on 0.20 drill. Base 1.6 mm, 2 oz outer; Core 0.8 mm (JLCPCB 6-layer minimum), 1 oz |
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
# schematic and board checks (no --schematic-parity: each board holds a subset of the schematic)
kicad-cli sch erc --exit-code-violations hardware/OpenAIO.kicad_sch
kicad-cli pcb drc --refill-zones --exit-code-violations hardware/OpenAIO-Base.kicad_pcb
kicad-cli pcb drc --refill-zones --exit-code-violations hardware/OpenAIO-Core.kicad_pcb

# netlist, for scripted analysis
kicad-cli sch export netlist --format kicadsexpr -o /tmp/OpenAIO.net hardware/OpenAIO.kicad_sch

# schematic -> boards (KiCad's Update PCB from Schematic would import the whole
# schematic into each board; the multiboard plugin only brings each board its own
# footprints). GUI: PCB editor > Tools > External Plugins > Multi-Board Manager,
# select the board that should receive new parts, Update. Headless, boards closed:
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY ~/OpenDrone/software/OpenDrone-Scripts/kicad/multiboard/update.py hardware              # refresh both, new parts to the Base
$KPY ~/OpenDrone/software/OpenDrone-Scripts/kicad/multiboard/update.py hardware OpenAIO-Core # new parts to the Core

# Core 3D model for J90 on the Base (after changing the Core layout; KiCad may stay open)
cd hardware && python3 tools/core_model.py
```

Plugin, once per machine: `sh ~/OpenDrone/software/OpenDrone-Scripts/kicad/multiboard/install.sh`
(OpenDrone fork of [Kicad-Multi-PCB](https://github.com/Eliot-Abramo/Kicad-Multi-PCB),
KiCad 10, its README says what was changed). On macOS `kicad-cli` is at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, and `pcbnew` imports
only under KiCad's bundled Python. Shared scripts (renders, STEP export,
packaging art) live in `OpenDrone-Scripts`; board-specific scripts live in
`hardware/tools/` (`lga_gen.py`, `core_model.py`).

## Architecture

Two PCBs, one schematic. KiCad has one board per project, so there are three
projects in `hardware/`: `OpenAIO` (schematic only), `OpenAIO-Base` and
`OpenAIO-Core` (one board each, root schematic symlinked to `OpenAIO.kicad_sch`).
The plugin's ownership rule decides the split: a footprint belongs to the board
it was placed on first, and an Update of a board only refreshes its own
footprints and adds symbols that are on no board yet. To move a part, delete it
from one board and Update the other. Nets are board-wide names, so a net that
crosses the LGA is complete on each board through J90 or J91. Edit the schematic
from the `OpenAIO` project only: opening it through a board project works for
reading and cross-probing but saving from there writes extra project instance
data into the shared sheets.

The Base<->Core interface is one pin table in `tools/lga_gen.py`, which emits
everything that must agree: `lib:Core_LGA_land` (F.Cu land pattern on the
Base, J90), `lib:Core_LGA_pads` (B.Cu pads on the Core, J91, X pre-mirrored so
the flipped footprint overlays the land pad for pad), the `lib:Core_LGA`
symbol and the `core_interface` sheet. 2 x 16 pads, 1.0 mm pitch, 12 mm row
gap, 0.6 mm round pads: 8 GND, `+BATT`, `+5V` x2, `+10V` x2, `+3.3V` x2,
`+4v5`, and 16 signals (`MOTOR1..4`, `UART0_TX/RX`, `UART1_TX/RX` to the RX,
`SPI0` + `FLASH_CS` to the SD card, `USB_D+/-`, `10V_ENABLE`, `CURR`). Every
interface net is a global label; `python3 tools/lga_gen.py` prints the table.
`tools/core_model.py` exports the Core as `export/OpenAIO-Core.wrl` (+ `.step`,
origin at J91) and that file is J90's 3D model, so the Base's 3D view shows the
Core stacked at its true position for collision checks; the Core outline also
sits on J90's User.Comments layer while routing the Base. `export/` is
gitignored: run the script once after cloning.

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

- J90 (Base, F.Cu) and J91 (Core, B.Cu, flipped) are a mirror pair from one
  generator; change pads in `tools/lga_gen.py`, regenerate, then Update
  Footprints from Library on both boards. J91's position is the Core's model
  origin: `core_model.py` after moving it.
- Only the Core's top face carries parts; its bottom is the LGA (DRU rule on
  the Core). Nothing on the Base may stand under the Core outline (J90
  User.Comments); check the Base 3D view.
- The Core is 0.8 mm thick, the JLCPCB 6-layer minimum, 1 oz outer; the Base
  is 1.6 mm, 2 oz outer. Both are board settings of their own project now.

## Revisions

| Rev | Date | Change |
|---|---|---|
| <rev1> | <YYYY-MM-DD> | First release. |
