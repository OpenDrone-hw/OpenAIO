"""Current-sense (INA186 U25 across Rsense2 0.2 mOhm) Kelvin check: how much plane drop the sense pins pick up.
/CSA+ solved with the battery pad at 0 V and 80 A drawn at the shunt pad 1; +BATT solved with the shunt pad 2 at 0 V and
4 x 20 A drawn at one high-side drain per motor. Error = sense-pin potential minus shunt-pad potential, vs 16 mV true signal."""
import numpy as np
from lr_dc import *
from lr_common import load
b = load('base')
U25 = [f for f in b['footprints'] if f['ref'] == 'U25'][0]
print('U25 at', U25['x'], U25['y'], U25['side'], [(p['num'], p['net'], round(p['x'], 2), round(p['y'], 2)) for p in U25['pads']])
I = 80.0
m = NetModel('base', '/CSA+', h=0.05)
m.factor(m.pad_nodes('U24', '1'))
sh = m.pad_nodes('Rsense2', '1')
V = m.solve([(sh, I)])
v_sh = np.mean(V[sh]); v_in = np.mean(V[m.pad_nodes('U25', '4')])
v_sh_min, v_sh_max = V[sh].min(), V[sh].max()
print(f'/CSA+: shunt pad1 mean {v_sh*1e3:.2f} mV (span {v_sh_min*1e3:.2f}..{v_sh_max*1e3:.2f}), U25.+IN {v_in*1e3:.2f} mV -> +IN picks up {(v_in - v_sh)*1e3:+.2f} mV vs pad mean')
m2 = NetModel('base', '+BATT', h=0.05)
m2.factor(m2.pad_nodes('Rsense2', '2'))
sinks = [(m2.pad_nodes(q, '3'), 20.0) for q in ('Q3', 'Q9', 'Q15', 'Q21')]
V2 = m2.solve(sinks)
sh2 = m2.pad_nodes('Rsense2', '2'); vin2 = np.mean(V2[m2.pad_nodes('U25', '5')])
print(f'+BATT: shunt pad2 0 mV (Dirichlet), U25.-IN {vin2*1e3:.2f} mV')
true = 0.2e-3 * I
extra = (v_in - v_sh) - vin2   # V(+IN)-V(-IN) = true + (v_in - v_sh) - vin2
print(f'true shunt drop {true*1e3:.1f} mV; INA186 sees {(true+extra)*1e3:.2f} mV -> copper error {extra*1e3:+.2f} mV = {100*extra/true:+.1f} % (phase-A HS of all 4 motors at 20 A)')
# transfer resistance from each high-side drain current to the -IN pick-up (depends on which FETs conduct)
tr = []
for q in ('Q3','Q5','Q7','Q9','Q11','Q13','Q15','Q17','Q19','Q21','Q23','Q25'):
    Vq = m2.solve([(m2.pad_nodes(q, '3'), 1.0)])
    tr.append((q, -np.mean(Vq[m2.pad_nodes('U25', '5')]) * 1e3))
print('-IN pick-up per amp drawn by each high-side FET (mOhm, vs 0.2 mOhm shunt):', [(q, round(r, 4)) for q, r in tr])
lo, hi = min(r for _, r in tr), max(r for _, r in tr)
print(f'range {lo:.3f}..{hi:.3f} mOhm = {100*lo/0.2:.0f}..{100*hi/0.2:.0f} % of the shunt: the reading depends on which phase conducts')
