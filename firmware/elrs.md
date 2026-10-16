# ELRS on OpenAIO (ESP32-C3 + SX1281)

Sources:
- ExpressLRS/targets `42ed776a`
- ExpressLRS/ExpressLRS `15c78990`
- OpenAIO netlist, 2026-10-16

Pin-by-pin evidence is in [PINOUT.md](PINOUT.md), section "ELRS receiver".

## Target

| Field | Value | Source |
|---|---|---|
| Vendor / type / key | `generic` / `rx_2400` / `c3-plain` | `targets.json:1538-1546` |
| Product name (Configurator) | **Generic ESP32C3 2.4Ghz RX** (Lua name "C3 2400RX") | same |
| Hardware layout | `RX/Generic C3 2400.json` | same |
| Firmware | `Unified_ESP32C3_2400_RX`, min version 3.5.0 | same |
| Upload methods | `uart`, `wifi`, `betaflight` | same |

## Pin overrides

**None are needed.** The wiring matches `RX/Generic C3 2400.json:2-20` on every pin it defines:
- `serial_rx` 20, `serial_tx` 21
- `radio_busy` 3, `radio_dio1` 1, `radio_rst` 2
- `radio_miso` 5, `radio_mosi` 4, `radio_sck` 6, `radio_nss` 7
- `led_rgb` 8 (GRB: XL-1010RGBC-WS2812B.pdf p7 "GRB"), `button` 9

The JSON defines no PA, LNA or antenna switch, and the board has none. The SX1281 feeds FL1 and the u.FL JP1 directly, so `power_values: [13]` is correct.

**Optional: enable the SX1281 DC-DC.**
- The board fits the DC-DC inductor: L4 15 uH from DCC_SW (U21.14) to DCC_FB (U21.12).
- VDD_IN (U21.2) is tied to DCC_FB, as SX1281.pdf p17 requires.
- `Generic C3 2400.json` leaves `radio_dcdc` unset, so the radio runs on its LDO. That works with the inductor fitted.
- To cut radio supply current, add the overlay below. `radio_dcdc` is a hardware-layout boolean (`src/lib/OPTIONS/hardware.cpp:39`). It makes the driver send `SetRegulatorMode(USE_DCDC)` (`src/lib/SX1280Driver/SX1280.cpp:128-131`).
- Two ways to apply it:
  - the hardware-layout page of the ELRS web UI in WiFi mode;
  - a custom layout file when flashing.

```json
{ "radio_dcdc": true }
```

Not verified on hardware. Without the overlay, the board runs exactly as the stock target.

## Betaflight side

- **Port:** UART1, on GPIO6/7 through the F11 UART_AUX function. It is set as the serial RX by default:
  - `SERIALRX_UART SERIAL_PORT_UART1`
  - `SERIALRX_PROVIDER SERIALRX_CRSF`
  - `DEFAULT_RX_FEATURE FEATURE_RX_SERIAL`
- **Telemetry:** CRSF telemetry runs on the same port (`FEATURE_TELEMETRY` is on by default).
- **Test pads:** J54 "TX1" and J55 "RX1" sit on this link. They are not a spare UART (ISSUES I9).
- **ELRS enable:** GPIO27 (`ELRS_EN`, PINIO1 in `config.h`) drives the ESP32-C3 CHIP_EN through R115. Solder jumper JP2
  (normally open) pulls CHIP_EN to GND and holds ELRS off (ISSUES I5, I10).

## Flashing paths

The ESP32-C3 straps are correct for both boot modes (ESP32-C3FH4.pdf §3, p25-26):
- GPIO2 is pulled up by R111.
- GPIO8 is pulled up by R112.
- GPIO9 is pulled up by R113 and can be pulled low through TP9.
- CHIP_EN has R114 10k to +3.3V, C84 1 uF and R115 1k from `ELRS_EN` (GPIO27): the FC can reset the C3 but cannot pull GPIO9 low (ISSUES I5).

**Power:** the RX runs on +3.3V from U7, which is fed by +4v5. USB power alone is enough for every path below.

### 1. Normal update (ELRS already running)

1. **ExpressLRS Configurator.** Pick the target "Generic ESP32C3 2.4Ghz RX" and the method **Betaflight Passthrough**. Connect the FC over USB; the FC must be running Betaflight with UART1 as the serial RX.
2. **WiFi.** The RX starts its access point after about 60 s without a link (or on request from the Lua script). Upload through the web UI. The ESP32-C3 has its own antenna for this: AE2 chip antenna on LNA_IN via L7.

### 2. First flash of a blank C3, or recovery

The ESP32-C3FH4 arrives blank. Passthrough cannot tell blank ELRS firmware to reboot into its bootloader, so the ROM download mode must be forced by hand:
1. Short TP9 "BOOT" (B.Cu) to GND.
2. Apply power, or reset the C3 (JP2 briefly closed), then remove the short. The reset samples GPIO9 low and the C3 enters UART download mode on U0TXD/U0RXD.
3. Flash, using either route:
   - **(a) External 3.3 V USB-UART adapter on the pads.** Adapter TX goes to J54 "TX1" (net `UART1_TX`, ESP32 U0RXD). Adapter RX goes to J55 "RX1" (net `UART1_RX`, ESP32 U0TXD). Hold the RP2354A in BOOTSEL (U1 pressed at plug-in) so that it does not drive GPIO6. Then use the Configurator method "UART", or esptool.
   - **(b) Betaflight passthrough with the C3 already in ROM download mode.** Expected to work, because esptool only needs the ROM loader on the far side of the passthrough. **Not verified.**
4. Power-cycle without the short.

## Known board limits that touch ELRS

- **I5:** no FC control of GPIO9. Recovering a bricked RX needs TP9 and a reset.
- **I10:** SH-6 pin 6 (SBUS from an air unit) is on the same net as the ESP32 TX; hold ELRS off to use it.
- **I11:** the D9 status LED runs on +3.3V, below its 3.5 V VDD minimum. The LED may be dim, show wrong colours, or stay dark. The radio link is not affected.
- **I12:** ESP32-C3 GPIO10 is tied to GND. No ELRS layout for this target uses GPIO10.
