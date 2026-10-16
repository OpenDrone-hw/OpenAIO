"""Add the copper Freerouting routed (a .ses session) to the board; everything already on the board stays as it is.

Run with KiCad closed:  $KPY hardware/tools/fr_import.py hardware/OpenAIO.kicad_pcb run.ses [--skip-nets a,b] [--dry-run]

Only wires and vias that are not (type protect) are new: fr_prep.py protected every existing item. Wires become
tracks of the routed width (at least 0.09, the board minimum: Freerouting necks down at pins)
on their layer; nets in --skip-nets (default GND, /CSA+, +BATT, the phases: they are pours) are not imported; vias become 0.33/0.15 vias on their padstack layers (through, or blind with fr_prep.py --blind). KiCad's own
Specctra import is not used: it replaces all tracks, which would drop arcs, via types and the owner's routing.
The UUIDs of the new items go to <ses>.new.txt for tools/fr_prune.py.
"""
import os
import re
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


P = quiet_import()


def parse(text):
    toks = re.findall(r'"[^"]*"|\(|\)|[^\s()]+', text)
    stack = [[]]
    for t in toks:
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t.strip('"'))
    return stack[0][0]


def find(node, head):
    for x in node:
        if isinstance(x, list) and x and x[0] == head:
            yield x


def main():
    a = sys.argv[1:]
    path, ses = [x for x in a if not x.startswith("--")][:2]
    b = P.LoadBoard(path)
    s = parse(open(ses).read())
    routes = next(find(s, "routes"))
    res = next(find(routes, "resolution"))
    scale = {"um": 1000, "mm": 1e6, "mil": 25400}[res[1]] / float(res[2])   # nm per unit
    nets = {n.GetNetname(): n for n in b.GetNetsByName().values()}
    layer = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    xy = lambda x, y: P.VECTOR2I(int(round(float(x) * scale)), int(round(-float(y) * scale)))
    added = {"track": 0, "via": 0}
    skip = set(a[a.index("--skip-nets") + 1].split(",")) if "--skip-nets" in a else \
        {"GND", "/CSA+", "+BATT", *[f"/{i}{c}" for i in range(1, 5) for c in "ABC"]}
    new = []
    for net in find(next(find(routes, "network_out")), "net"):
        if net[1] in skip:
            continue
        ni = nets.get(net[1])
        if ni is None:
            print("unknown net", net[1])
            continue
        for item in net[2:]:
            if not isinstance(item, list) or any(isinstance(x, list) and x[:2] == ["type", "protect"] for x in item):
                continue
            if item[0] == "wire":
                p = next(find(item, "path"))
                w = max(P.FromMM(0.09), int(round(float(p[2]) * scale)))
                pts = [xy(p[i], p[i + 1]) for i in range(3, len(p) - 1, 2)]
                for u, v in zip(pts, pts[1:]):
                    t = P.PCB_TRACK(b)
                    t.SetStart(u)
                    t.SetEnd(v)
                    t.SetWidth(w)
                    t.SetLayer(layer[p[1]])
                    t.SetNet(ni)
                    b.Add(t)
                    new.append(t.m_Uuid.AsString())
                    added["track"] += 1
            elif item[0] == "via":
                v = P.PCB_VIA(b)
                v.SetPosition(xy(item[2], item[3]))
                lo, hi = (int(x) for x in re.match(r"Via\[(\d+)-(\d+)\]", item[1]).groups())
                stack = list(b.GetEnabledLayers().CuStack())
                v.SetViaType(P.VIATYPE_THROUGH if (lo, hi) == (0, len(stack) - 1) else P.VIATYPE_BLIND)
                v.SetLayerPair(stack[lo], stack[hi])
                v.SetWidth(P.FromMM(0.33))
                v.SetDrill(P.FromMM(0.15))
                v.SetNet(ni)
                b.Add(v)
                new.append(v.m_Uuid.AsString())
                added["via"] += 1
    print("added", added)
    if "--dry-run" not in a:
        P.ZONE_FILLER(b).Fill(b.Zones())
        P.SaveBoard(path, b)
        open(ses + ".new.txt", "w").write("\n".join(new) + "\n")
        print("saved")


if __name__ == "__main__":
    main()
