# OpenAIO

All-in-one board for toothpick-class FPV, 2-6S, on one PCB: RP2354A flight
controller (BMI270, DPS368 baro, PIO analog OSD, microSD blackbox), 4x AM32 ESC
(AT32F421 + NSG2065Q + DOY180N03T) and an ExpressLRS 2.4 GHz receiver
(ESP32-C3 + SX1281). The sub-sheets come from the manufactured
OpenFC-Lite-Mini, OpenESC-20x20 and OpenRX-Lite designs. The layout is the
routed Base and Core boards of the earlier two-board revision (8fa8d7b), merged
into one file on the OpenAIO-Whoop 8-layer HDI stackup.

## Architecture

One schematic, one board. The Base and Core boards of the previous revision
were joined by a 46-pad LGA (J90 on the Base, J91 on the Core) whose pads
carried identical nets; both footprints and the `core_interface` sheet are
gone, so every former LGA net is now a plain net between the two layouts and
shows as a ratsnest line. The Core's escape vias that went down to J91 are
left as routing anchors (via_dangling until routed).

## Voltage envelope

2S-6S, 6.0 to 25.2 V. The ceiling is the MOSFET: DOY180N03T is 30 V VDSS, the
same part and the same NSG2065Q topology OpenESC-20x20 flies at 6S. The 40 V
SP40N01GHNK that takes OpenESC-30x30 to 8S is PDFN-8L 5x6 and four channels of
it do not fit on 25.5 mm, so 6S is the ceiling here, not 8S.

At the bottom of the range the +10V gate rail is not regulated: the buck runs
in pass-through and the drivers see roughly +BATT, 5.6-8.2 V over a 2S flight.
That clears the NSG2065Q UVLO (4.5 V typ, 4.9 V max) but sits below the 8-20 V
VCC of its recommended operating conditions (datasheet section 8.5; the 5-20 V
on page 1 is the feature list), see `research/review-2026-10/INPUT_RANGE.md`.
2S is outside the driver's specified range until a bench run says otherwise;
no continuous-current figure is published at 2S or 6S without a measurement.

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

## Repo

| | |
|---|---|
| Maintainer | @Just4Stan (Discord: juststan_) |
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
| Shared library | `hardware/KiCad-Library/`, pinned submodule of [OpenDrone-hw/KiCad-Library](https://github.com/OpenDrone-hw/KiCad-Library). Not referenced by the lib tables: every part used is copied into `lib` |
| License | CERN-OHL-S-2.0 |

## Environment

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
# schematic and board checks
$CLI sch erc hardware/OpenAIO.kicad_sch
$CLI pcb drc --schematic-parity --refill-zones hardware/OpenAIO.kicad_pcb

# netlist, for scripted analysis
$CLI sch export netlist --format kicadsexpr -o /tmp/OpenAIO.net hardware/OpenAIO.kicad_sch

# Update PCB from Schematic without the GUI (KiCad closed); new parts park right of the board
$CLI sch export netlist --format kicadsexpr -o /tmp/OpenAIO.net hardware/OpenAIO.kicad_sch
$KPY hardware/tools/sync_pcb.py hardware/OpenAIO.kicad_pcb --netlist /tmp/OpenAIO.net
```

On macOS `kicad-cli` is at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, and `pcbnew` imports
only under KiCad's bundled Python. Reusable scripts for renders, STEP export,
and packaging art come from Incutec hardware tooling. The OpenDrone release
standard is
[RELEASES.md](https://github.com/OpenDrone-hw/.github/blob/main/RELEASES.md).
`KPY` is KiCad's bundled Python, on macOS
`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`.

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
  footprinted and shipped it, and its symbol links to the exact committed
  datasheet: place it from `OpenDrone`. Draw a new part into `lib` only when
  the catalogue has nothing that fits, imported with
  `easyeda2kicad` from its LCSC number. Pulling a newer catalogue is a
  deliberate, reviewed commit: `git submodule update --remote
  hardware/KiCad-Library`, then DRC.
- **One person holds a board layout at a time.** KiCad files do not merge. Say
  on Discord that you are taking it. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **Run ERC and DRC before every pull request.** Existing approved findings
  may remain; a new type or increased count must be reviewed before merge.
  Commands are in Environment above.

## By task

Board-specific paths are in Environment above. `KPY` is KiCad's bundled
Python named there.

- Check the design: run the ERC and DRC commands in Environment before every pull request.
- Add a part: place it from the `OpenDrone` library if `hardware/KiCad-Library/PARTS-USED.md` lists it; otherwise import it into `lib` with `$KPY <hardware-tooling>/hardware/kicad/import_part.py` (read `--help` first), KiCad closed.
- Render the board for the README: `$KPY <hardware-tooling>/hardware/kicad/render_board.py hardware/OpenAIO.kicad_pcb --outdir images`, KiCad closed.
- Analyse the netlist: export it with the netlist command in Environment, then read it with a script; never hand-write a second BOM.
- Update the shared library: `git submodule update --remote hardware/KiCad-Library`, run DRC, commit as its own reviewed change.

## Revisions

| Rev | Date | Change |
|---|---|---|
| r3 | 2026-10-15 | One board: Base and Core merged, OpenAIO-Whoop 8L HDI stackup, DPS368 baro, schematic review fixes. Not routed as one board. |
