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

All-in-one board for toothpick-class 3S-6S FPV on one PCB: RP2354A flight
controller (BMI270, DPS368 baro, PIO analog OSD, microSD blackbox), 4x AM32 ESC
(AT32F421 + NSG2065Q + DOY180N03T) and an ExpressLRS 2.4 GHz receiver
(ESP32-C3 + SX1281) on 25.5 x 25.5 mm. The sub-sheets come from the
manufactured OpenFC-Lite-Mini, OpenESC-20x20 and OpenRX-Lite designs. The
layout is the routed Base and Core boards of the earlier two-board revision
(8fa8d7b), merged into one file on the OpenAIO-Whoop 8-layer HDI stackup.

## Repo

| | |
|---|---|
| Maintainer | @stancoene |
| Status | See the `status-*` topic on the repo. Never written here. |
| Designed in | KiCad 10 |
| KiCad project | `hardware/OpenAIO.kicad_pro`, one schematic and one board |
| Root schematic | `hardware/OpenAIO.kicad_sch`. Sub-sheets: `fc_power`, `fc_rp2350a`, `fc_imu`, `fc_osd`, `fc_blackbox`, `fc_pads` (OpenFC-Lite-Mini, plus the DPS368 baro U28), `esc_channel` x4 (OpenESC-20x20), `rx_esp32c3_sx1281` (OpenRX-Lite) |
| Board | `hardware/OpenAIO.kicad_pcb`, 35.4 x 35.4 mm. While the merge is open, the Core layout sits right of the Base outline with its own Edge.Cuts; see `research/ROUTING.md` |
| Library | Project-local only: `hardware/lib.kicad_sym`, `hardware/lib.pretty/`, `hardware/lib.3dshapes/` (nickname `lib`). KiCad 10 stock `Device`, `power`, `Connector`, `Connector_Generic` and `MCU_Espressif` symbols cover the rest. No `OPENDRONE_LIB` paths in the tables |
| Design rules | `hardware/OpenAIO.kicad_dru`: canonical block, the HDI 1+6+1 via rules from OpenAIO-Whoop, and the Base/Core rules that still apply (RF, CSA, PHASE, USB, DOY180N03T EP, AE2 antenna, edge pads, mask gangs) |
| Fab config | `hardware/fabrication-toolkit-options.json` |
| Stackup | 8-layer HDI 1+6+1, 0.997 mm, 1 oz on all layers, ENIG, copied from OpenAIO-Whoop (`hardware/tools` of that repo, `stackup.json`): 1080 0.077 / 1080 0.077 / core 0.127 / 2116 0.125 / core 0.127 / 1080 0.077 / 1080 0.077 |
| Vias | Fab form: laser microvia F.Cu-In1.Cu and In6.Cu-B.Cu 0.25/0.10, buried In1.Cu-In6.Cu 0.33/0.15, stacked allowed. Edit form: one through via per stack (0.35/0.15-0.20), a DRC warning, converted by `tools/hdi_via_pass.py` |
| License | CERN-OHL-S-2.0 |

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
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$CLI sch erc hardware/OpenAIO.kicad_sch
$CLI pcb drc --schematic-parity --refill-zones hardware/OpenAIO.kicad_pcb
$CLI sch export netlist --format kicadsexpr -o /tmp/OpenAIO.net hardware/OpenAIO.kicad_sch

# Update PCB from Schematic without the GUI (KiCad closed); new parts park right of the board
$CLI sch export netlist --format kicadsexpr -o /tmp/OpenAIO.net hardware/OpenAIO.kicad_sch
$KPY hardware/tools/sync_pcb.py hardware/OpenAIO.kicad_pcb --netlist /tmp/OpenAIO.net
```

`sync_pcb.py` needs the `kicad-cli` path or `--netlist`. A pcbnew save rewrites
`OpenAIO.kicad_pro`; check `git diff` on it after every script and keep only
deliberate changes.

Board tools in `hardware/tools/`, from OpenAIO-Whoop, each with its usage in
the docstring: `hdi_via_pass.py` (edit form <-> fab form vias, `--collapse`),
`sync_pcb.py`, `pad_vias.py`, `gnd_stitch.py`, `track_to_pour.py`,
`track_widen.py`, `via_declutter.py`, `via_relocate.py`, `inner_router.py`,
`loop_resistance.py`. They were written for the Whoop's net and class names
(`Power`, `Gate`, `Phase`); this board's classes are `POWER`, `PHASE`, `CSA`,
`RF`, `USB`. Read the class and net constants at the top of a tool before
running it here.

## Architecture

One schematic, one board. The Base and Core boards of the previous revision
were joined by a 46-pad LGA (J90 on the Base, J91 on the Core) whose pads
carried identical nets; both footprints and the `core_interface` sheet are
gone, so every former LGA net is now a plain net between the two layouts and
shows as a ratsnest line. The Core's escape vias that went down to J91 are
left as routing anchors (via_dangling until routed).

## Layout rules

- Layer use as routed (from the two-board layouts, not yet re-planned): Base
  In1-In4 carry the phase-node copper of the power stages, In5 `+BATT` and
  `+10V`, In6 GND, In2 most Base signal routing; the Core used In1/In4 as GND,
  In2/In3 for signals and `+3.3V`. The OpenAIO-Whoop plan (L2 and L7 solid GND,
  power planes on L4/L5) is the target when the layers are re-planned.
- RF: `+BATT` keeps 0.80 mm from the 2.4 GHz chain; no tracks or vias in the
  `AE2 antenna` area except the antenna feed.
- DOY180N03T exposed pads: no other-net copper inside `DOY_EP`.
- Keep the USB1 locating peg check: the board is now 0.997 mm thick.

## Revisions

| Rev | Date | Change |
|---|---|---|
| r3 | 2026-10-15 | One board: Base and Core merged, OpenAIO-Whoop 8L HDI stackup, DPS368 baro, schematic review fixes. Not routed as one board. |
