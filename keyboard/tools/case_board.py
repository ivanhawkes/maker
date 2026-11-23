"""Write what the case generator needs to know about each board to cad/case/board-<side>.json.

Run with KiCad's Python (it needs pcbnew; see docs/pcb.md, working notes), from keyboard/:

    "$PY" tools/case_board.py

Per board: the outline, and for every footprint its reference, side, position, rotation and
the bounding box of its courtyard. Coordinates are the layout's (plan view, mm, +y away from
the user; layout/README.md), not KiCad's. The file's sha256 is recorded so that
tools/case_generate.py can refuse a JSON that is older than its board.
"""

import hashlib
import json
import pathlib

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORIGIN = (150.0, 100.0)  # as tools/pcb_generate.py: KiCad page position (mm) of layout (0, 0)


def plan(p) -> tuple[float, float]:
    return round(pcbnew.ToMM(p.x) - ORIGIN[0], 4), round(ORIGIN[1] - pcbnew.ToMM(p.y), 4)


def outline(board) -> list[tuple[float, float]]:
    """The Edge.Cuts segments chained into one closed polygon."""
    segs = [(plan(d.GetStart()), plan(d.GetEnd())) for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    pts = list(segs.pop(0))
    while segs:
        i = next(i for i, s in enumerate(segs) if pts[-1] in s)
        a, b = segs.pop(i)
        pts.append(b if a == pts[-1] else a)
    assert pts[0] == pts[-1], "outline is not closed"
    return pts[:-1]


def main():
    out = ROOT / "cad" / "case"
    out.mkdir(parents=True, exist_ok=True)
    for side in ("left", "right"):
        path = ROOT / "pcb" / side / f"{side}.kicad_pcb"
        board = pcbnew.LoadBoard(str(path))
        parts = []
        for f in board.GetFootprints():
            back = f.GetLayer() == pcbnew.B_Cu
            yard = f.GetCourtyard(pcbnew.B_CrtYd if back else pcbnew.F_CrtYd)
            box = None  # the controller's footprint has no courtyard
            if yard.OutlineCount():
                bbox = yard.BBox()  # kept in a variable: SWIG frees a temporary before its corners are read
                (x0, y0), (x1, y1) = plan(bbox.GetOrigin()), plan(bbox.GetEnd())
                box = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
            parts.append({
                "ref": f.GetReference(), "back": back, "at": plan(f.GetPosition()),
                "rot": round(f.GetOrientationDegrees(), 4), "box": box,
            })
        data = {
            "board": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "thickness": pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness()),
            "outline": outline(board),
            "parts": sorted(parts, key=lambda p: p["ref"]),
        }
        (out / f"board-{side}.json").write_text(json.dumps(data, indent=1) + "\n")
        print(f"{side}: {len(data['outline'])} outline points, {len(parts)} footprints")


if __name__ == "__main__":
    main()
