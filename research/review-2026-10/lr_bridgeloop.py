"""Half-bridge commutation loop proxy: for each phase leg, plan-view distance HS drain pad -> nearest +BATT/GND
decoupling cap (+ pad) and LS source pads -> same cap (GND pad); cap side. Bulk caps C90..C103, C105, C106 have value 'C'."""
import math
from lr_common import *
b = load('base'); F = {f['ref']: f for f in b['footprints']}
caps = [f for f in b['footprints'] if f['ref'].startswith('C') and {p['net'] for p in f['pads']} == {'+BATT', 'GND'}]
print('+BATT/GND caps:', [(f['ref'], f['val'], f['fpid'].split(':')[1][:14], f['side']) for f in caps])
HS = ['Q3', 'Q5', 'Q7', 'Q9', 'Q11', 'Q13', 'Q15', 'Q17', 'Q19', 'Q21', 'Q23', 'Q25']
rows = []
for hs in HS:
    n = int(hs[1:]); ls = f'Q{n + 1}'
    d = pad_geom([p for p in F[hs]['pads'] if p['num'] == '3'][0])
    s = unary_union([pad_geom(p) for p in F[ls]['pads'] if p['num'] == '1'])
    best = None
    for cf in caps:
        cp = pad_geom([p for p in cf['pads'] if p['net'] == '+BATT'][0]); cn = pad_geom([p for p in cf['pads'] if p['net'] == 'GND'][0])
        L = d.distance(cp) + s.distance(cn)
        if best is None or L < best[0]:
            best = (L, cf['ref'], cf['side'])
    rows.append((hs, ls, round(best[0], 2), best[1], best[2]))
for r in rows:
    print('  leg %s/%s: drain->cap+ + source->cap- = %.2f mm (%s, %s side)' % r)
print('caps shared: ', {c: sum(1 for r in rows if r[3] == c) for c in {r[3] for r in rows}})
