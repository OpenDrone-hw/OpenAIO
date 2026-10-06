"""Re-evaluate every candidate result with the current cost (GPIOW from env, default 2.0) and save the best as chosen.json."""
import json, glob, sys
import r2a_geo as G, r2a_opt as O
u7c = json.load(open(G.HERE + '/u7.json'))
u7, blk = G.u7_place(u7c['cx'], u7c['cy'], u7c['rot']); u7['blk'] = blk
cands = []
for fn in ['best_final.json', 'sweep_deep.json', 'sweep_deep2.json', 'sweep_final.json']:
    try:
        r = json.load(open(G.HERE + '/' + fn))
    except FileNotFoundError:
        continue
    for i, d in enumerate(r if isinstance(r, list) else [r]):
        if (d['ox'], d['oy'], d['ngnd']) != (0.25, 1.25, 21):
            continue
        cands.append((fn, i, d))
O.setup(0.25, 1.25, u7)
best = None
for fn, i, d in cands:
    det = O.evaluate(d['assign'], d['gmap'], detail=True)
    print(fn, i, round(det['total'], 1), 'wl', round(det['wl'], 1), 'sig', round(det['sig'], 1), {k: round(v, 1) for k, v in det['pen'].items()})
    if best is None or det['total'] < best[0]:
        best = (det['total'], fn, i, d)
d = best[3]; d['detail'] = O.evaluate(d['assign'], d['gmap'], detail=True); d['cost'] = best[0]
json.dump(d, open(G.HERE + '/chosen.json', 'w'), default=float)
print('chosen', best[1], best[2], round(best[0], 1))
