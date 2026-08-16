#!/usr/bin/env python3
"""OpenAIO Base<->Core LGA interface generator.

One pin table produces every artefact of the board-to-board interface, so
they cannot drift:

  lib.pretty/Core_LGA_land.kicad_mod   F.Cu land pattern, goes on the Base island
  lib.pretty/Core_LGA_pads.kicad_mod   pads for the Core island, place it on B.Cu
                                       (its X is pre-mirrored so that after the
                                       flip pad k sits exactly over land pad k)
  lib.kicad_sym : symbol Core_LGA      one symbol, two instances in the schematic
  core_interface.kicad_sch             the interface sheet (only if missing, or
                                       with --sheet; it is a hand-editable file)

Run from hardware/:  python3 tools/lga_gen.py [--sheet]
Plain Python 3, no dependencies. Never edits OpenAIO.kicad_sch.
"""
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)

# ---------------------------------------------------------------- pin table
# (number, name, kind)   kind: PWR power net, SIG signal, BUS member of SPI0.
# Every interface net is a GLOBAL label: the interface is board-wide by nature.
# Row A = pins 1..16 (y = -ROW_GAP/2), row B = pins 17..32 (y = +ROW_GAP/2),
# pin 1 top-left, numbers increase left to right in each row (top view of the
# Base land pattern).
PITCH = 1.0        # mm, pad pitch inside a row
ROW_GAP = 12.0     # mm, distance between the two rows
PAD = 0.6          # mm, round pad diameter
NPR = 16           # pads per row

PINS = [
    (1, "GND", "PWR"),
    (2, "+BATT", "PWR"),
    (3, "GND", "PWR"),
    (4, "+5V", "PWR"),
    (5, "+5V", "PWR"),
    (6, "GND", "PWR"),
    (7, "+10V", "PWR"),
    (8, "+10V", "PWR"),
    (9, "GND", "PWR"),
    (10, "+3.3V", "PWR"),
    (11, "+3.3V", "PWR"),
    (12, "+4v5", "PWR"),
    (13, "GND", "PWR"),
    (14, "10V_ENABLE", "SIG"),
    (15, "CURR", "SIG"),
    (16, "GND", "PWR"),
    (17, "GND", "PWR"),
    (18, "USB_D+", "SIG"),
    (19, "USB_D-", "SIG"),
    (20, "GND", "PWR"),
    (21, "MOTOR1", "SIG"),
    (22, "MOTOR2", "SIG"),
    (23, "MOTOR3", "SIG"),
    (24, "MOTOR4", "SIG"),
    (25, "UART0_TX", "SIG"),
    (26, "UART0_RX", "SIG"),
    (27, "UART1_TX", "SIG"),
    (28, "UART1_RX", "SIG"),
    (29, "SPI0.SCK", "BUS"),
    (30, "SPI0.MOSI", "BUS"),
    (31, "SPI0.MISO", "BUS"),
    (32, "FLASH_CS", "SIG"),
]
BUS_LABEL = "SPI0{SCK,MOSI,MISO}"
assert len(PINS) == 2 * NPR and [p[0] for p in PINS] == list(range(1, 2 * NPR + 1))


def pad_xy(n):
    """Top-view position of pad n on the Base land pattern, footprint origin
    at the array centre."""
    row, col = divmod(n - 1, NPR)
    x = (col - (NPR - 1) / 2) * PITCH
    y = (row - 0.5) * ROW_GAP
    return round(x, 4), round(y, 4)


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
    half_w = (NPR - 1) / 2 * PITCH + PAD / 2 + 0.25
    half_h = ROW_GAP / 2 + PAD / 2 + 0.25

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
    for n, pname, kind in PINS:
        x, y = pad_xy(n)
        if mirror:
            x = -x
        lay = " ".join(f'"{l}"' for l in layers)
        L.append(f'\t(pad "{n}" smd circle (at {x:.4f} {y:.4f}) (size {PAD} {PAD})'
                 f' (layers {lay}) (uuid "{u()}"))')
    L.append('\t(embedded_fonts no)')
    L.append(')')
    return "\n".join(L) + "\n"


def write_footprints():
    d = os.path.join(HW, "lib.pretty")
    land = footprint("Core_LGA_land", False, ["F.Cu", "F.Mask", "F.Paste"], True,
                     "OpenAIO Core LGA land pattern on the Base, 2x16 pads, 1.0 mm pitch, 12 mm row gap, "
                     "0.6 mm pads, paste. Generated by tools/lga_gen.py")
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
SYM_H = (2 * NPR + 1) * SYM_PITCH   # body height


def symbol_block():
    """Symbol with all pins on the left, one per LGA pad. Reference J."""
    top = -((2 * NPR - 1) / 2) * SYM_PITCH  # y of pin 1
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
    prop("Description", "OpenAIO Base<->Core LGA interface, 32 pads. Two instances: J90 land (Base), J91 pads (Core). Pin table: tools/lga_gen.py", 0, 0, True)
    L.append(f'\t\t(symbol "{SYM}_0_1"')
    L.append(f'\t\t\t(rectangle (start 0 {top - 2.54}) (end 12.7 {top + (2 * NPR) * SYM_PITCH - 0.0})'
             ' (stroke (width 0.254) (type default)) (fill (type background)))')
    L.append('\t\t)')
    L.append(f'\t\t(symbol "{SYM}_1_1"')
    for n, pname, kind in PINS:
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

    top = -((2 * NPR - 1) / 2) * SYM_PITCH
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
        for n, _, _ in PINS:
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
        for n, pname, kind in PINS:
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
        bus_pins = [n for n, _, k in PINS if k == "BUS"]
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
    for n, pname, kind in PINS:
        x, y = pad_xy(n)
        print(f"  {n:2d}  {pname:12s} {kind:3s}  x={x:+6.2f} y={y:+6.2f}")


if __name__ == "__main__":
    write_footprints()
    splice_symbol()
    write_sheet("--sheet" in sys.argv)
    print_table()
