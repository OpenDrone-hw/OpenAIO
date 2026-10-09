"""Double-sided assembly facts: parts per side, parts under the Core footprint on each Base side, LGA pad area vs Core
mass estimate, heights, Core copper balance (warpage proxy) and 0.8 mm thickness."""
import json, collections
from shapely import affinity
from lr_common import *
c = load('core'); b = load('base')
co = affinity.translate(outline(c), *OFF)
H = json.load(open('lr_heights.json'))
hb = {r[1]: r[0] for r in H['base']}; hc = {r[1]: r[0] for r in H['core']}
for side in ('F', 'B'):
    lay = 'F.Cu' if side == 'F' else 'B.Cu'
    ps = [f for f in b['footprints'] if f['side'] == side and f['ref'] not in ('U24', 'J90')]
    under = []
    for f in ps:
        env = body_envelope(f, lay)[0]
        if env is not None and env.intersects(co):
            under.append((f['ref'], round(env.intersection(co).area / env.area, 2)))
    print(f'Base {side}: {len(ps)} parts; under the Core outline: {len(under)}' + (f' {under}' if side == 'F' or len(under) < 15 else ''))
    if side == 'B':
        big = [r for r, _ in under if r.startswith(('U', 'Q', 'L', 'X', 'OSC'))]
        print('   ICs/heavy under the Core (B side):', big)
J91 = [f for f in c['footprints'] if f['ref'] == 'J91'][0]
padA = sum(pad_geom(p).area for p in J91['pads'])
# mass estimate: FR4+Cu 0.8 mm board (density ~1.9 g/cm3 incl. copper) + parts (QFN-60 ~0.12 g, others small)
board_g = outline(c).area * 0.8 * 1.9e-3
parts_g = 0.12 + 0.01 * 3 + 0.03 + 0.02 + 0.0004 * 75  # QFN-60, IMU/SOT/X2SON, switch, L1, ~75 x 0201/0402
print(f'Core: outline {outline(c).area:.0f} mm2, est. mass {board_g + parts_g:.2f} g ({board_g:.2f} board + ~{parts_g:.2f} parts); '
      f'LGA pad area {padA:.1f} mm2 -> {1000 * (board_g + parts_g) / padA:.1f} mg/mm2 (guideline for a part hanging upside down: <= 46 mg/mm2 = 30 g/in2)')
print('Core tallest parts (mm above Core top):', sorted(((round(v, 2), k) for k, v in hc.items() if v and v > 0.6), reverse=True)[:5])
print('Base F tallest (mm above Base top):', sorted(((round(v, 2), k) for k, v in hb.items() if v and v > 1.0 and k in {f["ref"] for f in b["footprints"] if f["side"] == "F"}), reverse=True))
print('Base B tallest (mm below Base bottom):', sorted(((round(v, 2), k) for k, v in hb.items() if v and v > 0.9 and k in {f["ref"] for f in b["footprints"] if f["side"] == "B"}), reverse=True)[:6])
core_top = 0.07 + 0.8 + max(v for v in hc.values() if v)
print(f'Core stack top above Base F surface: {core_top:.2f} mm (0.07 joint + 0.8 board + {max(v for v in hc.values() if v):.2f} part)')
