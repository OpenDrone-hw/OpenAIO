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
- PCB layout: the layout in `OpenAIO.kicad_pcb` predates the refresh, so it does not match the current schematic. The committed board file carries a single 33.0 x 33.0 mm outline with the 25.5 x 25.5 mounting pattern; the stacked two-board construction inherited from the original port (FC top, ESC bottom, bonded via solder pads) is not implemented in it, and the single-board vs stacked question is unresolved. The board also still places the pre-refresh FETs: 24x SP40N03GNJ on `POWERPAK-1212-8` (3.0 x 3.0 mm), against the schematic's DOY180N03T on `Package_SON:Diodes_PowerDI3333-8` (3.3 x 3.3 mm). All 24 land patterns change when the layout is redone
- Gyro LDO and RX MCU part swaps are listed in the Key ICs tables below
- Stale symbol metadata: the six DOY180N03T symbols in `esc_channel.kicad_sch` still carry the SP40N03GNJ Description string ("2.9mOhm@10V ... 40V 55W 75A ... PDFN-8L(3x3)") from the pre-refresh BOM, while Value, MPN and LCSC on the same symbols are DOY180N03T / C49441966. That string contradicts the symbol's own PowerDI3333-8 footprint and is exported into BOM description columns, so JLCPCB would receive a 40 V part spec. Rewrite it from the DOY180N03T datasheet, in the GUI or via kicad-skip, and apply the same change to the `ESC.kicad_sch` copy

## Schematic structure

Root sheet `hardware/OpenAIO.kicad_sch` instantiates:

| Sheet | File | Instances |
|---|---|---|
| RP2350, POWER, IMU, OSD, BLACKBOX, PADS | `hardware/schematics/fc/*.kicad_sch` | 1 each |
| ESC1-ESC4 | `hardware/schematics/esc/esc_channel.kicad_sch` | 4 |
| ELRS | `hardware/schematics/elrs/elrs.kicad_sch` | 1 |

`esc_main.kicad_sch` is the OpenESC-20x20 top sheet (buck, LDO, current sense, TVS, ESC connector) kept as reference circuitry; it is not instantiated by the root sheet. `ESC.kicad_sch` is a byte-for-byte duplicate of `esc_channel.kicad_sch` that exists only so `esc_main`'s internal channel instances resolve if opened. Any edit to the channel sheet has to be applied to both copies or they drift; delete `ESC.kicad_sch` if `esc_main` is dropped.

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
| 1.8 V gyro LDO | NCV8187AMT180TAG. Replacement TPS7A2018PDQNR decided 2026-06-12, symbol imported into the `imports` library, schematic swap still pending. Rationale and PSRR comparison: [SOURCING-2026-06.md](../../docs/SOURCING-2026-06.md) | C893189 |
| OSD sync comparator | TLV7031DPWR | C2876045 |
| OSD video op-amp | COS8051 (175 MHz RRIO) | C7463385 |
| OSD SPDT switch | SN74LVC1G3157DTBR | C2673087 |
| Blackbox | microSD slot TF-021B-H265 | C498185 |

### ESC stage (OpenESC-20x20 Rev 2, distributed-MCU AM32, 4 independent channels)

| Function | Part | LCSC | Where |
|---|---|---|---|
| ESC MCU x4 | AT32F421G8U7 (QFN-28, Cortex-M4) | C2765098 | `esc_channel` |
| Gate driver x4 | NSG2065Q (FD6288Q-compatible footprint) | C41414478 | `esc_channel` |
| MOSFETs x24 | DOY180N03T (30 V, PowerDI3333-8) | C49441966 | `esc_channel` |
| Current sense | INA186A3IDCKR + 0.2 mOhm 2512 shunt, 100 V/V gain | C2058245 / C695806 | root sheet |
| Buck | LMR54406DBVR | C5219316 | `esc_main`, reference only |
| LDO | TLV76733DRVR | C2848334 | `esc_main`, reference only |
| Input TVS | SMF24A-T13 | C1977154 | `esc_main`, reference only |

The three `esc_main` parts are not in the instantiated design: `esc_main.kicad_sch` is reference circuitry that the root sheet does not pull in, so an exported BOM will not contain the ESC buck, the ESC LDO or the input TVS. Either add them to the root sheet or accept that the ESC stage runs off the FC bucks. Unresolved, needs a decision before the layout is redone.

### RX stage (OpenRX-Lite)

| Function | Part |
|---|---|
| MCU | intended ESP32-C3FH4 (C2858491); the sheet currently instantiates the generic `MCU_Espressif:ESP32-C3` symbol with no MPN or LCSC field, see below |
| Radio | SX1281IMLTRT (2.4 GHz) |
| BPF | 2450FM07D0034T |
| LDO | TLV75533PDQNR |
| ELRS antenna | Molex 47948-0001 chip (Lite); U.FL variant possible |
| Wi-Fi antenna (OTA) | 2450AT18A100E ceramic chip |

U1 on `elrs.kicad_sch` is the stock KiCad `MCU_Espressif:ESP32-C3` symbol, footprint `Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm`, and it carries neither an MPN nor an LCSC property. C2858491 does not appear in any committed schematic; it exists only in the `OpenRX-Shared` library and in the stale PCB. The plain ESP32-C3 has no in-package flash while the FH4 has 4 MB, so this is a functional difference, not just a BOM label. Fix before export: swap U1 to the `OpenRX-Shared:ESP32-C3FH4` symbol, or add MPN and LCSC fields to the existing one.

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

Single reference for stock, part risks and sourcing decisions: [docs/SOURCING-2026-06.md](../../docs/SOURCING-2026-06.md) (2026-06-12 snapshot). Read it before ordering anything; the risks and the open action items are not repeated here.

Component alternatives for the ESC stage, covering the gate-driver clone family, MOSFET options, the ESC MCU and the current-sense-amp fallbacks: [docs/ALTERNATIVES.md](../../docs/ALTERNATIVES.md) (2026-03 snapshot of the pre-refresh ESC BOM; its stock and price figures are superseded by SOURCING).

Market context: [docs/MARKET-RESEARCH-2026-06.md](../../docs/MARKET-RESEARCH-2026-06.md).

## Revisions

- **2026-08-06**: docs pass. Statements that disagreed with the design files corrected (esc_main parts not instantiated, RX MCU symbol, FET land pattern, JLCPCB Basic passives). `docs/COST_ANALYSIS.md` retired: its cost model described a 30.5 x 32.2 mm board whose top three cost drivers are not in this design; its MCU, current-sense-amp, buck and passive research moved into `docs/ALTERNATIVES.md`. Recover the cost model from git history if needed.
- **2026-08-04**: shared Incutec KiCad library wired in as the `libs/KiCad-Library` submodule.
- **2026-06-12**: schematic sources refreshed from the current sibling revisions (OpenFC-Lite-Mini rev 2, OpenESC-20x20 Rev 2, OpenRX-Lite); KiCad project moved under `hardware/`; TPS7A2018 gyro LDO replacement decided and imported into the `imports` library; sourcing and market research snapshots added.
- **2026-04-11**: initial port: root sheet, first ESC channel layout, project tree consolidated.
