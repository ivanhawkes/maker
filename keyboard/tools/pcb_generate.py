#!/usr/bin/env python3
"""Generate the left and right keyboard PCBs (placement and nets, no routing yet).

    python tools/pcb_generate.py            # writes pcb/left/left.kicad_pcb, pcb/right/right.kicad_pcb

Needs KiCad 10's `pcbnew` Python module (the devenv shell's KiCad, or PYTHONPATH set to
kicad-base's site-packages) and PyYAML. Inputs:
    layout/generated/{left,right}-hand.csv   switch centres and rotations (from layout.yaml)
    pcb/pins.yaml                            controller pin assignment (shared with firmware)
    pcb/lib/marbastlib/...                   pinned third-party footprints
    $KICAD10_FOOTPRINT_DIR                   KiCad stock footprints

Stage: v0 placement. Placeholder (clearly labelled on the board):
    - LED supply net VLED ends at test pad TP_VLED: supply design is open.

Battery path: JST-PH -> power switch -> nice!nano RAW pin. The official nice!nano v2
pinout labels RAW "BATTERY+" (as well as the extra B+ pad, which is not socketed).
A copper keep-out covers the whole controller footprint on both layers, because the
antenna position on the module has not been verified.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from pathlib import Path

import pcbnew
import yaml

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "layout" / "generated"
PINS = ROOT / "pcb" / "pins.yaml"
MARB = ROOT / "pcb" / "lib" / "marbastlib"
STOCK = Path(os.environ.get("KICAD10_FOOTPRINT_DIR", ""))

ORIGIN = (150.0, 100.0)  # KiCad page position (mm) of layout (0, 0)

# Part positions in key-local plan coordinates (mm; x right, y away from the user),
# rotated with the key. Chosen to clear the hot-swap socket pads, which sit north of the
# stem on the bottom side, and the MX LED window, which is south of the stem.
DIODE_OFFSET = (7.0, -4.0)
LED_OFFSET = (0.0, -5.08)

# Controller and edge parts in half-local plan coordinates for the LEFT half; the right
# half mirrors x. Provisional, for review.
CONTROLLER_AT = (52.0, 20.0)
JST_AT = (52.0, -6.0)
POWER_SWITCH_AT = (64.0, 30.0)
RESET_AT = (64.0, 12.0)
VLED_PAD_AT = (59.0, -1.0)
CONTROLLER_KEEPOUT = (9.5, 17.5)  # half-width, half-height (mm) around the controller centre


def mm(v: float) -> int:
    return pcbnew.FromMM(v)


def to_board(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(ORIGIN[0] + x), mm(ORIGIN[1] - y))


def rot(dx: float, dy: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def load(lib: Path, name: str) -> pcbnew.FOOTPRINT:
    fp = pcbnew.FootprintLoad(str(lib), name)
    if fp is None:
        raise SystemExit(f"footprint not found: {lib}:{name}")
    return fp


class Board:
    def __init__(self):
        self.b = pcbnew.BOARD()
        self.nets: dict[str, pcbnew.NETINFO_ITEM] = {}

    def net(self, name: str) -> pcbnew.NETINFO_ITEM:
        if name not in self.nets:
            n = pcbnew.NETINFO_ITEM(self.b, name)
            self.b.Add(n)
            self.nets[name] = n
        return self.nets[name]

    def place(self, fp, ref: str, x: float, y: float, plan_rot: float, bottom: bool, value: str = ""):
        self.b.Add(fp)
        fp.SetReference(ref)
        if value:
            fp.SetValue(value)
        fp.SetPosition(to_board(x, y))
        if bottom:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetOrientationDegrees(180.0 + plan_rot)  # verified in check_switch_pins()
        else:
            fp.SetOrientationDegrees(plan_rot)
        return fp

    def connect(self, fp, pad_number: str, net: str):
        hit = False
        for p in fp.Pads():
            if p.GetNumber() == pad_number:
                p.SetNet(self.net(net))
                hit = True
        if not hit:
            raise SystemExit(f"{fp.GetReference()}: no pad {pad_number!r}")


def read_keys(side: str) -> list[dict]:
    with (LAYOUT / f"{side}-hand.csv").open() as f:
        return list(csv.DictReader(f))


def check_switch_pins(fp, x: float, y: float, r: float):
    """MX pin 1 must be at plan-local (-3.81, +2.54) and pin 2 at (+2.54, +5.08)."""
    want = {"1": (-3.81, 2.54), "2": (2.54, 5.08)}
    for p in fp.Pads():
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_PTH or p.GetNumber() not in want:
            continue
        px = pcbnew.ToMM(p.GetPosition().x) - ORIGIN[0] - x
        py = -(pcbnew.ToMM(p.GetPosition().y) - ORIGIN[1]) - y
        ex, ey = rot(*want[p.GetNumber()], r)
        if math.hypot(px - ex, py - ey) > 1e-3:
            raise SystemExit(f"{fp.GetReference()}: pin {p.GetNumber()} at ({px:.3f},{py:.3f}), expected ({ex:.3f},{ey:.3f})")


def outline_points(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convex hull (monotone chain)."""
    pts = sorted(set(pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def build(side: str) -> Board:
    pins = yaml.safe_load(PINS.read_text())
    sx = 1.0 if side == "left" else -1.0  # mirror for half-local extra parts
    B = Board()
    keys = read_keys(side)
    pad_net = {}  # controller pad -> net name
    for row, pad in pins["rows"].items():
        pad_net[pad] = f"ROW_{row}"
    for col, pad in pins["columns"].items():
        pad_net[pad] = f"COL_{col}"
    pad_net[pins["led_data"]] = "LED_DIN"
    for pad in pins["power"]["gnd"]:
        pad_net[pad] = "GND"
    pad_net[pins["power"]["rst"]] = "RST"
    pad_net[pins["power"]["vcc"]] = "VCC_3V3_SW"
    pad_net[pins["power"]["raw"]] = "RAW"

    # Switches, diodes and LEDs.
    led_order = []
    for i, k in enumerate(keys, start=1):
        x, y, r = float(k["x_mm"]), float(k["y_mm"]), float(k["rotation_deg"])
        kid = k["id"]
        sw = B.place(load(MARB / "marbastlib-mx.pretty", "SW_MX_HS_CPG151101S11_1u"), f"SW{i}", x, y, r, True, kid)
        check_switch_pins(sw, x, y, r)
        if k["group"] == "T":
            col, row = "T", pins["thumb_rows"][kid]
        else:
            col, row = k["group"], k["row"]
        B.connect(sw, "2", f"COL_{col}")
        B.connect(sw, "1", f"K_{kid}")
        dx, dy = rot(*DIODE_OFFSET, r)
        d = B.place(load(STOCK / "Diode_SMD.pretty", "D_SOD-123"), f"D{i}", x + dx, y + dy, r + 90.0, True, "1N4148W")
        B.connect(d, "1", f"ROW_{row}")  # cathode to row (col2row)
        B.connect(d, "2", f"K_{kid}")
        lx, ly = rot(*LED_OFFSET, r)
        led = B.place(load(STOCK / "LED_SMD.pretty", "LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount"),
                      f"LED{i}", x + lx, y + ly, r, True, "SK6812MINI-E (optional)")
        led_order.append((col, row, kid, led))

    # LED chain: serpentine down/up the finger columns, then the thumb keys.
    col_order = ["C0", "C1", "C2", "C3", "C4", "C5", "T"]
    chain = []
    for ci, col in enumerate(col_order):
        items = [t for t in led_order if t[0] == col]
        items.sort(key=lambda t: t[1], reverse=(ci % 2 == 1))
        chain.extend(items)
    prev = "LED_DIN"
    for n, (_, _, kid, led) in enumerate(chain):
        B.connect(led, "4", prev)               # DIN
        nxt = f"LED_D{n + 1}" if n + 1 < len(chain) else "LED_DOUT_END"
        B.connect(led, "2", nxt)                # DOUT
        B.connect(led, "1", "VLED")             # VDD
        B.connect(led, "3", "GND")              # VSS
        prev = nxt

    # Controller (top side, USB towards the far edge).
    cx, cy = CONTROLLER_AT[0] * sx, CONTROLLER_AT[1]
    u = B.place(load(MARB / "marbastlib-xp-promicroish.pretty", "ProMicro_Reversible_Single"), "U1", cx, cy, 0.0, False,
                "nice!nano v2 (socketed)")
    for pad, net in pad_net.items():
        B.connect(u, str(pad), net)

    # Battery connector, power switch, reset, and placeholder pads.
    j = B.place(load(STOCK / "Connector_JST.pretty", "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal"), "J1",
                JST_AT[0] * sx, JST_AT[1], 0.0, False, "JST-PH battery (check polarity)")
    B.connect(j, "1", "BAT_IN")
    B.connect(j, "2", "GND")
    s = B.place(load(STOCK / "Button_Switch_SMD.pretty", "SW_SPDT_PCM12"), "SW_PWR",
                POWER_SWITCH_AT[0] * sx, POWER_SWITCH_AT[1], -90.0 * sx, False, "Power")
    B.connect(s, "2", "BAT_IN")
    B.connect(s, "1", "RAW")  # RAW is BATTERY+ on the nice!nano v2
    rst = B.place(load(STOCK / "Button_Switch_SMD.pretty", "SW_SPST_TL3342"), "SW_RST",
                  RESET_AT[0] * sx, RESET_AT[1], -90.0 * sx, False, "Reset")
    B.connect(rst, "1", "RST")
    B.connect(rst, "2", "GND")
    tp = B.place(load(STOCK / "TestPoint.pretty", "TestPoint_Pad_D1.5mm"), "TP_VLED",
                 VLED_PAD_AT[0] * sx, VLED_PAD_AT[1], 0.0, False, "placeholder: LED supply open")
    B.connect(tp, "1", "VLED")

    # Copper keep-out under the whole controller (antenna position unverified).
    hw, hh = CONTROLLER_KEEPOUT
    zone = pcbnew.ZONE(B.b)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(ls)
    poly = zone.Outline()
    poly.NewOutline()
    for ox, oy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        poly.Append(to_board(cx + ox, cy + oy))
    zone.SetZoneName("controller-keepout")
    B.b.Add(zone)

    # Provisional outline: convex hull of key cells, the controller and edge parts.
    pts = []
    for k in keys:
        x, y, r = float(k["x_mm"]), float(k["y_mm"]), float(k["rotation_deg"])
        for cxo, cyo in ((-9.525, -9.525), (9.525, -9.525), (9.525, 9.525), (-9.525, 9.525)):
            dx, dy = rot(cxo, cyo, r)
            pts.append((x + dx, y + dy))
    for (px, py), (hw, hh) in ((CONTROLLER_AT, (10.0, 18.5)), (POWER_SWITCH_AT, (3.5, 5.0)), (RESET_AT, (3.5, 5.0)),
                               (JST_AT, (5.0, 5.0))):
        for ox, oy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            pts.append(((px + ox) * sx, py + oy))
    hull = outline_points([(round(a, 4), round(b, 4)) for a, b in pts])
    for a, b in zip(hull, hull[1:] + hull[:1]):
        seg = pcbnew.PCB_SHAPE(B.b)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(to_board(*a))
        seg.SetEnd(to_board(*b))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        B.b.Add(seg)

    note = pcbnew.PCB_TEXT(B.b)
    note.SetText(f"{side.upper()} v0 placement - NOT ROUTED - NOT FOR FAB")
    note.SetPosition(to_board(0.0, 70.0))
    note.SetLayer(pcbnew.Cmts_User)
    B.b.Add(note)
    return B


def main() -> int:
    if not STOCK.is_dir():
        raise SystemExit("set KICAD10_FOOTPRINT_DIR to KiCad's stock footprint directory")
    for side in ("left", "right"):
        B = build(side)
        out = ROOT / "pcb" / side / f"{side}.kicad_pcb"
        out.parent.mkdir(parents=True, exist_ok=True)
        pcbnew.SaveBoard(str(out), B.b)
        fps = len(B.b.GetFootprints())
        print(f"wrote {out.relative_to(ROOT)}: {fps} footprints, {len(B.nets)} nets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
