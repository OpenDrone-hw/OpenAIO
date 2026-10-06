"""Plan-view body of parts that have a VRML model (x/y extent of the model, rotated/placed like the footprint),
to check fab/silk-derived bodies: Card1 vs R34, L2/L3, USB1, U12, JP1, U10 vs C34."""
import re, math, os
from shapely.geometry import MultiPoint
from shapely import affinity
from lr_common import *
from lr_heights import HW, OD
def model_hull(f):
    for m in f['models']:
        p = m['file'].replace('${KIPRJMOD}', HW).replace('${OPENDRONE_LIB}', OD)
        if p.endswith('.step'):
            p = p[:-5] + '.wrl'
        if not os.path.exists(p):
            continue
        s = open(p, errors='ignore').read()
        pts = []
        for blk in re.findall(r'point\s*\[([^\]]*)\]', s):
            v = [float(x) for x in re.findall(r'-?\d+\.?\d*(?:[eE]-?\d+)?', blk)]
            pts += [(v[i] * 2.54 + m['off'][0], -(v[i + 1] * 2.54 + m['off'][1])) for i in range(0, len(v) - 2, 3)]
        if not pts:
            continue
        h = MultiPoint(pts).convex_hull
        if f['side'] == 'B':
            h = affinity.scale(h, -1, 1, origin=(0, 0))
        h = affinity.rotate(h, f['rot'] if f['side'] == 'F' else -f['rot'], origin=(0, 0))
        return affinity.translate(h, f['x'], f['y'])
    return None
for bn, pairs in (('base', [('Card1', 'R34'), ('L2', 'L3'), ('USB1', 'R3'), ('U12', 'Q13'), ('JP1', 'Q21')]), ('core', [('U10', 'C34'), ('X1', 'C4'), ('U8', 'C29')])):
    d = load(bn); F = {f['ref']: f for f in d['footprints']}
    for a, bb in pairs:
        ha = model_hull(F[a])
        ea, ba, src = body_envelope(F[a], 'F.Cu' if F[a]['side'] == 'F' else 'B.Cu')
        eb, bb_, _ = body_envelope(F[bb], 'F.Cu' if F[bb]['side'] == 'F' else 'B.Cu')
        if ha is None:
            print(bn, a, 'no wrl'); continue
        print(f"{bn} {a}: model plan {ha.area:.2f} mm2 bbox {[round(v,2) for v in ha.bounds]} vs {src} body {ba.area:.2f} mm2; "
              f"gap model->{bb} envelope {ha.distance(eb):.3f} mm (overlap {ha.intersection(eb).area:.3f} mm2)")
