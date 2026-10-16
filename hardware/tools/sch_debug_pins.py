"""2026-10-16: ELRS enable from the FC and SWD test pads (sexpdata, no line edits).

Run with KiCad closed, from hardware/:  python3 tools/sch_debug_pins.py
then `kicad-cli sch upgrade --force` both sheets and prove the result with ERC and a netlist diff.

fc_rp2350a.kicad_sch
  - GPIO27 (U2.41, was free): global label ELRS_EN, no-connect removed
  - SWCLK (U2.24) and SWDIO (U2.25): no-connects removed, test pads TP42 / TP43 on the pin ends, labels SWCLK / SWDIO
rx_esp32c3_sx1281.kicad_sch
  - global label ELRS_EN on the CHIP_EN net (R114 10k pull-up keeps ELRS on; the FC drives it low to hold the
    ESP32-C3 in reset, e.g. when the DJI SBUS output shares UART1_RX)
"""
import copy
import uuid

import sexpdata as S

sym = lambda x: str(x) if isinstance(x, S.Symbol) else None


def find(node, head):
    return [x for x in node if isinstance(x, list) and x and sym(x[0]) == head]


def at(n):
    a = find(n, "at")[0]
    return round(float(a[1]), 2), round(float(a[2]), 2)


def set_at(n, x, y, ang=None):
    a = find(n, "at")[0]
    a[1], a[2] = x, y
    if ang is not None:
        a[3] = ang


def fresh(n):
    for x in n:
        if isinstance(x, list):
            if x and sym(x[0]) == "uuid":
                x[1] = str(uuid.uuid4())
            else:
                fresh(x)


def insert_after_last(d, head, items):
    i = max(i for i, x in enumerate(d) if isinstance(x, list) and sym(x[0]) == head)
    d[i + 1:i + 1] = items


def global_label(template, name, x, y, ang):
    g = copy.deepcopy(template)
    g[1] = name
    set_at(g, x, y, ang)
    for p in find(g, "property"):      # intersheet refs field sits next to the label
        set_at(p, x, y, ang)
    fresh(g)
    return g


def rp2350():
    path = "fc_rp2350a.kicad_sch"
    d = S.loads(open(path).read())
    drop = {(321.31, 250.19), (270.51, 196.85), (270.51, 199.39)}
    ncs = [n for n in find(d, "no_connect") if at(n) in drop]
    assert len(ncs) == 3, len(ncs)
    d[:] = [x for x in d if not any(x is n for n in ncs)]
    tmpl_g = find(d, "global_label")[0]
    insert_after_last(d, "global_label", [global_label(tmpl_g, "ELRS_EN", 321.31, 250.19, 0)])
    tmpl_l = next(l for l in find(d, "label") if l[1] == "LED0")
    labs = []
    for name, y in (("SWCLK", 196.85), ("SWDIO", 199.39)):
        l = copy.deepcopy(tmpl_l)
        l[1] = name
        set_at(l, 270.51, y, 180)
        for e in find(l, "effects"):
            for j in find(e, "justify"):
                j[1:] = [S.Symbol("right")]
        fresh(l)
        labs.append(l)
    insert_after_last(d, "label", labs)
    tp18 = next(s for s in find(d, "symbol") if any(p[1] == "Reference" and p[2] == "TP18" for p in find(s, "property")))
    tps = []
    for ref, y in (("TP42", 196.85), ("TP43", 199.39)):
        t = copy.deepcopy(tp18)
        dx, dy = 270.51 - 324.485, y - 182.88
        set_at(t, 270.51, y, 90)
        for p in find(t, "property"):
            a = find(p, "at")[0]
            a[1], a[2] = round(float(a[1]) + dx - 6.0, 4), round(float(a[2]) + dy, 4)
            if p[1] == "Reference":
                p[2] = ref
        for f in find(t, "on_board"):
            f[1] = S.Symbol("yes")
        for inst in find(t, "instances"):
            for proj in find(inst, "project"):
                for pth in find(proj, "path"):
                    for r in find(pth, "reference"):
                        r[1] = ref
        fresh(t)
        tps.append(t)
    insert_after_last(d, "symbol", tps)
    open(path, "w").write(S.dumps(d))
    print("fc_rp2350a: GPIO27 -> ELRS_EN; TP42 SWCLK, TP43 SWDIO")


def rx():
    path = "rx_esp32c3_sx1281.kicad_sch"
    d = S.loads(open(path).read())
    ce = next(l for l in find(d, "label") if l[1] == "CHIP_EN")
    x, y = at(ce)
    ang = float(find(ce, "at")[0][3])
    tmpl = find(d, "global_label")
    if not tmpl:
        rp = S.loads(open("fc_rp2350a.kicad_sch").read())
        tmpl = find(rp, "global_label")
    insert_after_last(d, "label", [global_label(tmpl[0], "ELRS_EN", x, y, ang)])
    open(path, "w").write(S.dumps(d))
    print(f"rx: ELRS_EN on CHIP_EN at ({x}, {y})")


if __name__ == "__main__":
    rp2350()
    rx()
