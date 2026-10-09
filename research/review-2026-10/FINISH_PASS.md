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
| USB 1 (E3), not done | USB_D+, USB_D−, USB1 to J90.42 / J90.37 | USB1 (61.88, 55.51); J90.37 (76.5, 66.9); J90.42 (76.5, 68.9) | **D+ 27.84 mm:** F 17.73, In2 10.11, 3 vias.<br>**D− 26.67 mm:** F 6.43, In2 11.19, In3 9.05, 4 vias.<br>**Coupling:** only 1.3 mm coupled (edge gap ≤ 0.30).<br>**Switch node:** D+ on In2 comes within 0.09 mm in plan view of U3 SW copper (vias at 64.78–64.80, 58.76–59.39).<br>**Reference:** 3.8 mm (D+) and 4.4 mm (D−) have no GND plane. | See USB 2 and USB 3. If the length target matters, the owner must change the placement or the pad assignment. |
| USB 2: J90 entry | /ESC1/FBCOMMON via; J90.28, J90.29 | via (73.68, 65.02), between J90.28 (72.5, 64.9) and J90.29 (74.5, 64.9) | **Only one USB track fits into the J90.37/.42 pocket on F.Cu.** The 28/29 gap is the only F entry, and this via leaves room for one 0.14 mm track.<br>**No other layer works:** In2 and B.Cu have no path, and pads 37/42 have no through-via site (B.Cu U15/U16 pads, In2 +3V3, In4 /ESC2/CL).<br>**Moving the via:** with the via gone, a coupled pair (0.14/0.15) fits through the gap. Its R51→R48 link cannot move to B.Cu x ≈ 73.0, because the /1B track from R50.1 to via (73.78, 63.52) crosses it. | Reroute /1B (R50.1) or FBCOMMON, then move this via out of the gap. Both USB tracks can then enter as a pair (pair router: clearance 0.14, 0.0125 mm grid). |
| USB 3: FB4b candidate, not committed | USB_D±, +5V_USB, LED_STRIP, USB1 shell GND vias | In2: left of the USB1 NPTH (63.1, 58.4). Layer-change vias D+ (64.95, 62.05) and D− (65.45, 61.85). F.Cu pair to (70.3, 62.4) | **Route:** coupled In2 pair down the left of the NPTH, then a coupled F pair. D− goes through the 28/29 gap. D+ has to go west and south of J90.36.<br>**Lengths:** D+ 28.25 mm (no shorter than now); D− 24.55 mm; 13.9 mm coupled (gap 0.14–0.30).<br>**Checks:** DRC equal to baseline, 0 unconnected, +BATT 0.579 mΩ.<br>**Side moves it needs:**<ul><li>re-link the +5V_USB A9 via (63.885, 57.895) west of the +10V via (63.72, 56.79), because the +10V In2 track (63.72–64.91, 56.79–57.30) blocks the right side;</li><li>move the In3 LED_STRIP to x 61.70;</li><li>replace the 6 USB1 shell-pad GND vias with one, the only site at (63.52, 59.85);</li><li>remove GND vias (71.29, 62.79), (73.44, 68.03), (73.94, 67.99) and (74.40, 68.11);</li><li>add a +BATT via (74.15, 67.45, margin 0.02) for J90.36.</li></ul>**With USB 2 done:** D+ would be about 26.6 mm (−4.5 %). | Do USB 2 first and route both tracks through the gap, or take an owner placement option: move L2/U3 or the VBUS loop away from USB1, or reassign the LGA pads. Then set DRU diff_pair_gap and diff_pair_uncoupled for the USB class. |
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
| +10V output caps | C23 (CL10A226MO7JZNC), +10V | C23 at (67.70, 59.45), B.Cu; L2.2 at (67.62, 57.65) | C23 gives about 3.06 µF at 9.84 V (−86 % DC bias). The 1.5 A VTX step at 5 % needs ≥ 10.9 µF (LMR51430 Eq. 14), so three more CL10A226MO7JZNC are needed (4 × 3.06 = 12.2 µF). There is a B.Cu 0603 site for one, taking only the GND pour as movable: (71.60, 54.00), rotation 90, 5.4 mm from L2.2, with +10V on In5 under one pad. | Add one cap there, with a +10V via to In5. The other two need a placement change, or larger 25 V parts. |
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
