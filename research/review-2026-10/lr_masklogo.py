"""B.Mask 'AIO' logo (mask opening) on the Base: which B.Cu copper (nets) it exposes, using the text render_cache
stored in the board (the 'Tokyo' font is not installed here, so kicad-cli DRC renders a substitute and over-reports)."""
import re, collections
from shapely.geometry import Polygon
from lr_common import *
s = open(HERE + '/../rev/d81e559/hardware/OpenAIO-Base.kicad_pcb').read()
i = s.index('(gr_text "AIO"'); j = s.index('(render_cache', i); k = s.index('\n\t)', j)
polys_ = []
for blk in re.findall(r'\(polygon\s*\(pts(.*?)\)\s*\)', s[j:k], re.S):
    pts = [(float(a), float(b)) for a, b in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', blk)]
    if len(pts) >= 3:
        polys_.append(Polygon(pts).buffer(0))
logo = unary_union(polys_)
print('logo opening area %.2f mm2, bbox %s' % (logo.area, [round(v, 2) for v in logo.bounds]))
b = load('base')
cb = copper_by_layer_net(b, 'base')
exp = {n: g.intersection(logo).area for (L, n), g in cb.items() if L == 'B.Cu' and g.intersects(logo)}
print('B.Cu copper exposed by the logo, by net (mm2):', {n: round(a, 3) for n, a in sorted(exp.items(), key=lambda t: -t[1]) if a > 0.001})
parts = [f['ref'] for f in b['footprints'] if f['side'] == 'B' and any(pad_geom(p, 'B.Cu').intersects(logo) for p in f['pads'])]
print('B-side parts with pads inside the opening:', parts)
