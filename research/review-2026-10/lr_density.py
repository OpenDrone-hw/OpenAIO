"""Density: body-to-body gaps (fab outline), envelope gaps (body U pads), free area per side,
parts that could flip side, unused pads per ref.  usage: python3 lr_density.py  -> prints + lr_density.json"""
import json, collections, math
from shapely.strtree import STRtree
from shapely import affinity
from lr_common import *

TARGET = 0.20
c = load('core'); b = load('base')
co_b = affinity.translate(outline(c), *OFF)  # core outline in base coords
SKIP_BODY = ('U24', 'J90', 'J91')            # outline footprint and LGA lands: not components


def is_padonly(f):
    return f['fpid'].endswith(('small_pad', 'TestPoint_Pad_D1.0mm')) or f['ref'].startswith(('TP', 'J')) and len(f['pads']) <= 2 and not f['fabpts']


def parts(d, side):
    lay = 'F.Cu' if side == 'F' else 'B.Cu'
    out = []
    for f in d['footprints']:
        if f['side'] != side or f['ref'] in SKIP_BODY:
            continue
        env, body, src = body_envelope(f, lay)
        if env is None:
            continue
        out.append(dict(ref=f['ref'], val=f['val'], fpid=f['fpid'], env=env, body=body if body is not None else env, src=src,
                        padonly=is_padonly(f)))
    return out


def side_obstacles(d, side):
    """copper pads on that side that are not components (U24 battery/motor pads, LGA, mounting holes)"""
    lay = 'F.Cu' if side == 'F' else 'B.Cu'
    g = []
    for f in d['footprints']:
        if f['ref'] in SKIP_BODY:
            for p in f['pads']:
                g.append(pad_geom(p, lay))
                if p['drill'] > 0:
                    g.append(Point(p['x'], p['y']).buffer(p['drill'] / 2 + 0.25))
    return unary_union([x for x in g if not x.is_empty])


def gaps(P):
    geoms = [p['body'] for p in P]
    envs = [p['env'] for p in P]
    tree = STRtree(geoms)
    etree = STRtree(envs)
    for i, p in enumerate(P):
        nb = [j for j in tree.query(p['body'].buffer(3.0)) if j != i and not P[j]['padonly']]
        if p['padonly'] or not nb:
            p['nn'] = None; p['nn_env'] = None; p['nn_ref'] = None
            continue
        dists = sorted((p['body'].distance(geoms[j]), P[j]['ref']) for j in nb)
        p['nn'], p['nn_ref'] = dists[0]
        p['nn_env'] = min(p['env'].distance(envs[j]) for j in nb)
    pairs = []
    for i, p in enumerate(P):
        if p['padonly']:
            continue
        for j in tree.query(p['body'].buffer(TARGET)):
            if j > i and not P[j]['padonly']:
                dd = p['body'].distance(geoms[j])
                if dd < TARGET - 1e-6:
                    pairs.append((p['ref'], P[j]['ref'], round(dd, 3), round(p['body'].intersection(geoms[j]).area, 3)))
    return pairs


res = {}
for bn, d in (('core', c), ('base', b)):
    bo = outline(d)
    for side in ('F', 'B'):
        P = parts(d, side)
        if not P:
            continue
        pairs = gaps(P)
        comps = [p for p in P if not p['padonly']]
        nn = sorted(p['nn'] for p in comps if p['nn'] is not None)
        occupied = unary_union([p['env'].buffer(TARGET / 2) for p in P] + [side_obstacles(d, side).buffer(TARGET / 2)])
        usable = bo.buffer(-0.3)  # 0.3 mm from the board edge
        blocked_extra = Polygon()
        if bn == 'base' and side == 'F':
            blocked_extra = co_b.buffer(0.2)   # the Core module sits here
        if bn == 'core' and side == 'B':
            blocked_extra = bo                 # LGA side: nothing but J91
        free = usable.difference(occupied).difference(blocked_extra)
        # free area in pieces big enough for a 0201 (0.6x0.3 + 0.1 margin each side): erode by 0.25
        free_big = free.buffer(-0.25).buffer(0.25)
        body_area = unary_union([p['body'] for p in comps]).area
        env_area = unary_union([p['env'] for p in P]).area
        hist = collections.Counter()
        for x in nn:
            k = '<0.10' if x < 0.1 else '0.10-0.20' if x < 0.2 else '0.20-0.30' if x < 0.3 else '0.30-0.50' if x < 0.5 else '0.50-1.00' if x < 1.0 else '>=1.00'
            hist[k] += 1
        key = f'{bn}_{side}'
        res[key] = dict(parts=len(comps), board_area=bo.area, body_area=body_area, env_area=env_area,
                        free=free.area, free_usable=free_big.area,
                        nn_median=nn[len(nn) // 2] if nn else None, nn_hist=dict(hist), pairs_below_target=pairs,
                        nn=[(p['ref'], p['val'], round(p['nn'], 3) if p['nn'] is not None else None, p['nn_ref'],
                             round(p['nn_env'], 3) if p['nn_env'] is not None else None, p['src']) for p in P])
        res[key]['free_regions'] = sorted([(round(g.area, 2), round(g.centroid.x, 2), round(g.centroid.y, 2),
                                            [round(v, 2) for v in g.bounds]) for g in (free_big.geoms if hasattr(free_big, 'geoms') else [free_big]) if g.area > 1.0], reverse=True)
        print(f"\n== {bn} {side}: {len(comps)} parts; board {bo.area:.0f} mm2, bodies {body_area:.0f} mm2 ({100*body_area/bo.area:.0f}%), "
              f"bodies+pads {env_area:.0f} mm2; free (0.1 mm halo, 0.3 mm edge{', minus Core footprint' if blocked_extra.area > 0 else ''}) "
              f"{free.area:.0f} mm2, of which in pieces >=0.5 mm wide {free_big.area:.0f} mm2")
        print(f"   nearest-neighbour body gap median {res[key]['nn_median']:.3f} mm; histogram {dict(sorted(hist.items()))}")
        print(f"   pairs closer than {TARGET} mm body-to-body: {len(pairs)}: {pairs[:25]}")
        print(f"   largest free regions (mm2, cx, cy): {[r[:3] for r in res[key]['free_regions'][:8]]}")
        nosrc = [p['ref'] for p in P if p['src'] in ('pads-hull', 'none') and not p['padonly']]
        if nosrc:
            print(f'   (no fab outline, pads hull used: {nosrc})')

# ---------- flip candidates (base): part fits at the same XY on the other side
print('\n== flip candidates on the Base (envelope + 0.1 mm halo free on the other side at the same XY)')
for side, other in (('B', 'F'), ('F', 'B')):
    Po = parts(b, other)
    occ_o = unary_union([p['env'].buffer(TARGET / 2) for p in Po] + [side_obstacles(b, other).buffer(TARGET / 2)])
    if other == 'F':
        occ_o = unary_union([occ_o, co_b.buffer(0.2)])
    usable = outline(b).buffer(-0.3)
    cand = []
    for p in parts(b, side):
        if p['padonly']:
            continue
        g = p['env'].buffer(TARGET / 2)
        if usable.contains(g) and not g.intersects(occ_o):
            cand.append((p['ref'], p['val']))
    print(f'   {side} -> {other}: {len(cand)} parts: {cand}')
    res[f'flip_{side}_to_{other}'] = cand

# ---------- unused pads
print('\n== unused pads (no net / unconnected-* / single-pad net with no tracks), per ref')
for bn, d in (('core', c), ('base', b)):
    npads = collections.Counter(p['net'] for f in d['footprints'] for p in f['pads'])
    tracked = {t['net'] for t in d['tracks']} | {v['net'] for v in d['vias']}
    per = collections.defaultdict(list)
    for f in d['footprints']:
        if f['ref'] in ('U24',):
            continue
        for p in f['pads']:
            if p['num'] == '' :
                continue
            n = p['net']
            if n == '' or n.startswith('unconnected-') or (npads[n] == 1 and n not in tracked and not n.startswith(('+', 'GND'))):
                per[f['ref']].append(f"{p['num']}:{p['fn'] or n}")
    tot = sum(len(v) for v in per.values())
    print(f'  {bn}: {tot} unused pads on {len(per)} parts')
    for r, l in sorted(per.items(), key=lambda t: -len(t[1])):
        val = [f['val'] for f in d['footprints'] if f['ref'] == r][0]
        print(f'     {r:7s} {val[:18]:18s} {len(l):2d}  {", ".join(l)}')
    res[f'unused_{bn}'] = per
json.dump(res, open('lr_density.json', 'w'), indent=1, default=str)
