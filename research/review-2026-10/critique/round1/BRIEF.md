# OpenAIO critique brief (round 1)

You are one independent reviewer of the OpenAIO two-board FPV all-in-one: a Core hat on a 46-pad LGA over a Base. Your perspective is given in your task prompt.

## Files you review

- **Repo:** `/home/user/OpenAIO`, branch `work/d81e559` at the commit named in your prompt.
- **Schematic:** `hardware/OpenAIO.kicad_sch`, one schematic for both boards.
- **Boards:** `hardware/OpenAIO-Base.kicad_pcb` (8 Cu, 1.6 mm, 2 oz outer) and `hardware/OpenAIO-Core.kicad_pcb` (6 Cu, 0.8 mm).
- **Rules:** `hardware/*.kicad_dru`.
- **Earlier reviews and decisions:** `research/review-2026-10/` (PLAN.md, CIRCUIT_REVIEW.md, LAYOUT_REVIEW.md, NEXTPCB.md, LGA_SPEC.md) and its scripts `lr_*.py`.

## Rules

1. **Read only.** Never modify the repo. Write only your own findings file: `/tmp/claude-0/-home-user-OpenAIO/08e5d1e0-9b8c-55cb-abfb-7d7e9f538e35/scratchpad/critique/<perspective>.md`. Put any scripts in `scratchpad/critique/<perspective>/`.
2. **Memory.** The container has 16 GB and no swap. Run every python or pcbnew job as `prlimit --as=5368709120 -- /usr/bin/python3 -I ...` from a clean directory. Use spatial prefilters, never all-pairs loops.
3. **Zone fills.** Refill only in a directory that has the project's `.kicad_pro` and `.kicad_dru` next to the board, or the fills are wrong.
4. **Library path.** Run `export OPENDRONE_LIB=/home/user/OpenAIO/hardware/KiCad-Library` before kicad-cli.
5. **Evidence.** Verify every claim against the actual files: a coordinate, a net, a measured number, or a datasheet page under `hardware/KiCad-Library/datasheet/`. A claim you cannot verify is not a finding.
6. **Re-read before you accuse.** Reviewer premises are often wrong, so check the part number, package and datasheet before you call something a defect.
7. **Size.** Print counts, not long listings. Stop and write your file before about 250k tokens.

## Severities

| Severity | Meaning |
|---|---|
| BLOCKER | The board will not work or cannot be built or assembled |
| MAJOR | Measurable electrical, thermal, reliability or DFM penalty, or an owner rule broken |
| MINOR | Should fix, low impact |
| NIT | Cosmetic |

## Findings file format

- **Verdict:** 3 lines.
- **Findings table:** columns `ID | severity | board/layer | location (ref, net, x,y) | evidence | fix`.
- **Already known:** findings below that you confirmed still hold. One line each.

## Already known or accepted: do not re-raise unless you find it got worse

- **FET stacking:** high-side and low-side FETs are stacked mirror-image on F and B. As a result there is no room for vias at the low-side sources (about 4.5 A per GND via at 20 A per motor), and 2D X-ray cannot see the exposed pads. This waits on the owner's decision about offsetting the stacks.
- **Original edge defects in the owner's design:** JP1.1, FL1.2 (RF chain, not moved), U12.7/8 and Core D1.2.
- **Leftover routing in Core silk, dangling vias and long routes:** listed for the owner's finish pass: I2C0 about 21 mm, UART0/PU0RX corner, +5V to R14.
- **No HDI:** through vias only, by owner rule. Base vias are 0.35/0.20, which the owner confirmed with NextPCB; Core vias are 0.35/0.15.
- **Product questions:** SD card versus flash, LR1121 versus SX1281, and VBAT divider placement are owner product decisions.
- **+10V:** always on with battery, by design (9aba717).
- **Clearance errors:** the remaining 17 on the Base date from before the re-route and are being tracked.
- Repo commit under review: 1522ed6 (board files as of f512434). Do not review anything newer.
- Shunt: keep a discrete shunt vs 0.1 mOhm + INA186A4 is an owner decision (research/review-2026-10/shunt/); Rsense2 still lacks a manufacturer/MPN (known).
- U3 buck HF cap: not placed, no legal site with small nudges (known, owner finish pass).
- 21 nets still on the In4/In5 +BATT planes (no path elsewhere) and the Core finish-pass routes are known.
- Owner decision 2026-10-07: an external electrolytic capacitor on the battery leads provides +BATT bulk capacitance and hot-plug protection. Do not raise on-board +BATT bulk capacitance; the per-leg 0805 ceramics remain the HF bypass and are in scope.
- Owner requirement 2026-10-07: DRC must end clean (0 errors on both boards). Intended departures become named, scoped DRU exceptions with a justification (NextPCB capability, owner decision, datasheet land pattern); real fab risks get fixed, not exempted. Reviewers: flag any existing rule or exception that hides a real risk.
