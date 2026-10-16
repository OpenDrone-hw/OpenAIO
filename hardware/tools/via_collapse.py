"""Edit form for routing: every non-GND via stack becomes one via; GND keeps its microvias.

Run with KiCad closed:  $KPY hardware/tools/via_collapse.py hardware/OpenAIO.kicad_pcb [--keep uuid,...] [--dry-run]

A stack is the vias of one net at one position (microvia + buried, from tools/via_types.py). Each non-GND stack,
and each lone non-GND microvia, is replaced by one 0.33/0.15 via over the union of the layers it spanned:
  L1 and L8      -> through
  L1 + inner     -> blind L1-L7
  L8 + inner     -> blind L2-L8
  inner only     -> buried L2-L7
Blind vias show as items_not_allowed warnings while routing. When routing is done, tools/via_types.py
--buried-size 0.33/0.15 turns them back into stacks.
--keep: UUIDs of new vias (from <board>.collapse.txt) to turn back into their original stack, e.g. those in a DRC
error after collapsing. The original stacks are stored in <board>.collapse.json.
"""
import collections
import json
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


def via_rec(v):
    return {"x": v.GetPosition().x, "y": v.GetPosition().y, "type": int(v.GetViaType()), "top": v.TopLayer(),
            "bot": v.BottomLayer(), "w": v.GetWidth(v.TopLayer()), "d": v.GetDrillValue()}


def add_via(b, net, r):
    v = P.PCB_VIA(b)
    v.SetPosition(P.VECTOR2I(r["x"], r["y"]))
    v.SetViaType(r["type"])
    v.SetLayerPair(r["top"], r["bot"])
    v.SetWidth(r["w"])
    v.SetDrill(r["d"])
    v.SetNet(net)
    b.Add(v)
    return v


def main():
    a = sys.argv[1:]
    path = a[0]
    b = P.LoadBoard(path)
    cu = list(b.GetEnabledLayers().CuStack())
    order = {l: i for i, l in enumerate(cu)}
    F, B, I1, IN = cu[0], cu[-1], cu[1], cu[-2]
    store = path + ".collapse.json"

    if "--keep" in a:      # turn the listed collapsed vias back into their original stacks
        keep = set(a[a.index("--keep") + 1].split(","))
        orig = json.load(open(store))
        n = 0
        for v in [t for t in b.GetTracks() if t.m_Uuid.AsString() in keep]:
            for r in orig.get(v.m_Uuid.AsString(), []):
                add_via(b, v.GetNet(), r)
            b.Remove(v)
            n += 1
        print(f"{n} vias turned back into stacks")
        if "--dry-run" not in a:
            P.ZONE_FILLER(b).Fill(b.Zones())
            P.SaveBoard(path, b)
        return

    groups = collections.defaultdict(list)
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetname() != "GND":
            p = t.GetPosition()
            groups[(t.GetNetCode(), p.x, p.y)].append(t)
    stat = collections.Counter()
    plan = []
    for key, vs in groups.items():
        if len(vs) == 1 and vs[0].GetViaType() != P.VIATYPE_MICROVIA:
            continue                       # already one via (through, blind or buried)
        layers = set()
        for v in vs:
            lo, hi = sorted((order[v.TopLayer()], order[v.BottomLayer()]))
            layers |= set(cu[lo:hi + 1])
        if F in layers and B in layers:
            kind, top, bot = P.VIATYPE_THROUGH, F, B
        elif F in layers:
            kind, top, bot = P.VIATYPE_BLIND, F, IN
        elif B in layers:
            kind, top, bot = P.VIATYPE_BLIND, I1, B
        else:
            kind, top, bot = P.VIATYPE_BURIED, I1, IN
        stat[{P.VIATYPE_THROUGH: "through", P.VIATYPE_BLIND: "blind", P.VIATYPE_BURIED: "buried"}[kind]] += 1
        plan.append((vs, kind, top, bot))
    print("stacks collapsed:", dict(stat))
    if "--dry-run" in a:
        return
    orig, new = {}, []
    for vs, kind, top, bot in plan:
        net, p = vs[0].GetNet(), vs[0].GetPosition()
        recs = [via_rec(v) for v in vs]
        for v in vs:
            b.Remove(v)
        nv = add_via(b, net, {"x": p.x, "y": p.y, "type": kind, "top": top, "bot": bot,
                              "w": MM(0.33), "d": MM(0.15)})
        orig[nv.m_Uuid.AsString()] = recs
        new.append(nv.m_Uuid.AsString())
    P.ZONE_FILLER(b).Fill(b.Zones())
    P.SaveBoard(path, b)
    json.dump(orig, open(store, "w"))
    open(path + ".collapse.txt", "w").write("\n".join(new) + "\n")
    print("saved")


if __name__ == "__main__":
    main()
