"""Generate the retro case (keyboard 2) for both halves, check it, and export it to cad/case-retro/.

Run with FreeCADCmd from keyboard/, after tools/case_board.py has written the board data:

    FreeCADCmd tools/case_retro_generate.py

The insides are keyboard 1's, built by tools/case_generate.py and not changed: the board
cavity, posts, battery bay, plate, dovetail and screw positions. This file wraps them in
another shell (docs/case-retro.md has the drawing and the reasons):

    tray    keyboard 1's tray inside a 6 mm thicker body with 10 mm corners and a rolled top edge
    plate   keyboard 1's plate, printed in the accent colour
    lid     the hood: keyboard 1's lid inside a taller body with a rolled edge and louvre grooves
    plinth  a raked base under the tray, 6 degrees, far edge high; a recessed stripe round its top
    stripe  an optional ring in the accent colour that fills the stripe

Six screws a half from below, through the plinth: four M3 x 16 (lid) and two M3 x 12 (plate).
Coordinates are keyboard 1's: the layout's plan, z = 0 at the board's top face. The plinth is
also written in desk coordinates (the desk is z = 0), which is how it prints.
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
from case_generate import (V, say, poly, disc, grow, one, prism, cyl, carve, add, hull, in_polygon, seg_dist, thin,  # noqa: E402
                           Z_BOT, PLATE_TOP, LID_CEIL, WALL, LAYER)

OUT = "cad/case-retro"

EXTRA = 6.0          # the body stands this far outside keyboard 1's tray, all round
R_CONCAVE = 10.0     # radius of the outline's inside corners; its outside corners come to WALL + EXTRA
OVERLAP = 1.5        # the new body reaches this far into keyboard 1's walls, so the two fuse
ROLL_R = 6.0         # rolled edge: an arc from 45 degrees to upright, so it prints on the bed without support
HOOD_TOP = 12.0      # keyboard 1's lid ends at 8.6; the keycaps' tops are at about 18
GROOVE_W, GROOVE_Z, GROOVE_PITCH = 2.0, 0.8, 5.0
GROOVE_Y = (-50.0, -6.0)     # the louvres lie over the battery
GROOVE_IN = 6.0              # and stop this far inside the hood's outline
SCOOP = 18.0         # finger notch through the body at the power switch: this far along the inner edge from its far end
USB_FLARE = 3.0      # the USB tunnel is this much wider through the new body

RAKE = 6.0           # degrees, far edge high (owner, 2026-11-23)
T_MIN = 3.5          # the plinth's thickness at its near edge
STRIPE_H, STRIPE_D = 2.0, 1.4
RING_FIT = 0.2
LEDGE = 7.0          # the tray rests on this much of the plinth round its edge, and on the ribs
RIB, RIB_PITCH_X, RIB_PITCH_Y = 2.4, 40.0, 30.0
PAD_R = 6.5          # solid round each screw and under each foot
SEEDS = cg.FEET + ((40.0, 40.0),)
SCREW_LID, SCREW_PLATE = 16.0, 12.0   # keyboard 1's screws, 4 mm longer, to pass through the plinth
HEAD_Z = 2.4         # room a screw head needs
PRESS_Z = PLATE_TOP + 9.0


def roll(face, z, up):
    """Rings that round the edge of a solid's end face at z, a print layer at a time (see cg.bevel)."""
    wide, rings = grow(face, 1.0), []
    for k in range(math.ceil(ROLL_R * math.sin(math.pi / 4) / LAYER)):
        c = math.cos(math.pi / 4) - LAYER * (k + 0.5) / ROLL_R
        inset = ROLL_R * (1 - math.sqrt(1 - c * c)) if c > 0 else 0
        if inset < 0.02:
            break
        a, b = sorted((z + up * LAYER * k, z + up * LAYER * (k + 1)))
        rings.append(prism(wide, a, b).cut(prism(grow(face, -inset), a, b)))
    return rings


def shave(solid, tools):
    """Cut all the tools at once; the result must be one valid, smaller solid."""
    out = solid.cut(tools)
    assert out.isValid() and len(out.Solids) == 1 and out.Volume < solid.Volume - 1e-6, "a cut broke the solid"
    return out.Solids[0]


def build(parts, fig, keys):
    """The retro parts of the left half in keyboard 1's coordinates, the plinth as it prints, and figures."""
    outer, inner, lid_face, keyside, tunnel = fig["outer"], fig["inner"], fig["lid face"], fig["keyside"], fig["tunnel"]
    sw, rst, u1 = fig["switch"], fig["reset"], fig["u1"]
    shell = one(grow(one(grow(fig["core"], WALL + EXTRA + R_CONCAVE)), -R_CONCAVE))
    shell = poly(thin([(v.X, v.Y) for v in shell.OuterWire.OrderedVertexes], 0.02))
    hood_face = one(shell.cut(keyside))
    top = HOOD_TOP + 1

    flare = poly([(u1[0] - cg.USB_W / 2 - USB_FLARE / 2, u1[1] + cg.USB_FROM), (u1[0] + cg.USB_W / 2 + USB_FLARE / 2, u1[1] + cg.USB_FROM),
                  (u1[0] + cg.USB_W / 2 + USB_FLARE / 2, u1[1] + 100), (u1[0] - cg.USB_W / 2 - USB_FLARE / 2, u1[1] + 100)])
    flare = one(flare.common(shell).cut(outer))                                   # the wider part, outside keyboard 1's wall
    # The notch starts where the inner edge does, so it leaves the body's rounded far corner whole.
    assert 0 < sw - cg.SLOT / 2 and sw + cg.SLOT / 2 < SCOOP < cg.LOBE_S0
    scoop = inner.box(0, SCOOP, WALL, WALL + EXTRA + 30)                          # outside keyboard 1's wall, to the open air
    scallop = inner.box(0, sw + cg.SCALLOP / 2, cg.SCALLOP_D, WALL + 1)           # keyboard 1's own recess, within the notch

    # Tray: keyboard 1's tray in a thicker body. The top edge is rolled where the hood does not sit.
    under_hood = prism(hood_face, Z_BOT - 1, top)
    body = prism(shell, Z_BOT, PLATE_TOP).cut(prism(grow(outer, -OVERLAP), Z_BOT - 1, top))
    body = shave(body, [r.cut(under_hood) for r in roll(shell, PLATE_TOP, -1)])
    tray = add(parts["tray"], [body]
               # the screw heads move down into the plinth: fill keyboard 1's head recesses
               + [cyl(p, cg.HEAD_R + 0.4, Z_BOT, seat + cg.SKIN + 0.05) for p, seat, _ in fig["seats"]])
    tray = carve(tray, [cyl(p, cg.CLEAR_R, Z_BOT - 1, seat + cg.SKIN + 0.1) for p, seat, _ in fig["seats"]]
                 + [prism(tunnel, cg.USB_Z0, top), prism(flare, cg.USB_Z0, top),
                    prism(scallop, -1.5, top), prism(scoop, -1.5, top)])

    # Hood: keyboard 1's lid in a taller body.
    body = shave(prism(hood_face, PLATE_TOP, HOOD_TOP), roll(hood_face, HOOD_TOP, -1))
    body = body.cut(prism(grow(lid_face, -OVERLAP), PLATE_TOP - 1, LID_CEIL + 0.5))
    hood = add(parts["lid"], [body])
    field = grow(hood_face, -GROOVE_IN).cut(inner.box(-4, SCOOP + 4, 0, 60))
    b = hood_face.BoundBox
    grooves = []
    y = GROOVE_Y[0]
    while y <= GROOVE_Y[1]:
        bar = poly([(b.XMin - 1, y - GROOVE_W / 2), (b.XMax + 1, y - GROOVE_W / 2), (b.XMax + 1, y + GROOVE_W / 2), (b.XMin - 1, y + GROOVE_W / 2)])
        grooves += [f for f in bar.common(field).Faces if f.Area > 3 * GROOVE_W]
        y += GROOVE_PITCH
    assert all(f.distToShape(disc(rst, cg.RESET_R))[0] > 3 for f in grooves), "a groove is at the reset hole"
    hood = carve(hood, [cyl(rst, cg.RESET_R, LID_CEIL - 1, top), prism(tunnel, PLATE_TOP - 1, LID_CEIL),
                        prism(flare, PLATE_TOP - 1, LID_CEIL), prism(scoop, PLATE_TOP - 1, top)]
                 + [prism(f, HOOD_TOP - GROOVE_Z, top) for f in grooves])

    # Plinth: built under the tray, square to it, then turned so the desk is z = 0.
    t = math.radians(RAKE)
    sb = shell.BoundBox
    dz = T_MIN - (sb.YMin * math.sin(t) + Z_BOT * math.cos(t))

    def place(shape, back=False):
        s = shape.copy()
        if back:
            s.translate(V(0, 0, -dz))
            s.rotate(V(0, 0, 0), V(1, 0, 0), -RAKE)
        else:
            s.rotate(V(0, 0, 0), V(1, 0, 0), RAKE)
            s.translate(V(0, 0, dz))
        return s

    def desk(p):
        return (p[0], p[1] * math.cos(t) - p[2] * math.sin(t), p[1] * math.sin(t) + p[2] * math.cos(t) + dz)

    def landing(p):
        """Where keyboard 1's z axis through the plan point p meets the desk."""
        return (p[0], p[1] / math.cos(t) + dz * math.tan(t))

    def push(p, d):
        for _ in range(160):
            q = (p[0] + 0.5 * d[0], p[1] + 0.5 * d[1])
            if disc(q, PAD_R).cut(shell).Area > 1e-6:
                break
            p = q
        return p
    c = shell.CenterOfMass
    feet = []
    for p in SEEDS:
        r = math.dist(p, (c.x, c.y))
        feet.append(push(push(p, ((p[0] - c.x) / r, (p[1] - c.y) / r)), (math.copysign(1, p[0] - c.x), 0)))
    seats = [(p, seat - (SCREW_LID - cg.SCREW_LID if seat == cg.SEAT_LID else SCREW_PLATE - cg.SCREW_PLATE)) for p, seat, _ in fig["seats"]]

    z_low = Z_BOT - (sb.YLength * math.tan(t) + T_MIN + 5)
    ribs = [poly([(sb.XMin - 1, y - RIB / 2), (sb.XMax + 1, y - RIB / 2), (sb.XMax + 1, y + RIB / 2), (sb.XMin - 1, y + RIB / 2)])
            for y in [sb.YMin + RIB_PITCH_Y * k for k in range(1, int(sb.YLength / RIB_PITCH_Y) + 1)]]
    ribs += [poly([(x - RIB / 2, sb.YMin - 1), (x + RIB / 2, sb.YMin - 1), (x + RIB / 2, sb.YMax + 1), (x - RIB / 2, sb.YMax + 1)])
             for x in [sb.XMin + RIB_PITCH_X * k for k in range(1, int(sb.XLength / RIB_PITCH_X) + 1)]]
    ribs += [poly([(sb.XMin - 1, p[1] - RIB / 2), (sb.XMax + 1, p[1] - RIB / 2), (sb.XMax + 1, p[1] + RIB / 2), (sb.XMin - 1, p[1] + RIB / 2)])
             for p, _ in seats]   # one through each screw, so its pad is not an island
    windows = [f for f in grow(shell, -LEDGE).cut(ribs + [disc(p, PAD_R) for p in feet] + [disc(p, PAD_R) for p, _ in seats]).Faces
               if f.Area > 4]
    band = one(shell.cut(grow(shell, -STRIPE_D)))
    block = carve(prism(shell, z_low, Z_BOT), [prism(band, Z_BOT - STRIPE_H, Z_BOT + 1)]
                  + [prism(w, z_low - 1, Z_BOT + 1) for w in windows]
                  + [cyl(p, cg.HEAD_R, z_low - 1, seat) for p, seat in seats]
                  + [cyl(p, cg.CLEAR_R, seat + cg.SKIN, Z_BOT + 1) for p, seat in seats])
    printed = place(block).cut(Part.makeBox(800, 800, 200, V(-400, -400, -200)))
    assert printed.isValid() and len(printed.Solids) == 1
    printed = carve(printed.Solids[0], [cyl(landing(p), cg.FOOT_R, -0.1, cg.FOOT_Z) for p in feet])
    base = poly([landing((v.X, v.Y)) for v in shell.OuterWire.OrderedVertexes])   # the plinth's outline on the desk
    printed = cg.bevel(printed, base, 0, 1)
    plinth = place(printed, back=True)

    ring = prism(one(shell.cut(grow(shell, -(STRIPE_D - RING_FIT)))), Z_BOT - STRIPE_H + RING_FIT, Z_BOT)

    pad = hull([landing(p) for p in feet])
    lands = []
    for k in keys:
        x, y, _ = desk((k["x"], k["y"], PRESS_Z))
        lands += [(x, y), landing((k["x"], k["y"]))]

    def outside(p):
        return 0.0 if in_polygon(p, pad) else min(seg_dist(p, a, b) for a, b in zip(pad, pad[1:] + pad[:1]))
    figures = {
        "shell": shell, "printed": printed, "grooves": len(grooves), "outside": max(outside(p) for p in lands),
        "head room": min(desk((p[0], p[1], seat))[2] for p, seat in seats),
        "webs": sorted({round(Z_BOT - seat, 2) for _, seat in seats}),
        "near": desk((0, sb.YMin, PLATE_TOP))[2], "far": desk((0, sb.YMax, PLATE_TOP))[2], "hood": desk((0, sb.YMax, HOOD_TOP))[2],
        "feet": [landing(p) for p in feet],
    }
    return {"tray": tray, "plate": parts["plate"], "lid": hood, "plinth": plinth, "stripe": ring}, figures


def main():
    os.makedirs(OUT + "/print", exist_ok=True)
    path = OUT + "/report.txt"
    if os.path.exists(path):
        os.remove(path)
    left, right = cg.read_board("left"), cg.read_board("right")
    cg.check_mirror(left, right)
    keys = cg.read_keys("left")
    first, fig = cg.build(keys, left, right)
    parts, rf = build(first, fig, keys)
    inner = fig["inner"]
    flip = cg.Frame((-inner.p0[0], inner.p0[1]), (-inner.at(inner.length, 0)[0], inner.at(inner.length, 0)[1]), (0, 0))

    def mirror(s):
        return s.mirror(V(0, 0, 0), V(1, 0, 0))
    halves = {"left": parts, "right": {n: mirror(s) for n, s in parts.items()}}
    printed = {"left": rf["printed"], "right": mirror(rf["printed"])}
    bad = []

    def check(ok, text):
        say("RETRO %s %s" % ("ok  " if ok else "FAIL", text))
        if not ok:
            bad.append(text)
    for side, board, frame in (("left", left, inner), ("right", right, flip)):
        env, caps = cg.envelopes(cg.read_keys(side), board, frame)
        bad += cg.report(side, halves[side], env, caps)
    b = rf["shell"].BoundBox
    say("RETRO size: %.1f x %.1f mm in plan; rake %.0f degrees; plate's top %.1f mm above the desk at the near edge, %.1f at the far edge; hood %.1f" % (
        b.XLength, b.YLength, RAKE, rf["near"], rf["far"], rf["hood"]))
    check(rf["grooves"] >= 6, "the hood has %d louvre grooves" % rf["grooves"])
    check(rf["head room"] >= HEAD_Z + 0.2, "every screw head has at least %.1f mm of recess in the plinth, on a web of %s mm" % (
        rf["head room"], " or ".join("%.1f" % w for w in rf["webs"])))
    check(rf["outside"] < 1e-9, "a press on any key, straight down or along its axis, lands inside the plinth's feet"
          + ("" if rf["outside"] < 1e-9 else ": worst is %.1f mm outside" % rf["outside"]))
    p = rf["printed"].optimalBoundingBox(False, False)   # BoundBox is loose round the leaning screw holes
    check(rf["printed"].isValid() and abs(p.ZMin) < 1e-6 and max(p.XLength, p.YLength) < cg.BED - 10,
          "the plinth as printed: %.1f x %.1f x %.1f mm, flat on the desk" % (p.XLength, p.YLength, p.ZLength))
    say("RETRO plinth feet at %s" % ", ".join("(%.1f, %.1f)" % q for q in rf["feet"]))

    for side, ps in halves.items():
        doc = FreeCAD.newDocument("retro_" + side)
        for name, s in ps.items():
            s.exportStep("%s/%s-%s.step" % (OUT, side, name))
            doc.addObject("Part::Feature", name).Shape = s
            q = printed[side].copy() if name == "plinth" else s.copy()
            if name in ("plate", "lid"):
                q.rotate(V(0, 0, 0), V(1, 0, 0), 180)   # top face down
            if name != "plinth":   # which already stands on z = 0
                q.translate(V(0, 0, -q.BoundBox.ZMin))
            mesh = MeshPart.meshFromShape(Shape=q, LinearDeflection=0.02, AngularDeflection=math.radians(5))
            file = "%s/print/%s-%s.3mf" % (OUT, side, name)
            mesh.write(file)
            m = Mesh.Mesh(file)
            m.removeDuplicatedPoints()
            ok = m.isSolid() and abs(m.Volume - s.Volume) < 0.002 * s.Volume
            say("RETRO %-5s %s %s: %d facets, volume %.1f cm3" % (side, "ok  " if ok else "FAIL", file, m.CountFacets, m.Volume / 1000))
            if not ok:
                bad.append(file)
        env, caps = cg.envelopes(cg.read_keys(side), left if side == "left" else right, inner if side == "left" else flip)
        doc.addObject("Part::Feature", "board_and_parts").Shape = Part.makeCompound(list(env.values()))
        doc.addObject("Part::Feature", "keycaps").Shape = Part.makeCompound(caps)
        doc.recompute()
        file = "%s/%s-case.FCStd" % (OUT, side)
        if os.path.exists(file):
            os.remove(file)
        doc.saveAs(file)
        FreeCAD.closeDocument(doc.Name)
    say("RETRO RESULT: %s" % ("%d FAILURES" % len(bad) if bad else "all checks pass"))
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
