#!/usr/bin/env python3
"""One-shot: drop J90 (Core_LGA_land) on the Base island and J91
(Core_LGA_pads, flipped to B.Cu) on the Core island of the master PCB, with
the schematic paths set so 'Update PCB from Schematic' relinks them instead
of adding duplicates. Nets are assigned by that update. Idempotent.
Run with KiCad's Python, KiCad closed:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 tools/lga_place.py
"""
import os
import re
import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "OpenAIO.kicad_pcb")
IFACE = os.path.join(HW, "core_interface.kicad_sch")
J90_AT = (75.4, 60.91)     # Base island centre (U24 outline centre)
J91_AT = (123.15, 47.7)    # Core electronics block centre

sch = open(IFACE).read()
sheet_uuid = re.search(r'\(uuid "([0-9a-f-]{36})"', sch).group(1)
sym = dict((r, u) for u, r in re.findall(
    r'\(symbol\n\t\t\(lib_id "lib:Core_LGA"\).*?\(uuid "([0-9a-f-]{36})"\).*?\(property "Reference" "(J\d+)"', sch, re.S))

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
    print("placed", ref, fpname, at, "B.Cu" if flip else "F.Cu", "path", fp.GetPath().AsString())
pcbnew.SaveBoard(PCB, b)
