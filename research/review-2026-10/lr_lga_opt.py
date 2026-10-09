"""LGA pin-assignment optimisation (simulated annealing) over
  A) the current 34 pad positions (keep 11 GND / 5 power / 18 signal), and
  B) regular 2.0 mm and 1.6 mm grids inside the Core outline (choose sites + assignment),
cost = sum over nets of straight-line |core_end - pad| + |pad - base_end| (base coords)
     + 4 mm penalty per mm a signal pad is farther than 2.0 mm (B: 1 pitch) from its nearest GND pad
     + 3 mm penalty for each MOTOR pad orthogonally adjacent to CURR/USB/+BATT (aggressor next to victim)
     + 30 mm penalty if USB_D+ and USB_D- are not on neighbouring pads (<= 1.45 pitch).
Reads lr_lga.json. Prints current vs best and writes lr_lga_opt.json."""
import json, math, random, itertools
from lr_common import *

rows = json.load(open('lr_lga.json'))
c = load('core'); b = load('base')
fpc = {f['ref']: f for f in c['footprints']}
fpb = {f['ref']: f for f in b['footprints']}


def padxy(fps, ref, num, core=False):
    for p in fps[ref]['pads']:
        if p['num'] == num:
            return (p['x'] + OFF[0], p['y'] + OFF[1]) if core else (p['x'], p['y'])


def cen(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


# endpoints: (core point, base point, weight)
NETS = {}
for r in rows:
    if r['kind'] == 'SIG':
        NETS[r['net']] = ((r['ce']['x'], r['ce']['y']), (r['be']['x'], r['be']['y']), 1.0)
U2c = (fpc['U2']['x'] + OFF[0], fpc['U2']['y'] + OFF[1])
NETS['+3.3V'] = (U2c, padxy(fpb, 'U7', '1'), 1.0)
NETS['+10V'] = (cen([padxy(fpc, 'J41', '1', True), padxy(fpc, 'J51', '1', True)]), padxy(fpb, 'L2', '2'), 1.0)
NETS['+4v5'] = (padxy(fpc, 'U6', '6', True), padxy(fpb, 'D3', '1'), 1.0)
NETS['+5V'] = (cen([padxy(fpc, 'J30', '1', True), padxy(fpc, 'J37', '1', True)]), padxy(fpb, 'L3', '2'), 1.0)
NETS['+BATT'] = (padxy(fpc, 'R1', '2', True), None, 1.0)  # base side: F.Cu +BATT pour under the whole core
SIG = [r['net'] for r in rows if r['kind'] == 'SIG']
PWR = ['+3.3V', '+10V', '+4v5', '+5V', '+BATT']
MOT = {'MOTOR1', 'MOTOR2', 'MOTOR3', 'MOTOR4'}
VICT = {'CURR', 'USB_D+', 'USB_D-'}


def netcost(n, P):
    ce, be, w = NETS[n]
    s = math.dist(ce, P)
    if be is not None:
        s += math.dist(P, be)
    return w * s


def evaluate(assign, sites, pitch=2.0, detail=False):
    """assign: list net-or-'GND'-or-None per site index."""
    g = [sites[i] for i, n in enumerate(assign) if n == 'GND']
    wl = 0.0; pen = 0.0; sigwl = 0.0
    pos = {n: sites[i] for i, n in enumerate(assign) if n not in (None, 'GND')}
    for n, P in pos.items():
        k = netcost(n, P)
        wl += k
        if n in SIG:
            sigwl += k
            dg = min(math.dist(P, q) for q in g) if g else 99
            pen += 4.0 * max(0.0, dg - pitch * 1.001)
    if 'USB_D+' in pos and 'USB_D-' in pos and math.dist(pos['USB_D+'], pos['USB_D-']) > pitch * 1.45:
        pen += 30.0   # USB pair must sit on neighbouring pads (orthogonal or diagonal)
    for m in MOT:
        if m in pos:
            for v in VICT | {'+BATT'}:
                if v in pos and math.dist(pos[m], pos[v]) <= pitch * 1.01:
                    pen += 3.0
    if detail:
        return wl, sigwl, pen
    return wl + pen


def anneal(sites, nets, ngnd, pitch, iters=200000, seed=0, init=None):
    rnd = random.Random(seed)
    nslots = len(sites)
    if init is None:
        a = list(nets) + ['GND'] * ngnd + [None] * (nslots - len(nets) - ngnd)
        rnd.shuffle(a)
    else:
        a = list(init)
    cur = evaluate(a, sites, pitch)
    best = (cur, list(a))
    T0, T1 = 8.0, 0.02
    for it in range(iters):
        T = T0 * (T1 / T0) ** (it / iters)
        i, j = rnd.randrange(nslots), rnd.randrange(nslots)
        if a[i] == a[j]:
            continue
        a[i], a[j] = a[j], a[i]
        new = evaluate(a, sites, pitch)
        if new <= cur or rnd.random() < math.exp((cur - new) / T):
            cur = new
            if cur < best[0]:
                best = (cur, list(a))
        else:
            a[i], a[j] = a[j], a[i]
    return best


out = {}
# ---------- A: current positions
sites = [(r['x'], r['y']) for r in rows]
cur_assign = [r['net'] for r in rows]
wl0, sig0, pen0 = evaluate(cur_assign, sites, 2.0, detail=True)
print(f'A0 current assignment: total geo length {wl0:.1f} mm (signals {sig0:.1f}), penalty {pen0:.1f}')
bestA = None
for s in range(6):
    r_ = anneal(sites, SIG + PWR, 11, 2.0, 150000, seed=s)
    if bestA is None or r_[0] < bestA[0]:
        bestA = r_
wl1, sig1, pen1 = evaluate(bestA[1], sites, 2.0, detail=True)
print(f'A1 optimised on current pads: total {wl1:.1f} mm (signals {sig1:.1f}), penalty {pen1:.1f}; saves {wl0 - wl1:.1f} mm total, {sig0 - sig1:.1f} mm signals')
moves = []
for i, n in enumerate(bestA[1]):
    if n != cur_assign[i]:
        moves.append((rows[i]['num'], cur_assign[i], n))
print('  pad: current -> proposed')
for m in moves:
    print('   ', m)
out['A'] = dict(current=dict(total=wl0, sig=sig0, pen=pen0), best=dict(total=wl1, sig=sig1, pen=pen1),
                assign={rows[i]['num']: n for i, n in enumerate(bestA[1])})

# ---------- B: regular grids inside the Core outline
co = outline(c)
from shapely import affinity
cob = affinity.translate(co, *OFF)
for pitch, padd in ((2.0, 1.0), (1.6, 0.9), (1.5, 0.8)):
    inner = cob.buffer(-(padd / 2 + 0.35))  # pad edge >= 0.35 mm from the Core edge
    x0, y0, x1, y1 = cob.bounds
    best = None
    for ox, oy in itertools.product([0, pitch / 2], [0, pitch / 2]):
        g = []
        y = y0 + oy
        while y <= y1:
            x = x0 + ox
            while x <= x1:
                if inner.contains(Point(x, y)):
                    g.append((round(x, 3), round(y, 3)))
                x += pitch
            y += pitch
        if best is None or len(g) > len(best):
            best = g
    gsites = best
    for npads, ngnd in ((34, 11), (34, 13), (40, 17), (46, 23)):
        if npads > len(gsites):
            continue
        rb = None
        for s in range(4):
            r_ = anneal(gsites, SIG + PWR, ngnd, pitch, 200000, seed=s)
            if rb is None or r_[0] < rb[0]:
                rb = r_
        wl, sg, pen = evaluate(rb[1], gsites, pitch, detail=True)
        nused = sum(1 for n in rb[1] if n is not None)
        print(f'B grid {pitch} mm ({len(gsites)} sites), {npads} pads used={nused}, {ngnd} GND: total {wl:.1f} mm (signals {sg:.1f}), penalty {pen:.1f}; vs current saves {wl0 - wl:.1f} mm total, {sig0 - sg:.1f} mm signals')
        out[f'B_{pitch}_{npads}_{ngnd}'] = dict(sites=len(gsites), total=wl, sig=sg, pen=pen,
                                                 assign=[(gsites[i], n) for i, n in enumerate(rb[1]) if n is not None])
json.dump(out, open('lr_lga_opt.json', 'w'), indent=1)
