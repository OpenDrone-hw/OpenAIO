"""Aggressor copper on the Base under the Core outline: track length per class and layer (plan view)."""
import re, collections
from shapely import affinity
from lr_common import *
c = load('core'); b = load('base')
co = affinity.translate(outline(c), *OFF)
AGG = {'phase nodes': r'^/[1-4][ABC]$', 'gate drive': r'^(/ESC[1-4]/G[HL][ABC]|Net-\(Q\d+-G\)|Net-\(U(14|16|18|20)-VB\d\))$',
       'buck SW': r'^Net-\((U3-SW|U4-SW|U21-DCC_SW)\)$', 'BEMF/comparator': r'^/ESC[1-4]/FB'}
tot = collections.defaultdict(float); under = collections.defaultdict(float)
for t in b['tracks']:
    for k, rx in AGG.items():
        if re.match(rx, t['net']):
            g = track_geom(t)
            tot[(k, t['layer'])] += t['len']
            if g.intersects(co):
                frac = g.intersection(co).area / max(g.area, 1e-9)
                under[(k, t['layer'])] += t['len'] * frac
for k in AGG:
    print(k, 'total track mm by layer:', {L: round(v, 1) for (kk, L), v in tot.items() if kk == k},
          '| under the Core:', {L: round(v, 1) for (kk, L), v in under.items() if kk == k})
# zones of phase nets under core
for z in b['zones']:
    if not z['rule'] and re.match(AGG['phase nodes'], z['net']):
        a = polys(z['filled']).intersection(co).area
        if a > 0.01: print('phase zone under core', z['net'], z['layer'], round(a, 2))
