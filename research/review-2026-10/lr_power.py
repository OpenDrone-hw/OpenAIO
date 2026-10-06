"""Power-path DC analysis on both boards (lr_dc.py solver, h = 0.05 mm, refilled zones).
For each rail: source pad(s) held at 0 V; per-sink path resistance (1 A alone); load scenario with all sinks
at their assumed currents: drop, isopotential bottleneck cross-section (mid 10-90 % of the potential range),
current share per layer at that cut, vias in the cut, hottest via, peak in-plane current density.
Assumed currents are stated in SCEN below. Writes lr_power.json and prints markdown tables."""
import sys, json, time
import numpy as np
from lr_dc import *

H = 0.05
I_MOTOR = 20.0   # A per motor channel (assumption: 20 A continuous class, 6S toothpick ESC)

b = load('base'); c = load('core')
fpb = {f['ref']: f for f in b['footprints']}
HS = ['Q3', 'Q5', 'Q7', 'Q9', 'Q11', 'Q13', 'Q15', 'Q17', 'Q19', 'Q21', 'Q23', 'Q25']   # F.Cu, drain = +BATT
LS = ['Q4', 'Q6', 'Q8', 'Q10', 'Q12', 'Q14', 'Q16', 'Q18', 'Q20', 'Q22', 'Q24', 'Q26']  # B.Cu, source = GND
MOTOR_OF = {}
for q in HS + LS:
    ph = [p['net'] for p in fpb[q]['pads'] if p['net'].startswith('/') and len(p['net']) == 3][0]
    MOTOR_OF[q] = ph
CH = {k: [q for q in HS if MOTOR_OF[q][1] == k] for k in '1234'}
CHL = {k: [q for q in LS if MOTOR_OF[q][1] == k] for k in '1234'}


def pads_of(d, net, refprefix=('U', 'Card', 'J', 'D')):
    out = []
    for f in d['footprints']:
        if f['ref'].startswith(refprefix):
            for p in f['pads']:
                if p['net'] == net:
                    out.append((f['ref'], p['num']))
    return sorted(set(out))


def run(board, net, sources, sinks, scen_note=''):
    t = time.time()
    m = NetModel(board, net, h=H)
    src = []
    for r, n in sources:
        src += m.pad_nodes(r, n)
    m.factor(src)
    res = dict(board=board, net=net, nodes=m.N, floating=m.floating, layers=m.layers, sinks=[], note=scen_note)
    scen = []
    for label, pads, amps in sinks:
        nd = []
        for r, n in pads:
            nd += m.pad_nodes(r, n)
        if not nd:
            res['sinks'].append(dict(label=label, err='no copper nodes'))
            continue
        if not np.all(m.live[nd]):
            res['sinks'].append(dict(label=label, err='NOT CONNECTED to source copper'))
            continue
        V = m.solve([(nd, 1.0)])
        R = float(-np.mean(V[nd]))
        cs = m.cut_stats(-V, 0.0, float(np.min(-V[nd])))
        bc = sorted(m.barrel_currents(V), reverse=True)
        nvia_10 = sum(1 for x in bc if x[0] > 0.10)   # vias carrying >10 % of the path current
        res['sinks'].append(dict(label=label, R_mohm=R * 1e3, amps=amps, cut_mm2=cs['min_area'], cut_loc=cs['loc'],
                                 cut_layers={k: round(v, 4) for k, v in cs['per_layer_area'].items()},
                                 cut_share={k: round(v, 3) for k, v in cs['per_layer_current'].items()},
                                 cut_vias=cs['vias_in_cut'], top_via_frac=bc[0][0] if bc else 0,
                                 top_via_xy=(bc[0][1], bc[0][2]) if bc else None, vias_gt10pct=nvia_10))
        scen.append((nd, amps))
    if scen:
        V = m.solve(scen)
        tot = sum(a for _, a in scen)
        bc = sorted(m.barrel_currents(V), reverse=True)
        J = m.layer_current_density(V)
        drops = [float(-np.mean(V[nd])) for nd, _ in scen]
        res['scenario'] = dict(total_A=tot, max_drop_mV=max(drops) * 1e3, loss_W=float(sum(-np.mean(V[nd]) * a for nd, a in scen)),
                               top_vias=[(round(x[0], 3), round(x[1], 2), round(x[2], 2), x[3], x[4]) for x in bc[:5]],
                               vias_over_1A=sum(1 for x in bc if x[0] > 1.0), vias_over_2A=sum(1 for x in bc if x[0] > 2.0),
                               peakJ={k: (round(v[0], 1), round(v[1], 2), round(v[2], 2)) for k, v in J.items()})
    res['t'] = time.time() - t
    return res


R = []
# ---------------- BASE
R.append(run('base', '/CSA+', [('U24', '1')], [('battery pad -> shunt', [('Rsense2', '1')], 4 * I_MOTOR)],
             '4 motors x 20 A'))
sinks = [(f'{q} drain (M{MOTOR_OF[q][1]} {MOTOR_OF[q][2]})', [(q, '3')], I_MOTOR if MOTOR_OF[q][2] == 'A' else 0.0) for q in HS]
sinks = [s for s in sinks if s[2] > 0] + [(s[0], s[1], 1e-9) for s in sinks if s[2] == 0]
R.append(run('base', '+BATT', [('Rsense2', '2')], sinks, 'phase A high side of each motor at 20 A (80 A)'))
# phase nodes: motor pad is the source; HS source pins and LS drain are sinks
for ph in sorted(set(MOTOR_OF.values())):
    hs = [q for q in HS if MOTOR_OF[q] == ph][0]; ls = [q for q in LS if MOTOR_OF[q] == ph][0]
    upad = [p['num'] for p in fpb['U24']['pads'] if p['net'] == ph][0]
    R.append(run('base', ph, [('U24', upad)], [(f'{hs} source (HS on)', [(hs, '1')], I_MOTOR),
                                                [f'{ls} drain (LS on)', [(ls, '3')], 1e-9]], '20 A, HS conducting'))
sinks = [(f'{q} source (M{MOTOR_OF[q][1]} {MOTOR_OF[q][2]})', [(q, '1')], I_MOTOR if MOTOR_OF[q][2] == 'B' else 1e-9) for q in LS]
R.append(run('base', 'GND', [('U24', '2')], sinks, 'phase B low side of each motor at 20 A (80 A return)'))
# +10V: U3 output inductor -> 4 gate drivers + LGA pad 7 (VTX 1.5 A)
drv = [('U14', '4'), ('U16', '4'), ('U18', '4'), ('U20', '4')]
R.append(run('base', '+10V', [('L2', '2')], [(f'{r}.VCC', [(r, n)], 0.02) for r, n in drv] +
             [('LGA J90.7 (to core VTX)', [('J90', '7')], 1.5), ('SH6 U12.1 (DJI)', [('U12', '1')], 1e-9)],
             'VTX 1.5 A via LGA + 4 x 20 mA drivers'))
R.append(run('base', '+5V', [('L3', '2')], [('LGA J90.14', [('J90', '14')], 1.0), ('D2 anode (->+4v5)', [('D2', '2')], 0.6)] +
             [(f'{r} pad', [(r, '1')], 0.25) for r in ('J15', 'J16', 'J24', 'J25', 'J33')], '1 A to core, 0.6 A to +4v5, 5 x 0.25 A pads'))
R.append(run('base', '+4v5', [('D2', '1'), ('D3', '1')], [('U7.IN (FC 3.3 V LDO)', [('U7', '6')], 0.2),
                                                         ('U23.IN (RX 3.3 V LDO)', [('U23', '4')], 0.45),
                                                         ('LGA J90.12', [('J90', '12')], 0.15)], 'LDO input currents'))
sinks3 = []
for r, n in pads_of(b, '+3V3', ('U', 'Card')):
    if r == 'U23':
        continue
    amps = {'U22': 0.35 / 4, 'U21': 0.12 / 3, 'Card1': 0.1}.get(r, 0.005)
    sinks3.append((f'{r}.{n}', [(r, n)], amps))
R.append(run('base', '+3V3', [('U23', '1')], sinks3, 'ESP32-C3 0.35 A, SX1281 0.12 A, SD 0.1 A, others 5 mA/pin'))
R.append(run('base', '+3.3V', [('U7', '1')], [('LGA J90.8 (whole FC)', [('J90', '8')], 0.15)], 'core 150 mA'))
R.append(run('base', '+5V_USB', [('USB1', 'A4'), ('USB1', 'A9')], [('D3 anode', [('D3', '2')], 0.5)], 'USB 0.5 A'))
# ---------------- CORE
cf = {f['ref']: f for f in c['footprints']}
R.append(run('core', '+10V', [('J91', '7')], [('J41 VTX pad', [('J41', '1')], 0.75), ('J51 VTX pad', [('J51', '1')], 0.75)], 'VTX 1.5 A'))
R.append(run('core', '+5V', [('J91', '14')], [('J30', [('J30', '1')], 0.5), ('J37', [('J37', '1')], 0.5), ('R14', [('R14', '1')], 1e-9)], '1 A'))
R.append(run('core', '+4v5', [('J91', '12')], [('U6.IN', [('U6', '6')], 0.02), ('J42', [('J42', '1')], 0.1), ('J52', [('J52', '1')], 0.1)], ''))
s33 = [(f'{r}.{n}', [(r, n)], 0.15 / 8 if r == 'U2' else 0.005) for r, n in pads_of(c, '+3.3V', ('U',))]
R.append(run('core', '+3.3V', [('J91', '8')], s33, '150 mA total'))
gpads = [p['num'] for p in cf['J91']['pads'] if p['net'] == 'GND']
vtxg = [(f['ref'], p['num']) for f in c['footprints'] if f['ref'].startswith('J') and f['ref'] != 'J91' for p in f['pads'] if p['net'] == 'GND']
R.append(run('core', 'GND', [('J91', n) for n in gpads], [(f'{r} GND pad', [(r, n)], 1.5 / len(vtxg)) for r, n in vtxg], 'VTX/cam return 1.5 A'))
json.dump(R, open('lr_power.json', 'w'), indent=1, default=float)

for r in R:
    print(f"\n### {r['board']} {r['net']}  ({r['note']}; {r['nodes']} nodes, floating cells {r['floating']}, layers {','.join(l.replace('.Cu','') for l in r['layers'])})")
    print('| sink | R mOhm | bottleneck mm2 (=1oz mm) | at (x,y) | vias in cut | layer share at cut | hottest via share |')
    print('|---|---|---|---|---|---|---|')
    for s in r['sinks']:
        if 'err' in s:
            print(f"| {s['label']} | {s['err']} |"); continue
        share = ', '.join(f"{k.replace('.Cu','')} {v:.0%}" for k, v in sorted(s['cut_share'].items(), key=lambda t: -t[1]) if v > 0.02)
        print(f"| {s['label']} | {s['R_mohm']:.3f} | {s['cut_mm2']:.4f} ({s['cut_mm2']/0.035:.2f}) | ({s['cut_loc'][0]:.1f},{s['cut_loc'][1]:.1f}) | {s['cut_vias']} | {share} | {s['top_via_frac']:.0%} |")
    if 'scenario' in r:
        sc = r['scenario']
        print(f"scenario {sc['total_A']:.2f} A: max drop {sc['max_drop_mV']:.1f} mV, loss {sc['loss_W']:.3f} W, vias >1 A: {sc['vias_over_1A']}, >2 A: {sc['vias_over_2A']}, top vias (A,x,y,drill,type) {sc['top_vias'][:3]}")
        print(f"  peak in-plane J (A/mm2, x, y): {sc['peakJ']}")
