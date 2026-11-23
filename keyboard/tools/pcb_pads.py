#!/usr/bin/env python3
"""Print the pads of named footprints as they are on a generated board, for checking a footprint
against its datasheet (parts/README.md, "Footprint check").

    python tools/pcb_pads.py pcb/left/left.kicad_pcb SW1 LED1 U1

Same Python as tools/pcb_generate.py (KiCad's pcbnew). Offsets are from the footprint's origin
in board axes (x right, y down, seen from the top), so rotation and flipping are included.
"""

from __future__ import annotations

import sys

import pcbnew

mm = pcbnew.ToMM
board = pcbnew.LoadBoard(sys.argv[1])
found = set()
for fp in board.GetFootprints():
    if fp.GetReference() not in sys.argv[2:]:
        continue
    found.add(fp.GetReference())
    o = fp.GetPosition()
    print(f"{fp.GetReference()} {fp.GetFPIDAsString()} at ({mm(o.x):.3f}, {mm(o.y):.3f}) "
          f"rot {fp.GetOrientationDegrees():g} flipped {fp.IsFlipped()}")
    for p in fp.Pads():
        q, s, d = p.GetPosition(), p.GetSize(pcbnew.F_Cu), p.GetDrillSize()
        print(f"  pad {p.GetNumber() or '-':3} {p.ShowPadAttr():5} offset ({mm(q.x - o.x):8.3f}, {mm(q.y - o.y):8.3f}) "
              f"size {mm(s.x):.3f} x {mm(s.y):.3f} drill {mm(d.x):.3f} net {p.GetNetname() or '-'}")
if missing := set(sys.argv[2:]) - found:
    sys.exit(f"not on the board: {', '.join(sorted(missing))}")
