"""Part heights from available VRML models (lib.3dshapes, OPENDRONE_LIB 3dmodel); x2.54 VRML unit; model z offset added.
Parts whose model is a KiCad stock STEP (not installed here) get the nominal package height from NOMINAL."""
import re, os, json, glob
from lr_common import *
HW = os.path.join(HERE, '..', 'rev', 'd81e559', 'hardware')
OD = '/home/user/OpenAIO/hardware/KiCad-Library'
NOMINAL = {  # mm, datasheet / IPC nominal maximum heights for stock KiCad packages used here
    'C_0201': 0.33, 'R_0201': 0.28, 'L_0201': 0.33, 'C_0402': 0.55, 'LED_0402': 0.5, 'C_0603': 0.9, 'C_0805': 1.35, 'L_0805': 1.0,
    'C_1206': 1.8, 'R_2512': 0.65, 'PowerDI3333': 0.8, 'QFN-32': 0.9, 'WSON-6': 0.8, 'SOT-363': 1.1, 'QFN-28': 0.75}


def wrl_zrange(path):
    try:
        s = open(path, errors='ignore').read()
    except OSError:
        return None
    zs = []
    for blk in re.findall(r'point\s*\[([^\]]*)\]', s):
        v = [float(x) for x in re.findall(r'-?\d+\.?\d*(?:[eE]-?\d+)?', blk)]
        zs += v[2::3]
    if not zs:
        return None
    return min(zs) * 2.54, max(zs) * 2.54


def height(f):
    for m in f['models']:
        p = m['file'].replace('${KIPRJMOD}', HW).replace('${OPENDRONE_LIB}', OD)
        if p.endswith('.step'):
            alt = p[:-5] + '.wrl'
            p = alt if os.path.exists(alt) else p
        if p.endswith('.wrl') and os.path.exists(p):
            r = wrl_zrange(p)
            if r:
                return r[1] + m['off'][2], 'wrl'
        for k, v in NOMINAL.items():
            if k in m['file'] or k in f['fpid']:
                return v, 'nominal'
    for k, v in NOMINAL.items():
        if k in f['fpid']:
            return v, 'nominal'
    return None, 'unknown'


if __name__ == '__main__':
    out = {}
    for bn in ('core', 'base'):
        d = load(bn)
        rows = []
        for f in d['footprints']:
            h, src = height(f)
            rows.append((h if h is not None else -1, f['ref'], f['val'], f['side'], src))
        rows.sort(reverse=True)
        out[bn] = rows
        print(bn, 'tallest:', [(r[1], r[3], round(r[0], 2), r[4]) for r in rows[:14]])
        print('   unknown height:', [r[1] for r in rows if r[4] == 'unknown'])
    json.dump(out, open('lr_heights.json', 'w'), indent=1)
