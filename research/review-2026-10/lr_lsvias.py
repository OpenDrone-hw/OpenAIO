"""GND vias serving each low-side source (B.Cu pins 1) and the hottest via current per LS at 20 A (that LS alone)."""
import numpy as np, math
from lr_dc import *
from lr_common import load, pad_geom
from shapely.ops import unary_union
from shapely.geometry import Point
b = load('base'); F = {f['ref']: f for f in b['footprints']}
m = NetModel('base', 'GND', h=0.05); m.factor(m.pad_nodes('U24', '2'))
for q in ['Q4', 'Q6', 'Q8', 'Q10', 'Q12', 'Q14', 'Q16', 'Q18', 'Q20', 'Q22', 'Q24', 'Q26']:
    src = unary_union([pad_geom(p) for p in F[q]['pads'] if p['num'] == '1'])
    near = [v for v in b['vias'] if v['net'] == 'GND' and src.distance(Point(v['x'], v['y'])) <= 1.0]
    V = m.solve([(m.pad_nodes(q, '1'), 20.0)])
    bc = sorted(m.barrel_currents(V), reverse=True)
    print(f"{q}: GND vias within 1 mm of the source pins {len(near):2d}; at 20 A hottest vias {[round(x[0], 2) for x in bc[:3]]} A at {[(round(x[1], 2), round(x[2], 2)) for x in bc[:2]]}")
