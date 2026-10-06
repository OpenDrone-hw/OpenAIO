"""Render board layers to PNG for visual checks.
usage: python3 lr_render.py <core|base> <layer>[,<layer>...] <out.png> [highlight_net_regex] [--fab F|B]
Colours: GND grey, +BATT red, other power orange, highlighted nets cyan, signals green. Pads white edge.
"""
import sys, re
from PIL import Image, ImageDraw
from lr_common import *

board = sys.argv[1]
layers = sys.argv[2].split(',')
outp = sys.argv[3]
hl = re.compile(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] not in ('', '-') else None
fabside = sys.argv[sys.argv.index('--fab') + 1] if '--fab' in sys.argv else None
d = load(board)
bo = outline(d)
x0, y0, x1, y1 = bo.bounds
S = 40
W, H = int((x1 - x0) * S) + 20, int((y1 - y0) * S) + 20
im = Image.new('RGB', (W, H), (10, 10, 20))
dr = ImageDraw.Draw(im, 'RGBA')
T = lambda x, y: ((x - x0) * S + 10, (y - y0) * S + 10)


def col(net, a=255):
    if hl and hl.search(net):
        return (0, 230, 255, a)
    if net == 'GND':
        return (110, 110, 110, a)
    if net in ('+BATT', 'VBAT', '/+BATT'):
        return (230, 40, 40, a)
    if net.startswith('+') or net.startswith('VBUS'):
        return (255, 150, 0, a)
    if not net:
        return (80, 80, 160, a)
    return (60, 200, 60, a)


def draw_geom(g, fill, outline=None):
    if g.is_empty:
        return
    gs = g.geoms if hasattr(g, 'geoms') else [g]
    for p in gs:
        if p.geom_type != 'Polygon':
            continue
        dr.polygon([T(*c) for c in p.exterior.coords], fill=fill, outline=outline)
        for h in p.interiors:
            dr.polygon([T(*c) for c in h.coords], fill=(10, 10, 20, 255))


draw_geom(bo, (25, 25, 40, 255), (200, 200, 0, 255))
alpha = 255 if len(layers) == 1 else 140
for L in layers:
    for z in sorted([z for z in d['zones'] if not z['rule'] and z['layer'] == L], key=lambda z: z['prio']):
        draw_geom(polys(z['filled']), col(z['net'], alpha // 2 if len(layers) == 1 else 70))
    for t in d['tracks']:
        if t['layer'] == L:
            draw_geom(track_geom(t), col(t['net'], alpha))
    for f in d['footprints']:
        for p in f['pads']:
            if L in p['polys']:
                draw_geom(polys(p['polys'][L]), col(p['net'], alpha), (255, 255, 255, 120))
for v in d['vias']:
    if any(L in via_layers(board, v) for L in layers):
        draw_geom(Point(v['x'], v['y']).buffer(v['d'] / 2), col(v['net']), (255, 255, 255, 200))
if fabside:
    lay = 'F.Cu' if fabside == 'F' else 'B.Cu'
    for f in d['footprints']:
        if f['side'] != fabside:
            continue
        env, body, src = body_envelope(f, lay)
        if body is not None and body.geom_type in ('Polygon',):
            dr.line([T(*c) for c in body.exterior.coords], fill=(255, 255, 255, 255), width=2)
        if env is not None:
            cx, cy = env.centroid.x, env.centroid.y
            dr.text(T(cx - 0.4, cy - 0.2), f['ref'], fill=(255, 255, 0, 255))
im.save(outp)
print('saved', outp, W, H)
