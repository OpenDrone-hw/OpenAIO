# OpenAIO current sensing: Kelvin-sensed PCB copper vs. discrete shunt

Market survey, literature review, firmware constraints and recommendation

- Board under study: OpenAIO, 25.5 mm toothpick AIO, 2-6S, 4x AM32 ESC, Betaflight FC, INA186A3 (100 V/V), 0.2 mOhm 2512 shunt.
- Date of research: 2026-10-07. Sources were fetched on this date. Every claim carries a URL. Claims I could not confirm are marked **UNCONFIRMED**. Numbers I calculated myself are marked **(derived)** and show their inputs.
- Photo evidence: for the market survey I downloaded product photos (mostly 1000-1600 px) and inspected them, cropping when needed. Each row gives a confidence level:
  - **High**: a shunt body plus a legible value marking, or a manufacturer render or diagram that labels the part as a shunt.
  - **Medium**: a metal-strip or chip shunt body is clearly visible near the battery pads, but the marking or package is uncertain.
  - **Low**: a probable shunt that I cannot resolve.
  - **Not identified**: the shunt location is not visible (heatsink, case, or that side is not photographed), or no candidate part is visible.

---

## 0. Bottom line

1. **No product in the sample uses PCB-copper current sensing.** The sample covers 34 AIOs and 20 4-in-1 ESCs from the 12 requested brands and others, plus 6 open-source designs. Every board where the sense element could be seen uses a discrete shunt: 22/34 AIOs, 13/20 ESCs and 5/5 open designs with a documented sensor. The other 7 ESCs and 12 AIOs could not be resolved from photos. None advertises trace or copper sensing.
2. **Literature on copper sensing is consistent.** It works only with per-board calibration plus temperature compensation, and even then the best reported results are about 1-4%:
   - ams AS8510 (copper-specific algorithm): ±1%.
   - Renesas SLG47011 (digital lookup table): ≤4.2%.
   - TI two-point calibration: about 1-5% at one temperature, with no temperature compensation.
3. **Copper's TCR is about 0.39 %/°C, so resistance rises about 26% from 30 °C to 100 °C (derived).** Stock Betaflight (`ibata_scale`, `ibata_offset`) and AM32 (`MILLIVOLT_PER_AMP`, `CURRENT_OFFSET`) are purely linear with no temperature term. Without a firmware fork, compensation would have to be analog: an NTC network or a dedicated compensating IC.
4. **Recommendation: keep a discrete metal-alloy shunt with proper Kelvin taps.** If loss or headroom matters, go to 0.1 mOhm (2x 0.2 mOhm 2512 in parallel, as in OpenESC-30x30 and Holybro Tekko32 50A) and consider INA186A4 (200 V/V) to keep 20 mV/A. **Main risk of the copper option:** temperature drift that stock firmware cannot correct, about +26% over 30-100 °C, on top of fab-lot thickness variation of tens of percent that forces per-board calibration.

---

## 1. Market

### 1.1 How the counts were made
- Product pages and photos come mainly from Shopify stores, read through their product JSON: RaceDayQuads, UnmannedTech, betafpv.com, newbeedrone.com and holybro.com.
- Value markings are decoded with two conventions:
  - "R001" = 1 mOhm, using EIA R-as-decimal. Example: the Bourns part-number scheme "L represents decimal point (L500 = .500 milliohms)" ([Bourns CSS2H-2512 datasheet](https://www.bourns.com/docs/product-datasheets/css2h-2512.pdf)).
  - "m30", "0m25", "m50" = 0.30, 0.25 and 0.50 mOhm, using the "m as decimal point in milliohms" convention (for example "0m25" = 0.25 mOhm). This is per a search summary of the CTS 73M datasheet ([CTS 73M datasheet](https://www.mouser.com/datasheet/2/96/73M1A-73M2A-73M3x-73M5-1662200.pdf)). The PDF itself could not be fetched, so the convention is **UNCONFIRMED from the primary text**; it is widely used.
- Bare "0.2" or "0.5" printed on copper-coloured alloy shunts is read as mOhm. **UNCONFIRMED unit.**
- Betaflight board configs do not reveal hardware. 606 of 630 configs in `betaflight/config` define `ADC_CURR_PIN` and 386 set a scale (commit 1e3f778, 2026-10-06) ([betaflight/config](https://github.com/betaflight/config)). So a pin or scale in a config does not prove a sensor exists.

### 1.2 Whoop and toothpick AIOs (25-26 mm class first), 34 boards

| # | Product | Sense element seen | Value / package | Confidence | Source |
|---|---|---|---|---|---|
| 1 | BetaFPV Toothpick F405 2-4S 20A AIO V5 | Discrete shunt, ESC side by battery pads | "R001" (1 mOhm), white body, about 5x3 mm (2010/2512 class) | High | [WREKD](https://wrekd.com/products/betafpv-toothpick-f405-2-4s-20a-aio-brushless-flight-controller-v5-blheli_s-icm42688) |
| 2 | BetaFPV F4 2-3S 20A AIO FC V1 | Discrete chip shunt at "+" tab | "R001", about 1206 | Medium | [betafpv.com](https://betafpv.com/products/f4-2-3s-20a-aio-fc-v1) |
| 3 | BetaFPV Air 1S brushless FC (G4) | Discrete chip shunt by battery pads | "R001", about 1206 | Medium | [betafpv.com](https://betafpv.com/products/air-brushless-flight-controller) |
| 4 | BetaFPV Matrix V2 1S 12A | None visible; sensor not advertised | - | Not identified | [RDQ](https://www.racedayquads.com/products/betafpv-matrix-v2-aio-g4-fc-12a-1s-esc-400mw-vtx-elrs-2-4ghz-solderless) |
| 5 | Happymodel 1S F4 AIO 5A ELRS | None visible; not advertised | - | Not identified | [RDQ](https://www.racedayquads.com/products/happymodel-1s-f4-aio-toothpick-whoop-flight-controller-w-5a-8bit-4in1-esc-200mw-vtx-elrs-2-4ghz-spi) |
| 6 | Happymodel CrazyF405 HD 1-2S 12A | Sensor advertised ("current meter scale 470"); no 2512/2010 part visible | - | Not identified | [RDQ](https://www.racedayquads.com/products/happymodel-crazyf405-elrs-hd) |
| 7 | Happymodel SuperX AIO V2 1S 5A | Advertised ("Current meter scale 1175"); not resolved | - | Not identified | [RDQ](https://www.racedayquads.com/products/happymodel-superx-aio-v2-f4-5a-1s-blheli_s-esc-elrs-2-4ghz) |
| 8 | Happymodel Crazybee G473 5-in-1 1S 5A | Small black chip resistor next to B+ pad | "02" visible; about 0805/1206; value unknown | Low-medium | [RDQ](https://www.racedayquads.com/products/happymodel-crazybee-v1-0-5-in-1-aio-g473-fc-5a-1s-bluejay-esc-elrs-rx) |
| 9 | JHEMCU GHF411AIO Pro 25/35A 2-6S | Advertised ("Built-in Current Sensor"); ESC side not shown | - | Not identified | [UnmannedTech](https://www.unmannedtechshop.co.uk/products/ghf411-pro-aio-toothpick-flight-controller-25a-35a-2-6s) |
| 10 | Flywoo GOKU ERVT 1S 5A | None visible (renders); not advertised | - | Not identified | [RDQ](https://www.racedayquads.com/products/flywoo-goku-ervt-5-in-1-aio-f405-fc-1s-5a-esc-400mw-vtx-elrs-rx-osd) |
| 11 | Flywoo GOKU GN405S 20A AIO | Advertised; white rectangular part by USB/+ pad | Probably a white-body shunt; marking illegible | Low | [UnmannedTech](https://www.unmannedtechshop.co.uk/products/goku-gn-405s-20a-aio-icm42688-25-5-x-25-5) |
| 12 | Flywoo GOKU GN745 AIO V3 45A | Discrete shunt next to battery pads (render) | "R 001" | High | [UnmannedTech](https://www.unmannedtechshop.co.uk/products/goku-gn745-45a-aio-32bit-flight-controller) |
| 13 | Flywoo GOKU F405 HD 1-2S 12A V2 | Unclear small chip near VCC; not advertised in retailer text | - | Not identified | [UnmannedTech](https://www.unmannedtechshop.co.uk/products/flywoo-goku-f405-hd-1-2s-12a-elrs-v2-aio-flight-controller) |
| 14 | iFlight Blitz F411 1S 5A | None visible; not advertised | - | Not identified | [RDQ](https://www.racedayquads.com/products/iflight-f4-1s-5a-toothpick-whoop-flight-controller-2-4ghz-elrs-w-ceramic-antenna) |
| 15 | iFlight Defender 25 Blitz F7 AIO 20A | Render shows a part labelled "2512" by the battery pads; "Current sensor: ratio 200" | 2512 shunt (value not shown) | High | [UnmannedTech](https://www.unmannedtechshop.co.uk/products/iflight-defender-25-blitz-f7-aio-20a) |
| 16 | GEPRC Taker F411 2-4S 12A AIO | Discrete shunt by battery pads | "R001", white body, 2512 class | High | [RDQ](https://www.racedayquads.com/products/geprc-taker-f411-2-4s-aio-whoop-toothpick-w-12a-8bit-4in1-esc-elrs-2-4ghz-spi) |
| 17 | GEPRC F411 2-6S 35A AIO (25.5 mm) | Discrete shunt, ESC side; "Current meter: 210" | "R001", white body | High | [RDQ](https://www.racedayquads.com/products/geprc-f411-2-6s-aio-toothpick-whoop-flight-controller-w-35a-4in1-esc) |
| 18 | T-Motor F411 1S 13A AIO (same board as Tron80 F4 HD AIO) | Unmarked metal-alloy chip shunt at "+" pad | About 1206-2010 | Medium | [RDQ](https://www.racedayquads.com/products/t-motor-f411-1s-toothpick-whoop-aio-w-13a-esc), [UnmannedTech](https://www.unmannedtechshop.co.uk/products/tron80-aio-fc-esc-replacement-rma) |
| 19 | T-Motor F7 35A AIO | Discrete shunt by battery pads | "m50" (0.5 mOhm) | High | [UnmannedTech](https://www.unmannedtechshop.co.uk/products/t-motor-f7-35a-aio-flight-controller) |
| 20 | Holybro Kakute G4 AIO 35A AM32 (25x25 holes, 33 mm board) | Copper-alloy shunt at "+" pad; "Onboard analog current sensor" | "0.2", about 7x3.5 mm from the dimension photo (2512) | High | [holybro.com](https://holybro.com/products/kakute-g4-aio-35a) |
| 21 | SpeedyBee F405 AIO V2 35/40A (25.5 mm) | The manufacturer's annotated diagram labels a **"Shunt Resistor"** between the battery pads; "Scale=88" | Value not shown | High | [UnmannedTech](https://www.unmannedtechshop.co.uk/products/speedybee-f405-v2-aio-35-40a-3-6s-flight-controller-esc-25-5x25-5mm) |
| 22 | Skystars Jupiter AIO F4 45A | Advertised ("Current Scale: 400"); covered | - | Not identified | [RDQ](https://www.racedayquads.com/products/skystars-jupiter-aio-f4-3-6s-whoop-toothpick-flight-controller-w-45a-blheli_s-4in1-esc-mpu6000) |
| 23 | Aikon F7 Mini AIO 45A (BLHeli_32) | Advertised ("Current Sensor Scale: 200"); ESC side not shown | - | Not identified | [RDQ](https://www.racedayquads.com/products/aikon-f7-mini-25x25-aio-flight-controller-w-45a-32bit-4in1-esc) |
| 24 | Aikon F7 AIO 60A 8-bit | Metal-strip shunt by V+ pad | Marking illegible | Medium | [RDQ](https://www.racedayquads.com/products/aikon-3-6s-f7-aio-flight-controlller-w-60a-8bit-esc) |
| 25 | Lumenier LUX HD G4 AIO 35A AM32 | Shunt by "+" pad; "Current sensor: Analog" | "m30" (0.3 mOhm), 2512 | High | [RDQ](https://www.racedayquads.com/products/lumenier-lux-hd-g4-aio-whoop-toothpick-flight-controller-w-35a-am32-4in1-esc) |
| 26 | Airbot Fenix G4 AIO 35A AM32 (appears to be the same OEM board as #25) | Shunt by "+" pad, cropped at full resolution | "m30", about 6.5x3.3 mm, so 2512 | High | [RDQ](https://www.racedayquads.com/products/airbot-fenix-g4-4-6s-aio-toothpick-whoop-flight-controller-w-35a-32bit-am32-4in1-esc) |
| 27 | HDZero Gamma AIO 45A AM32 | Alloy shunt at VBAT pad; "Scale = 107" | "0.2", 2512 class | High | [RDQ](https://www.racedayquads.com/products/hdzero-gamma-45a-hd-ready-aio) |
| 28 | HDZero AIO15 15A | Alloy chip shunt by battery pads | "0.5", about 1206 | Medium | [RDQ](https://www.racedayquads.com/products/hdzero-aio15-g4-fc-15a-esc-elrs-2-4ghz-rx-200mw-vtx) |
| 29 | NewBeeDrone Hummingbird 255 AIO 50A AM32 (25.5 mm) | Shunt between battery tabs | "R001", white body, 2512 class | High | [newbeedrone.com](https://newbeedrone.com/products/hummingbird-255-aio-flight-controller-at32f435-am32-45a-3-6s) |
| 30 | NewBeeDrone BeeBrain BLV5 1-2S 18A | None visible; not advertised | - | Not identified | [RDQ](https://www.racedayquads.com/products/newbeedrone-beebrain-blv5-aio-g4-fc-18a-1-2s-4-in-1-bluejay-esc-mpu6000-25x25) |
| 31 | HGLRC Specter F722 3-6S 25A AIO | Shunt by "+" pad | "m30", 2512 class | High | [RDQ](https://www.racedayquads.com/products/hglrc-specter-f722-3-6s-aio-whoop-toothpick-flight-controller-w-25a-8bit-4in1-esc) |
| 32 | DeepSpace Talos AIO 40A AM32 | Copper-coloured metal-strip part near the battery edge | Illegible | Medium | [RDQ](https://www.racedayquads.com/products/deepspace-talos-aio-f722-fc-40a-4-6s-blheli_32-esc) |
| 33 | AxisFlying Argus F745 AIO 40A AM32 | Advertised ("Amperage Meter: 200 Scale"); not resolved | - | Not identified | [RDQ](https://www.racedayquads.com/products/axisflying-argus-f745-aio-f745-fc-40a-4-6s-am32-esc) |
| 34 | NeutronRC AT32F435 Mini AIO | The manufacturer diagram labels a "R001" part **"Current sensor"**; "Scale 100" | "R001", 2512 class | High | [UnmannedTech](https://www.unmannedtechshop.co.uk/products/neutronrc-at32f435-mini-aio-flight-controller) |

**AIO counts (n = 34):**
- Discrete shunt identified: **22**, of which 14 High, 6 Medium and 2 Low or Low-medium.
- Sensor advertised but element not resolvable: **6**.
- No sensor advertised and nothing visible: **6**, all 1S or 2S whoop class. Whether a sensor exists on these is **UNCONFIRMED**. Absence from the text is not proof: #3 shows an R001 shunt although its page text never mentions current.
- PCB-trace or copper sensing confirmed: **0**.
- Not examined: Foxeer's AIO (the F745 AIO V4 listing image is a 12,000 px tall composite and was skipped) ([UnmannedTech](https://www.unmannedtechshop.co.uk/products/foxeer-reaper-f745-aio-v4-flight-controller-mpu6000-f745-35a-bls-2-4s)).

### 1.3 4-in-1 ESCs, 20 boards

| # | Product | Sense element | Value | Conf. | Source |
|---|---|---|---|---|---|
| 1 | Holybro Tekko32 50A AM32 (V2.2T) | **2 alloy shunts in parallel** next to a SOT-23-6 amplifier | 2x "0.2", so 0.1 mOhm; scale 120 | High | [RDQ](https://www.racedayquads.com/products/holybro-tekko32-50a-4-6s-am32-4-in-1-esc-30-5x30-5-f4-mcu) |
| 2 | Holybro Tekko32 F4 Metal 65A AM32 | 2 shunts in parallel next to the amplifier | 2x "m30", so 0.15 mOhm; scale 180 | High | [RDQ](https://www.racedayquads.com/products/holybro-tekko32-f4-metal-65a-am32-4-in-1-esc) |
| 3 | Foxeer Reaper F4 Mini 60A | 2 shunts in parallel | 2x "m30" | High | [RDQ](https://www.racedayquads.com/products/foxeer-reaper-f4-32bit-60a-3-8s-20x20-4in1-esc) |
| 4 | HDZero Halo 70A AM32 | 2 copper-alloy shunts at the battery pads; "Scale = 170" | Illegible | High (type) | [RDQ](https://www.racedayquads.com/products/hdzero-halo-70a-3-8s-am32-4-in-1-esc-20x20) |
| 5 | Flywoo GOKU G45M 45A AM32 | Shunt (render) | "R 001" | High | [RDQ](https://www.racedayquads.com/products/flywoo-goku-g45m-45a-3-6s-am32-4-in-1-esc-20x20) |
| 6 | iFlight Blitz E55S Mini 55A (BLHeli_S) | Shunt; "Current Sensor: Yes" | "0m25" (0.25 mOhm) | High | [RDQ](https://www.racedayquads.com/products/iflight-blitz-mini-e55s-mini-v1-1-8bit-55a-2-6s-20x20-4in1-esc) |
| 7 | Lumenier Razor LED F4 55A AM32 | 2 shunts in parallel next to the amplifier | 2x "m30" | High | [RDQ](https://www.racedayquads.com/products/lumenier-razor-led-f4-55a-2-6s-am32-4-in-1-esc-30x30) |
| 8 | Lumenier Siege 55A AM32 | 2 shunts in parallel | 2x "m30" | High | [RDQ](https://www.racedayquads.com/products/lumenier-siege-g071-55a-3-6s-4-in-1-am32-esc-ndaa) |
| 9 | NewBeeDrone Hummingbird 305 80A AM32 | Two white-body shunts | 2x "R001" (probable) | Medium | [RDQ](https://www.racedayquads.com/products/hummingbird-305-4in1-esc-80a-3-8s-am32-30x30-built-for-durability-reliability) |
| 10 | TBS Lucid 60A 8S AM32 | Shunt | "0m25" | High | [RDQ](https://www.racedayquads.com/products/tbs-lucid-60a-8s-am32-4-in-1-esc) |
| 11 | XILO Stax V3 50A AM32 | 2 shunts in parallel | 2x "m30" | High | [RDQ](https://www.racedayquads.com/products/xilo-stax-v3-f4-50a-am32-3-6s-4-in-1-esc) |
| 12 | AxisFlying Argus 55A (BLHeli_32) | Shunt; "Scale=400" | "0m25" | High | [RDQ](https://www.racedayquads.com/products/axisflying-argus-32bit-55a-3-6s-30x30-4in1-esc) |
| 13 | HAKRC HK3220 60A | Shunt | "0m25" | High | [RDQ](https://www.racedayquads.com/products/hakrc-hk3220-2-8s-blheli_32bit-60a-20x20-4in1-esc) |
| 14 | Aikon AK32 V3 55A | Covered by heatsink; "Current Sensor Scale: 210" | - | Not identified | [RDQ](https://www.racedayquads.com/products/aikon-ak32-v3-55a-6s-30x30-4in1-esc) |
| 15 | Aikon AK32PRO II 50A | Covered | - | Not identified | [RDQ](https://www.racedayquads.com/products/aikon-ak32pro-ii-32bit-50a-2-6s-20x20-4in1-esc) |
| 16 | Skystars KO60II 60A AM32 | Covered | - | Not identified | [RDQ](https://www.racedayquads.com/products/skystars-ko60ii-60a-3-6s-am32-4-in-1-esc-30x30) |
| 17 | HGLRC Specter G071 60A | Metal case | - | Not identified | [RDQ](https://www.racedayquads.com/products/hglrc-specter-g071-128k-32bit-60a-3-6s-20x20-4in1-esc) |
| 18 | JHEMCU BL32 60A | No shunt visible on the photographed face; amplifier-like SOT next to battery pads | - | Not identified (**UNCONFIRMED**: other side not shown) | [RDQ](https://www.racedayquads.com/products/jhemcu-bl32-32bit-60a-3-6s-4in1-esc-choose-version) |
| 19 | Flywoo GOKU Quad V3 35A 16x16 (BLHeli_S) | Small metal part between battery pads; "C" pin on connector | - | Not identified (**UNCONFIRMED**) | [RDQ](https://www.racedayquads.com/products/flywoo-goku-quad-v3-35a-2-4s-4-in-1-blheli_s-esc-16x16) |
| 20 | FETtec SFOC 50A (FOC) | No board-level shunt visible on either face; sensing method unknown | - | Not identified (**UNCONFIRMED**) | [RDQ](https://www.racedayquads.com/products/fettec-sfoc-50a-2-8s-4-in-1-esc) |

**ESC counts (n = 20):** discrete shunt **13** (12 High, 1 Medium); not identified **7**; copper or trace confirmed **0**. **6 of the 13 use two shunts in parallel** to cut loss.

Revision note: Holybro's own table shows the Betaflight scale changing between board revisions of the same ESC, for example Tekko32 F4 50A going 168 to 110 to 120 ([Holybro docs](https://docs.holybro.com/esc/current-sensor-scale)). Even with discrete shunts, the effective scale depends on layout. An observation that is **UNCONFIRMED**: Tekko32 50A at scale 120 with 0.1 mOhm implies about 12 mV/A against roughly 10 mV/A nominal for a 100 V/V amplifier, which hints that copper between the sense taps adds resistance. The amplifier gain was not verified.

### 1.4 Open-source designs

| Design | Sensing | Source |
|---|---|---|
| OpenESC-20x20 (incutec / OpenDrone-hw) | Single 0.2 mOhm 2512 (LCSC C695806) + INA186A3 at 100 V/V, giving 20 mV/A and 165 A full scale | [AGENTS.md](https://raw.githubusercontent.com/incutec-hw/OpenESC_20X20/main/AGENTS.md) |
| OpenESC-30x30 | Two 0.2 mOhm 2512 in parallel (0.1 mOhm) + INA186A3, giving 10 mV/A and about 330 A full scale | [AGENTS.md](https://raw.githubusercontent.com/incutec-hw/OpenESC-30x30/main/AGENTS.md) |
| crteensy ESC_4in1_G071_1S3_SIZ200 | "0m5 current sense shunt with INA186A2" (0.5 mOhm by the m-decimal convention) | [GitHub](https://github.com/crteensy/ESC_4in1_G071_1S3_SIZ200) |
| Kestrel ESC (HeyPCB) | "2 x 0.5 mOhm 2512 low-side shunts", INA180A2, 12.5 mV/A, Betaflight `ibata_scale 125`; not yet built | [GitHub](https://github.com/HeyPCB/kestrel-esc) |
| Cogless (single-channel FOC) | "2 mOhm 2512 shunt, Kelvin-routed differential pair" | [GitHub](https://github.com/rmingon/Cogless) |
| DroneController (STM32F411 AIO) | Current sensing not documented | [GitHub](https://github.com/FPV-Drone-STM32F411/DroneController) |

AM32 firmware targets: `Inc/targets.h` has 126 `MILLIVOLT_PER_AMP` definitions and 3 `NO_CURRENT_SENSE` targets. Defaults are 20 mV/A and offset 0 ([targets.h](https://raw.githubusercontent.com/am32-firmware/AM32/main/Inc/targets.h)). The file does not say which sense element each target uses.

Bluejay and BLHeli_S ESCs do not report current. Current on such builds is analog to the FC only ([ArduPilot ESC telemetry](https://ardupilot.org/copter/docs/common-esc-telemetry.html); detail **UNCONFIRMED** from the Bluejay repository itself).

**Open-source count:** 5 of 5 designs with documented sensing use discrete shunts; 0 use copper.

### 1.5 Shunt values observed (all designs)

| Value | Where seen |
|---|---|
| 1 mOhm (R001) | BetaFPV x3 (one 2010/2512 class, two about 1206), GEPRC x2, Flywoo GN745 and G45M, NBD 255, NeutronRC, NBD 305 (2x) |
| 0.5 mOhm | T-Motor F7 AIO ("m50"), HDZero AIO15 ("0.5"), crteensy ("0m5"), Kestrel (2x) |
| 0.3 mOhm ("m30") | Single: LUX/Fenix, HGLRC F722. Doubled: Tekko32 65A, Reaper F4 Mini, Razor LED, Siege, XILO |
| 0.25 mOhm ("0m25") | Blitz E55S, TBS Lucid, Argus 55A, HAKRC HK3220 |
| 0.2 mOhm | HDZero Gamma, Kakute G4 AIO, Tekko32 50A (2x), OpenESC-20x20, OpenESC-30x30 (2x) |

The trend: whoop and 1S boards use 1 mOhm chip shunts (about 1206). 25-30 mm AIOs use one 2512 at 0.2-1 mOhm. 50-80 A 4-in-1s use 0.25-0.3 mOhm or two in parallel. The OpenAIO's 0.2 mOhm is already at the low end of the market.

---

## 2. Technical literature on PCB-copper current sensing

### 2.1 TI, SBOA533A "Using a PCB Copper Trace as a Current Sense Shunt Resistor" (Stanfel, Morse; rev. April 2026) ([PDF](https://ti.com/lit/pdf/sboa533))

**Setup.** Traces of 8, 100, 200 and 1750 mil, 1-3 inches long, read by an INA190.

**Room-temperature error against a 1 oz calculation:**
- -31% to -58% for 8-200 mil traces.
- About 0-3% only for the 1750 mil (44.5 mm) trace (Table 3-1).

**Root cause: copper thickness.** SEM sections measured 61-63.5 µm on isolated 100 and 200 mil outer traces, and 41.7 µm on the 1750 mil trace, against 34.8 µm nominal "1 oz" (Table 3-2). The note states:
- "patterns with less surrounding copper are thicker in general".
- IPC "mandate a minimum copper trace thickness, but do not specify the maximum".

**Board-to-board spread.** The same 100 mil design read -45.3% on one board and -54.8% on another (Table 3-1).

**Ground-plane mitigation.** Adding surrounding copper cut the error to about -20% but "takes up a significant amount of space" (Table 4-1).

**Two-point calibration (same board revision):**
- About -5% to +4.5% at 2.5-7 A on 100 mil traces (Tables 4-3 and 4-7).
- Applying a calibration from a different trace or revision gave +14% to +50% error (Table 4-4).
- "Batch calibration processes introduce inaccuracies".
- "Outputs settling times were recorded in excess of 5 minutes" because of self-heating.
- Calibration "does not allow for changes caused by temperature variation".

**Thermal sizing.** For 20 °C rise they sized 50 A to need the 1750 mil (44.5 mm) trace. The OpenAIO PCB is about 32 mm wide.

**Conclusion, quoted:** "Copper trace shunt resistors are not designed for any application that requires a high degree of accuracy … An implementation using this method can not be assured to behave as expected, and requires adjusting calibration constants".

### 2.2 Renesas, AN-CM-394 "Current Sensing with Cu Trace" (SLG47011 AnalogPAK, 2024) ([PDF](https://www.renesas.com/en/document/apn/cm-394-current-sensing-cu-trace))
- Copper TCR quoted as 0.393 %/°C.
- A 5 mm x 102 mm, 35 µm, 10 mOhm trace measured 9.91-10.34 mOhm across 5 prototype PCBs, a spread of about ±2% within one lot.
- Uncompensated error over -40 to 85 °C: about 27%.
- With temperature compensation (on-chip temperature sensor plus a 4096-entry 1/R lookup table and on-chip math), worst-case error was **≤4.18%** over -40 to 85 °C at 1-5 A.
- The remaining error is attributed to a chip-to-trace temperature difference "since copper traces heat up as current passes through", and the note recommends an external sensor.
- Stated drawbacks: "take up a lot of space" and "impossible to precisely control their dimensions, especially their thickness and width".
- The SLG47011 result can feed an internal DAC, an analog output in principle. Whether an SLG47011 DAC output would suit a Betaflight ADC input is **UNCONFIRMED**. Its PGA common-mode is limited to the supply, so this suits low-side (ground) sensing (**UNCONFIRMED** for FPV ground-bounce effects).

### 2.3 ams (now ams OSRAM), AS8510 copper-shunt reference design
- Uses a 10 mm PCB copper track plus an ams compensation algorithm.
- Claims ±1% over -40 to 125 °C, 40 A in the reference design and "adaptable to 100 A" ([Electronic Design, 2014](https://www.electronicdesign.com/technologies/power/article/21799690/battery-board-measures-current-without-shunt-resistor)).
- One measurement path uses a "fine copper meander trace to sense temperature" (search summary of [AN000545](https://www.mouser.com/datasheet/2/588/AS8510_AN000545_1_00-1513137.pdf); the PDF fetch returned HTTP 503, so details are **UNCONFIRMED**).
- Calibration needs (per board or not) are **UNCONFIRMED**.

### 2.4 Ratiometric copper gain resistor: TI patent and EDN/Microchip
- **US7683604B1** (Texas Instruments; Steele and Mullins; granted 2010) puts a copper gain resistor *on the amplifier die* with the same TCR as the PCB trace shunt, so compensation is automatic. It relies on a zero-drift amplifier for drops of "roughly 50 microvolts" ([Google Patents](https://patents.google.com/patent/US7683604)).
- No catalog TI part implementing this was found: **UNCONFIRMED** whether one exists.
- The INA186 has fixed internal gain resistors, so this method is not available with the current amplifier.
- Jerry Steele (Microchip; EDN, 2023) describes an interdigitated copper gain resistor with 100:1 geometry next to the shunt. He states that it needs a zero-drift amplifier and concludes: "the physically smallest solution will favor the dedicated shunt resistor" ([EDN](https://www.edn.com/current-sensing-pcb-traces-vs-shunt-resistors/)).

### 2.5 Copper-TCR compensation borrowed from inductor-DCR sensing
- Richtek AN026 (2014) describes NTC-plus-resistor networks that cancel a copper DCR TCR of about 3930 ppm/°C. With Y resistors and one NTC, the error is zero at Y chosen temperatures, for example 20, 60 and 100 °C ([PDF](https://www.richtek.com/~/media/AN%20PDF/AN026_EN.pdf)).
- Search summaries of the inductor literature note that "external compensation cannot respond quickly to changes in conductor heating" ([Electronic Design](https://electronicdesign.com/technologies/components/passives/article/21190352/copper-alloy-inductors-stabilize-current-sensing); quote from search summary).
- Qorvo/Active-Semi **US11002772B2** uses a PCB copper "temperature compensation trace" placed within 5 mm of the inductor and calibrated at room temperature ([Google Patents](https://patents.google.com/patent/US11002772)).
- **Implication for the OpenAIO (derived):** an NTC divider between INA186 OUT and the FC ADC could approximate the 0.39 %/°C slope at about 2-3 calibration points. It only tracks the copper if it sits at the copper's temperature, and the section self-heats with I²R (see 2.1 settling time and the 2.2 residual error).

### 2.6 ICs with built-in trace or copper TCR compensation
- **ADI (Maxim) MAX17260 and MAX1720x fuel gauges** offer "trace sensing with temperature compensation" with a sense-resistor range of 1-1000 mOhm, per a search snippet of the [analog.com MAX17260 page](https://www.analog.com/en/products/max17260.html). The page and datasheet fetches failed with 503, so the register details are **UNCONFIRMED**.
- These are I²C fuel gauges for battery packs. Betaflight has no driver for them, and an I²C driver would mean a firmware change.
- **Renesas SLG47011** (2.2) and **ams AS8510** (2.3) compensate digitally.
- **Allegro, Infineon, TI Hall sensors** sidestep copper TCR by sensing magnetic field (section 4).
- I found **no** current-sense amplifier with an analog output and a built-in copper-TCR gain term that is a drop-in replacement for the INA186: **UNCONFIRMED** that none exists.

### 2.7 Copper thickness and etch tolerance

**Outer layers (plated):**
- IPC-6012 specifies minimum thickness only. Finished outer copper for 1 oz base is ≥47.9 µm (Class 2) or ≥52.9 µm (Class 3); inner 1 oz is ≥24.9 µm after processing ([NCAB](https://www.ncabgroup.com/faq/how-much-finished-copper-can-be-expected/)).
- Eurocircuits notes galvanic plating tolerance and copper balance make outer copper "thicker or thinner in certain areas" ([Eurocircuits](https://www.eurocircuits.com/tolerances-on-copper-thickness/)).
- TI measured +20% to +82% over nominal on isolated outer traces (2.1).

**Inner layers (foil only):**
- IPC-4562A: foil may be up to 10% under nominal; 1 oz = 34.3 µm nominal and 30.9 µm minimum ([Siemens EDA blog](https://blogs.sw.siemens.com/electronic-systems-design/2025/08/13/copper-thickness/); search summary of the same).
- Processing removes about 5 µm on average (Siemens).
- **Derived:** inner-layer copper is better controlled than plated outer copper. Expect roughly -0% to +35% resistance versus the 34.3 µm calculation, and lot-dependent. This is **UNCONFIRMED** as a guaranteed band; fabs do not publish it.

**JLCPCB:**
- Trace width tolerance ±20%.
- Inner layers default to 0.5 oz (1 oz and 2 oz optional).
- No copper-thickness tolerance is stated ([JLCPCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities)).

### 2.8 Discrete shunts at very low values: the copper in the terminals matters
- **Vishay WSLP3921** (10.0 x 5.2 mm, four-terminal Kelvin), 0.1 mOhm, 9 W, ±1%. Component TCR including the copper terminals:
  - **±350 ppm/°C at 0.1 mOhm**
  - +150 at 0.2 mOhm
  - +170 at 0.3 and 0.4 mOhm
  - The alloy element alone is <20 ppm/°C.
  - WSLP5931 (15 x 7.75 mm) also offers 0.1 mOhm at +300 ppm/°C ([Vishay datasheet](https://wwwlegacy.vishay.com/docs/30176/wslp3921-wslp5931.pdf)).
- **Bourns CSS2H-2512:** the lowest alloy value in 2512 is 0.3 mOhm / 6 W / ±150 ppm/°C including copper terminals. There is also a "CSS2H-2512C-000 < 0.1 mΩ / 100 A" **copper jumper** in 2512 ([Bourns PDF](https://www.bourns.com/docs/product-datasheets/css2h-2512.pdf)).
- **OpenAIO's current part** (LCSC C695806, Yezhan ASR-S-3-0.2F): 0.2 mOhm, ±1%, 6 W, ±175 ppm/°C, 2512, about $0.20-0.33 ([LCSC](https://www.lcsc.com/product-detail/C695806.html)).
- **Littelfuse SSA 2512** covers 0.2-4 mOhm (search summary, [Littelfuse SSA2512L0M25F](https://www.littelfuse.com/products/capacitors-inductors-resistors/resistors/current-sensing-resistors/metal-type-current-shunt-resistors/ssa/ssa2512l0m25f); the page returned 403, so **UNCONFIRMED**).
- **No 0.1 mOhm or 0.05 mOhm part in 2512, 2010 or 1206 wide-terminal was found** (**UNCONFIRMED** that none exists). 0.1 mOhm in practice means 2x 0.2 mOhm 2512 in parallel, or a 3921 or 5931 body. 0.05 mOhm means 4x 0.2 or 2x 0.1.
- **Layout guidance** for shunt Kelvin connections: [TI Precision Labs "Shunt resistor layout"](https://www.ti.com/video/6076326896001) (video, content not transcribed).

---

## 3. Firmware: can stock firmware compensate copper TCR?

### 3.1 Betaflight (master, fetched 2026-10-07)
- The ADC current meter is purely linear. In `currentMeterADCToCentiamps()`, `centiAmps = (millivolts*10000/scale + offset)/10`, with "scale in (mV/10A) and b is offset in (mA)". There is no temperature term ([current.c](https://raw.githubusercontent.com/betaflight/betaflight/master/src/main/sensors/current.c)).
- CLI ranges: `ibata_scale` int16 from -16000 to 16000, `ibata_offset` int16 from -32000 to 32000 mA ([settings.c](https://raw.githubusercontent.com/betaflight/betaflight/master/src/main/cli/settings.c)).
- Other sources: `current_meter = VIRTUAL` (a throttle model) or `ESC` (summed ESC telemetry) ([current.c](https://raw.githubusercontent.com/betaflight/betaflight/master/src/main/sensors/current.c)). Betaflight's guide notes the sensor "has to be thoroughly calibrated" ([Betaflight docs](https://betaflight.com/docs/wiki/guides/current/Current-Sensor-Calibration)).
- **Per-board calibration with stock firmware is possible** by setting `ibata_scale` and `ibata_offset` in the CLI. **Temperature compensation is not possible** without a fork.

Quantisation and range limits (derived):

| Sense resistance | Scale (0.1 mV/A) | One-unit scale step | 12-bit ADC LSB at 3.3 V |
|---|---|---|---|
| 0.2 mOhm (20 mV/A) | 200 | 0.5% | about 40 mA |
| 0.1 mOhm (10 mV/A) | 100 | 1% | about 81 mA |
| 0.05 mOhm (5 mV/A) | 50 | 2% | about 161 mA |

- A mid-supply bidirectional Hall sensor needs an offset of about -125 A (ACS37220-100B3: 1.65 V / 13.2 mV/A) or -250 A (-200B5: 2.5 V / 10 mV/A). That is **outside the ±32 A `ibata_offset` range**, so only unidirectional-output Hall variants fit stock Betaflight (derived; whether unidirectional ACS37220 variants exist is **UNCONFIRMED**).

### 3.2 AM32 (main, fetched 2026-10-07)
- Per-ESC current is `actual_current = ((smoothed_raw_current*3300/41) - CURRENT_OFFSET*100) / MILLIVOLT_PER_AMP`.
- The constants are compile-time per target (defaults 20 mV/A and 0), and there is no temperature term ([main.c](https://raw.githubusercontent.com/am32-firmware/AM32/main/Src/main.c), [targets.h](https://raw.githubusercontent.com/am32-firmware/AM32/main/Inc/targets.h)).
- The MCU or NTC temperature is read, but it is only used for thermal derating.
- In OpenESC and OpenAIO style boards the shunt feeds the FC (`/CURR`), not the ESC MCUs ([OpenESC-20x20 AGENTS.md](https://raw.githubusercontent.com/incutec-hw/OpenESC_20X20/main/AGENTS.md)), so AM32 is not in this signal path.

### 3.3 Consequence
With firmware forks forbidden, copper TCR can only be handled in hardware: an NTC divider, or a compensating front-end IC such as the SLG47011 DAC route (**UNCONFIRMED**). Otherwise it is left uncorrected.

---

## 4. Alternatives in numbers

### 4.1 Hall-effect sensors (80-160 A class)

| Part | Range | Primary R | Loss at 100 A (derived) | Size | Accuracy | Supply | Price | Notes |
|---|---|---|---|---|---|---|---|---|
| Allegro ACS37220 | up to ±200 A | 0.1 mOhm | 1 W | 4x4 mm QFN | **UNCONFIRMED** (datasheet not fetched) | -100B3: 3.15-3.45 V, 13.2 mV/A; -200B5: 4.5-5.5 V, 10 mV/A | -100B3 $1.40 @ 7k ([DigiKey](https://www.digikey.com/en/products/detail/allegro-microsystems/ACS37220LEZATR-100B3/22490778)) | Pololu carrier ran 60 A continuous with no airflow ([Pololu](https://www.pololu.com/product/5299)); [Allegro](https://dev.allegromicro.com/en/products/sense/current-sensor-ics/integrated-current-sensors/acs37220) |
| Infineon TLI4971 | 25/50/75/120 A | 0.22 mOhm | 2.2 W | 8x8x1.1 mm TISON-8 | Error <2% (family press release) | - | $2.60 @ 2.5k, $4.58 @ 1 ([DigiKey](https://azcus.digikey.com/en/products/detail/infineon-technologies/TLI4971A120T5E0001XUMA1/11500489)) | [Infineon](https://infineon.com/cms/en/about-infineon/press/market-news/2022/INFATV202211-019.html) |
| TI TMCS1123 | 80 A RMS at 25 °C | 0.7 mOhm | 7 W, and over its rating | 10.3x10.3 mm SOIC-10 | <1.75% total over temperature and lifetime; <1.4% sensitivity error | - | - | Not suitable at 100 A ([TI](https://www.ti.com/product/TMCS1123); [Mouser](https://www.mouser.cl/ti-tmcs1123-hall-effect-sensors)) |
| Allegro ACS772 | 50-400 A | 0.1 mOhm | 1 W | Through-hole CB package (ACS770 CB is about 10x13x7 mm) | ±2.1% lifetime | - | - | Too large for a 25.5 mm AIO ([Mouser](https://www.mouser.se/allegro-acs772-sensor-ics)) |

### 4.2 Lower-value metal shunts
- 2x 0.2 mOhm 2512 (OpenESC-30x30, Tekko32 50A) or 2x 0.3 mOhm (five ESCs in 1.3) are the proven way down to 0.1-0.15 mOhm.
- WSLP3921 gives 0.1 mOhm in one 10x5.2 mm Kelvin body at ±350 ppm/°C (2.8).

---

## 5. Engineering checks for a copper Kelvin section on a 25.5 mm AIO (derived unless cited)

**Sheet resistance** (ρ20 = 1.72e-8 Ω·m, as used by Renesas, 2.2):

| Copper thickness | Sheet R | Squares for 0.2 mOhm | Example geometry |
|---|---|---|---|
| 35 µm (1 oz) | 0.49 mOhm/sq | 0.41 | 2 x 4.9 mm |
| 70 µm (2 oz) | 0.25 mOhm/sq | 0.81 | - |
| 17 µm (inner 0.5 oz, JLC default) | 1.0 mOhm/sq | 0.2 | 1 x 5 mm |

**Current density.** 100 A through a 5.7 mm x 30 µm single-layer neck is about 585 A/mm². TI needed a 44.5 mm wide outer trace for 50 A at ≤20 °C rise (2.1). A single-layer section that carries the full battery current is therefore thermally extreme on a 32 mm board. If all layers are paralleled instead, R drops (smaller signal) and each layer's thickness tolerance adds in.

**Same loss, harder heat path.** Loss is set by R and I, not by material: 0.2 mOhm gives 2 W at 100 A whether copper or alloy. Copper concentrates those 2 W in a 17-70 µm film, while an alloy shunt has a mm-thick element and copper terminals. Copper also self-heats, which shifts its own value at 0.39 %/K, the effect TI saw as minute-long settling (2.1).

**Kelvin tap placement.** An extra 0.5 mm of 5 mm wide 1 oz copper between the taps adds 0.049 mOhm, which is **+25% of 0.2 mOhm**. Tap geometry is as critical for a discrete 0.2 mOhm shunt as for a copper section. TI saw up to 6.4% difference between centre and edge taps (2.1).

**INA186 offset and drift** (±50 µV max, 0.5 µV/°C max, gain error ±1% max, gains 25/50/100/200/500 V/V; [TI INA186](https://www.ti.com/product/INA186)):

| Sense resistance | Offset error | Additional drift over 70 K |
|---|---|---|
| 0.2 mOhm | ±0.25 A | ±0.18 A |
| 0.1 mOhm | ±0.5 A | ±0.35 A |
| 0.05 mOhm | ±1 A | ±0.7 A |

Room-temperature offset can be trimmed with `ibata_offset`.

**Copper drift.** R(100 °C)/R(30 °C) = (1 + 0.00393·80)/(1 + 0.00393·10) = **1.265**. That is +26.5% reading error at 100 °C if calibrated at 30 °C.

---

## 6. Options compared (100 A, 30-100 °C)

| Option | Loss at 100 A | Initial accuracy (uncalibrated) | Drift 30→100 °C | Size | BOM delta vs today | Calibration needed |
|---|---|---|---|---|---|---|
| **A. Kelvin PCB copper section, 0.2 mOhm design** | 2.0 W at 30 °C, about 2.5 W at 100 °C | Outer plated copper: -31% to -58% measured (TI). Inner foil: about 0 to +35% (derived from IPC-4562 and processing). Same-lot spread about ±2% (Renesas) | **+26.5%** uncompensated. NTC-network or digital compensation residual about 1-4% (ams ±1%, Renesas ≤4.2%), only if the sensor tracks copper temperature | 0 parts, but needs about 1-2 mm x 5-6 mm single-layer neck, cut-outs in parallel layers, Kelvin taps, and NTC placement | Saves about $0.20-0.33 shunt; adds NTC and 2-3 resistors if compensating | **Mandatory per board** (scale; offset optional). Calibration does not transfer across fab lots or revisions (TI: +14% to +50%). Temperature compensation must be analog; stock Betaflight cannot do it |
| **B. 0.2 mOhm 2512 (current)** | 2.0 W (6 W part) | ±1% part + ±1% INA gain + ±0.25 A offset, plus copper-between-taps error (layout-dependent) | ±1.2% (±175 ppm/°C) + INA gain drift 10 ppm/°C | 6.3 x 3.2 mm | Baseline (about $0.20-0.33) | Optional (nominal `ibata_scale` 200); a one-time design calibration covers layout copper |
| **C. 0.1 mOhm metal strip (2x 0.2 mOhm 2512, or WSLP3921)** | 1.0 W | ±1% part, ±0.5 A offset; 10 mV/A with A3 (use INA186A4 for 20 mV/A) | ±1.2% (2x Yezhan) or ±2.5% (WSLP3921, ±350 ppm/°C) | 2x 2512 (about 6.4 x 6.4 mm) or 10 x 5.2 mm | +1 shunt (about $0.2-0.3), or a costlier Vishay part (price **UNCONFIRMED**) | As B |
| **D. Hall sensor (ACS37220 or TLI4971)** | 1.0 W (ACS37220) / 2.2 W (TLI4971) | TLI4971 <2%; ACS37220 **UNCONFIRMED**; TMCS1123 class <1.75% (not usable at 100 A) | Included in the totals above (factory compensated) | 4x4 mm QFN / 8x8 mm | -INA186 -shunt +$1.4-4.6 sensor | Offset: bidirectional variants cannot be zeroed within Betaflight's ±32 A `ibata_offset` (derived); needs unidirectional output or level-shift; 3.3 V variant (-100B3) needed or a 5 V rail; stray-field and pad-layout sensitive |

---

## 7. Recommendation and main risk

**Recommendation: do not replace the discrete shunt with a copper Kelvin section.** Keep a metal-alloy shunt and spend the effort on the Kelvin layout:
- Put the taps at the inner pad edges, with no plane copper between them.
- If dissipation or headroom matters, move to 0.1 mOhm as 2x 0.2 mOhm 2512 in parallel, which is proven in OpenESC-30x30 and Holybro Tekko32 50A.
- Optionally pair it with INA186A4 (200 V/V) to keep 20 mV/A.

**Evidence:**
- 0 of 40 resolvable commercial and open designs use copper sensing.
- TI's own note concludes copper shunts are "not designed for any application that requires a high degree of accuracy".
- Stock Betaflight and AM32 cannot apply a temperature term.

**Main risk of the copper option (why not):**
- Drift that stock firmware cannot correct: about +26% between 30 and 100 °C, a range an AIO crosses in every flight.
- Fab-lot copper thickness variation of tens of percent (IPC sets a minimum only). This forces per-board calibration that does not carry across PCB orders.
- The 0.2 mOhm neck must carry 100 A in a single copper film. That fights both the thermal budget and the measurement, through self-heating.

**Main risk of the recommended option:** Kelvin-tap layout. Copper left between the taps adds positive-TCR error, for example 0.5 mm of 1 oz is about 25% of 0.2 mOhm (derived). Verify with one bench calibration at known current and two board temperatures. At 0.1 mOhm, INA186 offset of about ±0.5 A matters at hover currents; trim it with `ibata_offset`.

**If the owner still wants to try copper:**
- Prototype it alongside a populated shunt footprint (or a DNP jumper) on the same board.
- Use an **inner foil layer**, not a plated outer layer.
- Put an NTC divider at the INA186 output, thermally bonded to the neck.
- Expect per-board `ibata_scale` calibration.
- Compare both readings across 30-100 °C before committing.

---

## 8. Sources (all fetched 2026-10-07)

**Copper sensing and compensation:**
- TI SBOA533A: https://ti.com/lit/pdf/sboa533
- Renesas AN-CM-394: https://www.renesas.com/en/document/apn/cm-394-current-sensing-cu-trace
- ams AS8510 (Electronic Design): https://www.electronicdesign.com/technologies/power/article/21799690/battery-board-measures-current-without-shunt-resistor
- ams AN000545: https://www.mouser.com/datasheet/2/588/AS8510_AN000545_1_00-1513137.pdf (503, not read)
- EDN (Steele, Microchip): https://www.edn.com/current-sensing-pcb-traces-vs-shunt-resistors/
- US7683604 (TI): https://patents.google.com/patent/US7683604
- US11002772 (Qorvo): https://patents.google.com/patent/US11002772
- Richtek AN026: https://www.richtek.com/~/media/AN%20PDF/AN026_EN.pdf
- MAX17260: https://www.analog.com/en/products/max17260.html (snippet only)

**PCB copper tolerances:**
- NCAB: https://www.ncabgroup.com/faq/how-much-finished-copper-can-be-expected/
- Eurocircuits: https://www.eurocircuits.com/tolerances-on-copper-thickness/
- Siemens: https://blogs.sw.siemens.com/electronic-systems-design/2025/08/13/copper-thickness/
- JLCPCB: https://jlcpcb.com/capabilities/pcb-capabilities

**Shunts:**
- Vishay WSLP3921/5931: https://wwwlegacy.vishay.com/docs/30176/wslp3921-wslp5931.pdf
- Bourns CSS2H-2512: https://www.bourns.com/docs/product-datasheets/css2h-2512.pdf
- LCSC C695806: https://www.lcsc.com/product-detail/C695806.html
- CTS 73M: https://www.mouser.com/datasheet/2/96/73M1A-73M2A-73M3x-73M5-1662200.pdf

**Amplifier and Hall sensors:**
- INA186: https://www.ti.com/product/INA186
- TMCS1123: https://www.ti.com/product/TMCS1123
- TLI4971: https://infineon.com/cms/en/about-infineon/press/market-news/2022/INFATV202211-019.html and https://azcus.digikey.com/en/products/detail/infineon-technologies/TLI4971A120T5E0001XUMA1/11500489
- ACS37220: https://www.pololu.com/product/5299, https://www.digikey.com/en/products/detail/allegro-microsystems/ACS37220LEZATR-100B3/22490778, https://dev.allegromicro.com/en/products/sense/current-sensor-ics/integrated-current-sensors/acs37220
- ACS772: https://www.mouser.se/allegro-acs772-sensor-ics

**Firmware:**
- Betaflight current.c: https://raw.githubusercontent.com/betaflight/betaflight/master/src/main/sensors/current.c
- Betaflight settings.c: https://raw.githubusercontent.com/betaflight/betaflight/master/src/main/cli/settings.c
- Betaflight board configs: https://github.com/betaflight/config
- AM32 main.c: https://raw.githubusercontent.com/am32-firmware/AM32/main/Src/main.c
- AM32 targets.h: https://raw.githubusercontent.com/am32-firmware/AM32/main/Inc/targets.h

**Open-source designs and market:**
- Open designs: URLs in table 1.4.
- Product pages: URLs in tables 1.2 and 1.3.
- Holybro scale table: https://docs.holybro.com/esc/current-sensor-scale
