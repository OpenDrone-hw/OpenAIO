#!/usr/bin/env python3
"""One-shot: move the Core outline drawn on User.2 (right island of the
master) to Edge.Cuts, replacing whatever Edge.Cuts the Core island had.
Refuses if the User.2 contour is not closed. KiCad's Python, KiCad closed.
"""
import math
import os
import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "OpenAIO.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
xs = [f.GetPosition().x for f in b.GetFootprints()]
split = 99e6
u2 = [d for d in b.GetDrawings() if d.GetLayerName() == "User.2" and d.GetBoundingBox().GetCenter().x > split]
ends = []
for d in u2:
    ends += [(d.GetStart().x, d.GetStart().y), (d.GetEnd().x, d.GetEnd().y)]
loose = [p for p in ends if sum(1 for q in ends if math.hypot(p[0] - q[0], p[1] - q[1]) < 10000) < 2]
assert u2 and not loose, f"User.2 contour missing or open at {loose}"
old = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetBoundingBox().GetCenter().x > split]
for d in old:
    b.Delete(d)
for d in u2:
    d.SetLayer(pcbnew.Edge_Cuts)
    d.SetWidth(pcbnew.FromMM(0.1))
pcbnew.SaveBoard(PCB, b)
print(f"Core outline: {len(u2)} User.2 items -> Edge.Cuts, {len(old)} old Edge.Cuts items removed")
