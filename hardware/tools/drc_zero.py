"""Clear DRC errors by deleting the tracks and vias that cause them; footprint-intrinsic errors become exclusions.

Run with KiCad closed:  $KPY hardware/tools/drc_zero.py hardware/OpenAIO.kicad_pcb [--rounds 8]

Each round runs kicad-cli DRC (zones refilled) and, for every error, deletes one item of the pair:
  1. a via that is not needed (another same-net via in the same pad, or a GND via with no track),
  2. otherwise a via,
  3. otherwise the shortest track segment.
Pads are never deleted. An error with no track or via inside one footprint, or on a mechanical no-net pad, is
written to the .kicad_pro as a DRC exclusion with a note; pad to pad between two parts stays an error (placement). Deleted copper leaves ratsnest lines to reroute;
the script prints what it deleted, per net.
"""
import collections
import json
import os
import subprocess
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


P = quiet_import()
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def drc(path):
    out = os.path.join(tempfile.mkdtemp(), "drc.json")
    pro = os.path.splitext(path)[0] + ".kicad_pro"
    saved = open(pro).read()
    subprocess.run([CLI, "pcb", "drc", "--refill-zones", "--format", "json", "-o", out, path], capture_output=True)
    open(pro, "w").write(saved)  # kicad-cli DRC may rewrite the project file
    d = json.load(open(out))
    return [x for x in d["violations"] if x["severity"] == "error"], len(d["unconnected_items"])


def main():
    a = sys.argv[1:]
    path = os.path.abspath([x for x in a if not x.startswith("--")][0])
    rounds = int(a[a.index("--rounds") + 1]) if "--rounds" in a else 8
    pro_path = os.path.splitext(path)[0] + ".kicad_pro"
    deleted = collections.Counter()
    excl = {}
    for rnd in range(rounds):
        errors, unconn = drc(path)
        print(f"round {rnd}: {len(errors)} errors, {unconn} unconnected")
        if not errors:
            break
        b = P.LoadBoard(path)
        items = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
        pads = {p.m_Uuid.AsString(): p for f in b.GetFootprints() for p in f.Pads()}
        vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]

        def cost(t):
            if t.GetClass() == "PCB_VIA":
                same = [v for v in vias if v is not t and v.GetNetCode() == t.GetNetCode()]
                for p in pads.values():
                    if p.GetNetCode() == t.GetNetCode() and p.HitTest(t.GetPosition()):
                        if any(p.HitTest(v.GetPosition()) for v in same):
                            return 0
                tracked = any(x.GetClass() == "PCB_TRACK" and x.GetNetCode() == t.GetNetCode() and
                              (x.GetStart() == t.GetPosition() or x.GetEnd() == t.GetPosition()) for x in b.GetTracks())
                return 1 if t.GetNetname() == "GND" and not tracked else 2
            return 3 + P.ToMM(t.GetLength())

        gone = set()
        progress = False
        for e in errors:
            cand = [items[i["uuid"]] for i in e["items"] if i.get("uuid") in items]
            cand = [c for c in cand if id(c) not in gone]
            if not cand:
                refs = {i["description"].split(" of ")[-1] for i in e["items"] if " of " in i["description"]}
                mech = any("<no net>" in i["description"] for i in e["items"])
                if len(refs) == 1 or mech:  # inside one footprint, or a mechanical no-net pad
                    u = [i["uuid"] for i in e["items"]] + ["00000000-0000-0000-0000-000000000000"]
                    pos = e["items"][0]["pos"]
                    key = f'{e["type"]}|{int(round(pos["x"] * 1e6))}|{int(round(pos["y"] * 1e6))}|{u[0]}|{u[1]}'
                    excl[key] = "Footprint-intrinsic (drc_zero.py 2026-10-15): " + "; ".join(i["description"] for i in e["items"])
                continue
            victim = min(cand, key=cost)
            gone.add(id(victim))
            deleted[(victim.GetClass().replace("PCB_", "").lower(), victim.GetNetname())] += 1
            b.Remove(victim)
            progress = True
        if progress:
            P.ZONE_FILLER(b).Fill(b.Zones())
            saved = open(pro_path).read()
            P.SaveBoard(path, b)
            open(pro_path, "w").write(saved)
        elif not excl:
            break
        if not progress:
            break
    if excl:
        p = json.load(open(pro_path))
        ex = p["board"]["design_settings"].setdefault("drc_exclusions", [])
        have = {x[0] if isinstance(x, list) else x for x in ex}
        for k, note in excl.items():
            if k not in have:
                ex.append([k, note])
        json.dump(p, open(pro_path, "w"), indent=2)
        open(pro_path, "a").write("\n")
        print(f"{len(excl)} footprint-intrinsic errors excluded with a note")
    errors, unconn = drc(path)
    print(f"final: {len(errors)} errors, {unconn} unconnected")
    by = collections.Counter()
    for (kind, net), n in deleted.items():
        by[kind] += n
    print("deleted:", dict(by))
    for (kind, net), n in sorted(deleted.items(), key=lambda kv: -kv[1])[:40]:
        print(f"  {n:3} {kind:5} {net}")


if __name__ == "__main__":
    main()
