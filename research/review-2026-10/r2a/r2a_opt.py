"""R2a LGA optimiser: choose 2.0 mm grid sites, net assignment and legal RP2354A GPIO re-map together.
cost = sum_w (|core_end - pad| + |pad - base_end|) straight line (core coords), plus rule penalties (see RULES).
Usage: python3 r2a_opt.py <ox> <oy> <ngnd> <iters> <seeds> [fixgpio]   -> prints JSON result on the last line."""
import sys, json, math, random
import r2a_geo as G

# ---------------------------------------------------------------- nets
SIG = ['CURR', 'SPI0.MISO', 'SPI0.SCK', 'SPI0.MOSI', 'FLASH_CS', 'USB_D+', 'USB_D-', 'MOTOR1', 'MOTOR2', 'MOTOR3', 'MOTOR4',
       'BUZZER-', 'LED_STRIP', 'UART0_TX', 'UART0_RX', 'UART1_TX', 'UART1_RX', 'PU0RX', 'SWDIO', 'SWCLK']
PWR = ['+4v5#1', '+4v5#2', '+5V#1', '+5V#2', '+BATT']
NETS = SIG + PWR


def NET(n):
    return n.split('#')[0]


MOT = {'MOTOR1', 'MOTOR2', 'MOTOR3', 'MOTOR4'}
MOT_VICTIM = {'CURR', 'USB_D+', 'USB_D-', '+BATT'}
AGGR = {'SPI0.SCK', 'LED_STRIP', 'SWCLK', 'MOTOR1', 'MOTOR2', 'MOTOR3', 'MOTOR4'}
W = {n: 1.0 for n in NETS}
W.update({'SWDIO': 0.5, 'SWCLK': 0.5, '+BATT': 1.5})   # +BATT: keep the 25 V trace on the Core short

# GPIO-driven functions: current GPIO and legal set (RP2350 function table, QFN-60 GPIO0-29; UART AUX = F11)
GPIO_CUR = {'UART0_TX': 0, 'UART0_RX': 1, 'UART1_TX': 6, 'UART1_RX': 7, 'SPI0.SCK': 18, 'SPI0.MOSI': 19, 'SPI0.MISO': 20,
            'FLASH_CS': 21, 'MOTOR4': 22, 'MOTOR3': 23, 'MOTOR2': 24, 'MOTOR1': 25, 'LED0': 26}
ANY = set(range(30))
LEGAL = {'UART0_TX': {0, 2, 12, 14, 16, 18, 28}, 'UART0_RX': {1, 3, 13, 15, 17, 19, 29},
         'UART1_TX': {4, 6, 8, 10, 20, 22, 24, 26}, 'UART1_RX': {5, 7, 9, 11, 21, 23, 25, 27},
         'SPI0.MISO': {0, 4, 16, 20}, 'SPI0.SCK': {2, 6, 18, 22}, 'SPI0.MOSI': {3, 7, 19, 23},
         'FLASH_CS': ANY, 'MOTOR1': ANY, 'MOTOR2': ANY, 'MOTOR3': ANY, 'MOTOR4': ANY, 'LED0': ANY}
# pool = GPIOs the LGA functions use today + GPIO26 (LED0) + GPIO27 (freed by B1). Everything else stays put:
# 2/3 PIO UART0 (J44/J45, PU0RX), 4/5 I2C0, 8 LED_STRIP_L, 9-13 IMU, 14-16 OSD, 17 BEEPER, 28 CURR ADC, 29 VBAT ADC.
POOL = [0, 1, 6, 7, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
REMAP = list(GPIO_CUR)

# ---------------------------------------------------------------- endpoints (core coords)
U7 = None   # filled by setup()
CORE_FIXED = {'CURR': G.cpad('R5', '1'), 'USB_D+': G.cpad('R9', '2'), 'USB_D-': G.cpad('R8', '1'),
              'BUZZER-': G.cpad('Q1', '3'), 'LED_STRIP': G.cpad('Q2', '3'), 'PU0RX': G.U2PIN[3],
              'SWDIO': G.U2PIN['SWDIO'], 'SWCLK': G.U2PIN['SWCLK'], '+5V#1': G.cpad('J30', '1'), '+5V#2': G.cpad('J37', '1'),
              '+BATT': G.cpad('R1', '2')}
# Core user pads hanging on GPIO nets (the GPIO choice moves their Core routing too; weight 0.5)
CORE_USERPAD = {'UART0_TX': G.cpad('J49', '1'), 'UART0_RX': G.cpad('J48', '1'), 'UART1_TX': G.cpad('J54', '1'),
                'UART1_RX': G.cpad('J55', '1')}
BASE_END = {'CURR': [G.bpad('U25', '6')], 'SPI0.MISO': [G.bpad('Card1', '7')], 'SPI0.SCK': [G.bpad('Card1', '5')],
            'SPI0.MOSI': [G.bpad('Card1', '3')], 'FLASH_CS': [G.bpad('Card1', '2')], 'USB_D+': [G.bpad('USB1', 'A6')],
            'USB_D-': [G.bpad('USB1', 'A7')], 'MOTOR1': [G.bpad('R39', '1')], 'MOTOR2': [G.bpad('R58', '1')],
            'MOTOR3': [G.bpad('R77', '1')], 'MOTOR4': [G.bpad('R96', '1')], 'BUZZER-': [G.bpad('J29', '1')],
            'LED_STRIP': [G.bpad(r, '1') for r in ('J20', 'J21', 'J31', 'J32')],   # tree to 4 corner pads: nearest
            'UART0_TX': [G.bpad('U12', '3')], 'UART0_RX': [G.bpad('U12', '4')], 'UART1_TX': [G.bpad('U22', '27')],
            'UART1_RX': [G.bpad('U22', '28')], 'PU0RX': [G.bpad('U12', '6')], 'SWDIO': None, 'SWCLK': None,
            '+4v5#1': [((G.bpad('D2', '1')[0] + G.bpad('D3', '1')[0]) / 2, (G.bpad('D2', '1')[1] + G.bpad('D3', '1')[1]) / 2)],
            '+5V#1': [G.bpad('L3', '2')], '+BATT': None}
BASE_END['+4v5#2'] = BASE_END['+4v5#1']; BASE_END['+5V#2'] = BASE_END['+5V#1']

H = 60.0           # hard-rule penalty
import os as _os
GPIOW = float(_os.environ.get('GPIOW', '2.0'))   # mm-equivalent per changed GPIO (Betaflight target change)


def setup(ox, oy, u7):
    global SITES, ATTR, ORTH, DIAG, BEYOND, ANCH, NS, WL, WLG, CC, U7
    U7 = u7
    SITES = G.grid_sites(ox, oy)
    NS = len(SITES)
    ATTR = G.site_attrs(SITES, u7['blk'])
    ORTH = [[j for j in range(NS) if abs(math.dist(SITES[i], SITES[j]) - G.PITCH) < 1e-3] for i in range(NS)]
    DIAG = [[j for j in range(NS) if abs(math.dist(SITES[i], SITES[j]) - G.PITCH * math.sqrt(2)) < 1e-3] for i in range(NS)]
    idx = {s: k for k, s in enumerate(SITES)}
    BEYOND = {}
    for i in range(NS):
        for j in ORTH[i]:
            q = (round(2 * SITES[j][0] - SITES[i][0], 4), round(2 * SITES[j][1] - SITES[i][1], 4))
            BEYOND[(i, j)] = idx.get(q)
    # corner anchors: nearest site to each convex Core corner must be GND
    ANCH = {}
    for name, p in G.corners().items():
        k = min(range(NS), key=lambda k: math.dist(SITES[k], p))
        ANCH.setdefault(k, []).append(name)
    core_end_fixed = dict(CORE_FIXED)
    # +4v5 Core loads: U7 (LP5912-3.3, all FC 3.3 V) dominates; U6 (1.8 V gyro LDO, ~1 mA) and J42/J52 hang off a thin trace
    core_end_fixed['+4v5#1'] = core_end_fixed['+4v5#2'] = u7['IN']
    # wirelength tables
    WL = {}
    for n in NETS:
        be = BASE_END[n]
        WL[n] = [0.0] * NS
        for k, P in enumerate(SITES):
            bpart = 0.0 if be is None else min(math.dist(P, q) for q in be)
            cpart = math.dist(P, core_end_fixed[n]) if n in core_end_fixed else 0.0
            WL[n][k] = W[n] * (cpart + bpart)          # GPIO nets: base part only; core part from WLG
    WLG = {}
    for f in REMAP:
        if f == 'LED0':
            continue
        for g in POOL:
            if g not in LEGAL[f]:
                continue
            up = 0.5 * math.dist(G.U2PIN[g], CORE_USERPAD[f]) if f in CORE_USERPAD else 0.0
            WLG[(f, g)] = [W[f] * math.dist(SITES[k], G.U2PIN[g]) + up for k in range(NS)]
    CC = core_end_fixed
    return SITES


def core_ok(k, net):
    a = ATTR[k]
    return a['core_ok_any'] or net in a['core_ok_nets']


def base_ok(k, net):
    a = ATTR[k]
    return a['base_ok_any'] or net in a['base_ok_nets']


def evaluate(assign, gmap, detail=False):
    pos = {}
    isg = [False] * NS
    for k, n in enumerate(assign):
        if n is None:
            continue
        if n == 'GND':
            isg[k] = True
        else:
            pos[n] = k
    wl = sig = 0.0
    pen = {}

    def add(key, v):
        pen[key] = pen.get(key, 0.0) + v

    for n, k in pos.items():
        x = WL[n][k]
        if n in gmap:
            x += WLG[(n, gmap[n])][k]
        wl += x
        if n in SIG:
            sig += x
        nn = NET(n)
        if not any(isg[j] for j in ORTH[k]):
            add('no_orth_gnd', H)
        if not core_ok(k, nn):
            add('core_via', H)
        if not base_ok(k, nn):
            add('base_via', 10.0)
        if ATTR[k]['heat']:
            add('heat', 6.0)
    for k in range(NS):
        if isg[k]:
            if not base_ok(k, 'GND'):
                add('base_via_gnd', 2.0)
            if ATTR[k]['heat']:
                add('heat_gnd', 1.5)
    for k in ANCH:
        if not isg[k]:
            add('anchor', H)
    # USB pair: orthogonal neighbours, GND on both collinear ends
    if 'USB_D+' in pos and 'USB_D-' in pos:
        a, b_ = pos['USB_D+'], pos['USB_D-']
        if b_ not in ORTH[a]:
            add('usb_pair', H)
        else:
            for i, j in ((b_, a), (a, b_)):
                e = BEYOND.get((i, j))
                if e is None or not isg[e]:
                    add('usb_fence', H)
    for m in MOT:
        if m in pos:
            k = pos[m]
            for v in MOT_VICTIM:
                if v in pos:
                    if pos[v] in ORTH[k]:
                        add('motor_adj', H)
                    elif pos[v] in DIAG[k]:
                        add('motor_diag', 3.0)
    if '+BATT' in pos:
        # 25 V pad fenced: orthogonal neighbours GND or empty (hard), diagonal neighbours GND or empty (soft)
        k = pos['+BATT']
        for n, j in pos.items():
            if n == '+BATT':
                continue
            if j in ORTH[k]:
                add('batt_adj', H)
            elif j in DIAG[k]:
                add('batt_diag', 3.0)
    if 'CURR' in pos:
        k = pos['CURR']
        for n in AGGR | {'USB_D+', 'USB_D-'}:
            if n in pos and pos[n] in ORTH[k] and n not in MOT:
                add('curr_aggr', 2.0)
    if '+4v5#1' in pos and '+4v5#2' in pos and pos['+4v5#2'] not in ORTH[pos['+4v5#1']]:
        add('4v5_pair', 4.0)
    # centroid of the whole pattern vs Core centroid (self-alignment)
    used = [SITES[k] for k, n in enumerate(assign) if n is not None]
    cx = sum(p[0] for p in used) / len(used); cy = sum(p[1] for p in used) / len(used)
    off = math.dist((cx, cy), CENT)
    add('centroid', 10.0 * max(0.0, off - 0.3))
    ch = sum(1 for f, g in gmap.items() if g != GPIO_CUR[f])
    add('gpio_change', GPIOW * ch)
    tot = wl + sum(pen.values())
    if detail:
        return dict(total=tot, wl=wl, sig=sig, pen=pen, centroid_off=off)
    return tot


CENT = (G.CO.centroid.x, G.CO.centroid.y)


def anneal(ngnd, iters, seed, fixgpio=False, init=None):
    rnd = random.Random(seed)
    fixed = set(ANCH)
    free_idx = [k for k in range(NS) if k not in fixed]
    if init is None:
        items = list(NETS) + ['GND'] * (ngnd - len(fixed)) + [None] * (len(free_idx) - len(NETS) - (ngnd - len(fixed)))
        rnd.shuffle(items)
        a = [None] * NS
        for k in fixed:
            a[k] = 'GND'
        for k, it in zip(free_idx, items):
            a[k] = it
        gmap = {f: g for f, g in GPIO_CUR.items() if f != 'LED0'}
        gled = GPIO_CUR['LED0']
    else:
        a, gmap, gled = list(init[0]), dict(init[1]), init[2]
    full = lambda: dict(gmap)
    cur = evaluate(a, gmap)
    best = (cur, list(a), dict(gmap), gled)
    T0, T1 = 12.0, 0.03
    funcs = [f for f in GPIO_CUR if f != 'LED0']
    for it in range(iters):
        T = T0 * (T1 / T0) ** (it / iters)
        if fixgpio or rnd.random() < 0.85:
            i, j = rnd.choice(free_idx), rnd.choice(free_idx)
            if a[i] == a[j]:
                continue
            a[i], a[j] = a[j], a[i]
            new = evaluate(a, gmap)
            if new <= cur or rnd.random() < math.exp((cur - new) / T):
                cur = new
                if cur < best[0]:
                    best = (cur, list(a), dict(gmap), gled)
            else:
                a[i], a[j] = a[j], a[i]
        else:
            f = rnd.choice(funcs)
            g = rnd.choice([x for x in POOL if x in LEGAL[f]])
            old = gmap[f]
            if g == old:
                continue
            inv = {v: k for k, v in gmap.items()}
            f2 = inv.get(g)
            saved = dict(gmap); sled = gled
            if f2 is None:
                if g == gled:          # LED0 gives way to any free pool GPIO
                    freeg = [x for x in POOL if x not in inv and x != gled and x != g] + [old]
                    gled = old
                gmap[f] = g
            else:
                if old not in LEGAL[f2]:
                    continue
                gmap[f], gmap[f2] = g, old
            new = evaluate(a, gmap)
            if new <= cur or rnd.random() < math.exp((cur - new) / T):
                cur = new
                if cur < best[0]:
                    best = (cur, list(a), dict(gmap), gled)
            else:
                gmap = saved; gled = sled
    return best


def descent(a, gmap, gled, fixgpio=False):
    """steepest-first 2-swap descent over sites, then GPIO swaps/moves, until no improvement"""
    fixed = set(ANCH)
    idx = [k for k in range(NS) if k not in fixed]
    cur = evaluate(a, gmap)
    improved = True
    while improved:
        improved = False
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                i, j = idx[x], idx[y]
                if a[i] == a[j]:
                    continue
                a[i], a[j] = a[j], a[i]
                new = evaluate(a, gmap)
                if new < cur - 1e-9:
                    cur = new; improved = True
                else:
                    a[i], a[j] = a[j], a[i]
        if not fixgpio:
            funcs = [f for f in GPIO_CUR if f != 'LED0']
            for f in funcs:
                for g in POOL:
                    if g not in LEGAL[f] or g == gmap[f]:
                        continue
                    inv = {v: k for k, v in gmap.items()}
                    f2 = inv.get(g); saved = dict(gmap); sled = gled
                    if f2 is None:
                        if g == gled:
                            gled = gmap[f]
                        gmap[f] = g
                    elif gmap[f] in LEGAL[f2]:
                        gmap[f], gmap[f2] = g, gmap[f]
                    else:
                        continue
                    new = evaluate(a, gmap)
                    if new < cur - 1e-9:
                        cur = new; improved = True
                    else:
                        gmap.clear(); gmap.update(saved); gled = sled
    return cur, a, gmap, gled


def run(ox, oy, ngnd, iters, seeds, fixgpio, u7):
    setup(ox, oy, u7)
    res = None
    import os
    s0 = int(os.environ.get('SEED0', '0'))
    for s in range(s0, s0 + seeds):
        r = anneal(ngnd, iters, s, fixgpio)
        r = descent(list(r[1]), dict(r[2]), r[3], fixgpio)
        if res is None or r[0] < res[0]:
            res = r
    # polish
    r = anneal(ngnd, iters // 2, 99, fixgpio, init=(res[1], res[2], res[3]))
    r = descent(list(r[1]), dict(r[2]), r[3], fixgpio)
    if r[0] < res[0]:
        res = r
    d = evaluate(res[1], res[2], detail=True)
    return dict(ox=ox, oy=oy, ngnd=ngnd, nsites=NS, cost=res[0], detail=d, assign=res[1], gmap=res[2], led0=res[3],
                sites=SITES, anchors={str(k): v for k, v in ANCH.items()})


if __name__ == '__main__':
    ox, oy, ng, iters, seeds = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    fixg = len(sys.argv) > 6 and sys.argv[6] == 'fixgpio'
    u7c = json.load(open(G.HERE + '/u7.json'))
    pl, blk = G.u7_place(u7c['cx'], u7c['cy'], u7c['rot'])
    pl['blk'] = blk
    out = run(ox, oy, ng, iters, seeds, fixg, pl)
    print(json.dumps(out, default=float))
