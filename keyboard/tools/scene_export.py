"""Convert the cases, the keycaps and a switch to meshes for the Blender scenes.

Run with FreeCADCmd from keyboard/, after the case generators:

    FreeCADCmd tools/scene_export.py

Blender has no STEP import, so this writes STL meshes and a manifest to cad/scenes/build/
(not kept in git) for tools/scene_build.py. Everything stays in the cases' coordinates: the
layout's plan, z = 0 at the board's top face, millimetres.
"""

import json
import math
import os
import re
import sys

import FreeCAD
import MeshPart
import Part

FreeCAD.case_as_library = True
sys.path.insert(0, "tools")
import case_generate as cg          # noqa: E402
import case_retro_generate as retro  # noqa: E402

V = FreeCAD.Vector
OUT = "cad/scenes/build"
KLP = "parts/3d/third-party/klp-lame/mx-stem-mx-size/MX_Stem_MX_Size_%s.step"
CAPS = ("Saddle", "Saddle_Tilted", "Saddle_Homing", "Thumb", "1.5U_Thumb_V")
SWITCH = "parts/3d/third-party/SW_Cherry_MX_PCB.step"   # kiswitch's model: z = 0 is the board's top
SWITCH_PARTS = {"bottom": (0,), "top": (1,), "stem": (2, 6), "metal": (3, 4)}   # solid 5 is the spring: a million facets nobody sees


def mesh(shape, name, lin=0.03, ang=8.0):
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=lin, AngularDeflection=math.radians(ang))
    m.write("%s/%s.stl" % (OUT, name))
    return m.CountFacets


def box(s):
    b = s.BoundBox
    return [b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax]


def main():
    os.makedirs(OUT, exist_ok=True)
    man = {"z_bot": cg.Z_BOT, "caps": {}, "left": {}, "right": {}}
    count = 0

    for side in ("left", "right"):
        for kb, folder, names in (("kb1", "cad/case", ("tray", "plate", "lid")),
                                  ("retro", "cad/case-retro", ("tray", "plate", "lid", "plinth", "stripe"))):
            for n in names:
                s = Part.read("%s/%s-%s.step" % (folder, side, n))
                count += mesh(s, "%s-%s-%s" % (kb, side, n))
                if (kb, n) == ("retro", "tray"):
                    man[side]["retro_ymin"] = s.BoundBox.YMin
        # The board, the cell and the controller, as the case generator's own check blocks.
        doc = FreeCAD.openDocument("cad/case/%s-case.FCStd" % side)
        solids = doc.getObject("board_and_parts").Shape.Solids
        flat = [s for s in solids if abs(s.BoundBox.ZMin + cg.PCB_T) < 1e-6 and abs(s.BoundBox.ZMax) < 1e-6]
        count += mesh(max(flat, key=lambda s: s.Volume), "%s-board" % side)
        cell = [s for s in solids if abs(s.BoundBox.ZMin - cg.Z_FLOOR) < 1e-6 and abs(s.BoundBox.ZLength - cg.CELL[2]) < 1e-6]
        u1 = [s for s in solids if abs(s.BoundBox.ZMin) < 1e-6 and abs(s.BoundBox.ZMax - 6.5) < 1e-6]
        assert len(cell) == 1 and len(u1) == 1, "cannot find the cell or the controller in %s" % doc.Name
        man[side]["cell"], man[side]["controller"] = box(cell[0]), box(u1[0])
        FreeCAD.closeDocument(doc.Name)

    # Keycaps: where the hole for the switch's stem ends decides how high the cap sits.
    for kind in CAPS:
        s = Part.read(KLP % kind)
        b = s.BoundBox
        cx, cy = (b.XMin + b.XMax) / 2 + 0.3, (b.YMin + b.YMax) / 2 + 0.3
        hits = sorted({round(v.Z, 3) for v in s.section(Part.makeLine(V(cx, cy, b.ZMax + 5), V(cx, cy, b.ZMin - 5))).Vertexes}, reverse=True)
        assert len(hits) == 2, "%s: expected the top and the stem hole's end under the centre, got %s" % (kind, hits)
        man["caps"][kind] = {"ceiling": hits[1], "box": box(s)}
        count += mesh(s, "cap-%s" % kind, lin=0.03, ang=6.0)

    solids = Part.read(SWITCH).Solids
    assert len(solids) == 7
    for name, picks in SWITCH_PARTS.items():
        count += mesh(Part.makeCompound([solids[i] for i in picks]), "switch-%s" % name, lin=0.02, ang=6.0)
    man["switch"] = {"stem_top": solids[2].BoundBox.ZMax, "housing_top": solids[1].BoundBox.ZMax}

    # Screws: positions from the case report; lengths and head seats from the generators.
    with open("cad/case/report.txt") as f:
        line = next(x for x in f if "screws at" in x)
    at = [(float(a), float(b)) for a, b in re.findall(r"\((-?[\d.]+), (-?[\d.]+)\)", line.split("screws at")[1].split(";")[0])]
    assert len(at) == 6
    lid = (True, True, False, False, True, True)   # the lobe's two, then H1 and H2 (plate), then H3 and H4
    man["kb1"] = {"screws": [{"at": p, "seat": cg.SEAT_LID if l else cg.SEAT_PLATE, "length": cg.SCREW_LID if l else cg.SCREW_PLATE}
                             for p, l in zip(at, lid)]}
    man["retro"] = {"rake": retro.RAKE, "t_min": retro.T_MIN,
                    "screws": [{"at": p, "seat": (cg.SEAT_LID + cg.SCREW_LID - retro.SCREW_LID) if l else (cg.SEAT_PLATE + cg.SCREW_PLATE - retro.SCREW_PLATE),
                                "length": retro.SCREW_LID if l else retro.SCREW_PLATE} for p, l in zip(at, lid)]}
    with open(OUT + "/manifest.json", "w") as f:
        json.dump(man, f, indent=1)
    with open(OUT + "/done.txt", "w") as f:
        f.write("%d facets\n" % count)


try:
    main()
except Exception:
    import traceback
    with open(OUT + "/error.txt", "w") as f:
        traceback.print_exc(file=f)
    raise
