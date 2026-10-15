"""Make every schematic symbol project-local: lib_id "<nick>:<name>" -> "lib:<name>", definition in lib.kicad_sym.

Run with KiCad closed:
  python3 hardware/tools/localise_symbols.py hardware [--prune]
then re-save every sheet with `kicad-cli sch upgrade --force` and prove the change with an ERC and a netlist
diff against the version before (only lib_ids may differ).

The definition copied into lib.kicad_sym is the schematic's own cached one, so graphics and pins stay exactly as
placed. A name already in lib.kicad_sym with a different definition gets the suffix _OpenAIO (units renamed with
it). A lib symbol whose lib.kicad_sym copy differs from the schematic's cached one is refreshed from the
schematic. --prune removes lib.kicad_sym symbols no sheet uses. Needs sexpdata.
"""
import copy
import glob
import os
import sys

import sexpdata

Sym = sexpdata.Symbol


def S(x):
    return x.value() if isinstance(x, Sym) else x


def kids(n, tag):
    return [x for x in n if isinstance(x, list) and x and S(x[0]) == tag]


def kid(n, tag):
    k = kids(n, tag)
    return k[0] if k else None


def rename(sym, old, new):
    """Rename a symbol definition and its unit sub-symbols (<name>_<unit>_<style>)."""
    sym[1] = new
    for sub in kids(sym, "symbol"):
        if sub[1].startswith(old + "_"):
            sub[1] = new + sub[1][len(old):]


def norm(sym):
    s = copy.deepcopy(sym)
    rename(s, s[1].split(":", 1)[-1], "X")
    return sexpdata.dumps(s)


def main():
    hw = os.path.abspath(sys.argv[1])
    prune = "--prune" in sys.argv
    libf = os.path.join(hw, "lib.kicad_sym")
    lib = sexpdata.loads(open(libf).read())
    defs = {x[1]: x for x in kids(lib, "symbol")}
    moved, used, synced = {}, set(), set()
    for f in sorted(glob.glob(os.path.join(hw, "*.kicad_sch"))):
        d = sexpdata.loads(open(f).read())
        cache = kid(d, "lib_symbols")
        ren = {}
        for x in cache[1:]:
            key = x[1]
            nick, _, name = key.partition(":")
            if not name:
                nick, name = "", key  # lib_name override entry, no nickname
            if nick == "lib":
                # The schematic is the reference: a lib.kicad_sym copy that differs is replaced by the cache.
                if name in defs and norm(defs[name]) != norm(x) and name not in synced:
                    y = copy.deepcopy(x)
                    rename(y, name, name)
                    y[1] = name
                    lib[lib.index(defs[name])] = y
                    defs[name] = y
                    synced.add(name)
                elif name in synced and norm(defs[name]) != norm(x):
                    print("WARNING: sheets disagree on", key, "in", os.path.basename(f))
                continue
            target = name
            if target in defs and norm(defs[target]) != norm(x):
                target = name + "_OpenAIO"
                while target in defs and norm(defs[target]) != norm(x):
                    target += "_"
            if target not in defs:
                y = copy.deepcopy(x)
                rename(y, name, target)
                y[1] = target
                lib.append(y)
                defs[target] = y
                moved[target] = key
            ren[key] = (name, target)
        for x in cache[1:]:
            if x[1] in ren:
                name, target = ren[x[1]]
                rename(x, name, target)
                x[1] = "lib:" + target
        for s in kids(d, "symbol"):
            ln, li = kid(s, "lib_name"), kid(s, "lib_id")
            key = ln[1] if ln else li[1]
            if key in ren:
                if ln:
                    s.remove(ln)
                li[1] = "lib:" + ren[key][1]
            used.add(kid(s, "lib_id")[1].split(":", 1)[1])
        if ren:
            open(f, "w").write(sexpdata.dumps(d) + "\n")
            print(os.path.basename(f), len(ren), "cache entries relinked")
    if prune:
        for x in kids(lib, "symbol"):
            if x[1] not in used:
                lib.remove(x)
                print("prune symbol", x[1])
    open(libf, "w").write(sexpdata.dumps(lib) + "\n")
    print("moved into lib:", ", ".join(f"{k} ({v})" for k, v in sorted(moved.items())))
    print("lib.kicad_sym copies refreshed from the schematic:", ", ".join(sorted(synced)) or "none")


if __name__ == "__main__":
    main()
