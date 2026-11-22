"""Read-only extraction of switch cutouts from a FreeCAD sketch.

Run with FreeCADCmd (not the normal Python interpreter):

    LAYOUT_FCSTD=prototype/left-hand/test-pad.fcstd LAYOUT_SKETCH=Sketch \
        FreeCADCmd tools/freecad_extract.py

FreeCAD prints its own messages to stdout, so the result is written as a single
line prefixed with ``LAYOUT_JSON:``. The document is opened and closed without
saving. Each closed loop shorter than ``MAX_CUTOUT_PERIMETER`` mm is treated as
a switch cutout; the longest loop is reported as the outline.
"""

import json
import math
import os

import FreeCAD
import Part

MAX_CUTOUT_PERIMETER = 100.0  # mm; a 14 mm square cutout has a 56 mm perimeter


def loop_info(edges):
    wire = Part.Wire(edges)
    vertices = [v.Point for v in wire.Vertexes]
    centre = FreeCAD.Vector()
    for p in vertices:
        centre += p
    centre = centre * (1.0 / len(vertices))
    lengths = [e.Length for e in edges]
    # Rotation of a square/rectangle is only defined modulo 90 degrees.
    # Report the first edge's direction folded into (-45, 45].
    first = edges[0]
    d = first.Vertexes[1].Point - first.Vertexes[0].Point
    angle = math.degrees(math.atan2(d.y, d.x)) % 90.0
    if angle > 45.0:
        angle -= 90.0
    return {
        "x": centre.x,
        "y": centre.y,
        "rotation_deg": angle,
        "edge_count": len(edges),
        "edge_lengths": lengths,
        "perimeter": sum(lengths),
        "closed": wire.isClosed(),
    }


def main():
    path = os.environ["LAYOUT_FCSTD"]
    sketch_name = os.environ.get("LAYOUT_SKETCH", "Sketch")
    doc = FreeCAD.openDocument(path)
    try:
        sketch = doc.getObject(sketch_name)
        if sketch is None:
            raise SystemExit("sketch %r not found" % sketch_name)
        loops = [loop_info(g) for g in Part.sortEdges(sketch.Shape.Edges)]
        cutouts = [l for l in loops if l["perimeter"] < MAX_CUTOUT_PERIMETER]
        others = [l for l in loops if l["perimeter"] >= MAX_CUTOUT_PERIMETER]
        bb = sketch.Shape.BoundBox
        result = {
            "freecad_version": ".".join(FreeCAD.Version()[:3]),
            "file": path,
            "sketch": sketch_name,
            "bound_box": [bb.XMin, bb.YMin, bb.XMax, bb.YMax],
            "outline_count": len(others),
            "cutouts": cutouts,
        }
        print("LAYOUT_JSON:" + json.dumps(result))
    finally:
        FreeCAD.closeDocument(doc.Name)


main()
