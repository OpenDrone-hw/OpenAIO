"""Vias inside / touching the LGA pads (J91 core B.Cu, J90 base F.Cu): solder-wicking risk, needs plugged+capped vias."""
from lr_common import *
from shapely.geometry import Point
for bn, ref in (('core','J91'),('base','J90')):
    d=load(bn); J=[f for f in d['footprints'] if f['ref']==ref][0]
    tot=0; touching=0; per=[]
    for p in J['pads']:
        g=pad_geom(p)
        inside=[v for v in d['vias'] if g.contains(Point(v['x'],v['y']))]
        touch=[v for v in d['vias'] if not g.contains(Point(v['x'],v['y'])) and g.distance(Point(v['x'],v['y']).buffer(v['d']/2))<1e-6]
        if inside or touch: per.append((p['num'],p['net'],len(inside),len(touch)))
        tot+=len(inside); touching+=len(touch)
    print(f"{bn} {ref}: {len(J['pads'])} pads; vias with centre inside a pad: {tot}; vias overlapping pad edge: {touching}; pads affected: {len(per)}")
    print('   ', per)
