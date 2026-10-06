"""R2a geometry: shared helpers, endpoints, U7 placement, site grid and per-site attributes.
All internal coordinates are CORE coordinates (OpenAIO-Core.kicad_pcb). base = core + OFF (no mirror).
Reads the review dumps lr_core.json / lr_base.json (d81e559, zones refilled) through lr_common."""
import sys, os, json, math, itertools
REV = '/tmp/claude-0/-home-user-OpenAIO/08e5d1e0-9b8c-55cb-abfb-7d7e9f538e35/scratchpad/review'
sys.path.insert(0, REV)
from lr_common import load, outline, pad_geom, body_envelope, polys, OFF   # noqa: E402
from shapely.geometry import Point, Polygon, box, MultiPoint                # noqa: E402
from shapely.ops import unary_union                                         # noqa: E402
from shapely import affinity                                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
c = load('core'); b = load('base')
fc = {f['ref']: f for f in c['footprints']}
fb = {f['ref']: f for f in b['footprints']}
CO = outline(c)                                  # Core outline, core coords
BO = outline(b)                                  # Base outline, base coords
O = (fc['J91']['x'], fc['J91']['y'])             # J91 origin (core) == J90 origin (base) - OFF

PITCH, PAD_D, EDGE = 2.0, 1.0, 0.35
VIA_D = 0.35
VIA_OFF = PAD_D / 2 - VIA_D / 2                  # via centre may sit 0.325 mm off the pad centre (POFV via-in-pad)
CORE_CLR, BASE_CLR = 0.09, 0.16                  # Core line standard; Base 2 oz outer
REMOVED_CORE = {'J41', 'J51'}                    # S2: +10V VTX pads leave the Core


def c2b(p):
    return (p[0] + OFF[0], p[1] + OFF[1])


def b2c(p):
    return (p[0] - OFF[0], p[1] - OFF[1])


def padxy(fps, ref, num):
    for p in fps[ref]['pads']:
        if p['num'] == num:
            return (p['x'], p['y'])
    raise KeyError(ref + '.' + num)


def cpad(ref, num):
    return padxy(fc, ref, num)


def bpad(ref, num):                              # base pad, returned in CORE coords
    return b2c(padxy(fb, ref, num))


# ---------------------------------------------------------------- U2 (RP2354A) GPIO pin positions (core)
U2PIN = {}
GPIO_PAD = {}
for p in fc['U2']['pads']:
    fn = p['fn']
    if fn.startswith('GPIO'):
        g = int(fn.split('_')[0][4:])
        U2PIN[g] = (p['x'], p['y']); GPIO_PAD[g] = p['num']
U2PIN['SWCLK'] = cpad('U2', '24'); U2PIN['SWDIO'] = cpad('U2', '25')
GPIO_PAD['SWCLK'] = '24'; GPIO_PAD['SWDIO'] = '25'

# ---------------------------------------------------------------- Core F.Cu obstacles (placement stays)
core_F = [f for f in c['footprints'] if f['side'] == 'F' and f['ref'] not in REMOVED_CORE]
USERPADS = {f['ref']: (pad_geom(f['pads'][0], 'F.Cu'), f['pads'][0]['net']) for f in core_F if 'small_pad' in f['fpid']}


def core_env():
    return [(f['ref'], body_envelope(f, 'F.Cu')[0]) for f in core_F]


# ---------------------------------------------------------------- U7 (LP5912-3.3, WSON-6 2x2) block on Core F.Cu
# Block = U7 + COUT (0402, outside the pin 1-3 row, at pin 1) + CIN (0402, outside the pin 4-6 row, at pin 6),
# the same arrangement as U6/C27/C25 on this Core. Local frame (rot 0): pins 1-3 row at y=-0.8875 (pin 1 at x=+0.65),
# pins 4-6 row at y=+0.8875 (pin 6 at x=+0.65), EP at 0.  Body 2.0x2.0 (envelope 2.10 x 2.15 like U6).
U7_LOCAL = {'U7': (0.0, 0.0), 'COUT': (0.29, -1.075 - 0.2 - 0.31), 'CIN': (0.29, 1.075 + 0.2 + 0.31),
            'OUT': (0.65, -0.8875), 'IN': (0.65, 0.8875), 'EN': (-0.65, 0.8875), 'GND5': (0.0, 0.8875)}
U7_BLOCK = box(-1.05, -1.075 - 0.2 - 0.62, 1.05, 1.075 + 0.2 + 0.62)   # 2.10 x 3.79


def u7_place(cx, cy, rot):
    out = {}
    for k, (x, y) in U7_LOCAL.items():
        p = affinity.rotate(Point(x, y), rot, origin=(0, 0))   # shapely CCW in y-up; we only use 0/90/180/270
        out[k] = (cx + p.x, cy + p.y)
    blk = affinity.translate(affinity.rotate(U7_BLOCK, rot, origin=(0, 0)), cx, cy)
    return out, blk


def place_u7():
    env = unary_union([e.buffer(0.2) for r, e in core_env() if e is not None])
    usable = CO.buffer(-0.3)
    free = usable.difference(env)
    pin49 = cpad('U2', '49')
    v33 = [(p['x'], p['y']) for f in c['footprints'] for p in f['pads'] if p['net'] == '+3.3V' and f['ref'] in ('U2', 'U8', 'U9', 'U10', 'U11')]
    v33c = (sum(x for x, y in v33) / len(v33), sum(y for x, y in v33) / len(v33))
    imu = fc['U8']
    imu_c = (imu['x'], imu['y'])
    import numpy as np
    from shapely import contains_xy
    R = 0.05
    x0, y0, x1, y1 = CO.bounds
    gx = np.arange(x0, x1, R) + R / 2; gy = np.arange(y0, y1, R) + R / 2
    X, Y = np.meshgrid(gx, gy)
    M = contains_xy(free, X, Y).astype(np.int32)          # rows = y, cols = x
    I = np.pad(M, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    cands = []
    for rot in (0, 90, 180, 270):
        w, h = (2.10, 3.79) if rot in (0, 180) else (3.79, 2.10)
        nw, nh = int(math.ceil(w / R)), int(math.ceil(h / R))
        S = I[nh:, nw:] - I[:-nh, nw:] - I[nh:, :-nw] + I[:-nh, :-nw]
        jj, ii = np.nonzero(S == nw * nh)
        for j, i in zip(jj, ii):
            cx = gx[i] - R / 2 + nw * R / 2; cy = gy[j] - R / 2 + nh * R / 2
            pl, blk = u7_place(cx, cy, rot)
            s = math.dist(pl['OUT'], pin49) + 0.3 * math.dist(pl['OUT'], v33c)
            cands.append(dict(score=s, cx=round(cx, 3), cy=round(cy, 3), rot=rot, imu=math.dist((cx, cy), imu_c),
                              d49=math.dist(pl['OUT'], pin49), place={k: (round(v[0], 3), round(v[1], 3)) for k, v in pl.items()}))
    cands.sort(key=lambda d: d['score'])
    # distinct regions
    best = []
    for d in cands:
        if all(math.dist((d['cx'], d['cy']), (e['cx'], e['cy'])) > 2.5 for e in best):
            best.append(d)
    return best, free


# ---------------------------------------------------------------- grid sites
def grid_sites(ox, oy):
    inner = CO.buffer(-(PAD_D / 2 + EDGE))
    x0, y0, x1, y1 = CO.bounds
    i0 = math.floor((x0 - O[0] - ox) / PITCH) - 1; i1 = math.ceil((x1 - O[0] - ox) / PITCH) + 1
    j0 = math.floor((y0 - O[1] - oy) / PITCH) - 1; j1 = math.ceil((y1 - O[1] - oy) / PITCH) + 1
    s = []
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            x, y = O[0] + ox + i * PITCH, O[1] + oy + j * PITCH
            if inner.contains(Point(x, y)):
                s.append((round(x, 4), round(y, 4)))
    return s


def via_ok_sets(sites, padlist, clr):
    """padlist: [(poly, net)] on the via landing layer. Returns per site: (ok_any, set(nets for which ok))."""
    infl = clr + VIA_D / 2
    res = []
    for (x, y) in sites:
        reg = Point(x, y).buffer(VIA_OFF, 24)
        near = [(g, n) for g, n in padlist if g.distance(Point(x, y)) < VIA_OFF + infl]
        if not near:
            res.append((True, set()))
            continue
        allb = unary_union([g.buffer(infl, 12) for g, n in near])
        ok_any = reg.difference(allb).area > 1e-4
        oks = set()
        for net in set(n for g, n in near):
            ob = [g.buffer(infl, 12) for g, n in near if n != net]
            r = reg.difference(unary_union(ob)) if ob else reg
            if r.area > 1e-4:
                oks.add(net)
        res.append((ok_any, oks))
    return res


def core_fcu_pads(u7blk=None):
    pl = []
    for f in core_F:
        for p in f['pads']:
            if 'F.Cu' in p['polys']:
                pl.append((polys(p['polys']['F.Cu']), p['net']))
    if u7blk is not None:
        pl.append((u7blk, '__U7__'))
    return pl


def base_bcu_pads():
    pl = []
    for f in b['footprints']:
        if f['ref'] == 'U24':
            continue
        for p in f['pads']:
            if 'B.Cu' in p['polys']:
                pl.append((affinity.translate(polys(p['polys']['B.Cu']), -OFF[0], -OFF[1]), p['net']))
    return pl


def base_bcu_bodies():
    out = []
    for f in b['footprints']:
        if f['side'] != 'B':
            continue
        e = body_envelope(f, 'B.Cu')[0]
        if e is not None:
            out.append((f['ref'], affinity.translate(e, -OFF[0], -OFF[1])))
    return out


def base_vias_core():
    return [((v['x'] - OFF[0], v['y'] - OFF[1]), v['net'], v['d'], v['drill']) for v in b['vias']]


def site_attrs(sites, u7blk):
    cpads = core_fcu_pads(u7blk)
    bpads = base_bcu_pads()
    cv = via_ok_sets(sites, cpads, CORE_CLR)
    bv = via_ok_sets(sites, bpads, BASE_CLR)
    bodies = base_bcu_bodies()
    bvias = base_vias_core()
    cenv = core_env()
    out = []
    for k, (x, y) in enumerate(sites):
        P = Point(x, y); disc = P.buffer(PAD_D / 2)
        heat = [(r, n) for r, (g, n) in USERPADS.items() if g.distance(disc) < 0.3]
        under_core = [r for r, e in cenv if e is not None and e.intersects(disc) and 'small_pad' not in fc[r]['fpid']]
        under_base = [r for r, e in bodies if e.intersects(disc)]
        vias = [(n, round(math.dist((x, y), q), 2)) for q, n, d, dr in bvias if math.dist((x, y), q) < PAD_D / 2 + BASE_CLR + d / 2]
        out.append(dict(core_ok_any=cv[k][0], core_ok_nets=sorted(cv[k][1]), base_ok_any=bv[k][0], base_ok_nets=sorted(bv[k][1]),
                        heat=heat, under_core=under_core, under_base=under_base, base_vias=vias,
                        u7=bool(u7blk is not None and u7blk.buffer(0.1).intersects(disc))))
    return out


def corners():
    """Convex corners of the Core outline (fillets merged): TL, TR, ear top, ear bottom, BR, bottom tab, BL, left chamfer."""
    return {'TL': (103.1, 43.5), 'TR': (120.3, 43.5), 'EAR_T': (126.1, 52.2), 'EAR_B': (126.1, 58.3),
            'BR': (122.3, 62.8), 'BL': (105.0, 63.6), 'L': (103.1, 50.7)}
