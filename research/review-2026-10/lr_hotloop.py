"""Buck input hot loops (U3 10 V, U4 5 V LMR51430): VIN pin -> nearest +BATT cap pad, cap GND pad -> GND pin.
Loop = polygon VIN pin, cap+, cap-, GND pin (plan view); plus whether the cap is on the same side as the IC."""
import math
from shapely.geometry import Polygon
from lr_common import *
b = load('base'); F = {f['ref']: f for f in b['footprints']}
def pad(ref, num): return [p for p in F[ref]['pads'] if p['num'] == num][0]
caps = [f for f in b['footprints'] if f['ref'].startswith('C') and {p['net'] for p in f['pads']} == {'+BATT', 'GND'}]
for u in ('U3', 'U4'):
    vin = pad(u, '3'); gnd = pad(u, '1'); sw = pad(u, '2')
    best = []
    for cf in caps:
        cp = [p for p in cf['pads'] if p['net'] == '+BATT'][0]; cn = [p for p in cf['pads'] if p['net'] == 'GND'][0]
        loop = Polygon([(vin['x'], vin['y']), (cp['x'], cp['y']), (cn['x'], cn['y']), (gnd['x'], gnd['y'])]).buffer(0)
        best.append((math.dist((vin['x'], vin['y']), (cp['x'], cp['y'])) + math.dist((gnd['x'], gnd['y']), (cn['x'], cn['y'])), cf['ref'], cf['val'], cf['side'], loop.area))
    best.sort()
    print(u, F[u]['side'], 'VIN', (vin['x'], vin['y']), '-> nearest input caps (pin-to-pad path mm, ref, value, side, loop mm2):', [(round(a, 2), r, v, s, round(l, 2)) for a, r, v, s, l in best[:3]])
