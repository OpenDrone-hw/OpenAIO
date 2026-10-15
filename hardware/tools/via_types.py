"""Give every through (and edit-form blind) via the via type its connections need, in place: no via or track moves.

Run with KiCad closed, using KiCad's bundled Python:
  $KPY hardware/tools/via_types.py hardware/OpenAIO.kicad_pcb [--buried-size 0.33/0.15 | --buried-drill 0.20] [--dry-run]

Works for any 1+N+1 layer count: microvias F.Cu-In1.Cu and In(N).Cu-B.Cu, buried In1.Cu-In(N).Cu.
--buried-size LAND/DRILL sets every buried via to that size (0.33/0.15 on the 8L Whoop stackup).
--buried-drill is the minimum buried drill (span thickness / NextPCB's 5:1 limit; 0.20 for the 12L build).

used = layers where the via's own net touches its land (track, pad, filled zone), as hdi_via_pass.used_layers.
  F and B both used     -> stays a through via (unchanged)
  otherwise             -> microvia F-In1 if F used, buried In1-In6 if any of In2..In5 is used (or both outer
                           layers are not enough), microvia In6-B if B used
Microvia 0.25 / 0.10, or the routed land where 0.25 would lose a pad or track end. Buried: the via's land, drill min(land - 0.18, 0.25), at least 0.15 (ring 0.09)."""
import os,sys,collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import hdi_via_pass as H
P=H.pcbnew
b=P.LoadBoard(sys.argv[1]); MM=P.FromMM
n_inner=b.GetCopperLayerCount()-2
H.I6=getattr(P,'In%d_Cu'%n_inner)                                  # last inner layer: bottom microvia target
H.INNER={getattr(P,'In%d_Cu'%i) for i in range(2,n_inner)}
MINB=MM(float(sys.argv[sys.argv.index('--buried-drill')+1])) if '--buried-drill' in sys.argv else MM(0.15)
FIXB=[MM(float(x)) for x in sys.argv[sys.argv.index('--buried-size')+1].split('/')] if '--buried-size' in sys.argv else None
P.ZONE_FILLER(b).Fill(b.Zones())
tracks=[t for t in b.GetTracks() if t.GetClass()!='PCB_VIA']
vias=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA']
stat=collections.Counter(); spans=collections.Counter()
pads_by_net=collections.defaultdict(list)
for fp in b.GetFootprints():
    for pad in fp.Pads(): pads_by_net[pad.GetNetCode()].append(pad)
for v in vias:
    if v.GetViaType() not in (P.VIATYPE_THROUGH, P.VIATYPE_BLIND): continue  # edit form: one via per connection
    used=H.used_layers(b,v,tracks)
    # Pads by shape overlap, not a centre hit test: a via off the pad centre whose land overlaps the pad
    # still connects it (U21.19 was missed by the hit test).
    land=P.SHAPE_CIRCLE(v.GetPosition(), v.GetWidth(v.TopLayer())//2)
    for pad in pads_by_net.get(v.GetNetCode(),[]):
        for l in (H.F,H.B):
            if pad.IsOnLayer(l) and pad.GetEffectiveShape(l).Collide(land,0): used.add(l)
    side='Core' if P.ToMM(v.GetPosition().x)>100 else 'Base'
    if H.F in used and H.B in used:
        stat[(side,'through kept')]+=1; continue
    parts=H.plan(used)
    landw=v.GetWidth(v.TopLayer()); drill=v.GetDrillValue()
    bdrill=max(MINB,min(MM(0.25),landw-MM(0.18),drill)); bland=max(landw,bdrill+MM(0.18))
    if FIXB: bland,bdrill=FIXB
    for p in parts:
        n=P.PCB_VIA(b); b.Add(n); n.SetPosition(v.GetPosition()); n.SetNet(v.GetNet())
        if p=='buried':
            n.SetViaType(P.VIATYPE_BURIED); n.SetLayerPair(H.I1,H.I6); n.SetWidth(bland); n.SetDrill(bdrill)
        else:
            n.SetViaType(P.VIATYPE_MICROVIA); n.SetLayerPair(*((H.F,H.I1) if p=='micro_top' else (H.I6,H.B)))
            outer=H.F if p=='micro_top' else H.B
            # 0.25 land unless that loses a pad the routed land reached; then the routed land stays.
            small=P.SHAPE_CIRCLE(v.GetPosition(), MM(0.25)//2)
            need=any(pad.IsOnLayer(outer) and pad.GetEffectiveShape(outer).Collide(land,0) and not pad.GetEffectiveShape(outer).Collide(small,0)
                     for pad in pads_by_net.get(v.GetNetCode(),[])) or any(
                     tr.GetNetCode()==v.GetNetCode() and tr.GetLayer()==outer and tr.GetEffectiveShape(outer).Collide(land,0)
                     and not tr.GetEffectiveShape(outer).Collide(small,0) for tr in tracks)
            n.SetWidth(landw if need else MM(0.25)); n.SetDrill(MM(0.10)); stat[('micro land kept '+str(round(P.ToMM(landw),2)),side)]+=int(need)
    b.Remove(v)
    stat[(side,'+'.join(parts))]+=1
for k,c in sorted(stat.items()): print(c,k)
P.ZONE_FILLER(b).Fill(b.Zones())
if '--dry-run' not in sys.argv: P.SaveBoard(sys.argv[1],b); print('saved')
