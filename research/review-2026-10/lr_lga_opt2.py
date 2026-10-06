"""Exact (Hungarian) LGA reassignment variants + legal RP2354A GPIO re-mapping for the LGA-crossing functions.
A2: GND + power pads fixed, the 18 signals permuted over the 18 signal pads.
A3: GND fixed, signals + power permuted over the 23 non-GND pads.
GPIO: with a given LGA assignment, re-map LGA-crossing functions onto legal RP2350 GPIOs (QFN-60, GPIO0-29)
      taken from the pool of GPIOs those functions use today (+ GPIO26 LED0, any-function), minimising
      core-side straight-line distance U2 pin -> LGA pad (core side only; base side unchanged)."""
import json, math
import numpy as np
from scipy.optimize import linear_sum_assignment
from lr_common import *

exec(open('lr_lga_opt.py').read().split('out = {}')[0])  # reuse NETS, evaluate, netcost, rows, SIG, PWR

sites = [(r['x'], r['y']) for r in rows]
cur = [r['net'] for r in rows]
g_fixed = [sites[i] for i, n in enumerate(cur) if n == 'GND']


def gpen(P):
    return 4.0 * max(0.0, min(math.dist(P, q) for q in g_fixed) - 2.0 * 1.001)


def hung(nets, idx):
    """exact assignment with the USB pair forced onto neighbouring pads (<= 2.9 mm): enumerate pad pairs"""
    best = None
    rest = [n for n in nets if n not in ('USB_D+', 'USB_D-')]
    for i in idx:
        for j in idx:
            if i == j or math.dist(sites[i], sites[j]) > 2.9:
                continue
            asg = hung0(rest, [k for k in idx if k not in (i, j)])
            asg[i] = 'USB_D+'; asg[j] = 'USB_D-'
            sc = evaluate(asg, sites, 2.0)
            if best is None or sc < best[0]:
                best = (sc, asg)
    return best[1]


def hung0(nets, idx):
    C = np.zeros((len(nets), len(idx)))
    for a, n in enumerate(nets):
        for b_, i in enumerate(idx):
            C[a, b_] = netcost(n, sites[i]) + (gpen(sites[i]) if n in SIG else 0)
    r, cidx = linear_sum_assignment(C)
    asg = [n if n == 'GND' or (n not in nets and n not in ('USB_D+', 'USB_D-')) else None for n in cur]
    for a, b_ in zip(r, cidx):
        asg[idx[b_]] = nets[a]
    return asg


res = {}
A0 = evaluate(cur, sites, 2.0, detail=True)
sig_idx = [i for i, n in enumerate(cur) if n in SIG]
A2 = hung(SIG, sig_idx)
nong = [i for i, n in enumerate(cur) if n != 'GND']
A3 = hung(SIG + PWR, nong)
for name, a in (('A0 current', cur), ('A2 signals only', A2), ('A3 signals+power', A3)):
    wl, sg, pen = evaluate(a, sites, 2.0, detail=True)
    moved = sum(1 for i in range(len(a)) if a[i] != cur[i])
    print(f'{name:18s}: total {wl:6.1f} mm, signals {sg:6.1f} mm (saves {A0[1] - sg:5.1f}), GND/adjacency penalty {pen:5.1f}, pads changed {moved}')
    res[name] = {rows[i]['num']: a[i] for i in range(len(a))}
    if name != 'A0 current':
        print('   ', ', '.join(f"{rows[i]['num']}:{cur[i]}->{a[i]}" for i in range(len(a)) if a[i] != cur[i]))

# ---------------- GPIO legality
UART = {('UART0', 'TX'): {0, 2, 12, 14, 16, 18, 28}, ('UART0', 'RX'): {1, 3, 13, 15, 17, 19, 29},
        ('UART1', 'TX'): {4, 6, 8, 10, 20, 22, 24, 26}, ('UART1', 'RX'): {5, 7, 9, 11, 21, 23, 25, 27}}
SPI0 = {'RX': {0, 4, 16, 20}, 'CS': {1, 5, 17, 21}, 'SCK': {2, 6, 18, 22}, 'TX': {3, 7, 19, 23}}
ANY = set(range(30))
ADC = {26, 27, 28, 29}
LEGAL = {
    'UART0_TX': UART[('UART0', 'TX')], 'UART0_RX': UART[('UART0', 'RX')],
    'UART1_TX': UART[('UART1', 'TX')], 'UART1_RX': UART[('UART1', 'RX')],
    'SPI0.MISO': SPI0['RX'], 'SPI0.SCK': SPI0['SCK'], 'SPI0.MOSI': SPI0['TX'],
    'FLASH_CS': ANY,  # SD chip select is a software GPIO in Betaflight; hardware CSn would be {1,5,17,21}
    'MOTOR1': ANY, 'MOTOR2': ANY, 'MOTOR3': ANY, 'MOTOR4': ANY,  # PIO DShot
    '10V_ENABLE': ANY, 'LED_STRIP': ANY, 'BUZZER-': ANY,  # PINIO / PIO / PWM
    'CURR': ADC, 'LED0': ANY,
}
fpc = {f['ref']: f for f in c['footprints']}
U2 = {int(p['fn'].split('_')[0][4:]): (p['x'] + OFF[0], p['y'] + OFF[1]) for p in fpc['U2']['pads'] if p['fn'].startswith('GPIO')}
CURGPIO = {'UART0_TX': 0, 'UART0_RX': 1, 'UART1_TX': 6, 'UART1_RX': 7, 'LED_STRIP': 8, 'BUZZER-': 17, 'SPI0.SCK': 18,
           'SPI0.MOSI': 19, 'SPI0.MISO': 20, 'FLASH_CS': 21, 'MOTOR4': 22, 'MOTOR3': 23, 'MOTOR2': 24, 'MOTOR1': 25,
           'LED0': 26, '10V_ENABLE': 27, 'CURR': 28}
pool = sorted(g for f, g in CURGPIO.items() if f not in ('LED_STRIP', 'BUZZER-', 'CURR'))
# LED_STRIP/BUZZER/CURR go through Q2/Q1/R5 first: keep those as their core endpoint (GPIO move only shortens GPIO->part trace,
# not modelled) -> exclude from re-mapping except as pool members.
FIXED_PART = {'LED_STRIP', 'BUZZER-', 'CURR'}
print('\nGPIO legality (RP2350, QFN-60): legal alternatives inside today\'s pool', pool)
for f, g in CURGPIO.items():
    print(f'   {f:11s} GPIO{g:<2d} legal (all GPIO0-29): {sorted(LEGAL[f]) if len(LEGAL[f]) < 30 else "any"}; inside pool: {sorted(LEGAL[f] & set(pool)) if len(LEGAL[f] & set(pool)) < len(pool) else "any"}')


def gpio_opt(asg):
    padpos = {asg[i]: sites[i] for i in range(len(asg))}
    funcs = [f for f in CURGPIO if f not in FIXED_PART]
    BIG = 1e6
    C = np.full((len(funcs), len(pool)), BIG)
    for a, f in enumerate(funcs):
        for b_, gp in enumerate(pool):
            if gp in LEGAL[f]:
                C[a, b_] = 0.0 if f == 'LED0' else math.dist(U2[gp], padpos[f])
    r, cc = linear_sum_assignment(C)
    before = sum(math.dist(U2[CURGPIO[f]], padpos[f]) for f in funcs if f != 'LED0')
    after = sum(C[a, b_] for a, b_ in zip(r, cc))
    m = {funcs[a]: pool[b_] for a, b_ in zip(r, cc)}
    return before, after, m


for name, a in (('A0 current', cur), ('A3 signals+power', A3)):
    bf, af, m = gpio_opt(a)
    ch = {f: (CURGPIO[f], g) for f, g in m.items() if g != CURGPIO[f]}
    print(f'\nGPIO re-map with LGA {name}: core-side straight-line {bf:.1f} -> {af:.1f} mm (saves {bf - af:.1f}); changes {ch}')
    res['gpio_' + name] = dict(before=bf, after=af, map=m)
json.dump(res, open('lr_lga_opt2.json', 'w'), indent=1)
