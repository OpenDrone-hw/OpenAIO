"""Standardise track widths without moving any track (run with KiCad closed:
$KPY hardware/tools/track_widths.py hardware/OpenAIO.kicad_pcb [--dry-run]).
Digital signals 0.10, gate drive 0.25, power rails and GND at least 0.30; phase, switch-node, feedback, sense,
video, USB, RF and +BATT tracks are left as routed. A width change is kept only when the track still clears
other-net copper (tracks, vias, pads; zones refill) at the new width."""
import os,sys,json,collections,re
s,n=os.dup(2),os.open(os.devnull,os.O_WRONLY);os.dup2(n,2)
import pcbnew as P
os.dup2(s,2)
MM=P.FromMM; path=sys.argv[1]
b=P.LoadBoard(path); pro=json.load(open(os.path.splitext(path)[0]+'.kicad_pro'))
cls={c['name']:c['clearance'] for c in pro['net_settings']['classes']}
def clr(a,o): return MM(max(cls.get(a.GetNetClassName(),0.09),cls.get(o.GetNetClassName(),0.09)))+MM(0.002)
POWER={'+5V','+3.3V','+3V3','+10V','+4v5','+1.1V','+1.8V_GYRO','+5V_USB','GND','/ESC1/vdda','/ESC2/vdda','/ESC3/vdda','/ESC4/vdda'}
KEEP=re.compile(r'^(USB_D[+-]|\+BATT|/CSA\+|Net-\(FL1|/RX/WIFI|Net-\(U22-LNA|.*ANT.*)$')
GATE=re.compile(r'^Net-\(Q\d+-G\)$')
DIGITAL=re.compile(r'^(UART\d_(TX|RX)|/Pads/(PIOUART0_TX|PU0RX|I2C0\.(SDA|SCL))|SPI\d\.(SCK|MOSI|MISO)|FLASH_CS|MOTOR[1-4]|LED_STRIP|/RP2354A/LED_STRIP_L|/RP2354A/(LED0|BEEPER)|/IMU/.*|/RX/(MOSI|MISO|SCK|NSS|RST|BUSY|DIO\d|BOOT|LED)|SWDIO|SWCLK|/OSD/(OSD_W|OSD_EN|OSD_SYNC)|Net-\(U(13|15|17|19)-P[AB]\d+\))$')
def target(t):
    nm=t.GetNetname(); w=P.ToMM(t.GetWidth())
    if KEEP.match(nm) or t.GetNetClassName() in ('RF','USB','VBAT'): return None
    if GATE.match(nm): return 0.25 if w<0.25 else None
    if nm in POWER or t.GetNetClassName()=='Power': return 0.30 if w<0.30 else None
    if DIGITAL.match(nm): return 0.10 if abs(w-0.10)>1e-6 else None
    return None  # phase, switch nodes, feedback, sense, buzzer, video: left as routed
tracks=[t for t in b.GetTracks() if t.GetClass()=='PCB_TRACK']
others=[t for t in b.GetTracks()]+[p for f in b.GetFootprints() for p in f.Pads()]
G=MM(1.0); grid=collections.defaultdict(list)
def cells(bb):
    for i in range(bb.GetLeft()//G-1,bb.GetRight()//G+2):
        for j in range(bb.GetTop()//G-1,bb.GetBottom()//G+2): yield (i,j)
for o in others:
    for c in cells(o.GetBoundingBox()): grid[c].append(o)
def near(t):
    seen=set()
    for c in cells(t.GetBoundingBox()):
        for o in grid.get(c,[]):
            if id(o) not in seen: seen.add(id(o)); yield o
st=collections.Counter()
# shrink first (frees room), then grow
order=sorted(tracks,key=lambda t:(0 if (target(t) or 9)<P.ToMM(t.GetWidth()) else 1))
for t in order:
    w=target(t)
    if w is None: continue
    old=t.GetWidth(); new=MM(w)
    if new<old:
        t.SetWidth(new); st['shrunk to %.2f'%w]+=1; continue
    t.SetWidth(new); l=t.GetLayer(); sh=t.GetEffectiveShape(l); ok=True
    for o in near(t):
        if o is t or o.GetNetCode()==t.GetNetCode() or not o.IsOnLayer(l): continue
        if o.GetEffectiveShape(l).Collide(sh,clr(t,o)): ok=False; break
    if ok: st['grown to %.2f'%w]+=1
    else: t.SetWidth(old); st['kept (no room for %.2f)'%w]+=1
for k,v in sorted(st.items()): print(v,k)
P.ZONE_FILLER(b).Fill(b.Zones())
if '--dry-run' not in sys.argv: P.SaveBoard(path,b); print('saved')
