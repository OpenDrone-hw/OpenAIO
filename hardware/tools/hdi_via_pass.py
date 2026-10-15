"""Convert vias placed while routing into buildable HDI 1+6+1 stacks.

Run with KiCad closed, using KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/hdi_via_pass.py hardware/<board>.kicad_pcb [--allow-through] [--collapse] [--dry-run]

A via is kept when it is a microvia F.Cu-In1.Cu or In6.Cu-B.Cu at the net class microvia size,
a buried via In1.Cu-In6.Cu, or (with --allow-through) a through via. A via that already spans
F.Cu-In1.Cu or In6.Cu-B.Cu (a mechanical blind via from Option+V, or a microvia at the wrong
size) becomes a microvia in place. Every other via is replaced at the same position by
the smallest stack that joins the layers its tracks, pads and zones use: microvia F.Cu-In1.Cu,
buried In1.Cu-In6.Cu, microvia In6.Cu-B.Cu. Only copper on a layer the via spans counts. Sizes come from the board's net class
(read from the .kicad_pro, microvia and via size; a larger routed land is kept). Where the new stack is closer than the copper clearance to other-net
copper, it is moved up to 0.05 mm together with its track ends; larger conflicts are listed
and left for the owner. A stitching microvia (into its own net's L2/L7 plane, no track attached, not the
last via of a pad) that then sits within copper clearance or different-net hole spacing of
another net's via or track on a shared layer is removed. Zones are refilled. The script prints a report and saves the board unless --dry-run.

--collapse turns the board into its edit form: every stack (microvia, buried via and microvia of one net whose
lands overlap) becomes one via F.Cu-B.Cu (or F.Cu-In6.Cu / In1.Cu-B.Cu for a two-part stack) at the buried via
position, with a front/inner/back padstack carrying the stack's lands and the buried drill. In KiCad the stack
then moves as one object, and Drag (D) holds clearance to other nets while it moves; Move (M) never checks DRC.
A microvia that sat off the buried via keeps its copper through an outer-layer stub to the new position; when
its land would not clear other-net copper there, the stack is kept as it is and listed.
DRC is only meaningful in the fab form: the next normal run of this script rebuilds the stacks from the
padstack sizes.
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


pcbnew = quiet_import()
F, B, I1, I6 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In6_Cu
INNER = {pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.In5_Cu}
MAX_NUDGE = pcbnew.FromMM(0.05)
CLEARANCE = pcbnew.FromMM(0.09)
HOLE_GAP = pcbnew.FromMM(0.30)
HOLE_CLEARANCE = pcbnew.FromMM(0.18)


def legal(v, allow_through, micro):
    t, top, bot = v.GetViaType(), v.TopLayer(), v.BottomLayer()
    if t == pcbnew.VIATYPE_MICROVIA:
        # The land is DRC's to judge (a scoped rule may allow a smaller one, D21 U14); only span and drill matter.
        return (top, bot) in ((F, I1), (I6, B)) and v.GetDrillValue() == micro[1]
    if t == pcbnew.VIATYPE_BURIED:
        return (top, bot) == (I1, I6)
    if t == pcbnew.VIATYPE_THROUGH:
        return allow_through
    return False


def used_layers(board, v, tracks):
    # Copper overlap counts as a connection, as in KiCad's connectivity: a track end or body, a pad
    # edge or a zone fill touching the via land on a layer the via spans.
    p, r, layers = v.GetPosition(), v.GetWidth(v.TopLayer()) // 2, set()
    for t in tracks:
        if t.GetNetCode() == v.GetNetCode() and v.IsOnLayer(t.GetLayer()) and seg_dist(p, t.GetStart(), t.GetEnd()) <= r + t.GetWidth() / 2:
            layers.add(t.GetLayer())
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == v.GetNetCode() and pad.HitTest(p, int(r)):
                layers |= {l for l in (F, B) if pad.IsOnLayer(l) and v.IsOnLayer(l)}
    for z in board.Zones():
        if z.GetNetCode() == v.GetNetCode() and not z.GetIsRuleArea():
            layers |= {l for l in z.GetLayerSet().CuStack() if v.IsOnLayer(l) and z.HitTestFilledArea(l, p, int(r))}
    span = {v.TopLayer(), v.BottomLayer()}
    if not layers - {F, B}:
        layers |= span & INNER  # a via ending on an inner layer was placed to route there next
    return layers


def plan(layers):
    parts = []
    if F in layers:
        parts.append("micro_top")
    if layers & INNER or (F in layers and B in layers):
        parts.append("buried")
    if B in layers:
        parts.append("micro_bot")
    return parts or ["buried"]


def nearest_gap(board, pos, net, radius, layers):
    worst = None
    for t in board.GetTracks():
        if t.GetNetCode() == net or t.GetClass() == "PCB_VIA":
            continue
        if t.GetLayer() not in layers:
            continue
        a, b = t.GetStart(), t.GetEnd()
        dx, dy = b.x - a.x, b.y - a.y
        L = dx * dx + dy * dy
        u = max(0.0, min(1.0, ((pos.x - a.x) * dx + (pos.y - a.y) * dy) / L)) if L else 0.0
        nx, ny = a.x + u * dx, a.y + u * dy
        gap = math.dist((nx, ny), (pos.x, pos.y)) - radius - t.GetWidth() / 2
        if worst is None or gap < worst[0]:
            worst = (gap, nx, ny, t)
    return worst


def shared(a, b):
    return any(a.IsOnLayer(l) and b.IsOnLayer(l) for l in (F, I1, *sorted(INNER), I6, B))


def seg_dist(p, a, b):
    dx, dy = b.x - a.x, b.y - a.y
    L = dx * dx + dy * dy
    u = max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L)) if L else 0.0
    return math.dist((a.x + u * dx, a.y + u * dy), (p.x, p.y))


def clear_stitching(board):
    """Remove track-free vias that collide with another net's via or track."""
    items = list(board.GetTracks())
    vias = [t for t in items if t.GetClass() == "PCB_VIA"]
    tracks = [t for t in items if t.GetClass() != "PCB_VIA"]
    planes = {(z.GetNetCode(), l) for z in board.Zones() if not z.GetIsRuleArea() for l in (I1, I6) if z.IsOnLayer(l)}
    pads = [pad for fp in board.GetFootprints() for pad in fp.Pads()]
    def on_pad(v):
        r = int(v.GetWidth(v.TopLayer()) // 2)
        return [pad for pad in pads if pad.GetNetCode() == v.GetNetCode() and pad.HitTest(v.GetPosition(), r)]
    def stitch(v):
        # A microvia into its own net's L2/L7 plane, with no track attached.
        r = v.GetWidth(v.TopLayer()) / 2
        inner = I1 if v.TopLayer() == F else I6
        if v.GetViaType() != pcbnew.VIATYPE_MICROVIA or (v.GetNetCode(), inner) not in planes:
            return False
        return not any(seg_dist(v.GetPosition(), t.GetStart(), t.GetEnd()) <= r + t.GetWidth() / 2
                       for t in tracks if t.GetNetCode() == v.GetNetCode() and v.IsOnLayer(t.GetLayer()))
    def last_on_pad(v):
        # Never strip the only via of a pad.
        return any(sum(1 for o in vias if id(o) not in gone and o.GetNetCode() == v.GetNetCode()
                       and pad.HitTest(o.GetPosition(), int(o.GetWidth(o.TopLayer()) // 2))) <= 1 for pad in on_pad(v))
    gone = set()
    for v in vias:
        if not stitch(v):
            continue
        p, r = v.GetPosition(), v.GetWidth(v.TopLayer()) / 2
        hit = False
        for o in vias:
            if o is v or id(o) in gone or o.GetNetCode() == v.GetNetCode() or not shared(v, o):
                continue
            d = (o.GetPosition() - p).EuclideanNorm()
            if d < r + o.GetWidth(o.TopLayer()) / 2 + CLEARANCE or d < (v.GetDrillValue() + o.GetDrillValue()) / 2 + HOLE_GAP:
                hit = True
                break
        if not hit:
            for t in tracks:
                if t.GetNetCode() != v.GetNetCode() and v.IsOnLayer(t.GetLayer()) and seg_dist(p, t.GetStart(), t.GetEnd()) < r + t.GetWidth() / 2 + CLEARANCE:
                    hit = True
                    break
        if hit and not last_on_pad(v):
            gone.add(id(v))
            board.Remove(v)
    return len(gone)


def collapse(board):
    """Replace each HDI stack with one via carrying the stack's lands in a front/inner/back padstack."""
    items = list(board.GetTracks())
    vias = [t for t in items if t.GetClass() == "PCB_VIA"]
    tracks = [t for t in items if t.GetClass() != "PCB_VIA"]
    buried = [v for v in vias if v.GetViaType() == pcbnew.VIATYPE_BURIED]
    micros = [v for v in vias if v.GetViaType() == pcbnew.VIATYPE_MICROVIA]
    claims = {}
    for m in micros:
        # The nearest same-net buried via whose land overlaps this microvia's land.
        best = None
        for q in buried:
            if q.GetNetCode() != m.GetNetCode():
                continue
            d = (q.GetPosition() - m.GetPosition()).EuclideanNorm()
            if d < (q.GetWidth(I1) + m.GetWidth(m.TopLayer())) / 2 and (best is None or d < best[0]):
                best = (d, q)
        if best:
            side = "top" if m.TopLayer() == F else "bot"
            prev = claims.get((id(best[1]), side))
            if prev is None or best[0] < prev[0]:
                claims[(id(best[1]), side)] = (best[0], m)
    pads = [pad for fp in board.GetFootprints() for pad in fp.Pads()]

    def outer_clear(m, pos, outer):
        # The microvia land and hole moved to pos must clear other-net copper on its outer layer.
        land = pcbnew.SHAPE_CIRCLE(pos, m.GetWidth(outer) // 2)
        hole = pcbnew.SHAPE_CIRCLE(pos, m.GetDrillValue() // 2)
        for o in items + pads:
            if o is m or o.GetNetCode() == m.GetNetCode() or not o.IsOnLayer(outer):
                continue
            shape = o.GetEffectiveShape(outer)
            if shape.Collide(land, CLEARANCE) or shape.Collide(hole, HOLE_CLEARANCE):
                return False
        return True

    done, stubs, offset = 0, 0, []
    for q in buried:
        top = claims.get((id(q), "top"))
        bot = claims.get((id(q), "bot"))
        if not top and not bot:
            continue
        pos = q.GetPosition()
        blocked = [part[1] for part, outer in ((top, F), (bot, B)) if part and (part[1].GetPosition() - pos).EuclideanNorm() > 10
                   and not outer_clear(part[1], pos, outer)]
        if blocked:
            offset.append(f"{q.GetNetname()} {pcbnew.ToMM(pos.x):.2f},{pcbnew.ToMM(pos.y):.2f}")
            continue
        n = pcbnew.PCB_VIA(board)
        board.Add(n)
        n.SetPosition(pos)
        n.SetNet(q.GetNet())
        n.SetViaType(pcbnew.VIATYPE_THROUGH if top and bot else pcbnew.VIATYPE_BLIND)
        n.SetLayerPair(F if top else I1, B if bot else I6)
        ps = n.Padstack()
        ps.SetMode(pcbnew.PADSTACK.MODE_FRONT_INNER_BACK)
        for layer, w in ((F, top[1].GetWidth(F) if top else q.GetWidth(I1)), (I1, q.GetWidth(I1)),
                         (B, bot[1].GetWidth(B) if bot else q.GetWidth(I1))):
            ps.SetSize(pcbnew.VECTOR2I(w, w), layer)
        n.SetPadstack(ps)
        n.SetDrill(q.GetDrillValue())
        for part, outer in ((top, F), (bot, B)):
            if not part:
                continue
            m = part[1]
            p = m.GetPosition()
            if (p - pos).EuclideanNorm() > 10:
                w = max([t.GetWidth() for t in tracks if t.GetNetCode() == m.GetNetCode() and t.GetLayer() == outer
                         and ((t.GetStart() - p).EuclideanNorm() < 10 or (t.GetEnd() - p).EuclideanNorm() < 10)]
                        or [pcbnew.FromMM(0.15)])
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(p)
                t.SetEnd(pos)
                t.SetWidth(min(w, m.GetWidth(outer)))
                t.SetLayer(outer)
                t.SetNet(m.GetNet())
                board.Add(t)
                stubs += 1
            board.Remove(m)
        board.Remove(q)
        done += 1
    return done, stubs, offset


def main():
    args = sys.argv[1:]
    path = [a for a in args if not a.startswith("--")][0]
    allow_through, dry = "--allow-through" in args, "--dry-run" in args
    board = pcbnew.LoadBoard(path)
    if "--collapse" in args:
        before = len([t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"])
        done, stubs, offset = collapse(board)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        print(f"{before} vias; {done} stacks collapsed to one via each, {stubs} outer stubs for offset microvias")
        for where in offset:
            print(f"  kept as a stack: {where} (its microvia sits off the buried via to clear outer-layer copper)")
        if not dry:
            pcbnew.SaveBoard(path, board)
            print("saved")
        return
    # KiCad 10 Python does not wrap NETCLASS, so via sizes come from the project file.
    pro = json.load(open(os.path.splitext(path)[0] + ".kicad_pro"))
    classes = {c["name"]: c for c in pro["net_settings"]["classes"]}
    tracks = [t for t in board.GetTracks() if t.GetClass() != "PCB_VIA"]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    def sizes(v):
        cls = classes.get(v.GetNetClassName(), classes["Default"])
        return ((pcbnew.FromMM(cls["microvia_diameter"]), pcbnew.FromMM(cls["microvia_drill"])),
                (pcbnew.FromMM(cls["via_diameter"]), pcbnew.FromMM(cls["via_drill"])))
    bad = [v for v in vias if not legal(v, allow_through, sizes(v)[0])]
    print(f"{len(vias)} vias, {len(bad)} to convert")
    left, retyped = [], 0
    for v in bad:
        pos, net = v.GetPosition(), v.GetNet()
        micro, mech = sizes(v)
        # Keep the routed land when it is larger, so overlap connections made while routing survive. A collapsed
        # stack carries its lands per layer: front = top microvia, inner = buried via, back = bottom microvia.
        top = (max(micro[0], v.GetWidth(v.TopLayer())), micro[1])
        bot = (max(micro[0], v.GetWidth(v.BottomLayer())), micro[1])
        inner = I1 if v.IsOnLayer(I1) else v.TopLayer()
        mech = (max(mech[0], v.GetWidth(inner)), mech[1])
        micro = top
        if (v.TopLayer(), v.BottomLayer()) in ((F, I1), (I6, B)):
            v.SetViaType(pcbnew.VIATYPE_MICROVIA)
            v.SetWidth(micro[0])
            v.SetDrill(micro[1])
            retyped += 1
            continue
        parts = plan(used_layers(board, v, tracks))
        new = []
        for p in parts:
            n = pcbnew.PCB_VIA(board)
            board.Add(n)
            n.SetPosition(pos)
            n.SetNet(net)
            if p == "buried":
                n.SetViaType(pcbnew.VIATYPE_BURIED)
                n.SetLayerPair(I1, I6)
                n.SetWidth(mech[0])
                n.SetDrill(mech[1])
            else:
                n.SetViaType(pcbnew.VIATYPE_MICROVIA)
                n.SetLayerPair(*((F, I1) if p == "micro_top" else (I6, B)))
                n.SetWidth((top if p == "micro_top" else bot)[0])
                n.SetDrill(micro[1])
            new.append(n)
        label = f"{v.GetNetname()} {board.GetLayerName(v.TopLayer())}-{board.GetLayerName(v.BottomLayer())}"
        board.Remove(v)
        if "buried" in parts:
            g = nearest_gap(board, pos, net.GetNetCode(), mech[0] / 2, INNER | {I1, I6})
            if g and g[0] < CLEARANCE:
                need = CLEARANCE - g[0] + pcbnew.FromMM(0.005)
                if need <= MAX_NUDGE:
                    d = math.dist((g[1], g[2]), (pos.x, pos.y)) or 1
                    newp = pcbnew.VECTOR2I(int(pos.x + (pos.x - g[1]) / d * need), int(pos.y + (pos.y - g[2]) / d * need))
                    for n in new:
                        n.SetPosition(newp)
                    for t in tracks:
                        if t.GetNetCode() == net.GetNetCode():
                            if (t.GetStart() - pos).EuclideanNorm() < 10:
                                t.SetStart(newp)
                            if (t.GetEnd() - pos).EuclideanNorm() < 10:
                                t.SetEnd(newp)
                    label += f" (moved {pcbnew.ToMM(need):.3f} mm)"
                else:
                    left.append(f"{label}: buried pad {pcbnew.ToMM(g[0]):.3f} mm from {g[3].GetNetname()} on {board.GetLayerName(g[3].GetLayer())}")
        print(f"  {label} -> {' + '.join(parts)}")
    print(f"{retyped} retyped in place to microvias")
    print(f"{clear_stitching(board)} stitching vias removed for clashing with another net")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    for item in left:
        print("OWNER:", item)
    if not dry:
        pcbnew.SaveBoard(path, board)
        print("saved")


if __name__ == "__main__":
    main()
