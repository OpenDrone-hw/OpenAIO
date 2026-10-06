"""Figure + mechanical metrics for the LGA pad patterns: current, A1 (optimised on current pads), B (2.0 mm grid, 40 pads).
Mechanical: centroid offset of the pad pattern from the Core outline centroid, pad-hull coverage of the Core area."""
import json, math
from PIL import Image, ImageDraw
from shapely.geometry import MultiPoint
from shapely import affinity
from lr_common import *

rows = json.load(open('lr_lga.json'))
opt = json.load(open('lr_lga_opt.json'))
c = load('core')
co = affinity.translate(outline(c), *OFF)
cur = [((r['x'], r['y']), r['net']) for r in rows]
A1 = [((r['x'], r['y']), opt['A']['assign'][r['num']]) for r in rows]
B = [(tuple(p), n) for p, n in opt['B_2.0_40_17']['assign']]
ends = {r['net']: ((r['ce']['x'], r['ce']['y']), (r['be']['x'], r['be']['y'])) for r in rows if r['kind'] == 'SIG'}


def mech(pat):
    pts = MultiPoint([p for p, n in pat])
    cx = sum(p[0] for p, n in pat) / len(pat); cy = sum(p[1] for p, n in pat) / len(pat)
    g = co.centroid
    sig = [p for p, n in pat if n not in ('GND',) and not n.startswith('+')]
    gnd = [p for p, n in pat if n == 'GND']
    nn = [min(math.dist(s, q) for q in gnd) for s in sig]
    return dict(centroid_offset=math.dist((cx, cy), (g.x, g.y)), hull_cover=pts.convex_hull.area / co.area,
                sig_gnd_le2=sum(1 for x in nn if x <= 2.01), sig=len(sig), worst_gnd=max(nn))


S = 30
x0, y0, x1, y1 = co.bounds
W, H = int((x1 - x0) * S) + 40, int((y1 - y0) * S) + 60
im = Image.new('RGB', (3 * W, H), (250, 250, 250))
dr = ImageDraw.Draw(im)
for k, (name, pat) in enumerate((('current (34 pads, 11 GND)', cur), ('A1: same pads, re-assigned', A1), ('B: 2.0 mm grid, 40 pads, 17 GND', B))):
    ox = k * W
    T = lambda x, y: (ox + 20 + (x - x0) * S, 40 + (y - y0) * S)
    dr.polygon([T(*p) for p in co.exterior.coords], outline=(0, 0, 0))
    m = mech(pat)
    dr.text((ox + 10, 5), name, fill=(0, 0, 0))
    dr.text((ox + 10, 18), f"centroid off {m['centroid_offset']:.1f} mm, hull {m['hull_cover']:.0%}, sig w/ GND<=2mm {m['sig_gnd_le2']}/{m['sig']}", fill=(0, 0, 0))
    for (x, y), n in pat:
        if n is None:
            continue
        col = (150, 150, 150) if n == 'GND' else (240, 150, 0) if n.startswith('+') else (40, 170, 40)
        r = 0.5 * S
        X, Y = T(x, y)
        dr.ellipse([X - r, Y - r, X + r, Y + r], fill=col, outline=(0, 0, 0))
        if n != 'GND':
            dr.text((X - r, Y + r), n.replace('SPI0.', '').replace('_', '')[:9], fill=(0, 0, 0))
            if n in ends:
                ce, be = ends[n]
                dr.line([T(*ce), (X, Y)], fill=(80, 80, 255), width=1)
                dr.line([(X, Y), T(*be)], fill=(255, 80, 80), width=1)
im.save('lr_img/lga_patterns.png')
for name, pat in (('current', cur), ('A1', A1), ('B grid 40', B), ('B grid 34', [(tuple(p), n) for p, n in opt['B_2.0_34_11']['assign']])):
    print(name, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in mech(pat).items()})
