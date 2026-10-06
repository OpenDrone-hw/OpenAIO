"""Single-via / single-track feeds on power pins: for each IC/connector/power-part pad on a power net, does it touch a
same-net pour on its own layer, and how many same-net vias reach it (inside the pad or via a track <= 1.5 mm)."""
import re, math, collections
from shapely.geometry import Point
from lr_common import *
import lr_graph, networkx as nx
PWR = re.compile(r'^(\+.*|GND|/CSA\+|/[1-4][ABC])$')
for bn in ('core', 'base'):
    d = load(bn)
    fills = collections.defaultdict(dict)
    for z in d['zones']:
        if not z['rule']:
            fills[z['layer']].setdefault(z['net'], []).append(polys(z['filled']))
    fills = {L: {n: unary_union(v) for n, v in m.items()} for L, m in fills.items()}
    graphs = {}
    rows = []
    for f in d['footprints']:
        if not re.match(r'^(U|Q|L|D|J9|USB|Card|Rsense|JP)', f['ref']):
            continue
        for p in f['pads']:
            n = p['net']
            if not PWR.match(n) or n == 'GND' and not f['ref'].startswith(('U', 'J9', 'USB', 'Q', 'Rsense')):
                continue
            L = list(p['polys'].keys())[0] if p['polys'] else None
            if L is None:
                continue
            g = pad_geom(p, L)
            pour = n in fills.get(L, {}) and fills[L][n].buffer(0.01).intersects(g) and fills[L][n].intersection(g.buffer(0.05)).area > 0.02
            if n not in graphs:
                graphs[n] = lr_graph.build(d, bn, n)
            G = graphs[n]
            node = ('PAD', f['ref'], p['num'])
            nv = 0
            if node in G:
                dist = nx.single_source_dijkstra_path_length(G, node, cutoff=1.5, weight='w')
                nv = sum(1 for k in dist if k[0] == 'VIA')
            rows.append((f['ref'], p['num'], p['fn'], n, L, pour, nv))
    print(f'== {bn}: power pads checked {len(rows)}')
    single = [r for r in rows if not r[5] and r[6] <= 1 and not r[0].startswith('J9')]
    print(f'   not pour-connected and reached by <=1 via within 1.5 mm of track: {len(single)}')
    for r in single:
        print('     %-7s %-4s %-12s %-10s %s vias=%d' % (r[0], r[1], r[2][:12], r[3], r[4], r[6]))
    lga = [r for r in rows if r[0].startswith('J9')]
    for r in lga:
        if r[3] != 'GND':
            print('   LGA %s pad %s %s: pour %s, vias within 1.5 mm %d' % (r[0], r[1], r[3], r[5], r[6]))
    gl = [r for r in lga if r[3] == 'GND']
    print('   LGA GND pads: %d, pour-connected %d, mean vias %.1f' % (len(gl), sum(1 for r in gl if r[5]), sum(r[6] for r in gl) / max(len(gl), 1)))
