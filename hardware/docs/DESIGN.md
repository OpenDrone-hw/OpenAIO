# OpenAIO Design Notes

Detailed design description of the OpenAIO. Values are extracted from the KiCad design files under `hardware/`.

## Architecture

Three stages merged from sibling OpenDrone designs into one hierarchical KiCad project:

| Stage | Source design | Status of source |
|---|---|---|
| FC | OpenFC-Lite-Mini rev 2 (RP2354A) | Rev 2 ordered |
| ESC | OpenESC-20x20 Rev 2 (20x20 AM32 4-in-1) | Rev 2 ordered |
| RX | OpenRX-Lite (ESP32-C3 + SX1281 ELRS 2.4 GHz) | All variants finalized |

The ESC stage uses the distributed-MCU AM32 topology: each of the four channels has its own AT32F421 MCU and NSG2065Q gate driver, with six MOSFETs per channel.

## Design state (2026-08-05)

Schematic sources were refreshed 2026-06-12 from the current sibling revisions, replacing the original 2026-04 port. Not yet complete:

- Root-sheet wiring: hierarchical sheets are imported but inter-stage signal routing (FC-ESC, FC-RX) is not finalized
- Schematic re-annotation: reference collisions across merged sheets and the 4x ESC channel instances
- PCB layout: the layout in `OpenAIO.kicad_pcb` predates the refresh. The committed board file carries a single ~33 x 33 mm outline with the 25.5 x 25.5 mounting pattern; the stacked two-board construction inherited from the original port (FC top, ESC bottom, bonded via solder pads) is not implemented in it, and the single-board vs stacked question is unresolved
- Gyro LDO: the power sheet still instantiates the NCV8187AMT180TAG, whose replacement (TPS7A2018PDQNR) was decided 2026-06-12 and imported into the `imports` library but not yet swapped in

## Schematic structure

Root sheet `hardware/OpenAIO.kicad_sch` instantiates:

| Sheet | File | Instances |
|---|---|---|
| RP2350, POWER, IMU, OSD, BLACKBOX, PADS | `hardware/schematics/fc/*.kicad_sch` | 1 each |
| ESC1-ESC4 | `hardware/schematics/esc/esc_channel.kicad_sch` | 4 |
| ELRS | `hardware/schematics/elrs/elrs.kicad_sch` | 1 |

`esc_main.kicad_sch` is the OpenESC-20x20 top sheet (buck, LDO, current sense, TVS, ESC connector) kept as reference circuitry; it is not instantiated by the root sheet. `ESC.kicad_sch` is a duplicate of `esc_channel.kicad_sch` that exists only so `esc_main`'s internal channel instances resolve if opened.

## Key ICs

### FC stage (OpenFC-Lite-Mini rev 2)

| Function | Part | LCSC |
|---|---|---|
| MCU | RP2354A (QFN-60, dual Cortex-M33, 2 MB flash, 30 GPIO) | C41378174 |
| IMU | LSM6DSV16XTR (LGA-14, SPI) | C5267406 |
| 10 V buck (switchable VTX rail) | LMR51430YFDDCR, 3 A | C5219261 |
| 5 V buck (always-on) | LMR51430YFDDCR, 3 A | C5219261 |
| 5 V power mux (USB/BATT) | TPS2116DRLR | C3235557 |
| 3.3 V LDO | LP5912-3.3DRVR | C524780 |
| 1.8 V gyro LDO | NCV8187AMT180TAG (replacement TPS7A2018PDQNR decided 2026-06-12, not yet in schematic) | C893189 |
| OSD sync comparator | TLV7031DPWR | C2876045 |
| OSD video op-amp | COS8051 (175 MHz RRIO) | C7463385 |
| OSD SPDT switch | SN74LVC1G3157DTBR | C2673087 |
| Blackbox | microSD slot TF-021B-H265 | C498185 |

### ESC stage (OpenESC-20x20 Rev 2, distributed-MCU AM32, 4 independent channels)

| Function | Part | LCSC |
|---|---|---|
| ESC MCU x4 | AT32F421G8U7 (QFN-28, Cortex-M4) | C2765098 |
| Gate driver x4 | NSG2065Q (FD6288Q-compatible footprint) | C41414478 |
| MOSFETs x24 | DOY180N03T (30 V, PowerDI3333-8) | C49441966 |
| Current sense | INA186A3IDCKR + 0.2 mOhm 2512 shunt | C2058245 / C695806 |
| Buck | LMR54406DBVR | C5219316 |
| LDO | TLV76733DRVR | C2848334 |
| Input TVS | SMF24A-T13 | C1977154 |

### RX stage (OpenRX-Lite)

| Function | Part |
|---|---|
| MCU | ESP32-C3FH4 |
| Radio | SX1281IMLTRT (2.4 GHz) |
| BPF | 2450FM07D0034T |
| LDO | TLV75533PDQNR |
| ELRS antenna | Molex 47948-0001 chip (Lite); U.FL variant possible |
| Wi-Fi antenna (OTA) | 2450AT18A100E ceramic chip |

## Libraries

Project-local libraries, per the committed lib tables:

| Library | Files | Origin |
|---|---|---|
| `lib` | `lib.kicad_sym` / `lib.pretty` / `lib.3dshapes` | FC (OpenFC-Lite-Mini rev 2) |
| `components`, `4in1ESC` | `components.kicad_sym` / `4in1ESC.pretty` / `4in1ESC.3dshapes` | ESC (OpenESC-20x20 Rev 2) |
| `OpenRX-Shared` | `OpenRX-Shared.kicad_sym` / `.pretty` / `.3dshapes` | RX (OpenRX shared) |
| `imports` | `imports.kicad_sym` / `.pretty` / `.3dshapes` | easyeda2kicad imports (TPS7A2018) |
| `Incutec` | `libs/KiCad-Library` submodule | Shared incutec library, used for new parts |

The ESC sheets (`esc_channel`, `ESC`, `esc_main`) still carry legacy footprint references from their source repo (`ESCLibrary:`, `PCM_Resistor_SMD_AKL:`, `PCM_Package_TO_SOT_THT_AKL:`, `PCM_Transistor_MOSFET_AKL:`, `footprint:`) that are not defined in the committed `fp-lib-table`. They must be remapped to the project-local or shared libraries before the layout is updated from the schematic.

## Firmware targets

| Stage | Target |
|---|---|
| FC | Betaflight, derived from `OPENFC_LITE_MINI_RP2350A` (custom target, `MANUFACTURER_ID = OPFC`); the AIO needs its own resource map |
| ESC x4 | AM32, AT32F421 target (flashed per channel) |
| RX | ExpressLRS `Unified_ESP32C3_2400_RX` (3.5.0 or later) |

## Supply chain

Primary reference: [docs/SOURCING-2026-06.md](../../docs/SOURCING-2026-06.md) (2026-06-12 stock snapshot, part risks, and decisions). Headline items from it:

- NCV8187AMT180TAG is effectively unobtainable; replacement TPS7A2018PDQNR decided, schematic swap pending
- DOY180N03T is not in the JLCPCB assembly library: consign, global-source, or revisit the MOSFET
- All parts are Extended for JLCPCB assembly; several are below 1k JLC stock

Historical snapshots of the pre-refresh ESC BOM: [docs/ALTERNATIVES.md](../../docs/ALTERNATIVES.md) (pin-compatible alternatives, 2026-03-14) and [docs/COST_ANALYSIS.md](../../docs/COST_ANALYSIS.md) (cost model, 2026-03-17). Still-valid notes from them:

- NSG2065Q: footprint stays FD6288Q-compatible, so the 6288Q clone family is drop-in
- INA186A3IDCKR: watch stock; the INA199A2 fallback has 26 V common-mode, tight at 6S

Market context: [docs/MARKET-RESEARCH-2026-06.md](../../docs/MARKET-RESEARCH-2026-06.md).

## Revisions

- **2026-08-04**: shared Incutec KiCad library wired in as the `libs/KiCad-Library` submodule.
- **2026-06-12**: schematic sources refreshed from the current sibling revisions (OpenFC-Lite-Mini rev 2, OpenESC-20x20 Rev 2, OpenRX-Lite); KiCad project moved under `hardware/`; TPS7A2018 gyro LDO replacement decided and imported into the `imports` library; sourcing and market research snapshots added.
- **2026-04-11**: initial port: root sheet, first ESC channel layout, project tree consolidated.
