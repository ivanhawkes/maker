#!/usr/bin/env python3
"""Generate the left and right keyboard PCBs: placement, nets and routing.

    python tools/pcb_generate.py            # writes pcb/left/left.kicad_pcb, pcb/right/right.kicad_pcb

Needs KiCad 10's `pcbnew` Python module (the devenv shell's KiCad, or PYTHONPATH set to
kicad-base's site-packages) and PyYAML. Inputs:
    layout/generated/{left,right}-hand.csv   switch centres and rotations (from layout.yaml)
    pcb/pins.yaml                            controller pin assignment (shared with firmware)
    parts/footprints/marbastlib/...          pinned third-party footprints
    parts/footprints/kicad/...               the KiCad stock footprints used, copied in

Stage: v3. The boards are fully routed here, by rule: per-key templates for the regular parts
and tools/pcb_maze.py for the few irregular links. No autorouter; the result is the same on every
run. Run kicad-cli DRC afterwards.

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
import subprocess
import sys
from pathlib import Path

import pcbnew
import yaml

from pcb_maze import Maze

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "layout" / "generated"
PINS = ROOT / "pcb" / "pins.yaml"
# Every footprint is loaded from the project's own copies (parts/README.md), so a board does
# not depend on which KiCad library version is installed.
MARB = ROOT / "parts" / "footprints" / "marbastlib"
STOCK = ROOT / "parts" / "footprints" / "kicad"

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
POWER_SWITCH_AT = (66.0, 30.0)
# The power switch sits on the board edge with its actuator overhanging (owner, 2026-11-23).
# Centre to edge: the mount pads end 1.83 mm from the centre and copper keeps 0.3 mm from the
# edge. The actuator reaches 3.15 mm, so it overhangs by 1.0 mm.
POWER_SWITCH_TO_EDGE = 2.15
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

# Plated-through pads: JLCPCB wants 0.3 mm from the hole to inner-layer copper (0.28 mm on the
# outer layers; vias and NPTH 0.2 mm, the board floor), and PCBWay's 10 mil component-hole ring
# is stricter than JLCPCB's 0.18 mm. The pair of a plated pad and a non-plated hole is left to
# the 0.2 mm floor: the socket's widened pads sit 0.205 mm from its own peg holes.
# Check kicad-cli's output after editing: a constraint KiCad does not know stops it reading
# the rest of this file without failing the run (min_resolved_spokes did, until 2026-11-23).
(rule "PTH hole to copper"
  (constraint hole_clearance (min 0.3mm))
  (condition "A.Type == 'Pad' && A.Pad_Type == 'Through-hole' && (B.Type != 'Pad' || B.Pad_Type != 'NPTH, mechanical')"))

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

    def keepout(self, pts: list[tuple[float, float]], name: str, copper=None):
        """A rule area with no tracks, vias or fills (pads allowed), on every copper layer unless given."""
        zone = pcbnew.ZONE(self.b)
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowZoneFills(True)
        zone.SetDoNotAllowPads(False)
        zone.SetDoNotAllowFootprints(False)
        layers = pcbnew.LSET()
        for layer in copper or COPPER:
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
    """KiCad's SK6812MINI-E reverse-mount footprint with its pads moved LED_PAD_SHIFT outward.

    KiCad draws the cut corner and triangle at pin 1 (VDD); the part's own cut corner is at
    pin 3 (GND, datasheet). The drawing is turned half a turn so the board shows the part as it
    is fitted. Pads and cut-out are the same either way round.
    """
    fp = load(STOCK / "LED_SMD.pretty", "LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount")
    for g in fp.GraphicalItems():
        if g.GetClass() == "PCB_SHAPE" and g.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_Fab):
            g.Rotate(pcbnew.VECTOR2I(0, 0), pcbnew.EDA_ANGLE(180.0, pcbnew.DEGREES_T))
    mark = next(g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_SilkS and g.GetShape() == pcbnew.SHAPE_T_POLY)
    near = min(fp.Pads(), key=lambda p: (p.GetPosition() - mark.GetBoundingBox().GetCenter()).EuclideanNorm())
    assert near.GetNumber() == "3", f"LED mark is at pad {near.GetNumber()}, not pad 3 (GND)"
    for p in fp.Pads():  # freshly loaded: footprint at the origin, so positions are local
        pos = p.GetPosition()
        p.SetPosition(pcbnew.VECTOR2I(pos.x + mm(math.copysign(LED_PAD_SHIFT, pos.x)), pos.y))
    return fp


def pth_ring(fp: pcbnew.FOOTPRINT) -> pcbnew.FOOTPRINT:
    """Widen plated-through pads whose ring is under the fab minimum (the PTH rule in CUSTOM_RULES).

    The hot-swap socket footprint has 3.3 mm pads on 3.0 mm holes (0.15 mm) and KiCad's JST-PH
    1.2 mm pads on 0.75 mm holes (0.225 mm); PCBWay's normal tier wants 0.254 mm.
    """
    ring = mm(0.26)
    for p in fp.Pads():
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
            continue
        size, drill = p.GetSize(), p.GetDrillSize()
        want = pcbnew.VECTOR2I(max(size.x, drill.x + 2 * ring), max(size.y, drill.y + 2 * ring))
        if want != size:
            p.SetSize(want)
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


def edge_pose(at: tuple[float, float], d: float, pts: list[tuple[float, float]]):
    """Angle (degrees from square) and outline points for a part whose outer side is the board edge.

    Left-half plan coordinates. The edge runs from the part down to whichever outline point
    below it sticks out furthest, and passes `d` from the part's centre: the tangent from that
    point to a circle of radius `d`. Returns the angle and the edge 5 mm either side of the part.
    """
    px, py = at
    phi = max(math.atan2(qx - px, py - qy) - math.asin(d / math.hypot(qx - px, qy - py))
              for qx, qy in pts if qy < py - d)
    tx, ty = px + d * math.cos(phi), py + d * math.sin(phi)
    ex, ey = 5.0 * math.sin(phi), -5.0 * math.cos(phi)
    return math.degrees(phi), [(tx - ex, ty - ey), (tx + ex, ty + ey)]


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
    frames: dict[str, tuple[float, float, float]] = {}  # key id -> (x, y, rotation)
    parts_by_key: dict[str, tuple] = {}  # key id -> (switch, diode)
    thumb_pin2: dict[str, pcbnew.PAD] = {}  # thumb key id -> pin 2 plated hole
    for i, k in enumerate(keys, start=1):
        x, y, r = float(k["x_mm"]), float(k["y_mm"]), float(k["rotation_deg"])
        kid = k["id"]
        sw = B.place(pth_ring(load(MARB / "marbastlib-mx.pretty", "SW_MX_HS_CPG151101S11_1u")), f"SW{i}", x, y, r, True, kid)
        check_switch_pins(sw, x, y, r)
        if k["group"] == "T":
            col, row = "T", pins["thumb_rows"][kid]
        else:
            col, row = k["group"], k["row"]
        B.connect(sw, "2", f"COL_{col}")
        if col == "T":
            thumb_pin2[kid] = next(p for p in sw.Pads() if p.GetNumber() == "2" and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
        else:
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
        parts_by_key[kid] = (sw, d)
        if col == "T":
            thumb_links.append((x, y, r, next(p for p in sw.Pads() if p.GetNumber() == "1" and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH),
                                next(p for p in d.Pads() if p.GetNumber() == "2")))
        lx, ly = rot(*LED_OFFSET, r)
        # The right half's chain crosses the thumbs the other way, so its thumb LEDs turn 180
        # degrees: DOUT then faces the next thumb, as on the left (see the thumb chain below).
        flip = 180.0 if col == "T" and side == "right" else 0.0
        led = B.place(load_led(), f"LED{i}", x + lx, y + ly, r + flip, True, "SK6812MINI-E (optional)")
        led_order.append((col, row, kid, led))
        frames[kid] = (x, y, r)
        # Freerouting does not treat a footprint's cut-out as board edge, so keep tracks and
        # vias out of the cut-out plus the 0.3 mm edge rule (cut-out reaches 1.80 x 1.60 mm
        # from the centre, arcs included). The pads start at 2.11 mm and stay reachable.
        cx_, cy_ = x + lx, y + ly
        B.keepout([(cx_ + a, cy_ + b) for a, b in (rot(-2.1, -1.9, r), rot(2.1, -1.9, r), rot(2.1, 1.9, r), rot(-2.1, 1.9, r))],
                  f"led-cutout-{kid}")

    # LED chain: from the controller's thumb end, up C5, serpentine across to C0 (ending at
    # C0R4, bottom left), then along the bottom edge to the thumb keys T0..T3.
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
    if side == "right":
        # Decided (owner, 2026-11-23): on the right half the nice!nano mounts upside down
        # (components towards the PCB), the usual practice on split boards, which mirrors its
        # pins: the matrix pins (pads 1-12) then face the keys and RAW/RST face the power switch
        # and reset, as on the left. In KiCad that is the footprint flipped in x.
        u.Flip(u.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)  # checked: pad 1 at (-44.38, 33.97)
    for pad_no, net in pad_net.items():
        B.connect(u, str(pad_no), net)
    upads = {p.GetNumber(): p for p in u.Pads()}

    # ------------------------------------------------------------------ scripted routing
    # Every track below is placed by rule and locked, so a board is the same on every run.
    # Freerouting 2.5.0 is not repeatable and leaves short links open (docs/pcb.md). The paths
    # were checked by hand in key-local coordinates and then by KiCad DRC. A point is a board
    # point, a plan (x, y), or a key-local (key id, x, y); the key-local facts used:
    #   switch pin 1 (-3.81, 2.54), pin 2 (2.54, 5.08), holes 3.3 mm; socket tabs on B.Cu out to
    #   x = -8.64 and 7.37; stem hole r 2.0 at (0, 0); pegs r 0.875 at (+/-5.08, 0);
    #   diode cathode (7, -2.35), anode (7, -5.65); LED pads at x = +/-2.785, y = -4.33 and -5.83
    #   (DOUT right upper, DIN left lower), its keep-out |x| <= 2.1, y -6.98..-3.18;
    #   plane vias at (3.92, -6.14) and (-4.02, -4.0).
    F, BK = pcbnew.F_Cu, pcbnew.B_Cu
    def pt(p):
        if isinstance(p, pcbnew.VECTOR2I):
            return p
        if isinstance(p[0], str):
            kx, ky, kr = frames[p[0]]
            ox, oy = rot(p[1], p[2], kr)
            return to_board(kx + ox, ky + oy)
        return to_board(*p)

    def plan(p):
        return pcbnew.ToMM(p.x) - ORIGIN[0], ORIGIN[1] - pcbnew.ToMM(p.y)

    def pad_of(fp, number, pth=False):
        return next(p for p in fp.Pads() if p.GetNumber() == number
                    and (not pth or p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH))

    def track(pts, net, layer=BK):
        pts = [pt(p) for p in pts]
        for s, e in zip(pts, pts[1:]):
            if math.hypot(s.x - e.x, s.y - e.y) < mm(0.001):
                continue
            t = pcbnew.PCB_TRACK(B.b)
            t.SetStart(s)
            t.SetEnd(e)
            t.SetWidth(mm(RULES["track"]))
            t.SetLayer(layer)
            t.SetNet(net)
            t.SetLocked(True)
            B.b.Add(t)
        return pts[-1]

    def via_at(p, net):
        v = pcbnew.PCB_VIA(B.b)
        v.SetPosition(pt(p))
        v.SetWidth(mm(RULES["via_diameter"]))
        v.SetDrill(mm(RULES["via_drill"]))
        v.SetNet(net)
        v.SetLocked(True)
        B.b.Add(v)

    def path(net, *runs):
        """Tracks on alternating layers: each (layer, points) run starts, through a via, where the last ended."""
        last = None
        for layer, pts in runs:
            if last is not None:
                via_at(last, net)
                pts = [last, *pts]
            last = track(pts, net, layer)

    # Finger columns: the keys of a column are collinear, so one straight F.Cu track joins the
    # pin 2 holes. It clears the stem hole by 0.42 mm and the LED cut-out by 0.6 mm.
    for pads in col_pins.values():
        pads.sort(key=lambda t: t[0])
        track([p.GetPosition() for _, p in pads], pads[0][1].GetNet(), F)

    # Finger rows: B.Cu at key-local y = -2.35 (the cathode's height; 0.225 mm under the stem
    # hole, 0.7 mm over the LED keep-out). From each cathode to x = 8.6, between the diode and
    # the next column's socket, across to the next column's x = -10.45, then to its cathode.
    # Columns in board order, so the mirrored half works.
    for row, cells in row_cells.items():
        cols = sorted(cells, key=lambda c: cells[c][0])
        for a, b in zip(cols, cols[1:]):
            track([cells[a][3].GetPosition(), (a + row, 8.6, -2.35), (b + row, -10.45, -2.35), cells[b][3].GetPosition()],
                  cells[a][3].GetNet())

    # Row ends, from C5's cathode (next to the controller) to the row's pad. A row on the inner
    # pin row leaves outward past C5's cell edge (x = 40.3) and angles to 2 mm short of its pad;
    # a row on the outer pin row passes under the antenna keep-out (y = -1.6) and comes up
    # beside the outer row (x = 62.5).
    for row, cells in row_cells.items():
        cpad, upad = cells["C5"][3], upads[str(pins["rows"][row])]
        (_, cy_), (ux, uy) = plan(cpad.GetPosition()), plan(upad.GetPosition())
        if (ux - cx) * sx < 0:  # inner pin row, facing the keys
            mid = [(40.3 * sx, cy_), (ux - 2.0 * sx, uy)]
        else:
            mid = [(40.3 * sx, cy_), (40.3 * sx, -1.6), (62.5 * sx, -1.6), (62.5 * sx, uy)]
        track([cpad.GetPosition(), *mid, upad.GetPosition()], cpad.GetNet())

    # Key-to-diode links. Thumbs (no row passes through them): B.Cu from pin 1 down to
    # y = -2.65, across above the LED pads to x = 5.5, down, then to the anode. Fingers: the row
    # is in the way on B.Cu, so pin 1 goes down F.Cu (0.27 mm from the peg) to a via under the
    # row, then B.Cu at y = -3.0, between the row and the LED keep-out, to the same end.
    for kid, (sw, d) in parts_by_key.items():
        p1, an = pad_of(sw, "1", True), pad_of(d, "2")
        if kid.startswith("T"):
            track([p1.GetPosition(), (kid, -3.81, -2.65), (kid, 5.5, -2.65), (kid, 5.5, -4.6), an.GetPosition()], p1.GetNet())
        else:
            path(p1.GetNet(), (F, [p1.GetPosition(), (kid, -3.81, -2.5), (kid, -3.2, -3.1)]),
                 (BK, [(kid, -2.6, -3.0), (kid, 5.5, -3.0), (kid, 5.5, -4.6), an.GetPosition()]))

    # LED chain links, DOUT of one LED to DIN of the next. DOUT leaves to the right, between the
    # VLED via and the key-to-diode link; DIN is entered from below-left at x = -4.1.
    #   down a column: B.Cu to a via under the LED, F.Cu down the right of the column track
    #     (x = 4.85 past the next pin 2, then x = 3.05 between the column track and the peg),
    #     a via under the next LED (at x = 3.2, to clear the column track), B.Cu across to DIN.
    #   up a column: a via beside DOUT, F.Cu up the same corridor, a via under the next LED.
    #   between columns and to the thumbs: see the branches; they differ by half because the
    #     next column is to the left on the left half and to the right on the mirrored half.
    thumb_out, thumb_in = [(4.85, -4.33), (4.85, -8.3)], [(-4.1, -8.3), (-4.1, -5.83)]
    if side == "right":  # thumb LEDs turned 180 degrees
        thumb_out, thumb_in = [(-4.1, -5.83), (-4.1, -8.3)], [(4.85, -8.3), (4.85, -4.33)]
    for (ca, ra, ka, la), (cb, rb, kb, lb) in zip(chain, chain[1:]):
        dout, din = pad_of(la, "2"), pad_of(lb, "4")
        net, o, i = dout.GetNet(), dout.GetPosition(), din.GetPosition()

        def at(kid, pts):
            return [(kid, x_, y_) for x_, y_ in pts]
        enter = [(kb, -4.1, -5.83), i]
        if ca == "T":
            track([o, *at(ka, thumb_out), *at(kb, thumb_in), i], net)
        elif cb == "T":
            # The long run to the first thumb, about 3 mm inside the bottom edge. On the right
            # half it first passes under C0R4's own incoming link.
            out = [(4.85, -4.33), (4.85, -9.5)] if side == "left" else [(4.85, -4.33), (4.85, -9.8), (-5.5, -9.8)]
            track([o, *at(ka, out), *at(kb, thumb_in), i], net)
        elif ca == cb and rb > ra:
            path(net, (BK, [o, (ka, 4.85, -4.33), (ka, 4.85, -8.3)]),
                 (F, [(kb, 4.85, 2.75), (kb, 3.05, 1.45), (kb, 3.05, -8.5), (kb, 3.2, -9.15)]),
                 (BK, [(kb, -4.1, -9.15), *enter]))
        elif ca == cb:
            path(net, (BK, [o, (ka, 4.75, -4.33)]),
                 (F, [(ka, 3.05, -2.6), (ka, 3.05, 1.3), (ka, 4.7, 2.9), (kb, 4.7, -8.3)]),
                 (BK, [(kb, -4.1, -8.3), *enter]))
        elif side == "left" and ra == "R1":
            # Over the top: F.Cu above both keys' pin 2, down the far left of the next key.
            path(net, (BK, [o, (ka, 4.75, -4.33)]),
                 (F, [(ka, 3.05, -2.6), (ka, 3.05, 1.3), (ka, 4.7, 2.9), (ka, 4.7, 8.6), (kb, -6.5, 8.6), (kb, -6.5, -5.83)]),
                 (BK, [i]))
        elif side == "left":
            # Under the bottom: below this key's own incoming link and the next key's cell.
            track([o, (ka, 4.85, -4.33), (ka, 4.85, -10.2), (ka, -5.5, -10.2), (kb, 11.0, -10.2), (kb, -4.1, -10.2), *enter], net)
        elif ra == "R1":
            # Under the anode to the next key. Where the next column is lower (C3 to C2), stay
            # above the column bus, which jogs up in the gap below this key.
            high = [(ka, 8.0, -9.1), (kb, -8.45, -3.1)] if frames[kb][1] < frames[ka][1] - 3.0 else []
            track([o, (ka, 4.85, -4.33), (ka, 4.85, -7.0), *high, (kb, -4.1, -8.3), *enter], net)
        else:
            # Where there is a gap between the columns (C2 to C1), stay left of the row's jog.
            gap = math.hypot(frames[ka][0] - frames[kb][0], frames[ka][1] - frames[kb][1]) > 21.0
            track([o, (ka, 4.85, -4.33), (ka, 4.85, -8.3), *([(kb, -12.0, -8.3)] if gap else []), (kb, -4.1, -8.3), *enter], net)

    # LED data: from its pad down F.Cu beside the controller (x = 41.0, clear of the antenna
    # keep-out), under C5R4 to a via, then B.Cu into the first LED's DIN.
    first = chain[0]
    din, dpad = pad_of(first[3], "4"), upads[str(pins["led_data"])]
    path(din.GetNet(), (F, [dpad.GetPosition(), (41.0 * sx, plan(dpad.GetPosition())[1]), (41.0 * sx, -24.5), (first[2], -4.1, -8.3)]),
         (BK, [(first[2], -4.1, -5.83), din.GetPosition()]))

    # Thumb column: an F.Cu trunk through key-local (2.54, 7.6) of each thumb, above the switch
    # pins, with a drop to each pin 2. A straight pin-to-pin track would pass 0.17 mm from the
    # next thumb's pin 1.
    tkeys = sorted(thumb_pin2, key=lambda k: frames[k][0] * sx)
    tnet = thumb_pin2[tkeys[0]].GetNet()
    track([(k, 2.54, 7.6) for k in tkeys], tnet, F)
    for k in tkeys:
        track([thumb_pin2[k].GetPosition(), (k, 2.54, 7.6)], tnet, F)

    # Column bus: each column reaches the controller along a B.Cu lane between two key rows,
    # in the 2.4 mm band above a key's socket (key-local y 7.06..9.45) and below the LED links of
    # the key above. C0-C2 run above the R2 keys, C3-C4 above the R3 keys; a lane starts at a
    # via on its column track and ends at its pad. Between two columns the lanes jog in the
    # 2 mm between one column's diode and the next's socket; the jog order (which lane turns
    # first) follows the stagger, so lanes never cross. The pads are assigned in arrival order
    # (pins.yaml), so the last turn beside the controller is crossing-free too.
    travel = ["C0", "C1", "C2", "C3", "C4", "C5"]
    lane_y, jog_x, turn_x = (7.3, 8.05, 8.8), (8.2, 8.95, 9.7), (40.5, 41.2, 41.9)
    for row, cols in (("R2", ("C0", "C1", "C2")), ("R3", ("C3", "C4"))):
        for i, col in enumerate(cols):
            net, y = col_pins[col][0][1].GetNet(), lane_y[i]
            pts = [(col + row, 2.54, y)]
            seq = travel[travel.index(col):]
            for c, d in zip(seq, seq[1:]):
                a, b = sorted((c + row, d + row), key=lambda k: frames[k][0])  # a is left on the board
                jx = jog_x[i] if frames[b][1] < frames[a][1] else jog_x[len(jog_x) - 1 - i]
                jog = [(a, jx, y), (b, jx - 19.05, y)]
                pts += jog if a == c + row else jog[::-1]
            upad = upads[str(pins["columns"][col])]
            uy, ly = plan(upad.GetPosition())[1], plan(pt(("C5" + row, 0.0, y)))[1]
            tx = turn_x[i] if uy < ly else turn_x[len(cols) - 1 - i]
            via_at(pts[0], net)
            track([*pts, (tx * sx, ly), (tx * sx, uy), upad.GetPosition()], net)
    # C5 is beside the controller: straight from its pad to C5R3's pin 2.
    c5pin = next(p for r_, p in col_pins["C5"] if r_ == "R3")
    c5pad = upads[str(pins["columns"]["C5"])]
    track([c5pad.GetPosition(), (40.0 * sx, plan(c5pad.GetPosition())[1]), ("C5R3", 9.0 * sx, 5.08), c5pin.GetPosition()], c5pin.GetNet())

    # Thumb rows: every thumb is on a different row, so rows must cross the board to them.
    # Thumb cathodes are reached down key-local x = 8.6, right of the switch's pin 2 tabs (to
    # 7.365) and the diode (to 7.6). A row tap is a via on the row's own track.
    def into_thumb(kid):
        return [(kid, 8.6, 8.5), (kid, 8.6, -2.35), pad_of(parts_by_key[kid][1], "1").GetPosition()]

    rnet = {r: B.net(f"ROW_{r}") for r in ("R1", "R2", "R3", "R4")}
    # R1 to T0 and R2 to T1: a via on the row in the gap between two columns, F.Cu down the gap
    # (clear of both columns' holes), a via above the thumb, then B.Cu into its cathode. The
    # gaps differ by half because the cathodes, hence the row tracks, sit on each key's right.
    taps = ((("R1", 1.5, 41.65, -24.0, "T0"), ("R2", 20.8, 20.6, -25.5, "T1")) if side == "left" else
            (("R1", -1.5, 45.65, -24.0, "T0"), ("R2", -20.6, 22.6, -24.5, "T1")))
    for row, x_, y_top, y_bot, kid in taps:
        via_at((x_, y_top), rnet[row])
        path(rnet[row], (F, [(x_, y_top), (x_, y_bot)]), (BK, into_thumb(kid)))
    # R3 to T2: from pad 12 along F.Cu beside the antenna keep-out (x = 42.1, 1.1 mm from the
    # LED data line), to a via above T2, then B.Cu into its cathode.
    # R4 to T3: B.Cu from R4's existing track, around the load switch, to T3.
    p12 = upads[str(pins["rows"]["R3"])].GetPosition()
    if side == "left":
        path(rnet["R3"], (F, [p12, (42.1, plan(p12)[1]), (42.1, -26.5), (59.5, -26.5)]), (BK, into_thumb("T2")))
        track([(40.3, -17.5), (40.3, -25.0), (64.0, -25.0), *into_thumb("T3")], rnet["R4"])
    else:
        path(rnet["R3"], (F, [p12, (-42.1, plan(p12)[1]), (-42.1, -23.2)]), (BK, into_thumb("T2")))
        track([(-62.5, -1.6), (-68.5, -7.6), (-68.5, -27.0), *into_thumb("T3")], rnet["R4"])

    # Battery connector, power switch, reset, and placeholder pads.
    j = B.place(pth_ring(load(STOCK / "Connector_JST.pretty", "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal")), "J1",
                JST_AT[0] * sx, JST_AT[1], 0.0, False, "JST-PH battery (check polarity)")
    B.connect(j, "1", "BAT_IN")
    B.connect(j, "2", "GND")
    # Provisional outline: convex hull of key cells, the controller and edge parts. Collected
    # here because the power switch is turned to lie along the edge it makes.
    pts = []
    for k in keys:
        x, y, r = float(k["x_mm"]), float(k["y_mm"]), float(k["rotation_deg"])
        for cxo, cyo in ((-9.525, -9.525), (9.525, -9.525), (9.525, 9.525), (-9.525, 9.525)):
            dx, dy = rot(cxo, cyo, r)
            pts.append((x + dx, y + dy))
    for (px, py), (hw, hh) in ((RESET_AT, (3.5, 5.0)), (JST_AT, (5.0, 5.0))):
        for ox, oy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            pts.append(((px + ox) * sx, py + oy))
    for ox, oy in ((-10.0, -21.5), (10.0, -21.5), (10.0, 18.5), (-10.0, 18.5)):  # controller incl. antenna strip
        pts.append(((CONTROLLER_AT[0] + ox) * sx, CONTROLLER_AT[1] + oy))
    tilt, switch_edge = edge_pose(POWER_SWITCH_AT, POWER_SWITCH_TO_EDGE, [(a * sx, b) for a, b in pts])
    switch_edge = [(round(a * sx, 4), round(b, 4)) for a, b in switch_edge]
    # The footprint's actuator is at local +y: a quarter turn points it off the board.
    s = B.place(load(STOCK / "Button_Switch_SMD.pretty", "SW_SPDT_PCM12"), "SW_PWR",
                POWER_SWITCH_AT[0] * sx, POWER_SWITCH_AT[1], (90.0 + tilt) * sx, False, "Power")
    B.connect(s, "2", "BAT_IN")
    # On joins pad 2 to the pad the slider is pushed towards. The right half's switch is turned
    # the other way, so it uses pad 3: on is towards the user on both halves.
    on_pad = "1" if side == "left" else "3"
    B.connect(s, on_pad, "RAW")  # RAW is BATTERY+ on the nice!nano v2
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
    lsw = {}
    for ref, lib, name, (dx, dy), value, nets in parts:
        fp = lsw[ref] = B.place(load(lib, name), ref, (lx0 + dx) * sx, ly0 + dy, 0.0, True, value)
        for pad_no, net in nets.items():
            B.connect(fp, pad_no, net)

    # Copper keep-outs at the controller (antenna position on the module still unverified;
    # see CONTROLLER_KEEPOUTS). Pads stay outside them.
    # The area between the pin rows is kept clear on the outer layers only (parts on the
    # module's underside); the inner planes run under it, so the GND pins get their thermal
    # spokes. The antenna strip is clear on every layer.
    for i, (x0, y0, x1, y1) in enumerate(CONTROLLER_KEEPOUTS):
        B.keepout([(cx + ox * sx, cy + oy) for ox, oy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))],
                  f"controller-keepout-{i}", (pcbnew.F_Cu, pcbnew.B_Cu) if i == 0 else None)

    hull = outline_points([(round(a, 4), round(b, 4)) for a, b in pts] + switch_edge)
    assert switch_edge[0] in hull, "the power switch is not on the board edge"

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

    # The irregular remainder, the power nets and the thumb column's run to the controller, goes
    # to the grid router (tools/pcb_maze.py): deterministic, in this order, over the controller
    # side of the board, around everything placed above.
    def term(p):
        pos = p.GetPosition()
        return (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y),
                tuple(i for i, layer in enumerate((F, BK)) if p.IsOnLayer(layer)))

    def terms(fp, number):
        return [term(p) for p in fp.Pads() if p.GetNumber() == number]

    xa, xb = sorted((36.0 * sx, 86.0 * sx))
    maze = Maze(B.b, (ORIGIN[0] + xa, ORIGIN[1] - 40.0, ORIGIN[0] + xb, ORIGIN[1] + 52.0),
                [(ORIGIN[0] + a, ORIGIN[1] - b) for a, b in hull], RULES["clearance"], RULES["copper_edge"])
    trunk_end = pt((tkeys[-1], 2.54, 7.6))  # the thumb nearest the controller's outer side
    trunk = (pcbnew.ToMM(trunk_end.x), pcbnew.ToMM(trunk_end.y), (0,))
    # Longest first: the router has no rip-up, so a later net must find its way round earlier ones.
    jobs = (
        ("COL_T", [term(upads[str(pins["columns"]["T"])]), trunk]),
        ("RST", [term(upads[str(pins["power"]["rst"])])] + terms(rst, "1")),
        ("LED_EN", [term(upads[str(pins["led_power_enable"])])] + terms(lsw["Q2"], "1") + terms(lsw["R2"], "1")),
        ("BAT_IN", terms(j, "1") + terms(s, "2")),
        ("RAW", [term(upads[str(pins["power"]["raw"])])] + terms(s, on_pad) + terms(lsw["Q1"], "2") + terms(lsw["R1"], "1")),
        ("LED_GATE", terms(lsw["Q1"], "1") + terms(lsw["Q2"], "3") + terms(lsw["R1"], "2")),
    )
    for name, ts in jobs:
        power = name in POWER_NETS
        maze.route(B.net(name), ts, RULES["power_track" if power else "track"],
                   (RULES["power_via_diameter" if power else "via_diameter"], RULES["power_via_drill" if power else "via_drill"]))
    fill_zones(B.b)

    note = pcbnew.PCB_TEXT(B.b)
    note.SetText(f"{side.upper()} v3 - NOT FOR FAB")
    note.SetPosition(to_board(0.0, 70.0))
    note.SetLayer(pcbnew.Cmts_User)
    B.b.Add(note)
    return B


def main() -> int:
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
