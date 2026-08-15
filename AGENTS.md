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
copied verbatim into `hardware/` and not yet placed on the root sheet.

## Repo

| | |
|---|---|
| Maintainer | @stancoene |
| Status | See the `status-*` topic on the repo. Never written here. |
| Designed in | KiCad 10 |
| KiCad project | `hardware/OpenAIO.kicad_pro` |
| Root schematic | `hardware/OpenAIO.kicad_sch`. Sub-sheets awaiting placement: `fc_power`, `fc_rp2350a`, `fc_imu`, `fc_osd`, `fc_blackbox`, `fc_pads` (OpenFC-Lite-Mini), `esc_channel` (OpenESC-20x20, one channel), `rx_esp32c3_sx1281` (OpenRX-Lite) |
| Board | `hardware/OpenAIO.kicad_pcb`, 6 layers, template stackup, nothing placed |
| Local library | `hardware/lib.kicad_sym`, `hardware/lib.pretty/`, `hardware/lib.3dshapes/`, nickname `lib`. Seeded with the OpenFC-Lite-Mini local library so the copied FC sheets resolve; the lib tables also alias `components`, `4in1ESC` and `OpenRX-Shared` onto the catalogue for the same reason |
| Shared library | [OpenDrone-hw/KiCad-Library](https://github.com/OpenDrone-hw/KiCad-Library), one checkout per machine, nickname `OpenDrone`, resolved through the KiCad path variable `OPENDRONE_LIB` (Preferences > Configure Paths) |
| Design rules | `hardware/OpenAIO.kicad_dru`, canonical block, no board-specific rules yet |
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
```

On macOS `kicad-cli` is at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, and `pcbnew` imports
only under KiCad's bundled Python. Shared scripts (renders, STEP export,
packaging art) live in `OpenDrone-Scripts`; board-specific scripts live in
`hardware/tools/`.

## Architecture

<The signal and power chain, block by block, in prose. Roughly ten lines. Say
why, not just what: the parts of the design a reader could not infer from the
schematic. Sub-sheet names in backticks so a reader can open the right one.>

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

<Only constraints a future editor would break by accident: keep-outs, RF
clearances, thermal copper, differential pairs, antenna keepouts, current paths
that must stay short. Delete the section if the board has none.>

## Revisions

| Rev | Date | Change |
|---|---|---|
| <rev1> | <YYYY-MM-DD> | First release. |
