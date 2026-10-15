"""Remove redundant vias that DRC flags against other copper, without losing a connection.

Run with KiCad closed, using KiCad's bundled Python, on a DRC report made from the same board:
  kicad-cli pcb drc --format json -o drc.json hardware/<board>.kicad_pcb
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/via_declutter.py hardware/<board>.kicad_pcb drc.json [--dry-run]

Only three kinds of via are ever removed:
  - a GND via named in a short, clearance, hole-to-hole or hole-clearance error (stitching and exposed-pad
    arrays carry many; the error says this one sits on another net's copper);
  - the second of two same-net vias of one type closer than the hole spacing (a duplicate);
  - a via DRC reports as dangling (copper on one layer only, so it joins nothing).
Signal and power vias that clash with another net are listed for the owner, never moved or removed.
Each removal is kept only if the board's unconnected count does not rise; zones are refilled at the end and
the count is checked again. Errors that involve an item named with --skip REF (a part waiting to be moved)
are left alone.
"""
import json
import os
import re
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
TYPES = ("shorting_items", "clearance", "hole_to_hole", "hole_clearance")
KIND = {"Micro via": pcbnew.VIATYPE_MICROVIA, "Buried via": pcbnew.VIATYPE_BURIED, "Via": pcbnew.VIATYPE_THROUGH}


def unconnected(board):
    board.BuildConnectivity()
    return board.GetConnectivity().GetUnconnectedCount(True)


def find_via(vias, item):
    m = re.match(r"\s*(Micro via|Buried via|Via) \[(.*?)\]", item["description"])
    if not m:
        return None
    p = pcbnew.VECTOR2I(pcbnew.FromMM(item["pos"]["x"]), pcbnew.FromMM(item["pos"]["y"]))
    hits = [v for v in vias if v.GetNetname() == m.group(2) and v.GetViaType() == KIND[m.group(1)]
            and (v.GetPosition() - p).EuclideanNorm() < pcbnew.FromMM(0.005)]
    return hits[0] if hits else None


def main():
    args = sys.argv[1:]
    skip = [args[i + 1] for i, a in enumerate(args) if a == "--skip"]
    path, report = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--skip")][:2]
    dry = "--dry-run" in args
    board = pcbnew.LoadBoard(path)
    drc = json.load(open(report))
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    base = unconnected(board)
    gone, kept, owner = set(), 0, []
    for x in drc["violations"]:
        if x["type"] not in TYPES or x["severity"] != "error":
            continue
        if any(re.search(rf"\bof {re.escape(r)}\b", i["description"]) for r in skip for i in x["items"]):
            continue
        found = [find_via(vias, i) for i in x["items"]]
        if any(v is not None and id(v) in gone for v in found):
            continue
        a, b = (found + [None, None])[:2]
        pick = None
        if a is not None and b is not None and a.GetNetCode() == b.GetNetCode() and a.GetViaType() == b.GetViaType():
            pick = b
        else:
            pick = next((v for v in found if v is not None and v.GetNetname() == "GND"), None)
        if pick is None:
            owner.append(x)
            continue
        board.Remove(pick)
        now = unconnected(board)
        if now > base:
            board.Add(pick)
            kept += 1
            owner.append(x)
            continue
        gone.add(id(pick))
    dangling = 0
    for x in drc["violations"]:
        if x["type"] != "via_dangling":
            continue
        v = find_via(vias, x["items"][0])
        if v is None or id(v) in gone:
            continue
        board.Remove(v)
        if unconnected(board) > base:
            board.Add(v)
            kept += 1
            continue
        gone.add(id(v))
        dangling += 1
    print(f"{len(gone)} vias removed ({dangling} dangling), {kept} kept because removal broke a connection")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    after = unconnected(board)
    print(f"unconnected {base} -> {after}")
    # DRC repeats one clash per layer and per item pair; list each pair of nets once per spot.
    seen = set()
    for x in owner:
        p = x["items"][0]["pos"]
        nets = tuple(sorted(re.findall(r"\[(.*?)\]", " ".join(i["description"] for i in x["items"]))))
        key = (round(p["x"], 1), round(p["y"], 1), nets)
        if key in seen:
            continue
        seen.add(key)
        print(f"OWNER {p['x']:.2f},{p['y']:.2f} {x['type']}: " + " / ".join(re.sub(r", length .*", "", i["description"]) for i in x["items"]))
    if after > base:
        sys.exit("refill lost a connection; board not saved")
    if not dry:
        pcbnew.SaveBoard(path, board)
        print("saved")


if __name__ == "__main__":
    main()
