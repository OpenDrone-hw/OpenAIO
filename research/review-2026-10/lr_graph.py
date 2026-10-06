"""Copper connectivity graph of one net (tracks, vias, pads; zones ignored) for routed-length queries."""
import math, collections
import networkx as nx
from shapely.geometry import Point, LineString
from lr_common import polys, via_layers

EPS = 0.002


def build(d, board, net):
    G = nx.Graph()
    trk = [t for t in d['tracks'] if t['net'] == net]
    vias = [v for v in d['vias'] if v['net'] == net]
    pads = [(f['ref'], p) for f in d['footprints'] for p in f['pads'] if p['net'] == net]
    key = lambda L, x, y: (L, round(x, 3), round(y, 3))
    # split segments at T-junctions (endpoint of one lying inside another on the same layer)
    ends = collections.defaultdict(list)
    for t in trk:
        ends[t['layer']] += [tuple(t['a']), tuple(t['b'])]
    segs = []
    for t in trk:
        a, b = tuple(t['a']), tuple(t['b'])
        if 'mid' in t:
            segs.append((t['layer'], a, b, t['len'], t['w']))
            continue
        ls = LineString([a, b]) if a != b else None
        cuts = []
        if ls is not None:
            for e in ends[t['layer']]:
                if e in (a, b):
                    continue
                if ls.distance(Point(e)) < EPS:
                    cuts.append(ls.project(Point(e)))
        pts = [a] + [ls.interpolate(c).coords[0] for c in sorted(cuts)] + [b] if cuts else [a, b]
        for p, q in zip(pts, pts[1:]):
            segs.append((t['layer'], p, q, math.dist(p, q), t['w']))
    for L, a, b, ln, w in segs:
        G.add_edge(key(L, *a), key(L, *b), w=ln, kind='trk', width=w)
    nodes_by_layer = collections.defaultdict(list)
    for n in list(G.nodes):
        nodes_by_layer[n[0]].append(n)
    for i, v in enumerate(vias):
        vn = ('VIA', i, v['x'], v['y'])
        G.add_node(vn)
        for L in via_layers(board, v):
            for n in nodes_by_layer[L]:
                if math.hypot(n[1] - v['x'], n[2] - v['y']) <= v['d'] / 2 + EPS:
                    G.add_edge(vn, n, w=0.0, kind='via')
    for ref, p in pads:
        pn = ('PAD', ref, p['num'])
        G.add_node(pn, x=p['x'], y=p['y'])
        for L, pl in p['polys'].items():
            geo = polys(pl)
            for n in nodes_by_layer[L]:
                if geo.distance(Point(n[1], n[2])) < 0.01:
                    G.add_edge(pn, n, w=0.0, kind='pad')
        if p['drill'] > 0:  # through-hole: all layers
            for L in p['layers']:
                for n in nodes_by_layer[L]:
                    if math.hypot(n[1] - p['x'], n[2] - p['y']) <= p['drill'] / 2 + 0.15:
                        G.add_edge(pn, n, w=0.0, kind='pad')
        # vias inside the pad (via-in-pad)
        for i, v in enumerate(vias):
            for L, pl in p['polys'].items():
                if polys(pl).distance(Point(v['x'], v['y'])) < v['d'] / 2:
                    G.add_edge(pn, ('VIA', i, v['x'], v['y']), w=0.0, kind='pad')
    return G


def path_info(G, src, dst):
    try:
        L, path = nx.single_source_dijkstra(G, src, dst, weight='w')
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
    nvia = sum(1 for n in path if n[0] == 'VIA')
    layers = collections.Counter()
    minw = 9e9
    for a, b in zip(path, path[1:]):
        e = G.edges[a, b]
        if e['kind'] == 'trk':
            layers[a[0]] += e['w']
            minw = min(minw, e['width'])
    return dict(len=L, vias=nvia, layers=dict(layers), minw=minw if minw < 9e9 else None, path=path)


def tree_len(G):
    return sum(e['w'] for _, _, e in G.edges(data=True) if e['kind'] == 'trk')
