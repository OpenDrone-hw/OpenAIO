"""Give every pad of an unrouted link a via: a short track from the pad to a through via 0.33/0.15 (a dogbone).

Run with KiCad closed:  $KPY hardware/tools/esc_vias.py hardware/OpenAIO.kicad_pcb drc.json [--blind] [--dry-run]

--blind: where no through via fits, try a 0.33/0.15 blind via that stops one layer short of the far side
(L1-L7 from the top, L2-L8 from the bottom), so opposite-side parts no longer block it.

drc.json is `kicad-cli pcb drc --format json --severity-all` of the board. For every unconnected link, each end
that is an SMD pad on F.Cu or B.Cu whose copper island has no via yet gets one. Skipped: GND, /CSA+, +BATT and
the phases (they are pours), and pads whose island already holds a via. The via goes to the nearest spot,
0.35 to 2.0 mm from the pad centre, preferring the direction of the other end, where:
  - its land clears every other-net pad, track and via on all layers (the larger own clearance, at least 0.10),
    and other-net pours other than GND and the priority-1 +BATT planes (they reflow around it);
  - its hole is 0.20 from every other hole and the board edge is 0.30 away;
  - the stub (0.10 wide, on the pad's layer) clears every other-net item there.
New items go to <board>.esc.txt (UUIDs), so they can be pruned like tools/fr_prune.py does.
"""
import json
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
SKIP = {"GND", "/CSA+", "+BATT", *[f"/{i}{c}" for i in range(1, 5) for c in "ABC"]}
LAND, DRILL, STUB = MM(0.33), MM(0.15), MM(0.10)


def main():
    a = sys.argv[1:]
    path, drc = [x for x in a if not x.startswith("--")][:2]
    b = P.LoadBoard(path)
    P.ZONE_FILLER(b).Fill(b.Zones())
    cu = list(b.GetEnabledLayers().CuStack())
    con = b.GetConnectivity()
    by_uuid = {}
    pads = [p for f in b.GetFootprints() for p in f.Pads()]
    for p in pads:
        by_uuid[p.m_Uuid.AsString()] = p
    tracks = list(b.GetTracks())
    vias = [t for t in tracks if t.GetClass() == "PCB_VIA"]
    items = pads + tracks
    zones = [b.GetArea(i) for i in range(b.GetAreaCount())
             if not b.GetArea(i).GetIsRuleArea() and b.GetArea(i).GetNetname() != "GND"
             and b.GetArea(i).GetAssignedPriority() > 1]          # GND (0) and the +BATT planes (1) reflow around it
    outline = P.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline, True)
    edges = [d for d in b.GetDrawings() if d.GetLayer() == P.Edge_Cuts]

    def island_has_via(p):
        seen, todo = {p.m_Uuid.AsString()}, [p]
        while todo:
            x = todo.pop()
            for y in con.GetConnectedItems(x):
                k = y.m_Uuid.AsString()
                if y.GetClass() == "PCB_VIA":
                    return True
                if k not in seen and y.GetClass() in ("PCB_TRACK", "PCB_ARC", "PAD"):
                    seen.add(k)
                    todo.append(y)
        return False

    def clear(shape, layer, net, extra=0):
        for o in items + added_objs:
            if o.GetNetCode() == net or not o.IsOnLayer(layer):
                continue
            cl = max(o.GetOwnClearance(layer), MM(0.10)) + extra
            if o.GetEffectiveShape(layer).Collide(shape, cl - 5):
                return False
        return True

    def via_ok(pos, net, lays):
        if not outline.Contains(pos) or any(d.GetEffectiveShape().Collide(P.SHAPE_CIRCLE(pos, LAND // 2), MM(0.30))
                                            for d in edges):
            return False
        land = P.SHAPE_CIRCLE(pos, LAND // 2)
        for l in lays:
            if not clear(land, l, net):
                return False
            for z in zones:
                if z.GetNetCode() != net and z.IsOnLayer(l) and \
                        z.HitTestFilledArea(l, pos, LAND // 2 + MM(0.10)):
                    return False
        for v in vias + [o for o in added_objs if o.GetClass() == "PCB_VIA"]:
            if (v.GetPosition() - pos).EuclideanNorm() < DRILL // 2 + v.GetDrillValue() // 2 + MM(0.20):
                return False
        return True

    def scan(p, c, layer, o, lays):
        toward = math.atan2(MM(o["y"]) - c.y, MM(o["x"]) - c.x)
        for r in [0.35, 0.45, 0.55, 0.7, 0.85, 1.0, 1.2, 1.4, 1.7, 2.0]:
            for k in range(48):
                ang = toward + ((k + 1) // 2) * (1 if k % 2 else -1) * math.pi / 24
                pos = P.VECTOR2I(int(c.x + MM(r) * math.cos(ang)), int(c.y + MM(r) * math.sin(ang)))
                if p.GetEffectiveShape(layer).Collide(P.SHAPE_CIRCLE(pos, LAND // 2), MM(0.10)) and \
                        not p.HitTest(pos):
                    continue
                if not via_ok(pos, p.GetNetCode(), lays):
                    continue
                if not clear(P.SHAPE_SEGMENT(c, pos, STUB), layer, p.GetNetCode()):
                    continue
                return pos
        return None

    links = json.load(open(drc))["unconnected_items"]
    added_objs, done, report = [], set(), []
    for u in links:
        ends = u["items"]
        for i, e in enumerate(ends):
            p = by_uuid.get(e["uuid"])
            if p is None or p.GetNetname() in SKIP or p.m_Uuid.AsString() in done:
                continue
            if p.GetAttribute() != P.PAD_ATTRIB_SMD:
                continue
            done.add(p.m_Uuid.AsString())
            if island_has_via(p):
                continue
            layer = P.F_Cu if p.IsOnLayer(P.F_Cu) else P.B_Cu
            far = P.B_Cu if layer == P.F_Cu else P.F_Cu
            c = p.GetPosition()
            options = [(cu, P.VIATYPE_THROUGH, P.F_Cu, P.B_Cu)]
            if "--blind" in a:      # stop one layer short of the far side: L1-L7 or L2-L8
                options.append(([l for l in cu if l != far], P.VIATYPE_BLIND,
                                layer, cu[-2] if layer == P.F_Cu else cu[1]))
            best = None
            for lays, vtype, la, lb in options:
                best = scan(p, c, layer, ends[1 - i]["pos"], lays)
                if best:
                    break
            ref = f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()} {p.GetNetname()}"
            if not best:
                report.append("no spot " + ref)
                continue
            t = P.PCB_TRACK(b)
            t.SetStart(c)
            t.SetEnd(best)
            t.SetWidth(STUB)
            t.SetLayer(layer)
            t.SetNet(p.GetNet())
            b.Add(t)
            v = P.PCB_VIA(b)
            v.SetPosition(best)
            v.SetViaType(vtype)
            v.SetLayerPair(la, lb)
            v.SetWidth(LAND)
            v.SetDrill(DRILL)
            v.SetNet(p.GetNet())
            b.Add(v)
            added_objs += [t, v]
            report.append(("via " if vtype == P.VIATYPE_THROUGH else "via blind ") + ref)
    n = sum(1 for r in report if r.startswith("via"))
    print(f"{n} escape vias added, {len(report) - n} pads without a free spot")
    for r in report:
        if not r.startswith("via"):
            print("  ", r)
    if "--dry-run" not in a:
        P.ZONE_FILLER(b).Fill(b.Zones())
        P.SaveBoard(path, b)
        open(path + ".esc.txt", "w").write("\n".join(o.m_Uuid.AsString() for o in added_objs) + "\n")
        print("saved")


if __name__ == "__main__":
    main()
