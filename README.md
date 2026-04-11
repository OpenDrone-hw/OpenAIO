# OpenAIO

Open-source 25.5×25.5 mounting-pattern AIO (flight controller + 4-in-1 ESC) for toothpick-class 6S FPV drones. Target: 30 A continuous per channel at 6S.

Built by combining three existing projects:

- **[OpenFC-ECO](https://github.com/Just4Stan/OpenFC-ECO)** — RP2354B flight controller stage (IMU, OSD, power, blackbox, USB-C)
- **[4in1ESC](https://github.com/Just4Stan/OpenESC)** — AT32F421 + NSG2065Q + SP40N03GNJ ESC stage, AM32 firmware
- **[OpenRX-Lite](https://github.com/Just4Stan/OpenRX)** — ESP32-C3 + SX1281 2.4 GHz ExpressLRS receiver

Physical construction: two PCBs reflowed together via BGA-style solder pad bonding. FC stage is the top board, ESC stage is the bottom daughterboard, both fabricated in the same KiCad project.

## Firmware targets (already merged upstream)

| Stage | Target |
|---|---|
| FC (RP2354B) | Betaflight `OPENFC_RP2350B` (PICO platform) |
| ESC ×4 (AT32F421) | AM32 AT32F421 target |
| ELRS (ESP32-C3 + SX1281) | ExpressLRS `Unified_ESP32C3_2400_RX` |

## Repository layout

```
OpenAIO/
├── OpenAIO.kicad_pro
├── OpenAIO.kicad_sch         ← root sheet (to be created)
├── OpenAIO.kicad_pcb         ← both board outlines in one file
├── rp2350a.kicad_sch         ← FC MCU         (from OpenFC-ECO)
├── power.kicad_sch           ← FC power tree  (from OpenFC-ECO)
├── imu.kicad_sch             ← LSM6DSV16XTR   (from OpenFC-ECO)
├── osd.kicad_sch             ← PIO analog OSD (from OpenFC-ECO)
├── blackbox.kicad_sch        ← microSD slot   (from OpenFC-ECO)
├── pads.kicad_sch            ← connectors     (from OpenFC-ECO)
├── esc_main.kicad_sch        ← ESC power + sense (from 4in1ESC)
├── esc_channel.kicad_sch     ← single ESC channel, reused 4× (from 4in1ESC)
├── elrs.kicad_sch            ← ESP32-C3 + SX1281 (from OpenRX-Lite)
├── lib.kicad_sym             ← main merged symbol lib
├── components.kicad_sym      ← 4in1ESC components (ported)
├── ESCLibrary.kicad_sym      ← 4in1ESC legacy pre-valued passives (ported)
├── PCM_Resistor_AKL.kicad_sym
├── PCM_Transistor_MOSFET_AKL.kicad_sym
├── OpenRX-Shared.kicad_sym   ← OpenRX-Lite ELRS symbols (ported)
├── lib.pretty/               ← main footprint library
├── {4in1ESC,components,footprint,ESCLibrary,OpenRX-Shared,PCM_*}.pretty/
├── lib.3dshapes/             ← main 3D models
├── {4in1ESC,OpenRX-Shared}.3dshapes/
├── JLC2KiCad_lib/            ← legacy 3D packages (referenced by ESCLibrary footprints)
├── sym-lib-table
└── fp-lib-table
```

All libraries are project-local. No global or PCM dependencies.

## Key ICs

### FC stage (from OpenFC-ECO, V0.3 — known-good, prototype ordered)
| IC | Part | LCSC |
|---|---|---|
| MCU | RP2354B (QFN-80, 2 MB flash) | C39843328 |
| IMU | LSM6DSV16XTR | C5267406 |
| 5V Buck | LMR51420YFDDCR (upgrade to LMR51430 3A recommended) | C7296200 |
| 3.3V LDO | LP5912-3.3DRVR | C524780 |
| 1.8V Gyro LDO | NCV8187AMT180TAG | C893189 |
| 5V Power Mux | TPS2116DRLR | C3235557 |
| OSD sync-sep | TLV3201AIDBVR | C105188 |
| OSD buffer | TLV9061IDPWR | C2057878 |
| OSD mux | SN74LVC1G3157DTBR | C2673087 |
| SD card slot | TF-021B-H265 | C498185 |
| USB-C | TYPE-C16PQTWT | — |

### ESC stage (from 4in1ESC 2, 6-layer, 30.5×32.2 mm standalone, 35 A/ch rated)
| IC | Part | LCSC |
|---|---|---|
| ESC MCU ×4 | AT32F421G8U7 (ARM Cortex-M4, AM32) | C2765098 |
| Gate driver ×4 | NSG2065Q (FD6288Q-compatible footprint) | C41414478 |
| MOSFETs ×24 | SP40N03GNJ (40V 2.9 mΩ) | C22466709 |
| Buck | LMR51420YDDCR | C7296200 |
| LDO | TLV76733DRVR | C2848334 |
| CSA | INA186A3IDCKR | C2058245 |
| Shunt | 0.2 mΩ 2512 | C695806 |
| ESC output connector | SM08B-SRSS-TB | C160407 |

### ELRS stage (from OpenRX-Lite)
| IC | Part |
|---|---|
| MCU | ESP32-C3FH4 |
| Radio | SX1281IMLTRT (2.4 GHz) |
| BPF | 2450FM07D0034T |
| LDO | TLV75533PDQNR |
| Antenna | AOTA-B201610S3R3-101-T (ceramic) |

## Known issues inherited from source designs

From OpenFC-ECO V0.3 — fix before first AIO spin:
- **C28** (22 µF 0603 16V on +10V rail): voltage rating too low — change to 25V
- **R30** (6.8k): gives 9.42V not 10V — change to 6.34k (E96)
- **L2** (4.7 µH): undersized for 10V rail at 6S — change to ~10 µH (FTC303020D100MBCA)
- **LED0** (D7, green): Betaflight manufacturer guidelines §3.1.4.6 **require** LED0 to be blue
- **Reverse-polarity protection**: not present in ECO, add for AIO
- **LMR51420** (2A): drop-in upgrade to LMR51430YFDDCR (3A)

From 4in1ESC 2 — supply chain notes in `ALTERNATIVES.md` and `COST_ANALYSIS.md`:
- **NSG2065Q** stock is tight on LCSC (~225 units); FD6288Q-compatible clones available as drop-in
- **INA186A3IDCKR** stock critical; INA199A2 is a possible fallback (26V common-mode — tight at 6S)

## License

Hardware: [CERN-OHL-S-2.0](https://ohwr.org/cern_ohl_s_v2.txt).

Firmware references upstream projects under their respective licenses (Betaflight, AM32, ExpressLRS).
