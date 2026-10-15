"""Replace the tracks of high-current nets with copper pours that follow their route.

Run with KiCad closed, using KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/tools/track_to_pour.py hardware/<board>.kicad_pcb --net +BATT [--net ...] [--grow 0.3] [--dry-run]

For each named net and each copper layer it has tracks on, a zone is drawn over the union of those tracks and the
net's pads on that layer, grown by --grow mm: the pour widens the route as far as other-net copper allows and
takes at most --grow of the GND fill beside it. The zone sits one priority above the lowest zone on the board (the
GND fill), so every existing zone keeps its copper; existing zones move up one priority to make room. Pads connect
solid, clearance 0.10, minimum width 0.15. Then the net's tracks are removed one at a time (shortest first) with a refill after each; a track
whose removal leaves something unconnected goes straight back. Kelvin and measurement nets are never named here: their tracks stay tracks.
"""
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


pcbnew = quiet_import()
MM = pcbnew.FromMM


def main():
    a = sys.argv[1:]
    path = a[0]
    nets = [a[i + 1] for i, x in enumerate(a) if x == "--net"]
    grow = MM(float(a[a.index("--grow") + 1])) if "--grow" in a else MM(0.3)
    dry = "--dry-run" in a
    board = pcbnew.LoadBoard(path)
    filler = pcbnew.ZONE_FILLER(board)

    def unconnected():
        filler.Fill(board.Zones())
        board.BuildConnectivity()
        return board.GetConnectivity().GetUnconnectedCount(True)

    base = unconnected()
    zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
    floor = min(z.GetAssignedPriority() for z in zones)
    for z in zones:
        if z.GetAssignedPriority() > floor:
            z.SetAssignedPriority(z.GetAssignedPriority() + 1)
    removed = []
    for name in nets:
        net = board.GetNetInfo().GetNetItem(name)
        tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == name]
        pads = [p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNetname() == name]
        for layer in sorted({t.GetLayer() for t in tracks}):
            poly = pcbnew.SHAPE_POLY_SET()
            for t in tracks:
                if t.GetLayer() == layer:
                    t.TransformShapeToPolygon(poly, layer, grow, MM(0.005), pcbnew.ERROR_INSIDE)
            for p in pads:
                if p.IsOnLayer(layer):
                    p.TransformShapeToPolygon(poly, layer, grow, MM(0.005), pcbnew.ERROR_INSIDE)
            poly.Simplify()
            # One zone per outline: a zone with several outlines does not survive a save (one polygon is written).
            for i in range(poly.OutlineCount()):
                z = pcbnew.ZONE(board)
                z.SetLayer(layer)
                z.SetNet(net)
                z.SetZoneName(f"pour {name} {board.GetLayerName(layer)}")
                outline = z.Outline()  # the zone's own polygon set; SetOutline() would keep a pointer Python frees
                outline.AddOutline(poly.Outline(i))
                for h in range(poly.HoleCount(i)):
                    outline.AddHole(poly.Hole(i, h), 0)
                z.SetAssignedPriority(floor + 1)
                z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
                z.SetLocalClearance(MM(0.10))
                z.SetMinThickness(MM(0.15))
                z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
                board.Add(z)
            print(f"pour {name} on {board.GetLayerName(layer)}: {poly.OutlineCount()} outlines")
        removed += tracks
    base = unconnected()
    # One track at a time, shortest first: a track whose removal leaves something unconnected goes straight back.
    gone, kept = 0, 0
    for t in sorted(removed, key=lambda t: t.GetLength()):
        board.Remove(t)
        if unconnected() > base:
            board.Add(t)
            kept += 1
        else:
            gone += 1
    now = unconnected()
    print(f"{gone} tracks removed, {kept} kept (the pour does not connect without them); unconnected {base} -> {now}")
    if now > base:
        sys.exit("connectivity not restored; board not saved")
    print("run DRC: it must report the same unconnected count as before")
    if not dry:
        pcbnew.SaveBoard(path, board)
        print("saved")


if __name__ == "__main__":
    main()
