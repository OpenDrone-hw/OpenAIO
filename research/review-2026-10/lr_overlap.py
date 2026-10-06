"""Broadside overlap of switching copper (phase nodes, gate drive, buck SW) with the planes on the neighbouring layers
(Base), and a parallel-plate capacitance estimate C = e0*er*A/h (er 4.2, no fringing) -> injected current at 1 V/ns."""
import re, collections
from lr_common import *
from lr_dc import net_layer_geoms
b = load('base')
E0, ER = 8.854e-12, 4.2
AGG = {'phase nodes': r'^/[1-4][ABC]$', 'gate drive': r'^(/ESC[1-4]/G[HL][ABC]|Net-\(Q\d+-G\)|Net-\(U(14|16|18|20)-VB\d\))$',
       'buck SW': r'^Net-\((U3-SW|U4-SW|U21-DCC_SW)\)$'}
cu = b['copper']; z = layer_z('base')
fills = collections.defaultdict(lambda: collections.defaultdict(list))
for zz in b['zones']:
    if not zz['rule']:
        fills[zz['layer']][zz['net']].append(polys(zz['filled']))
fills = {L: {n: unary_union(v) for n, v in m.items()} for L, m in fills.items()}
nets = {p['net'] for f in b['footprints'] for p in f['pads']}
for k, rx in AGG.items():
    per = collections.defaultdict(list)
    for n in nets:
        if re.match(rx, n):
            g, _ = net_layer_geoms(b, 'base', n)
            for L, gg in g.items():
                per[L].append(gg)
    per = {L: unary_union(v) for L, v in per.items()}
    tot = collections.Counter()
    rows = []
    for L, g in per.items():
        i = cu.index(L)
        for j in (i - 1, i + 1):
            if 0 <= j < len(cu):
                Ln = cu[j]
                h = abs(z[Ln] - z[L]) - 0.035
                for n, f in fills.get(Ln, {}).items():
                    if re.match(rx, n):
                        continue
                    a = g.intersection(f).area
                    if a > 0.05:
                        C = E0 * ER * a * 1e-6 / (h * 1e-3) * 1e12
                        tot[n] += C
                        rows.append(f'{L}->{Ln}:{n} {a:.1f} mm2 h{h:.2f} {C:.1f} pF')
    print(f'{k}: ' + '; '.join(rows))
    print(f'   total C to: ' + ', '.join(f'{n} {v:.1f} pF ({v:.0f} mA at 1 V/ns)' for n, v in tot.most_common()))
