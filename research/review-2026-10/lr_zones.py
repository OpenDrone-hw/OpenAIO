"""Per-layer zone fill area by net + signal track length per layer (after refill). usage: lr_zones.py core|base"""
import sys, collections
from lr_common import *
bn=sys.argv[1]; d=load(bn)
bo=outline(d)
print(f'{bn}: outline area {bo.area:.1f} mm2')
za=collections.defaultdict(float); tl=collections.defaultdict(float); nsig=collections.defaultdict(set)
for z in d['zones']:
    if not z['rule']: za[(z['layer'],z['net'])]+=polys(z['filled']).area
PWR=lambda n: n=='GND' or n.startswith('+') or n.startswith('/CSA')
for t in d['tracks']:
    tl[t['layer']]+=t['len']
    if not PWR(t['net']): nsig[t['layer']].add(t['net'])
for L in d['copper']:
    row=sorted(((n,a) for (l,n),a in za.items() if l==L), key=lambda t:-t[1])
    tot=sum(a for n,a in row)
    print(f"{L:7s} fill {tot:6.0f} mm2 ({100*tot/bo.area:3.0f}%) | "+', '.join(f'{n} {a:.0f}' for n,a in row if a>0.5)+f" | tracks {tl[L]:.0f} mm, {len(nsig[L])} signal nets")
