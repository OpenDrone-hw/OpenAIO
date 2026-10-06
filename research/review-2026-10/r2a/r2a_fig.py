"""Figure: the new LGA pattern over the Core (core coords) and over the Base (base coords). Reads lga_spec.json."""
import json, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle
import r2a_geo as G
from lr_common import body_envelope, polys, pad_geom

S = json.load(open(G.HERE + '/lga_spec.json'))
COL = {'GND': '#8f8e89', 'PWR': '#eb6834', 'SIG': '#2a78d6'}
INK, INK2, FAINT = '#0b0b0b', '#52514e', '#d9d8d3'


def draw_poly(ax, g, **kw):
    gs = g.geoms if hasattr(g, 'geoms') else [g]
    for p in gs:
        if p.is_empty or p.geom_type != 'Polygon':
            continue
        ax.add_patch(MPoly(list(p.exterior.coords), closed=True, **kw))


def shortname(n):
    return n.replace('SPI0.', '').replace('UART', 'U').replace('_', '').replace('MOTOR', 'M').replace('BUZZER-', 'BUZ').replace('LEDSTRIP', 'LED')


fig, axs = plt.subplots(1, 2, figsize=(19, 9.5), dpi=130)
fig.patch.set_facecolor('#fcfcfb')

# ------------------------------------------------------------ Core panel (core coords)
ax = axs[0]
draw_poly(ax, G.CO, fill=False, ec=INK, lw=1.2)
for f in G.core_F:
    e = body_envelope(f, 'F.Cu')[0]
    if e is None:
        continue
    if 'small_pad' in f['fpid']:
        draw_poly(ax, e, fc='#f3efe2', ec='#b9b18f', lw=0.6)
        c = e.centroid
        ax.text(c.x, c.y - 0.75, f"{f['ref']} {f['pads'][0]['net'].split('/')[-1]}", fontsize=5, color=INK2, ha='center')
    else:
        draw_poly(ax, e, fc='#efefec', ec='#c4c3bd', lw=0.4)
        if f['ref'] in ('U2', 'U6', 'U8', 'X1', 'U10', 'L1', 'U1', 'Q1', 'Q2', 'R5', 'R8', 'R9', 'R1'):
            c = e.centroid
            ax.text(c.x, c.y, f['ref'], fontsize=6, color=INK2, ha='center', va='center')
for r in G.REMOVED_CORE:
    f = G.fc[r]; e = pad_geom(f['pads'][0], 'F.Cu')
    draw_poly(ax, e, fill=False, ec='#b9b18f', lw=0.6, ls='--')
    ax.text(e.centroid.x, e.centroid.y, f'{r}\nremoved', fontsize=5, color=INK2, ha='center', va='center')
u7 = S['u7']; bx0, by0, bx1, by1 = u7['block_bounds']
ax.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, fc='#f6d58a', ec='#c98500', lw=1.0, zorder=3))
ax.text(bx1 + 0.15, by0 + 0.35, 'new U7 LP5912-3.3\n+ CIN + COUT', fontsize=6, ha='left', va='center', zorder=7,
        bbox=dict(boxstyle='round,pad=0.15', fc='#fcfcfb', ec='#c98500', lw=0.5))
# previous pads
for p in G.fc['J91']['pads']:
    ax.add_patch(Circle((p['x'], p['y']), 0.5, fill=False, ec='#52514e', lw=0.5, ls=':', zorder=2))
# new pads
for d in S['pads']:
    x, y = d['core_xy']
    ax.add_patch(Circle((x, y), 0.5, fc=COL[d['role']], ec='white', lw=0.8, zorder=5))
    ax.text(x, y, d['pad'], fontsize=5.5, color='white', ha='center', va='center', zorder=6, weight='bold')
    if d['role'] != 'GND':
        ax.text(x, y + 0.82, shortname(d['net']), fontsize=5.5, color=INK, ha='center', va='center', zorder=6)
    if d['anchor']:
        ax.add_patch(Circle((x, y), 0.68, fill=False, ec=INK, lw=0.8, zorder=6))
for d in S['pads']:
    if d['role'] == 'GND':
        continue
    ce = d.get('core_end_xy_core')
    if ce:
        ax.plot([d['core_xy'][0], ce[0]], [d['core_xy'][1], ce[1]], color=COL[d['role']], lw=0.8, alpha=0.55, zorder=4)
        ax.plot([ce[0]], [ce[1]], marker='o', ms=2.2, color=COL[d['role']], zorder=4)
ax.set_xlim(102.3, 126.9); ax.set_ylim(64.4, 42.7); ax.set_aspect('equal')
ax.set_title('Core (OpenAIO-Core coords, top view; LGA on B.Cu seen through). Lines: pad to Core-side driver', fontsize=9, color=INK)
ax.tick_params(labelsize=7)

# ------------------------------------------------------------ Base panel (base coords)
ax = axs[1]
draw_poly(ax, G.BO, fill=False, ec=INK, lw=1.2)
from shapely import affinity
cob = affinity.translate(G.CO, *G.OFF)
for f in G.b['footprints']:
    if f['ref'] in ('U24', 'J90'):
        continue
    e = body_envelope(f, f['side'] + '.Cu')[0]
    if e is None:
        continue
    if f['side'] == 'B':
        draw_poly(ax, e, fc='#eef2f8', ec='#b7c3d6', lw=0.4)
    else:
        draw_poly(ax, e, fc='#f3efe2', ec='#b9b18f', lw=0.4)
    if f['ref'] in ('Card1', 'USB1', 'U12', 'U22', 'U25', 'J29', 'R39', 'R58', 'R77', 'R96', 'D2', 'D3', 'L3', 'U13', 'U15', 'U17', 'U19',
                    'U21', 'U16', 'U18', 'U20', 'U14', 'J20', 'J21', 'J31', 'J32', 'AE2', 'Rsense2', 'U23'):
        c = e.centroid
        ax.text(c.x, c.y, f['ref'], fontsize=6, color=INK2, ha='center', va='center')
for p in G.fb['U24']['pads']:
    for L in ('F.Cu',):
        if L in p['polys'] and p['drill'] > 2:
            draw_poly(ax, polys(p['polys'][L]), fc='#e4e3de', ec='#b0afa9', lw=0.4)
draw_poly(ax, cob, fill=False, ec=INK, lw=1.0, ls='--')
for p in G.fb['J90']['pads']:
    ax.add_patch(Circle((p['x'], p['y']), 0.5, fill=False, ec='#52514e', lw=0.5, ls=':', zorder=2))
for d in S['pads']:
    x, y = d['base_xy']
    ax.add_patch(Circle((x, y), 0.5, fc=COL[d['role']], ec='white', lw=0.8, zorder=5))
    ax.text(x, y, d['pad'], fontsize=5.5, color='white', ha='center', va='center', zorder=6, weight='bold')
    if d['role'] != 'GND':
        ax.text(x, y + 0.82, shortname(d['net']), fontsize=5.5, color=INK, ha='center', va='center', zorder=6)
        be = d.get('base_end_xy_base')
        if be:
            ax.plot([x, be[0]], [y, be[1]], color=COL[d['role']], lw=0.8, alpha=0.55, zorder=4)
            ax.plot([be[0]], [be[1]], marker='o', ms=2.2, color=COL[d['role']], zorder=4)
    if d['anchor']:
        ax.add_patch(Circle((x, y), 0.68, fill=False, ec=INK, lw=0.8, zorder=6))
for i, (n, tp) in enumerate(S['swd_testpads_base'].items()):
    ax.add_patch(Circle(tp[:2], 0.4, fc='#4a3aa7', ec='white', lw=0.6, zorder=7))
    ax.annotate(f'TP {n} (B.Cu)', tp[:2], xytext=(tp[0] - 1.5 + 3.0 * i, tp[1] - 1.6 + 3.2 * i), fontsize=6, color='#4a3aa7',
                ha='center', zorder=8, arrowprops=dict(arrowstyle='-', color='#4a3aa7', lw=0.5))
if 'vtx_pads_base' in S:
    for k, col in (('p10', '#eb6834'), ('gnd', '#8f8e89')):
        x, y, w, h = S['vtx_pads_base'][k]
        ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=col, ec=INK, lw=0.6, zorder=7))
        ax.text(x + w / 2 + 0.2, y, 'VTX +10V' if k == 'p10' else 'VTX GND', fontsize=6, va='center', zorder=7)
ax.set_xlim(57.4, 93.4); ax.set_ylim(78.9, 42.9); ax.set_aspect('equal')
ax.set_title('Base (OpenAIO-Base coords, top view). Dashed: Core outline. Lines: pad to Base-side load. Blue-grey parts: B.Cu', fontsize=9, color=INK)
ax.tick_params(labelsize=7)

from matplotlib.lines import Line2D
h = [Line2D([], [], marker='o', ls='', ms=9, mfc=COL['SIG'], mec='white', label='signal pad'),
     Line2D([], [], marker='o', ls='', ms=9, mfc=COL['PWR'], mec='white', label='power pad'),
     Line2D([], [], marker='o', ls='', ms=9, mfc=COL['GND'], mec='white', label='GND pad'),
     Line2D([], [], marker='o', ls='', ms=11, mfc='none', mec=INK, label='GND corner anchor'),
     Line2D([], [], marker='o', ls='', ms=9, mfc='none', mec=INK2, mew=0.8, label='d81e559 pad (34)', linestyle='')]
fig.legend(handles=h, loc='lower center', ncol=5, fontsize=8, frameon=False)
m = S['metrics']
fig.suptitle(f"OpenAIO Core/Base LGA R2a: {m['new']['pads']} pads on a 2.0 mm grid, {m['new']['gnd']} GND "
             f"({100 * m['new']['gnd'] / m['new']['pads']:.0f} %); 17 common signals {m['new']['sig17']:.0f} mm straight-line vs "
             f"{m['today']['sig17']:.0f} mm today; centroid offset {m['new']['centroid_off']:.2f} mm; hull {100 * m['new']['hull']:.0f} %",
             fontsize=11, color=INK)
plt.tight_layout(rect=(0, 0.04, 1, 0.95))
plt.savefig(G.HERE + '/lga_spec.png', facecolor=fig.get_facecolor())
print('ok')
