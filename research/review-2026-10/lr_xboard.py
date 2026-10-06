"""What sits on the Base beneath sensitive Core parts (IMU, crystal, OSD, RP2354A): lateral distance (mm, plan view)
from each Core part body to Base aggressor copper on any layer, to Base heat sources, and the Base parts under it."""
import re, collections
from shapely import affinity
from lr_common import *
from lr_dc import net_layer_geoms
c = load('core'); b = load('base')
AGG = {'phase nodes': r'^/[1-4][ABC]$', 'gate drive': r'^(/ESC[1-4]/G[HL][ABC]|Net-\(Q\d+-G\)|Net-\(U(14|16|18|20)-VB\d\))$',
       'buck SW': r'^Net-\((U3-SW|U4-SW|U21-DCC_SW)\)$'}
nets = {p['net'] for f in b['footprints'] for p in f['pads']}
ag = {}
for k, rx in AGG.items():
    gs = []
    for n in nets:
        if re.match(rx, n):
            g, _ = net_layer_geoms(b, 'base', n)
            gs += list(g.values())
    ag[k] = unary_union(gs)
heat = {f['ref']: body_envelope(f, 'F.Cu' if f['side'] == 'F' else 'B.Cu')[0] for f in b['footprints']
        if re.match(r'^(Q\d+|U(3|4|14|16|18|20)|L[23]|Rsense2)$', f['ref'])}
bparts = [(f['ref'], f['side'], body_envelope(f, 'F.Cu' if f['side'] == 'F' else 'B.Cu')[0]) for f in b['footprints'] if f['ref'] not in ('U24', 'J90')]
for ref in ('U8', 'X1', 'U2', 'U10', 'U11', 'U9', 'U6'):
    f = [x for x in c['footprints'] if x['ref'] == ref][0]
    env = affinity.translate(body_envelope(f, 'F.Cu')[0], *OFF)
    out = [f"{ref} ({f['val']}) at base ({env.centroid.x:.2f},{env.centroid.y:.2f}):"]
    for k, g in ag.items():
        out.append(f"{k} {env.distance(g):.2f}")
    hd = sorted((env.distance(g), r) for r, g in heat.items() if g is not None)[:3]
    out.append('nearest heat sources ' + ', '.join(f'{r} {d:.2f}' for d, r in hd))
    under = [r + '/' + s for r, s, g in bparts if g is not None and g.intersects(env)]
    out.append('base parts directly under: ' + (', '.join(under) or 'none'))
    print('; '.join(out))
