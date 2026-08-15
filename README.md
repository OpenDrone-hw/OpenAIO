# OpenAIO

An all-in-one board for toothpick-class 6S FPV: flight controller, 4-in-1 ESC
and ExpressLRS receiver on a single 25.5 x 25.5 mm board. One board, one
connector, no stack. It merges three boards OpenDrone already makes.

[![Status](https://img.shields.io/endpoint?url=https://opendrone.be/api/status/OpenAIO.json)](https://github.com/OpenDrone-hw/.github/blob/main/CONTRIBUTING.md#the-life-of-a-project)
[![Discord](https://img.shields.io/badge/Discord-join-5865F2?logo=discord&logoColor=white)](https://discord.gg/v3sWmTcx3R)

Nobody holds this board yet: claim it on Discord.

## Why

The three-board stack works and OpenDrone already ships all three parts, but on
a toothpick the stack is most of the weight and all of the height. Merging them
removes two connectors, two sets of mounting hardware and a lot of wiring, and
those connectors are where builds fail.

The parts are proven separately, so this is an integration problem rather than
a research one. That makes it a good first board for someone who has not
designed for us before. The only 6S AIO with onboard serial ELRS on the market
is closed and digital-only; an open one with analog OSD and blackbox has a
place, see the market research below.

## Specifications

Targets. The board does not exist yet.

| | |
|---|---|
| Mounting | 25.5 x 25.5 mm |
| Input | 6S |
| Flight controller | RP2354A, Betaflight target |
| ESC | 4x AM32, one MCU per channel like the OpenESC boards |
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
- [research/DESIGN.md](research/DESIGN.md): write-up of the stitched design that was reset in August 2026, kept for its part list and lessons

## Open questions

The decisions to make before any of it gets drawn. Answering them is a real
contribution that needs no KiCad.

- **Thermal.** Four power stages next to an MCU and a radio on 25.5 mm square,
  with no airflow guarantee. What is the continuous current budget, and does it
  need copper beyond 2 oz outer?
- **RF isolation.** A 2.4 GHz receiver on top of four switching power stages.
  Where does the antenna go, what does the ground plane have to do, and is a
  shield can needed?
- **Current sensing.** Board level like the ESCs, or per channel?
- **Video.** Analog OSD, digital only, or both?
- **What gets dropped.** An AIO cannot carry everything the three separate
  boards do. Which I/O is worth the space?

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
