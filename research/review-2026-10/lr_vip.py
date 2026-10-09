"""Via-in-pad census (via centre inside an SMD pad) by part class, both boards. Board setup has no filling/capping."""
import re, collections
from shapely.geometry import Point
from shapely.strtree import STRtree
from lr_common import *
def cls(ref, fpid):
    if ref.startswith(('J90', 'J91')): return 'LGA land'
    if ref.startswith('Q'): return 'MOSFET / small FET'
    if re.search(r'0201', fpid): return '0201 passive'
    if re.search(r'0402|0603|0805|1206|2512', fpid): return '0402+ passive'
    if ref.startswith('U'): return 'IC (QFN/LGA/SOT)'
    return 'other (pads, conn, L, X)'
for bn in ('core', 'base'):
    d = load(bn)
    geoms, meta = [], []
    for f in d['footprints']:
        for p in f['pads']:
            if p['drill'] > 0: continue
            for L, pl in p['polys'].items():
                geoms.append(polys(pl)); meta.append((f['ref'], f['fpid']))
    tree = STRtree(geoms)
    c = collections.Counter(); parts = collections.defaultdict(set)
    for v in d['vias']:
        pt = Point(v['x'], v['y'])
        for i in tree.query(pt):
            if geoms[i].contains(pt):
                k = cls(*meta[i]); c[k] += 1; parts[k].add(meta[i][0]); break
    print(f"{bn}: {sum(c.values())} of {len(d['vias'])} vias are in SMD pads: " + ', '.join(f'{k} {n} ({len(parts[k])} parts)' for k, n in c.most_common()))
