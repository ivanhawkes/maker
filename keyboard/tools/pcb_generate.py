#!/usr/bin/env python3
"""Generate the left and right keyboard PCBs (placement and nets, no routing yet).

    python tools/pcb_generate.py            # writes pcb/left/left.kicad_pcb, pcb/right/right.kicad_pcb

Needs KiCad 10's `pcbnew` Python module (the devenv shell's KiCad, or PYTHONPATH set to
kicad-base's site-packages) and PyYAML. Inputs:
    layout/generated/{left,right}-hand.csv   switch centres and rotations (from layout.yaml)
    pcb/pins.yaml                            controller pin assignment (shared with firmware)
    pcb/lib/marbastlib/...                   pinned third-party footprints
    $KICAD10_FOOTPRINT_DIR                   KiCad stock footprints

Stage: v2, ready for tools/pcb_route.py. The finger columns (F.Cu) and finger rows (B.Cu) are
pre-routed as locked tracks; everything else is left to Freerouting.

LED supply (option B, owner 2026-11-23): VLED is RAW (the battery, 3.0-4.2 V) through a
high-side P-MOSFET, Q1, driven by a small N-MOSFET, Q2, from the LED_EN pin (pins.yaml).
R2 holds LED_EN low, so the LEDs are off unless the firmware turns them on. Each LED draws
about 1 mA even when dark (datasheet), hence the hardware switch.

Battery path: JST-PH -> power switch -> nice!nano RAW pin. The official nice!nano v2
pinout labels RAW "BATTERY+" (as well as the extra B+ pad, which is not socketed).
Copper keep-outs cover the area between the controller's pin rows and a strip beyond its
antenna end (see CONTROLLER_KEEPOUTS); the antenna position on the module is unverified.
Four layers: signals on F.Cu and B.Cu, a GND plane on In1.Cu and a VLED plane on In2.Cu.
Every SMD pad on a plane net gets a locked stub and via to its plane (Board.plane_vias).
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
# KiCad's stock SK6812MINI-E reverse-mount pads sit 0.247 mm from its 3.4 x 3.0 mm cut-out,
# under the 0.3 mm copper-to-edge rule. The cut-out cannot shrink: the body is 3.2 x 2.8 mm
# +/-0.1 (datasheet), so the pads move outward instead. The leads (5.88 mm tip to tip) still
# overlap the pads by about 0.8 mm.
LED_PAD_SHIFT = 0.06

# LED supply load switch, bottom side, in half-local plan coordinates for the LEFT half: the
# free area between the battery connector and the thumb keys.
LOAD_SWITCH_AT = (58.0, -16.0)

# Controller and edge parts in half-local plan coordinates for the LEFT half; the right
# half mirrors x. Provisional, for review.
CONTROLLER_AT = (52.0, 20.0)
JST_AT = (52.0, -6.0)
POWER_SWITCH_AT = (64.0, 30.0)
RESET_AT = (64.0, 12.0)
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


COPPER = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
PLANES = ((pcbnew.In1_Cu, "GND"), (pcbnew.In2_Cu, "VLED"))


def mm(v: float) -> int:
    return pcbnew.FromMM(v)


# Net class values: what the router uses, wider than the fab minimums below.
RULES = {
    "track": 0.25, "clearance": 0.2, "via_diameter": 0.6, "via_drill": 0.3,
    "power_track": 0.5, "power_via_diameter": 0.8, "power_via_drill": 0.4,
    "copper_edge": 0.3,  # enforced by the custom rule in CUSTOM_RULES
}

# Board-setup minimums (mm): the stricter of JLCPCB's and PCBWay's no-surcharge limits for a
# 2-layer, 1.6 mm, 1 oz board, read 2026-11-23, so either can make the board. Sources and the
# comparison are in docs/pcb.md, "Fab house design rules".
# BOARD_DESIGN_SETTINGS attribute: (value, .kicad_pro rules key, or None if kept in the board).
FAB_MIN = {
    "m_TrackMinWidth": (0.127, "min_track_width"),            # PCBWay 5 mil
    "m_MinClearance": (0.152, "min_clearance"),               # PCBWay 6 mil
    "m_CopperEdgeClearance": (0.25, "min_copper_edge_clearance"),  # PCBWay CNC edge
    "m_HoleClearance": (0.2, "min_hole_clearance"),  # JLCPCB via, NPTH; PTH 0.28 in CUSTOM_RULES
    "m_HoleToHoleMin": (0.45, "min_hole_to_hole"),            # JLCPCB pad hole to hole
    "m_MinThroughDrill": (0.2, "min_through_hole_diameter"),  # PCBWay: smaller costs extra
    "m_ViasMinSize": (0.45, "min_via_diameter"),              # JLCPCB: smaller costs extra
    "m_ViasMinAnnularWidth": (0.13, "min_via_annular_width"),  # PCBWay 5 mil via ring
    "m_SilkClearance": (0.15, "min_silk_clearance"),          # JLCPCB silk to pad
    "m_MinSilkTextHeight": (1.0, "min_text_height"),          # JLCPCB 1.0 mm
    "m_MinSilkTextThickness": (0.15, "min_text_thickness"),   # both 0.15 mm
    "m_SolderMaskToCopperClearance": (0.09, "solder_mask_to_copper_clearance"),  # JLCPCB
    "m_SolderMaskMinWidth": (0.13, None),                     # JLCPCB, black or white mask
}
# VLED is not here: at 0.5 mm Freerouting cannot pass between the LED pads. The LEDs are
# capped in firmware, so the current per track stays well under what 0.25 mm carries.
POWER_NETS = ("GND", "RAW", "BAT_IN", "VCC_3V3_SW")


def apply_rules(board: pcbnew.BOARD) -> None:
    ds = board.GetDesignSettings()
    for attr, (value, _) in FAB_MIN.items():
        setattr(ds, attr, mm(value))
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

# The board-setup copper-to-edge minimum is the fab floor, 0.25 mm (FAB_MIN); keep 0.3 mm.
(rule "Copper to edge"
  (constraint edge_clearance (min 0.3mm)))

# The keep-out between the controller's pin rows blocks the inward thermal spoke, so GND
# pins there get at least one spoke instead of two.
(rule "Controller GND spokes"
  (constraint min_resolved_spokes (min 1))
  (condition "A.memberOfFootprint('U1') || B.memberOfFootprint('U1')"))

# Plated-through pads: JLCPCB wants 0.3 mm from the hole to inner-layer copper (0.28 mm on the
# outer layers; vias and NPTH 0.2 mm, the board floor), and PCBWay's 10 mil component-hole ring
# is stricter than JLCPCB's 0.18 mm.
(rule "PTH hole to copper"
  (constraint hole_clearance (min 0.3mm))
  (condition "A.Type == 'Pad' && A.Pad_Type == 'Through-hole'"))

(rule "PTH pad annular ring"
  (constraint annular_width (min 0.254mm))
  (condition "A.Type == 'Pad' && A.Pad_Type == 'Through-hole'"))
"""


def check_rules(board_path: Path) -> None:
    """Read the saved project file back and confirm the rules reached it."""
    import json
    pro = json.loads(board_path.with_suffix(".kicad_pro").read_text())
    rules = pro["board"]["design_settings"]["rules"]
    classes = {c["name"]: c for c in pro["net_settings"]["classes"]}
    patterns = {p["pattern"]: p["netclass"] for p in pro["net_settings"].get("netclass_patterns") or []}
    problems = []
    for value, key in FAB_MIN.values():
        if key and abs(rules[key] - value) > 1e-6:
            problems.append(f"{key} {rules[key]}")
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
        self.b.SetCopperLayerCount(4)
        for layer, _ in PLANES:
            self.b.SetLayerType(layer, pcbnew.LT_POWER)
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

    def keepout(self, pts: list[tuple[float, float]], name: str):
        """A rule area on every copper layer with no tracks, vias or fills (pads allowed)."""
        zone = pcbnew.ZONE(self.b)
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowZoneFills(True)
        zone.SetDoNotAllowPads(False)
        zone.SetDoNotAllowFootprints(False)
        layers = pcbnew.LSET()
        for layer in COPPER:
            layers.AddLayer(layer)
        zone.SetLayerSet(layers)
        poly = zone.Outline()
        poly.NewOutline()
        for px, py in pts:
            poly.Append(to_board(px, py))
        zone.SetZoneName(name)
        self.b.Add(zone)

    def plane_vias(self):
        """Join each SMD pad on a plane net to its plane with a short, locked stub and via.

        Freerouting does not connect SMD pads to the inner planes. The via sits beyond the pad,
        away from the footprint centre, clear of the pad by the net's clearance.
        """
        planes = {net for _, net in PLANES}
        placed: list[tuple[str, pcbnew.VECTOR2I]] = []
        for fp in self.b.GetFootprints():
            centre = fp.GetPosition()
            for p in fp.Pads():
                if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or p.GetNetname() not in planes:
                    continue
                power = p.GetNetname() in POWER_NETS  # same values as apply_rules gives the classes
                via_d = mm(RULES["power_via_diameter" if power else "via_diameter"])
                drill = mm(RULES["power_via_drill" if power else "via_drill"])
                track_w = mm(RULES["power_track" if power else "track"])
                pos = p.GetPosition()
                dx, dy = pos.x - centre.x, pos.y - centre.y
                n = math.hypot(dx, dy) or 1.0
                reach = max(p.GetSize().x, p.GetSize().y) / 2 + via_d / 2 + mm(RULES["clearance"])
                at = pcbnew.VECTOR2I(int(pos.x + dx / n * reach), int(pos.y + dy / n * reach))
                # Two pads' vias can land together (left board, Q1 and C1): share the first.
                near = [v for net, v in placed if net == p.GetNetname()
                        and math.hypot(v.x - at.x, v.y - at.y) < via_d + mm(FAB_MIN["m_HoleToHoleMin"][0])]
                if near:
                    at = near[0]
                else:
                    placed.append((p.GetNetname(), at))
                    via = pcbnew.PCB_VIA(self.b)
                    via.SetPosition(at)
                    via.SetWidth(via_d)
                    via.SetDrill(drill)
                    via.SetNet(p.GetNet())
                    via.SetLocked(True)
                    self.b.Add(via)
                t = pcbnew.PCB_TRACK(self.b)
                t.SetStart(pos)
                t.SetEnd(at)
                t.SetWidth(track_w)
                t.SetLayer(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
                t.SetNet(p.GetNet())
                t.SetLocked(True)
                self.b.Add(t)

    def connect(self, fp, pad_number: str, net: str):
        hit = False
        for p in fp.Pads():
            if p.GetNumber() == pad_number:
                p.SetNet(self.net(net))
                hit = True
        if not hit:
            raise SystemExit(f"{fp.GetReference()}: no pad {pad_number!r}")


def load_led() -> pcbnew.FOOTPRINT:
    """KiCad's SK6812MINI-E reverse-mount footprint with its pads moved LED_PAD_SHIFT outward."""
    fp = load(STOCK / "LED_SMD.pretty", "LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount")
    for p in fp.Pads():  # freshly loaded: footprint at the origin, so positions are local
        pos = p.GetPosition()
        p.SetPosition(pcbnew.VECTOR2I(pos.x + mm(math.copysign(LED_PAD_SHIFT, pos.x)), pos.y))
    return fp


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
    pad_net[pins["led_power_enable"]] = "LED_EN"

    # Switches, diodes and LEDs.
    led_order = []
    col_pins: dict[str, list] = {}  # finger column -> pin 2 plated holes, by row
    row_cells: dict[str, dict] = {}  # finger row -> {column: (x, y, r, cathode pad)}
    thumb_links: list = []  # thumb keys: (x, y, r, switch pin 1 hole, diode anode)
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
        if col != "T":
            col_pins.setdefault(col, []).append(
                (row, next(p for p in sw.Pads() if p.GetNumber() == "2" and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)))
        B.connect(sw, "1", f"K_{kid}")
        B.join_same_pads(sw)
        dx, dy = rot(*DIODE_OFFSET, r)
        d = B.place(load(STOCK / "Diode_SMD.pretty", "D_SOD-123"), f"D{i}", x + dx, y + dy, r + 90.0, True, "1N4148W")
        B.connect(d, "1", f"ROW_{row}")  # cathode to row (col2row)
        if col != "T":
            row_cells.setdefault(row, {})[col] = (x, y, r, next(p for p in d.Pads() if p.GetNumber() == "1"))
        B.connect(d, "2", f"K_{kid}")
        if col == "T":
            thumb_links.append((x, y, r, next(p for p in sw.Pads() if p.GetNumber() == "1" and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH),
                                next(p for p in d.Pads() if p.GetNumber() == "2")))
        lx, ly = rot(*LED_OFFSET, r)
        led = B.place(load_led(), f"LED{i}", x + lx, y + ly, r, True, "SK6812MINI-E (optional)")
        led_order.append((col, row, kid, led))
        # Freerouting does not treat a footprint's cut-out as board edge, so keep tracks and
        # vias out of the cut-out plus the 0.3 mm edge rule (cut-out reaches 1.80 x 1.60 mm
        # from the centre, arcs included). The pads start at 2.11 mm and stay reachable.
        cx_, cy_ = x + lx, y + ly
        B.keepout([(cx_ + a, cy_ + b) for a, b in (rot(-2.1, -1.9, r), rot(2.1, -1.9, r), rot(2.1, 1.9, r), rot(-2.1, 1.9, r))],
                  f"led-cutout-{kid}")

    # Finger columns: the keys of a column are collinear, so one straight F.Cu track joins each
    # pin 2 hole to the next. It clears the stem hole by 0.42 mm and the LED cut-out by 0.6 mm.
    # Locked, so Freerouting keeps it.
    for col, pads in col_pins.items():
        pads.sort(key=lambda t: t[0])
        for (_, a), (_, b) in zip(pads, pads[1:]):
            t = pcbnew.PCB_TRACK(B.b)
            t.SetStart(a.GetPosition())
            t.SetEnd(b.GetPosition())
            t.SetWidth(mm(RULES["track"]))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(a.GetNet())
            t.SetLocked(True)
            B.b.Add(t)

    # Finger rows: one locked B.Cu track per row, at key-local y = -2.35 mm (the cathode's
    # height): it clears the stem hole by 0.225 mm and the LED cut-out keep-out by 0.7 mm. It
    # leaves each cathode to key-local x = 8.6, between the diode and the next column's socket,
    # jogs to the next column's x = -10.45 (19.05 mm on) and runs to that column's cathode.
    for row, cells in row_cells.items():
        # Left to right on the board: C0 first on the left half, C5 first on the mirrored right.
        cols = sorted(cells, key=lambda c: cells[c][0])
        for a, b in zip(cols, cols[1:]):
            ax, ay, ar, apad = cells[a]
            bx, by, br, bpad = cells[b]
            ox, oy = rot(8.6, -2.35, ar)
            ix, iy = rot(-10.45, -2.35, br)
            pts = [apad.GetPosition(), to_board(ax + ox, ay + oy), to_board(bx + ix, by + iy), bpad.GetPosition()]
            for s, e in zip(pts, pts[1:]):
                if math.hypot(s.x - e.x, s.y - e.y) < mm(0.001):
                    continue
                t = pcbnew.PCB_TRACK(B.b)
                t.SetStart(s)
                t.SetEnd(e)
                t.SetWidth(mm(RULES["track"]))
                t.SetLayer(pcbnew.B_Cu)
                t.SetNet(apad.GetNet())
                t.SetLocked(True)
                B.b.Add(t)

    # Thumb key-to-diode links, which Freerouting leaves open (it routes the finger keys' own).
    # B.Cu, key-local: pin 1 straight down to y = -2.65 (0.2 mm under the stem hole, clear of
    # the LED cut-out keep-out), across above the LED pads to x = 5.5, down, then to the anode.
    for x, y, r, pin, anode in thumb_links:
        pts = [pin.GetPosition()]
        for lx_, ly_ in ((-3.81, -2.65), (5.5, -2.65), (5.5, -4.6)):
            ox, oy = rot(lx_, ly_, r)
            pts.append(to_board(x + ox, y + oy))
        pts.append(anode.GetPosition())
        for s, e in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(B.b)
            t.SetStart(s)
            t.SetEnd(e)
            t.SetWidth(mm(RULES["track"]))
            t.SetLayer(pcbnew.B_Cu)
            t.SetNet(pin.GetNet())
            t.SetLocked(True)
            B.b.Add(t)

    # LED chain: from the controller's thumb end, up C5, serpentine across to C0 (ending at
    # C0R4, bottom left), then along the bottom edge to the thumb keys T0..T3. Each link is
    # short except C0R4 to T0, which has free board along the bottom edge.
    col_order = ["C5", "C4", "C3", "C2", "C1", "C0", "T"]
    chain = []
    for ci, col in enumerate(col_order):
        items = [t for t in led_order if t[0] == col]
        items.sort(key=lambda t: t[1] if col != "T" else t[2], reverse=(col != "T" and ci % 2 == 0))
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
    # LED supply load switch (option B), bottom side, 1206 passives and SOT-23 transistors.
    # SOT-23 pads: 1 gate, 2 source, 3 drain (DMG2305UX and BSS138: check the bought parts).
    lx0, ly0 = LOAD_SWITCH_AT
    sot = STOCK / "Package_TO_SOT_SMD.pretty"
    parts = (
        # ref, library, footprint, (dx, dy), value, {pad: net}
        ("Q1", sot, "SOT-23_Handsoldering", (0.0, 0.0), "DMG2305UX-7 (P-MOSFET)", {"1": "LED_GATE", "2": "RAW", "3": "VLED"}),
        ("Q2", sot, "SOT-23_Handsoldering", (0.0, -6.0), "BSS138 (N-MOSFET)", {"1": "LED_EN", "2": "GND", "3": "LED_GATE"}),
        ("R1", STOCK / "Resistor_SMD.pretty", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", (6.0, 0.0),
         "100k (Q1 gate pull-up)", {"1": "RAW", "2": "LED_GATE"}),
        ("R2", STOCK / "Resistor_SMD.pretty", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", (6.0, -6.0),
         "100k (LED_EN pull-down)", {"1": "LED_EN", "2": "GND"}),
        ("C1", STOCK / "Capacitor_SMD.pretty", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", (-6.0, 0.0),
         "10uF 10V X5R (VLED bulk)", {"1": "VLED", "2": "GND"}),
    )
    for ref, lib, name, (dx, dy), value, nets in parts:
        fp = B.place(load(lib, name), ref, (lx0 + dx) * sx, ly0 + dy, 0.0, True, value)
        for pad, net in nets.items():
            B.connect(fp, pad, net)

    # Copper keep-outs at the controller (antenna position on the module still unverified;
    # see CONTROLLER_KEEPOUTS). Pads stay outside them.
    for i, (x0, y0, x1, y1) in enumerate(CONTROLLER_KEEPOUTS):
        B.keepout([(cx + ox * sx, cy + oy) for ox, oy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))],
                  f"controller-keepout-{i}")

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

    # Four layers (owner, 2026-11-23): signals on F.Cu and B.Cu, solid planes inside, GND on
    # In1.Cu and VLED on In2.Cu. The planes are "power" layers, which the DSN export passes on,
    # so Freerouting routes no signals there and reaches the planes with vias.
    # tools/pcb_route.py refills them after routing.
    for layer, net in PLANES:
        zone = pcbnew.ZONE(B.b)
        zone.SetLayer(layer)
        zone.SetNet(B.net(net))
        zone.SetLocalClearance(mm(RULES["clearance"]))
        zone.SetMinThickness(mm(0.25))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        zone.SetThermalReliefGap(mm(0.3))
        zone.SetThermalReliefSpokeWidth(mm(0.4))
        zone.SetZoneName(f"{net}-plane")
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

    apply_rules(B.b)  # before plane_vias, which reads the net classes
    B.plane_vias()
    fill_zones(B.b)

    note = pcbnew.PCB_TEXT(B.b)
    note.SetText(f"{side.upper()} v1 - NOT FOR FAB")
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
