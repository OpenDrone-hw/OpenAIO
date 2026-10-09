# DRC exceptions: OpenAIO Base and Core

Branch `work/d81e559`. The baseline is the owner's d81e559. The current state is the FB7d commit on top of 6b21113 (FB7c 1cd470c merged); it adds this file. All runs used KiCad 10.0.6, `kicad-cli pcb drc --refill-zones --schematic-parity --severity-all`.

## 1. Summary

| Item | Status at FB7d |
|---|---|
| Owner requirement (PLAN.md, f193d5f) | DRC ends at 0 errors on both boards. Intended departures are named DRU rules, scoped to pads, footprints or nets, each with a reason. Real fab risks are fixed, not exempted. No check is globally ignored. This table goes in the PR. |
| DRC errors | **Base 0, Core 0.** Unconnected 0 / 0. ERC 31 errors (schematic unchanged). |
| DRC warnings | Base 344, Core 100 (section 4). Schematic parity, non-missing: Base 87 (net_conflict 70, footprint_filters_mismatch 17), Core 27 (7, 20). `missing_footprint` (the other board's parts, multiboard schematic) is left out of these counts. |
| Custom DRU rules | 66: Base 43, Core 23 (section 3). FB7d added none: the two checks that needed an exception are not rule-driven (section 3a). |
| Rules that relax a check | 14 in all. 13 relax a generic NextPCB rule: Base 9, Core 4. The 14th, Base B41, relaxes only the USB pair rule B40. 11 of the 14 set `(severity ignore)` on a single constraint, each scoped to named pads or footprints. |
| DRC exclusions | 3, Base only (X1-X3, section 3a): one PTH and one NPTH courtyard item each, keyed to the exact pad and footprint, each with its reason stored in the `.kicad_pro`. Core: none. |
| Footprint-level exemptions | One: U24 (AIO_outline, the board outline footprint) has `allow_missing_courtyard`, because a courtyard would cover the whole board (4af7219). |
| Fixed, not exempted (examples) | **Base:**<ul><li>copper_edge 78 → 4: tracks and vias moved ≥ 0.20 mm inside the edge (5b15929).</li><li>15 inner clearances: owner 0.090 mm routing against the 0.10 mm rule, fixed by vertex nudges (8415dcc).</li><li>Mask bridges: fixed by moving R64-R66, R83, FID1/2 and U25 (153c308).</li><li>R107 moved back off the U19 body; it was 0.045 mm from it (49882dc).</li><li>R20/C21 cleared from the U4 body (1cd470c).</li><li>J90/J91 pours pulled back to 0.30 mm (dd813f0).</li></ul>**Core:**<ul><li>copper_edge 28 → 0: tracks re-routed inside the notch, D1 moved 0.025 mm (5b15929).</li><li>27 open vias deleted (68c2f77): owner vias in wire pads, plus two +1.1V vias at C16.</li></ul>**FB7d, both boards:**<ul><li>L2/L3 footprint type set to SMD.</li><li>201 off-centre track ends brought to the via centre (Base 132, Core 69).</li></ul> |
| **"No check is globally ignored"** | **Met.** No check is `ignore` in either `.kicad_pro` (FB7d). The seven checks that were still `ignore` from d81e559 were each set to error, run, and then fixed, excepted per item, or set to warning (table below). |

Checks that were `ignore` until FB7d (all of them were already `ignore` at d81e559):

| Check | Hits when set to error (6b21113) | Resolution (FB7d) | Severity now (Base / Core) |
|---|---|---|---|
| footprint_type_mismatch (parity) | Base 2, Core 0 | **Fixed.** L2 and L3 (AFE303020S, SMD-only) carried `attr through_hole`. Set to SMD on both board instances and in the project footprint `lib.pretty/IND-SMD_L3.0-W3.0_AFE303020S.kicad_mod`. Their position-file and BOM attributes are unchanged. | error / error |
| track_not_centered_on_via | Base 132, Core 69 | **Fixed.** Every flagged track end now ends on the via centre: the track is cut where it enters the via land, and a short segment of the same width runs to the centre. Track ends whose whole track lies inside the land were snapped. The offsets were 0.00003-0.245 mm (Base median 0.088, Core 0.117). New copper outside the old copper: Base at most 0.010 mm (0.014 mm² in all), Core at most 0.025 mm. There is one exception: the 1.0 mm In2 +3.3V strap between the vias at (109.00, 49.87) and (108.72, 50.18) was redrawn centre to centre at 0.8 mm, because a centred 1.0 mm strap would short the +1.1V via at (108.86, 50.83). DRU-scoped exceptions are not possible: the check is not rule-driven. | error / error |
| pth_inside_courtyard | Base 2, Core 0 | **Per-item exclusions X1 and X2** (owner placement, section 3a and 5). The U24.11 grommet holes are inside the Q15 and USB1 courtyards. | error / error |
| npth_inside_courtyard | Base 1, Core 0 | **Per-item exclusion X3** (intended, section 3a). The USB1 locating peg is under the turned B-side shunt Rsense2. | error / error |
| tuning_profile_track_geometries | 0 / 0 | **Error.** No tuning profile is defined, so it cannot fire today. It stays an error so a future profile is checked. | error / error |
| footprint_filters_mismatch (parity) | Base 17, Core 20 | **Warning.** It compares the symbol's footprint filter text with the assigned footprint name. That is library metadata, and the assignment itself is checked by footprint_symbol_mismatch and parity. It cannot hide a fab risk. | warning / warning |
| lib_footprint_mismatch | Core 32 (Base 71 was already a warning) | **Warning** on the Core too. The board copy is what gets built. The differences are the intended per-instance edits (redrawn courtyards, small_pad wire pads). Core: J 21 (small_pad 20), U 7, D, Q, L, X 1 each. | warning / warning |

Checks that are demoted but not ignored:
- solder_mask_bridge is a warning on the Base and an error on the Core. The Base has 0 hits (critique R2-11).
- Parity net_conflict is a warning on both boards: Base 70, Core 7. Both boards come from one multiboard schematic.
- footprint_filters_mismatch and lib_footprint_mismatch: see the table above.

## 2. DRC summary per board and type

Command: `kicad-cli pcb drc --refill-zones --format json --severity-all`, with `OPENDRONE_LIB` set to `hardware/KiCad-Library`.

- **d81e559 column:** the owner's board with its own `.kicad_dru` and Board Setup values. Only `rule_severities` is replaced by the 29c003d one, so every check that 29c003d enables is on. The seven checks that were `ignore` until FB7d stay off in this column ("-").
- **FB7d column:** the current boards. For the seven checks enabled in FB7d, the note gives the hits at 6b21113 with the check set to error.
- **Capped counts:** kicad-cli lists at most 199 items per type, so "≥199" marks a capped count.

### Base

| Type | Severity now | d81e559, all checks on | FB7d | Note |
|---|---|---|---|---|
| annular_width | error | 2 | 0 | The USB1 locating pegs were PTH with no copper. They are now NPTH. |
| clearance | error | 4 | 0 | **d81e559:** 3 were U23 X2SON pads against the 0.16 rule, 1 was the USB1 peg to R4 at 0.08 mm (both fixed in c4ef88c).<br>**Later:** the 15 inner clearances found after the rule change were fixed in 8415dcc. |
| copper_edge_clearance | error | 55 | 0 | **Fixed:** tracks and vias re-routed inside the edge (5b15929).<br>**Exempt:** intended edge pads, covered by rules B25-B30. |
| missing_courtyard | error | 56 | 0 | Courtyards added (4af7219). U24 uses `allow_missing_courtyard`. |
| silk_edge_clearance | error | 6 | 0 | Silk passes: FB5 items 1-4, a236148, 153c308, FB6. |
| silk_over_copper | error | ≥199 | 0 | Same silk passes. |
| silk_overlap | error | ≥199 | 0 | Same silk passes. |
| text_thickness | error | 2 | 0 | Labels replaced. |
| via_dangling | error | 2 | 0 | The U3-SW via was deleted (68c2f77). The +5V_USB via went in the re-route. |
| unconnected_items | error | 0 | 0 | |
| connection_width | warning | 7 | 4 | Section 4. |
| copper_sliver | warning | 3 | 2 | Section 4. |
| courtyards_overlap | warning | 163 | 64 | **d81e559:** library courtyards.<br>**Now:** courtyards are max(body, land) + 0.10 mm, with clearance 0 (d4ed300, 29c003d). 29c003d had 63. The R20/C21 move (1cd470c) added C21-C24, C24-R18 and C24-Rsense2, and removed R18-U3 and R19-U4. |
| holes_co_located | warning | 1 | 0 | A duplicate GND via at (80.43, 64.01). |
| lib_footprint_issues | warning | ≥199 | 192 | Section 4. |
| lib_footprint_mismatch | warning | 29 | 71 | Section 4. |
| padstack | warning | 2 | 0 | The USB1 pegs (now NPTH). |
| solder_mask_bridge | warning | ≥199 | 0 | **Mask settings:** expansion 0.04 mm, web 0.09 mm (153c308).<br>**Fixed:** real bridges, by moving parts.<br>**Exempt:** the U23 and U27 gangs (B33, B34). |
| track_dangling | warning | 0 | 11 | Introduced during the work. Section 4. |
| footprint_type_mismatch | error | - | 0 | 6b21113: 2 (L2, L3). Fixed in FB7d. |
| track_not_centered_on_via | error | - | 0 | 6b21113: 132. Fixed in FB7d. |
| pth_inside_courtyard | error | - | 0 (2 excluded) | 6b21113: 2. Exclusions X1, X2. |
| npth_inside_courtyard | error | - | 0 (1 excluded) | 6b21113: 1. Exclusion X3. |
| tuning_profile_track_geometries | error | - | 0 | No tuning profile is defined. |
| footprint_filters_mismatch (parity) | warning | - | 17 | Section 4. Not in the total, which counts board items only. |
| **Total** | | **1128** (≥525 errors) | **344** (0 errors) | |

### Core

| Type | Severity now | d81e559, all checks on | FB7d | Note |
|---|---|---|---|---|
| copper_edge_clearance | error | 21 | 0 | **Fixed:** UART1_TX, VIDEO_IN and +5V re-routed inside the notch; D1 moved (5b15929).<br>**Exempt:** wire pads, covered by rule C19. |
| missing_courtyard | error | 31 | 0 | Courtyards added (4af7219). |
| silk_edge_clearance | error | 4 | 0 | Silk passes (5b15929, FB5, 153c308). |
| silk_over_copper | error | 151 | 0 | Same silk passes. |
| silk_overlap | error | 39 | 0 | Same silk passes. |
| text_thickness | error | 5 | 0 | Labels replaced. |
| via_dangling | error | 33 | 0 | 27 deleted in 68c2f77: owner vias in F.Cu wire pads, plus two +1.1V vias at C16. The other 6 went in the re-route. |
| clearance, solder_mask_bridge, unconnected | error | 0 | 0 | **d81e559:** no mask web was set.<br>**Now:** web 0.09 mm. U9 and U11 are exempt (C18, C21, C22). |
| courtyards_overlap | warning | 42 | 8 | Section 4. |
| lib_footprint_issues | warning | 52 | 60 | Section 4. |
| lib_footprint_mismatch | warning | - | 32 | It was `ignore` on the Core only. Now a warning. Section 4. |
| track_not_centered_on_via | error | - | 0 | 6b21113: 69. Fixed in FB7d. One 1.0 mm strap was narrowed to 0.8 mm (section 1). |
| footprint_type_mismatch, pth/npth_inside_courtyard, tuning_profile_track_geometries | error | - | 0 | 0 hits at 6b21113 as well. |
| footprint_filters_mismatch (parity) | warning | - | 20 | Section 4. Not in the total. |
| **Total** | | **378** (284 errors) | **100** (0 errors) | |

## 3. Custom DRU rules (every rule, in DRU order)

"Generic" means a rule that sets NextPCB's extreme-tier limit as listed in NEXTPCB.md 2.1 and 2.2. **RELAX** marks a rule that loosens a check compared with those generic rules. KiCad applies the last matching rule, per constraint.

### Base (`hardware/OpenAIO-Base.kicad_dru`, 43 rules)

| # | Rule name | Scope (refs / nets / area) | Check relaxed or tightened | Justification | Source commit |
|---|---|---|---|---|---|
| B1 | silkscreen over pad | All pads | Tightened: silk_clearance 0.15 (Board Setup 0) | OpenDrone template block, kept byte-identical | 00ffc27 (pre-d81e559) |
| B2 | NPCB base: outer 2 oz track | Outer layers | Generic: track ≥ 0.14 | NEXTPCB.md 2.2, 2 oz outer | b3a593e |
| B3 | NPCB base: outer 2 oz clearance | Outer layers | Generic: clearance 0.14 | NEXTPCB.md 2.2 | b3a593e |
| B4 | TODO-R3: outer pours keep 0.16 until the power-stage re-plan | Outer layers, any zone | Tightened: zone clearance 0.16 (> 0.14) | At 0.14 the priority-32 F.Cu +BATT pour slips between the /1C motor pad and Q7's sources and cuts the phase pour (1 unconnected) | b3a593e |
| B5 | NPCB base: inner 1 oz track | Inner layers | Generic: track ≥ 0.10 | NEXTPCB.md 2.2, 1 oz inner | b3a593e |
| B6 | NPCB base: inner 1 oz clearance | Inner layers | Generic: clearance 0.10 | NEXTPCB.md 2.2 | b3a593e |
| B7 | RF: clearance, outer | RF class: Net-(FL1-\*), /RX/WIFI, Net-(U22-LNA_IN) | Tightened: 0.15 | EMC E4. Custom rules override netclass clearances, so the class value is restated here. 0.15 is the largest value existing copper meets; 0.20 would leave 9 items short. | 5cd1898 |
| B8 | RF: clearance, inner | RF class | Tightened: 0.15 (> 0.10) | EMC E4 | 5cd1898 |
| B9 | CSA: clearance, outer | CSA class (/CSA+) | Tightened: 0.16 | EMC E4 | 5cd1898 |
| B10 | CSA: clearance, inner | CSA class | Tightened: 0.12 | EMC E4. 0.15 would leave 2 items short. | 5cd1898 |
| B11 | PHASE: clearance, outer | PHASE class (/[1-4][ABC]) | Tightened: 0.15 | EMC E4. Inner stays at 0.10 because 116 items are short of 0.15. | 5cd1898 |
| B12 | RF: track width | RF class, all layers | Tightened: min 0.16 | EMC E4 | 5cd1898 |
| B13 | CSA: track width | CSA class | Tightened: min 0.15 | EMC E4 | 5cd1898 |
| B14 | POWER: +BATT, +5V, +4v5, ESC vdda track width | +BATT, +5V, +4v5, /ESC?/vdda | Tightened: min 0.15 (opt 0.30) | EMC E4. Tracks under 0.30 were listed for FB7. | 5cd1898 |
| B15 | POWER: +5V_USB track width | +5V_USB | Tightened: min 0.20 | EMC E4 | 5cd1898 |
| B16 | NPCB base: SMD pad to SMD pad | Outer, SMD to SMD | Generic: 0.15 (governs over 0.14) | NEXTPCB.md 2.2 pad to pad | b3a593e |
| B17 | NPCB base: PTH pad to PTH pad | PTH to PTH | Generic: 0.40 | NEXTPCB.md 3.3 | b3a593e |
| B18 | NPCB base: through via, 1.6 mm board | All through vias | Generic: drill ≥ 0.20, Ø ≥ 0.43, ring ≥ 0.115, hole clearance 0.18 | NEXTPCB.md 2.2 (2 oz ring) | b3a593e |
| B19 | TODO-R3: Base vias stay 0.35/0.20 until the R3 re-route | All 1348 Base through vias (1305 × 0.35/0.20, 41 × 0.50/0.30, 2 × 0.45/0.25) | **RELAX:** via Ø 0.43 → 0.35, ring 0.115 → 0.075. Drill and hole clearance from B18 still apply. | Owner decision, PLAN.md gate R2 (d40a0b2): "Base vias stay 0.35/0.20", NextPCB builds them, the resize is dropped. The rule name and comment ("delete in R3") predate that decision and are stale. | b3a593e |
| B20 | NPCB base: PTH hole to copper | PTH pads | Generic: hole clearance 0.23, ring 0.115 | NEXTPCB.md 2.2 | b3a593e |
| B21 | NPCB base: NPTH hole to copper | NPTH pads | Generic: 0.20 | NEXTPCB.md 2.2 | b3a593e |
| B22 | NPCB base: hole to hole, different nets (CAF) | Different nets | Generic: 0.30 | NEXTPCB.md 2.2 | b3a593e |
| B23 | NPCB base: copper to routed edge | All | Generic: 0.20 | NEXTPCB.md 2.2 | b3a593e |
| B24 | NPCB base: body to body 0.20 mm (courtyards may touch) | All footprints | Generic: courtyard_clearance 0. With courtyards at max(body, land) + 0.10, this equals NextPCB's 0.20 body to body. | NEXTPCB.md 2.2. Replaces b3a593e's 0.20 on padded library courtyards. | b3a593e, d4ed300 |
| B25 | Edge pads: U24 battery and motor solder pads | U24 pads 1, 2, 12-23 (30 pads) | **RELAX:** edge_clearance `severity ignore` | The battery and motor pads are meant to sit at the edge (R3-E) | 5b15929 |
| B26 | Edge pads: USB1 shell tabs (pad 0) | USB1 pad 0 (4 tabs) | **RELAX:** edge_clearance ignore | The USB-C shell tabs sit at the edge by design | 5b15929 |
| B27 | Edge pads: J15-J33 wire pads (lib:small_pad) | 14 lib:small_pad pads | **RELAX:** edge_clearance ignore | The wire pads sit at the edge | 5b15929 |
| B28 | Edge pads: JP1.1 u.FL centre pad (owner original, decision listed) | JP1 pad 1 | **RELAX:** edge_clearance ignore | The owner's land overhangs the edge by 0.165 mm. A trim would cut the datasheet land. Owner item, section 5. | e7464d7 |
| B29 | Edge pads: FL1.2 filter GND pad (owner original, decision listed) | FL1 pad 2 | **RELAX:** edge_clearance ignore | A 0.30 × 0.30 GND land, 0.010 mm inside the edge. Owner item. | e7464d7 |
| B30 | Edge pads: U12.7/.8 SH-6 shell tabs (owner original, decision listed) | U12 pads 7, 8 | **RELAX:** edge_clearance ignore | The SM06B-SRSS-TB tabs overhang by 0.493 mm (connector mouth over the edge). Owner item. | e7464d7 |
| B31 | LGA J90: other-net pours 0.30 from the land | F.Cu: J90 pads to other-net zones | Tightened: 0.30 | DFM-06 / D2: a hidden LGA joint cannot be inspected or reworked | dd813f0 |
| B32 | LGA J90: +BATT 0.30 from the land | F.Cu: J90 to any +BATT item | Tightened: 0.30 | +BATT next to an FC signal is the worst short on the board | dd813f0 |
| B33 | Mask gang: U23 X2SON-4 land pattern | U23 | **RELAX:** bridged_mask ignore | The datasheet land has pad gaps under 0.17 (2 × 0.04 + 0.09). KiCad 10.0.6 matches bridged_mask on item A only. No bridge leaves U23. Keep only if NextPCB accepts the gang (NEXTPCB.md 4.6 Q11). | 153c308 |
| B34 | Mask gang: U27 X2SON-4 land pattern | U27 | **RELAX:** bridged_mask ignore | Same as U23. Pad to EP is 0.164, so the 0.15 rule passes. | 05537a3 |
| B35 | DOY180N03T EP: other-net pours 0.40 from the drain land | Outer: pad 3 of the 24 lib:DOY180N03T FETs to other-net zones | Tightened: 0.40 | DFM-03 interim: the land covers 70 % of the EP. A KiCad keepout is not net-aware. | 277d5ec |
| B36 | DOY180N03T EP: no other tracks or vias under the exposed pad | Rule area DOY_EP, outer | Tightened: no track or via except GND, +BATT, gate and phase | DFM-03 interim (PLAN.md FET land decision) | 277d5ec |
| B37 | RF: +BATT keeps 0.80 mm from the RF chain | Net-(FL1-OUT/IN), /RX/WIFI, Net-(U22-LNA_IN) to +BATT, all layers | Tightened: 0.80 | EMC E1: the feed via sat 0.105 mm from the In4/In5 +BATT planes | 0eb970c |
| B38 | AE2 antenna: no tracks or vias in the antenna area | Rule area 'AE2 antenna', all layers | Tightened: no track or via except the /RX/WIFI feed | EMC E2, antenna datasheet clearance | fdcda87 |
| B39 | LGA overlap: no F.Silkscreen under the Core | Rule area 'Core footprint', F.Silkscreen | Tightened: no visible text or graphic | Silk ink (10-25 µm) under the hat against 30-65 µm LGA joints | 369ad7a |
| B40 | USB: D+/D- diff pair gap and uncoupled length | USB_D+, USB_D- | Added: gap 0.14-0.30 (opt 0.15), uncoupled ≤ 9.9 mm | Limits set to the FB8b route (uncoupled 9.35 mm). Accepted compromise under PLAN.md "Compromise is expected". | 9f71f9f |
| B41 | USB: D+/D- USB1 pad escape | F.Cu, USB_D± inside the USB1 courtyard | **RELAX vs B40** (no NextPCB limit): gap max 0.35, uncoupled max 1.2 (actual 0.63) | The USB1 A6/B6 and A7/B7 stubs are 0.34 apart. KiCad groups pair items by rule. | 9f71f9f |
| B42 | USB: D+/D- track width, outer | USB_D± outer | Tightened: 0.14-0.20 (max added) | FB8b route as built | 9f71f9f |
| B43 | USB: D+/D- track width, inner | USB_D± inner | Tightened: 0.12 fixed (> 0.10) | FB8b route on In2 | 9f71f9f |

### Core (`hardware/OpenAIO-Core.kicad_dru`, 23 rules)

| # | Rule name | Scope (refs / nets / area) | Check relaxed or tightened | Justification | Source commit |
|---|---|---|---|---|---|
| C1 | silkscreen over pad | All pads | Tightened: silk_clearance 0.15 | Template block | 00ffc27 (pre-d81e559) |
| C2 | Core bottom is the LGA only | B.Cu: every footprint except J91 | Tightened: disallow footprint | Owner design: the bottom face is the LGA | 00ffc27 (pre-d81e559) |
| C3 | NPCB core: outer 1 oz track | Outer layers | Generic: 0.076 | NEXTPCB.md 2.1 | b3a593e |
| C4 | NPCB core: outer 1 oz clearance | Outer layers | Generic: 0.076 | NEXTPCB.md 2.1 | b3a593e |
| C5 | NPCB core: inner 0.5 oz track | Inner layers | Generic: 0.064 | NEXTPCB.md 2.1 | b3a593e |
| C6 | NPCB core: inner 0.5 oz clearance | Inner layers | Generic: 0.076 | NEXTPCB.md 2.1 | b3a593e |
| C7 | POWER: +1.1V and +1.8V_GYRO track width | +1.1V, +1.8V_GYRO | Tightened: min 0.17 (opt 0.20) | EMC E4 | 5cd1898 |
| C8 | POWER: +4v5 track width | +4v5 | Tightened: min 0.12 (opt 0.20) | EMC E4 | 5cd1898 |
| C9 | NPCB core: SMD pad to track or pour | Outer, SMD pad to track, arc or zone | Generic: 0.10 | NEXTPCB.md 2.1 | b3a593e |
| C10 | NPCB core: SMD pad to SMD pad | Outer, SMD to SMD | Generic: 0.15 | NEXTPCB.md 2.1 | b3a593e |
| C11 | NPCB core: PTH pad to PTH pad | PTH to PTH | Generic: 0.40 | NEXTPCB.md 3.2 | b3a593e |
| C12 | NPCB core: through via | All through vias | Generic: drill 0.15, Ø 0.35, ring 0.10, hole clearance 0.18 | NEXTPCB.md 2.1: 0.15 drill is offered for boards ≤ 1.2 mm | b3a593e |
| C13 | NPCB core: PTH hole to copper | PTH pads | Generic: 0.23, ring 0.09 | NEXTPCB.md 2.1 (1 oz PTH figure) | b3a593e |
| C14 | NPCB core: NPTH hole to copper | NPTH pads | Generic: 0.20 | NEXTPCB.md 2.1 | b3a593e |
| C15 | NPCB core: hole to hole, different nets (CAF) | Different nets | Generic: 0.30 | NEXTPCB.md 2.1 | b3a593e |
| C16 | NPCB core: copper to routed edge | All | Generic: 0.20 | NEXTPCB.md 2.1 | b3a593e |
| C17 | NPCB core: body to body 0.20 mm (courtyards may touch) | All footprints | Generic: courtyard_clearance 0 (= 0.20 body to body) | Same as B24 | b3a593e, d4ed300 |
| C18 | NPCB core: U9 X2SON-6 land pattern below 0.15 | Outer, U9 pad to U9 pad | **RELAX:** pad to pad 0.15 → 0.076 | The datasheet land has pad gaps of 0.09-0.11 (NEXTPCB.md 2.1). Keep only if NextPCB accepts the gang (Q11). | b3a593e |
| C19 | Edge pads: J* wire pads (lib:small_pad) | 20 lib:small_pad pads | **RELAX:** edge_clearance ignore | The wire pads sit at the edge | 5b15929 |
| C20 | LGA J91: other-net pours 0.30 from the pads | B.Cu: J91 pads to other-net zones | Tightened: 0.30 | DFM-06 | dd813f0 |
| C21 | Mask gang: U9 X2SON-6 land pattern | U9 | **RELAX:** bridged_mask ignore | As B33 | 153c308 |
| C22 | Mask gang: U11 X2SON-4 land pattern | U11 | **RELAX:** bridged_mask ignore | As B33 | 153c308 |
| C23 | LGA overlap: no B.Silkscreen on the Core | B.Silkscreen | Tightened: no visible text or graphic | Silk under the LGA face | 369ad7a |

### 3a. Per-item DRC exclusions (FB7d)

**Why these are not DRU rules.** In KiCad 10.0.6, pth_inside_courtyard, npth_inside_courtyard and track_not_centered_on_via are not driven by any DRU constraint, so a DRU rule cannot scope them. This was tested: scoped rules on U24/Q15 and USB1 with courtyard_clearance, hole_clearance and physical_hole_clearance set to `(severity ignore)` left all three courtyard items in place.

**How the exclusions work.** KiCad's per-item mechanism is the DRC exclusion. It is stored in `board.design_settings.drc_exclusions` of `hardware/OpenAIO-Base.kicad_pro` as `check|x|y|pad UUID|footprint UUID`, and the reason is stored next to it as the exclusion comment. An exclusion matches only that pad-footprint pair at that position. If either part moves, the error comes back. The checks themselves stay at error. The off-centre vias were fixed, not excluded (section 1).

| # | Check | Items | Facts | Justification |
|---|---|---|---|---|
| X1 | pth_inside_courtyard | U24 pad 11 (GND grommet hole, 88.15, 48.16) in the Q15 courtyard | <ul><li>The hole is a 3.0 mm drill with a 3.4 mm ring, on the 25.5 mm whoop pattern.</li><li>The Q15 courtyard reaches 0.02 mm into the drill.</li><li>The Q15 body and land stay ≥ 0.08 mm outside the drill, but overlap the ring by up to 0.12 mm.</li></ul> | Owner placement: Q15 and the hole are where the owner put them in d81e559. It is listed in section 5. |
| X2 | pth_inside_courtyard | U24 pad 11 (GND grommet hole, 62.65, 48.16) in the USB1 courtyard | <ul><li>The USB1 courtyard reaches 0.19 mm into the drill.</li><li>The USB1 fab outline reaches 0.05 mm into it.</li><li>The USB1 3D body (shell and tabs) ends about 0.18 mm outside it.</li></ul> | Owner placement (d81e559). It is listed in section 5. |
| X3 | npth_inside_courtyard | USB1 locating-peg NPTH (Ø0.6, 63.10, 52.62) in the Rsense2 courtyard | <ul><li>The peg hole is under the 2512 shunt body on B.Cu, 0.69 mm from its centre, between the terminals.</li><li>From the USB1 model, the peg is about 0.8 mm long. The board is 1.6 mm, so the peg stops about 0.8 mm short of the B face and of Rsense2.</li><li>The NPTH hole-to-copper rule (0.20) passes.</li></ul> | Intended: the shunt was turned 27° under the battery pad in R3-2b to cut the +BATT path resistance. |

### What the relaxing rules cover at 29c003d

These counts come from a DRC run with the 14 rules removed (scratch copy).

| Rule | Items it removes |
|---|---|
| B19 Base vias 0.35/0.20 | via_diameter ≥199 and annular_width ≥199 errors (all 1348 vias) |
| B25 U24 pads | copper_edge_clearance 35 |
| B26 USB1 tabs | copper_edge_clearance 2 |
| B27 J15-J33 wire pads | copper_edge_clearance 14 |
| B28, B29, B30 | copper_edge_clearance 1, 1, 2 (JP1.1, FL1.2, U12.7, U12.8) |
| B33, B34 | solder_mask_bridge 2 and 2 (warnings on the Base) |
| B41 USB1 escape | diff_pair_gap_out_of_range 6, diff_pair_uncoupled_length_too_long 1 |
| C18 U9 land | clearance 5 |
| C19 wire pads | copper_edge_clearance 18 |
| C21, C22 | solder_mask_bridge 5 and 4 |

## 4. Remaining warnings at FB7d

### Base (344)

| Type | Count | Note |
|---|---|---|
| footprint_filters_mismatch (parity) | 17 | The symbol footprint filter text does not match the assigned footprint name. This is library metadata only, so it is a warning (section 1). |
| lib_footprint_issues | 192 | Library-vs-board notice. The footprints come from KiCad stock libraries that the project `fp-lib-table` does not list: Resistor_SMD 91, Capacitor_SMD 82, TestPoint 8, other 11. No copper effect. |
| lib_footprint_mismatch | 71 | Library-vs-board notice: the board instance differs from the library copy. DOY180N03T 24, small_pad 14, QFN 8, other 25. The count rose from 42 to 71 with the per-instance courtyard redraw (29c003d). |
| courtyards_overlap | 64 | The classes below are as of 29c003d, when the count was 63.<ul><li>51 land-only pairs: body gap ≥ 0.20, land ≥ 0.15, land to body ≥ 0.15. NextPCB places 0201 at 0.20-0.25 pad spacing.</li><li>8 same-net land pairs under 0.15 (section 5).</li><li>4 body pairs under 0.20: J41/J51-U12 (section 5), and R20/C21-U4. R20/C21-U4 were fixed in 1cd470c: their body gaps are now 0.42 and 0.21 mm, but the courtyards still overlap.</li></ul>1cd470c added C21-C24, C24-R18 and C24-Rsense2, and removed R18-U3 and R19-U4. The full 29c003d list is in `research/review-2026-10/fb7/cyfinal_Base.txt`. No scoped DRU exception was added for the land-only pairs. |
| track_dangling | 11 | <ul><li>8 B.Cu GND stubs: (68.38, 75.48), (64.84, 75.47), (71.96, 75.51), (78.94, 46.27), (82.52, 46.30), (86.11, 46.35), (89.95, 51.84), (89.91, 59.70). 277d5ec left 8 such stubs when the pour was kept off the FET EPs and kept them for the owner pass.</li><li>+3V3 B.Cu stub, 0.20 mm, at (75.02, 50.84).</li><li>/2C B.Cu phase stub, 1.30 mm, at (79.35, 66.70), 0.375 mm from J90.38 (critique R2-06).</li><li>+4v5 F.Cu stub, 0.58 mm, at (70.30, 54.50).</li></ul> |
| connection_width | 4 | All GND (d81e559 had 7):<ul><li>A 0.023 mm pour neck on In4 and In5 between the vias at (65.45, 60.39) and (65.86, 60.10). It counts twice.</li><li>JP1.2 to its via, 0.070 mm on F.Cu.</li><li>A 0.066 mm neck between B.Cu tracks at (71.96, 75.51).</li></ul> |
| copper_sliver | 2 | B.Cu pour slivers (d81e559 had 3). |

### Core (100)

| Type | Count | Note |
|---|---|---|
| lib_footprint_issues | 60 | Library-vs-board notice, stock libraries: Capacitor_SMD 30, Resistor_SMD 24, Fiducial 3, LED_SMD 2, Package_SON 1. |
| lib_footprint_mismatch | 32 | Library-vs-board notice. It was `ignore` until FB7d. small_pad 20, other J 1, U 7, D 1, Q 1, L 1, X 1: per-instance courtyards and wire pads. |
| footprint_filters_mismatch (parity) | 20 | As on the Base. |
| courtyards_overlap | 8 | 7 land-only pairs with body gap ≥ 0.20. 1 same-net pair, Q1-R13, with a 0.125 land gap. The list is in `research/review-2026-10/fb7/cyfinal_Core.txt`. |

## 5. Owner items

| Item | Facts | Decision needed |
|---|---|---|
| Edge pads JP1.1, FL1.2, U12.7, U12.8 (Base, rules B28-B30) | <ul><li>JP1.1, the u.FL centre land (1.00 × 1.05), overhangs the edge by 0.165 mm.</li><li>FL1.2, the 2.4 GHz filter GND land (0.30 × 0.30, B.Cu), sits 0.010 mm inside.</li><li>U12.7/.8, the SH-6 shell tabs (1.20 × 1.80), overhang by 0.493 mm.</li><li>All four are the owner's placement. The lands are the datasheet lands, untrimmed.</li></ul> | Keep the lands or move the parts. If they are kept, add an order note asking NextPCB to keep these four lands: by default NextPCB pulls copper back 0.20 mm from a routed edge. NEXTPCB.md 4.7 has no such note yet. |
| J41/J51 wire pads under U12 (Base F) | J41 (+10V, 75.7, 73.35) and J51 (GND, 75.7, 74.9) are VTX power pads inside the U12 SH-6 fab outline (body gap 0.0). Their lands are 1.35 and 0.654 mm from U12's lands, on the same nets. They stay as courtyards_overlap warnings. | Choose pads or connector, or move one of them. |
| Same-net lands under 0.15 mm | <ul><li>Base, land gap / body gap: C107.1-U4.3 (+BATT) 0.000 / 0.35; C112-C113 0.055 / 0.205; C112-C23 0.055 / 0.205; R19-U4.4 (FB) 0.055 / 0.70; R17-R18 0.09 / 0.39; C36-C79 0.105 / 0.205; R18-U3 0.117 / 1.13; R18-R3 0.139 / 0.579.</li><li>Core: Q1-R13 0.125 / 0.22.</li><li>These are not DRC errors, because the pads share a net. They show only as courtyard warnings and are not exempted (critique R2-02).</li></ul> | Accept them, or spread the parts to 0.15 mm. |
| Card1 (Base F, microSD) | The datasheet outline is 0.360 mm clear of the Core outline, and the courtyard 0.367 mm clear. Only the fab convex hull, which fills the socket notch, overlaps the Core by 0.182 mm². That is not a collision. Since 29c003d, J90's courtyard is the pad field, so DRC no longer guards the Core outline (critique R2-01). It is clean today: the closest are C106 at 0.104 and C105 at 0.119 mm. | Optional: add an F.Cu "disallow footprint" rule on 'Core footprint' that exempts J90. |
| R20/C21 vs U4 (Base B, U4 LMR51430 SOT-23-6) | Fixed in 1cd470c (R20 0.42 mm, C21 0.21 mm from the U4 body). | None. |
| Grommet holes vs Q15 and USB1 (Base, exclusions X1 and X2) | <ul><li>The U24.11 holes at (88.15, 48.16) and (62.65, 48.16) are 3.0 mm drills with 3.4 mm rings.</li><li>The Q15 courtyard is 0.02 mm into the drill, and its body is 0.08 mm outside it.</li><li>The USB1 courtyard is 0.19 mm into the drill, its fab outline 0.05 mm, and its 3D body is 0.18 mm outside it.</li><li>Both parts are at the owner's d81e559 positions.</li></ul> | Check that the grommet or screw head clears Q15 and the USB1 shell. If it does, keep X1 and X2. If not, move a part. |
