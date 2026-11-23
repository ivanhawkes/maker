"""Generate the dongle's case, check it, and export it to cad/dongle/.

Run with FreeCADCmd from keyboard/:

    FreeCADCmd tools/dongle_generate.py

Two printed parts (docs/dongle-case.md has the drawing and the reasons):

    base  a plate carrying the bare nice!nano, flat, and four pillars the display rests on
    top   the walls and a face sloped at 30 degrees with the display's window; four M3 x 8 from below

The dongle is hand-wired: four wires from the controller's pads to the display's header. There
is no board. x is across, y runs from the front (-) to the USB end (+), z = 0 is the base's top.
Sloped things are built in (u, v, w): u = x, v up the slope from the front inner wall, w out of
the face, w = 0 at the face's underside. Every size is from a product page or a common listing,
not from a measured part.
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
from case_generate import V, say, poly, grow, prism, cyl, carve, add  # noqa: E402

OUT = "cad/dongle"
SLOPE = 30.0
T = math.tan(math.radians(SLOPE))
C = math.cos(math.radians(SLOPE))

# Outside, mm.
HALF_W, WALL = 19.0, 2.0
Y_FRONT, Y_BACK = -48.0, 2.3          # outer faces; the inner faces are a wall in from these
PLATE_T = 3.4
FACE_T = 1.8
Z_FRONT = 6.0                         # the face's underside at the front inner wall
R_CORNER = 3.0

# nice!nano v2: 17.78 x 33.02 x 1.6, 3.2 thick over its mid-mount USB-C (nicekeyboards.com).
# y = 0 is its USB end.
NANO_HW, NANO_L, NANO_T = 9.1, 33.3, 1.6   # half width and length, with slack
NANO_Z = 3.4                               # its underside: wire ends and the plug's overmould clear the base
USB_W, USB_Z = 13.0, (0.2, 8.2)            # opening for a plug's overmould

# Display: the common 0.96 in 128 x 64 SSD1306 I2C module, taken as 27.8 x 27.8, 3.2 thick with
# its glass, a four-pin header at the top edge with its pins out of the back.
OLED, OLED_T, OLED_FIT = 27.8, 3.2, 0.3
OLED_Y = -32.0                             # plan position of its lower edge
OLED_V = (OLED_Y - (Y_FRONT + WALL)) / C   # the same, up the slope
WINDOW = (25.0, 16.0)                      # across, up the slope; centred on the module
REST, FENCE = OLED_T + 0.4, 0.6            # pillar tops, as depths under the face

# Screws: M3 x 8 from below, as in the keyboard case.
SCREW = 8.0
SEAT = -1.0
SCREWS = ((13.6, -42.5), (13.6, -3.1))     # and mirrored
BLOCK_Z = 9.0
FEET = ((5.6, -38.5), (5.6, -7.5))         # and mirrored


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def both(solids):
    """Each solid and its mirror image in x."""
    return [s for a in solids for s in (a, a.mirror(V(0, 0, 0), V(1, 0, 0)))]


def side(pts, x0, x1):
    """A solid from a (y, z) profile, between x0 and x1."""
    w = [V(x0, y, z) for y, z in pts]
    return Part.Face(Part.makePolygon(w + [w[0]])).extrude(V(x1 - x0, 0, 0))


def sloped(u0, u1, v0, v1, w0, w1):
    """A box given in the face's coordinates."""
    s = box(u0, u1, v0, v1, w0, w1)
    s.rotate(V(0, 0, 0), V(1, 0, 0), SLOPE)
    s.translate(V(0, Y_FRONT + WALL, Z_FRONT))
    return s


def under(y):
    return Z_FRONT + (y - (Y_FRONT + WALL)) * T


def build():
    plan = grow(poly([(-HALF_W + R_CORNER, Y_FRONT + R_CORNER), (HALF_W - R_CORNER, Y_FRONT + R_CORNER),
                      (HALF_W - R_CORNER, Y_BACK - R_CORNER), (-HALF_W + R_CORNER, Y_BACK - R_CORNER)]), R_CORNER)
    yi0, yi1, xi = Y_FRONT + WALL, Y_BACK - WALL, HALF_W - WALL
    lift = FACE_T / C

    # Top.
    outer = prism(plan, 0, 80).common(side([(Y_FRONT - 1, 0), (Y_BACK + 1, 0), (Y_BACK + 1, under(Y_BACK + 1) + lift),
                                            (Y_FRONT - 1, under(Y_FRONT - 1) + lift)], -HALF_W - 1, HALF_W + 1))
    top = carve(outer, [side([(yi0, -1), (yi1, -1), (yi1, under(yi1)), (yi0, under(yi0))], -xi, xi)])
    # Screw blocks in the corners. The front ones end in a 45 degree face: the top prints standing on its back.
    front = prism(poly([(xi + 0.5, yi0 - 0.5), (10.1, yi0 - 0.5), (10.1, yi0 + 6.9), (xi + 0.5, yi0 + 14.3)]), 0, BLOCK_Z)
    blocks = both([front, box(10.1, xi + 0.5, yi1 - 7.3, yi1 + 0.5, 0, BLOCK_Z),
                   # ledges over the controller's corners beside the USB connector
                   box(6.6, 12.0, yi1 - 2.5, yi1 + 0.5, NANO_Z + NANO_T + 0.3, NANO_Z + NANO_T + 2.5)])
    top = add(top, [b.common(outer) for b in blocks])
    vc = OLED_V + OLED / 2
    top = carve(top, [sloped(-WINDOW[0] / 2, WINDOW[0] / 2, vc - WINDOW[1] / 2, vc + WINDOW[1] / 2, -1, FACE_T + 1),
                      box(-USB_W / 2, USB_W / 2, yi1 - 0.1, Y_BACK + 1, -1, USB_Z[1])]
                + both([cyl(p, cg.PILOT_R, -0.1, SEAT + SCREW + 0.2) for p in SCREWS]))

    # Base.
    def column(x0, x1, y0, y1, depth):
        return box(x0, x1, y0, y1, -0.1, 80).common(sloped(-40, 40, -30, 90, -90, -depth))
    edge = OLED / 2 + OLED_FIT                       # the display's side edge, with its fit
    y_top = OLED_Y + OLED * C                        # plan position of the display's upper edge
    pillars = both([
        column(10.9, edge, OLED_Y + 0.2, OLED_Y + 4.5, REST),           # under the lower corner
        column(10.9, edge, OLED_Y - 2.0, OLED_Y - OLED_FIT, FENCE),      # stop: the display cannot slide down the slope
        column(edge, xi - 0.4, OLED_Y, OLED_Y + 4.5, FENCE),             # fence beside it
        column(10.9, edge, y_top - 5.1, y_top - 0.7, REST),             # under the upper corner
        column(edge, xi - 0.4, y_top - 5.1, y_top - 0.7, FENCE),
    ])
    base = add(prism(plan, -PLATE_T, 0), [
        box(-5.5, 5.5, -NANO_L, -9.0, -0.1, NANO_Z),                     # the controller lies on this, between its pin rows
        box(-6.0, 6.0, -NANO_L - 2.5, -NANO_L, -0.1, NANO_Z + NANO_T + 1.0),   # front stop
    ] + both([box(NANO_HW + 0.2, NANO_HW + 2.2, -30.0, -22.0, -0.1, NANO_Z + NANO_T + 0.5)]) + pillars)
    base = carve(base, both([cyl(p, cg.HEAD_R, -PLATE_T - 0.1, SEAT) for p in SCREWS]
                            + [cyl(p, cg.CLEAR_R, SEAT + cg.SKIN, 0.1) for p in SCREWS]
                            + [cyl(p, cg.FOOT_R, -PLATE_T - 0.1, -PLATE_T + cg.FOOT_Z) for p in FEET]))

    # What goes inside, as blocks.
    env = {
        "controller board": box(-NANO_HW + 0.2, NANO_HW - 0.2, -NANO_L + 0.3, 0, NANO_Z, NANO_Z + NANO_T),
        "controller parts": box(-6.2, 6.2, -NANO_L + 0.8, 0, NANO_Z + NANO_T, NANO_Z + NANO_T + 1.6),
        "USB connector": box(-4.6, 4.6, -7.0, 1.5, NANO_Z - 0.8, NANO_Z + NANO_T + 0.8),
        "USB plug": box(-6.25, 6.25, 0.0, 20.0, NANO_Z + NANO_T / 2 - 3.5, NANO_Z + NANO_T / 2 + 3.5),
        "display": sloped(-OLED / 2, OLED / 2, OLED_V, OLED_V + OLED, -OLED_T, -0.05),
        "display header": sloped(-5.1, 5.1, OLED_V + OLED - 3.0, OLED_V + OLED - 0.4, -OLED_T - 8.5, -OLED_T),
    }
    return {"base": base, "top": top}, env


def main():
    os.makedirs(OUT + "/print", exist_ok=True)
    report = OUT + "/report.txt"
    if os.path.exists(report):
        os.remove(report)
    parts, env = build()
    bad = []

    def check(ok, text):
        say("DONGLE %s %s" % ("ok  " if ok else "FAIL", text))
        if not ok:
            bad.append(text)
    for name, s in parts.items():
        b = s.BoundBox
        check(s.isValid() and len(s.Solids) == 1, "%s: one valid solid, %.1f cm3, %.1f x %.1f x %.1f mm" % (
            name, s.Volume / 1000, b.XLength, b.YLength, b.ZLength))
        hits = [n for n, e in env.items() if s.common(e).Volume > 1e-6]
        check(not hits, "%s clears the controller, the display and a plug%s" % (name, ": hits " + ", ".join(hits) if hits else ""))
    check(parts["base"].common(parts["top"]).Volume < 1e-6, "base and top do not overlap")
    gap = parts["base"].distToShape(env["display"])[0]
    check(0.3 < gap < 0.5, "the display's back is %.2f mm above the pillars" % gap)
    held = env["display"].copy()
    held.translate(V(0, -1.0, -1.0 * T))   # 1 mm down the slope
    check(parts["base"].common(held).Volume > 1e-3, "the stops keep the display from sliding down the slope")
    side_ = env["display"].copy()
    side_.translate(V(1.0, 0, 0))
    check(parts["base"].common(side_).Volume > 1e-3, "the fences keep the display from moving sideways")
    lifted = env["controller board"].copy()
    lifted.translate(V(0, 0, 1.0))
    check(parts["top"].common(lifted).Volume > 1e-3, "the top's ledges hold the controller's USB end down")
    pulled = env["controller board"].copy()
    pulled.translate(V(0, 1.0, 0))
    check(parts["top"].common(pulled).Volume > 1e-3, "the back wall takes the pull of unplugging")
    b = parts["top"].BoundBox
    say("DONGLE size: %.1f x %.1f mm in plan, %.1f mm high; face at %.0f degrees; window %.0f x %.0f mm" % (
        b.XLength, b.YLength, b.ZMax + PLATE_T, SLOPE, WINDOW[0], WINDOW[1]))
    for name, s in parts.items():
        s.exportStep("%s/%s.step" % (OUT, name))
        p = s.copy()
        if name == "top":
            p.rotate(V(0, 0, 0), V(1, 0, 0), -90)   # standing on its back wall
        p.translate(V(0, 0, -p.BoundBox.ZMin))
        mesh = MeshPart.meshFromShape(Shape=p, LinearDeflection=0.02, AngularDeflection=math.radians(5))
        path = "%s/print/%s.3mf" % (OUT, name)
        mesh.write(path)
        m = Mesh.Mesh(path)
        m.removeDuplicatedPoints()
        ok = m.isSolid() and abs(m.Volume - s.Volume) < 0.002 * s.Volume
        check(ok, "%s: %d facets, volume %.1f cm3" % (path, m.CountFacets, m.Volume / 1000))
    doc = FreeCAD.newDocument("dongle")
    for name, s in list(parts.items()) + [("contents", Part.makeCompound(list(env.values())))]:
        doc.addObject("Part::Feature", name).Shape = s
    doc.recompute()
    path = OUT + "/dongle.FCStd"
    if os.path.exists(path):
        os.remove(path)
    doc.saveAs(path)
    say("DONGLE RESULT: %s" % ("%d FAILURES" % len(bad) if bad else "all checks pass"))
    with open(report, "w") as f:
        f.write("\n".join(cg.LINES) + "\n")
    if bad:
        raise SystemExit(1)


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    raise
