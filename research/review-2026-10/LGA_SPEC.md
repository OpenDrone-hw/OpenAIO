# OpenAIO Core/Base LGA interface: R2a spec

This spec is for the agent that applies step R2. It covers the new J90 land on the Base, the new J91 pads on the Core,
the net assignment, the GPIO map, and three placements that the decisions move: U7 to the Core (S1), the VTX pads to
the Base (S2) and the SWD test pads (D7).

The analysis is read-only. It was run on the d81e559 boards (`scratchpad/rev/d81e559/hardware`, zones refilled, read
through the review dumps `lr_core.json` and `lr_base.json`). Nothing under `/home/user/OpenAIO` was changed.

The placement does not change. The Core outline, J91 at Core (114.4819, 53.2758) rot 180 on B.Cu, and J90 at Base
(80.2500, 61.6500) rot 0 on F.Cu all stay. Coordinate rules:
- `base = core + (-34.2319, +8.3740)`. Both boards are seen from the top and nothing is mirrored.
- The footprint-local coordinates for J90 are the board offsets from the footprint origin.
- The library coordinates for J91 have x negated, because the footprint is flipped onto B.Cu at rot 180.

Files in `scratchpad/r2a/`:

| File | Content |
|---|---|
| `lga_spec.json` | Machine-readable spec. `pads[]` gives `pad`, `net`, `role`, `core_xy`, `base_xy`, `j90_local`, `j91_lib_local`, the endpoints, the legs and the via notes. Also `gpio`, `u7.kicad`, `vtx_pads_base`, `swd_testpads_base` and `metrics` (including the rule check) |
| `lr_img/lga_spec.png` | The pattern over the Core (left) and over the Base (right), with the d81e559 pads dotted |
| `r2a_geo.py`, `r2a_opt.py`, `r2a_sweep.py`, `r2a_pick.py`, `r2a_report.py`, `r2a_fig.py`, `r2a_vtx2.py`, `r2a_md_tables.py` | The scripts that produced every number in this spec. They reuse `review/lr_common.py` and the d81e559 dumps |
| `sweep_*.log/json`, `chosen.json` | Optimiser runs and the chosen solution |

## 1. Headline

| Metric | d81e559 (34 pads) | R2a (46 pads) |
|---|---|---|
| Pads: signal / power / GND | 18 / 5 / 11 (GND 32 %) | **20 / 5 / 21 (GND 46 %)** |
| Straight-line Core end → pad → Base end, the 17 signals that cross on both | 260.7 mm | **201.7 mm (−59.0 mm, −23 %)**. The lower bound, with every pad on its straight line, is 170.2 mm |
| The same, all 20 R2a signals | – | 221.4 mm (PU0RX 9.3, SWDIO 5.9, SWCLK 4.5) |
| Signals with a GND pad within 1 pitch (2.0 mm) | 7/18 (worst 6.6 mm, 10V_ENABLE) | **20/20, all orthogonally adjacent** |
| Pattern centroid offset from the Core outline centroid | 1.41 mm | **0.70 mm** |
| Pad convex hull as a share of the Core area | 75 % | **81 %** |
| RP2354A GPIO changes | – | **none** (§5) |
| Core vias in pad (POFV) | 30 vias in 23 pads, B.Cu routed | 25: one per non-GND pad. GND pads sit in the B.Cu GND pour, and B.Cu carries no signals |

The routed copper should fall by about 75 mm. This uses the review's routed/straight ratio of 1.27 for today's routing.
The straight-line numbers use the same endpoint model for both columns:
- Core end: the RP2354A pin, or the part pin that drives the net.
- Base end: the load pin.
- LED_STRIP is measured to the nearest of its four corner pads.

So the d81e559 column is 260.7 mm, not the review's 285.5 mm. The review's figure counted 18 signals, including
10V_ENABLE, and took a different LED_STRIP end.

## 2. Nets that cross (verified against the d81e559 netlist and decisions B1, B2, S1, S2, D7)

| Net | Pads | Core side (d81e559 netlist) | Base side | Change against d81e559 |
|---|---|---|---|---|
| CURR | 1 | R5.1 (1 kΩ to the ADC, GPIO28) | U25.6 (INA186 OUT) | none. U25 may move with D6 |
| SPI0.MISO / SCK / MOSI | 3 | U2.32 / .29 / .31 (GPIO20/18/19) | Card1.7 / .5 / .3 | none |
| FLASH_CS (SD CS) | 1 | U2.33 (GPIO21) | Card1.2, R34.2 | none |
| USB_D+ / USB_D- | 2 | R9.2 / R8.1 (30 Ω) | USB1.A6+B6 / A7+B7 | none |
| MOTOR1..4 | 4 | U2.37 / .36 / .35 / .34 (GPIO25..22) | R39 / R58 / R77 / R96 pin 1 | none |
| BUZZER- | 1 | Q1.3 (AP1606 drain) | J29 | none (drivers stay on the Core) |
| LED_STRIP | 1 | Q2.3, R14.2 | J20, J21, J31, J32 | none |
| UART0_TX / RX | 2 | U2.2 / .3 (GPIO0/1), J49 / J48 | U12.3 / .4 (SH-6) | none |
| UART1_TX / RX | 2 | U2.9 / .10 (GPIO6/7, AUX), J54 / J55 | U22.27 / .28 (ESP32-C3) | **B2: U12.6 comes off UART1_RX** |
| PU0RX | 1 | U2.5 (GPIO3, PIO UART0 RX), J45 | **U12.6 (SH-6 SBUS)** | **New (B2).** Today it is the local net `/Pads/PU0RX`; it must become a net that crosses the LGA |
| SWDIO / SWCLK | 2 | U2.25 / U2.24 (unconnected today) | **2 new Base test pads** (§8) | **New (D7)** |
| +4v5 | 2 | **U7 IN/EN (new on the Core)**, U6.4/.6, C25, J42, J52, R23 | D2.1 / D3.1 (OR diodes), U23 | U7, its CIN and COUT move to the Core (S1) |
| +5V | 2 | J30, J37 (5 V user pads), R14.1 | U4 / L3.2 and the 5 V pads | none |
| +BATT | 1 | R1.2 (VBAT divider only) | the power stage | none |
| GND | 21 | | | 11 → 21 |
| ~~10V_ENABLE~~ | – | | | removed (B1, 9aba717). GPIO27 is free |
| ~~+10V~~ | – | J41, J51 (VTX pads) | | **removed (S2).** J41 and J51 leave the Core; the VTX pads go on the Base (§7) |
| ~~+3.3V~~ | – | all FC 3.3 V loads | U7, C28, D6, R24 | **removed (S1).** U7 moves to the Core (§6) and C28 is dropped. **D6 and R24 (power LED on +3.3V) must move to the Core or be deleted**, because +3.3V no longer exists on the Base |

## 3. Pad count per net, from current

A 1.0 mm land is 0.785 mm². A SAC305 joint about 70 µm tall is about 13 µΩ. At 1 A that is 13 µW and 0.13 kA/cm²,
two orders of magnitude below the current density where solder electromigration matters. The joint is therefore not
the limit. Two things are:
- **The feed.** Each pad is fed by one 0.35/0.20 mm via in pad on each board. The review's working limit is about 1 A per
  via for a 10 °C rise. A second via fits in the land if a pad needs more: 0.45 mm centres, 0.25 mm hole to hole.
- **Redundancy.** An open LGA joint can be neither seen nor reworked. Coplanarity is the dominant risk: IPC bow on the
  0.8 mm Core allows about 0.2 mm, against a joint about 0.06 mm tall.

Rule applied: any supply whose single open joint browns out or bricks the board gets 2 pads. With one joint open, the
other pad must carry the whole design current at 1 A or less.

| Net | Pads | Load estimate (Core side) | Design current | Per pad (both / one open) |
|---|---|---|---|---|
| +4v5 | **2**, adjacent | U7 LP5912-3.3 feeds the whole FC 3.3 V rail: RP2354A core regulator and IO, BMI270, OSD, LEDs. That is 0.10–0.15 A typical; the LDO is rated 0.5 A. U6 (1.8 V gyro) draws about 1 mA. J42/J52 can power an external receiver or GPS, up to about 0.3 A | 0.8 A | 0.4 / 0.8 A |
| +5V | **2** (pad 6 by J30, pad 22 towards J37) | J30 (GPS/mag, up to 0.1 A), J37 (camera, up to 0.3 A), R14 (LED_STRIP pull-up, 2 mA) | 0.5 A, sized for 1 A | 0.25–0.5 / 0.5–1 A. Core +5V copper ties both pads, so one open joint still feeds both user pads |
| +BATT | **1**, fenced by GND | R1/R2 VBAT divider: 25.2 V / 110 kΩ = 0.23 mA | < 1 mA | An open joint reads VBAT = 0, which Betaflight flags. Nothing is damaged. It is 25 V on a pad, so its orthogonal neighbours are GND or empty (§4) |
| GND | 21 | return for the above (1.3 A or less) plus every signal return | – | Count is set by the return-path and anchor rules, not by current |
| signals | 1 each | mA-level | – | – |

## 4. The pattern

**Grid.** 2.0 mm pitch with round 1.0 mm pads. Pads sit at J90-local (0.25 + 2i, 1.25 + 2j). That offset gives the most
sites (79) inside the Core with the pad edge at least 0.35 mm from the outline. Of the 79 sites, 46 are used.

**Hard rules.** The optimiser charges 60 mm per violation. The final pattern meets every one, and `metrics.rules` in the
JSON shows the check:
- Every signal pad and every power pad has a GND pad orthogonally adjacent: 20/20 signals, 5/5 power.
- The USB pair is orthogonally adjacent, D- above D+ (pads 37 and 42). GND pads 30 and 45 close both collinear ends.
- No MOTOR pad is orthogonally or diagonally adjacent to CURR, USB or +BATT.
- The +BATT pad (36) has only GND or empty sites as orthogonal neighbours. Its one diagonal neighbour is FLASH_CS (pad
  29), 1.83 mm edge to edge.
- Each of the 7 convex Core corners has a GND anchor on the nearest site: TL pad 1, TR pad 2, left chamfer pad 11, ear
  top pad 27, ear bottom pad 35, BR pad 43, BL pad 44.
- Each non-GND pad has a Core via-in-pad position that clears every other-net Core F.Cu pad by 0.09 mm. U7 and its caps
  are included as obstacles.

**Soft costs**, in mm-equivalent:
- A Base via-in-pad blocked by a B.Cu part pad: 10 for a signal or power pad, 2 for GND. The Base via clears B.Cu pads
  by 0.16 mm (2 oz).
- A pad within 0.3 mm of a Core user solder pad (a wire soldered there reheats the joint): 6 for a signal, 1.5 for GND.
- Pattern centroid more than 0.3 mm off the Core centroid: 10 per mm.
- +BATT diagonal to any pad: 3.
- CURR next to an aggressor: 2.
- +4v5 pads not adjacent: 4.
- Each changed GPIO: 2.

**Search.** Simulated annealing over sites, nets and legal GPIOs, then exhaustive 2-swap descent:
- 35 grid offsets;
- 17 to 23 GND pads on the three best offsets;
- about 40 seeds on the chosen offset.

Run-to-run spread is about ±5 mm of cost. The best 21-GND solution beats the best 19-GND one by about 8 mm.

**Map**, top view (Base F.Cu view, the Core seen through), J90-local mm. `pad:net`. VBAT! = +BATT, DP/DM = USB_D+/D-,
SDCS = FLASH_CS, M1..M4 = MOTOR1..4.

```
J90 local y \ x     -9.75    -7.75    -5.75    -3.75    -1.75     0.25     2.25     4.25     6.25     8.25    10.25
          -8.75     1:GND        .        .        .        .        .        .    2:GND        .        .        .
          -6.75     3:4V5    4:4V5    5:GND        .        .     6:5V    7:GND        .        .        .        .
          -4.75         .        .        .   8:CURR    9:GND 10:SWDIO        .        .        .        .        .
          -2.75    11:GND   12:SCK        .  13:MOSI   14:GND   15:GND   16:GND        .        .        .        .
          -0.75         .  17:MISO   18:GND        .    19:M3 20:SWCLK    21:M4    22:5V        .        .        .
           1.25         .    23:M2    24:M1        .        .  25:U1RX        .   26:GND        .        .   27:GND
           3.25         .   28:GND  29:SDCS   30:GND   31:GND   32:GND  33:U1TX   34:BUZ        .        .   35:GND
           5.25         . 36:VBAT!        .    37:DM  38:U0TX  39:U0RX 40:PU0RX   41:GND        .        .        .
           7.25         .        .        .    42:DP        .        .        .        .   43:GND        .        .
           9.25         .   44:GND        .   45:GND   46:LED        .        .        .        .        .        .
```

**Per-signal straight-line length**, in mm. The new numbers use the same GPIOs as today.

CURR is the one signal that gets longer: 24.6 mm against 18.4 mm. Every site on the R5 side is blocked or taken:
- (106.73, 54.53) and (106.73, 56.53) are Core-blocked by U2 pins 34–42, Q1, R5.2 and C9;
- (104.73, 48.53) is Core-blocked by U10 and C34;
- (106.73, 48.53) is Base-blocked by R87, R89 and R90;
- the rest went to MISO, SCK, MOTOR2 and +BATT.

CURR is an op-amp output with an RC filter at the ADC. U25 may move anyway under D6.

| signal | today mm | new mm | new, GPIO unchanged | direct (lower bound) |
|---|---|---|---|---|
| CURR | 18.4 | 24.6 | 24.6 | 16.8 |
| SPI0.MISO | 14.4 | 4.9 | 4.9 | 4.2 |
| SPI0.SCK | 16.1 | 9.4 | 9.4 | 7.1 |
| SPI0.MOSI | 20.8 | 15.6 | 15.6 | 7.5 |
| FLASH_CS | 24.7 | 10.0 | 10.0 | 7.8 |
| USB_D+ | 19.8 | 18.5 | 18.5 | 18.5 |
| USB_D- | 18.3 | 18.8 | 18.8 | 17.7 |
| MOTOR1 | 10.7 | 9.8 | 9.8 | 6.4 |
| MOTOR2 | 4.7 | 2.1 | 2.1 | 2.0 |
| MOTOR3 | 10.0 | 6.2 | 6.2 | 6.0 |
| MOTOR4 | 13.5 | 13.2 | 13.2 | 12.3 |
| BUZZER- | 19.3 | 19.6 | 19.6 | 19.3 |
| LED_STRIP | 18.7 | 15.5 | 15.5 | 14.2 |
| UART0_TX | 12.5 | 8.1 | 8.1 | 6.8 |
| UART0_RX | 15.3 | 7.3 | 7.3 | 7.3 |
| UART1_TX | 10.3 | 8.8 | 8.8 | 7.7 |
| UART1_RX | 13.2 | 9.1 | 9.1 | 8.6 |

## 5. RP2354A GPIO map: no changes

The chosen pattern keeps every GPIO as it is today. Two alternatives were checked:
- **Re-mapping on this pattern.** The exact assignment inside the legal sets (§2.4 of the review: SPI0 instance sets,
  UART0/UART1 including AUX, PIO anything, ADC only GPIO26–29) saves **2.1 mm** of Core straight line, for 3 changes:
  FLASH_CS 21→27, MOTOR3 23→21, MOTOR1 25→23. Not recommended.
- **Joint optimisation of pattern and GPIOs**, at 0.5 mm per change. The best found is 199.4 mm, only 2.3 mm better
  than the chosen pattern, and it needs 6 changes: SPI0.SCK 18→22, SPI0.MOSI 19→23, FLASH_CS 21→27, MOTOR4 22→18,
  MOTOR3 23→21, MOTOR1 25→19. Rejected.

**Betaflight target change list.** Betaflight's PICO platform names GPIOn as PAn. Check each define name against the
target's `config.h`. Nothing changes because of the LGA. These rows change because of the decisions:

| Function | GPIO | Betaflight pin | Change |
|---|---|---|---|
| UART0 TX / RX (SH-6 pins 3/4, J49/J48) | 0 / 1 | PA0 / PA1 | none |
| PIO UART0 TX / RX (J44 / J45, **and SH-6 pin 6 SBUS**) | 2 / 3 | PA2 / PA3 | **B2: DJI SBUS now arrives on PIO UART0 RX (GPIO3).** Set serial RX on that port for an SBUS air unit |
| UART1 TX / RX (ESP32-C3, AUX F11) | 6 / 7 | PA6 / PA7 | none. **B2: CRSF from the onboard ELRS only.** SH-6 pin 6 is no longer on it |
| SPI0 SCK / SDO (MOSI) / SDI (MISO), SD CS | 18 / 19 / 20, 21 | PA18 / PA19 / PA20, PA21 | none |
| MOTOR4 / 3 / 2 / 1 (PIO DShot) | 22 / 23 / 24 / 25 | PA22..PA25 | none |
| LED0 | 26 | PA26 | none |
| ~~10V_ENABLE~~ | 27 | PA27 | **B1: remove** any PINIO or VTX-power box that drives GPIO27. The pin is spare |
| ESC current ADC / VBAT ADC | 28 / 29 | PA28 / PA29 | none |
| SWCLK / SWDIO | dedicated pins 24 / 25 | – | D7: hardware only |

## 6. U7 (LP5912-3.3, S1) on the Core F.Cu

| Part | Core x, y | KiCad rot | Pins / pads |
|---|---|---|---|
| U7 LP5912-3.3DRVR (C524780), WSON-6 2x2 | **108.750, 47.100** | 180 | pin 1 OUT (109.638, 47.750); pin 6 IN (107.862, 47.750); pin 4 EN (107.862, 46.450), tied to IN as today; pin 5 GND and EP to GND |
| CIN 1 µF 25 V 0402 CL05A105KA5NQNC (C52923) | **107.165, 47.390** | 90 | pad 1 +4v5 at y 47.87, next to pin 6; pad 2 GND |
| COUT 1 µF 25 V 0402 (C52923) | **110.335, 47.390** | 90 | pad 1 +3.3V at y 47.87, next to pin 1; pad 2 GND |

- **Block.** 3.79 x 2.10 mm, bounds x 106.855–110.645 and y 46.050–48.150. It sits in the top band of Core F.Cu,
  between the user-pad row (J40, J23) and the OSD and crystal group.
- **Clearances.** Envelope to envelope (body plus pads): U10 0.21, X1 0.22, J23 0.24, R31 0.25, C10 0.25, R32 0.25,
  J40 0.27 mm. All meet the 0.2 mm target.
- **Why here.** It is the only free spot that takes the block with a 0.2 mm halo. Core F.Cu has 83 mm² free, mostly
  this band. No other free region (19 mm² beside U8 and U6, 9 mm² in the ear) takes it. The runner-up, (111.30, 47.10)
  at the same rotation, is 0.4 mm worse.
- **+4v5 side.** The +4v5 LGA pads 4 and 3 are 1.7 and 3.4 mm from IN, and D2/D3 on the Base sit 1.3 and 2.9 mm under
  them.
- **+3.3V side.** OUT is 4.6–4.8 mm from IOVDD pins 30 and 20. It is 11.4 mm from VREG_VIN (pin 49), where C15
  (4.7 µF) stays. Run +3.3V as an inner-layer pour.
- **COUT window.** Effective COUT is about 0.8 µF (COUT) + 2.3 µF (C15) + 11 x 100 nF, roughly 4 µF. That is inside the
  LP5912's 0.7–10 µF window from S2. C28 (22 µF, Base) is dropped. The ADC_AVDD filter in S2 is a separate item.
- **Heat and thermal path.** The BMI270 is 9.9 mm away. Dissipation is (4.6 − 3.3) V x 0.15 A, about 0.2 W. LGA GND pad
  5 is directly under U7, so the EP thermal vias land in the B.Cu GND pour over pad 5.
- **Other +4v5 loads on the Core** take +4v5 from the U7 area:
  - U6 IN (1 mA, thin trace, about 14 mm);
  - J42/J52 and R23 (up to 0.3 A, at least 0.3 mm or an In2/In3 pour).

## 7. VTX +10V / GND solder pads (S2) on the Base F.Cu, next to U12

| Pad | Base x, y | Size | Net |
|---|---|---|---|
| VTX +10V | **75.70, 73.35** | 1.2 x 1.2 mm, rounded rectangle | +10V. It is 2.26 mm from U12.1 (+10V); join them on F.Cu |
| VTX GND | **75.70, 74.90** | 1.2 x 1.2 mm | GND (0.35 mm gap to the +10V pad) |

- **How the spot was found.** The search kept these clear:
  - F.Cu part envelopes plus 0.2 mm;
  - the U24 hole and motor pads plus 0.2 mm;
  - the mounting holes, with a 2.8 mm radius (M2 grommet flange);
  - the Core outline plus 0.5 mm (iron access);
  - the board edge, 0.5 mm.
- **Only fit.** The pocket between Q13 and U12, left of pin 1, is the only place next to the SH-6 where two pads fit.
  The 1.6 x 2.2 mm Core user-pad size does not fit as a pair anywhere next to U12. A 1.6 x 1.4 pair right of U12 would
  sit 1.95 mm from the mounting-hole centre, under a standoff or washer, so it was rejected.
- **Wire size.** The pads take 26–24 AWG VTX leads.
- **Vias to move.** GND (76.41, 73.42), /RX/BOOT (75.52, 73.85), +3V3 (75.55, 74.74).

## 8. SWD test pads (D7) on the Base B.Cu

| Pad | Base x, y | Size | Link |
|---|---|---|---|
| TP SWDIO | **78.32, 55.15** | 0.8 mm round | 2.79 mm from LGA pad 10 (80.50, 56.90). It crosses one B.Cu track, Net-(U18-VB1), which must be re-routed |
| TP SWCLK | **79.88, 61.41** | 0.8 mm round | 0.80 mm from LGA pad 20 (80.50, 60.90). Two GND stitching vias must move: (79.36, 61.18) and (79.75, 61.68). It sits between TP5 and TP6 |

The test pads are at least 0.2 mm from every B.Cu part envelope and 2 mm or more from the chip antenna. Any Base GND
pad serves as the probe ground. Add a GND test pad only if a pogo fixture is planned.

## 9. What R2 and R3 must do with this

**Footprints and symbol**
- Rewrite `lib:Core_LGA_land` (J90: F.Cu, F.Mask and F.Paste, as today) and `lib:Core_LGA_pads` (J91: F.Cu and F.Mask,
  no paste, as today).
- Use the KiCad footprint editor or the pcbnew API, not a text edit.
- Each footprint gets 46 round 1.0 mm SMD pads at `j90_local` and `j91_lib_local` respectively. The origins are
  unchanged, so neither board moves.
- The LGA symbol(s) in `core_interface.kicad_sch` get pins 1–46 with the nets in the table.

**Core (R2)**
- **Via in pad.** Each of the 25 non-GND pads gets a 0.35/0.20 via in the pad (POFV, D4) at a position that clears
  every other-net F.Cu pad by 0.09 mm. Two of these vias land on the driver pad itself:
  - pad 23 (MOTOR2) on U2.36, leaving 0.125 mm to U2.35 and U2.37;
  - pad 42 (USB_D+) on R9.2.
- **GND pads.** The 21 GND pads sit in the B.Cu GND pour. Stitch the pour to In4 next to each.
- **B.Cu** carries nothing else (D2).
- **Removed.** J41 and J51 go.
- **Heat near user pads.** No signal or power pad is within 0.3 mm of a Core user pad. Five GND anchors are: 1 (J39),
  2 (J54), 27 (J35, J37), 35 (J37, J38) and 43 (J44, J48, J49). Soldering a wire on those user pads reheats only a GND
  joint.

**Base (R3)**
- **Via in pad.** Every J90 pad gets a via in the pad. The exception is +BATT pad 36, which may join the F.Cu +BATT
  pour directly. Every other pad keeps at least 0.3 mm clearance to that pour (D2).
- **Blocked vias.** Ten Base vias would land on B.Cu pads of other nets. For each, either move the part in the R3
  density pass, or run an F.Cu dog-bone of 0.5 mm or less to a via beside the pad:
  - signals: 12 SPI0.SCK (R86, R88, TP3), 23 MOTOR2 (R48, R50), 42 USB_D+ (U16 pins 2–4);
  - GND: 2 (U20.15–17), 7 (U19.19–21, U20.21–23), 14 (R105, R107), 15 (U19.6–8), 18 (R56, R59, R85), 27 (J29, J33),
    43 (U21.8–10).
- **Vias landing on their own pad.** MOTOR3 pad 19 is 0.34 mm from R77.1 and lands on it. GND pads 9, 28 and 31 land
  on GND B.Cu pads.
- **Existing vias inside pads.** Other-net Base vias inside the new pads are listed per pad. They go when R3 re-routes
  the LGA side. The phase-node vias (/1B, /1C, /2B, /2C, /3A, /4A, /4B) leave the area under the Core anyway (review
  finding 9). So do the gate-drive vias (/ESC2/AL, /ESC2/BL, /ESC4/CL).

## 10. Pad table

Columns:
- Core and Base x, y are absolute board coordinates.
- J90 local is the footprint offset; the J91 library x is the negation of it.
- The legs are straight-line mm from the Core end and to the Base end.
- Core via "in pad" means a free spot exists inside the pad.
- Base via "blocked by" lists the other-net B.Cu pads in the way.
- "Base vias to clear" lists existing Base vias of other nets inside the pad.

| pad | row,col | Core x, y | Base x, y | J90 local | net | role | Core end | Base end | Core / Base leg mm | Core via | Base via (blockers) | Base vias to clear | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1,1 | 104.7319, 44.5258 | 70.4999, 52.8998 | -9.75, -8.75 | GND | GND |  |  |  | none (B.Cu GND) | free | +10V | anchor TL; near Core pad J39 |
| 2 | 1,8 | 118.7319, 44.5258 | 84.4999, 52.8998 | +4.25, -8.75 | GND | GND |  |  |  | none (B.Cu GND) | blocked by U20.15, U20.16, U20.17 |  | anchor TR; near Core pad J54 |
| 3 | 2,1 | 104.7319, 46.5258 | 70.4999, 54.8998 | -9.75, -6.75 | +4v5 | PWR | U7.6 (new LP5912-3.3 IN) | D2.1/D3.1 (OR) | 3.4 / 1.3 | in pad | free |  |  |
| 4 | 2,2 | 106.7319, 46.5258 | 72.4999, 54.8998 | -7.75, -6.75 | +4v5 | PWR | U7.6 (new LP5912-3.3 IN) | D2.1/D3.1 (OR) | 1.7 / 2.9 | in pad | free |  |  |
| 5 | 2,3 | 108.7319, 46.5258 | 74.4999, 54.8998 | -5.75, -6.75 | GND | GND |  |  |  | none (B.Cu GND) | free |  |  |
| 6 | 2,6 | 114.7319, 46.5258 | 80.4999, 54.8998 | +0.25, -6.75 | +5V | PWR | J30 (5 V user pad) | L3.2 (U4 out) | 2.2 / 14.8 | in pad | free | +10V |  |
| 7 | 2,7 | 116.7319, 46.5258 | 82.4999, 54.8998 | +2.25, -6.75 | GND | GND |  |  |  | none (B.Cu GND) | blocked by U19.19, U19.20, U19.21, U20.21, U20.22, U20.23 |  |  |
| 8 | 3,4 | 110.7319, 48.5258 | 76.4999, 56.8998 | -3.75, -4.75 | CURR | SIG | R5.1 | U25.6 (INA186 out) | 9.9 / 14.7 | in pad | free | GND, Net-(U17-PA13) |  |
| 9 | 3,5 | 112.7319, 48.5258 | 78.4999, 56.8998 | -1.75, -4.75 | GND | GND |  |  |  | none (B.Cu GND) | on same-net B.Cu pad | /ESC4/FBCOMMON |  |
| 10 | 3,6 | 114.7319, 48.5258 | 80.4999, 56.8998 | +0.25, -4.75 | SWDIO | SIG | U2.25 | test pad (new) | 5.9 / 0.0 | in pad | free | /ESC4/CL, GND |  |
| 11 | 4,1 | 104.7319, 50.5258 | 70.4999, 58.8998 | -9.75, -2.75 | GND | GND |  |  |  | none (B.Cu GND) | free |  | anchor L |
| 12 | 4,2 | 106.7319, 50.5258 | 72.4999, 58.8998 | -7.75, -2.75 | SPI0.SCK | SIG | U2.29 (GPIO18) | Card1.5 | 2.1 / 7.3 | in pad | blocked by R86.1, R86.2, R88.1, R88.2, TP3.1 | /ESC3/FBCOMMON |  |
| 13 | 4,4 | 110.7319, 50.5258 | 76.4999, 58.8998 | -3.75, -2.75 | SPI0.MOSI | SIG | U2.31 (GPIO19) | Card1.3 | 4.2 / 11.4 | in pad | free |  |  |
| 14 | 4,5 | 112.7319, 50.5258 | 78.4999, 58.8998 | -1.75, -2.75 | GND | GND |  |  |  | none (B.Cu GND) | blocked by R105.1, R105.2, R107.1, R107.2 | /4B, /ESC4/FBCOMMON |  |
| 15 | 4,6 | 114.7319, 50.5258 | 80.4999, 58.8998 | +0.25, -2.75 | GND | GND |  |  |  | none (B.Cu GND) | blocked by U19.6, U19.7, U19.8 |  |  |
| 16 | 4,7 | 116.7319, 50.5258 | 82.4999, 58.8998 | +2.25, -2.75 | GND | GND |  |  |  | none (B.Cu GND) | free |  |  |
| 17 | 5,2 | 106.7319, 52.5258 | 72.4999, 60.8998 | -7.75, -0.75 | SPI0.MISO | SIG | U2.32 (GPIO20) | Card1.7 | 0.7 / 4.2 | in pad | free | MOTOR2, Net-(U15-PA13) |  |
| 18 | 5,3 | 108.7319, 52.5258 | 74.4999, 60.8998 | -5.75, -0.75 | GND | GND |  |  |  | none (B.Cu GND) | blocked by R56.2, R59.2, R85.1 | +3V3, /3A |  |
| 19 | 5,5 | 112.7319, 52.5258 | 78.4999, 60.8998 | -1.75, -0.75 | MOTOR3 | SIG | U2.35 (GPIO23) | R77.1 | 5.9 / 0.3 | in pad | on same-net B.Cu pad | GND, Net-(U17-PA13) |  |
| 20 | 5,6 | 114.7319, 52.5258 | 80.4999, 60.8998 | +0.25, -0.75 | SWCLK | SIG | U2.24 | test pad (new) | 4.5 / 0.0 | in pad | free | /4A, Net-(U17-PA14) |  |
| 21 | 5,7 | 116.7319, 52.5258 | 82.4999, 60.8998 | +2.25, -0.75 | MOTOR4 | SIG | U2.34 (GPIO22) | R96.1 | 9.7 / 3.5 | in pad | free | +3V3 |  |
| 22 | 5,8 | 118.7319, 52.5258 | 84.4999, 60.8998 | +4.25, -0.75 | +5V | PWR | J37 (5 V user pad) | L3.2 (U4 out) | 6.8 / 20.0 | in pad | free | GND |  |
| 23 | 6,2 | 106.7319, 54.5258 | 72.4999, 62.8998 | -7.75, +1.25 | MOTOR2 | SIG | U2.36 (GPIO24) | R58.1 | 0.5 / 1.7 | in pad, lands on same-net F.Cu pad | blocked by R48.1, R48.2, R50.1, R50.2 | /1B, /ESC1/FBCOMMON |  |
| 24 | 6,3 | 108.7319, 54.5258 | 74.4999, 62.8998 | -5.75, +1.25 | MOTOR1 | SIG | U2.37 (GPIO25) | R39.1 | 1.7 / 8.1 | in pad | free | MOTOR2 |  |
| 25 | 6,6 | 114.7319, 54.5258 | 80.4999, 62.8998 | +0.25, +1.25 | UART1_RX | SIG | U2.10 (GPIO7) | U22.28 | 0.5 / 8.7 | in pad | free | GND |  |
| 26 | 6,8 | 118.7319, 54.5258 | 84.4999, 62.8998 | +4.25, +1.25 | GND | GND |  |  |  | none (B.Cu GND) | free |  |  |
| 27 | 6,10 | 124.7319, 54.5258 | 90.4999, 62.8998 | +10.25, +1.25 | GND | GND |  |  |  | none (B.Cu GND) | blocked by J29.1, J33.1 |  | anchor EAR_T; near Core pad J37/J35 |
| 28 | 7,2 | 106.7319, 56.5258 | 72.4999, 64.8998 | -7.75, +3.25 | GND | GND |  |  |  | none (B.Cu GND) | on same-net B.Cu pad | /ESC1/FBCOMMON |  |
| 29 | 7,3 | 108.7319, 56.5258 | 74.4999, 64.8998 | -5.75, +3.25 | FLASH_CS | SIG | U2.33 (GPIO21) | Card1.2 | 3.4 / 6.7 | in pad | free | GND, MOTOR1, Net-(U15-PB4) |  |
| 30 | 7,4 | 110.7319, 56.5258 | 76.4999, 64.8998 | -3.75, +3.25 | GND | GND |  |  |  | none (B.Cu GND) | free | MOTOR3 |  |
| 31 | 7,5 | 112.7319, 56.5258 | 78.4999, 64.8998 | -1.75, +3.25 | GND | GND |  |  |  | none (B.Cu GND) | on same-net B.Cu pad | /2B, /ESC2/FBCOMMON |  |
| 32 | 7,6 | 114.7319, 56.5258 | 80.4999, 64.8998 | +0.25, +3.25 | GND | GND |  |  |  | none (B.Cu GND) | free |  |  |
| 33 | 7,7 | 116.7319, 56.5258 | 82.4999, 64.8998 | +2.25, +3.25 | UART1_TX | SIG | U2.9 (GPIO6) | U22.27 | 2.8 / 6.0 | in pad | free |  |  |
| 34 | 7,8 | 118.7319, 56.5258 | 84.4999, 64.8998 | +4.25, +3.25 | BUZZER- | SIG | Q1.3 (drain) | J29 | 12.8 / 6.8 | in pad | free |  |  |
| 35 | 7,10 | 124.7319, 56.5258 | 90.4999, 64.8998 | +10.25, +3.25 | GND | GND |  |  |  | none (B.Cu GND) | free |  | anchor EAR_B; near Core pad J37/J38 |
| 36 | 8,2 | 106.7319, 58.5258 | 72.4999, 66.8998 | -7.75, +5.25 | +BATT | PWR | R1.2 (VBAT divider) | In4/In5 +BATT plane | 1.6 / 0.0 | in pad | free | /1C |  |
| 37 | 8,4 | 110.7319, 58.5258 | 76.4999, 66.8998 | -3.75, +5.25 | USB_D- | SIG | R8.1 | USB1.A7 | 2.2 / 16.6 | in pad | free | /ESC2/AL, /ESC2/BL, GND |  |
| 38 | 8,5 | 112.7319, 58.5258 | 78.4999, 66.8998 | -1.75, +5.25 | UART0_TX | SIG | U2.2 (GPIO0) | U12.3 | 1.7 / 6.4 | in pad | free | /2C, GND |  |
| 39 | 8,6 | 114.7319, 58.5258 | 80.4999, 66.8998 | +0.25, +5.25 | UART0_RX | SIG | U2.3 (GPIO1) | U12.4 | 1.1 / 6.2 | in pad | free | GND |  |
| 40 | 8,7 | 116.7319, 58.5258 | 82.4999, 66.8998 | +2.25, +5.25 | PU0RX | SIG | U2.5 (GPIO3) | U12.6 | 3.0 / 6.2 | in pad | free | GND |  |
| 41 | 8,8 | 118.7319, 58.5258 | 84.4999, 66.8998 | +4.25, +5.25 | GND | GND |  |  |  | none (B.Cu GND) | free |  |  |
| 42 | 9,4 | 110.7319, 60.5258 | 76.4999, 68.8998 | -3.75, +7.25 | USB_D+ | SIG | R9.2 | USB1.A6 | 0.2 / 18.4 | in pad, lands on same-net F.Cu pad | blocked by U16.2, U16.3, U16.4 | /ESC2/BL |  |
| 43 | 9,9 | 120.7319, 60.5258 | 86.4999, 68.8998 | +6.25, +7.25 | GND | GND |  |  |  | none (B.Cu GND) | blocked by U21.10, U21.8, U21.9 | /RX/BUSY | anchor BR; near Core pad J48/J44/J49 |
| 44 | 10,2 | 106.7319, 62.5258 | 72.4999, 70.8998 | -7.75, +9.25 | GND | GND |  |  |  | none (B.Cu GND) | free | LED_STRIP | anchor BL |
| 45 | 10,4 | 110.7319, 62.5258 | 76.4999, 70.8998 | -3.75, +9.25 | GND | GND |  |  |  | none (B.Cu GND) | free | /RX/NSS |  |
| 46 | 10,5 | 112.7319, 62.5258 | 78.4999, 70.8998 | -1.75, +9.25 | LED_STRIP | SIG | Q2.3 (drain) | J20/J21/J31/J32 (nearest) | 1.8 / 13.7 | in pad | free | /RX/LED |  |

## 11. Limits

- **Model.** Lengths are straight lines, with no routing-congestion term. Inner-layer routing on both boards is left to
  R2 and R3.
- **Base ends are d81e559 positions.** D6 may move U25 (CURR) and D10 may move Card1 (SPI). `r2a_report.py` reads the
  endpoints from the boards, so re-run it after those moves. Re-run `r2a_opt.py` only if a Base end moves by more than
  about 3 mm.
- **Unmodelled loads.** J42/J52 (+4v5) and R14 (+5V) are routed on the Core and are not in the cost.
- **Solder joint.** The figures assume a SAC305 joint about 70 µm tall and a 1 A working limit per 0.20 mm via, the
  review's assumption.
