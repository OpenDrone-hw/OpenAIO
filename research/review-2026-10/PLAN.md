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

Adopted from the other boards' lessons in the commons (gate R2):
- **Base vias stay 0.35/0.20.** The owner told OpenFC-H7 that NextPCB builds 0.35/0.20 vias, so the planned resize to 0.43/0.20 is dropped. The Core keeps 0.35/0.15.
- **The route is a proof of concept.** The owner does the finish pass, so every net is routed or listed, without polishing.
- **Agents are bounded.** Each has one deliverable and checkpoints to a state file.
- **Shared tools:** freeroute.py, sync_pcb.py, check_rules.py and silk_check.py from the commons.
- **X-ray:** offset back-to-back exposed pads so 2D X-ray can read them. Mirrored high-side/low-side FET pairs are weighed against this in R3.

Owner decisions during the run (2026-10-07):
- The +BATT bulk capacitance and hot-plug protection come from an external electrolytic capacitor on the battery leads. No on-board bulk capacitance is added. The per-leg 0805 ceramics stay as the HF bypass for each half-bridge.
- **LED strip (critique F1):** Q2 and its 2.4 k pull-up are replaced by a non-inverting 5 V buffer (74AHCT1G125 class). Betaflight's RP2350 LED driver cannot invert the signal.
- **ESC MCU supply (critique F2):** the four AT32F421 run from a battery-only 3.3 V rail, a small LDO fed from the +5V buck. On USB-only power, AM32's startup tune then cannot drive unpowered NSG2065Q inputs.
- **DRC must end clean on both boards.** The target is 0 errors.
  - Intended departures (NextPCB capability, owner decisions, datasheet land patterns) become named DRU exceptions, each scoped to the pads, footprints or nets involved.
  - No check is globally ignored.
  - Real fabrication risks are fixed, not exempted.
  - The exceptions table goes in the PR.

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
2. **R2, LGA and Core.** The LGA spec is in `LGA_SPEC.md`: 46 pads, 21 GND, 2.0 mm grid.
   - R2-1: schematic moves S1, S2, B2 and D7; new land and pad footprints; nets synced to both boards. Base interface nets are reconnected so both boards are back at 0 unconnected.
   - R2-2: Core re-route, with B.Cu signal-free.
3. **R3, Base:**
   - stack re-plan;
   - power stage (shunt, Kelvin, via arrays, feeds);
   - LGA-side routing;
   - density pass to the 0.2 mm body-to-body target.
4. **R4:** final verification and an updated review with before/after numbers.
