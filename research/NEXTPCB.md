# NextPCB fabrication and assembly capabilities

Researched 2026-10-06 from NextPCB's own pages, its online order form (option
lists from the order-form JavaScript, help text from the order form's
language feed), its stackup library and its help centre. Every number carries a
source tag `[Sx]`, and the URLs are listed in section 3.

Labels used below:

- **UNCONFIRMED**: NextPCB publishes nothing on this, or its pages disagree. Ask
  the account manager before you rely on it.
- **derived**: computed from published numbers, not published itself.
- **$ / time**: NextPCB says the option raises the price and/or the lead time.

The board this applies to: 35.4 mm square, 8 layers HDI 1+6+1, 0.997 mm, 1 oz on all layers, 24x PowerDI3333-8 on both
sides, QFN-28 at 0.4 mm, QFN-60 at 0.4 mm, QFN-32 at 0.5 mm, 0201 passives.

NextPCB's pages disagree in places: microvia 0.075 vs 0.1 mm, fine pitch
0.38 vs 0.35 vs 0.25 mm, impedance ±5 vs ±3 %, edge rail 3 vs 5 mm. Where they
do, both values are shown.

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

### 1.2 Assembly (turnkey PCBA)

| Item | NextPCB figure | Notes |
|---|---|---|
| Min passive | 01005 imperial (0402 metric) [S4] | |
| Fine pitch | ICs 0.38 mm pitch; BGA/LGA 0.25 mm ball pitch [S4] | Other NextPCB pages say 0.25 mm fine-pitch parts [S12][S26] and 0.35 mm BGA "stable" [S23]. QFN 0.4 mm is inside every figure |
| Placement accuracy | 15 µm @ 3σ, Siemens/ASM E-series [S25] | |
| Body to body / pad to pad between parts | DFA guide: component to component **0.5 mm** recommended; 0402: 0.25-0.75 mm [S10]. BGA page: **min BGA to BGA 0.2 mm**, min pad to circuit line 0.2 mm [S5]. Fab floor: SMD pad to SMD pad, different nets, 0.15 mm [S1] | **0.2 mm body to body for chip passives and QFNs is UNCONFIRMED.** The only published 0.2 mm figure is BGA to BGA. Get it signed off in the free DFA review [S12] |
| Component to edge | DFA guide: 3.0 mm from the board edge, for depanelisation [S10]. BGA: 200 mil from the edge, for rework [S5] | No hard minimum is published (UNCONFIRMED). Copper ≥0.2 mm to a routed edge [S1] |
| Rails / panel | Rails recommended for PCBA, "if not, custom made fixtures may be required which cost extra" [S7]. Rail ≥3 mm [S1]. Order form default 5 mm and rejects <3 mm [S8]. 3 mm on both long sides if NextPCB panelises [S22]. Min PCBA panel 50 x 50 mm [S19]. Routed gap 1.6 mm. Mouse-bite tab ≥5 mm. Stamp holes 0.5-0.8 mm [S1] | Both boards (Core 23 x 20, Base 25.5 x 25.5) must be panelised for assembly |
| Fiducials | 1 mm diameter [S7] | |
| Double-sided reflow | One reflow per side. "A special adhesive is applied underneath the components that were soldered in the first run" [S7]. Lighter side first; trays or glue for heavy parts [S24] | **No weight or size limit for second-side parts is published (UNCONFIRMED).** Price of the second side and the glue: UNCONFIRMED |
| X-ray | Mandatory for every board with BGA, QFN, LGA or flip-chip [S4]. "Included by default on all NextPCB quotations which include such parts" [S7] | The PCBA form asks for X-ray component and board counts [S8]; whether that changes the price is UNCONFIRMED |
| Stencil | 0.03-1.0 mm. Cut accuracy ±0.005 mm. Step-down/step-up with a ≥2 mm transition zone. Electropolish, nano-coat [S9]. Free with PCBA orders [S12] | NextPCB's thickness guide: BGA 0.40 or IC 0.35 mm pitch → 0.08 mm. BGA 0.50 or IC 0.40 mm → 0.10 mm. IC 0.50 → 0.10-0.12 mm [S7]. 0201/0402: 0.10-0.12. QFN/LGA: 0.12-0.15 [S9] |
| Workmanship | IPC-A-610 Class 2; Class 3 on request [S4] | |
| Consigned parts | Handling fee **$50 per 50 consigned BOM lines once there are more than 5** [S11]. Customer pays freight and customs. Parts must carry overage. Max 7-day wait for client parts [S14]. Packaging: cut tape, reel, tube, tray, laser-cut stainless carrier [S4] | |
| Sourcing | HQ Online: 600k+ parts in local stock, "within 2 days". Global distributors: Digi-Key, Mouser, Element14, Avnet, Verical, RS, TME, Rochester, Chip One Stop [S12][S7], and Arrow [S7]. Can buy from a supplier you name [S11] | **LCSC is not listed (UNCONFIRMED).** Rev 0 service uses HQ Online parts only [S12] |
| Attrition | "Include 5-10 % attrition overage for SMT passives" (consigned) [S4] | Turnkey attrition is computed by the quote engine; percentage UNCONFIRMED |
| Lead time | SMT 3-5 days. Parts 5-7 working days [S14]. PCBA ~7 business days at best, average 17-30 [S13]. Rev 0: 7 working days, 5 or 10 pcs [S12] | |

---

## 2. Notes on method

- The order-form option lists (layers 1-22 standard / 40 advanced, copper
  0.5-6 oz, trace steps down to 2/2 mil, drills down to 0.1 mm, via processes,
  HDI ranks, the rail default of 5 mm with <3 mm rejected) come from the
  JavaScript bundle that `https://www.nextpcb.com/pcb-quote` loads [S8].
- The help strings come from the order form's language feed [S7].
- NextPCB's online price API refused anonymous requests ("Valuation params
  error"). So the only cost numbers here are the published HDI and prototype
  prices. Everything else is marked UNCONFIRMED.

## 3. Sources

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
