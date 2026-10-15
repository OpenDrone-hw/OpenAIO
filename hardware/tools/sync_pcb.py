#!/usr/bin/env python3
"""Update a board from its schematic without the GUI ("Update PCB from Schematic").

    $KPY hardware/tools/sync_pcb.py hardware/OpenAIO-Whoop.kicad_pcb [--sch ROOT.kicad_sch | --netlist X.net]
                                    [--keep-extra] [--dry-run] [--quiet]

Runs under KiCad's Python (KPY: /usr/bin/python3.12 on Linux, see AGENTS.md).
kicad-cli has no update-PCB command, so this does what pcbnew's dialog does:

* exports the netlist with kicad-cli (or reads --netlist),
* matches each symbol to its footprint by the symbol's sheet path + uuid (the
  footprint "path", the link `kicad-cli pcb drc --schematic-parity` checks),
  falling back to the reference for footprints that have no path yet,
* adds missing footprints from the libraries in fp-lib-table (new parts are
  parked in a grid right of the board outline, on the front),
* swaps a footprint whose library id changed, keeping position, rotation,
  side and lock,
* writes reference, value, path, sheet name/file, every symbol field (MPN,
  LCSC, Manufacturer ...), DNP and exclude-from-BOM flags,
* creates nets and sets every pad's net, pin function and pin type; a net
  that only changed name keeps its tracks, vias and zones (they move to the
  new name); copper of a deleted part is left in place, as the GUI does, and
  shows up in DRC as dangling,
* deletes footprints whose symbol is gone (footprints with no path, i.e.
  board-only items such as logos or mounting holes, are always kept; pass
  --keep-extra to keep everything).

Idempotent: a second run with an unchanged schematic changes nothing (the
board file is not even rewritten) and existing placement is never touched.
Close KiCad before running it. Not done: footprint unit maps for multi-unit
symbols and netclass assignment from the schematic (netclasses come from the
project's patterns). Verified with `kicad-cli pcb drc --schematic-parity`:
0 parity issues after a sync, and every kind of drift (value, footprint,
net, missing and extra part) is reported before one.
Exit 0 on success (prints a change summary), 1 on a missing library or
footprint, 2 on bad arguments.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sch_build as sb  # noqa: E402  (pure Python: s-expression + netlist reader)


def quiet_import_pcbnew():
    """pcbnew prints wx asserts on import; silence fd 2 while importing."""
    saved, null = os.dup(2), os.open(os.devnull, os.O_WRONLY)
    os.dup2(null, 2)
    try:
        import pcbnew
    finally:
        os.dup2(saved, 2)
        os.close(null)
        os.close(saved)
    return pcbnew


P = quiet_import_pcbnew()
KICAD_CLI = sb.KICAD_CLI
# Fields KiCad keeps elsewhere on a footprint, not as user fields.
NOT_FIELDS = {"Reference", "Value", "Footprint"}


def fp_lib_paths(project_dir, extra_vars=None):
    """nickname -> .pretty directory, from the project and global fp-lib-table."""
    env = dict(os.environ)
    env["KIPRJMOD"] = project_dir
    env.update(extra_vars or {})
    tables = [os.path.join(project_dir, "fp-lib-table")]
    cfg = os.environ.get("KICAD_CONFIG_HOME") or os.path.expanduser("~/.config/kicad/10.0")
    tables.append(os.path.join(cfg, "fp-lib-table"))
    libs = {}
    for t in tables:
        if not os.path.exists(t):
            continue
        root = sb.parse(open(t, encoding="utf-8").read())
        for lib in sb.findall(root, "lib"):
            name, uri = sb.find(lib, "name")[1], sb.find(lib, "uri")[1]
            uri = re.sub(r"\$\{(\w+)\}", lambda m: env.get(m.group(1), m.group(0)), uri)
            libs.setdefault(name, uri)
    return libs


def text_vars(project_file):
    """Project text variables (e.g. OPENDRONE_LIB), used to resolve library URIs."""
    import json
    try:
        return json.load(open(project_file)).get("text_variables", {})
    except (OSError, ValueError):
        return {}


class Sync:
    def __init__(self, board_path, comps, nets, keep_extra=False, log=print):
        self.path = board_path
        self.dir = os.path.dirname(os.path.abspath(board_path))
        self.board = P.LoadBoard(board_path)
        tv = text_vars(os.path.splitext(board_path)[0] + ".kicad_pro")
        tv = {k: v.replace("${KIPRJMOD}", self.dir) for k, v in tv.items()}
        self.libs = fp_lib_paths(self.dir, tv)
        self.comps, self.nets = comps, nets
        self.keep_extra = keep_extra
        self.log = log
        self.changes = []
        self._park = 0

    # -- helpers ---------------------------------------------------------
    def note(self, msg):
        self.changes.append(msg)
        self.log("  " + msg)

    def load_fp(self, fpid):
        nick, name = fpid.split(":", 1)
        if nick not in self.libs:
            raise SystemExit("footprint library %r not in fp-lib-table (%s)" % (nick, fpid))
        fp = P.FootprintLoad(self.libs[nick], name)
        if fp is None:
            raise SystemExit("footprint %s not found in %s" % (fpid, self.libs[nick]))
        fp.SetFPID(P.LIB_ID(nick, name))
        return fp

    def park_position(self):
        """New footprints go in a grid right of the outline, so they never land on placed parts."""
        bb = self.board.GetBoardEdgesBoundingBox()
        x0 = bb.GetRight() + P.FromMM(5) if bb.GetWidth() > 0 else 0
        y0 = bb.GetTop() if bb.GetWidth() > 0 else 0
        i = self._park
        self._park += 1
        return P.VECTOR2I(int(x0 + (i % 8) * P.FromMM(4)), int(y0 + (i // 8) * P.FromMM(4)))

    # -- the update ------------------------------------------------------
    def run(self):
        b = self.board
        by_path, by_ref = {}, {}
        for fp in b.GetFootprints():
            p = fp.GetPath().AsString()
            if p:
                by_path[p] = fp
            by_ref[fp.GetReference()] = fp
        wanted = {}
        for ref, c in sorted(self.comps.items()):
            if c["exclude_from_board"]:
                continue
            fp = by_path.get(c["path"])
            if fp is None:
                cand = by_ref.get(ref)
                if cand is not None and cand.GetPath().AsString() not in {x["path"] for x in self.comps.values()}:
                    fp = cand
                    self.note("%s: relinked by reference" % ref)
            fp = self.update_footprint(fp, c)
            wanted[fp.m_Uuid.AsString()] = fp
        # footprints whose symbol is gone
        for fp in list(b.GetFootprints()):
            if fp.m_Uuid.AsString() in wanted or self.keep_extra or not fp.GetPath().AsString():
                continue
            self.note("%s: deleted (no symbol)" % fp.GetReference())
            b.Delete(fp)              # Delete, not Remove: Remove orphans the SWIG proxy
        self.update_nets()
        return self.changes

    def update_footprint(self, fp, c):
        b = self.board
        fpid = c["footprint"]
        if not fpid:
            raise SystemExit("%s has no footprint in the schematic" % c["ref"])
        if fp is None:
            fp = self.load_fp(fpid)
            fp.SetPosition(self.park_position())
            b.Add(fp)
            self.note("%s: added %s" % (c["ref"], fpid))
        elif fp.GetFPIDAsString() != fpid:
            new = self.load_fp(fpid)
            b.Add(new)                              # add before Flip: flipping an orphan crashes 10.0.6
            new.SetPosition(fp.GetPosition())
            new.SetOrientation(fp.GetOrientation())
            if fp.IsFlipped():
                new.Flip(new.GetPosition(), P.FLIP_DIRECTION_TOP_BOTTOM)
            new.SetLocked(fp.IsLocked())
            self.note("%s: footprint %s -> %s" % (c["ref"], fp.GetFPIDAsString(), fpid))
            b.Delete(fp)
            fp = new
        self.set_if(fp, "reference", fp.GetReference(), c["ref"], fp.SetReference)
        self.set_if(fp, "value", fp.GetValue(), c["value"], fp.SetValue)
        path = P.KIID_PATH(c["path"])
        if fp.GetPath().AsString() != c["path"]:
            fp.SetPath(path)
            self.note("%s: path %s" % (c["ref"], c["path"]))
        self.set_if(fp, "sheetname", fp.GetSheetname(), c["sheetname"], fp.SetSheetname)
        self.set_if(fp, "sheetfile", fp.GetSheetfile(), c["sheetfile"], fp.SetSheetfile)
        fields = dict(c["fields"])
        if c.get("datasheet") and "Datasheet" not in fields:
            fields["Datasheet"] = c["datasheet"]
        for name, val in sorted(fields.items()):
            if name in NOT_FIELDS:
                continue
            have = fp.GetFieldText(name) if fp.HasField(name) else None
            if have != val:
                new_field = not fp.HasField(name)
                fp.SetField(name, val)
                if new_field:
                    f = fp.GetField(name)
                    f.SetVisible(False)
                    f.SetLayer(P.F_Fab if not fp.IsFlipped() else P.B_Fab)
                self.note("%s: field %s = %r" % (c["ref"], name, val))
        for flag, get, set_ in (("dnp", fp.IsDNP, fp.SetDNP),
                                ("exclude_from_bom", fp.IsExcludedFromBOM, fp.SetExcludedFromBOM)):
            if bool(get()) != bool(c[flag]):
                set_(bool(c[flag]))
                self.note("%s: %s = %s" % (c["ref"], flag, c[flag]))
        return fp

    def set_if(self, fp, what, have, want, setter):
        if have != want:
            setter(want)
            self.note("%s: %s %r -> %r" % (fp.GetReference(), what, have, want))

    def update_nets(self):
        b = self.board
        # pads per schematic net and per current board net
        want_pads = {name: frozenset((r, p) for r, p, _, _ in nodes) for name, nodes in self.nets.items()}
        have_pads = {}
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() > 0:
                    have_pads.setdefault(pad.GetNetname(), set()).add((fp.GetReference(), pad.GetNumber()))
        # a net whose pads are unchanged but whose name changed keeps its copper: its tracks,
        # vias and zones move to the new net (NETINFO_ITEM.SetNetname does not update the
        # board's name map in 10.0, so the items are re-pointed instead)
        existing = {str(k) for k in b.GetNetsByName().keys()}
        renames = {}
        for old, pads in have_pads.items():
            if old in want_pads:
                continue
            for new, wp in want_pads.items():
                if new not in existing and new not in renames.values() and wp == frozenset(pads):
                    renames[old] = new
                    break
        nets = {}
        for name in self.nets:
            net = b.FindNet(name)
            if net is None:
                net = P.NETINFO_ITEM(b, name)
                b.Add(net)
                if name not in renames.values():
                    self.note("net %s added" % name)
            nets[name] = net
        if renames:
            for item in list(b.GetTracks()) + list(b.Zones()):
                new = renames.get(item.GetNetname())
                if new:
                    item.SetNet(nets[new])
            for old, new in sorted(renames.items()):
                self.note("net %s renamed to %s (copper kept)" % (old, new))
        pin_net = {}
        for name, nodes in self.nets.items():
            for ref, pin, func, ptype in nodes:
                pin_net[(ref, pin)] = (name, func, ptype)
        for fp in b.GetFootprints():
            ref = fp.GetReference()
            if ref not in self.comps:
                continue
            for pad in fp.Pads():
                key = (ref, pad.GetNumber())
                if key in pin_net:
                    name, func, ptype = pin_net[key]
                    if pad.GetNetname() != name:
                        self.note("%s.%s: net %r -> %r" % (ref, pad.GetNumber(), pad.GetNetname(), name))
                        pad.SetNet(nets[name])
                    if pad.GetPinFunction() != func:
                        pad.SetPinFunction(func)
                    if pad.GetPinType() != ptype:
                        pad.SetPinType(ptype)
                elif pad.GetNetCode() > 0 and pad.GetNumber():
                    self.note("%s.%s: net %r removed (pin not in schematic)" % (ref, pad.GetNumber(), pad.GetNetname()))
                    pad.SetNetCode(0)
        # drop nets nothing uses any more
        used = set(self.nets)
        for item in list(b.GetTracks()) + list(b.Zones()):
            used.add(item.GetNetname())
        for fp in b.GetFootprints():                 # board-only footprints keep their nets
            used.update(p.GetNetname() for p in fp.Pads())
        for name, net in list(b.GetNetsByName().items()):
            name = str(name)
            if name and name not in used:
                b.Remove(net)
                self.note("net %s removed" % name)

    def save(self):
        self.board.BuildConnectivity()
        P.SaveBoard(self.path, self.board)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("board")
    ap.add_argument("--sch", help="root schematic (default: board name .kicad_sch)")
    ap.add_argument("--netlist", help="kicadsexpr netlist to use instead of exporting one")
    ap.add_argument("--keep-extra", action="store_true", help="keep footprints whose symbol is gone")
    ap.add_argument("--dry-run", action="store_true", help="report changes, do not save")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    board = os.path.abspath(a.board)
    if not os.path.exists(board):
        ap.error("no board %s" % board)
    if a.netlist:
        net = a.netlist
    else:
        sch = a.sch or os.path.splitext(board)[0] + ".kicad_sch"
        net = os.path.join(tempfile.mkdtemp(prefix="sync_pcb_"), "netlist.net")
        r = subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit("netlist export failed:\n" + r.stdout + r.stderr)
    comps, nets = sb.read_netlist(net)
    s = Sync(board, comps, nets, a.keep_extra, log=(lambda m: None) if a.quiet else print)
    changes = s.run()
    if not a.dry_run and changes:
        s.save()
    print("%d components, %d nets, %d changes%s" % (len(comps), len(nets), len(changes),
                                                   " (dry run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
