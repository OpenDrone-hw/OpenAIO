"""Move conflicting vias (with their stack and their own track ends) up to RMAX mm to a spot that clears other-net
copper on every layer they span. Nothing else moves; zones are ignored (they refill). Same-net copper that touched
a via before the move must still touch it after, so no connection is lost.

Run with KiCad closed:  $KPY hardware/tools/via_nudge.py hardware/OpenAIO.kicad_pcb [RMAX, default 0.25] [--dry-run]
Clearance per net class from the .kicad_pro, hole clearance 0.18, hole to hole 0.25 (0.20 same net)."""
import os,sys,math,json,collections
s,n=os.dup(2),os.open(os.devnull,os.O_WRONLY);os.dup2(n,2)
import pcbnew as P
os.dup2(s,2)
MM=P.FromMM
path=sys.argv[1]; RMAX=float(sys.argv[2]) if len(sys.argv)>2 else 0.25
b=P.LoadBoard(path)
pro=json.load(open(os.path.splitext(path)[0]+'.kicad_pro'))
cls={c['name']:c['clearance'] for c in pro['net_settings']['classes']}
def clr(a,bb):
    return MM(max(cls.get(a.GetNetClassName(),0.09),cls.get(bb.GetNetClassName(),0.09)))+MM(0.002)
HOLE_CLR=MM(0.18)+MM(0.002)
def hh(a,bb): # hole to hole
    if a.GetNetCode()==bb.GetNetCode(): return MM(0.20)
    return MM(0.25)
CU=list(b.GetEnabledLayers().CuStack())
tracks=[t for t in b.GetTracks() if t.GetClass()=='PCB_TRACK']
vias=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA']
pads=[p for f in b.GetFootprints() for p in f.Pads()]
G=MM(1.0)
grid=collections.defaultdict(list)
def cells(bb):
    for i in range(bb.GetLeft()//G-1,bb.GetRight()//G+2):
        for j in range(bb.GetTop()//G-1,bb.GetBottom()//G+2): yield (i,j)
for o in tracks+vias+pads:
    for c in cells(o.GetBoundingBox()): grid[c].append(o)
def near(p):
    seen=set()
    for i in range(p.x//G-1,p.x//G+2):
        for j in range(p.y//G-1,p.y//G+2):
            for o in grid.get((i,j),[]):
                if id(o) not in seen: seen.add(id(o)); yield o
def vlayers(v): return [l for l in CU if v.IsOnLayer(l)]
# stacks: vias at same position and net
stacks=collections.defaultdict(list)
for v in vias: stacks[(v.GetNetCode(),v.GetPosition().x,v.GetPosition().y)].append(v)
def own_tracks(stack,pos):
    net=stack[0].GetNetCode(); out=[]
    for o in near(pos):
        if o.GetClass()=='PCB_TRACK' and o.GetNetCode()==net:
            if o.GetStart()==pos: out.append((o,'s'))
            elif o.GetEnd()==pos: out.append((o,'e'))
    return out
def touching(stack,own,pos):
    # same-net copper (other than the stretched track ends) whose shape meets the stack's lands at pos
    ownids={id(v) for v in stack}|{id(t) for t,_ in own}; net=stack[0].GetNetCode(); out=[]
    for o in near(pos):
        if id(o) in ownids or o.GetNetCode()!=net: continue
        for v in stack:
            hit=False
            for l in vlayers(v):
                if o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(P.SHAPE_CIRCLE(pos,v.GetWidth(l)//2),0): hit=True; break
            if hit: out.append((o,v)); break
    return out
def ok_at(stack,own,newp,keep=()):
    ownids={id(v) for v in stack}|{id(t) for t,_ in own}
    net=stack[0].GetNetCode()
    for o,v in keep:
        if not any(o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(P.SHAPE_CIRCLE(newp,v.GetWidth(l)//2),0) for l in vlayers(v)): return False
    for v in stack:
        for l in vlayers(v):
            land=P.SHAPE_CIRCLE(newp,v.GetWidth(l)//2)
            for o in near(newp):
                if id(o) in ownids or not o.IsOnLayer(l): continue
                if o.GetNetCode()==net and o.GetClass()!='PCB_VIA': continue
                sh=o.GetEffectiveShape(l)
                if o.GetNetCode()!=net and sh.Collide(land,clr(v,o)): return False
        hole=P.SHAPE_CIRCLE(newp,v.GetDrillValue()//2)
        for o in near(newp):
            if id(o) in ownids: continue
            if o.GetClass()=='PCB_VIA':
                d=(o.GetPosition()-newp).EuclideanNorm()-v.GetDrillValue()/2-o.GetDrillValue()/2
                shared=any(o.IsOnLayer(l) for l in vlayers(v))
                if shared and d<hh(v,o) and not (o.GetNetCode()==net and o.GetPosition()==newp): return False
            elif o.GetNetCode()!=net:
                for l in vlayers(v):
                    if o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(hole,HOLE_CLR): return False
                if o.GetClass()=='PAD' and o.HasHole() and o.GetEffectiveHoleShape().Collide(hole,MM(0.25)): return False
    # stretched own tracks
    for t,end in own:
        a=newp if end=='s' else t.GetStart(); e=newp if end=='e' else t.GetEnd()
        seg=P.SHAPE_SEGMENT(a,e,t.GetWidth())
        mid=P.VECTOR2I((a.x+e.x)//2,(a.y+e.y)//2)
        for o in list(near(a))+list(near(e))+list(near(mid)):
            if id(o) in ownids or o.GetNetCode()==t.GetNetCode() or not o.IsOnLayer(t.GetLayer()): continue
            if o.GetEffectiveShape(t.GetLayer()).Collide(seg,clr(t,o)): return False
    return True
def bad(stack,pos): return not ok_at(stack,own_tracks(stack,pos),pos)
moved=0; stuck=0; cand=[]
for k,st in stacks.items():
    pos=st[0].GetPosition()
    if bad(st,pos): cand.append(k)
print('stacks in conflict',len(cand),'of',len(stacks))
for k in cand:
    st=stacks[k]; pos=st[0].GetPosition(); own=own_tracks(st,pos)
    if ok_at(st,own,pos): continue  # an earlier move fixed it
    keep=touching(st,own,pos)
    done=False
    r=0.025
    while r<=RMAX+1e-9 and not done:
        nang=max(8,int(2*math.pi*r/0.025))
        for i in range(nang):
            ang=2*math.pi*i/nang
            newp=P.VECTOR2I(int(pos.x+MM(r)*math.cos(ang)),int(pos.y+MM(r)*math.sin(ang)))
            if ok_at(st,own,newp,keep):
                for o in st+[t for t,_ in own]:
                    for c in cells(o.GetBoundingBox()):
                        if o in grid[c]: grid[c].remove(o)
                for v in st: v.SetPosition(newp)
                for t,end in own:
                    (t.SetStart if end=='s' else t.SetEnd)(newp)
                for o in st+[t for t,_ in own]:
                    for c in cells(o.GetBoundingBox()): grid[c].append(o)
                moved+=1; done=True; break
        r+=0.025
    if not done: stuck+=1
print('moved',moved,'still in conflict',stuck)
P.ZONE_FILLER(b).Fill(b.Zones())
if '--dry-run' not in sys.argv: P.SaveBoard(path,b); print('saved')
