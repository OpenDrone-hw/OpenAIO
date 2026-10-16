"""Edit form for routing: every non-GND via becomes one through via 0.33/0.15; every via gets its type's size.

Run with KiCad closed:  $KPY hardware/tools/via_norm.py hardware/OpenAIO.kicad_pcb [--dry-run]

  non-GND via (blind, buried or microvia)  -> through 0.33/0.15 at the same spot, when its new lands on the layers
                                              it did not span clear every other-net track, pad and via there
                                              (the larger of both items' own clearance) and its hole is 0.20 from
                                              every other hole; otherwise it stays as it is and is listed
  GND via                                  -> keeps its type (microvia into the nearest plane, or through)
  size                                     -> microvia 0.25/0.10, through and buried 0.33/0.15, unless only the
                                              larger land reaches a pour of its net (listed)
A new outer land under a mask opening (graphics on F.Mask / B.Mask, e.g. the AIO logo) is a conflict too.
Zones are refilled. The final pass (via_types.py) turns the through vias back into HDI stacks.
"""
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
HOLE_TO_HOLE = MM(0.20)


def main():
    a = sys.argv[1:]
    path = [x for x in a if not x.startswith("--")][0]
    b = P.LoadBoard(path)
    cu = list(b.GetEnabledLayers().CuStack())
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    others = [t for t in b.GetTracks() if t.GetClass() != "PCB_VIA"] + \
        [p for f in b.GetFootprints() for p in f.Pads()]
    mask = {P.F_Cu: [], P.B_Cu: []}
    for d in b.GetDrawings():
        if d.GetLayer() in (P.F_Mask, P.B_Mask):
            mask[P.F_Cu if d.GetLayer() == P.F_Mask else P.B_Cu].append(d)
    P.ZONE_FILLER(b).Fill(b.Zones())
    zones = [b.GetArea(i) for i in range(b.GetAreaCount()) if not b.GetArea(i).GetIsRuleArea()]

    def zone_hits(v, r):
        return {(id(z), l) for z in zones if z.GetNetCode() == v.GetNetCode()
                for l in cu if v.IsOnLayer(l) and z.IsOnLayer(l) and z.HitTestFilledArea(l, v.GetPosition(), int(r))}
    sized, through, kept, big = 0, 0, [], []
    for v in vias:
        pos = v.GetPosition()
        if v.GetNetname() != "GND" and v.GetViaType() != P.VIATYPE_THROUGH:
            land, drill = SIZE[P.VIATYPE_THROUGH]
            new = [l for l in cu if not v.IsOnLayer(l)]
            why = None
            for l in new:
                c = P.SHAPE_CIRCLE(pos, land // 2)
                for o in others + vias:
                    if o is v or o.GetNetCode() == v.GetNetCode() or not o.IsOnLayer(l):
                        continue
                    if o.GetClass() == "PCB_VIA" and o.GetViaType() != P.VIATYPE_THROUGH and not o.IsOnLayer(l):
                        continue
                    cl = max(o.GetOwnClearance(l), v.GetOwnClearance(l), MM(0.10))
                    if o.GetEffectiveShape(l).Collide(c, cl - 5):
                        why = f"{l} {o.GetClass()} {o.GetNetname()}"
                        break
                if why:
                    break
                if l in mask and any(d.GetEffectiveShape(d.GetLayer()).Collide(P.SHAPE_CIRCLE(pos, land // 2), MM(0.05))
                                     for d in mask[l]):
                    why = f"{l} mask opening"
                    break
            if not why:
                for o in vias:
                    if o is not v and (o.GetPosition() - pos).EuclideanNorm() < \
                            drill // 2 + o.GetDrillValue() // 2 + HOLE_TO_HOLE and o.GetNetCode() != v.GetNetCode():
                        why = f"hole {o.GetNetname()}"
                        break
            if why:
                kept.append((v.GetNetname(), round(P.ToMM(pos.x), 2), round(P.ToMM(pos.y), 2), why))
            else:
                v.SetViaType(P.VIATYPE_THROUGH)
                v.SetLayerPair(P.F_Cu, P.B_Cu)
                through += 1
        want = SIZE.get(v.GetViaType())
        if want and (v.GetWidth(v.TopLayer()) != want[0] or v.GetDrillValue() != want[1]):
            old = (v.GetWidth(v.TopLayer()), v.GetDrillValue())
            if zone_hits(v, old[0] // 2) - zone_hits(v, want[0] // 2):
                big.append((v.GetNetname(), round(P.ToMM(pos.x), 2), round(P.ToMM(pos.y), 2), P.ToMM(old[0])))
                continue
            v.SetWidth(want[0])
            v.SetDrill(want[1])
            sized += 1
    P.ZONE_FILLER(b).Fill(b.Zones())
    print(f"{through} non-GND vias made through, {sized} vias set to their type's size, {len(kept)} kept:")
    for k in kept:
        print("  kept", *k)
    print(f"{len(big)} vias keep a larger land: only it reaches their pour")
    for k in big:
        print("  large", *k)
    if "--dry-run" not in a:
        P.SaveBoard(path, b)
        print("saved")


if __name__ == "__main__":
    main()
