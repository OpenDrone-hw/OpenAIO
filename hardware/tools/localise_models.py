"""Make every 3D model of the board and of lib.pretty project-local: ${KIPRJMOD}/lib.3dshapes/<file>.

Run with KiCad closed, using KiCad's bundled Python:
  $KPY hardware/tools/localise_models.py hardware/OpenAIO.kicad_pcb [--prune] [--dry-run]

Each model path is resolved through ${KIPRJMOD}, KiCad's stock ${KICAD*_3DMODEL_DIR} and ${OPENDRONE_LIB}
(taken as the repo's KiCad-Library submodule, whatever the machine's KiCad settings say). A .wrl whose .step
sibling exists becomes the .step. The file is copied into lib.3dshapes and the path rewritten, on the board's
footprints and in lib.pretty. Only model paths change: no footprint, pad, track or position. A model that
resolves nowhere is listed and left as it is. --prune also deletes lib.pretty footprints the board does not
use and lib.3dshapes files nothing references.
"""
import glob
import os
import re
import shutil
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
STOCK = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels"


def main():
    args = sys.argv[1:]
    path = os.path.abspath([a for a in args if not a.startswith("--")][0])
    dry, prune = "--dry-run" in args, "--prune" in args
    hw = os.path.dirname(path)
    shapes = os.path.join(hw, "lib.3dshapes")
    roots = {"${KIPRJMOD}": hw, "${OPENDRONE_LIB}": os.path.join(hw, "KiCad-Library")}
    for v in ("10", "9", "8", "7"):
        roots["${KICAD%s_3DMODEL_DIR}" % v] = os.environ.get("KICAD%s_3DMODEL_DIR" % v, STOCK)

    def resolve(p):
        for k, v in roots.items():
            p = p.replace(k, v)
        if p.endswith(".wrl") and os.path.exists(p[:-4] + ".step"):
            p = p[:-4] + ".step"
        return p if os.path.exists(p) else None

    copied, missing = set(), {}

    def localise(old, where):
        if old.startswith("${KIPRJMOD}/lib.3dshapes/") and resolve(old):
            return "${KIPRJMOD}/lib.3dshapes/" + os.path.basename(resolve(old))
        src = resolve(old)
        if not src:
            missing.setdefault(old, []).append(where)
            return old
        name = os.path.basename(src)
        dst = os.path.join(shapes, name)
        if not os.path.exists(dst):
            copied.add(name)
            if not dry:
                shutil.copy(src, dst)
        return "${KIPRJMOD}/lib.3dshapes/" + name

    board = pcbnew.LoadBoard(path)
    changed = 0
    for fp in board.GetFootprints():
        models = fp.Models()  # index access: iterating the list yields copies, and edits to them are lost
        for i in range(len(models)):
            new = localise(models[i].m_Filename, fp.GetReference())
            if new != models[i].m_Filename:
                models[i].m_Filename = new
                changed += 1
    used_fp = {str(fp.GetFPID().GetLibItemName()) for fp in board.GetFootprints()}

    lib_changed = 0
    for f in sorted(glob.glob(os.path.join(hw, "lib.pretty", "*.kicad_mod"))):
        text = open(f).read()
        new = re.sub(r'\(model "([^"]+)"', lambda m: '(model "%s"' % localise(m.group(1), os.path.basename(f)), text)
        if new != text:
            lib_changed += 1
            if not dry:
                open(f, "w").write(new)

    print(f"board: {changed} model paths rewritten; lib.pretty: {lib_changed} footprints rewritten; {len(copied)} files copied")
    for old, where in sorted(missing.items()):
        print(f"MISSING {old}: {', '.join(sorted(set(where))[:8])}")
    if prune:
        for f in sorted(glob.glob(os.path.join(hw, "lib.pretty", "*.kicad_mod"))):
            if os.path.basename(f)[:-10] not in used_fp:
                print("prune footprint", os.path.basename(f))
                if not dry:
                    os.remove(f)
        refs = set()
        for f in glob.glob(os.path.join(hw, "lib.pretty", "*.kicad_mod")):
            if os.path.exists(f):
                refs |= {os.path.basename(m) for m in re.findall(r'\(model "([^"]+)"', open(f).read())}
        refs |= {os.path.basename(m.m_Filename) for fp in board.GetFootprints() for m in fp.Models()}
        for f in sorted(os.listdir(shapes)):
            if f not in refs and f not in copied and not f.startswith("."):
                print("prune model", f)
                if not dry:
                    os.remove(os.path.join(shapes, f))
    if not dry:
        pcbnew.SaveBoard(path, board)
        print("saved")


if __name__ == "__main__":
    main()
