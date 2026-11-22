"""Export the corrected left plate CAD to STEP, DXF and 3MF, then read each back.

Run with FreeCADCmd from the keyboard/ directory:

    FreeCADCmd tools/freecad_export.py

Inputs and outputs (all in cad/left-hand/):
    plate.fcstd            source (opened, not saved)
    plate.step             the whole Body (plate + test rim), like the prototype STEP
    plate-baseplate.dxf    the Baseplate sketch (outline + 28 cutouts), mm
    plate.3mf              plain mesh of the Body (not a Bambu Studio project)
"""

import math
import os

import FreeCAD
import Import
import importDXF
import Mesh
import MeshPart
import Part

SRC = "cad/left-hand/plate.fcstd"
OUT = "cad/left-hand"


def main():
    doc = FreeCAD.openDocument(SRC)
    try:
        body = doc.getObject("Body")
        sketch = doc.getObject("Sketch")
        shape = body.Shape
        step = os.path.join(OUT, "plate.step")
        dxf = os.path.join(OUT, "plate-baseplate.dxf")
        mf = os.path.join(OUT, "plate.3mf")

        Import.export([body], step)
        importDXF.export([sketch], dxf)
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.01, AngularDeflection=math.radians(5))
        mesh.write(mf)

        # Read-back checks.
        s = Part.Shape()
        s.read(step)
        print("EXPORT step solids %d volume %.3f (source %.3f) bbox %s" % (
            len(s.Solids), s.Volume, shape.Volume, s.BoundBox))
        m = Mesh.Mesh(mf)
        print("EXPORT 3mf facets %d solid %s volume %.3f (source %.3f)" % (
            m.CountFacets, m.isSolid(), m.Volume, shape.Volume))
        lines = 0
        with open(dxf, errors="replace") as f:
            prev = None
            for line in f:
                t = line.strip()
                if prev == "0" and t == "LINE":
                    lines += 1
                prev = t
        print("EXPORT dxf LINE entities %d (sketch edges %d)" % (lines, len(sketch.Shape.Edges)))
    finally:
        FreeCAD.closeDocument(doc.Name)


main()
