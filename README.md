# OpenAIO

**Planned.** No design exists yet. This page is the specification: what we want
built and why. If you want to design it, say so on
[Discord](https://discord.gg/v3sWmTcx3R).

An all-in-one board for toothpick-class 6S FPV: flight controller, 4-in-1 ESC
and ExpressLRS receiver on a single 25.5 x 25.5 mm board. One board, one
connector, no stack.

## Why

The three-board stack works and OpenDrone already ships all three parts, but on
a toothpick the stack is most of the weight and all of the height. Merging them
removes two connectors, two sets of mounting hardware and a lot of wiring, and
those connectors are where builds fail.

The parts are already proven separately, so this is an integration problem
rather than a research one. That makes it a good first board for someone who
has not designed for us before.

## Requirements

| | |
|---|---|
| Mounting | 25.5 x 25.5 mm |
| Input | 6S |
| Flight controller | RP2354A class, Betaflight target |
| ESC | 4 channels, AM32, distributed-MCU topology like the OpenESC boards |
| Receiver | ExpressLRS 2.4 GHz, ESP32-C3 + SX1281 |
| Assembly | JLCPCB, LCSC basic parts preferred |

## Prior art in the line

The three designs this merges, all of them manufactured and flying:

- [OpenFC-Lite-Mini](https://github.com/OpenDrone-hw/OpenFC-Lite-Mini): the RP2354A flight controller
- [OpenESC-20x20](https://github.com/OpenDrone-hw/OpenESC-20x20): the AM32 4-in-1 power stage
- [OpenRX](https://github.com/OpenDrone-hw/OpenRX): the ELRS receiver

Do not start from a copy of all three stitched together. That was tried and it
produced a board that looked finished and was not. Start from the requirements.

## Open questions

These are the decisions that have to be made before any of it gets drawn, and
answering them is a real contribution that needs no KiCad.

- **Thermal.** Four power stages next to an MCU and a radio on 25.5 mm square,
  with no airflow guarantee. What is the continuous current budget, and does it
  need copper thickness beyond 2 oz outer?
- **RF isolation.** A 2.4 GHz receiver sitting on top of four switching power
  stages. Where does the antenna go, what does the ground plane have to do, and
  is a shield can needed?
- **Current sensing.** Board level like the ESCs, or per channel?
- **Video.** Analog OSD, digital only, or both?
- **What gets dropped.** An AIO cannot carry everything the three separate
  boards do. Which I/O is worth the space?

## Research

Component and market work done so far is in [research/](research/). It is
reference, not decisions.

## Contributing

Issues and pull requests are welcome on any repo. KiCad files cannot be merged,
so say what you intend to change before you do, on
[Discord](https://discord.gg/v3sWmTcx3R).

How everything works: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Hardware licensed under [CERN-OHL-S-2.0](https://ohwr.org/cern_ohl_s_v2.txt),
see [LICENSE](LICENSE).
