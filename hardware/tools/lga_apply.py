#!/usr/bin/env python3
"""Put the generated LGA footprints on the boards. Run after tools/lga_gen.py
(--from-base) with KiCad's Python and both board editors closed:

  KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
  $KPY tools/lga_apply.py

  Base  OpenAIO-Base.kicad_pcb : deletes the marker test points (TP10 and up)
        and any old J90, places lib:Core_LGA_land as J90 at ORIGIN, pad nets
        from the pin table
  Core  OpenAIO-Core.kicad_pcb : replaces J91 (lib:Core_LGA_pads, B.Cu) at its
        current position, pad nets from the pin table
  Schematic: the marker test points get "exclude from board" (they stay as the
        record of which net crosses where, the plugin skips them); nets that
        were local labels get the matching global label on the root
        (ROOT_GLOBALS below, positions on the root wires)
Then:  multiboard update.py .   and   python3 tools/core_model.py
"""
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lga_gen  # noqa: E402

BASE = os.path.join(HW, "OpenAIO-Base.kicad_pcb")
CORE = os.path.join(HW, "OpenAIO-Core.kicad_pcb")
IFACE = os.path.join(HW, "core_interface.kicad_sch")
ROOT = os.path.join(HW, "OpenAIO.kicad_sch")
PRETTY = os.path.join(HW, "lib.pretty")
# global label to add on the root wire, for interface nets that were local labels
ROOT_GLOBALS = [("LED_STRIP", 160.02, 24.13)]   # root wire RP2354A LED_STRIP -> Pads LED_STRIP, TP15 sat on it


def sym_paths():
    """/sheet uuid/symbol uuid for J90 and J91 from core_interface.kicad_sch."""
    t = open(IFACE).read()
    sheet = re.search(r'\(uuid "([0-9a-f-]{36})"', t).group(1)
    out = {}
    for m in re.finditer(r'\(symbol\n\t\t\(lib_id "lib:Core_LGA"\).*?\(uuid "([0-9a-f-]{36})"\).*?\(property "Reference" "(J\d+)"', t, re.S):
        out[m.group(2)] = f"/{sheet}/{m.group(1)}"
    return out


def place(board, name, ref, pos, flip, path):
    fp = pcbnew.FootprintLoad(PRETTY, name)
    if fp is None:
        sys.exit(f"lib.pretty has no {name}, run tools/lga_gen.py first")
    fp.SetReference(ref)
    fp.SetValue("Core_LGA")
    board.Add(fp)              # Add before Flip: pcbnew segfaults the other way round
    if flip:
        fp.Flip(fp.GetPosition(), False)
    fp.SetPosition(pos)
    fp.SetPath(pcbnew.KIID_PATH(path))
    for pad in fp.Pads():
        n = int(pad.GetNumber())
        net = board.FindNet(lga_gen.pad_name(n))
        if net:
            pad.SetNet(net)
    return fp


def do_base(paths):
    b = pcbnew.LoadBoard(BASE)
    gone = []
    for f in list(b.GetFootprints()):
        r = f.GetReference()
        m = re.fullmatch(r"TP(\d+)", r)
        if (m and int(m.group(1)) >= lga_gen.MARKER_MIN) or f.GetFPID().GetLibItemName() == "Core_LGA_land":
            gone.append(r)
            b.Delete(f)
    ox, oy = lga_gen.ORIGIN
    place(b, "Core_LGA_land", "J90", pcbnew.VECTOR2I(pcbnew.FromMM(ox), pcbnew.FromMM(oy)), False, paths["J90"])
    pcbnew.SaveBoard(BASE, b)
    print(f"Base: removed {len(gone)} ({', '.join(sorted(gone))}), J90 at ({ox}, {oy})")


def do_core(paths):
    c = pcbnew.LoadBoard(CORE)
    old = [f for f in c.GetFootprints() if f.GetReference() == "J91" or f.GetFPID().GetLibItemName() == "Core_LGA_pads"]
    if old:
        pos = old[0].GetPosition()
        for f in old:
            c.Delete(f)
    else:
        pos = c.GetDesignSettings().GetAuxOrigin()
    place(c, "Core_LGA_pads", "J91", pos, True, paths["J91"])
    c.GetDesignSettings().SetAuxOrigin(pos)
    pcbnew.SaveBoard(CORE, c)
    print(f"Core: J91 at ({pcbnew.ToMM(pos.x)}, {pcbnew.ToMM(pos.y)}) on B.Cu, aux origin there")


def block_end(s, i):
    d = 0
    j = i
    while True:
        if s[j] == '(':
            d += 1
        elif s[j] == ')':
            d -= 1
            if d == 0:
                return j + 1
        j += 1


def markers_off_board():
    """Marker test point symbols: on_board no, in_bom no, in every sheet."""
    n = 0
    for fn in sorted(os.listdir(HW)):
        if not fn.endswith(".kicad_sch") or os.path.islink(os.path.join(HW, fn)):
            continue
        p = os.path.join(HW, fn)
        s = open(p).read()
        out, i, changed = [], 0, 0
        while True:
            j = s.find("\n\t(symbol\n", i)
            if j < 0:
                out.append(s[i:])
                break
            j += 1
            k = block_end(s, j)
            blk = s[j:k]
            m = re.search(r'\(property "Reference" "TP(\d+)"', blk)
            if m and int(m.group(1)) >= lga_gen.MARKER_MIN and "(on_board yes)" in blk:
                blk = blk.replace("(on_board yes)", "(on_board no)").replace("(in_bom yes)", "(in_bom no)")
                changed += 1
            out.append(s[i:j])
            out.append(blk)
            i = k
        if changed:
            t = "".join(out)
            assert t.count('(') == t.count(')'), fn
            open(p, "w").write(t)
            print(f"{fn}: {changed} marker test points set exclude from board")
            n += changed
    return n


def root_globals():
    s = open(ROOT).read()
    add = ""
    for text, x, y in ROOT_GLOBALS:
        if f'(global_label "{text}"' in s:
            continue
        add += (f'\t(global_label "{text}"\n\t\t(shape bidirectional)\n\t\t(at {x} {y} 0)\n'
                f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left)\n\t\t)\n'
                f'\t\t(uuid "{lga_gen.u()}")\n\t)\n')
        print(f"root: global label {text} at ({x}, {y})")
    if add:
        i = s.index('\t(sheet_instances')
        s = s[:i] + add + s[i:]
        assert s.count('(') == s.count(')')
        open(ROOT, "w").write(s)


def main():
    if not lga_gen.PINS:
        sys.exit("empty pin table, run tools/lga_gen.py --from-base first")
    for f in (BASE, CORE):
        if os.path.exists(os.path.join(HW, "~" + os.path.basename(f) + ".lck")):
            sys.exit(f"{os.path.basename(f)} is open in KiCad, close it")
    paths = sym_paths()
    root_globals()
    markers_off_board()
    do_base(paths)
    do_core(paths)


if __name__ == "__main__":
    main()
