"""Set every via to the stackup minimum without losing a connection.

Run with KiCad closed:  $KPY hardware/tools/via_min.py hardware/OpenAIO.kicad_pcb [--dry-run]

Sizes (land / drill, 8L HDI 1+6+1 on the OpenAIO-Whoop stackup):
  microvia 0.25 / 0.10, buried 0.33 / 0.15, through 0.33 / 0.15 (0.997 mm board, 6.6:1, NextPCB min drill 0.15).
A via keeps its position. Same-net copper (pad, track) that touched the old land but not the new one is joined by a
stub track from the via centre to that copper, on the layer where it touched: to the pad centre, or to the nearest
point of the track. A via whose old land reached a pour that the new land does not reach keeps its old size. Stub width 0.15 mm (or the touching track's width if smaller). Zones are refilled.
"""
import math
import os
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


P = quiet_import()
MM = P.FromMM
SIZE = {P.VIATYPE_MICROVIA: (MM(0.25), MM(0.10)), P.VIATYPE_BURIED: (MM(0.33), MM(0.15)),
        P.VIATYPE_THROUGH: (MM(0.33), MM(0.15))}


def main():
    a = sys.argv[1:]
    path = [x for x in a if not x.startswith("--")][0]
    b = P.LoadBoard(path)
    cu = list(b.GetEnabledLayers().CuStack())
    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
    pads = [p for f in b.GetFootprints() for p in f.Pads()]
    by_net = {}
    for o in tracks + pads:
        by_net.setdefault(o.GetNetCode(), []).append(o)
    changed, stubs = 0, 0
    P.ZONE_FILLER(b).Fill(b.Zones())
    zones = [b.GetArea(i) for i in range(b.GetAreaCount()) if not b.GetArea(i).GetIsRuleArea()]

    def zone_hits(v, r):
        return {(id(z), l) for z in zones if z.GetNetCode() == v.GetNetCode()
                for l in cu if v.IsOnLayer(l) and z.IsOnLayer(l) and z.HitTestFilledArea(l, v.GetPosition(), int(r))}
    olds = {}
    for v in [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]:
        want = SIZE.get(v.GetViaType())
        if not want or (v.GetWidth(v.TopLayer()) == want[0] and v.GetDrillValue() == want[1]):
            continue
        pos = v.GetPosition()
        layers = [l for l in cu if v.IsOnLayer(l)]
        before = []
        for o in by_net.get(v.GetNetCode(), []):
            for l in layers:
                if o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(P.SHAPE_CIRCLE(pos, v.GetWidth(l) // 2), 0):
                    before.append((o, l))
        olds[id(v)] = (v, v.GetWidth(v.TopLayer()), v.GetDrillValue(), zone_hits(v, v.GetWidth(v.TopLayer()) // 2))
        v.SetWidth(want[0])
        v.SetDrill(want[1])
        changed += 1
        land = P.SHAPE_CIRCLE(pos, want[0] // 2)
        for o, l in before:
            if o.GetEffectiveShape(l).Collide(land, 0):
                continue
            if o.GetClass() == "PCB_TRACK":
                s, e = o.GetStart(), o.GetEnd()
                dx, dy = e.x - s.x, e.y - s.y
                L2 = dx * dx + dy * dy
                u = max(0.0, min(1.0, ((pos.x - s.x) * dx + (pos.y - s.y) * dy) / L2)) if L2 else 0.0
                end = P.VECTOR2I(int(s.x + u * dx), int(s.y + u * dy))
                w = min(MM(0.15), o.GetWidth())
            else:
                end = o.GetPosition()
                w = MM(0.15)
            t = P.PCB_TRACK(b)
            t.SetStart(pos)
            t.SetEnd(end)
            t.SetWidth(w)
            t.SetLayer(l)
            t.SetNet(v.GetNet())
            b.Add(t)
            stubs += 1
    P.ZONE_FILLER(b).Fill(b.Zones())
    # A via that reached a pour only through its old land keeps its old size (pours have no stub).
    kept = 0
    for v, w, d, hits in olds.values():
        if hits - zone_hits(v, v.GetWidth(v.TopLayer()) // 2):
            v.SetWidth(w)
            v.SetDrill(d)
            kept += 1
    if kept:
        P.ZONE_FILLER(b).Fill(b.Zones())
    changed -= kept
    print(f"{kept} vias kept their size: they reach a pour only through the larger land")
    print(f"{changed} vias set to the minimum size, {stubs} stub tracks added to keep their connections")
    if "--dry-run" not in a:
        P.SaveBoard(path, b)
        print("saved")


if __name__ == "__main__":
    main()
