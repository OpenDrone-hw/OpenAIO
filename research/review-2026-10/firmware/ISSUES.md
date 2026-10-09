# OpenAIO firmware issues: what the netlist blocks or limits

**Baseline:** OpenAIO `be152bb` (branch `work/d81e559`). The netlist comes from `kicad-cli sch export netlist`, and pad nets were cross-checked on both PCBs.

**Upstream sources:**
- **[BF]:** betaflight/betaflight master `4dea42a9`.
- **[CFG]:** betaflight/config `e1d87e7e`.
- **AM32:** `50234143`.
- **ExpressLRS/targets:** `42ed776a`.

**Datasheets:** page numbers refer to the PDFs in `hardware/KiCad-Library/datasheet/`.

**Severity:**
- **BLOCKER:** stock firmware cannot provide the function on the board as it stands.
- **MAJOR:** wrong or damaging behaviour, or a planned function that does not work as designed.
- **MINOR:** degraded behaviour, with a workaround.
- **NIT:** documentation or naming.

| ID | Severity | Topic | Status |
|---|---|---|---|
| I1 | MAJOR | SBUS cannot run on a PIO UART, so PU0RX on PIOUART0 does not work | **Worked around in `config.h`**: hardware UART0 moved to GPIO2/3 |
| I2 | BLOCKER (LED strip) | LED-strip stage still inverting (Q2) at be152bb | Owner fix decided (TXU0101), **not yet in the netlist** |
| I3 | MAJOR | AT32 ESC MCUs powered from USB while gate-driver VCC = 0 V | Owner fix decided (battery-only LDO), **not yet in the netlist** |
| I4 | MINOR | TLV7031 delay shifts the PIO OSD about 22 px right, with no firmware offset | Open |
| I5 | MINOR | FC cannot reset or strap the ESP32-C3 | Open |
| I6 | NIT | No USB VBUS detect | Open, harmless |
| I7 | MINOR | Motor pad names (U24 symbol) run in reverse of MOTOR1-4; no M1-M4 labels | Open, set the order at bring-up |
| I8 | NIT | No forward marking, so the gyro alignment is an assumption | Open |
| I9 | NIT | J54/J55 "TX1/RX1" are the ELRS link, not a spare UART | Open |
| I10 | NIT | PU0RX shared by J45 and SH-6 pin 6 | Open |
| I11 | MINOR | ELRS status LED D9 on +3V3, below its 3.5 V minimum | Open |
| I12 | NIT | ESP32-C3 GPIO10 tied to GND | Harmless |
| I13 | NIT | BMI270 INT2 on a one-node net named `/IMU/CLKIN` | Harmless |
| I14 | NIT | microSD DAT1/DAT2 floating; no pull-ups on CMD/DAT0 | Open, unverified risk |
| I15 | NIT | microSD VDD on the Base +3V3, SPI host IO on the Core +3.3V | Open |
| I16 | handled | 2 MB flash against the upstream 8 MB/4 MB defaults | Handled by `config.mk` + `pico_flash_mem.ld`; image size not verified |
| I17 | handled | PIO2 overflows with LED strip + FB OSD | Handled by `PIO_LEDSTRIP_INDEX 1`; PIOUART1 must stay unused |
| I18 | NIT | AT32 NRST and VTref not on test pads | Open |

---

## I1: SBUS cannot run on a PIO UART (MAJOR, worked around in `config.h`)

**Netlist:** net `PU0RX` ties together:
- U2.5 (GPIO3);
- U12.6 (SH-6 pin 6, the air-unit SBUS output), through LGA pad 40;
- J45 "PIO_RX0";
- J46 (DNP).

J44 "PIO_TX0" is on `/Pads/PIOUART0_TX` (GPIO2). PLAN.md decision B2 routed SH-6 pin 6 here, "PU0RX (GPIO3, PIO UART)".

**Firmware:**
- The PIO UART refuses even parity. `serialUART_pio()` returns false when `SERIAL_PARITY_EVEN` is requested ([BF `src/platform/PICO/uart/uart_pio.c:275-277`]).
- When it fails, the port open returns NULL ([BF `src/platform/PICO/uart/serial_uart_pico.c:168-179`]).
- The PIO RX program has no parity slot: 8 data bits, then the stop-bit check ([BF `uart_rx_program.c:48-58`]).
- SBUS always opens with `SERIAL_STOPBITS_2 | SERIAL_PARITY_EVEN` ([BF `src/main/rx/sbus.c:81-82,206-216`]). Overriding `SBUS_PORT_OPTIONS` without parity does not help: the parity bit would land in the stop-bit slot and about half the bytes would be dropped as framing errors.
- **Result:** with PIOUART0 on GPIO2/3, the configuration in critique round 1, the SBUS port never opens. Critique round 1 checked only the inversion path (`gpio_set_inover`), which is fine.

**Workaround (used in `config.h`):**
- GPIO2/3 are UART0 TX/RX in function F11, UART_AUX (RP2350.pdf p19). Betaflight lists them for UART0 ([BF `uart_hw.c:43,59`]) and selects the AUX function automatically ([BF `uart_hw.c:252,259`]).
- So `UART0_TX/RX_PIN = PA2/PA3`. The hardware UART supports 8E2 ([BF `uart_hw.c:269-274`]), pad inversion and the RX pull-down.
- The SH-6 pair GPIO0/1 moves to `PIOUART0` (8N1 MSP DisplayPort).
- DJI-style MSP + SBUS then run at the same time.
- SmartAudio and Tramp on SH-6 still work on the PIO UART: it supports half duplex and 2 stop bits ([BF `uart_tx_program.c:53-67`; `uart_pio.c:283-287`]).

**Cost:** the pad names disagree with the firmware port names:
- J44/J45 "PIO_TX0/PIO_RX0" are Betaflight **UART0**.
- J49/J48 "TX0/RX0" and SH-6 pins 3/4 are Betaflight **PIOUART0**.

**Board fix (optional, no electrical change):** relabel J44/J45 as "TX0/RX0 (SBUS)" and J48/J49 as "PTX/PRX", or rename the nets to match.

## I2: LED-strip stage still inverting at be152bb (BLOCKER for the LED strip until the planned change lands)

**Netlist:**
- Q2 AP1606 (N-FET): G = `/RP2354A/LED_STRIP_L` (U2.12, GPIO8), S = GND, D = `LED_STRIP`.
- R14 2.4k pulls `LED_STRIP` up to +5V.
- `LED_STRIP` crosses LGA pad 46 to J20/J21/J31/J32.
- `grep TXU0101 hardware/*.kicad_sch` finds nothing. The owner decision (PLAN.md "LED strip (critique F1)", commit `c1da3e7`) is recorded but not yet drawn.

**Firmware:**
- The WS2812 PIO program drives the pin straight from side-set, with no output inversion ([BF `src/platform/PICO/light_ws2811strip_pico.c:63-101`]). There is no CLI inversion setting.
- With Q2, the line idles high and every bit is inverted, so the LED strip does not work.

**`config.h` assumes the TXU0101 version.** For the new stage to work with stock firmware:
- **Non-inverting:** A = GPIO8, B = pads through 200R.
- **OE tied enabled.**
- **Idle low at reset.** RP2350 pads reset with the pull-down on (PADS_BANK0 GPIOx.PDE reset = 1, RP2350.pdf p788), so GPIO8 idles low before firmware runs. Do not add a pull-up on the A side.

## I3: AT32 ESC MCUs powered from USB while gate-driver VCC = 0 V (MAJOR, fix decided, not yet in the netlist)

**Netlist:**
- U13/U15/U17/U19 pin 17 VDD = `+3V3`.
- U23 TLV75533 IN = EN = `+4v5`.
- D3 feeds `+4v5` from `+5V_USB`, so the ESC MCUs run on USB alone.
- U3 VIN = EN = `+BATT` produces `+10V` = NSG2065Q VCC (U14.4 etc.), which is 0 V without a battery.

**Firmware:**
- AM32 plays its startup tune unconditionally on the AT421 (`Src/main.c:1893`).
- The tune drives phases through `comStep()`, even when a custom tune is stored (`Src/sounds.c:118-142`).
- No AM32 or Betaflight setting prevents this. The HIN/LIN inputs see 3.3 V while VCC = 0 V; the critique cites NSG2065Q.pdf p5 for VIN at most VCC + 0.3 V.

**Fix:** the owner-approved battery-only 3.3 V LDO for the four AT32s (PLAN.md "ESC MCU supply (critique F2)"). Until then, do not power ESC-populated boards from USB alone.

## I4: PIO OSD shifted about 22 px right by the sync comparator delay (MINOR)

**Netlist:** U11 TLV7031 OUT goes to `/OSD/OSD_SYNC`, U2.27 (GPIO16). IN+ = `/OSD/VID_DC`, IN- = GND.

**Datasheet:** TLV7031 propagation delay is 3 us (TLV7031.pdf p1, p8 tPHL/tPLH).

**Firmware:**
- PAL starts pixels 6 + (1+26)(1+29) + 12 = 828 PIO clocks after the sync edge the PIO sees ([BF `src/platform/PICO/osd/osd_tx.pio:19-20,42-44`]).
- At 75 MHz ([BF `osd_pico.c:263`]) that is 11.04 us, followed by 368 px x 10 clocks = 49.07 us.
- The shifts are assembled into the PIO program. There is no CLI or VCD horizontal offset: `osd_pico.c` includes `pg/vcd.h` but reads no offset from it.

**Effect:**
- **Shift:** 3 us = 22.5 px, about 2 columns of 12 px, to the right.
- **PAL canvas end:** moves from 60.1 us to 63.1 us after sync, against the end of active video at about 62.5 us.
- **Text still fits:** the character area (360 px) ends at about 62.0 us, so text still lands inside active video, but with no margin against display overscan.
- **Jitter:** variation in the comparator delay appears as horizontal jitter.

**Workarounds:**
- **Firmware/user:** keep OSD elements out of the rightmost column.
- **Board:** fit a comparator with tPD of about 0.3 us or less, or raise the overdrive (threshold at mid-sync).

## I5: FC cannot reset or strap the ESP32-C3 (MINOR)

**Netlist:**
- U22.7 CHIP_EN has only R114 10k to +3V3 and C84 1 uF.
- U22.15 GPIO9 has only R113 10k pull-up and TP9.
- U2.41 GPIO27 is `unconnected-(U2-GPIO27_ADC1-Pad41)`.

**Effect:**
- Betaflight passthrough flashing works only while ELRS firmware is running.
- A blank (factory) or bricked C3 needs TP9 shorted to GND through a power cycle (`elrs.md` path 2).

**Fix:** route GPIO27 to CHIP_EN (or to GPIO9), driven as a Betaflight PINIO (`USE_PINIO` is in [BF `src/main/target/common_pre.h`] classic builds).

## I6: No USB VBUS detect (NIT)

**Netlist:** USB1 A4/A9 `+5V_USB` goes only to D3 (to `+4v5`). No GPIO senses it.

**Firmware:** with no `USB_DETECT_PIN`, `usbCableIsInserted()` falls back to "VCP connected" ([BF `src/main/drivers/usb_io.c:56-70`]). That is acceptable.

**Optional fix:** a divider from `+5V_USB` to a free GPIO. GPIO27 is the only free pin, and I5 competes for it.

## I7: Motor pad numbering (MINOR)

**Netlist:**
- U24 (AIO_outline) pins 12-14 are named **4A/4B/4C** but carry `/1A /1B /1C` (ESC1, `MOTOR1`, GPIO25).
- Pins 21-23 are named **1C/1B/1A** and carry `/4x` (ESC4, `MOTOR4`).
- ESC2 and ESC3 are crossed the same way (3x and 2x).

**Base PCB:**
- The pad groups sit at the left edge, lower half (ESC1); bottom edge, left half (ESC2); top edge, right half (ESC3); right edge, upper half (ESC4). See `PINOUT.md`.
- No M1-M4 text was found in the Base `gr_text` items (DJI, 5V, LED, -, +, B+, B-, Open) or in the U24 footprint text.

**Effect:** the Quad-X order cannot be read off the board. Set it at bring-up with the configurator's motor-reorder, which writes `motor_output_reordering` and is honoured by the PIO DShot driver ([BF `src/platform/PICO/dshot_pico.c:396-397,441-442`]).

**Board fix:** rename the symbol pins to match `MOTORn` and add M1-M4 pad labels (owner rule: every pad gets a function label).

## I8: No forward marking, so the gyro alignment is an assumption (NIT)

**Evidence:**
- U8 BMI270 is at 180 deg on Core F.Cu, with pad 1 top-left.
- The Core maps onto the Base by pure translation (J91 = J90 nets, critique round 1).
- BMI270 axes: with pin 1 top-left, +X points up and +Y left (BMI270.pdf p144).

**Choice in `config.h`:** `GYRO_1_ALIGN CW180_DEG`, assuming forward = SH-6 edge and battery pads at the rear. If forward is the battery-pad edge, use `CW0_DEG`. Confirm in the Setup tab.

## I9: J54/J55 "TX1/RX1" are the ELRS link (NIT)

**Netlist:** J54 is on `UART1_TX` (GPIO6, ESP32 U0RXD). J55 is on `UART1_RX` (GPIO7, ESP32 U0TXD push-pull).

**Effect:** a device that drives J55 fights the ESP32. The pads are useful only as ELRS service pads (`elrs.md` path 2a).

## I10: PU0RX shared by J45 and SH-6 pin 6 (NIT)

**Netlist:** net `PU0RX` = J45, U12.6, J46 (DNP), U2.5.

**Effect:** a GPS on J44/J45 and an air unit that drives SBUS on SH-6 pin 6 cannot be connected together. These are either/or uses of Betaflight UART0 RX.

## I11: ELRS status LED D9 on +3V3 (MINOR, ELRS LED only)

**Netlist:** D9 XL-1010RGBC-WS2812B VDD (pin 2) = `+3V3`.

**Datasheet:** VDD 3.5-5.5 V (XL-1010RGBC-WS2812B.pdf p4, p5 minimum 3.5 V).

**Effect:** colours and timing are not guaranteed; the LED may stay dark. The radio link is not affected.

## I12: ESP32-C3 GPIO10 tied to GND (NIT)

**Netlist:** U22.16 GPIO10 is on `GND`.

**Effect:** `Generic C3 2400.json` does not use GPIO10, so there is no conflict today. A future layout that drives GPIO10 high would short it.

## I13: BMI270 INT2 on a one-node net `/IMU/CLKIN` (NIT)

**Netlist:** `/IMU/CLKIN` has one node, U8.9 INT2.

**Datasheet:** leave unused INT pins unconnected (BMI270.pdf p122). INT2_IO_CTRL resets to 0x00, with input and output disabled (p110).

**Firmware:** Betaflight's gyro CLKIN (`USE_GYRO_CLKIN`, [BF `src/platform/PICO/gyro_clkin_pico.c`]) is used only by the ICM426xx driver (`grep CLKIN src/main/drivers/accgyro/`). BMI270 has none.

**Effect:** harmless, but the net name suggests a feature that does not exist.

## I14: microSD DAT1/DAT2 floating; no pull-ups on CMD/DAT0 (NIT, unverified)

**Netlist:** Card1.1 (DAT2) and Card1.8 (DAT1) are unconnected. Only CS (DAT3) has a pull-up (R34 10k).

**Reference:** the SD physical-layer specification recommends pull-ups on CMD and DAT lines (10-100 kOhm). That document is not in the repo, so this rests on general knowledge.

**Effect:** many FCs ship this way and work. If a card misbehaves at init, this is the first thing to check.

## I15: microSD supply rail against the SPI host rail (NIT, earlier review O7)

**Netlist:** Card1.4 VDD = `+3V3` (Base U23). U2 IOVDD = `+3.3V` (Core U7). Both LDOs are fed from `+4v5`.

**Firmware:** no impact expected, because card init happens after boot.

## I16: Flash size (handled)

**Facts:**
- RP2354A has 2 MB (RP2350.pdf p14, p1331).
- Upstream defaults to `PICO_FLASH_SIZE_BYTES=8388608` / `MCU_FLASH_SIZE 8192` ([BF `src/platform/PICO/target/common/target_RP2350.mk:1-10`]).
- The upstream linker default is `PRIMARY_FLASH_LENGTH = 4M` ([BF `link/pico_flash_mem_defaults.ld:5`]), which would put the config area at 4 MB - 64 KB.

**Handling:** `config.mk` (2048 KB, 2097152 bytes) and `pico_flash_mem.ld` (2M, 16K font) override all three.

**Not verified:** the firmware image must fit 1968 KB. I did not run a build.

## I17: PIO budget (handled)

**Problem:** by default, the LED strip and the FB OSD share PIO2 ([BF `target_RP2350.h:100-106`]). The OSD program is 31 instructions ([BF `osd_tx.pio.h:60,122`]) and the WS2812 program is 4, which is more than 32.

**Handling:** `config.h` sets `PIO_LEDSTRIP_INDEX 1`. PIO1 then holds PIOUART0 (10 + 9 instructions, 2 SMs) and the LED strip (4, 1 SM).

**Constraint:** **do not assign PIOUART1.** It would need 2 more SMs, 5 of 4 in total.

## I18: AT32 NRST and VTref not on test pads (NIT)

**Netlist:** TP1-TP8 are only PA13/PA14 per ESC. NRST (pin 4) has R/C only.

**Effect:** connect-under-reset is impossible. A plain SWD attach works because AM32 never remaps PA13/PA14 (`am32.md`).
