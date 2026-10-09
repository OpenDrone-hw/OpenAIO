# OpenAIO Core + Base: layout review

Baseline: commit **d81e559** (`origin/archive/openaio-base-routed-2026-08-22`, "Base fully routed"), extracted at
`scratchpad/rev/d81e559/hardware`. Boards: `OpenAIO-Core.kicad_pcb` (6 L, 0.8 mm, 23.0 x 20.1 mm, 87 footprints,
LGA J91 on B.Cu) and `OpenAIO-Base.kicad_pcb` (8 L, 1.6 mm, 35 x 35 mm, 254 footprints, LGA land J90 on F.Cu).
Schematic `OpenAIO.kicad_sch` is identical to 105e858; the Core differs from 105e858 only by silkscreen graphics, so
every number below was measured fresh on d81e559.

Reviewer stance: the maintainer's direction is binding (extreme density, 0.2 mm body-to-body, removable unused pads,
deliberate double-sided assembly, shortest and thickest power copper, NextPCB). Findings are ranked against that
direction. Nothing in the repo or the extracted boards was modified.

## How the numbers were made

Every number in this file comes from a script in `scratchpad/review/` (prefix `lr_`). Geometry comes from the
pcbnew API with **all zones refilled** (`lr_dump.py` writes `lr_core.json` and `lr_base.json`: pads as polygons,
tracks, arcs, vias, filled zones, fab, silk and 3D-model references). The Core is mapped onto the Base with
`base = core + (-34.232, +8.374)` mm (both views from the top, no mirror; derived from J90/J91 pad 1).
**Coordinates are Base coordinates unless a row says "core coords".**

| Topic | Script (output) |
|---|---|
| LGA routing, detour, GND distance | `lr_lga.py` (`lr_lga.txt`, `lr_lga.json`), `lr_graph.py` (copper graph, Dijkstra) |
| LGA re-assignment | `lr_lga_opt.py` (simulated annealing, `lr_lga_opt.txt`), `lr_lga_opt2.py` (exact Hungarian + GPIO legality, `lr_lga_opt2.txt`), `lr_lga_table.py`, `lr_lga_fig.py` (`lr_img/lga_patterns.png`) |
| Vias in LGA / SMD pads | `lr_lga_vip.py`, `lr_vip.py` |
| DC power (3-D resistor network, 0.05 mm grid, all layers + via barrels) | `lr_dc.py` (solver), `lr_power.py` (`lr_power.txt`, `lr_power_summary.md`), `lr_kelvin.py`, `lr_lsvias.py`, `lr_whatif.py`, `lr_jmap.py` (`lr_img/J_csa.png`, `lr_img/J_batt.png`) |
| Feeds, loops, decoupling | `lr_feeds.py`, `lr_hotloop.py`, `lr_bridgeloop.py` |
| Noise / SI | `lr_si.py` (`lr_si.txt`), `lr_aggmap.py`, `lr_overlap.py`, `lr_xboard.py`, `lr_rxspi.py`, `lr_perf.py` |
| Density, unused pads, flips | `lr_density.py` (`lr_density.txt`), `lr_wrlbody.py` (3-D model plan-view cross-check) |
| Assembly, heights | `lr_assembly.py`, `lr_heights.py`, `lr_misc.py`, `lr_masklogo.py` |
| DRC | `lr_drc.sh` (kicad-cli `--refill-zones --schematic-parity` on a private copy), `lr_drcsum.py` (`lr_drc.txt`) |
| Pictures | `lr_render.py` (`lr_img/*.png`) |

Assumptions (change them in the scripts if they are wrong):
- Load: **20 A per motor channel**, so 80 A battery current with all four motors at full duty. Results are also
  given per amp (mOhm) so they scale.
- Copper: Base outer layers 2 oz (70 um) as the `.kicad_dru` and AGENTS.md say, inner 1 oz (35 um); Core 1 oz
  everywhere. Note that the board-file stackup of the Base lists **35 um for F.Cu and B.Cu**, so a fab order taken
  from the stackup would be 1 oz outer and every outer-layer resistance below would double.
- Via barrel: 20 um wall plating (IPC class 2 average). Working limit used for "overloaded": ~1 A per 0.2 mm via
  (about 10 C rise); vias above 2 A are called out.
- Grid convergence: 0.1 mm vs 0.05 mm grid changed path resistances by about 8 %, so read them as +/-10 %.
- Body outlines: fab drawing; where the fab is missing or degenerate, the body size from the EasyEDA name
  (`_L7.0-W7.0`) or the silkscreen hull minus 0.1 mm. Checked against the VRML models where those exist.

---

## 1. Ranked findings

Severity: **blocking** = fab/assembly will fail or a function is broken; **should-fix** = measurable electrical,
thermal or reliability penalty that the next re-route should remove; **optimisation** = density/length gain.

| # | Sev. | Board / layer | Finding | Number | Where | Script |
|---|---|---|---|---|---|---|
| 1 | blocking | both | Via-in-pad everywhere, but board setup has `plugging/filling/capping = no`. LGA joints have open vias in them: solder wicks out of joints that can be neither seen nor reworked | Core: 30 vias in 23 of 34 J91 pads, 162 of 246 vias in SMD pads. Base: 24 vias in 19 of 34 J90 pads, 668 of 1333 vias in SMD pads (223 in IC pads, 56 in 0201 pads) | J90/J91, all QFNs | `lr_lga_vip.py`, `lr_vip.py` |
| 2 | blocking | Base B.Cu | Fab-rule violations on 2 oz outer copper. (a) U23 (TLV75533 X2SON-4): pad-to-EP 0.134 mm; NextPCB's 2 oz minimum is 0.14 mm and the board rule is 0.16. (b) USB1 shell holes are PTH with zero annular ring, and R4 pad 2 (CC2) sits 0.08 mm from the hole. (c) Duplicate GND via | 0.134 mm; 0.080 mm; 2 holes at one spot | U23 (83.72,68.30); USB1 (63.10,58.40)/(63.10,52.62), R4 (63.30,57.80); via (80.43,64.01) | `lr_drc.txt` |
| 3 | should-fix (high) | Base B.Cu | Current sense is not Kelvin. INA186 (U25) −IN goes by a 0.2 mm track to a +BATT plane via at (64.15,51.65), not to the shunt pad, so it reads +BATT plane drop as current | +0.035 to +0.21 mOhm extra per amp, depending on which high-side FET conducts. That adds 17 % to 105 % to the 0.2 mOhm shunt signal; +46 % with 4 x 20 A on phase A. The error changes with commutation, so it cannot be calibrated out | U25 (64.27,51.11), Rsense2 pad 2 (60.95,56.74) | `lr_kelvin.py` |
| 4 | should-fix | Base In1–In3, B | The battery + path wraps round the top-left GND mounting hole: battery pad, then a crescent of copper round the hole, then the shunt. It is the largest single loss on the board | /CSA+ 0.52 mOhm; narrowest cut 0.31 mm² (8.8 mm of 1-oz equivalent); 3.3 W at 80 A; 17 vias above 2 A (worst 3.9 A at (61.61,50.52)). Total board copper loss at 80 A is ~8.4 W (/CSA+ 3.3, shunt 1.3, +BATT 2.3, GND 1.5), against 3.2 W of FET conduction (8 FETs x 1.0 mOhm x 20 A²) | hole (62.65,48.16), battery pad (67.48,44.36), shunt pad 1 (60.95,50.81) | `lr_power.py`, `lr_img/J_csa.png` |
| 5 | should-fix | Base | Return and supply vias at the power stage are overloaded: current crowds into the 2–3 vias nearest each low-side source | GND at 4 x 20 A: 48 vias above 1 A, 18 above 2 A, worst 4.9 A at (80.90,46.69) next to Q18. Each LS at 20 A on its own: hottest via 2.5–5.2 A. +BATT: 66 above 1 A, 4 above 2 A, worst 3.3 A at (67.97,50.78) | Q4–Q26 source pins | `lr_power.py`, `lr_lsvias.py` |
| 6 | should-fix | Base stack | Plane use: In2 carries 504 mm of signals on 62 nets, but its 0.1 mm reference (In3) is a five-way power split, so each bus crosses 10–15 reference changes. +BATT sits on parts of F, In2 and In5 and on no full plane | Making In3 GND and In4/In5 +BATT planes (simulated) cuts +BATT shunt-to-drain from 0.73 to 0.39 mOhm mean (−47 %, worst 1.03 → 0.54) and the 80 A loss from 2.30 to 1.29 W; GND from 0.445 to 0.325 mOhm | In2/In3/In4/In5 | `lr_zones.py`, `lr_si.py`, `lr_whatif.py` |
| 7 | should-fix | Core B.Cu / Base F.Cu | The LGA face of the Core carries signals, and the Base copper it faces is +BATT, about 0.11 mm away with only two solder-mask layers between. Every J90 joint is ringed by +BATT | 110.9 mm of Core B.Cu tracks on 23 nets. Directly over +BATT: UART1 21.6 mm, VIDEO_IN 7.2, MOTOR 6.8, CURR 6.2. +BATT covers 201 of the 363 mm² under the Core. 28 of 34 J90 pads are 0.16 mm from +BATT copper | under J90 | `lr_si.py`, `lr_misc.py` |
| 8 | should-fix | both / LGA | LGA pin assignment fights the floorplan: the SD bus leaves the Core at the top and comes back to the SD card at the bottom left. GND pads are clustered | 18 signals: 363 mm routed against 181 mm straight-line Core end to Base end (+182 mm, 59 vias). Only 7 of 18 signal pads have a GND pad within 2.0 mm (worst 10V_ENABLE 6.6 mm). Re-assignment on the same 34 pads (A1) saves −60.7 mm of straight-line length (−21 %) with 16 of 18 signals at ≤ 2.0 mm from GND; a 2.0 mm on-grid pattern with 40 pads / 17 GND saves −89.0 mm with 18 of 18 | J90/J91 | `lr_lga*.py` |
| 9 | should-fix | Base In2/In5/B | Switching nodes run on the signal layers under the Core | Phase-node tracks: 170.5 mm on In2, of which 95 mm is under the Core. DShot on In2 passes within 0.27 mm of phase copper for 6.0 mm. SD SPI on In5 passes within 0.5 mm of phase copper for 3.0 mm. The IMU (U8) sits directly above phase-node copper (0 mm in plan) and 2.8 mm from Q21 | (66.47,63.87), (71.15,65.88), U8 at (82.53,61.34) | `lr_si.py`, `lr_aggmap.py`, `lr_xboard.py` |
| 10 | should-fix | Base | Single-via feeds on power pins | The whole RX/ESC +3V3 rail (ESP32-C3, SX1281, SD, 4 x AT32, INA186) leaves U23 through one via that carries 94 % of the rail current (0.60 of 0.64 A). Also one via each for: U4 VIN (5 V buck input), U16/U18/U20 VCC (gate drivers), 5 V pads J15/J16/J24/J25/J33, and Card1 VDD + U13 VDD (shared). The 1.5 A VTX current crosses one LGA pad fed by 2 vias | via (84.09,69.70) etc. | `lr_power.py`, `lr_feeds.py` |
| 11 | should-fix | Base | U21 (SX1281) pin 5 is GND in the datasheet but is a no-connect net, so the pad between XTA and XTB floats (schematic and layout) | 1 pad | U21 (88.38,68.48) | `lr_density.py`, SX1281 datasheet |
| 12 | should-fix | Base F | R34 (0201, SD CS pull-up) sits under the TF socket body | 3-D model overlap 0.37 mm² | (69.97,70.90) | `lr_wrlbody.py` |
| 13 | should-fix | both | No fiducials on either board, with 0.4 mm-pitch QFN-60 and QFN-28, 0201s and a 34-pad LGA | 0 | – | `lr_misc.py` |
| 14 | should-fix | Base | Buck input loops. Cin sits 3.1–3.3 mm (pin to pad) from VIN/GND, the loop is ~3 mm², and there is no HF cap | U3 3.27 mm / 3.09 mm², U4 3.11 mm / 2.95 mm² | U3, U4 | `lr_hotloop.py` |
| 15 | optimisation | both | Density slack against the 0.2 mm target | Median nearest-neighbour body gap: Core F 0.325 mm, Base F 0.27 mm, Base B 0.42 mm (57 parts above 0.5 mm). Free area (0.1 mm halo, pieces ≥ 0.5 mm wide): Core F 83 mm², Base F 150 mm² (outside the Core), Base B 237 mm² | – | `lr_density.py` |
| 16 | optimisation | both | Unused pads still in place | Core 10 (U2 ×7, U8 ×3); Base 60 on 13 parts. The maintainer has already deleted 16 | §5.3 | `lr_density.py`, `lr_drc.txt` |
| 17 | optimisation | Base | RX: ESP32-C3 ↔ SX1281 bus is 97 mm routed (81 mm straight) on In2; U21 and U22 are 9 mm apart | 97.3 mm | U22 (79.85,71.62), U21 (88.38,68.48) | `lr_rxspi.py` |
| 18 | optimisation | Core | RP2354A GPIO swaps within the legal pin-mux sets save little | 6–9 mm on the Core side | §2.4 | `lr_lga_opt2.py` |
| 19 | info | both | Good practice already in place: every half-bridge leg has its own 0805 cap 0.27–0.39 mm (plan view) from HS drain and LS source; HS and LS are stacked mirror-image on F/B; the LS→motor-pad via arrays have 18–19 vias (≈1.1 A per via at 20 A); the Core has solid GND on In1/In4 (88 % coverage); Core copper balance F/B is 72 %/77 %. But 14 bulk caps (C90–C103, C105, C106) have value "C" and no MPN | – | – | `lr_bridgeloop.py`, `lr_misc.py` |

---

## 2. LGA interface (J91 Core B.Cu ↔ J90 Base F.Cu)

### 2.1 Pattern and routing as built

34 round pads (0.99 mm diameter) on an irregular pattern, nominally a 2.0 mm grid with offsets. Allocation:
**18 signal, 5 power** (+10V, +3.3V, +4v5, +5V, +BATT), **11 GND (32 %)**. Pattern centroid sits 1.4 mm off the
Core centroid, and the pad hull covers 75 % of the Core area (good mechanically).

Routed lengths come from Dijkstra over each net's copper graph (tracks, vias, pads; T-junctions split), from the
LGA pad to the main endpoint on each side. "Direct" is the straight line from the Core endpoint (mapped to Base
coords) to the Base endpoint: the ideal if the pad sat on that line. "Pad-geo detour" is the part of the detour
that the pad position alone forces (|core−pad| + |pad−base| − direct).

| pad | net | Core end | Core mm | Core vias | Base end | Base mm | Base vias | routed | direct | detour | pad-geo detour | nearest GND pad mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10V_ENABLE | U2.41 | 14.7 | 1 | U3.5 | 13.3 | 2 | 27.9 | 11.1 | 16.8 | 7.8 | 6.60 |
| 2 | CURR | R5.1 | 11.4 | 1 | U25.6 | 13.7 | 1 | 25.2 | 16.8 | 8.3 | 1.6 | 5.37 |
| 3 | SPI0.MISO | U2.32 | 6.6 | 2 | Card1.7 | 9.5 | 2 | 16.1 | 4.2 | 11.9 | 10.2 | 2.83 |
| 4 | SPI0.SCK | U2.29 | 9.2 | 2 | Card1.5 | 13.3 | 2 | 22.5 | 7.1 | 15.3 | 9.0 | 2.00 |
| 5 | SPI0.MOSI | U2.31 | 7.7 | 2 | Card1.3 | 17.9 | 2 | 25.5 | 7.5 | 18.0 | 13.3 | 2.00 |
| 6 | FLASH_CS (SD CS) | U2.33 | 9.6 | 2 | Card1.2 | 18.7 | 2 | 28.3 | 7.8 | 20.5 | 16.9 | 2.83 |
| 9 | USB_D+ | R9.2 | 16.7 | 2 | USB1.A6 | 9.6 | 2 | 26.3 | 18.5 | 7.8 | 1.3 | 4.70 |
| 13 | USB_D- | R8.1 | 13.6 | 2 | USB1.A7 | 10.3 | 2 | 23.9 | 17.7 | 6.2 | 0.6 | 4.83 |
| 17 | MOTOR2 | U2.36 | 1.1 | 1 | R58.1 | 3.0 | 2 | 4.2 | 2.0 | 2.2 | 2.7 | 4.00 |
| 18 | MOTOR4 | U2.34 | 4.0 | 1 | R96.1 | 10.7 | 2 | 14.8 | 12.3 | 2.5 | 1.2 | 2.00 |
| 21 | BUZZER- | Q1.3 | 20.5 | 2 | J29.1 | 0.0 | 1 | 20.5 | 19.3 | 1.2 | 0.0 | 2.00 |
| 22 | MOTOR1 | U2.37 | 3.4 | 1 | R39.1 | 9.1 | 2 | 12.6 | 6.4 | 6.1 | 4.3 | 3.24 |
| 23 | MOTOR3 | U2.35 | 5.5 | 1 | R77.1 | 6.4 | 2 | 11.9 | 6.0 | 5.9 | 3.9 | 2.00 |
| 30 | UART0_TX | U2.2 | 6.4 | 3 | U12.3 | 15.1 | 0 | 21.5 | 6.8 | 14.7 | 5.7 | 2.00 |
| 31 | UART0_RX | U2.3 | 9.9 | 3 | U12.4 | 8.3 | 0 | 18.2 | 7.3 | 10.9 | 8.0 | 4.00 |
| 32 | LED_STRIP | Q2.3 | 5.8 | 1 | J32.1 | 27.6 | 2 | 33.4 | 14.2 | 19.2 | 10.4 | 2.00 |
| 33 | UART1_RX | U2.10 | 10.9 | 2 | U22.28 | 5.5 | 1 | 16.4 | 8.6 | 7.8 | 4.7 | 2.23 |
| 34 | UART1_TX | U2.9 | 10.6 | 2 | U22.27 | 3.7 | 1 | 14.4 | 7.7 | 6.7 | 2.6 | 3.60 |
| | **total** | | **177.8** | **31** | | **186.0** | **28** | **363.4** | **181.4** | **182.0** | **104.1** | |

Multi-drop nets: the LED_STRIP tree on the Base is 109.7 mm, running to all four corner pads; the farthest, J31,
is 73.9 mm away. UART1_RX also reaches U12.6 (the DJI SH-6). UART0_TX/RX also reach the Core pads J49/J48, which
sit directly over LGA pads 30/31 (0 mm).

Reading it:
- The **SD bus** is the worst offender (pads 3–6: +65.7 mm detour, 49.4 mm of it from pad position alone). U2's
  SPI0 pins are at (72.9–74.1, 60.3–61.9) and Card1 is at (67.7, 65.9), yet the SPI pads sit in the top row at
  y = 55.47. The Base side then routes 42 mm of SD bus on In5 next to phase-node copper (§4).
- **10V_ENABLE** (pad 1, 16.8 mm detour) and **LED_STRIP** (19.2 mm) are the next worst.
- **USB** and **BUZZER** have small detours, but their direct paths are long (17–19 mm) because the Type-C sits
  at the left edge while USB_DP/DM (U2.51/52) are at the bottom of U2.

### 2.2 GND pads and return path

At the LGA, a signal's return current must cross through the nearest GND joint. On the Core that path is
In4 GND (0.1 mm above B.Cu) to a GND pad; on the Base it is a GND pad to In1 GND. Base F.Cu under the Core is
+BATT, not GND (§2.6).

| signal pads with nearest GND pad | ≤ 2.0 mm | 2.0–3.0 mm | > 3.0 mm |
|---|---|---|---|
| current | 7 (SCK, MOSI, MOTOR4, MOTOR3, BUZZER-, UART0_TX, LED_STRIP) | 4 (MISO, FLASH_CS, UART1_RX, …) | 7: 10V_ENABLE 6.6, CURR 5.4, USB_D- 4.8, USB_D+ 4.7, MOTOR2 4.0, UART0_RX 4.0, UART1_TX 3.6, MOTOR1 3.2 |

- Six of the 11 GND pads (10/11, 19/20/24/25) cluster in two 2x2 blocks: the four under U2's exposed pad, and
  10/11 between the SPI pads.
- Pads 15/16 are at the far right, serving BUZZER- and mechanical support only.
- The USB pair, CURR and 10V_ENABLE have no GND neighbour at all. Power pads +10V/+3.3V/+4v5 are 4.5–6.3 mm from
  any GND pad, so the 1.5 A VTX supply crosses the interface with its return 4.5 mm away.
- MOTOR1 is 2.48 mm from the +BATT pad and adjacent to MOTOR2/MOTOR3.

### 2.3 Optimised pin assignment (same 34 pad positions, same 11 GND / 5 power)

Cost per net = straight-line |Core end − pad| + |pad − Base end| (the +BATT pad's Base side is free because Base
F.Cu under the whole Core is +BATT). Penalties:
- 4 mm per mm a signal pad sits beyond 2.0 mm from its nearest GND pad;
- 3 mm per MOTOR pad orthogonally next to CURR, USB or +BATT;
- 30 mm if USB_D+/D− are not neighbouring pads.

Three solvers were run: exact Hungarian with GND (and optionally power) fixed, and simulated annealing over the
full permutation (6 seeds x 150 k moves).

| variant | solver | pads changed | signal straight-line mm | change | penalty (GND/adjacency) | signals with GND ≤ 2.0 mm | worst GND distance |
|---|---|---|---|---|---|---|---|
| A0 as built | – | 0 | 285.5 | – | 88.8 | 7/18 | 6.6 mm |
| A2: signals permuted, GND + power fixed | exact (Hungarian; USB pair placements enumerated) | 14 | 246.4 | −39.1 (−14 %) | 88.8 | 7/18 | 6.6 mm |
| A3: signals + power permuted, GND fixed | exact | 21 | 235.8 | −49.7 (−17 %) | 65.1 | 7/18 | 4.8 mm |
| **A1: full permutation (GND pads move too)** | annealing, best of 6 | 28 | **224.8** | **−60.7 (−21 %)** | 5.2 | **16/18** | 2.83 mm |
| lower bound: each pad on its straight line | – | – | 181.4 | −104.1 | – | – | – |

Routed length tracks straight-line length: today 363.4 mm routed / 285.5 mm straight = 1.27. So A1 is worth about
**−77 mm of routed signal copper** and the 2.0 mm grid of §2.5 about −113 mm.

- A2 moves: 1 CURR, 2 USB_D-, 3 USB_D+, 5 MOTOR3, 6 MOTOR4, 9 10V_ENABLE, 13 SPI0.MISO, 18 SPI0.MOSI, 23 UART1_TX,
  30 UART1_RX, 31 LED_STRIP, 32 FLASH_CS, 33 UART0_TX, 34 UART0_RX.
- A3 moves: 1 +3.3V, 2 +10V, 3 USB_D-, 4 USB_D+, 5 SPI0.SCK, 6 MOTOR4, 7 +4v5, 8 +BATT, 9 CURR, 12 +5V,
  13 10V_ENABLE, 14 SPI0.MISO, 18 MOTOR3, 22 SPI0.MOSI, 23 UART1_TX, 26 MOTOR1, 30 UART1_RX, 31 LED_STRIP,
  32 FLASH_CS, 33 UART0_TX, 34 UART0_RX.

A1 is the one that matters, because only moving GND pads fixes the return path: 16 of 18 signals then sit within
2.0 mm of a GND pad, and the USB pair lands on pads 23/24 with GND on both sides.

Proposed pad map (A1, full re-assignment), next to the current one. "geo" is |core−pad|+|pad−base| straight-line
mm; "GND" is the distance from that pad to the nearest GND pad:

| pad | (x,y) base | current | geo mm | GND mm | A1 proposal | geo mm | GND mm |
|---|---|---|---|---|---|---|---|
| 1 | (69.80,52.78) | 10V_ENABLE | 18.9 | 6.6 | +3.3V | 14.6 |  |
| 2 | (69.80,54.78) | CURR | 18.4 | 5.4 | CURR | 18.4 | 2.0 |
| 3 | (72.45,55.47) | SPI0.MISO | 14.4 | 2.8 | 10V_ENABLE | 17.0 | 2.0 |
| 4 | (74.45,55.47) | SPI0.SCK | 16.1 | 2.0 | GND |  |  |
| 5 | (76.45,55.47) | SPI0.MOSI | 20.8 | 2.0 | GND |  |  |
| 6 | (78.45,55.47) | FLASH_CS | 24.7 | 2.8 | +4v5 | 21.1 |  |
| 7 | (80.45,55.47) | +10V | 20.3 |  | MOTOR4 | 14.8 | 2.0 |
| 8 | (82.45,55.47) | +3.3V | 21.8 |  | GND |  |  |
| 9 | (69.80,56.78) | USB_D+ | 19.8 | 4.7 | GND |  |  |
| 10 | (74.45,57.47) | GND |  |  | SPI0.SCK | 12.4 | 2.0 |
| 11 | (76.45,57.47) | GND |  |  | MOTOR3 | 10.0 | 2.0 |
| 12 | (84.45,57.47) | +4v5 | 24.3 |  | +5V | 21.0 |  |
| 13 | (69.80,58.78) | USB_D- | 18.3 | 4.8 | SPI0.MISO | 8.5 | 2.0 |
| 14 | (71.80,58.77) | +5V | 22.1 |  | +10V | 9.7 |  |
| 15 | (88.70,61.66) | GND |  |  | GND |  |  |
| 16 | (90.70,61.66) | GND |  |  | GND |  |  |
| 17 | (74.43,63.55) | MOTOR2 | 4.7 | 4.0 | MOTOR2 | 4.7 | 2.0 |
| 18 | (76.43,63.55) | MOTOR4 | 13.5 | 2.0 | SPI0.MOSI | 12.7 | 2.0 |
| 19 | (78.43,63.55) | GND |  |  | GND |  |  |
| 20 | (80.43,63.55) | GND |  |  | UART1_RX | 8.6 | 2.0 |
| 21 | (90.70,63.66) | BUZZER- | 19.3 | 2.0 | BUZZER- | 19.3 | 2.0 |
| 22 | (74.43,65.55) | MOTOR1 | 10.7 | 3.2 | GND |  |  |
| 23 | (76.43,65.55) | MOTOR3 | 10.0 | 2.0 | USB_D- | 19.2 | 2.0 |
| 24 | (78.43,65.55) | GND |  |  | USB_D+ | 21.6 | 2.0 |
| 25 | (80.43,65.55) | GND |  |  | UART0_RX | 8.1 | 2.8 |
| 26 | (71.95,65.66) | +BATT | 0.8 |  | MOTOR1 | 8.1 | 2.5 |
| 27 | (73.12,68.51) | GND |  |  | FLASH_CS | 10.8 | 2.0 |
| 28 | (76.13,68.51) | GND |  |  | +BATT | 5.5 |  |
| 29 | (83.22,70.21) | GND |  |  | UART1_TX | 8.5 | 2.0 |
| 30 | (85.22,70.21) | UART0_TX | 12.5 | 2.0 | GND |  |  |
| 31 | (87.22,70.21) | UART0_RX | 15.3 | 4.0 | LED_STRIP | 14.8 | 2.0 |
| 32 | (73.12,70.51) | LED_STRIP | 24.6 | 2.0 | GND |  |  |
| 33 | (77.12,70.51) | UART1_RX | 13.2 | 2.2 | GND |  |  |
| 34 | (79.12,70.51) | UART1_TX | 10.3 | 3.6 | UART0_TX | 7.1 | 2.0 |

Figure: `lr_img/lga_patterns.png` shows the current pattern, A1 and the 2.0 mm grid proposal (B), with Core
endpoints joined in blue and Base endpoints in red.

### 2.4 RP2354A GPIO legality (QFN-60 has GPIO0–29)

Current map:
- UART0 TX/RX: GPIO0/1
- UART1 TX/RX: GPIO6/7, through the **UART_AUX** function F11
- LED_STRIP: GPIO8
- IMU SPI1: GPIO9–13
- OSD: GPIO14–16
- BEEPER: GPIO17
- SD SPI0 SCK/TX/RX/CS: GPIO18–21
- MOTOR4..1: GPIO22–25
- LED0: GPIO26 (an ADC pin)
- 10V_ENABLE: GPIO27 (an ADC pin)
- ESC_CURR: GPIO28 (ADC2)
- ADC_VBAT: GPIO29 (ADC3)

Unused: SWCLK/SWDIO and QSPI_SD0–3/SCLK.

| function | legal pins (RP2350 function table) | notes |
|---|---|---|
| SPI0 RX / SCK / TX | RX {0,4,16,20}, SCK {2,6,18,22}, TX {3,7,19,23} | all three must be the same SPI instance. SPI1 alternative: RX {8,12,24,28}, SCK {10,14,26}, TX {11,15,27}, but the IMU owns SPI1 |
| SD CS (FLASH_CS) | any GPIO (software CS in Betaflight); hardware CSn would be {1,5,17,21} | |
| UART0 TX / RX | TX {0,12,16,28} + AUX {2,14,18}; RX {1,13,17,29} + AUX {3,15,19} | AUX = function F11 (CTS/RTS pins used as TX/RX); verify that Betaflight's RP2350 UART pin table accepts AUX pins before relying on them (UART1 already does) |
| UART1 TX / RX | TX {4,8,20,24} + AUX {6,10,22,26}; RX {5,9,21,25} + AUX {7,11,23,27} | |
| MOTOR1–4 (PIO DShot), LED_STRIP (PIO), BEEPER (PWM), 10V_ENABLE (PINIO), LED0 | any GPIO | 10V_ENABLE and LED0 currently burn two of the four ADC pins |
| CURR / VBAT ADC | GPIO26–29 only | freeing 26/27 lets CURR and VBAT pick the closer ADC pins |
| I2C0 (pads) | SDA {0,4,8,12,16,20,24,28}, SCL = SDA+1; I2C1 SDA {2,6,10,…} | |

Measured (`lr_lga_opt2.py`; exact assignment inside the legal sets, using only the GPIOs the LGA functions
occupy today: 0, 1, 6, 7, 18–27; LED0 rides along as "any"):
- **current pad map**: Core-side straight-line total 81.1 → 74.8 mm (**−6.3 mm**). Moves: UART1_RX 7→27 (AUX RX),
  FLASH_CS 21→7, MOTOR4 22→23, MOTOR3 23→25, MOTOR1 25→26, LED0 26→22, 10V_ENABLE 27→21.
- **A3 pad map**: 67.9 → 58.5 mm (**−9.4 mm**). Moves: SPI0.MOSI 19→23 (still SPI0 TX), FLASH_CS 21→27,
  MOTOR4 22→19, MOTOR3 23→24, MOTOR2 24→25, MOTOR1 25→26, LED0 26→22, 10V_ENABLE 27→21.

Conclusion: on the Core side, GPIO swaps buy **6–9 mm**. Pad position (§2.3) is worth 5–10x more.
- Re-map only where the new pad map makes it free: MOTORx, SD CS, 10V_ENABLE and UART1 on AUX pins.
- Keep SPI0 on 18–20 and the IMU on SPI1 9–13.
- Move LED0 off the ADC pins.

### 2.5 Should the pattern become a regular grid?

The annealer was let loose on all sites of a regular grid inside the Core outline (pad edge ≥ 0.35 mm from the
outline), choosing both the sites and the assignment:

| grid pitch (pad Ø) | sites inside the Core | pads used / GND | signal straight-line mm | vs today | signals with GND ≤ 1 pitch | pad hull / centroid offset |
|---|---|---|---|---|---|---|
| 2.0 mm (1.0 mm) | 79 | 34 / 11 | 194.0 | −91.6 | 17/18 (worst 2.83) | 48 % / 3.1 mm |
| 2.0 mm | 79 | 36 / 13 | 196.9 | −88.6 | 18/18 | – |
| **2.0 mm** | 79 | **40 / 17** | **196.5** | **−89.0** | **18/18** | 66 % / 2.15 mm |
| 2.0 mm | 79 | 46 / 23 | 196.4 | −89.1 | 18/18 | – |
| 1.6 mm (0.9 mm) | 120 | 40 / 17 | 188.0 | −97.5 | 18/18 | – |
| 1.5 mm (0.8 mm) | 132 | 40 / 17 | 185.9 | −99.6 | 18/18 | – |
| lower bound | – | – | 181.4 | −104.1 | – | – |

The 40-pad, 2.0 mm solution is in `lr_lga_opt.json` (key `B_2.0_40_17`) and in the right-hand panel of
`lr_img/lga_patterns.png`.

Recommendation (to be decided by the maintainer, see §9):
- **Yes, put the pads on a 2.0 mm grid, but depopulated**: choose the sites by optimisation. Do not use a full
  array.
- **40–44 pads, ≥ 40 % GND (16–18 GND)**:
  - 18 signals;
  - 6–7 power: +10V x2 for the 1.5 A VTX, +5V, +4v5, +3.3V, +BATT;
  - optionally 2 SWD pads (SWCLK/SWDIO are unconnected today, so the Core has no debug access at all).
- Every signal orthogonally adjacent to a GND pad, the USB pair adjacent with GND on both sides, and MOTOR pads not
  adjacent to CURR/USB/+BATT.
- Add one GND anchor pad near each Core corner. The wirelength-optimal 40-pad cluster has its centroid 2.15 mm
  off and covers only 66 % of the Core (today 1.4 mm / 75 %), which is bad for self-alignment and coplanarity.
- Why these numbers:
  - Adding GND pads costs **almost nothing in wirelength** (signals 194.0 mm at 34/11 against 196.5 mm at 40/17
    and 196.4 mm at 46/23).
  - 2.0 mm to 1.5 mm pitch gains only ~8 mm more and halves the pad gap, so keep 2.0 mm pitch and 1.0 mm pads.

### 2.6 LGA manufacturing

- **Vias in pads** (blocking, finding 1). The board setup must say `filling yes, capping yes` and the order must
  specify POFV / IPC-4761 type VII, which NextPCB offers. The alternative is moving every via out of J90/J91 pads,
  which costs routing room.
  - Core J91: 30 vias with centre inside a pad (23 of 34 pads) plus 7 overlapping a pad edge.
  - Base J90: 24 inside (19 pads) plus 13 overlapping an edge.
  - The Core solder pads J48/J49 (F.Cu) sit directly on LGA pads 30/31, with 4–5 through-vias in each stack.
- **+BATT ring**: 28 of 34 J90 pads, GND pads included, sit 0.16 mm from the F.Cu +BATT pour (`lr_misc.py`). A mask
  defect or solder ball under a module that cannot be inspected optically puts 25 V on an I/O.
  - Either raise the +BATT clearance to J90 to ≥ 0.3 mm (custom rule), or make the copper under the Core GND
    (cost quantified in §3.6).
- **Coplanarity**: the Core is 0.8 mm, 6 layers, 23 x 20 mm. IPC bow/twist of 0.75 % allows ~0.2 mm over the
  diagonal, against a ~0.05–0.08 mm LGA joint.
  - Copper balance is good (F 72 % / B 77 %, inner 75–88 %).
  - Still, specify warpage ≤ 0.1 mm on the Core order, use a 0.12–0.15 mm (step) stencil on J90, and expect AXI
    (NextPCB does AXI on every LGA board).
- **Mass**: Core estimate 0.78 g on 26.4 mm² of LGA copper = 29.6 mg/mm². It sits on top in the final reflow, so
  there is no drop risk.

---

## 3. Power

### 3.1 Copper per layer (refilled zone area, mm²; `lr_zones.py`)

| Base layer | fill | content |
|---|---|---|
| F (2 oz) | 600 | +BATT 460, GND 41, +5V 21, phase nodes 6–7 each, plus 132 mm of tracks |
| In1 | 942 | GND 851, /CSA+ 39, phase 4–5 each |
| In2 | 748 | GND 520, +BATT 138, /CSA+ 38, phase 4 each, plus 504 mm of signal tracks (62 nets) |
| In3 | 559 | +3V3 293, +4v5 80, +3.3V 52, +5V_USB 45, /CSA+ 39, phase 3–5 each |
| In4 | 731 | +5V 535, +3V3 167, phase 2–4 each (no longer empty as on 105e858) |
| In5 | 550 | +BATT 408, +10V 142, plus 186 mm of tracks (20 nets) |
| In6 | 894 | GND 894 |
| B (2 oz) | 634 | GND 484, /CSA+ 39, +BATT 19, +5V 9, phase 6–7 each, plus 430 mm of tracks |

Core: In1 and In4 are solid GND (305 mm² each, 84 %); In3 holds +10V 99, +3.3V 61 and GND 72; B is GND 236.
Through-vias perforate every plane: 735 foreign vias punch through each Base GND plane (`lr_perf.py`).

### 3.2 Path resistance, bottleneck, vias (`lr_power_summary.md`; Core rows in core coords)

| board | net | scenario | R source→sink mOhm | narrowest mid-path cut, mm² (1-oz-eq. mm) @xy, worst sink | max drop mV | loss W | vias >1 A / >2 A | hottest via |
|---|---|---|---|---|---|---|---|---|
| Base | /CSA+ (battery pad → shunt) | 80 A | 0.522 | 0.308 (8.8) @(62.9,45.5) | 41.8 | 3.34 | 24 / 17 | 3.9 A @(61.61,50.52); the 3 mm battery barrel carries 7.3 A |
| Base | +BATT (shunt → 12 HS drains) | 4 x 20 A, phase A | 0.161 (Q3) .. 1.033 (Q25) | 0.191 (5.4) @(67.6,71.6) to Q9 | 40.4 | 2.30 | 66 / 4 | 3.27 A @(67.97,50.78) |
| Base | phase nodes /1A../4C (motor pad → HS source / LS drain) | 20 A | HS 0.064–0.094; LS 0.114–0.123 | HS: 0.123–0.174 (3.5–5.0) at the source pins; LS: 18–19 vias = 0.226–0.239 mm² | 1.3–1.9 | 0.03 each | 0 / 0 (HS); LS path ~1.1 A per via | – |
| Base | GND (12 LS sources → battery −) | 4 x 20 A, phase B | 0.227 .. 0.595 | 0.350 (10.0) @(68.4,75.2) Q12 | 23.3 | 1.49 | 48 / 18 | 4.88 A @(80.90,46.69) |
| Base | +10V (L2 → drivers, LGA 7, SH-6) | 1.5 A VTX + 4 x 20 mA | 3.8 .. 10.2 | single via 0.0126 (0.36) to U16/U18/U20 VCC | 6.4 | 0.01 | 0 / 0 | 0.75 A x 2 vias at LGA pad 7 |
| Base | +5V (L3 → LGA 14, D2, 5 V pads) | 2.85 A | 1.03 .. 7.18 | single via to each 5 V pad | 4.3 | 0.01 | 0 / 0 | 0.85 A @(65.15,55.74) |
| Base | +4v5 (D2/D3 → U7, U23, LGA 12) | 0.8 A | 0.54 .. 8.65 | 2 vias (0.025) | 4.4 | – | 0 / 0 | – |
| Base | +3V3 (U23 → RX, AT32 x4, SD, INA) | 0.64 A | 2.5 .. 12.3 | 1 via carries 94 % @(84.09,69.70) | 2.0 | – | 0 / 0 | 0.60 A |
| Base | +3.3V (U7 → LGA 8) | 0.15 A | 4.38 | 2 vias | 0.7 | – | 0 / 0 | – |
| Core | +10V (J91.7 → J41/J51 VTX pads) | 1.5 A | 2.2 / 9.5 | In3 0.75 mm wide to J51 | 8.6 | 0.01 | 0 / 0 | 0.44 A |
| Core | +5V (J91.14 → J30/J37) | 1 A | 6.0 / 10.6 | In3 1.05 mm | 7.6 | 0.01 | – | – |
| Core | +3.3V (J91.8 → U2 etc.) | 0.15 A | 8.4 .. 21.6 | 0.1 mm track to U9.5 | 1.8 | – | – | – |
| Core | GND (VTX return → 11 LGA GND pads) | 1.5 A | 0.12 .. 0.24 | – | 0.1 | – | – | – |

The current-density maps (`lr_img/J_csa.png`, `lr_img/J_batt.png`) show where the current goes:
- **/CSA+**: the whole battery current runs in a ~2 mm crescent round the GND mounting hole on In1, In2, In3 and
  B.Cu, above 200 A/mm² along the arc. F.Cu, the thickest layer, carries none of it.
- **+BATT**: current runs along the top band (y 45–52) and the left edge of F.Cu, threaded between the antipads of
  1107 foreign vias inside the pour outline.
  - The bottom-row FETs (Q9/Q11/Q13) are fed past the **TF socket**, which blocks F.Cu. That is the 0.19 mm²
    bottleneck at (67.6,71.6), equal to 2.7 mm of 2 oz copper for 20 A.

### 3.3 Overloaded vias at the low-side sources (`lr_lsvias.py`, each LS alone at 20 A)

| LS | GND vias within 1 mm of the source pins | hottest vias (A) |
|---|---|---|
| Q4 | 6 | 2.75, 2.06, 1.85 |
| Q6 | 9 | 4.39, 2.60, 1.60 |
| Q8 | 11 | 3.17, 2.99, 1.72 |
| Q10 | 11 | 5.19, 2.39, 1.89 |
| Q12 | 6 | 3.88, 3.75, 2.82 |
| Q14 | 8 | 2.61, 2.47, 2.35 |
| Q16 | 8 | 6.97 (mounting-hole barrel), 3.42, 2.38 |
| Q18 | 8 | 3.82, 3.58, 1.95 |
| Q20 | 6 | 4.15, 3.92, 3.79 |
| Q22 | 12 | 2.45, 2.17, 1.39 |
| Q24 | 7 | 3.39, 2.67, 2.14 |
| Q26 | 10 | 2.62, 2.54, 2.48 |

Current crowds into the 2–3 vias at the edge of the source pins. Fixes:
- 6–8 vias in line along the three source pins (VIPPO, since finding 1 needs it anyway), or 0.3 mm-drill vias;
- carry the source current on B.Cu (2 oz) towards the battery GND pad before it changes layer.

### 3.4 Single-pad / single-via feeds (`lr_feeds.py`, `lr_power.py`)

- **LGA**: every power rail crosses on exactly **one pad**.
  - +10V carries the VTX (1.5 A) on one 1.0 mm joint, fed by 2 Base vias at 0.75 A each and 4 Core vias.
  - +3.3V for the whole FC: one pad, 2 vias on each side.
  - +BATT (VBAT sense only): 1 via.
  - Recommendation: two pads each for +10V and +5V.
- **Base**:
  - U23 OUT (+3V3): 1 via for the whole rail.
  - U23 IN/EN: track-fed, no via within 1.5 mm.
  - U4 VIN (5 V buck, pulsed up to 3 A): 1 via.
  - U14/U16/U18/U20: VCC 0–1 via, VS1–3 1 via each. VS carries the bootstrap charge pulses.
  - AT32 VDD (U13/15/17/19): 0–1 via.
  - ESP32-C3 VDD3P3/VDDA: 0–1 via.
  - SX1281 VBAT/VBAT_IO: 0–1 via.
  - Card1 VDD: 1 via, shared with U13.
  - INA186 VS/±IN: 1 via.
  - SH-6 GND (U12.8): 1 via.
- **Core**: 25 power pins, including all RP2354A IOVDD/DVDD and both BMI270 supplies, are fed by F.Cu tracks with
  0–1 via within 1.5 mm. There is no F.Cu power pour.
  - These are low-current pins with local decoupling, so this is acceptable. The exception is ADC_AVDD (U2.44),
    which shares the IOVDD track and has no separate filter.

### 3.5 Current-sense accuracy (`lr_kelvin.py`)

INA186 U25 (B side, (64.27,51.11)) senses the 0.2 mOhm shunt Rsense2:
- **+IN** is a 0.2 mm track to the /CSA+ copper next to shunt pad 1. That is near-Kelvin: the tap sits within the
  pad's own potential span.
- **−IN** goes through a via into the +BATT inner planes at (64.15,51.65), 5.6 mm from shunt pad 2.

With phase-A high side of all four motors at 20 A:
- −IN sits 9.17 mV below shunt pad 2. The amplifier sees 23.4 mV for a true 16.0 mV.
- Per FET, the −IN pick-up is 0.035 mOhm (Q3) to 0.210 mOhm (Q19) per amp, so the reading is **+17 % to +105 %**
  depending on which phase conducts. Motor 3 (Q15–Q19) doubles its own current reading.

Fix: run two 0.2 mm Kelvin tracks as a pair, from U25 ±IN to the inner edges of the two shunt pads, on B.Cu or
In6-referenced copper. Never via into a plane that carries current.

### 3.6 What-if studies (`lr_whatif.py`, same solver, +BATT shunt → 12 drains, scenario 4 x 20 A)

| variant | R mean mOhm | R worst | 80 A loss | vias >2 A |
|---|---|---|---|---|
| as routed | 0.729 | 1.033 | 2.30 W | 4 |
| F.Cu +BATT under the Core given to GND (only) | 1.130 | 2.180 | 3.21 W | – |
| In5 = full +BATT plane (keeping the +10V island) | 0.572 | 0.820 | 1.89 W | 3 |
| … and F.Cu under the Core given to GND | 0.782 | 1.373 | 2.39 W | 2 |
| In4 = additional full +BATT plane | 0.433 | 0.609 | 1.42 W | – |
| … and F.Cu under the Core given to GND | 0.508 | 0.783 | 1.58 W | – |
| **proposed: In4 + In5 full +BATT planes** | **0.387** | **0.541** | **1.29 W** | **1** |
| GND as routed (12 LS → battery −) | 0.445 | 0.595 | 1.49 W | 18 |
| GND with In3 as a full GND plane | 0.325 | 0.431 | 1.06 W | 15 (local crowding, see §3.3) |

Conclusions:
- F.Cu under the Core is a real +BATT conductor today. Removing it alone raises the mean by 55 % and doubles the
  resistance to Q21/Q23.
- With two inner +BATT planes, the area under the Core can become GND and the board is still 30 % better than today.
- The LV rails need no plane: +5V ≤ 3 A, +3V3 ≤ 0.6 A, +4v5 ≤ 0.8 A. Wide tracks or local pours on B/F carry them.

### 3.7 Decoupling and hot loops

- **Half-bridges**: good. Every leg has a dedicated 0805 cap directly under or next to it on B (`lr_bridgeloop.py`:
  0.27–0.39 mm plan-view gap from drain to cap+ plus source to cap−). The 14 bulk caps have no value/MPN; specify
  them, for example 50 V X7R ≥ 1 uF effective at 25 V.
- **Bucks U3/U4** (LMR51430, SOT-23-6, B side): the single 0805 4.7 uF input cap is 3.1–3.3 mm from the VIN/GND
  pins (loop ≈ 3 mm²).
  - VIN (pin 3) and GND (pin 1) are on the same package edge, 1.9 mm apart. A 0402 100 nF straddling them takes the
    HF loop to < 0.5 mm².

---

## 4. Noise / SI

Full table: `lr_si.txt`. Victims are sampled every 0.05 mm. "run ≤0.5/≤0.2" is the length within that edge gap of
aggressor copper on the same layer. "h" is the layer-centre distance. "splits" counts reference-net changes along
the track.

| board | victim | layer | len mm | nearest aggressor (same layer) | same-layer run ≤0.5 / ≤0.2 mm | broadside / cross-board | reference (nearest layer) |
|---|---|---|---|---|---|---|---|
| Base | USB D+/D- | In2 | 18.9 | +BATT pour 0.16 mm | **16.2 / 9.6** | – | In3 h0.135: +5V_USB 48 %, +4v5 25 %, void 21 %, **12 splits** |
| Base | USB | F | 7.7 | +BATT 0.16 | 3.5 / 2.0 | – | In1 GND 64 %, void 24 % |
| Base | SD SPI0 | In5 | **42.0** | +BATT 0.13; **phase nodes within 0.5 mm for 3.0 mm** | +BATT 4.4 / 2.1 | +BATT on In4 0.7 | In4 h0.135: +3V3 68 %, +5V 9 % |
| Base | SD SPI0 | F | 17.2 | +BATT 0.16 | +BATT 15.2 / 10.1, phase 0.7 | – | In1 GND 77 %, void 17 % |
| Base | DShot MOTOR1-4 | In2 | 28.4 | **phase nodes 0.27 @(66.47,63.87)** | phase 6.0 / 0 | – | In3 +3V3 62 %, 10 splits |
| Base | SX1281 SPI/ctl | In2 | 96.6 | phase 1.02 @(78.91,67.92) | – | – | In3 +3V3 71 %, 14 splits; In1 GND at 0.335 |
| Base | RX xtal/TCXO | B | 7.3 | U21 DCC_SW 3.58 | – | – | In6 GND 94 % |
| Base | RF (FL1, U.FL, WiFi) | B | 4.8 | DCC_SW 3.20 | – | – | In6 GND 89 %, void 9 % |
| Base | CURR/VBAT ADC | B | 10.3 | +BATT 0.37 | 0.2 / 0 | – | In6 GND 95 % |
| Core | ADC CURR/VBAT | B | 11.6 | +BATT 0.22 | 0.8 / 0 | **over Base +BATT 6.2 mm** | In4 GND 87 %; Base F: +BATT 44 %, +5V 26 % |
| Core | Video (VIDEO_IN etc.) | B | 10.0 | – | – | **over Base +BATT 7.2 mm** | In4 GND 88 % |
| Core | CRSF UART1 | B | 21.9 | – | – | **over Base +BATT 21.6 mm, over phase nodes 1.5 mm** | In4 GND 82 % |
| Core | DShot | B | 9.0 | +BATT 1.94 | – | over Base +BATT 6.8 mm | In4 GND 78 % |
| Core | USB | In2 | 29.7 | +BATT 2.25 | – | – | In1 GND 90 % (h0.145) |
| Core | SD SPI0 | In2 | 30.6 | – | – | – | In1 (h0.145) GND 83 %, 10 splits; In3 (h0.285) void 54 % |
| Core | IMU SPI1 | F / In2 | 12.4 / 7.3 | VREG_LX 7.45 | – | – | In1 GND 83 % / 70 % |
| Core | FC crystal | F | 7.4 | VREG_LX 7.06 | – | – | In1 GND 95 % |

Aggressor inventory under the Core (`lr_aggmap.py`; plan-view length inside the Core outline):

| class | In2 | In5 | B.Cu |
|---|---|---|---|
| phase nodes | 95.1 of 170.5 mm | 4.6 of 58.2 mm | 12.6 of 19.3 mm |
| gate drive | 4.6 of 80.4 mm | 6.3 of 79.4 mm | 27.6 of 71.9 mm |
| BEMF/comparator | 12.8 of 12.8 mm | – | 37.7 of 39.5 mm |

Broadside capacitance from switch nodes to the planes (`lr_overlap.py`, parallel plate, εr 4.2, no fringing):
- phase nodes: 26.9 pF to GND, 5.8 pF to +5V, 3.4 pF to +3V3, 1.4 pF to +3.3V (the FC supply that crosses the
  LGA), 1.1 pF to +4v5;
- at ~1 V/ns that is 1–6 mA of edge current into each LV plane.

Cross-board (`lr_xboard.py`): plan-view distance from Core parts to Base copper.

| Core part | phase-node copper | gate drive | buck SW | heat source | Base parts directly underneath |
|---|---|---|---|---|---|
| BMI270 (U8) | 0.0 mm | 4.8 mm | 3.8 mm | Q21 2.8 mm | 7 (B side) |
| crystal X1 | 0.0 mm | 1.7 mm | – | U18 2.1 mm | – |
| COS8051 OSD (U10) | 0.0 mm | – | **1.2 mm** | U4 1.6 mm, L2 1.7 mm | – |
| RP2354A | – | – | – | – | 39 Base parts, including drivers U16 and U15 |

The Core's In1/In4 GND planes shield electric coupling. Gyro thermal drift above Q21 and the video OSD 1.2 mm from
the 5 V buck switch node are the realistic risks.

Stackup conclusion. The Base dielectric order is F-0.1-In1-0.3-In2-0.1-In3-0.3-In4-0.1-In5-0.3-In6-0.1-B:
- **In2 references In3 at 0.1 mm**, and In3 is a five-way power split.
- **In5 references In4 at 0.1 mm**, and In4 is a +5V/+3V3 flood.
- GND (In1, In6) is the far (0.3 mm) reference for both inner signal layers.

The fix is to make **In3 GND**. Then In2 (the main signal layer) has GND at 0.1 mm. Move +BATT into In4/In5 (§3.6),
and the LV rails to local pours. On the Core, the stack is fine (In2 is 0.11 mm from In1 GND, B.Cu 0.1 mm from In4
GND); the problem is only what B.Cu faces on the Base.

RF: the SX1281 RFIO → FL1 (2450FM07D0034, matched filter) path is 1.28 mm of 0.16 mm track on B.Cu over In6 GND,
then one via to the U.FL (JP1, F.Cu).
- At h = 0.1 mm a 0.16 mm microstrip is ≈ 53 Ohm. Fine.
- The transition via has 2 GND vias within 0.8 mm and 7 within 1.2 mm. Add 2 more symmetric GND vias within
  0.6 mm.
- The antenna keepout rule area (79.5–84.0, 75.3–77.9) is present on all layers.

---

## 5. Density

### 5.1 Body-to-body gaps (fab/model bodies, not courtyards; `lr_density.py`)

| side | parts | bodies % of board | median NN gap | ≤ 0.30 mm | > 0.5 mm | pairs < 0.2 mm |
|---|---|---|---|---|---|---|
| Core F | 64 | 26 % | 0.325 mm | 48 % | 4 (R33 0.77, C7, R25, C35) | 1: C34–U10 (C34 sits between U10's gull-wing leads; model hull overlap 0.21 mm², verify) |
| Base F | 20 | 28 % | 0.27 mm | 70 % | 6 (U12 1.83, USB1 1.56, C105/C106 0.67, L2/L3 0.53) | 1: **R34 under Card1 body (0.37 mm² overlap)** |
| Base B | 208 | 38 % | 0.42 mm | 34 % | 57 (e.g. R22, C71, D4 0.78; FL1 0.74; U3 0.70; C18/C82/C70 0.70; L4 0.68; U4 0.63; U15/U17 0.60; Rsense2 0.60; U22 0.59) | 0 |

Free area (0.1 mm halo around bodies and pads, 0.3 mm from the edge, pieces ≥ 0.5 mm wide):
- Core F: **83 mm²** (23 % of the Core). Largest pieces are 40 mm² across the top between the solder-pad row and the
  parts (103–118, 44–50.5, core coords) and 19 mm² at the right (115–121, 51–61).
- Base F outside the Core: **150 mm²**. Largest: 55 mm² at (61–77, 45–53) between the battery pads and the Core;
  26 mm² at (80–92, 71–77) around U12/JP1.
- Base B: **237 mm²**. Largest connected region: 101 mm² around (85.5,65.8), the right half under the Core;
  38 mm² at (59–77, 45–50).

At the 0.2 mm target the Base B side alone has room for the whole RX section (≈ 60 mm² of bodies and pads) or for
moving the TF socket's F-side job elsewhere. In practice: tighten Base B to a ~0.25 mm median and give the freed
area to vias (findings 5 and 10).

### 5.2 Side changes (`lr_density.py`: the part's envelope + 0.1 mm halo is free on the other side at the same XY)

- B → F: R82, C72, R100, R112, R24, R113, D4, C67, R21, D6 (10 parts) fit without moving anything. Value: small.
- F → B: none fit. Base F is the deliberate heavy/tall side (MOSFETs, USB-C, inductors, TF, SH-6, U.FL, LGA);
  keep it that way.
- Bigger levers:
  - The **TF socket (Card1)** sits on the +BATT path to motor 2 (§3.2). Moving it, for example over the 101 mm²
    free region's mirror on F (it does not fit there today because the Core covers it), is a floorplan decision.
  - **U21 next to U22** shortens the RX SPI from 97 mm.

### 5.3 Unused pads that can be removed (`lr_density.py`; "no net / unconnected / single-pad")

| ref | part | removable pads | remark |
|---|---|---|---|
| U2 (Core) | RP2354A QFN-60 | 55–59 QSPI_SD3/SCLK/SD0/SD2/SD1 | must stay unconnected on RP2354 (in-package flash). Removing them frees a 2 mm channel along U2's bottom edge. **Keep 24/25 SWCLK/SWDIO** and bring them to pads (decision) |
| U8 (Core) | BMI270 | 9 INT2, 10 OCSB, 11 OSDO | keep. IMU solder-joint symmetry matters more than 3 pads of routing |
| U13/U15/U17/U19 | AT32F421 QFN-28 | 8–9 each: PF1/OSC_OUT 3, PA2 8, PA3 9, PA6 12, PA15 23, PB3 24, PB5 26, PB6 27, PB7 28 | 0.4 mm pitch, so each removal opens a channel; firmware must keep them as outputs or pulled |
| U22 | ESP32-C3 | SPIHD 19, SPICS0 21, SPICLK 22, SPID 23, SPIQ 24, GPIO18 25, GPIO19 26 | flash pins only if the BOM part is **ESP32-C3FH4/FN4** (the BOM line has no MPN). With a plain ESP32-C3 an external flash is required |
| U21 | SX1281 | 9 DIO2, 10 DIO3 (6 XTB is NC with the TCXO) | **pad 5 is GND and must be connected, not removed** (finding 11) |
| U14/U16/U18/U20 | NSG2065Q | NC 5, 7, 8, 21 (2–4 left each) | |
| U7 | LP5912 | 2 NC | |
| AE2, D9 | antenna pad 2, WS2812 DOUT | keep (mechanical / tuning) | |

Already deleted by the maintainer (schematic-parity "no pad for pin"): Core U6.2; Base USB1 A8/B8, Card1 1/8,
U13 2/23, U14 7, U15 2, U16 7/8, U17 2, U19 2/23, U20 7, U22 4/20 (16 pads).

---

## 6. Double-sided assembly and the stack

| item | finding |
|---|---|
| Sides | Core: 86 parts on F, B = J91 only (enforced by the DRU rule "Core bottom is the LGA only"). Base: F 33 parts (12 HS MOSFETs, USB-C, L2/L3, TF socket, SH-6, U.FL, 2 x 1206, R34, 12 solder pads) plus the J90 land; B 219 parts (12 LS MOSFETs, 4 x AT32, 4 x NSG2065Q, RX, LDOs, shunt, all passives) |
| Reflow order | Base **B first** (many light parts), then **F** with the heavy and tall parts and the pre-assembled Core placed on J90 in the same pass. Every B part passes the hanging-part rule in the second reflow: the heaviest are the PowerDI3333 at ≈ 5–10 mg/mm² against the 46 mg/mm² (30 g/in²) guideline. The Core is reflowed twice (its own run, then the Base F run) |
| Parts under the LGA | Base F: none. Card1 touches the Core outline but does not overlap it. Base B: 109 of 219 parts are under the Core footprint, including U13/U15/U17/U19, U16/U18/U20, U21/U22, U7/U23, L4 and X2. That is allowed by AGENTS.md, but it also makes the Base B side under the Core un-reworkable once the Core is on |
| Core bottom keepout | No parts (good). But 110.9 mm of B.Cu signal tracks and 236 mm² of GND pour face Base +BATT through mask only (finding 7) |
| Heights | Core stack top = 0.07 joint + 0.8 board + 1.20 (U10 SOT-23-5) = **2.07 mm** above Base F. Base F parts that rise above the Core: **USB1 3.08 mm, U12 SH-6 2.90 mm, Card1 2.45 mm**; L2/L3 1.9 mm, C105/C106 1.8 mm. Base B tallest 1.35 mm (0805 bulk caps). Stack envelope ≈ 1.35 + 1.6 + 3.08 = 6.0 mm |
| Fiducials | none on either board (finding 13): add 3 per board, or panel fiducials |
| Mask logo | "AIO" opening on B.Mask at (79.3–84.7, 62.9–66.8) exposes GND 9.4 mm² and a +4v5 track 0.19 mm² (`lr_masklogo.py`). Keep the logo off foreign-net copper |

---

## 7. DRC breakdown (kicad-cli 10.0.6, `--refill-zones --schematic-parity`, private copy; `lr_drc.txt`)

pcbnew `GetUnconnectedCount()` after refill: **Core 0, Base 0** (kicad-cli unconnected_items also 0, so the
499 cap does not matter).

| board | errors | warnings | parity |
|---|---|---|---|
| Core | **0** | 52 lib_footprint_issues | 201: 199 missing_footprint (expected: the other board's parts), 1 net_conflict (U6 pad 2 deleted), 1 field mismatch (J91 description) |
| Base | **6**: 4 clearance, 2 annular_width | 440: 199 solder_mask_bridge, 199 lib_footprint_issues, 29 lib_footprint_mismatch, 7 connection_width, 3 copper_sliver, 2 padstack, 1 holes_co_located | 103: 87 missing_footprint (expected), 16 net_conflict (deleted pads, §5.3) |

The Base errors and notable warnings:
- clearance U23 pad 1/3/4 to EP: 0.134 / 0.141 / 0.134 mm on 2 oz;
- clearance USB1 shell PTH ↔ R4.2: 0.080 mm;
- annular_width USB1 PTH ×2: 0 mm (+2 padstack);
- holes_co_located: duplicate GND via at (80.43,64.01);
- connection_width:
  - Net-(U3-FB) at R18 pad 1, 0.047 mm (the buck feedback node; inspect);
  - JP1 GND pad, 0.070 mm;
  - GND via pair (65.45,60.39)/(65.86,60.10), 0.023 mm on In3/In4/In5;
  - zone necks +BATT In5 0.043 mm and +5V In4 0.075 mm.
- **solder_mask_bridge 199**: almost all are a font artefact. The "AIO" B.Mask text uses the font "Tokyo", which is
  not installed here, so kicad-cli renders a substitute that covers U15/R67–R72. The board's own render cache gives
  the real exposure: GND plus one +4v5 track. Re-run DRC on the maintainer's machine.

---

## 8. Re-route plan

Ordered so that each step is self-contained and verifiable with the `lr_*` scripts.

**Step 1: fab/assembly blockers, no re-route (Base and Core, ~2 h)**
1. Board setup → via protection `filling yes, capping yes` on both boards, and order POFV (IPC-4761 VII). Set
   finished copper 2 oz outer in the Base stackup.
2. U23 footprint: shrink the EP or the signal pads to get ≥ 0.16 mm (or a footprint-scoped rule ≥ 0.14 mm with
   NextPCB sign-off).
3. USB1 shell holes → NPTH, or a proper annular ring; move R4 ≥ 0.3 mm from the hole.
4. Delete the duplicate via at (80.43,64.01).
5. Move R34 out from under Card1.
6. U21 pin 5 to GND (schematic + a 0.3 mm stub to the EP).
7. 3 fiducials per board.
8. Bulk cap values/MPNs.
9. Keep the "AIO" mask logo off foreign-net copper.

Gain: 0 DRC errors, a DFM-clean order.

**Step 2: Base power stage (Base only)**
1. Move Rsense2 (and U25) so battery+ → shunt is a straight, wide path that does not wrap round the mounting hole.
   Put /CSA+ on F.Cu (2 oz) as well as B and two inner layers.
   - Target: /CSA+ ≤ 0.15 mOhm (from 0.52), saving ≈ 2.4 W at 80 A, and no vias above 2 A.
2. Kelvin-route U25 ±IN to the inner shunt-pad edges. Target: sense error < 2 % (from +17…+105 %).
3. Via arrays: 6–8 vias (VIPPO) along each LS source pin row and each HS drain.
   - Target: no GND via above 2 A (from 18) and hottest ≤ 1.5 A at 20 A per motor.
4. Single-via feeds → ≥ 2 vias: U23 OUT, U4 VIN, U14/16/18/20 VCC and VS, 5 V pads, Card1/U13 VDD.
5. Add a 0402 HF cap across VIN/GND of U3 and U4 (pins 3/1).

**Step 3: Base stack re-plan (Base only; decision D3)**
1. Layers: In3 → solid GND; In4 → +BATT plane; In5 → +BATT plane with the +10V island.
2. Move +5V/+3V3/+4v5/+3.3V/+5V_USB to local pours on B/F and to 0.5–1 mm tracks.
3. Move In5's 186 mm of signals (SD bus 42 mm, gate drive 79 mm, phase 58 mm) to In2/B.
4. Route phase-node (VS, BEMF) and gate nets on **B.Cu** next to the drivers, not on In2. Keep ≥ 0.5 mm plus GND
   between them and logic.

Expected:
- +BATT 0.73 → ~0.39 mOhm mean (worst 1.03 → 0.54), 80 A loss 2.30 → 1.29 W;
- GND 0.445 → 0.325 mOhm, loss 1.49 → 1.06 W;
- In2 signals get GND at 0.1 mm, with zero reference splits (today 10–15 per bus).

**Step 4: LGA re-pattern (both boards; decisions D1/D2)**
1. Edit `lib:Core_LGA_land` and `lib:Core_LGA_pads` together (they are local to this repo, unlike the OpenFC-Core
   module): 2.0 mm on-grid, depopulated, 40–44 pads, ≥ 40 % GND, corner anchors, two pads each for +10V/+5V, and
   optionally SWD.
2. Assign nets per §2.3/§2.5, with the SD bus at the bottom-left near Card1/U2 SPI0, USB at the left with GND on
   both sides, and motors in the middle away from CURR.
3. Re-map RP2354A GPIOs only within the legal sets in §2.4.

Expected: straight-line signal length 285.5 → 196.5 mm with the grid (−89 mm, ≈ −113 mm routed) or 224.8 mm
with A1 on today's pads (−61 mm, ≈ −77 mm routed); 18 of 18 (grid) or 16 of 18 (A1) signals with GND ≤ 2.0 mm,
from 7 today.

**Step 5: Core clean-up (Core only)**
1. Clear Core B.Cu of all signal tracks (110.9 mm) and keep it as LGA pads plus GND. Re-route on In2/F, which the
   shorter LGA routes make possible.
2. Delete the U2 QSPI pads 55–59.
3. If D7 is accepted, bring out SWD.

Expected: zero signal length over Base +BATT (from 42 mm incl. video/ADC/UART); the J90 +BATT ring stops mattering.

**Step 6: density pass (Base)**
1. Compact Base B towards the 0.2 mm target (median 0.42 → ~0.25 mm; 237 mm² free).
2. Delete the unused pads in §5.3 where they free a channel.
3. Place U21 against U22's SPI pins: 97 → ~50 mm.
4. Spend the recovered area on step 2's via arrays and on GND stitching round the RF via.

**Step 7: verify**

ERC, DRC with `--refill-zones --schematic-parity` on both boards, then re-run `lr_dump.py`, `lr_lga.py`,
`lr_power.py`, `lr_kelvin.py`, `lr_si.py` and `lr_density.py`, and compare against the numbers above.

## 9. Decisions for the maintainer

| id | decision | options / my recommendation |
|---|---|---|
| D1 | LGA pattern | (a) keep the 34 positions and re-assign (§2.3, minimal mechanical change); (b) **2.0 mm grid, 40–44 pads, ≥ 40 % GND** (recommended) |
| D2 | What the Core's B.Cu faces | (a) **Core B.Cu signal-free** plus ≥ 0.3 mm +BATT clearance round J90 (cheapest); (b) also make Base F under the Core GND, which only pays off together with D3 (§3.6) |
| D3 | Base stack | **In3 GND, In4/In5 +BATT** (recommended), or keep and accept the In2 reference splits |
| D4 | POFV on both boards | required while vias stay in pads, at NextPCB cost |
| D5 | Current rating | this review assumed 20 A per motor. At 30 A every via current is ×1.5 and every loss ×2.25 |
| D6 | Shunt / battery-pad floorplan | moving Rsense2 changes the battery-lead position |
| D7 | SWD access on the Core | 2 extra LGA pads to Base test pads; today the RP2354A cannot be debugged |
| D8 | Blind/buried vias (NextPCB HDI) | would remove the 735-hole perforation of every Base GND plane and free the LGA field; cost |
| D9 | ESP32-C3 variant in the BOM | FH4/FN4 lets 5 flash pads go |
| D10 | TF socket location | it blocks +BATT F.Cu to motor 2 and is 2.45 mm tall next to the Core |
