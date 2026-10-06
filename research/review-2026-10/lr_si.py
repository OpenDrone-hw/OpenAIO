"""Noise / SI screening on refilled copper.
For every sensitive (victim) track, sampled every 0.05 mm:
  * same layer: min edge-to-edge gap to each aggressor class, length with gap <= 0.5 mm and <= 0.2 mm
  * adjacent copper layers (above/below): length lying over/under aggressor copper (lateral gap <= 0.2 mm)
  * reference: which net's fill is directly above/below on the nearest layers (solid = inside the fill and >= 0.1 mm
    from its edge), void fraction, number of reference changes along the track (split crossings)
  * cross-board: Core B.Cu victims vs Base F.Cu copper (0.1-0.15 mm away through two masks and the LGA gap)
Writes lr_si.json, prints markdown."""
import re, json, collections, math
import numpy as np
import shapely
from shapely import affinity
from lr_common import *
from lr_dc import net_layer_geoms

STEP = 0.05
VICT = {
    'USB': r'^(USB_D[+-]|Net-\(U2-USB_D[PM]\))$',
    'SD SPI0': r'^(SPI0\.(MISO|MOSI|SCK)|FLASH_CS)$',
    'IMU SPI1': r'^/IMU/',
    'FC crystal': r'^(/RP2354A/X(IN|OUT)|Net-\(C10-Pad2\))$',
    'RX xtal/TCXO': r'^(/RX/XTAL_[NP]|Net-\(OSC1-Out_Put\)|Net-\(U21-XTA\))$',
    'ADC (CURR, VBAT)': r'^(CURR|/RP2354A/(ESC_CURR|ADC_VBAT))$',
    'Video': r'^/OSD/(VIDEO_IN|VIDEO_OUT|VID_FILT|VID_DC|OSD_LVL)$',
    'DShot MOTOR1-4': r'^MOTOR[1-4]$',
    'SX1281 SPI/ctl': r'^/RX/(MOSI|MISO|SCK|NSS|BUSY|DIO1|RST)$',
    'RF': r'^(Net-\(FL1-(IN|OUT)\)|/RX/WIFI|Net-\(U22-LNA_IN\))$',
    'CRSF UART1': r'^UART1_(RX|TX)$',
}
AGG = {
    'phase nodes': r'^/[1-4][ABC]$',
    'gate drive': r'^(/ESC[1-4]/G[HL][ABC]|Net-\(Q\d+-G\)|Net-\(U(14|16|18|20)-VB\d\))$',
    'buck/LX SW': r'^Net-\((U3-SW|U4-SW|U3-CB|U4-CB|U21-DCC_SW|U2-VREG_LX)\)$',
    '+BATT': r'^\+BATT$',
}
c = load('core'); b = load('base')
BOARDS = {'core': c, 'base': b}


def nets_of(d):
    s = set()
    for f in d['footprints']:
        for p in f['pads']:
            s.add(p['net'])
    for t in d['tracks']:
        s.add(t['net'])
    return s


def agg_geoms(bn, d):
    out = {}
    for k, rx in AGG.items():
        per = collections.defaultdict(list)
        for n in nets_of(d):
            if re.match(rx, n):
                g, _ = net_layer_geoms(d, bn, n)
                for L, gg in g.items():
                    per[L].append(gg)
        out[k] = {L: unary_union(v) for L, v in per.items()}
    return out


def fills(d):
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    for z in d['zones']:
        if not z['rule']:
            per[z['layer']][z['net']].append(polys(z['filled']))
    return {L: {n: unary_union(v) for n, v in m.items()} for L, m in per.items()}


def samples(t):
    a, bb = np.array(t['a']), np.array(t['b'])
    L = max(np.linalg.norm(bb - a), 1e-9)
    n = max(int(L / STEP), 1)
    s = (np.arange(n) + 0.5) / n
    pts = a[None, :] + s[:, None] * (bb - a)[None, :]
    return pts, L / n


AG = {bn: agg_geoms(bn, d) for bn, d in BOARDS.items()}
FI = {bn: fills(d) for bn, d in BOARDS.items()}
# Base F.Cu fills/aggressors seen from the Core bottom (core coords = base - OFF)
base_F_fill = {n: affinity.translate(g, -OFF[0], -OFF[1]) for n, g in FI['base'].get('F.Cu', {}).items()}
base_F_agg = {k: affinity.translate(v['F.Cu'], -OFF[0], -OFF[1]) for k, v in AG['base'].items() if 'F.Cu' in v}
base_F_tracks = collections.defaultdict(list)
for t in b['tracks']:
    if t['layer'] == 'F.Cu':
        base_F_tracks[t['net']].append(affinity.translate(track_geom(t), -OFF[0], -OFF[1]))

res = []
for bn, d in BOARDS.items():
    cu = d['copper']
    z = layer_z(bn)
    for vk, vrx in VICT.items():
        vnets = sorted({t['net'] for t in d['tracks'] if re.match(vrx, t['net'])})
        if not vnets:
            continue
        for L in cu:
            trk = [t for t in d['tracks'] if t['layer'] == L and t['net'] in vnets]
            if not trk:
                continue
            P = []; W = []; DL = []; NET = []
            for t in trk:
                pts, dl = samples(t)
                P.append(pts); W += [t['w']] * len(pts); DL += [dl] * len(pts); NET += [t['net']] * len(pts)
            P = np.vstack(P); W = np.array(W); DL = np.array(DL)
            pts = shapely.points(P)
            row = dict(board=bn, victim=vk, layer=L, nets=vnets, length=float(DL.sum()), agg={})
            i = cu.index(L)
            nbrs = [cu[j] for j in (i - 1, i + 1) if 0 <= j < len(cu)]
            for ak, perL in AG[bn].items():
                rec = {}
                if L in perL and not perL[L].is_empty:
                    dd = shapely.distance(pts, perL[L]) - W / 2
                    rec['same_min'] = float(dd.min()); rec['same_le0.5'] = float(DL[dd <= 0.5].sum()); rec['same_le0.2'] = float(DL[dd <= 0.2].sum())
                    k = int(np.argmin(dd)); rec['same_at'] = (round(float(P[k][0]), 2), round(float(P[k][1]), 2))
                for Ln in nbrs:
                    if Ln in perL and not perL[Ln].is_empty:
                        dd = shapely.distance(pts, perL[Ln]) - W / 2
                        ov = float(DL[dd <= 0.2].sum())
                        if ov > 0:
                            k = int(np.argmin(dd))
                            rec[f'adj_{Ln}'] = (round(ov, 2), round(abs(z[Ln] - z[L]), 3), (round(float(P[k][0]), 2), round(float(P[k][1]), 2)))
                if rec:
                    row['agg'][ak] = rec
            # cross-board exposure of Core B.Cu tracks to the Base F.Cu copper directly below
            if bn == 'core' and L == 'B.Cu':
                for ak, g in base_F_agg.items():
                    dd = shapely.distance(pts, g) - W / 2
                    ov = float(DL[dd <= 0.2].sum())
                    if ov > 0:
                        row['agg'].setdefault(ak, {})['xboard_baseF'] = round(ov, 2)
                # base F.Cu signal tracks under core B.Cu victims
                xs = {}
                for n, gl in base_F_tracks.items():
                    if n in vnets or n == 'GND' or n.startswith('+'):
                        continue
                    g = unary_union(gl)
                    dd = shapely.distance(pts, g) - W / 2
                    ov = float(DL[dd <= 0.2].sum())
                    if ov > 0.3:
                        xs[n] = round(ov, 2)
                if xs:
                    row['xboard_base_tracks'] = xs
            # reference planes
            refs = {}
            for Ln in nbrs + (['BASE F.Cu'] if (bn == 'core' and L == 'B.Cu') else []):
                fl = base_F_fill if Ln == 'BASE F.Cu' else FI[bn].get(Ln, {})
                lab = np.array(['void'] * len(P), dtype=object)
                for n, g in fl.items():
                    if g.is_empty:
                        continue
                    inside = shapely.contains(g, pts)
                    if inside.any():
                        edge = shapely.distance(pts, g.boundary)
                        solid = inside & (edge >= 0.1)
                        lab[solid] = n
                        lab[inside & ~solid] = 'edge:' + n
                cnt = collections.Counter()
                for l_, dl in zip(lab, DL):
                    cnt[l_] += dl
                changes = int(sum(1 for a_, b_ in zip(lab, lab[1:]) if a_ != b_ and not str(a_).startswith('edge') and not str(b_).startswith('edge')))
                dist = 0.11 if Ln == 'BASE F.Cu' else abs(z[Ln] - z[L])
                refs[Ln] = dict(h=round(dist, 3), share={k: round(v / DL.sum(), 3) for k, v in cnt.most_common()}, changes=changes)
            row['ref'] = refs
            res.append(row)

json.dump(res, open('lr_si.json', 'w'), indent=1, default=str)

print('| board | victim | layer | len mm | nearest aggressor same layer (gap mm @xy) | same-layer run <=0.5 / <=0.2 mm | adjacent-layer overlap mm (layer, h) | reference (nearest layers: net share) |')
print('|---|---|---|---|---|---|---|---|')
for r in res:
    same = []
    runs = []
    adj = []
    for ak, rec in r['agg'].items():
        if 'same_min' in rec:
            same.append((rec['same_min'], ak, rec['same_at']))
            if rec['same_le0.5'] > 0:
                runs.append(f"{ak} {rec['same_le0.5']:.1f}/{rec['same_le0.2']:.1f}")
        for k, v in rec.items():
            if k.startswith('adj_'):
                adj.append(f"{ak} {v[0]:.1f} ({k[4:].replace('.Cu','')}, {v[1]}) @{v[2]}")
            if k == 'xboard_baseF':
                adj.append(f"{ak} {v:.1f} (BASE F, ~0.11)")
    same.sort()
    s0 = f"{same[0][1]} {same[0][0]:.2f} @{same[0][2]}" if same else '-'
    refs = '; '.join(f"{Ln.replace('.Cu','')}(h{v['h']}): " + ', '.join(f"{k} {x:.0%}" for k, x in list(v['share'].items())[:3]) + (f", {v['changes']} splits" if v['changes'] else '')
                     for Ln, v in r['ref'].items())
    print(f"| {r['board']} | {r['victim']} | {r['layer'].replace('.Cu','')} | {r['length']:.1f} | {s0} | {', '.join(runs) or '-'} | {'; '.join(adj) or '-'} | {refs} |")
    if r.get('xboard_base_tracks'):
        print(f"|  |  |  |  | base F.Cu signal tracks directly under (mm): {r['xboard_base_tracks']} | | | |")
