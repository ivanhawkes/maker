"""Write the plan outlines of the KLP Lame keycap models, for tools/layout.py.

Run with FreeCADCmd from keyboard/, when a keycap model changes:

    FreeCADCmd tools/keycap_outlines.py

Writes layout/keycap-outlines.json: for each model, the convex hull of everything the cap
covers seen from above, in the model's own axes (mm, origin at the stem), and the model's
sha256 so layout.py can tell when this file is stale. The hull is of a mesh that follows the
model to 0.005 mm and is then thinned by up to 0.005 mm more, so it is inside the true
outline by at most 0.01 mm.
"""

import hashlib
import json
import math

import Part

KLP = "parts/3d/third-party/klp-lame/mx-stem-mx-size/MX_Stem_MX_Size_%s.step"
CAPS = ("Saddle", "Saddle_Tilted", "Saddle_Homing", "Thumb", "1.5U_Thumb_V")
OUT = "layout/keycap-outlines.json"
TOL = 0.005   # mm, for the mesh and again for the thinning


def hull(points):
    """Convex hull, counter-clockwise (Andrew's monotone chain)."""
    pts = sorted(set(points))

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return thin(h)[:-1]
    return half(pts) + half(reversed(pts))


def thin(line):
    """Drop the points that are within TOL of the line through those kept (Douglas-Peucker)."""
    if len(line) < 3:
        return line
    (ax, ay), (bx, by) = line[0], line[-1]
    far = [abs((bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax)) / math.hypot(bx - ax, by - ay) for p in line]
    i = max(range(len(line)), key=far.__getitem__)
    return [line[0], line[-1]] if far[i] <= TOL else thin(line[:i + 1])[:-1] + thin(line[i:])


def main():
    out = {}
    for kind in CAPS:
        path = KLP % kind
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        outline = hull([(round(v.x, 3), round(v.y, 3)) for v in Part.read(path).tessellate(TOL)[0]])
        xs, ys = [p[0] for p in outline], [p[1] for p in outline]
        assert len(outline) >= 8 and min(xs) < -8 and max(xs) > 8 and min(ys) < -8 and max(ys) > 8, "%s: not a keycap's outline" % kind
        out[kind] = {"sha256": digest, "outline": outline}
        print("KEYCAP %-14s %3d points, %.3f x %.3f mm" % (kind, len(outline), max(xs) - min(xs), max(ys) - min(ys)))
    with open(OUT, "w") as f:
        f.write("{\n" + ",\n".join('"%s": %s' % (k, json.dumps(v)) for k, v in out.items()) + "\n}\n")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    import os
    os._exit(1)   # FreeCADCmd otherwise exits with 0
