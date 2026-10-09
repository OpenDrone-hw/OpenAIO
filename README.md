# OpenAIO

An all-in-one for toothpick-class 6S FPV: flight controller, 4-in-1 ESC and
ExpressLRS receiver on 25.5 x 25.5 mm mounting. It merges three boards
OpenDrone already makes. Two PCBs, no connector: the **Base** carries the ESC
power stages, power, receiver and all pads, and the **Core**, a 23 x 20 mm hat
with the RP2354A, IMU, OSD and blackbox, is soldered flat onto it as an
interior LGA.

[![Status](https://img.shields.io/endpoint?url=https://opendrone.be/api/status/OpenAIO.json)](https://github.com/OpenDrone-hw/.github/blob/main/CONTRIBUTING.md#the-life-of-a-project)
[![Discord](https://img.shields.io/badge/Discord-join-5865F2?logo=discord&logoColor=white)](https://discord.gg/v3sWmTcx3R)

Held by @stancoene. Layout in progress on the branch
`claude/openaio-split-reroute`; nothing has been manufactured.

## Why

The three-board stack works and OpenDrone already ships all three parts, but on
a toothpick the stack is most of the weight and all of the height. Merging them
removes two connectors, two sets of mounting hardware and a lot of wiring, and
those connectors are where builds fail.

The parts are proven separately, so this is an integration problem rather than
a research one. The only 6S AIO with onboard serial ELRS on the market is
closed and digital-only; an open one with analog OSD and blackbox has a place,
see the market research below.

## Specifications

From the design files. Not manufactured yet.

| | |
|---|---|
| Mounting | 25.5 x 25.5 mm, board 35.4 x 35.4 mm (Base) |
| Stack | Base 8 copper layers, 1.6 mm, 35.4 x 35.4 mm; Core hat 23.1 x 20.2 mm, 6 copper layers, 0.8 mm, soldered on as a 46-pad LGA (interface R2a). Board rev r2, 2026-10 |
| Input | 6S |
| Flight controller | RP2354A, BMI270 IMU, analog OSD, microSD blackbox, USB-C |
| ESC | 4x AM32, AT32F421 + NSG2065Q per channel like the OpenESC boards |
| Receiver | ExpressLRS 2.4 GHz, ESP32-C3 + SX1281 |
| Assembly | NextPCB turnkey by MPN; DFM kept compatible with JLCPCB |

## Pinout

Measured from `OpenAIO-Core.kicad_pcb` and `OpenAIO-Base.kicad_pcb` (pad nets)
and the Betaflight target in `research/review-2026-10/firmware/` (`config.h`,
`PINOUT.md` has the full GPIO map). The silkscreen codes below are the ones
printed next to each pad; port names follow `config.h`.

**Orientation.** Forward is the SH-6 (U12) edge of the Base, battery pads at
the rear. Edge names in the Base table are for the top view with the forward
arrow pointing up (the KiCad view turned 180 degrees). An arrow on the Base top (next to the motor map) and on the Core
bottom points forward. This matches `GYRO_1_ALIGN CW180_DEG`; confirm it in
the configurator Setup tab at bring-up.

### Core, top pads (reachable with the Core fitted)

| Pad | Silk | Net | Function |
|---|---|---|---|
| J39 | VTX | `/OSD/VIDEO_OUT` | Analog video out (OSD) to the VTX |
| J38 | CAM | `/OSD/VIDEO_IN` | Analog video in from the camera |
| J30, J37 | 5V | `+5V` | 5 V out |
| J42, J52 | 4V5 (`4.5` at J52) | `+4v5` | 4.5 V rail |
| J34, J35, J40, J43, J50, J53 | GND (`G` where short) | `GND` | Ground |
| J26 | SDA | `/Pads/I2C0.SDA` | I2C0 SDA, GPIO4 (external mag or baro) |
| J23 | (legend) SCL | `/Pads/I2C0.SCL` | I2C0 SCL, GPIO5 |
| J44 | TX0 | `/Pads/PIOUART0_TX` | Betaflight UART0 TX, GPIO2 |
| J45 | RX0 | `PU0RX` | Betaflight UART0 RX, GPIO3: SBUS from the air unit (also SH-6 pin 6) |
| J49 | (legend) PTX | `UART0_TX` | Betaflight PIOUART0 TX, GPIO0: MSP DisplayPort (also SH-6 pin 3) |
| J48 | (legend) PRX | `UART0_RX` | Betaflight PIOUART0 RX, GPIO1 (also SH-6 pin 4) |
| J54 | (legend) TX1 | `UART1_TX` | UART1 TX, GPIO6, CRSF to the onboard ELRS (service pad) |
| J55 | RX1 | `UART1_RX` | UART1 RX, GPIO7, CRSF from the onboard ELRS; driven by the ESP32, do not drive it |

The net names are the schematic's; `UART0_TX/RX` on the LGA carry the PIO UART
and `PIOUART0_TX`/`PU0RX` the hardware UART0, because Betaflight cannot run
SBUS on a PIO UART (firmware ISSUES I1).

### Base pads

| Pad | Silk | Net | Function |
|---|---|---|---|
| U24.1 | `+` | `/CSA+` | Battery + (6S), through the current shunt |
| U24.2 | `-` | `GND` | Battery - |
| U24.12-14 | M1 (motor map) | `/1A /1B /1C` | Motor 1, ESC1 (Betaflight MOTOR1, GPIO25): right edge, front half |
| U24.15-17 | M2 | `/2A /2B /2C` | Motor 2, ESC2 (MOTOR2, GPIO24): front edge, right half |
| U24.18-20 | M3 | `/3C /3B /3A` | Motor 3, ESC3 (MOTOR3, GPIO23): rear edge, left half |
| U24.21-23 | M4 | `/4C /4B /4A` | Motor 4, ESC4 (MOTOR4, GPIO22): left edge, rear half |
| J15, J16, J24, J25 | 5V | `+5V` | 5 V for the LED strip, one per corner |
| J17, J18, J27, J28 | GND (bottom) | `GND` | Ground, one per corner |
| J20, J21, J31, J32 | LED (`L` at J20) | `LED_STRIP` | WS2812 data, GPIO8 |
| J41 | (legend) 10V | `+10V` | VTX / air-unit power, switched by GPIO27 (`10V_ENABLE`) |
| J51 | (legend) GND | `GND` | VTX ground |
| U12 | DJI | SH-6 | 1 `+10V`, 2 `GND`, 3 PIOUART0 TX, 4 PIOUART0 RX, 5 `GND`, 6 UART0 RX (SBUS) |
| J33 | BZ+ (bottom) | `+5V` | Buzzer + |
| J29 | BZ- (bottom) | `BUZZER-` | Buzzer - (low-side switched) |
| TP9 | BT0 (bottom) | `/RX/BOOT` | ESP32-C3 boot strap (ELRS flashing) |
| TP31 | (legend) SWD | `SWDIO` | RP2354A SWD data |
| TP32 | (legend) SWC | `SWCLK` | RP2354A SWD clock |
| TP1, TP3, TP4, TP6, TP8 | SD1, SD2, SC2, SC3, SC4 (bottom) | ESC n `PA13`/`PA14` | AM32 SWD of ESC n: SDn = SWDIO (PA13), SCn = SWCLK (PA14) |
| TP2, TP5, TP7 | (legend) SC1, SD3, SD4 | ESC n `PA14`/`PA13` | as above |
| USB1 | none | USB-C | USB (DFU and configurator) |
| JP1 | none | RF | ELRS 2.4 GHz antenna connector |

The motor map (M1-M4 around the forward arrow) on the Base top shows which pad
group belongs to which motor. **Pad legend** for the pads with no room for a
label: Core J23 SCL, J54 TX1, J48 PRX, J49 PTX; Base J41 10V, J51 GND, TP31 SWD,
TP32 SWC, TP2 SC1, TP5 SD3, TP7 SD4. Motor phase letters
are not printed: within each motor group the pads carry phases A, B, C (nets
above); swapping any two reverses the motor, so set direction in AM32 or with
Betaflight's motor direction instead of rewiring.

## Constraints

- 25.5 x 25.5 mm mounting, the toothpick standard.
- Runs stock firmware: Betaflight on the FC, AM32 per ESC channel, ExpressLRS
  on the receiver. No forks.
- Reuses the manufactured circuits of OpenFC-Lite-Mini, OpenESC-20x20 and
  OpenRX where they fit; parts come from the shared library first.
- NextPCB turnkey assembly by manufacturer part number; stay DFM-compatible
  with JLCPCB.
- Do not start from the three schematics stitched together. That was tried,
  and it produced a board that looked finished and was not (recoverable at the
  `pre-reset-2026-08-13` tag). Start from the requirements.

## Prior art

The three designs this merges, all manufactured and flying:

- [OpenFC-Lite-Mini](https://github.com/OpenDrone-hw/OpenFC-Lite-Mini): the RP2354A flight controller
- [OpenESC-20x20](https://github.com/OpenDrone-hw/OpenESC-20x20): the AM32 4-in-1 power stage
- [OpenRX](https://github.com/OpenDrone-hw/OpenRX): the ELRS receiver

Research so far, reference rather than decisions:

- [research/MARKET-RESEARCH-2026-06.md](research/MARKET-RESEARCH-2026-06.md): competing toothpick and whoop AIOs, June 2026
- [research/ALTERNATIVES.md](research/ALTERNATIVES.md): ESC-stage part alternatives, gate driver and FET options, March 2026
- The stitched design reset in August 2026 is in the git history before #9; reference for the thinking, not a design to continue from.

## Open questions

Still open while the layout is drawn. Answering them is a real contribution
that needs no KiCad.

- **Thermal.** Four power stages next to an MCU and a radio on 25.5 mm square,
  with no airflow guarantee. What is the continuous current budget on 2 oz
  outer copper?
- **RF isolation.** A 2.4 GHz receiver next to four switching power stages.
  Antenna placement, ground plane, shield can or not.

## In the line

What pairs with what, and what is available:
[opendrone.be](https://opendrone.be).

## Contributing

KiCad files cannot be merged, so say what you intend to change before you do,
on [Discord](https://discord.gg/v3sWmTcx3R). How everything works:
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

Hardware licensed under [CERN-OHL-S-2.0](https://ohwr.org/cern_ohl_s_v2.txt),
see [LICENSE](LICENSE).
