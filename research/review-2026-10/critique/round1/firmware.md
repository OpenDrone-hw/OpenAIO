# Firmware and pin-map review: OpenAIO at 1522ed6 (boards as of f512434)

**Verdict**
1. The pin map is legal and conflict-free. A stock Betaflight RP2350A target can be written for this board with no firmware changes: one `config.h` plus one `pico_flash_mem.ld`, given below. ELRS (`Generic C3 2400`) and AM32 (`OPENESC_20/30_F421`) already have targets that match the wiring pin for pin.
2. Two MAJOR problems. (a) Q2 inverts the LED-strip data, and no Betaflight driver can invert it back, so the LED strip cannot work on stock firmware. (b) On USB power alone, AM32 drives the gate-driver inputs while the NSG2065Q VCC (+10V) is at 0 V.
3. Also: the OSD sync comparator (TLV7031, 3 µs) moves the PIO OSD canvas about 22 px to the right, and Betaflight has no setting to move it back. The target has to override two defaults: the PIO block for the LED strip, and the flash size (2 MB).

Method: I exported the netlist with `kicad-cli` (OPENDRONE_LIB set) and read the pad nets from both PCBs with pcbnew. Scripts and outputs are in `scratchpad/critique/firmware/`. Sources checked:
- Betaflight master `498430ad` (the same constraints are in release tag `2026.6.2`)
- betaflight/config `1e3f7782`
- AM32 `50234143`
- AM32-bootloader `578ff29c`
- ExpressLRS/targets `42ed776a`

Each claim below cites a file and line in one of these repos, or a datasheet page under `hardware/KiCad-Library/datasheet/`.

## Findings

| ID | severity | board/layer | location (ref, net, x,y) | evidence | fix |
|---|---|---|---|---|---|
| FW1 | MAJOR | Core F.Cu | Q2 (112.78,60.35), R14 (112.00,60.37); U2.12 GPIO8 `/RP2354A/LED_STRIP_L` → Q2.G; Q2.D = `LED_STRIP` → R14 2.4 kΩ to +5V → J20/J21/J31/J32 | Q2 is an AP1606, an N-channel MOSFET (AP1606.pdf p1), wired common-source, so GPIO high gives a low line: the data is inverted. Betaflight's RP2350 WS2812 driver drives the pin straight from PIO side-set and has no inversion: `src/platform/PICO/light_ws2811strip_pico.c:63-68` (program), `:88-100` (init, no `gpio_set_outover`). The CLI has no `ledstrip_*` inversion setting (`src/main/cli/settings.c:1554-1565`). The PIO idles low, so the line idles high: no WS2812 reset/latch and every bit inverted. CIRCUIT_REVIEW O6 said "firmware must handle" the inversion. Stock firmware cannot. This breaks the owner rule "stock firmware, no forks" (README.md:45-46). | Make the stage non-inverting: a 5 V-supplied single buffer with TTL thresholds (e.g. 74AHCT1G125 class) in place of Q2+R14. Or drop Q2/R14 and drive GPIO8 straight to the pads through 33-100 Ω, as most FCs do. |
| FW2 | MAJOR | Base B.Cu | U13/U15/U17/U19 AT32F421 (69.12,64.54 … 81.74,57.26) PA8-10/PA7/PB0/PB1 → U14/U16/U18/U20 HIN/LIN, direct nets; NSG2065Q VCC (pin 4) = +10V; AT32 VDD = +3V3 from U23 (EN = IN = +4v5) | On USB power alone, +4v5 comes from VBUS through D3. U23 then powers the four AT32s, while +10V is 0 V because U3 VIN/EN = +BATT (netlist). AM32 plays its startup tune unconditionally at boot (`Src/main.c:1893`), and the tune PWMs the phases through `comStep()` (`Src/sounds.c:118-142`). The call has no voltage or input gate, and the OPENESC targets have no voltage sense at all. The result is 3.3 V on HIN/LIN with VCC = 0, but the NSG2065Q abs max is VIN ≤ VCC + 0.3 V (NSG2065Q.pdf p5). This happens on every USB plug-in. The current flows through the input ESD into +10V (C23, the SH-6 VTX if one is plugged in), and through U3's body diode into +BATT. CIRCUIT_REVIEW §6 ("B1's fix removes both") covers only the battery case. | Power the four AT32 VDDs from a battery-only rail (a small LDO from +5V or +10V), so ESCs are off on USB, as on most AIOs. Or, at minimum, put 1 kΩ in series with each of the 24 HIN/LIN lines to limit injection. |
| FW3 | MINOR | Core F.Cu | U11 TLV7031 (113.56,49.08), OUT → U2.27 GPIO16 `/OSD/OSD_SYNC` | TLV7031 tPD is 3 µs typical at 100 mV overdrive (TLV7031.pdf p1, p8). The sync tip here sits only about 0.1-0.2 V below the IN− = GND threshold (D8 clamp). Betaflight's PIO OSD starts each line a fixed count after the comparator edge. For PAL that is 6 + 27·30 + 12 = 828 clocks = 11.04 µs at 75 MHz (`osd/osd_tx.pio:20,42-44,74`; `osd_pico.c:262-266`), then outputs 368 px × 10 clocks = 49.07 µs (`osd_tx.pio:4,29`). The canvas therefore ends at 60.1 µs nominal, but at about 63.1 µs with a 3 µs lag, past the end of PAL active video (about 62.5 µs). The image shifts about 22 px right. Any variation in delay (overdrive, noise) becomes line-to-line horizontal jitter. The hshift values are compile-time PIO constants, and no CLI or VCD offset is applied (`grep vcdProfile osd_pico.c`: none). | Fit a fast comparator (tPD ≤ about 0.3 µs, push-pull, 3.3 V, rail-inclusive input) on the U11 site. A same-footprint TLV70x1 sibling is a candidate: check its tPD and package. Or move the threshold to mid-sync, using a divider on IN−, to raise the overdrive. |
| FW4 | MINOR | Core F.Cu | J54 "TX1" (119.13,44.40) = `UART1_TX`, J55 "RX1" (119.13,46.40) = `UART1_RX` = U22.28 ESP32-C3 U0TXD (push-pull) | The pads look like a spare UART. UART1 is in fact the onboard ELRS link (U22.27/28 ↔ U2.9/10), so any device that drives J55 fights the ESP32 TX output. | Label them as ELRS service pads (for UART flashing with the FC held in BOOTSEL), or remove them. |
| FW5 | MINOR | target (no board change) | PIO2: FB OSD (GPIO14-16) and LED strip (GPIO8) | By default both the LED strip and FB OSD go on PIO2 (`target/common/target_RP2350.h:100-106`). The OSD program is 31 instructions (`osd_tx.pio.h:60,122`) and WS2812 is 4 (`light_ws2811strip_pico.c:63-68`): 35 > 32. So one of them fails: the LED strip quietly through `pio_can_add_program`, or the OSD with an unchecked `pio_add_program` (`osd_pico.c:233`). Betaflight's own UAVFC config says "choose between LED STRIP or FB OSD" (betaflight/config `configs/RASP/RASPBERRY_PI_UAVFC/config.h:176`). PIO1 holds PIOUART0 (tx 10 + rx 9 instructions, 2 SMs), so it has room. | In `config.h`, set `#define PIO_LEDSTRIP_INDEX 1`. The `#ifndef` allows it, and `config.h` is included before `target.h` (`src/main/platform.h:25-34`). PIO1 then holds 23/32 instructions and 3/4 SMs. Leave PIOUART1 unassigned. |
| FW6 | MINOR | target (no board change) | U2 RP2354A internal flash | The RP2354A has 2 MB (RP2350.pdf p14, p1331). Betaflight's default layout assumes `PRIMARY_FLASH_LENGTH = 4M` (`link/pico_flash_mem_defaults.ld:5`), which puts the 64 KB config area at 4 MB − 64 KB (`pico_rp2350_memory.ld:4-11`), beyond the device. A config folder can override this (`mk/RP2350.mk:510-516`). | Ship `pico_flash_mem.ld` with `PRIMARY_FLASH_LENGTH = 2M; FONT_LENGTH = 16K;` in the config folder. |
| FW7 | NIT | Core F.Cu / Base F.Cu | J45 "PIO_RX0" (121.07,57.18) and U12.6 (SH-6 pin 6, 80.45,75.06) are the same net `PU0RX` (GPIO3) | These are either/or uses of one RX. A GPS on J44/J45 together with an air unit that drives SH-6 pin 6 would contend. | Say so on the silk or in the docs. |
| FW8 | NIT | Base B.Cu | TP1-TP8 (AT32 PA13/PA14), e.g. TP1 (65.12,65.45), TP2 (65.12,62.91) | SWD-only pads, with no NRST or +3V3 per ESC. AM32 never remaps PA13/PA14, so a plain SWD connect works, but connect-under-reset is impossible. | Optional: one shared +3V3 pad next to TP1-TP8 for the jig's VTref. |

## Betaflight target (config.h), stock RP2350A platform

Every pin below appears in the platform pin tables:
- UART0 RX/TX: `uart/uart_hw.c:43,59`.
- UART1 on GPIO6/7 through the F11 UART_AUX function: `uart_hw.c:87,103`, funcsel at `:252,259`.
- SPI0 18/19/20 and SPI1 10/11/12: `bus_spi_pico.c:71,82,91,103,114,123`.
- ADC GPIO28/29 map to channels 2/3: `adc_pico.c:81-95`.
- OSD pins must be W, EN, SYNC consecutive: `osd/osd_pico.c:138-160`. The board's 14/15/16 matches. The EN=0 pass-through and EN=1 W-level convention (`osd_pico.c:698-700`) matches the SN74LVC1G3157 wiring (S low selects B1 = VIDEO_IN).
- SBUS inversion on a PIO UART through `gpio_set_inover`: `uart/serial_uart_pico.c:59-87`.
- Bidirectional DShot on PIO0 (29 instructions): `dshot_pico.c:410-438`, `dshot_pio_programs.h:107`.
- 4-way AM32 passthrough: `target_RP2350.h:144-147`.
- `bl` command to the USB bootrom: `system.c:157-161`.

```c
#define FC_TARGET_MCU        RP2350A      // RP2354A = RP2350A + 2 MB in-package flash
#define BOARD_NAME           OPENAIO
#define MANUFACTURER_ID      OPDR         // TBD

#define USE_GYRO
#define USE_ACC
#define USE_ACCGYRO_BMI270
#define SPI1_SCK_PIN         PA10
#define SPI1_SDO_PIN         PA11
#define SPI1_SDI_PIN         PA12
#define GYRO_1_SPI_INSTANCE  SPI1
#define GYRO_1_CS_PIN        PA13
#define GYRO_1_EXTI_PIN      PA9
#define GYRO_1_ALIGN         CW180_DEG    // U8 sits at 180 deg on Core F.Cu: confirm against the board's "forward"
#define GYRO_2_CS_PIN        NONE

#define USE_SDCARD
#define USE_SDCARD_SPI
#define SPI0_SCK_PIN         PA18
#define SPI0_SDO_PIN         PA19
#define SPI0_SDI_PIN         PA20
#define SDCARD_SPI_INSTANCE  SPI0
#define SDCARD_SPI_CS_PIN    PA21         // net is named FLASH_CS
#define SDCARD_DETECT_PIN    NONE
#define DEFAULT_BLACKBOX_DEVICE BLACKBOX_DEVICE_SDCARD

#define MOTOR1_PIN           PA25         // PIO0, bidir DShot
#define MOTOR2_PIN           PA24
#define MOTOR3_PIN           PA23
#define MOTOR4_PIN           PA22

#define UART0_TX_PIN         PA0          // SH-6.3 / J49
#define UART0_RX_PIN         PA1          // SH-6.4 / J48
#define MSP_DISPLAYPORT_UART SERIAL_PORT_UART0
#define UART1_TX_PIN         PA6          // F11 UART_AUX -> ESP32-C3 U0RXD
#define UART1_RX_PIN         PA7          // F11 UART_AUX <- ESP32-C3 U0TXD
#define DEFAULT_RX_FEATURE   FEATURE_RX_SERIAL
#define SERIALRX_PROVIDER    SERIALRX_CRSF
#define SERIALRX_UART        SERIAL_PORT_UART1
#define PIOUART0_TX_PIN      PA2          // J44
#define PIOUART0_RX_PIN      PA3          // J45 + SH-6.6 (SBUS, inverted via inover)
#define PIO_LEDSTRIP_INDEX   1            // FW5: PIO2 is full with FB OSD

#define I2C0_SDA_PIN         PA4
#define I2C0_SCL_PIN         PA5
#define MAG_I2C_INSTANCE     I2CDEV_0
#define BARO_I2C_INSTANCE    I2CDEV_0

#define USE_ADC
#define ADC_VBAT_PIN         PA29
#define ADC_CURR_PIN         PA28
#define DEFAULT_VOLTAGE_METER_SOURCE VOLTAGE_METER_ADC
#define DEFAULT_CURRENT_METER_SOURCE CURRENT_METER_ADC
#define DEFAULT_VOLTAGE_METER_SCALE  110  // R1 100k / R2 10k
#define DEFAULT_CURRENT_METER_SCALE  200  // INA186A3 100 V/V x 0.2 mOhm = 20 mV/A

#define USE_BEEPER
#define BEEPER_PIN           PA17
#define BEEPER_INVERTED                   // Q1 low-side N-FET: high = on (active buzzer, no PWM)
#define LED0_PIN             PA26
#define LED_STRIP_PIN        PA8          // FW1: hardware inverts, does not work as built

#define ENABLE_FB_OSD        1
#define USE_OSD_SD
#define OSD_W_PIN            PA14
#define OSD_EN_PIN           PA15
#define OSD_SYNC_PIN         PA16
#define OSD_FB_PICO_FLASH_FONT
```
Plus `pico_flash_mem.ld`: `PRIMARY_FLASH_LENGTH = 2M; FONT_LENGTH = 16K;` (FW6).

**What Betaflight cannot express:**
- LED-strip polarity (FW1).
- A horizontal canvas offset to absorb comparator delay (FW3).

Everything else is expressible. Motor order depends on the wiring: the motor pads form a pinwheel (M1 left edge, M2 bottom edge, M3 top edge, M4 right edge), so check `resource MOTOR` / `mixer` at bring-up.

## Verified OK (no finding)

**What this PR changed** (netlist d81e559 → 1522ed6):
- GPIO27 changed from `10V_ENABLE` to NC (U3 EN = +BATT).
- U12.6 (SH-6 pin 6) moved from `UART1_RX` to `PU0RX` (GPIO3). This removes the B2 contention with the ESP32 TX.
- SWCLK/SWDIO changed from NC to LGA pads 20/10, then TP32/TP31 (Base B.Cu, 79.58,61.41 / 78.32,55.15).

**RP2354A pin map:** every function sits on a legal pin (RP2350.pdf function table, p19/p591):
- SPI0 SCK/TX/RX: 18/19/20
- SPI1: 10/11/12
- UART0: 0/1
- UART1 on its AUX pins 6/7
- I2C0: 4/5
- ADC: 28/29 (26 = LED0, 27 free)
- PIO: 2/3, 8, 14-16, 22-25

There are no duplicate assignments. The PIO budget fits with FW5's override:
- PIO0: DShot, 4 SMs, 29/32 instructions.
- PIO1: PIOUART0 + LED strip.
- PIO2: OSD, 31/32 instructions.

**Boot:**
- RUN is tied to +3.3V, which is acceptable because it has an internal pull-up (RP2350.pdf p1338).
- BOOTSEL: U1 to QSPI_SS through R7 1 kΩ.
- XOSC is 12 MHz, the pico-sdk default.
- `bl` reboots into the bootrom.
- The pin numbers for SWD (24/25), USB DM/DP (51/52) and QSPI_SS (60) match the datasheet (p1338).

**USB:**
- No swap. USB1 A6/B6 = `USB_D+` → J90/J91 pad 42 → R9 → U2.52 USB_DP. A7/B7 = `USB_D-` → pad 37 → R8 → U2.51 USB_DM.
- All 46 LGA pads match by pure translation (−34.232, +8.374 mm) with identical nets on both PCBs.
- CC1/CC2 each have their own 5.1 kΩ.
- VBUS reaches +4v5 only through D3, with no VBUS sense. Betaflight falls back to "VCP connected" (`src/main/drivers/usb_io.c:56-70`).
- `kicad-cli pcb drc`: 0 unconnected on both boards.

**ELRS:** the ESP32-C3 wiring equals `RX/Generic C3 2400.json:2-20` exactly:
- serial_rx 20 / tx 21
- busy 3, dio1 1, rst 2
- miso 5 / mosi 4 / sck 6 / nss 7
- led_rgb 8, button 9

The ESP32-C3 datasheet confirms the pins (p14) and the straps GPIO2 = 1, GPIO8 = 1, GPIO9 = 0/1 (p26; R111/R112/R113 pull-ups, TP9). The upload methods include `betaflight` passthrough (targets.json `generic/rx_2400/c3-plain`). On the SX1281, DIO2/DIO3 being NC and the SPI auto-detect are fine (SX1281 p59).

**AM32:** pins match `HARDWARE_GROUP_AT_B` (input PB4 on TMR3_CH1; A = PA10/PB1, B = PA9/PB0, C = PA8/PA7; `Inc/targets.h:4889-4922`) plus `AT_045` (comparator PA0/PA4/PA5, common PA1; `:5101-5105`).
- The four ESC MCUs are wired identically.
- The NSG2065Q inputs are in phase (non-inverted; NSG2065Q.pdf p4), and VIH = 2.5 V (p6).
- The best-fit target is `OPENESC_20_F421` / `OPENESC_30_F421` (`Inc/targets.h:2111-2129`: AT_B + AT_045 + NO_VOLTAGE_SENSE + NO_CURRENT_SENSE). The AT32DEV, FLYWOO and TBS variants would read the NC pins PA3/PA6.
- The bootloader builds for PB4 (AM32-bootloader `Makefile:27`).
- Each MOTOR line has a 220 Ω series resistor (R39/R58/R77/R96) at the ESC.

**OSD levels:** black 0.26 V and white 1.06 V at U9.B2 (R27 3.9 k / R28 12 k / R29 1.4 k), matching CIRCUIT_REVIEW O8. The sync output is push-pull and active-low, as the PIO program expects.

## Already known (confirmed still holding)
- **+10V:** U3 EN = VIN = +BATT (always on with battery, 9aba717).
- **Product choices:** SX1281 and microSD are fitted, as in the owner's product decisions.
- **Rsense2:** 0.2 mΩ, MPN ASR-S-3-0.2F, Manufacturer field still empty.
- **Earlier review, still open (firmware-relevant), S9:** ESP32-C3 CHIP_EN is an RC only, and GPIO27 is free but unused. The FC cannot reset or strap the C3, so ELRS passthrough works only while ELRS is running, and a blank or bricked C3 needs TP9 (Base B.Cu 79.70,67.70) shorted through a power cycle. GPIO27 → CHIP_EN would also work through Betaflight PINIO (`src/main/target/common_pre.h:220`).
- **Earlier review, still open, S10:** D9 (WS2812, Base B.Cu 75.91,76.49) runs on +3V3, below its 3.5 V VDD minimum (XL-1010RGBC p4).
- **Earlier review, still open, O7:** Card1 VDD is on +3V3 (Base LDO U23), while its SPI master runs from +3.3V (Core LDO U7).
