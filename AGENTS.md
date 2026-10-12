# OpenAIO

All-in-one board for toothpick-class FPV, 2-6S: 4x AM32 ESC, power, pads and ExpressLRS receiver, with the flight controller on the OpenFC-Core module.

Validate: `kicad-cli sch erc hardware/OpenAIO.kicad_sch && kicad-cli pcb drc --schematic-parity --refill-zones hardware/OpenAIO.kicad_pcb`

## Boundaries

- Sourcing (suppliers, prices, quotes, RFQs, contacts) never lives in OpenDrone repositories.
- Never text-edit `.kicad_sch`, `.kicad_pcb` or `.kicad_dru`: use KiCad, or kicad-skip / the pcbnew API with KiCad closed. `.kicad_pro` is JSON and may be edited for metadata.
- Agents write metadata fields only (MPN, Manufacturer, LCSC, Datasheet, text variables), never nets, wiring, routing, placement, footprint assignment or circuit values.
- KiCad libraries stay project-local; import parts with `easyeda2kicad` only.
- KiCad files do not merge: one person holds a board layout at a time.

## Board boundaries

- The `OpenDrone-Core` symbol and `OpenDrone-Core_LGA_land` footprint in `lib` are vendored from OpenFC-Core: never edit them here; move the core only by moving J1.

## Pointers

- Shared parts catalogue: `hardware/KiCad-Library/PARTS-USED.md`
- Release standard: https://github.com/OpenDrone-hw/.github/blob/main/RELEASES.md
