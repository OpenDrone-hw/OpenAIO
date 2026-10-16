"""Apply the 2026-10-16 RP2354A IO remap to hardware/fc_rp2350a.kicad_sch (sexpdata, no line edits).

Run with KiCad closed:  python3 hardware/tools/io_remap_sch.py hardware/fc_rp2350a.kicad_sch
                        python3 hardware/tools/io_remap_sch.py hardware/fc_pads.kicad_sch   (SH-6 pin 6 to PU0RX)
then re-save with `kicad-cli sch upgrade --force` and prove the result with ERC and a netlist diff.

Every U2 GPIO pin ends at x 321.31 on this sheet. A net moves to its new pin in one of three ways:
  - a label that sits on the old pin end moves to the new pin end
  - a wire that runs from the old pin to its label or test point loses only the segment that touches the pin,
    and a local label of the same name goes on the new pin end (same-name labels join within a sheet)
  - the no-connect flag moves with the free pin
"""
import copy
import sys
import uuid

import sexpdata as S

X = 321.31
# GPIO -> y of its pin end (from the RP2354A symbol at 295.91, 213.36)
Y = {0: 213.36, 1: 215.9, 2: 226.06, 3: 228.6, 4: 234.95, 5: 232.41, 6: 238.76, 7: 241.3, 8: 219.71, 9: 163.83,
     10: 166.37, 11: 168.91, 12: 171.45, 13: 173.99, 14: 264.16, 15: 266.7, 16: 269.24, 17: 222.25, 18: 182.88,
     19: 185.42, 20: 187.96, 21: 190.5, 22: 199.39, 23: 201.93, 24: 204.47, 25: 207.01, 26: 247.65, 27: 250.19,
     28: 252.73, 29: 255.27}
# net label: (old GPIO, new GPIO)
MOVES = {
    "SPI0.SCK": (18, 22), "FLASH_CS": (21, 24),
    "MOTOR2": (24, 21), "MOTOR3": (23, 18), "MOTOR4": (22, 8), "LED_STRIP_L": (8, 26), "LED0": (26, 27),
}
NC = (27, 23)   # no-connect flag: old free pin -> new free pin

sym = lambda x: str(x) if isinstance(x, S.Symbol) else None


def find(node, head):
    return [x for x in node if isinstance(x, list) and x and sym(x[0]) == head]


def at(n):
    a = find(n, "at")[0]
    return round(float(a[1]), 2), round(float(a[2]), 2)


def set_at(n, x, y):
    a = find(n, "at")[0]
    a[1], a[2] = x, y


def new_uuid(n):
    for u in find(n, "uuid"):
        u[1] = str(uuid.uuid4())


def sh6_pin6(path):
    """fc_pads: SH-6 pin 6 (air unit SBUS out) moves from UART1_RX, where it fought the ESP32 TX, to PU0RX
    (hardware UART0 RX, GPIO3), as config.h intends: SBUS (8E2) needs a hardware UART."""
    d = S.loads(open(path).read())
    r = lambda p: (round(float(p[1]), 2), round(float(p[2]), 2))
    cut = {((179.07, 59.69), (179.07, 44.45)), ((172.72, 44.45), (179.07, 44.45))}
    keep = []
    for x in d:
        if isinstance(x, list) and sym(x[0]) == "wire":
            pts = tuple(r(p) for p in find(find(x, "pts")[0], "xy"))
            if pts in cut or pts[::-1] in cut:
                continue
        keep.append(x)
    assert len(d) - len(keep) == 2
    lab = copy.deepcopy(next(l for l in find(keep, "label") if l[1] == "PU0RX"))
    a = find(lab, "at")[0]
    a[1], a[2], a[3] = 179.07, 59.69, 90
    new_uuid(lab)
    keep.insert(max(i for i, x in enumerate(keep) if isinstance(x, list) and sym(x[0]) == "label") + 1, lab)
    d[:] = keep
    open(path, "w").write(S.dumps(d))
    print("U12.6 (SH-6 pin 6): cut from U1RX / UART1_RX, label PU0RX")


def main():
    path = sys.argv[1]
    if path.endswith("fc_pads.kicad_sch"):
        return sh6_pin6(path)
    d = S.loads(open(path).read())
    labels = [l for h in ("hierarchical_label", "label") for l in find(d, h)]
    template = next(l for l in find(d, "label") if l[1] == "LED0" and at(l)[0] == X)   # a local label on a pin end
    pin_end = {g: (X, y) for g, y in Y.items()}
    report = []
    to_add, to_drop = [], []
    for name, (old, new) in MOVES.items():
        op, np_ = pin_end[old], pin_end[new]
        direct = [l for l in labels if l[1] == name and at(l) == op]
        if direct:                                   # label on the pin end: move it
            set_at(direct[0], *np_)
            # move its text field too, if it has one at the old spot
            report.append(f"{name}: label moved GPIO{old} -> GPIO{new}")
            continue
        segs = [w for w in find(d, "wire")
                if any((round(float(p[1]), 2), round(float(p[2]), 2)) == op for p in find(find(w, "pts")[0], "xy"))]
        assert len(segs) == 1, (name, len(segs))
        to_drop.append(segs[0])
        lab = copy.deepcopy(template)
        lab[1] = name
        set_at(lab, *np_)
        new_uuid(lab)
        to_add.append(lab)
        report.append(f"{name}: pin stub cut at GPIO{old}, label on GPIO{new}")
    # the LED_STRIP_L local label at 336.55 sat on the stub from GPIO8 only: drop it with its wire
    for l in find(d, "label"):
        if l[1] == "LED_STRIP_L" and at(l) == (336.55, 219.71):
            to_drop.append(l)
            report.append("LED_STRIP_L: orphan label at the old stub removed")
    nc = [n for n in find(d, "no_connect") if at(n) == pin_end[NC[0]]]
    assert len(nc) == 1
    set_at(nc[0], *pin_end[NC[1]])
    report.append(f"no-connect: GPIO{NC[0]} -> GPIO{NC[1]}")
    d[:] = [x for x in d if not any(x is y for y in to_drop)]
    i = max(i for i, x in enumerate(d) if isinstance(x, list) and sym(x[0]) == "label")
    d[i + 1:i + 1] = to_add
    open(path, "w").write(S.dumps(d))
    print("\n".join(report))


if __name__ == "__main__":
    main()
