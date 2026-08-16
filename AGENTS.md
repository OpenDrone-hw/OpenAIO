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
blackbox), soldered onto the Base as an interior LGA. Both live in one project
and one master PCB; see Architecture.

## Repo

| | |
|---|---|
| Maintainer | @stancoene |
| Status | See the `status-*` topic on the repo. Never written here. |
| Designed in | KiCad 10 |
| KiCad project | `hardware/OpenAIO.kicad_pro` |
| Root schematic | `hardware/OpenAIO.kicad_sch`. Sub-sheets: `fc_power`, `fc_rp2350a`, `fc_imu`, `fc_osd`, `fc_blackbox`, `fc_pads` (OpenFC-Lite-Mini), `esc_channel` x4 (OpenESC-20x20), `rx_esp32c3_sx1281` (OpenRX-Lite), `core_interface` (the Base<->Core LGA, generated) |
| Board | `hardware/OpenAIO.kicad_pcb`, the **master**: Base island and Core island side by side, one stackup, all routing lives here |
| Derived boards | `hardware/export/OpenAIO-Base.kicad_pcb` and `OpenAIO-Core.kicad_pcb`, written by `hardware/tools/split_boards.py`, gitignored, never edited by hand. DRC, Fabrication Toolkit and STEP run on these |
| Local library | `hardware/lib.kicad_sym`, `hardware/lib.pretty/`, `hardware/lib.3dshapes/`, nickname `lib`. Seeded with the OpenFC-Lite-Mini local library so the copied FC sheets resolve; the lib tables also alias `components`, `4in1ESC` and `OpenRX-Shared` onto the catalogue for the same reason |
| Shared library | [OpenDrone-hw/KiCad-Library](https://github.com/OpenDrone-hw/KiCad-Library), one checkout per machine, nickname `OpenDrone`, resolved through the KiCad path variable `OPENDRONE_LIB` (Preferences > Configure Paths) |
| Design rules | `hardware/OpenAIO.kicad_dru`: canonical block plus 2 oz outer copper (0.16 mm clearance and track) for the Base only; the rules skip the rule area `Core`, which covers the Core island (1 oz, line standard 0.09) |
| Fab config | `hardware/fabrication-toolkit-options.json` |
| Board setup | Standard: 6 layers, 0.09 mm clearance and track, via 0.35 on 0.20 drill |
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

# derive Base and Core from the master, DRC both, refresh J90's Core model (KiCad closed)
cd hardware && /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 tools/split_boards.py --drc --update-master
```

On macOS `kicad-cli` is at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, and `pcbnew` imports
only under KiCad's bundled Python. Shared scripts (renders, STEP export,
packaging art) live in `OpenDrone-Scripts`; board-specific scripts live in
`hardware/tools/`.

## Architecture

Two PCBs, one project, one schematic, one master PCB. KiCad has one board per
project, so the master `OpenAIO.kicad_pcb` carries both boards as separate
islands (Base left, Core right); `tools/split_boards.py` derives the two
shippable boards from it by island. Nothing is ever routed in the derived files.

The Base<->Core interface is one pin table in `tools/lga_gen.py`, which emits
everything that must agree: `lib:Core_LGA_land` (F.Cu land pattern on the
Base, J90), `lib:Core_LGA_pads` (B.Cu pads on the Core, J91, X pre-mirrored so
the flipped footprint overlays the land pad for pad), the `lib:Core_LGA`
symbol and the `core_interface` sheet. 2 x 16 pads, 1.0 mm pitch, 12 mm row
gap, 0.6 mm round pads: 8 GND, `+BATT`, `+5V` x2, `+10V` x2, `+3.3V` x2,
`+4v5`, and 16 signals (`MOTOR1..4`, `UART0_TX/RX`, `UART1_TX/RX` to the RX,
`SPI0` + `FLASH_CS` to the SD card, `USB_D+/-`, `10V_ENABLE`, `CURR`). Every
interface net is a global label; `python3 tools/lga_gen.py` prints the table.
In the master those nets show one ratsnest line each between the islands, land
pad to Core pad; that is the interface, not an error (exclude them in the DRC
dialog once). The Core STEP from the split is J90's 3D model, so the master's
3D view shows the Core stacked at its true position for collision checks, and
the Core outline sits on J90's User.Comments layer while routing the Base.

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

- The Core is one island in the master, kept right of the Base with a clear
  gap; `split_boards.py` sorts items by which side of the J90/J91 midpoint they
  lie on and drops anything spanning it. Do not park parts in the gap.
- J90 and J91 must stay a mirror pair: same rotation, J91 flipped to B.Cu. Move
  the Core outline (Edge.Cuts) with the island; the split re-derives the shadow.
- Only the Core's top face carries parts; its bottom is the LGA. Nothing on the
  Base may stand under the Core footprint outline (J90 User.Comments).
- The rule area named `Core` (all copper layers, Core Edge.Cuts + 1 mm) is what
  switches the 2 oz rules off for the Core. Keep it over the whole island;
  `tools/lga_core_area.py` redraws it from the Core outline.

## Revisions

| Rev | Date | Change |
|---|---|---|
| <rev1> | <YYYY-MM-DD> | First release. |
