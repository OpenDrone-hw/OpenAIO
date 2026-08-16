#!/usr/bin/env python3
"""One-shot: put the core_interface sheet on the OpenAIO root and tie the
LGA nets to the existing nets with GLOBAL labels. Idempotent (skips if the
sheet is already on the root).

Root edits (OpenAIO.kicad_sch):
  - sheet block "Core_Interface" -> core_interface.kicad_sch (no sheet pins,
    every interface net is a global label)
  - a global label at each root sheet pin that carries an interface net
    (RP2354A sheet pins), same text as inside core_interface.kicad_sch
  - the stray hierarchical label "CURR" on the root (U25 CSA output) becomes
    a global label "CURR", which also closes the open ESC-current link
fc_rp2350a.kicad_sch: global labels USB_D+/USB_D- on the USB1 D+/D- wires
(those nets never reached the root).
Run from hardware/ with KiCad closed:  python3 tools/lga_wire_root.py
"""
import os
import re
import uuid

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(HW, "OpenAIO.kicad_sch")
RP = os.path.join(HW, "fc_rp2350a.kicad_sch")
IFACE = os.path.join(HW, "core_interface.kicad_sch")

SHEET_AT = (33.655, 118.11)
SHEET_SZ = (40.64, 12.7)

BUS = "SPI0{SCK,MOSI,MISO}"
# (global label text, x, y, rot) at existing root sheet pins carrying the net
# Labels sit vertically on the short root wires between the sheets (right of
# RP2354A: x 145.415..149.86, left: 74.295..78.74). Up (rot 90) and down
# (rot 270) alternate, in two x lanes, so nothing overlaps.
XU, XD, XL = 146.4, 148.8, 76.5175
ROOT_LABELS = [
    ("10V_ENABLE", XL, 61.595, 270),
    ("CURR", XL, 56.515, 90),
    ("MOTOR1", XU, 93.98, 90),
    ("MOTOR2", XU, 107.95, 90),
    ("MOTOR3", XU, 121.92, 90),
    ("MOTOR4", XU, 135.89, 90),
    ("UART0_TX", XU, 46.355, 90),
    ("UART0_RX", XD, 48.895, 270),
    ("UART1_TX", XL, 110.49, 270),
    ("UART1_RX", XL, 107.95, 90),
    (BUS, XD, 62.865, 270),
    ("FLASH_CS", XU, 60.325, 90),
]
# global labels inside fc_rp2350a on the USB1 D+/D- wires
RP_LABELS = [("USB_D+", 252.73, 190.5, 0), ("USB_D-", 252.73, 187.96, 0)]


def u():
    return str(uuid.uuid4())


def glabel(text, x, y, rot, shape="bidirectional"):
    just = "right" if rot in (180, 270) else "left"
    return (f'\t(global_label "{text}"\n\t\t(shape {shape})\n\t\t(at {x} {y} {rot})\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n'
            f'\t\t(uuid "{u()}")\n\t)\n')


def sheet_block(root_uuid, sheet_uuid, page):
    x, y = SHEET_AT
    w, h = SHEET_SZ
    L = ['\t(sheet', f'\t\t(at {x} {y})', f'\t\t(size {w} {h})',
         '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)', '\t\t(dnp no)',
         '\t\t(fields_autoplaced yes)', '\t\t(stroke\n\t\t\t(width 0.1524)\n\t\t\t(type solid)\n\t\t)',
         '\t\t(fill\n\t\t\t(color 0 0 0 0)\n\t\t)', f'\t\t(uuid "{sheet_uuid}")']
    L.append(f'\t\t(property "Sheetname" "Core_Interface"\n\t\t\t(at {x} {y - 0.7116} 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
             '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left bottom)\n\t\t\t)\n\t\t)')
    L.append(f'\t\t(property "Sheetfile" "core_interface.kicad_sch"\n\t\t\t(at {x} {y + h + 0.5846} 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
             '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left top)\n\t\t\t)\n\t\t)')
    L.append(f'\t\t(instances\n\t\t\t(project "OpenAIO"\n\t\t\t\t(path "/{root_uuid}"\n\t\t\t\t\t(page "{page}")\n'
             '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
    return "\n".join(L) + "\n"


def main():
    root = open(ROOT).read()
    if 'core_interface.kicad_sch' in root:
        print("root already has the Core_Interface sheet, nothing done")
        return
    iface = open(IFACE).read()
    sheet_uuid = re.search(r'\(uuid "([0-9a-f-]{36})"', iface).group(1)
    root_uuid = re.search(r'\(path "/([0-9a-f-]{36})"', root).group(1)
    page = max(int(p) for p in re.findall(r'\(page "(\d+)"\)', root)) + 1

    # stray hierarchical label CURR on the root -> global label
    n = root.count('\t(hierarchical_label "CURR"\n')
    assert n == 1, f"expected one root hierarchical label CURR, found {n}"
    root = root.replace('\t(hierarchical_label "CURR"\n\t\t(shape input)', '\t(global_label "CURR"\n\t\t(shape bidirectional)')

    ins = root.index('\t(sheet_instances')
    blk = sheet_block(root_uuid, sheet_uuid, page)
    for text, x, y, rot in ROOT_LABELS:
        blk += glabel(text, x, y, rot)
    root = root[:ins] + blk + root[ins:]
    assert root.count('(') == root.count(')'), "root paren imbalance"

    rp = open(RP).read()
    ins = rp.index('\t(sheet_instances') if '\t(sheet_instances' in rp else rp.rstrip().rfind(')')
    add = "".join(glabel(*a) for a in RP_LABELS)
    rp = rp[:ins] + add + rp[ins:]
    assert rp.count('(') == rp.count(')'), "rp paren imbalance"

    open(ROOT, 'w').write(root)
    open(RP, 'w').write(rp)
    print(f"root: Core_Interface sheet (page {page}), {len(ROOT_LABELS)} global labels, CURR hier->global; fc_rp2350a: USB_D+/USB_D-")


if __name__ == "__main__":
    main()
