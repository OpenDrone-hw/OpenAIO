"""Dump a KiCad board to JSON for geometric analysis (pcbnew API, zones refilled).
usage: python3 dump.py <board.kicad_pcb> <out.json>
Everything in mm. Polygons are lists of rings [[x,y],...]; zones/pads as list of
(outer, [holes]) polygons. Fab outline comes from F.Fab/B.Fab graphics of each
footprint (convex hull of all fab points if they do not close).
"""
import sys, json, math, pcbnew

MM = pcbnew.ToMM
MAXERR = pcbnew.FromMM(0.005)

def polyset_to_list(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        outer = [[MM(o.CPoint(j).x), MM(o.CPoint(j).y)] for j in range(o.PointCount())]
        holes = []
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h)
            holes.append([[MM(hh.CPoint(j).x), MM(hh.CPoint(j).y)] for j in range(hh.PointCount())])
        out.append([outer, holes])
    return out

b = pcbnew.LoadBoard(sys.argv[1])
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
b.BuildConnectivity()
conn = b.GetConnectivity()

LN = b.GetLayerName
cu = [LN(l) for l in b.GetEnabledLayers().CuStack()]

# stackup thickness by copper layer order
bds = b.GetDesignSettings()
stack = []
try:
    st = bds.GetStackupDescriptor()
    for it in st.GetList():
        stack.append(dict(name=it.GetLayerName(), type=it.GetTypeName(), t=MM(it.GetThickness())))
except Exception as e:
    stack = [dict(err=str(e))]

outline = pcbnew.SHAPE_POLY_SET()
b.GetBoardPolygonOutlines(outline, True)

out = dict(file=sys.argv[1], copper=cu, stack=stack, outline=polyset_to_list(outline),
           unconnected=conn.GetUnconnectedCount(False),
           footprints=[], tracks=[], vias=[], zones=[])

for fp in b.GetFootprints():
    side = 'B' if fp.IsFlipped() else 'F'
    fab = LN(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
    silk = LN(pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS)
    silkpts = []
    for g in fp.GraphicalItems():
        if g.GetClass() in ('PCB_SHAPE', 'FP_SHAPE') and LN(g.GetLayer()) == silk:
            ps = pcbnew.SHAPE_POLY_SET()
            g.TransformShapeToPolygon(ps, g.GetLayer(), 0, MAXERR, pcbnew.ERROR_INSIDE)
            for o, _h in polyset_to_list(ps):
                silkpts += o
    fabpts, fabsegs, fabpolys = [], [], []
    for g in fp.GraphicalItems():
        if g.GetClass() not in ('PCB_SHAPE', 'FP_SHAPE'):
            continue
        if LN(g.GetLayer()) != fab:
            continue
        st_ = g.GetShape()
        if st_ == pcbnew.SHAPE_T_SEGMENT:
            a, c = g.GetStart(), g.GetEnd()
            fabsegs.append([[MM(a.x), MM(a.y)], [MM(c.x), MM(c.y)]])
            fabpts += [[MM(a.x), MM(a.y)], [MM(c.x), MM(c.y)]]
        else:
            ps = pcbnew.SHAPE_POLY_SET()
            g.TransformShapeToPolygon(ps, g.GetLayer(), 0, MAXERR, pcbnew.ERROR_INSIDE)
            pl = polyset_to_list(ps)
            if st_ in (pcbnew.SHAPE_T_RECTANGLE, pcbnew.SHAPE_T_POLY, pcbnew.SHAPE_T_CIRCLE):
                # filled or outline - use the corner points
                if st_ == pcbnew.SHAPE_T_RECTANGLE:
                    cs = g.GetRectCorners() if hasattr(g, 'GetRectCorners') else []
                    pts = [[MM(p.x), MM(p.y)] for p in cs]
                    if pts:
                        fabpolys.append(pts)
                        fabpts += pts
                        continue
            for o, _h in pl:
                fabpts += o
    pads = []
    for p in fp.Pads():
        pos = p.GetPosition()
        layers = [LN(l) for l in p.GetLayerSet().Seq() if pcbnew.IsCopperLayer(l)]
        polys = {}
        for L in (pcbnew.F_Cu, pcbnew.B_Cu):
            if p.IsOnLayer(L):
                ps = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(ps, L, 0, MAXERR, pcbnew.ERROR_INSIDE)
                polys[LN(L)] = polyset_to_list(ps)
        if not polys and layers:
            ps = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(ps, p.GetLayerSet().Seq()[0], 0, MAXERR, pcbnew.ERROR_INSIDE)
            polys[layers[0]] = polyset_to_list(ps)
        sz = p.GetSize(pcbnew.F_Cu) if hasattr(p, 'GetSize') else None
        try:
            drill = MM(p.GetDrillSize().x)
        except Exception:
            drill = 0
        pads.append(dict(num=p.GetNumber(), net=p.GetNetname(), fn=p.GetPinFunction(), type=p.GetPinType(),
                         x=MM(pos.x), y=MM(pos.y), layers=layers, polys=polys, drill=drill,
                         attr=int(p.GetAttribute())))
    crt = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    props = {}
    try:
        for f in fp.GetFields():
            props[f.GetName()] = f.GetText()
    except Exception:
        pass
    models = []
    try:
        for m in fp.Models():
            models.append(dict(file=m.m_Filename, off=[m.m_Offset.x, m.m_Offset.y, m.m_Offset.z]))
    except Exception:
        pass
    pos = fp.GetPosition()
    out['footprints'].append(dict(ref=fp.GetReference(), val=fp.GetValue(), fpid=str(fp.GetFPIDAsString()),
        side=side, x=MM(pos.x), y=MM(pos.y), rot=fp.GetOrientationDegrees(), attr=fp.GetAttributes(),
        dnp=fp.IsDNP(), silkpts=silkpts, fabpts=fabpts, fabsegs=fabsegs, fabpolys=fabpolys,
        crt=polyset_to_list(crt), pads=pads, props=props, models=models))

for t in b.GetTracks():
    n = t.GetNetname()
    if t.Type() == pcbnew.PCB_VIA_T:
        v = t
        top, bot = v.TopLayer(), v.BottomLayer()
        out['vias'].append(dict(x=MM(v.GetPosition().x), y=MM(v.GetPosition().y), d=MM(v.GetWidth(pcbnew.F_Cu)),
                                drill=MM(v.GetDrillValue()), top=LN(top), bot=LN(bot), net=n,
                                vtype=int(v.GetViaType())))
    else:
        a, c = t.GetStart(), t.GetEnd()
        rec = dict(a=[MM(a.x), MM(a.y)], b=[MM(c.x), MM(c.y)], w=MM(t.GetWidth()), layer=LN(t.GetLayer()), net=n,
                   len=MM(t.GetLength()))
        if t.Type() == pcbnew.PCB_ARC_T:
            m = t.GetMid()
            rec['mid'] = [MM(m.x), MM(m.y)]
        out['tracks'].append(rec)

for z in b.Zones():
    if z.GetIsRuleArea():
        lays = [LN(l) for l in z.GetLayerSet().Seq()]
        out['zones'].append(dict(rule=True, name=z.GetZoneName(), layers=lays,
            outline=polyset_to_list(z.Outline()),
            notracks=z.GetDoNotAllowTracks(), novias=z.GetDoNotAllowVias(), nofp=z.GetDoNotAllowFootprints(),
            nopour=z.GetDoNotAllowZoneFills()))
        continue
    for L in z.GetLayerSet().Seq():
        if not pcbnew.IsCopperLayer(L):
            continue
        fp_ = z.GetFilledPolysList(L)
        out['zones'].append(dict(rule=False, net=z.GetNetname(), layer=LN(L), prio=z.GetAssignedPriority(),
                                 filled=polyset_to_list(fp_), outline=polyset_to_list(z.Outline()),
                                 minw=MM(z.GetMinThickness())))

json.dump(out, open(sys.argv[2], 'w'))
print('dumped', sys.argv[1], 'fps', len(out['footprints']), 'tracks', len(out['tracks']), 'vias', len(out['vias']),
      'zones', len(out['zones']), 'unconnected', out['unconnected'])
