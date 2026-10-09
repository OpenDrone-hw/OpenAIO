"""Current-density map (A/mm2, per layer) for a DC scenario, saved as PNG strips. usage: lr_jmap.py <net> <out.png>
/CSA+: battery pad -> shunt pad 1 at 80 A; +BATT: shunt pad 2 -> phase-A HS drains 4 x 20 A; GND: phase-B LS sources 4x20 A -> battery GND."""
import sys
import numpy as np
from PIL import Image, ImageDraw
from lr_dc import *
net, outp = sys.argv[1], sys.argv[2]
m = NetModel('base', net, h=0.05)
if net == '/CSA+':
    m.factor(m.pad_nodes('U24', '1')); V = m.solve([(m.pad_nodes('Rsense2', '1'), 80.0)])
elif net == '+BATT':
    m.factor(m.pad_nodes('Rsense2', '2')); V = m.solve([(m.pad_nodes(q, '3'), 20.0) for q in ('Q3', 'Q9', 'Q15', 'Q21')])
else:
    m.factor(m.pad_nodes('U24', '2')); V = m.solve([(m.pad_nodes(q, '1'), 20.0) for q in ('Q6', 'Q12', 'Q18', 'Q24')])
I = m.edge_currents(V)
tiles = []
for li, L in enumerate(m.layers):
    J = np.zeros(m.N)
    sel = m.e_kind == li
    np.add.at(J, m.e_r[sel], np.abs(I[sel]) / m.e_area[sel] / 2)
    np.add.at(J, m.e_c[sel], np.abs(I[sel]) / m.e_area[sel] / 2)
    img = np.zeros((m.ny, m.nx))
    jj, ii = np.nonzero(m.idx[L] >= 0)
    img[jj, ii] = J[m.idx[L][jj, ii]]
    v = np.clip(img / 200.0, 0, 1)  # full scale 200 A/mm2
    rgb = np.zeros((m.ny, m.nx, 3), np.uint8)
    rgb[..., 0] = (255 * v).astype(np.uint8); rgb[..., 1] = (255 * np.clip(v * 2 - 1, 0, 1)).astype(np.uint8)
    rgb[m.idx[L] >= 0, 2] = np.maximum(rgb[m.idx[L] >= 0, 2], 60)
    t = Image.fromarray(rgb).resize((m.nx // 2, m.ny // 2))
    ImageDraw.Draw(t).text((3, 3), f'{L} max {img.max():.0f}', fill=(255, 255, 255))
    tiles.append(t)
W = sum(t.size[0] for t in tiles[:4]); Hh = max(t.size[1] for t in tiles) * 2
out = Image.new('RGB', (W, Hh))
x = 0
for i, t in enumerate(tiles):
    out.paste(t, ((i % 4) * tiles[0].size[0], (i // 4) * tiles[0].size[1]))
out.save(outp); print('saved', outp, 'origin', round(m.x0, 2), round(m.y0, 2), 'px/mm 10')
