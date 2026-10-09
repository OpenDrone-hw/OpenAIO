# Finish pass: routing left for the owner

Boards at be152bb (KiCad files identical to 5cd1898). All numbers were measured on these boards after a zone refill (pcbnew dump, FB4b). Coordinates are in board mm.
- Base: `hardware/OpenAIO-Base.kicad_pcb`.
- Core: `hardware/OpenAIO-Core.kicad_pcb`.

**Baseline DRC at be152bb:**
- Base: 45 errors (clearance 16, copper_edge 4, silk_edge 4, silk_over_copper 20, via_dangling 1).
- Core: 42 errors (silk_edge 2, silk_over_copper 12, via_dangling 28).
- 0 unconnected on both boards.

Phase nets are /1A to /4C. "No GND plane" means no GND fill on either neighbouring copper layer: In1 for F.Cu, and In1 and In3 for In2.

| item | net/ref | location (x,y) mm | problem (measured) | suggested fix |
|---|---|---|---|---|
| USB 1 (E3), done with departures (FB8c) | USB_D+, USB_D−, USB1 to J90.42 / J90.37 | USB1 (61.88, 55.51); J90.37 (76.5, 66.9); J90.42 (76.5, 68.9) | **Routed (FB8c, accepted compromise):** coupled pair, In2 descent left of the USB1 NPTH, then F.Cu through the J90 23/28 gap, the 28/29 gap and the J90.29/PA13 passage.<br>**D+ 26.94 mm** (was 27.84), 2 layer changes. **D− 24.39 mm** (was 26.67), 3 layer changes. 5 GND return vias.<br>**Coupling:** 21.4 mm coupled at a 0.141–0.298 mm gap (was 1.3 mm).<br>**Switch node:** route copper at least 1.285 mm from SW, L2 and L3 (was 0).<br>**Departures:**<ul><li>D+ 2.74 mm and D− 2.02 mm have no adjacent GND plane (was 3.81 / 4.36), all over the In1 +5V branch at the USB1 escape;</li><li>+BATT 0.584 mΩ, +0.007 against 0.577;</li><li>USB1 D pads are 0.37 mm from the L2.1 SW pad.</li></ul>**DRU:** USB_D± gap 0.14–0.30, uncoupled max 9.9 mm (KiCad measures 9.35); the USB1 F pad escape (gap 0.34) has its own rule, gap max 0.35, uncoupled max 1.2 mm (0.63). Widths F 0.14–0.20, In2 0.12. | **Owner options for L2:** accept L2 at 0.87 mm with a 0.50 mm east shift (moves the U3 EN +BATT via to about (65.2, 56.35) and adds SW F strips), or rotate or replace L2. GND reference: re-run the In1 +5V branch away from under the D pads (y 54.6–56.4). |
| USB 2: J90 entry, done (FB8c) | /ESC1/FBCOMMON via; J90.28, J90.29 | via (73.68, 65.02), between J90.28 (72.5, 64.9) and J90.29 (74.5, 64.9) | **Only one USB track fits into the J90.37/.42 pocket on F.Cu.** The 28/29 gap is the only F entry, and this via leaves room for one 0.14 mm track.<br>**No other layer works:** In2 and B.Cu have no path, and pads 37/42 have no through-via site (B.Cu U15/U16 pads, In2 +3V3, In4 /ESC2/CL).<br>**Moving the via:** with the via gone, a coupled pair (0.14/0.15) fits through the gap. Its R51→R48 link cannot move to B.Cu x ≈ 73.0, because the /1B track from R50.1 to via (73.78, 63.52) crosses it. | Done in FB8c: the U15-PA14 fan-out via moved to (73.45, 65.85) and FBCOMMON now runs B (73.03, 65.3–66.1) → via (73.275, 66.35) → In2; both USB tracks enter as a pair. Was: reroute /1B (R50.1) or FBCOMMON, then move this via out of the gap. Both USB tracks can then enter as a pair (pair router: clearance 0.14, 0.0125 mm grid). |
| USB 3: FB4b candidate, superseded by FB8c | USB_D±, +5V_USB, LED_STRIP, USB1 shell GND vias | In2: left of the USB1 NPTH (63.1, 58.4). Layer-change vias D+ (64.95, 62.05) and D− (65.45, 61.85). F.Cu pair to (70.3, 62.4) | **Route:** coupled In2 pair down the left of the NPTH, then a coupled F pair. D− goes through the 28/29 gap. D+ has to go west and south of J90.36.<br>**Lengths:** D+ 28.25 mm (no shorter than now); D− 24.55 mm; 13.9 mm coupled (gap 0.14–0.30).<br>**Checks:** DRC equal to baseline, 0 unconnected, +BATT 0.579 mΩ.<br>**Side moves it needs:**<ul><li>re-link the +5V_USB A9 via (63.885, 57.895) west of the +10V via (63.72, 56.79), because the +10V In2 track (63.72–64.91, 56.79–57.30) blocks the right side;</li><li>move the In3 LED_STRIP to x 61.70;</li><li>replace the 6 USB1 shell-pad GND vias with one, the only site at (63.52, 59.85);</li><li>remove GND vias (71.29, 62.79), (73.44, 68.03), (73.94, 67.99) and (74.40, 68.11);</li><li>add a +BATT via (74.15, 67.45, margin 0.02) for J90.36.</li></ul>**With USB 2 done:** D+ would be about 26.6 mm (−4.5 %). | Do USB 2 first and route both tracks through the gap, or take an owner placement option: move L2/U3 or the VBUS loop away from USB1, or reassign the LGA pads. Then set DRU diff_pair_gap and diff_pair_uncoupled for the USB class. |
| E5: SPI0.MOSI | SPI0.MOSI | In5, longest segment at (70.34, 66.37) | 14.8 mm on In5. In4 +BATT is the nearest plane; the track runs under /1B. | Move it to In2 (GND at 0.135 / 0.335 mm). Phase-sense tracks go to In4/In5. |
| E5: SPI0.SCK | SPI0.SCK | In5 (68.72, 62.86) | 6.9 mm on In5. | Move it to In2. |
| E5: FLASH_CS | FLASH_CS | In4 (70.00, 67.11) | 6.6 mm on In4 (+BATT plane layer), beside /1B. | Move it to In2. |
| E5: MOTOR1 | MOTOR1 | In4 (71.96, 63.09) | 4.0 mm on In4 (DShot). | Move it to In2 or F. |
| E5: UART1_TX | UART1_TX | In5 (81.97, 67.33) | 5.6 mm on In5. | Move it to In2. |
| E5: /ESC2/FBCOMMON | /ESC2/FBCOMMON | In5 (78.99, 63.96) | 2.4 mm on In5 (BEMF neutral). | Move it to In2 or B. |
| E5: totals | In4 / In5 | n/a | **19 signal nets** on In4/In5.<br>**In4:** 34.6 mm (/1B 10.4, /1C 9.2, FLASH_CS 6.6, /ESC2/CL 4.3, MOTOR1 4.0).<br>**In5:** 117.8 mm, of which 10 gate nets carry 79.5 mm (Q22-G 13.0, Q15-G 10.1, Q6-G 9.6, Q8-G 9.2, Q26-G 8.7, Q16-G 7.0, Q3-G 6.5, Q23-G 5.5, Q10-G 5.3, Q12-G 4.6), plus /1B 8.7. | Low priority for gate and phase nets, which need no reference. |
| E7: In3 LED_STRIP | LED_STRIP | In3, longest segment (9.6 mm) at (69.95, 49.17) | 98.5 mm on In3, the GND plane layer, which cuts it. | Move it to B.Cu or In2. Failing that, add GND vias on both sides of each crossing. |
| E7: In3 others | UART0_TX, USB_D−, +3V3, +5V, CURR | (82.49, 72.24), (74.62, 61.45), (80.31, 70.80), (81.60, 55.80), (66.62, 51.96) | In3 lengths: UART0_TX 10.2, USB_D− 9.1, +3V3 6.3, +5V 5.5, CURR 5.4 mm. The In3 total is 135.0 mm. | UART0_TX: see the U12 row. USB_D−: see USB 1–3. Move the rails to In5/B pours. |
| E6: phase vias at J90 | /2C, /4A, /4B, /1B | (79.35, 66.73), (89.64, 64.86), (80.29, 62.03), (79.20, 58.30), (73.78, 63.52) | 42 phase vias lie inside the J90 field (69.5–91.5 × 52–72). Five are ≤ 0.30 mm edge-to-edge from a J90 pad:<ul><li>/2C to J90.38 UART0_TX: 0.19 mm;</li><li>/4A to J90.35 GND: 0.19 mm;</li><li>/4A to J90.25 UART1_RX: 0.22 mm;</li><li>/4B to J90.14 GND: 0.25 mm;</li><li>/1B to J90.24 MOTOR1: 0.28 mm.</li></ul> | Move these vias out of the LGA field, or to ≥ 0.5 mm from signal pads. |
| E10: Base edge stitching | GND | Base edge (59.01, 47.24) to (68.49, 44.41) | 11.0 mm of board edge has no GND via within 3 mm. Also 3.0 mm at (57.90, 55.66)–(57.90, 52.86), 1.2 mm at (92.05, 49.52) and 1.2 mm at (58.65, 72.23). | Add an edge row of GND vias at ≤ 3 mm pitch. Keep out of the CSA-feed no-via area (64.22–69.65 × 47.55–52.65). |
| E10: Core edge stitching | GND | Core edge (103.10, 44.73)–(104.60, 43.50) | 2.8 mm with no GND via within 3 mm, plus 1.2 mm at (120.30, 45.79). | Add one or two GND vias. |
| E12: Base victim vias | LED_STRIP, USB_D±, SWDIO | (61.33, 52.55) 3.00; (63.23, 57.10) 2.99; (62.37, 55.43) 2.93; (62.77, 55.75) 2.84; (62.78, 54.84) 2.26; (78.55, 55.35) 2.06 | 52 sensitive signal vias: 33 are > 1 mm and 6 are > 2 mm from the nearest GND via (distances listed). | Add a GND via within 0.5–1 mm of each one. The USB ones move with USB 1–3. |
| E12: Core victim vias | UART1_RX/TX, I2C0, MOTOR3, UART0, VIDEO, FLASH_CS, SWDIO, SPI0.SCK | e.g. UART1_RX (119.81, 46.85) 2.98; I2C0.SDA (113.55, 53.35) 2.49; MOTOR3 (112.80, 52.67) 2.47; VIDEO_IN (125.59, 56.75) 2.32; FLASH_CS (107.86, 54.75) 2.28; SPI0.SCK (108.31, 51.85) 2.17 | 92 sensitive vias: 71 are > 1 mm and 19 are > 2 mm from a GND via. | Add GND vias next to SCK, DShot and video layer changes first. |
| E13: J90 GND pads | J90.2, .5, .7, .14, .44 (GND) | (84.5, 52.9), (74.5, 54.9), (82.5, 54.9), (78.5, 58.9), (72.5, 70.9) | Each pad reaches In1 through one F.Cu track and one via.<br>No through-via site exists in the pad or within 0.95 mm, so via-in-pad (POFV) cannot be added. One site at (83.09, 54.80) for pad 7 has 0.00 margin.<br>**Blockers on B.Cu:**<ul><li>pad 2: U20 pads and /ESC4/GHB;</li><li>pad 5: U17 pads, +3V3, and In2 /ESC3/CL;</li><li>pad 7: U20/U19 /ESC4/AH;</li><li>pad 14: R105/R107 /ESC4/FBB;</li><li>pad 44: U16 /ESC2/GHC.</li></ul> | Accept, or free B.Cu under the pads when the ESC drivers move. |
| AE2 antenna clearance (E2) | AE2, U12, /RX/WIFI | keepout 79.5–83.98 × 75.28–77.94; AE2 at (81.75, 76.30), B.Cu | **Keepout contents:** no tracks, vias or GND fill, except the intended /RX/WIFI feed (B.Cu, (80.92, 75.16)–(80.51, 75.57)).<br>**Nearest GND fill to the AE2 body:** 0.77 mm on In1, In2, In3 and In6; 0.83 mm on B.Cu.<br>**U12 (SH-6, F.Cu):** sits over the antenna on the opposite face; its pad hull covers 0.55 of 11.92 mm² of the keepout. The critique's 3D-body figure, 11.67 mm², is not re-measured here. | Owner placement: move U12 or AE2 apart. Re-tune C89/L7/C87 on the built board. |
| U12 escape | U12.3 UART0_TX, U12.4 UART0_RX, U12.6 PU0RX | pads (79.95, 73.12), (80.95, 73.12), (82.95, 73.12) | **UART0_TX:** runs 4.3 mm on F to its first via at (84.33, 74.40), 4.56 mm from the pad, then 10.2 mm on In3.<br>**UART0_RX and PU0RX:** stay on F (6.3 and 6.6 mm within 6 mm of U12), with no via.<br>**No via site** under the U12 band (x 77–84.2, y 73.9–75.1) or above U12.3 (U22 exposed pad on B.Cu). | Move U12 (together with the AE2 item) so the UART pins can escape with vias. Then take UART0_TX off In3. |
| U3 HF cap | U3 (LMR51430), +BATT pins 3 and 5 | U3 at (65.26, 58.15), B.Cu; VIN pins (64.31, 59.30) and (65.26, 57.00) | No 0.1 µF cap at the VIN pins (TI SLUSEF4A 9.2.2.6). The input cap beside it is C18 4.7 µF at (65.45, 60.92). The FB3/R3-2 searches found no legal 0402 site with small nudges. | Place CL05B104KB54PNC (0402, 50 V) at pin 3 when U3, USB1 or the shell vias move. |
| +10V output caps, 2 of 3 added (FB8d) | C23, C112, C113 (CL10A226MO7JZNC), +10V | C23 (67.59, 59.45), C112 (68.60, 59.59), C113 (69.60, 59.59), B.Cu, rotation −90; L2.2 at (67.62, 57.65) | **Added (FB8d):** C112 and C113, same part and fields as C23, in a row beside C23. Bodies are 0.205 mm apart. +10V and GND are joined by 0.5 mm B.Cu strips. The GND pads are 2.6 and 3.6 mm from U3.1 GND.<br>**Effective capacitance at 9.84 V:** 3.06 µF (C23 alone) → **9.2 µF**. The 1.5 A VTX step at 5 % needs ≥ 10.9 µF (LMR51430 Eq. 14), so the board is **1.7 µF (16 %) short**.<br>**Moves that made room:**<ul><li>C23 moved −0.11 mm in x.</li><li>TP4 (U15 PA14, SWCLK) moved +1.0 mm in x. Its via moved into the pad at (70.61, 59.87), clear of In5 SPI0.SCK.</li><li>J90.11 GND lost its only via (70.15, 58.75), which sat under C113.1. It now has a via in the land at (70.45, 58.95) (POFV).</li><li>To clear that via, the In2 SPI0.MISO detour was straightened, 0.6 mm shorter. The B.Cu +5V feed from D2.2 to R22.1 now runs east of it.</li><li>The ESC2 SWD labels SC2 and SD2 moved to B.Fab, centred on TP4 and TP3. No legal B.Silkscreen spot exists within 2.5 mm.</li></ul>**No third site:** the row ends at TP4. East of TP4 are the MOTOR2 via (71.45, 60.55), the SPI0 vias (71.25/71.78, 59.3) and TP3. F.Cu is the Card1.9 pad, with the Core outline beside it. | For the last 1.7 µF, either fit 0603 parts with less DC-bias loss (check the maker's curve at 9.84 V), or move TP3/TP4 and the SPI0/MOTOR2 vias east for a fourth 0603. Give SC2/SD2 a silk spot, or list them in the README. FB7: the new land-only courtyard overlaps (bodies ≥ 0.205 mm) are C23–C112, C112–C113, C112/C113 with the R37/R40/C37/C38/R46 0201 row, C113–TP4, and TP4 with R45/R22/TP3/R47. |
| Base clearance (16) | gate nets Q6/Q7/Q8/Q15–Q18/Q24–Q26-G, /3C, /4B, LED_STRIP vs U24.11 | U24.11 PTH (62.65, 73.66) and (88.15, 48.16); In5 (81.07–84.27, 47.18–49.60); In2 (79.38–89.33, 48.83–54.54) | 16 DRC clearance errors, all pre-existing (tracked since R3):<ul><li>gate and phase tracks on In2/In5 too close to each other;</li><li>gate and LED_STRIP tracks too close to the U24 mounting PTH pads.</li></ul> | Nudge these tracks. Each fix is local. |
| Base edge (4) | JP1.1, FL1.2, U12.7, U12.8 | (91.54, 69.28), (91.74, 69.24), (84.25, 77.0), (76.65, 77.0) | copper_edge_clearance errors at the owner's original placement (RF chain, SH-6 tabs). | Owner placement, or a scoped DRU exception (FB7). |
| Core: I2C0 | /Pads/I2C0.SCL, /Pads/I2C0.SDA | dangling vias SCL (109.67, 45.38), (110.41, 44.01), (109.61, 44.00); SDA (111.62, 44.05), (112.34, 44.05) | **SCL:** 22.4 mm (In2 8.7, In3 9.9, F 3.8), 7 vias.<br>**SDA:** 29.1 mm (In2 21.0, In3 7.5), 7 vias.<br>**Width:** 0.10 mm. | Shorten both (a 21 mm detour is known), and remove the dangling vias. |
| Core: UART0/PU0RX corner | UART0_TX, UART0_RX, PU0RX, /Pads/PIOUART0_TX, UART1_TX/RX | dangling vias:<ul><li>UART0_TX (119.92, 62.42), (119.86, 60.82), (118.87, 62.40);</li><li>UART0_RX (121.92, 62.42), (120.86, 62.42);</li><li>PU0RX (121.73, 56.80), (120.39, 56.80), (121.74, 57.60);</li><li>PIOUART0_TX (121.81, 58.76), (121.10, 59.23), (121.80, 59.62);</li><li>UART1_RX (119.80, 45.98), (119.81, 46.85), (118.43, 46.01);</li><li>UART1_TX (119.75, 43.96).</li></ul> | **Lengths:** UART0_TX 7.2, UART0_RX 10.4, PU0RX 14.6, PIOUART0_TX 8.9 mm.<br>**Vias:** 15 of the Core's 28 via_dangling errors are on these nets. | Finish the corner routing at the pads and drop the dangling vias. |
| Core: +5V to R14 | +5V, R14 (2.4 k LED_STRIP pull-up) | R14 at (112.00, 60.37), F.Cu; thin run (112.05, 62.05)–(112.65, 61.95)–(113.58, 61.08), (115.65, 61.08)–(116.83, 60.33)–(117.62, 60.23), (118.33, 57.23)–(118.90, 55.75) | 13.9 mm of Core +5V is 0.10 mm wide on F.Cu (the class POWER minimum is 0.15). The +5V total is 38.5 mm, of which 28.1 mm is on In3. | Widen to ≥ 0.15 mm where there is room, or shorten the route. |
| Core: other dangling vias | /OSD/VIDEO_IN, /OSD/VIDEO_OUT, +1.1V, Net-(R7-Pad1) | VIDEO_IN (124.30, 57.61), (125.62, 57.63), (125.59, 56.75); VIDEO_OUT (104.36, 45.37), (103.53, 45.35); +1.1V (109.20, 60.84), (109.60, 60.71); R7 (110.46, 61.73) | The remaining 8 of the 28 Core via_dangling errors. | Remove them, or connect them on a second layer. |
| Core silk | F.Silkscreen pad labels; Edge.Cuts | t1/R1 (118.1, 44.9–46.9), 4v5 (118.1, 49.0), 5v (116.6, 45.7), gnd (114.9–123.6, 46.0–54.2), VTX (104.9, 45.7), tp0 (119.7, 60.0); edge (125.8, 52.2), (103.1, 43.8) | silk_over_copper 12, silk_edge_clearance 2. | Move or shrink the labels. |

## FB4b notes

- **USB:**
  - Nothing is committed for USB, because the must-haves were not met within the time box: D+ is not shorter.
  - The DRU diff-pair and uncoupled-length rules are not added. They follow the final route.
- **E13:** not possible with through vias (see the table).
- **Method:**
  - Pair centreline A\* on an exact-geometry raster.
  - Precheck of every new copper item against other-net copper.
  - The candidate was applied with pcbnew and checked with KiCad DRC (refill, parity), the DC solver and an island check.
  - The scripts are in the FB4b scratchpad (`fb4b/py/pair.py`, `build.py`, `usbm.py`, `fp.py`).

## FB6 item 2 notes (battery-only `+3V3_ESC`, owner polish)

U27 TLV75533 (IN = EN = +5V) feeds `+3V3_ESC` to the four AT32 VDD pins. The checks below were run on the committed boards after a zone refill.
- **Checks:**
  - Base DRC: 20 errors (clearance 15, copper_edge 4, via_dangling 1), with no new type. Parity: 70 non-missing.
  - Core DRC: 27/7. ERC: 31. Unconnected: 0/0.
  - +BATT: 0.577 mΩ, pw2 mean (0.573 at 1700c87). GND: 0.356 mΩ. +5V: 56.4 mV.
- **SD card +3V3 feed:** Card1.4 runs to via (69.12, 69.30), then 8.2 mm of 0.15 mm track on In5 to via (76.55, 72.23), then to B.Cu.
  - The In5 run stays inside the +10V pour outline, so it cuts the +10V pour and not +BATT.
  - When it ran on In4 it cut the +BATT plane: +BATT measured 0.596 there, against 0.577 on In5, In2 or B.Cu, or with the feed removed.
  - Owner: widen or shorten it.
- **U25 INA186 +3V3 feed:** pad 3 at (68.08, 50.76) is fed by a chain of 0.15 mm segments on F, In1 and In2 (about 13.8 mm), through vias (67.44, 51.25), (71.71, 51.45) and (74.61, 51.78). Owner: shorten or widen it.
- **C36 (+3V3 bypass for the SD card):** C36 is on B at (75.62, 73.20), about 8.5 mm along the rail from the SD feed via (69.12, 69.30). Within 8 mm of that via there was no free B spot. Owner: move it closer to Card1 when that area is reworked.
- **Base identity:** "OpenAIO Base" and "r2 2026-10" are on **B.Fab only** (not fabricated), at their 1700c87 spot (83.4–84.5, 64.2).
  - No B.Cu GND pour area fits 0.5 mm knockout text (the Core style, about 4.2 × 0.9 mm) at ≥ 0.3 mm from pads with the pour kept connected. The only fit is under the Rsense2 body.
  - F.Silk under Card1 is not acceptable.
  - Owner: place the identity on copper when an area is freed.

## FB8a notes (T0 courtyards, T1 USB exit)

- **Courtyard rule:** the DRU courtyard clearance is now 0 on both boards (courtyards touch, not overlap), so `courtyards_overlap` means two parts closer than 0.20 mm body or land. Pair list with classes: `fb8/courtyard_classes_fb7.txt`.
- **USB 2 (J90 entry), FB8a finding: the /ESC1/FBCOMMON via at (73.68, 65.02) has no other site.** R51.1 (B, 72.57, 65.30) is boxed in:
  - On F, J90.28 GND land sits above it, so a via-in-pad is not possible.
  - On B, R52.1 GND is to the north, R53.1 (/1C via-in-pad at 72.58, 65.88) to the south, R51.2 FBC to the west, and the U15-PA14 via (73.23, 65.76) with U15.22 to the east.
  - The only exit is the present north-east one, and it ends inside the 28/29 gap. The /1B track (R50.1 to via 73.78, 63.525) blocks a B link north to R48.1 along x ≈ 73.04.
  - Every through-via site in x 73.0–74.0, y 63.4–65.4 sits in the pair's approach to the gap. The nearest free site, (73.275, 66.35) with a 0.09 mm margin, is unreachable on B because of the PA14 via.
  - Past the gap, the pair has 0.748 mm between J90.29 and the U15-PA13 via (73.87, 66.17). A 0.14/0.15 pair at 0.147 mm clearance needs 0.724 mm.
  - **Fix needs a part move:** shift the ESC1 FB divider column R48–R53, or move U15 with its PA13/PA14 vias by about 0.3 mm east. Then route both USB tracks through the gap.

## FB8b notes (T1 USB exit: candidate built; committed in FB8c, see below)

T1 does not pass, so no board change is committed. Candidate board: scratchpad `fb8b/w3/OpenAIO-Base.kicad_pcb` (spec `fb8b/d8b.json` → `s8b.json` + `sb.json`, applied with `fb8b/rt8.py`).

- **FBCOMMON blocker cleared without moving a part.** Only the U15-PA14 fan-out via moves, (73.233, 65.755) → (73.45, 65.85); U15, the R48–R53 column and the PA13 via stay. This opens a B.Cu channel at x 73.03 between R53.1 and the PA14 via (0.155 / 0.175 mm). /ESC1/FBCOMMON then runs R51.1 → B (73.03, 65.3–66.1) → new via (73.275, 66.35) → In2 (72.57, 66.25). The via at (73.68, 65.02) and its In2 stubs are removed. Islands, DRC and parity are unchanged.
- **Pair route (candidate):** reuses the FB4b In2 descent, then an F pair (0.14 wide, 0.15 gap) through the J90 23/28 gap, the 28/29 gap and the J90.29/PA13 passage to J90.37 / .42.
  - **Lengths:** D+ 26.94 mm (was 27.84), D− 24.39 mm (was 26.67).
  - **Coupling:** 21.4 mm coupled at a 0.141–0.298 mm gap.
  - **Distance from SW, L2 and L3:** route copper at least 1.285 mm.
  - **Layer changes:** D+ 2, D− 3.
  - **GND return vias:** (62.25, 54.34), (61.79, 55.98), (65.985, 61.291), (66.062, 62.673) and (63.52, 59.85).
  - **J90.36:** the pocket pour is fed by a +BATT via at (74.15, 67.45); the F pair cuts it off otherwise.
  - **Checks:** DRC errors equal to baseline (clearance 15, copper_edge 4, via_dangling 1, parity non-missing 70); 0 unconnected; GND 0.356 mΩ.
- **Remaining blockers (exact):**
  1. **+BATT 0.584 mΩ against 0.577 (+0.007, limit +0.005).** The F pair cuts the F +BATT pour between y 62 and 64.4 for x 65.4–72. Before the extra vias it was 0.588. Four extra +BATT stitching vias, (64.5, 64.05), (67.45, 63.1), (65.6, 64.0) and (74.1, 67.0), recover 0.004. North of the cut there is no via site in both the F and the In3/In4 +BATT fill.
     - Next to try: revert the In3 LED_STRIP move to x 61.70, which may cut In3 +BATT near the battery. Measure per FET with `pw2.py`.
  2. **GND reference.** D+ has 2.74 mm and D− 2.02 mm with no adjacent GND plane; the old route had 3.81 / 4.36 mm.
     - All of it is in the USB1 escape: the F stubs sit over the In1 +5V branch to the +5V via (65.15, 55.74), and the In2 D− link (62.785, 54.845)–(62.765, 55.748) has neither In1 nor In3 GND under it.
     - Fix: re-run the In1 +5V branch away from under the D pads (y 54.6–56.4).
  3. **USB1 D pads to the L2.1 SW pad: 0.37 mm.** The Core outline (rule area 'Core footprint') starts at x 68.868, and the L2 body (3.0 × 3.0 mm, 2 mm tall) ends at 68.165.
     - An east move of 0.50 mm keeps the 0.20 mm body gap and gives 0.87 mm, not 1.0.
     - FB8a's 0.65 mm move leaves the body 0.05 mm from the Core edge.
     - Either move also needs the U3 EN +BATT via (66.65, 57.91) moved, because it would sit inside the new L2.1. The only site is about (65.2, 56.35) on U3.5. SW F strips from the vias (65.23–65.26, 58.2–59.3) to L2.1 are needed too.
     - **Owner decision:** accept 0.87 mm, or rotate or replace L2.
- DRU diff-pair rules were not set, because there is no committed route. With the candidate they would be `diff_pair_gap` 0.14–0.30 and `diff_pair_uncoupled` max about 5.6 mm (D+ 26.94 total − 21.4 coupled, mostly the USB1 escape and the J90.42 tail).


## FB8c notes (FB8b USB candidate committed as an accepted compromise)

- **Committed:** the FB8b candidate board (`fb8b/w3`) unchanged. A semantic diff against 39a7170 shows only tracks and vias in x 61.3–77.3, y 53.4–68.9 (USB pair, +5V_USB In2 loop, In3 LED_STRIP, FBCOMMON/PA14, 5 GND return vias, 5 +BATT vias, a dangling In1 +5V stub removed); footprints, zones and drawings are identical.
- **DRU (USB_D+ / USB_D−):** `diff_pair_gap` 0.14–0.30 (opt 0.15), `diff_pair_uncoupled` max 9.9 mm; outer track width 0.14–0.20, inner 0.12.
  - KiCad groups pair items by the rule that matches them, so the USB1 F.Cu pad escape (stubs joining A6/B6 and A7/B7, gap 0.34) has its own rule, scoped by `intersectsCourtyard('USB1')` on F.Cu: gap max 0.35, uncoupled max 1.2 mm.
  - Measured by KiCad DRC: uncoupled 9.35 mm (pair) and 0.63 mm (escape); limits are these plus 0.5, rounded up. KiCad counts only parallel same-layer segments as coupled, so its uncoupled figure is larger than the 21.4 mm coupled from `usbm.py` implies.
- **Checks:** Base DRC 20 errors (clearance 15, copper_edge 4, via_dangling 1), no new type, parity non-missing 70, 0 unconnected. Core 27 / parity 7, 0 unconnected. ERC 31. +BATT 0.584 mΩ, GND 0.357 mΩ. +5V worst drop 56.4 mV at J25 (3.2 A scenario, unchanged). U3/U4 FB-SW gaps unchanged (U4 0.57 mm, U3 0.71 mm, B.Cu).
- **Departures (accepted):**
  1. D+ 2.74 mm and D− 2.02 mm have no adjacent GND plane, over the In1 +5V branch at the USB1 escape.
  2. +BATT +0.007 mΩ (0.584 against 0.577).
  3. USB1 D pads are 0.37 mm from L2.1 (SW).
- **Owner options for L2:** accept L2 at 0.87 mm with a 0.50 mm east shift, or rotate or replace L2.
