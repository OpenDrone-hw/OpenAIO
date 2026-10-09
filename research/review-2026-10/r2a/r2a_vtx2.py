"""S2 VTX pads, targeted: two pads stacked in the free F.Cu pocket right of U12 (the only pocket next to the SH-6 that
takes two pads; left of U12 Q13 leaves 0.95 mm). Free = Base F.Cu minus part envelopes + 0.2, U24 hole/motor pads + 0.2,
Core outline + 0.5 (iron access), board edge 0.5."""
import r2a_geo as G, math, json
import numpy as np
from lr_common import body_envelope, polys
from shapely.geometry import Point, box
from shapely.ops import unary_union
from shapely import affinity
b = G.b; fb = G.fb
obs = []
for f in b['footprints']:
    if f['ref'] == 'U24':
        obs += [polys(p['polys']['F.Cu']).buffer(0.2) for p in f['pads'] if 'F.Cu' in p['polys']]
    elif f['side'] == 'F':
        e = body_envelope(f, 'F.Cu')[0]
        if e is not None:
            obs.append(e.buffer(0.2))
obs.append(affinity.translate(G.CO, *G.OFF).buffer(0.5))
HOLES = [(62.65, 48.16), (62.65, 73.66), (88.15, 48.16), (88.15, 73.66)]
KO = 2.8   # grommet / standoff keep-out radius from the hole centre (M2 grommet flange ~5.2 mm OD + 0.2)
obs += [Point(h).buffer(KO) for h in HOLES]
free = G.BO.buffer(-0.5).difference(unary_union(obs))
pocket = free.intersection(box(73.5, 70.5, 87.0, 78.4))
print('pocket bounds', [round(v, 2) for v in pocket.bounds], 'area', round(pocket.area, 2))
vias = [(v['x'], v['y'], v['net'], v['d']) for v in b['vias']]
vv = lambda r, net: [(round(x, 2), round(y, 2), n) for x, y, n, d in vias if r.buffer(0.16 + d / 2).contains(Point(x, y)) and n != net]
p1 = G.padxy(fb, 'U12', '1')
best = []
for (w, h) in ((1.6, 1.4), (1.4, 1.4), (1.4, 1.2), (1.2, 1.2)):
    for x in np.arange(73.5, 87.0, 0.05):
        for y1 in np.arange(71.5, 78.0, 0.05):
            a = box(x - w / 2, y1 - h / 2, x + w / 2, y1 + h / 2)
            if not free.contains(a):
                continue
            for dx, dy in ((0, h + 0.35), (w + 0.35, 0)):
                bb = affinity.translate(a, dx, dy)
                if not free.contains(bb):
                    continue
                for order in (('GND', '+10V'), ('+10V', 'GND')):
                    conf = vv(a, order[0]) + vv(bb, order[1])
                    p10 = (x, y1) if order[0] == '+10V' else (x + dx, y1 + dy)
                    best.append((-(w * h), len(conf), math.dist(p10, p1), round(x, 2), round(y1, 2), round(x + dx, 2), round(y1 + dy, 2), w, h, order, conf))
best.sort(key=lambda t: (t[0], t[1] + 0.3 * t[2]))
for t in best[:6]:
    print(t)
t = best[0]
x, y1, x2, y2, w, h, order = t[3], t[4], t[5], t[6], t[7], t[8], t[9]
pads = {order[0]: (x, y1), order[1]: (x2, y2)}
out = dict(p10=[pads['+10V'][0], pads['+10V'][1], w, h], gnd=[pads['GND'][0], pads['GND'][1], w, h],
           vias_to_move=t[10], hole_keepout_mm=KO, dist_p10_to_U12pin1=round(t[2], 2), pocket=[round(v, 2) for v in pocket.bounds],
           note='Base F.Cu, rounded-rect SMD pads with mask opening; +10V fed from the +10V net (U12.1 / gate-drive rail) on an inner layer')
json.dump(out, open(G.HERE + '/vtx_choice.json', 'w'), indent=1, default=float)
print(out)
