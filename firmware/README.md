# OpenAIO firmware

OpenAIO runs stock firmware on three processors. The target files for Betaflight are in this folder; AM32 and
ExpressLRS use upstream targets.

| Processor | Ref | Firmware | Target | Notes |
|---|---|---|---|---|
| RP2354A flight controller | U2 | Betaflight | `OPENAIO`: `betaflight/configs/OPENAIO/` | not registered upstream; `MANUFACTURER_ID` is a placeholder in `config.h` |
| 4x AT32F421G8U7 ESC | U13, U15, U17, U19 | AM32 | `OPENESC_20_F421`, bootloader `AM32_F421_BOOTLOADER_PB4` | [am32.md](am32.md) |
| ESP32-C3 + SX1281 receiver | U22, U21 | ExpressLRS | `Generic ESP32C3 2.4Ghz RX` (`Generic C3 2400.json`) | [elrs.md](elrs.md) |

| File | Content |
|---|---|
| [PINOUT.md](PINOUT.md) | GPIO map of the RP2354A, SH-6, motor pads, ELRS and ESC MCU pins, from the netlist |
| [ISSUES.md](ISSUES.md) | What the board blocks or limits for each firmware, with status |
| [am32.md](am32.md) | AM32 target, files, flashing paths |
| [elrs.md](elrs.md) | ExpressLRS target, flashing paths, ELRS enable |
| `betaflight/configs/OPENAIO/config.h` | Pin and feature definitions |
| `betaflight/configs/OPENAIO/config.mk`, `pico_flash_mem.ld` | 2 MB flash layout for the RP2354A (1968 KB code, 64 KB config, 16 KB OSD font) |
| [../research/IO-CONSTRAINTS.md](../research/IO-CONSTRAINTS.md) | RP2350 and Betaflight pin constraints behind the map |

## Betaflight target

- Betaflight master `4dea42a9` and betaflight/config `e1d87e7e` were the upstream references for `config.h`.
- Build from a Betaflight checkout with `make fwo CONFIG=OPENAIO CONFIG_DIR=<absolute path to firmware/betaflight>`,
  the same layout as OpenAIO-Whoop. No build was run for this repository, so the command and the 1968 KB image limit
  are unchecked.
- Blackbox is the microSD card on SPI0; the IMU is the BMI270 on SPI1; the analog OSD is the PIO framebuffer OSD on
  PIO2; DShot (bidirectional) runs on PIO0.
- Gyro alignment is `CW180_DEG` with forward at the SH-6 edge. Confirm it in the configurator Setup tab.
- `config.h` comments still carry pin cross-references from the retired Base and Core split (LGA pad numbers, J45 and
  SH-6 pin 6 sharing `PU0RX`, TP42/TP43). The `#define` pins match the current netlist; read [PINOUT.md](PINOUT.md)
  for the endpoints.

## First flash

| Processor | First flash | Later |
|---|---|---|
| RP2354A | USB-C with the BOOTSEL button (U1) held at plug-in; there are no SWD pads | Betaflight configurator over USB, or CLI `bl` |
| AT32F421 (ESC) | SWD on TP1 to TP8 (B.Cu), once per ESC, bootloader first | Betaflight 4-way passthrough, battery connected |
| ESP32-C3 | UART download mode (TP9 to GND at reset) over J54/J55 | Betaflight passthrough or WiFi |
