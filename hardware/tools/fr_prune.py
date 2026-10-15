"""Delete the autorouted items that DRC flags; the owner's copper is never touched.

Run with KiCad closed:  $KPY hardware/tools/fr_prune.py hardware/OpenAIO.kicad_pcb drc.json run.ses.new.txt [--dry-run]

drc.json is `kicad-cli pcb drc --format json --severity-all` of the board after tools/fr_import.py. Every item of
an error-severity violation whose UUID is in the .new.txt list (written by fr_import.py) is removed. Run
tools/cleanup.py afterwards (repeat until it deletes nothing) for the track ends this leaves dangling.
"""
import json
import os
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


P = quiet_import()


def main():
    a = sys.argv[1:]
    path, drc, newf = [x for x in a if not x.startswith("--")][:3]
    new = set(open(newf).read().split())
    bad = set()
    for v in json.load(open(drc))["violations"]:
        if v["severity"] == "error":
            bad |= {i["uuid"] for i in v["items"] if i["uuid"] in new}
    b = P.LoadBoard(path)
    gone = [t for t in b.GetTracks() if t.m_Uuid.AsString() in bad]
    for t in gone:
        b.Remove(t)
    print(f"{len(gone)} autorouted items removed ({len(bad)} flagged)")
    if "--dry-run" not in a and gone:
        P.SaveBoard(path, b)
        print("saved")


if __name__ == "__main__":
    main()
