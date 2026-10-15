"""Widen tracks to a target width per net class, as far as the copper around them allows.

Run with KiCad closed, using KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/track_widen.py hardware/<board>.kicad_pcb [--dry-run]

Each track segment gets the widest width on the ladder 0.10 / 0.15 / 0.20 / 0.25 / 0.30 / 0.40 / 0.50, from its
class target down to above its present width, at which it clears every other-net track, via, pad and hole on its layer by the copper clearance (0.15 next to
RF), stays 0.20 inside the board edge and stays out of rule areas that forbid tracks. A track is never made
narrower. USB, RF and the BEMF sense lines of the phase nets keep their widths (impedance and sense, not
current). The board is saved; run DRC after it, then track_widen.py --revert drc.json reverts every widened
track named in an error to the width it had before (kept in the system temp folder as track_widen.json).
"""
import json
import os
import sys
import tempfile


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
MM = pcbnew.FromMM
CLEAR, RF_CLEAR, EDGE, HOLE = MM(0.09), MM(0.15), MM(0.20), MM(0.18)
LADDER = [MM(w) for w in (0.50, 0.40, 0.30, 0.25, 0.20, 0.15, 0.10)]
LOG = os.path.join(tempfile.gettempdir(), "track_widen.json")

# Target width per net class; a net name listed in NETS wins over its class.
CLASSES = {"VBAT": 0.5, "Power": 0.3, "GND": 0.3, "Gate": 0.2, "Default": 0.1, "Analog": 0.1}
NETS = {"+5V_BST": 0.4, "+5V": 0.4, "/VBUS": 0.4, "/POWER/U2_SW": 0.4}
KEEP = ("USB", "RF", "Phase")


def target(t):
    if t.GetNetname() in NETS:
        return MM(NETS[t.GetNetname()])
    cls = t.GetNetClassName()
    if cls in KEEP or cls not in CLASSES:
        return None
    return MM(CLASSES[cls])


def key(t):
    s, e = t.GetStart(), t.GetEnd()
    return f"{t.GetNetname()}|{t.GetLayer()}|{s.x},{s.y}|{e.x},{e.y}"


def widen(path, dry):
    board = pcbnew.LoadBoard(path)
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    edges = [d.GetEffectiveShape(pcbnew.Edge_Cuts) for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    keepouts = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
    by_layer = {}
    for o in tracks + vias + pads:
        for layer in o.GetLayerSet().CuStack():
            by_layer.setdefault(layer, []).append(o)

    def fits(t, w):
        layer = t.GetLayer()
        seg = pcbnew.SHAPE_SEGMENT(t.GetStart(), t.GetEnd(), w)
        box = t.GetBoundingBox()
        box.Inflate(w + RF_CLEAR)
        for o in by_layer.get(layer, []):
            if o is t or o.GetNetCode() == t.GetNetCode() or not box.Intersects(o.GetBoundingBox()):
                continue
            gap = RF_CLEAR if "RF" in (o.GetNetClassName(), t.GetNetClassName()) else CLEAR
            if o.GetEffectiveShape(layer).Collide(seg, gap):
                return False
            if o.GetClass() in ("PCB_VIA", "PAD") and o.HasHole() and o.GetEffectiveHoleShape().Collide(seg, HOLE):
                return False
        if any(e.Collide(seg, EDGE) for e in edges):
            return False
        for z in keepouts:
            if z.IsOnLayer(layer) and z.Outline().Collide(seg):
                return False
        return True

    log, n, gained = {}, 0, 0.0
    for t in tracks:
        goal = target(t)
        w0 = t.GetWidth()
        if goal is None or goal <= w0:
            continue
        w = next((w for w in LADDER if w0 < w <= goal and fits(t, w)), w0)
        if w > w0:
            log[key(t)] = w0
            t.SetWidth(w)
            n += 1
            gained += pcbnew.ToMM(w - w0) * pcbnew.ToMM(t.GetLength())
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    print(f"{n} segments widened, {gained:.1f} mm2 of copper added")
    if not dry:
        json.dump(log, open(LOG, "w"))
        pcbnew.SaveBoard(path, board)
        print("saved")


def revert(path, report):
    board = pcbnew.LoadBoard(path)
    log = json.load(open(LOG))
    drc = json.load(open(report))
    hits = set()
    for x in drc["violations"]:
        if x["severity"] != "error":
            continue
        for it in x["items"]:
            hits.add((round(it["pos"]["x"], 3), round(it["pos"]["y"], 3)))
    n = 0
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or key(t) not in log:
            continue
        box = t.GetBoundingBox()
        if any(box.Contains(pcbnew.VECTOR2I(MM(x), MM(y))) for x, y in hits):
            t.SetWidth(log.pop(key(t)))
            n += 1
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    json.dump(log, open(LOG, "w"))
    pcbnew.SaveBoard(path, board)
    print(f"{n} segments reverted")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--revert" in a:
        revert(a[0], a[a.index("--revert") + 1])
    else:
        widen(a[0], "--dry-run" in a)
