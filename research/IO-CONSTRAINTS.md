# OpenAIO RP2354A pin constraints

What the RP2350 and Betaflight allow on each GPIO, for anyone who wants to move a signal. Sources: RP2350 datasheet
(Table 3 section 1.2.3 and Table 677 "GPIO Bank 0 Functions"), pico-sdk in the Betaflight tree, Betaflight branch
`pico-enable-osd-hd`. Firmware cites are relative to `src/platform/PICO/` in the Betaflight tree. The pin assignment of
this board is `firmware/betaflight/configs/OPENAIO/config.h`, listed in [PINOUT.md](../firmware/PINOUT.md).

OPENAIO puts HW UART0 on GPIO2/3 (F11 AUX, for SBUS 8E2) and PIOUART0 on GPIO0/1. It sets `PIO_LEDSTRIP_INDEX 1`
(config.h) because the OSD program takes 31 of 32 PIO2 slots; the target.h default is the LED strip on PIO2
(`target/RP2350A/target.h:104-110`), which would fail next to the OSD (`osd/osd_pico.c:225-230`).

## 1. RP2350 GPIO function table, GPIO0-29 (QFN-60 RP2350A)

Verified: the generator rule below reproduces all 30 rows of datasheet Table 677 (0 mismatches, checked by script against the pdftotext of the PDF).
Rules (mod = GPIO mod 4):
- SPI: instance SPI0 for GPIO 0-7,16-23; SPI1 for 8-15,24-29. mod0 RX(MISO), mod1 CSn, mod2 SCK, mod3 TX(MOSI).
- UART F2: instance UART0 for GPIO 0-3,12-19,28-29; UART1 for 4-11,20-27. mod0 TX, mod1 RX, mod2 CTS, mod3 RTS.
- UART F11 (UART_AUX): only on mod2 = TX, mod3 = RX, same instance as that pin's F2 UART.
- I2C F3: mod0 I2C0 SDA, mod1 I2C0 SCL, mod2 I2C1 SDA, mod3 I2C1 SCL.
- PWM F4: slice = (GPIO>>1)&7, channel A for even, B for odd. (Slices are shared: GPIO n and n+16 share a slice.)
- ADC: GPIO26..29 = ADC0..3 (RP2350A). No other ADC pins. PIO0/1/2 and SIO reach every GPIO.
- Caution: "each peripheral input should only be selected by one GPIO" (datasheet, after Table 677). SPI/UART/I2C inputs from two pins are OR-ed.

| GPIO | SPI | UART F2 | UART_AUX F11 | I2C | PWM | ADC |
|---|---|---|---|---|---|---|
| 0 | SPI0.RX | UART0.TX | - | I2C0.SDA | PWM0A | - |
| 1 | SPI0.CSN | UART0.RX | - | I2C0.SCL | PWM0B | - |
| 2 | SPI0.SCK | UART0.CTS | UART0.TX | I2C1.SDA | PWM1A | - |
| 3 | SPI0.TX | UART0.RTS | UART0.RX | I2C1.SCL | PWM1B | - |
| 4 | SPI0.RX | UART1.TX | - | I2C0.SDA | PWM2A | - |
| 5 | SPI0.CSN | UART1.RX | - | I2C0.SCL | PWM2B | - |
| 6 | SPI0.SCK | UART1.CTS | UART1.TX | I2C1.SDA | PWM3A | - |
| 7 | SPI0.TX | UART1.RTS | UART1.RX | I2C1.SCL | PWM3B | - |
| 8 | SPI1.RX | UART1.TX | - | I2C0.SDA | PWM4A | - |
| 9 | SPI1.CSN | UART1.RX | - | I2C0.SCL | PWM4B | - |
| 10 | SPI1.SCK | UART1.CTS | UART1.TX | I2C1.SDA | PWM5A | - |
| 11 | SPI1.TX | UART1.RTS | UART1.RX | I2C1.SCL | PWM5B | - |
| 12 | SPI1.RX | UART0.TX | - | I2C0.SDA | PWM6A | - |
| 13 | SPI1.CSN | UART0.RX | - | I2C0.SCL | PWM6B | - |
| 14 | SPI1.SCK | UART0.CTS | UART0.TX | I2C1.SDA | PWM7A | - |
| 15 | SPI1.TX | UART0.RTS | UART0.RX | I2C1.SCL | PWM7B | - |
| 16 | SPI0.RX | UART0.TX | - | I2C0.SDA | PWM0A | - |
| 17 | SPI0.CSN | UART0.RX | - | I2C0.SCL | PWM0B | - |
| 18 | SPI0.SCK | UART0.CTS | UART0.TX | I2C1.SDA | PWM1A | - |
| 19 | SPI0.TX | UART0.RTS | UART0.RX | I2C1.SCL | PWM1B | - |
| 20 | SPI0.RX | UART1.TX | - | I2C0.SDA | PWM2A | - |
| 21 | SPI0.CSN | UART1.RX | - | I2C0.SCL | PWM2B | - |
| 22 | SPI0.SCK | UART1.CTS | UART1.TX | I2C1.SDA | PWM3A | - |
| 23 | SPI0.TX | UART1.RTS | UART1.RX | I2C1.SCL | PWM3B | - |
| 24 | SPI1.RX | UART1.TX | - | I2C0.SDA | PWM4A | - |
| 25 | SPI1.CSN | UART1.RX | - | I2C0.SCL | PWM4B | - |
| 26 | SPI1.SCK | UART1.CTS | UART1.TX | I2C1.SDA | PWM5A | ADC0 |
| 27 | SPI1.TX | UART1.RTS | UART1.RX | I2C1.SCL | PWM5B | ADC1 |
| 28 | SPI1.RX | UART0.TX | - | I2C0.SDA | PWM6A | ADC2 |
| 29 | SPI1.CSN | UART0.RX | - | I2C0.SCL | PWM6B | ADC3 |
Pasteable dict (keys are lowercase peripheral names, `_aux` = F11, spiN roles rx=MISO, tx=MOSI):

```python
GPIO_FUNCS = 
{
  0: {'spi0': 'rx', 'uart0': 'tx', 'i2c0': 'sda', 'pwm': '0A'},
  1: {'spi0': 'csn', 'uart0': 'rx', 'i2c0': 'scl', 'pwm': '0B'},
  2: {'spi0': 'sck', 'uart0': 'cts', 'uart0_aux': 'tx', 'i2c1': 'sda', 'pwm': '1A'},
  3: {'spi0': 'tx', 'uart0': 'rts', 'uart0_aux': 'rx', 'i2c1': 'scl', 'pwm': '1B'},
  4: {'spi0': 'rx', 'uart1': 'tx', 'i2c0': 'sda', 'pwm': '2A'},
  5: {'spi0': 'csn', 'uart1': 'rx', 'i2c0': 'scl', 'pwm': '2B'},
  6: {'spi0': 'sck', 'uart1': 'cts', 'uart1_aux': 'tx', 'i2c1': 'sda', 'pwm': '3A'},
  7: {'spi0': 'tx', 'uart1': 'rts', 'uart1_aux': 'rx', 'i2c1': 'scl', 'pwm': '3B'},
  8: {'spi1': 'rx', 'uart1': 'tx', 'i2c0': 'sda', 'pwm': '4A'},
  9: {'spi1': 'csn', 'uart1': 'rx', 'i2c0': 'scl', 'pwm': '4B'},
  10: {'spi1': 'sck', 'uart1': 'cts', 'uart1_aux': 'tx', 'i2c1': 'sda', 'pwm': '5A'},
  11: {'spi1': 'tx', 'uart1': 'rts', 'uart1_aux': 'rx', 'i2c1': 'scl', 'pwm': '5B'},
  12: {'spi1': 'rx', 'uart0': 'tx', 'i2c0': 'sda', 'pwm': '6A'},
  13: {'spi1': 'csn', 'uart0': 'rx', 'i2c0': 'scl', 'pwm': '6B'},
  14: {'spi1': 'sck', 'uart0': 'cts', 'uart0_aux': 'tx', 'i2c1': 'sda', 'pwm': '7A'},
  15: {'spi1': 'tx', 'uart0': 'rts', 'uart0_aux': 'rx', 'i2c1': 'scl', 'pwm': '7B'},
  16: {'spi0': 'rx', 'uart0': 'tx', 'i2c0': 'sda', 'pwm': '0A'},
  17: {'spi0': 'csn', 'uart0': 'rx', 'i2c0': 'scl', 'pwm': '0B'},
  18: {'spi0': 'sck', 'uart0': 'cts', 'uart0_aux': 'tx', 'i2c1': 'sda', 'pwm': '1A'},
  19: {'spi0': 'tx', 'uart0': 'rts', 'uart0_aux': 'rx', 'i2c1': 'scl', 'pwm': '1B'},
  20: {'spi0': 'rx', 'uart1': 'tx', 'i2c0': 'sda', 'pwm': '2A'},
  21: {'spi0': 'csn', 'uart1': 'rx', 'i2c0': 'scl', 'pwm': '2B'},
  22: {'spi0': 'sck', 'uart1': 'cts', 'uart1_aux': 'tx', 'i2c1': 'sda', 'pwm': '3A'},
  23: {'spi0': 'tx', 'uart1': 'rts', 'uart1_aux': 'rx', 'i2c1': 'scl', 'pwm': '3B'},
  24: {'spi1': 'rx', 'uart1': 'tx', 'i2c0': 'sda', 'pwm': '4A'},
  25: {'spi1': 'csn', 'uart1': 'rx', 'i2c0': 'scl', 'pwm': '4B'},
  26: {'spi1': 'sck', 'uart1': 'cts', 'uart1_aux': 'tx', 'i2c1': 'sda', 'pwm': '5A', 'adc': 0},
  27: {'spi1': 'tx', 'uart1': 'rts', 'uart1_aux': 'rx', 'i2c1': 'scl', 'pwm': '5B', 'adc': 1},
  28: {'spi1': 'rx', 'uart0': 'tx', 'i2c0': 'sda', 'pwm': '6A', 'adc': 2},
  29: {'spi1': 'csn', 'uart0': 'rx', 'i2c0': 'scl', 'pwm': '6B', 'adc': 3},
}
```

Derived pin sets (what Betaflight can actually use, section 2):
- HW UART0 TX {0,2,12,14,16,18,28}, RX {1,3,13,15,17,19,29}
- HW UART1 TX {4,6,8,10,20,22,24,26}, RX {5,7,9,11,21,23,25,27}
- HW SPI0 SCK {2,6,18,22}, MISO {0,4,16,20}, MOSI {3,7,19,23}
- HW SPI1 SCK {10,14,26}, MISO {8,12,24,28}, MOSI {11,15,27}
- HW I2C0 SDA {0,4,8,12,16,20,24,28} SCL {1,5,9,13,17,21,25,29}; I2C1 SDA {2,6,10,14,18,22,26} SCL {3,7,11,15,19,23,27}

## 2. Betaflight PICO constraints (code-verified)

| Function | Constraint | Cite |
|---|---|---|
| HW UART pin validity | Tag must appear in the per-UART table. TX and RX are matched INDEPENDENTLY (any listed TX with any listed RX, no pairing). Non-matching pin: port gets no pins and silently stays unconfigured (log only under PICO_TRACE). | `uart/uart_hw.c:41-72` (UART0), `85-116` (UART1), match loop `144-159`; `UARTHARDWARE_MAX_PINS 8` at `target/RP2350A/target.h:42` |
| HW UART accepts F11 AUX? | YES, automatically. Funcsel = `UART_FUNCSEL_NUM` = `(gpio & 2) ? GPIO_FUNC_UART_AUX : GPIO_FUNC_UART` (pico-sdk `hardware_uart/include/hardware/uart.h:181`). So GPIO2/3,6/7,10/11,14/15,18/19,22/23,26/27 are AUX. The tables above already include them (e.g. PA2,PA3,PA6,PA7,PA10,PA11). | `uart/uart_hw.c:165,246,253` |
| HW UART format | 8E2/parity and 2 stop bits supported; SBUS inversion done by pad override. No CTS/RTS (flow control forced off). | `uart_hw.c:266-280`, `uart/serial_uart_pico.c:146-156` |
| PIO UART (PIOUART0/1) | ANY GPIO, TX and RX independent (separate SMs, each 1 pin). Only restriction: all pins of the PIO block within 0-31 or 16-47 (irrelevant for 0-29). No parity, no 2 stop bits: `serialUART_pio` returns false for them. | `uart/uart_pio.c:118-167`, `135-148`, `273-281`; TX `uart/uart_tx_program.c:68,85-86` (sideset = out = pin_tx, 1 pin); RX `uart/uart_rx_program.c:56-61` (in/jmp = pin) |
| PIO UART count/PIO | Max PIOUART0, PIOUART1, on PIO `PIO_UART_INDEX` (default 1), 4 SM/32 instr shared with LED strip in OPENAIO | `uart_pio.c:56-58`, `target.h:100-102` |
| SPI | SCK, MISO, MOSI MUST be in the hardware lists of ONE SPI instance (sets in section 1). The three may mix positions (e.g. SCK=10, MISO=12, MOSI=11 or MISO=8). All three must match or the device is not created. CSn: NOT hardware, plain GPIO via `csnPin`; ANY pin. `MAX_SPI_PIN_SEL 4` (only first 4 list entries searched; RP2350A lists have <=4). | `bus_spi_pico.c:66-130` (lists), `145-165` (match, all-three requirement at 161), funcsel `230-232`, `target.h:50`; CS toggled by IOHi/IOLo (`bus_spi_pico.c:267-269`) |
| SDCARD CS, GYRO CS | any GPIO (plain IO) | same as above |
| Gyro EXTI | any GPIO; per-GPIO IRQ via IO_IRQ_BANK0, one handler per pin | `exti_pico.c:25-41,74-77` |
| I2C | HW only, but pin check is loose: SDA index mod4 == 0 (I2C0) or 2 (I2C1); SCL index mod4 == 1 or 3 respectively, both < 30. SDA and SCL need NOT be adjacent (any SDA of its set with any SCL of its set). | `bus_i2c_pico.c:106-121` |
| DShot motors | PIO0 (`PIO_DSHOT_INDEX`), 1 SM per motor, ANY pin each, no adjacency, NO consecutive-pin requirement (set_pins count 1; bidir uses in/jmp on same pin). Max 4 motors (one PIO block); >4 returns false. Order of pins free. Pin must be free (not claimed). | `dshot_pico.c:59-67,364-367,383-401,424-453`; `dshot_bidir_pico.c:67-72`; `target.h:96-98` |
| LED strip (WS2812) | PIO driver, ANY single GPIO, 1 SM, 4 instr, no inversion option. Defaults to PIO2 which clashes with the OSD, so PIO1 override is mandatory. | `light_ws2811strip_pico.c:84-93,145-153` |
| OSD (fb_osd, PIO2) | **W, EN, SYNC must be three CONSECUTIVE ASCENDING GPIOs: EN = W+1, SYNC = EN+1.** Order is fixed (W lowest, SYNC highest). Reasons: `out/set pins` base=W count 2 (bit0=W, bit1=EN); SYNC is in-pin base/jmp pin. Code returns false (OSD dead) otherwise. Any base N with N+2 <= 29 works, N+2 may be any GPIO (no peripheral function needed, PIO funcsel only on W and EN). Needs all 31 of 32 PIO2 instructions, so nothing else on PIO2. Also needs 2 DMA channels. | `osd/osd_pico.c:26-27`, `138-153` (consecutive check), `224-232`, `248-255` (pindirs, in/jmp/set/out pins), sync-detect program `380-391`; pio program `osd/osd_tx.pio:49-56` (`wait PIN 0`, `jmp PIN`) |
| Beeper | any GPIO. If BEEPER_PWM_HZ is used it takes that pin's PWM slice (every GPIO has PWM F4) and `pwm_gpio_to_slice_num`; avoid sharing the slice with servo/PWM outputs (not used on OPENAIO). | `pwm_beeper_pico.c:71-77`, `38-44` |
| LED0, PINIO | plain GPIO, any | n/a |
| ADC (VBAT, CURR, RSSI, EXT1) | pins MUST be GPIO26..29 (RP2350A); anything else is silently skipped. Max 4 channels total (`PICO_ADC_MAX_CHANNELS 4`). Pin to channel is fixed: ADCn = GPIO(26+n). Any of the 4 inputs may take any of the 4 pins. | `adc_pico.c:48,65-66,81-93,132-146` |
| Bank/range | RP2350A has only GPIO0-29 so the "0-31 / 16-47 PIO base" rule is moot. `numPins = 30` for I2C on A. | `bus_i2c_pico.c:111-113` |
| Not available | HW UART CTS/RTS, PIO UART parity, UART pin swap (`UART_TRAIT_PINSWAP` errors). SPI1 on RP2350A has only 3 SCK/3 MOSI choices (10,14,26 / 11,15,27). | `uart/serial_uart_pico.c:51-53`, `bus_spi_pico.c:100-130` |

### 2.1 Resulting hard slots for OPENAIO (what really limits the remap)

| Group | Pins needed | Allowed set |
|---|---|---|
| ELRS CRSF (UART1 TX+RX) | 2 | TX {4,6,8,10,20,22,24,26}, RX {5,7,9,11,21,23,25,27} (or UART0 sets) |
| SBUS UART (needs 8E2, so HW, not PIO) | 2 (RX needed; TX optional) | other UART instance, sets above |
| MSP DisplayPort VTX (PIOUART0, 8N1) | 2 | any |
| IMU SPI (SCK+MOSI+MISO, one instance) | 3 | SPI1 or SPI0 sets in section 1; CS, INT any |
| SD SPI (SCK+MOSI+MISO, the other instance) | 3 | other SPI instance; CS any |
| I2C0 (SDA+SCL, baro+mag) | 2 | SDA mod4=0, SCL mod4=1 (or I2C1: mod 2 / mod 3) |
| OSD W,EN,SYNC | 3 | N, N+1, N+2 |
| ADC VBAT, CURR | 2 | two of {26,27,28,29} |
| MOTOR1-4, LED_STRIP, BEEPER, LED0, GYRO INT, 3 CS | 11 | free |
| SWD / USB / QSPI / RUN | dedicated pins, not GPIO | n/a |
| Total GPIO used today | 30 of 30 (GPIO27 is `ELRS_EN`) | |

Conflict traps for a global search: (a) SPI0 and I2C0/UART share pins by position, a GPIO has exactly one funcsel; (b) UART0 and SPI0 positions overlap physically (GPIO0-3 both), so choose instances then positions; (c) ADC pins 26-29 are also SPI1/UART1/UART0/I2C pins, so using 2 for ADC removes 2 UART/SPI1 options.

## 3. ESP32-C3 (U22, schematic value `ESP32-C3`, pin usage as the FH4 package) for ExpressLRS

Source: `hardware/KiCad-Library/datasheet/ESP32-C3FH4.pdf` v1.9, sec 2 pin tables and sec 3 strapping (Chinese edition).

| Pins | Status |
|---|---|
| GPIO2, GPIO8, GPIO9 | Strapping. GPIO9 low at reset = download boot (needs GPIO2=1, GPIO8=1). GPIO8 also gates ROM log. Keep GPIO2 and GPIO8 high at reset (R111/R112 pull-ups do this), GPIO9 high unless forcing download. Usable as outputs after boot, so RST (GPIO2), RGB LED (GPIO8) and BOOT button (GPIO9) work as in the stock layout. Do not hang a device that pulls these low at reset. |
| GPIO18, GPIO19 | USB D-/D+ (USB-Serial-JTAG), default function at reset. Usable as GPIO only after reconfiguration. Currently NC. |
| GPIO11-17 (pins 18-24) | In-package flash on the FH4 (VDD_SPI, SPIHD/WP/CS0/CLK/D/Q). Never use. |
| GPIO4-7 (MTMS, MTDI, MTCK, MTDO) | JTAG function; normal GPIO unless eFuse JTAG pads are enabled (EFUSE_DIS_PAD_JTAG default 0 = JTAG on pads only if you use it). Safe in practice and used for SX1281 SPI today. |
| GPIO20, GPIO21 | U0RXD/U0TXD. ROM UART download mode listens ONLY here. Keep serial_rx/serial_tx on 20/21 if UART flashing from the FC/pads must work (C3 arrives blank). |
| GPIO0, GPIO1 | XTAL_32K pins, normal GPIO with no 32k crystal (DIO1 is on GPIO1 today). |
| Free GPIO today | GPIO0, GPIO10 (tied to GND by board) |

Arbitrary pins in ELRS: YES for everything the stock `Generic C3 2400.json` defines. Hardware layout JSON keys (`src/lib/OPTIONS/hardware.cpp:22-82`): `serial_rx/tx`, `radio_busy/dio1/miso/mosi/nss/rst/sck`, `radio_dcdc`, `led_rgb`, `led_rgb_isgrb`, `button`. SPI is initialised via `SPIEx.begin(GPIO_PIN_SCK, GPIO_PIN_MISO, GPIO_PIN_MOSI, GPIO_PIN_NSS)` (`src/lib/SX1280Driver/SX1280_hal.cpp:67`, GPIO matrix, "ss can be any GPIO"). Shipped layout: `src/hardware/RX/Generic C3 2400.json` (serial 20/21, busy 3, dio1 1, miso 5, mosi 4, nss 7, rst 2, sck 6, led 8, button 9; identical to the board netlist per PINOUT.md).

Safe for SX1281 on C3: SCK/MOSI/MISO/NSS any of {0,1,3,4,5,6,7,10}; BUSY any input (3 fine); DIO1 needs a GPIO with interrupt (any, 1 is fine); RST any, but if you move it avoid levels that fight GPIO2 pull-up. Do not put the radio on GPIO2/8/9 except RST/LED/button with pulls as today, never on 11-17, avoid 18/19. UART to FC: keep GPIO20/21. Caveat: the layout is ESP-side only; changes require a custom hardware JSON (Configurator custom layout or web UI), not the stock key `c3-plain`, and ELRS `targets.json` fixed target will no longer match. The ESP32 pins are not on the RP2354A side, so for the FC pin remap only the RP side of UART1_TX/RX (GPIO6/7 today) matters.

## 4. AM32 ESC MCUs (AT32F421G8U7 x4: U13/U15/U17/U19)

Netlist part: AT32F421G8U7. Input is fixed by the AM32 hardware group of the target, tied to a timer capture channel: AT_B = PB4/TMR3_CH1 (`Inc/targets.h` OPENESC_20_F421 uses AT_B at 4889-4922 of upstream 50234143; `HARDWARE_GROUP_AT_B` uses GPIOB, TMR3 ch1; AT_F uses PA2/TMR15 ch1 and AT_C/E use a GPIOA pin on TMR15 ch1 in the AM32 tree `Inc/targets.h`). The bootloader (`AM32_F421_BOOTLOADER_PB4`) also assumes PB4. Answer: do NOT remap the ESC input; it is hardwired on the PCB to PB4, remapping needs a new PCB and a new AM32 target plus bootloader. The only free end is the FC side: MOTORn can be ANY RP2354A GPIO (PIO DShot, section 2), 220R series, so wiring length can be optimised freely there. Phase/comp pins are likewise fixed by AT_B/AT_045.
