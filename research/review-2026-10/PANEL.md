# Panels for the NextPCB order (DFM-10)

Both boards are below NextPCB's 50 x 50 mm minimum PCBA panel, so each is
ordered as an array with rails. This file proposes the panels. It does not
change either board outline. Measurements come from FB1
(`scratchpad/fb1/py/edgeruns.py` on the f193d5f+FB1 boards): an edge run is
"free" when no pad or part body (either side, from the F.Fab or B.Fab outline)
is within the stated distance.

## NextPCB limits that apply

All from NEXTPCB.md sections 1 and 2:

- Minimum PCBA panel 50 x 50 mm.
- Rails at least 3 mm; the order form defaults to 5 mm.
- Routed gap 1.6 mm.
- Mouse-bite tabs at least 5 mm wide, with stamp holes of 0.5-0.8 mm.
- Parts at least 3.0 mm from a tab (DFA guide).
- Fiducials 1 mm.

## What the edges allow

| Board | Perimeter | Free run, nothing within 0.5 mm | Free run, nothing within 1.0 mm |
|---|---|---|---|
| Core | 84.1 mm | 21.6 mm in total. Longest: 11.1 mm on the bottom edge (Core x 105.0-114.4, y 62.2-63.1), 2.7 mm on the new corner chamfer and diagonal (103.1-103.6, 49.1-51.7), 1.65 mm at (105.0, 53.2) | 2.75 mm in total, longest 1.45 mm |
| Base | 131.3 mm | 9.4 mm in total. Longest: 2.9 mm at x = 91.9 (y 64.9-67.8), 2.05 mm on the bottom edge (x 87.4, y 77.4), 2.0 mm at x = 91.9 (y 70.8) | 0.95 mm |

Nothing on either board is 3 mm from a 5 mm tab.

Other edge conditions:

- On the Base, the battery and motor pads (U24) and the wire pads (J15-J33) cross the routed edge on every side (DFM-20).
- USB1 overhangs the Base edge by 1.1 mm.
- The Core has wire pads (J*) along three sides.
- On the Base top, U12, Q13 and Q11 sit 0.37-0.53 mm from the Core's bottom edge once the Core is placed. Any nub left on that Core edge would touch them.

So the tabs must be narrow, sit only on the free runs, and be cut by a router.
They must not be snapped, because snapping leaves nubs and puts strain on the
parts.

## Proposal

**Depanelling.** Solid tabs, no perforation. NextPCB separates the boards
after assembly with a router (CNC depanel), so the cut is flush with the
board outline and no nubs are left. If NextPCB only offers mouse bites, use 0.5 mm stamp holes at a 0.75 mm
pitch with the hole centres 0.25 mm outside the board outline. Then sand every
Core nub flush before the Core is placed on J90.

**Core panel.** 3 x 2 Cores, 1.6 mm routed gaps, 5 mm rails top and bottom.
The panel is 72.2 x 51.8 mm (3 x 23.0 + 2 x 1.6 by 2 x 20.1 + 1.6 + 2 x 5).
Three tabs per Core:

| Tab | Where (Core coordinates) | Width | Clearance to parts |
|---|---|---|---|
| T1 | bottom edge, x 106.0-109.0 | 3.0 mm | >= 0.5 mm |
| T2 | bottom edge, x 111.0-114.0 | 3.0 mm | >= 0.5 mm |
| T3 | corner chamfer / diagonal, (103.2, 50.0)-(103.5, 51.3) | 1.5 mm | >= 0.5 mm |

T1 and T2 face the Base parts U12, Q13 and Q11, so the cut there must be
flush (router).

**Base panel.** 2 x 2 Bases, 1.6 mm routed gaps, 5 mm rails top and bottom.
The panel is 52.6 x 62.6 mm. Three tabs per Base, all on the free runs:

| Tab | Where (Base coordinates) | Width |
|---|---|---|
| T1 | right edge x = 91.9, y 65.1-67.6 | 2.5 mm |
| T2 | right edge x = 91.9, y 70.9-72.6 | 1.7 mm |
| T3 | bottom edge, x 86.6-88.4 (y 77.4) | 1.8 mm |

Two more points for the Base panel:

- **USB1 overhang.** The routed gap on the USB1 side must be at least 2.5 mm, so the connector overhang clears the neighbouring board or the rail.
- **Edge pads.** The pads that cross the edge stay as drawn. Put "copper to the routed edge intended, no pull-back" on the order (DFM-20).

**Rails (both panels).**

- **Fiducials.** Three global fiducials, 1.0 mm copper with a 2.0 mm opening, placed asymmetrically: two at the ends of one rail and one 10 mm off-centre on the other. They go on both F and B, because the Base is assembled on both sides and its top has no fiducials of its own (DFM-21).
- **Tooling holes.** Four NPTH tooling holes, 2.0 mm, at the rail corners, 3.5 mm from the panel edges.
- **Board fiducials.** These stay as local references. The Core has FID1 (1.0 mm) and FID2/FID3 (0.5 mm local fiducials, see NEXTPCB.md 4.7). The Base has FID1-FID3 on B.

## Questions for NextPCB (add to NEXTPCB.md 4.6)

- Do you accept tabs narrower than 5 mm (1.5-3.0 mm here) if you depanel by router?
- Do you accept parts 0.5 mm from a router-cut tab?
- Can you panelize from this description, or should we send KiKit panel Gerbers?

To generate the panels, run KiKit (`kikit panelize`) with a fixed-grid
layout, `tabs: annotation`, and the tab positions above placed as KiKit tab
annotations on a copy of each board. The repo boards keep their outline.
