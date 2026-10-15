"""Write KiCad 10 schematics from Python: symbols, wires, labels, sheets.

KiCad 10 has no schematic API (the IPC API covers the board editor only), so
this module writes the .kicad_sch s-expressions itself and then has KiCad
re-save every file (`kicad-cli sch upgrade --force`), which both proves the
file loads and leaves it in KiCad's own formatting. Run with any Python 3.9+;
no KiCad import is needed. kicad-cli must be on PATH (or set KICAD_CLI).

    import sch_build as sb
    prj = sb.Project("hardware/OpenAIO-Whoop.kicad_sch")          # keeps the root uuid
    prj.lib("OpenDrone", "hardware/KiCad-Library/symbol/OpenDrone.kicad_sym")
    prj.lib("lib", "hardware/lib.kicad_sym")
    pwr = prj.sheet("power.kicad_sch", title="POWER")              # a sheet file
    prj.root.add_sheet(pwr, "POWER", at=(30, 30), size=(25, 20),
                       pins=[("VBAT", "input"), ("+3V3", "output")])
    u1 = pwr.symbol("OpenDrone:LP5912-3.3DRVR", "U1", at=(100, 80))
    pwr.connect(u1, "IN", "VBAT", kind="hier")                     # stub + hierarchical label
    pwr.connect(u1, "GND", "lib:GND", kind="power")                # stub + power symbol
    pwr.connect(u1, "PG", None)                                    # no-connect flag
    prj.save()                                                     # writes, then kicad-cli re-saves

Connection kinds for Sheet.connect / connect_point:
    "label"   local net label (net name is sheet-local, "/<sheet path>/<name>")
    "global"  global label (net name is <name> everywhere)
    "hier"    hierarchical label; the parent sheet symbol needs a pin of that name
    "power"   power symbol by lib_id, e.g. "lib:GND"; net name = its Value
    None      no-connect flag on the pin

Determinism: every uuid is uuid5(project-uuid, file + key). A symbol's key is
its reference unless `key=` is given, so regenerating the schematic keeps the
symbol uuids, and sync_pcb.py keeps the footprints and their placement. Keep
the key when renaming a part (`key="old ref"`).

A sheet file may be placed several times (an ESC channel x4). Give each
placement a `ref_offset`; the numeric part of every reference in that file is
offset per placement (R1 -> R101, R201, ...), and offsets add up through
nested sheets. `ref_offset` may also be a {prefix: n} dict ("*" = every other
prefix) when the instances follow a per-prefix stride, e.g. ESC2 =
{"U": 1, "Q": 3, "R": 7, "C": 6, "TP": 2} (hardware/sch_contract.json). Power and flag symbols are numbered automatically (#PWR01..,
#FLG01..). Multi-unit parts: place each unit with the same ref and `unit=n`.

Readability helpers: connect_group() joins same-side pins (VDD/VDDA, VSS)
to one rail with a single terminator; stub=0 puts a label straight on the
pin end. Symbol fields come from the library and are overridden by `fields=`
(MPN, LCSC, Manufacturer, Footprint ...).

Coordinates are mm, schematic axes (+y down). Keep everything on the 1.27 mm
grid: symbol pins in KiCad libraries are on it, and a connection only exists
where two points coincide exactly. Pin geometry is checked for all four
rotations x mirror none/x/y (pipeline_selftest.py).

Also here: erc(), export_netlist(), read_netlist() (used by sync_pcb.py),
symbols_from_schematic() / write_symbol_lib() to seed a project library from
symbols embedded in another schematic.
"""
import math
import os
import re
import shutil
import subprocess
import uuid as _uuid

GRID = 1.27
SCH_VERSION = "20260306"
SYM_VERSION = "20251024"
KICAD_CLI = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli") or "kicad-cli"


# --------------------------------------------------------------------------
# s-expressions: atoms are Atom (unquoted), quoted strings are plain str
# --------------------------------------------------------------------------
class Atom(str):
    """An unquoted s-expression token (keyword or number)."""


_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)
_UNESC = re.compile(r"\\(.)", re.S)


def _unescape(s):
    return _UNESC.sub(lambda m: {"n": "\n", "r": "\r", "t": "\t"}.get(m.group(1), m.group(1)), s)


def parse(text):
    """Parse s-expression text; returns the first top-level list."""
    stack = [[]]
    for m in _TOKEN.finditer(text):
        lp, rp, qs, atom = m.groups()
        if lp:
            stack.append([])
        elif rp:
            node = stack.pop()
            stack[-1].append(node)
        elif qs is not None:
            stack[-1].append(_unescape(qs))
        elif atom is not None:
            stack[-1].append(Atom(atom))
    return stack[0][0]


def _q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def num(v):
    """Format a number the way KiCad does: at most 4 decimals, no trailing zeros."""
    if isinstance(v, str):
        return Atom(v)
    s = ("%.4f" % float(v)).rstrip("0").rstrip(".")
    return Atom("0" if s in ("-0", "") else s)


def dump(node, indent=0):
    """Serialize a node tree with KiCad-like tab indentation."""
    if isinstance(node, Atom):
        return str(node)
    if isinstance(node, str):
        return _q(node)
    if isinstance(node, bool):
        return "yes" if node else "no"
    if isinstance(node, (int, float)):
        return str(num(node))
    if not any(isinstance(c, list) for c in node):
        return "(" + " ".join(dump(c) for c in node) + ")"
    out, i = [], 0
    while i < len(node) and not isinstance(node[i], list):
        out.append(dump(node[i]))
        i += 1
    s = "(" + " ".join(out)
    for c in node[i:]:
        s += "\n" + "\t" * (indent + 1) + dump(c, indent + 1)
    return s + "\n" + "\t" * indent + ")"


def S(*items):
    """Build a node: S('at', 1, 2, 0) -> (at 1 2 0). First item becomes an Atom."""
    out = [Atom(items[0])]
    for it in items[1:]:
        if isinstance(it, bool):
            out.append(Atom("yes" if it else "no"))
        elif isinstance(it, (int, float)):
            out.append(num(it))
        else:
            out.append(it)
    return out


def find(node, key):
    """First child list whose head is `key`."""
    for c in node[1:]:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def findall(node, key):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == key]


def snap(v, grid=GRID):
    return round(round(v / grid) * grid, 4)


def _r4(v):
    return round(v + 0.0, 4)


# --------------------------------------------------------------------------
# symbol libraries
# --------------------------------------------------------------------------
class Pin:
    def __init__(self, node, unit, body):
        at = find(node, "at")
        self.etype, self.shape = str(node[1]), str(node[2])
        self.x, self.y = float(at[1]), float(at[2])
        self.angle = float(at[3]) if len(at) > 3 else 0.0
        self.name = find(node, "name")[1]
        self.number = find(node, "number")[1]
        self.hidden = any(c == ["hide", "yes"] or c == "hide" for c in node[1:])
        self.unit, self.body = unit, body

    def __repr__(self):
        return "Pin(%s %s %s @%g,%g a%g)" % (self.number, self.name, self.etype, self.x, self.y, self.angle)


class LibSymbol:
    """One symbol from a .kicad_sym file, flattened if it `extends` another."""

    def __init__(self, nick, node):
        self.nick, self.node = nick, node
        self.name = node[1]
        self.lib_id = "%s:%s" % (nick, self.name)
        # `(property private "KLC_S4.1" ...)` (stock Crystal_GND24 etc.): the name is the atom `private`, not a
        # field; copying it onto a placed symbol writes an unquoted `private` that kicad-cli refuses (P4 integration)
        self.props = {p[1]: p[2] for p in findall(node, "property") if not isinstance(p[1], Atom)}
        self.is_power = find(node, "power") is not None
        self.pins = []
        self.units = 1
        for sub in findall(node, "symbol"):
            m = re.match(r"^(.*)_(\d+)_(\d+)$", sub[1])
            unit, body = int(m.group(2)), int(m.group(3))
            self.units = max(self.units, unit)
            for p in findall(sub, "pin"):
                self.pins.append(Pin(p, unit, body))

    def unit_pins(self, unit=1, body=1):
        return [p for p in self.pins if p.unit in (0, unit) and p.body in (0, body)]

    def pin(self, ident, unit=1, body=1):
        """Find a pin by number, or by name when the name is unique in the unit."""
        pins = self.unit_pins(unit, body)
        hit = [p for p in pins if p.number == ident]
        if not hit:
            hit = [p for p in pins if p.name == ident]
        if not hit:
            raise KeyError("%s: no pin %r in unit %d" % (self.lib_id, ident, unit))
        if len(hit) > 1 and len({(p.x, p.y) for p in hit}) > 1:
            raise KeyError("%s: pin %r is ambiguous (%s); use the number"
                           % (self.lib_id, ident, ", ".join(p.number for p in hit)))
        return hit[0]

    def embedded(self):
        """The node as it goes into a schematic's lib_symbols ("nick:name")."""
        n = list(self.node)
        n[1] = self.lib_id
        return n

    def body_direction(self):
        """For power symbols: unit vector (lib axes, +y up) from the pin to the graphics."""
        xs, ys = [], []

        def walk(n):
            for c in n:
                if isinstance(c, list):
                    if c and c[0] in ("xy", "start", "end", "center", "mid") and len(c) >= 3:
                        xs.append(float(c[1]))
                        ys.append(float(c[2]))
                    elif c and c[0] != "property":
                        walk(c)
        walk(self.node)
        p = self.pins[0] if self.pins else None
        if not ys or p is None:
            return (0, -1)
        dx, dy = sum(xs) / len(xs) - p.x, sum(ys) / len(ys) - p.y
        if abs(dy) >= abs(dx):
            return (0, 1 if dy > 0 else -1)
        return (1 if dx > 0 else -1, 0)


class SymbolLib:
    def __init__(self, nick, path):
        self.nick, self.path = nick, path
        root = parse(open(path, encoding="utf-8").read())
        self.raw = {s[1]: s for s in findall(root, "symbol")}
        self._cache = {}

    def names(self):
        return sorted(self.raw)

    def get(self, name):
        if name not in self._cache:
            if name not in self.raw:
                raise KeyError("symbol %r not in %s (%s)" % (name, self.nick, self.path))
            self._cache[name] = LibSymbol(self.nick, self._flatten(self.raw[name]))
        return self._cache[name]

    def _flatten(self, node):
        ext = find(node, "extends")
        if ext is None:
            return node
        parent = self._flatten(self.raw[ext[1]])
        name, pname = node[1], parent[1]
        own = {p[1]: p for p in findall(node, "property")}
        out = [node[0], name]
        for c in parent[2:]:
            if isinstance(c, list) and c and c[0] == "property" and c[1] in own:
                out.append(own.pop(c[1]))
            elif isinstance(c, list) and c and c[0] == "symbol":
                sub = list(c)
                sub[1] = name + sub[1][len(pname):]
                out.append(sub)
            else:
                out.append(c)
        out[2:2] = list(own.values())
        return out


def write_symbol_lib(path, lib_symbols):
    """Write LibSymbol objects (or raw nodes) into a .kicad_sym file, names without nickname."""
    root = [Atom("kicad_symbol_lib"), S("version", Atom(SYM_VERSION)),
            S("generator", "kicad_symbol_editor"), S("generator_version", "10.0")]
    for s in lib_symbols:
        n = list(s.node if isinstance(s, LibSymbol) else s)
        n[1] = n[1].split(":", 1)[-1]
        root.append(n)
    with open(path, "w", encoding="utf-8") as f:
        f.write(dump(root) + "\n")


def symbols_from_schematic(sch_path, lib_ids):
    """Pull embedded lib_symbols (e.g. 'Device:R', 'power:GND') out of an existing schematic."""
    root = parse(open(sch_path, encoding="utf-8").read())
    have = {s[1]: s for s in findall(find(root, "lib_symbols"), "symbol")}
    out = []
    for lid in lib_ids:
        n = list(have[lid])
        name = lid.split(":", 1)[-1]
        old = n[1].split(":", 1)[-1]
        n[1] = name
        out.append([c if not (isinstance(c, list) and c and c[0] == "symbol")
                    else [c[0], name + c[1][len(old):]] + c[2:] for c in n])
    return out


# --------------------------------------------------------------------------
# geometry: library (+y up) -> schematic (+y down)
# --------------------------------------------------------------------------
def _xform(x, y, rot, mirror):
    """Library offset -> schematic offset for a symbol at rotation `rot` (CCW deg) and mirror."""
    a = math.radians(rot)
    c, s = round(math.cos(a)), round(math.sin(a))
    xr, yr = x * c - y * s, x * s + y * c      # rotate CCW in library axes
    sx, sy = xr, -yr                           # library -> schematic axes
    if mirror == "x":                          # mirror about the horizontal axis
        sy = -sy
    elif mirror == "y":                        # mirror about the vertical axis
        sx = -sx
    return sx, sy


def _angle_of(dx, dy):
    """Schematic direction vector -> label angle (0 right, 90 up, 180 left, 270 down)."""
    if abs(dx) >= abs(dy):
        return 0 if dx > 0 else 180
    return 90 if dy < 0 else 270


# --------------------------------------------------------------------------
# schematic objects
# --------------------------------------------------------------------------
class Placed:
    """A symbol placed on a sheet file."""

    def __init__(self, sheet, lib, ref, at, rot, mirror, unit, value, fields, key,
                 dnp, in_bom, on_board, body):
        self.sheet, self.lib, self.ref = sheet, lib, ref
        self.at = (_r4(at[0]), _r4(at[1]))
        self.rot, self.mirror, self.unit, self.body = rot % 360, mirror, unit, body
        self.value = value if value is not None else lib.props.get("Value", "")
        self.fields = dict(fields or {})
        self.key = key or ref
        self.dnp, self.in_bom, self.on_board = dnp, in_bom, on_board
        # each unit of a multi-unit part is its own symbol with its own uuid
        self.uuid = sheet.prj.uid(sheet.file, "sym", self.key if unit == 1 else "%s|unit%d" % (self.key, unit))

    def pin_xy(self, ident):
        """(x, y, outward angle) of a pin's connection point in schematic coordinates."""
        p = self.lib.pin(ident, self.unit, self.body)
        dx, dy = _xform(p.x, p.y, self.rot, self.mirror)
        a = math.radians(p.angle + 180)        # outward = away from the body
        vx, vy = _xform(round(math.cos(a)), round(math.sin(a)), self.rot, self.mirror)
        return _r4(self.at[0] + dx), _r4(self.at[1] + dy), _angle_of(vx, vy)

    def pins(self):
        return self.lib.unit_pins(self.unit, self.body)


class SheetUse:
    """One placement of a sheet file inside a parent sheet."""

    def __init__(self, parent, child, name, at, size, pins, ref_offset, key):
        self.parent, self.child, self.name = parent, child, name
        self.at, self.size, self.ref_offset = at, size, ref_offset
        self.uuid = parent.prj.uid(parent.file, "sheet", key or name)
        self.pins = []                       # (name, shape, x, y, angle)
        x0, y0 = at
        w, h = size
        sides = {"right": [], "left": [], "top": [], "bottom": []}
        for p in pins:
            name_, shape = p[0], p[1]
            side = p[2] if len(p) > 2 else ("left" if shape == "input" else "right")
            sides[side].append((name_, shape))
        for side, lst in sides.items():
            for i, (n, shape) in enumerate(lst):
                off = (i + 1) * 2.54
                if side == "right":
                    self.pins.append((n, shape, x0 + w, y0 + off, 0))
                elif side == "left":
                    self.pins.append((n, shape, x0, y0 + off, 180))
                elif side == "top":
                    self.pins.append((n, shape, x0 + off, y0, 90))
                else:
                    self.pins.append((n, shape, x0 + off, y0 + h, 270))

    def pin_xy(self, name):
        for n, shape, x, y, a in self.pins:
            if n == name:
                return _r4(x), _r4(y), a
        raise KeyError("sheet %s has no pin %r" % (self.name, name))


class Sheet:
    """The contents of one .kicad_sch file."""

    def __init__(self, prj, file, title=None, paper="A4", file_uuid=None, extra=None):
        self.prj, self.file, self.title, self.paper = prj, file, title, paper
        self.uuid = file_uuid or prj.uid(file, "file", "")
        self.symbols, self.items, self.uses = [], [], []
        self.extra = extra or []          # raw nodes kept from an existing file
        self._n = 0

    # -- low level -------------------------------------------------------
    def _uid(self, kind):
        self._n += 1
        return self.prj.uid(self.file, kind, str(self._n))

    def symbol(self, lib_id, ref, at, rot=0, mirror=None, unit=1, value=None, fields=None,
               key=None, dnp=False, in_bom=True, on_board=True, body=1):
        """Place a symbol. `fields` overrides/adds properties (MPN, LCSC, Footprint ...)."""
        lib = self.prj.symbol_def(lib_id)
        s = Placed(self, lib, ref, at, rot, mirror, unit, value, fields, key, dnp, in_bom, on_board, body)
        if any(o.key == s.key and o.unit == s.unit for o in self.symbols):
            raise ValueError("%s: duplicate symbol key %r" % (self.file, s.key))
        self.symbols.append(s)
        return s

    def wire(self, *pts):
        """A wire through the given points (one segment per pair)."""
        for a, b in zip(pts, pts[1:]):
            self.items.append(S("wire", S("pts", S("xy", a[0], a[1]), S("xy", b[0], b[1])),
                                S("stroke", S("width", 0), S("type", Atom("default"))),
                                S("uuid", self._uid("wire"))))

    def junction(self, x, y):
        self.items.append(S("junction", S("at", x, y), S("diameter", 0), S("color", 0, 0, 0, 0),
                            S("uuid", self._uid("junction"))))

    def no_connect(self, x, y):
        self.items.append(S("no_connect", S("at", x, y), S("uuid", self._uid("nc"))))

    def label(self, name, x, y, angle=0):
        j = "left" if angle in (0, 90) else "right"
        self.items.append(S("label", name, S("at", x, y, angle),
                            S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Atom(j), Atom("bottom"))),
                            S("uuid", self._uid("label"))))

    def global_label(self, name, x, y, angle=0, shape="bidirectional"):
        j = "left" if angle in (0, 90) else "right"
        self.items.append(S("global_label", name, S("shape", Atom(shape)), S("at", x, y, angle),
                            S("fields_autoplaced", True),
                            S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Atom(j))),
                            S("uuid", self._uid("glabel")),
                            S("property", "Intersheetrefs", "${INTERSHEET_REFS}", S("at", x, y, 0),
                              S("hide", True), S("show_name", False), S("do_not_autoplace", False),
                              S("effects", S("font", S("size", 1.27, 1.27))))))

    def hier_label(self, name, x, y, angle=0, shape="bidirectional"):
        j = "left" if angle in (0, 90) else "right"
        self.items.append(S("hierarchical_label", name, S("shape", Atom(shape)), S("at", x, y, angle),
                            S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Atom(j))),
                            S("uuid", self._uid("hlabel"))))

    def text(self, s, x, y, size=1.27):
        self.items.append(S("text", s, S("exclude_from_sim", False), S("at", x, y, 0),
                            S("effects", S("font", S("size", size, size)), S("justify", Atom("left"))),
                            S("uuid", self._uid("text"))))

    def power(self, lib_id, x, y, angle=None, value=None):
        """Place a power (or PWR_FLAG) symbol with its pin at (x, y), body pointing `angle`."""
        lib = self.prj.symbol_def(lib_id)
        bx, by = lib.body_direction()          # library axes
        native = _angle_of(bx, -by)
        rot = 0 if angle is None else (angle - native) % 360
        prefix = "#FLG" if "FLAG" in lib.name.upper() else "#PWR"
        key = "%s@%s" % (prefix, self._n + 1)
        self._n += 1
        s = Placed(self, lib, prefix + "?", (x, y), rot, None, 1, value, None, key, False, True, True, 1)
        s.auto = prefix
        self.symbols.append(s)
        return s

    # -- connecting pins ------------------------------------------------
    def connect_point(self, x, y, angle, net, kind="label", stub=2.54, shape="bidirectional"):
        """Draw a stub from (x, y) in direction `angle` and terminate it with `net`."""
        if net is None:
            self.no_connect(x, y)
            return
        a = math.radians(angle)
        ex, ey = _r4(x + stub * round(math.cos(a))), _r4(y - stub * round(math.sin(a)))
        if stub:
            self.wire((x, y), (ex, ey))
        if kind == "label":
            self.label(net, ex, ey, angle)
        elif kind == "global":
            self.global_label(net, ex, ey, angle, shape)
        elif kind == "hier":
            self.hier_label(net, ex, ey, angle, shape)
        elif kind == "power":
            self.power(net, ex, ey, angle)
        else:
            raise ValueError("unknown connection kind %r" % kind)

    def connect(self, sym, pin, net, kind="label", stub=2.54, shape="bidirectional"):
        """Connect one pin of a placed symbol: stub wire plus label / power symbol / no-connect."""
        x, y, a = sym.pin_xy(pin)
        self.connect_point(x, y, a, net, kind, stub, shape)

    def connect_many(self, sym, mapping, kind="label", stub=2.54):
        """mapping {pin: net or None}; net may be (net, kind) to override the kind."""
        for pin, net in mapping.items():
            k = kind
            if isinstance(net, tuple):
                net, k = net
            self.connect(sym, pin, net, k, stub)

    def connect_group(self, sym, pins, net, kind="power", stub=2.54, shape="bidirectional"):
        """Join several pins on the same side (VDD/VDDA, VSS pairs ...) to one rail with a
        single label or power symbol, instead of one terminator per pin."""
        pts = [sym.pin_xy(p) for p in pins]
        angles = {a for _, _, a in pts}
        if len(angles) != 1:
            raise ValueError("connect_group: pins %s are not on one side" % (pins,))
        a = angles.pop()
        dx, dy = round(math.cos(math.radians(a))), -round(math.sin(math.radians(a)))
        ends = []
        for x, y, _ in pts:
            e = (_r4(x + stub * dx), _r4(y + stub * dy))
            self.wire((x, y), e)
            ends.append(e)
        ends.sort()
        for e1, e2 in zip(ends, ends[1:]):
            self.wire(e1, e2)
        for e in ends[1:-1]:
            self.junction(*e)
        if len(ends) > 1:
            self.junction(*ends[0])
        self.connect_point(ends[0][0], ends[0][1], a, net, kind, stub=0, shape=shape)

    def wire_pins(self, a, pa, b, pb):
        """Direct wire (with one bend if needed) between two pins."""
        x1, y1, _ = a.pin_xy(pa)
        x2, y2, _ = b.pin_xy(pb)
        if x1 == x2 or y1 == y2:
            self.wire((x1, y1), (x2, y2))
        else:
            self.wire((x1, y1), (x2, y1), (x2, y2))

    # -- hierarchy ------------------------------------------------------
    def add_sheet(self, child, name, at, size, pins=(), ref_offset=0, key=None):
        """Place sheet file `child` here. pins: (name, shape[, side]) with shape in
        input/output/bidirectional/tri_state/passive and side left/right/top/bottom."""
        u = SheetUse(self, child, name, (snap(at[0]), snap(at[1])), size, pins, ref_offset, key)
        self.uses.append(u)
        return u

    def connect_sheet_pin(self, use, pin, net, kind="label", stub=2.54):
        x, y, a = use.pin_xy(pin)
        self.connect_point(x, y, a, net, kind, stub)


def _add_offset(a, b):
    """Reference offsets add up through nested sheets; an offset is an int (every
    prefix) or a {prefix: int} dict with "*" for every prefix not listed."""
    if isinstance(a, dict) or isinstance(b, dict):
        da = a if isinstance(a, dict) else {"*": a}
        db = b if isinstance(b, dict) else {"*": b}
        return {k: da.get(k, da.get("*", 0)) + db.get(k, db.get("*", 0)) for k in set(da) | set(db)}
    return a + b


def _offset_ref(ref, off):
    if not off or ref.startswith("#"):
        return ref
    m = re.match(r"^(.*?)(\d+)$", ref)
    if not m:
        raise ValueError("cannot offset reference %r" % ref)
    n = off.get(m.group(1), off.get("*", 0)) if isinstance(off, dict) else off
    return "%s%d" % (m.group(1), int(m.group(2)) + n)


class Project:
    """A hierarchy of sheet files rooted at an existing (or new) root schematic."""

    def __init__(self, root_path, name=None):
        self.root_path = os.path.abspath(root_path)
        self.dir = os.path.dirname(self.root_path)
        self.name = name or os.path.splitext(os.path.basename(self.root_path))[0]
        self.libs = {}
        self._defs = {}
        title, paper, ruuid, keep = self.name, "A4", None, []
        if os.path.exists(self.root_path):
            root = parse(open(self.root_path, encoding="utf-8").read())
            ruuid = find(root, "uuid")[1]
            paper = find(root, "paper")[1] if find(root, "paper") else paper
            tb = find(root, "title_block")
            keep = [tb] if tb else []
        self.ns = _uuid.UUID(ruuid) if ruuid else _uuid.uuid4()
        self.root = Sheet(self, os.path.basename(self.root_path), title, paper,
                          file_uuid=str(self.ns), extra=keep)
        self.sheets = {self.root.file: self.root}

    def uid(self, file, kind, key):
        return str(_uuid.uuid5(self.ns, "%s|%s|%s" % (file, kind, key)))

    def lib(self, nick, path):
        self.libs[nick] = SymbolLib(nick, path)

    def symbol_def(self, lib_id):
        if lib_id not in self._defs:
            nick, name = lib_id.split(":", 1)
            if nick not in self.libs:
                raise KeyError("library %r not registered (Project.lib)" % nick)
            self._defs[lib_id] = self.libs[nick].get(name)
        return self._defs[lib_id]

    def sheet(self, file, title=None, paper="A4"):
        if file not in self.sheets:
            self.sheets[file] = Sheet(self, file, title or os.path.splitext(file)[0].upper(), paper)
        return self.sheets[file]

    # -- hierarchy walk -------------------------------------------------
    def instances(self):
        """[(sheet, path_uuids, path_names, ref_offset, page)] in page order, root first."""
        out = []

        def walk(sheet, uuids, names, off):
            out.append((sheet, uuids, names, off, str(len(out) + 1)))
            for u in sheet.uses:
                walk(u.child, uuids + [u.uuid], names + [u.name], _add_offset(off, u.ref_offset))
        walk(self.root, [], [], 0)
        return out

    # -- writing --------------------------------------------------------
    def _symbol_node(self, s, inst_paths):
        lib = s.lib
        props = []
        skip = {"ki_keywords", "ki_fp_filters", "ki_description", "ki_locked"}
        fields = {k: v for k, v in lib.props.items() if k not in skip}
        fields["Value"] = s.value
        fields.update(s.fields)
        first_ref = inst_paths[0][1]
        fields["Reference"] = first_ref
        order = ["Reference", "Value", "Footprint", "Datasheet", "Description"]
        names = order + sorted(k for k in fields if k not in order)
        lib_props = {p[1]: p for p in findall(lib.node, "property")}
        for k in names:
            if k not in fields:
                continue
            lp = lib_props.get(k)
            if lp is not None and find(lp, "at") is not None and k in ("Reference", "Value"):
                at = find(lp, "at")
                dx, dy = _xform(float(at[1]), float(at[2]), s.rot, s.mirror)
                ang = (float(at[3]) if len(at) > 3 else 0) + s.rot
                ang = 90 if ang % 180 else 0
                pos = (s.at[0] + dx, s.at[1] + dy, ang)
            else:
                pos = (s.at[0], s.at[1], 0)
            hidden = k not in ("Reference", "Value") or (lp is not None and find(lp, "hide") == ["hide", "yes"])
            if lib.is_power and k == "Reference":
                hidden = True
            node = S("property", k, str(fields[k]), S("at", *pos))
            if hidden:
                node.append(S("hide", True))
            node += [S("show_name", False), S("do_not_autoplace", False),
                     S("effects", S("font", S("size", 1.27, 1.27)))]
            props.append(node)
        n = S("symbol", S("lib_id", lib.lib_id), S("at", s.at[0], s.at[1], s.rot))
        if s.mirror:
            n.append(S("mirror", Atom(s.mirror)))
        n += [S("unit", s.unit), S("body_style", s.body), S("exclude_from_sim", False),
              S("in_bom", s.in_bom and not lib.is_power), S("on_board", s.on_board),
              S("in_pos_files", s.on_board and not lib.is_power), S("dnp", s.dnp),
              S("uuid", s.uuid)]
        n += props
        for p in s.pins():
            n.append(S("pin", p.number, S("uuid", self.uid(s.sheet.file, "pin", s.uuid + "|" + p.number))))
        paths = [S("path", path, S("reference", ref), S("unit", s.unit)) for path, ref in inst_paths]
        n.append(S("instances", S("project", self.name, *paths)))
        return n

    def _sheet_node(self, u, parent_paths):
        x, y = u.at
        w, h = u.size
        n = S("sheet", S("at", x, y), S("size", w, h), S("exclude_from_sim", False), S("in_bom", True),
              S("on_board", True), S("dnp", False), S("fields_autoplaced", True),
              S("stroke", S("width", 0.1524), S("type", Atom("solid"))), S("fill", S("color", 0, 0, 0, 0)),
              S("uuid", u.uuid),
              S("property", "Sheetname", u.name, S("at", x, _r4(y - 0.7116), 0), S("show_name", False),
                S("do_not_autoplace", False),
                S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Atom("left"), Atom("bottom")))),
              S("property", "Sheetfile", u.child.file, S("at", x, _r4(y + h + 0.5846), 0),
                S("show_name", False), S("do_not_autoplace", False),
                S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Atom("left"), Atom("top")))))
        for name, shape, px, py, a in u.pins:
            j = {0: "right", 180: "left", 90: "right", 270: "left"}[a]
            n.append(S("pin", name, Atom(shape), S("at", px, py, a),
                       S("uuid", self.uid(u.parent.file, "sheetpin", u.uuid + name)),
                       S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Atom(j)))))
        n.append(S("instances", S("project", self.name,
                                  *[S("path", pp, S("page", page)) for pp, page in parent_paths])))
        return n

    def save(self, upgrade=True):
        """Write every sheet file, then have kicad-cli load and re-save each one."""
        insts = self.instances()
        root_uuid = self.root.uuid
        # number power / flag symbols across every placement of every file
        counters, auto_refs = {}, {}
        for sheet, uuids, names, off, page in insts:
            for s in sheet.symbols:
                if getattr(s, "auto", None):
                    counters[s.auto] = counters.get(s.auto, 0) + 1
                    auto_refs[(s.uuid, tuple(uuids))] = "%s%02d" % (s.auto, counters[s.auto])
        pages = {}
        for sheet, uuids, names, off, page in insts:
            pages[tuple(uuids)] = page
        written = []
        for file, sheet in self.sheets.items():
            mine = [(uuids, off) for sh, uuids, names, off, page in insts if sh is sheet]
            if not mine:
                raise ValueError("sheet %s is never placed in the hierarchy" % file)
            root = [Atom("kicad_sch"), S("version", Atom(SCH_VERSION)), S("generator", "eeschema"),
                    S("generator_version", "10.0"), S("uuid", sheet.uuid), S("paper", sheet.paper)]
            tb = [x for x in sheet.extra if x and x[0] == "title_block"]
            if tb:
                root += tb
            elif sheet.title:
                root.append(S("title_block", S("title", sheet.title)))
            libs, seen = [], set()
            for s in sheet.symbols:
                if s.lib.lib_id not in seen:
                    seen.add(s.lib.lib_id)
                    libs.append(s.lib.embedded())
            root.append([Atom("lib_symbols")] + sorted(libs, key=lambda n: n[1]))
            root += sheet.items
            for s in sheet.symbols:
                paths = []
                for uuids, off in mine:
                    path = "/" + "/".join([root_uuid] + uuids)
                    ref = auto_refs[(s.uuid, tuple(uuids))] if getattr(s, "auto", None) else _offset_ref(s.ref, off)
                    paths.append((path, ref))
                root.append(self._symbol_node(s, paths))
            for u in sheet.uses:
                parent_paths = [("/" + "/".join([root_uuid] + uuids), pages[tuple(uuids + [u.uuid])])
                                for uuids, off in mine]
                root.append(self._sheet_node(u, parent_paths))
            if sheet is self.root:
                root.append(S("sheet_instances", S("path", "/", S("page", "1"))))
            root.append(S("embedded_fonts", False))
            path = os.path.join(self.dir, file)
            with open(path, "w", encoding="utf-8") as f:
                f.write(dump(root) + "\n")
            written.append(path)
        if upgrade:
            # `sch upgrade` on the root only re-saves the root file, so every sheet file is
            # re-saved on its own (instance data for other sheet paths is preserved).
            for path in written:
                kicad_resave(path)
        return written


def kicad_resave(sch_path):
    """Load and re-save a schematic hierarchy with KiCad (proves it loads)."""
    r = subprocess.run([KICAD_CLI, "sch", "upgrade", "--force", sch_path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("kicad-cli sch upgrade failed:\n" + r.stdout + r.stderr)
    return r.stdout


def erc(sch_path, out_json=None):
    """Run ERC; returns (errors, warnings, violations list)."""
    import json
    out_json = out_json or os.path.splitext(sch_path)[0] + "-erc.json"
    subprocess.run([KICAD_CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", out_json, sch_path],
                   capture_output=True, text=True)
    d = json.load(open(out_json))
    v = [dict(x, sheet=s["path"]) for s in d["sheets"] for x in s["violations"]]
    return (sum(1 for x in v if x["severity"] == "error"),
            sum(1 for x in v if x["severity"] == "warning"), v)


def export_netlist(sch_path, out=None):
    out = out or os.path.splitext(sch_path)[0] + ".net"
    r = subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, sch_path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return out


def read_netlist(path):
    """Parse a kicadsexpr netlist -> (components, nets).
    components: {ref: {value, footprint, fields, path, sheetname, sheetfile, lib_id, dnp, ...}}
    nets: {name: [(ref, pin, pinfunction, pintype)]}"""
    root = parse(open(path, encoding="utf-8").read())
    comps = {}
    for c in findall(find(root, "components"), "comp"):
        ref = find(c, "ref")[1]
        sp = find(c, "sheetpath")
        tst = find(c, "tstamps")
        fields = {}
        fl = find(c, "fields")
        if fl:
            for f in findall(fl, "field"):
                name = find(f, "name")[1]
                fields[name] = f[2] if len(f) > 2 and isinstance(f[2], str) else ""
        props = {find(p, "name")[1]: (find(p, "value")[1] if find(p, "value") else "")
                 for p in findall(c, "property")}
        ls = find(c, "libsource")
        comps[ref] = {
            "ref": ref,
            "value": find(c, "value")[1] if find(c, "value") else "",
            "footprint": find(c, "footprint")[1] if find(c, "footprint") else "",
            "datasheet": find(c, "datasheet")[1] if find(c, "datasheet") else "",
            "fields": fields,
            "props": props,
            "lib_id": ("%s:%s" % (find(ls, "lib")[1], find(ls, "part")[1])) if ls else "",
            "sheetname": find(sp, "names")[1] if sp else "/",
            "sheetfile": "",
            "path": (find(sp, "tstamps")[1] if sp else "/") + (tst[1] if tst else ""),
            "dnp": "dnp" in props,
            "exclude_from_bom": "exclude_from_bom" in props,
            "exclude_from_board": "exclude_from_board" in props,
        }
        if "Sheetfile" in props:
            comps[ref]["sheetfile"] = props["Sheetfile"]
    nets = {}
    for n in findall(find(root, "nets"), "net"):
        name = find(n, "name")[1]
        nodes = []
        for nd in findall(n, "node"):
            pf, pt = find(nd, "pinfunction"), find(nd, "pintype")
            nodes.append((find(nd, "ref")[1], find(nd, "pin")[1], pf[1] if pf else "", pt[1] if pt else ""))
        nets[name] = nodes
    return comps, nets
