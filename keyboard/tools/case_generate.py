"""Generate the keyboard-1 case for both halves, check it, and export it to cad/case/.

Run with FreeCADCmd from keyboard/, after tools/case_board.py has written the board data:

    FreeCADCmd tools/case_generate.py

Three printed parts a half (docs/case.md has the drawing and the reasons):

    tray   floor, walls, board supports, battery bay; the board drops in from above
    plate  1.6 mm switch plate, inlaid flush in the tray; its outer edge hooks under a dovetail
    lid    raised cover over the controller, connector and battery; four M3 screws from below
           hold it, and its skirt clamps the plate's inner edge

Six screws a half, all from below: two through the board's holes H1 and H2 into bosses under
the plate, two through H3 and H4 into bosses under the lid, two in the battery lobe.

Everything is built for the left half in the layout's plan coordinates (layout/README.md) with
z = 0 at the board's top face, then mirrored for the right half. The right board is checked to
be the left one's mirror image first. Dimensions are from datasheets, not from measured parts.
"""

import csv
import hashlib
import json
import math
import os

import FreeCAD
import Mesh
import MeshPart
import Part

V = FreeCAD.Vector
OUT = "cad/case"

# Stack, mm. z = 0 is the board's top face.
PCB_T = 1.6
PLATE_TOP = 5.0   # Kailh CPG151101D214: plate top to board 5.0
PLATE_T = 1.6     # spec 1.5 +/- 0.1; the 1.6 mm PETG prototype holds the switches well (owner)
UNDER = 3.0       # below the board: hot-swap socket 1.8, pin tails about 1.8, and slack
FLOOR = 2.0
Z_PLATE = PLATE_TOP - PLATE_T
Z_FLOOR = -PCB_T - UNDER
Z_BOT = Z_FLOOR - FLOOR
LID_CEIL = 7.0    # clear height over the board under the lid (USB plug, see docs/case.md)
LID_T = 1.6
LID_TOP = LID_CEIL + LID_T

# Walls, mm, measured outwards from the board edge.
GAP = 0.8         # board to wall; lets the board swing in under the dovetail
LEDGE = 1.2       # the plate rests on this
RIM = 2.0         # wall beside the plate, flush with its top; the lid's skirt is as thick
WALL = GAP + LEDGE + RIM
FIT = 0.2         # plate to rim, each side
R_IN = 3.0        # radius given to inside corners of the outline
DOVE = 1.0        # dovetail: the rim overhangs the plate's outer edge by this at the top
DOVE_END = 6.0    # dovetail stops this far from the ends of the outer edge
CHAMFER = 1.0     # tray bottom edge and lid top edge
LAYER = 0.2       # print layer height (docs/decisions.md)

# Battery: Core Electronics CE04375, 400 mAh, 38 x 25 x 6 mm (product page, 2026-11-23).
CELL = (38.0, 25.0, 6.0)
BAY_L, BAY_W = CELL[0] + 4.5, CELL[1] + 3.5   # slack for the protection board, leads, tolerance
CELL_SWELL = 1.0                              # the lid's ribs stop this far above a 6 mm cell
DIVIDER = 1.6                                 # wall between the board and the bay
BAY_WALL = 2.4                                # outside wall of the bay
BAY_S0 = 40.5                                 # bay start, along the inner edge from its far end
BAY_D0 = GAP + DIVIDER
LOBE_D = BAY_D0 + BAY_W + BAY_WALL - WALL     # how far the lobe's core stands off the board edge
LOBE_S0, LOBE_RAMP = 20.0, 20.0               # the lobe starts below the power switch
LOBE_S1, LOBE_S2, LOBE_D2 = 84.0, 99.0, 12.0  # lower ramp, down to the bottom edge's line
WIRE_S = (48.0, 53.0)                         # slot for the battery lead through the divider
WIRE_Z = 0.5
RIB_S = (58.0, 76.0)                          # lid ribs that keep the cell in the bay

# Screws: M3, from below, the head recessed in the tray, the thread cut by the screw itself.
#   lid:   M3 x 12, two in the lobe and two through the board's holes H3 and H4;
#   plate: M3 x 8, through the board's holes H1 and H2 into bosses under the plate.
SCREW_LID, SCREW_PLATE = 12.0, 8.0
HEAD_R, CLEAR_R, PILOT_R, BOSS_R = 3.25, 1.7, 1.3, 3.5
HOLE_POST_R = 4.0                                      # tray post under a board hole: 0.75 mm round the head
LOBE_SCREWS_SD = ((31.0, 8.0), (90.0, 12.0))           # (s, d) on the inner edge
PLATE_HOLES, LID_HOLES = ("H1", "H2"), ("H3", "H4")
TIP = 0.8                                              # a screw's tip stops this far under the visible face
SEAT_LID = LID_TOP - TIP - SCREW_LID                   # where the head sits
SEAT_PLATE = PLATE_TOP - TIP - SCREW_PLATE
SKIN = 0.2                                             # printed over the head recess; drill it out

# Openings.
USB_W = 13.0          # tunnel for the USB-C plug's overmould
USB_FROM = 10.0       # the tunnel starts this far from the controller's centre, towards USB
USB_Z0 = -2.0         # its floor: the board is notched under the plug, so the plug can hang below the board's top
SLOT = 9.0            # power switch slot, along the edge
SCALLOP = 16.0        # recess outside it, for a fingernail
SCALLOP_D = GAP + 1.0  # the slider overhangs the board by 1.85: its tip is level with the recess's floor
RESET_R = 1.6         # hole over the reset button, for a pen
FOOT_R, FOOT_Z = 5.1, 0.6
FEET = ((-70.0, 26.0), (-64.0, -36.0), (-10.0, 50.0), (60.0, -50.0), (95.0, -25.0))

# Board supports: one post under the board for each key, at the spot within the key's cell
# that is furthest from the parts on the underside of both boards (searched on a 0.25 mm grid).
POST_R = 2.0
POST_MARGIN = 0.4     # least distance from a post to a part's courtyard

# Keycaps (KLP Lame, layout/README.md): 18 x 18, and 18 x 27 fitted lengthways on T2 and T3.
CAP, CAP_LONG, LONG_CAPS = 18.0, 27.0, ("T2", "T3")
CAP_GAP = 2.0         # lid to the long thumb caps, in plan
SPLIT_GAP = 1.3       # lid to the inner column's caps: less, to leave a wall beside H3's screw
BED = 256.0           # Bambu X2D profile found in the prototype's 3MF (docs/decisions.md)


LINES = []


def say(text):
    """Print a report line now (FreeCADCmd drops buffered output on exit) and keep it for report.txt."""
    print(text, flush=True)
    LINES.append(text)


def poly(pts):
    """A face from plan points. Points in line with their neighbours are dropped: the board's
    straight outer edge has two, and they leave T-junctions (open edges) in the meshes."""
    pts = [(p[0], p[1]) for p in pts]
    keep = [p for i, p in enumerate(pts)
            if seg_dist(p, pts[i - 1], pts[(i + 1) % len(pts)]) > 1e-4]
    return Part.Face(Part.makePolygon([V(x, y, 0) for x, y in keep] + [V(keep[0][0], keep[0][1], 0)]))


def disc(c, r):
    return Part.Face(Part.Wire(Part.makeCircle(r, V(c[0], c[1], 0))))


def grow(face, d):
    """Offset a face by d, with round corners. The arcs come back as 0.005 mm polylines: a prism
    of the face OCCT returns (lines and true arcs) drops out of later booleans without an error."""
    out = face.makeOffset2D(d, join=0, fill=False, openResult=False, intersection=False)
    assert len(out.Faces) == 1 and len(out.Faces[0].Wires) == 1, "offset by %.2f split the face" % d
    pts = out.Faces[0].OuterWire.discretize(Deflection=0.005)
    if pts[0].distanceToPoint(pts[-1]) < 1e-9:
        pts = pts[:-1]
    return poly([(p.x, p.y) for p in pts])


def one(shape):
    """Booleans return compounds: the single face in one.

    A fuse of faces can leave them split. Faces merge reliably as the top of a refined solid.
    """
    if len(shape.Faces) > 1:
        slabs = [f.extrude(V(0, 0, 1)) for f in shape.Faces]
        solid = slabs[0].fuse(slabs[1:]).removeSplitter()
        tops = [f for f in solid.Faces if all(abs(v.Z - 1) < 1e-9 for v in f.Vertexes)]
        assert len(tops) == 1, "expected one face, got %d" % len(tops)
        tops[0].translate(V(0, 0, -1))
        return tops[0]
    return shape.Faces[0]


def prism(face, z0, z1):
    f = face.copy()
    u0, _, v0, _ = f.ParameterRange
    if f.normalAt(u0, v0).z < 0:   # a face from a boolean can face down: its prism would be inside out
        f.reverse()
    f.translate(V(0, 0, z0))
    return f.extrude(V(0, 0, z1 - z0))


def cyl(c, r, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(c[0], c[1], z0))


def rect(c, hw, hh, rot):
    a = math.radians(rot)
    return [(c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a))
            for x, y in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]


def carve(solid, tools):
    """Cut the tools out one at a time; each must remove something and leave one valid solid."""
    for i, tool in enumerate(tools):
        out = solid.cut(tool)
        assert out.isValid() and len(out.Solids) == 1 and out.Volume < solid.Volume - 1e-6, \
            "cut %d of %d did nothing or broke the solid (%.3f -> %.3f mm3, %d solids)" % (
                i + 1, len(tools), solid.Volume, out.Volume, len(out.Solids))
        solid = out.Solids[0]
    return solid


def add(solid, tools):
    """Fuse the tools on one at a time; the result must stay one valid solid."""
    for i, tool in enumerate(tools):
        out = solid.fuse(tool).removeSplitter()
        assert out.isValid() and len(out.Solids) == 1, "fuse %d of %d broke the solid" % (i + 1, len(tools))
        solid = out.Solids[0]
    return solid


def bevel(solid, face, z, up):
    """Chamfer the outline of the solid's end face at height z, in steps of one print layer.

    OCCT's own chamfer fails on the lid's outline and returns a tray whose volume is wrong, so
    the edge is cut away a layer at a time instead; sliced at 0.2 mm it prints as a 45 degree
    chamfer. up is +1 when the solid lies above z, -1 when below.
    """
    wide = grow(face, 1.0)
    rings = []
    for k in range(round(CHAMFER / LAYER)):   # k = 0 is the layer at the end face
        a, b = sorted((z + up * LAYER * k, z + up * LAYER * (k + 1)))
        rings.append(prism(wide, a, b).cut(prism(grow(face, -(CHAMFER - LAYER * (k + 0.5))), a, b)))
    return carve(solid, rings)


class Frame:
    """(s, d) coordinates on an outline edge: s along it from p0, d outwards from the board."""

    def __init__(self, p0, p1, inside):
        self.p0 = p0
        self.length = math.dist(p0, p1)
        self.t = ((p1[0] - p0[0]) / self.length, (p1[1] - p0[1]) / self.length)
        n = (self.t[1], -self.t[0])
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        if (mid[0] - inside[0]) * n[0] + (mid[1] - inside[1]) * n[1] < 0:
            n = (-n[0], -n[1])
        self.n = n

    def at(self, s, d):
        return (self.p0[0] + s * self.t[0] + d * self.n[0], self.p0[1] + s * self.t[1] + d * self.n[1])

    def of(self, p):
        x, y = p[0] - self.p0[0], p[1] - self.p0[1]
        return x * self.t[0] + y * self.t[1], x * self.n[0] + y * self.n[1]

    def box(self, s0, s1, d0, d1):
        return poly([self.at(s0, d0), self.at(s1, d0), self.at(s1, d1), self.at(s0, d1)])

    def strip(self, s0, s1, dz):
        """A prism along the edge from a cross-section given as (d, z) points."""
        pts = [V(*self.at(s0, d), z) for d, z in dz]
        return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(self.t[0] * (s1 - s0), self.t[1] * (s1 - s0), 0))


def in_polygon(p, pts):
    hit = False
    for a, b in zip(pts, pts[1:] + pts[:1]):
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]:
            hit = not hit
    return hit


def post_spot(key, keys, out, keep):
    """(clearance, point) of the clearest spot under a key: clear of parts, the board edge and
    the switches' centre holes."""
    near = [b for b in keep if math.dist(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), (key["x"], key["y"])) < 35]
    holes = [(k["x"], k["y"]) for k in keys if math.dist((k["x"], k["y"]), (key["x"], key["y"])) < 35]
    edges = list(zip(out, out[1:] + out[:1]))
    best = (-1.0, None)
    for i in range(-40, 41):
        for j in range(-40, 41):
            p = rect((key["x"], key["y"]), -i * 0.25, -j * 0.25, key["rot"])[0]   # corner 0 is (-hw, -hh)
            c = min(max(x0 - p[0], p[0] - x1, y0 - p[1], p[1] - y1) for x0, y0, x1, y1 in near)
            if c <= best[0] or not in_polygon(p, out):
                continue
            c = min(c, min(math.dist(p, h) for h in holes) - 2.0, min(seg_dist(p, a, b) for a, b in edges) - 0.3)
            if c > best[0]:
                best = (c, p)
    return best


def hull(pts):
    """Convex hull (monotone chain), counter-clockwise."""
    pts = sorted(set(pts))

    def half(seq):
        out = []
        for p in seq:
            while len(out) > 1 and (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0]) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]
    return half(pts) + half(pts[::-1])


def seg_dist(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    k = max(0.0, min(1.0, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
    return math.dist(p, (ax + k * (bx - ax), ay + k * (by - ay)))


def thin(pts, tol):
    """Drop outline points that lie within tol of the chord that replaces them.

    The outlines here have thousands of 0.005 mm facets; cut at an angle they crash OCCT."""
    keep, i = [pts[0]], 0
    while i < len(pts) - 1:
        j = i + 1
        while j + 1 < len(pts) and all(seg_dist(p, pts[i], pts[j + 1]) < tol for p in pts[i + 1:j + 1]):
            j += 1
        keep.append(pts[j])
        i = j
    return keep


def read_keys(side):
    with open("layout/generated/%s-hand.csv" % side) as f:
        return [{"id": r["id"], "x": float(r["x_mm"]), "y": float(r["y_mm"]), "rot": float(r["rotation_deg"]),
                 "cut": float(r["cutout_mm"])} for r in csv.DictReader(f)]


def read_board(side):
    with open("%s/board-%s.json" % (OUT, side)) as f:
        board = json.load(f)
    with open(board["board"], "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == board["sha256"], \
            "%s changed since tools/case_board.py ran: run it again" % board["board"]
    assert board["thickness"] == PCB_T
    return board


def mirrored(box):
    return [-box[2], box[1], -box[0], box[3]]


def check_mirror(left, right):
    """The case is mirrored, so the right outline and top-side part positions must mirror the left's.

    The parts themselves do not mirror (the battery connector's body, and the sockets, diodes
    and LEDs under the board keep their handedness): the posts are placed clear of both boards'
    undersides, and each half is checked against its own board.
    """
    def key(board, flip):
        pts = sorted((round(-x if flip else x, 2), round(y, 2)) for x, y in board["outline"])
        tops = {p["ref"]: (round(-p["at"][0] if flip else p["at"][0], 2), round(p["at"][1], 2))
                for p in board["parts"] if p["ref"] in ("U1", "J1", "SW_PWR", "SW_RST") + PLATE_HOLES + LID_HOLES}
        return pts, tops
    assert key(left, True) == key(right, False), "the right board is not the left one mirrored"


def envelopes(keys, board, inner):
    """Solids standing for the board and everything on it, from datasheet sizes plus slack."""
    env = {"board": prism(poly(board["outline"]), -PCB_T, 0)}
    for p in board["parts"]:
        ref, at, box = p["ref"], p["at"], p["box"]
        if ref == "U1":      # nice!nano: 18 x 33 on sockets, USB end towards +y; height with slack
            env[ref] = prism(poly([(at[0] - 9.1, at[1] - 17.0), (at[0] + 9.1, at[1] - 17.0),
                                   (at[0] + 9.1, at[1] + 18.0), (at[0] - 9.1, at[1] + 18.0)]), 0, 6.5)
            env["U1 tails"] = prism(poly(rect(at, 9.0, 15.3, 0)), -PCB_T - 2.0, -PCB_T)
            continue
        if ref in PLATE_HOLES + LID_HOLES:
            continue
        face = poly([(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])])
        if p["back"]:
            env[ref] = prism(face, -PCB_T - 2.0, -PCB_T)   # sockets 1.8; the rest is lower
        else:
            env[ref] = prism(face, 0, {"J1": 5.2, "SW_RST": 2.2, "SW_PWR": 1.8}[ref])
            if ref == "J1":
                env["J1 tails"] = prism(face, -PCB_T - 2.0, -PCB_T)
            if ref == "SW_PWR":  # the slider overhangs the edge by 1.85 and travels along it
                s = inner.of(at)[0]
                env["SW_PWR slider"] = prism(inner.box(s - 2.6, s + 2.6, -0.5, 1.9), 0.2, 1.5)
    for k in keys:
        c = (k["x"], k["y"])
        env["MX " + k["id"]] = prism(poly(rect(c, 6.95, 6.95, k["rot"])), 0, PLATE_TOP).fuse(
            prism(poly(rect(c, 7.8, 7.8, k["rot"])), PLATE_TOP, PLATE_TOP + 6.6))
    cell = inner.box(BAY_S0 + (BAY_L - CELL[0]) / 2, BAY_S0 + (BAY_L + CELL[0]) / 2,
                     BAY_D0 + (BAY_W - CELL[1]) / 2, BAY_D0 + (BAY_W + CELL[1]) / 2)
    env["cell"] = prism(cell, Z_FLOOR, Z_FLOOR + CELL[2])
    caps = [prism(poly(rect((k["x"], k["y"]), CAP / 2, (CAP_LONG if k["id"] in LONG_CAPS else CAP) / 2, k["rot"])),
                  PLATE_TOP + 1.0, PLATE_TOP + 13.0) for k in keys]
    return env, caps


def build(keys, board, other):
    """The three parts of the left half, and the figures the report prints.

    other is the right board: the posts must also be clear of its underside, mirrored.
    """
    real = [tuple(p) for p in board["outline"]]
    out = hull(real)   # the outline without its two notches: the walls, the plate and the frames follow this
    parts = {p["ref"]: p for p in board["parts"]}
    holes = {r: tuple(parts[r]["at"]) for r in PLATE_HOLES + LID_HOLES}
    by_id = {k["id"]: k for k in keys}
    pcb = poly(out)
    inside = (pcb.CenterOfMass.x, pcb.CenterOfMass.y)
    u1, pwr, rst = (parts[r]["at"] for r in ("U1", "SW_PWR", "SW_RST"))

    # The inner edge carries the power switch; the outer edge is the straight left side.
    n = len(out)
    a, b = min(((out[i], out[(i + 1) % n]) for i in range(n)), key=lambda e: seg_dist(pwr, *e))
    g, h = (a, b) if a[1] > b[1] else (b, a)
    inner = Frame(g, h, inside)
    corner = next(p for p in (out[out.index(h) - 1], out[(out.index(h) + 1) % n]) if p != g)
    top_left = min(out, key=lambda p: p[0])
    bottom_left = min((p for p in out if p[1] < -30), key=lambda p: p[0])
    left = Frame(top_left, bottom_left, inside)
    assert all(abs(left.of(p)[1]) < 0.01 for p in out if p[0] < -70), "the outer edge is not straight"

    # Outline: the board, and a lobe on the inner edge for the battery.
    screws = [inner.at(s, d) for s, d in LOBE_SCREWS_SD]
    lobe = poly([inner.at(LOBE_S0, -0.5), inner.at(LOBE_S0 + LOBE_RAMP, LOBE_D), inner.at(LOBE_S1, LOBE_D),
                 inner.at(LOBE_S2, LOBE_D2), corner, inner.at(inner.length - 0.5, -0.5)])
    core = one(pcb.fuse([lobe]))
    outer = one(grow(one(grow(core, WALL + R_IN)), -R_IN))

    # The plate's side of the top: the finger columns, and the long thumb caps with their gap.
    def cap_corner(key, sx, sy):
        return rect((key["x"], key["y"]), CAP / 2 + CAP_GAP, CAP_LONG / 2 + CAP_GAP, key["rot"])[
            {(-1, 1): 3, (1, 1): 2, (1, -1): 1}[(sx, sy)]]
    t2, t3 = by_id["T2"], by_id["T3"]
    tl2, tr2, tl3, tr3, br3 = cap_corner(t2, -1, 1), cap_corner(t2, 1, 1), cap_corner(t3, -1, 1), \
        cap_corner(t3, 1, 1), cap_corner(t3, 1, -1)
    x_split = max(k["x"] for k in keys if k["id"].startswith("C5")) + CAP / 2 + SPLIT_GAP
    y_split = tl2[1] + (x_split - tl2[0]) * (tr2[1] - tl2[1]) / (tr2[0] - tl2[0])
    down = ((br3[0] - tr3[0]) / math.dist(br3, tr3), (br3[1] - tr3[1]) / math.dist(br3, tr3))
    keyside = poly([(-300, 300), (x_split, 300), (x_split, y_split), tr2, tl3, tr3, br3,
                    (br3[0] + 100 * down[0], br3[1] + 100 * down[1]), (-300, -300)])
    lid_face = one(outer.cut(keyside))

    # Plate.
    plate_face = one(grow(pcb, GAP + LEDGE - FIT).common(grow(keyside, RIM - FIT)))
    # The lid's bosses on the board's holes stay within the lid's own outline.
    lid_bosses = {r: one(disc(holes[r], BOSS_R).common(lid_face)) for r in LID_HOLES}
    plate = add(prism(plate_face, Z_PLATE, PLATE_TOP), [cyl(holes[r], BOSS_R - 0.25, 0.0, Z_PLATE + 0.1) for r in PLATE_HOLES])
    edge = GAP + LEDGE
    under_lid = [prism(grow(lid_bosses[r], FIT), Z_PLATE - 1, PLATE_TOP + 1) for r in LID_HOLES]
    plate = carve(plate, [t for t in under_lid if t.common(plate).Volume > 1e-6]   # where a lid boss passes the plate's edge
                  + [cyl(holes[r], PILOT_R, -0.1, SEAT_PLATE + SCREW_PLATE + 0.2) for r in PLATE_HOLES] + [prism(poly(rect((k["x"], k["y"]), k["cut"] / 2, k["cut"] / 2, k["rot"])), Z_PLATE - 1, PLATE_TOP + 1)
                          for k in keys]
                  + [left.strip(DOVE_END, left.length - DOVE_END, [
                      (edge - FIT - DOVE, PLATE_TOP + 0.01), (edge + 1, PLATE_TOP + 0.01), (edge + 1, Z_PLATE - 0.01),
                      (edge - FIT, Z_PLATE - 0.01)])])

    # Tray.
    top = PLATE_TOP + 1
    tray = bevel(prism(outer, Z_BOT, PLATE_TOP), outer, Z_BOT, 1)
    cavity = one(grow(pcb, GAP))
    recess = one(grow(pcb, edge).common(grow(keyside, RIM)))
    bay = inner.box(BAY_S0, BAY_S0 + BAY_L, BAY_D0, BAY_D0 + BAY_W)
    sw = inner.of(pwr)[0]
    tunnel = poly([(u1[0] - USB_W / 2, u1[1] + USB_FROM), (u1[0] + USB_W / 2, u1[1] + USB_FROM),
                   (u1[0] + USB_W / 2, u1[1] + 100), (u1[0] - USB_W / 2, u1[1] + 100)])
    tray = carve(tray, [
        prism(cavity, Z_FLOOR, top), prism(recess, Z_PLATE, top), prism(bay, Z_FLOOR, top),
        prism(inner.box(WIRE_S[0], WIRE_S[1], -1, BAY_D0 + 1), WIRE_Z, top),
        prism(tunnel, USB_Z0, top),
        prism(inner.box(sw - SLOT / 2, sw + SLOT / 2, -0.5, WALL + 1), -0.3, top),
        prism(inner.box(sw - SCALLOP / 2, sw + SCALLOP / 2, SCALLOP_D, WALL + 1), -1.5, top),
    ])
    tray = add(tray, [left.strip(DOVE_END, left.length - DOVE_END, [(edge + 0.01, Z_PLATE), (edge + 0.01, PLATE_TOP), (edge - DOVE, PLATE_TOP)])])

    # Posts under the board.
    keep = [p["box"] for p in board["parts"] if p["box"] and (p["back"] or p["ref"] == "J1")]
    keep += [mirrored(p["box"]) for p in other["parts"] if p["box"] and p["back"]]
    keep.append([u1[0] - 9.0, u1[1] - 15.3, u1[0] + 9.0, u1[1] + 15.3])   # socket tails
    posts, post_gap = [], 99.0
    for k in keys:
        gap, spot = post_spot(k, keys, real, keep)
        assert spot and gap >= POST_R + POST_MARGIN, "no clear spot for a post under %s (%.2f)" % (k["id"], gap)
        if all(math.dist(spot, p) > 2 * POST_R + 1 for p in posts):   # neighbours may share one
            posts.append(spot)
            post_gap = min(post_gap, gap - POST_R)
    tray = add(tray, [cyl(p, POST_R, Z_FLOOR - 0.1, -PCB_T) for p in posts]
               + [cyl(p, HOLE_POST_R, Z_FLOOR - 0.1, -PCB_T) for p in holes.values()])   # a wider post under each board hole

    # Screws and feet. The screw sites must be solid tray from the floor to the lid.
    solid = outer.cut([cavity, bay, recess])
    for p in screws:
        assert disc(p, HEAD_R + 1.2).cut(solid).Area < 1e-6, "screw site %s is not in solid tray" % (p,)
    seats = [(p, SEAT_LID, top) for p in screws] + [(holes[r], SEAT_LID, -PCB_T + 0.1) for r in LID_HOLES] \
        + [(holes[r], SEAT_PLATE, -PCB_T + 0.1) for r in PLATE_HOLES]
    tray = carve(tray, [cyl(p, HEAD_R, Z_BOT - 0.1, seat) for p, seat, _ in seats]
                 + [cyl(p, CLEAR_R, seat + SKIN, to) for p, seat, to in seats]
                 + [cyl(p, FOOT_R, Z_BOT - 0.1, Z_BOT + FOOT_Z) for p in FEET])

    # Lid.
    lid = bevel(prism(lid_face, PLATE_TOP, LID_TOP), lid_face, LID_TOP, -1)
    lid = carve(lid, [prism(grow(lid_face, -RIM), PLATE_TOP - 1, LID_CEIL)])
    rib_z = Z_FLOOR + CELL[2] + CELL_SWELL
    lid = add(lid, [cyl(p, BOSS_R, PLATE_TOP, LID_CEIL + 0.1) for p in screws]
              + [prism(lid_bosses[r], 0.0, LID_CEIL + 0.1) for r in LID_HOLES]   # these stand on the board
              + [prism(inner.box(s - 0.6, s + 0.6, BAY_D0 + 0.5, BAY_D0 + BAY_W - 0.5), rib_z, LID_CEIL + 0.1) for s in RIB_S])
    tip = SEAT_LID + SCREW_LID + 0.2
    lid = carve(lid, [cyl(p, PILOT_R, PLATE_TOP - 0.1, tip) for p in screws] + [cyl(holes[r], PILOT_R, -0.1, tip) for r in LID_HOLES]
                + [cyl(rst, RESET_R, LID_CEIL - 1, LID_TOP + 1), prism(tunnel, -1, LID_CEIL)])

    figures = {
        "inner": inner, "posts": len(posts), "post gap": post_gap,
        "bay wall": bay.distToShape(outer.OuterWire)[0],
        "cell to antenna": prism(bay, 0, 1).distToShape(prism(poly(rect((u1[0], u1[1] - 14.0), 9.0, 3.0, 0)), 0, 1))[0],
        "screws": screws + list(holes.values()), "outer": outer,
        # for tools/case_retro_generate.py, which builds another shell round these parts
        "core": core, "lid face": lid_face, "keyside": keyside, "tunnel": tunnel, "switch": sw, "reset": rst,
        "u1": u1, "seats": seats,
    }
    return {"tray": tray, "plate": plate, "lid": lid}, figures


def report(side, parts, env, caps):
    """Check one half's parts against its board and print the results. Returns the failures."""
    bad = []

    def check(ok, text):
        say("CASE %-5s %s %s" % (side, "ok  " if ok else "FAIL", text))
        if not ok:
            bad.append(text)
    for name, s in parts.items():
        b = s.BoundBox
        check(s.isValid() and len(s.Solids) == 1, "%s: one valid solid, %.1f cm3, %.1f x %.1f x %.1f mm" % (
            name, s.Volume / 1000, b.XLength, b.YLength, b.ZLength))
        check(max(b.XLength, b.YLength) < BED - 10, "%s fits the %.0f mm bed" % (name, BED))
    names = list(parts)
    for i, p in enumerate(names):
        for q in names[i + 1:]:
            check(parts[p].common(parts[q]).Volume < 1e-6, "%s and %s do not overlap" % (p, q))
    for name, s in parts.items():
        hits = [ref for ref, e in env.items() if s.common(e).Volume > 1e-6]
        check(not hits, "%s clears the board and its %d parts%s" % (name, len(env) - 1, ": hits " + ", ".join(hits) if hits else ""))
    gap = min(parts["lid"].distToShape(c)[0] for c in caps)
    check(gap >= SPLIT_GAP - 0.05, "lid to nearest keycap %.2f mm" % gap)
    cuts = [f for f in parts["plate"].Faces if abs(f.BoundBox.ZMax - PLATE_TOP) < 1e-6 and abs(f.BoundBox.ZMin - PLATE_TOP) < 1e-6]
    holes = sum(len(f.Wires) - 1 for f in cuts)
    check(holes == 28, "plate has %d switch cutouts" % holes)
    return bad


def main():
    if os.path.exists(OUT + "/report.txt"):
        os.remove(OUT + "/report.txt")   # a run that stops early must not leave the last run's results
    left, right = read_board("left"), read_board("right")
    check_mirror(left, right)
    say("CASE the right outline and top-side part positions are the left's mirrored: one case, mirrored")
    parts, fig = build(read_keys("left"), left, right)
    inner = fig["inner"]
    halves = {"left": parts, "right": {n: s.mirror(V(0, 0, 0), V(1, 0, 0)) for n, s in parts.items()}}
    mirrored_inner = Frame((-inner.p0[0], inner.p0[1]), (-inner.at(inner.length, 0)[0], inner.at(inner.length, 0)[1]), (0, 0))
    bad = []
    for side, board, frame in (("left", left, inner), ("right", right, mirrored_inner)):
        env, caps = envelopes(read_keys(side), board, frame)
        bad += report(side, halves[side], env, caps)

    b = fig["outer"].BoundBox
    say("CASE size: %.1f x %.1f mm in plan; tray %.1f high, %.1f to the plate's top, %.1f over the lid" % (
        b.XLength, b.YLength, PLATE_TOP - Z_BOT, PLATE_TOP - Z_BOT, LID_TOP - Z_BOT))
    say("CASE bay %.1f x %.1f x %.1f for a %.0f x %.0f x %.0f cell; outside wall at least %.2f; cell to the antenna end %.1f" % (
        BAY_L, BAY_W, Z_FLOOR + CELL[2] + CELL_SWELL - Z_FLOOR, CELL[0], CELL[1], CELL[2], fig["bay wall"], fig["cell to antenna"]))
    say("CASE %d board posts, at least %.2f from any part; screws at %s; head seats at z %.1f (lid) and %.1f (plate)" % (
        fig["posts"], fig["post gap"], ", ".join("(%.1f, %.1f)" % p for p in fig["screws"]), SEAT_LID, SEAT_PLATE))

    # Exports: STEP in assembly coordinates; 3MF meshes turned as they print (plate and lid top down).
    os.makedirs(OUT + "/print", exist_ok=True)
    for side, ps in halves.items():
        doc = FreeCAD.newDocument("case_" + side)
        for name, s in ps.items():
            s.exportStep("%s/%s-%s.step" % (OUT, side, name))
            doc.addObject("Part::Feature", name).Shape = s
            p = s.copy()
            if name != "tray":
                p.rotate(V(0, 0, 0), V(1, 0, 0), 180)
            p.translate(V(0, 0, -p.BoundBox.ZMin))
            mesh = MeshPart.meshFromShape(Shape=p, LinearDeflection=0.02, AngularDeflection=math.radians(5))
            path = "%s/print/%s-%s.3mf" % (OUT, side, name)
            mesh.write(path)
            m = Mesh.Mesh(path)
            m.removeDuplicatedPoints()   # the file repeats shared points; slicers merge them too
            ok = m.isSolid() and abs(m.Volume - s.Volume) < 0.002 * s.Volume
            say("CASE %-5s %s %s: %d facets, volume %.1f cm3" % (side, "ok  " if ok else "FAIL", path, m.CountFacets, m.Volume / 1000))
            if not ok:
                bad.append(path)
        env, caps = envelopes(read_keys(side), left if side == "left" else right, inner if side == "left" else mirrored_inner)
        doc.addObject("Part::Feature", "board_and_parts").Shape = Part.makeCompound(list(env.values()))
        doc.addObject("Part::Feature", "keycaps").Shape = Part.makeCompound(caps)
        doc.recompute()
        path = "%s/%s-case.FCStd" % (OUT, side)
        if os.path.exists(path):
            os.remove(path)   # saving over a file leaves a .FCBak beside it
        doc.saveAs(path)
        FreeCAD.closeDocument(doc.Name)
    say("CASE RESULT: %s" % ("%d FAILURES" % len(bad) if bad else "all checks pass"))
    with open(OUT + "/report.txt", "w") as f:
        f.write("\n".join(LINES) + "\n")
    if bad:
        raise SystemExit(1)


if not getattr(FreeCAD, "case_as_library", False):   # tools/wedge_generate.py imports this file for its helpers
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise
