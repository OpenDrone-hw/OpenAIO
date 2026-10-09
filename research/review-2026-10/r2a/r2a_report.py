"""R2a report: number the chosen pattern, compute metrics vs today (34-pad J90/J91 of d81e559), place SWD test pads,
write lga_spec.json and the tables used in LGA_SPEC.md, and draw lga_spec.png.
Usage: python3 r2a_report.py <result.json> [index]"""
import sys, json, math
import r2a_geo as G
import r2a_opt as O
from lr_common import body_envelope, polys, pad_geom
from shapely.geometry import Point, MultiPoint, box
from shapely.ops import unary_union
from shapely import affinity

res = json.load(open(sys.argv[1]))
if isinstance(res, list):
    res = res[int(sys.argv[2]) if len(sys.argv) > 2 else 0]
u7c = json.load(open(G.HERE + '/u7.json'))
u7, u7blk = G.u7_place(u7c['cx'], u7c['cy'], u7c['rot'])
u7['blk'] = u7blk
O.setup(res['ox'], res['oy'], u7)
SITES = [tuple(s) for s in res['sites']]
assert SITES == O.SITES
assign = res['assign']; gmap = res['gmap']; led0 = res['led0']
ATTR = O.ATTR

# ------------------------------------------------------------------ numbering: row-major, top view (Base F.Cu view)
used = [k for k, n in enumerate(assign) if n is not None]
used.sort(key=lambda k: (round(SITES[k][1], 3), round(SITES[k][0], 3)))
num = {k: i + 1 for i, k in enumerate(used)}
rows = sorted(set(round(SITES[k][1], 3) for k in used))
cols = sorted(set(round(SITES[k][0], 3) for k in used))


def role(n):
    if n == 'GND':
        return 'GND'
    if n.startswith('+'):
        return 'PWR'
    return 'SIG'


def short(n):
    return n.split('#')[0]


# core / base endpoint of each net (for the table and the figure), core coords
def core_end(n):
    if n in gmap:
        return G.U2PIN[gmap[n]], f"U2.{G.GPIO_PAD[gmap[n]]} (GPIO{gmap[n]})"
    lab = {'CURR': 'R5.1', 'USB_D+': 'R9.2', 'USB_D-': 'R8.1', 'BUZZER-': 'Q1.3 (drain)', 'LED_STRIP': 'Q2.3 (drain)',
           'PU0RX': 'U2.5 (GPIO3)', 'SWDIO': 'U2.25', 'SWCLK': 'U2.24', '+5V#1': 'J30 (5 V user pad)', '+5V#2': 'J37 (5 V user pad)',
           '+BATT': 'R1.2 (VBAT divider)', '+4v5#1': 'U7.6 (new LP5912-3.3 IN)', '+4v5#2': 'U7.6 (new LP5912-3.3 IN)'}[n]
    return O.CC[n], lab


BLAB = {'CURR': 'U25.6 (INA186 out)', 'SPI0.MISO': 'Card1.7', 'SPI0.SCK': 'Card1.5', 'SPI0.MOSI': 'Card1.3', 'FLASH_CS': 'Card1.2',
        'USB_D+': 'USB1.A6', 'USB_D-': 'USB1.A7', 'MOTOR1': 'R39.1', 'MOTOR2': 'R58.1', 'MOTOR3': 'R77.1', 'MOTOR4': 'R96.1',
        'BUZZER-': 'J29', 'LED_STRIP': 'J20/J21/J31/J32 (nearest)', 'UART0_TX': 'U12.3', 'UART0_RX': 'U12.4', 'UART1_TX': 'U22.27',
        'UART1_RX': 'U22.28', 'PU0RX': 'U12.6', 'SWDIO': 'test pad (new)', 'SWCLK': 'test pad (new)',
        '+4v5#1': 'D2.1/D3.1 (OR)', '+4v5#2': 'D2.1/D3.1 (OR)', '+5V#1': 'L3.2 (U4 out)', '+5V#2': 'L3.2 (U4 out)',
        '+BATT': 'In4/In5 +BATT plane'}


def base_end(n, P):
    be = O.BASE_END[n]
    if be is None:
        return None
    return min(be, key=lambda q: math.dist(P, q))


def seg(n, P, gm=None):
    """straight-line core leg, base leg (mm)."""
    gm = gmap if gm is None else gm
    ce = G.U2PIN[gm[n]] if n in gm else O.CC[n]
    be = base_end(n, P)
    return math.dist(ce, P), (math.dist(P, be) if be is not None else 0.0)


# ------------------------------------------------------------------ today (d81e559 J91/J90)
today = [(p['net'], (p['x'], p['y'])) for p in G.fc['J91']['pads']]
TODAY_GPIO = {k: v for k, v in O.GPIO_CUR.items() if k != 'LED0'}
COMMON = [n for n in O.SIG if n not in ('PU0RX', 'SWDIO', 'SWCLK')]   # the 17 signals that cross today and tomorrow


def mech(pat):
    pts = [p for n, p in pat]
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    g = G.CO.centroid
    return math.dist((cx, cy), (g.x, g.y)), MultiPoint(pts).convex_hull.area / G.CO.area, (cx, cy)


def gnd_dist(pat):
    gs = [p for n, p in pat if n == 'GND']
    return {n: min(math.dist(p, q) for q in gs) for n, p in pat if role(n) != 'GND'}


tpos = {n: p for n, p in today}
t_len = {n: sum(seg(n, tpos[n], TODAY_GPIO)) for n in COMMON}
t_gd = gnd_dist(today)
t_mech = mech(today)

pat = [(assign[k], SITES[k]) for k in used]
npos = {assign[k]: SITES[k] for k in used if assign[k] != 'GND'}
n_len = {n: sum(seg(n, npos[n])) for n in O.SIG}
n_len_fixg = {n: sum(seg(n, npos[n], TODAY_GPIO)) for n in O.SIG}
n_gd = gnd_dist(pat)
n_mech = mech(pat)
direct = {}
for n in COMMON:
    ce = G.U2PIN[TODAY_GPIO[n]] if n in TODAY_GPIO else O.CC[n]
    be = O.BASE_END[n]
    direct[n] = min(math.dist(ce, q) for q in be)

orth = lambda a, b_: abs(math.dist(a, b_) - 2.0) < 1e-3
n_orth = {n: any(orth(p, q) for m, q in pat if m == 'GND') for n, p in pat if role(n) == 'SIG'}

M = dict(
    today=dict(pads=len(today), gnd=sum(1 for n, p in today if n == 'GND'), sig17=sum(t_len.values()),
               gnd_le_pitch=sum(1 for n in COMMON if t_gd[n] <= 2.001), gnd_le_pitch_of=len(COMMON),
               gnd_le_pitch_18=sum(1 for n, p in today if role(n) == 'SIG' and t_gd[n] <= 2.001),
               worst_gnd=max(t_gd[n] for n in COMMON), centroid_off=t_mech[0], hull=t_mech[1]),
    new=dict(pads=len(pat), gnd=sum(1 for n, p in pat if n == 'GND'), sig17=sum(n_len[n] for n in COMMON),
             sig17_fixgpio=sum(n_len_fixg[n] for n in COMMON), sig20=sum(n_len.values()),
             new3={n: n_len[n] for n in ('PU0RX', 'SWDIO', 'SWCLK')},
             gnd_le_pitch=sum(1 for n in O.SIG if n_gd[n] <= 2.001), orth_gnd=sum(n_orth.values()), nsig=len(O.SIG),
             worst_gnd=max(n_gd[n] for n in O.SIG), centroid_off=n_mech[0], hull=n_mech[1], centroid=n_mech[2]),
    lower_bound17=sum(direct.values()),
    per_net={n: dict(today=t_len[n], new=n_len[n], new_fixgpio=n_len_fixg[n], direct=direct[n]) for n in COMMON},
    cost=res['detail'])

# ------------------------------------------------------------------ explicit rule check on the final pattern
P_ = {n: p for n, p in pat}
gset = [p for n, p in pat if n == 'GND']
isg = lambda q: any(math.dist(q, g) < 1e-3 for g in gset)
occupied = lambda q: any(math.dist(q, p) < 1e-3 for n, p in pat)
diag = lambda a, b_: abs(math.dist(a, b_) - 2.0 * math.sqrt(2)) < 1e-3
RULES = {}
RULES['signals_with_orth_GND'] = f"{sum(1 for n in O.SIG if any(orth(P_[n], g) for g in gset))}/{len(O.SIG)}"
RULES['power_with_orth_GND'] = f"{sum(1 for n in O.PWR if any(orth(P_[n], g) for g in gset))}/{len(O.PWR)}"
a_, b_ = P_['USB_D+'], P_['USB_D-']
ends_ = [(2 * a_[0] - b_[0], 2 * a_[1] - b_[1]), (2 * b_[0] - a_[0], 2 * b_[1] - a_[1])]
RULES['usb_pair_adjacent'] = orth(a_, b_)
RULES['usb_gnd_both_ends'] = all(isg(q) for q in ends_)
RULES['motor_orth_to_CURR_USB_BATT'] = [(m, v) for m in O.MOT for v in O.MOT_VICTIM if orth(P_[m], P_[v])]
RULES['motor_diag_to_CURR_USB_BATT'] = [(m, v) for m in O.MOT for v in O.MOT_VICTIM if diag(P_[m], P_[v])]
RULES['batt_orth_neighbours'] = [n for n, p in pat if n != '+BATT' and orth(p, P_['+BATT'])]
RULES['batt_diag_neighbours'] = [n for n, p in pat if n != '+BATT' and diag(p, P_['+BATT'])]
RULES['4v5_pads_adjacent'] = orth(P_['+4v5#1'], P_['+4v5#2'])
RULES['anchors'] = {str(num[k]): v for k, v in ((int(k), v) for k, v in res['anchors'].items())}
RULES['gnd_ratio'] = f"{sum(1 for n, p in pat if n == 'GND')}/{len(pat)}"
RULES['signals_core_via_blocked'] = [short(n) for n, p in pat if n != 'GND' and not O.core_ok(SITES.index(p), short(n))]
RULES['pads_base_via_blocked'] = [str(num[k]) + ':' + short(assign[k]) for k in used if not O.base_ok(k, short(assign[k]))]
RULES['pads_within_0.3mm_of_core_userpad'] = [str(num[k]) + ':' + short(assign[k]) + '@' + '/'.join(r for r, nn in ATTR[k]['heat']) for k in used if ATTR[k]['heat']]
M['rules'] = RULES

# ------------------------------------------------------------------ SWD test pads on Base B.Cu (0.8 mm round)
bb = G.b
obsB = []
for f in bb['footprints']:
    if f['ref'] == 'U24':
        for p in f['pads']:
            if 'B.Cu' in p['polys']:
                obsB.append(polys(p['polys']['B.Cu']).buffer(0.2))
        continue
    if f['side'] == 'B':
        e = body_envelope(f, 'B.Cu')[0]
        if e is not None:
            obsB.append(e.buffer(0.2 if f['ref'] != 'AE2' else 2.0))     # 2 mm keep-out round the chip antenna
freeB = G.BO.buffer(-0.5).difference(unary_union(obsB)).buffer(-0.4)
TP = {}
for n in ('SWDIO', 'SWCLK'):
    P = G.c2b(npos[n])
    q = freeB.exterior.interpolate(0) if False else None
    from shapely.ops import nearest_points
    cand = nearest_points(freeB, Point(P))[0]
    TP[n] = (round(cand.x, 2), round(cand.y, 2), round(math.dist((cand.x, cand.y), P), 2))
# keep the two test pads >= 1.5 mm apart
if math.dist(TP['SWDIO'][:2], TP['SWCLK'][:2]) < 1.5:
    P = G.c2b(npos['SWCLK'])
    from shapely.ops import nearest_points
    fr2 = freeB.difference(Point(TP['SWDIO'][:2]).buffer(1.5))
    cand = nearest_points(fr2, Point(P))[0]
    TP['SWCLK'] = (round(cand.x, 2), round(cand.y, 2), round(math.dist((cand.x, cand.y), P), 2))

# ------------------------------------------------------------------ pad table + JSON
BPADS = [(f['ref'], p['num'], affinity.translate(polys(p['polys']['B.Cu']), -G.OFF[0], -G.OFF[1]), p['net'])
         for f in G.b['footprints'] if f['ref'] != 'U24' for p in f['pads'] if 'B.Cu' in p['polys']]
pads = []
for k in used:
    n = assign[k]; x, y = SITES[k]; bx, by = G.c2b((x, y))
    dx, dy = x - G.O[0], y - G.O[1]
    a = ATTR[k]
    d = dict(pad=str(num[k]), net=short(n), role=role(n), core_xy=[round(x, 4), round(y, 4)], base_xy=[round(bx, 4), round(by, 4)],
             j90_local=[round(dx, 4), round(dy, 4)], j91_lib_local=[round(-dx, 4), round(dy, 4)],
             row=rows.index(round(y, 3)) + 1, col=cols.index(round(x, 3)) + 1)
    if n != 'GND':
        ce, cl = core_end(n)
        be = base_end(n, (x, y))
        cleg, bleg = seg(n, (x, y)) if role(n) == 'SIG' else (math.dist(ce, (x, y)), math.dist((x, y), be) if be else 0.0)
        d.update(core_end=cl, base_end=BLAB[n], core_end_xy_core=[round(ce[0], 3), round(ce[1], 3)],
                 base_end_xy_base=([round(v, 3) for v in G.c2b(be)] if be is not None else None),
                 core_leg_mm=round(cleg, 2), base_leg_mm=round(bleg, 2), nearest_gnd_mm=round(n_gd[n], 2))
    d['anchor'] = res['anchors'].get(str(k), [])
    d['core_via'] = 'not needed (B.Cu GND pour)' if n == 'GND' else ('free' if a['core_ok_any'] else 'on same-net pad')
    bn = short(n)
    d['base_via'] = 'free' if a['base_ok_any'] else ('on same-net B.Cu pad' if bn in a['base_ok_nets'] else 'BLOCKED: move B.Cu part')
    d['base_bcu_under'] = a['under_base']
    if not (a['base_ok_any'] or bn in a['base_ok_nets']):
        d['base_via_blockers'] = sorted(set(f"{r}.{pn}" for r, pn, g, nn in BPADS if nn != bn and g.distance(Point(x, y)) < G.VIA_OFF + G.BASE_CLR + G.VIA_D / 2))
    d['base_vias_to_clear'] = sorted(set(v[0] for v in a['base_vias'] if v[0] != bn))
    d['core_userpad_within_0.3mm'] = [r for r, nn in a['heat']]
    pads.append(d)

gchg = {f: (O.GPIO_CUR[f], g) for f, g in gmap.items() if g != O.GPIO_CUR[f]}
if led0 != O.GPIO_CUR['LED0']:
    gchg['LED0'] = (O.GPIO_CUR['LED0'], led0)
used_g = set(gmap.values()) | {led0}
spare = [g for g in O.POOL if g not in used_g]

vtx = json.load(open(G.HERE + '/vtx_choice.json')) if __import__('os').path.exists(G.HERE + '/vtx_choice.json') else None
out = dict(
    source=dict(baseline='d81e559', core_board='OpenAIO-Core.kicad_pcb', base_board='OpenAIO-Base.kicad_pcb',
                offset_base_minus_core=[round(G.OFF[0], 4), round(G.OFF[1], 4)],
                core_origin_J91=[round(G.O[0], 6), round(G.O[1], 6)], base_origin_J90=[round(G.fb['J90']['x'], 6), round(G.fb['J90']['y'], 6)],
                note='core_xy/base_xy are absolute board coordinates. j90_local = footprint-local for the Base land (F.Cu, rot 0). '
                     'j91_lib_local = footprint-local as stored in the library for the Core pads footprint, which is placed on B.Cu '
                     'at rot 180 (flip mirrors x): board position = J91 origin + (x, y) of j90_local.'),
    grid=dict(pitch=2.0, pad_diameter=1.0, edge_clearance_min=0.35, offset_from_origin=[res['ox'], res['oy']], sites_inside=len(SITES)),
    pads=pads,
    gpio=dict(map={f: g for f, g in gmap.items()}, led0=led0, changes={f: list(v) for f, v in gchg.items()}, spare_in_pool=spare),
    u7=dict(center_core=[round(u7c['cx'], 3), round(u7c['cy'], 3)], rot_search=u7c['rot'],
            pins={k: [round(v[0], 3), round(v[1], 3)] for k, v in u7.items() if k != 'blk'},
            block_bounds=[round(v, 3) for v in u7blk.bounds],
            kicad=dict(U7=dict(part='LP5912-3.3DRVR (C524780), WSON-6-1EP 2x2', at=[round(u7c['cx'], 3), round(u7c['cy'], 3)], rot=180,
                               pin1_OUT=[round(u7['OUT'][0], 3), round(u7['OUT'][1], 3)], pin6_IN=[round(u7['IN'][0], 3), round(u7['IN'][1], 3)],
                               pin4_EN=[round(u7['EN'][0], 3), round(u7['EN'][1], 3)], note='EN (pin 4) tied to IN as today; EP to GND'),
                       CIN=dict(part='1 uF 25 V 0402 CL05A105KA5NQNC (C52923)', at=[round(u7['CIN'][0], 3), round(u7['CIN'][1], 3)], rot=90,
                                pad1='+4v5 (next to pin 6)', pad2='GND'),
                       COUT=dict(part='1 uF 25 V 0402 CL05A105KA5NQNC (C52923); C15 4.7 uF at VREG_VIN stays', at=[round(u7['COUT'][0], 3), round(u7['COUT'][1], 3)], rot=90,
                                 pad1='+3.3V (next to pin 1)', pad2='GND'))),
    swd_testpads_base=TP,
    metrics=M)
if vtx:
    out['vtx_pads_base'] = vtx
json.dump(out, open(G.HERE + '/lga_spec.json', 'w'), indent=1, default=float)
print(json.dumps(M, indent=1, default=float))
print('GPIO changes', gchg, 'LED0', led0, 'spare', spare)
print(json.dumps(RULES, indent=0))
print('SWD TP', TP)
for d in pads:
    print(d['pad'], d['net'], d['core_xy'], d['base_xy'], d.get('core_end', ''), d.get('base_end', ''), d.get('core_leg_mm', ''),
          d.get('base_leg_mm', ''), d['anchor'], d['core_via'], d['base_via'], d.get('base_via_blockers'), d['base_vias_to_clear'], d['core_userpad_within_0.3mm'])
