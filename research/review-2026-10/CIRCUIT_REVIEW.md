# OpenAIO Core + Base: circuit review (baseline d81e559)

Reviewer scope: the schematic and netlist of the two-board design at `d81e559`
(the Base routed with zones refilled), checked against the datasheets in
`hardware/KiCad-Library/datasheet/`. This is a circuit review. Layout is covered
only where it changes a circuit conclusion.

Tags: **[main]** means the finding also applies to main `9968ebb` (one board with the
OpenFC-Core module, netlist `scratchpad/mainnet.json`). **[main: fixed]** means main
already fixed it. **[main: n/a]** means main has no such circuit, or it sits inside the
private core.

## 0. Method and artefacts

- `git diff --stat 105e858 d81e559 -- 'hardware/*.kicad_sch'` is **empty**. d81e559
  changed only the PCBs and 8 footprints in `lib.pretty`. The exported d81e559 netlist
  JSON is byte-identical to the 105e858 one (`oldnet.json`), so every schematic finding
  in NOTES carries over unchanged.
- Files in `scratchpad/review/`:
  - `d81e559.net`, `d81e559.json`: netlist and its JSON.
  - `d81e559_dump.txt`, `dump_tagged.txt`: per-part pin to net dump, tagged [CORE]/[BASE].
  - `erc_d81e559.json`: ERC output.
  - `Core.json`, `Base.json`: pcbnew pad, track and via dumps of the d81e559 boards.
  - `boards.json`: which part sits on which board.
  - `ds/*.txt`: the datasheets as text.
  - `cr/`: scratch scripts plus `main_dump.txt`.
- Board assignment: Core has 87 parts and Base has 254. No part is on both boards and
  none is missing.
- ERC (d81e559, all severities): 1128 violations.
  - 32 errors: 16 pin_not_driven, 9 power_pin_not_driven, 3 bus_to_net_conflict,
    1 hier_label_mismatch, 1 pin_to_pin, 1 pin_not_connected.
  - Warnings: 101 endpoint_off_grid, 8 multiple_net_names, 14 lib_symbol_mismatch,
    419 lib_symbol_issues, 172 footprint_link_issues, 379 pin_to_pin, 4 unconnected
    wire endpoints.
  - Every error was traced (§4, O10). None hides a real connectivity fault: the SPI0,
    SPI1 and I2C0 nets each carry all their expected pins.

## 1. Ranked findings (overview)

| # | Rank | Finding | Applies to main |
|---|---|---|---|
| B1 | **Blocking** | The +10V gate-drive rail is switched by a FC GPIO (no pull resistor) and shared with VTX power. This allows LMR51430 EN abs-max violations on USB power, NSG2065Q input abs-max violations while +10V is off, and a PINIO "VTX off" that also kills all four ESCs | [main] |
| B2 | **Blocking** | UART1_RX has two push-pull drivers: ESP32-C3 U0TXD and SH-6 pin 6 (DJI SBUS) | [main: fixed] |
| B3 | **Blocking (BOM)** | 16 +BATT bulk capacitors have no value or LCSC. ESP32-C3 has no MPN/LCSC (the variant with flash is required). L4, D9 and FL1 have no LCSC | [main] (16 caps + ESP32-C3) |
| S1 | Should-fix | 2S is outside the NSG2065Q recommended VCC (8 V) and VBS (≥ 6 V). DJI-class VTX on +10V also browns out at 2S. AGENTS.md misquotes the datasheet | [main] |
| S2 | Should-fix | FC +3.3V is made on the Base and fed through one LGA pad over 59 mm of Core copper. ADC_AVDD is unfiltered. The LP5912 CIN/COUT stability window is broken (both LDOs) | 3.3 V part [main: fixed]. LP5912-1.8 [main: n/a] |
| S3 | Should-fix | The +3V3 TLV75533 (500 mA, 1 x 1 mm) feeds ESP32-C3, SX1281, 4x AT32, SD, INA186 and WS2812. Espressif asks ≥ 0.5 A for the C3 alone | [main] (worse: LR1121 + RFX2401C) |
| S4 | Should-fix | BMI270 ASDx/ASCx are tied to GND. The BMI270 datasheet says "Do not connect to GND" | [main: n/a] |
| S5 | Should-fix | The BOOTSEL resistor R7 = 10 kΩ gives zero margin to VIL. The datasheet recommends 4.7 kΩ | [main: n/a] |
| S6 | Should-fix | No SWD access to RP2354A (SWCLK/SWDIO NC; TP10 exists but is "not on board") | [main: n/a] |
| S7 | Should-fix | NSG2065Q VCC has only a 100 nF 0201 (about 3.5 mm away) for 1.2/1.5 A gate pulses and 3 bootstrap recharges | [main] |
| S8 | Should-fix | +10V output capacitance is about 6 µF effective vs TI's 3 x 10 µF table. +5V is borderline | [main] |
| S9 | Should-fix | The FC cannot reset the ESP32-C3 or put it in its bootloader (CHIP_EN is RC-only; BOOT is a solder pad) | [main: fixed] |
| S10 | Should-fix | XL-1010 WS2812 runs at 3.3 V; its VDD minimum is 3.5 V | [main] |
| S11 | Should-fix | SX1281 pin 5 (GND, between XTA and XTB) is marked no-connect and is floating on the PCB | [main: n/a] (LR1121) |
| S12 | Should-fix (low) | 0201 resistors carry about 23 V at 6S (VBAT divider R1, 4x3 BEMF top resistors) | [main] (BEMF) |
| O1-O12 | Optimisation | Crystal, USB, ADC_AVDD, AT32 VDDA, INA186 gain, LED/buzzer drivers, SD, OSD, ESP32 GPIO10, ERC hygiene, 2S bootstrap, catalogue labels | per item |
| M1 | Verify (main only) | USB D+/D- cross over at J1. UART pad names cross over at J1 | main only |

---

## 2. Verification of the seven NOTES findings against d81e559

| NOTES # | Verdict on d81e559 | Evidence and correction |
|---|---|---|
| 1. +10V shared, EN from GPIO, no pull | **Confirmed, extended** (B1) | +10V (17 nodes) is: U14/16/18/20.4 (NSG2065Q VCC), U12.1 (SH-6 pin 1), Core pads J41/J51 (via LGA pad 7), C23, C43/50/57/64, R17, R21. 10V_ENABLE has 4 nodes only: U2.41 (GPIO27), J91.1, J90.1, U3.5. RP2350 pads reset with PDE=1, ISO=1 (RP2350 DS Table 853, PADS_BANK0 GPIO), so +10V is **off by default** until firmware drives GPIO27. New on top of NOTES: while +10V is off, the AT32s are powered (+3V3), and any AM32 output (startup tones, beacon, brake) drives HIN/LIN above VCC+0.3, the NSG2065Q abs max (§8.1, p5) |
| 2. LMR51430 EN vs VIN = 0 | **Confirmed** (B1) | LMR51430 SLUSEF4A §7.1 (p4): EN max = VIN + 0.3 V. §8.3.3 note (p12): "Do not apply EN voltage when VIN is 0 V", and the pin "cannot be left open or floating". On USB only, VBUS → D3 → +4v5 → U7 → +3.3V powers the RP2354A while +BATT ≈ 0, so GPIO27 high violates the rating. Small correction: the pin table (p3) also says "If the EN pin is left floating, the device is disabled", so floating is defined but not allowed per §8.3.3 |
| 3. NSG2065Q at 2S | **Confirmed, with a correction** (S1) | NSG2065Q DS v1.0: the p1 feature bullet says "Gate drive supply range from 5 V to 20 V". **§8.5 Recommended Operating Conditions (p5) says VCC 8-20 V and VB ≥ VS + 6 V**, and every electrical characteristic is specified only at VCC = VB = 15 V (§8.6). UVLO is 4.5 typ / 4.9 max for both VCC and VBS, with 0.2 V hysteresis (§8.6.2, p6). The bootstrap path is the integrated BSD, RBSD ≤ 300 Ω (§8.6.2). So the AGENTS.md "inside its 5-20 V supply range" quotes the marketing bullet. The binding table says 8 V. The MOSFET is not the limit: DOY180N03T RDS(on) is 1.3/1.7 mΩ (typ/max) at VGS 4.5 V vs 1.0/1.2 at 10 V |
| 4. UART1_RX contention | **Confirmed** (B2) | UART1_RX (6 nodes): U22.28 (ESP32-C3 U0TXD, push-pull), U12.6 (SH-6 pin 6 = DJI SBUS out), U2.10 (GPIO7), J55 (Core pad), J90/J91.33. No series resistor anywhere. Main fixed it (ESP on its own core UART; SH-6.6 goes to PIOUART1_RX) |
| 5. FC +3.3V via one LGA pad | **Confirmed, extended** (S2) | U7 (LP5912-3.3) and C28 22 µF sit on the Base. Core +3.3V loads are 33 nodes behind J91.8. Core +3.3V copper is 58.9 mm (F.Cu 36.1, In2 13.5, In3 7.8, B.Cu 1.5) with 11 vias. LGA pad 8 to VREG_VIN is 14.2 mm in a straight line. New: LP5912 COUT max is 10 µF and CIN min is 0.7 µF effective (LP5912 §7.6, p7). U7 sees 22 µF + 4.7 µF + 11 x 100 nF out, and only C26 100 nF in (1.7 mm). The nearest µF-class +4v5 cap, C82, is 17.3 mm away |
| 6. SD card on +3V3 | **Confirmed, downgraded to optimisation for the domain mismatch, and folded into S3 for load** | Card1.4 and R34 are on +3V3 (U23 TLV75533). SPI0 and FLASH_CS are driven from the +3.3V domain. Both LDOs come from +4v5 and ramp together, so cross-domain back-powering is limited to LDO ramp skew and +3V3 brown-outs. Trivial fix on d81e559: U7 is on the Base too, so move Card1.4 and R34 to +3.3V without any LGA cost (or see §7, flash on the Core) |
| 7. ERC | **Confirmed, more detail** | See §0 for counts. `hier_label_mismatch` is the Power sheet's (fc_power) dangling sheet pin CURR. CURR itself is connected through global labels: U25.6, J90/J91.2, R5. `pin_to_pin` U7 PG ↔ GND is a false positive: LP5912 §8.3.6 allows PG to GND when unused. `pin_not_connected` TP10 is a TestPoint with `on_board no` in fc_rp2350a (probably meant for SWD, see S6). The 16 `pin_not_driven` come from capacitor symbols with "input" pin type (C37 and C40-42 in each ESC). The 9 `power_pin_not_driven` are missing PWR_FLAGs, U22 VDD3P3 fed via L6, and U24 VBAT. The 3 `bus_to_net_conflict` are cosmetic: the nets resolve correctly |

---

## 3. Blocking

### B1. +10V gate-drive rail: FC-switched, unpulled, shared with VTX. [main]
- **Refs/nets:** U3 LMR51430YFDDCR EN = `10V_ENABLE` = U2 GPIO27 via LGA pad 1.
  - +10V → U14/U16/U18/U20 VCC (NSG2065Q), U12.1 (SH-6), J41/J51 (Core VTX pads), D4/R21.
  - Main has the same topology: U8.EN = J1.23, +10V → U12/14/16/18.4, U10.1, J28/J38.
- **What breaks:**
  1. **Default-off ESC drive.** RP2350 GPIO27 resets with its pull-down on (PDE=1). +10V
     stays off until Betaflight drives GPIO27 high through a PINIO. With no PINIO
     configured, or a target default that leaves it low, all four ESCs have no gate
     drive.
  2. **PINIO "VTX power" switch.** A Betaflight PINIO VTX-power switch toggles the ESC
     gate supply too. A user who powers down the VTX on the bench or in flight disables
     the motors.
  3. **NSG2065Q input abs max.** VIN(HIN/LIN) ≤ VCC + 0.3 V (§8.1, p5). The AT32F421s
     run from +3V3 as soon as +4v5 exists, on battery or on USB. AM32 startup tones,
     beacon or brake drive 3.3 V into a driver with VCC = 0. The input ESD then back-feeds
     the +10V net, and through U3's high-side body diode +BATT as well.
  4. **LMR51430 EN abs max on USB.** See NOTES 2: EN ≤ VIN + 0.3 V, "do not apply EN
     voltage when VIN is 0 V" (§7.1 p4, §8.3.3 p12). On USB only, a GPIO27 high
     violates this.
  5. **Floating EN.** EN floats while the Core is unpowered or unfitted, and during
     the +5V → +4v5 → +3.3V ramp. §8.3.3 forbids a floating EN.
  6. **Shared rail noise.** The VTX load (DJI O3-class, around 0.5-1 A at 10 V) shares
     the rail with 1.2/1.5 A gate pulses, and C43-C64 are only 100 nF (S7).
- **Fix (recommended):**
  - Tie **U3 EN to +BATT**, exactly like U4 (zero parts). +10V then comes up with the
    battery, and the NSG2065Q UVLO protects at low VIN.
  - This frees GPIO27 and LGA pad 1. Use GPIO27 for RX_EN (S9), or for a **VTX-only**
    load switch: a P-MOSFET in series with the VTX branch only (U12.1 + VTX pads),
    rated ≥ 20 V and |VGS| ≥ 12 V (AO3401A class, LCSC TBD, not in PARTS-USED). Drive it
    from an AP1606 (C2849580, catalogue), with 100 kΩ (C270364) gate pull-down on the
    AP1606 so the VTX is **on** by default and the GPIO turns it off.
  - The ESC gate supply must never be firmware-switchable.
- **If the switch must stay as is (not recommended):** add 100 kΩ (C270364) from U3 EN
  to GND on the Base, and 10 kΩ in series from GPIO27. This defines the off state but
  still leaves items 1-3.

### B2. UART1_RX driven by both ESP32-C3 TX and SH-6 pin 6. [main: fixed]
- **Refs/nets:** U22.28 U0TXD, U12.6, U2.10 (GPIO7, UART1 RX via F11 AUX, RP2350 Table 3
  p17), J55, J90/J91.33.
- **Problem:** with a stock DJI O3/O4 6-pin harness plugged in, the air unit's SBUS
  output and the ESP32 TX are two push-pull outputs on one wire. CRSF frames corrupt,
  and the ESP32 pin fights the air unit.
- **Fix (d81e559, no free GPIO):**
  - Disconnect U12.6 from UART1_RX. Either route it to `PU0RX` (GPIO3, PIOUART0 RX, also
    pad J45; the user picks one function), or leave pin 6 NC (onboard ELRS makes DJI
    SBUS redundant).
  - If a shared wire must stay, put 1 kΩ (C270365) in series at U22.28. That limits the
    fight but does not fix the data.
  - The main design (dedicated UART for the RX, SH-6.6 on PIOUART1_RX) is the reference.

### B3. BOM holes that block turnkey assembly. [main]
- **Bulk capacitors with value "C" and no LCSC:**
  - d81e559: C90-C101 (3 x 0805 per ESC), C102, C103 (0805), C105, C106 (1206), all on
    +BATT.
  - main: C35, C36, C39, C40, C50-52, C60-62, C70-72, C80-82.
  - As drawn, the ESC bus decoupling is undefined. Fix: 0805 → **4.7 µF 50 V X5R
    CL21A475KBQNNNE, C98192** (catalogue, already C18/C19). 1206 → **4.7 µF 50 V X7R
    TCC1206X7R475K500HT, C380366** (catalogue, OpenESC).
  - Document a user low-ESR electrolytic on the battery leads (≥ 35 V, 220-470 µF).
    At 25 V DC bias the ceramics keep only about 30 % of their rated value.
- **U22 ESP32-C3** has no MPN or LCSC. The SPI-flash pins are NC, so it **must** be the
  version with in-package flash: set **ESP32-C3FH4, C2858491** (catalogue, OpenRX).
  Same for main U4.
- **No LCSC:**
  - D9 → C5349953 (catalogue).
  - FL1 → C2651081 (catalogue).
  - L4 15 µH 0805 (SX1281 DC-DC) → Semtech reference BOM part **TDK MLZ2012M150W**
    (SX1281 DS, §15 BOM). LCSC TBD; import with easyeda2kicad.

---

## 4. Should-fix

### S1. 2S operation outside the gate-driver spec. [main]
- **Evidence:** NSG2065Q §8.5 (p5): VCC 8-20 V, VB ≥ VS + 6 V. §8.6.2: VCC and VBS UVLO+
  4.5 typ / 4.9 max, 0.2 V hysteresis, RBSD ≤ 300 Ω. DOY180N03T Qg = 39.8 nC at 10 V.
- **At 2S:**
  - Pack: 8.4 V full, about 6.0-6.4 V sagged at the end of a flight.
  - U3 is in dropout (98 % DMAX with frequency foldback, LMR51430 §7.6 note 2), so
    VCC ≈ VIN − 0.1-0.2 V ≈ 6 V.
  - VBS ≈ VCC − RBSD·I − Qg/Cboot (39.8 nC / about 80 nF effective ≈ 0.5 V) ≈ 5.3-5.5 V.
    That is below the 6 V recommended minimum and only 0.4-1.0 V above the worst-case
    VBS UVLO. A punch-out sag can drop a high side mid-commutation (desync).
  - IR AN-978-style sizing at VCC = 6 V needs Cboot ≈ 2(2Qg + Iqbs/f + Qls)/(VCC − Vf − VLS − VUVLO,max)
    ≈ 175 nC / 0.9 V ≈ 190 nF. Fitted: 100 nF.
  - At 3S (≥ 9.6 V sagged) everything is inside spec.
- **Second victim:** DJI O3/O4-class air units need ≥ 7.4 V on SH-6 pin 1 (+10V), and
  +10V follows the pack down at 2S.
- **Fix:** pick one.
  - (a) Declare the envelope **3S-6S** in README and AGENTS.md, and correct the
    "5-20 V" sentence to cite §8.5.
  - (b) Keep 2S: generate the gate-drive VCC with a small boost or SEPIC (≥ 10 V from
    6 V), and go to 220 nF / 25 V X7R 0402 bootstrap caps (O11).
  - (c) Get NSIC to characterise the part at VCC 6 V.

### S2. FC 3.3 V supply path and LP5912 cap windows. [3.3 V part: main fixed; LP5912-1.8: main n/a]
- **Path:**
  - +3.3V comes from U7 on the Base through LGA pad 8, then 58.9 mm and 11 vias of Core
    copper.
  - It feeds IOVDD x6, QSPI_IOVDD, USB_OTP_VDD, **ADC_AVDD (unfiltered)**, VREG_VIN (the
    switching core regulator) and VREG_AVDD (30 Ω / 4.7 µF, fine).
  - The only µF-class cap on the Core is C15, 4.7 µF at VREG_VIN (1.0 mm). The LDO's
    regulation point and C28 22 µF are on the Base.
  - VBAT (GPIO29) and CURR (GPIO28) are measured against this noisy reference.
- **LP5912 limits (LP5912 §7.6, p7):** CIN ≥ 0.7 µF effective, COUT 0.7-10 µF,
  ESR 5-500 mΩ.
  - **U7:** COUT = C28 22 µF (0402 6.3 V) + C15 4.7 µF + 11 x 100 nF ≈ 28 µF nominal,
    about 12-14 µF effective at 3.3 V. Over the limit. CIN locally is C26 100 nF only.
  - **U6 (1.8 V gyro LDO, Core):** COUT = C27 22 µF (GRM155R60J226ME11D) + C29. At 1.8 V
    bias that is still about 15 µF, also over the limit.
- **Fix:**
  - **Move U7 to the Core** (main did this). +4v5 already crosses; LGA pad 8 is freed.
  - Size the outputs: U7 COUT ≈ 4.7 µF (keep C15) + the 100 nF array, drop C28. U6:
    C27 → **4.7 µF CL05A475MP5NRNC, C23733** (catalogue).
  - CIN at U7 and U6 → **1 µF 25 V 0402 CL05A105KA5NQNC, C52923** (catalogue).
  - Filter ADC_AVDD from +3.3V: 33 Ω (or a 0201 ferrite) + 1 µF (C76935).
  - If U7 stays on the Base for now: replace C26 with 1 µF (C52923) and cut C28 to 1 µF.

### S3. +3V3 rail (TLV75533PDQNR, U23) over budget. [main, worse]
- **Loads on +3V3** (49 nodes):
  - ESP32-C3: Espressif DS v1.9 Table 5-2 asks **IVDD ≥ 0.5 A** from the supply; TX
    802.11b at 21 dBm draws 335 mA (Table 5-7).
  - SX1281.
  - 4x AT32F421: 16.7 mA each at 120 MHz (AT32F421 Table 17).
  - microSD (50-100 mA write peaks), INA186, WS2812, TCXO.
- **TLV755P limits:** IOUT ≤ 500 mA (§6.3). RθJA for DQN (1 x 1 mm) is 168.4 °C/W (§6.4).
  - In flight (about 250 mA): (4.6 − 3.3) V x 0.25 A ≈ 0.33 W, about +55 °C rise.
  - Bench with ELRS WiFi update: about 450 mA peaks, 0.6 W, about +100 °C, at the
    current limit.
- **Main:** adds the LR1121 (high-power PA from VBAT) and the RFX2401C PA on the same
  regulator.
- **Fix:**
  - Swap U23 for **TLV76733DRVR, C2848334** (catalogue, 1 A, WSON-6 2 x 2, already used
    on OpenESC). Or split the rail: give the 4 AT32s (and the SD card, if it stays)
    their own TLV76733 as on OpenESC-20x20, and keep the TLV75533 for the radio.
  - Add 4.7 µF (C23733) at Card1 VDD (only C36 100 nF today, 3.7 mm away, opposite side).

### S4. BMI270 auxiliary pins grounded. [main: n/a]
- **Refs:** U8 pins 2 (ASDx) and 3 (ASCx) are on GND. The symbol uses LSM6DSV16X names
  (SDx/SCx/Qvar).
- **Evidence:** BMI270 DS BST-BMI270-DS000-08, Table 22, footnote ** (p135): "If secondary
  interface is unused, ASDx and ASCx can be connected to VDDIO or left unconnected. **Do
  not connect to GND.**" The LSM6DSV16X allows Vdd_IO or GND (LSM6DSV16X Table 2).
- **Fix:** tie pins 2 and 3 to **+3.3V (VDDIO)**. That is valid for both footprint
  options. The rest of the IMU is correct: CSB pull-up R25, INT1 → GPIO9, 100 nF on VDD
  and VDDIO per §7.2, OCSB/OSDO NC.

### S5. BOOTSEL resistor. [main: n/a]
- **Refs:** R7 10 kΩ between QSPI_SS and U1 (button to GND).
- **Evidence:** RP2350 DS §5.2 (p374): "A 4.7 kΩ resistance to ground is a good
  intermediate value." Pull-up RPU at 3.3 V is 32-86 kΩ, and VIL max is 0.8 V
  (§14.9.4, p1340). With 10 kΩ and a 32 kΩ pull-up, VCSn = 0.79 V: no margin.
- **Fix:** R7 → **1 kΩ 0201WMF1001TEE, C270365** (catalogue, same part as R5/R6), or
  4.7 kΩ.

### S6. No SWD on the RP2354A. [main: n/a]
- **Refs:** U2.24 SWCLK and U2.25 SWDIO are no_connect. TP10 exists in fc_rp2350a but is
  `on_board no`.
- **Impact:** no debugger for Betaflight bring-up, and no SWD recovery path (UF2
  BOOTSEL is the only one).
- **Fix:** two 0.6-0.8 mm test pads on the Core, on the top side or at a Core edge off
  the LGA. They cost no LGA pads.

### S7. NSG2065Q VCC decoupling. [main]
- **Refs:** C43/C50/C57/C64, 100 nF GRM033R6YA104KE14D (0201, about 50-60 nF at 10 V),
  3.0-3.7 mm from VCC. The rail's only bulk cap, C23, is 10-17 mm away.
- **Why it matters:** each low-side turn-on pulls up to Qg = 40 nC at 1.5 A, and every
  bootstrap recharge (100 nF via RBSD) comes out of VCC too. ΔV ≈ 40 nC / 55 nF ≈ 0.7 V
  per edge. The usual rule is CVCC ≥ 10 x Cboot = 1 µF.
- **Fix:** add **1 µF 25 V 0402 CL05A105KA5NQNC, C52923** (catalogue) at each VCC pin,
  next to the existing 100 nF.

### S8. Buck output capacitance. [main]
- **Evidence:** LMR51430 Table 9-2 (p16, 1.1 MHz): 5 V → 3.3 µH and 2 x 10 µF/25 V;
  12 V → 6.8 µH and 3 x 10 µF/25 V.
- **Fitted:**
  - +10V: L2 4.7 µH and C23 22 µF/16 V 0603 X5R (CL10A226MO7JZNC). That is roughly
    5-7 µF effective at 9.8 V (estimate).
  - +5V: C24, same part, about 10-12 µF at 5 V.
- **Fix:**
  - +10V: add a second **22 µF 0603 C2762594** (catalogue) at U3, preferably a 25 V
    rated 10-22 µF if one is sourced. Plus the 4 x 1 µF from S7.
  - +5V: add one 22 µF (C2762594).
  - Verify with a 0 → 1 A load step on +10V.

### S9. ESP32-C3 flashing and reset path. [main: fixed]
- **As drawn:**
  - CHIP_EN = R114 10 kΩ + C84 1 µF (RC only).
  - GPIO9 BOOT = R113 pull-up + TP9 solder pad.
  - GPIO2 (SX1281 NRESET, R111) and GPIO8 (LED, R112) are pulled high, which is
    correct for SPI and Joint-Download boot (ESP32-C3 DS v1.9 Table 3-3).
  - UART0 goes to RP2354 UART1 and pads J54/J55.
- **Consequence:** FC passthrough flashing only works while ELRS firmware is alive and
  reboots itself into ROM download. A blank or bricked C3 needs TP9 shorted during a
  full power cycle.
- **Fix:**
  - Use the GPIO27 freed by B1 as **RX_EN**: open-drain onto CHIP_EN, keeping the RC.
  - Optionally bring out GPIO18/19 (native USB-Serial-JTAG) as factory test pads.
  - Main carries both RX_EN and RX_BOOT.

### S10. WS2812 (XL-1010RGBC) below its supply minimum. [main]
- **Refs:** D9 (main D1) VDD on +3V3.
- **Evidence:** XL-1010RGBC electrical table: VDD 3.5-5.5 V, VIH 2.8 V min.
- **Fix:** power D9 from **+4v5** (about 4.6 V, already at U23 on the RX sheet). The
  3.3 V DIN from GPIO8 still meets VIH 2.8 V. Keep a 100 nF at VDD.

### S11. SX1281 pin 5 GND floating. [main: n/a]
- **Refs:** U21.5 is `no_connect` in the schematic and `unconnected-(U21-GND-Pad5)` on
  the Base PCB.
- **Evidence:** SX1281 pin table: pin 5 = GND. It is the guard between XTA (4, TCXO in)
  and XTB (6, NC).
- **Fix:** connect pin 5 to GND.

### S12. 0201 resistors at 23 V. [main for BEMF]
- **Refs:** R1 100 kΩ VBAT divider top (Core, 0201WMF): 22.9 V at 6S full. The ESC BEMF
  top resistors R47/R50/R53 (x4) are RC0201 10 kΩ on the phase nodes.
- **Evidence:** 0201 working-voltage ratings are about 25 V for these series (check the
  Uniroyal/Yageo sheets), and phase ringing and regen spikes exceed 25.2 V.
- **Fix:** 0402 parts for R1 and the BEMF top resistors, or two 0201 in series. R1 moves
  to the Base anyway in §7.

---

## 5. Optimisation

- **O1. Crystal.**
  - X1 XTM25012000JT00351001 has C4/C10 20 pF and R6 1 kΩ.
  - The XTM-2520 series sheet lists CL options from 6 to 20 pF and ESR ≤ 100 Ω at
    12-16 MHz. The ordering code's CL is not stated in the sheet.
  - The effective load here is about 10 pF + 2-3 pF stray ≈ 13 pF.
  - RP2350 §8.2.1.1 (p555) recommends ABM8-272-T3 (CL 10 pF, ESR ≤ 50 Ω) and warns that
    other crystals need temperature testing.
  - Action: confirm CL with the vendor and set C = 2(CL − Cstray). It flies on
    OpenFC-Lite-Mini, so low risk.
- **O2. USB.**
  - RP2350 asks for 27 Ω series resistors (pin description p16). R8/R9 are 30 Ω 5 %;
    acceptable, 27 Ω is the exact value.
  - There is no ESD on D+/D-/VBUS. Add a 2-line TVS (USBLC6-2P6 or a 0201 TVS pair,
    LCSC TBD) at USB1 on the Base. [main]
  - There is no VBUS detect (no GPIO free). Fine.
- **O3. RP2354A decoupling.**
  - 3.3 V side: 10 supply pins (IOVDD x6, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN)
    have 7 x 100 nF + 4.7 µF. Pico-2-style is 100 nF per pin + 4.7 µF at VREG_VIN.
  - DVDD x3 has 2 x 100 nF + 2 x 4.7 µF.
  - Add 2 x 100 nF on 3.3 V and 1 x 100 nF on DVDD if space allows. Six of the 3.3 V caps
    are 2.5-9.1 mm from VREG_VIN.
- **O4. AT32F421 VDDA.** Fig. 8 (p26) asks for 100 nF + 1 µF. Fitted is R40-type 10 Ω +
  100 nF only. Add **1 µF C76935** (catalogue) per ESC. [main]
- **O5. INA186 range.**
  - Fitted: A3 = 100 V/V with 0.2 mΩ gives 20 mV/A. Full scale is (3.3 − 0.04) V /
    0.02 ≈ 163 A (INA186 §6.5: VSP ≥ VS − 40 mV; VZL ≤ 10 mV; VOS ±50 µV = ±0.25 A;
    BW 35 kHz; CLOAD ≤ 1 nF, satisfied because R5 1 kΩ isolates C9).
  - A 4-motor toothpick peaks around 40-60 A, which uses 25-37 % of the range.
    **INA186A4 (200 V/V)** gives 81 A full scale and twice the resolution (LCSC TBD).
  - The Core RC filter R5/C9 (1 kΩ / 100 nF, 1.6 kHz) is in the right place, at the ADC.
    Main's differential input filter (1 kΩ + 1 kΩ, 1 µF + 2 x 100 nF) is a good addition
    to copy.
- **O6. LED strip and buzzer.**
  - Q2 is an open-drain inverter with R14 2.4 kΩ to +5V. With about 100 pF of cable,
    τ ≈ 0.24 µs against WS2812 T0H ≈ 0.4 µs: marginal on long strips. It also makes the
    signal inverted, which firmware must handle. Use 1 kΩ, or a push-pull 5 V buffer.
  - Q1 buzzer: add a flyback **SDM02U30LP3-7B, C151629** (catalogue) across the buzzer
    pads.
- **O7. SD card** (if it stays):
  - Supply from the SPI master's domain (S3, NOTES 6).
  - 33 Ω series resistors at the Core on SCK/MOSI/CS (the SPI0 nets run 18-24 mm on the
    Base with 9-17 mm detours).
  - 47-100 kΩ pull-ups on DAT1/DAT2 (both NC today).
  - 4.7 µF at VDD.
- **O8. OSD (verify).**
  - The sync path (C33 + D8 clamp → TLV7031, IN− = GND) is fine. TLV7031 VCM extends
    0.1 V past VEE and it has no phase reversal.
  - The pass-through path (VIDEO_IN → 3157 → COS8051 x2) has no DC restore. It only
    works with cameras whose sync tip sits ≥ 0 V, because the 3157 range is 0..VCC and
    the COS8051 CMR starts at −0.1 V. That matches the OSD_LVL levels (0.26 V / 1.06 V)
    being absolute DC. Test with AC-coupled cameras, or add a clamp on the camera path.
- **O9. ESP32-C3 GPIO10 hard-tied to GND.** A firmware that drives it high shorts it.
  Leave it NC (main does).
- **O10. ERC hygiene.**
  - Remove the CURR sheet pin from the Power sheet symbol.
  - Fix the three bus-pin wires.
  - Add PWR_FLAGs.
  - Set capacitor pin types to passive.
  - Either place TP10 (S6) or delete it.
- **O11. Bootstrap caps.** 100 nF CL05B104KB54PNC is fine at 3S-6S. Use 220 nF 25 V X7R
  0402 only if 2S stays in scope (S1). [main]
- **O12. PARTS-USED.md label errors** (catalogue repo):
  - C270365 is listed as "10k" but its MPN 0201WMF1001TEE is **1 kΩ**.
  - C274342 is listed as "10k" but its MPN RC0201FR-07220RL is **220 Ω**.
  - Fix in the KiCad-Library repo, not here.

---

## 6. Power tree, sequencing, USB-only behaviour

```
Battery pad /CSA+ → Rsense2 0.2 mΩ (INA186 U25 on +3V3) → +BATT (2S-6S)
  ├─ U4 LMR51430 (EN = VIN) → +5V 4.98 V → pads (cam/VTX/LED/buzzer), R14 → D2 DSK24 ─┐
  ├─ U3 LMR51430 (EN = GPIO27!) → +10V 9.85 V → 4x NSG2065Q VCC, SH-6.1, J41/J51 (Core) │
  ├─ 4x 6 DOY180N03T bridges                                                            │
  └─ R1/R2 VBAT divider (Core, via LGA pad 26)                                          │
USB VBUS → D3 DSK24 ────────────────────────────────────────────────────────→ +4v5 ≈ 4.6 V
  +4v5 → U7 LP5912-3.3 (Base) → +3.3V → LGA pad 8 → RP2354A, BMI270 VDDIO, OSD, D6
       → U6 LP5912-1.8 (Core) → BMI270 VDD
       → U23 TLV75533 (Base) → +3V3 → ESP32-C3, SX1281, TCXO, 4x AT32, INA186, SD, WS2812
       → J42/J52 (Core pads, external RX)
  RP2354A VREG (3.3 µH AOTA, 2x 4.7 µF) → +1.1V
```

- **On battery:**
  - VIN UVLO 3.89 V. +5V then +4v5 then the three LDOs ramp together; no PG gating
    anywhere.
  - The RP2354A (internal POR/BOR), the AT32s and the ESP32-C3 (10 ms RC on CHIP_EN)
    boot within milliseconds.
  - +10V waits for firmware (B1). The AM32 startup routine runs with the drivers
    unpowered.
- **USB only:**
  - Powered: +4v5 (VBUS − 0.35-0.45 V), the FC, gyro, ELRS RX, all four AT32s, SD and
    INA186.
  - Unpowered: +BATT, +5V, +10V (VTX/cam/LED strip/buzzer pads, gate drivers).
  - Typical draw is 200-250 mA. ELRS WiFi update peaks around 450 mA, near the 500 mA
    USB 2.0 budget and the TLV75533 limit (S3).
  - Abs-max events on USB: LMR51430 EN (B1.4), and NSG2065Q inputs from AM32 activity
    (B1.3). Both back-feed +10V/+BATT via ESD and body diodes. B1's fix removes both.
- **USB and battery together:** D2/D3 OR the two 5 V sources. Whichever is higher feeds
  +4v5. No back-feed into the host or into +5V.
- **Domain crossings:**
  - FC → AT32 (MOTOR, 220 Ω at the AT32: good).
  - FC ↔ ESP32 (UART, no series R).
  - FC → SD (SPI, no series R).
  - INA186 (+3V3) → FC ADC (1 kΩ R5: good).
  - All of them are from +4v5, so ramp skew is small. Add 33 Ω at the Core on SPI0 and
    UART1 if they stay cross-domain.

## 7. Decoupling per IC (d81e559)

| IC | Present | Datasheet asks | Verdict |
|---|---|---|---|
| RP2354A 3.3 V pins (10) | 7 x 100 nF, 4.7 µF (C15, 1.0 mm at VREG_VIN) | 100 nF/pin, 4.7 µF VREG_VIN (RP2350 Fig. 19, p451) | −2 x 100 nF (O3) |
| RP2354A DVDD (3) + VREG out | 2 x 100 nF, 2 x 4.7 µF | 100 nF/DVDD, 2 x 4.7 µF | −1 x 100 nF |
| RP2354A VREG_AVDD | 30 Ω + 4.7 µF (1.5 mm) | 33 Ω + 4.7 µF | OK |
| BMI270 | 100 nF VDD (C29), 100 nF VDDIO (C30) | 100 nF each (§7.2) | OK |
| LP5912-1.8 (U6) | CIN 4.7 µF, COUT 22 µF + 100 nF | CIN ≥ 1 µF, COUT ≤ 10 µF | COUT over (S2) |
| LP5912-3.3 (U7) | CIN 100 nF, COUT 22 µF + Core 5.8 µF | same | both out (S2) |
| OSD (U9/U10/U11) | 100 nF each | 100 nF | OK |
| LMR51430 U3/U4 | CIN 4.7 µF 50 V each; COUT 22 µF/16 V each | Table 9-2 | +10V low, +5V borderline (S8) |
| NSG2065Q x4 | 100 nF 0201 | rule ≥ 10 x Cboot | add 1 µF (S7) |
| AT32F421 x4 | VDD 100 nF, VDDA 10 Ω + 100 nF, NRST 100 nF | VDD 100 nF; VDDA 100 nF + 1 µF; NRST 100 nF (Fig. 8, Fig. 18) | +1 µF VDDA (O4) |
| TLV75533 | CIN 10 µF + 1 µF, COUT 1 µF + 10 µF | 1-200 µF | OK (load: S3) |
| ESP32-C3 | 2 x 10 µF, 3 x 1 µF, 7 x 100 nF, 10 nF on +3V3; VDD3P3 via 2 nH + 1 µF | Espressif reference (OpenRX copy) | OK |
| SX1281 | DCC 15 µH + 470 nF + 10 nF, VR_PA 10 nF, VBAT/VBAT_IO 100 nF | §15.2 Fig. 15-3 | OK |
| INA186 | 100 nF (C104, 1.7 mm) | 100 nF | OK |
| microSD | 100 nF (3.7 mm, other side) | bulk 4.7-10 µF customary | add 4.7 µF (S3/O7) |

---

## 8. Board split: what belongs where

### 8.1 Today's LGA (34 pads)
- 18 signals, 5 power (+10V, +3.3V, +4v5, +5V, +BATT) and 11 GND: **GND ratio 32 %**.
- **Base F.Cu under the Core land** (sampled on a 0.25 mm grid, J90 bbox):
  - 51 % +BATT pour.
  - 7 % GND.
  - About 2 % ESC4 phase copper (/4A, /4B, /4C).
  - 37 % no pour.
- **Core B.Cu** (facing it across the solder stand-off) carries about 115 mm of signal
  routing: I2C0 28 mm, 10V_ENABLE 14 mm, UART1 22 mm, **CURR 11.6 mm**,
  **VIDEO_IN 10 mm**, LED_STRIP 5.8 mm, MOTORx 9 mm.
- **Six Core user pads sit within 0.3 mm of an LGA pad** (J35, J37, J39, J48, J49, J50).
  Soldering a wire there reheats the LGA joint 0.8 mm below.

### 8.2 Per-net verdict

| LGA net (pad) | Core side today | Base side today | Belongs | Action |
|---|---|---|---|---|
| 10V_ENABLE (1) | GPIO27 | U3.EN | neither | **Remove**: U3 EN → +BATT (B1). GPIO27 → RX_EN or VTX_EN |
| CURR (2) | R5/C9 → ADC | INA186 out | sensor on Base, filter on Core | **Keep** (today's split is right). Route off Core B.Cu |
| SPI0 MISO/SCK/MOSI, FLASH_CS (3-6) | SPI0 master | Card1, R34, C36 | Core | **Replace the microSD with 16 MB SPI NOR on the Core** (e.g. W25Q128JV, WSON-8 or SOIC-8; LCSC TBD). Saves 4 pads, the 9-17 mm detours and the cross-domain supply |
| +10V (7) | J41/J51 VTX pads only | U3 | Base | **Remove**: VTX power pads to the Base (next to SH-6) |
| +3.3V (8) | all FC loads | U7, C28, D6 | Core | **Remove**: U7 to the Core (S2). D6 to the Core or delete |
| USB_D+/D- (9, 13) | R8/R9 → U2 | USB1 | PHY and 30 Ω on Core, ESD on Base | **Keep**, flanked by GND. ESD at USB1 (O2) |
| +4v5 (12) | U6, D7/R23, J42/J52 | D2/D3 OR | Core supply | **Keep, use 2 pads**. It becomes the only Core supply input (about 150 mA) |
| +5V (14) | R14 + J30/J37 | U4 | Base | **Remove**: Q2/R14 and the 5 V pads to the Base |
| MOTOR1-4 (17, 18, 22, 23) | GPIO22-25 | 220 Ω → AT32 PB4 | crossing | **Keep**. Optional 33 Ω source resistor on the Core |
| BUZZER- (21) | Q1 drain | J29 | Base | **Cross logic `BEEPER`**. Q1/R13 and the flyback diode go to the Base |
| +BATT (26) | R1 (VBAT divider) only | all power | Base | **Cross `VBAT_SENSE`** (≤ 2.3 V). R1/R2 to the Base, C2 stays at the ADC. No 25 V on the Core |
| UART0 TX/RX (30, 31) | GPIO0/1 + J48/J49 | SH-6.3/.4 | crossing | **Keep** |
| LED_STRIP (32) | Q2 + R14 | J20/21/31/32 | Base | **Cross logic `LED_STRIP_L`** |
| UART1 TX/RX (33, 34) | GPIO6/7 + J54/J55 | ESP32-C3 (+ SH-6.6) | crossing | **Keep**. Drop SH-6.6 (B2) |

### 8.3 Target LGA list (recommended: Core = FC + 3.3 V LDO + blackbox flash)

| Group | Nets | Count |
|---|---|---|
| ESC | MOTOR1, MOTOR2, MOTOR3, MOTOR4 | 4 |
| USB | USB_D+, USB_D- | 2 |
| Serial | UART0_TX, UART0_RX, UART1_TX, UART1_RX | 4 |
| Analog | CURR, VBAT_SENSE | 2 |
| Logic to Base drivers | BEEPER, LED_STRIP_L | 2 |
| Control | RX_EN (ESP32-C3 CHIP_EN, open-drain), or VTX_EN for a VTX-only load switch | 1 |
| Power | +4v5, +4v5 | 2 |
| Ground | GND | 11 |
| **Total** | **15 signals, 2 power, 11 GND** | **28 pads, GND 39 %** (−6 pads, −3 signals, −3 power vs today) |

- **Same 34-pad land (no footprint change):** put GND on the 6 freed sites. That gives
  15 signals, 2 power and 17 GND: **GND 50 %**, as main's 52-pad core (26 GND).
- **If the microSD stays on the Base:** add SPI0 x3 + SD_CS. That is 19 signals, 2 power
  and 13 GND (34 pads, 38 %). Power the card from Base +3V3 with 33 Ω series resistors
  at the Core.
- **Placement rules for the pin map:**
  - USB pair adjacent and fenced by GND on both sides.
  - MOTOR1-4 as one block with a GND between pairs.
  - CURR and VBAT_SENSE adjacent, each next to GND, far from USB, motors and +4v5.
  - Each +4v5 pad next to a GND pad.
  - GND in all four corners (the highest-strain LGA sites).
- **Copper rules:**
  - Base F.Cu under the Core land solid GND: move the +BATT pour and all phase copper
    out.
  - Core B.Cu: GND plus LGA pads only, no signal routing.
  - Move Core user pads off the LGA footprint, or to the Base, so wire soldering does not
    reflow LGA joints.
- **Length removed:**
  - 59 mm of +3.3V and 56 mm of +5V Core routing.
  - 18 mm of +10V on the Core, plus the Base branch to LGA pad 7.
  - 29 mm of 10V_ENABLE.
  - All SPI0 Base routing and its 9-17 mm detours.

---

## 9. Main only (verify against the OpenFC-Core pin map)

- **M1a. USB data lines cross at J1.** J1.15 "D-" is on net /D+ (USB1 A6/B6 DP), and
  J1.22 "D+" is on /D- (USB1 A7/B7 DN). If the core is RP2350-class, a swap can be
  absorbed only by OTP USB_BOOT_FLAGS.DP_DM_SWAP for the bootrom plus USB_MUXING.SWAP_DPDM
  at runtime (RP2350 DS Table 1211). Otherwise USB, including the bootloader, does not
  enumerate. Confirm whether the vendored symbol or the wiring is wrong.
- **M1b. UART names cross at J1.**
  - Core UART0_TX → pad `PU0RX`, and UART0_RX → pad `PIOUART0_TX`.
  - PIOUART1_TX → SH-6.4 (`UART0_RX`), which is the air unit's TX: TX meets TX unless
    the PIO pin is reassigned as RX in firmware.
  - Silkscreen and Betaflight target must agree. Confirm.
- Main already fixes NOTES 4 and 5 and S9, and adds a differential INA186 input filter.
- Still open on main: B1, B3, S1, S3 (worse), S7, S8, S10, S12 (BEMF), O2, O4, O11.
