"""3-D DC resistance solver for one net (all copper layers + via barrels), on refilled copper.
Copper of the net on each layer (tracks, arcs, pads, via annuli, zone fills) is rasterised at h mm;
neighbouring cells are joined with sheet conductance t/rho; vias and plated holes are barrels
(pi*drill*t_plate) between consecutive copper layers of the net, tied to every annulus cell on each layer.
Source pads are held at 0 V; each sink pad draws its current uniformly over its cells.

API: solve(board, net, sources, sinks, h) -> result dict  (sinks: list of (label, [(ref, padnum), ...], amps))
"""
import math, collections
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from PIL import Image, ImageDraw
from shapely.geometry import Point
from shapely.ops import unary_union
from lr_common import *

RHO = 1.72e-8      # ohm*m, copper 20 C
T_PLATE = 0.020    # mm, hole wall plating (IPC class 2 average)
_cache = {}


def net_layer_geoms(d, board, net):
    acc = collections.defaultdict(list)
    for t in d['tracks']:
        if t['net'] == net:
            acc[t['layer']].append(track_geom(t))
    for v in d['vias']:
        if v['net'] == net:
            for L in via_layers(board, v):
                acc[L].append(Point(v['x'], v['y']).buffer(v['d'] / 2))
    for z in d['zones']:
        if not z['rule'] and z['net'] == net:
            acc[z['layer']].append(polys(z['filled']))
    holes = []
    for f in d['footprints']:
        for p in f['pads']:
            if p['net'] != net:
                continue
            for L, pl in p['polys'].items():
                acc[L].append(polys(pl))
            if p['drill'] > 0:
                holes.append((p['x'], p['y'], p['drill']))
                for L in d['copper']:
                    if L not in p['polys']:
                        acc[L].append(Point(p['x'], p['y']).buffer(p['drill'] / 2 + 0.15))
    return {L: unary_union(g) for L, g in acc.items()}, holes


def rasterise(geom, x0, y0, nx, ny, h):
    im = Image.new('1', (nx, ny), 0)
    dr = ImageDraw.Draw(im)
    gs = geom.geoms if hasattr(geom, 'geoms') else [geom]
    T = lambda c: ((c[0] - x0) / h - 0.5, (c[1] - y0) / h - 0.5)
    for p in gs:
        if p.geom_type != 'Polygon' or p.is_empty:
            continue
        dr.polygon([T(c) for c in p.exterior.coords], fill=1)
        for hh in p.interiors:
            dr.polygon([T(c) for c in hh.coords], fill=0)
    return np.array(im, dtype=bool)


class NetModel:
    def __init__(self, board, net, h=0.05, clip=None, add=None):
        """clip/add: {layer: polygon} removed from / added to the net copper (what-if studies)"""
        d = load(board) if board not in _cache else _cache[board]
        _cache[board] = d
        self.d, self.board, self.net, self.h = d, board, net, h
        geoms, holes = net_layer_geoms(d, board, net)
        for L, g in (clip or {}).items():
            if L in geoms:
                geoms[L] = geoms[L].difference(g)
        for L, g in (add or {}).items():
            geoms[L] = geoms[L].union(g) if L in geoms else g
        self.layers = [L for L in d['copper'] if L in geoms and not geoms[L].is_empty]
        allg = unary_union(list(geoms.values()))
        x0, y0, x1, y1 = allg.bounds
        self.x0, self.y0 = x0 - h, y0 - h
        self.nx, self.ny = int((x1 - x0) / h) + 3, int((y1 - y0) / h) + 3
        self.mask = {L: rasterise(geoms[L], self.x0, self.y0, self.nx, self.ny, h) for L in self.layers}
        self.geoms = geoms
        idx = {}
        n = 0
        for L in self.layers:
            a = np.full(self.mask[L].shape, -1, dtype=np.int64)
            k = int(self.mask[L].sum())
            a[self.mask[L]] = np.arange(n, n + k)
            idx[L] = a
            n += k
        self.idx = idx
        self.ncell = n
        ncx = np.zeros(n); ncy = np.zeros(n); ncl = np.zeros(n, dtype=np.int64)
        for li, L in enumerate(self.layers):
            jj, ii = np.nonzero(idx[L] >= 0)
            k = idx[L][jj, ii]
            ncx[k] = self.x0 + (ii + 0.5) * h; ncy[k] = self.y0 + (jj + 0.5) * h; ncl[k] = li
        rows, cols, vals, area, kind = [], [], [], [], []
        z = layer_z(board)
        for li, L in enumerate(self.layers):
            g = (cu_thick(board, L) * 1e-3) / RHO
            a = idx[L]
            for sl1, sl2 in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                             ((slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
                p, q = a[sl1], a[sl2]
                m = (p >= 0) & (q >= 0)
                rows.append(p[m]); cols.append(q[m]); vals.append(np.full(m.sum(), g))
                area.append(np.full(m.sum(), h * cu_thick(board, L))); kind.append(np.full(m.sum(), li))
        # barrels
        self.via_edges = []   # (edge index range, via record)
        nextnode = n
        barrels = [(v['x'], v['y'], v['drill'], via_layers(board, v), 'via') for v in d['vias'] if v['net'] == net]
        barrels += [(x, y, dr, d['copper'], 'pth') for x, y, dr in holes]
        self.barrels = barrels
        e_off = sum(len(r) for r in rows)
        brow, bcol, bval, barea, bkind = [], [], [], [], []
        self.barrel_edge_ranges = []
        for bi, (x, y, dr, span, typ) in enumerate(barrels):
            Ls = [L for L in self.layers if L in span]
            ring_r = dr / 2 + 0.12
            lnodes = []
            for L in Ls:
                i0 = int((x - ring_r - self.x0) / h); i1 = int((x + ring_r - self.x0) / h) + 1
                j0 = int((y - ring_r - self.y0) / h); j1 = int((y + ring_r - self.y0) / h) + 1
                cells = []
                for j in range(max(j0, 0), min(j1 + 1, self.ny)):
                    for i in range(max(i0, 0), min(i1 + 1, self.nx)):
                        cx, cy = self.x0 + (i + 0.5) * h, self.y0 + (j + 0.5) * h
                        if math.hypot(cx - x, cy - y) <= ring_r and idx[L][j, i] >= 0:
                            cells.append(idx[L][j, i])
                if not cells:
                    continue
                node = nextnode; nextnode += 1
                self._bxy = getattr(self, '_bxy', []); self._bxy.append((x, y))
                lnodes.append((L, node))
                for c_ in cells:
                    brow.append(node); bcol.append(c_); bval.append(1e5); barea.append(0.0); bkind.append(-2)
            start = len(brow)
            A = math.pi * dr * T_PLATE  # mm^2
            for (La, na), (Lb, nb) in zip(lnodes, lnodes[1:]):
                dz = abs(z[Lb] - z[La])
                g = (A * 1e-6) / (RHO * dz * 1e-3)
                brow.append(na); bcol.append(nb); bval.append(g); barea.append(A); bkind.append(-1)
            self.barrel_edge_ranges.append((start, len(brow)))
        self.N = nextnode
        bxy = np.array(getattr(self, '_bxy', [])).reshape(-1, 2)
        bx = bxy[:, 0] if len(bxy) else np.zeros(0); by = bxy[:, 1] if len(bxy) else np.zeros(0)
        self.cx = np.concatenate([ncx, bx]); self.cy = np.concatenate([ncy, by]); self.cl = np.concatenate([ncl, np.full(nextnode - n, -1)])
        r_ = np.concatenate(rows + [np.array(brow, dtype=np.int64)])
        c_ = np.concatenate(cols + [np.array(bcol, dtype=np.int64)])
        v_ = np.concatenate(vals + [np.array(bval)])
        self.e_r, self.e_c, self.e_g = r_, c_, v_
        self.e_area = np.concatenate(area + [np.array(barea)])
        self.e_kind = np.concatenate(kind + [np.array(bkind)])
        self.barrel_off = e_off
        Gm = sp.coo_matrix((v_, (r_, c_)), shape=(self.N, self.N)).tocsr()
        Gm = Gm + Gm.T
        dg = np.asarray(Gm.sum(axis=1)).ravel()
        self.L = (sp.diags(dg) - Gm).tocsc()

    def pad_nodes(self, ref, num):
        out = []
        for f in self.d['footprints']:
            if f['ref'] != ref:
                continue
            for p in f['pads']:
                if p['num'] != num or p['net'] != self.net:
                    continue
                for L, pl in p['polys'].items():
                    if L not in self.idx:
                        continue
                    g = polys(pl)
                    x0, y0, x1, y1 = g.bounds
                    for j in range(int((y0 - self.y0) / self.h), int((y1 - self.y0) / self.h) + 1):
                        for i in range(int((x0 - self.x0) / self.h), int((x1 - self.x0) / self.h) + 1):
                            if 0 <= i < self.nx and 0 <= j < self.ny and self.idx[L][j, i] >= 0:
                                if g.contains(Point(self.x0 + (i + 0.5) * self.h, self.y0 + (j + 0.5) * self.h)):
                                    out.append(self.idx[L][j, i])
        return out

    def factor(self, src_nodes):
        from scipy.sparse.csgraph import connected_components
        self.src = np.array(sorted(set(src_nodes)))
        ncomp, lab = connected_components(self.L, directed=False)
        live = np.isin(lab, np.unique(lab[self.src]))
        self.live = live
        self.floating = int((~live).sum())
        keep = live.copy(); keep[self.src] = False
        self.keep = keep
        self.kidx = np.full(self.N, -1); self.kidx[keep] = np.arange(keep.sum())
        A = self.L[keep][:, keep]
        self.solver = spla.factorized(A.tocsc())

    def solve(self, sinks):
        """sinks: list of (nodes, amps). Returns potential (V) per node (source = 0)."""
        b = np.zeros(self.N)
        for nodes, I in sinks:
            nodes = np.array(nodes)
            b[nodes] -= I / len(nodes)
        if np.any(b[~self.live] != 0):
            raise ValueError('sink not connected to source')
        x = self.solver(b[self.keep])
        V = np.zeros(self.N); V[self.keep] = x; V[~self.live] = np.nan
        return V

    def edge_currents(self, V):
        return self.e_g * (V[self.e_r] - V[self.e_c])

    def cut_stats(self, V, vmin, vmax, nlev=400, frac=(0.1, 0.9)):
        """Isopotential cuts between vmin..vmax (source..sink): min copper cross-section over the mid range."""
        I = self.edge_currents(V)
        hi = np.maximum(V[self.e_r], V[self.e_c]); lo = np.minimum(V[self.e_r], V[self.e_c])
        sel = (self.e_kind != -2) & (hi > lo)
        levels = vmin + (vmax - vmin) * np.linspace(frac[0], frac[1], nlev)
        a_lo = np.searchsorted(levels, lo[sel], side='right'); a_hi = np.searchsorted(levels, hi[sel], side='left')
        acc = np.zeros(nlev + 1)
        np.add.at(acc, a_lo, self.e_area[sel]); np.add.at(acc, a_hi, -self.e_area[sel])
        area = np.cumsum(acc)[:nlev]
        k = int(np.argmin(area))
        lev = levels[k]
        cross = sel & (lo < lev) & (hi > lev)
        cross_idx = np.nonzero(sel)[0]
        m = (lo[sel] < lev) & (hi[sel] > lev)
        ei = cross_idx[m]
        per_layer = collections.Counter()
        cur_layer = collections.Counter()
        nvia = 0; via_I = []
        for e in ei:
            kd = self.e_kind[e]
            if kd >= 0:
                per_layer[self.layers[kd]] += self.e_area[e]
                cur_layer[self.layers[kd]] += abs(I[e])
            elif kd == -1:
                nvia += 1; via_I.append(abs(I[e]))
                per_layer['vias'] += self.e_area[e]
                cur_layer['vias'] += abs(I[e])
        w = np.abs(I[ei]); r_ = self.e_r[ei]
        loc = (float(np.sum(self.cx[r_] * w) / max(w.sum(), 1e-30)), float(np.sum(self.cy[r_] * w) / max(w.sum(), 1e-30)))
        xs, ys = self.cx[r_], self.cy[r_]
        ext = (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())) if len(xs) else None
        return dict(min_area=float(area[k]), level=float(lev), loc=loc, extent=ext, per_layer_area=dict(per_layer),
                    per_layer_current=dict(cur_layer), vias_in_cut=nvia, area_profile=area)

    def node_xy(self, nodes):
        """map grid nodes back to (layer, x, y)"""
        out = []
        for n_ in nodes:
            for L in self.layers:
                a = self.idx[L]
                w = np.argwhere(a == n_)
                if len(w):
                    j, i = w[0]
                    out.append((L, self.x0 + (i + 0.5) * self.h, self.y0 + (j + 0.5) * self.h))
                    break
        return out

    def barrel_currents(self, V):
        I = self.edge_currents(V)
        res = []
        for bi, (s, e) in enumerate(self.barrel_edge_ranges):
            k = np.arange(s, e) + self.barrel_off
            mx = float(np.max(np.abs(I[k]))) if e > s else 0.0
            x, y, dr, span, typ = self.barrels[bi]
            res.append((mx, x, y, dr, typ))
        return res

    def layer_current_density(self, V):
        """max in-plane current density per layer (A/mm^2) and its location"""
        I = self.edge_currents(V)
        out = {}
        # per node: sum |I| of in-plane edges /2 ~ local current; use edge-wise density
        for li, L in enumerate(self.layers):
            m = self.e_kind == li
            if not m.any():
                continue
            J = np.abs(I[m]) / self.e_area[m]
            k = int(np.argmax(J))
            e = np.nonzero(m)[0][k]
            n_ = self.e_r[e]
            w = np.argwhere(self.idx[L] == n_)[0]
            out[L] = (float(J[k]), self.x0 + (w[1] + 0.5) * self.h, self.y0 + (w[0] + 0.5) * self.h)
        return out
