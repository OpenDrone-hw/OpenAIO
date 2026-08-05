# OpenAIO

Open-source AIO board (flight controller + 4-in-1 ESC + ExpressLRS receiver) for toothpick-class 6S FPV drones, 25.5 x 25.5 mm mounting pattern, part of the incutec OpenDrone line. The three stages are merged from proven sibling designs: RP2354A flight controller (OpenFC-Lite-Mini rev 2), distributed-MCU AM32 4-in-1 ESC (OpenESC-20x20 Rev 2), and ESP32-C3 + SX1281 ELRS 2.4 GHz receiver (OpenRX-Lite). Designed in KiCad 10 for JLCPCB assembly. Full design detail: [hardware/docs/DESIGN.md](hardware/docs/DESIGN.md).

## Status

**Prototype pending**, design stage, no hardware yet, 2026-08-05.

Schematic sources were refreshed 2026-06-12 from the current sibling revisions. Not yet complete: inter-stage signal wiring on the root sheet (FC-ESC, FC-RX), re-annotation across the merged sheets, and the PCB layout, which predates the refresh. Details in [hardware/docs/DESIGN.md](hardware/docs/DESIGN.md).

## Specifications

| Parameter | Value |
|---|---|
| Function | FC + 4-in-1 ESC + ELRS RX on one board |
| Class | Toothpick, 6S, ~30 A continuous per motor design target |
| FC | RP2354A (dual Cortex-M33), LSM6DSV16XTR IMU, analog OSD, microSD blackbox |
| ESC | 4 independent AM32 channels, AT32F421G8U7 + NSG2065Q per channel, 24x DOY180N03T |
| RX | ESP32-C3FH4 + SX1281, ExpressLRS 2.4 GHz |
| Firmware | Betaflight (FC), AM32 (ESC), ExpressLRS (RX) |
| PCB | 6 copper layers, 25.5 x 25.5 mm mounting pattern |

Part-level detail is in [hardware/docs/DESIGN.md](hardware/docs/DESIGN.md).

## Repository layout

| Path | Contents |
|---|---|
| `hardware/` | KiCad 10 project: root schematic, PCB, project-local libraries |
| `hardware/schematics/` | Hierarchical sheets: `fc/`, `esc/`, `elrs/` |
| `hardware/docs/` | Design documentation ([DESIGN.md](hardware/docs/DESIGN.md)) |
| `docs/` | Sourcing, alternatives, cost, and market research snapshots |
| `libs/KiCad-Library` | Shared Incutec symbol/footprint/3D library (git submodule) |

## Design entry points

- Root schematic: `hardware/OpenAIO.kicad_sch`, instantiates six FC sheets, four ESC channel sheets, and the RX sheet
- FC sheets: `hardware/schematics/fc/` (rp2350a, power, imu, osd, blackbox, pads)
- ESC channel sheet: `hardware/schematics/esc/esc_channel.kicad_sch`, instantiated 4 times
- RX sheet: `hardware/schematics/elrs/elrs.kicad_sch`
- Board layout: `hardware/OpenAIO.kicad_pcb`, 6 copper layers (predates the 2026-06 schematic refresh)

Project-local libraries: `lib` (FC), `components` / `4in1ESC.pretty` (ESC), `OpenRX-Shared` (RX), `imports` (easyeda2kicad imports). The lib tables also reference the shared `Incutec` library from the `libs/KiCad-Library` submodule, used for new parts. The ESC sheets still carry legacy footprint references (`ESCLibrary:`, `PCM_*:`, `footprint:`) that are not in the project lib tables; see [hardware/docs/DESIGN.md](hardware/docs/DESIGN.md).

## Build and export

```
git clone --recursive https://github.com/incutec-hw/OpenAIO.git
```

Open `hardware/OpenAIO.kicad_pro` in KiCad 10. Production exports (gerbers, BOM, CPL) are generated with the [KiCad Fabrication Toolkit](https://github.com/bennymeg/Fabrication-Toolkit) plugin into `hardware/production/` (gitignored); none exist yet for this design. Headless checks use `kicad-cli`:

```
kicad-cli sch erc --exit-code-violations hardware/OpenAIO.kicad_sch
kicad-cli pcb drc --exit-code-violations hardware/OpenAIO.kicad_pcb
```

## Manufacturing

Designed for JLCPCB assembly with LCSC parts. No fabrication exports or hardware exist yet. Current sourcing status, stock risks, and part decisions: [docs/SOURCING-2026-06.md](docs/SOURCING-2026-06.md) (primary reference). [docs/ALTERNATIVES.md](docs/ALTERNATIVES.md) and [docs/COST_ANALYSIS.md](docs/COST_ANALYSIS.md) are 2026-03 snapshots of the pre-refresh ESC BOM.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Hardware licensed under [CERN-OHL-S-2.0](https://ohwr.org/cern_ohl_s_v2.txt). See [LICENSE](LICENSE). Firmware targets reference upstream projects (Betaflight, AM32, ExpressLRS) under their respective licenses.
