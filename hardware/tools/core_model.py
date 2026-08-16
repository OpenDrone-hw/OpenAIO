#!/usr/bin/env python3
"""Export the Core as a 3D model for J90 on the Base, so the Base's 3D view
shows the hat stacked at its true position (fit check against the FETs, the
SD card and the USB connector). Plain python3 + kicad-cli, no pcbnew.

Writes, origin at the centre of J91 (Core_LGA_pads):
  export/OpenAIO-Core.wrl   what J90's 3D model points at; the VRML exporter
                            embeds every part, also the .wrl-only ones
  export/OpenAIO-Core.step  same in STEP for the Base STEP export
                            (--subst-models swaps it in for the .wrl)
Both share offset 0: the STEP body starts at z=0 (bottom face), the VRML
exporter centres the board on z=0, so the VRML gets wrapped in a Transform
raising it by half the board thickness. J90's model origin sits on the Base
top face, so the Core's LGA lands on J90 with zero offset.

Run from hardware/ after changing the Core layout:  python3 tools/core_model.py
KiCad may stay open; reopen the Base 3D viewer to see the new model.
"""
import os
import re
import subprocess
import sys

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(HW, "OpenAIO-Core.kicad_pcb")
OUT = os.path.join(HW, "export")
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
if not os.path.exists(KICAD_CLI):
    KICAD_CLI = "kicad-cli"


def j91_origin(pcb_text):
    """(x, y) mm of the Core_LGA_pads footprint and the board thickness."""
    m = re.search(r'\(footprint "lib:Core_LGA_pads"(?:(?!\(footprint ).)*?\(at ([-\d.]+) ([-\d.]+)', pcb_text, re.S)
    if not m:
        sys.exit("no lib:Core_LGA_pads (J91) in OpenAIO-Core.kicad_pcb")
    t = re.search(r'\(general\s*\(thickness ([\d.]+)\)', pcb_text)
    return float(m.group(1)), float(m.group(2)), float(t.group(1))


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    noise = ("assert", "Fontconfig", "Debug:")
    err = "\n".join(l for l in r.stderr.splitlines() if not any(n in l for n in noise))
    return r.returncode, err


def main():
    os.makedirs(OUT, exist_ok=True)
    x, y, thick = j91_origin(open(CORE).read())
    origin = f"{x}x{y}mm"
    wrl = os.path.join(OUT, "OpenAIO-Core.wrl")
    step = os.path.join(OUT, "OpenAIO-Core.step")

    rc, err = run([KICAD_CLI, "pcb", "export", "vrml", "--units", "tenths", "--user-origin", origin,
                   "--no-dnp", "--force", "-o", wrl, CORE])
    if rc or not os.path.exists(wrl):
        sys.exit(f"VRML export failed: {err[-400:]}")
    head, body = open(wrl).read().split("\n", 1)
    dz = thick / 2 / 2.54   # tenths of an inch
    open(wrl, "w").write(f"{head}\nTransform {{ translation 0 0 {dz:.6f} children [\n{body}\n] }}\n")
    print(f"export/OpenAIO-Core.wrl  origin J91 ({x}, {y}), board {thick} mm, {os.path.getsize(wrl) // 1024} kB")

    rc, err = run([KICAD_CLI, "pcb", "export", "step", "--user-origin", origin, "--no-dnp", "--subst-models",
                   "--force", "-o", step, CORE])
    skipped = err.count("Cannot use VRML")
    if not os.path.exists(step):
        sys.exit(f"STEP export failed: {err[-400:]}")
    print(f"export/OpenAIO-Core.step ({skipped} .wrl-only parts not in the STEP, they are in the .wrl)")


if __name__ == "__main__":
    main()
