"""Sweep grid offsets / GND counts with r2a_opt.py in parallel. Usage: r2a_sweep.py <mode> -> writes sweep_<mode>.json"""
import sys, json, subprocess, itertools
from multiprocessing import Pool
import r2a_geo as G

mode = sys.argv[1]
HERE = G.HERE


def job(args):
    ox, oy, ng, iters, seeds, extra = args
    import os
    env = dict(os.environ)
    ex = [e for e in extra if not e.startswith('SEED0=')]
    for e in extra:
        if e.startswith('SEED0='):
            env['SEED0'] = e.split('=')[1]
    cmd = ['python3', HERE + '/r2a_opt.py', str(ox), str(oy), str(ng), str(iters), str(seeds)] + ex
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE, env=env).stdout.strip().splitlines()[-1]
    d = json.loads(out)
    print(f"{extra} ox {ox} oy {oy} G {ng} sites {d['nsites']} cost {d['cost']:.1f} wl {d['detail']['wl']:.1f} sig {d['detail']['sig']:.1f} pen {d['detail']['pen']}", flush=True)
    return d


if __name__ == '__main__':
    jobs = []
    if mode == 'offsets':
        for i, j in itertools.product(range(8), range(8)):
            ox, oy = i * 0.25, j * 0.25
            if len(G.grid_sites(ox, oy)) >= 75:
                jobs.append((ox, oy, 19, 150000, 2, []))
    elif mode.startswith('gnd'):
        ox, oy = float(sys.argv[2]), float(sys.argv[3])
        for ng in range(17, 24):
            jobs.append((ox, oy, ng, 300000, 3, []))
    elif mode == 'final':
        for ox, oy in ((0.25, 1.25), (1.5, 1.25), (1.75, 1.25)):
            for ng in (19, 21):
                jobs.append((ox, oy, ng, 400000, 5, []))
    elif mode == 'deep':
        ox, oy, ng = float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
        jobs = [(ox, oy, ng, 400000, 5, ['SEED0=100']), (ox, oy, ng, 400000, 5, ['SEED0=200']),
                (ox, oy, ng, 400000, 5, ['fixgpio', 'SEED0=300'])]
    elif mode == 'deep2':
        ox, oy, ng = float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
        jobs = [(ox, oy, ng, 400000, 5, ['SEED0=400']), (ox, oy, ng, 400000, 5, ['SEED0=500']),
                (ox, oy, ng, 400000, 5, ['SEED0=600'])]
    elif mode == 'fixg':
        ox, oy, ng = float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
        jobs = [(ox, oy, ng, 400000, 5, ['fixgpio'])]
    with Pool(3) as p:
        res = p.map(job, jobs)
    json.dump(res, open(f'{HERE}/sweep_{mode}.json', 'w'), default=float)
