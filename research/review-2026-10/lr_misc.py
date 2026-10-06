"""Misc checks: copper balance per layer (warpage), Base J90 pad clearance to +BATT F.Cu pour, Core B.Cu content,
GND stitching around the RF via, fiducials, AIO mask logo extent."""
import collections, math, re
from shapely.geometry import Point
from shapely import affinity
from lr_common import *
c = load('core'); b = load('base')
for bn, d in (('core', c), ('base', b)):
    cb = copper_by_layer_net(d, bn)
    bo = outline(d)
    per = collections.defaultdict(list)
    for (L, n), g in cb.items():
        if L in d['copper']:
            per[L].append(g)
    print(bn, 'copper coverage per layer (% of outline):',
          {L.replace('.Cu', ''): round(100 * unary_union(v).intersection(bo).area / bo.area) for L, v in sorted(per.items(), key=lambda t: d['copper'].index(t[0]))})
# J90 pads vs +BATT on base F.Cu
J90 = [f for f in b['footprints'] if f['ref'] == 'J90'][0]
batt = zone_union(b, '+BATT', 'F.Cu')
dd = sorted((pad_geom(p, 'F.Cu').distance(batt), p['num'], p['net']) for p in J90['pads'])
print('J90 pad -> +BATT F.Cu copper gap: min %.3f mm; pads with gap < 0.25 mm: %d of 34; median %.3f' % (dd[0][0], sum(1 for x in dd if x[0] < 0.25), dd[17][0]))
print('   signal pads ringed by +BATT:', [(n, net, round(g, 3)) for g, n, net in dd if g < 0.25 and net != '+BATT'][:40])
# Core B.Cu content
trk = [t for t in c['tracks'] if t['layer'] == 'B.Cu']
print('Core B.Cu: %.1f mm of tracks on %d nets; non-GND nets: %s' % (sum(t['len'] for t in trk), len({t['net'] for t in trk}),
      sorted({t['net'] for t in trk if t['net'] != 'GND'})))
co_b = affinity.translate(outline(c), *OFF)
bF = zone_union(b, '+BATT', 'F.Cu').intersection(co_b).area
print('Base F.Cu under the Core outline: +BATT %.0f mm2 of %.0f mm2 (%.0f%%); GND %.0f mm2' % (bF, co_b.area, 100 * bF / co_b.area, zone_union(b, 'GND', 'F.Cu').intersection(co_b).area))
# RF via GND stitching
rv = [v for v in b['vias'] if v['net'] == 'Net-(FL1-OUT)'][0]
g = sorted(math.dist((rv['x'], rv['y']), (v['x'], v['y'])) for v in b['vias'] if v['net'] == 'GND')
print('RF via (FL1->U.FL) at (%.2f,%.2f): GND vias within 0.8 mm: %d, within 1.2 mm: %d, nearest %.2f mm' % (rv['x'], rv['y'], sum(1 for x in g if x <= 0.8), sum(1 for x in g if x <= 1.2), g[0]))
# fiducials
for bn, d in (('core', c), ('base', b)):
    fid = [f['ref'] for f in d['footprints'] if f['ref'].upper().startswith('FID') or 'Fiducial' in f['fpid']]
    print(bn, 'fiducials:', fid or 'none')
