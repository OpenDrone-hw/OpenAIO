"""Shared helpers for the layout review (reads lr_core.json / lr_base.json made by lr_dump.py)."""
import json, math, os
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, MultiPoint
from shapely.ops import unary_union, polygonize

HERE = os.path.dirname(os.path.abspath(__file__))
# LGA offset: base coordinate = core coordinate + OFF (both seen from the top, no mirror)
OFF = (69.800 - 104.032, 52.780 - 44.406)

# Stackups (from the .kicad_pcb setup/stackup blocks)
STACK = {
    'core': [('F.Cu', 0.035), ('d', 0.0994), ('In1.Cu', 0.035), ('d', 0.11), ('In2.Cu', 0.035), ('d', 0.25),
             ('In3.Cu', 0.035), ('d', 0.11), ('In4.Cu', 0.035), ('d', 0.0994), ('B.Cu', 0.035)],
    'base': [('F.Cu', 0.035), ('d', 0.1), ('In1.Cu', 0.035), ('d', 0.3), ('In2.Cu', 0.035), ('d', 0.1),
             ('In3.Cu', 0.035), ('d', 0.3), ('In4.Cu', 0.035), ('d', 0.1), ('In5.Cu', 0.035), ('d', 0.3),
             ('In6.Cu', 0.035), ('d', 0.1), ('B.Cu', 0.035)],
}
# copper thickness actually ordered: Base 2 oz outer (70 um) per AGENTS/board setup; inner 1 oz (35 um)
CU_T = {'base': {'F.Cu': 0.070, 'B.Cu': 0.070}, 'core': {}}


def cu_thick(board, layer):
    return CU_T[board].get(layer, 0.035)


def layer_z(board):
    """z (mm from top) of each copper layer centre, and dielectric gap between neighbours."""
    z = 0.0
    out = {}
    for name, t in STACK[board]:
        if name != 'd':
            out[name] = z + t / 2
        z += t
    return out


def load(board):
    return json.load(open(os.path.join(HERE, f'lr_{board}.json')))


def polys(lst):
    ps = []
    for outer, holes in lst:
        if len(outer) >= 3:
            p = Polygon(outer, [h for h in holes if len(h) >= 3])
            if not p.is_valid:
                p = p.buffer(0)
            ps.append(p)
    return unary_union(ps) if ps else Polygon()


def outline(d):
    return polys(d['outline'])


def pad_geom(p, layer=None):
    if layer:
        if layer in p['polys']:
            return polys(p['polys'][layer])
        return Polygon()
    return unary_union([polys(v) for v in p['polys'].values()])


def fab_body(f):
    """Package body from the fab layer. Returns (polygon, source)."""
    pts = f['fabpts'] + [q for poly in f['fabpolys'] for q in poly]
    if f['fabsegs']:
        lines = [LineString(s) for s in f['fabsegs'] if s[0] != s[1]]
        try:
            pg = list(polygonize(unary_union(lines)))
        except Exception:
            pg = []
        if pg:
            u = unary_union(pg)
            hull = MultiPoint(pts).convex_hull if len(pts) >= 3 else u
            # prefer the closed polygon unless it is a tiny piece (pin-1 chamfer) of the hull
            if u.area > 0.6 * hull.area:
                return u, 'fab-poly'
            return hull, 'fab-hull'
    if len(pts) >= 3:
        h = MultiPoint(pts).convex_hull
        if h.area > 0.01:
            return h, 'fab-hull'
    return None, 'none'


def body_envelope(f, side_layer):
    """Package body (fab) united with its copper pads on the mounting side: the real space the part takes."""
    body, src = fab_body(f)
    pads = unary_union([pad_geom(p, side_layer) for p in f['pads']])
    # fab drawing missing or degenerate (< 60 % of the pads hull):
    #  1) EasyEDA names carry the body size (..._L7.0-W7.0-...): rectangle at the pad centroid, orientation that
    #     best covers the pads hull;  2) else the silkscreen hull shrunk by 0.1 mm (silk is drawn just outside the body)
    phull = pads.convex_hull if not pads.is_empty else None
    if phull is not None and (body is None or body.area < 0.6 * phull.area):
        import re
        from shapely.geometry import box
        from shapely import affinity
        m = re.search(r'_L(\d+(?:\.\d+)?)-W(\d+(?:\.\d+)?)', f['fpid'])
        if m:
            Lb, Wb = float(m.group(1)), float(m.group(2))
            cx_, cy_ = phull.centroid.x, phull.centroid.y
            best = None
            for ang in (f['rot'], f['rot'] + 90):
                r_ = affinity.rotate(box(cx_ - Lb / 2, cy_ - Wb / 2, cx_ + Lb / 2, cy_ + Wb / 2), -ang, origin=(cx_, cy_))
                k = r_.intersection(phull).area
                if best is None or k > best[0]:
                    best = (k, r_)
            body, src = best[1], 'name-LxW'
        else:
            sp = f.get('silkpts', [])
            if len(sp) >= 3:
                sh = MultiPoint(sp).convex_hull.buffer(-0.1, join_style='mitre')
                if sh.area > 0.6 * phull.area:
                    body, src = sh, 'silk-hull'
    if body is None:
        if pads.is_empty:
            return None, None, 'none'
        return pads.convex_hull, pads, 'pads-hull'
    return unary_union([body, pads]), body, src


def track_geom(t, extra=0.0):
    w = t['w'] / 2 + extra
    if 'mid' in t:
        # approximate arc by 8 segments through mid
        a, m, b = t['a'], t['mid'], t['b']
        return LineString([a, m, b]).buffer(w, cap_style='round')
    if t['a'] == t['b']:
        return Point(t['a']).buffer(w)
    return LineString([t['a'], t['b']]).buffer(w, cap_style='round')


def via_layers(board, v):
    cu = [n for n, _ in STACK[board] if n != 'd']
    i, j = cu.index(v['top']), cu.index(v['bot'])
    return cu[min(i, j):max(i, j) + 1]


def zone_union(d, net=None, layer=None):
    ps = [polys(z['filled']) for z in d['zones'] if not z['rule'] and (net is None or z['net'] == net)
          and (layer is None or z['layer'] == layer)]
    return unary_union(ps) if ps else Polygon()


def copper_by_layer_net(d, board):
    """dict (layer, net) -> union of tracks + zone fills + pads (+ via annuli) on that layer."""
    from collections import defaultdict
    acc = defaultdict(list)
    for t in d['tracks']:
        acc[(t['layer'], t['net'])].append(track_geom(t))
    for v in d['vias']:
        for L in via_layers(board, v):
            acc[(L, v['net'])].append(Point(v['x'], v['y']).buffer(v['d'] / 2))
    for z in d['zones']:
        if not z['rule']:
            acc[(z['layer'], z['net'])].append(polys(z['filled']))
    for f in d['footprints']:
        for p in f['pads']:
            for L, pl in p['polys'].items():
                acc[(L, p['net'])].append(polys(pl))
            # through-hole pads on inner layers
            if p['drill'] > 0:
                for L in p['layers']:
                    if L not in p['polys']:
                        acc[(L, p['net'])].append(Point(p['x'], p['y']).buffer(p['drill'] / 2 + 0.1))
    return {k: unary_union(v) for k, v in acc.items()}


def fmt(x, n=2):
    return f'{x:.{n}f}'
