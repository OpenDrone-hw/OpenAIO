# LCSC / JLCPCB Sourcing Snapshot — 2026-06-12

JLC = JLCPCB assembly parts library stock; LCSC = retail warehouse. $@100 = LCSC USD unit price at 100-pc ladder. **All parts are Extended for JLCPCB assembly** (zero basic parts in the design). No formal EOL flags, but several parts are effectively unavailable.

## Stock table

| LCSC# | MPN | Role | JLC | LCSC | $@100 | Risk |
|---|---|---|---|---|---|---|
| C2765098 | AT32F421G8U7 | ESC MCU ×4 | 3,288 | 464 | 0.538 | ⚠ LCSC retail <1k (need 4/board) |
| C41414478 | NSG2065Q | gate driver ×4 | **365** | 4,373 | 0.278 | ⚠ JLC <1k |
| C49441966 | DOY180N03T | ESC FET ×24 | **not in JLC lib** | 1,450 | 0.227 | ⚠⚠ consign or global-source; 1,450 pcs = 60 boards |
| C2058245 | INA186A3IDCKR | CSA | **318** | 4,047 | 0.465 | ⚠ JLC <1k (known issue confirmed) |
| C5219316 | LMR54406DBVR | ESC buck | 5,014 | 57,377 | 0.230 | OK |
| C2848334 | TLV76733DRVR | ESC LDO | 8,666 | 4,000 | 0.180 | OK |
| C5267406 | LSM6DSV16XTR | IMU | 2,883 | **10** | 3.154 | ⚠⚠ LCSC retail empty; JLC ok for now |
| C5219261 | LMR51430YFDDCR | FC buck ×2 | 1,187 | 7,921 | 0.513 | OK (JLC marginal) |
| C3235557 | TPS2116DRLR | power mux | 11,017 | 18,448 | 0.268 | OK |
| C524780 | LP5912-3.3DRVR | 3.3 V LDO | 3,997 | 7,720 | 0.597 | OK |
| C893189 | NCV8187AMT180TAG | 1.8 V gyro LDO | **62** | **19** | 0.380 | ⚠⚠⚠ **effectively unobtainable — replace before any spin** |
| C7463385 | COS8051SOT | OSD opamp | 11,538 | 4,675 | 0.218 | OK |
| C2876045 | TLV7031DPWR | OSD comparator | **172** | 5,556 | 0.270 | ⚠ JLC <1k |
| C2673087 | SN74LVC1G3157DTBR | OSD switch | 2,868 | 2,565 | 0.097 | OK |
| C498185 | TF-021B-H265 | microSD slot | 9,124 | 32,596 | 0.179 | OK |
| C41378174 | RP2354A | FC MCU (QFN-60) | **184** | 3,674 | 1.269 | ⚠ JLC <1k; LCSC retail fine |
| C2858491 | ESP32-C3FH4 | RX MCU | 3,520 | 16,528 | 1.569 | OK |
| C2151551 | SX1281IMLTRT | RX radio | 3,470 | **4** | 2.255 | ⚠ LCSC retail empty; JLC ok |
| C2861882 | TLV75533PDQNR | RX LDO | **103** | 1,400 | 0.186 | ⚠ JLC <1k |
| C2651081 | 2450FM07D0034T | RX BPF | 3,798 | **0** | 0.253 | ⚠ LCSC retail 0; JLC ok |
| C89334 | 2450AT18A100E | Wi-Fi antenna | **729** | 5,235 | 0.301 | ⚠ JLC <1k |
| C160405 | SM06B-SRSS-TB | JST SH 6P | 4,840 | 65,780 | 0.242 | OK |
| C160407 | SM08B-SRSS-TB | JST SH 8P | 7,624 | 265,850 | 0.255 | OK |

Whoop-specific parts (OpenAIO-Whoop): see that repo's `docs/ESC_DESIGN.md` — headline risks there are AGM310MAP (515 pcs total), BY25Q64ESCIG (1 pc — swap part), EFM8BB51F16G (not in JLC lib, 17k at LCSC retail).

## Action items

1. **NCV8187AMT180TAG replacement — candidates compared on actual PSRR curves (gyro load ≈1 mA), 2026-06-12:**

   | Freq | NCV8187 (curve) | LP5912-1.8 (curve) | TPS7A2018 (spec) |
   |---|---|---|---|
   | 1 kHz | ~90 dB | ~78 dB | 95 dB |
   | 10 kHz | ~70 dB | ~58 dB | **75 dB** |
   | 100 kHz | ~40 dB | ~50 dB | **75 dB** |
   | 300 kHz | ~35 dB (valley) | ~50 dB | ~70 dB |
   | 1 MHz (buck fsw) | ~50 dB | ~47 dB | 45 dB |
   | Noise | 15 µVrms | 12 µVrms | **7–10 µVrms** |

   **Preferred: TPS7A2018** — dominates both legacy parts through the band where motor-PWM/loop noise lives (10 k–300 kHz). Packages: X2SON-4 **1×1 mm** DQN (LCSC C2878130 only 42 pcs; DigiKey 25k @ $0.136 — consign) or SOT-23-5 DBV (LCSC C963430, 25k stock, $0.144). Costs PG (D8 LED net) and a footprint change. At 1 MHz all three are equivalent — kill buck ripple with an input ferrite/RC regardless.
   **No-new-footprint alternative: LP5912-1.8DRVR** (C2876234) — same WSON-6 2×2 land pattern as the design's LP5912-3.3, keeps PG, but has a ~58 dB valley at 10–30 kHz (still a higher floor than NCV8187's 35 dB @ 300 kHz). LCSC 550 / DK 5.8k.
   Applies family-wide (OpenAIO, OpenAIO-Whoop, OpenFC-Lite-Mini).

   *How the IMU LDO is spec'd (rationale):* three bands matter, not one cutoff. (a) **DC–1 kHz, hardest requirement** — ripple here couples directly into the flight-control band as fake rotation; the dominant real aggressors are ELRS TX current bursts at packet rate (250 Hz–1 kHz) and motor/prop-wash-correlated rail sag. (b) **~20–30 kHz** — MEMS gyro drive resonance; supply tones here intermodulate into the sense path, so keep ≥55–60 dB (this is exactly where LP5912 dips). (c) **buck fsw ~1.1 MHz + harmonics** — aliases/demodulates through the IMU's internal sampling; no LDO is strong there (all ~45–50 dB), so a ferrite/RC pole ahead of the LDO handles it regardless of part choice. LDO output noise (7–15 µVrms, 1/f corner) sits below the gyro's own noise floor for all three candidates — not a differentiator.
2. **DOY180N03T** — not orderable through JLCPCB assembly. Options: consignment, JLCPCB global sourcing, or revisit the MOSFET (see `ALTERNATIVES.md`).
3. Prototype runs are fine on current JLC stock for everything else; the <1k-JLC parts (NSG2065Q, INA186A3, TLV7031, RP2354A, TLV75533, antenna) need pre-order/reservation for any production batch.
