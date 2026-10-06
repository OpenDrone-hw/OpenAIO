"""Compact per-rail summary of lr_power.json (markdown)."""
import json
R = json.load(open('lr_power.json'))
print('| board | net | scenario | sinks | R source->sink mOhm (min..max) | narrowest mid-path cut mm2 (1-oz-equiv mm) @xy, worst sink | max drop mV | loss W | vias >1 A / >2 A | hottest via A @xy |')
print('|---|---|---|---|---|---|---|---|---|---|')
for r in R:
    s = [x for x in r['sinks'] if 'R_mohm' in x]
    if not s:
        continue
    w = min(s, key=lambda x: x['cut_mm2'])
    sc = r.get('scenario', {})
    tv = sc.get('top_vias', [[0, 0, 0]])[0]
    print(f"| {r['board']} | {r['net']} | {r['note']} | {len(s)} | {min(x['R_mohm'] for x in s):.3f}..{max(x['R_mohm'] for x in s):.3f} | "
          f"{w['cut_mm2']:.3f} ({w['cut_mm2']/0.035:.1f}) @({w['cut_loc'][0]:.1f},{w['cut_loc'][1]:.1f}) {w['label']} | {sc.get('max_drop_mV', 0):.1f} | {sc.get('loss_W', 0):.2f} | "
          f"{sc.get('vias_over_1A', 0)} / {sc.get('vias_over_2A', 0)} | {tv[0]:.2f} @({tv[1]:.2f},{tv[2]:.2f}) |")
