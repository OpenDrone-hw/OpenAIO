"""What-if: +BATT path resistance if the Base F.Cu +BATT pour under the Core outline (plus 0.3 mm) is given to GND
(keeping the J90 +BATT pad and a 1 mm ring around it). Compares shunt->HS drain resistance and the 80 A scenario."""
import numpy as np
from shapely import affinity
from shapely.geometry import Point
from lr_dc import *
from lr_common import load, outline, OFF, zone_union
c = load('core'); b = load('base')
co = affinity.translate(outline(c), *OFF).buffer(0.3)
J90 = [f for f in b['footprints'] if f['ref'] == 'J90'][0]
p26 = [p for p in J90['pads'] if p['num'] == '26'][0]
clipg = co.difference(Point(p26['x'], p26['y']).buffer(1.0))
HS = ['Q3', 'Q5', 'Q7', 'Q9', 'Q11', 'Q13', 'Q15', 'Q17', 'Q19', 'Q21', 'Q23', 'Q25']
res = {}
for name, clip in (('as routed', None), ('F.Cu +BATT removed under Core', {'F.Cu': clipg})):
    m = NetModel('base', '+BATT', h=0.05, clip=clip)
    m.factor(m.pad_nodes('Rsense2', '2'))
    R = []
    for q in HS:
        nd = m.pad_nodes(q, '3')
        V = m.solve([(nd, 1.0)])
        R.append(-np.mean(V[nd]) * 1e3)
    sc = [(m.pad_nodes(q, '3'), 20.0) for q in ('Q3', 'Q9', 'Q15', 'Q21')]
    V = m.solve(sc)
    loss = sum(-np.mean(V[nd]) * a for nd, a in sc)
    res[name] = R
    print(f"{name:32s}: R shunt->drain mOhm min {min(R):.3f} max {max(R):.3f} mean {np.mean(R):.3f}; 80 A loss {loss:.2f} W; floating cells {m.floating}")
a, bb = res['as routed'], res['F.Cu +BATT removed under Core']
print('per-FET change %:', [(q, round(100 * (y - x) / x, 1)) for q, x, y in zip(HS, a, bb)])

# what-if 2: also turn In4 (today +5V 535 mm2 / +3V3 167 mm2) into a +BATT plane (board minus 0.3 mm edge, minus
# 0.53 mm antipads for every non-+BATT through via and 0.2 mm around non-+BATT PTH), LV rails moved elsewhere
from shapely.ops import unary_union
bo = outline(b).buffer(-0.3)
anti = [Point(v['x'], v['y']).buffer(0.265) for v in b['vias'] if v['net'] != '+BATT']
anti += [Point(p['x'], p['y']).buffer(p['drill'] / 2 + 0.25) for f in b['footprints'] for p in f['pads'] if p['drill'] > 0 and p['net'] != '+BATT']
in4 = bo.difference(unary_union(anti))
for name, clip, add in (('In4 +BATT plane added', None, {'In4.Cu': in4}),
                        ('F under Core -> GND, In4 +BATT plane', {'F.Cu': clipg}, {'In4.Cu': in4})):
    m = NetModel('base', '+BATT', h=0.05, clip=clip, add=add)
    m.factor(m.pad_nodes('Rsense2', '2'))
    R = []
    for q in HS:
        nd = m.pad_nodes(q, '3'); V = m.solve([(nd, 1.0)]); R.append(-np.mean(V[nd]) * 1e3)
    sc = [(m.pad_nodes(q, '3'), 20.0) for q in ('Q3', 'Q9', 'Q15', 'Q21')]
    V = m.solve(sc); loss = sum(-np.mean(V[nd]) * a for nd, a in sc)
    print(f"{name:36s}: R min {min(R):.3f} max {max(R):.3f} mean {np.mean(R):.3f} mOhm; 80 A loss {loss:.2f} W")

# what-if 3 (recommended stack): In5 becomes a full +BATT plane except the existing +10V island (signals moved off In5);
# F.Cu under the Core either kept or given to GND
ten = zone_union(b, '+10V', 'In5.Cu').buffer(0.2)
in5 = in4.difference(ten)
for name, clip, add in (('In5 full +BATT (keep +10V island)', None, {'In5.Cu': in5}),
                        ('...and F under Core -> GND', {'F.Cu': clipg}, {'In5.Cu': in5})):
    m = NetModel('base', '+BATT', h=0.05, clip=clip, add=add)
    m.factor(m.pad_nodes('Rsense2', '2'))
    R = []
    for q in HS:
        nd = m.pad_nodes(q, '3'); V = m.solve([(nd, 1.0)]); R.append(-np.mean(V[nd]) * 1e3)
    sc = [(m.pad_nodes(q, '3'), 20.0) for q in ('Q3', 'Q9', 'Q15', 'Q21')]
    V = m.solve(sc); loss = sum(-np.mean(V[nd]) * a for nd, a in sc)
    bc = sorted(m.barrel_currents(V), reverse=True)
    print(f"{name:36s}: R min {min(R):.3f} max {max(R):.3f} mean {np.mean(R):.3f} mOhm; 80 A loss {loss:.2f} W; vias >1 A {sum(1 for x in bc if x[0] > 1)}, >2 A {sum(1 for x in bc if x[0] > 2)}")

# what-if 4: proposed stack  In3 = GND plane, In4 = +BATT plane, In5 = +BATT plane with the +10V island
m = NetModel('base', '+BATT', h=0.05, add={'In4.Cu': in4, 'In5.Cu': in5})
m.factor(m.pad_nodes('Rsense2', '2'))
R = []
for q in HS:
    nd = m.pad_nodes(q, '3'); V = m.solve([(nd, 1.0)]); R.append(-np.mean(V[nd]) * 1e3)
sc = [(m.pad_nodes(q, '3'), 20.0) for q in ('Q3', 'Q9', 'Q15', 'Q21')]
V = m.solve(sc); loss = sum(-np.mean(V[nd]) * a for nd, a in sc); bc = sorted(m.barrel_currents(V), reverse=True)
print(f"{'PROPOSED +BATT In4+In5 planes':36s}: R min {min(R):.3f} max {max(R):.3f} mean {np.mean(R):.3f} mOhm; 80 A loss {loss:.2f} W; vias >1 A {sum(1 for x in bc if x[0] > 1)}, >2 A {sum(1 for x in bc if x[0] > 2)}")
antig = [Point(v['x'], v['y']).buffer(0.265) for v in b['vias'] if v['net'] != 'GND']
antig += [Point(p['x'], p['y']).buffer(p['drill'] / 2 + 0.25) for f in b['footprints'] for p in f['pads'] if p['drill'] > 0 and p['net'] != 'GND']
in3 = bo.difference(unary_union(antig))
LS = ['Q4', 'Q6', 'Q8', 'Q10', 'Q12', 'Q14', 'Q16', 'Q18', 'Q20', 'Q22', 'Q24', 'Q26']
for name, add in (('GND as routed', None), ('GND + In3 plane', {'In3.Cu': in3})):
    m = NetModel('base', 'GND', h=0.05, add=add)
    m.factor(m.pad_nodes('U24', '2'))
    R = []
    for q in LS:
        nd = m.pad_nodes(q, '1'); V = m.solve([(nd, 1.0)]); R.append(-np.mean(V[nd]) * 1e3)
    sc = [(m.pad_nodes(q, '1'), 20.0) for q in ('Q6', 'Q12', 'Q18', 'Q24')]
    V = m.solve(sc); loss = sum(-np.mean(V[nd]) * a for nd, a in sc); bc = sorted(m.barrel_currents(V), reverse=True)
    print(f"{name:36s}: R min {min(R):.3f} max {max(R):.3f} mean {np.mean(R):.3f} mOhm; 80 A loss {loss:.2f} W; vias >1 A {sum(1 for x in bc if x[0] > 1)}, >2 A {sum(1 for x in bc if x[0] > 2)}, max {bc[0][0]:.2f} A")
