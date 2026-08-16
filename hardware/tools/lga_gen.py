#!/usr/bin/env python3
"""OpenAIO Base<->Core LGA interface generator.

One pin table produces every artefact of the board-to-board interface, so
they cannot drift:

  lib.pretty/Core_LGA_land.kicad_mod   F.Cu land pattern, J90 on OpenAIO-Base
  lib.pretty/Core_LGA_pads.kicad_mod   pads for the Core, J91 on B.Cu of OpenAIO-Core
                                       (its X is pre-mirrored so that after the
                                       flip pad k sits exactly over land pad k)
  lib.kicad_sym : symbol Core_LGA      one symbol, two instances in the schematic
  core_interface.kicad_sch             the interface sheet (only if missing, or
                                       with --sheet; it is a hand-editable file)

Run from hardware/:
  KPY tools/lga_gen.py --from-base [--sheet]   read the marker test points on the Base
                                               (KiCad's Python), rewrite the pin table
                                               here, then generate everything
  python3 tools/lga_gen.py [--sheet]           regenerate from the stored table
Never edits OpenAIO.kicad_sch. Putting the new footprints on the boards is
tools/lga_apply.py.
"""
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)

# ---------------------------------------------------------------- pin table
# (number, name, kind, x, y)   kind: PWR power net, SIG signal, BUS member of SPI0.
# x, y in mm, top view of the Base land pattern, footprint origin = ORIGIN.
# Every interface net is a GLOBAL label: the interface is board-wide by nature.
# The table is written by `--from-base`: it reads the J90 on the board plus the
# marker test points (see read_markers_from_base) from OpenAIO-Base.kicad_pcb
# and rewrites the block between PINS-BEGIN and PINS-END in this file. Pins
# are numbered in reading order, top row first, left to right.
PAD = 1.0          # mm, round pad diameter, same as the marker test points
MARKER_MIN = 10    # TP references below this are real test points, not markers
MOVE_R = 1.0       # mm, a marker this close to an existing pin moves (with net) or deletes (no net) it
# PINS-BEGIN
ORIGIN = (80.25, 61.65)   # absolute Base position of J90 (and of J91 relative to the Core)
PINS = [
    (1, "10V_ENABLE", "SIG", -10.45, -8.87),
    (2, "CURR", "SIG", -10.45, -6.87),
    (3, "SPI0.MISO", "BUS", -7.8, -6.18),
    (4, "SPI0.SCK", "BUS", -5.8, -6.18),
    (5, "SPI0.MOSI", "BUS", -3.8, -6.18),
    (6, "FLASH_CS", "SIG", -1.8, -6.18),
    (7, "+10V", "PWR", 0.2, -6.18),
    (8, "+3.3V", "PWR", 2.2, -6.18),
    (9, "USB_D+", "SIG", -10.45, -4.87),
    (10, "GND", "PWR", -5.8, -4.18),
    (11, "GND", "PWR", -3.8, -4.18),
    (12, "USB_D-", "SIG", -10.45, -2.87),
    (13, "+5V", "PWR", -8.45, -2.88),
    (14, "GND", "PWR", 8.45, 0.01),
    (15, "GND", "PWR", 10.45, 0.01),
    (16, "MOTOR2", "SIG", -5.82, 1.9),
    (17, "MOTOR4", "SIG", -3.82, 1.9),
    (18, "GND", "PWR", -1.82, 1.9),
    (19, "GND", "PWR", 0.18, 1.9),
    (20, "BUZZER-", "SIG", 10.45, 2.01),
    (21, "MOTOR1", "SIG", -5.82, 3.9),
    (22, "MOTOR3", "SIG", -3.82, 3.9),
    (23, "GND", "PWR", -1.82, 3.9),
    (24, "GND", "PWR", 0.18, 3.9),
    (25, "+BATT", "PWR", -8.3, 4.01),
    (26, "GND", "PWR", -7.13, 6.86),
    (27, "GND", "PWR", -4.12, 6.86),
    (28, "GND", "PWR", 2.97, 8.56),
    (29, "UART0_TX", "SIG", 4.97, 8.56),
    (30, "UART0_RX", "SIG", 6.97, 8.56),
    (31, "LED_STRIP", "SIG", -7.13, 8.86),
    (32, "UART1_RX", "SIG", -3.13, 8.86),
    (33, "UART1_TX", "SIG", -1.13, 8.86),
]
# PINS-END
BUS_LABEL = "SPI0{SCK,MOSI,MISO}"


def N():
    return len(PINS)


def kind_of(name):
    if name.startswith("SPI0."):
        return "BUS"
    if name == "GND" or name.startswith("+"):
        return "PWR"
    return "SIG"


def pad_xy(n):
    """Top-view position of pad n on the Base land pattern, footprint origin
    at ORIGIN."""
    for m, _, _, x, y in PINS:
        if m == n:
            return x, y
    raise KeyError(n)


def pad_name(n):
    for m, name, _, _, _ in PINS:
        if m == n:
            return name
    raise KeyError(n)


def bbox():
    xs = [p[3] for p in PINS]
    ys = [p[4] for p in PINS]
    return min(xs), min(ys), max(xs), max(ys)


def read_markers_from_base():
    """Markers on OpenAIO-Base.kicad_pcb -> (origin, pins). Needs KiCad's
    Python (pcbnew).

    The pin set starts from the pads of the J90 already on the board (net +
    position), so the pattern survives between regenerations. Then every test
    point footprint (any lib, name TestPoint*, reference not TP1..TP9, which
    are the board's real test points):
      with a net     -> a pin. If a pin of the same net lies within MOVE_R of
                        it, that pin moves here (moved pad); else it is added.
      without a net  -> deletes the pin within MOVE_R of it (any net); a
                        footprint added straight from the library has no net,
                        so "drop a TestPoint on the pad" removes the pad.
    A local net (/Pads/LED_STRIP) becomes the global label LED_STRIP.
    """
    import pcbnew
    b = pcbnew.LoadBoard(os.path.join(HW, "OpenAIO-Base.kicad_pcb"))
    pins = []      # [net, x, y]
    for f in b.GetFootprints():
        if f.GetFPID().GetLibItemName() == "Core_LGA_land":
            for p in f.Pads():
                q = p.GetPosition()
                pins.append([p.GetNetname(), round(pcbnew.ToMM(q.x), 3), round(pcbnew.ToMM(q.y), 3)])
    if pins:
        print(f"  {len(pins)} pins from the J90 on the board")

    def near(x, y, net=None):
        for i, (n, px, py) in enumerate(pins):
            if ((px - x) ** 2 + (py - y) ** 2) ** 0.5 <= MOVE_R and (net is None or n == net):
                return i
        return None

    for f in b.GetFootprints():
        ref = f.GetReference()
        if not str(f.GetFPID().GetLibItemName()).startswith("TestPoint"):
            continue
        m = re.fullmatch(r"TP(\d+)", ref)
        if m and int(m.group(1)) < MARKER_MIN:
            continue
        pos = f.GetPosition()
        x, y = round(pcbnew.ToMM(pos.x), 3), round(pcbnew.ToMM(pos.y), 3)
        nets = {p.GetNetname() for p in f.Pads()} - {""}
        net = next(iter(nets)) if len(nets) == 1 else None
        if not net or net.startswith("unconnected-"):
            i = near(x, y)
            if i is None:
                print(f"  {ref} at ({x}, {y}): no net and no pad within {MOVE_R} mm, ignored")
            else:
                print(f"  {ref}: deletes pin {pins[i][0]} at ({pins[i][1]}, {pins[i][2]})")
                pins.pop(i)
            continue
        net = net.rsplit("/", 1)[-1]
        i = near(x, y, net)
        if i is not None:
            print(f"  {ref}: moves {net} ({pins[i][1]}, {pins[i][2]}) -> ({x}, {y})")
            pins[i][1], pins[i][2] = x, y
        else:
            print(f"  {ref}: adds {net} at ({x}, {y})")
            pins.append([net, x, y])
    if not pins:
        sys.exit("no pins: no J90 and no marker test points with a net on OpenAIO-Base")
    xs = [p[1] for p in pins]
    ys = [p[2] for p in pins]
    ox = round((min(xs) + max(xs)) / 2, 2)
    oy = round((min(ys) + max(ys)) / 2, 2)
    pins.sort(key=lambda p: (round(p[2], 1), p[1]))
    out = [(i + 1, net, kind_of(net), round(x - ox, 3), round(y - oy, 3)) for i, (net, x, y) in enumerate(pins)]
    for n, net, kind, x, y in out:
        print(f"  pin {n:2d} {net:12s} at ({x:+.3f}, {y:+.3f})")
    return (ox, oy), out


def rewrite_pins(origin, pins):
    """Rewrite the PINS-BEGIN..PINS-END block of this file."""
    path = os.path.abspath(__file__)
    s = open(path).read()
    a = s.index("# PINS-BEGIN\n") + len("# PINS-BEGIN\n")
    z = s.index("# PINS-END")
    body = [f"ORIGIN = ({origin[0]}, {origin[1]})   # absolute Base position of J90 (and of J91 relative to the Core)", "PINS = ["]
    for n, name, kind, x, y in pins:
        body.append(f'    ({n}, "{name}", "{kind}", {x}, {y}),')
    body.append("]")
    s = s[:a] + "\n".join(body) + "\n" + s[z:]
    open(path, "w").write(s)
    print(f"rewrote PINS in tools/lga_gen.py: {len(pins)} pins, origin {origin}")


def u():
    return str(uuid.uuid4())


# ---------------------------------------------------------------- footprints
def footprint(name, mirror, layers, paste, descr):
    L = []
    L.append(f'(footprint "{name}"')
    L.append('\t(version 20260206)')
    L.append('\t(generator "lga_gen.py")')
    L.append('\t(generator_version "10.0")')
    L.append('\t(layer "F.Cu")')
    L.append(f'\t(descr "{descr}")')
    L.append('\t(tags "OpenAIO LGA board-to-board")')
    x0, y0, x1, y1 = bbox()
    half_w = max(abs(x0), abs(x1)) + PAD / 2 + 0.25
    half_h = max(abs(y0), abs(y1)) + PAD / 2 + 0.25

    def prop(k, v, y, layer, hide=False):
        L.append(f'\t(property "{k}" "{v}"')
        L.append(f'\t\t(at 0 {y} 0)')
        L.append('\t\t(unlocked yes)')
        L.append(f'\t\t(layer "{layer}")')
        if hide:
            L.append('\t\t(hide yes)')
        L.append(f'\t\t(uuid "{u()}")')
        L.append('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))')
        L.append('\t)')

    prop("Reference", "REF**", -half_h - 1.0, "F.SilkS")
    prop("Value", name, half_h + 1.0, "F.Fab")
    prop("Datasheet", "", 0, "F.Fab", True)
    prop("Description", descr, 0, "F.Fab", True)
    L.append('\t(attr smd exclude_from_pos_files exclude_from_bom)')
    # courtyard and fab outline
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1)):
        L.append(f'\t(fp_rect (start {-half_w} {-half_h}) (end {half_w} {half_h})'
                 f' (stroke (width {w}) (type default)) (fill no) (layer "{layer}") (uuid "{u()}"))')
    # pin 1 marker: chamfer triangle on Fab + dot on silk, at the pin-1 corner
    x1, y1 = pad_xy(1)
    sx = -1 if mirror else 1
    L.append(f'\t(fp_circle (center {sx * (x1 - 0.9):.4f} {y1 - 0.9:.4f}) (end {sx * (x1 - 0.9) + 0.15:.4f} {y1 - 0.9:.4f})'
             f' (stroke (width 0.15) (type default)) (fill yes) (layer "F.SilkS") (uuid "{u()}"))')
    L.append(f'\t(fp_circle (center {sx * (x1 - 0.9):.4f} {y1 - 0.9:.4f}) (end {sx * (x1 - 0.9) + 0.15:.4f} {y1 - 0.9:.4f})'
             f' (stroke (width 0.1) (type default)) (fill yes) (layer "F.Fab") (uuid "{u()}"))')
    for n, pname, kind, x, y in PINS:
        if mirror:
            x = -x
        lay = " ".join(f'"{l}"' for l in layers)
        L.append(f'\t(pad "{n}" smd circle (at {x:.4f} {y:.4f}) (size {PAD} {PAD})'
                 f' (layers {lay}) (uuid "{u()}"))')
    if not mirror:
        # the land carries the Core as its 3D model (tools/core_model.py writes
        # it, origin at J91 = this footprint's origin), so the Base 3D view
        # shows the hat in place
        L.append('\t(model "${KIPRJMOD}/export/OpenAIO-Core.wrl"')
        L.append('\t\t(offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0))')
        L.append('\t)')
    L.append('\t(embedded_fonts no)')
    L.append(')')
    return "\n".join(L) + "\n"


def write_footprints():
    d = os.path.join(HW, "lib.pretty")
    land = footprint("Core_LGA_land", False, ["F.Cu", "F.Mask", "F.Paste"], True,
                     f"OpenAIO Core LGA land pattern on the Base, {N()} pads, {PAD} mm, positions from the marker "
                     "test points. Paste. Generated by tools/lga_gen.py --from-base")
    pads = footprint("Core_LGA_pads", True, ["F.Cu", "F.Mask"], False,
                     "OpenAIO Core LGA pads on the Core bottom. Place on B.Cu: X is pre-mirrored so the flipped "
                     "footprint overlays Core_LGA_land pad for pad. No paste. Generated by tools/lga_gen.py")
    for name, txt in (("Core_LGA_land", land), ("Core_LGA_pads", pads)):
        with open(os.path.join(d, name + ".kicad_mod"), "w") as f:
            f.write(txt)
        print("wrote lib.pretty/" + name + ".kicad_mod")


# ---------------------------------------------------------------- symbol
SYM = "Core_LGA"
SYM_PITCH = 2.54


def symbol_block():
    """Symbol with all pins on the left, one per LGA pad. Reference J."""
    top = -((N() - 1) / 2) * SYM_PITCH  # y of pin 1
    L = []
    L.append(f'\t(symbol "{SYM}"')
    L.append('\t\t(exclude_from_sim no)')
    L.append('\t\t(in_bom no)')
    L.append('\t\t(on_board yes)')
    L.append('\t\t(in_pos_files no)')
    L.append('\t\t(duplicate_pin_numbers_are_jumpers no)')

    def prop(k, v, x, y, hide=False, just="left"):
        L.append(f'\t\t(property "{k}" "{v}"')
        L.append(f'\t\t\t(at {x} {y} 0)')
        L.append('\t\t\t(show_name no)')
        L.append('\t\t\t(do_not_autoplace no)')
        L.append('\t\t\t(effects (font (size 1.27 1.27))' + (' (justify left)' if just else '') + (' (hide yes)' if hide else '') + ')')
        L.append('\t\t)')

    prop("Reference", "J", 0, top - 6.35)
    prop("Value", SYM, 0, top - 3.81)
    prop("Footprint", "lib:Core_LGA_land", 0, 0, True)
    prop("Datasheet", "", 0, 0, True)
    prop("Description", f"OpenAIO Base<->Core LGA interface, {N()} pads. Two instances: J90 land (Base), J91 pads (Core). Pin table: tools/lga_gen.py", 0, 0, True)
    L.append(f'\t\t(symbol "{SYM}_0_1"')
    L.append(f'\t\t\t(rectangle (start 0 {top - 2.54}) (end 12.7 {top + N() * SYM_PITCH - 0.0})'
             ' (stroke (width 0.254) (type default)) (fill (type background)))')
    L.append('\t\t)')
    L.append(f'\t\t(symbol "{SYM}_1_1"')
    for n, pname, kind, _, _ in PINS:
        y = -(top + (n - 1) * SYM_PITCH)   # symbol Y axis is up in lib files
        etype = "passive"
        L.append(f'\t\t\t(pin {etype} line')
        L.append(f'\t\t\t\t(at -3.81 {y:.4f} 0)')
        L.append('\t\t\t\t(length 3.81)')
        L.append(f'\t\t\t\t(name "{pname}" (effects (font (size 1.0 1.0))))')
        L.append(f'\t\t\t\t(number "{n}" (effects (font (size 1.0 1.0))))')
        L.append('\t\t\t)')
    L.append('\t\t)')
    L.append('\t\t(embedded_fonts no)')
    L.append('\t)')
    return "\n".join(L) + "\n"


def splice_symbol():
    path = os.path.join(HW, "lib.kicad_sym")
    s = open(path).read()
    key = f'\t(symbol "{SYM}"'
    if key in s:
        i = s.index(key)
        d = 0
        j = i
        while True:
            c = s[j]
            if c == '(':
                d += 1
            elif c == ')':
                d -= 1
                if d == 0:
                    j += 1
                    break
            j += 1
        if s[j] == '\n':
            j += 1
        s = s[:i] + s[j:]
    k = s.rstrip().rfind(')')
    s = s[:k].rstrip('\n') + '\n' + symbol_block() + ')\n'
    assert s.count('(') == s.count(')'), "paren imbalance"
    open(path, 'w').write(s)
    print("spliced symbol lib:" + SYM)


# ---------------------------------------------------------------- interface sheet
def lib_symbol_for_sheet():
    """Copy of the symbol for the sheet's lib_symbols block, lib_id prefixed."""
    blk = symbol_block()
    blk = blk.replace(f'\t(symbol "{SYM}"', f'\t(symbol "lib:{SYM}"', 1)
    return blk


def sheet_file(root_uuid, sheet_uuid, sym_uuids):
    """core_interface.kicad_sch: J90 (land) and J91 (pads) side by side, every
    pin wired to a global label; SPI0 members through a bus with a global bus
    label. No sheet pins: the same global labels sit on the root at the
    sheet pins that carry these nets (tools/lga_wire_root.py)."""
    L = []
    L.append('(kicad_sch')
    L.append('\t(version 20260306)')
    L.append('\t(generator "lga_gen.py")')
    L.append('\t(generator_version "10.0")')
    L.append(f'\t(uuid "{sheet_uuid}")')
    L.append('\t(paper "A4")')
    L.append('\t(title_block (title "OpenAIO Base <-> Core LGA interface") (rev "1")'
             ' (comment 1 "J90 = land pattern on Base, J91 = pads on Core bottom. Pin table: tools/lga_gen.py"))')
    L.append('\t(lib_symbols')
    L.append(lib_symbol_for_sheet().rstrip('\n'))
    L.append('\t)')

    top = -((N() - 1) / 2) * SYM_PITCH
    inst_path = f"/{root_uuid}/{sheet_uuid}"

    def place(ref, fpname, ox, oy):
        """Symbol at (ox,oy); pin n end at (ox-3.81, oy+top+(n-1)*pitch)."""
        L.append('\t(symbol')
        L.append(f'\t\t(lib_id "lib:{SYM}")')
        L.append(f'\t\t(at {ox} {oy} 0)')
        L.append('\t\t(unit 1)')
        L.append('\t\t(body_style 1)')
        L.append('\t\t(exclude_from_sim no)')
        L.append('\t\t(in_bom no)')
        L.append('\t\t(on_board yes)')
        L.append('\t\t(in_pos_files no)')
        L.append('\t\t(dnp no)')
        L.append('\t\t(fields_autoplaced yes)')
        L.append(f'\t\t(uuid "{sym_uuids.get(ref) or u()}")')
        for k, v, dy, hide in (("Reference", ref, top - 6.35, False), ("Value", SYM, top - 3.81, False),
                               ("Footprint", fpname, 0, True), ("Datasheet", "", 0, True),
                               ("Description", "OpenAIO Base<->Core LGA interface", 0, True)):
            L.append(f'\t\t(property "{k}" "{v}"')
            L.append(f'\t\t\t(at {ox + 1.27} {oy + dy} 0)')
            if hide:
                L.append('\t\t\t(hide yes)')
            L.append('\t\t\t(show_name no)')
            L.append('\t\t\t(do_not_autoplace no)')
            L.append('\t\t\t(effects (font (size 1.27 1.27)) (justify left))')
            L.append('\t\t)')
        for n, _, _, _, _ in PINS:
            L.append(f'\t\t(pin "{n}" (uuid "{u()}"))')
        L.append('\t\t(instances')
        L.append('\t\t\t(project "OpenAIO"')
        L.append(f'\t\t\t\t(path "{inst_path}"')
        L.append(f'\t\t\t\t\t(reference "{ref}")')
        L.append('\t\t\t\t\t(unit 1)')
        L.append('\t\t\t\t)')
        L.append('\t\t\t)')
        L.append('\t\t)')
        L.append('\t)')

    def wire(x1, y1, x2, y2):
        L.append(f'\t(wire (pts (xy {x1:.4f} {y1:.4f}) (xy {x2:.4f} {y2:.4f}))'
                 f' (stroke (width 0) (type default)) (uuid "{u()}"))')

    def bus(x1, y1, x2, y2):
        L.append(f'\t(bus (pts (xy {x1:.4f} {y1:.4f}) (xy {x2:.4f} {y2:.4f}))'
                 f' (stroke (width 0) (type default)) (uuid "{u()}"))')

    def label(kind, text, x, y, rot=180, shape=None):
        L.append(f'\t({kind} "{text}"')
        if shape:
            L.append(f'\t\t(shape {shape})')
        L.append(f'\t\t(at {x:.4f} {y:.4f} {rot})')
        just = "right" if rot == 180 else "left"
        L.append(f'\t\t(effects (font (size 1.27 1.27)) (justify {just}))')
        L.append(f'\t\t(uuid "{u()}")')
        L.append('\t)')

    # two symbols, pins pointing left, wires 7.62 long, labels at the wire ends
    for ref, fp, ox in (("J90", "lib:Core_LGA_land", 76.2), ("J91", "lib:Core_LGA_pads", 177.8)):
        oy = 105.41
        place(ref, fp, ox, oy)
        px = ox - 3.81
        bus_x = px - 20.32
        for n, pname, kind, _, _ in PINS:
            py = oy + top + (n - 1) * SYM_PITCH
            if kind == "PWR":
                wire(px, py, px - 7.62, py)
                label("global_label", pname, px - 7.62, py, 180, "input" if pname != "GND" else "passive")
            elif kind == "SIG":
                wire(px, py, px - 7.62, py)
                label("global_label", pname, px - 7.62, py, 180, "bidirectional")
            else:  # BUS member: wire to a bus entry, label the wire
                wire(px, py, bus_x + 2.54, py)
                label("label", pname, px - 1.27, py, 180)
                L.append(f'\t(bus_entry (at {bus_x:.4f} {py + 2.54:.4f}) (size 2.54 -2.54)'
                         f' (stroke (width 0) (type default)) (uuid "{u()}"))')
        # bus spine + hierarchical bus label
        bus_pins = [n for n, _, k, _, _ in PINS if k == "BUS"]
        y0 = oy + top + (bus_pins[0] - 1) * SYM_PITCH + 2.54
        y1 = oy + top + (bus_pins[-1] - 1) * SYM_PITCH + 2.54 + 7.62
        bus(bus_x, y0 - 2.54, bus_x, y1)
        label("global_label", BUS_LABEL, bus_x, y1, 270, "bidirectional")
        L.append(f'\t(text "{"land on Base" if ref == "J90" else "pads on Core bottom"}"'
                 f' (exclude_from_sim no) (at {ox:.4f} {oy + top - 8.89:.4f} 0)'
                 f' (effects (font (size 1.5 1.5)) (justify left bottom)) (uuid "{u()}"))')

    L.append('\t(sheet_instances (path "/" (page "1")))')
    L.append('\t(embedded_fonts no)')
    L.append(')')
    return "\n".join(L) + "\n"


def write_sheet(force):
    path = os.path.join(HW, "core_interface.kicad_sch")
    if os.path.exists(path) and not force:
        print("core_interface.kicad_sch exists, not touched (use --sheet to regenerate)")
        return
    root = open(os.path.join(HW, "OpenAIO.kicad_sch")).read()
    # the project's root path as used by every existing instance
    m = re.search(r'\(path "/([0-9a-f-]{36})(?:/|")', root)
    root_uuid = m.group(1)
    sheet_uuid = None
    if os.path.exists(path):
        sheet_uuid = re.search(r'\(uuid "([0-9a-f-]{36})"', open(path).read()).group(1)
    sheet_uuid = sheet_uuid or u()
    # keep the symbol uuids stable across regenerations: the PCB links by path
    sym_uuids = {}
    if os.path.exists(path):
        old = open(path).read()
        for m in re.finditer(r'\(symbol\n\t\t\(lib_id "lib:Core_LGA"\).*?\(uuid "([0-9a-f-]{36})"\).*?\(property "Reference" "(J\d+)"', old, re.S):
            sym_uuids[m.group(2)] = m.group(1)
    txt = sheet_file(root_uuid, sheet_uuid, sym_uuids)
    assert txt.count('(') == txt.count(')'), "paren imbalance in sheet"
    open(path, 'w').write(txt)
    print("wrote core_interface.kicad_sch  (sheet uuid %s, root %s)" % (sheet_uuid, root_uuid))


def print_table():
    print("\nLGA pin table (top view of the Base land pattern):")
    for n, pname, kind, x, y in PINS:
        print(f"  {n:2d}  {pname:12s} {kind:3s}  x={x:+7.3f} y={y:+7.3f}")


if __name__ == "__main__":
    if "--from-base" in sys.argv:
        origin, pins = read_markers_from_base()
        rewrite_pins(origin, pins)
        ORIGIN, PINS = origin, pins
    if not PINS:
        sys.exit("PINS is empty: run  tools/lga_gen.py --from-base  with the marker test points on OpenAIO-Base")
    write_footprints()
    splice_symbol()
    write_sheet("--sheet" in sys.argv)
    print_table()
