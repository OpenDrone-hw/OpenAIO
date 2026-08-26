# OpenAIO

An all-in-one for toothpick-class 6S FPV: flight controller, 4-in-1 ESC and
ExpressLRS receiver on 25.5 x 25.5 mm mounting. It merges three boards
OpenDrone already makes: the ESC power stages, power, receiver and all pads on
this board, and the flight controller as the shared OpenFC-Core module, a
15 x 15 mm LGA reflowed flat onto it, no connector.

[![Status](https://img.shields.io/endpoint?url=https://opendrone.be/api/status/OpenAIO.json)](https://github.com/OpenDrone-hw/.github/blob/main/CONTRIBUTING.md#the-life-of-a-project)
[![Discord](https://img.shields.io/badge/Discord-join-5865F2?logo=discord&logoColor=white)](https://discord.gg/v3sWmTcx3R)

Held by @stancoene. Layout in progress on the branch
`design/start-kicad-project`; nothing has been manufactured.

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
| Mounting | 25.5 x 25.5 mm, board 35.4 x 35.4 mm |
| Stack | 6 layers 1.6 mm, 2 oz outer; OpenFC-Core module on top as a 54-pad LGA |
| Input | 6S |
| Flight controller | OpenFC-Core module: RP2350-class MCU, IMU, barometer, analog OSD, microSD blackbox; USB-C on this board |
| ESC | 4x AM32, AT32F421 + NSG2065Q per channel like the OpenESC boards |
| Receiver | ExpressLRS 2.4 GHz, ESP32-C3 + SX1281 |
| Assembly | JLCPCB, LCSC basic parts preferred |

## Constraints

- 25.5 x 25.5 mm mounting, the toothpick standard.
- Runs stock firmware: Betaflight on the FC, AM32 per ESC channel, ExpressLRS
  on the receiver. No forks.
- Reuses the manufactured circuits of OpenFC-Lite-Mini, OpenESC-20x20 and
  OpenRX where they fit; parts come from the shared library first.
- JLCPCB assembly from LCSC parts, extended parts kept to a minimum.
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
