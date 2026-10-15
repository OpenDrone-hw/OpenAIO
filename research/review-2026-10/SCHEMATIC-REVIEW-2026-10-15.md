# Schematic review, 2026-10-15

Five parallel read-only reviews (MCU, FC peripherals, power, ESC, RX + pads) of every sheet
against the netlist and datasheets, before the one-board merge. Raw findings:
`schematic-review-2026-10-15.json`. Verdict: every sheet is electrically complete; no blocker.

## Applied

| Change | Sheet | Netlist effect |
|---|---|---|
| J90/J91 and `core_interface` deleted | root | 46 LGA nets keep every other node |
| DPS368 baro U28 + C114/C115 on I2C0 (0x76, SDO to GND, CSB to VDDIO), `+3.3V` | fc_pads | new part |
| C116 100 nF 50 V at U3 VIN (LMR51430 9.2.2.6) | fc_power | new part |
| C117/C118 100 nF at RP2354 pins 44/53/54 (RP2350 6.1.4, 6.1.5, 14.3) | fc_rp2350a | new parts |
| D10 SDM02U30LP3 flyback, BUZZER- to +5V (Q1 AP1606 is 20 V) | fc_pads | new part |
| microSD Card1 VDD, R34, C36 from `+3V3` (radio LDO) to `+3.3V` (FC LDO, same rail as the SPI host) | fc_blackbox | 3 pins move |
| D9 WS2812 VDD from `+3V3` to `+4v5` (3.5 V minimum) | rx | 1 pin moves |
| `FLASH_CS` renamed `SD_CS` (there is no flash chip) | root, fc_rp2350a, fc_blackbox | rename |
| ESC cap symbol pins input to passive (16 ERC errors) | esc_channel | none |
| U7 LP5912 pin names fixed (3 = PG, 5 = GND per datasheet; both pads on GND) | fc_power | none |
| PWR_FLAGs on `+BATT`, `/CSA+`, `+1.1V`, `+5V_USB`, `+5V`, `+4v5`, `+10V`, `+1.8V_GYRO`, `GND`, U22 VDD3P3 | several | none |
| Dangling `CURR` sheet pin, TP10 and its stub removed; bus stubs drawn as bus | root, fc_rp2350a | none |
| L4 LCSC C383402 (TDK MLZ2012M150WT000); DOY180N03T description; D4-D7 MPN trailing space | rx, esc, power | metadata |
| Every footprint and symbol in the project library; `OPENDRONE_LIB` removed from the lib tables | all | none |

ERC after: 0 errors (32 before). Netlist diff against 8fa8d7b: only the rows above.

## Open

Owner decisions are listed in `research/ROUTING.md`. Minor items not applied: SD DAT1/DAT2
pull-ups, PU0RX 8.2k pull-down (RP2350 A2 erratum E9), 0402 regulator caps' DC bias,
+10V output capacitance 1.7 uF short (FINISH_PASS), Rsense2 manufacturer field, OSC1 datasheet.
