"""Reroute the In2.Cu / In5.Cu signal tracks between the vias that already exist: short, and noisy apart from sensitive.

Run with KiCad closed, using KiCad's bundled Python (numpy, PIL):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/inner_router.py hardware/<board>.kicad_pcb [--grid 0.05] [--passes 3] [--dry-run]

What it routes. Every net with tracks on In2.Cu or In5.Cu, except USB (a matched pair), RF and power nets. The
tracks of one net that touch each other form a cluster; the vias and plated pad holes a cluster touches are its
terminals, and the new route joins exactly those terminals. No via is added, moved or removed: buried vias reach
both In2.Cu and In5.Cu, so a route may use either layer and change layer only at one of its own vias.

How. Octilinear A* on a --grid mm mesh. A cell is open to a net when its centre keeps copper clearance (0.09; 0.30
from plated pad holes on inner layers, 0.15 next to RF) plus both half widths from every other net's via, pad, fixed
track and already routed track, and 0.20 from the board edge. Cost per mm:
  - layer: sensitive nets prefer In2.Cu (between the L2 GND plane and the quiet +3.3V plane), noisy nets In5.Cu
    (between +BATT and the L7 GND plane, beside the switching they come from), others In2.Cu slightly, since a track
    on In5.Cu cuts the +5V planes;
  - coupling: a sensitive net within 0.5 mm of a noisy route on the same layer pays extra, and the other way round;
  - a small cost per bend.
Improvement, not rip-up-all: starting from the board's own routing, each connection in turn (sensitive, noisy, then the
rest) is rerouted with every other track in place and kept only when it scores lower (length x layer cost + coupling +
bends) and only if the zones still connect everything after a refill (a route on In5.Cu must not split the +5V
planes); --passes rounds (default 3) or until nothing improves. Every state in between is a complete board. Run DRC
afterwards: the script prints total length and coupled length before and after.
"""
import heapq
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
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

MM = pcbnew.FromMM
IN2, IN5 = pcbnew.In2_Cu, pcbnew.In5_Cu
LAYERS = (IN2, IN5)
CLEAR, RF_CLEAR, PTH_CLEAR, EDGE, MARGIN = 0.09, 0.15, 0.30, 0.20, 0.03
NEAR = 0.5  # coupling distance, mm
FIXED_CLASSES = ("USB", "RF", "Power", "VBAT", "GND")
NOISY = re.compile(r"(_PWM|_COM|PHASE_|/MOTOR\d|BUZZER|LED_STRIP|AMP_PWM|SCK|_CLK|CLKIN|U2_SW)")
SENSITIVE_CLASSES = ("Analog",)
SENSITIVE = re.compile(r"(XIN|XOUT|PA_VREF|VREG_RADIO)")


def kind(net, cls):
    if cls in SENSITIVE_CLASSES or SENSITIVE.search(net):
        return "sensitive"
    if cls in ("Gate", "Phase") or NOISY.search(net):
        return "noisy"
    return "neutral"


LAYER_COST = {"sensitive": (1.0, 1.6), "noisy": (1.3, 1.0), "neutral": (1.0, 1.15)}
COUPLE_COST = 3.0  # extra per mm inside NEAR of an incompatible route
BEND_COST = 0.05  # mm-equivalent per 45 degree turn


class Grid:
    def __init__(self, board, h):
        self.b = board
        self.h = MM(h)
        bb = board.GetBoardEdgesBoundingBox()
        self.x0, self.y0 = bb.GetLeft(), bb.GetTop()
        self.nx, self.ny = bb.GetWidth() // self.h + 2, bb.GetHeight() // self.h + 2

    def cell(self, p):
        return int(round((p.x - self.x0) / self.h)), int(round((p.y - self.y0) / self.h))

    def point(self, x, y):
        return pcbnew.VECTOR2I(self.x0 + x * self.h, self.y0 + y * self.h)

    def mask(self, polys):
        img = Image.new("1", (self.nx, self.ny), 0)
        d = ImageDraw.Draw(img)
        for i in range(polys.OutlineCount()):
            o = polys.Outline(i)
            pts = [((o.CPoint(k).x - self.x0) / self.h, (o.CPoint(k).y - self.y0) / self.h) for k in range(o.PointCount())]
            if len(pts) > 2:
                d.polygon(pts, fill=1)
        return np.array(img, dtype=bool).T


def segments_of(path):
    """Cell path -> list of straight runs (start, end) merging collinear steps."""
    runs, start, prev, d = [], path[0], path[0], None
    for c in path[1:]:
        step = (c[1] - prev[1], c[2] - prev[2], c[0] - prev[0])
        if d is not None and step != d:
            runs.append((start, prev))
            start = prev
        d = step
        prev = c
    runs.append((start, prev))
    return [r for r in runs if r[0][0] == r[1][0] and r[0] != r[1]]


def main():
    a = sys.argv[1:]
    path = a[0]
    h = float(a[a.index("--grid") + 1]) if "--grid" in a else 0.05
    dry = "--dry-run" in a
    board = pcbnew.LoadBoard(path)
    G = Grid(board, h)
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetLayer() in LAYERS]
    vias = [v for v in board.GetTracks() if v.GetClass() == "PCB_VIA"]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    routable = [t for t in tracks if t.GetNetClassName() not in FIXED_CLASSES]
    fixed = [t for t in tracks if t.GetNetClassName() in FIXED_CLASSES]

    # Terminals: clusters of a net's routable tracks and the vias / plated holes they touch.
    def touches(item, t):
        if item.GetClass() == "PCB_VIA":
            r = item.GetWidth(t.GetLayer()) // 2
            return any((item.GetPosition() - e).EuclideanNorm() <= r for e in (t.GetStart(), t.GetEnd()))
        return any(item.HitTest(e) for e in (t.GetStart(), t.GetEnd()))

    by_net = {}
    for t in routable:
        by_net.setdefault(t.GetNetCode(), []).append(t)
    jobs = []  # (netcode, name, cls, width, [terminal items])
    for code, ts in by_net.items():
        parent = list(range(len(ts)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        ends = [(t.GetStart(), t.GetEnd()) for t in ts]
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                if any((p - q).EuclideanNorm() < MM(0.01) for p in ends[i] for q in ends[j]):
                    parent[find(i)] = find(j)
        term_items = [v for v in vias if v.GetNetCode() == code and v.IsOnLayer(IN2) and v.IsOnLayer(IN5)]
        term_items += [p for p in pads if p.GetNetCode() == code and p.HasHole()]
        clusters = {}
        for i, t in enumerate(ts):
            clusters.setdefault(find(i), []).append(t)
        for cl in clusters.values():
            terms = [it for it in term_items if any(touches(it, t) for t in cl)]
            uniq = []
            for it in terms:
                if all((it.GetPosition() - u.GetPosition()).EuclideanNorm() > MM(0.05) for u in uniq):
                    uniq.append(it)
            if len(uniq) >= 2:
                t0 = cl[0]
                w = 0.15 if t0.GetNetClassName() == "Gate" else 0.10
                jobs.append((code, t0.GetNetname(), kind(t0.GetNetname(), t0.GetNetClassName()), w, uniq, cl))
    widths = sorted({j[3] for j in jobs})
    in_jobs = {id(t) for j in jobs for t in j[5]}
    fixed = [t for t in tracks if id(t) not in in_jobs]  # USB, RF, power and stubs that join fewer than two terminals

    def metrics(segs):
        """segs: list of (netcode, kind, layer, start, end, width). Returns (length mm, coupled mm)."""
        length = sum(pcbnew.ToMM((e - s).EuclideanNorm()) for _, _, _, s, e, _ in segs)
        coupled = 0.0
        noisy = [(l, s, e) for _, k, l, s, e, _ in segs if k == "noisy"]
        for _, k, l, s, e, _ in segs:
            if k != "sensitive":
                continue
            n = max(1, int(pcbnew.ToMM((e - s).EuclideanNorm()) / 0.1))
            for i in range(n):
                f = (i + 0.5) / n
                p = pcbnew.VECTOR2I(int(s.x + (e.x - s.x) * f), int(s.y + (e.y - s.y) * f))
                for nl, ns, ne in noisy:
                    if nl == l and pcbnew.SHAPE_SEGMENT(ns, ne, 0).Collide(p, MM(NEAR)):
                        coupled += pcbnew.ToMM((e - s).EuclideanNorm()) / n
                        break
        return length, coupled

    before = metrics([(t.GetNetCode(), kind(t.GetNetname(), t.GetNetClassName()), t.GetLayer(), t.GetStart(), t.GetEnd(),
                       t.GetWidth()) for t in routable])

    # Static obstacles per layer and width: owner net code, -1 free, -2 closed to every net.
    def static_owner(layer, w):
        own = np.full((G.nx, G.ny), -1, dtype=np.int32)

        def paint(polys, code):
            m = G.mask(polys)
            free = own == -1
            own[m & free] = code
            own[m & ~free & (own != code)] = -2

        for v in vias:
            if v.IsOnLayer(layer):
                ps = pcbnew.SHAPE_POLY_SET()
                gap = RF_CLEAR if v.GetNetClassName() == "RF" else CLEAR
                v.TransformShapeToPolygon(ps, layer, MM(gap + w / 2 + MARGIN), MM(0.005), pcbnew.ERROR_OUTSIDE)
                paint(ps, v.GetNetCode())
        for p in pads:
            if p.IsOnLayer(layer) or p.HasHole():
                ps = pcbnew.SHAPE_POLY_SET()
                if p.HasHole():
                    r = p.GetDrillSize().x // 2 + MM(PTH_CLEAR + w / 2 + MARGIN)
                    pcbnew.SHAPE_SEGMENT(p.GetPosition(), p.GetPosition(), 2 * r).TransformToPolygon(ps, MM(0.005), pcbnew.ERROR_OUTSIDE)
                else:
                    gap = RF_CLEAR if p.GetNetClassName() == "RF" else CLEAR
                    p.TransformShapeToPolygon(ps, layer, MM(gap + w / 2 + MARGIN), MM(0.005), pcbnew.ERROR_OUTSIDE)
                paint(ps, p.GetNetCode())
        for t in fixed:
            if t.GetLayer() == layer:
                gap = RF_CLEAR if t.GetNetClassName() == "RF" else CLEAR
                ps = pcbnew.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(ps, layer, MM(gap + w / 2 + MARGIN), MM(0.005), pcbnew.ERROR_OUTSIDE)
                paint(ps, t.GetNetCode())
        for z in board.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.IsOnLayer(layer):
                paint(z.Outline(), -2)
        outline = pcbnew.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(outline, False)
        outline.Deflate(MM(EDGE + w / 2 + MARGIN), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.005))
        own[~G.mask(outline)] = -2
        return own

    static = {(l, w): static_owner(l, w) for l in LAYERS for w in widths}
    print(f"{len(jobs)} connections in {len({j[0] for j in jobs})} nets; before: {before[0]:.1f} mm, "
          f"{before[1]:.1f} mm sensitive within {NEAR} mm of noisy")

    DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    def score(segs, k, others):
        """Cost of one net's segments [(layer, s, e)] given the other nets' segments [(kind, layer, s, e)]."""
        lc = LAYER_COST[k]
        cost = 0.0
        bad = {"sensitive": "noisy", "noisy": "sensitive"}.get(k)
        for l, s, e in segs:
            L = pcbnew.ToMM((e - s).EuclideanNorm())
            cost += L * lc[LAYERS.index(l)]
            if bad:
                n = max(1, int(L / 0.1))
                for i in range(n):
                    f = (i + 0.5) / n
                    p = pcbnew.VECTOR2I(int(s.x + (e.x - s.x) * f), int(s.y + (e.y - s.y) * f))
                    if any(ok_ == bad and ol == l and pcbnew.SHAPE_SEGMENT(os_, oe, 0).Collide(p, MM(NEAR))
                           for ok_, ol, os_, oe in others):
                        cost += L / n * COUPLE_COST
        return cost + BEND_COST * max(0, len(segs) - 1)

    def draw(segs, grow):
        """Union mask of segments [(layer, s, e, width)] grown by grow mm, per layer."""
        out = {}
        for l in LAYERS:
            img = Image.new("1", (G.nx, G.ny), 0)
            d = ImageDraw.Draw(img)
            for sl, s, e, w in segs:
                if sl != l:
                    continue
                r = (w / 2 + MM(grow)) / G.h
                x1, y1 = (s.x - G.x0) / G.h, (s.y - G.y0) / G.h
                x2, y2 = (e.x - G.x0) / G.h, (e.y - G.y0) / G.h
                d.line([(x1, y1), (x2, y2)], fill=1, width=max(1, int(math.ceil(2 * r))))
                d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=1)
                d.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], fill=1)
            out[l] = np.array(img, dtype=bool).T
        return out

    def astar(code, k, w, terms, blocked, near):
        li_cost = LAYER_COST[k]
        other = {"sensitive": "noisy", "noisy": "sensitive"}.get(k)
        open_ = {}
        for li, l in enumerate(LAYERS):
            st = static[(l, w)]
            open_[li] = ((st == -1) | (st == code)) & ~blocked[l]
        term_cells = [G.cell(t.GetPosition()) for t in terms]
        term_set = set(term_cells)
        for li in range(2):
            for c in term_cells:
                open_[li][c] = True
        tree = {(li, *term_cells[0]) for li in range(2)}
        paths = []
        for tc in term_cells[1:]:
            if {(li, *tc) for li in range(2)} & tree:
                continue
            sample = list({(c[1], c[2]) for c in tree})
            sample = sample[:: max(1, len(sample) // 16)]

            def hfun(x, y):
                return min(max(abs(x - a_), abs(y - b_)) + 0.414 * min(abs(x - a_), abs(y - b_)) for a_, b_ in sample)

            g, came, pq = {}, {}, []
            for li in range(2):
                st = (li, *tc)
                g[st] = 0.0
                heapq.heappush(pq, (hfun(*tc) * h * min(li_cost), 0.0, st, None))
            found = None
            while pq:
                f, gc, c, d = heapq.heappop(pq)
                if gc > g.get(c, 1e18):
                    continue
                if c in tree:
                    found = c
                    break
                li, x, y = c
                for dx, dy in DIRS:
                    nx_, ny_ = x + dx, y + dy
                    if not (0 <= nx_ < G.nx and 0 <= ny_ < G.ny) or not open_[li][nx_, ny_]:
                        continue
                    if dx and dy and not (open_[li][x + dx, y] or open_[li][x, y + dy]):
                        continue
                    unit = (1.414 if dx and dy else 1.0) * h
                    step = unit * li_cost[li]
                    if other and near[other][LAYERS[li]][nx_, ny_]:
                        step += unit * COUPLE_COST
                    if d is not None and d != (dx, dy):
                        step += BEND_COST
                    n = (li, nx_, ny_)
                    ng = gc + step
                    if ng < g.get(n, 1e18):
                        g[n], came[n] = ng, c
                        heapq.heappush(pq, (ng + hfun(nx_, ny_) * h * min(li_cost), ng, n, (dx, dy)))
                if (x, y) in term_set:
                    n = (1 - li, x, y)
                    if gc < g.get(n, 1e18):
                        g[n], came[n] = gc, c
                        heapq.heappush(pq, (f, gc, n, None))
            if found is None:
                return None
            cpath = [found]
            while cpath[-1] in came:
                cpath.append(came[cpath[-1]])
            paths.append(cpath)
            tree |= set(cpath)
        snap = {G.cell(t.GetPosition()): t.GetPosition() for t in terms}
        segs = []
        for cpath in paths:
            for s_, e_ in segments_of(cpath):
                sc, ec = (s_[1], s_[2]), (e_[1], e_[2])
                segs.append((LAYERS[s_[0]], snap.get(sc, G.point(*sc)), snap.get(ec, G.point(*ec))))
        return segs

    # Current state: every job's segments (start from the board's own routing).
    state = {}
    for j in jobs:
        state[id(j)] = [(t.GetLayer(), t.GetStart(), t.GetEnd()) for t in j[5]]
    jw = {id(j): MM(j[3]) for j in jobs}
    orig_w = {id(j): {(t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y): t.GetWidth() for t in j[5]}
              for j in jobs}
    groups = {"sensitive": 0, "noisy": 1, "neutral": 2}
    order = sorted(jobs, key=lambda j: groups[j[2]])
    passes = int(a[a.index("--passes") + 1]) if "--passes" in a else 3
    changed = set()
    filler = pcbnew.ZONE_FILLER(board)

    def unconnected():
        filler.Fill(board.Zones())
        board.BuildConnectivity()
        return board.GetConnectivity().GetUnconnectedCount(True)

    base = unconnected()
    live = {id(j): list(j[5]) for j in jobs}  # the board track objects of each connection now

    def put(j, segs):
        for t in live[id(j)]:
            board.Remove(t)
        made = []
        for l, s_, e_ in segs:
            t = pcbnew.PCB_TRACK(board)
            t.SetLayer(l)
            t.SetNet(j[5][0].GetNet())
            t.SetWidth(MM(j[3]))
            t.SetStart(s_)
            t.SetEnd(e_)
            board.Add(t)
            made.append(t)
        old_live = live[id(j)]
        live[id(j)] = made
        return old_live

    rejected = 0
    for rnd in range(passes):
        improved = 0
        for j in order:
            code, name, k, w, terms, cl = j
            others = [(oj[2], l, s_, e_) for oj in jobs if oj is not j for (l, s_, e_) in state[id(oj)]]
            other_segs = [(l, s_, e_, orig_w[id(oj)].get((l, s_.x, s_.y, e_.x, e_.y), jw[id(oj)]))
                          for oj in jobs if oj is not j and oj[0] != code for (l, s_, e_) in state[id(oj)]]
            blocked = draw(other_segs, CLEAR + w / 2 + MARGIN)
            near = {kk: draw([(l, s_, e_, MM(0.0)) for ok_, l, s_, e_ in others if ok_ == kk], NEAR)
                    for kk in ("noisy", "sensitive")}
            old = score(state[id(j)], k, others)
            segs = astar(code, k, w, terms, blocked, near)
            if segs is None:
                continue
            new_ = score(segs, k, others)
            if new_ < old - 0.05:
                previous = put(j, segs)
                if unconnected() > base:  # the route split a plane or pour
                    for t in live[id(j)]:
                        board.Remove(t)
                    for t in previous:
                        board.Add(t)
                    live[id(j)] = previous
                    rejected += 1
                    continue
                state[id(j)] = segs
                changed.add(id(j))
                improved += 1
        total = sum(pcbnew.ToMM((e_ - s_).EuclideanNorm()) for j in jobs for (l, s_, e_) in state[id(j)])
        print(f"pass {rnd + 1}: {improved} connections improved; {total:.1f} mm")
        if not improved:
            break

    allsegs = [(j[0], j[2], l, s_, e_, 0) for j in jobs for (l, s_, e_) in state[id(j)]]
    after = metrics(allsegs)
    print(f"{len(changed)} of {len(jobs)} connections rerouted, {rejected} better routes refused for splitting a plane")
    print(f"after: {after[0]:.1f} mm, {after[1]:.1f} mm sensitive within {NEAR} mm of noisy; "
          f"In2 {sum(pcbnew.ToMM((e - s).EuclideanNorm()) for _, _, l, s, e, _ in allsegs if l == IN2):.1f} mm, "
          f"In5 {sum(pcbnew.ToMM((e - s).EuclideanNorm()) for _, _, l, s, e, _ in allsegs if l == IN5):.1f} mm")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    if not dry:
        pcbnew.SaveBoard(path, board)
        print("saved")


if __name__ == "__main__":
    main()
