"""RP2354A IO optimiser: assign every FC signal to a GPIO, minimising total wire length (U2 pad to its endpoint).

    python3 hardware/tools/io_opt.py u2.json [rework=1]

u2.json: U2 pad positions and nets from the board (see research/IO-CONSTRAINTS.md for the mux rules used).
Exhaustive over peripheral-instance choices (SPI/I2C instance, which serial device is the PIO UART, OSD base),
Hungarian (scipy linear_sum_assignment) for the pin choice inside each. Cost = Euclidean distance from the U2 pad
to the nearest pad of the signal's first-hop part, plus rework x mm of track already on the old pin.
Fixed: OSD W/EN/SYNC consecutive, SBUS/GPS port on a hardware UART (8E2), the VTX pair stays on GPIO0/1.
"""
import itertools, json, math, sys
import numpy as np
from scipy.optimize import linear_sum_assignment

U2 = json.load(open(sys.argv[1]))
GPIO_PIN = [2, 3, 4, 5, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 40, 41, 42, 43]
POS = {g: tuple(U2[str(p)]["pos"]) for g, p in enumerate(GPIO_PIN)}
CUR = {g: U2[str(p)]["net"] for g, p in enumerate(GPIO_PIN)}


def spi(g):   return (0 if (g // 8) % 2 == 0 else 1), ["RX", "CSn", "SCK", "TX"][g % 4]
def uart(g):  return [0, 1, 1, 0, 0, 1, 1, 0][g // 4], ["TX", "RX", "CTS", "RTS"][g % 4]
def i2c(g):   return (g // 2) % 2, ("SDA" if g % 2 == 0 else "SCL")


def uart_ok(g, inst, role):           # hardware UART incl. UART_AUX (F11): CTS pin = TX, RTS pin = RX
    i, r = uart(g)
    return i == inst and (r == role or (role == "TX" and r == "CTS") or (role == "RX" and r == "RTS"))


# signal: (endpoints [(x, y, side)], extra mm penalty if endpoint on bottom) ; endpoints = first-hop pads
EP = {
    "IMU_SCK": [(82.44, 60.59)], "IMU_MOSI": [(81.94, 60.59)], "IMU_MISO": [(81.27, 60.76)],
    "IMU_CS": [(82.94, 60.59), (78.12, 59.30)], "GYRO_INT": [(81.27, 62.26)],
    "SD_SCK": [(65.56, 66.62)], "SD_MOSI": [(65.56, 64.41)], "SD_MISO": [(65.56, 68.81)],
    "SD_CS": [(65.56, 63.32), (64.72, 62.21)],
    "I2C_SDA": [(82.86, 68.44), (77.67, 53.26), (82.01, 67.38)],
    "I2C_SCL": [(80.84, 68.44), (75.70, 53.26), (81.48, 66.60)],
    "ELRS_TX": [(82.30, 70.87)], "ELRS_RX": [(82.30, 71.37)],          # FC TX -> ESP U0RXD ; FC RX <- U0TXD
    "VTX_TX": [(79.94, 72.71), (85.06, 70.17)], "VTX_RX": [(80.94, 72.71), (87.06, 70.17)],
    "GPS_TX": [(86.77, 67.72)], "GPS_RX": [(86.74, 65.72)],
    "VBAT": [(71.79, 66.69)], "CURR": [(71.81, 65.18)],
    "ESC_R39": [(66.47, 63.87)], "ESC_R58": [(72.40, 61.20)], "ESC_R77": [(78.54, 60.56)], "ESC_R96": [(84.39, 57.93)],
    "LED_STRIP": [(78.67, 68.56)], "OSD_W": [(79.78, 59.96)], "OSD_EN": [(80.72, 58.48)], "OSD_SYNC": [(78.84, 57.38)],
    "BEEPER": [(72.00, 62.38)], "LED0": [(71.77, 68.54)],
}
NETNAME = {"IMU_SCK": "/IMU/SPI1.SCK", "IMU_MOSI": "/IMU/SPI1.MOSI", "IMU_MISO": "/IMU/SPI1.MISO", "IMU_CS": "/IMU/CS",
           "GYRO_INT": "/IMU/GYRO_INT", "SD_SCK": "SPI0.SCK", "SD_MOSI": "SPI0.MOSI", "SD_MISO": "SPI0.MISO",
           "SD_CS": "FLASH_CS", "I2C_SDA": "/Pads/I2C0.SDA", "I2C_SCL": "/Pads/I2C0.SCL", "ELRS_TX": "UART1_TX",
           "ELRS_RX": "UART1_RX", "VTX_TX": "UART0_TX", "VTX_RX": "UART0_RX", "GPS_TX": "/Pads/PIOUART0_TX",
           "GPS_RX": "/Pads/PU0RX", "VBAT": "/RP2354A/ADC_VBAT", "CURR": "/RP2354A/ESC_CURR", "ESC_R39": "MOTOR1",
           "ESC_R58": "MOTOR2", "ESC_R77": "MOTOR3", "ESC_R96": "MOTOR4", "LED_STRIP": "/RP2354A/LED_STRIP_L",
           "OSD_W": "/OSD/OSD_W", "OSD_EN": "/OSD/OSD_EN", "OSD_SYNC": "/OSD/OSD_SYNC", "BEEPER": "/RP2354A/BEEPER",
           "LED0": "/RP2354A/LED0"}
SIGS = list(EP)
_inv = {v: k for k, v in NETNAME.items()}
CURPIN = {_inv[n]: g for g, n in CUR.items() if n in _inv}


ROUTED = {"ELRS_TX": 14.4, "ELRS_RX": 26.3, "I2C_SDA": 12.7, "BEEPER": 14.9, "SD_MISO": 12.2, "ESC_R39": 7.8,
          "IMU_CS": 7.2, "IMU_SCK": 5.1, "IMU_MOSI": 2.5, "IMU_MISO": 2.6, "SD_MOSI": 2.1, "OSD_W": 1.6,
          "GYRO_INT": 1.4, "VBAT": 2.2, "CURR": 1.7}       # mm of track already on the current U2 pin
REWORK = float(dict(a.split("=") for a in sys.argv[2:]).get("rework", "1"))   # weight of discarded routing


def cost(g, s):
    c = dist(g, s)
    if CURPIN.get(s) is not None and g != CURPIN[s]:
        c += REWORK * ROUTED.get(s, 0.0)
    return c


def dist(g, s):
    x, y = POS[g]
    return min(math.hypot(x - a, y - b) for a, b in EP[s])


OSD_RULE = None   # filled in from the firmware research: e.g. lambda a: a["OSD_EN"] == a["OSD_W"] + 1


FIXED = {"VTX_TX": 0, "VTX_RX": 1}   # keep the SH-6 pair together (Euclidean cost ignores crossings)


def allowed(s, g, ch):
    if s in FIXED:
        return g == FIXED[s] and (not s.startswith("VTX") or ch["uart"].get("VTX") is None
                                  or uart_ok(g, ch["uart"]["VTX"], s[-2:]))
    if s.startswith("IMU_") and s != "IMU_CS":
        inst, role = spi(g)
        return inst == ch["imu_spi"] and role == {"IMU_SCK": "SCK", "IMU_MOSI": "TX", "IMU_MISO": "RX"}[s]
    if s.startswith("SD_") and s != "SD_CS":
        inst, role = spi(g)
        return inst == 1 - ch["imu_spi"] and role == {"SD_SCK": "SCK", "SD_MOSI": "TX", "SD_MISO": "RX"}[s]
    if s.startswith("I2C_"):
        inst, role = i2c(g)
        return inst == ch["i2c"] and role == s[4:]
    if s in ("VBAT", "CURR"):
        return g >= 26
    for dev in ("ELRS", "VTX", "GPS"):
        if s.startswith(dev + "_"):
            hw = ch["uart"].get(dev)
            return True if hw is None else uart_ok(g, hw, s[-2:])
    if s in FIXED:
        return g == FIXED[s]
    return True     # PIO / GPIO: any pin


def solve(ch):
    C = np.full((len(SIGS), 30), 1e6)
    osd = {"OSD_W": ch["osd"], "OSD_EN": ch["osd"] + 1, "OSD_SYNC": ch["osd"] + 2}   # osd_pico.c:138-153
    for i, s in enumerate(SIGS):
        for g in range(30):
            if s in osd:
                if g == osd[s]:
                    C[i, g] = cost(g, s)
                continue
            if allowed(s, g, ch):
                C[i, g] = cost(g, s)
    r, c = linear_sum_assignment(C)
    tot = C[r, c].sum()
    return tot, {SIGS[i]: int(g) for i, g in zip(r, c)}


best = None
for imu_spi, i2c_i, pio_dev, hw0, osd in itertools.product((0, 1), (0, 1), ("ELRS", "VTX"), (0, 1), range(28)):
    devs = [d for d in ("ELRS", "VTX", "GPS") if d != pio_dev]
    ch = {"imu_spi": imu_spi, "i2c": i2c_i, "uart": {devs[0]: hw0, devs[1]: 1 - hw0, pio_dev: None}, "osd": osd}
    tot, a = solve(ch)
    if tot >= 1e6:
        continue
    if OSD_RULE and not OSD_RULE(a):
        continue
    if best is None or tot < best[0]:
        best = (tot, a, ch)

cur_tot = 0
inv = {v: k for k, v in NETNAME.items()}
cur = {}
for g, n in CUR.items():
    if n in inv:
        cur[inv[n]] = g
for s, g in cur.items():
    cur_tot += dist(g, s)
wl = sum(dist(g, s) for s, g in best[1].items())
print(f"current wire {cur_tot:.1f} mm  ->  {wl:.1f} mm (objective {best[0]:.1f}, rework weight {REWORK})  choice {best[2]}")
for s in SIGS:
    g = best[1][s]
    print(f"{s:10s} GPIO{cur.get(s, '-'):>3} -> GPIO{g:<3} pin {GPIO_PIN[g]:>2}  {dist(cur[s], s) if s in cur else 0:5.1f} -> {dist(g, s):5.1f} mm")
json.dump({"assign": best[1], "choice": best[2], "netname": NETNAME, "gpio_pin": GPIO_PIN},
          open(sys.argv[1].replace("u2.json", "assign.json"), "w"), indent=1)
