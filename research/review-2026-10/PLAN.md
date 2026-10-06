# Split Core/Base: review and re-route plan (October 2026)

Baseline: d81e559, the two-board design, fully routed (Core 0 unconnected, Base 0 unconnected).

## Files in this folder

| File | What it is |
|---|---|
| [CIRCUIT_REVIEW.md](CIRCUIT_REVIEW.md) | Schematic review against the datasheets, ranked, with fixes |
| [LAYOUT_REVIEW.md](LAYOUT_REVIEW.md) | Layout review, ranked |
| [NEXTPCB.md](NEXTPCB.md) | NextPCB fab and assembly limits with sources, and the rule sets derived from them |
| `lr_*.py`, `lr_*.txt`, `lr_img/` | Every number in LAYOUT_REVIEW.md comes from these scripts and their outputs |

The layout review covers: LGA interface, power paths (DC solver), noise, density, assembly and DRC.

The scripts run under KiCad 10's pcbnew Python against the d81e559 boards.

## Decisions taken while the maintainer was away

Every decision below is made on this branch only and can be reverted. "Recommended" means the option the
reviews recommend.

| id | Decision | Taken |
|---|---|---|
| B1 | +10V buck enable from the FC | **Done in 9aba717.** EN tied to +BATT, `10V_ENABLE` removed (maintainer's call) |
| D1 | LGA pattern | **2.0 mm grid, about 40 pads, at least 40 % GND, a GND anchor near each Core corner** (recommended) |
| D2 | What the Core B.Cu faces | **Core B.Cu signal-free**, at least 0.3 mm +BATT clearance around J90 (recommended) |
| D3 | Base stack | **In3 solid GND, In4/In5 +BATT planes**; logic power moves to local pours (recommended) |
| D4 | Vias in pads | **Filled and capped (POFV, IPC-4761 VII)** in board setup on both boards |
| D5 | Current design point | 20 A per motor, as reviewed |
| D6 | Shunt and battery-pad floorplan | **Move Rsense2/U25** for a straight battery-to-shunt path and Kelvin sense. The battery lead may move a few mm |
| D7 | SWD on the Core | **Yes**: 2 LGA pads to Base test pads |
| D8 | HDI / blind vias | **No**: about 4x the board price at NextPCB |
| D9 | ESP32-C3 variant | **ESP32-C3FH4** (internal flash); the unused flash pads go |
| D10 | TF socket | **Keep the microSD**; it may move in the density pass |
| S1 | 3.3 V LDO | **Moves to the Core**, next to the RP2354A. Main's OpenFC-Core already does this |
| S2 | VTX +10V pads | **Move to the Base** next to the SH-6 connector; +10V leaves the LGA |
| B2 | UART1_RX contention (ESP32 TX vs SH-6 SBUS) | **SH-6 pin 6 to PU0RX (GPIO3, PIO UART)** across the LGA, as main does |

The circuit review's other should-fix items are also taken:
- B3: values and part numbers;
- LDO output caps;
- BMI270 unused pins;
- BOOTSEL resistor;
- gate-driver and buck decoupling;
- RX LED supply;
- SX1281 pin 5 to GND.

Owner rules from the shared `pcb-agent-commons` repo, adopted at R1 (the owner set them on 2026-10-06 for every board):
- no component silkscreen;
- every solder pad gets a legible function label;
- no "Drone" text on the boards;
- manufacturer and exact MPN on every BOM line;
- 0201 passives by default, with minimal justified capacitance;
- through vias only (consistent with D8);
- KiCad features used properly: netclass directive labels, impedance stackup, diff pairs, custom DRU rules, keepouts, zone priorities;
- independent critique rounds until no round finds a BLOCKER or MAJOR.

Not done without the maintainer:
- replacing the microSD with flash;
- swapping the SX1281 receiver for the LR1121 "mono" sheet;
- moving the VBAT divider and buzzer/LED drivers to the Base.

## Order of work

Each step ends with these checks:
- ERC;
- `kicad-cli pcb drc --refill-zones --schematic-parity` on both boards;
- pcbnew unconnected count = 0;
- the review scripts re-run to compare against the baseline numbers.

A step that makes any of these worse is reverted, not pushed.

1. **R1, DFM and circuit fixes** (both boards, local edits only): LAYOUT_REVIEW step 1, plus the circuit fixes above that need no re-pattern.
2. **R2, LGA and Core:**
   - new land and pad footprints;
   - net assignment;
   - schematic moves S1, S2, B2, D7;
   - Core re-route with B.Cu signal-free.
3. **R3, Base:**
   - stack re-plan;
   - power stage (shunt, Kelvin, via arrays, feeds);
   - LGA-side routing;
   - density pass to the 0.2 mm body-to-body target.
4. **R4:** final verification and an updated review with before/after numbers.
