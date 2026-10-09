# OpenAIO pinout

Source: `kicad-cli sch export netlist` of `hardware/OpenAIO.kicad_sch` at OpenAIO `be152bb` (branch `work/d81e559`).

The pad nets of `OpenAIO-Core.kicad_pcb` and `OpenAIO-Base.kicad_pcb` match the netlist:
- J91 (Core LGA pads) and J90 (Base land) carry the same net on all 46 pads.
- U2, U22, U13, Card1 and U12 match pad for pad.

`config.h` was checked pin by pin against this netlist by script: 29 of 29 pins match.

**Reading the tables**
- **LGA** is the J91/J90 pad number. "Core" means the net stays on the Core.
- **Core parts** are on the Core PCB and **Base endpoint** on the Base PCB. Board membership comes from the reference lists of the two PCB files.
- Parts in the schematic but on neither PCB (TP10, TP12, TP13, TP15-TP30, TP41, J19, J22, J46, J47) are DNP or excluded from the board, and are left out.

## RP2354A (U2, Core)

| GPIO | U2 pin | Net | LGA | Core parts | Base endpoint | Firmware function (`config.h`) |
|---|---|---|---|---|---|---|
| 0 | 2 | `UART0_TX` | 38 | J49 "TX0" | U12.3 (SH-6 pin 3) | **PIOUART0 TX**: MSP DisplayPort to the digital VTX |
| 1 | 3 | `UART0_RX` | 39 | J48 "RX0" | U12.4 (SH-6 pin 4) | **PIOUART0 RX** |
| 2 | 4 | `/Pads/PIOUART0_TX` | Core | J44 "PIO_TX0" | none | **UART0 TX** (F11 UART_AUX) |
| 3 | 5 | `PU0RX` | 40 | J45 "PIO_RX0" | U12.6 (SH-6 pin 6) | **UART0 RX** (F11 UART_AUX): SBUS from the air unit, or a GPS on J44/J45. See ISSUES I1 |
| 4 | 7 | `/Pads/I2C0.SDA` | Core | J26 "SDA", R12 5.1k to +3.3V | none | I2C0 SDA (external mag or baro) |
| 5 | 8 | `/Pads/I2C0.SCL` | Core | J23 "SCL", R11 5.1k to +3.3V | none | I2C0 SCL |
| 6 | 9 | `UART1_TX` | 33 | J54 "TX1" | U22.27 U0RXD (ESP32-C3 GPIO20) | **UART1 TX** (F11 UART_AUX): CRSF to ELRS |
| 7 | 10 | `UART1_RX` | 25 | J55 "RX1" | U22.28 U0TXD (ESP32-C3 GPIO21) | **UART1 RX** (F11 UART_AUX): CRSF from ELRS, `SERIALRX_UART` |
| 8 | 12 | `/RP2354A/LED_STRIP_L` | 46 as `LED_STRIP` | Q2 AP1606 gate. Q2 drain = `LED_STRIP` with R14 2.4k to +5V. TXU0101 + 200R planned | J20, J21, J31, J32 "LED" | LED_STRIP, WS2812 on PIO1. Inverted by Q2 today (ISSUES I2) |
| 9 | 13 | `/IMU/GYRO_INT` | Core | U8.4 INT1 | none | GYRO_1_EXTI |
| 10 | 14 | `/IMU/SPI1.SCK` | Core | U8.13 SCx | none | SPI1 SCK |
| 11 | 15 | `/IMU/SPI1.MOSI` | Core | U8.14 SDx | none | SPI1 SDO |
| 12 | 16 | `/IMU/SPI1.MISO` | Core | U8.1 SDO | none | SPI1 SDI |
| 13 | 17 | `/IMU/CS` | Core | U8.12 CSB, R25 10k to +3.3V | none | GYRO_1_CS |
| 14 | 18 | `/OSD/OSD_W` | Core | R27 3.9k to `/OSD/OSD_LVL` (U9.1 B2) | none | OSD_W (PIO2) |
| 15 | 19 | `/OSD/OSD_EN` | Core | U9.6 S (SN74LVC1G3157). Low selects B1 = `VIDEO_IN` | none | OSD_EN (PIO2) |
| 16 | 27 | `/OSD/OSD_SYNC` | Core | U11.1 TLV7031 OUT | none | OSD_SYNC (PIO2 input) |
| 17 | 28 | `/RP2354A/BEEPER` | 34 as `BUZZER-` | Q1 AP1606 gate, R13 100k to GND | J29 "BUZ-" (J33 "BUZ+" = +5V) | BEEPER, `BEEPER_INVERTED` (high = on) |
| 18 | 29 | `SPI0.SCK` | 12 | none | Card1.5 CLK | SPI0 SCK |
| 19 | 31 | `SPI0.MOSI` | 13 | none | Card1.3 CMD | SPI0 SDO |
| 20 | 32 | `SPI0.MISO` | 17 | none | Card1.7 DAT0 | SPI0 SDI |
| 21 | 33 | `FLASH_CS` | 29 | none | Card1.2 CD/DAT3, R34 10k to +3V3 | SDCARD_SPI_CS. The name is historical: this is the SD card CS |
| 22 | 34 | `MOTOR4` | 21 | none | R96 220R to U19.25 PB4 (ESC4) | MOTOR 4, DShot on PIO0 |
| 23 | 35 | `MOTOR3` | 19 | none | R77 220R to U17.25 PB4 (ESC3) | MOTOR 3 |
| 24 | 36 | `MOTOR2` | 23 | none | R58 220R to U15.25 PB4 (ESC2) | MOTOR 2 |
| 25 | 37 | `MOTOR1` | 24 | none | R39 220R to U13.25 PB4 (ESC1) | MOTOR 1 |
| 26 | 40 | `/RP2354A/LED0` | Core | R15 75R + R16 75R to D1 (blue), cathode to GND | none | LED0, `LED0_INVERTED` (active high) |
| 27 | 41 | unconnected | none | none | none | Free (ADC1). See ISSUES I5 and I6 |
| 28 | 42 | `/RP2354A/ESC_CURR` | 8 as `CURR` | R5 1k + C9 100n | U25.6 INA186A3 OUT | ADC_CURR (ADC2), `ibat_scale` 200 |
| 29 | 43 | `/RP2354A/ADC_VBAT` | 36 as `+BATT` | R1 100k from +BATT, R2 10k to GND, C2 100n | +BATT | ADC_VBAT (ADC3), `vbat_scale` 110 |
| SWCLK | 24 | `SWCLK` | 20 | none | TP32 (Base B.Cu) | SWD |
| SWDIO | 25 | `SWDIO` | 10 | none | TP31 (Base B.Cu) | SWD |
| USB_DM | 51 | via R8 30R to `USB_D-` | 37 | R8 | USB1 A7/B7 | USB |
| USB_DP | 52 | via R9 30R to `USB_D+` | 42 | R9 | USB1 A6/B6 | USB. No VBUS sense GPIO |
| QSPI_SS | 60 | via R7 1k | Core | U1 BOOTSEL button to GND | none | BOOTSEL |
| RUN | 26 | +3.3V | Core | none | none | none |

**Peripheral blocks**
- SPI1: 10/11/12 is SCK/TX/RX.
- SPI0: 18/19/20 is SCK/TX/RX.
- I2C0: 4/5 is SDA/SCL.
- UART1 TX/RX on 6/7 is function F11.
- UART0 TX/RX on 2/3 is function F11.
- These pins are taken from the RP2350 function table (RP2350.pdf p19) and the Betaflight pin tables cited in `config.h`.
- The QFN-60 pin numbers come from RP2350.pdf p16.

**PIO allocation**
- PIO0: DShot, 4 SMs, 29/32 instructions.
- PIO1: PIOUART0 (2 SMs) and the LED strip (1 SM), 23/32 instructions.
- PIO2: framebuffer OSD alone, 31/32 instructions. The sync-detect program (25) is loaded first, then swapped out.

### LGA power and ground

| Pads | Net |
|---|---|
| 3, 4 | +4v5. Base: D2 from +5V, D3 from USB VBUS. Feeds the Core LDOs U7 and U6 and the Base LDO U23 |
| 6, 22 | +5V (Base buck U4) |
| 36 | +BATT (VBAT divider on the Core) |
| 1, 2, 5, 7, 9, 11, 14, 15, 16, 18, 26, 27, 28, 30, 31, 32, 35, 41, 43, 44, 45 | GND (21 pads) |

### Motor pads (Base, U24 AIO_outline footprint)

| ESC | MCU | Firmware | Phase nets | U24 symbol pin names | Pad group position, KiCad top view (U24 at 75.37, 60.91) |
|---|---|---|---|---|---|
| ESC1 | U13 | MOTOR1, GPIO25 | `/1A /1B /1C` | 4A 4B 4C (pins 12-14) | left edge, lower half (x = -17, y = +1.2 to +10.5) |
| ESC2 | U15 | MOTOR2, GPIO24 | `/2A /2B /2C` | 3B 3C 3A (pins 15-17) | bottom edge, left half (y = +17, x = -10.4 to -1.2) |
| ESC3 | U17 | MOTOR3, GPIO23 | `/3C /3B /3A` | 2A 2C 2B (pins 18-20) | top edge, right half (y = -17, x = +1.2 to +10.6) |
| ESC4 | U19 | MOTOR4, GPIO22 | `/4C /4B /4A` | 1C 1B 1A (pins 21-23) | right edge, upper half (x = +17, y = -10.5 to -1.2) |

The other Base features, by position:
- Battery pads at the top edge.
- SH-6 (U12) at the bottom edge.
- USB-C at the left edge.

Two consequences:
- The symbol pin names number the motors in reverse of the ESC/MOTOR nets.
- Betaflight motor order must be set at bring-up (ISSUES I7).

## ELRS receiver (Base): ESP32-C3FH4 (U22) + SX1281 (U21)

ESP32-C3 pins come from ESP32-C3FH4.pdf p14 (pin list) and p17-18 (GPIO numbers). The hardware JSON is `RX/Generic C3 2400.json` in ExpressLRS/targets `42ed776a`.

| ESP32-C3 pin | GPIO | Net | Connects to | `Generic C3 2400.json` key | Match |
|---|---|---|---|---|---|
| 27 U0RXD | 20 | `UART1_TX` | RP2354A GPIO6 via LGA 33 | `serial_rx: 20` | yes |
| 28 U0TXD | 21 | `UART1_RX` | RP2354A GPIO7 via LGA 25 | `serial_tx: 21` | yes |
| 5 XTAL_32K_N | 1 | `/RX/DIO1` | U21.8 DIO1 | `radio_dio1: 1` | yes |
| 6 GPIO2 | 2 | `/RX/RST` | U21.3 NRESET, R111 10k to +3V3 (strap GPIO2 = 1) | `radio_rst: 2` | yes |
| 8 GPIO3 | 3 | `/RX/BUSY` | U21.7 BUSY | `radio_busy: 3` | yes |
| 9 MTMS | 4 | `/RX/MOSI` | U21.17 MOSI | `radio_mosi: 4` | yes |
| 10 MTDI | 5 | `/RX/MISO` | U21.16 MISO | `radio_miso: 5` | yes |
| 12 MTCK | 6 | `/RX/SCK` | U21.18 SCK | `radio_sck: 6` | yes |
| 13 MTDO | 7 | `/RX/NSS` | U21.19 NSS | `radio_nss: 7` | yes |
| 14 GPIO8 | 8 | `/RX/LED` | D9.4 DIN (XL-1010RGBC WS2812, GRB), R112 10k to +3V3 (strap GPIO8 = 1) | `led_rgb: 8`, `led_rgb_isgrb: true` | yes |
| 15 GPIO9 | 9 | `/RX/BOOT` | TP9 "BOOT" pad, R113 10k to +3V3 (strap: low = download) | `button: 9` | yes |
| 7 CHIP_EN | none | `/RX/CHIP_EN` | R114 10k to +3V3, C84 1 uF to GND (RC only) | none | none |
| 16 GPIO10 | 10 | GND | tied to ground | not used | harmless (ISSUES I12) |
| 4 XTAL_32K_P | 0 | NC | none | not used | none |
| 25, 26 | 18, 19 (USB) | NC | no native-USB flashing | none | none |
| 19-24 | SPI flash pins | NC | FH4 in-package flash | none | none |
| 1 LNA_IN | none | via L7 to `/RX/WIFI` | AE2 2.4 GHz chip antenna (WiFi only) | none | none |

**SX1281 (U21)**
- Signal pins are as in the table above.
- DIO2 (9) and DIO3 (10) are NC. XTB (6) is NC.
- XTA (4): OSC1 52 MHz oscillator, AC-coupled through C69.
- RFIO (22): FL1 band-pass, then JP1 u.FL. The ELRS antenna is external.
- DC-DC is fitted:
  - L4 15 uH runs from DCC_SW (14) to DCC_FB (12).
  - VDD_IN (2) is on DCC_FB, as the datasheet requires (SX1281.pdf p17).
  - So the optional `radio_dcdc` overlay is valid (`elrs.md`).
- Supply: +3V3 from U23 (TLV75533, fed by +4v5).

## ESC MCUs (Base): AT32F421G8U7 x4 (U13, U15, U17, U19), identical wiring

The AM32 groups are defined in `Inc/targets.h` of AM32 `50234143`:
- `HARDWARE_GROUP_AT_B`: lines 4889-4922.
- `HARDWARE_GROUP_AT_045`: lines 5101-5105.

| AT32 pin | Port | Net (ESC1 shown) | Connects to | AM32 macro | Match |
|---|---|---|---|---|---|
| 25 | PB4 | `Net-(U13-PB4)` | 220R (R39/R58/R77/R96) to `MOTORn` to RP2354A | `INPUT_PIN` PB4, TMR3_CH1 | yes |
| 20 | PA10 | `/ESC1/AH` | U14.22 HIN1 (NSG2065Q) | `PHASE_A_GPIO_HIGH` PA10 | yes |
| 15 | PB1 | `/ESC1/AL` | U14.1 LIN1 | `PHASE_A_GPIO_LOW` PB1 | yes |
| 19 | PA9 | `/ESC1/BH` | U14.23 HIN2 | `PHASE_B_GPIO_HIGH` PA9 | yes |
| 14 | PB0 | `/ESC1/BL` | U14.2 LIN2 | `PHASE_B_GPIO_LOW` PB0 | yes |
| 18 | PA8 | `/ESC1/CH` | U14.24 HIN3 | `PHASE_C_GPIO_HIGH` PA8 | yes |
| 13 | PA7 | `/ESC1/CL` | U14.3 LIN3 | `PHASE_C_GPIO_LOW` PA7 | yes |
| 6 | PA0 | `/ESC1/FBA` | phase A via 10k, 1k to GND | `PHASE_A_COMP` PA0 | yes |
| 10 | PA4 | `/ESC1/FBB` | phase B via 10k, 1k to GND | `PHASE_B_COMP` PA4 | yes |
| 11 | PA5 | `/ESC1/FBC` | phase C via 10k, 1k to GND | `PHASE_C_COMP` PA5 | yes |
| 7 | PA1 | `/ESC1/FBCOMMON` | virtual neutral, 3 x 10k from FBA/FBB/FBC | comparator common, set analog in `Mcu/f421/Src/peripherals.c:77` | yes |
| 21 | PA13 | SWDIO | TP1 / TP3 / TP5 / TP7 | SWD (never remapped by AM32) | none |
| 22 | PA14 | SWCLK | TP2 / TP4 / TP6 / TP8 | SWD | none |
| 1 | BOOT0 | none | 10k to GND (R38/R57/R76/R95) | none | none |
| 4 | NRST | none | 10k to +3V3 + 100n to GND. **Not on a test pad** | none | none |
| 5, 17 | VDDA, VDD | none | VDDA via 10R + 100n. VDD = +3V3 from U23 | none | ISSUES I3 |
| 8, 9, 12, 23, 24, 26-28, 2, 3 | PA2, PA3, PA6, PA15, PB3, PB5-7, PF0, PF1 | NC | none | PA3/PA6 are the voltage and current sense pins on other targets. OPENESC sets `NO_VOLTAGE_SENSE` and `NO_CURRENT_SENSE` | no ESC-level sense |

**ESC current sense:** none per ESC. The only current sense is the board-level INA186A3 (U25) into RP2354A GPIO28.
