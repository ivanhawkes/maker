"""Generate the tenting wedges for the keyboard-1 case, check them, and export them to cad/case/.

Run with FreeCADCmd from keyboard/, after tools/case_generate.py has written the tray:

    FreeCADCmd tools/wedge_generate.py

A wedge is a cradle: the assembled case, stick-on feet and all, drops into a low rim that
follows its outline, and lifts out again. Nothing is screwed and the tray is not changed. The
wedge raises the inner edge; there is no tilt towards or away from the user.

It is built round the left tray in the case's own coordinates, with walls square to the case,
then turned so the desk is z = 0, which is also how it prints. The walls therefore lean with
the case, and a push along a key's axis lands on the base under that key. The body is a rim, a
ledge and ribs with open windows between them, so it prints without supports.
"""

import math
import os
import sys

import FreeCAD
import Mesh
import MeshPart
import Part

FreeCAD.case_as_library = True
sys.path.insert(0, "tools")
import case_generate as cg   # noqa: E402
from case_generate import V, say, poly, disc, grow, one, prism, cyl, carve, add, hull, in_polygon, seg_dist  # noqa: E402

OUT = "cad/case"
ANGLES = (5, 10, 15)   # trial angles (docs/decisions.md)
FIT = 0.3              # case to rim, each side
RIM_W, RIM_H = 2.4, 3.0   # the rim's top is 1.6 below the lowest opening in the tray (the USB tunnel, z -2)
LEDGE = 3.0            # the case's bottom edge rests on this, inside the rim
RIB, RIB_PITCH_X, RIB_PITCH_Y = 2.4, 40.0, 30.0
T_MIN = 5.0            # thickness under the case at its low edge
PAD_R = 6.5            # solid pad for each of the wedge's own stick-on feet
SEEDS = cg.FEET + ((40.0, 40.0),)    # the wedge's feet start under the case's, plus one under the high far corner
CASE_FOOT_R, CASE_FOOT_Z = 6.5, 3.5   # pocket for a foot left on the case: up to 12 mm across, 3 mm proud
PRESS_Z = cg.PLATE_TOP + 9.0          # about the top of a keycap


def thin(pts, tol):
    """Drop outline points that lie within tol of the chord that replaces them.

    The tray's outline has thousands of 0.005 mm facets; cut at an angle they crash OCCT."""
    keep, i = [pts[0]], 0
    while i < len(pts) - 1:
        j = i + 1
        while j + 1 < len(pts) and all(seg_dist(p, pts[i], pts[j + 1]) < tol for p in pts[i + 1:j + 1]):
            j += 1
        keep.append(pts[j])
        i = j
    return keep


def build(outer, keys, angle):
    """The left wedge in desk coordinates (the desk is z = 0), and the figures the report prints."""
    t = math.radians(angle)
    foot = grow(outer, FIT + RIM_W)
    b = foot.BoundBox
    ribs = [poly([(b.XMin - 1, y - RIB / 2), (b.XMax + 1, y - RIB / 2), (b.XMax + 1, y + RIB / 2), (b.XMin - 1, y + RIB / 2)])
            for y in [b.YMin + RIB_PITCH_Y * k for k in range(1, int(b.YLength / RIB_PITCH_Y) + 1)]]
    ribs += [poly([(x - RIB / 2, b.YMin - 1), (x + RIB / 2, b.YMin - 1), (x + RIB / 2, b.YMax + 1), (x - RIB / 2, b.YMax + 1)])
             for x in [b.XMin + RIB_PITCH_X * k for k in range(1, int(b.XLength / RIB_PITCH_X) + 1)]]
    windows = grow(outer, FIT - LEDGE).cut(ribs).Faces   # what is left open between the ledge and the ribs

    dz = T_MIN - (b.XMin * math.sin(t) + cg.Z_BOT * math.cos(t))

    def place(shape):
        s = shape.copy()
        s.rotate(V(0, 0, 0), V(0, 1, 0), -angle)
        s.translate(V(0, 0, dz))
        return s

    def desk(p):
        """Case coordinates to desk coordinates."""
        return (p[0] * math.cos(t) - p[2] * math.sin(t), p[1], p[0] * math.sin(t) + p[2] * math.cos(t) + dz)

    z_low = cg.Z_BOT - (b.XLength * math.tan(t) + T_MIN + 5)
    top = cg.Z_BOT + RIM_H
    seat = prism(grow(outer, FIT), cg.Z_BOT, top + 1)
    below = Part.makeBox(800, 800, 200, V(-400, -400, -200))
    block = carve(prism(foot, z_low, top), [seat]   # and a pocket for each foot left on the case
                  + [cyl(p, CASE_FOOT_R, cg.Z_BOT - CASE_FOOT_Z, top) for p in cg.FEET])
    full = place(block).cut(below).Solids[0]   # the wedge without its windows
    wedge = place(carve(block, [prism(w, z_low - 1, top + 1) for w in windows])).cut(below)
    assert len(wedge.Solids) == 1 and wedge.isValid()
    wedge = wedge.Solids[0]

    # The wedge's own feet: under the case's feet, pushed out to the edge of the base.
    base = one(Part.makeCompound([f for f in full.Faces if f.BoundBox.ZMax < 1e-6]))
    base.translate(V(0, 0, -base.BoundBox.ZMin))
    c = base.CenterOfMass
    def push(p, d):
        """p moved along d, in 0.5 mm steps, as far as a pad there stays on the base."""
        for _ in range(120):
            q = (p[0] + 0.5 * d[0], p[1] + 0.5 * d[1])
            if disc(q, PAD_R).cut(base).Area > 1e-6:
                break
            p = q
        return p

    feet = []
    for p in SEEDS:
        x = p[0] * math.cos(t) - (-dz - p[0] * math.sin(t)) * math.tan(t)   # where the case's own axis through p meets the desk
        assert disc((x, p[1]), PAD_R).cut(base).Area < 1e-6, "no room for a foot under %s" % (p,)
        r = math.dist((x, p[1]), (c.x, c.y))
        spot = push((x, p[1]), ((x - c.x) / r, (p[1] - c.y) / r))        # out from the middle,
        feet.append(push(spot, (math.copysign(1, x - c.x), 0)))          # then sideways to the edge
    wedge = add(wedge, [cyl(p, PAD_R, 0, 300).common(full) for p in feet])
    wedge = carve(wedge, [cyl(p, cg.FOOT_R, -0.1, cg.FOOT_Z) for p in feet])

    # Where a press on each key lands on the desk: straight down, and along the key's axis.
    pad = hull(feet)
    lands = []
    for k in keys:
        X, Y, Z = desk((k["x"], k["y"], PRESS_Z))
        lands += [(X, Y), (X + Z * math.tan(t), Y)]

    def outside(p):
        return 0.0 if in_polygon(p, pad) else min(seg_dist(p, a, b) for a, b in zip(pad, pad[1:] + pad[:1]))
    return wedge, {"place": place, "desk": desk, "feet": feet, "pad": pad, "outside": max(outside(p) for p in lands),
                   "low": desk((outer.BoundBox.XMin, 0, cg.Z_BOT))[2], "high": desk((outer.BoundBox.XMax, 0, cg.Z_BOT))[2]}


def main():
    path = OUT + "/wedge-report.txt"
    if os.path.exists(path):
        os.remove(path)
    tray = Part.read(OUT + "/left-tray.step").Solids[0]
    assert abs(tray.BoundBox.ZMin - cg.Z_BOT) < 1e-6
    # The tray's outline is the outside of the top step of its bottom chamfer. (Slicing the tray crashes OCCT.)
    z = cg.Z_BOT + cg.CHAMFER
    step = max((f for f in tray.Faces if abs(f.BoundBox.ZMin - z) < 1e-6 and abs(f.BoundBox.ZMax - z) < 1e-6),
               key=lambda f: f.BoundBox.DiagonalLength)
    outer = poly(thin([(v.X, v.Y) for v in step.OuterWire.OrderedVertexes], 0.02))
    say("WEDGE the tray's outline, %d points, from %s" % (len(outer.Edges), OUT + "/left-tray.step"))
    assert abs(outer.BoundBox.XLength - tray.BoundBox.XLength) < 0.05 and abs(outer.BoundBox.YLength - tray.BoundBox.YLength) < 0.05
    keys = cg.read_keys("left")
    bad = []
    os.makedirs(OUT + "/print", exist_ok=True)
    for angle in ANGLES:
        wedge, fig = build(outer, keys, angle)
        name = "wedge-%d" % angle

        def check(ok, text):
            say("WEDGE %2d %s %s" % (angle, "ok  " if ok else "FAIL", text))
            if not ok:
                bad.append("%s: %s" % (name, text))
        b = wedge.BoundBox
        check(wedge.isValid() and len(wedge.Solids) == 1 and abs(b.ZMin) < 1e-6,
              "one valid solid, %.1f cm3, %.1f x %.1f x %.1f mm" % (wedge.Volume / 1000, b.XLength, b.YLength, b.ZLength))
        check(max(b.XLength, b.YLength) < cg.BED - 10, "fits the %.0f mm bed" % cg.BED)
        over = wedge.common(fig["place"](tray)).Volume
        check(over < 1e-6, "the case sits in it without overlap (%.4f mm3)" % over)
        sunk = tray.copy()
        sunk.translate(V(0, 0, -0.05))
        area = wedge.common(fig["place"](sunk)).Volume / 0.05
        check(area > 2000, "the case's floor rests on %.0f mm2 of ledge and ribs" % area)
        held = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            moved = tray.copy()
            moved.translate(V(dx, dy, 0))
            held.append(wedge.common(fig["place"](moved)).Volume > 1e-3)
        check(all(held), "the rim stops the case sliding 1 mm in any of four directions")
        check(fig["outside"] < 1e-9, "a press on any key, straight down or along its axis, lands inside the feet"
              + ("" if fig["outside"] < 1e-9 else ": worst is %.1f mm outside" % fig["outside"]))
        whole = fig["place"](tray)
        cm = (whole.CenterOfMass * whole.Volume + wedge.CenterOfMass * wedge.Volume) * (1 / (whole.Volume + wedge.Volume))
        check(in_polygon((cm.x, cm.y), fig["pad"]), "centre of mass of tray and wedge is over the feet")
        say("WEDGE %2d the case's outer edge is %.1f mm above the desk, its inner edge %.1f mm; feet at %s" % (
            angle, fig["low"], fig["high"], ", ".join("(%.1f, %.1f)" % p for p in fig["feet"])))
        for side, s in (("left", wedge), ("right", wedge.mirror(V(0, 0, 0), V(1, 0, 0)))):
            s.exportStep("%s/%s-%s.step" % (OUT, side, name))
            mesh = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.02, AngularDeflection=math.radians(5))
            file = "%s/print/%s-%s.3mf" % (OUT, side, name)
            mesh.write(file)
            m = Mesh.Mesh(file)
            m.removeDuplicatedPoints()
            ok = m.isSolid() and abs(m.Volume - s.Volume) < 0.002 * s.Volume
            say("WEDGE %2d %s %s: %d facets, volume %.1f cm3" % (angle, "ok  " if ok else "FAIL", file, m.CountFacets, m.Volume / 1000))
            if not ok:
                bad.append(file)
    say("WEDGE RESULT: %s" % ("%d FAILURES" % len(bad) if bad else "all checks pass"))
    with open(path, "w") as f:
        f.write("\n".join(cg.LINES) + "\n")
    if bad:
        raise SystemExit(1)


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    raise
