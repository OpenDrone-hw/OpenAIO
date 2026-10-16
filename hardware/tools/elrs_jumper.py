"""2026-10-16: "ELRS OFF" solder jumper JP2 (CHIP_EN to GND) and 1k series resistor R115 (GPIO27 to CHIP_EN).

Bridging JP2 holds the ESP32-C3 in reset with any firmware, so an external receiver on J54/J55 (or the DJI
SBUS on SH-6 pin 6) owns UART1. R115 keeps GPIO27 (PINIO1, ELRS_EN) from shorting into the bridged jumper
(3.3 mA worst case).

  $KPY tools/elrs_jumper.py footprint      writes lib.pretty/SolderJumper-2_P0.65mm_Tiny_Open.kicad_mod
  python3 tools/elrs_jumper.py schematic   lib.kicad_sym + rx_esp32c3_sx1281.kicad_sch (sexpdata)
then `kicad-cli sch upgrade --force rx_esp32c3_sx1281.kicad_sch` and prove it with ERC and a netlist diff.
"""
import copy
import sys
import uuid

FP = "SolderJumper-2_P0.65mm_Tiny_Open"
PAD_W, PAD_H, GAP = 0.45, 0.55, 0.20       # mm; 0.20 gap is bridged with a touch of solder


def footprint():
    import pcbnew as P
    MM = P.FromMM
    f = P.FOOTPRINT(None)
    f.SetFPID(P.LIB_ID("lib", FP))
    f.SetReference("JP**")
    f.SetValue(FP)
    f.SetAttributes(P.FP_SMD | P.FP_EXCLUDE_FROM_BOM)
    pitch = PAD_W + GAP
    for i, x in ((1, -pitch / 2), (2, pitch / 2)):
        p = P.PAD(f)
        p.SetNumber(str(i))
        p.SetAttribute(P.PAD_ATTRIB_SMD)
        p.SetShape(P.PAD_SHAPE_RECT)
        p.SetSize(P.VECTOR2I(MM(PAD_W), MM(PAD_H)))
        ls = P.LSET()
        ls.AddLayer(P.F_Cu)
        ls.AddLayer(P.F_Mask)           # no paste: the jumper ships open
        p.SetLayerSet(ls)
        p.SetPosition(P.VECTOR2I(MM(x), 0))
        f.Add(p)
    w, h = 2 * PAD_W + GAP, PAD_H
    mask = P.PCB_SHAPE(f)               # one opening over both pads and the gap, so solder can bridge it
    mask.SetShape(P.SHAPE_T_RECT)
    mask.SetStart(P.VECTOR2I(MM(-w / 2 - 0.05), MM(-h / 2 - 0.05)))
    mask.SetEnd(P.VECTOR2I(MM(w / 2 + 0.05), MM(h / 2 + 0.05)))
    mask.SetFilled(True)
    mask.SetLayer(P.F_Mask)
    mask.SetWidth(0)
    f.Add(mask)
    cy = P.PCB_SHAPE(f)
    cy.SetShape(P.SHAPE_T_RECT)
    cy.SetStart(P.VECTOR2I(MM(-w / 2 - 0.15), MM(-h / 2 - 0.15)))
    cy.SetEnd(P.VECTOR2I(MM(w / 2 + 0.15), MM(h / 2 + 0.15)))
    cy.SetLayer(P.F_CrtYd)
    cy.SetWidth(MM(0.05))
    f.Add(cy)
    f.Reference().SetLayer(P.F_Fab)
    f.Value().SetLayer(P.F_Fab)
    P.FootprintSave("lib.pretty", f)
    print("footprint", FP, f"{w:.2f} x {h:.2f} mm")


def schematic():
    import sexpdata as S
    sym = lambda x: str(x) if isinstance(x, S.Symbol) else None
    find = lambda n, h: [x for x in n if isinstance(x, list) and x and sym(x[0]) == h]
    r = lambda a: (round(float(a[1]), 2), round(float(a[2]), 2))

    def fresh(n):
        for x in n:
            if isinstance(x, list):
                if x and sym(x[0]) == "uuid":
                    x[1] = str(uuid.uuid4())
                else:
                    fresh(x)

    def prop(s, name, val):
        for p in find(s, "property"):
            if p[1] == name:
                p[2] = val

    std = S.loads(open("/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/Jumper.kicad_sym").read())
    jsym = copy.deepcopy(next(x for x in find(std, "symbol") if x[1] == "SolderJumper_2_Open"))
    prop(jsym, "Footprint", "lib:" + FP)
    # project library
    lib = S.loads(open("lib.kicad_sym").read())
    if not any(x[1] == "SolderJumper_2_Open" for x in find(lib, "symbol")):
        lib.append(copy.deepcopy(jsym))
        open("lib.kicad_sym", "w").write(S.dumps(lib))
    path = "rx_esp32c3_sx1281.kicad_sch"
    d = S.loads(open(path).read())
    cache = find(d, "lib_symbols")[0]
    if not any(x[1] == "lib:SolderJumper_2_Open" for x in find(cache, "symbol")):
        c = copy.deepcopy(jsym)
        c[1] = "lib:SolderJumper_2_Open"
        cache.append(c)
    # drop the ELRS_EN global label from the CHIP_EN wire; it moves to R115's far pin
    g = next(l for l in find(d, "global_label") if l[1] == "ELRS_EN")
    assert r(find(g, "at")[0]) == (255.27, 205.74)
    gl = copy.deepcopy(g)
    d[:] = [x for x in d if x is not g]
    r114 = next(s for s in find(d, "symbol") if find(s, "lib_id") and find(s, "lib_id")[0][1] == "lib:R"
                and r(find(s, "at")[0]) == (273.05, 205.74))
    oa_path = next(p for inst in find(r114, "instances") for pr in find(inst, "project") if pr[1] == "OpenAIO"
                   for p in find(pr, "path"))[1]

    def place(src, ref, x, y, ang, value=None, lib_id=None, fp=None, lcsc=""):
        s = copy.deepcopy(src)
        a = find(s, "at")[0]
        ox, oy = float(a[1]), float(a[2])
        a[1], a[2], a[3] = x, y, ang
        for p in find(s, "property"):
            pa = find(p, "at")[0]
            pa[1], pa[2] = round(float(pa[1]) - ox + x, 4), round(float(pa[2]) - oy + y, 4)
        if lib_id:
            find(s, "lib_id")[0][1] = lib_id
        prop(s, "Reference", ref)
        if value:
            prop(s, "Value", value)
        if fp:
            prop(s, "Footprint", fp)
        for k in ("LCSC", "LCSC Part"):
            prop(s, k, lcsc)
        s[:] = [x for x in s if not (isinstance(x, list) and x and sym(x[0]) == "instances")]
        s.append([S.Symbol("instances"), [S.Symbol("project"), "OpenAIO",
                  [S.Symbol("path"), oa_path, [S.Symbol("reference"), ref], [S.Symbol("unit"), 1]]]])
        fresh(s)
        return s

    r115 = place(r114, "R115", 256.54, 209.55, 0, value="1k")
    jp = place(r114, "JP2", 260.35, 210.82, 90, value="ELRS OFF", lib_id="lib:SolderJumper_2_Open",
               fp="lib:" + FP)
    pins = find(jp, "pin")                 # the jumper's pins are 1 and 2 as for R
    for p in pins:
        p[2:] = [[S.Symbol("uuid"), str(uuid.uuid4())]]
    find(gl, "at")[0][1:4] = [256.54, 213.36, 270]
    for p in find(gl, "property"):
        find(p, "at")[0][1:4] = [256.54, 213.36, 270]
    fresh(gl)
    wires, junctions = [], []
    tmpl_w = find(d, "wire")[0]
    for a, b in (((260.35, 215.9), (264.16, 215.9)), ((264.16, 215.9), (264.16, 213.36))):
        w = copy.deepcopy(tmpl_w)
        xy = find(find(w, "pts")[0], "xy")
        xy[0][1:3], xy[1][1:3] = list(a), list(b)
        fresh(w)
        wires.append(w)
    tmpl_j = find(d, "junction")[0]
    for pt in ((256.54, 205.74), (260.35, 205.74), (264.16, 213.36)):
        j = copy.deepcopy(tmpl_j)
        find(j, "at")[0][1:3] = list(pt)
        fresh(j)
        junctions.append(j)
    i = next((i for i, x in enumerate(d) if isinstance(x, list) and sym(x[0]) in ("sheet_instances", "embedded_fonts")),
             len(d))
    d[i:i] = [r115, jp, gl] + wires + junctions
    open(path, "w").write(S.dumps(d))
    print("rx sheet: R115 1k (ELRS_EN -> CHIP_EN), JP2 ELRS OFF (CHIP_EN -> GND)")


if __name__ == "__main__":
    {"footprint": footprint, "schematic": schematic}[sys.argv[1]]()
