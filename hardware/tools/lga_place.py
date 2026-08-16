#!/usr/bin/env python3
"""One-shot: drop J90 (Core_LGA_land) on the Base island and J91
(Core_LGA_pads, flipped to B.Cu) on the Core island of the master PCB, with
the schematic paths set so 'Update PCB from Schematic' relinks them instead
of adding duplicates. Pad nets come from the lga_gen pin table when the nets
exist on the board. Idempotent.
Run with KiCad's Python, KiCad closed:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 tools/lga_place.py
"""
import os
import re
import sys
import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "OpenAIO.kicad_pcb")
IFACE = os.path.join(HW, "core_interface.kicad_sch")
J90_AT = (78.9, 62.0)      # centre of the free area on the Base top (Card1 .. Q21-25, C105/6 .. U12)
J91_AT = (114.1, 53.55)    # inside the Core outline, 0.4 mm clear of its right step

sch = open(IFACE).read()
sheet_uuid = re.search(r'\(uuid "([0-9a-f-]{36})"', sch).group(1)
sym = dict((r, u) for u, r in re.findall(
    r'\(symbol\n\t\t\(lib_id "lib:Core_LGA"\).*?\(uuid "([0-9a-f-]{36})"\).*?\(property "Reference" "(J\d+)"', sch, re.S))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lga_gen import PINS
PIN_NET = {n: name for n, name, kind in PINS}
missing = set()

b = pcbnew.LoadBoard(PCB)
have = {f.GetReference(): f for f in b.GetFootprints()}
lib = os.path.join(HW, "lib.pretty")
for ref, fpname, at, flip in (("J90", "Core_LGA_land", J90_AT, False), ("J91", "Core_LGA_pads", J91_AT, True)):
    if ref in have:
        print(ref, "already on board at", have[ref].GetPosition())
        continue
    fp = pcbnew.FootprintLoad(lib, fpname)
    fp.SetReference(ref)
    fp.SetValue("Core_LGA")
    b.Add(fp)                      # add first: Flip() on a board-less footprint crashes
    fp.SetFPIDAsString("lib:" + fpname)
    fp.SetPath(pcbnew.KIID_PATH("/" + sheet_uuid + "/" + sym[ref]))
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(at[0]), pcbnew.FromMM(at[1])))
    if flip:
        fp.Flip(fp.GetPosition(), False)
    for pad in fp.Pads():
        net = b.FindNet(PIN_NET[int(pad.GetNumber())])
        if net is not None:
            pad.SetNet(net)
        else:
            missing.add(PIN_NET[int(pad.GetNumber())])
    print("placed", ref, fpname, at, "B.Cu" if flip else "F.Cu", "path", fp.GetPath().AsString())
pcbnew.SaveBoard(PCB, b)
if missing:
    print("nets not on the board yet (Update PCB from Schematic will assign them):", sorted(missing))
