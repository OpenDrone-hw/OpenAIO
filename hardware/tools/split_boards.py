#!/usr/bin/env python3
"""Derive the two shippable boards from the OpenAIO master PCB.

The master OpenAIO.kicad_pcb holds both boards side by side (Base island on
the left with J90 Core_LGA_land, Core island on the right with J91
Core_LGA_pads). Everything is routed there. This script never touches the
master's copper; it writes:

  export/OpenAIO-Base.kicad_pcb  (+ .kicad_pro/.kicad_dru copies)   Base island only
  export/OpenAIO-Core.kicad_pcb  (+ .kicad_pro/.kicad_dru copies)   Core island only,
                              aux (drill) origin at the LGA centre = J91,
                              board thickness CORE_THICKNESS_MM
  export/OpenAIO-Core.wrl        Core VRML (all models, incl. the .wrl-only
                              ones), origin at the LGA centre: the 3D model of
                              J90 in the master (--update-master)
  export/OpenAIO-Core.step       same in STEP (VRML-only parts missing); the
                              master's STEP export picks it up via --subst-models
  export/*-drc.json              DRC of each derived board (--drc)

Items go to the island whose side of SPLIT_X they lie on; SPLIT_X is the
midpoint between J90 and J91. Anything spanning the gap is reported and
dropped.

--update-master   also gives J90 in the master the Core VRML as 3D model
                  (offset so the Core sits pad on pad on the Base) and draws
                  the Core outline on J90's User.Comments layer.
Run with KiCad's Python, KiCad closed:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 tools/split_boards.py [--drc] [--update-master]
"""
import os
import re
import shutil
import subprocess
import sys

import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(HW, "OpenAIO.kicad_pcb")
FAB = os.path.join(HW, "export")
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
LAND, PADS = "J90", "J91"
CORE_THICKNESS_MM = 0.8   # thinnest JLCPCB 6-layer (the Core inherits the master layer count); order it at this thickness


def mm(v):
    return v / 1e6


def item_x(it):
    if isinstance(it, pcbnew.FOOTPRINT):
        return it.GetPosition().x          # not the bbox: stray text fields inflate it
    if isinstance(it, pcbnew.PCB_TRACK):
        return (it.GetStart().x + it.GetEnd().x) / 2
    return it.GetBoundingBox().GetCenter().x


def spans(it, split):
    if isinstance(it, pcbnew.PCB_TRACK):
        return (it.GetStart().x < split) != (it.GetEnd().x < split)
    if isinstance(it, (pcbnew.FOOTPRINT, pcbnew.PCB_TEXT)):
        return False
    bb = it.GetBoundingBox()
    return bb.GetLeft() < split < bb.GetRight()


def load():
    b = pcbnew.LoadBoard(MASTER)
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    assert LAND in fps and PADS in fps, f"{LAND}/{PADS} not on the master board (run tools/lga_place.py, then Update PCB from Schematic)"
    split = (fps[LAND].GetPosition().x + fps[PADS].GetPosition().x) // 2
    return b, fps, split


def set_thickness(b, total_mm):
    """Board thickness for the STEP export. KiCad builds the body from the
    stackup, whose descriptor is not reachable from Python, so the general
    thickness is set here and the dielectric layers of the stackup are scaled
    in the written file by fix_stackup()."""
    b.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(total_mm))


def fix_stackup(path, total_mm):
    """Scale every dielectric thickness in the (stackup ...) block of a derived
    board file so copper + dielectric = total_mm. Generated file, text edit is fine."""
    s = open(path).read()
    a = s.find("(stackup")
    if a < 0:
        return
    d = 0
    e = a
    while True:
        c = s[e]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                e += 1
                break
        e += 1
    blk = s[a:e]
    layers = re.findall(r'\(layer "([^"]+)"(.*?)\n\t\t\t\)', blk, re.S)
    cu = sum(float(m) for name, body in layers if name.endswith(".Cu")
             for m in re.findall(r"\(thickness ([0-9.]+)\)", body))
    ndiel = sum(len(re.findall(r"\(thickness ([0-9.]+)", body)) for name, body in layers if name.startswith("dielectric"))
    if not ndiel:
        return
    each = (total_mm - cu) / ndiel

    def sub(m):
        name, body = m.group(1), m.group(2)
        if name.startswith("dielectric"):
            body = re.sub(r"\(thickness [0-9.]+", f"(thickness {each:.4f}", body)
        return f'(layer "{name}"{body}\n\t\t\t)'
    blk2 = re.sub(r'\(layer "([^"]+)"(.*?)\n\t\t\t\)', sub, blk, flags=re.S)
    open(path, "w").write(s[:a] + blk2 + s[e:])


def derive(keep_left, name):
    """Reload the master and delete everything on the other side."""
    b, fps, split = load()
    dropped, spanning = 0, []
    items = list(b.GetFootprints()) + list(b.GetTracks()) + list(b.Zones()) + list(b.GetDrawings())
    for it in items:
        if spans(it, split):
            spanning.append(f"{type(it).__name__} at x={mm(item_x(it)):.1f}")
        keep = (item_x(it) < split) == keep_left
        if not keep:
            b.Delete(it)
            dropped += 1
    if spanning:
        print(f"  {name}: {len(spanning)} item(s) span the split and were dropped: {spanning[:5]}")
    if not keep_left:
        # aux origin at the LGA centre so STEP/gerber origins are the mating point
        j = {f.GetReference(): f for f in b.GetFootprints()}[PADS]
        b.GetDesignSettings().SetAuxOrigin(j.GetPosition())
        set_thickness(b, CORE_THICKNESS_MM)
        # Core outline relative to the LGA centre, for the shadow on J90
        bb = None
        for d in b.GetDrawings():
            if d.GetLayer() == pcbnew.Edge_Cuts:
                r = d.GetBoundingBox()
                if bb is None:
                    bb = pcbnew.BOX2I(r.GetPosition(), r.GetSize())
                else:
                    bb.Merge(r)
        import json
        o = j.GetPosition()
        json.dump(None if bb is None else dict(left=mm(bb.GetLeft() - o.x), top=mm(bb.GetTop() - o.y),
                                                right=mm(bb.GetRight() - o.x), bottom=mm(bb.GetBottom() - o.y)),
                  open(os.path.join(FAB, "OpenAIO-Core-outline.json"), "w"))
    out = os.path.join(FAB, name + ".kicad_pcb")
    b.SetFileName(out)
    pcbnew.SaveBoard(out, b)
    if not keep_left:
        fix_stackup(out, CORE_THICKNESS_MM)
    print(f"  wrote export/{name}.kicad_pcb  ({len(list(b.GetFootprints()))} footprints, {dropped} items dropped)")
    return out


def sidecars(name):
    for ext in (".kicad_pro", ".kicad_dru"):
        src = os.path.join(HW, "OpenAIO" + ext)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(FAB, name + ext))


def export_step(core_pcb):
    out = os.path.join(FAB, "OpenAIO-Core.step")
    r = subprocess.run([KICAD_CLI, "pcb", "export", "step", "--drill-origin", "--no-dnp", "--subst-models",
                        "--force", "-o", out, core_pcb], capture_output=True, text=True)
    ok = os.path.exists(out) and r.returncode == 0
    if not ok:  # kicad-cli exits non-zero for skipped .wrl models but still writes the STEP
        ok = os.path.exists(out) and "Export time" in (r.stdout + r.stderr) or "Cannot use VRML" in r.stderr
    wrl = r.stderr.count("Cannot use VRML")
    print(f"  Core STEP {'ok' if ok else 'FAILED: ' + r.stderr.strip()[-300:]}: export/OpenAIO-Core.step"
          + (f"  ({wrl} .wrl-only models skipped, STEP export cannot use VRML)" if wrl else ""))
    return out if ok else None


def export_vrml(core_pcb):
    """VRML of the Core with KiCad's own exporter: unlike STEP it embeds every
    model, VRML or STEP. Units 'tenths' (0.1 in) is the footprint-model VRML
    convention, so scale 1 in J90. KiCad centres the VRML board on z=0
    (thickness field), while the STEP body starts at z=0; the whole file is
    wrapped in a Transform raising it by thickness/2 so both files share
    offset 0 and --subst-models stays consistent."""
    out = os.path.join(FAB, "OpenAIO-Core.wrl")
    b = pcbnew.LoadBoard(core_pcb)
    o = b.GetDesignSettings().GetAuxOrigin()
    origin = f"{pcbnew.ToMM(o.x)}x{pcbnew.ToMM(o.y)}mm"
    r = subprocess.run([KICAD_CLI, "pcb", "export", "vrml", "--units", "tenths", "--user-origin", origin,
                        "--no-dnp", "--force", "-o", out, core_pcb], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        print(f"  Core VRML FAILED: {r.stderr.strip()[-300:]}")
        return None
    t = open(out).read()
    head, body = t.split("\n", 1)          # keep the '#VRML V2.0 utf8' line first
    dz = CORE_THICKNESS_MM / 2 / 2.54
    open(out, "w").write(f"{head}\nTransform {{ translation 0 0 {dz:.6f} children [\n{body}\n] }}\n")
    print(f"  Core VRML ok: export/OpenAIO-Core.wrl ({os.path.getsize(out) // 1024} kB, all models)")
    return out


def drc(pcb):
    out = pcb.replace(".kicad_pcb", "-drc.json")
    subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-error", "--refill-zones",
                    "-o", out, pcb], capture_output=True, text=True)
    import json
    d = json.load(open(out))
    n = len(d.get("violations", [])) + len(d.get("unconnected_items", []))
    from collections import Counter
    c = Counter(v["type"] for v in d.get("violations", []))
    print(f"  DRC {os.path.basename(pcb)}: {len(d.get('violations', []))} violations, {len(d.get('unconnected_items', []))} unconnected  {dict(c)}")
    return out


def update_master(step_path, core_pcb):
    """J90 in the master gets the Core VRML (STEP alongside) + the outline shadow."""
    b, fps, split = load()
    j90, j91 = fps[LAND], fps[PADS]
    # 3D model: origin = J91 centre (drill origin), body from z=0 (bottom face)
    # up, y up (STEP verified with a PLY export, VRML shifted to match in
    # export_vrml). A footprint model's origin sits on the Base top face, so
    # the Core's bottom pads land on the Base pads with zero offset. The .wrl
    # is what the 3D viewer shows; a STEP export of the master with
    # --subst-models swaps in OpenAIO-Core.step.
    j90.Models().clear() if hasattr(j90.Models(), 'clear') else None
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = "${KIPRJMOD}/export/OpenAIO-Core.wrl"
    m.m_Offset = pcbnew.VECTOR3D(0, 0, 0)
    m.m_Show = True
    j90.Models().push_back(m)
    # shadow: Core outline (from Core Edge.Cuts) relative to J91, drawn on J90's User.Comments
    import json
    bb = json.load(open(os.path.join(FAB, "OpenAIO-Core-outline.json")))
    for g in list(j90.GraphicalItems()):
        if g.GetLayer() == pcbnew.Cmts_User:
            j90.Remove(g)
    if bb is not None:
        r = pcbnew.PCB_SHAPE(j90, pcbnew.SHAPE_T_RECT)
        r.SetLayer(pcbnew.Cmts_User)
        r.SetWidth(pcbnew.FromMM(0.1))
        o = j90.GetPosition()
        r.SetStart(pcbnew.VECTOR2I(o.x + pcbnew.FromMM(bb["left"]), o.y + pcbnew.FromMM(bb["top"])))
        r.SetEnd(pcbnew.VECTOR2I(o.x + pcbnew.FromMM(bb["right"]), o.y + pcbnew.FromMM(bb["bottom"])))
        j90.Add(r)
        print(f"  master: J90 shadow {bb['right'] - bb['left']:.1f} x {bb['bottom'] - bb['top']:.1f} mm on User.Comments")
    else:
        print("  master: Core has no Edge.Cuts yet, no shadow drawn")
    pcbnew.SaveBoard(MASTER, b)
    print("  master: J90 3D model = export/OpenAIO-Core.wrl (STEP alongside for --subst-models)")


def main():
    # pcbnew only tolerates one LoadBoard per process, so every board-touching
    # phase runs in a child process of this same script.
    if "--phase" in sys.argv:
        ph = sys.argv[sys.argv.index("--phase") + 1]
        if ph == "base":
            derive(True, "OpenAIO-Base")
        elif ph == "core":
            derive(False, "OpenAIO-Core")
        elif ph == "master":
            update_master(os.path.join(FAB, "OpenAIO-Core.step"), os.path.join(FAB, "OpenAIO-Core.kicad_pcb"))
        return
    os.makedirs(FAB, exist_ok=True)
    # ${KIPRJMOD} of a derived board is export/, so the project 3D models must
    # be reachable there for the STEP export
    link = os.path.join(FAB, "lib.3dshapes")
    if not os.path.lexists(link):
        os.symlink(os.path.join("..", "lib.3dshapes"), link)
    print("split master into export/OpenAIO-Base and export/OpenAIO-Core")

    def child(ph):
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--phase", ph], capture_output=True, text=True)
        out = [l for l in (r.stdout + r.stderr).splitlines() if not re.search(r"assert|Debug:|memory leak|Fontconfig", l)]
        print("\n".join(out))
        if r.returncode != 0:
            sys.exit(f"phase {ph} failed")

    child("base")
    child("core")
    base = os.path.join(FAB, "OpenAIO-Base.kicad_pcb")
    core = os.path.join(FAB, "OpenAIO-Core.kicad_pcb")
    sidecars("OpenAIO-Base")
    sidecars("OpenAIO-Core")
    step = export_step(core)
    export_vrml(core)
    if "--drc" in sys.argv:
        drc(base)
        drc(core)
    if "--update-master" in sys.argv and step:
        child("master")


if __name__ == "__main__":
    main()
