"""Estimate the copper resistance and I2R loss of the high-current loops, vias included.

Run with KiCad's bundled Python (it ships numpy, scipy and PIL); KiCad may stay open, the board is only read:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/loop_resistance.py hardware/<board>.kicad_pcb [--esc 3.0] [--boost 2.5] [--temp 45] [--grid 0.1] [--by-layer]

Model. Each net's copper (filled zones, tracks, pads, via lands) is rasterised per layer on a --grid mm mesh; a
cell joins its four neighbours through the sheet resistance of that layer (copper thickness from the board
stackup, resistivity at --temp C). Vias join layers through their barrel: buried 0.15 mm holes plated 20 um
(NextPCB minimum average), laser microvias copper filled, plated pad holes 25 um, each barrel segment as long as
the dielectric it crosses. A pad is one node (its copper is a short). The battery pad is the source; every load
pad sinks its current; the sparse system is solved once and the loss is summed over every cell edge and via.

Loads (6-step commutation, battery-side average):
  ESC FETs     --esc A per ESC (full-throttle motor current at the battery), shared by the three high-side
               (+BATT pin 3) and three low-side (GND pin 1) pins; each phase net carries I x sqrt(2/3) RMS
               between the FET phase pads and the motor pad.
  Boost U2     --boost A from +BATT into its VIN and back on GND (O4 Lite in HD mode, 1.5 A at 5 V).
The shunt R2 (0.5 mOhm) is listed for scale; FET RDS(on) is not copper and is not included.
"""
import math
import os
import sys


def quiet_import():
    saved, null = os.dup(2), os.open(os.devnull, os.O_WRONLY)
    os.dup2(null, 2)
    try:
        import pcbnew
        return pcbnew
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(null)


pcbnew = quiet_import()
import numpy as np  # noqa: E402
import scipy.sparse as sp  # noqa: E402
import scipy.sparse.linalg as spla  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

MM = pcbnew.FromMM
RHO20, ALPHA = 1.72e-8, 0.00393
BURIED_PLATING, PTH_PLATING = 20e-6, 25e-6


def arg(a, name, default):
    return float(a[a.index(name) + 1]) if name in a else default


class Board:
    def __init__(self, path, grid, temp):
        self.b = pcbnew.LoadBoard(path)
        pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
        self.h = MM(grid)
        self.rho = RHO20 * (1 + ALPHA * (temp - 20))
        bb = self.b.GetBoardEdgesBoundingBox()
        self.x0, self.y0 = bb.GetLeft(), bb.GetTop()
        self.nx, self.ny = bb.GetWidth() // self.h + 1, bb.GetHeight() // self.h + 1
        self.layers = list(self.b.GetEnabledLayers().CuStack())
        # Copper thickness per layer and the dielectric between neighbours, read from the stackup in the board file
        # (read only; KiCad 10 Python does not expose the stackup items reliably).
        import re
        text = open(path).read()
        stack = text[text.index("(stackup"):text.index("(copper_finish")]
        cu_t, di_t = [], []
        for kind, th in re.findall(r'\(type "([^"]+)"\)\s*\(thickness ([\d.]+)\)', stack):
            if kind == "copper":
                cu_t.append(float(th) * 1e-3)
            elif kind in ("prepreg", "core"):
                di_t.append(float(th) * 1e-3)
        self.cu = {l: (cu_t[i] if i < len(cu_t) else 35e-6) for i, l in enumerate(self.layers)}
        self.gap = [di_t[i] if i < len(di_t) else 1e-4 for i in range(len(self.layers) - 1)]

    def cell(self, p):
        return (int(round((p.x - self.x0) / self.h)), int(round((p.y - self.y0) / self.h)))

    def raster(self, net, layer):
        img = Image.new("1", (self.nx, self.ny), 0)
        d = ImageDraw.Draw(img)

        def poly(ps):
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i)
                pts = [((o.CPoint(k).x - self.x0) / self.h, (o.CPoint(k).y - self.y0) / self.h) for k in range(o.PointCount())]
                if len(pts) > 2:
                    d.polygon(pts, fill=1)

        for z in self.b.Zones():
            if not z.GetIsRuleArea() and z.GetNetname() == net and z.IsOnLayer(layer):
                poly(z.GetFilledPolysList(layer))
        shapes = pcbnew.SHAPE_POLY_SET()
        for t in self.b.GetTracks():
            if t.GetNetname() == net and t.IsOnLayer(layer):
                t.TransformShapeToPolygon(shapes, layer, 0, MM(0.005), pcbnew.ERROR_INSIDE)
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net and p.IsOnLayer(layer):
                    p.TransformShapeToPolygon(shapes, layer, 0, MM(0.005), pcbnew.ERROR_INSIDE)
        poly(shapes)
        return np.array(img, dtype=bool).T  # [x, y]


def solve(B, net, source_pads, sinks, label):
    """sinks: list of (pads, amps). Returns per-sink drop (V), total loss (W), via loss (W)."""
    masks = {l: B.raster(net, l) for l in B.layers}
    index, n = {}, 0
    for li, l in enumerate(B.layers):
        xs, ys = np.nonzero(masks[l])
        for x, y in zip(xs, ys):
            index[(li, x, y)] = n
            n += 1
    rows, cols, vals = [], [], []
    edges = []  # (a, b, g, kind)

    def link(a, b, g, kind):
        edges.append((a, b, g, kind))

    for li, l in enumerate(B.layers):
        g = B.cu[l] / B.rho  # square cell: sheet conductance
        m = masks[l]
        xs, ys = np.nonzero(m[:-1, :] & m[1:, :])
        for x, y in zip(xs, ys):
            link(index[(li, x, y)], index[(li, x + 1, y)], g, B.b.GetLayerName(l))
        xs, ys = np.nonzero(m[:, :-1] & m[:, 1:])
        for x, y in zip(xs, ys):
            link(index[(li, x, y)], index[(li, x, y + 1)], g, B.b.GetLayerName(l))

    def nearest(li, c):
        for r in range(0, 4):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    k = (li, c[0] + dx, c[1] + dy)
                    if k in index:
                        return index[k]
        return None

    def barrel(p, top, bot, area):
        a, b_ = B.layers.index(top), B.layers.index(bot)
        prev = None
        for li in range(a, b_ + 1):
            node = nearest(li, B.cell(p))
            if prev is not None and node is not None:
                length = sum(B.gap[k] for k in range(prev[0], li)) + B.cu[B.layers[li]]
                link(prev[1], node, area / (B.rho * length), "via")
            if node is not None:
                prev = (li, node)

    for v in B.b.GetTracks():
        if v.GetClass() != "PCB_VIA" or v.GetNetname() != net:
            continue
        r = v.GetDrillValue() * 1e-9 / 2
        if v.GetViaType() == pcbnew.VIATYPE_MICROVIA:
            area = math.pi * r * r  # copper filled
        else:
            area = math.pi * ((r + BURIED_PLATING) ** 2 - r * r)
        barrel(v.GetPosition(), v.TopLayer(), v.BottomLayer(), area)
    for fp in B.b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and p.HasHole():
                r = p.GetDrillSize().x * 1e-9 / 2
                barrel(p.GetPosition(), B.layers[0], B.layers[-1], math.pi * ((r + PTH_PLATING) ** 2 - r * r))

    # Pads are nodes: every cell under a pad ties to one extra node.
    def pad_node(pads):
        nonlocal n
        node = n
        n += 1
        for p in pads:
            for li, l in enumerate(B.layers):
                if not p.IsOnLayer(l):
                    continue
                bb = p.GetBoundingBox()
                c0, c1 = B.cell(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop())), B.cell(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
                hit = False
                for x in range(c0[0], c1[0] + 1):
                    for y in range(c0[1], c1[1] + 1):
                        k = (li, x, y)
                        if k in index and p.HitTest(pcbnew.VECTOR2I(B.x0 + x * B.h, B.y0 + y * B.h)):
                            link(node, index[k], 1e6, "pad")
                            hit = True
                if not hit:
                    k = nearest(li, B.cell(p.GetPosition()))
                    if k is not None:
                        link(node, k, 1e6, "pad")
        return node

    src = pad_node(source_pads)
    sink_nodes = [(pad_node(pads), amps) for pads, amps in sinks]
    a = np.array([e[0] for e in edges]); b_ = np.array([e[1] for e in edges]); g = np.array([e[2] for e in edges])
    G = sp.coo_matrix((np.concatenate([g, g, -g, -g]), (np.concatenate([a, b_, a, b_]), np.concatenate([a, b_, b_, a]))),
                      shape=(n, n)).tocsr()
    keep = np.ones(n, bool)
    keep[src] = False  # source at 0 V
    rhs = np.zeros(n)
    for node, amps in sink_nodes:
        rhs[node] -= amps
    Gk = G[keep][:, keep]
    # Copper islands not tied to the source make the matrix singular; a tiny leak to 0 V fixes that harmlessly.
    Gk = Gk + sp.identity(Gk.shape[0]) * 1e-9
    V = np.zeros(n)
    V[keep] = spla.spsolve(Gk.tocsc(), rhs[keep])
    dv = V[a] - V[b_]
    loss = g * dv * dv
    kinds = np.array([e[3] for e in edges])
    total = loss[kinds != "pad"].sum()
    via = loss[kinds == "via"].sum()
    drops = [-V[node] for node, _ in sink_nodes]
    if "--by-layer" in sys.argv:
        parts = {k: loss[kinds == k].sum() for k in set(kinds) if k != "pad"}
        print(f"  {label}: " + ", ".join(f"{k} {v * 1e3:.1f} mW" for k, v in sorted(parts.items(), key=lambda kv: -kv[1])))
    return drops, total, via


def main():
    a = sys.argv[1:]
    path = a[0]
    i_esc, i_boost = arg(a, "--esc", 3.0), arg(a, "--boost", 2.5)
    B = Board(path, arg(a, "--grid", 0.1), arg(a, "--temp", 45))
    fp = {f.GetReference(): f for f in B.b.GetFootprints()}

    def pads(ref, net):
        return [p for p in fp[ref].Pads() if p.GetNetname() == net]

    escs = {"ESC1": ("Q29", "Q30", "Q31", "J4"), "ESC2": ("Q32", "Q33", "Q34", "J7"),
            "ESC3": ("Q35", "Q36", "Q37", "J10"), "ESC4": ("Q38", "Q39", "Q40", "J13")}
    i_total = 4 * i_esc + i_boost
    rows = []
    # Battery + to the shunt.
    d, w, wv = solve(B, "/POWER/CSA+", pads("J2", "/POWER/CSA+"), [(pads("R2", "/POWER/CSA+"), i_total)], "CSA+")
    rows.append(("J2 to shunt R2 (CSA+)", i_total, d[0] / i_total, w, wv))
    rows.append(("shunt R2 0.5 mOhm (part)", i_total, 0.5e-3, i_total ** 2 * 0.5e-3, 0.0))
    # +BATT from the shunt to the FET high sides and the boost input.
    sinks = [(pads(q, "+BATT"), i_esc / 3) for e in escs.values() for q in e[:3]] + [(pads("L1", "+BATT") or pads("U2", "+BATT"), i_boost)]
    d, w, wv = solve(B, "+BATT", pads("R2", "+BATT"), sinks, "+BATT")
    rows.append(("+BATT shunt to FETs and boost", i_total, w / i_total ** 2, w, wv))
    # GND from the FET low sides and the boost back to the battery - pad.
    sinks = [(pads(q, "GND"), i_esc / 3) for e in escs.values() for q in e[:3]] + [(pads("U2", "GND"), i_boost)]
    d, w, wv = solve(B, "GND", pads("J3", "GND"), sinks, "GND")
    rows.append(("GND FETs and boost to J3", i_total, w / i_total ** 2, w, wv))
    # Phases.
    i_ph = i_esc * math.sqrt(2 / 3)
    for name, (qa, qb, qc, j) in escs.items():
        for q in (qa, qb, qc):
            net = next(p.GetNetname() for p in fp[q].Pads() if "PHASE" in p.GetNetname())
            mot = [p for p in fp[j].Pads() if p.GetNetname() == net]
            d, w, wv = solve(B, net, mot, [(pads(q, net), i_ph)], net)
            rows.append((f"{net} {q} to {j}", i_ph, d[0] / i_ph, w, wv))
    print(f"copper at {arg(a, '--temp', 45):.0f} C, grid {arg(a, '--grid', 0.1)} mm, ESC {i_esc} A each, boost {i_boost} A, battery {i_total} A")
    print(f"{'path':42} {'I (A)':>6} {'R (mOhm)':>9} {'P (mW)':>8} {'vias (mW)':>9}")
    for name, i, r, w, wv in rows:
        print(f"{name:42} {i:6.2f} {r * 1e3:9.3f} {w * 1e3:8.1f} {wv * 1e3:9.1f}")
    tot = sum(r[3] for r in rows)
    print(f"{'total':42} {'':6} {'':9} {tot * 1e3:8.1f} {sum(r[4] for r in rows) * 1e3:9.1f}")


if __name__ == "__main__":
    main()
