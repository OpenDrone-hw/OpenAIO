"""Markdown tables for LGA_SPEC.md from lga_spec.json."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(HERE + '/lga_spec.json'))
f = lambda v: f'{v:.2f}'
# ASCII map, top view (Base F.Cu view; the Core B.Cu seen through the Core)
lx = sorted(set(d['j90_local'][0] for d in S['pads'])); ly = sorted(set(d['j90_local'][1] for d in S['pads']))
XS = [round(lx[0] + 2 * i, 2) for i in range(int(round((lx[-1] - lx[0]) / 2)) + 1)]
YS = [round(ly[0] + 2 * i, 2) for i in range(int(round((ly[-1] - ly[0]) / 2)) + 1)]
ab = {'GND': 'GND', '+4v5': '4V5', '+5V': '5V', '+BATT': 'VBAT!', 'USB_D+': 'DP', 'USB_D-': 'DM', 'SPI0.MISO': 'MISO', 'SPI0.SCK': 'SCK',
      'SPI0.MOSI': 'MOSI', 'FLASH_CS': 'SDCS', 'BUZZER-': 'BUZ', 'LED_STRIP': 'LED', 'UART0_TX': 'U0TX', 'UART0_RX': 'U0RX',
      'UART1_TX': 'U1TX', 'UART1_RX': 'U1RX', 'PU0RX': 'PU0RX', 'SWDIO': 'SWDIO', 'SWCLK': 'SWCLK', 'CURR': 'CURR'}
cell = {(round(d['j90_local'][1], 2), round(d['j90_local'][0], 2)): (d['pad'], ab.get(d['net'], d['net'].replace('MOTOR', 'M'))) for d in S['pads']}
print('```')
print('J90 local y \\ x ' + ''.join(f'{x:>9.2f}' for x in XS))
for y in YS:
    print(f'{y:>15.2f} ' + ''.join(f"{(cell[(y, x)][0] + ':' + cell[(y, x)][1]) if (y, x) in cell else '.':>9s}" for x in XS))
print('```')
print()
print('| pad | row,col | Core x, y | Base x, y | J90 local | net | role | Core end | Base end | Core / Base leg mm | Core via | Base via (blockers) | Base vias to clear | note |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for d in S['pads']:
    note = []
    if d['anchor']:
        note.append('anchor ' + '/'.join(d['anchor']))
    if d['core_userpad_within_0.3mm']:
        note.append('near Core pad ' + '/'.join(d['core_userpad_within_0.3mm']))
    bv = d['base_via']
    if 'base_via_blockers' in d:
        bv = 'blocked by ' + ', '.join(d['base_via_blockers'])
    cv = {'not needed (B.Cu GND pour)': 'none (B.Cu GND)', 'free': 'in pad', 'on same-net pad': 'in pad, lands on same-net F.Cu pad'}[d['core_via']]
    legs = f"{d['core_leg_mm']:.1f} / {d['base_leg_mm']:.1f}" if 'core_leg_mm' in d else ''
    print(f"| {d['pad']} | {d['row']},{d['col']} | {d['core_xy'][0]:.4f}, {d['core_xy'][1]:.4f} | {d['base_xy'][0]:.4f}, {d['base_xy'][1]:.4f} | "
          f"{d['j90_local'][0]:+.2f}, {d['j90_local'][1]:+.2f} | {d['net']} | {d['role']} | {d.get('core_end', '')} | {d.get('base_end', '')} | {legs} | "
          f"{cv} | {bv} | {', '.join(d['base_vias_to_clear'])} | {'; '.join(note)} |")
print()
M = S['metrics']
print(json.dumps({k: v for k, v in M.items() if k != 'per_net'}, indent=1, default=float))
print()
print('| signal | today mm | new mm | new, GPIO unchanged | direct (lower bound) |')
print('|---|---|---|---|---|')
for n, v in M['per_net'].items():
    print(f"| {n} | {v['today']:.1f} | {v['new']:.1f} | {v['new_fixgpio']:.1f} | {v['direct']:.1f} |")
print()
print(S['gpio'])
print(S['u7'])
print(S['swd_testpads_base'])
print(S.get('vtx_pads_base'))
