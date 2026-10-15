"""OpenAIO high-current paths: copper resistance and I2R loss per path, vias included.

Run with KiCad's bundled Python; the board is only read:
  $KPY hardware/tools/power_paths.py hardware/OpenAIO.kicad_pcb [--esc 15] [--buck 0.5] [--temp 45] [--grid 0.1]

Uses the solver of loop_resistance.py (copper rasterised per layer, thickness from the board stackup, via barrels).
Paths, battery-side currents in 6-step commutation:
  battery + pad (U24.1, /CSA+) to the shunt Rsense2          4 x ESC + 2 x buck
  +BATT from the shunt to every high-side FET drain (F.Cu, pin 3) and the bucks U3/U4
  GND from every low-side FET source (B.Cu, pin 1) and the bucks to the battery - pad (U24.2)
  each phase: motor pad (U24) to its high-side source and low-side drain, I x sqrt(2/3) RMS
FET RDS(on) and the 0.2 mOhm shunt are parts, not copper; the shunt is listed for scale.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loop_resistance as LR  # noqa: E402

pcbnew = LR.pcbnew


def main():
    a = sys.argv[1:]
    path = a[0]
    i_esc, i_buck = LR.arg(a, "--esc", 15.0), LR.arg(a, "--buck", 0.5)
    B = LR.Board(path, LR.arg(a, "--grid", 0.1), LR.arg(a, "--temp", 45))
    fp = {f.GetReference(): f for f in B.b.GetFootprints()}

    def pads(ref, net, num=None):
        return [p for p in fp[ref].Pads() if p.GetNetname() == net and (num is None or p.GetNumber() == num)]

    fets = [f for f in B.b.GetFootprints() if f.GetReference().startswith("Q") and f.GetValue().startswith("DOY")]
    high = [f for f in fets if any(p.GetNetname() == "+BATT" for p in f.Pads())]
    low = [f for f in fets if any(p.GetNetname() == "GND" for p in f.Pads())]
    bucks = [r for r in ("U3", "U4") if r in fp]
    i_total = 4 * i_esc + len(bucks) * i_buck
    rows = []
    d, w, wv = LR.solve(B, "/CSA+", pads("U24", "/CSA+"), [(pads("Rsense2", "/CSA+"), i_total)], "CSA+")
    rows.append(("battery + pad to shunt (/CSA+)", i_total, d[0] / i_total, w, wv))
    rows.append(("shunt Rsense2 0.2 mOhm (part)", i_total, 0.2e-3, i_total ** 2 * 0.2e-3, 0.0))
    sinks = [(pads(q.GetReference(), "+BATT"), i_esc / 3) for q in high] + [(pads(u, "+BATT"), i_buck) for u in bucks]
    d, w, wv = LR.solve(B, "+BATT", pads("Rsense2", "+BATT"), sinks, "+BATT")
    rows.append(("+BATT shunt to 12 high-side FETs + bucks", i_total, w / i_total ** 2, w, wv))
    sinks = [(pads(q.GetReference(), "GND"), i_esc / 3) for q in low] + [(pads(u, "GND"), i_buck) for u in bucks]
    d, w, wv = LR.solve(B, "GND", pads("U24", "GND", "2"), sinks, "GND")
    rows.append(("GND 12 low-side FETs + bucks to battery -", i_total, w / i_total ** 2, w, wv))
    i_ph = i_esc * math.sqrt(2 / 3)
    ph_r, ph_w, ph_v = [], 0.0, 0.0
    for q in high:
        net = next(p.GetNetname() for p in q.Pads() if p.GetNetname().startswith("/") and p.GetNetname()[1:2].isdigit())
        lo = [f for f in low if any(p.GetNetname() == net for p in f.Pads())][0]
        mot = pads("U24", net)
        sinks = [(pads(q.GetReference(), net), i_ph / 2), (pads(lo.GetReference(), net), i_ph / 2)]
        d, w, wv = LR.solve(B, net, mot, sinks, net)
        ph_r.append(w / i_ph ** 2); ph_w += w; ph_v += wv
    rows.append((f"12 phases, motor pad to FETs (mean, min-max {min(ph_r)*1e3:.2f}-{max(ph_r)*1e3:.2f})", i_ph,
                 sum(ph_r) / len(ph_r), ph_w, ph_v))
    print(f"copper at {LR.arg(a, '--temp', 45):.0f} C, grid {LR.arg(a, '--grid', 0.1)} mm, ESC {i_esc} A each, "
          f"bucks {i_buck} A each, battery {i_total} A")
    print(f"{'path':58} {'I (A)':>6} {'R (mOhm)':>9} {'P (W)':>7} {'in vias':>8}")
    for name, i, r, w, wv in rows:
        print(f"{name:58} {i:6.2f} {r * 1e3:9.3f} {w:7.2f} {wv:8.2f}")
    print(f"{'total copper + shunt':58} {'':6} {'':9} {sum(r[3] for r in rows):7.2f}")


if __name__ == "__main__":
    main()
