"""Export the board as a Specctra DSN for Freerouting: existing copper fixed, power nets left alone.

Run with KiCad closed (the board is only read):
  $KPY hardware/tools/fr_prep.py hardware/OpenAIO.kicad_pcb out.dsn [--skip GND,/CSA+,+BATT,/1A,...]

- every existing wire and via becomes (type protect): Freerouting adds copper, it does not move the owner's routing
- planes are the zones' FILLED copper, not their outlines (KiCad exports outlines, and Freerouting treats a plane
  as an obstacle for other nets: the /CSA+ outline alone blocks 14 x 12 mm on L2-L8); GND planes are dropped
  (the full-board GND fill would block every layer; it reflows around the new tracks)
- the skipped nets (default GND, /CSA+, +BATT and the 12 phases) move to class NOROUTE: run Freerouting with
  -inc NOROUTE so their pads stay obstacles and their links stay for the pours
- every class may use only the through via 0.33/0.15 (the edit form); the structure lists no other via. With
  --blind also the blind L1-L7 and L2-L8 0.33/0.15 (the edit-form via where a through via does not fit)
- the GND plane layers L2 and L7 become (type power): no signal is routed on them; --power L4.BATT,L5.Rails adds
  more (Freerouting does not treat a foreign plane as an obstacle, so it routes straight through the +BATT planes)
Run Freerouting on the result with tools/fr_run.sh.
"""
import os
import re
import sys

PHASES = [f"/{i}{c}" for i in range(1, 5) for c in "ABC"]


def blocks(text, head):
    """(start, end) of every balanced block that starts with head."""
    out, i = [], 0
    while True:
        i = text.find(head, i)
        if i < 0:
            return out
        d, j = 0, i
        while True:
            if text[j] == "(":
                d += 1
            elif text[j] == ")":
                d -= 1
                if d == 0:
                    break
            j += 1
        out.append((i, j + 1))
        i = j + 1


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


def filled_planes(P, b):
    """(plane ...) lines from the filled copper of every non-GND zone, in DSN um (y up)."""
    out = []
    for i in range(b.GetAreaCount()):
        z = b.GetArea(i)
        if z.GetIsRuleArea() or z.GetNetname() in ("GND", ""):
            continue
        for l in z.GetLayerSet().CuStack():
            polys = z.GetFilledPolysList(l)
            for k in range(polys.OutlineCount()):
                o = polys.Outline(k)
                pts = " ".join(f"{P.ToMM(o.CPoint(j).x) * 1000:.1f} {-P.ToMM(o.CPoint(j).y) * 1000:.1f}"
                               for j in range(o.PointCount()))
                out.append(f'    (plane "{z.GetNetname()}" (polygon {b.GetLayerName(l)} 0 {pts}))\n')
    return "".join(out)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    vias = ['"Via[0-7]_330:150_um"'] + (['"Via[0-6]_330:150_um"', '"Via[1-7]_330:150_um"'] if "--blind" in sys.argv else [])
    skip = set(sys.argv[sys.argv.index("--skip") + 1].split(",")) if "--skip" in sys.argv else \
        {"GND", "/CSA+", "+BATT", *PHASES}
    P = quiet_import()
    b = P.LoadBoard(src)
    P.ZONE_FILLER(b).Fill(b.Zones())
    tmp = dst + ".kicad.dsn"
    P.ExportSpecctraDSN(b, tmp)
    t = open(tmp).read()
    os.remove(tmp)
    for s, e in reversed(blocks(t, "(plane ")):
        t = t[:s] + t[e:]
    i = t.index("(via ", t.index("(structure"))
    t = t[:i] + filled_planes(P, b).lstrip() + "    " + t[i:]
    w0 = t.index("(wiring")
    t = t[:w0] + t[w0:].replace("(type route)", "(type protect)")
    net_tok = r'("[^"]*"|[^\s()]+)'
    out, last = [], 0
    for s, e in blocks(t, "(class "):
        blk = t[s:e]
        head_end = blk.index("(circuit") if "(circuit" in blk else blk.index("(rule")
        toks = re.findall(net_tok, blk[len("(class "):head_end])
        name, nets = toks[0], toks[1:]
        keep = [n for n in nets if n.strip('"') not in skip]
        blk = "(class " + " ".join([name] + keep) + "\n      " + blk[head_end:]
        out.append(t[last:s] + blk)
        last = e
    t = "".join(out) + t[last:]
    cls = " ".join(f'"{n}"' for n in sorted(skip))
    i = t.rindex("(class ")
    t = t[:i] + f"(class NOROUTE {cls}\n      (circuit (use_via \"Via[0-7]_330:150_um\"))\n" \
        "      (rule (width 100) (clearance 100))\n    )\n    " + t[i:]
    t = re.sub(r'\(use_via [^)]*\)', "(use_via " + " ".join(vias) + ")", t)
    s0 = t.index("(via ", t.index("(structure"))
    s1 = t.index(")", s0)
    t = t[:s0] + "(via " + " ".join(vias) + t[s1:]
    for name in ["L2.GND", "L7.GND"] + (sys.argv[sys.argv.index("--power") + 1].split(",")
                                        if "--power" in sys.argv else []):
        t = re.sub(r"(\(layer " + re.escape(name) + r"\s+\(type )signal", r"\1power", t)
    open(dst, "w").write(t)
    print("protected wires", t.count("(type protect)"), "| skipped nets", len(skip))


if __name__ == "__main__":
    main()
