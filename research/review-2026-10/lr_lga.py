"""LGA interface: per-net routed length on both boards, vias, detour, GND pad distribution.
Writes lr_lga.json (used by lr_lga_opt.py) and prints tables.
Coordinates reported in Base coordinates (core + OFF)."""
import json, math, collections
from lr_common import *
import lr_graph

c = load('core'); b = load('base')
J91 = [f for f in c['footprints'] if f['ref'] == 'J91'][0]
J90 = [f for f in b['footprints'] if f['ref'] == 'J90'][0]
pads = {p['num']: p for p in J90['pads']}
cpads = {p['num']: p for p in J91['pads']}
# main endpoint preference per net (core / base): first matching prefix wins
PREF_CORE = ['U2', 'R5', 'R9', 'R8', 'Q1', 'Q2', 'R1', 'U6', 'R14', 'J41', 'C11']
PREF_BASE = {'USB_D+': 'USB1', 'USB_D-': 'USB1', 'UART1_RX': 'U22', 'UART1_TX': 'U22', 'LED_STRIP': None}


def endpoints(d, net, skip):
    return [(f['ref'], p) for f in d['footprints'] for p in f['pads'] if p['net'] == net and f['ref'] != skip]


rows = []
for num, cp in sorted(cpads.items(), key=lambda t: int(t[0])):
    net = cp['net']
    bp = pads[num]
    row = dict(num=num, net=net, x=bp['x'], y=bp['y'])
    if net == 'GND' or net.startswith('+'):
        row['kind'] = 'GND' if net == 'GND' else 'PWR'
        rows.append(row)
        continue
    row['kind'] = 'SIG'
    for side, d, bn, J, ref in (('core', c, 'core', J91, 'J91'), ('base', b, 'base', J90, 'J90')):
        G = lr_graph.build(d, bn, net)
        src = ('PAD', ref, num)
        eps = endpoints(d, net, ref)
        res = []
        for r, p in eps:
            pi = lr_graph.path_info(G, src, ('PAD', r, p['num']))
            x, y = p['x'], p['y']
            if side == 'core':
                x, y = x + OFF[0], y + OFF[1]
            res.append(dict(ref=r, pin=p['num'], x=x, y=y, **({k: v for k, v in pi.items() if k != 'path'} if pi else {'len': None})))
        row[side + '_tree'] = lr_graph.tree_len(G)
        row[side + '_eps'] = res
    # main endpoints
    def pick(eps, pref):
        for pr in pref:
            for e in eps:
                if e['ref'].startswith(pr):
                    return e
        return eps[0] if eps else None
    ce = pick(row['core_eps'], PREF_CORE)
    bpref = PREF_BASE.get(net, 'X')
    if bpref is None:   # LED_STRIP: nearest base endpoint
        be = min(row['base_eps'], key=lambda e: math.hypot(e['x'] - ce['x'], e['y'] - ce['y']))
    else:
        be = pick(row['base_eps'], [bpref] if bpref != 'X' else ['U', 'Card', 'USB', 'J', 'Q', 'R', 'C'])
    row['ce'] = ce; row['be'] = be
    direct = math.hypot(ce['x'] - be['x'], ce['y'] - be['y'])
    via_pad = math.hypot(ce['x'] - bp['x'], ce['y'] - bp['y']) + math.hypot(bp['x'] - be['x'], bp['y'] - be['y'])
    routed = (ce['len'] or 0) + (be['len'] or 0)
    row.update(direct=direct, via_pad=via_pad, routed=routed, detour=routed - direct, geo_detour=via_pad - direct,
               vias=(ce.get('vias') or 0) + (be.get('vias') or 0))
    rows.append(row)

# GND distribution
gnd = [r for r in rows if r['kind'] == 'GND']
for r in rows:
    ds = sorted(math.hypot(r['x'] - g['x'], r['y'] - g['y']) for g in gnd if g is not r)
    r['gnd_nearest'] = ds[0]
    r['gnd_within_2p9'] = sum(1 for x in ds if x <= 2.9)
    others = [o for o in rows if o is not r]
    r['nearest_any'] = min(math.hypot(r['x'] - o['x'], r['y'] - o['y']) for o in others)
    nb = sorted(others, key=lambda o: math.hypot(r['x'] - o['x'], r['y'] - o['y']))[:3]
    r['neighbours'] = [(o['net'], round(math.hypot(r['x'] - o['x'], r['y'] - o['y']), 2)) for o in nb]

json.dump(rows, open('lr_lga.json', 'w'), indent=1, default=str)

print('LGA pad pattern: %d pads, %d GND, %d power, %d signal' % (len(rows), len(gnd), sum(r['kind'] == 'PWR' for r in rows),
                                                                  sum(r['kind'] == 'SIG' for r in rows)))
print('\n| pad | net | core end | core len mm | core vias | base end | base len mm | base vias | routed total | direct | detour | pad-geo detour | nearest GND mm | GND <=2.9 mm | nearest neighbours |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
tot = collections.Counter()
for r in rows:
    if r['kind'] != 'SIG':
        continue
    ce, be = r['ce'], r['be']
    print(f"| {r['num']} | {r['net']} | {ce['ref']}.{ce['pin']} | {ce['len']:.1f} | {ce.get('vias')} | {be['ref']}.{be['pin']} | {be['len']:.1f} | {be.get('vias')} | {r['routed']:.1f} | {r['direct']:.1f} | {r['detour']:.1f} | {r['geo_detour']:.1f} | {r['gnd_nearest']:.2f} | {r['gnd_within_2p9']} | {r['neighbours']} |")
    tot['routed'] += r['routed']; tot['direct'] += r['direct']; tot['detour'] += r['detour']; tot['geo'] += r['geo_detour']
    tot['vias'] += r['vias']
print(f"\nTOTAL signals: routed {tot['routed']:.1f} mm, direct {tot['direct']:.1f} mm, detour {tot['detour']:.1f} mm, pad-geometry detour {tot['geo']:.1f} mm, vias {tot['vias']}")
print('\nPower / GND pads:')
for r in rows:
    if r['kind'] != 'SIG':
        print(f"  {r['num']:>3} {r['net']:8s} ({r['x']:.2f},{r['y']:.2f}) nearest GND {r['gnd_nearest']:.2f} mm; neighbours {r['neighbours']}")
# extra endpoints
print('\nAll endpoints (multi-drop nets):')
for r in rows:
    if r['kind'] == 'SIG' and (len(r['core_eps']) > 1 or len(r['base_eps']) > 1):
        print(' ', r['net'], 'core', [(e['ref'], (round(e['len'], 1) if e['len'] is not None else None), e.get('vias')) for e in r['core_eps']],
              'base', [(e['ref'], (round(e['len'], 1) if e['len'] is not None else None), e.get('vias')) for e in r['base_eps']],
              'tree core %.1f base %.1f' % (r['core_tree'], r['base_tree']))
