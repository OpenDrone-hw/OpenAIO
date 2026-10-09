/*
 * This file is part of Betaflight.
 *
 * Betaflight is free software. You can redistribute this software
 * and/or modify this software under the terms of the GNU General
 * Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later
 * version.
 *
 * Betaflight is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program.
 *
 * If not, see <http://www.gnu.org/licenses/>.
 */

/*
 * OpenAIO: FPV all-in-one in two boards.
 *   Core (hat, on a 46-pad LGA): RP2354A flight controller, BMI270, PIO framebuffer OSD.
 *   Base: 4x AT32F421 ESC (AM32), ESP32-C3 + SX1281 ELRS receiver, microSD, bucks,
 *         LED-strip pads, SH-6 digital-VTX connector, USB-C.
 *
 * Pins: every pin below was taken from the kicad-cli netlist of
 * hardware/OpenAIO.kicad_sch at OpenAIO be152bb (branch work/d81e559), and checked
 * against the pad nets of OpenAIO-Core.kicad_pcb and OpenAIO-Base.kicad_pcb.
 * Each pin comment gives: net | RP2354A (U2) pin | LGA pad (J91 Core = J90 Base) | endpoint.
 * The full table is in PINOUT.md.
 *
 * Macro names: every macro below comes from an upstream file, cited in brackets.
 *   [BF ...]  betaflight/betaflight master 4dea42a9 (2026-10-09)
 *   [CFG ...] betaflight/config e1d87e7e (2026-10-08), the RP2350 configs in configs/RASP/
 *
 * Flash: RP2354A has 2 MB in package. This folder also carries config.mk and
 * pico_flash_mem.ld, the upstream mechanism for a non-default flash size
 * [BF src/platform/PICO/mk/RP2350.mk:506-516; CFG configs/RASP/RASPBERRY_PI_UAVFC/config.mk].
 *
 * Board assumptions this file depends on (see ISSUES.md):
 *   - LED strip: the TXU0101 non-inverting translator replaces Q2/R14 (owner decision
 *     c1da3e7). At be152bb the netlist still has the inverting Q2 stage (ISSUES.md I2).
 *   - Forward = the edge with the SH-6 connector, battery pads at the rear (ISSUES.md I8).
 */

#pragma once

// [CFG configs/RASP/PICO2_2350A/config.h:24-26]; FC_TARGET_MCU is read by [BF mk/config.mk:86]
#define FC_TARGET_MCU        RP2350A      // RP2354A = RP2350A die + 2 MB W25Q16JV flash die (RP2350.pdf p1331)
#define BOARD_NAME           OPENAIO
#define MANUFACTURER_ID      OPDR         // PLACEHOLDER: needs a registered 4-char ID before upstreaming

// ---------------------------------------------------------------------------
// Gyro / accelerometer: BMI270 (U8) on SPI1, Core
// [CFG configs/RASP/RASPBERRY_PI_UAVFC/config.h:28-33,64-72]
// [BF src/main/target/common_pre.h:150 (USE_ACCGYRO_BMI270); src/main/pg/gyrodev.c:38-43,163-172]
// [BF src/main/pg/bus_spi.c:35-45,95-98 (SPIn_SCK/SDI/SDO_PIN); SDI = MISO, SDO = MOSI]
// SPI1 pin legality: [BF src/platform/PICO/bus_spi_pico.c:103 (PA10 SCK),114 (PA12 MISO),123 (PA11 MOSI)]
// ---------------------------------------------------------------------------
#define USE_GYRO
#define USE_ACC
#define USE_ACCGYRO_BMI270

#define SPI1_SCK_PIN         PA10         // /IMU/SPI1.SCK  | U2.14 | Core only | U8.13 SCx
#define SPI1_SDI_PIN         PA12         // /IMU/SPI1.MISO | U2.16 | Core only | U8.1 SDO
#define SPI1_SDO_PIN         PA11         // /IMU/SPI1.MOSI | U2.15 | Core only | U8.14 SDx
#define GYRO_1_SPI_INSTANCE  SPI1
#define GYRO_1_CS_PIN        PA13         // /IMU/CS        | U2.17 | Core only | U8.12 CSB, R25 10k pull-up to +3.3V
#define GYRO_1_EXTI_PIN      PA9          // /IMU/GYRO_INT  | U2.13 | Core only | U8.4 INT1
#define GYRO_2_CS_PIN        NONE

// U8 sits at 180 deg on Core F.Cu (pin 1 at the top-left in the KiCad top view), so the
// BMI270 +X points to the battery-pad edge and +Y to the USB edge (BMI270.pdf p144).
// Betaflight's body frame is X forward, Y left, Z up: rMat maps body X/Y/Z onto earth NWU and is
// the identity for a level craft facing north [BF src/main/flight/imu.c:151-154].
// Forward = SH-6 edge  -> CW180_DEG.   Forward = battery-pad edge -> CW0_DEG.
// The board has no forward marking: confirm in the Setup tab at bring-up (ISSUES.md I8).
#define GYRO_1_ALIGN         CW180_DEG

// ---------------------------------------------------------------------------
// Blackbox: microSD (Card1, Base) on SPI0, across the LGA
// [CFG configs/RASP/RASPBERRY_PI_UAVFC/config.h:35-36,67,260,266]
// [BF src/main/pg/sdcard.c:39-48,82-84; src/main/blackbox/blackbox.c:105-114]
// SPI0 pin legality: [BF src/platform/PICO/bus_spi_pico.c:71 (PA18 SCK),82 (PA20 MISO),91 (PA19 MOSI)]
// ---------------------------------------------------------------------------
#define USE_SDCARD
#define USE_SDCARD_SPI
#define SPI0_SCK_PIN         PA18         // SPI0.SCK  | U2.29 | LGA 12 | Card1.5 CLK
#define SPI0_SDI_PIN         PA20         // SPI0.MISO | U2.32 | LGA 17 | Card1.7 DAT0
#define SPI0_SDO_PIN         PA19         // SPI0.MOSI | U2.31 | LGA 13 | Card1.3 CMD
#define SDCARD_SPI_INSTANCE  SPI0
#define SDCARD_SPI_CS_PIN    PA21         // FLASH_CS  | U2.33 | LGA 29 | Card1.2 CD/DAT3, R34 10k pull-up to +3V3.
                                          //   The net name is historical: there is no flash chip, this is the SD CS.
#define SDCARD_DETECT_PIN    NONE         // no card-detect switch is wired
#define DEFAULT_BLACKBOX_DEVICE BLACKBOX_DEVICE_SDCARD

// ---------------------------------------------------------------------------
// Motors: DShot on PIO0 (default PIO_DSHOT_INDEX 0, [BF src/platform/PICO/target/common/target_RP2350.h:92-94]).
// Bidirectional DShot program is 29 instructions, 1 SM per motor
// [BF src/platform/PICO/dshot_pio_programs.h:107; dshot_pico.c:426-453].
// [BF src/main/pg/motor.c:46-47,97-98; CFG configs/RASP/RASPBERRY_PI_UAVFC/config.h:51-55]
// Each MOTORn line has 220R at the ESC and lands on AT32F421 PB4 (AM32 HARDWARE_GROUP_AT_B input).
// Physical pad positions differ from the AIO_outline symbol's pad names: see PINOUT.md and ISSUES.md I7.
// ---------------------------------------------------------------------------
#define MOTOR1_PIN           PA25         // MOTOR1 | U2.37 | LGA 24 | R39 220R -> U13 (ESC1) PB4
#define MOTOR2_PIN           PA24         // MOTOR2 | U2.36 | LGA 23 | R58 220R -> U15 (ESC2) PB4
#define MOTOR3_PIN           PA23         // MOTOR3 | U2.35 | LGA 19 | R77 220R -> U17 (ESC3) PB4
#define MOTOR4_PIN           PA22         // MOTOR4 | U2.34 | LGA 21 | R96 220R -> U19 (ESC4) PB4
#define DEFAULT_DSHOT_TELEMETRY DSHOT_TELEMETRY_ON   // AM32 answers bidirectional DShot

// ---------------------------------------------------------------------------
// Serial ports.
// Pin tables: [BF src/platform/PICO/uart/uart_hw.c:42-43 (UART0 RX PA1/PA3), 58-59 (UART0 TX PA0/PA2),
//              87 (UART1 RX PA7), 103 (UART1 TX PA6)]. GPIO2/3 and GPIO6/7 use the F11 UART_AUX
//              function, selected automatically [BF uart_hw.c:252,259; RP2350.pdf p19].
// Pin macros: [BF src/main/drivers/serial_pinconfig.c:44,101,104]
//
// SBUS NOTE (ISSUES.md I1): the PIO UART rejects SERIAL_PARITY_EVEN
// [BF src/platform/PICO/uart/uart_pio.c:275-277], and SBUS always opens with it
// [BF src/main/rx/sbus.c:81-82,206-216], so SBUS cannot run on a PIO UART. The SBUS input
// (net PU0RX, GPIO3) is therefore served by HARDWARE UART0 on its AUX pins GPIO2/3, and the
// SH-6 UART pair (GPIO0/1) moves to PIOUART0, which only carries 8N1 traffic (MSP DisplayPort).
// Consequence: the pad labels are swapped relative to the firmware ports:
//   J44 "PIO_TX0" / J45 "PIO_RX0" = Betaflight UART0;  J49 "TX0" / J48 "RX0" = Betaflight PIOUART0.
// ---------------------------------------------------------------------------

// Hardware UART1 (AUX pins): onboard ELRS receiver, CRSF.
// [BF src/main/pg/rx.c:38-52,119-120; src/main/config/feature.c:34; CFG configs/TEBS/TBS_LUCID_RPI_FC/config.h (SERIALRX_*)]
#define UART1_TX_PIN         PA6          // UART1_TX | U2.9  | LGA 33 | U22.27 U0RXD (ESP32-C3 GPIO20); J54 "TX1" (Core)
#define UART1_RX_PIN         PA7          // UART1_RX | U2.10 | LGA 25 | U22.28 U0TXD (ESP32-C3 GPIO21); J55 "RX1" (Core)
#define DEFAULT_RX_FEATURE   FEATURE_RX_SERIAL
#define SERIALRX_PROVIDER    SERIALRX_CRSF
#define SERIALRX_UART        SERIAL_PORT_UART1

// Hardware UART0 (AUX pins): SBUS from the digital air unit (SH-6 pin 6), or a GPS on J44/J45.
// 8E2 is supported here [BF uart_hw.c:269-274]. SBUS inversion is done in the pad (gpio_set_inover) [BF src/platform/PICO/uart/serial_uart_pico.c:59-87],
// with the RX pull-down for an inverted port [BF uart_hw.c:261-265]. No external inverter is needed.
#define UART0_TX_PIN         PA2          // /Pads/PIOUART0_TX | U2.4 | Core only | J44 "PIO_TX0"
#define UART0_RX_PIN         PA3          // PU0RX             | U2.5 | LGA 40    | U12.6 (SH-6 pin 6, SBUS); J45 "PIO_RX0" (Core)

// PIOUART0 on PIO1 (default PIO_UART_INDEX 1): SH-6 UART pair for the digital VTX (MSP DisplayPort).
// [BF src/main/io/serial.h:129 (SERIAL_PORT_PIOUART0); src/main/pg/msp.c:67-68;
//  CFG configs/TEBS/TBS_LUCID_RPI_FC/config.h (MSP_DISPLAYPORT_UART)]
#define PIOUART0_TX_PIN      PA0          // UART0_TX | U2.2 | LGA 38 | U12.3 (SH-6 pin 3); J49 "TX0" (Core)
#define PIOUART0_RX_PIN      PA1          // UART0_RX | U2.3 | LGA 39 | U12.4 (SH-6 pin 4); J48 "RX0" (Core)
#define MSP_DISPLAYPORT_UART SERIAL_PORT_PIOUART0
// PIOUART1 is left unassigned: PIO1 then holds PIOUART0 (2 SMs, 10 + 9 instructions) and the
// LED strip (1 SM, 4 instructions) = 3/4 SMs, 23/32 instructions.

// ---------------------------------------------------------------------------
// PIO allocation (defaults in [BF src/platform/PICO/target/common/target_RP2350.h:85-106]):
//   PIO0 DShot x4 | PIO1 PIOUART0 + LED strip | PIO2 framebuffer OSD alone.
// The OSD program is 31 instructions [BF src/platform/PICO/osd/osd_tx.pio.h:60,122]; with the
// default PIO_LEDSTRIP_INDEX 2 the WS2812 program (4) would not fit next to it
// ([BF src/platform/PICO/light_ws2811strip_pico.c:63-78,145-153]; [CFG configs/RASP/RASPBERRY_PI_UAVFC/config.h:176]).
// config.h is included before target.h, so the #ifndef default yields to this.
// ---------------------------------------------------------------------------
#define PIO_LEDSTRIP_INDEX   1

// ---------------------------------------------------------------------------
// I2C0: external magnetometer / barometer pads on the Core (no onboard sensor).
// [BF src/main/pg/bus_i2c.c:44-48,120; CFG configs/RASP/RASPBERRY_PI_UAVFC/config.h:149-154]
// ---------------------------------------------------------------------------
#define I2C0_SDA_PIN         PA4          // /Pads/I2C0.SDA | U2.7 | Core only | J26 "SDA", R12 5.1k pull-up to +3.3V
#define I2C0_SCL_PIN         PA5          // /Pads/I2C0.SCL | U2.8 | Core only | J23 "SCL", R11 5.1k pull-up to +3.3V
#define MAG_I2C_INSTANCE     I2CDEV_0
#define BARO_I2C_INSTANCE    I2CDEV_0

// ---------------------------------------------------------------------------
// ADC. RP2350A: GPIO26..29 = ADC0..3 [BF src/platform/PICO/adc_pico.c:81-85]; ADC_AVDD = +3.3V (U7),
// Vref 3300 mV default [BF src/main/sensors/adcinternal.c:114-120].
// [BF src/main/pg/adc.c:40-52; src/main/sensors/battery.c:89-102; voltage.c:104-105,161-166;
//  current.c:93-98,112-119]
// ---------------------------------------------------------------------------
#define ADC_VBAT_PIN         PA29         // /RP2354A/ADC_VBAT | U2.43 (ADC3) | +BATT via LGA 36 | R1 100k / R2 10k, C2 100n (Core)
#define ADC_CURR_PIN         PA28         // /RP2354A/ESC_CURR | U2.42 (ADC2) | CURR via LGA 8 | R5 1k + C9 100n (Core) <- U25.6 INA186A3 OUT (Base)
#define DEFAULT_VOLTAGE_METER_SOURCE VOLTAGE_METER_ADC
#define DEFAULT_CURRENT_METER_SOURCE CURRENT_METER_ADC
// vbat_scale: (R1 + R2) / R2 = (100k + 10k) / 10k = 11 -> 110 with the default resdivval 10.
// Full scale 36.3 V; 6S full charge 25.2 V reads 2.29 V at the pin.
#define DEFAULT_VOLTAGE_METER_SCALE  110
// ibat_scale is in mV per 10 A [BF src/main/sensors/current.c:118].
// INA186A3 gain 100 V/V (INA186A3IDCKR.pdf p1, p5) x Rsense2 0.2 mOhm (ASR-S-3-0.2F) = 20 mV/A = 200 mV/10A.
// REF = GND (unidirectional): 0 A reads 2 mV typ / 10 mV max (VZL, p5), i.e. 0.1-0.5 A; trim ibat_offset at bring-up.
// Range: about 162 A before the INA186 output swing limit (VS = +3V3 minus 20-40 mV); 40 mA per ADC LSB.
#define DEFAULT_CURRENT_METER_SCALE  200
#define DEFAULT_CURRENT_METER_OFFSET 0

// ---------------------------------------------------------------------------
// Beeper and status LED
// [BF src/main/pg/beeper_dev.c:33-53; src/main/drivers/sound_beeper.c:39-44]
// [BF src/main/drivers/light_led.c:47-55,82-88]
// ---------------------------------------------------------------------------
#define USE_BEEPER
#define BEEPER_PIN           PA17         // /RP2354A/BEEPER | U2.28 | Q1 AP1606 gate, R13 100k pull-down (Core);
                                          //   Q1 drain = BUZZER- | LGA 34 | J29 "BUZ-"; J33 "BUZ+" = +5V (Base)
// Low-side N-FET: GPIO high = buzzer on, so push-pull and inverted (default is open-drain, active-low).
// For an active (self-oscillating) 5 V buzzer, the usual FPV part. For a passive buzzer, replace with
// BEEPER_PWM_HZ 1971 as in [CFG configs/RASP/RASPBERRY_PI_UAVFC/config.h:162]: GPIO17 is PWM0 B and the
// PWM beeper forces the pin low when off [BF src/platform/PICO/pwm_beeper_pico.c:38-44].
#define BEEPER_INVERTED

#define LED0_PIN             PA26         // /RP2354A/LED0 | U2.40 | Core only | R15 75R + R16 75R -> D1 (blue) anode, cathode GND
#define LED0_INVERTED                     // LED is active-high; Betaflight's default drives LEDs active-low

// ---------------------------------------------------------------------------
// LED strip (WS2812) on PIO1 (see PIO_LEDSTRIP_INDEX above). The driver has no output inversion
// [BF src/platform/PICO/light_ws2811strip_pico.c:88-101], so the board stage must be non-inverting:
// TXU0101 + 200R per owner decision c1da3e7. NOT YET IN THE NETLIST at be152bb (ISSUES.md I2).
// [BF src/main/io/ledstrip.c:207-208]
// ---------------------------------------------------------------------------
#define LED_STRIP_PIN        PA8          // /RP2354A/LED_STRIP_L | U2.12 | (Q2 today, TXU0101 planned) -> LED_STRIP
                                          //   | LGA 46 | J20, J21, J31, J32 "LED" (Base)

// ---------------------------------------------------------------------------
// Analogue OSD: PIO framebuffer OSD on PIO2 (default PIO_OSD_INDEX 2).
// W, EN, SYNC must be consecutive GPIOs [BF src/platform/PICO/osd/osd_pico.c:26-27,137-160].
// EN = 0 is pass-through, EN = 1 overlays W level [BF osd_pico.c:698-700]; U9 S low selects B1 = VIDEO_IN.
// Block below mirrors the upstream FB-OSD reference [CFG configs/RASP/RASPBERRY_PI_UAVFC/config.h:176-248];
// ENABLE_FB_OSD / OSD_FB_PICO_FLASH_FONT are read by [BF src/platform/PICO/osd/fb_osd_pico.c:28,38,61].
// The flash font needs FONT_LENGTH = 16K in pico_flash_mem.ld (this folder).
// U11 TLV7031 adds about 3 us of sync delay, which shifts the canvas about 22 px right (ISSUES.md I4).
// Default display device: MSP (because MSP_DISPLAYPORT_UART is set, [BF src/main/osd/osd.c:126-131]).
// For an analogue VTX: set osd_displayport_device = FBOSD.
// ---------------------------------------------------------------------------
#ifndef ENABLE_FB_OSD
#define ENABLE_FB_OSD        1
#endif

#if ENABLE_FB_OSD

#ifndef USE_OSD_SD
#define USE_OSD_SD
#endif

#define OSD_W_PIN            PA14         // /OSD/OSD_W    | U2.18 | Core only | R27 3.9k -> /OSD/OSD_LVL -> U9.1 B2
#define OSD_EN_PIN           PA15         // /OSD/OSD_EN   | U2.19 | Core only | U9.6 S (SN74LVC1G3157)
#define OSD_SYNC_PIN         PA16         // /OSD/OSD_SYNC | U2.27 | Core only | U11.1 TLV7031 OUT (push-pull)

#define OSD_FB_PICO_FLASH_FONT

#ifndef OSD_FB_PICO_ENABLE_PIXEL_MODE
#define OSD_FB_PICO_ENABLE_PIXEL_MODE 1
#endif

#if OSD_FB_PICO_ENABLE_PIXEL_MODE
#define OSD_FB_PICO_POSTPROCESS 2
#define OSD_BATTERY_PERCENT_WITH_SYMBOL
#define OSD_RSSI_WITH_SYMBOL
#ifndef OSD_FB_ENABLE_SMALLFONT
#define OSD_FB_ENABLE_SMALLFONT 1
#endif
#endif // OSD_FB_PICO_ENABLE_PIXEL_MODE

#if !OSD_FB_ENABLE_SMALLFONT
#undef OSD_RSSI_WITH_SYMBOL
#endif

#define OSD_FRAMERATE_MAX_HZ         100
#define OSD_FRAMERATE_DEFAULT_HZ     50
#define OSD_DRAWSCREEN_TIME_LIMIT_US 20

#endif // ENABLE_FB_OSD

// ---------------------------------------------------------------------------
// Defaults [BF src/main/config/feature.c:34]
// ---------------------------------------------------------------------------
#define DEFAULT_FEATURES     (FEATURE_OSD | FEATURE_TELEMETRY | FEATURE_LED_STRIP)

// ---------------------------------------------------------------------------
// Not wired (recorded so nobody looks for them):
//   USB VBUS detect: none. VBUS (+5V_USB) only feeds +4v5 through D3. Betaflight then treats
//     "VCP connected" as cable inserted [BF src/main/drivers/usb_io.c:56-70]. No USB_DETECT_PIN.
//   GPIO27 (U2.41, ADC1): unconnected. Candidate for ESP32-C3 CHIP_EN / BOOT control (ISSUES.md I5).
//   SWD: SWCLK U2.24 -> LGA 20 -> TP32, SWDIO U2.25 -> LGA 10 -> TP31 (Base B.Cu).
//   BOOTSEL: U1 button -> R7 1k -> QSPI_SS (U2.60); the `bl` CLI command also reboots to the
//     USB bootrom [BF src/platform/PICO/system.c:157-161].
// ---------------------------------------------------------------------------
