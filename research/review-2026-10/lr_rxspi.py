"""ESP32-C3 (U22) <-> SX1281 (U21) bus: routed vs straight-line length per net, vias, layers."""
import math
from lr_common import *
import lr_graph
b = load('base'); F = {f['ref']: f for f in b['footprints']}
print('U22 at', (F['U22']['x'], F['U22']['y']), F['U22']['side'], '| U21 at', (F['U21']['x'], F['U21']['y']), F['U21']['side'])
tr = td = 0
for n in ['/RX/MOSI', '/RX/MISO', '/RX/SCK', '/RX/NSS', '/RX/BUSY', '/RX/DIO1', '/RX/RST']:
    G = lr_graph.build(b, 'base', n)
    a = [p for p in F['U22']['pads'] if p['net'] == n][0]; c = [p for p in F['U21']['pads'] if p['net'] == n][0]
    pi = lr_graph.path_info(G, ('PAD', 'U22', a['num']), ('PAD', 'U21', c['num']))
    dd = math.dist((a['x'], a['y']), (c['x'], c['y']))
    tr += pi['len']; td += dd
    print(f"  {n:10s} routed {pi['len']:5.1f} mm, direct {dd:4.1f} mm, vias {pi['vias']}, layers { {k.replace('.Cu',''): round(v,1) for k, v in pi['layers'].items()} }")
print(f'  total routed {tr:.1f} mm vs direct {td:.1f} mm')
