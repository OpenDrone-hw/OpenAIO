# OpenAIO

All-in-one board for toothpick-class FPV, 2-6S: 4x AM32 ESC, power, pads and
ExpressLRS dual band (LR1121) receiver on 25.5 x 25.5 mm, with the flight controller
(MCU, IMU, baro, OSD, blackbox) on the shared OpenFC-Core module, reflowed onto
this board as a 52 pad LGA (J1). The ESC sheet comes from OpenESC-20x20, the RX sheet
(`esp32c3_lr1121_mono`: ESP32-C3FH4, LR1121, RFX2401C, SKY13373, one U.FL) from
OpenRX-Mono, the pads from OpenFC-Lite-Mini, wired on the root sheet.

## Architecture

One board. The flight controller is not designed here: it is the OpenFC-Core
module, placed as J1 (`lib:OpenDrone-Core`, footprint
`OpenDrone-Core_LGA_land`, 52 pads of 1.0 mm on a 2.0 mm grid, 15 x 15 mm)
and reflowed onto the top side like any other part. Everything the core needs
from this board crosses that land: `+4v5` and `+BATT` in, `MOTOR1..4` out to
the four `esc_channel` sheets, `UART0`/`UART1` and `PIOUART0`/`PIOUART1` to
the RX sheet and the pads, `CURR` from the current sense amplifier,
`10V_ENABLE` to the power sheet, `BUZZER-`, `LED_STRIP`, `VIDEO_IN`/`OUT`,
USB `D+`/`D-` to the Type-C. Pad names are the core's net names; the pin map
and land are defined by the core's vendored symbol and footprint. They are not
edited in this repo.

## Voltage envelope

2S-6S, 6.0 to 25.2 V. The ceiling is the MOSFET: DOY180N03T is 30 V VDSS, the
same part and the same NSG2065Q topology OpenESC-20x20 flies at 6S. The 40 V
SP40N01GHNK that takes OpenESC-30x30 to 8S is PDFN-8L 5x6 and four channels of
it do not fit on 25.5 mm, so 6S is the ceiling here, not 8S.

At the bottom of the range the +10V gate rail is not regulated. The 10 V buck
(U8, LMR51430, FB divider for 9.85 V) drops out near 10.3 V input and runs in
pass-through below that, so the drivers see roughly +BATT. At 2S (about 5.9 V
at 3.0 V/cell, 8.4 V full) that is above the NSG2065Q UVLO (4.9 V max) but
below its recommended VCC range of 8 to 20 V (datasheet section 8.5; an earlier
revision of this file said 5 to 20 V). The board runs, but gate drive is
reduced, so the continuous-current rating at 2S is lower than at 6S; neither
figure is published without a measurement. The gate drive is outside the recommended
range whenever +BATT is below about 10.3 V (all of 2S, and 3S below about 3.4 V
per cell).

## Battery lead

- No reverse polarity protection: a reversed battery destroys the board.
- Required: a 330 to 470 uF low-ESR 35 V capacitor at the battery lead, as
  OpenESC-20x20 uses. The on-board bank is ceramic only; a hot-plugged 6S pack
  can ring above the 30 V FETs and the 38 V buck absolute maximum, and a TVS
  does not fix that.

## Betaflight target settings

| Item | Value | Source |
|---|---|---|
| Shunt | Rsense2 0.2 mOhm, INA186A3 gain 100 V/V = 20 mV/A | `hardware/OpenAIO.kicad_sch` |
| `ibata_scale` | 200 (units of 0.1 mV/A) | 20 mV/A |
| Current full scale | about 162 A | 3.3 V output span at 20 mV/A |
| Zero offset | calibrate after assembly; up to about 0.25 A | INA186 datasheet |
| Gate rail | off until PINIO/USER1 is set permanent ON for `10V_ENABLE` (J1 pad 23 through 100 k to U8 EN) | `fc_power` |
| `CURR` | includes the 5 V buck input current (U9 is downstream of the shunt) | `fc_power` |
| LED and 5 V pads | live only with a battery connected, not from USB | `fc_power` |

## Layout rules

- Nothing may stand under J1 on the top side: the core's bottom is flat
  copper on the land. Bottom side parts under it are fine.
- J1 keeps every pad, unused ones stay open; delete pads per instance only for
  routing room. Ground pads tie into the plane.
- Move the core only by moving J1; never edit the footprint here.

## Repo

| | |
|---|---|
| Maintainer | @Just4Stan (Discord: juststan_) |
| Status | See the `status-*` topic on the repo. Never written here. |
| Designed in | KiCad 10 |
| KiCad project | `hardware/OpenAIO.kicad_pro` |
| Root schematic | `hardware/OpenAIO.kicad_sch`. Sub-sheets: `fc_power`, `fc_pads` (OpenFC-Lite-Mini), `esc_channel` x4 (OpenESC-20x20), `esp32c3_lr1121_mono` (OpenRX-Mono). The core is the symbol `lib:OpenDrone-Core`, J1, on the root |
| Board | `hardware/OpenAIO.kicad_pcb`, 8 layer HDI 1+6+1, 1.6 mm, 1 oz copper on all layers |
| Core module | OpenFC-Core, one symbol and one footprint (`OpenDrone-Core_LGA_land`) vendored into `lib`; never edit them here |
| Local library | `hardware/lib.kicad_sym`, `hardware/lib.pretty/`, `hardware/lib.3dshapes/`, nickname `lib`. Seeded with the OpenFC-Lite-Mini local library so the copied sheets resolve; the lib tables also alias `components`, `4in1ESC` and `OpenRX-Shared` onto the catalogue for the same reason |
| Shared library | `hardware/KiCad-Library/`, pinned submodule of [OpenDrone-hw/KiCad-Library](https://github.com/OpenDrone-hw/KiCad-Library), nickname `OpenDrone`; 3D models and exact component datasheets resolve through `OPENDRONE_LIB` |
| Design rules | `hardware/OpenAIO.kicad_dru`: canonical block plus the HDI 1+6+1 via, plane and RF rules |
| Fab config | `hardware/fabrication-toolkit-options.json` |
| Board setup | 8 copper layers, 1.6 mm, 0.09 mm clearance and track, 0.075 mm annular ring, microvia 0.25 on 0.10 drill, buried and default through via 0.40 on 0.20 drill. Pre-defined sizes and net classes in `hardware/OpenAIO.kicad_pro` |
| Layer plan | L1 `F.Cu` parts, L2 `In1.Cu` GND plane (type power, no tracks), L3 `In2.Cu` signal, L4 `In3.Cu` power and signal, L5 `In4.Cu` power and signal, L6 `In5.Cu` signal, L7 `In6.Cu` GND plane (type power, no tracks), L8 `B.Cu` parts |
| Vias | Laser microvia `F.Cu`-`In1.Cu` and `In6.Cu`-`B.Cu` 0.25/0.10; buried `In1.Cu`-`In6.Cu` 0.40/0.20 (Power class 0.45/0.25); through `F.Cu`-`B.Cu` 0.40/0.20 (ring 0.09 min). Mechanical blind vias, other microvia spans and other buried spans are errors in the `.kicad_dru`. Layer pair presets `Buried L2-L7` and `Outer F-B` are in `hardware/OpenAIO.kicad_pro`. Routing how-to text is on `Cmts.User` right of the outline |
| Stackup | 1.602 mm in `hardware/OpenAIO.kicad_pcb`: mask 0.015, 1 oz (0.035 mm) copper on all eight layers, dielectrics L1-L8 1080 0.077 (Dk 4.0) / 2116 0.125 (4.2) / core 0.330 (4.3) / 2116+2313 0.228 (4.15) / core 0.330 / 2116 0.125 / 1080 0.077. ENIG. Vias filled and capped (IPC-4761 VII) |
| License | CERN-OHL-S-2.0 |

## Decisions

- 2026-10-13: 8 layer HDI 1+6+1 at NextPCB, layer plan B: L1 parts, L2 GND,
  L3 signal, L4 power, L5 power, L6 signal, L7 GND, L8 parts. GND on L2/L7
  gives every GND pin one microvia, puts 50 ohm on L1/L8 at about 0.105-0.115
  mm over 0.077 mm 1080, and shields inner layers from the phase nodes. 1 oz on
  all layers: 2 oz forces 5/5 mil at NextPCB. Vias: laser 0.25/0.10
  `F.Cu`-`In1.Cu` and `In6.Cu`-`B.Cu`, buried `In1.Cu`-`In6.Cu` 0.40/0.20
  (power 0.45/0.25), through 0.40/0.20; no mechanical blind vias, microvias
  stacked on a same-net buried via or staggered 0.25 mm (stacking allowed
  2026-10-13, priced by NextPCB as HDI II / Rank 2). All tracks and vias were
  removed for a full re-route; footprints, zones and nets kept. Sources:
  NextPCB HDI capabilities and stackup case study, EPC and TI power-loop
  layout notes, IPC-WP-023 on stacked microvias.

- 2026-10-13: stacked microvia allowed on a same-net buried via; staggered
  0.25 mm stays allowed. NextPCB prices the stack as HDI II (Rank 2), about
  +0.34 USD per board at 1000 pcs and +4 days.

## Environment

```sh
# schematic and board checks
kicad-cli sch erc hardware/OpenAIO.kicad_sch
kicad-cli pcb drc --schematic-parity --refill-zones hardware/OpenAIO.kicad_pcb

# netlist, for scripted analysis
kicad-cli sch export netlist --format kicadsexpr -o /tmp/OpenAIO.net hardware/OpenAIO.kicad_sch
```

On macOS `kicad-cli` is at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, and `pcbnew` imports
only under KiCad's bundled Python. Reusable scripts for renders, STEP export,
and packaging art come from Incutec hardware tooling. The OpenDrone release
standard is
[RELEASES.md](https://github.com/OpenDrone-hw/.github/blob/main/RELEASES.md).
This board has no board-specific scripts; any it gets go in a `tools` folder under `hardware`.
`KPY` is KiCad's bundled Python, on macOS
`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`.

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
