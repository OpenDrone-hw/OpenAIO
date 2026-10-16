# Battery input range: 3S to 6S

The input range the design supports, from the part ratings. Datasheets are in `hardware/KiCad-Library/datasheet/`.

**Result: 3S-6S LiPo (9.0-25.2 V). 2S is not supported.**

## What sets the floor: the gate-driver supply

The four NSG2065Q gate drivers (U14/U16/U18/U20) take VCC from +10V. +10V comes from U3, an LMR51430YFDD buck
(1.1 MHz, FPWM). R17/R18 (100 k / 6.49 k, VFB 0.6 V) set it to 9.84 V. Its EN is tied to +BATT, so +10V is on
whenever a pack is connected.

| Source | Value |
|---|---|
| NSG2065Q DS v1.0, §8.5 Recommended Operating Conditions (p5) | VCC 8-20 V; VB ≥ VS + 6 V |
| NSG2065Q §8.6.2 (p6) | VCC and VBS UVLO+ 4.5 V typ, 4.9 V max, 0.2 V hysteresis; RBSD ≤ 300 Ω; every characteristic is specified at VCC = VB = 15 V |
| NSG2065Q p1 feature list | "Gate drive supply range from 5 V to 20 V". This is the marketing bullet; §8.5 is the binding table |
| LMR51430 §7.5-7.6 (p5-6) | RDS(on) HS 0.12 Ω; VIN 4.5-36 V; DMAX 98 % with frequency foldback in dropout (§7.6 note 2) |

Below about 10.2 V in (9.84 V / 0.98, plus the drop across the high-side FET and L2), U3 is in dropout, and +10V
follows the pack at about VIN − 0.2-0.4 V.

| Pack | VIN (full / nominal / sagged at end of flight) | +10V = NSG2065Q VCC | VBS (VCC − bootstrap diode − Qg/Cboot ≈ 0.5 V) | Against §8.5 / UVLO |
|---|---|---|---|---|
| 2S | 8.4 / 7.4 / 6.0-6.4 V | 8.0-8.2 / 7.0-7.2 / 5.6-6.2 V | 4.6-7.6 V | VCC below 8 V for most of the flight. VBS below VS + 6 V, and at end of flight within 0-1 V of the 4.9 V max UVLO, so a high side can drop out mid-commutation |
| 3S | 12.6 / 11.1 / 9.0-9.6 V | 9.84 V regulated, 8.6-9.4 V when sagged | ≥ 7.6 V | Inside §8.5 down to about 8.4 V pack (2.8 V/cell) |
| 6S | 25.2 / 22.2 / 18-19 V | 9.84 V | ≈ 9 V | Inside |

Other 2S problems:
- **VTX supply.** +10V also feeds SH-6 pin 1 and the VTX pads. A digital air unit that needs 7.4 V or more
  (vendor figure, not checked here) browns out with the pack at 2S.
- **Bootstrap caps.** The fitted 100 nF bootstrap caps (CL05B104KB54PNC) are sized for VCC around 10 V. A 2S
  design would need about 190 nF (derived, not simulated).
- **MOSFETs.** The FETs are not the limit. DOY180N03T RDS(on) is 1.3/1.7 mΩ (typ/max) at VGS 4.5 V, against 1.0/1.2 mΩ
  at 10 V.

## What sets the ceiling: 6S

| Part | Limit | At 6S full (25.2 V) |
|---|---|---|
| Q3-Q26 DOY180N03T | VDS 30 V | About 2.8 V margin after an estimated 2 V turn-off overshoot  |
| U3/U4 LMR51430 | VIN 36 V | Inside |
| NSG2065Q | VS up to 250 V | Inside |
| U25 INA186 | Common mode −0.2 to 40 V | Inside |
| Bulk ceramics (CL21A475KBQNNNE) | 50 V | Inside |

The 6S margin relies on a low-ESR electrolytic on the battery leads for the +BATT bulk capacitance and hot-plug
damping. The on-board capacitors are ceramic only (C18 and C19 4.7 uF 50 V, plus C90 to C106, whose values are empty
in the schematic). A 6S build without that capacitor has no
margin left for regenerative braking or long leads.

## Gate-driver VCC decoupling

- **Fitted:** one 100 nF 0201 X5R 35 V (GRM033R6YA104KE14D) at each NSG2065Q VCC pin (C43/C50/C57/C64), about
  55 nF at 10 V.
- **What the datasheet asks for:** the NSG2065Q datasheet gives no value for the VCC capacitor.
  - The typical application circuit (Figure 10-2, p8) draws a "C1" from VCC to COM with no value.
  - No section of the text sizes it.
- **Result:** the datasheet asks for no more than is fitted.
- **Effect at 3S and above:** a VCC dip is estimated of about 0.7 V on each low-side turn-on
  (Qg 39.8 nC from about 55 nF, derived).
  - From 8.6-9.84 V of VCC, that dip still leaves at least 3 V above the 4.9 V UVLO.
  - The gate drive falls by the same 0.7 V. At these VGS values the FET RDS(on) is flat (see above).
- **Effect at 2S:** the same dip lands within 0-1 V of UVLO. This is another reason not to claim 2S.
- **If 2S is ever wanted:** add a 1 µF 25 V 0402 (CL05A105KA5NQNC, catalogue part) at each VCC pin, together with a
  VCC boost and 220 nF bootstrap caps.
