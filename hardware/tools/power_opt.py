"""OpenAIO power copper optimiser.

Usage (KiCad's bundled Python):  $KPY power_opt.py <board.kicad_pcb> [--out other.kicad_pcb] [--only stage,stage]

Applies, in place, every accepted high-current change to a board that sits next to its .kicad_pro / .kicad_dru:
  planes   +BATT pours on L3-L6 over the whole interior (env POPT_PLANES=L4.BATT,L5.Rails restricts it), zone priority 1
           (above the GND fill, below every other pour); carved back where it would isolate a GND item
  taps     closes every unconnected +BATT / GND / phase / /CSA+ cluster with a via into a pour of its own net
  links    closes what a via cannot with a grid-routed 0.5 mm track (through vias allowed); boxed-in stubs are reported
  arrays   via arrays in the FET pads: drain +BATT (through), low-side source GND (L7-L8 micro), high-side source phase (L1-L2 micro)
Every via and pour piece is checked against the copper that is already on the board; what conflicts is skipped and
printed as SKIP. Each stage is kept only if no net ends with more unconnected items than before the stage.
Edits go through the pcbnew API only (LoadBoard / SaveBoard).
"""
import collections
import math
import os
import shutil
import sys
import tempfile

import pcbnew as P

MM, TO = P.FromMM, P.ToMM

# ---- rules (project rules, see OpenAIO.kicad_pro / .kicad_dru) -------------------------------------------------
THR_DIA, THR_DRILL = 0.33, 0.15          # through via
MIC_DIA, MIC_DRILL = 0.25, 0.10          # microvia, L1-L2 and L7-L8 only
BUR_DIA, BUR_DRILL = 0.33, 0.15          # buried via, L2-L7 only
MIN_CLR = 0.10                           # power / VBAT clearance, also used for every foreign copper
H2H_SAME, H2H_DIFF = 0.20, 0.25          # hole to hole edge distance
HOLE_CLR = 0.18                          # hole edge to foreign copper
EDGE_CLR = 0.25                          # copper to board edge (rule 0.20 plus margin)
BATT_FULL_LAYERS = ("L4.BATT", "L5.Rails")                    # +BATT over the whole interior (existing through vias land on them)
BATT_POCKET_LAYERS = ("L3.Signal", "L6.Signal_5V")            # +BATT only at the shunt exit
BATT_POCKET = (56.4, 53.8, 66.5, 63.2)
CSA_BRANCH_LAYERS = ("L2.GND", "L3.Signal", "L4.BATT", "L5.Rails", "L6.Signal_5V", "L7.GND")
CSA_BRANCH = (60.0, 48.5, 69.5, 53.5)                         # second /CSA+ branch below the U24.11 mounting hole
CSA_BRANCH_PRIO = 35
PLANE_PRIO = 1                           # GND fill is 0; every existing pour is 2 or higher (so the plane never cuts a pour)
PITCH_THR, PITCH_MIC = 0.40, 0.32
STITCH_R, STITCH_PITCH, STITCH_MAX = 4.0, 0.42, 24   # GND L7-L8 microvias around each low-side source
PHASES = ["/%d%s" % (i, c) for i in range(1, 5) for c in "ABC"]
POWER_NETS = ["+BATT", "GND", "/CSA+"] + PHASES

LOG = []
DIRTY = [True]
SEEN = set()


def log(msg):
    LOG.append(msg)
    print(msg)


def skip(msg):
    if msg not in SEEN:
        SEEN.add(msg)
        log("SKIP " + msg)


# ---- board helpers -------------------------------------------------------------------------------------------------
def fill(b):
    P.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()


def zones(b):
    return [b.GetArea(i) for i in range(b.GetAreaCount())]


def unconnected(b):
    """per-net count of unconnected clusters minus one (same numbers as the DRC unconnected list)"""
    b.BuildConnectivity()
    c = b.GetConnectivity()
    items = collections.defaultdict(list)
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname():
                items[p.GetNetname()].append(p)
    for t in b.GetTracks():
        if t.GetNetname():
            items[t.GetNetname()].append(t)
    res = {}
    for name, its in items.items():
        seen, k = set(), 0
        for it in its:
            u = it.m_Uuid.AsString()
            if u in seen:
                continue
            k += 1
            seen.add(u)
            for o in c.GetConnectedItems(it):
                seen.add(o.m_Uuid.AsString())
        if k > 1:
            res[name] = k - 1
    return res


def clusters(b, net):
    """list of (uuid set, [pads], [tracks/vias]) for the net, biggest first"""
    b.BuildConnectivity()
    c = b.GetConnectivity()
    pads, trks = [], []
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == net:
                pads.append(p)
    for t in b.GetTracks():
        if t.GetNetname() == net:
            trks.append(t)
    seen, out = set(), []
    for it in pads + trks:
        u = it.m_Uuid.AsString()
        if u in seen:
            continue
        grp = [it] + list(c.GetConnectedItems(it))
        ids = {o.m_Uuid.AsString() for o in grp}
        seen |= ids
        out.append((ids, [o for o in grp if o.GetClass() == "PAD"],
                    [o for o in grp if o.GetClass() in ("PCB_TRACK", "PCB_VIA", "PCB_ARC")]))
    out.sort(key=lambda x: -len(x[0]))
    return out


def worse(now, ref):
    return {k: (ref.get(k, 0), v) for k, v in now.items() if v > ref.get(k, 0)}


def new_uuid(item):
    item.SetUuidDirect(P.KIID())


def vec(x, y):
    return P.VECTOR2I(MM(x), MM(y))


# ---- copper index for clearance checks ----------------------------------------------------------------------------
class Index:
    BIN = MM(2.0)

    def __init__(self, b):
        self.b = b
        self.layers = list(b.GetEnabledLayers().CuStack())
        self.obs = {l: collections.defaultdict(list) for l in self.layers}
        self.holes = collections.defaultdict(list)
        self.nclr = {}
        ol = P.SHAPE_POLY_SET()
        b.GetBoardPolygonOutlines(ol, True)
        self.edge = ol
        self.edge_in = P.SHAPE_POLY_SET(ol)
        self.edge_in.Deflate(MM(EDGE_CLR), P.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
        self.rule_areas = [z for z in zones(b) if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                self.add_via(t)
            else:
                self.add_track(t)
        for f in b.GetFootprints():
            for p in f.Pads():
                self.add_pad(p)

    def _bins(self, bb):
        B = self.BIN
        for ix in range(bb.GetLeft() // B, bb.GetRight() // B + 1):
            for iy in range(bb.GetTop() // B, bb.GetBottom() // B + 1):
                yield (ix, iy)

    def _put(self, layer, shape, bb, net, clr, kind):
        rec = (shape, net, clr, kind)
        for k in self._bins(bb):
            self.obs[layer][k].append(rec)

    def _clr(self, item, layer):
        try:
            c = item.GetOwnClearance(layer)
        except Exception:
            c = 0
        return max(c, MM(MIN_CLR))

    def add_track(self, t):
        l = t.GetLayer()
        if l in self.obs:
            self._put(l, t.GetEffectiveShape(l), t.GetBoundingBox(), t.GetNetCode(), self._clr(t, l), "track")
            self.nclr[t.GetNetCode()] = max(self.nclr.get(t.GetNetCode(), 0), self._clr(t, l))

    def add_via(self, v):
        for l in self.layers:
            if v.IsOnLayer(l):
                self._put(l, v.GetEffectiveShape(l), v.GetBoundingBox(), v.GetNetCode(), self._clr(v, l), "via")
        p = v.GetPosition()
        self.holes[(p.x // self.BIN, p.y // self.BIN)].append((p.x, p.y, v.GetDrillValue() / 2.0, v.GetNetCode(), "via"))
        self.nclr[v.GetNetCode()] = max(self.nclr.get(v.GetNetCode(), 0), self._clr(v, v.TopLayer()))

    def add_pad(self, p):
        for l in self.layers:
            if p.IsOnLayer(l):
                self._put(l, p.GetEffectiveShape(l), p.GetBoundingBox(), p.GetNetCode(), self._clr(p, l), "pad")
        if p.HasHole():
            q = p.GetPosition()
            r = max(p.GetDrillSize().x, p.GetDrillSize().y) / 2.0
            self.holes[(q.x // self.BIN, q.y // self.BIN)].append((q.x, q.y, r, p.GetNetCode(), "pad"))

    def net_clr(self, net):
        return max(self.nclr.get(net, 0), MM(MIN_CLR))

    def copper_ok(self, x, y, diam, layers, net, why=None, margin=0.003):
        """circle of diam mm at (x,y) on the given copper layers, net code; foreign copper must stay clear"""
        c = P.SHAPE_CIRCLE(vec(x, y), MM(diam / 2.0))
        cx, cy = MM(x), MM(y)
        B = self.BIN
        reach = MM(diam / 2.0 + 0.6)
        for l in layers:
            seen = set()
            for ix in range((cx - reach) // B, (cx + reach) // B + 1):
                for iy in range((cy - reach) // B, (cy + reach) // B + 1):
                    for rec in self.obs[l].get((ix, iy), ()):
                        if id(rec) in seen:
                            continue
                        seen.add(id(rec))
                        shape, onet, oclr, kind = rec
                        if onet == net:
                            continue
                        need = max(oclr, self.net_clr(net)) + MM(margin)
                        if shape.Collide(c, need):
                            if why is not None:
                                why.append("%s on %s" % (kind, self.b.GetLayerName(l)))
                            return False
        return True

    def hole_ok(self, x, y, drill, net, why=None, cu_diam=None):
        cx, cy = MM(x), MM(y)
        r = MM(drill) / 2.0
        for ix in range(cx // self.BIN - 1, cx // self.BIN + 2):
            for iy in range(cy // self.BIN - 1, cy // self.BIN + 2):
                for (hx, hy, hr, hnet, kind) in self.holes.get((ix, iy), ()):
                    d = math.hypot(hx - cx, hy - cy)
                    need = MM(H2H_SAME if hnet == net else H2H_DIFF)
                    if d - hr - r < need + MM(0.003):
                        if why is not None:
                            why.append("hole of %s" % kind)
                        return False
                    if hnet != net and cu_diam and d - hr - MM(cu_diam) / 2.0 < MM(HOLE_CLR) + MM(0.003):
                        if why is not None:
                            why.append("hole clearance")
                        return False
        return True

    def edge_ok(self, x, y):
        return self.edge_in.Contains(vec(x, y))

    def rule_ok(self, x, y):
        for z in self.rule_areas:
            if z.Outline().Collide(vec(x, y), 0):
                return False
        return True

    def via_ok(self, x, y, kind, net, why=None):
        dia, drill = {"through": (THR_DIA, THR_DRILL), "micro": (MIC_DIA, MIC_DRILL), "buried": (BUR_DIA, BUR_DRILL)}[kind]
        if not self.edge_ok(x, y):
            if why is not None:
                why.append("board edge")
            return False
        if not self.rule_ok(x, y):
            if why is not None:
                why.append("rule area")
            return False
        return self.hole_ok(x, y, drill, net, why, dia)


def eff_dia(kind):
    """copper circle to keep clear: the land, or the hole plus the 0.18 mm hole clearance, whichever reaches further"""
    dia, drill = {"through": (THR_DIA, THR_DRILL), "micro": (MIC_DIA, MIC_DRILL), "buried": (BUR_DIA, BUR_DRILL)}[kind]
    return max(dia, drill + 2 * (HOLE_CLR - MIN_CLR)) + 0.004


def via_layers(b, kind, side=None):
    """(top, bottom, span) copper layer ids a via of this kind touches. side: 'top' for L1-L2, 'bot' for L7-L8"""
    cu = list(b.GetEnabledLayers().CuStack())
    if kind == "through":
        return cu[0], cu[-1], cu
    if kind == "buried":
        return cu[1], cu[-2], cu[1:-1]
    if side == "top":
        return cu[0], cu[1], cu[:2]
    return cu[-2], cu[-1], cu[-2:]


def add_via(b, ix, x, y, kind, net, side=None, why=None):
    top, bot, span = via_layers(b, kind, side)
    dia, drill = {"through": (THR_DIA, THR_DRILL), "micro": (MIC_DIA, MIC_DRILL), "buried": (BUR_DIA, BUR_DRILL)}[kind]
    code = b.FindNet(net).GetNetCode()
    if not ix.via_ok(x, y, kind, code, why):
        return None
    if not ix.copper_ok(x, y, eff_dia(kind), span, code, why):
        return None
    v = P.PCB_VIA(b)
    v.SetViaType({"through": P.VIATYPE_THROUGH, "micro": P.VIATYPE_MICROVIA, "buried": P.VIATYPE_BURIED}[kind])
    v.SetLayerPair(top, bot)
    v.SetPosition(vec(x, y))
    v.SetWidth(MM(dia))
    v.SetDrill(MM(drill))
    v.SetNet(b.FindNet(net))
    b.Add(v)
    ix.add_via(v)
    return v


# ---- zones ---------------------------------------------------------------------------------------------------------
def template_zone(b, net):
    for z in zones(b):
        if not z.GetIsRuleArea() and z.GetNetname() == net:
            return z
    return None


def add_zone(b, net, layer, polys, prio, tmpl):
    """polys: SHAPE_POLY_SET (outlines + holes) copied into a new zone cloned from tmpl"""
    z = P.ZONE(tmpl)
    new_uuid(z)
    z.SetNet(b.FindNet(net))
    z.SetLayer(b.GetLayerID(layer))
    o = z.Outline()
    o.RemoveAllContours()
    o.Append(polys)
    z.SetAssignedPriority(prio)
    z.SetPadConnection(P.ZONE_CONNECTION_FULL)
    z.UnFill()
    b.Add(z)
    return z


def interior(b, inset=0.6):
    ps = P.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(ps, True)
    ps.Deflate(MM(inset), P.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    return ps


# ---- stages --------------------------------------------------------------------------------------------------------
def minor_ids(b, nets):
    ids = set()
    for n in nets:
        for c in clusters(b, n)[1:]:
            ids |= c[0]
    return ids


def rect_set(x0, y0, x1, y1):
    ps = P.SHAPE_POLY_SET()
    ps.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ps.Append(MM(x), MM(y))
    return ps


def rect_in_board(b, rect):
    r = rect_set(*rect)
    r.BooleanIntersection(interior(b))
    return r


def has_zone(b, net, layer, prio):
    lid = b.GetLayerID(layer)
    return any(z.GetNetname() == net and not z.GetIsRuleArea() and z.IsOnLayer(lid) and z.GetAssignedPriority() == prio for z in zones(b))


def carve_check(b, new, before, minor0):
    """a plane replaces the GND fill on its layer; carve it back where that isolates something that hung on the fill"""
    for rnd in range(8):
        fill(b)
        now = unconnected(b)
        bad = worse(now, before)
        if not bad:
            return
        for net in bad:
            for ids, pads, trks in clusters(b, net)[1:]:
                if ids <= minor0:
                    continue
                xs, ys = [], []
                for it in pads + trks:
                    bb = it.GetBoundingBox()
                    xs += [TO(bb.GetLeft()), TO(bb.GetRight())]
                    ys += [TO(bb.GetTop()), TO(bb.GetBottom())]
                if not xs:
                    continue
                r = rect_set(min(xs) - 1.5, min(ys) - 1.5, max(xs) + 1.5, max(ys) + 1.5)
                for z in new:
                    z.Outline().BooleanSubtract(r)
                minor0 |= ids
                log("carved %s around %.1f,%.1f (isolated %s item)" % ([b.GetLayerName(z.GetLayer()) for z in new], min(xs), min(ys), net))


def stage_planes(b, ix):
    tmpl = template_zone(b, "+BATT")
    if tmpl is None:
        skip("planes: no +BATT zone to clone settings from")
        return
    fill(b)
    before = unconnected(b)
    minor0 = minor_ids(b, list(before))
    new = []
    jobs = [(l, interior(b)) for l in BATT_FULL_LAYERS] + [(l, rect_in_board(b, BATT_POCKET)) for l in BATT_POCKET_LAYERS]
    for layer, poly in jobs:
        if b.GetLayerID(layer) < 0:
            skip("planes: layer %s missing" % layer)
            continue
        if has_zone(b, "+BATT", layer, PLANE_PRIO):
            skip("planes: %s already has a +BATT plane" % layer)
            continue
        new.append(add_zone(b, "+BATT", layer, poly, PLANE_PRIO, tmpl))
        DIRTY[0] = True
        log("planes: +BATT pour on %s prio %d%s" % (layer, PLANE_PRIO, " (shunt pocket)" if layer in BATT_POCKET_LAYERS else ""))
    carve_check(b, new, before, minor0)


def stage_csa(b, ix):
    tmpl = template_zone(b, "/CSA+")
    if tmpl is None:
        skip("csa: no /CSA+ zone to clone")
        return
    fill(b)
    before = unconnected(b)
    minor0 = minor_ids(b, list(before))
    new = []
    for layer in CSA_BRANCH_LAYERS:
        if b.GetLayerID(layer) < 0 or has_zone(b, "/CSA+", layer, CSA_BRANCH_PRIO):
            continue
        new.append(add_zone(b, "/CSA+", layer, rect_in_board(b, CSA_BRANCH), CSA_BRANCH_PRIO, tmpl))
        DIRTY[0] = True
    log("csa: /CSA+ second branch %s on %d layers prio %d" % (CSA_BRANCH, len(new), CSA_BRANCH_PRIO))
    carve_check(b, new, before, minor0)


def stage_phase(b, ix):
    """a microvia in every high-side source (phase) pad, and the phase pour of L2 extended to reach the pads"""
    cu = list(b.GetEnabledLayers().CuStack())
    n = 0
    for f in fets(b):
        if not any(p.GetNetname() == "+BATT" for p in f.Pads()):
            continue
        pads = [p for p in f.Pads() if p.GetNumber() == "1" and p.GetNetname() in PHASES]
        if not pads:
            continue
        net = pads[0].GetNetname()
        l2 = [z for z in zones(b) if z.GetNetname() == net and not z.GetIsRuleArea() and z.IsOnLayer(cu[1]) and z.GetAssignedPriority() != 40]
        if not l2:
            skip("phase: %s has no L2 pour" % net)
            continue
        zb = l2[0].GetBoundingBox()
        x0, x1 = min([TO(p.GetBoundingBox().GetLeft()) for p in pads] + [TO(zb.GetLeft())]) - 0.1, max([TO(p.GetBoundingBox().GetRight()) for p in pads] + [TO(zb.GetRight())]) + 0.1
        y0, y1 = min([TO(p.GetBoundingBox().GetTop()) for p in pads] + [TO(zb.GetTop())]) - 0.1, max([TO(p.GetBoundingBox().GetBottom()) for p in pads] + [TO(zb.GetBottom())]) + 0.1
        vias = []
        for p in pads:
            q = p.GetPosition()
            v = add_via(b, ix, TO(q.x), TO(q.y), "micro", net, "top")
            if v is not None:
                vias.append(v)
            else:
                skip("phase: %s source pad at %.2f,%.2f no microvia spot" % (net, TO(q.x), TO(q.y)))
        if vias and not has_zone(b, net, "L2.GND", 40):
            add_zone(b, net, "L2.GND", rect_in_board(b, (x0, y0, x1, y1)), 40, l2[0])
            DIRTY[0] = True
        n += len(vias)
    log("phase: %d L1-L2 microvias in high-side source pads, L2 phase pours extended" % n)


def sample_points(pads, trks):
    """candidate points on a cluster's own copper: (x, y, layer, w)"""
    pts = []
    for p in pads:
        if p.HasHole():
            continue
        bb = p.GetBoundingBox()
        l = list(p.GetLayerSet().CuStack())[0]
        x0, x1, y0, y1 = TO(bb.GetLeft()), TO(bb.GetRight()), TO(bb.GetTop()), TO(bb.GetBottom())
        nx, ny = max(1, int((x1 - x0) / 0.15)), max(1, int((y1 - y0) / 0.15))
        for i in range(nx + 1):
            for j in range(ny + 1):
                x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
                if p.HitTest(vec(x, y)):
                    pts.append((x, y, l, 0.0))
    for t in trks:
        if t.GetClass() == "PCB_VIA":
            continue
        a, e = t.GetStart(), t.GetEnd()
        n = max(1, int(TO(t.GetLength()) / 0.15))
        for i in range(n + 1):
            pts.append((TO(a.x + (e.x - a.x) * i / n), TO(a.y + (e.y - a.y) * i / n), t.GetLayer(), TO(t.GetWidth())))
    return pts

class FillMap:
    """outline lookup in the filled polygons of one zone on one layer (zone islands share the zone object)"""
    CELL = MM(1.0)

    def __init__(self, z, l):
        self.ps = z.GetFilledPolysList(l)
        self.n = self.ps.OutlineCount()
        self.area = []
        self.bins = collections.defaultdict(list)
        for i in range(self.n):
            ol = self.ps.Outline(i)
            bb = ol.BBox()
            self.area.append(abs(ol.Area()) / 1e12)
            for ix in range(bb.GetLeft() // self.CELL, bb.GetRight() // self.CELL + 1):
                for iy in range(bb.GetTop() // self.CELL, bb.GetBottom() // self.CELL + 1):
                    self.bins[(ix, iy)].append((i, bb))

    def idx(self, pt):
        for i, bb in self.bins.get((pt.x // self.CELL, pt.y // self.CELL), ()):
            if bb.Contains(pt) and self.ps.Contains(pt, i):
                return i
        return None



def cluster_points(b, net, pads, trks, limit=300):
    """own copper of a cluster plus the zone islands it sits on (fills of the same zone object share one polygon list)"""
    pts = sample_points(pads, trks)
    cu = list(b.GetEnabledLayers().CuStack())
    zs = [z for z in zones(b) if not z.GetIsRuleArea() and z.GetNetname() == net]
    extra = []
    for p in pads:
        if p.HasHole():
            continue
        l = list(p.GetLayerSet().CuStack())[0]
        for z in zs:
            if not z.IsOnLayer(l):
                continue
            fm = FillMap(z, l)
            i = fm.idx(p.GetPosition())
            if i is None or fm.area[i] > 60.0:
                continue
            bb = fm.ps.Outline(i).BBox()
            x0, x1, y0, y1 = TO(bb.GetLeft()), TO(bb.GetRight()), TO(bb.GetTop()), TO(bb.GetBottom())
            nx, ny = int((x1 - x0) / 0.2) + 1, int((y1 - y0) / 0.2) + 1
            for a in range(nx + 1):
                for c in range(ny + 1):
                    x, y = x0 + a * 0.2, y0 + c * 0.2
                    if fm.ps.Contains(vec(x, y), i):
                        extra.append((x, y, l, 0.0))
    px, py = (TO(pads[0].GetPosition().x), TO(pads[0].GetPosition().y)) if pads else (0, 0)
    extra.sort(key=lambda t: (t[0] - px) ** 2 + (t[1] - py) ** 2)
    return pts + extra[:limit]



def zone_hit(zs, layer, x, y):
    for z in zs:
        if z.IsOnLayer(layer) and z.HitTestFilledArea(layer, vec(x, y), 0):
            return z
    return None


def stage_taps(b, ix, nets):
    cu = list(b.GetEnabledLayers().CuStack())
    for net in nets:
        for rnd in range(6):
            if rnd > 0 or DIRTY[0]:
                fill(b)
                DIRTY[0] = False
            cl = clusters(b, net)
            if len(cl) < 2:
                break
            all_zones = [z for z in zones(b) if not z.GetIsRuleArea() and z.GetNetname() == net]
            done_one = False
            for ids, pads, trks in cl[1:]:
                pts = cluster_points(b, net, pads, trks)
                best = None
                code = b.FindNet(net).GetNetCode()
                reasons = collections.Counter()
                for (x, y, l, w) in pts:
                    opts = []
                    if l == cu[-1]:
                        opts += [("micro", "bot", cu[-2:])]
                    if l == cu[0]:
                        opts += [("micro", "top", cu[:2])]
                    opts += [("through", None, cu)]
                    for kind, side, span in opts:
                        hit = None
                        for tl in span:
                            if tl == l:
                                continue
                            hit = zone_hit(all_zones, tl, x, y)
                            if hit is not None:
                                break
                        if hit is None:
                            reasons["no pour"] += 1
                            continue
                        why = []
                        dia = eff_dia(kind)
                        if not ix.via_ok(x, y, kind, code, why) or not ix.copper_ok(x, y, dia, span, code, why):
                            reasons[why[0] if why else "?"] += 1
                            continue
                        cost = 0 if kind == "micro" else 1
                        if best is None or cost < best[0]:
                            best = (cost, x, y, kind, side)
                        break
                    if best is not None and best[0] == 0:
                        break
                ref_item = pads[0] if pads else trks[0]
                where = "%s cluster at %.1f,%.1f" % (net, TO(ref_item.GetPosition().x), TO(ref_item.GetPosition().y))
                if best is None:
                    skip("taps: %s no via spot (%s)" % (where, dict(reasons.most_common(3))))
                    continue
                v = add_via(b, ix, best[1], best[2], best[3], net, best[4])
                if v is not None:
                    log("taps: %s via %s at %.2f,%.2f" % (where, best[3], best[1], best[2]))
                    done_one = True
                    DIRTY[0] = True
            if not done_one:
                break
        if DIRTY[0]:
            fill(b)
            DIRTY[0] = False
        left = len(clusters(b, net)) - 1
        if left > 0:
            skip("taps: %s still %d unconnected after taps" % (net, left))



def fets(b):
    return [f for f in b.GetFootprints() if f.GetValue().startswith("DOY")]


def fill_pad(b, ix, pad, kind, side, net, pitch, limit, tag):
    """greedy via array inside one pad: scan on a 0.05 mm grid, keep a via when every check passes"""
    bb = pad.GetBoundingBox()
    dia = {"through": THR_DIA, "micro": MIC_DIA}[kind]
    r = dia / 2.0
    x0, x1, y0, y1 = TO(bb.GetLeft()) + r, TO(bb.GetRight()) - r, TO(bb.GetTop()) + r, TO(bb.GetBottom()) - r
    added, mine = 0, []
    for (x, y) in ((x0 + i * 0.05, y0 + j * 0.05) for j in range(int((y1 - y0) / 0.05) + 1) for i in range(int((x1 - x0) / 0.05) + 1)):
        if added >= limit:
            break
        if not pad.HitTest(vec(x, y)):
            continue
        if any(math.hypot(x - mx, y - my) < pitch for mx, my in mine):
            continue
        # the whole land must sit on the pad
        if not all(pad.HitTest(vec(x + r * math.cos(a), y + r * math.sin(a))) for a in (0, 1.57, 3.14, 4.71)):
            continue
        if add_via(b, ix, x, y, kind, net, side) is not None:
            mine.append((x, y))
            added += 1
    return added


def stage_arrays(b, ix):
    cu = list(b.GetEnabledLayers().CuStack())
    DIRTY[0] = True
    for f in fets(b):
        ref = f.GetReference()
        for pad in f.Pads():
            net = pad.GetNetname()
            if pad.GetNumber() == "3" and net == "+BATT":
                n = fill_pad(b, ix, pad, "through", None, net, PITCH_THR, 40, "drain")
                log("arrays: %s drain +BATT +%d through vias" % (ref, n))
            elif pad.GetNumber() == "1" and net == "GND" and pad.IsOnLayer(cu[-1]):
                n = fill_pad(b, ix, pad, "micro", "bot", net, PITCH_MIC, 2, "source")
                log("arrays: %s source GND pad at %.1f,%.1f +%d micro vias L7-L8" % (ref, TO(pad.GetPosition().x), TO(pad.GetPosition().y), n))


# ---- grid router for the few links a via cannot close ---------------------------------------------------------------
import heapq

STEP = 0.1          # router grid, mm
LINK_W = 0.5        # minimum track width for new power links


def add_track(b, ix, a, e, layer, width, net):
    t = P.PCB_TRACK(b)
    t.SetStart(vec(*a))
    t.SetEnd(vec(*e))
    t.SetLayer(layer)
    t.SetWidth(MM(width))
    t.SetNet(b.FindNet(net))
    b.Add(t)
    ix.add_track(t)
    return t


def route_cluster(b, ix, net, cl_main, cl_str, width=LINK_W, margin=4.0, max_nodes=250000):
    """connect the straggler cluster to the main cluster with tracks (and through vias); returns True when routed"""
    cu = list(b.GetEnabledLayers().CuStack())
    code = b.FindNet(net).GetNetCode()
    ids_m, pads_m, trk_m = cl_main
    ids_s, pads_s, trk_s = cl_str
    zs = [z for z in zones(b) if not z.GetIsRuleArea() and z.GetNetname() == net]
    # target test per layer
    m_shapes = {l: [] for l in cu}
    for t in trk_m:
        for l in cu:
            if t.IsOnLayer(l):
                m_shapes[l].append(t.GetEffectiveShape(l))
    m_pads = [(p, [l for l in cu if p.IsOnLayer(l)]) for p in pads_m]

    fmaps = {}
    for z in zs:
        for l in cu:
            if z.IsOnLayer(l):
                fmaps[(id(z), l)] = FillMap(z, l)
    own = collections.defaultdict(set)

    def is_target(l, x, y):
        pt = vec(x, y)
        for p, ls in m_pads:
            if l in ls and p.HitTest(pt):
                return True
        c = P.SHAPE_CIRCLE(pt, MM(0.02))
        for sh in m_shapes[l]:
            if sh.Collide(c, 0):
                return True
        for z in zs:
            fm = fmaps.get((id(z), l))
            if fm is not None:
                i = fm.idx(pt)
                if i is not None and i not in own[(id(z), l)] and fm.area[i] >= 4.0:
                    return True
        return False

    starts = [(x, y, l) for (x, y, l, w) in cluster_points(b, net, pads_s, trk_s)]
    if not starts:
        return False
    for (x, y, l) in starts:
        for z in zs:
            fm = fmaps.get((id(z), l))
            if fm is not None:
                i = fm.idx(vec(x, y))
                if i is not None:
                    own[(id(z), l)].add(i)
    xs = [p[0] for p in starts]
    ys = [p[1] for p in starts]
    # window: around the straggler and the main cluster copper nearest to it
    tx, ty = [], []
    for p in pads_m + trk_m:
        q = p.GetPosition()
        tx.append(TO(q.x))
        ty.append(TO(q.y))
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    near = sorted(range(len(tx)), key=lambda i: (tx[i] - cx) ** 2 + (ty[i] - cy) ** 2)[:1]
    if not near:
        return False
    d = math.hypot(tx[near[0]] - cx, ty[near[0]] - cy)
    x0, x1 = min(xs) - d - margin, max(xs) + d + margin
    y0, y1 = min(ys) - d - margin, max(ys) + d + margin
    gx = lambda x: int(round((x - x0) / STEP))
    gy = lambda y: int(round((y - y0) / STEP))
    cache = {}

    def free(l, i, j):
        k = (l, i, j)
        if k not in cache:
            x, y = x0 + i * STEP, y0 + j * STEP
            cache[k] = (ix.edge_ok(x, y) and ix.copper_ok(x, y, width, [l], code, margin=0.02))
        return cache[k]

    vcache = {}

    def via_free(i, j):
        k = (i, j)
        if k not in vcache:
            x, y = x0 + i * STEP, y0 + j * STEP
            vcache[k] = ix.via_ok(x, y, "through", code) and ix.copper_ok(x, y, eff_dia("through"), cu, code, margin=0.02)
        return vcache[k]

    pq, best, prev = [], {}, {}
    for (x, y, l) in starts:
        k = (l, gx(x), gy(y))
        if k not in best:
            best[k] = 0.0
            heapq.heappush(pq, (0.0, k))
    goal, n = None, 0
    while pq:
        c, k = heapq.heappop(pq)
        if c > best.get(k, 1e18):
            continue
        l, i, j = k
        n += 1
        if n > max_nodes:
            break
        if c > 0 and is_target(l, x0 + i * STEP, y0 + j * STEP):
            goal = k
            break
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            ni, nj = i + di, j + dj
            if not (0 <= ni <= gx(x1) and 0 <= nj <= gy(y1)):
                continue
            if not free(l, ni, nj):
                continue
            nk = (l, ni, nj)
            nc = c + (1.0 if di == 0 or dj == 0 else 1.414) + (0.05 if True else 0)
            if nc < best.get(nk, 1e18):
                best[nk] = nc
                prev[nk] = k
                heapq.heappush(pq, (nc, nk))
        if via_free(i, j):
            for l2 in cu:
                if l2 == l:
                    continue
                nk = (l2, i, j)
                if not free(l2, i, j):
                    continue
                nc = c + 25.0
                if nc < best.get(nk, 1e18):
                    best[nk] = nc
                    prev[nk] = k
                    heapq.heappush(pq, (nc, nk))
    if goal is None:
        return False
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    # emit tracks (merge straight runs) and vias
    runs = []
    for a, e in zip(path, path[1:]):
        if a[0] != e[0]:
            runs.append(("via", a, e))
        else:
            runs.append(("seg", a, e))
    made = []
    i = 0
    while i < len(runs):
        kind, a, e = runs[i]
        if kind == "via":
            x, y = x0 + a[1] * STEP, y0 + a[2] * STEP
            if not any(r[0] == "via" and (r[1][1], r[1][2]) == (a[1], a[2]) for r in runs[:i]):
                add_via(b, ix, x, y, "through", net)
            i += 1
            continue
        j = i
        dx, dy = e[1] - a[1], e[2] - a[2]
        while j + 1 < len(runs) and runs[j + 1][0] == "seg" and (runs[j + 1][2][1] - runs[j + 1][1][1], runs[j + 1][2][2] - runs[j + 1][1][2]) == (dx, dy):
            j += 1
        last = runs[j][2]
        add_track(b, ix, (x0 + a[1] * STEP, y0 + a[2] * STEP), (x0 + last[1] * STEP, y0 + last[2] * STEP), a[0], width, net)
        i = j + 1
    return True


def stage_links(b, ix, nets):
    for net in nets:
        for rnd in range(8):
            if rnd > 0 or DIRTY[0]:
                fill(b)
                DIRTY[0] = False
            cl = clusters(b, net)
            if len(cl) < 2:
                break
            progress = False
            for cs in cl[1:]:
                ref_item = cs[1][0] if cs[1] else cs[2][0]
                where = "%s cluster at %.1f,%.1f" % (net, TO(ref_item.GetPosition().x), TO(ref_item.GetPosition().y))
                ok = False
                for w in (LINK_W,):
                    ok = route_cluster(b, ix, net, cl[0], cs, w)
                    if ok:
                        break
                if ok:
                    log("links: %s routed with %.2f mm track" % (where, w))
                    progress = True
                    DIRTY[0] = True
                    break  # connectivity changed: recompute clusters
                skip("links: %s no route at %.2f mm" % (where, LINK_W))
            if not progress:
                break
        if DIRTY[0]:
            fill(b)
            DIRTY[0] = False



def stage_stitch(b, ix):
    """GND microvias (L7-L8) in the L8 GND pour around each low-side source row, where both the L8 and the L7 fill exist"""
    cu = list(b.GetEnabledLayers().CuStack())
    gz = [z for z in zones(b) if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
    code = b.FindNet("GND").GetNetCode()
    total = 0
    for f in fets(b):
        pads = [p for p in f.Pads() if p.GetNumber() == "1" and p.GetNetname() == "GND" and p.IsOnLayer(cu[-1])]
        if not pads:
            continue
        cx = sum(TO(p.GetPosition().x) for p in pads) / len(pads)
        cy = sum(TO(p.GetPosition().y) for p in pads) / len(pads)
        cand = []
        n = int(STITCH_R / 0.1)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x, y = cx + i * 0.1, cy + j * 0.1
                d = math.hypot(x - cx, y - cy)
                if d <= STITCH_R:
                    cand.append((d, x, y))
        cand.sort()
        mine, added = [], 0
        for d, x, y in cand:
            if added >= STITCH_MAX:
                break
            if any(math.hypot(x - mx, y - my) < STITCH_PITCH for mx, my in mine):
                continue
            if zone_hit(gz, cu[-1], x, y) is None or zone_hit(gz, cu[-2], x, y) is None:
                continue
            if add_via(b, ix, x, y, "micro", "GND", "bot") is not None:
                mine.append((x, y))
                added += 1
        total += added
    log("stitch: %d GND L7-L8 microvias around the low-side sources" % total)


STAGES = ["planes", "csa", "taps", "links", "phase", "arrays", "stitch"]


def snapshot(b, tmpdir, stem):
    path = os.path.join(tmpdir, stem + ".kicad_pcb")
    P.SaveBoard(path, b)
    return path


def run(path, out=None, only=None):
    d = os.path.dirname(os.path.abspath(path))
    stem = os.path.splitext(os.path.basename(path))[0]
    b = P.LoadBoard(path)
    fill(b)
    ref = unconnected(b)
    log("start: unconnected total %d (power nets %s)" % (sum(ref.values()), {k: v for k, v in ref.items() if k in POWER_NETS}))
    tmp = tempfile.mkdtemp(prefix=".popt_", dir=d)
    for ext in (".kicad_pro", ".kicad_dru"):
        if os.path.exists(os.path.join(d, stem + ext)):
            shutil.copy(os.path.join(d, stem + ext), os.path.join(tmp, stem + ext))
    try:
        for st in STAGES:
            if only and st not in only:
                continue
            snap = snapshot(b, tmp, stem)
            ix = Index(b)
            DIRTY[0] = False
            if st == "planes":
                stage_planes(b, ix)
            elif st == "csa":
                stage_csa(b, ix)
            elif st == "phase":
                stage_phase(b, ix)
            elif st == "taps":
                stage_taps(b, ix, ["+BATT", "GND", "/CSA+"] + PHASES)
            elif st == "links":
                stage_links(b, ix, ["+BATT", "GND", "/CSA+"] + PHASES)
            elif st == "arrays":
                stage_arrays(b, ix)
            elif st == "stitch":
                DIRTY[0] = True
                stage_stitch(b, ix)
            if DIRTY[0]:
                fill(b)
            DIRTY[0] = False
            now = unconnected(b)
            bad = worse(now, ref)
            if bad:
                skip("stage %s reverted: more unconnected on %s" % (st, bad))
                b = P.LoadBoard(snap)
                fill(b)
                DIRTY[0] = False
                continue
            ref = {k: min(ref.get(k, 99999), now.get(k, 0)) for k in set(ref) | set(now)}
            log("stage %s kept: unconnected total %d" % (st, sum(now.values())))
        P.SaveBoard(out or path, b)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    log("saved %s" % (out or path))


if __name__ == "__main__":
    a = sys.argv[1:]
    out = a[a.index("--out") + 1] if "--out" in a else None
    only = a[a.index("--only") + 1].split(",") if "--only" in a else None
    run(a[0], out, only)
