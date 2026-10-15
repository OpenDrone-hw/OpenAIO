"""Move plane-connection via stacks that DRC flags off other nets' copper.

Run with KiCad closed, using KiCad's bundled Python, on a DRC report made from the same board:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/via_relocate.py hardware/<board>.kicad_pcb drc.json --net +3.3V [--net ...] [--dry-run]

A stack is every via of one net at one position (microvia F.Cu-In1.Cu, buried In1.Cu-In6.Cu, microvia
In6.Cu-B.Cu). Only stacks of the named nets that appear in a short, clearance, hole-to-hole or hole-clearance
error are moved, and only when the net has a zone on an inner layer the buried via crosses (the stack is a
plane tap, so any clear spot on the plane serves). The new spot is the nearest one within 0.8 mm where every
land clears other-net copper by the copper clearance, every hole keeps the hole spacing, the stack stays
0.20 mm inside the board edge, and the outer-layer stub from the old spot to the new one clears other-net
copper too. Stacks with no clear spot are listed for the owner. Zones are refilled; the board is saved only
if the unconnected count does not rise.
"""
import json
import math
import os
import re
import sys


def quiet_import():
    saved, null = os.dup(2), os.open(os.devnull, os.O_WRONLY)
    os.dup2(null, 2)
    try:
        import pcbnew
        return pcbnew
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(null)


pcbnew = quiet_import()
MM = pcbnew.FromMM
TYPES = ("shorting_items", "clearance", "hole_to_hole", "hole_clearance")
CLEAR, RF_CLEAR, EDGE = MM(0.09), MM(0.15), MM(0.20)
F, B, I1, I6 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In6_Cu
INNER = (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.In5_Cu, pcbnew.In6_Cu)


def hole_gap(a_micro, b_micro):
    # .kicad_dru: 0.30 between different-net holes; 0.25 between a laser and a buried hole.
    return MM(0.25) if a_micro != b_micro else MM(0.30)


def unconnected(board):
    board.BuildConnectivity()
    return board.GetConnectivity().GetUnconnectedCount(True)


def spans(v):
    order = [F] + list(INNER) + [B]
    i, j = order.index(v.TopLayer()), order.index(v.BottomLayer())
    return order[i:j + 1]


def main():
    args = sys.argv[1:]
    nets = [args[i + 1] for i, a in enumerate(args) if a == "--net"]
    path, report = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--net")][:2]
    dry = "--dry-run" in args
    board = pcbnew.LoadBoard(path)
    drc = json.load(open(report))
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    edges = [d.GetEffectiveShape(pcbnew.Edge_Cuts) for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    items = list(board.GetTracks())
    vias = [t for t in items if t.GetClass() == "PCB_VIA"]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    planes = {(z.GetNetname(), l) for z in board.Zones() if not z.GetIsRuleArea() for l in z.GetLayerSet().CuStack() if l in INNER}

    # Stacks named in errors.
    targets = []
    for x in drc["violations"]:
        if x["type"] not in TYPES or x["severity"] != "error":
            continue
        for it in x["items"]:
            m = re.match(r"\s*Buried via \[(.*?)\]", it["description"])
            if not m or m.group(1) not in nets:
                continue
            p = pcbnew.VECTOR2I(MM(it["pos"]["x"]), MM(it["pos"]["y"]))
            stack = [v for v in vias if v.GetNetname() == m.group(1) and (v.GetPosition() - p).EuclideanNorm() < MM(0.005)]
            if stack and not any(stack[0] in s for s in targets):
                targets.append(stack)

    def rf(item):
        return item.GetNetClassName() == "RF"

    def clear_at(stack, pos, stubs):
        net = stack[0].GetNetCode()
        for v in stack:
            r = v.GetWidth(v.TopLayer()) // 2
            if not outline.Contains(pos) or any(e.Collide(pcbnew.SHAPE_CIRCLE(pos, r), EDGE) for e in edges):
                return False
            for layer in spans(v):
                land = pcbnew.SHAPE_CIRCLE(pos, r)
                for o in items:
                    if o in stack or o.GetNetCode() == net or not o.IsOnLayer(layer):
                        continue
                    gap = RF_CLEAR if rf(o) else CLEAR
                    if o.GetEffectiveShape(layer).Collide(land, gap):
                        return False
                for p in pads:
                    if p.GetNetCode() == net or not p.IsOnLayer(layer):
                        continue
                    gap = RF_CLEAR if rf(p) else CLEAR
                    if p.GetEffectiveShape(layer).Collide(land, gap):
                        return False
            micro = v.GetViaType() == pcbnew.VIATYPE_MICROVIA
            hr = v.GetDrillValue() // 2
            for o in vias:
                if o in stack or o.GetNetCode() == net:
                    continue
                if not set(spans(o)) & set(spans(v)):
                    continue
                d = (o.GetPosition() - pos).EuclideanNorm()
                if d - hr - o.GetDrillValue() // 2 < hole_gap(micro, o.GetViaType() == pcbnew.VIATYPE_MICROVIA):
                    return False
            for p in pads:
                if p.GetNetCode() != net and p.HasHole():
                    d = (p.GetPosition() - pos).EuclideanNorm()
                    if d - r - p.GetDrillSize().x // 2 < MM(0.23):
                        return False
        for layer, a, w in stubs:
            seg = pcbnew.SHAPE_SEGMENT(a, pos, w)
            for o in items + pads:
                if o in stack or o.GetNetCode() == net or not o.IsOnLayer(layer):
                    continue
                gap = RF_CLEAR if rf(o) else CLEAR
                if o.GetEffectiveShape(layer).Collide(seg, gap):
                    return False
        return True

    base = unconnected(board)
    moved, owner = [], []
    for stack in targets:
        net = stack[0].GetNetname()
        buried = [v for v in stack if v.GetViaType() == pcbnew.VIATYPE_BURIED]
        if not buried or not any((net, l) in planes for l in spans(buried[0])):
            owner.append((stack, "not a plane tap"))
            continue
        old = stack[0].GetPosition()
        stubs = []
        for v in stack:
            if v.GetViaType() != pcbnew.VIATYPE_MICROVIA:
                continue
            outer = F if v.TopLayer() == F else B
            w = max([t.GetWidth() for t in items if t.GetClass() != "PCB_VIA" and t.GetNetCode() == v.GetNetCode()
                     and t.GetLayer() == outer and (t.GetStart() == old or t.GetEnd() == old)] or [MM(0.15)])
            stubs.append((outer, old, min(w, MM(0.25))))
        best = None
        for step in range(1, 17):
            r = MM(0.05) * step
            for k in range(24):
                a = 2 * math.pi * k / 24
                pos = pcbnew.VECTOR2I(old.x + int(r * math.cos(a)), old.y + int(r * math.sin(a)))
                if clear_at(stack, pos, stubs):
                    best = pos
                    break
            if best:
                break
        if best is None:
            owner.append((stack, "no clear spot within 0.8 mm"))
            continue
        for v in stack:
            v.SetPosition(best)
        for layer, a, w in stubs:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(a)
            t.SetEnd(best)
            t.SetWidth(w)
            t.SetLayer(layer)
            t.SetNet(stack[0].GetNet())
            board.Add(t)
            items.append(t)
        moved.append((net, old, best))
        print(f"moved {net} {pcbnew.ToMM(old.x):.2f},{pcbnew.ToMM(old.y):.2f} -> "
              f"{pcbnew.ToMM(best.x):.2f},{pcbnew.ToMM(best.y):.2f} ({pcbnew.ToMM((best - old).EuclideanNorm()):.2f} mm)")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    after = unconnected(board)
    print(f"{len(moved)} stacks moved; unconnected {base} -> {after}")
    for stack, why in owner:
        p = stack[0].GetPosition()
        print(f"OWNER {stack[0].GetNetname()} {pcbnew.ToMM(p.x):.2f},{pcbnew.ToMM(p.y):.2f}: {why}")
    if after > base:
        sys.exit("a connection was lost; board not saved")
    if not dry:
        pcbnew.SaveBoard(path, board)
        print("saved")


if __name__ == "__main__":
    main()
