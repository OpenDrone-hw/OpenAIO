# OpenAIO

All-in-one board for 85 mm whoops, 2.5 inch cinewhoops and 3 inch freestyle on 3S to 6S: RP2354A flight controller (BMI270, BMP580, analog PIO OSD,
microSD blackbox), four AM32 ESC channels (AT32F421 + NSG2065Q + 6x DOY180N03T each) and an ExpressLRS 2.4 GHz
receiver (ESP32-C3 + SX1281). One schematic, one 35.4 mm square 8-layer HDI board, 25.5 mm mounting. It is not a
stack of modules and has no current rating established by measurement.

## Architecture

- **Power** (`fc_power`, root sheet): the battery pad (U24.1) feeds the 0.2 mOhm shunt Rsense2, which feeds `+BATT`.
  Two LMR51430 bucks run from `+BATT` with EN tied to it: U3 makes the always-on `+10V` gate-drive and VTX rail, U4
  makes `+5V`. `+5V` and USB VBUS are OR-ed by Schottky diodes into `+4v5`, which feeds the `+3.3V` LDO and the 1.8 V
  gyro LDO. At the bottom of the range U3 is in dropout and `+10V` follows the pack (research/INPUT_RANGE.md).
- **Flight controller** (`fc_rp2350a`, `fc_imu`, `fc_osd`, `fc_blackbox`, `fc_pads`): the RP2354A uses its internal
  SMPS for 1.1 V. The BMI270 is on SPI1 with Vdd from U6 (1.8 V) and Vdd_IO from 3.3 V. The OSD is a PIO framebuffer
  overlay: U9 switches camera video to U10 (op-amp buffer), U11 recovers sync. The microSD card is on SPI0. `fc_pads`
  holds the BMP580 (U26, I2C0), the SH-6 connector (U12) and the solder pads.
- **ESC** (`esc_channel` x4): each AT32F421 gets its throttle on PB4 from `MOTORn` (GPIO22 to 25) through 220R and drives
  one NSG2065Q (3 half bridges, VCC from `+10V`) with six DOY180N03T. Back-EMF dividers feed the AT32 comparator.
  The four ESCs share one shunt, read by the INA186A3 U25 (gain 100 V/V, 20 mV/A) into GPIO28. There is no per-ESC
  current or voltage sense.
- **Receiver** (`rx_esp32c3_sx1281`): the ESP32-C3 runs ExpressLRS and talks CRSF to the FC on UART1 (GPIO6/7). The
  SX1281 output goes through the band-pass FL1 to the u.FL JP1. The chip antenna AE2 on `/RX/WIFI` is for WiFi
  updates only. GPIO27 (`ELRS_EN`) drives the C3 CHIP_EN through R115; solder jumper JP2 (open) pulls it to GND.
- **Shared nets**: SH-6 pin 6, pad J55 and the ESP32-C3 TX share `UART1_RX`. SBUS from an air unit needs ELRS held
  off (JP2 closed or `ELRS_EN` low).

## Power

```
battery pad U24.1 (+) / U24.2 (-)
  Rsense2 0.2 mOhm 2512 (read by U25 INA186A3 -> GPIO28)
  +BATT  3S-6S (9.0-25.2 V)
   |- 12 high-side DOY180N03T drains, R1 100k / R2 10k divider to GPIO29
   |- U3 LMR51430YFDDCR, L2 4.7 uH, R17 100k / R18 6.49k  -> +10V = 9.84 V (follows +BATT in dropout)
   |     NSG2065Q VCC x4 (U14 U16 U18 U20), SH-6 pin 1, pads J41 J51
   |- U4 LMR51430YFDDCR, L3 4.7 uH, R19 100k / R20 13.7k  -> +5V = 4.98 V
   |     pads J15 J16 J24 J25 J30 J33 J37
  USB-C VBUS (+5V_USB) -> D3 DSK24 --+
  +5V                  -> D2 DSK24 --+-> +4v5 (pads J42 J52)
   |- U7 TLV76733DRVR (1 A) -> +3.3V: RP2354A IOVDD and ADC, BMI270 Vdd_IO, BMP580, microSD, OSD ICs,
   |     ESP32-C3, SX1281, 4x AT32F421 VDD, INA186A3
   |     RP2354A internal SMPS (L1 3.3 uH) -> +1.1V DVDD
   |- U6 LP5912-1.8DRVR -> +1.8V_GYRO (BMI270 Vdd)
```

## Key parts

| Function | Ref | Part | LCSC | Note |
|---|---|---|---|---|
| MCU | U2 | RP2354A | C41378174 | 2 MB in-package flash; crystal X1 XTM25012000JT00351001 (C37635340) |
| IMU | U8 | BMI270 | C2836813 | SPI1 |
| Barometer | U26 | BMP580 | C22391138 | I2C0, address 0x47 |
| OSD | U9, U10, U11 | SN74LVC1G3157, COS8051SOT, TLV7031 | C2673087, C7463385, C2876045 | video switch, buffer, sync comparator |
| Blackbox | Card1 | TF-021B-H265 microSD | C498185 | SPI0 |
| USB | USB1 | TYPE-C 16P QTWT | C5187472 | full speed, R8 R9 30R series |
| Buck, `+10V` and `+5V` | U3, U4 | LMR51430YFDDCR | C5219261 | 3 A, 36 V max VIN |
| Inductors | L2, L3 | XRTC303020D4R7MBCA | C39846837 | 4.7 uH |
| 3.3 V LDO | U7 | TLV76733DRVR | C2848334 | 1 A |
| 1.8 V LDO | U6 | LP5912-1.8DRVR | C2876234 | gyro supply |
| OR diodes | D2, D3 | DSK24 | C64890 | |
| ESC MCU | U13 U15 U17 U19 | AT32F421G8U7 | C2765098 | AM32 |
| Gate driver | U14 U16 U18 U20 | NSG2065Q | C41414478 | VCC 8-20 V recommended |
| Power FET | Q3 to Q26 | DOY180N03T | C49441966 | VDS 30 V, PowerDI3333-8; the schematic Description field says 40 V, the datasheet says 30 V |
| Shunt | Rsense2 | ASR-S-3-0.2F 0.2 mOhm 2512 | C695806 | |
| Current amp | U25 | INA186A3IDCKR | C2058245 | 100 V/V, common mode up to 40 V |
| Receiver MCU | U22 | ESP32-C3 (FH4 pin use) | none | no LCSC or MPN field in the schematic |
| Radio | U21 | SX1281IMLTRT | C2151551 | with OSC1 52 MHz TCXO (C22434896), crystal X2 CJ17-400001010B20 (C2875272) |
| RF | FL1, AE2, JP1 | 2450FM07D0034T, 2450AT18A100E, U.FL-R-SMT-1(80) | none, C89334, none | |
| SH-6 | U12 | SM06B-SRSS-TB(LF)(SN) | C160405 | |
| Buzzer and LED strip drivers | Q1, Q2 | AP1606 | C2849580 | Q2 inverts the LED strip (firmware/ISSUES.md I2) |

Fields missing in the schematic: LCSC for U22, FL1, JP1, D9, L4, R115; value and LCSC for C90 to C106 (the `+BATT`
ceramics, 0805 and 1206).

## Connectors and I/O

| Connector | Ref | Part | Function |
|---|---|---|---|
| Battery and motor pads | U24 (`AIO_outline`) | footprint pads | 1 `/CSA+` (battery +), 2 GND, 12-14 ESC1, 15-17 ESC2, 18-20 ESC3, 21-23 ESC4 |
| USB-C | USB1 | TYPE-C 16P QTWT | USB 2.0, DFU and configurator |
| SH-6 | U12 | JST SM06B-SRSS-TB | 1 `+10V`, 2 GND, 3 `UART0_TX`, 4 `UART0_RX`, 5 GND, 6 `UART1_RX`, 7 and 8 GND |
| microSD | Card1 | TF-021B-H265 | blackbox |
| ELRS antenna | JP1 | U.FL-R-SMT-1(80) | 2.4 GHz |

Solder pads (`small_pad` footprints, DNP-flagged on the board):

| Pads | Net |
|---|---|
| J15 J16 J24 J25 | `+5V` (LED strip) |
| J17 J18 J27 J28 | GND, one per corner |
| J20 J21 J31 J32 | `LED_STRIP` (WS2812 data, GPIO8) |
| J33, J29 | `+5V`, `BUZZER-` (low-side switched, B.Cu) |
| J30 J37, J34 J35 J40 J43 J50 J53 | `+5V`, GND |
| J38, J39 | `/OSD/VIDEO_IN`, `/OSD/VIDEO_OUT` |
| J41 J51 | `+10V` |
| J42 J52 | `+4v5` |
| J23, J26 | `/Pads/I2C0.SCL`, `/Pads/I2C0.SDA` (GPIO5, GPIO4) |
| J44, J45 | `/Pads/PIOUART0_TX`, `/Pads/PU0RX` (Betaflight UART0, GPIO2/3) |
| J49, J48 | `UART0_TX`, `UART0_RX` (Betaflight PIOUART0, GPIO0/1) |
| J54, J55 | `UART1_TX`, `UART1_RX` (ELRS link, GPIO6/7) |
| TP1/TP2, TP3/TP4, TP5/TP6, TP7/TP8 | AT32 SWDIO/SWCLK of ESC1 to ESC4 (B.Cu) |
| TP9 | `/RX/BOOT` (ESP32-C3 GPIO9, ELRS flashing) |
| JP2 | `/RX/CHIP_EN` to GND: closed forces ELRS off |

The RP2354A has no SWD pads (U2 SWCLK and SWDIO are unconnected); USB and BOOTSEL (U1) only. The full GPIO map is
`firmware/PINOUT.md`.

## Layout rules

- **HDI 1+6+1** (`OpenAIO.kicad_dru`): microvia 0.25 / 0.10 on L1-L2 and L7-L8 only, buried via 0.33 / 0.15 on L2-L7
  only, mechanical blind vias not allowed, microvia may stack on a same-net buried via, never on another microvia.
  Through vias 0.33 / 0.15 only where F.Cu and B.Cu copper meet.
- **Current path**: battery pad, `/CSA+`, Rsense2 (B.Cu, beside the pad), `+BATT` mostly on L4, 12 high-side FETs on
  F.Cu, 12 low-side FETs on B.Cu, return on L7 and L2. Shunt position and the L4 neck set the loss
  (research/ROUTING.md). Keep the U25 sense taps (`/CSA+` at U25.4, `+BATT` at U25.5) as a pair.
- **Phases and gates**: classes Phase (1.0 mm), Gate (0.2 mm), matched by net name patterns `/1A` to `/4C`,
  `Net-(Q*-G)`, `/ESC?/G[HL]?`.
- **RF**: `/RX/WIFI` and `*/ANT*` are class RF (0.12 clearance). A rule area at x 79.5 to 84.0 mm, y 75.3 to 78.0 mm
  (AE2) forbids zone fills on all copper layers. The ELRS path is U21.22, FL1, JP1.
- **USB**: class USB, 0.13 track, 0.12 clearance, 0.13 wide differential pair with 0.15 gap, R8 and R9 30R at U2.
- **Analog**: class Analog (0.12) for `CURR`, `ADC_VBAT`, `/ESC?/FB*`, video, crystal nets.
- **Clearances**: 0.09 mm line standard, copper to edge 0.20 mm.
- **Locating pegs** of USB1 are NPTH; the DRU accepts 0.08 mm to R4.2.

## Firmware

Betaflight (target `OPENAIO`, files in `firmware/betaflight/configs/OPENAIO/`), AM32 (`OPENESC_20_F421`), ExpressLRS
(`Generic ESP32C3 2.4Ghz RX`). First flash, pinout and known board limits: [firmware/README.md](firmware/README.md).
Upstream: [Betaflight](https://github.com/betaflight/betaflight), [AM32](https://github.com/am32-firmware/AM32),
[ExpressLRS](https://github.com/ExpressLRS/ExpressLRS).

## Repo

| | |
|---|---|
| Maintainer | OpenDrone-hw |
| Status | See the `status-*` topic on the repo. Never written here. |
| Designed in | KiCad 10 |
| KiCad project | `hardware/OpenAIO.kicad_pro` |
| Root schematic | `hardware/OpenAIO.kicad_sch`, sub-sheets `fc_power`, `fc_rp2350a`, `fc_imu`, `fc_osd`, `fc_blackbox`, `fc_pads`, `esc_channel` (x4), `rx_esp32c3_sx1281` |
| Board | `hardware/OpenAIO.kicad_pcb`, 8 layers, HDI 1+6+1, 0.997 mm, 1 oz on all layers, ENIG (stackup in research/ROUTING.md) |
| Local library | `hardware/lib.kicad_sym`, `hardware/lib.pretty/`, `hardware/lib.3dshapes/`, nickname `lib` |
| Shared library | `hardware/KiCad-Library/`, submodule of [OpenDrone-hw/KiCad-Library](https://github.com/OpenDrone-hw/KiCad-Library), nickname `OpenDrone`; 3D models and exact component datasheets resolve through the project text variable `OPENDRONE_LIB` |
| Design rules | `hardware/OpenAIO.kicad_dru`, canonical block plus the HDI 1+6+1 via rules, the U9 land pattern (0.076), the USB1 peg to R4 exception and a `Core layout` clearance rule that matches no rule area on the board |
| Fab config | `hardware/fabrication-toolkit-options.json` |
| Board setup | 8 layers, 0.09 mm clearance and track, via 0.33 on 0.15 drill, microvia 0.25 on 0.10 |
| License | CERN-OHL-S-2.0 |

A repository holds design files only. Sourcing (suppliers, prices, quotes, RFQs, contacts) is handled by Incutec and never lives in OpenDrone repositories.

## Parts and datasheets

- **Per-repository part index:** the root schematic and its listed sub-sheets
  are authoritative for what this board fits. Export the netlist with the
  command below when a script-readable board index is needed; do not maintain
  a second hand-written BOM.
- **Proven shared parts:**
  `hardware/KiCad-Library/PARTS-USED.md` is the catalogue index. Its `Boards`
  column identifies every repository using each LCSC part; filter that column
  for `OpenAIO` to get this repository's proven shared-part view.
- **Exact datasheets:**
  `hardware/KiCad-Library/datasheet/manifest.json` maps shared symbols to the
  committed PDFs and their SHA-256 hashes. The PDFs live in
  `hardware/KiCad-Library/datasheet/`, and symbol links resolve there through
  `OPENDRONE_LIB`.
- **Local-only parts:** inspect `hardware/lib.kicad_sym`,
  `hardware/lib.pretty/`, and `hardware/lib.3dshapes/`, then verify supplier
  fields in the board schematic. Do not duplicate a shared part or datasheet.

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
Board-specific scripts, where a board has any, live in `hardware/tools/`: via
passes (`via_*.py`, `hdi_via_pass.py`), copper models (`power_paths_v2.py`,
`loop_resistance.py`), routing helpers (`fr_*.py`, `cleanup.py`) and library
localisers. Each carries its usage in its docstring; read it before running, KiCad closed.

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

## Revisions

| Rev | Date | Change |
|---|---|---|
| unreleased | 2026-10-16 | One routed 8-layer HDI board, no release tag yet. ERC and DRC state in research/ROUTING.md. |

## By task

Board-specific paths are in Environment above. `KPY` is KiCad's bundled
Python named there.

- Check the design: run the ERC and DRC commands in Environment before every pull request.
- Add a part: place it from the `OpenDrone` library if `hardware/KiCad-Library/PARTS-USED.md` lists it; otherwise import it into `lib` with `$KPY <hardware-tooling>/hardware/kicad/import_part.py` (read `--help` first), KiCad closed.
- Render the board for the README: `$KPY <hardware-tooling>/hardware/kicad/render_board.py hardware/OpenAIO.kicad_pcb --outdir images`, KiCad closed.
- Analyse the netlist: export it with the netlist command in Environment, then read it with a script; never hand-write a second BOM.
- Update the shared library: `git submodule update --remote hardware/KiCad-Library`, run DRC, commit as its own reviewed change.
