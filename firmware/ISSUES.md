# OpenAIO firmware issues: what the board blocks or limits

Netlist facts are from `kicad-cli sch export netlist` of `hardware/OpenAIO.kicad_sch` (2026-10-16). Firmware facts cite
upstream sources by file and line; those citations were not re-checked on 2026-10-16.

Upstream sources:
- **[BF]** betaflight/betaflight master `4dea42a9`.
- **[CFG]** betaflight/config `e1d87e7e`.
- **AM32** `50234143`.
- **ExpressLRS/targets** `42ed776a`.

Datasheet pages refer to the PDFs in `hardware/KiCad-Library/datasheet/`.

Severity: **BLOCKER** stock firmware cannot provide the function; **MAJOR** wrong or damaging behaviour; **MINOR**
degraded behaviour with a workaround; **NIT** documentation or naming.

| ID | Severity | Topic | Status |
|---|---|---|---|
| I1 | MAJOR | SBUS cannot run on a PIO UART | Worked around in `config.h`: hardware UART0 on GPIO2/3 |
| I2 | BLOCKER (LED strip) | LED strip stage inverting (Q2, R14) | Open |
| I3 | MAJOR | AT32 ESC MCUs powered from USB while gate-driver VCC is 0 V | Open |
| I4 | MINOR | TLV7031 delay shifts the PIO OSD about 22 px right | Open |
| I5 | MINOR | FC can reset the ESP32-C3 (`ELRS_EN`) but cannot strap GPIO9 | Partly resolved |
| I6 | NIT | No USB VBUS detect, no free GPIO | Open, harmless |
| I7 | MINOR | Motor pad names (U24 symbol) run in reverse of MOTOR1-4 | Open, set the order at bring-up |
| I8 | NIT | No forward marking, gyro alignment is an assumption | Open |
| I9 | NIT | J54 and J55 are the ELRS link, not a spare UART | Open |
| I10 | MAJOR | SH-6 pin 6 shares `UART1_RX` with the ESP32-C3 TX | Open, needs ELRS off for SBUS |
| I11 | MINOR | ELRS status LED D9 on +3.3V, below its 3.5 V minimum | Open |
| I12 | NIT | ESP32-C3 GPIO10 tied to GND | Harmless |
| I13 | NIT | BMI270 INT2 on a one-node net `/IMU/CLKIN` | Harmless |
| I14 | NIT | microSD DAT1/DAT2 floating, no pull-ups on CMD/DAT0 | Open, unverified risk |
| I15 | handled | 2 MB flash against the upstream 8 MB/4 MB defaults | `config.mk` + `pico_flash_mem.ld`; image size not verified |
| I16 | handled | PIO2 overflows with LED strip + FB OSD | `PIO_LEDSTRIP_INDEX 1`; PIOUART1 must stay unused |
| I17 | NIT | AT32 NRST and VTref not on test pads | Open |
| I18 | NIT | No SWD pads for the RP2354A | Open, USB BOOTSEL only |

## I1: SBUS cannot run on a PIO UART (MAJOR, worked around)

- The PIO UART refuses even parity: `serialUART_pio()` returns false for `SERIAL_PARITY_EVEN` ([BF `uart/uart_pio.c:275-277`]).
- SBUS always opens with `SERIAL_STOPBITS_2 | SERIAL_PARITY_EVEN` ([BF `rx/sbus.c:81-82,206-216`]).
- Workaround in `config.h`: `UART0_TX/RX_PIN = PA2/PA3` (hardware UART0 on its F11 AUX pins, supports 8E2 and pad
  inversion); the SH-6 pair GPIO0/1 is `PIOUART0` (8N1 MSP DisplayPort).
- Pad names are swapped against the firmware ports: J44/J45 (`PIOUART0_TX`, `PU0RX`) are Betaflight UART0; J49/J48
  and SH-6 pins 3/4 (`UART0_TX/RX`) are Betaflight PIOUART0.
- On this board J45 is the only endpoint of `/Pads/PU0RX`; SH-6 pin 6 is on `UART1_RX` (I10).

## I2: LED strip stage is inverting (BLOCKER for the LED strip)

- Q2 AP1606: gate `/RP2354A/LED_STRIP_L` (GPIO8), source GND, drain `LED_STRIP`; R14 2.4k pulls `LED_STRIP` up to +5V.
  `LED_STRIP` goes to J20, J21, J31, J32.
- The WS2812 PIO program drives the pin directly with no inversion option ([BF `light_ws2811strip_pico.c:63-101`]), so
  the line idles high and every bit is inverted.
- A working stage needs a non-inverting buffer that idles low at reset (RP2350 pads reset with the pull-down on).

## I3: AT32 ESC MCUs powered from USB while gate-driver VCC is 0 V (MAJOR)

- U13/U15/U17/U19 pin 17 VDD = `+3.3V`, from U7, from `+4v5`. D3 feeds `+4v5` from `+5V_USB`, so the ESC MCUs run on
  USB alone.
- `+10V` (NSG2065Q VCC, U14/U16/U18/U20 pin 4) comes from U3 with EN tied to `+BATT`, so it is 0 V without a battery.
- AM32 plays its startup tune unconditionally on the AT421 (`Src/main.c:1893`) and drives the phases through
  `comStep()` (`Src/sounds.c:118-142`). HIN/LIN then see 3.3 V while VCC is 0 V; the NSG2065Q datasheet limits VIN
  to VCC + 0.3 V (abs max table).
- Do not power ESC-populated boards from USB alone.

## I4: PIO OSD shifted about 22 px right by the sync comparator delay (MINOR)

- U11 TLV7031 out is `/OSD/OSD_SYNC` (GPIO16); IN+ = `/OSD/VID_DC`, IN- = GND. Propagation delay 3 us (TLV7031
  datasheet tPHL/tPLH).
- At 75 MHz the PIO delay is fixed in the program ([BF `osd/osd_tx.pio:19-20,42-44`], [BF `osd_pico.c:263`]); there is
  no horizontal offset setting.
- 3 us is about 22.5 px, about 2 columns of 12 px. Text still fits in active video with no margin against overscan.
  Comparator delay jitter shows as horizontal jitter.
- Workaround: keep OSD elements out of the rightmost column.

## I5: ESP32-C3 reset and strapping (MINOR)

- `ELRS_EN` (GPIO27) drives CHIP_EN through R115 1k; R114 10k to +3.3V and C84 1 uF hold it up; JP2 (solder jumper,
  normally open) pulls CHIP_EN to GND and forces ELRS off.
- GPIO9 (boot strap) has only R113 10k to +3.3V and TP9. The FC cannot enter ROM download mode by itself, so a blank
  or bricked C3 needs TP9 shorted to GND through a reset (`elrs.md`).

## I6: No USB VBUS detect (NIT)

- USB1 A4/A9 `+5V_USB` goes only to D3. With no `USB_DETECT_PIN`, `usbCableIsInserted()` falls back to "VCP connected"
  ([BF `drivers/usb_io.c:56-70`]). All 30 GPIO are used.

## I7: Motor pad numbering (MINOR)

- U24 pins 12-14 are named 4A/4B/4C but carry `/1A /1B /1C` (ESC1, `MOTOR1`, GPIO25); pins 21-23 are named 1C/1B/1A and
  carry `/4x` (ESC4). ESC2 and ESC3 are crossed the same way (PINOUT.md).
- Set the Quad-X order at bring-up with the configurator motor reorder (`motor_output_reordering`, honoured by the PIO
  DShot driver [BF `dshot_pico.c:396-397,441-442`]).

## I8: No forward marking (NIT)

- U8 BMI270 is on F.Cu rotated 180 degrees. `config.h` sets `GYRO_1_ALIGN CW180_DEG`, assuming forward is the SH-6
  edge. If forward is the other edge use `CW0_DEG`. Confirm in the configurator Setup tab.

## I9: J54 and J55 are the ELRS link (NIT)

- J54 is `UART1_TX` (GPIO6, ESP32 U0RXD); J55 is `UART1_RX` (GPIO7, ESP32 U0TXD, push-pull). A device that drives J55
  fights the ESP32. They are ELRS service pads (`elrs.md`).

## I10: SH-6 pin 6 shares `UART1_RX` with the ESP32-C3 TX (MAJOR for SBUS)

- Net `UART1_RX` = U2.10 (GPIO7), U22.28 (ESP32-C3 U0TXD), U12.6 (SH-6 pin 6), J55.
- An air unit that drives SBUS on SH-6 pin 6 contends with the ESP32 TX unless ELRS is held in reset (`ELRS_EN` low,
  `config.h` PINIO1, or JP2 closed). SBUS input then uses UART1 (`SERIALRX_PROVIDER SBUS`).
- A GPS on J44/J45 uses UART0 (GPIO2/3) and does not conflict.

## I11: ELRS status LED D9 on +3.3V (MINOR, LED only)

- D9 XL-1010RGBC-WS2812B VDD (pin 2) = `+3.3V`; the datasheet minimum is 3.5 V. The LED may be dim, show wrong
  colours or stay dark. The radio link is not affected.

## I12: ESP32-C3 GPIO10 tied to GND (NIT)

- U22.16 is on `GND`. `Generic C3 2400.json` does not use GPIO10.

## I13: BMI270 INT2 on a one-node net (NIT)

- `/IMU/CLKIN` has only U8.9 (INT2). Betaflight's gyro CLKIN is used by the ICM426xx driver only. Harmless, but the
  name suggests a feature that does not exist.

## I14: microSD DAT1/DAT2 floating (NIT, unverified)

- Card1.1 (DAT2) and Card1.8 (DAT1) are unconnected. Only CS (DAT3) has a pull-up (R34 10k). If a card misbehaves at
  init, check this first.

## I15: Flash size (handled)

- RP2354A has 2 MB in package. Upstream defaults to `PICO_FLASH_SIZE_BYTES=8388608` / `MCU_FLASH_SIZE 8192` and
  `PRIMARY_FLASH_LENGTH = 4M`. `config.mk` (2048 KB) and `pico_flash_mem.ld` (2M, 16K font) override them.
- Not verified: the firmware image must fit 1968 KB; no build was run.

## I16: PIO budget (handled)

- By default the LED strip and the FB OSD share PIO2. The OSD program is 31 instructions and the WS2812 program is 4,
  which exceeds 32. `config.h` sets `PIO_LEDSTRIP_INDEX 1`: PIO1 holds PIOUART0 (2 SM) and the LED strip (1 SM).
- Do not assign PIOUART1: it would need 2 more SMs, 5 of 4.

## I17: AT32 NRST and VTref not on test pads (NIT)

- TP1 to TP8 are PA13/PA14 per ESC only. Connect-under-reset is impossible; a plain SWD attach works because AM32
  never remaps PA13/PA14.

## I18: No SWD pads for the RP2354A (NIT)

- U2 SWCLK (pin 24) and SWDIO (pin 25) are unconnected; the SWD test pads TP42/TP43 were removed and the footprint
  has no pad 24. Programming and recovery are by USB (BOOTSEL button U1, or the `bl` CLI command).
