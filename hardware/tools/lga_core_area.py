#!/usr/bin/env python3
"""One-shot: rule area "Core" over the Core island in the master PCB, all
copper layers, so the 2 oz outer rules in OpenAIO.kicad_dru skip the Core
(1 oz). Covers the Core Edge.Cuts bbox + 1 mm. Idempotent: an existing area
named Core is resized. Run with KiCad's Python, KiCad closed:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 tools/lga_core_area.py
"""
import os
import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "OpenAIO.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
fps = {f.GetReference(): f for f in b.GetFootprints()}
split = (fps["J90"].GetPosition().x + fps["J91"].GetPosition().x) // 2
bb = None
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts and d.GetBoundingBox().GetCenter().x > split:
        r = d.GetBoundingBox()
        if bb is None:
            bb = pcbnew.BOX2I(r.GetPosition(), r.GetSize())
        else:
            bb.Merge(r)
assert bb is not None, "no Edge.Cuts on the Core island"
m = pcbnew.FromMM(1.0)
pts = [(bb.GetLeft() - m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetTop() - m),
       (bb.GetRight() + m, bb.GetBottom() + m), (bb.GetLeft() - m, bb.GetBottom() + m)]
z = None
for zz in b.Zones():
    if zz.GetIsRuleArea() and zz.GetZoneName() == "Core":
        z = zz
if z is None:
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName("Core")
    z.SetDoNotAllowZoneFills(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    b.Add(z)
z.SetLayerSet(pcbnew.LSET.AllCuMask(b.GetCopperLayerCount()))
z.Outline().RemoveAllContours()
z.Outline().NewOutline()
for x, y in pts:
    z.Outline().Append(pcbnew.VECTOR2I(int(x), int(y)))
z.HatchBorder()
pcbnew.SaveBoard(PCB, b)
print("rule area Core: %.1f x %.1f mm at (%.1f, %.1f)" % ((bb.GetWidth() + 2 * m) / 1e6, (bb.GetHeight() + 2 * m) / 1e6, (bb.GetLeft() - m) / 1e6, (bb.GetTop() - m) / 1e6))
