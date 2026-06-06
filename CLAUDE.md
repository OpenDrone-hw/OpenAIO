# OpenAIO — Project Instructions

## What This Is
25.5×25.5 mounting-pattern AIO combining OpenFC-ECO (FC) + 4in1ESC (power stage) + OpenRX-Lite (ELRS). Two PCBs bonded via BGA-style solder pads, both in one KiCad project file. Target: 6S, 30 A per channel (toothpick class).

## Porting Status
- **Schematics**: copied from source repos, not yet wired into a hierarchical root. `OpenAIO.kicad_sch` (root) does not exist yet — user creates it.
- **PCB**: does not exist yet. Both board outlines live in one `.kicad_pcb` file.
- **Libraries**: all project-local. KiCad standard libs (Device, power, Connector, Package_SMD, etc.) are external via KiCad defaults — not bundled.

## Source Schematic Provenance
| File | From | Notes |
|---|---|---|
| `rp2350a.kicad_sch` | OpenFC-ECO V0.3 | RP2354B, verbatim |
| `power.kicad_sch` | OpenFC-ECO V0.3 | Apply V0.4 fixes before first spin (see Known Issues) |
| `imu.kicad_sch` | OpenFC-ECO V0.3 | LSM6DSV16XTR, verbatim |
| `osd.kicad_sch` | OpenFC-ECO V0.3 | PIO analog OSD |
| `blackbox.kicad_sch` | OpenFC-ECO V0.3 | TF-021B-H265 microSD slot |
| `pads.kicad_sch` | OpenFC-ECO V0.3 | Pads and connectors |
| `esc_main.kicad_sch` | 4in1ESC 2 (`4in1ESC.kicad_sch`) | ESC power rail, CSA, 8-pin JST |
| `esc_channel.kicad_sch` | 4in1ESC 2 (`ESC.kicad_sch`) | Single channel, instantiate 4× |
| `elrs.kicad_sch` | OpenRX-Lite (`esp32c3_sx1281_lite.kicad_sch`) | ESP32-C3 + SX1281, ceramic antenna |

## Library Structure (all project-local)

### Symbols
| Nickname | File | Source | Symbols |
|---|---|---|---|
| `lib` | `lib.kicad_sym` | OpenFC-ECO base + 4in1ESC + AT32F421 + SP40N03GNJ | 90 |
| `components` | `components.kicad_sym` | 4in1ESC 2 cached | 7 |
| `ESCLibrary` | `ESCLibrary.kicad_sym` | 4in1ESC 2 cached (legacy pre-valued passives + AT32F421) | 5 |
| `PCM_Resistor_AKL` | `PCM_Resistor_AKL.kicad_sym` | AKL PCM cached | 1 |
| `PCM_Transistor_MOSFET_AKL` | `PCM_Transistor_MOSFET_AKL.kicad_sym` | AKL PCM cached (2N6660 generic) | 1 |
| `OpenRX-Shared` | `OpenRX-Shared.kicad_sym` | OpenRX-Lite cached | 9 |

### Footprints
| Nickname | Directory | Source |
|---|---|---|
| `lib` | `lib.pretty/` | OpenFC-ECO base + 4in1ESC additions (164 fps) |
| `4in1ESC` | `4in1ESC.pretty/` | 4in1ESC 2 |
| `components` | `components.pretty/` | 4in1ESC 2 (mirror of 4in1ESC) |
| `footprint` | `footprint.pretty/` | 4in1ESC 2 (mirror of 4in1ESC) |
| `ESCLibrary` | `ESCLibrary.pretty/` | wearable_e-ink/JLC2KiCad_lib |
| `OpenRX-Shared` | `OpenRX-Shared.pretty/` | OpenRX/shared/libs |
| `PCM_Resistor_SMD_AKL` | `PCM_Resistor_SMD_AKL.pretty/` | AKL PCM install |
| `PCM_Package_TO_SOT_THT_AKL` | `PCM_Package_TO_SOT_THT_AKL.pretty/` | AKL PCM install |

### 3D models
- `lib.3dshapes/` — OpenFC-ECO + 4in1ESC additions
- `4in1ESC.3dshapes/` — matches paths inside 4in1ESC footprints
- `OpenRX-Shared.3dshapes/` — matches paths inside OpenRX-Lite footprints (rewritten from `../shared/libs/` → local)
- `JLC2KiCad_lib/footprint/packages3d/` — matches paths inside ESCLibrary footprints

## Known Issues (inherited from source designs)

### From OpenFC-ECO V0.3 — fix before first AIO spin
- **C28** (22 µF 0603 16V on +10V rail): voltage rating too low — change to 25V rated
- **R30** (6.8k): gives 9.42V not 10V — change to 6.34k (E96) for 10.06V output
- **L2** (4.7 µH): undersized for 10V rail at 6S input (116% ripple) — change to ~10 µH (FTC303020D100MBCA, C7423323)
- **D7 (LED0, green)**: Betaflight manufacturer guidelines §3.1.4.6 **require** LED0 to be blue
- **LMR51420** (2A): drop-in upgrade to LMR51430YFDDCR (C5219261) for 3A
- **Reverse-polarity protection**: not present in ECO, add for AIO
- **CRIT-2**: Motor pin numbering M1-M4 reversed vs BF OPENFC_RP2350B reference — fix in board config.h or swap J1-J4 labels
- **CRIT-3**: OSD FB_OSD 3-pin mapping at GPIO33/34/35 (consecutive, per BF PR#14882) — no upstream BF driver merged yet

### From 4in1ESC 2 — supply chain
- **NSG2065Q**: ~225 on LCSC. Footprint must stay FD6288Q-compatible so clone family (6288Q-MNS 9.9k stock) is drop-in
- **INA186A3IDCKR**: critically low stock. INA199A2 possible fallback (26V CM — tight at 6S nominal)
- **SP40N03GNJ**: 12k on LCSC, route via JLCPCB global sourcing for production runs

## Rules
- Be direct and critical — flag problems, skip praise.
- **Metadata yes, physical connections no.** Claude may edit *metadata* programmatically — KiCad text variables (`.kicad_pro`), symbol BOM/doc fields (MPN, Manufacturer, LCSC, Cost, BOM Comments, Datasheet, notes) — via kicad-skip or the pcbnew API. Claude must **never** change physical connections: nets, wiring, routing, placement, footprint assignments, or component values that alter the circuit. Those stay Stan's, done in KiCad.
- **NEVER raw-edit** `.kicad_sch`, `.kicad_pcb`, or `.kicad_pro` as text — use kicad-skip / the pcbnew API. (`.kicad_pro` is JSON; safe programmatic metadata edits there are fine.)
- Libraries are project-local: `lib.kicad_sym`, `lib.pretty/`, `lib.3dshapes/`, plus per-prefix shim libs
- KiCad standard libraries (`Device:`, `power:`, `Connector:`, `Package_SO:`, etc.) are external and NOT bundled
- Production exports go in `production/` via KiCad Fabrication Toolkit for JLCPCB
- JLCPCB assembly, prefer LCSC basic parts

## Firmware
- FC: Betaflight RP2350B (PICO platform) — target `OPENFC_RP2350B`
- ESC: AM32 AT32F421 target
- ELRS: `Unified_ESP32C3_2400_RX`
- All three targets already exist upstream — zero new firmware work required for V0.1

## Reference Docs
- `ALTERNATIVES.md` — gate driver and MOSFET alternatives (from 4in1ESC 2)
- `COST_ANALYSIS.md` — ESC BOM and supply chain notes (from 4in1ESC 2)
- Source repos: `../OpenFC-ECO/`, `../4in1ESC 2/`, `../OpenRX/`
- Archive of pre-port Jan 2026 OpenAIO state: `../OpenAIO-backup-jan2026/`
