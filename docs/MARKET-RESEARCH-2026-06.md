# FPV AIO Competitive Landscape — June 2026

Research for the two OpenDrone AIOs: **OpenAIO** (toothpick, 25.5×25.5, 6S, AM32, onboard ELRS) and **OpenAIO-Whoop** (1-2S, Bluejay, digital-only). Web research with adversarial verification against primary sources (DJI manuals, GitHub APIs, manufacturer manuals), 2026-06-12.

## Toothpick class (25.5×25.5, 3-6S, 30-55 A)

| Board | MCU / Gyro | ESC | RX | Blackbox | Weight | Price |
|---|---|---|---|---|---|---|
| **HDZero Gamma 45A** | G473 / — | 45A/60A AM32, 3-6S | **onboard serial ELRS 2.4G** | — | 8.4 g | $89.99 |
| Airbot Fenix G4 | G473 / ICM-42688P | 35A/45A AM32 (QF32MTF4AK8U7 = AT32F421+ID6288 chiplet) | none | 16 MB | — | $89.99 |
| Holybro Kakute AIO G473 | G473 / ICM-42688P | 35A AM32, 4× discrete MCUs | none | 16 MB | 7.5 g | ~$90 |
| Flywoo GOKU GN745 V3 | F745 / MPU6000 or ICM42688 | 45A AM32 | none (pads) | 16 MB | 9.4 g | $89.99 |
| GEPRC TAKER F722 45A | F722 / ICM-42688P | 45A/55A BLHeli_32 (EOL fw) | none | 16 MB | 9.2 g | $79.99 |
| iFlight BLITZ Whoop F7 55A | F745 / ICM42688 or BMI270 | 55A/65A Bluejay | none | 16 MB | 10.5 g | $116-141 |
| Foxeer Reaper AIO V4 | F745 / MPU6000 | 45A/50A BLHeli_S (Bluejay-flashable) | none | 16 Mb | 8.6 g | $99.99 |
| BetaFPV F722 35A V2 | F722 / ICM42688 | 35A/40A BLHeli_32 on AT32F421 | none | — | ~7 g | $51-114 |
| SpeedyBee F745 35A | F745 / MPU6000 | 35A/45A BLHeli_S | none | 8 MB | 10.1 g | $115.99 |
| Diatone Mamba MK5 G4 | G473 / IIM-42652 | 40A/45A BLHeli_32 | none | — | — | $79.99 |
| HGLRC Specter 25A | F722 / MPU6000 | 25A Bluejay | none | 16 MB | 12.05 g | — |

**Class structure mid-2026:** converged on G4/F7 FC + AT32F421-class ESC MCUs running AM32, 35-45 A, 25.5×25.5 Φ3 mm + M2 grommets, 16 MB flash, ICM-42688P, dual 5V/9-10V BEC, $80-100. Legacy boards stranded on EOL BLHeli_32 or 8-bit BLHeli_S.

**Direct competitor for OpenAIO: HDZero Gamma 45A** — the only 6S AIO with onboard serial ELRS. Digital-HD-only, single board, closed source, G473. OpenAIO's differentiators against it: analog PIO-OSD option, microSD blackbox (nobody has SD in class), open hardware, RP2350 (also a platform-maturity risk).

## Whoop class (1-2S)

| Board | Mount | MCU / Gyro | ESC | RX | VTX | Weight | Price |
|---|---|---|---|---|---|---|---|
| BetaFPV Air 5in1 (Air65/75) | 26×26 M1.4 | G473 / ICM42688P | 5A BB51 Bluejay 96k | serial ELRS | 400 mW analog | 2.9 g | $44.99 |
| **BetaFPV Matrix 1S 5IN1 II** | 26×26 | G473 / ICM42688P | **12A/18A BB51 Bluejay** | serial ELRS | 400 mW | ~3.5 g | $54.99 |
| **BetaFPV Matrix 1S 3IN1 HD** | 26×26 | G473 / ICM42688P | 12A/18A Bluejay | serial ELRS | **none — SH1.0 6-pin O4 port, 5V/3A BEC** | 3.2 g | ~$50 |
| BetaFPV F4 2-3S 20A (Pavo Pico) | 26×26 | F405 / ICM42688P | 20A/25A Bluejay | serial ELRS | none; 9V/2A + 5V/3A, O4 plug | 5.6 g | $54.99 |
| Happymodel X12 / Pro | 25.5×25.5 | F411 / lottery | 12A/15A | SPI / serial (Pro) | OpenVTX 400 mW | 5.1 g | $45-75 |
| Happymodel X14 | 25.5×25.5 | **G473 / LSM6DSV16X** | 12A/15A Bluejay | serial ELRS + WiFi | OpenVTX 400 mW | ~5 g | — |
| NewBeeDrone BeeBrain BLV5 | 25.5×25.5 | G474 / MPU6000 | **18A double-NMOS** Bluejay | serial ELRS **diversity** + TCXO | 400 mW | 5.8 g | $99 |
| NBD Hummingbird RaceSpec V2 | 25.5×25.5 | AT32F435 / ICM42688 | 18A Bluejay | serial ELRS | 400 mW | 4.71 g | $59.99 |
| GEPRC TAKER F411-12A-E | 25.5×25.5 M2 | F411 / ICM42688P | 12A/13A | serial ELRS | none | 4.2 g | $59.99 |
| Flywoo GOKU Versatile F405 | 25.5×25.5 | F405 / ICM42688 + baro | 12A Bluejay | serial ELRS | 400 mW | 4.6 g | $125.99 |

Notes: BetaFPV FC mount stays 26×26 M1.4 through the Matrix II generation (verified); everyone else is 25.5×25.5. Reference target for OpenAIO-Whoop: **Matrix 1S 3IN1 HD**.

## User pain points (ranked)

1. **SPI ELRS = designed-in obsolescence** — version-locked to BF, ELRS-4 incompatible today. Every 2024+ design is serial.
2. **F411 UART starvation** — structural reason F411 AIOs are legacy; vendors mislabel softserial as "FULL UARTS".
3. **Lifted motor/battery pads** during repair — mitigations users praise: through-hole-reinforced pads, motor plugs, big thermal-relieved battery pads.
4. **ESC burnout totals the whole AIO** — core economic argument against integration; per-channel SWD rescue pads help.
5. **O4-Lite-on-1S brownouts** — an entire aftermarket boost-BEC market exists (Flywoo O4 1S module, Fractal Boostybaby).
6. **Current sensing absent (1S) or miscalibrated** (factory scale off 2×).
7. **No/undersized blackbox** — 8 MB ≈ one flight; 16 MB is the bare minimum for tuning.
8. **USB ripping off** — anchor it through-hole, keep clear of frame rails.
9. **Betaflight target abandonment** + silent hardware revisions ("gyro lottery").
10. **Connector chaos** — same shells, different pinouts; silkscreen rail voltages at every plug.
11. **Mounting/grommet chaos** — 25.5/26/26.5 + M1.4/M2 mix; size holes to accept both grommet types.
12. **Zero open documentation** — no vendor publishes schematics.

## Verified trends 2025-2026

- 1S stays the 65/75 mm standard; 2S is the 85 mm tier. ESC headroom moved 5A → 12A/18A-peak even on 65 mm 1S. **12 A is the new whoop floor.**
- Digital-only "3in1/HD" whoop boards are the inflection. O4 Air Unit Lite: 6-pin SH1.0 (VCC/GND/RX/TX/GND/SBUS), no solder pads, 3.7-13.2 V, ~6 W @ 700 mW; DJI recommends ≥10 W BEC (5V/2A class) for the Lite.
- **ELRS 4.0.0** (2026-02-06): OTA-incompatible with 3.x, STM32 RX dropped; `Unified_ESP32C3_2400_RX` survives in 4.0 targets (verified).
- **BLHeli_32 dead** (June 2024). AM32 owns 32-bit; Bluejay on EFM8 BB51 (48/96 kHz) owns sub-20A whoop tier.
- **Betaflight on RP2350**: landed in 2025.12; PIO bidir DShot + PIO UARTs merged; open issues on I2C/SPI and PWM. Budget bring-up time; pin to a tested release.
- Gyros: ICM-42688-P mainstream; **LSM6DSV16X now shipping on Happymodel latest revs** — validates the family gyro choice.
- **Open-source landscape effectively empty** — no open-hardware Betaflight AIO has shipped. First-mover position intact for both boards.

## Conventions / targets

- Battery 1S: BT2.0 (9 A cont) or GNB A30; PH2.0 legacy; XT30 at 2S+. Soldered pigtail to pads, not board socket.
- Motor plugs: JST/Molex 1.25 mm 3-pin standard (PicoBlade).
- Weight bars: 1S AIO 2.9-3.6 g; 2S 12-20A ≈ 5-6 g; 6S 35-45A AIO 7.5-10 g (Gamma 8.4 g → OpenAIO stack should target ≤9 g combined).
- BF config: ship measured current-sensor scale + vbat_scale in the target config.h.
- Price bands: toothpick AM32 AIO $80-100; 1S serial-ELRS AIO $45-75; premium (diversity/18A) $99.

## Differentiation summary

**OpenAIO (vs HDZero Gamma):** open hardware + published schematics/repair diagrams, microSD blackbox, analog OSD option, honest measured current ratings, per-channel SWD rescue pads, maintained BF target every release cycle.

**OpenAIO-Whoop (vs Matrix 3IN1 HD):** open hardware, 64 Mbit+ blackbox flash (most 1S boards have none), real shunt + published current scale, ELRS antenna options, guaranteed-updated target. Must match: 12 A Bluejay BB51, 5V/3A to 2.8 Vin, SH1.0 6-pin O4 port, 25.5×25.5, ≤3.5 g.
