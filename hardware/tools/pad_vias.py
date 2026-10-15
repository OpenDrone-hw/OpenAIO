"""Fill SMD pads of GND and plane-fed power nets with as many vias as fit (filled laser via in pad, D107).

Run with KiCad closed, using KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/pad_vias.py hardware/<board>.kicad_pcb [--skip-net NAME ...] [--pour-net NAME ...] [--min-plane 50] [--dry-run]

A pad qualifies when its net is GND or has a plane (a zone over --min-plane mm2, default 50) on an inner layer:
  - GND pads get microvias into the GND plane next to their side (F.Cu-In1.Cu or In6.Cu-B.Cu, 0.25 / 0.10), on a
    0.30 mm grid;
  - other pads get stacks, microvia + buried In1.Cu-In6.Cu (0.33 / 0.15), on a 0.40 mm grid, reaching the plane.
Grid points are centred in the pad; a pad the grid leaves empty gets one via anywhere on a 0.05 mm grid inside
it. A land must lie 0.02 inside the pad copper. A via is kept when its land and
hole clear other-net copper on every layer it crosses (0.09 / 0.18, 0.30 to plated pad holes), the hole spacing
holds (0.20 same net, 0.25 laser to buried, 0.30 different nets) and it keeps 0.20 hole spacing to vias already in
the pad. --pour-net NAME also fills that net's outer-layer pours on the same grid (feeding a plane through
many vias instead of a few cuts the spreading loss around each one, loop_resistance.py). Measurement nets (Kelvin, BEMF, sense) never qualify: they have no plane. Zones are refilled; run DRC
and via_declutter.py on its report afterwards.
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


pcbnew = quiet_import()
MM = pcbnew.FromMM
F, B, I1, I6 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In6_Cu
ORDER = [F, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.In5_Cu, pcbnew.In6_Cu, B]
CLEAR, HOLE_CLEAR, PTH_CLEAR = MM(0.09), MM(0.18), MM(0.30)
MICRO, BURIED = (MM(0.25), MM(0.10)), (MM(0.33), MM(0.15))


def span(top, bot):
    return ORDER[ORDER.index(top):ORDER.index(bot) + 1]


def main():
    a = sys.argv[1:]
    path = a[0]
    skip = {a[i + 1] for i, x in enumerate(a) if x == "--skip-net"}
    dry = "--dry-run" in a
    min_plane = float(a[a.index("--min-plane") + 1]) if "--min-plane" in a else 50.0
    board = pcbnew.LoadBoard(path)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    planes = {}
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetFilledArea() > MM(1) * MM(1) * min_plane:
            for l in z.GetLayerSet().CuStack():
                if l in ORDER[1:-1]:
                    planes.setdefault(z.GetNetname(), set()).add(l)
    items = list(board.GetTracks()) + [p for fp in board.GetFootprints() for p in fp.Pads()]
    grid = {}

    def index(o):
        bb = o.GetBoundingBox()
        for i in range(bb.GetLeft() // MM(1), bb.GetRight() // MM(1) + 1):
            for j in range(bb.GetTop() // MM(1), bb.GetBottom() // MM(1) + 1):
                grid.setdefault((i, j), []).append(o)

    for o in items:
        index(o)

    def near(p):
        seen, out = set(), []
        for i in range(p.x // MM(1) - 1, p.x // MM(1) + 2):
            for j in range(p.y // MM(1) - 1, p.y // MM(1) + 2):
                for o in grid.get((i, j), []):
                    if id(o) not in seen:
                        seen.add(id(o))
                        out.append(o)
        return out

    def clear(p, size, top, bot, net, own):
        land, drill = size
        circle, hole = pcbnew.SHAPE_CIRCLE(p, land // 2), pcbnew.SHAPE_CIRCLE(p, drill // 2)
        layers = span(top, bot)
        micro = size == MICRO
        for o in near(p):
            if o is own:
                continue
            if o.GetClass() == "PCB_VIA":
                shared = set(span(o.TopLayer(), o.BottomLayer())) & set(layers)
                if not shared:
                    continue
                d = (o.GetPosition() - p).EuclideanNorm() - drill // 2 - o.GetDrillValue() // 2
                o_micro = o.GetViaType() == pcbnew.VIATYPE_MICROVIA
                if o.GetNetCode() == net:
                    if d < MM(0.20) and not (o.GetPosition() == p and o_micro != micro):
                        return False
                    continue
                if d < (MM(0.25) if o_micro != micro else MM(0.30)):
                    return False
                for l in shared:
                    sh = o.GetEffectiveShape(l)
                    if sh.Collide(circle, CLEAR) or sh.Collide(hole, HOLE_CLEAR):
                        return False
                continue
            if o.GetClass() == "PAD" and o.HasHole() and o.GetEffectiveHoleShape().Collide(circle, PTH_CLEAR):
                return False
            if o.GetNetCode() == net:
                continue
            for l in layers:
                if o.IsOnLayer(l):
                    sh = o.GetEffectiveShape(l)
                    if sh.Collide(circle, CLEAR) or sh.Collide(hole, HOLE_CLEAR):
                        return False
        return True

    def add(p, net, size, top, bot, kind):
        v = pcbnew.PCB_VIA(board)
        board.Add(v)
        v.SetPosition(p)
        v.SetNet(net)
        v.SetViaType(kind)
        v.SetLayerPair(top, bot)
        v.SetWidth(size[0])
        v.SetDrill(size[1])
        index(v)

    total, pads = 0, 0
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            name = pad.GetNetname()
            if pad.HasHole() or name in skip or name not in planes:
                continue
            outer = F if pad.IsOnLayer(F) else B if pad.IsOnLayer(B) else None
            if outer is None:
                continue
            gnd = name == "GND"
            mtop, mbot = (F, I1) if outer == F else (I6, B)
            if gnd and (mbot if outer == F else mtop) not in planes[name]:
                continue
            pitch, land = (MM(0.30), MICRO[0]) if gnd else (MM(0.40), MICRO[0])
            shape = pad.GetEffectiveShape(outer)
            bb = pad.GetBoundingBox()
            r = land // 2 + MM(0.02)
            nx = max(0, (bb.GetWidth() - 2 * r) // pitch)
            ny = max(0, (bb.GetHeight() - 2 * r) // pitch)
            x0 = bb.Centre().x - nx * pitch // 2
            y0 = bb.Centre().y - ny * pitch // 2
            n = 0
            points = [pcbnew.VECTOR2I(x0 + i * pitch, y0 + j * pitch) for j in range(ny + 1) for i in range(nx + 1)]
            # Where the centred grid finds nothing, any spot on a 0.05 mm grid inside the pad will do.
            fine = [pcbnew.VECTOR2I(bb.GetLeft() + i * MM(0.05), bb.GetTop() + j * MM(0.05))
                    for j in range(bb.GetHeight() // MM(0.05) + 1) for i in range(bb.GetWidth() // MM(0.05) + 1)]
            for candidates in (points, fine):
                for p in candidates:
                    if candidates is fine and n:
                        break
                    if not all(shape.Collide(pcbnew.VECTOR2I(p.x + int(r * math.cos(t)), p.y + int(r * math.sin(t))), 0)
                               for t in [k * math.pi / 4 for k in range(8)]):
                        continue
                    if gnd:
                        if clear(p, MICRO, mtop, mbot, pad.GetNetCode(), pad):
                            add(p, pad.GetNet(), MICRO, mtop, mbot, pcbnew.VIATYPE_MICROVIA)
                            n += 1
                    elif clear(p, MICRO, mtop, mbot, pad.GetNetCode(), pad) and clear(p, BURIED, I1, I6, pad.GetNetCode(), pad):
                        add(p, pad.GetNet(), MICRO, mtop, mbot, pcbnew.VIATYPE_MICROVIA)
                        add(p, pad.GetNet(), BURIED, I1, I6, pcbnew.VIATYPE_BURIED)
                        n += 1
            if n:
                total += n
                pads += 1
    # Pours: --pour-net NAME fills that net's outer-layer copper pours with the same vias, on the same grid.
    pour_nets = {a[i + 1] for i, x in enumerate(a) if x == "--pour-net"}
    in_pours = 0
    for z in list(board.Zones()):
        name = z.GetNetname()
        if z.GetIsRuleArea() or name not in pour_nets or name not in planes:
            continue
        gnd = name == "GND"
        for outer in (F, B):
            if not z.IsOnLayer(outer):
                continue
            mtop, mbot = (F, I1) if outer == F else (I6, B)
            if gnd and (mbot if outer == F else mtop) not in planes[name]:
                continue
            fill = z.GetFilledPolysList(outer)
            pitch = MM(0.30) if gnd else MM(0.40)
            r = MICRO[0] // 2 + MM(0.02)
            for k in range(fill.OutlineCount()):
                piece = pcbnew.SHAPE_POLY_SET()
                piece.AddOutline(fill.Outline(k))
                bb = fill.Outline(k).BBox()
                y = bb.GetTop() + r
                while y <= bb.GetBottom() - r:
                    x = bb.GetLeft() + r
                    while x <= bb.GetRight() - r:
                        p = pcbnew.VECTOR2I(x, y)
                        if all(piece.Contains(pcbnew.VECTOR2I(p.x + int(r * math.cos(t)), p.y + int(r * math.sin(t))))
                               for t in [j * math.pi / 4 for j in range(9)][:8]) and piece.Contains(p):
                            if gnd:
                                if clear(p, MICRO, mtop, mbot, z.GetNetCode(), None):
                                    add(p, z.GetNet(), MICRO, mtop, mbot, pcbnew.VIATYPE_MICROVIA)
                                    in_pours += 1
                            elif clear(p, MICRO, mtop, mbot, z.GetNetCode(), None) and clear(p, BURIED, I1, I6, z.GetNetCode(), None):
                                add(p, z.GetNet(), MICRO, mtop, mbot, pcbnew.VIATYPE_MICROVIA)
                                add(p, z.GetNet(), BURIED, I1, I6, pcbnew.VIATYPE_BURIED)
                                in_pours += 1
                        x += pitch
                    y += pitch
    filler.Fill(board.Zones())
    print(f"{total} vias / stacks in {pads} pads, {in_pours} in pours")
    if not dry:
        pcbnew.SaveBoard(path, board)
        print("saved")


if __name__ == "__main__":
    main()
