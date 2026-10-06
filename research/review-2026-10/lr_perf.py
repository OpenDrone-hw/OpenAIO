"""Plane perforation: filled area / zone outline area (inside board) for the main pours, and number of foreign
vias/holes punching through each pour."""
import collections
from shapely.geometry import Point
from lr_common import *
for bn in ('base', 'core'):
    d = load(bn); bo = outline(d)
    agg = collections.defaultdict(lambda: [Polygon(), Polygon()])
    for z in d['zones']:
        if z['rule']: continue
        k = (z['layer'], z['net'])
        agg[k][0] = agg[k][0].union(polys(z['outline']).intersection(bo))
        agg[k][1] = agg[k][1].union(polys(z['filled']))
    for (L, n), (o, f) in sorted(agg.items(), key=lambda t: -t[1][1].area):
        if f.area < 40: continue
        holes = sum(1 for v in d['vias'] if v['net'] != n and L in via_layers(bn, v) and o.contains(Point(v['x'], v['y'])))
        print(f'{bn} {L:7s} {n:7s} outline {o.area:6.0f} mm2 filled {f.area:6.0f} mm2 ({100 * f.area / max(o.area, 1e-9):3.0f}%), foreign vias inside {holes}')
