"""Routing clean-up: delete dead vias and dangling track ends.

Run with KiCad closed:  $KPY hardware/tools/cleanup.py hardware/OpenAIO.kicad_pcb [--dry-run]

A via (or stack: vias of one net at one position) is dead when the copper it touches lies on one layer only:
  - it touches nothing (orphan), or
  - it is on a signal or phase net and touches only its own pad or one track (an escape whose other side is gone),
  - it is on a power net and touches only a track or nothing.
Power and GND vias in a pad or a pour are kept: they are the hookups for planes still to be routed.
A track segment with an end that touches nothing (no track, via, pad or pour of its net) is deleted. Each run does
one batch (vias first, then dangling tracks); run it until it reports nothing deleted.
"""
import collections
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


def power(name):
    return name == "GND" or name.startswith("+") or name == "/CSA+"


def main():
    a = sys.argv[1:]
    path = [x for x in a if not x.startswith("--")][0]
    b = P.LoadBoard(path)
    P.ZONE_FILLER(b).Fill(b.Zones())
    cu = list(b.GetEnabledLayers().CuStack())
    pads = [p for f in b.GetFootprints() for p in f.Pads()]
    zones = [b.GetArea(i) for i in range(b.GetAreaCount()) if not b.GetArea(i).GetIsRuleArea()]

    def touches(v, tracks):
        c = P.SHAPE_CIRCLE(v.GetPosition(), v.GetWidth(v.TopLayer()) // 2)
        hit = collections.Counter()
        for t in tracks:
            if t.GetNetCode() == v.GetNetCode() and v.IsOnLayer(t.GetLayer()) and \
                    t.GetEffectiveShape(t.GetLayer()).Collide(c, 0):
                hit[("track", t.GetLayer())] += 1
        for p in pads:
            if p.GetNetCode() == v.GetNetCode():
                for l in (P.F_Cu, P.B_Cu):
                    if v.IsOnLayer(l) and p.IsOnLayer(l) and p.GetEffectiveShape(l).Collide(c, 0):
                        hit[("pad", l)] += 1
        for z in zones:
            if z.GetNetCode() == v.GetNetCode():
                for l in cu:
                    if v.IsOnLayer(l) and z.IsOnLayer(l) and z.HitTestFilledArea(l, v.GetPosition(), c.GetRadius()):
                        hit[("zone", l)] += 1
        return hit

    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
    stacks = collections.defaultdict(list)
    for v in [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]:
        stacks[(v.GetNetCode(), v.GetPosition().x, v.GetPosition().y)].append(v)
    dead = collections.Counter()
    for g in stacks.values():
        hit = collections.Counter()
        for v in g:
            hit += touches(v, tracks)
        layers = {l for _, l in hit}
        kinds = collections.Counter(k for k, _ in hit.elements())
        name = g[0].GetNetname()
        why = None
        if not layers:
            why = "orphan"
        elif len(layers) == 1 and not power(name) and kinds["track"] <= 1 and kinds["zone"] == 0:
            why = "signal dead end"
        elif len(layers) == 1 and power(name) and kinds["pad"] == 0 and kinds["zone"] == 0 and kinds["track"] <= 1:
            why = "power dead end"
        if why:
            for v in g:
                b.Remove(v)
            dead[why] += 1
    # dangling track ends: one batch per process (KiCad's Python loses the board after Remove); repeat until none
    if not dead:
        tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
        vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]

        def end_ok(t, p):
            c = P.SHAPE_CIRCLE(p, t.GetWidth() // 2)
            for o in tracks + vias + pads:
                if o is not t and o.GetNetCode() == t.GetNetCode() and o.IsOnLayer(t.GetLayer()) and \
                        o.GetEffectiveShape(t.GetLayer()).Collide(c, 0):
                    return True
            return any(z.GetNetCode() == t.GetNetCode() and z.IsOnLayer(t.GetLayer()) and
                       z.HitTestFilledArea(t.GetLayer(), p, 0) for z in zones)

        bad = [t for t in tracks if not (end_ok(t, t.GetStart()) and end_ok(t, t.GetEnd()))]
        for t in bad:
            b.Remove(t)
        gone = len(bad)
    else:
        gone = 0
    print("vias deleted:", dict(dead), "| dangling track segments deleted:", gone)
    if "--dry-run" not in a and (dead or gone):
        P.SaveBoard(path, b)
        print("saved")


if __name__ == "__main__":
    main()
