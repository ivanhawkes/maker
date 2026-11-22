#!/usr/bin/env python3
"""Generate the left and right keyboard PCBs (placement and nets, no routing yet).

    python tools/pcb_generate.py            # writes pcb/left/left.kicad_pcb, pcb/right/right.kicad_pcb

Needs KiCad 10's `pcbnew` Python module (the devenv shell's KiCad, or PYTHONPATH set to
kicad-base's site-packages) and PyYAML. Inputs:
    layout/generated/{left,right}-hand.csv   switch centres and rotations (from layout.yaml)
    pcb/pins.yaml                            controller pin assignment (shared with firmware)
    pcb/lib/marbastlib/...                   pinned third-party footprints
    $KICAD10_FOOTPRINT_DIR                   KiCad stock footprints

Stage: v1 placement, ready for tools/pcb_route.py. Placeholder (clearly labelled on the board):
    - LED supply net VLED ends at test pad TP_VLED: supply design is open.

Battery path: JST-PH -> power switch -> nice!nano RAW pin. The official nice!nano v2
pinout labels RAW "BATTERY+" (as well as the extra B+ pad, which is not socketed).
Copper keep-outs cover the area between the controller's pin rows and a strip beyond its
antenna end (see CONTROLLER_KEEPOUTS); the antenna position on the module is unverified.
GND is poured on both layers.
"""

from __future__ import annotations

import csv
import math
import os
import subprocess
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
# Copper keep-outs around the controller, as (x0, y0, x1, y1) relative to its centre in plan
# coordinates. The pin pads (x = +/-7.62, y = +/-13.97, 1.8 mm) stay outside, so tracks can
# reach them. v0 covered the pads too, which left every controller pin unroutable.
#   - between the two pin rows, the full module length (parts on the module's underside);
#   - the module's far end from USB (plan -y), where the antenna is: the footprint marks
#     USB at plan +y. The module ends about 16.6 mm from its centre; the strip runs to 21 mm.
CONTROLLER_KEEPOUTS = (
    (-6.3, -15.3, 6.3, 16.6),
    (-9.5, -21.0, 9.5, -15.3),
)


def mm(v: float) -> int:
    return pcbnew.FromMM(v)


# Design rules: conservative values inside JLCPCB's and PCBWay's standard 2-layer
# capabilities. Re-check against the chosen fab house before ordering.
RULES = {
    "track": 0.25, "clearance": 0.2, "via_diameter": 0.6, "via_drill": 0.3,
    "power_track": 0.5, "power_via_diameter": 0.8, "power_via_drill": 0.4,
    "copper_edge": 0.3,        # enforced by the custom rule in CUSTOM_RULES
    "copper_edge_floor": 0.2,  # board-setup minimum; only the LED cut-outs use it
}
POWER_NETS = ("GND", "RAW", "BAT_IN", "VLED", "VCC_3V3_SW")


def apply_rules(board: pcbnew.BOARD) -> None:
    ds = board.GetDesignSettings()
    ds.m_CopperEdgeClearance = mm(RULES["copper_edge_floor"])
    ds.m_TrackMinWidth = mm(0.2)  # fab minimum we allow; netclasses use wider tracks
    ns = ds.m_NetSettings
    dc = ns.GetDefaultNetclass()
    dc.SetTrackWidth(mm(RULES["track"]))
    dc.SetClearance(mm(RULES["clearance"]))
    dc.SetViaDiameter(mm(RULES["via_diameter"]))
    dc.SetViaDrill(mm(RULES["via_drill"]))
    pw = pcbnew.NETCLASS("Power")
    pw.SetTrackWidth(mm(RULES["power_track"]))
    pw.SetClearance(mm(RULES["clearance"]))
    pw.SetViaDiameter(mm(RULES["power_via_diameter"]))
    pw.SetViaDrill(mm(RULES["power_via_drill"]))
    ns.SetNetclass("Power", pw)
    ns.ClearNetclassPatternAssignments()
    for n in POWER_NETS:
        ns.SetNetclassPatternAssignment(n, "Power")
    ns.RecomputeEffectiveNetclasses()


# Custom DRC rules, written to <name>.kicad_dru next to each board. Each one narrows a board
# rule for a specific footprint, with the reason.
CUSTOM_RULES = """(version 1)

# KiCad's stock SK6812MINI-E reverse-mount footprint puts its pads 0.247 mm from its own
# cut-out (measured by DRC, KiCad 10.0.8). The board-setup minimum is a floor that custom
# rules cannot relax, so it is 0.2 mm (RULES["copper_edge_floor"]) and this rule restores
# 0.3 mm everywhere except at the LED cut-outs. To verify against the chosen fab house's
# copper-to-cut-out minimum before ordering.
(rule "Copper to edge except LED cut-outs"
  (constraint edge_clearance (min 0.3mm))
  (condition "!A.memberOfFootprint('LED*') && !B.memberOfFootprint('LED*')"))

# The keep-out between the controller's pin rows blocks the inward thermal spoke, so GND
# pins there get at least one spoke instead of two.
(rule "Controller GND spokes"
  (constraint min_resolved_spokes (min 1))
  (condition "A.memberOfFootprint('U1') || B.memberOfFootprint('U1')"))
"""


def check_rules(board_path: Path) -> None:
    """Read the saved project file back and confirm the rules reached it."""
    import json
    pro = json.loads(board_path.with_suffix(".kicad_pro").read_text())
    rules = pro["board"]["design_settings"]["rules"]
    classes = {c["name"]: c for c in pro["net_settings"]["classes"]}
    patterns = {p["pattern"]: p["netclass"] for p in pro["net_settings"].get("netclass_patterns") or []}
    problems = []
    if abs(rules["min_copper_edge_clearance"] - RULES["copper_edge_floor"]) > 1e-6:
        problems.append(f"copper edge {rules['min_copper_edge_clearance']}")
    if abs(classes["Default"]["track_width"] - RULES["track"]) > 1e-6:
        problems.append(f"default track {classes['Default']['track_width']}")
    if "Power" not in classes or abs(classes["Power"]["track_width"] - RULES["power_track"]) > 1e-6:
        problems.append("Power net class missing or wrong")
    if any(patterns.get(n) != "Power" for n in POWER_NETS):
        problems.append(f"power net patterns {patterns}")
    if problems:
        raise SystemExit(f"{board_path.name}: rules not saved: {problems}")


def fill_zones(board: pcbnew.BOARD) -> None:
    board.BuildConnectivity()
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise SystemExit("zone fill failed")


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

    def join_same_pads(self, fp, layer=pcbnew.B_Cu, width: float = 0.25):
        """Tie together pads that share a number within one footprint.

        The hot-swap socket footprint gives each socket pin a plated hole and two overlapping
        SMD tabs, all with the same number. KiCad treats overlapping copper as connected, but
        Freerouting does not and reports them as unrouted, so join their centres explicitly.
        """
        groups: dict[str, list] = {}
        for p in fp.Pads():
            if p.GetNumber() and p.IsOnLayer(layer):
                groups.setdefault(p.GetNumber(), []).append(p)
        for pads in groups.values():
            pads.sort(key=lambda p: (p.GetPosition().x, p.GetPosition().y))
            for a, b in zip(pads, pads[1:]):
                t = pcbnew.PCB_TRACK(self.b)
                t.SetStart(a.GetPosition())
                t.SetEnd(b.GetPosition())
                t.SetWidth(mm(width))
                t.SetLayer(layer)
                t.SetNet(a.GetNet())
                self.b.Add(t)

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
        B.join_same_pads(sw)
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

    # Copper keep-outs at the controller (antenna position on the module still unverified;
    # see CONTROLLER_KEEPOUTS). Pads stay outside them.
    both = pcbnew.LSET()
    both.AddLayer(pcbnew.F_Cu)
    both.AddLayer(pcbnew.B_Cu)
    for i, (x0, y0, x1, y1) in enumerate(CONTROLLER_KEEPOUTS):
        zone = pcbnew.ZONE(B.b)
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowZoneFills(True)
        zone.SetDoNotAllowPads(False)
        zone.SetDoNotAllowFootprints(False)
        zone.SetLayerSet(both)
        poly = zone.Outline()
        poly.NewOutline()
        for ox, oy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            poly.Append(to_board(cx + ox * sx, cy + oy))
        zone.SetZoneName(f"controller-keepout-{i}")
        B.b.Add(zone)

    # Provisional outline: convex hull of key cells, the controller and edge parts.
    pts = []
    for k in keys:
        x, y, r = float(k["x_mm"]), float(k["y_mm"]), float(k["rotation_deg"])
        for cxo, cyo in ((-9.525, -9.525), (9.525, -9.525), (9.525, 9.525), (-9.525, 9.525)):
            dx, dy = rot(cxo, cyo, r)
            pts.append((x + dx, y + dy))
    for (px, py), (hw, hh) in ((POWER_SWITCH_AT, (3.5, 5.0)), (RESET_AT, (3.5, 5.0)), (JST_AT, (5.0, 5.0))):
        for ox, oy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            pts.append(((px + ox) * sx, py + oy))
    for ox, oy in ((-10.0, -21.5), (10.0, -21.5), (10.0, 18.5), (-10.0, 18.5)):  # controller incl. antenna strip
        pts.append(((CONTROLLER_AT[0] + ox) * sx, CONTROLLER_AT[1] + oy))
    hull = outline_points([(round(a, 4), round(b, 4)) for a, b in pts])

    # GND pours on both layers, inset from the outline by the copper-to-edge rule (the zone
    # clearance and the edge rule both apply). Freerouting treats them as planes and connects
    # GND pads to them with vias; tools/pcb_route.py refills them after routing.
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(B.b)
        zone.SetLayer(layer)
        zone.SetNet(B.net("GND"))
        zone.SetLocalClearance(mm(RULES["clearance"]))
        zone.SetMinThickness(mm(0.25))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        zone.SetThermalReliefGap(mm(0.3))
        zone.SetThermalReliefSpokeWidth(mm(0.4))
        zone.SetZoneName(f"GND-{'top' if layer == pcbnew.F_Cu else 'bottom'}")
        poly = zone.Outline()
        poly.NewOutline()
        for a, b in hull:
            poly.Append(to_board(a, b))
        B.b.Add(zone)
    for a, b in zip(hull, hull[1:] + hull[:1]):
        seg = pcbnew.PCB_SHAPE(B.b)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(to_board(*a))
        seg.SetEnd(to_board(*b))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        B.b.Add(seg)

    apply_rules(B.b)
    fill_zones(B.b)

    note = pcbnew.PCB_TEXT(B.b)
    note.SetText(f"{side.upper()} v1 placement - NOT FOR FAB")
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
        # A BOARD built in Python has no project, so its net classes and rules are not saved
        # (KiCad keeps them in <name>.kicad_pro). Finish the board in a fresh process: start
        # an empty project file, load the board (which attaches that project), apply the
        # rules and save. In the process that built the board, SaveBoard does not write the
        # project (checked with KiCad 10.0.8), hence the subprocess.
        out.with_suffix(".kicad_pro").write_text("{}\n")
        out.with_suffix(".kicad_dru").write_text(CUSTOM_RULES)
        subprocess.run([sys.executable, __file__, "--finish", str(out)], check=True)
        check_rules(out)
        fps = len(B.b.GetFootprints())
        print(f"wrote {out.relative_to(ROOT)} (+ .kicad_pro rules): {fps} footprints, {len(B.nets)} nets")
    return 0


def finish(board_path: str) -> int:
    board = pcbnew.LoadBoard(board_path)
    apply_rules(board)
    fill_zones(board)
    pcbnew.SaveBoard(board_path, board)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--finish":
        sys.exit(finish(sys.argv[2]))
    sys.exit(main())
