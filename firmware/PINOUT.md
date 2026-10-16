# OpenAIO pinout

Source: `kicad-cli sch export netlist` of `hardware/OpenAIO.kicad_sch` and the pad nets of
`hardware/OpenAIO.kicad_pcb`. Firmware column: `firmware/betaflight/configs/OPENAIO/config.h`. All 30 GPIO
assignments in `config.h` match the netlist net for net.

Parts in the schematic but not on the board (excluded from the PCB): TP10, TP12, TP13, TP15 to TP30, TP41, J19, J22,
J46, J47. They are left out below unless they change a net.

## RP2354A (U2)

| GPIO | U2 pin | Net | Endpoint | Firmware function (`config.h`) |
|---|---|---|---|---|
| 0 | 2 | `UART0_TX` | U12.3 (SH-6 pin 3), J49 | PIOUART0 TX: MSP DisplayPort to the digital VTX |
| 1 | 3 | `UART0_RX` | U12.4 (SH-6 pin 4), J48 | PIOUART0 RX |
| 2 | 4 | `/Pads/PIOUART0_TX` | J44 | UART0 TX (F11 UART_AUX) |
| 3 | 5 | `/Pads/PU0RX` | J45 | UART0 RX (F11 UART_AUX) |
| 4 | 7 | `/Pads/I2C0.SDA` | J26, U26.4 (BMP580), R12 5.1k to +3.3V | I2C0 SDA |
| 5 | 8 | `/Pads/I2C0.SCL` | J23, U26.2, R11 5.1k to +3.3V | I2C0 SCL |
| 6 | 9 | `UART1_TX` | U22.27 (ESP32-C3 GPIO20, U0RXD), J54 | UART1 TX: CRSF to the onboard ELRS |
| 7 | 10 | `UART1_RX` | U22.28 (ESP32-C3 GPIO21, U0TXD), U12.6 (SH-6 pin 6), J55 | UART1 RX: CRSF from the onboard ELRS (`SERIALRX_UART`) |
| 8 | 12 | `/RP2354A/LED_STRIP_L` | Q2 gate (Q2 drain is `LED_STRIP`, R14 2.4k to +5V) | LED_STRIP, WS2812 on PIO1, inverted by Q2 (ISSUES I2) |
| 9 | 13 | `/IMU/GYRO_INT` | U8.4 INT1 | GYRO_1_EXTI |
| 10 | 14 | `/IMU/SPI1.SCK` | U8.13 | SPI1 SCK |
| 11 | 15 | `/IMU/SPI1.MOSI` | U8.14 | SPI1 SDO |
| 12 | 16 | `/IMU/SPI1.MISO` | U8.1 | SPI1 SDI |
| 13 | 17 | `/IMU/CS` | U8.12, R25 10k to +3.3V | GYRO_1_CS |
| 14 | 18 | `/OSD/OSD_W` | R27 3.9k to `/OSD/OSD_LVL` (U9.1 B2) | OSD_W (PIO2) |
| 15 | 19 | `/OSD/OSD_EN` | U9.6 S (SN74LVC1G3157); low selects B1 = `VIDEO_IN` | OSD_EN (PIO2) |
| 16 | 27 | `/OSD/OSD_SYNC` | U11.1 (TLV7031 out) | OSD_SYNC (PIO2 input) |
| 17 | 28 | `/RP2354A/BEEPER` | Q1 gate, R13 100k to GND (Q1 drain is `BUZZER-`) | BEEPER, inverted (high = on) |
| 18 | 29 | `SPI0.SCK` | Card1.5 | SPI0 SCK |
| 19 | 31 | `SPI0.MOSI` | Card1.3 | SPI0 SDO |
| 20 | 32 | `SPI0.MISO` | Card1.7 | SPI0 SDI |
| 21 | 33 | `FLASH_CS` | Card1.2, R34 10k to +3.3V | SDCARD_SPI_CS (the net name is historical) |
| 22 | 34 | `MOTOR4` | R96 220R to U19.25 (ESC4 PB4) | MOTOR4, DShot on PIO0 |
| 23 | 35 | `MOTOR3` | R77 220R to U17.25 (ESC3 PB4) | MOTOR3 |
| 24 | 36 | `MOTOR2` | R58 220R to U15.25 (ESC2 PB4) | MOTOR2 |
| 25 | 37 | `MOTOR1` | R39 220R to U13.25 (ESC1 PB4) | MOTOR1 |
| 26 | 40 | `/RP2354A/LED0` | R15 75R + R16 75R to D1 (blue), cathode GND | LED0, active high |
| 27 | 41 | `ELRS_EN` | R115 1k to U22.7 (ESP32-C3 CHIP_EN) | PINIO1: inverted push-pull, high = ELRS runs; JP2 closed forces ELRS off |
| 28 | 42 | `/RP2354A/ESC_CURR` | R5 1k + C9 100n, from U25.6 (INA186A3 out, net `CURR`) | ADC_CURR (ADC2), `ibat_scale` 200 |
| 29 | 43 | `/RP2354A/ADC_VBAT` | R1 100k from +BATT, R2 10k to GND, C2 100n | ADC_VBAT (ADC3), `vbat_scale` 110 |
| SWCLK | 24 | unconnected | no pad | none: the SWD pads TP42/TP43 were removed |
| SWDIO | 25 | unconnected | none | none |
| USB_DM | 51 | via R8 30R to `USB_D-` | USB1 A7/B7 | USB |
| USB_DP | 52 | via R9 30R to `USB_D+` | USB1 A6/B6 | USB, no VBUS sense GPIO |
| QSPI_SS | 60 | via R7 10k | U1 BOOTSEL button to GND | BOOTSEL |
| RUN | 26 | +3.3V | none | none |

PIO allocation (`config.h`): PIO0 DShot x4; PIO1 PIOUART0 (2 SM) and the LED strip (1 SM); PIO2 framebuffer OSD alone
(31 of 32 instructions). PIOUART1 must stay unused.

## SH-6 (U12, JST SM06B-SRSS-TB)

| Pin | Net |
|---|---|
| 1 | `+10V` |
| 2 | `GND` |
| 3 | `UART0_TX` (GPIO0, PIOUART0) |
| 4 | `UART0_RX` (GPIO1, PIOUART0) |
| 5 | `GND` |
| 6 | `UART1_RX` (GPIO7): the same net as the ESP32-C3 TX (U22.28) and pad J55. SBUS from an air unit needs ELRS held off (`ELRS_EN` low via PINIO1, or JP2 closed) |
| 7, 8 | `GND` (shell) |

## Motor pads (U24 `AIO_outline`)

| ESC | MCU | Firmware | Phase nets | U24 pins | U24 symbol pin names |
|---|---|---|---|---|---|
| ESC1 | U13 | MOTOR1, GPIO25 | `/1A /1B /1C` | 12-14 | 4A 4B 4C |
| ESC2 | U15 | MOTOR2, GPIO24 | `/2A /2B /2C` | 15-17 | 3B 3C 3A |
| ESC3 | U17 | MOTOR3, GPIO23 | `/3C /3B /3A` | 18-20 | 2A 2C 2B |
| ESC4 | U19 | MOTOR4, GPIO22 | `/4C /4B /4A` | 21-23 | 1C 1B 1A |

The symbol pin names number the motors in reverse of the `MOTORn` nets. Betaflight motor order must be set at
bring-up (ISSUES I7). U24.1 is `/CSA+` (battery plus through the shunt) and U24.2 is `GND`.

## ELRS receiver: ESP32-C3 (U22) + SX1281 (U21)

Hardware JSON `RX/Generic C3 2400.json` (ExpressLRS targets) matches every pin below.

| ESP32-C3 pin | GPIO | Net | Connects to | JSON key |
|---|---|---|---|---|
| 27 U0RXD | 20 | `UART1_TX` | RP2354A GPIO6 | `serial_rx: 20` |
| 28 U0TXD | 21 | `UART1_RX` | RP2354A GPIO7 | `serial_tx: 21` |
| 5 | 1 | `/RX/DIO1` | U21.8 | `radio_dio1: 1` |
| 6 | 2 | `/RX/RST` | U21.3, R111 10k to +3.3V (strap) | `radio_rst: 2` |
| 8 | 3 | `/RX/BUSY` | U21.7 | `radio_busy: 3` |
| 9 | 4 | `/RX/MOSI` | U21.17 | `radio_mosi: 4` |
| 10 | 5 | `/RX/MISO` | U21.16 | `radio_miso: 5` |
| 12 | 6 | `/RX/SCK` | U21.18 | `radio_sck: 6` |
| 13 | 7 | `/RX/NSS` | U21.19 | `radio_nss: 7` |
| 14 | 8 | `/RX/LED` | D9.4 (WS2812 data), R112 10k to +3.3V (strap) | `led_rgb: 8`, `led_rgb_isgrb: true` |
| 15 | 9 | `/RX/BOOT` | TP9, R113 10k to +3.3V (strap, low = download mode) | `button: 9` |
| 7 CHIP_EN | none | `/RX/CHIP_EN` | R114 10k to +3.3V, C84 1 uF, R115 1k from `ELRS_EN`, JP2 to GND | none |
| 16 | 10 | `GND` | tied to ground | not used |
| 1 LNA_IN | none | via L7 to `/RX/WIFI` | AE2 2.4 GHz chip antenna (WiFi only) | none |
| 4, 25, 26, 19-24 | 0, 18, 19, flash | unconnected | | |

SX1281 (U21): DIO2, DIO3 and XTB unconnected. XTA: OSC1 52 MHz TCXO, AC-coupled through C69. RFIO (22): FL1 band-pass,
then JP1 u.FL (the ELRS antenna is external). DC-DC fitted: L4 15 uH from DCC_SW (14) to DCC_FB (12), VDD_IN (2) on
DCC_FB. Supply: `+3.3V` from U7.

## ESC MCUs: AT32F421G8U7 x4 (U13, U15, U17, U19), identical wiring (ESC1 shown)

AM32 groups are defined in `Inc/targets.h` of AM32 `50234143`: `HARDWARE_GROUP_AT_B` and `HARDWARE_GROUP_AT_045`.

| AT32 pin | Port | Net | Connects to | AM32 macro |
|---|---|---|---|---|
| 25 | PB4 | `Net-(U13-PB4)` | R39 220R to `MOTORn` | `INPUT_PIN`, TMR3_CH1 |
| 20 | PA10 | `/ESC1/AH` | U14.22 HIN1 | `PHASE_A_GPIO_HIGH` |
| 15 | PB1 | `/ESC1/AL` | U14.1 LIN1 | `PHASE_A_GPIO_LOW` |
| 19 | PA9 | `/ESC1/BH` | U14.23 HIN2 | `PHASE_B_GPIO_HIGH` |
| 14 | PB0 | `/ESC1/BL` | U14.2 LIN2 | `PHASE_B_GPIO_LOW` |
| 18 | PA8 | `/ESC1/CH` | U14.24 HIN3 | `PHASE_C_GPIO_HIGH` |
| 13 | PA7 | `/ESC1/CL` | U14.3 LIN3 | `PHASE_C_GPIO_LOW` |
| 6 | PA0 | `/ESC1/FBA` | phase A through a 10k divider | `PHASE_A_COMP` |
| 10 | PA4 | `/ESC1/FBB` | phase B | `PHASE_B_COMP` |
| 11 | PA5 | `/ESC1/FBC` | phase C | `PHASE_C_COMP` |
| 7 | PA1 | `/ESC1/FBCOMMON` | virtual neutral, 10k from each of FBA, FBB, FBC | comparator common |
| 21, 22 | PA13, PA14 | SWDIO, SWCLK | TP1/TP2 (ESC1), TP3/TP4, TP5/TP6, TP7/TP8, all on B.Cu | SWD |
| 1 | BOOT0 | | R38 10k to GND | |
| 4 | NRST | | R37 10k to +3.3V, C37 100n; no test pad | |
| 5, 17 | VDDA, VDD | | VDDA from +3.3V through R40 10R + 100n; VDD = +3.3V | |

NC: PA2, PA3, PA6, PA15, PB3, PB5 to PB7, PF0, PF1. There is no per-ESC current or voltage sense. The only current
sense is the board-level INA186A3 (U25) into GPIO28.
