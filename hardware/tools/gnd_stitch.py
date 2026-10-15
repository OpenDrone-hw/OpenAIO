"""Add GND stitching vias to the HDI 1+6+1 board where every layer they cross has room.

Run with KiCad closed, using KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/gnd_stitch.py hardware/<board>.kicad_pcb [--buried 2.0] [--micro 1.2] [--fence 1.2] [--dry-run]

Three kinds, all GND, all at the net class sizes:
  - buried In1.Cu-In6.Cu (0.33 / 0.15) ties the L2 and L7 planes together: a grid of --buried mm pitch and a
    fence --fence mm apart, 0.6 mm inside the board outline. It must sit in the GND fill of In1.Cu and In6.Cu and
    clear every other-net track, via and pad on In1.Cu..In6.Cu; plane fills of other nets on In2..In5 yield to it.
  - microvia F.Cu-In1.Cu and In6.Cu-B.Cu (0.25 / 0.10) tie an outer GND pour to its plane: a grid of --micro mm
    pitch, at a buried via first (a stacked F.Cu-B.Cu column), else on the grid. It must sit in the GND fill of
    both layers it joins, away from every pad.
Every via keeps the copper clearance (0.09), hole clearance (0.18), hole spacing (0.30 different nets, 0.25
laser to buried, 0.20 same net), 0.40 from the board edge and out of rule areas that forbid vias. A candidate
that misses its grid point is tried up to 0.3 mm around it. Zones are refilled; the board is saved only if the
unconnected count does not rise. Run DRC afterwards and via_declutter.py on its report: it removes any GND via
DRC names in an error and every dangling one. Grid points that already have a GND via of the same span within
0.6 x pitch are skipped, so a rerun adds only what is missing. Last, every outer pour piece over 0.3 mm2 that
reaches its plane through one via gets a second one.
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
INNER = [pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.In5_Cu, pcbnew.In6_Cu]
ORDER = [F] + INNER + [B]
CLEAR, RF_CLEAR, HOLE_CLEAR, EDGE = MM(0.09), MM(0.15), MM(0.18), MM(0.40)
BURIED = (MM(0.33), MM(0.15))
MICRO = (MM(0.25), MM(0.10))


def span(top, bot):
    return ORDER[ORDER.index(top):ORDER.index(bot) + 1]


def arg(args, name, default):
    return float(args[args.index(name) + 1]) if name in args else default


def main():
    args = sys.argv[1:]
    path = args[0]
    dry = "--dry-run" in args
    pitch_b, pitch_m, fence = arg(args, "--buried", 2.0), arg(args, "--micro", 1.2), arg(args, "--fence", 1.2)
    board = pcbnew.LoadBoard(path)
    gnd = board.GetNetInfo().GetNetItem("GND")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.BuildConnectivity()
    base = board.GetConnectivity().GetUnconnectedCount(True)

    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    edges = [d.GetEffectiveShape(pcbnew.Edge_Cuts) for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    no_via = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    gnd_fill = {l: [z.GetFilledPolysList(l) for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"
                    and z.IsOnLayer(l)] for l in ORDER}
    items = [t for t in board.GetTracks()] + [p for fp in board.GetFootprints() for p in fp.Pads()]
    # A coarse spatial index: 1 mm buckets of bounding boxes.
    grid = {}

    def index(o):
        bb = o.GetBoundingBox()
        for i in range(bb.GetLeft() // MM(1), bb.GetRight() // MM(1) + 1):
            for j in range(bb.GetTop() // MM(1), bb.GetBottom() // MM(1) + 1):
                grid.setdefault((i, j), []).append(o)

    for o in items:
        index(o)

    def near(p, r):
        seen, out = set(), []
        for i in range((p.x - r) // MM(1), (p.x + r) // MM(1) + 1):
            for j in range((p.y - r) // MM(1), (p.y + r) // MM(1) + 1):
                for o in grid.get((i, j), []):
                    if id(o) not in seen:
                        seen.add(id(o))
                        out.append(o)
        return out

    def in_fill(p, r, layer):
        pts = [p] + [pcbnew.VECTOR2I(p.x + int(r * math.cos(a)), p.y + int(r * math.sin(a)))
                     for a in [k * math.pi / 4 for k in range(8)]]
        return any(all(poly.Contains(q) for q in pts) for poly in gnd_fill[layer])

    def ok(p, size, top, bot):
        land, drill = size
        r, hr = land // 2, drill // 2
        layers = span(top, bot)
        if not outline.Contains(p) or any(e.Collide(pcbnew.SHAPE_CIRCLE(p, r), EDGE) for e in edges):
            return False
        if not (in_fill(p, r, top) and in_fill(p, r, bot)):
            return False
        for z in no_via:
            if any(z.IsOnLayer(l) for l in layers) and z.Outline().Contains(p):
                return False
        circle, hole = pcbnew.SHAPE_CIRCLE(p, r), pcbnew.SHAPE_CIRCLE(p, hr)
        micro = top == F or bot == B
        for o in near(p, MM(0.8)):
            cls = o.GetClass()
            if cls == "PAD":
                for l in layers:
                    if o.IsOnLayer(l):
                        sh = o.GetEffectiveShape(l)
                        # never in or against a pad, own net included
                        if sh.Collide(circle, CLEAR + MM(0.05)) or sh.Collide(hole, HOLE_CLEAR):
                            return False
                if o.HasHole() and o.GetEffectiveHoleShape().Collide(circle, MM(0.30)):
                    return False
                continue
            if cls == "PCB_VIA":
                shared = set(span(o.TopLayer(), o.BottomLayer())) & set(layers)
                d = (o.GetPosition() - p).EuclideanNorm() - hr - o.GetDrillValue() // 2
                o_micro = o.GetViaType() == pcbnew.VIATYPE_MICROVIA
                if o.GetNetCode() == gnd.GetNetCode():
                    if shared and d < MM(0.20) and not (micro != o_micro and d < 0 and o.GetPosition() == p):
                        return False
                    continue
                if d < (MM(0.25) if micro != o_micro else MM(0.30)):
                    return False
                for l in shared:
                    if o.GetEffectiveShape(l).Collide(circle, CLEAR) or o.GetEffectiveShape(l).Collide(hole, HOLE_CLEAR):
                        return False
                continue
            if o.GetNetCode() == gnd.GetNetCode() or o.GetLayer() not in layers:
                continue
            gap = RF_CLEAR if o.GetNetClassName() == "RF" else CLEAR
            sh = o.GetEffectiveShape(o.GetLayer())
            if sh.Collide(circle, gap) or sh.Collide(hole, HOLE_CLEAR):
                return False
        return True

    def place(p, size, top, bot, kind):
        v = pcbnew.PCB_VIA(board)
        board.Add(v)
        v.SetPosition(p)
        v.SetNet(gnd)
        v.SetViaType(kind)
        v.SetLayerPair(top, bot)
        v.SetWidth(size[0])
        v.SetDrill(size[1])
        index(v)
        return v

    def crowded(p, top, bot, pitch):
        # a GND via of this span within 0.6 x pitch already does this grid point's job (rerun-safe)
        for o in near(p, int(pitch * 0.6)):
            if o.GetClass() == "PCB_VIA" and o.GetNetCode() == gnd.GetNetCode() and o.TopLayer() == top \
                    and o.BottomLayer() == bot and (o.GetPosition() - p).EuclideanNorm() < pitch * 0.6:
                return True
        return False

    def search(p, size, top, bot):
        if ok(p, size, top, bot):
            return p
        for rr in (0.1, 0.2, 0.3):
            for k in range(12):
                a = 2 * math.pi * k / 12
                q = pcbnew.VECTOR2I(p.x + int(MM(rr) * math.cos(a)), p.y + int(MM(rr) * math.sin(a)))
                if ok(q, size, top, bot):
                    return q
        return None

    bb = board.GetBoardEdgesBoundingBox()
    added = {"fence": [], "buried": [], "top": [], "bottom": []}

    # 1. Fence: points along the outline, inset 0.6 mm.
    inset = pcbnew.SHAPE_POLY_SET(outline)
    inset.Deflate(MM(0.6), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    for k in range(inset.OutlineCount()):
        ring = inset.Outline(k)
        n = ring.PointCount()
        walked, next_at = 0.0, 0.0
        for i in range(n):
            a, b = ring.CPoint(i), ring.CPoint((i + 1) % n)
            seg = math.dist((a.x, a.y), (b.x, b.y))
            while seg and next_at <= walked + seg:
                t = (next_at - walked) / seg
                p = pcbnew.VECTOR2I(int(a.x + (b.x - a.x) * t), int(a.y + (b.y - a.y) * t))
                q = None if crowded(p, I1, I6, MM(fence)) else search(p, BURIED, I1, I6)
                if q:
                    added["fence"].append(place(q, BURIED, I1, I6, pcbnew.VIATYPE_BURIED))
                next_at += MM(fence)
            walked += seg

    # 2. Buried grid.
    step = MM(pitch_b)
    y = bb.GetTop() + step // 2
    while y < bb.GetBottom():
        x = bb.GetLeft() + step // 2
        while x < bb.GetRight():
            p = pcbnew.VECTOR2I(x, y)
            q = None if crowded(p, I1, I6, step) else search(p, BURIED, I1, I6)
            if q:
                added["buried"].append(place(q, BURIED, I1, I6, pcbnew.VIATYPE_BURIED))
            x += step
        y += step

    # 3. Microvias: on every new buried via first (stacked column), then a grid.
    for v in added["fence"] + added["buried"]:
        p = v.GetPosition()
        if ok(p, MICRO, F, I1):
            added["top"].append(place(p, MICRO, F, I1, pcbnew.VIATYPE_MICROVIA))
        if ok(p, MICRO, I6, B):
            added["bottom"].append(place(p, MICRO, I6, B, pcbnew.VIATYPE_MICROVIA))
    step = MM(pitch_m)
    y = bb.GetTop() + step // 2
    while y < bb.GetBottom():
        x = bb.GetLeft() + step // 2
        while x < bb.GetRight():
            p = pcbnew.VECTOR2I(x, y)
            for top, bot, name in ((F, I1, "top"), (I6, B, "bottom")):
                q = None if crowded(p, top, bot, step) else search(p, MICRO, top, bot)
                if q:
                    added[name].append(place(q, MICRO, top, bot, pcbnew.VIATYPE_MICROVIA))
            x += step
        y += step

    # 4. Outer pour pieces (> 0.3 mm2) that reach their plane through one via get a second one.
    added["weak"] = []
    filler.Fill(board.Zones())
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != "GND":
            continue
        for outer, top, bot in ((F, F, I1), (B, I6, B)):
            if not z.IsOnLayer(outer):
                continue
            polys = z.GetFilledPolysList(outer)
            for i in range(polys.OutlineCount()):
                piece = pcbnew.SHAPE_POLY_SET()
                piece.AddOutline(polys.Outline(i))
                if piece.Area() < MM(1) * MM(1) * 0.3:
                    continue
                own = [o for o in board.GetTracks() if o.GetClass() == "PCB_VIA" and o.GetNetCode() == gnd.GetNetCode()
                       and o.IsOnLayer(outer) and piece.Contains(o.GetPosition())]
                if len(own) > 1:
                    continue
                box = polys.Outline(i).BBox()
                found = None
                y = box.GetTop()
                while y <= box.GetBottom() and not found:
                    x = box.GetLeft()
                    while x <= box.GetRight() and not found:
                        p = pcbnew.VECTOR2I(x, y)
                        if piece.Contains(p) and all((o.GetPosition() - p).EuclideanNorm() > MM(0.35) for o in own) \
                                and ok(p, MICRO, top, bot):
                            found = p
                        x += MM(0.1)
                    y += MM(0.1)
                if found:
                    added["weak"].append(place(found, MICRO, top, bot, pcbnew.VIATYPE_MICROVIA))

    filler.Fill(board.Zones())
    board.BuildConnectivity()
    after = board.GetConnectivity().GetUnconnectedCount(True)
    print(", ".join(f"{len(v)} {k}" for k, v in added.items()) + f"; unconnected {base} -> {after}")
    if after > base:
        sys.exit("a connection was lost; board not saved")
    if not dry:
        pcbnew.SaveBoard(path, board)
        print("saved")


if __name__ == "__main__":
    main()
