"""Markdown table of the current vs A1 (optimised on current pads) LGA assignment with per-pad geometry cost."""
import json, math
rows = json.load(open('lr_lga.json')); opt = json.load(open('lr_lga_opt.json'))
exec(open('lr_lga_opt.py').read().split('out = {}')[0])
A1 = opt['A']['assign']
pos = {r['num']: (r['x'], r['y']) for r in rows}
g_cur = [pos[k] for k, r in ((r['num'], r) for r in rows) if r['net'] == 'GND']
g_new = [pos[k] for k, n in A1.items() if n == 'GND']
print('| pad | (x,y) base | current | geo mm | GND mm | A1 proposal | geo mm | GND mm |')
print('|---|---|---|---|---|---|---|---|')
for r in rows:
    k = r['num']; P = pos[k]
    def cell(n, g):
        if n == 'GND':
            return 'GND', '', ''
        cost = netcost(n, P)
        dg = min(math.dist(P, q) for q in g)
        return n, f'{cost:.1f}', f'{dg:.1f}' if n in SIG else ''
    a = cell(r['net'], g_cur); bb = cell(A1[k], g_new)
    print(f"| {k} | ({P[0]:.2f},{P[1]:.2f}) | {a[0]} | {a[1]} | {a[2]} | {bb[0]} | {bb[1]} | {bb[2]} |")
