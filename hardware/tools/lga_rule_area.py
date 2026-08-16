#!/usr/bin/env python3
"""One-shot: rule area "Base" over the Base island in the master PCB, all
copper layers, Base Edge.Cuts bbox + 1 mm. The 2 oz outer rules in
OpenAIO.kicad_dru apply only inside it, so the Core island (1 oz) keeps the
line standard. Removes any old "Core" rule area. Idempotent. KiCad's Python,
KiCad closed:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 tools/lga_rule_area.py
"""
import os
import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "OpenAIO.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
fps = {f.GetReference(): f for f in b.GetFootprints()}
split = (fps["J90"].GetPosition().x + fps["J91"].GetPosition().x) // 2
bb = None
items = list(b.GetDrawings()) + [g for f in b.GetFootprints() for g in f.GraphicalItems()]
for d in items:
    if d.GetLayer() == pcbnew.Edge_Cuts and d.GetBoundingBox().GetCenter().x < split:
        r = d.GetBoundingBox()
        if bb is None:
            bb = pcbnew.BOX2I(r.GetPosition(), r.GetSize())
        else:
            bb.Merge(r)
assert bb is not None, "no Edge.Cuts on the Base island"
m = pcbnew.FromMM(1.0)
pts = [(bb.GetLeft() - m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetTop() - m),
       (bb.GetRight() + m, bb.GetBottom() + m), (bb.GetLeft() - m, bb.GetBottom() + m)]
z = None
for zz in list(b.Zones()):
    if zz.GetIsRuleArea() and zz.GetZoneName() == "Core":
        b.Delete(zz)
    elif zz.GetIsRuleArea() and zz.GetZoneName() == "Base":
        z = zz
if z is None:
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName("Base")
    for setter in (z.SetDoNotAllowZoneFills, z.SetDoNotAllowVias, z.SetDoNotAllowTracks, z.SetDoNotAllowPads, z.SetDoNotAllowFootprints):
        setter(False)
    b.Add(z)
z.SetLayerSet(pcbnew.LSET.AllCuMask(b.GetCopperLayerCount()))
z.Outline().RemoveAllContours()
z.Outline().NewOutline()
for x, y in pts:
    z.Outline().Append(pcbnew.VECTOR2I(int(x), int(y)))
z.HatchBorder()
pcbnew.SaveBoard(PCB, b)
print("rule area Base: %.1f x %.1f mm at (%.1f, %.1f)" % ((bb.GetWidth() + 2 * m) / 1e6, (bb.GetHeight() + 2 * m) / 1e6, (bb.GetLeft() - m) / 1e6, (bb.GetTop() - m) / 1e6))
