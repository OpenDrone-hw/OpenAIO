"""Corrected power-path copper model for OpenAIO (read only; the board is never written).

Run with KiCad's Python:
  $KPY power_paths_v2.py OpenAIO.kicad_pcb [--esc 15] [--buck 0.5] [--temp 45] [--grid 0.05] [--hot 8] [--islands]

Differences to tools/loop_resistance.py + tools/power_paths.py (evidence in the audit report):
  1. Unreachable sinks are DETECTED (connected components, sinks outside the source component are listed with their
     island and the net is flagged OPEN). v1 solved them with a 1e-9 S leak and summed loss over edges only, so the 14
     floating +BATT sinks (drops of millions of volts) contributed 0 W and +BATT read 0.003 mOhm.
  2. Commutation statistics. 6-step: per ESC exactly one high and one low FET carry the full ESC current, each for 1/3
     of the time, so the loss is E[I^2] R: P = I_mean^T R I_mean + sum_groups tr(R Cov). v1 put a DC 5 A on every FET
     (no variance term: GND +40 %, phases x2.7 low) and split I sqrt(2/3) over HS and LS at once on the phase nets.
     Phase net: P = I^2 (R_hs + R_ls) / 3.
  3. Coverage-weighted mesh (4x4 supersampling, edge conductance = harmonic mean of the two cell fractions) at 0.05 mm:
     binary 0.1 mm cells overstate pour area by 3-8 %, small lands by 50 %, and merge neighbouring via lands across a
     0.12 mm gap into a false inner-layer sheet.
  4. Vias attach only to copper in their own 3x3 cells (v1 snapped to any copper within 0.4 mm at zero resistance).
  5. Sinks inject uniformly over the pad copper (pad spreading counts, +5..9 % on GND R_kk); battery pads stay shorts.
  6. Only the source component is solved (no regularisation leak).
  7. Extras: resistance matrix R_ij between sinks, heat maps (jmap), XY-pooled hot spots, via clusters, islands.
Zone holes are NOT a bug of v1: KiCad 10 returns fractured fills (HoleCount 0), v1's outline raster is correct there.
"""
import math
import os
import re
import sys
import time

_sd, _n = os.dup(2), os.open(os.devnull, os.O_WRONLY)
os.dup2(_n, 2)
import pcbnew  # noqa: E402
os.dup2(_sd, 2)
import numpy as np  # noqa: E402
import scipy.sparse as sp  # noqa: E402
import scipy.sparse.linalg as spla  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

MM = pcbnew.FromMM
RHO20, ALPHA = 1.72e-8, 0.00393
PLATING = {"through": 20e-6, "buried": 20e-6, "pad": 25e-6}
SS = 4
THR = 0.03


def arg(a, name, default):
    return float(a[a.index(name) + 1]) if name in a else default


class Model:
    def __init__(self, path, grid=0.1, temp=45.0, holes=True, fill=True, board=None, inner_um=None, plating_um=None):
        self.path, self.holes = path, holes
        self.b = board or pcbnew.LoadBoard(path)
        if fill:
            pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
        self.h = MM(grid)
        self.hmm = grid
        self.rho = RHO20 * (1 + ALPHA * (temp - 20))
        bb = self.b.GetBoardEdgesBoundingBox()
        self.x0, self.y0 = bb.GetLeft() - self.h, bb.GetTop() - self.h
        self.nx, self.ny = bb.GetWidth() // self.h + 3, bb.GetHeight() // self.h + 3
        self.layers = list(self.b.GetEnabledLayers().CuStack())
        self.lname = [self.b.GetLayerName(l) for l in self.layers]
        text = open(path).read()
        stack = text[text.index("(stackup"):text.index("(copper_finish")]
        cu_t, di_t = [], []
        for kind, th in re.findall(r'\(type "([^"]+)"\)\s*\(thickness ([\d.]+)\)', stack):
            if kind == "copper":
                cu_t.append(float(th) * 1e-3)
            elif kind in ("prepreg", "core"):
                di_t.append(float(th) * 1e-3)
        self.cu = [cu_t[i] for i in range(len(self.layers))]
        if inner_um:  # sensitivity: inner copper thickness override (e.g. 17.5 for 0.5 oz)
            self.cu = [t if i in (0, len(self.layers) - 1) else inner_um * 1e-6 for i, t in enumerate(self.cu)]
        if plating_um:
            PLATING['through'] = PLATING['buried'] = plating_um * 1e-6
        self.gap = di_t[:len(self.layers) - 1]
        self.gs = [t / self.rho for t in self.cu]  # sheet conductance per layer (S per square)
        self.cache = {}
        self.fp = {f.GetReference(): f for f in self.b.GetFootprints()}

    # ---------------------------------------------------------------- raster
    def _px(self, x, y):
        f = self.h / SS
        return (x - self.x0) / f + SS / 2.0, (y - self.y0) / f + SS / 2.0

    def _draw(self, img, ps, parity=False):
        """Draw a SHAPE_POLY_SET into a bool array. parity=True: even-odd over all contours (zone fills with holes)."""
        W, H = img.shape[1], img.shape[0]
        for i in range(ps.OutlineCount()):
            contours = [ps.Outline(i)]
            if self.holes:
                contours += [ps.Hole(i, j) for j in range(ps.HoleCount(i))]
            for k, o in enumerate(contours):
                pts = [self._px(o.CPoint(m).x, o.CPoint(m).y) for m in range(o.PointCount())]
                if len(pts) < 3:
                    continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bx0, by0 = max(int(min(xs)) - 1, 0), max(int(min(ys)) - 1, 0)
                bx1, by1 = min(int(max(xs)) + 2, W), min(int(max(ys)) + 2, H)
                if bx1 <= bx0 or by1 <= by0:
                    continue
                t = Image.new("1", (bx1 - bx0, by1 - by0), 0)
                ImageDraw.Draw(t).polygon([(x - bx0, y - by0) for x, y in pts], fill=1)
                a = np.array(t, dtype=bool)
                if parity:
                    img[by0:by1, bx0:bx1] ^= a
                else:
                    img[by0:by1, bx0:bx1] |= a

    def _cover(self, fine):
        n = SS
        fy, fx = fine.shape
        c = fine[:self.ny * n, :self.nx * n].reshape(self.ny, n, self.nx, n).mean(axis=(1, 3))
        return c.T.astype(np.float32)  # [x, y]

    def cover(self, net, li):
        key = (net, li)
        if key in self.cache:
            return self.cache[key]
        layer = self.layers[li]
        fine = np.zeros((self.ny * SS, self.nx * SS), bool)
        for z in self.b.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != net or not z.IsOnLayer(layer):
                continue
            tmp = np.zeros_like(fine)
            self._draw(tmp, z.GetFilledPolysList(layer), parity=True)
            fine |= tmp
        shapes = pcbnew.SHAPE_POLY_SET()
        for t in self.b.GetTracks():
            if t.GetNetname() == net and t.IsOnLayer(layer):
                t.TransformShapeToPolygon(shapes, layer, 0, MM(0.005), pcbnew.ERROR_INSIDE)
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net and p.IsOnLayer(layer):
                    p.TransformShapeToPolygon(shapes, layer, 0, MM(0.005), pcbnew.ERROR_INSIDE)
        tmp = np.zeros_like(fine)
        saved, self.holes = self.holes, False
        self._draw(tmp, shapes)
        self.holes = saved
        fine |= tmp
        self.cache[key] = self._cover(fine)
        return self.cache[key]

    def pad_cover(self, pad, li):
        layer = self.layers[li]
        fine = np.zeros((self.ny * SS, self.nx * SS), bool)
        shapes = pcbnew.SHAPE_POLY_SET()
        pad.TransformShapeToPolygon(shapes, layer, 0, MM(0.005), pcbnew.ERROR_INSIDE)
        saved, self.holes = self.holes, False
        self._draw(fine, shapes)
        self.holes = saved
        return self._cover(fine)

    def cell(self, p):
        return (int(round((p.x - self.x0) / self.h)), int(round((p.y - self.y0) / self.h)))

    def xy(self, x, y):
        """cell -> board mm"""
        return ((self.x0 + x * self.h) / 1e6, (self.y0 + y * self.h) / 1e6)

    # ---------------------------------------------------------------- graph
    def build(self, net):
        cov = [self.cover(net, li) for li in range(len(self.layers))]
        idx, n = [], 0
        for li, c in enumerate(cov):
            m = c > THR
            ix = -np.ones(c.shape, np.int64)
            ix[m] = np.arange(n, n + int(m.sum()))
            n += int(m.sum())
            idx.append(ix)
        A, Bn, Gc, kind = [], [], [], []  # kind: layer index, or -1 - via index
        for li, c in enumerate(cov):
            ix = idx[li]
            for ax in (0, 1):
                a = c[:-1, :] if ax == 0 else c[:, :-1]
                b = c[1:, :] if ax == 0 else c[:, 1:]
                ia = ix[:-1, :] if ax == 0 else ix[:, :-1]
                ib = ix[1:, :] if ax == 0 else ix[:, 1:]
                m = (a > THR) & (b > THR)
                cc = np.where(m, 2 * a * b / np.maximum(a + b, 1e-9), 0)[m]
                A.append(ia[m]); Bn.append(ib[m]); Gc.append(cc * self.gs[li]); kind.append(np.full(m.sum(), li))
        vias = []
        for v in self.b.GetTracks():
            if v.GetClass() != "PCB_VIA" or v.GetNetname() != net:
                continue
            micro = v.GetViaType() == pcbnew.VIATYPE_MICROVIA
            r = v.GetDrillValue() * 1e-9 / 2
            area = math.pi * r * r if micro else math.pi * ((r + PLATING["through"]) ** 2 - r * r)
            top, bot = self.layers.index(v.TopLayer()), self.layers.index(v.BottomLayer())
            cx, cy = self.cell(v.GetPosition())
            prev = None
            for li in range(top, bot + 1):
                nd = idx[li][cx, cy] if 0 <= cx < self.nx and 0 <= cy < self.ny else -1
                if nd < 0:
                    # land rasterised at another cell centre: look at the 3x3 neighbourhood of this via only
                    sub = idx[li][max(cx - 1, 0):cx + 2, max(cy - 1, 0):cy + 2].ravel()
                    sub = sub[sub >= 0]
                    nd = sub[0] if len(sub) else -1
                if nd < 0:
                    continue
                if prev is not None:
                    length = sum(self.gap[k] for k in range(prev[0], li)) + self.cu[li]
                    vias.append((prev[1], nd, area / (self.rho * length), v, prev[0], li))
                prev = (li, nd)
        if vias:
            A.append(np.array([x[0] for x in vias])); Bn.append(np.array([x[1] for x in vias]))
            Gc.append(np.array([x[2] for x in vias])); kind.append(-1 - np.arange(len(vias)))
        G = dict(n=n, cov=cov, idx=idx, a=np.concatenate(A), b=np.concatenate(Bn), g=np.concatenate(Gc),
                 kind=np.concatenate(kind), vias=vias)
        adj = sp.coo_matrix((np.ones(len(G["a"])), (G["a"], G["b"])), shape=(n, n))
        G["ncomp"], G["comp"] = connected_components(adj, directed=False)
        return G

    def pad_cells(self, G, pads, layers=None, short=False):
        """cells (node, weight) under the pads; weights sum to 1."""
        cells = {}
        for p in pads:
            for li in range(len(self.layers)):
                if not p.IsOnLayer(self.layers[li]):
                    continue
                if layers is not None and li not in layers:
                    continue
                pc = self.pad_cover(p, li)
                ix = G["idx"][li]
                m = (pc > 0.5) & (ix >= 0)
                for x, y in zip(*np.nonzero(m)):
                    cells[int(ix[x, y])] = float(pc[x, y])
        tot = sum(cells.values())
        return {k: v / tot for k, v in cells.items()} if tot else {}

    # ---------------------------------------------------------------- solve
    def solve(self, net, src_pads, sinks, groups, src_layers=None, sink_layers=None, want_map=False, short=False):
        """sinks: list of (name, pads); groups: see below.
        Returns dict with R matrix, losses, unreachable sinks, islands, optional per-edge stats."""
        G = self.build(net)
        src = self.pad_cells(G, src_pads, src_layers)
        out = dict(G=G, net=net, unreachable=[], R={}, names=[s[0] for s in sinks])
        if not src:
            out["error"] = "source pads have no copper in the net graph"
            return out
        comp = G["comp"]
        src_comps = {int(comp[k]) for k in src}
        if len(src_comps) > 1:
            out["warn_src_split"] = sorted(src_comps)
        keep_c = src_comps
        cells = []
        for name, pads in sinks:
            cl = self.pad_cells(G, pads, sink_layers)
            cells.append(cl)
        reach = []
        for i, cl in enumerate(cells):
            ok = bool(cl) and all(int(comp[k]) in keep_c for k in cl)
            reach.append(ok)
            if not ok:
                out["unreachable"].append(sinks[i][0])
        nodes = np.nonzero(np.isin(comp, list(keep_c)))[0]
        pos = -np.ones(G["n"], np.int64)
        free = np.array([k for k in nodes if k not in src], dtype=np.int64)
        pos[free] = np.arange(len(free))
        a, b, g = G["a"], G["b"], G["g"]
        m = (pos[a] >= 0) & (pos[b] >= 0)
        aa, bb, gg = pos[a[m]], pos[b[m]], g[m]
        # edges to source cells: diagonal only
        ma = (pos[a] >= 0) & np.isin(b, list(src))
        mb = (pos[b] >= 0) & np.isin(a, list(src))
        da = np.concatenate([pos[a[ma]], pos[b[mb]]])
        dg = np.concatenate([g[ma], g[mb]])
        nf0 = len(free)
        ex_r, ex_c, ex_v = [], [], []
        nf = nf0
        vn = {}
        if short:  # one virtual node per sink pad group, tied to its cells (v1 behaviour, for comparison)
            for i, cl in enumerate(cells):
                if reach[i]:
                    vn[i] = nf; nf += 1
                    for k, w in cl.items():
                        if pos[k] >= 0:
                            gj = 1e5
                            ex_r += [vn[i], pos[k], vn[i], pos[k]]; ex_c += [vn[i], pos[k], pos[k], vn[i]]; ex_v += [gj, gj, -gj, -gj]
        Gm = sp.coo_matrix((np.concatenate([gg, gg, -gg, -gg, dg, ex_v]),
                            (np.concatenate([aa, bb, aa, bb, da, ex_r]).astype(np.int64),
                             np.concatenate([aa, bb, bb, aa, da, ex_c]).astype(np.int64))),
                           shape=(nf, nf)).tocsc()
        lu = spla.splu(Gm)
        rhs = []
        for i, cl in enumerate(cells):
            r = np.zeros(nf)
            if reach[i]:
                if short:
                    r[vn[i]] = 1.0
                else:
                    for k, w in cl.items():
                        if pos[k] >= 0:
                            r[pos[k]] += w
            rhs.append(r)
        K = len(sinks)
        V = [lu.solve(r) if reach[i] else None for i, r in enumerate(rhs)]
        R = np.full((K, K), np.nan)
        for i in range(K):
            for j in range(K):
                if V[j] is not None and reach[i]:
                    R[i, j] = float(rhs[i] @ V[j])
        out["R"] = R
        out["reach"] = reach
        Rz = np.nan_to_num(R)
        # groups: (members, [(prob, amps per member)]). E[I I^T] = sum over groups of the state second moments,
        # groups are independent of each other, members of one group are mutually exclusive (6-step commutation).
        mu = np.zeros(K)
        for members, states in groups:
            for p_, amps in states:
                for m_, a_ in zip(members, amps):
                    mu[m_] += p_ * a_
        mu = np.where(reach, mu, 0.0)
        P_mean = float(mu @ Rz @ mu)
        P_var = 0.0
        for members, states in groups:
            mg = np.zeros(K)
            C = np.zeros((K, K))
            for p_, amps in states:
                v = np.zeros(K)
                for m_, a_ in zip(members, amps):
                    v[m_] = a_ if reach[m_] else 0.0
                C += p_ * np.outer(v, v)
                mg += p_ * v
            P_var += float(np.sum((C - np.outer(mg, mg)) * Rz))
        out["P_mean"], out["P_var"] = P_mean, P_var
        out["I_total"] = float(mu.sum())
        if want_map:
            msk = (m | ma | mb)
            def edge(vec):
                f = np.zeros(G["n"]); f[free] = vec[:nf0]
                return (f[a] - f[b]) * g * msk
            Em = np.zeros(len(g))
            for k in range(K):
                if reach[k] and mu[k] != 0:
                    Em += mu[k] * edge(V[k])
            i2 = Em ** 2
            for members, states in groups:
                mem = [k for k in members if reach[k]]
                if not mem:
                    continue
                D = {k: edge(V[k]) for k in mem}
                mg = sum(p_ * a_ * D[k] for p_, amps in states for k, a_ in zip(members, amps) if k in D)
                sec = sum(p_ * sum(a_ * D[k] for k, a_ in zip(members, amps) if k in D) ** 2 for p_, amps in states)
                i2 += sec - mg ** 2
            out.update(i2=i2, imean=Em, free=free)
        return out

    def jmap(self, out, li, path, box=None, scale=14, jmax=None):
        """Heat map PNG of RMS current density (A/mm of real width) on layer li."""
        from PIL import Image
        G = out["G"]
        irms = np.sqrt(out["i2"])
        kind = G["kind"]
        cw = np.zeros(len(G["g"]))
        for k in range(len(self.layers)):
            cw[kind == k] = G["g"][kind == k] / self.gs[k]
        jj = irms / np.maximum(cw * self.hmm, 1e-6)
        sel = kind == li
        J = np.zeros((self.nx, self.ny), np.float32)
        ix = G["idx"][li]
        nodes_x, nodes_y = np.nonzero(ix >= 0)
        pos = -np.ones(G["n"], np.int64); pos[ix[nodes_x, nodes_y]] = np.arange(len(nodes_x))
        for e in np.nonzero(sel)[0]:
            for nd in (G["a"][e], G["b"][e]):
                p = pos[nd]
                J[nodes_x[p], nodes_y[p]] = max(J[nodes_x[p], nodes_y[p]], jj[e])
        jmax = jmax or max(float(J.max()), 1e-6)
        cov = G["cov"][li]
        img = np.zeros((self.ny, self.nx, 3), np.uint8)
        t = np.clip(J.T / jmax, 0, 1)
        has = (cov.T > THR)
        img[..., 0] = np.where(has, 40 + 215 * t, 20)
        img[..., 1] = np.where(has, 40 + 120 * (1 - np.abs(2 * t - 1)), 20)
        img[..., 2] = np.where(has, 90 * (1 - t), 20)
        im = Image.fromarray(img)
        if box:
            x0, y0, x1, y1 = box
            c0 = self.cell(pcbnew.VECTOR2I(MM(x0), MM(y0))); c1 = self.cell(pcbnew.VECTOR2I(MM(x1), MM(y1)))
            im = im.crop((c0[0], c0[1], c1[0], c1[1]))
        im = im.resize((im.width * scale // 10 * 1, im.height * scale // 10 * 1), Image.NEAREST) if scale != 10 else im
        im.save(path)
        return jmax

    def losses(self, out):
        """loss per edge (W) = I_rms^2 / g, summed by kind."""
        G = out["G"]
        p = out["i2"] / G["g"]
        res = {}
        for li, nm in enumerate(self.lname):
            res[nm] = float(p[G["kind"] == li].sum())
        res["vias"] = float(p[G["kind"] < 0].sum())
        return res, p

    def hotspots(self, out, top=8, radius_mm=1.2):
        """XY-pooled dissipation clusters (all layers summed), plus via fields.
        Returns (rows, via_rows). row: x, y, P_mW (cluster), share of net loss, J (A/mm, max over layers),
        layer split (mW per layer), 'layer' = dominating layer."""
        G = out["G"]
        p = out["i2"] / G["g"]
        irms = np.sqrt(out["i2"])
        kind = G["kind"]
        tot = float(p.sum())
        lay = kind >= 0
        cw = np.zeros(len(G["g"]))
        for li in range(len(self.layers)):
            cw[kind == li] = G["g"][kind == li] / self.gs[li]
        jj = np.zeros(len(G["g"]))
        jj[lay] = irms[lay] / np.maximum(cw[lay] * self.hmm, 1e-6)
        n = G["n"]
        xy = np.zeros((n, 2), np.int64); nl = np.zeros(n, np.int64)
        for li, ix in enumerate(G["idx"]):
            xs, ys = np.nonzero(ix >= 0)
            xy[ix[xs, ys]] = np.stack([xs, ys], 1); nl[ix[xs, ys]] = li
        PL = np.zeros((len(self.layers), self.nx, self.ny)); JL = np.zeros_like(PL)
        for sel_, a_, b_ in ((lay, G["a"], G["b"]),):
            e = np.nonzero(sel_)[0]
            for end in (G["a"][e], G["b"][e]):
                np.add.at(PL, (nl[end], xy[end, 0], xy[end, 1]), 0.5 * p[e])
                np.maximum.at(JL, (nl[end], xy[end, 0], xy[end, 1]), jj[e])
        P2 = PL.sum(0)
        from scipy.ndimage import uniform_filter
        r = int(radius_mm / self.hmm)
        Pc = uniform_filter(P2, size=2 * r + 1, mode="constant") * (2 * r + 1) ** 2
        rows = []
        used = Pc.copy()
        for _ in range(top):
            x, y = np.unravel_index(np.argmax(used), used.shape)
            if used[x, y] <= 0:
                break
            sl = (slice(max(x - r, 0), x + r + 1), slice(max(y - r, 0), y + r + 1))
            per = PL[(slice(None),) + sl].sum((1, 2))
            jl = JL[(slice(None),) + sl].max((1, 2))
            li = int(np.argmax(jl))
            mx, my = self.xy(x, y)
            rows.append(dict(x=mx, y=my, P_mW=float(Pc[x, y] * 1e3), share=float(Pc[x, y]) / max(tot, 1e-12), J=float(jl.max()),
                             layer=self.lname[li], by_layer={self.lname[k]: round(float(per[k] * 1e3), 1) for k in range(len(per)) if per[k] > 1e-5}))
            used[max(x - 2 * r, 0):x + 2 * r + 1, max(y - 2 * r, 0):y + 2 * r + 1] = 0
        vb = {}
        for vi, (na, nb, gv, v, l0, l1) in enumerate(G["vias"]):
            e = np.nonzero(kind == -1 - vi)[0][0]
            key = (round(v.GetPosition().x / 1e6 / 2.0), round(v.GetPosition().y / 1e6 / 2.0))
            d = vb.setdefault(key, dict(ids=set(), P=0.0, x=0.0, y=0.0, c=0, I=0.0, kinds=set()))
            d["ids"].add(id(v)); d["P"] += p[e]; d["x"] += v.GetPosition().x / 1e6; d["y"] += v.GetPosition().y / 1e6; d["c"] += 1
            d["I"] = max(d["I"], irms[e]); d["kinds"].add((self.lname[l0][:2], self.lname[l1][:2]))
        vrows = [dict(x=d["x"] / d["c"], y=d["y"] / d["c"], vias=len(d["ids"]), P_mW=d["P"] * 1e3, I_max=d["I"],
                      share=d["P"] / max(tot, 1e-12)) for d in vb.values()]
        vrows.sort(key=lambda r_: -r_["P_mW"])
        return rows, vrows[:top]

    def islands(self, G, net):
        """component -> pads, vias, copper area per layer."""
        comp = G["comp"]
        res = {}
        for c in range(G["ncomp"]):
            res[c] = dict(pads=[], vias=0, area={})
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() != net:
                    continue
                hit = False
                for li in range(len(self.layers)):
                    if not p.IsOnLayer(self.layers[li]):
                        continue
                    pc = self.pad_cover(p, li)
                    m = (pc > 0.5) & (G["idx"][li] >= 0)
                    if m.any():
                        c = int(comp[G["idx"][li][m][0]])
                        res[c]["pads"].append(f"{fp.GetReference()}.{p.GetNumber()}")
                        hit = True
                        break
                if not hit:
                    res.setdefault("floating", dict(pads=[], vias=0, area={}))["pads"].append(f"{fp.GetReference()}.{p.GetNumber()}")
        for vi, (na, nb, gv, v, l0, l1) in enumerate(G["vias"]):
            res[int(comp[na])]["vias"] += 1
        for li, ix in enumerate(G["idx"]):
            xs, ys = np.nonzero(ix >= 0)
            cs = comp[ix[xs, ys]]
            for c, cnt in zip(*np.unique(cs, return_counts=True)):
                res[int(c)]["area"][self.lname[li]] = res[int(c)]["area"].get(self.lname[li], 0) + cnt * self.hmm ** 2
        return {k: v for k, v in res.items() if v["pads"] or v["vias"]}


# ------------------------------------------------------------------- paths
def fet_groups(M):
    fets = [f for f in M.b.GetFootprints() if f.GetReference().startswith("Q") and f.GetValue().startswith("DOY")]
    high = sorted([f for f in fets if any(p.GetNetname() == "+BATT" for p in f.Pads())], key=lambda f: f.GetReference())
    low = sorted([f for f in fets if any(p.GetNetname() == "GND" for p in f.Pads())], key=lambda f: f.GetReference())
    return high, low


def phase_net(q):
    return next(p.GetNetname() for p in q.Pads() if re.match(r"^/\d[A-C]$", p.GetNetname()))


def run(M, i_esc=15.0, i_buck=0.5, want_map=False, nets=('CSA+', '+BATT', 'GND', 'phases'), **kw):
    fp = M.fp
    high, low = fet_groups(M)
    bucks = [u for u in ("U3", "U4") if u in fp]

    def pads(ref, net, num=None):
        return [p for p in fp[ref].Pads() if p.GetNetname() == net and (num is None or p.GetNumber() == num)]

    i_total = 4 * i_esc + len(bucks) * i_buck
    res = {}
    if "CSA+" in nets:
        res["CSA+"] = M.solve("/CSA+", pads("U24", "/CSA+"), [("Rsense2.1", pads("Rsense2", "/CSA+"))],
                              [([0], [(1.0, [i_total])])], want_map=want_map, **kw)

    def esc_groups(n_fets):
        gs = []
        for e in range(4):
            mem = [3 * e, 3 * e + 1, 3 * e + 2]
            gs.append((mem, [(1 / 3, [i_esc if k == j else 0.0 for k in range(3)]) for j in range(3)]))
        for j in range(len(bucks)):
            gs.append(([n_fets + j], [(1.0, [i_buck])]))
        return gs

    # high FETs ordered by ESC (phase net digit)
    high = sorted(high, key=lambda q: phase_net(q))
    low = sorted(low, key=lambda q: [p.GetNetname() for p in q.Pads() if re.match(r"^/\d[A-C]$", p.GetNetname())][0])
    sinks = [(q.GetReference() + ".3", pads(q.GetReference(), "+BATT")) for q in high] + [(u + ".VIN", pads(u, "+BATT")) for u in bucks]
    if "+BATT" in nets:
        res["+BATT"] = M.solve("+BATT", pads("Rsense2", "+BATT"), sinks, esc_groups(len(high)), want_map=want_map, **kw)
    sinks = [(q.GetReference() + ".S", pads(q.GetReference(), "GND")) for q in low] + [(u + ".GND", pads(u, "GND")) for u in bucks]
    if "GND" in nets:
        res["GND"] = M.solve("GND", pads("U24", "GND", "2"), sinks, esc_groups(len(low)), want_map=want_map, **kw)
    ph = {}
    for q in (high if "phases" in nets else []):
        net = phase_net(q)
        lo = [f for f in low if any(p.GetNetname() == net for p in f.Pads())][0]
        mot = pads("U24", net)
        sk = [("HS " + q.GetReference(), pads(q.GetReference(), net)), ("LS " + lo.GetReference(), pads(lo.GetReference(), net))]
        grp = [([0, 1], [(1 / 3, [i_esc, 0.0]), (1 / 3, [0.0, -i_esc]), (1 / 3, [0.0, 0.0])])]
        ph[net] = M.solve(net, mot, sk, grp, want_map=want_map, **kw)
    res["phases"] = ph
    return res, i_total


def summarize(res, i_esc, i_total):
    res = dict(res)
    """rows: name, I (A), P_dc (W, mean-current model like v1), P_rms (W, E[I^2] R), n unreachable"""
    rows = []
    o = res["CSA+"]
    rows.append(("/CSA+ U24.1 to Rsense2.1", i_total, o["P_mean"], o["P_mean"] + o["P_var"], 0))
    for key in ("+BATT", "GND"):
        o = res[key]
        rows.append((key, o["I_total"], o["P_mean"], o["P_mean"] + o["P_var"], len(o["unreachable"])))
    pm = sum(o["P_mean"] for o in res["phases"].values())
    pr = sum(o["P_mean"] + o["P_var"] for o in res["phases"].values())
    rows.append(("12 phases", i_esc, pm, pr, sum(len(o["unreachable"]) for o in res["phases"].values())))
    return rows


def fmt(M, res, i_esc, i_total):
    lines = [f"{'path':34} {'I(A)':>6} {'P_dc(W)':>8} {'P_rms(W)':>9} {'R_eff(mOhm)':>12} unreachable"]
    for name, I, pd, pr, un in summarize(res, i_esc, i_total):
        ieff = i_total if name != "12 phases" else i_esc * 12 ** 0.5 / 3 ** 0.5
        reff = f"{pr / ieff ** 2 * 1e3:12.3f}" if not (un and name != "12 phases") else "   OPEN(part)"
        lines.append(f"{name:34} {I:6.1f} {pd:8.3f} {pr:9.3f} {reff} {un}")
    rr = []
    for net, o in res["phases"].items():
        R = o["R"]
        rr.append((net, R[0, 0], R[1, 1], (o["P_mean"] + o["P_var"])))
    return "\n".join(lines), rr


def main():
    a = sys.argv[1:]
    t0 = time.time()
    M = Model(a[0], arg(a, "--grid", 0.05), arg(a, "--temp", 45), holes="--no-holes" not in a)
    i_esc = arg(a, "--esc", 15.0)
    res, it = run(M, i_esc, arg(a, "--buck", 0.5))
    txt, rr = fmt(M, res, i_esc, it)
    print(txt)
    for key in ("+BATT", "GND"):
        o = res[key]
        print(f"\n{key}: unreachable sinks {o['unreachable']}")
        print("  R_kk per reachable sink (mOhm):", {n: round(float(o['R'][i, i]) * 1e3, 3) for i, n in enumerate(o['names']) if o['reach'][i]})
    print("\nphase R_hs R_ls (mOhm), P_rms(W):")
    for net, h, l, p in rr:
        print(f"  {net}: {h * 1e3:.3f} {l * 1e3:.3f} {p:.3f}")
    if "--islands" in a or res["+BATT"]["unreachable"]:
        G = res["+BATT"]["G"]
        print("\n+BATT islands (component: pads / through-via segments / copper mm2 on L1, L8):")
        for c, d in sorted(M.islands(G, "+BATT").items(), key=lambda kv: -len(kv[1]["pads"]) if kv[0] != "floating" else 0):
            print(f"  {c}: {d['pads']} vias {d['vias']} L1 {d['area'].get(M.lname[0], 0):.1f} L8 {d['area'].get(M.lname[-1], 0):.1f}")
    if "--hot" in a:
        n = int(arg(a, "--hot", 8))
        res2, _ = run(M, i_esc, arg(a, "--buck", 0.5), want_map=True, nets=("CSA+", "GND"))
        for key in ("CSA+", "GND"):
            o = res2[key]
            L, _p = M.losses(o)
            print(f"\n{key}: {sum(L.values()):.3f} W, by layer mW " + str({k[:2]: round(v * 1e3) for k, v in L.items() if v > 2e-3}))
            hs, vs = M.hotspots(o, top=n)
            for h in hs:
                print("  (%.1f,%.1f) %.0f mW %.0f%% Jmax %.1f A/mm on %s" % (h["x"], h["y"], h["P_mW"], 100 * h["share"], h["J"], h["layer"][:2]))
            for v in vs[:5]:
                print("  vias (%.1f,%.1f) n=%d %.0f mW Imax %.2f A/via" % (v["x"], v["y"], v["vias"], v["P_mW"], v["I_max"]))
    print(f"[{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
