# NextPCB capabilities and rule sets for OpenAIO Core and Base

Researched 2026-10-06 from NextPCB's own pages, its online order form (option
lists from the order-form JavaScript, help text from the order form's
language feed), its stackup library and its help centre. Every number carries a
source tag `[Sx]`, and the URLs are listed in section 6.

Labels used below:

- **UNCONFIRMED**: NextPCB publishes nothing on this, or its pages disagree. Ask
  the account manager before you rely on it.
- **derived**: computed from published numbers, not published itself.
- **$ / time**: NextPCB says the option raises the price and/or the lead time.

The boards:

- **Core**: 6 layers, 0.8 mm, 1 oz outer. RP2354A QFN-60 at 0.4 mm pitch,
  BMI270 LGA-14, 0201 passives. LGA module, 34 pads of 1.0 mm.
- **Base**: 8 layers, 1.6 mm, 2 oz outer and 1 oz inner. 24x PowerDI3333-8 on
  both sides, QFN-28 at 0.4 mm, QFN-32 at 0.5 mm, 0201 passives.

NextPCB's pages disagree in places: microvia 0.075 vs 0.1 mm, fine pitch
0.38 vs 0.35 vs 0.25 mm, impedance ±5 vs ±3 %, edge rail 3 vs 5 mm. Where they
do, both values are shown, and the rule sets use the more conservative one.

---

## 1. Capability table

### 1.1 Fabrication

| Item | Standard PCB (online order) | Advanced PCB / HDI | Price or lead-time impact |
|---|---|---|---|
| Max layers | Capability page: 1-32 [S1]. Standard order form: 1, 2, 4 ... 22 [S8] | Up to 32 [S2]. Advanced order form: up to 40, plus custom [S8]. High-speed: up to 40 [S2] | Standard to Advanced: "Low, from $5" vs "from less than one hundred to thousands"; "from 24 hours" vs "few days to weeks" [S2] |
| Board thickness | 0.6/0.8/1.0/1.2/1.6/2.0/2.5/3.0/3.2 mm [S1] | 0.2-3.2 mm in 0.1 mm steps, plus custom [S8] | |
| Thickness tolerance | ±10 % for ≥1.0 mm, so 1.6 mm = 1.44-1.76. ±0.1 mm below 1.0 mm, so 0.8 mm = 0.7-0.9 [S1] | | |
| Outer copper (finished) | 1 / 2 oz [S1]. Order form: 0.5-6 oz [S8] | Up to 10 oz [S2]. Order form: 1-6 oz plus custom [S8] | |
| Inner copper | 0.5 / 1 / 2 oz [S1]. Order form: 0.5-6 oz [S8] | 4-6 oz max [S2] | |
| **Mixed 2 oz outer + 1 oz inner** | **Available.** Outer and inner weight are separate order-form fields [S8] | Same [S8] | Impedance control is **not offered when finished copper is ≥2 oz** [S7] |
| Min track / space, 0.5 oz inner | 2.5 mil (0.064) / 3 mil (0.076) mm [S1] | | |
| Min track / space, 1 oz outer | 3 / 3 mil (0.076 mm) [S1] | 2.5/2.5 mil advanced [S2]. HDI 2/2 mil (0.05 mm) [S2] | Order-form steps: 10/8/6/5/4/3.5/3/2 mil. Default 6/6 [S8][S7]. The price of each step is UNCONFIRMED |
| Min track / space, 2 oz outer | 5.5 / 5.5 mil (0.14 mm) [S1] | 3 oz: 8/8 mil [S2] | |
| Min track / space, 1 oz inner | **UNCONFIRMED** (no table row). NextPCB's own 8L 1.6 mm, 1 oz inner stackup routes 90 Ω pairs at W 4.0 / S 4.0 mil on L3 [S6] | HDI table: 3.5/3.5 mil, copper weight not stated [S3] | |
| Min mechanical drill | 0.15 mm, **only for board thickness ≤1.2 mm**. Max 6.5 mm [S1]. Order form: 1.0 down to 0.1 mm [S8] | 0.15 mm (6 mil), 20:1 aspect ratio [S2] | Older page: "0.2 mm to 6.3 mm ... does not need extra charges" [S18]. So 0.15 mm is a surcharge (amount UNCONFIRMED) |
| Drill tolerance | ≤0.05 mm. PTH ±0.075, NPTH ±0.05 [S1] | Registration ±2 mil [S2] | |
| Via pad / annular ring | 1 oz: 3.5 mil (0.09 mm) per side. 2 oz: 4.5 mil (0.11 mm) per side [S1]. "Via pad size ≥0.1 mm" [S1] (ambiguous: read as a 0.1 mm via ring). PTH (component) ring 0.2 mm per side [S1] | HDI min pad 8 mil (0.20 mm) [S3] | |
| Laser microvia | Standard form: blind/buried "Rank 1/2/3", 4 layers and up [S8][S7] | 0.075-0.15 mm [S3]. "Down to 0.1 mm (4 mil)" [S2 FAQ]. Aspect ratio max 1:1 (0.75:1 recommended) [S3], 0.8:1-1:1 [S2]. Dimple ≤10 µm [S3], ≤15 µm [S1]. Electroplated via fill available [S1] | 0.075 mm is UNCONFIRMED in practice, because the two pages disagree. Design to 0.10 mm |
| HDI stack-ups | 1+n+1, 2+n+2, 3+n+3 [S3]. Rank 1-5 on the advanced form [S8]. Any-layer (ELIC) [S2] | | **6L 1+4+1: from $223, 8 days. 8L 1+6+1: from $248, 8 days. 6L 2+2+2: from $380, 12 days. 8L 2+4+2: from $394, 12 days** [S3]. Plain 6L: from $60, 3-5 days. 8-32L/HDI: custom, 5-10 days [S15] |
| Mechanical blind/buried vias | Copper ≥20 µm [S1] | | Sequential lamination is "one of the major cost and lead time drivers" [S3] |
| Via-in-pad, filled and capped (POFV/VIPPO, IPC-4761 VII) | Standard form via options: Tented, Opened, Solder Mask Plug (IV-B), **Non-Conductive Fill & Cap (VII)** [S8][S7] | Advanced form adds: Resin Fill no cap (V), Conductive Fill & Cap (VII), Silver Fill & Cap (VII) [S8]. Max filled via diameter 0.45 mm [S3] | **$ / time**: "Via filling and capping requires additional processing which increases costs and extends the lead time" [S7]. The quote parser detects via-in-pad and prompts for VII [S7]. Min fill size UNCONFIRMED; assume the min drill |
| Tenting limit | Holes >0.45 mm cannot be fully tented [S7] | | |
| Hole to hole | Different nets ≥12 mil (0.30 mm), for CAF. Same net via to via ≥8 mil (0.20 mm) [S1] | | |
| Hole to copper | Via to track ≥7 mil (0.18). PTH to track ≥9 mil (0.23). NPTH to track ≥8 mil (0.20) mm [S1]. 0.18 = 0.10 ring + 0.076 space, so measured from the hole wall (derived) | | |
| Pad clearances | SMD pad to SMD pad, different nets, ≥0.15 mm. Pad with hole to pad with hole ≥0.40 mm. SMD pad to track ≥4 mil (0.10 mm) [S1] | BGA pad ≥0.2 mm. BGA pad to BGA pad 0.15 mm. BGA center to center 0.45 mm [S1] | |
| Copper to board edge | ≥0.2 mm to a CNC-routed edge. ≥0.4 mm to a V-cut [S1] | | |
| Solder mask | Opening/expansion ≥1.5 mil (0.04 mm) around the pad. Dam (bridge): **green 3.5 mil (0.089 mm), black/white 5 mil (0.127 mm), other colours 4 mil (0.10 mm)**. Thickness 0.6 mil on copper, 0.8 mil on laminate [S1] | | Black mask costs 1.5 mil of dam width at fine pitch |
| Silkscreen | Line ≥0.08 mm (printer) / ≥0.12 mm (screen). Height ≥0.61 / ≥0.76 mm. Pad to silk >0.15 mm [S1] | | |
| Impedance control | ±10 %, 4-20 layers, NextPCB or customer stackup [S1] | ±5 % on request [S21][S15]. "±3 %" claimed [S2] | "Customer Specified Stack up": "additional fees will be charged" [S7]. **Not available at ≥2 oz finished copper** [S7] |
| Castellated holes | Min 0.5 mm, min 0.55 mm between holes [S17][S1]. Hole >4 mm from board corner. Panelise with stamp holes and four rails [S1]. Not with HASL [S7] | 0.3 mm (custom), 0.50 mm between holes. Ring 0.15 standard / 0.12 advanced [S16] | The order form can cancel half-holes "due to the number of layers/board thickness" [S7] |
| Outline tolerance | CNC ±0.15 mm. V-cut ±0.2 mm [S1] | | |
| Max / min size | 6+ layers: 500 x 400 mm. Min 10 x 10 mm [S1] | | |

**Published stackups** [S6]. Dielectric thicknesses are read from NextPCB's
stackup diagrams.

- **6L 0.8 mm, `6L-0.8mm-0.5oz-1080`**:
  L1 (1 oz finished = 0.5 oz + plating) / 1080 PP 0.077 / core 0.20 incl. Cu
  H/H (L2-L3) / 2116 PP 0.125 / core 0.20 H/H (L4-L5) / 1080 PP 0.077 / L6.
  - Impedance: L1 50 Ω = 0.139 mm. L1 90 Ω diff = W 0.105 / S 0.127.
    L3 90 Ω = W 0.086 / S 0.140.
  - The 1080 layer under L1/L6 (0.077 mm) is what a 0.10 mm laser via needs:
    aspect ratio 0.77:1 (derived).
- **6L 0.8 mm, `6L-0.8mm-0.5oz-2116`**:
  2116 0.125 / core 0.20 / 2313 0.103 / core 0.20 / 2116 0.125.
- **Inner copper on 6L 0.8 mm**: the library publishes **only 0.5 oz inner**.
  1 oz inner at 0.8 mm is UNCONFIRMED; it may need a customer stackup (fee).
- **8L 1.6 mm, `8-1.6-1-2313`, 1 oz inner**:
  L1 (1 oz = 0.33 oz + plating) / 2313 0.103 / core 0.17 (1/1, L2-L3) /
  2x 7628H 0.23 / core 0.17 (L4-L5) / 2x 7628H 0.23 / core 0.17 (L6-L7) /
  2313 0.103 / L8.
  - Impedance: L1 90 Ω = W 0.114 / S 0.102. L3 90 Ω = W 0.102 / S 0.102.
  - The 0.5 oz-inner variant uses 0.135 mm cores.
- **8L with 2 oz outer**: no published stackup. With "No Requirement" NextPCB
  chooses the stackup; "Customer Specified Stack up" costs extra [S7].
- **8L 1.6 mm for HDI**: the 0.103 mm 2313 layer under L1/L8 gives a 1.03:1
  aspect ratio for a 0.10 mm laser via, which is over the 1:1 limit. It would
  have to become 1080 (0.077 mm), as in NextPCB's HDI stackups
  `6L-1.6mm-0.5oz-HDI 1080` [S6]. Stackup change is derived; NextPCB confirms
  it at order time.
- **Base stackup in the design** (F-0.1-In1-0.3-In2-0.1-In3-0.3-In4-0.1-In5-0.3-In6-0.1-B):
  this pairs layers differently from NextPCB's standard 8L. Either let NextPCB
  propose a stackup, or order "Customer Specified" (fee) [S7].

### 1.2 Assembly (turnkey PCBA)

| Item | NextPCB figure | Notes |
|---|---|---|
| Min passive | 01005 imperial (0402 metric) [S4] | |
| Fine pitch | ICs 0.38 mm pitch; BGA/LGA 0.25 mm ball pitch [S4] | Other NextPCB pages say 0.25 mm fine-pitch parts [S12][S26] and 0.35 mm BGA "stable" [S23]. QFN 0.4 mm (Core, Base) is inside every figure |
| Placement accuracy | 15 µm @ 3σ, Siemens/ASM E-series [S25] | |
| Body to body / pad to pad between parts | DFA guide: component to component **0.5 mm** recommended; 0402: 0.25-0.75 mm [S10]. BGA page: **min BGA to BGA 0.2 mm**, min pad to circuit line 0.2 mm [S5]. Fab floor: SMD pad to SMD pad, different nets, 0.15 mm [S1] | **0.2 mm body to body for chip passives and QFNs is UNCONFIRMED.** The only published 0.2 mm figure is BGA to BGA. Get it signed off in the free DFA review [S12] |
| Component to edge | DFA guide: 3.0 mm from the board edge, for depanelisation [S10]. BGA: 200 mil from the edge, for rework [S5] | No hard minimum is published (UNCONFIRMED). Copper ≥0.2 mm to a routed edge [S1] |
| Rails / panel | Rails recommended for PCBA, "if not, custom made fixtures may be required which cost extra" [S7]. Rail ≥3 mm [S1]. Order form default 5 mm and rejects <3 mm [S8]. 3 mm on both long sides if NextPCB panelises [S22]. Min PCBA panel 50 x 50 mm [S19]. Routed gap 1.6 mm. Mouse-bite tab ≥5 mm. Stamp holes 0.5-0.8 mm [S1] | Both boards (Core 23 x 20, Base 25.5 x 25.5) must be panelised for assembly |
| Fiducials | 1 mm diameter [S7] | |
| Double-sided reflow | One reflow per side. "A special adhesive is applied underneath the components that were soldered in the first run" [S7]. Lighter side first; trays or glue for heavy parts [S24] | **No weight or size limit for second-side parts is published (UNCONFIRMED).** Price of the second side and the glue: UNCONFIRMED |
| X-ray | Mandatory for every board with BGA, QFN, LGA or flip-chip [S4]. "Included by default on all NextPCB quotations which include such parts" [S7] | The PCBA form asks for X-ray component and board counts [S8]; whether that changes the price is UNCONFIRMED |
| Stencil | 0.03-1.0 mm. Cut accuracy ±0.005 mm. Step-down/step-up with a ≥2 mm transition zone. Electropolish, nano-coat [S9]. Free with PCBA orders [S12] | NextPCB's thickness guide: BGA 0.40 or IC 0.35 mm pitch → 0.08 mm. BGA 0.50 or IC 0.40 mm → 0.10 mm. IC 0.50 → 0.10-0.12 mm [S7]. 0201/0402: 0.10-0.12. QFN/LGA: 0.12-0.15 [S9] |
| Workmanship | IPC-A-610 Class 2; Class 3 on request [S4] | |
| PCB as a component (Core onto Base) | Not documented. NextPCB does support partial turnkey (customer-supplied lines marked `C` in the BOM) [S11][S4] and "turnkey PCB assembly ... castellated modules" [S16]. An LGA module counts as an LGA, so X-ray is mandatory [S4] | **UNCONFIRMED whether a Core PCBA from one NextPCB order can feed a Base order in-house** without export/re-import. Ask the account manager (see 4.6) |
| Consigned parts | Handling fee **$50 per 50 consigned BOM lines once there are more than 5** [S11]. Customer pays freight and customs. Parts must carry overage. Max 7-day wait for client parts [S14]. Packaging: cut tape, reel, tube, tray, laser-cut stainless carrier [S4] | |
| Sourcing | HQ Online: 600k+ parts in local stock, "within 2 days". Global distributors: Digi-Key, Mouser, Element14, Avnet, Verical, RS, TME, Rochester, Chip One Stop [S12][S7], and Arrow [S7]. Can buy from a supplier you name [S11] | **LCSC is not listed (UNCONFIRMED).** Rev 0 service uses HQ Online parts only [S12] |
| Attrition | "Include 5-10 % attrition overage for SMT passives" (consigned) [S4] | Turnkey attrition is computed by the quote engine; percentage UNCONFIRMED |
| Lead time | SMT 3-5 days. Parts 5-7 working days [S14]. PCBA ~7 business days at best, average 17-30 [S13]. Rev 0: 7 working days, 5 or 10 pcs [S12] | |

---

## 2. Proposed rule sets

The two tiers mean:

- **Standard-price**: the Standard PCB order. No HDI, no via fill, no drill
  below 0.20 mm (0.20 mm is the no-surcharge drill [S18]). Every number sits
  one step above NextPCB's published minimum, so the order passes CAM without
  an engineering question. The margins are my choice; the minimums are
  NextPCB's.
- **Extreme**: NextPCB's published minimums. Microvias and filled
  via-in-pad are optional add-ons.

Units are mm. "Body" spacing assumes courtyards are drawn on the real
package outline (the maintainer's intent). The pad-to-pad rule then catches
chip parts whose pads stick out past the body.

### 2.1 Core: 6L 0.8 mm, 1 oz finished outer, 0.5 oz inner

| Rule | Standard-price | Extreme | Source |
|---|---|---|---|
| Track / clearance, outer (1 oz) | 0.09 / 0.09 | **0.076 / 0.076** | [S1] |
| Track / clearance, inner (0.5 oz) | 0.09 / 0.09 | **0.064 / 0.076** | [S1] |
| Same, if 1 oz inner is ordered | 0.10 / 0.10 | 0.10 / 0.10 (lower is UNCONFIRMED) | [S6] |
| SMD pad to track or pour (outer) | 0.10 | 0.10 | [S1] |
| SMD pad to SMD pad, different nets | 0.15 | 0.15. Datasheet land patterns below this (U9 X2SON-6: 0.09-0.11) need a per-footprint exception and a ganged mask: agree with NextPCB | [S1] |
| Through via (drill / pad) | 0.20 / 0.40, tented | **0.15 / 0.35** (0.8 mm board ≤1.2 mm). Tented, or VII fill-and-cap when in a pad | [S1][S18] |
| Via annular ring | 0.10 | 0.10 (through via). The 0.09 mm 1 oz figure is used for PTH | [S1] |
| Laser microvia L1-L2, L6-L5 | none | **0.10 / 0.20**, copper-filled when in a pad. Ring 0.05 (derived) | [S2][S3][S1] |
| Hole to copper | via 0.20, PTH 0.25 | via 0.18, PTH 0.23, NPTH 0.20, microvia 0.13 (derived) | [S1] |
| Hole to hole | 0.30 different net / 0.20 same net | same | [S1] |
| Copper to edge | 0.25 routed | 0.20 routed / 0.40 V-cut | [S1] |
| Mask expansion / min dam | 0.05 / 0.10 (any colour except black or white) | 0.04 / **0.089, green only** | [S1] |
| Body to body (courtyard on the body) | 0.25 | **0.20** (UNCONFIRMED for chips; BGA to BGA is published) | [S10][S5] |
| Pad to pad, between different parts | 0.20 | 0.15 | [S5][S1] |
| Parts to break-tab / V-cut edge | 3.0 | 3.0 at tabs. Routed sides without tabs: copper rule only (UNCONFIRMED) | [S10] |
| Stencil | 0.10 | 0.10 (0.08 if 01005 or a pitch below 0.4 is added) | [S7][S9] |
| Smallest passive | 0201 | 01005 | [S4] |

### 2.2 Base: 8L 1.6 mm, 2 oz finished outer, 1 oz inner

| Rule | Standard-price | Extreme | Source |
|---|---|---|---|
| Track / clearance, outer (2 oz) | 0.16 / 0.16 | **0.14 / 0.14** | [S1] |
| Track / clearance, inner (1 oz) | 0.11 / 0.11 | 0.10 / 0.10 (lower is UNCONFIRMED) | [S6] |
| SMD pad to SMD pad, different nets | 0.15 | 0.15. U23 X2SON-4 (0.134-0.141) needs an exception, as on the Core | [S1] |
| Through via (drill / pad) | 0.20 / 0.45, tented | **0.20 / 0.43** (2 oz ring 0.115). 0.15 mm is not offered at 1.6 mm on the Standard order (≤1.2 mm only) | [S1] |
| Filled via-in-pad (VII) | none | 0.20 / 0.43 in LGA-land, EP and MOSFET pads. Filled diameter ≤0.45 | [S8][S3] |
| Laser microvia | none | 0.10 / 0.25, **only if NextPCB confirms** HDI with 2 oz outer and 1080 under L1/L8 (UNCONFIRMED) | [S3] |
| Hole to copper | via 0.20, PTH 0.25 | via 0.18, PTH 0.23, NPTH 0.20 | [S1] |
| Hole to hole | 0.30 different net / 0.20 same net | same | [S1] |
| Copper to edge | 0.25 routed | 0.20 routed / 0.40 V-cut | [S1] |
| Mask expansion / min dam | 0.05 / 0.10 | 0.04 / 0.089 (green) | [S1] |
| Body to body | 0.25 | 0.20 | [S10][S5] |
| Pad to pad between parts | 0.20 | 0.15 (on 2 oz the 0.14 copper rule is below this, so 0.15 governs) | [S1] |
| Stencil | 0.10 | 0.10 uniform. A step-up for the J90 land or MOSFET pads needs a ≥2 mm transition, which barely fits on 25.5 mm | [S9] |
| Impedance (USB D+/D-) | Route on an inner layer; impedance is not offered on 2 oz outer | same | [S7] |

### 2.3 Double-sided assembly and the stack (both boards)

- **Base**: reflow the bottom (lighter) side first. The **Core LGA and the
  heaviest parts go on the final-reflow side**, so the Core is never upside
  down over molten solder. First-side parts get glue [S7][S24].
- **Core**: one-sided (its bottom is the LGA). It sees at least two reflows:
  its own, then the Base pass. Moisture bake before the Base pass is
  UNCONFIRMED; ask.
- **Removing unused pads per instance**: NextPCB has no fab rule against it.
  The DFA review checks footprints against a 5-million-package library [S20],
  so expect an EQ for every modified footprint. Put a note in the order.

---

## 3. KiCad 10 custom rules, extreme tier

Validated with `kicad-cli 10.0.6 pcb drc` on scratch copies of the ce0aa59
split boards (`scratchpad/nextpcb_test/`). The rules parse and fire.

Two behaviours checked on 10.0.6:

- A matching custom rule **replaces** the Board Setup minimum for that item. It
  is not stacked on top of it (tested for clearance, annular ring and hole size).
- The last matching rule wins.

So the Board Setup floor below only governs items no rule matches.

### 3.1 Board Setup > Constraints floor

| Field | Core | Base |
|---|---|---|
| Min clearance | 0.076 | 0.10 |
| Min track width / connection width | 0.064 | 0.10 |
| Min annular width | 0.05 | 0.10 |
| Min via diameter | 0.20 | 0.43 |
| Min through-hole | 0.15 | 0.20 |
| Min uvia diameter / hole | 0.20 / 0.10 | 0.25 / 0.10 |
| Min hole clearance | 0.13 | 0.18 |
| Min hole to hole | 0.20 | 0.20 |
| Copper to edge | 0.20 | 0.20 |
| Solder mask expansion | 0.04 | 0.04 |
| Solder mask min web width | 0.09 (green) | 0.09 |
| Min text height / thickness | 0.61 / 0.08 | 0.61 / 0.08 |

### 3.2 `OpenAIO-Core.kicad_dru`, below the marker

```
# NextPCB extreme tier, OpenAIO Core: 6L 0.8 mm, 1 oz finished outer,
# 0.5 oz inner (NextPCB stack 6L-0.8mm-0.5oz-1080), HDI 1+4+1 optional.
# KiCad: the LAST matching rule wins; general rules first, specific last.

(rule "NPCB core: outer 1 oz track"
  (layer outer)
  (constraint track_width (min 0.076mm)))

(rule "NPCB core: outer 1 oz clearance"
  (layer outer)
  (constraint clearance (min 0.076mm)))

(rule "NPCB core: inner 0.5 oz track"
  (layer inner)
  (constraint track_width (min 0.064mm)))

(rule "NPCB core: inner 0.5 oz clearance"
  (layer inner)
  (constraint clearance (min 0.076mm)))

(rule "NPCB core: SMD pad to track or pour"
  (layer outer)
  (condition "A.Type == 'Pad' && A.Pad_Type == 'SMD' && (B.Type == 'Track' || B.Type == 'Arc' || B.Type == 'Zone')")
  (constraint clearance (min 0.10mm)))

(rule "NPCB core: SMD pad to SMD pad"
  (layer outer)
  (condition "A.Type == 'Pad' && B.Type == 'Pad' && A.Pad_Type == 'SMD' && B.Pad_Type == 'SMD'")
  (constraint clearance (min 0.15mm)))

(rule "NPCB core: PTH pad to PTH pad"
  (condition "A.Type == 'Pad' && B.Type == 'Pad' && A.Pad_Type == 'Through-hole' && B.Pad_Type == 'Through-hole'")
  (constraint clearance (min 0.40mm)))

(rule "NPCB core: through via"
  (condition "A.Type == 'Via' && A.Via_Type == 'Through'")
  (constraint hole_size (min 0.15mm))
  (constraint via_diameter (min 0.35mm))
  (constraint annular_width (min 0.10mm))
  (constraint hole_clearance (min 0.18mm)))

(rule "NPCB core: laser microvia L1-L2 / L6-L5"
  (condition "A.Type == 'Via' && A.Via_Type == 'Micro'")
  (constraint hole_size (min 0.10mm) (max 0.10mm))
  (constraint via_diameter (min 0.20mm))
  (constraint annular_width (min 0.05mm))
  (constraint hole_clearance (min 0.13mm)))

(rule "NPCB core: PTH hole to copper"
  (condition "A.Type == 'Pad' && A.Pad_Type == 'Through-hole'")
  (constraint hole_clearance (min 0.23mm))
  (constraint annular_width (min 0.09mm)))

(rule "NPCB core: NPTH hole to copper"
  (condition "A.Type == 'Pad' && A.Pad_Type == 'NPTH, mechanical'")
  (constraint hole_clearance (min 0.20mm)))

(rule "NPCB core: hole to hole, different nets (CAF)"
  (condition "A.Net != B.Net")
  (constraint hole_to_hole (min 0.30mm)))

(rule "NPCB core: copper to routed edge"
  (constraint edge_clearance (min 0.20mm)))

(rule "NPCB core: body to body (courtyard drawn on the body)"
  (constraint courtyard_clearance (min 0.20mm)))

# Only after NextPCB accepts a ganged mask on this datasheet land pattern.
(rule "NPCB core: U9 X2SON-6 land pattern below 0.15"
  (layer outer)
  (condition "A.Type == 'Pad' && B.Type == 'Pad' && A.memberOfFootprint('U9') && B.memberOfFootprint('U9')")
  (constraint clearance (min 0.076mm)))
```

### 3.3 `OpenAIO-Base.kicad_dru`, below the marker

This replaces the current "2 oz outer copper" pair, which sets 0.16 mm.

```
# NextPCB extreme tier, OpenAIO Base: 8L 1.6 mm, 2 oz finished outer,
# 1 oz inner, through vias + Non-Conductive Fill & Cap (VII) via-in-pad.
# KiCad: the LAST matching rule wins; general rules first, specific last.

(rule "NPCB base: outer 2 oz track"
  (layer outer)
  (constraint track_width (min 0.14mm)))

(rule "NPCB base: outer 2 oz clearance"
  (layer outer)
  (constraint clearance (min 0.14mm)))

(rule "NPCB base: inner 1 oz track"
  (layer inner)
  (constraint track_width (min 0.10mm)))

(rule "NPCB base: inner 1 oz clearance"
  (layer inner)
  (constraint clearance (min 0.10mm)))

(rule "NPCB base: SMD pad to SMD pad"
  (layer outer)
  (condition "A.Type == 'Pad' && B.Type == 'Pad' && A.Pad_Type == 'SMD' && B.Pad_Type == 'SMD'")
  (constraint clearance (min 0.15mm)))

(rule "NPCB base: PTH pad to PTH pad"
  (condition "A.Type == 'Pad' && B.Type == 'Pad' && A.Pad_Type == 'Through-hole' && B.Pad_Type == 'Through-hole'")
  (constraint clearance (min 0.40mm)))

(rule "NPCB base: through via, 1.6 mm board"
  (condition "A.Type == 'Via' && A.Via_Type == 'Through'")
  (constraint hole_size (min 0.20mm))
  (constraint via_diameter (min 0.43mm))
  (constraint annular_width (min 0.115mm))
  (constraint hole_clearance (min 0.18mm)))

# Delete unless NextPCB confirms laser HDI with 2 oz outer and 1080 under L1/L8.
(rule "NPCB base: laser microvia"
  (condition "A.Type == 'Via' && A.Via_Type == 'Micro'")
  (constraint hole_size (min 0.10mm) (max 0.10mm))
  (constraint via_diameter (min 0.25mm))
  (constraint annular_width (min 0.075mm))
  (constraint hole_clearance (min 0.13mm)))

(rule "NPCB base: PTH hole to copper"
  (condition "A.Type == 'Pad' && A.Pad_Type == 'Through-hole'")
  (constraint hole_clearance (min 0.23mm))
  (constraint annular_width (min 0.115mm)))

(rule "NPCB base: NPTH hole to copper"
  (condition "A.Type == 'Pad' && A.Pad_Type == 'NPTH, mechanical'")
  (constraint hole_clearance (min 0.20mm)))

(rule "NPCB base: hole to hole, different nets (CAF)"
  (condition "A.Net != B.Net")
  (constraint hole_to_hole (min 0.30mm)))

(rule "NPCB base: copper to routed edge"
  (constraint edge_clearance (min 0.20mm)))

(rule "NPCB base: body to body (courtyard drawn on the body)"
  (constraint courtyard_clearance (min 0.20mm)))

# Only after NextPCB accepts a ganged mask on this datasheet land pattern.
(rule "NPCB base: U23 X2SON-4 land pattern below 0.15"
  (layer outer)
  (condition "A.Type == 'Pad' && B.Type == 'Pad' && A.memberOfFootprint('U23') && B.memberOfFootprint('U23')")
  (constraint clearance (min 0.076mm)))
```

### 3.4 What these rules flag on the ce0aa59 split boards

kicad-cli lists at most 199 entries per violation type, so the via counts
below come from pcbnew.

- **Core**:
  - All 246 vias are 0.35 / 0.20, which leaves a **0.075 mm ring, below
    NextPCB's 0.09 / 0.10**. The OpenDrone line-standard via (annular 0.075)
    is **not a NextPCB via**. On the Core, change it to 0.35 / 0.15 or
    0.40 / 0.20.
  - 34 SMD pad-to-track gaps of 0.09-0.0965.
  - 7 different-net via pairs at 0.275 hole-to-hole (UART, I2C and LED pairs).
- **Base**:
  - All 1024 vias at 0.35 / 0.20 fail the 2 oz ring. They need 0.43 / 0.20.
  - 24 inner clearances below 0.10.
  - 17 PTH hole-clearance and 6 via hole-clearance hits.
  - 7 outer tracks below 0.14.
  - 1 CAF pair (+BATT/GND, 0.25).
  - 3 U23 pad gaps.

---

## 4. The five biggest density levers at NextPCB

1. **HDI 1+N+1 with copper-filled microvia-in-pad, Core first.**
   - What it buys: 0.10 / 0.20 laser vias L1-L2 drop straight into the
     RP2354A QFN-60 and BMI270 pads and escape to L2. That removes the
     dog-bone fan-out and frees L1, which a 0.4 mm QFN cannot otherwise get.
     The Core's 1080 layer (0.077 mm) already suits it.
   - Cost: 6L 1+4+1 is **from $223, 8 days**, against **from $60, 3-5 days**
     for a plain 6L [S3][S15].
   - On the Base: 8L 1+6+1 from $248, 8 days [S3], but HDI with 2 oz outer is
     UNCONFIRMED.
2. **Non-Conductive Fill & Cap (VII) on through vias.**
   - What it buys: vias inside EPs, the 24 PowerDI3333 drain/source pads, both
     sides of the 34-pad LGA (1.0 mm pads take a 0.20 / 0.43 via easily) and
     the QFN EPs. Shortest, thickest current path, and through-board thermal
     paths without dog-bones.
   - Cost: it is a Standard-order option, but "increases costs and extends the
     lead time" [S7]. Amount UNCONFIRMED. Filled diameter ≤0.45 mm [S3].
3. **Smallest standard drill and finest lines, Core only.**
   - What it buys: 0.15 / 0.35 vias against 0.20 / 0.40 is about 23 % less via
     area (derived). 3/3 mil outer and 2.5/3 mil inner on 0.5 oz.
   - Cost: drills below 0.2 mm lose the no-extra-charge status [S18]; the
     amount is UNCONFIRMED.
   - On the Base: 0.15 mm is only offered up to 1.2 mm thickness [S1]. An 8L
     1.2 mm Base (NextPCB publishes `8-1.2-1-2313` [S6]) would get it too, but
     changes the mechanical spec. 0.15 mm at 1.6 mm through Advanced PCB
     (20:1 aspect ratio [S2]) is UNCONFIRMED.
4. **Copper split on the Base: 1 oz outer + 2 oz inner planes instead of 2 oz
   outer.**
   - What it buys: outer rules drop from 0.14 to 0.076 mm, which matters for
     the QFN-28 at 0.4 mm. Impedance control comes back (not offered at ≥2 oz
     [S7]). Inner copper up to 2 oz is a standard option [S1].
   - Cost: UNCONFIRMED. Whether 2 oz inner still carries the phase current is
     an electrical question for the maintainer.
5. **Double-sided turnkey assembly at the placement limit.**
   - What it buys: glue-assisted second side [S7], 01005 parts [S4], 15 µm
     placement [S25], 0.2 mm spacing (published only for BGA to BGA [S5]),
     X-ray included [S7]. About 2x the placement area per board.
   - Cost: second-side setup and glue, amount UNCONFIRMED. Stencils are free
     with PCBA [S12]. The real cost is DFA review time on every 0.2 mm gap and
     every pad-stripped footprint.

### 4.6 Questions for the account manager

These are the UNCONFIRMED items above, phrased as questions:

1. Can a Core PCBA from one order be held in-house and placed as a `C` line
   on the Base order without export? Does the consigned-line fee apply? Is a
   moisture bake done before the second reflow?
2. Laser HDI with 2 oz finished outer?
3. 1 oz inner on 6L 0.8 mm (stackup and price)?
4. 1 oz inner minimum track and space (is 3.5 mil OK)?
5. Price steps for trace/space and drill (6, 4, 3.5, 3 mil; 0.2 vs 0.15 mm)
   and for VII fill?
6. Minimum filled-via size?
7. 0.2 mm body to body for 0201 parts and QFNs; component-to-routed-edge
   minimum?
8. Second-side weight limit?
9. Turnkey attrition percentage?
10. LCSC as a source?
11. Ganged mask accepted on the X2SON land patterns?
12. Are 0.5 mm local fiducials (1.0 mm mask opening) accepted on the Core
    next to one 1.0 mm fiducial, with 1.0 mm fiducials on the panel rails?
13. Can the Core be ordered with bow and twist of at most 0.10 mm over the
    J91 pad field, and the Base top printed with a 0.12 mm stencil?
14. Tabs narrower than 5 mm (1.5-3.0 mm) with router depanelling, and parts
    0.5 mm from a router-cut tab (PANEL.md)?

### 4.7 Order notes (DFM fix batch FB1)

These go on the NextPCB order and in the fab notes. Each one comes from the
critique round 1 DFM findings (DFM-xx).

**Stencils (DFM-04, DFM-05).** One stencil per printed side:

| Side | Thickness | Why |
|---|---|---|
| Core top (F) | 0.10 mm | 0.4 mm QFN-60 (U2); every aperture at area ratio >= 0.66 |
| Base bottom (B) | 0.10 mm | 0.4 mm QFN-28 (U13/U15/U17/U19); every aperture at area ratio >= 0.66 |
| Base top (F) | **0.12 mm** | J90 LGA land; the finest Base top apertures (0201 R34/C104, USB1) stay at area ratio >= 0.70 |

A step-up on J90 alone is not possible: NextPCB needs a 2 mm transition zone
and other Base top apertures sit 0.97 mm (U12, C105) from J90 pads. The
uniform 0.12 mm top stencil does the same job. Fine-pitch parts carry
footprint-level paste overrides (1:1 pins, exposed pads at the board default),
so all apertures except J90 reach area ratio 0.66 at 0.10 mm.

**LGA joint (DFM-05).** J90 prints a 1.1 mm round aperture on the 1.0 mm land
(+0.05 mm overprint; area ratio 2.3 at 0.12 mm). J91 on the Core has no paste.
Solder per joint, with paste at 50 % metal by volume and 90 % transfer:

| J90 aperture / stencil | Paste | Solder | Joint height (column on a 0.785 mm2 pad) |
|---|---|---|---|
| 0.8 mm / 0.10 mm (before) | 0.045 mm3 | 0.023 mm3 | 0.029 mm |
| 1.1 mm / 0.12 mm (now) | 0.103 mm3 | 0.051 mm3 | 0.065 mm |

IPC-6012 bow and twist (0.75 %) over the J91 pad field (21 x 19 mm outer
pad edges, 28.3 mm diagonal; the critique used 23.3 mm and got 0.17 mm)
allows 0.21 mm. That is 3x the joint height, so the IPC default is not good
enough. At placement the Core must touch every wet deposit (0.12 mm high), so
the Core order asks for **bow and twist of at most 0.10 mm over the J91 pad
field**, which leaves 0.02 mm for print height spread. After reflow the
0.065 mm columns absorb roughly +-0.03 mm of local gap, so first articles get
2.5D/oblique X-ray (DFM-14). For more margin, pre-bump J91 (paste print and
reflow on the Core bottom), which roughly doubles the solder per joint.

**Copper next to the LGA (DFM-06).** Pours of every other net keep 0.30 mm
from every J90 and J91 pad, and +BATT keeps 0.30 mm from J90 with every item
type (named rules in both `.kicad_dru` files). Still under mask at
0.15-0.30 mm: 80 Base signal/power track and via pairs next to J90 pads, and
49 Core via/track pairs next to J91 pads (closest 0.086 mm, a via beside a
J91 pad). They need a local re-route (owner finish pass).

**Solder mask (DFM-12).** Expansion 0.04 mm on both boards, minimum web
0.09 mm (green). Ganged openings only inside datasheet land patterns that are
too fine for a dam, each as a named `bridged_mask` rule.

**Fiducials (DFM-08).** The Core carries FID1 (1.0 mm dot, 2.0 mm opening)
and FID2/FID3 (0.5 mm dots, 1.0 mm openings) inside the outline; no Core top
site leaves room for three 1.0 mm fiducials. The panel rails carry 1.0 mm
fiducials (PANEL.md).

**Panels (DFM-10).** See PANEL.md: Core 3 x 2, Base 2 x 2, 5 mm rails,
solid tabs on the measured free edge runs, router depanel.

---

## 5. Notes on method

- The order-form option lists (layers 1-22 standard / 40 advanced, copper
  0.5-6 oz, trace steps down to 2/2 mil, drills down to 0.1 mm, via processes,
  HDI ranks, the rail default of 5 mm with <3 mm rejected) come from the
  JavaScript bundle that `https://www.nextpcb.com/pcb-quote` loads [S8].
- The help strings come from the order form's language feed [S7].
- NextPCB's online price API refused anonymous requests ("Valuation params
  error"). So the only cost numbers here are the published HDI and prototype
  prices. Everything else is marked UNCONFIRMED.

## 6. Sources

- [S1] Standard PCB capabilities: https://www.nextpcb.com/pcb-capabilities
- [S2] Advanced PCB capabilities: https://www.nextpcb.com/advanced-pcb-capabilities
  (same content at https://www.nextpcb.com/advanced-pcb-manufacturing-capabilities)
- [S3] HDI PCB capabilities, prices and lead times: https://www.nextpcb.com/pcb-type/hdi-pcb
- [S4] PCB assembly capabilities: https://www.nextpcb.com/assembly-capabilities
  (same content at https://www.nextpcb.com/pcb-assembly-capabilities)
- [S5] BGA assembly capabilities: https://www.nextpcb.com/pcb-vocabulary/bga-assembly-capabilities
- [S6] Stackup library: https://www.nextpcb.com/impedance-control-stackups. Diagrams:
  - https://static.nextpcb.com/images/stackup/6L-0.8mm-0.5oz-1080_Stack-up_Diagram.webp
  - https://static.nextpcb.com/images/stackup/6L-0.8mm-0.5oz-2116_Stack-up_Diagram.webp
  - https://static.nextpcb.com/images/stackup/8-1.6-1-2313_Stack-up_Diagram.webp
  - https://static.nextpcb.com/images/stackup/8-1.6-0.5-2313_Stack-up_Diagram.webp
  - https://static.nextpcb.com/images/stackup/6L-1.6mm-0.5oz-HDI%201080_Stack-up_Diagram.webp
- [S7] Order-form help text, served to https://www.nextpcb.com/pcb-quote and the
  PCBA quote from https://www.nextpcb.com/ajax/getlang. Keys used:
  - `readhelp_via process`, `readhelp_non-conductive_fill_cap`, `have_via_pad_result_tip`
  - `insidecopper_tips`, `readhelp_laminated_structure`, `readhelp_hdi buried/blind vias`
  - `bankong_tip`, `readhelp_plated half-holes`, `paba_breakaway_tip`
  - `double_sided_assembly_projects`, `after_process1-3`, `thickness_note`
  - `existing_fiducials_note`, `20_million_components`, `sourcing_components`
- [S8] Order-form option lists: https://static.nextpcb.com/js/nextstatic/js/chunk-common.1a48586d.js
  (loaded by https://www.nextpcb.com/pcb-quote)
- [S9] PCB stencil service: https://www.nextpcb.com/pcb-stencil
- [S10] PCB assembly design guide (DFA spacing): https://www.nextpcb.com/blog/pcb-assembly-design-guide
- [S11] Consigned parts process and fees: https://www.nextpcb.com/helpcenter/can-i-send-the-component-directly
- [S12] PCB assembly services (sourcing, Rev 0, free stencil, free DFA): https://www.nextpcb.com/pcb-assembly-services
- [S13] PCBA lead time: https://www.nextpcb.com/helpcenter/lead-time-for-pcb-assembly-orders
- [S14] Order and delivery FAQ: https://www.nextpcb.com/pcb-order-delivery-faq
- [S15] PCB prototype prices and lead times: https://www.nextpcb.com/pcb-prototype
- [S16] Castellated PCB guide (advanced half-holes): https://www.nextpcb.com/blog/plated-half-holes-castellated-pcb-guide
- [S17] Plated half-holes: https://www.nextpcb.com/pcb-vocabulary/plated-half-holes
- [S18] Annular rings (0.2-6.3 mm drill, no extra charge): https://www.nextpcb.com/pcb-vocabulary/annular-rings
- [S19] Panel creation (PCBA panel 50 x 50 mm minimum): https://www.nextpcb.com/pcb-vocabulary/panel-creation
- [S20] HQDFM user manual (DFA footprint checks): https://www.nextpcb.com/dfm-user-manual
- [S21] Impedance control: https://www.nextpcb.com/service-type/pcb-impedance-control
- [S22] Mobile capabilities page (3 mm default rails): https://mobile.nextpcb.com/pcb-capabilities
- [S23] Laser stencil article: https://www.nextpcb.com/pcb-vocabulary/laser-stencil
- [S24] PCB assembly guide (double-sided process): https://www.nextpcb.com/blog/pcb-assembly-guide
- [S25] Assembly line (15 µm @ 3σ): https://www.nextpcb.com/blog/automated-assembly-line-15-micron-smt-high-reliability-pcba
- [S26] PCBA capability comparison: https://www.nextpcb.com/blog/pcba-capability-comparison
