# OpenAIO critique, round 2 (all perspectives), commit 29c003d (branch work/d81e559)

Snapshot: `git archive 29c003d` into `critique/round2/snap/` (nothing newer reviewed). Both boards refilled in place next to their own `.kicad_pro`/`.kicad_dru` (`kicad-cli pcb drc --refill-zones --save-board --severity-all --schematic-parity`), then dumped with pcbnew. Scripts: `critique/round2/scripts/` (`dump.py`, `dump2.py`, `under_core.py`, `knockout.py`, `basechk.py`, `crtyd.py`, `missing2.py`, `paste.py`, `netparse.py`, `q.py`). Outputs: `critique/round2/out/`.

Measured baseline at 29c003d: DRC errors Base 0 / Core 0; unconnected 0 / 0; warnings Base 343 (courtyards_overlap 63, lib_footprint_issues 192, lib_footprint_mismatch 71, track_dangling 11, connection_width 4, copper_sliver 2), Core 68 (courtyards_overlap 8, lib_footprint_issues 60); parity net_conflict Base 70 / Core 7; ERC 31 errors.

## Verdict

1. **No BLOCKER.** The round-1 BLOCKER (DFM-01, Card1 under the Core corner) is fixed. The new circuits (TXU0101 LED stage, battery-only +3V3_ESC) are correct against their datasheets, and all 31 ERC errors are tool artefacts with no real circuit error.
2. **No new MAJOR.** Two round-1 owner-rule MAJORs remain partly open:
   - V2: 11 user pads still have no silk label, only a README legend.
   - V5: the assembled AIO shows no name or revision. The Core identity is on its hidden bottom face, and the Base identity is on B.Fab only.
3. **New this round:** 7 MINOR and 5 NIT. They cover a DRC coverage gap under the hat, same-net pad abutments, 25 V vias under unsoldered QFN leads, U26 paste, doc/value code drift, a dangling phase stub, and L2/L3 still THT (hidden by an `ignore`).

## ERC: 31 errors classified (none is a real circuit error)

| type | count | items | why it is not a circuit error |
|---|---|---|---|
| pin_not_driven | 16 | C37/C44/C51/C58 pin 1 (AT32 NRST nets), C40-42/C47-49/C54-56/C61-63 pin 2 (NSG2065Q VB1-3) | The ESC-sheet 100 nF symbol has pins typed Input. Each net has its real source: R37 10k to +3V3_ESC plus the NRST pin, or the NSG2065Q VB pin and its bootstrap |
| power_pin_not_driven | 9 | #PWR03 +BATT, #PWR015 +5V_USB, #PWR01 +1.1V, #PWR052 +5V, #PWR054 +4v5, #PWR066 +10V, #PWR072 +1.8V_GYRO, U24.1 VBAT, U22.2 VDD3P3 | No PWR_FLAG. Every net is fed through a passive or unspecified pin: battery pad or shunt, USB VBUS, L1 (RP2350 VREG, netlist +1.1V = L1.1 + U2.6/23/39/50), L3, D2/D3, L2, U6.1 OUT, and L6 2 nH from +3V3 (U22.2/.3) |
| bus_to_net_conflict | 3 | SPI1 sheet pin, I2C0 sheet pin, SPI0 global label (root) | Drawing stubs only. The member nets resolve: SPI1 U2.14/15/16 to U8.13/14/1; I2C0 U2.7/8 to J26/J23 + R12/R11; SPI0 U2.29/31/32 to LGA 12/13/17 to Card1.5/3/7 |
| hier_label_mismatch | 1 | root sheet pin CURR (62.23, 56.52) | Orphan sheet pin. Net CURR is intact: U25.6, then J90.8/J91.8, then R5, then U2.42 |
| pin_not_connected | 1 | TP10 (fc_rp2350a, 0.76, 5.59 mm, outside the A2 frame) | Not on either PCB and not in the netlist (V11 leftover) |
| pin_to_pin | 1 | U7 pin 5 "PG" (open collector) to GND (U24.11, typed power output) | The U7 symbol swaps the pin 3 and pin 5 names. LP5912.pdf p3 has 3 = PG and 5 = GND. Both pads are on GND in the netlist and on the Core PCB, so the circuit is right (PG grounded). See R2-08 |

## Findings (round 2)

| ID | severity | board/layer | location | evidence | fix |
|---|---|---|---|---|---|
| R2-01 | MINOR | Base F | J90 courtyard, Core outline | **Gap in DRC coverage.** Since 29c003d the J90 F.Courtyard is the pad field only (69.91-91.09 x 52.31-71.49). The Core outline in Base coordinates is 68.868-91.868 x 51.874-71.974 (J91 to J90 offset -34.2319, +8.3742, pad error 0.000). The rule area 'Core footprint' exists on F.Silkscreen only, so DRC no longer flags a Base F part placed under the hat. The uncovered band is 0.44-1.04 mm wide.<br>**Today it is clean:** no Base F courtyard reaches the outline. Closest: C106 0.104, C105 0.119, U12 0.278, Q21 0.294, Card1 0.367 mm. | Add an F.Cu "disallow footprint" DRU rule on 'Core footprint' that exempts J90, or draw the Core outline as J90's courtyard. |
| R2-02 | MINOR | Base B | U4 (68.1, 55.5); C23/C112/C113 (67.59-69.60, 59.45-59.59); R17/R18 | **Same-net pads that touch or nearly touch.** They show only as courtyard warnings:<ul><li>C107.1 to U4.3 (+BATT): 0.000 mm</li><li>R19.1 and R20.1 to U4.4 (FB): 0.055 mm</li><li>C23 to C112 to C113 (GND and +10V pads): 0.055 mm</li><li>R17.1 to R18.1: 0.090 mm</li></ul>With 0.04 mm mask expansion, each pair shares one mask opening, so the solder fillets merge. That risks 0201/0402 skew or tombstone, and NextPCB will raise a DFA EQ. Bodies are ≥ 0.2 mm apart (no collision). | Open each pair to a land gap ≥ 0.10 mm, or list them in the order as accepted. |
| R2-03 | MINOR | Base B | +BATT via (67.45, 63.10); /1B via (73.78, 63.52); +BATT vias (74.10, 67.00), (74.15, 67.45) | **25 V copper under unsoldered QFN leads.** The lands for unused pins were deleted per maintainer direction (LAYOUT_REVIEW 5.3, NEXTPCB.md). Some of those deleted-land footprints now have 25 V copper under them, with only solder mask between:<ul><li>The FB8c +BATT stitching via at (67.45, 63.10) reaches about 0.03 mm under the U13 pin 28 (PB7) lead.</li><li>The /1B phase via sits under U15 pins 27 and 28.</li><li>The +BATT vias sit under U16.21. That pin is NC, so this one is harmless.</li></ul>A mask defect would put the pack voltage on an AT32 GPIO. The check that would show these is parity `net_conflict`, which is demoted to warning (70 Base and 7 Core "no pad for pin" items; `missing2.py` fits the library-to-instance transform with 0.000 mm error). | Move the (67.45, 63.10) via about 0.1 mm off the PB7 lead. Keep +BATT and phase copper out of deleted-land footprints. |
| R2-04 | MINOR | Core F | U26 TXU0101 (112.47, 60.135) | **Paste below the IPC area ratio.** Paste is 1:1 (local margin 0). Pins 2-6 are 0.30 x 0.20 mm, giving area ratio 0.60 at a 0.10 mm stencil; pin 1 (0.35 x 0.20) gives 0.64. That is below the 0.66 that DFM-04 was fixed to. TI DRY0006A shows a 1:1 paste example for a 0.075-0.1 mm stencil (TXU0101 SCES940A p37).<br>**Checked and correct:** the footprint matches the TI land (pitch 0.5, rows 0.6 c-c, pads 0.2 x 0.3, pin 1 0.35). | Order the Core stencil at 0.08 mm, or accept 0.60 for these 6 apertures in the DFA. |
| R2-05 | MINOR | docs / schematic values | Core J44/J45/J48/J49; Base J41, J29/J33, TP9, TP31/32, TP1-8 | **Port mapping agrees across silk, README and firmware.** J44 'TX0' and J45 'RX0' are Betaflight UART0; J49 and J48 are PIOUART0 (config.h, README).<br>**The other sources are wrong or stale:**<ul><li>The schematic values are swapped against the silk: J44 'PIO_TX0', J49 'TX0', J45 'PIO_RX0', J48 'RX0'. The render confirms 'TX0' is printed beside J44 and that J49 has no label.</li><li>config.h comments still quote the old pad values.</li><li>PINOUT.md (be152bb) still shows Q2/R14 on GPIO8 and AT32 VDD = +3V3 from U23.</li><li>README J41 says "+10V switched by GPIO27 (10V_ENABLE)". In the netlist GPIO27 is `unconnected-(U2-GPIO27_ADC1-Pad41)` and U3 EN = +BATT.</li><li>Other values differ from the silk: BUZ±/BZ±, BOOT/BT0, SWDIO/SWD, SWCLK/SWC, and TestPoint against SDn/SCn.</li></ul> | Set the pad values to the silk codes, regenerate PINOUT.md, and correct README J41 ("always on with battery"). |
| R2-06 | MINOR | Base B.Cu | /2C (79.35, 66.70)-(80.65, 66.65) | **Dangling 25 V stub.** A 1.30 mm phase-node track with an open end, 0.375 mm from the J90.38 (UART0_TX) land on the opposite side. DRC reports it as track_dangling, which is a warning. Also dangling: +4v5 F.Cu 0.58 mm at (70.30, 54.50) and +3V3 B.Cu 0.20 mm at (75.02, 50.84). | Delete the stubs. |
| R2-07 | MINOR | Base F | L2 (66.665, 57.65), L3 (66.675, 54.125) | **Round-1 DFM-18 still open.** Both inductors still carry `attr through_hole` on SMD-only footprints. `footprint_type_mismatch` = ignore on both boards hides it. A CPL or quote that treats THT separately will drop or misquote the two buck inductors. | Set attr smd in lib.pretty and on both instances. |
| R2-08 | NIT | schematic fc_power | U7 LP5912-3.3 symbol | **Pin names swapped.** The symbol has pin 3 = GND and pin 5 = PG; LP5912.pdf p3 has PG = 3 and GND = 5. Both pads are tied to GND, so the circuit is correct. This is the source of the ERC pin_to_pin error. | Fix the symbol pin names, or tie PG through a no-connect intent. |
| R2-09 | NIT | docs | FINISH_PASS E13 | **Doc is stale.** FINISH_PASS says 7 of 10 J90 GND pads got vias, including pad 14 at (78.20, 58.55). Commit 49882dc reverted that via. The board has no GND via within 0.6 mm of J90.14, so the count is 6 of 10 (pads 2, 5, 14 and 44 have none). | Update FINISH_PASS. |
| R2-10 | NIT | Core B.Cu | arrow (110.6-111.5 x 43.93-45.53), OD mark (114.77-116.54 x 43.80-45.70) | **Floating copper.** Both shapes are netless islands (0.585 and 2.01 mm²), 0.077 and 0.081 mm from the GND fill. The OD mark is 0.548 mm from J91.6 (+5V). The two knockout texts do merge with GND (overlap 1.97 and 1.22 mm²). | Make the shapes GND: knock them out of the pour, as the texts are. |
| R2-11 | NIT | Base .kicad_pro | rule_severities | **Check demoted.** `solder_mask_bridge` is a warning on the Base (it is an error on the Core). There are 0 instances now, and U23/U27 already have scoped exceptions. | Restore it to error. |
| R2-12 | NIT | library | U26 TXU0101DRYR | **Datasheet missing from the library.** It is not in `hardware/KiCad-Library/datasheet/`; this review used the SCES940A copy in the fb6 scratchpad. | Add the PDF and a manifest entry. |

**Verified with no finding:**
- **LGA silk keep-out:** 0 visible Base F.Silk items inside the Core outline; the nearest is 0.39 mm. The Core has 0 B.Silk items and only J91 on B.
- **TXU0101:**
  - Netlist matches the pinout: VCCA = +3.3V, A = GPIO8, BY → R115 200R → LED_STRIP, OE = VCCB = +5V.
  - TXU0101 p3 allows OE pulled to VCCB, and p5 gives VI ≤ 5.5 V.
  - VCCA and GND each have a via at the pin.
- **U27 +3V3_ESC:**
  - Feeds all four AT32 VDD pins and the NRST pull-ups.
  - MOTOR lines land on PB4, which is FT (AT32F421.pdf p24), so there is no USB back-feed path.
  - TLV755P (p4): 5 V input is within the 5.5 V limit; COUT is 1 µF nominal plus 4 x 100 nF; θJA 168 °C/W gives about +23 °C at 80 mA.
- **Orientation:** U8 pin 1 sits top-left. The Base F arrow tip at (72.48, 51.41) and the Core B.Cu arrow both point toward the SH-6 edge. With BMI270.pdf p144, that makes CW180_DEG correct.
- **USB:**
  - D+ 26.94 mm (2 vias), D− 24.39 mm (3 vias).
  - Distance to the U3 SW net 1.285 mm, to U4 SW 1.639 mm.
- **+10V caps:** C112/C113 on +10V and GND, CL10A226MO7JZNC.

## Round-1 status (BLOCKER / MAJOR)

| ID | status | evidence at 29c003d |
|---|---|---|
| DFM-01 BLOCKER | fixed | Core corner chamfer. Core outline is 0.367 mm from the Card1 courtyard. With the KiCad transform, the model spans x 64.62-70.12, y 60.50-71.85 and the tab spans y 63.15-69.19 (the round-1 projection was rotated). |
| DFM-02 | fixed (premise wrong) | No model point at x > 69.6 in the R34 zone. R34 courtyard is 0.45 mm from the Card1 courtyard notch. |
| DFM-03 | accepted with number | Land covers 70 % of the 2.15 x 2.75 EP on all 24 FETs, pending the stack decision. Other-net pours keep 0.40 mm. Foreign copper left under the uncovered strip (mask only): GND tracks 0.28-0.47 mm² under 9 low-side EPs, GND vias 0.18-0.26 mm² under 12 high-side EPs. |
| DFM-04 | fixed | Paste is 1:1 on fine pitch. Area ratio at 0.10 mm: U2 0.81, AT32 0.73, U22 0.67. The new U26 is 0.60 (R2-04). |
| DFM-05 | fixed / accepted | J90 aperture 1.1 mm (margin +0.05); Base top stencil 0.12 mm; joint about 0.065 mm; Core warpage ≤ 0.10 asked of NextPCB. |
| DFM-06 | fixed | +BATT and other-net pours are ≥ 0.303 mm from every J90 pad; Core B GND is ≥ 0.303 mm from every J91 signal pad. |
| DFM-07 | partly fixed, with number | Flagged parts reduced from Core 15/4 to 6/1 and Base 33/2 to 26/0 (commit 5320413). |
| DFM-08 | fixed | Core FID1-3 are inside the outline, ≥ 1.0 mm from the edge. |
| DFM-09 | fixed | J90 = "OpenAIO-Core PCBA (consigned)", in the BOM and pos files. |
| DFM-10 | accepted with plan | PANEL.md: router-cut narrow tabs on the measured free runs. |
| PW1 | fixed | Both FB nets are on B.Cu only. FB to SW: U4 0.565 mm, U3 1.166 mm. Dividers sit at the FB pins (see R2-02). |
| PW2 | fixed with number | Worst +5V drop 75.3 → 56.4 mV; vias above 2 A 3 → 0. |
| PW3 | fixed | README states 6S and makes no 2S claim; INPUT_RANGE.md gives 3S-6S. |
| E1 | fixed | In4/In5 +BATT is 0.80 mm from the RF via. GND vias at 0.69/0.77 mm (geometry-limited). |
| E2 | fixed in rules; placement open (owner) | Only the /RX/WIFI B.Cu feed is inside the AE2 area. U12 over AE2 is an owner decision. |
| E3 | accepted with number | Pair coupled for 21.4 mm; departures as in FINISH_PASS (2.74/2.02 mm without a GND reference, +BATT 0.584 mΩ). |
| E4 | fixed | USB_D± are in class USB on both boards. RF, PHASE, CSA and POWER patterns resolve on the Base. |
| E5 | accepted (FINISH_PASS) | In4 unchanged: 34.6 mm, 5 nets. In5 sensitive nets unchanged (SPI0.MOSI 14.8, SCK 6.9, UART1_TX 5.6 mm). In5 total 131.5 mm (+8.2 mm SD +3V3 feed, +5.6 mm +3V3_ESC). |
| FW1 | fixed | TXU0101 non-inverting stage (see verified list). |
| FW2 | fixed | +3V3_ESC is battery-only (see verified list). |
| V1 | fixed | 0 silk errors with silk_overlap set to error. Core labels are legible in the render. |
| V2 | **open (partial)** | 11 pads have no silk, only the README legend: Core J23, J54, J48, J49; Base J41, J51, TP31, TP32, TP2, TP5, TP7. Also, 'SD1' sits between TP1 (1.14 mm) and TP2 (1.40 mm). |
| V3 | fixed | 'LED' is now text. |
| V4 | fixed on silk | Silk reads BZ+/BZ-, but the values are still BUZ+/BUZ- (R2-05). |
| V5 | **open (partial; FINISH_PASS FB6 owner item)** | The Core name and rev are on B.Cu, hidden once soldered. The Base identity is on B.Fab only. Nothing is visible on the assembled AIO. |
| V6 | fixed except U12 | Connector silk is stripped. U12 has its pin-1 dot on F.Fab only. |
| V7 | partly | The silk and courtyard checks are now error. Still ignored: footprint_type_mismatch (hides R2-07) and Core lib_footprint_mismatch. net_conflict and solder_mask_bridge (Base) are demoted to warning (R2-03, R2-11). |
| V8 | fixed | Courtyards on every footprint; 63 Base / 8 Core overlap warnings with no body overlap. |
| V9-V11 | partly (spot-checked) | Fixed: TP16/TP17 2.54 mm apart; C19/C107 7.6 mm apart. Still open: R24/D6 (+3V3) remain on the +3.3V Power sheet; TP10 is still outside the frame. |
| V12 | fixed | README pinout added; its errors are in R2-05. |

## Already known (confirmed)

- **FET stacking:** EP coverage is 70 %, with GND copper under the uncovered strip (DFM-03 numbers above).
- **Edge-pad DRU exceptions:** JP1.1 overhangs by 0.165 mm, U12.7/.8 by 0.493 mm, and FL1.2 sits 0.010 mm inside. The DRU asks for an order note so NextPCB keeps these lands.
- **Base vias:** the TODO-R3 0.35/0.20 rule (0.075 mm ring) is owner-confirmed. The outer-pour 0.16 rule is stricter than the line standard and hides nothing.
- **Deleted unused lands (maintainer direction):** 4 x AT32 10 of 29, 4 x NSG2065Q 3, SX1281 3, ESP32-C3 7, RP2354A 5, USB1 2, Card1 2, U6 1. Expect a NextPCB EQ. R2-03 covers only the 25 V copper under them.
- **+10V:** 3 x CL10A226 gives 9.2 µF effective against 10.9 µF needed (16 % short).
- **SD and INA186 feeds:** the SD +3V3 feed runs 8.2 mm on In5 at 0.15 mm, inside the +10V outline; C36 is about 8.5 mm away. The U25 +3V3 feed is about 13.8 mm, including 4.1 mm on In1 (the GND reference for F.Cu).
- **USB departures:** 2.74/2.02 mm without a GND reference; +BATT 0.584 mΩ; USB1 D pads 0.37 mm from L2.1 SW.
- **Unchanged items:** U3 HF cap not placed; AE2/U12 placement; In4/In5 nets.
- **0201 land gaps:** 0.175 mm pairs (DFM-13); courtyard warnings show no body overlap.
- **Remaining Core and Base finish-pass routes:** per FINISH_PASS. The 28 dangling Core vias were deleted (68c2f77).
