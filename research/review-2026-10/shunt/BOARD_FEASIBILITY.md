# Copper current sense on the OpenAIO Base: feasibility (board a236148)

Question: can Rsense2 (0.2 mOhm 2512, read by INA186A3 U25 at 100 V/V) be deleted, with U25 reading a Kelvin-tapped
section of copper that the battery current already flows through?

**Verdict: keep a shunt.**
- The only usable copper section is the existing B.Cu battery strap: about 0.14 mOhm, with a 0.5 % spread across motors.
- Using it saves little: 0.60 W at 4 x 25 A in the best layout without design-rule violations.
- It brings a ±15 % (worst ±26 %) initial tolerance and a +0.39 %/K drift (+24 % at 90 °C).
  Betaflight cannot correct either without per-board calibration and a temperature patch.
- The vias that collect the current after the strap carry 4-13 A each at 80 A.
- A 0.1 mOhm shunt with an INA186A4 saves more (1.0 W at 4 x 25 A) with none of these risks.

Repo untouched. Scratch copy: `research/shunt/board/hardware` (from `git archive a236148`; KiCad-Library symlinked;
.kicad_pro/.kicad_dru next to the board, zones refilled by `lr_dump.py`). Scripts: `research/shunt/py/`. Images: `research/shunt/img/`.

## Method

- Solver: the 3-D DC solver from review-2026-10 (`lr_dc.py`), copied to `py/` and run on the refilled a236148 dump.
  - Copper: F/B 70 µm, inner 35 µm. Via plating 25 µm (the review used 20 µm). ρ = 1.72e-8 Ω·m at 20 °C.
  - Grid h = 0.05 mm. A convergence check at h = 0.035 changed the strap value by +0.8 % and the effective path R by −1.5 %.
- Source and loads:
  - Source: the battery + pad U24.1 at 0 V. Two attachment models for the battery lead:
    - `pad`: the whole F+B pad sits at the wire potential.
    - `hole`: only copper within 2 mm of the 3 mm hole does.
  - Loads: 1 A drawn at each high-side drain (pad 3 of Q3…Q25). The motor groups are:

    | Motor | HS FETs |
    |---|---|
    | M1 | Q3/5/7 |
    | M2 | Q9/11/13 |
    | M3 | Q15/17/19 |
    | M4 | Q21/23/25 |

  - "Motor" = the mean of its 3 HS FETs, i.e. the commutation average seen behind the R5/C9 filter. "All" = 0.25 A per motor.
  - Buck loads U3/U4 VIN are also checked.
- Reading: sensed V per A between two taps (each tap = mean over a 0.15 mm radius).
  - Motor spread = (max − min over M1..M4) / All.
  - FET spread = the same over the 12 single FETs (instantaneous, before filtering).
- Variants (the copper outside each change is as built; the net-tie keeps the battery pad off the F/In4/In5 pours):
  - **V0**: as built. Strap, then the 0.2 mOhm shunt, then the pad-2 via field.
  - **V1**: Rsense2 replaced by a B.Cu net-tie bridge the size of the 2512 (pad hull, 23.9 mm²).
  - **V1w**: as V1, plus all free B area round the old shunt (39.7 mm²).
  - **V2 / V2i**: V1 plus 8 vias on DRC-clean sites / 13 vias if the In2/In3 signals are moved.
  - **V2w**: V1w plus 16 vias on DRC-clean sites, ≥ 0.6 mm downstream of the −IN tap. A 24-via version assumes the inner signals are moved.
  - **V3**: battery pad tied straight into F/In4/In5 (the gaps filled), strap kept.
  - **V4**: pad tied into F only, strap removed.

## 1. Candidate sections and their stability across motors

Values are mOhm (= mV per A).

| # | Section (+tap → −tap) | Variant | R all | M1 / M2 / M3 / M4 | Motor spread | FET spread | Lead-attach change |
|---|---|---|---|---|---|---|---|
| A | F battery-pad edge (67.48,48.25) → VP (65.54,50.78), B strap | V2w | 0.1666 | 0.1662 / 0.1664 / 0.1670 / 0.1669 | 0.49 % | 0.54 % | **+48 %** (`hole` vs `pad`) |
| B | strap start B (66.90,48.60) → VP | V2w | 0.1644 | 0.1639 / 0.1641 / 0.1647 / 0.1646 | 0.49 % | ~0.5 % | −1.2 % |
| **C** | **strap B (66.75,49.00) → VP** (recommended taps if copper) | V2w | **0.1392** | 0.1388 / 0.1389 / 0.1395 / 0.1394 | **0.56 %** | ~0.65 % | **−1.8 %** |
| C' | same, vias kept ≥ 1.5 mm past VP | V2w, 13 vias | 0.1333 | equal to 4 digits | 0.03 % | 0.03 % | −1.8 % |
| D | battery pad → VP | V1 | 0.1696 | 0.1696 x4 | 0.00 % | 0.00 % | (as A) |
| E | net-tie bridge VP → K2 (61.02,53.09) | V1 | 0.3490 | 0.3491 / 0.3491 / 0.3489 / 0.3490 | 0.05 % | 0.06 % | — |
| E' | same bridge once vias feed the planes | V2w | 0.147 | 0.160 / 0.155 / 0.134 / 0.137 | **17.8 %** | ~19 % | — |
| F | battery pad → K2 | V1 | 0.5187 | 0.5188 / 0.5187 / 0.5186 / 0.5186 | 0.03 % | 0.04 % | — |
| G | +BATT planes, pad tied in (V3): VP | V3 | 0.037 | 0.053 / 0.047 / 0.021 / 0.026 | **88 %** | — | — |
| G' | V3, best tap anywhere with spread ≤ 2 % / ≤ 5 % | V3 | 0.010 / 0.066 | — | 2 % / 5 % | 4 % / 9 % | — |
| H | GND: battery − pad → U25 GND (F 68.4,52.2) | as built | 0.0785 | 0.104 / 0.096 / 0.042 / 0.073 | **79 %** | — | — |
| H' | GND: − pad → In1 6 mm below the pad | as built | 0.0502 | 0.059 / 0.058 / 0.033 / 0.052 | 51 % | — | — |
| H" | GND: best tap on any layer with spread ≤ 2 % / ≤ 10 % | as built | 0.0016 / 0.0094 | — | 2 % / 10 % | 4 % / 24 % | — |

Buck (U3/U4) current reads the same as motor current on the strap (+0.06 %).

What the table shows:
- The B strap is the only section that all the battery current crosses on one layer.
  - It is stable: spread ≤ 0.6 %, and below 0.05 % when no via sits within 1.5 mm of the −IN tap.
  - The +tap must not be on the battery pad. Where the battery lead wets the pad moves the reading by 48 %.
  - Moving the +tap 0.4 mm onto the strap cuts that to 1-2 %.
- A net-tie bridge (E/F) is stable only while it carries all the current to the old pad-2 via field. That costs loss (section 5).
  Once vias let current leave early, the spread is 18 %.
- Plane sections fail:
  - +BATT with the pad tied in: below 2 % spread only at 0.01 mOhm.
  - GND return: below 2 % spread only at 0.0016 mOhm (0.16 mV at 100 A). The useful 0.05-0.08 mOhm taps show 50-80 % spread,
    because M3's return current reaches the − pad from the other side.

Maps: `img/map_V2w.png` (strap potential and motor spread, with taps and vias), `img/map_V3.png`.

## 2. Tolerances and temperature (section C, 0.139 mOhm)

These are assumptions: NEXTPCB.md gives no copper-thickness or etch tolerance (UNCONFIRMED; ask NextPCB).

| Item | Basis | Effect on R |
|---|---|---|
| Finished 2 oz outer thickness (~1 oz foil + ~35 µm plating) | ASSUMED: foil ±10 % (IPC-4562 weight), plating distribution ±20-25 % | ±15 % typical, ±20 % lot to lot |
| Etch on a 3.2-4.4 mm strap (measured, `strapw.py`) | ASSUMED: undercut 25-50 µm per edge on 70 µm Cu | −1 to −3 % (systematic) |
| Battery-lead attachment | solved (+tap at B3) | −1.8 % |
| INA186 gain error | datasheet max | ±1 % |
| **Initial total** | | **±15 % RSS, ±26 % worst case: per-board calibration is mandatory** |

The strap must stay under solder mask. A mask opening would let solder change R by an unknown amount.

**Temperature (copper TCR 0.00393/K, calibrated at 30 °C):**

| Board temperature | Copper section error (α·ΔT) | Copper, R20-referenced | 0.2 mOhm alloy shunt (ASSUMED 75 ppm/K) |
|---|---|---|---|
| 60 °C | +11.8 % | +11.3 % | +0.2 % |
| 90 °C | +23.6 % | +22.7 % | +0.45 % |
| 110 °C | +31.4 % | +30.3 % | +0.6 % |

The section is also a heater:
- It dissipates 1.4 W at 100 A and 2.0 W at 120 A in about 10 mm² beside the battery joint.
- No existing sensor sits on it (the AT32 and RP2354 die sensors are elsewhere).
- Each 10 K of unmeasured local rise adds 3.9 % error. Readings run high, so mAh is over-counted.

## 3. INA186 check

- Common mode: 2S-6S (6.0-25.2 V) is inside −0.2…40 V, unchanged.
- Output limit: VSP = VS − 40 mV = 3.26 V. ADC: RP2354, 12 bit at 3.3 V (0.806 mV/LSB).

| Current | 0.2 mOhm shunt: Vsense / A3 out | Copper 0.139 mOhm: Vsense / A3 out | Copper 0.139: A4 out |
|---|---|---|---|
| 10 A | 2.0 mV / 0.20 V | 1.39 mV / 0.139 V | 0.28 V |
| 50 A | 10.0 mV / 1.00 V | 6.95 mV / 0.695 V | 1.39 V |
| 100 A | 20.0 mV / 2.00 V | 13.9 mV / 1.39 V (43 % of range) | 2.78 V |
| 160 A | 32.0 mV / 3.20 V (98 %) | 22.2 mV / 2.22 V (68 %) | clips at 117 A |

| Element + gain | mV/A | Full scale | ADC step | Vos ±50 µV | Zero-current out ≤10 mV | CMRR 2S→6S | Vos drift 80 K |
|---|---|---|---|---|---|---|---|
| 0.2 mOhm, A3 (as built) | 20.0 | 163 A | 40 mA | ±0.25 A | 0.50 A | 0.10 A | 0.20 A |
| Cu 0.139, A3 | 13.9 | 235 A | 58 mA | ±0.36 A | 0.72 A | 0.14 A | 0.29 A |
| Cu 0.139, A4 | 27.8 | 117 A | 29 mA | ±0.36 A | 0.36 A | 0.14 A | 0.29 A |
| Cu 0.164 (INA on B), A3 | 16.4 | 199 A | 49 mA | ±0.30 A | 0.61 A | 0.12 A | 0.24 A |
| 0.1 mOhm shunt, A4 | 20.0 | 163 A | 40 mA | ±0.50 A | 0.50 A | 0.19 A | 0.40 A |

- Gain error is ±1 % max and gain drift 10 ppm/K. Both are negligible next to copper TCR, and calibration removes the gain error.
- Gain choice for copper: **keep A3.** A4 clips at 117 A, below 4 x 30 A plus bursts. A1/A2 waste resolution. A5 clips at 47 A.

## 4. Betaflight values and production calibration

Betaflight ADC current meter: I[mA] = mV·10000/`ibata_scale` + `ibata_offset`.
- `ibata_scale` is in 0.1 mV/A, so scale = 10 x R[mOhm] x G.
- `ibata_offset` is in mA.

| Element | ibata_scale (nominal) | Spread to expect | ibata_offset |
|---|---|---|---|
| 0.2 mOhm shunt + A3 (as built) | 200 | ±2 % (shunt ±1 % ASSUMED + INA ±1 %): fixed in the target | −V0·10000/200 (V0 = 2 mV typ → −100 mA) |
| Cu section C + A3 | 139 | 118…160 (±15 %): per board | −V0·10000/139 (2 mV → −144 mA) |
| Cu section B (U25 on B) + A3 | 164 | 139…189 | −V0·10000/164 |
| 0.1 mOhm + A4 | 200 | as the shunt | as the shunt |

The scale is an integer, so copper can be set no finer than 0.72 % per step (139).

**Proposed QC-jig calibration step** (after the AT32 flash, before the motor spin test, about 10 s):
1. The jig feeds the battery pads from its supply, with a reference current meter. For example a 1 mOhm 0.1 % shunt with a 16-20 bit monitor, or a supply readback better than ±0.5 %.
   The +tap sits on the strap, not on the pad, so where the pogo pins land changes the result by less than 2 %.
2. The jig flashes a short AT32 test image: hold one phase high (HS FET on, LS off), on command.
   An electronic load from that phase pad to GND sinks I1 = 2 A, then I2 = 20 A, for 0.2 s each.
   Both points must be above the INA's 0.7 A zero-current region.
   Fallback without an e-load: spin all four motors unloaded at two throttles and use the supply readback (about 1.5 A and 6-8 A; gain uncertainty about 1 %).
3. Read the FC's CURR millivolts over MSP (`debug_mode = CURRENT_SENSOR`, debug[0] = mV), averaging 256 samples per point.
4. Compute and write:
   - `scale = round(10·(mV2 − mV1)/(I2 − I1))`
   - `offset = round(I1[mA] − mV1·10000/scale)`
   - Write with `set ibata_scale`, `set ibata_offset`, `save` (or MSP_SET_CURRENT_METER_CONFIG).
5. Repeat at 10 A on each motor's phase in turn (M1..M4). Pass if within ±2 %.
   This also checks the copper spread (< 1 % expected) and every HS FET.
6. Log the AT32 die temperatures as T_cal. The target's default scale = lot median; `defaults` or a reflash loses the per-board value.
7. Temperature: Betaflight has no current-meter temperature compensation.
   - Without a firmware patch, readings run +12 % at 60 °C and +24 % at 90 °C.
   - A patch I/(1 + 0.0039(T − T_cal)) using EDT (extended DShot telemetry) ESC temperature leaves about ±2-4 %, plus the strap's untracked self-heating.

## 5. Board impact

**Loss on the battery + path**
- Path: battery wire to the 12 HS drains. R eff = mean over phase sets A/B/C, all four motors equal. Loss = R eff x I².
- GND is unchanged in every variant.
- Shunt solder joints are not modelled: they add a little to V0, so savings are slightly understated.

| Variant | R eff (mOhm) | Per-FET R from wire, mean / max (mOhm) | Loss 4x20 / 4x25 / 4x30 A (W) | Saved vs V0 (W) | Hottest via at 80 A |
|---|---|---|---|---|---|
| V0 as built (strap + 0.2 mOhm) | 0.662 | 0.958 / 1.209 | 4.24 / 6.62 / 9.54 | — | 2.8 A (pad-2 field) |
| V1 net-tie bridge in 2512 outline | 0.868 | 1.164 / 1.414 | 5.56 / 8.68 / 12.50 | **−1.32 / −2.06 / −2.97** | 6.1 A |
| V1w wide B bridge, no new vias | 0.803 | 1.099 / 1.349 | 5.14 / 8.03 / 11.57 | −0.90 / −1.41 / −2.03 | 5.3 A |
| V2 bridge + 8 vias (DRC-clean) | 0.627 | 0.918 / 1.136 | 4.01 / 6.27 / 9.03 | +0.23 / +0.35 / +0.51 | **15.2 A** |
| V2i bridge + 13 vias (inner signals moved) | 0.621 | 0.911 / 1.130 | 3.98 / 6.21 / 8.94 | +0.26 / +0.41 / +0.59 | 14.7 A |
| **V2w wide + 16 vias (DRC-clean)** | **0.602** | 0.893 / 1.113 | 3.85 / 6.02 / 8.67 | **+0.38 / +0.60 / +0.86** | **12.7 A** (5 vias > 4 A) |
| V2w wide + 24 vias (inner signals moved) | 0.597 | 0.887 / 1.108 | 3.82 / 5.97 / 8.59 | +0.42 / +0.65 / +0.94 | — |
| V2w, 13 vias ≥ 1.5 mm past −IN (spread 0.03 %) | 0.688 | 0.981 / 1.215 | 4.41 / 6.88 / 9.91 | −0.17 / −0.26 / −0.38 | 12.8 A |
| V3 pad into F/In4/In5 (**no stable section**) | 0.300 | 0.579 / 0.820 | 1.92 / 3.00 / 4.32 | +2.32 / +3.62 / +5.21 | 9.2 A (pad PTH) |
| V4 pad into F only, strap removed | 0.848 | 1.142 / 1.463 | 5.43 / 8.48 / 12.21 | −1.19 / −1.86 / −2.68 | — |
| *Reference: 0.1 mOhm shunt + A4 in the same place* | 0.562 | 0.858 / 1.109 | 3.60 / 5.62 / 8.09 | **+0.64 / +1.00 / +1.44** | 2.8 A |

Why the saving is small:
- A 2512-sized copper bridge (0.35 mOhm) has more resistance than the 0.2 mOhm alloy shunt.
- Current only leaves the strap early if vias go right at its end. That spot is crowded by the In2/In3 signal tracks and by the F parts (U25, C104, L3).
- So the first via row takes 4-13 A per 0.20 mm via, against 2.8 A today. Fixing that means re-routing In2/In3, which still saves only about 0.6 W.
- The real loss lever is the path, not the shunt. V3 shows the strap, shunt and pad-2 detour together cost 0.36 mOhm (3.6 W at 4 x 25 A).
  But a direct pad-to-plane tie leaves nothing single-path for any sensor, shunt or copper.

**Area**
- Deleting Rsense2 frees the 2512 outline: about 24 mm² of pads and body, about 32 mm² of courtyard, on B.
- In every copper-sense variant that area becomes the +BATT junction copper and via field. No part area is gained.
- Gained: the part height, one BOM line (C695806) and two large solder joints.

**Taps and U25 placement (copper option)**
- U25 stays on F at (67.15,51.55).
- −IN = the existing VP via (65.54,50.78), re-pointed from pin 4 to pin 5.
- +IN = a new via at (66.75,49.00) on the strap. Its F annulus must stay ≥ 0.2 mm off the F battery pad, or the via becomes a current path. Route it on F to pin 4 through a new F keepout channel.
- Alternative: U25 on B beside the strap, using section B (0.164 mOhm), with no tap vias.
- Delete the K2 B trace, the VM via (65.46,51.83) and its 'kelvin -IN' (In4/In5) and 'kelvin -IN F' rule areas.
- In the schematic, replace Rsense2 with a 4-terminal net-tie footprint (battery in, sense +, sense −, +BATT), so the INA inputs stay on separate nets.

**Rule areas**
- Shrink 'csa feed' (all-layer no-vias, 64.22-69.65 x 47.55-52.65, plus B no-tracks) to the strap. It should end 0.6-1.5 mm past VP, so the junction vias can go in.
- Keep a no-via, no-track zone over the strap itself.

**Plane resistance**
- +BATT planes are unchanged. Per-FET R from the battery wire drops 7 % (0.958 → 0.893 mOhm mean, V2w), because the shunt goes.
- GND is unchanged: battery − pad to LS source 0.353 mOhm mean (0.180-0.457).

## 6. Recommendation

**Keep a shunt.** Two options:

1. **Keep the as-built shunt.** 0.2 mOhm (C695806, ASR-S-3-0.2F) with INA186A3, Betaflight scale 200, no calibration.
2. **If loss matters, change to 0.1 mOhm.** A 0.1 mOhm 2512 metal-strip shunt with **INA186A4**.
   - Betaflight scale stays 200 and full scale stays 163 A.
   - Saves 0.64 / 1.0 / 1.44 W at 4 x 20 / 25 / 30 A, more than any realistic copper layout, with no calibration and no TCR term.
   - Bourns CSS2H-2512 lists 2512 values down to 0.1 mOhm. The exact part, TCR (≤ 75 ppm/K wanted) and NextPCB stock are UNCONFIRMED.
   - Costs: offset ±0.5 A instead of ±0.25 A, and the Kelvin tap position on the pads matters twice as much (follow the vendor land pattern).

**If copper is chosen anyway:**
- Use section C (B strap (66.75,49.00) → old pad-1 inner edge, 0.139 mOhm, motor spread 0.56 %), INA186A3, Betaflight scale about 139 (per board).
- The jig calibration in section 4 is required.
- Main risks:
  1. Copper TCR (+12 % at 60 °C, +24 % at 90 °C, +31 % at 110 °C), worsened by the strap's own 1.4 W at 100 A. Stock Betaflight cannot compensate.
  2. ±15-26 % initial tolerance from plating thickness.
  3. 4-13 A per via where the strap drops into the planes.
- A +tap on the battery pad would add a 48 % dependence on how the lead is soldered. That changes every time a user re-solders an XT60 pigtail.

## Files

All under `research/shunt/py/`.

| File | Purpose |
|---|---|
| `lr_dc.py`, `lr_common.py`, `lr_dump.py` | Solver, copied; plating set to 25 µm |
| `csmod.py` | Variant builders, taps |
| `cs_v0.py` | As-built baseline |
| `cs_run.py` | V1-V4 runs: taps, scan, loss |
| `cs_taps.py` | +tap position vs lead attachment |
| `cs_gnd.py` | GND scan |
| `v2vias.py` | DRC-aware via sites |
| `cs_vias.py` | Via currents |
| `summary.py` | Loss table |
| `ina_tol.py` | INA / Betaflight / TCR numbers |
| `strapw.py` | Strap width |
| `regplot.py`, `obsplot.py`, `mapplot.py` | Figures |

Outputs: `*.txt` next to each script. Run each one with `prlimit --as=5368709120 -- /usr/bin/python3 -I <script>`.
