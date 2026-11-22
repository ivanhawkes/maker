#!/usr/bin/env python3
"""Expand, mirror and check the keyboard switch layout.

    python tools/layout.py build       # write layout/generated/*
    python tools/layout.py check       # geometry, mirror and freshness checks
    python tools/layout.py check-cad   # compare the left half with the FreeCAD sketch

Run from the keyboard/ directory (or anywhere; paths are resolved relative to
this file). Requires PyYAML. check-cad also needs FreeCADCmd on PATH.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "layout" / "layout.yaml"
GENERATED = ROOT / "layout" / "generated"
DEFAULT_FCSTD = ROOT / "cad" / "left-hand" / "plate.fcstd"  # corrected working CAD
PROTOTYPE_FCSTD = ROOT / "prototype" / "left-hand" / "test-pad.fcstd"  # preserved print
EXTRACTOR = ROOT / "tools" / "freecad_extract.py"

# Comparison tolerances against the CAD.
POS_TOL = 0.001  # mm
ROT_TOL = 0.001  # degrees
SIZE_TOL = 0.001  # mm

# 1u KLP Lame keycap, MX stem and MX size: 17.99 x 17.99 mm at the base,
# measured from the published STEP model (commit 8e4b89b). 1.5u thumb caps
# are not modelled yet; see layout/README.md.
DEFAULT_KEYCAP = 17.99


@dataclass(frozen=True)
class Key:
    side: str  # "L" or "R"
    id: str  # e.g. C0R1, T2
    group: str  # column id or "T"
    row: str  # R1..R4, or "" for thumbs
    finger: str
    x: float
    y: float
    rotation: float
    cutout: float

    @property
    def name(self) -> str:
        return f"{self.side}_{self.id}"


# ---------------------------------------------------------------- expansion


def load_source(path: Path = SOURCE) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def column_shifts(src: dict) -> dict[str, tuple[float, float]]:
    """Plan-view (dx, dy) per column from the `adjustments` section."""
    rot = {c["id"]: math.radians(c["rotation"]) for c in src["columns"]}
    shifts: dict[str, tuple[float, float]] = {}
    for adj in src.get("adjustments") or []:
        along = float(adj.get("along_column", 0.0))
        ox, oy = map(float, adj.get("offset", (0.0, 0.0)))
        for cid in adj["columns"]:
            if cid not in rot:
                raise SystemExit(f"adjustment {adj.get('id')!r} names unknown column {cid!r}")
            a = rot[cid]
            # "Up the column" is the column's +y axis rotated by its angle.
            dx = -along * math.sin(a) + ox
            dy = along * math.cos(a) + oy
            px, py = shifts.get(cid, (0.0, 0.0))
            shifts[cid] = (px + dx, py + dy)
    return shifts


def left_keys(src: dict, adjusted: bool = True) -> list[Key]:
    """Expand the left half. With adjusted=False, return the prototype geometry."""
    defaults = src["defaults"]
    pitch = float(defaults["row_pitch"])
    shifts = column_shifts(src) if adjusted else {}
    keys: list[Key] = []
    for col in src["columns"]:
        a = math.radians(col["rotation"])
        sx, sy = shifts.get(col["id"], (0.0, 0.0))
        x0, y0 = float(col["top"][0]) + sx, float(col["top"][1]) + sy
        overrides = col.get("cutout_overrides", {}) or {}
        for i in range(int(col["rows"])):
            row = f"R{i + 1}"
            keys.append(
                Key(
                    side="L",
                    id=f"{col['id']}{row}",
                    group=col["id"],
                    row=row,
                    finger=col["finger"],
                    # Down the column axis: rotate (0, -pitch) by the column angle.
                    x=x0 + i * pitch * math.sin(a),
                    y=y0 - i * pitch * math.cos(a),
                    rotation=float(col["rotation"]),
                    cutout=float(overrides.get(row, defaults["cutout"])),
                )
            )
    arc = src["thumb_arc"]
    ax, ay = map(float, arc["anchor"])
    r = float(arc["radius"])
    # The arc centre is below the anchor (-y); each key's "up" axis points
    # radially away from it, so a key's rotation is also its angle on the arc.
    cx, cy = ax, ay - r
    for t in arc["keys"]:
        a = math.radians(t["rotation"])
        keys.append(
            Key(
                side="L",
                id=t["id"],
                group="T",
                row="",
                finger="thumb",
                x=cx - r * math.sin(a),
                y=cy + r * math.cos(a),
                rotation=float(t["rotation"]),
                cutout=float(t.get("cutout", defaults["cutout"])),
            )
        )
    return keys


def cad_known_defects(src: dict) -> dict[str, dict]:
    """Known prototype-CAD defects by left key id.

    Each value has ``cutout`` (as-found size, mm, or None) and ``offset``
    (prototype centre minus layout centre, plan coordinates, mm).
    """
    out = {}
    for kid, d in ((src.get("prototype_cad") or {}).get("known_defects") or {}).items():
        out[kid] = {
            "cutout": float(d["cutout"]) if "cutout" in d else None,
            "offset": tuple(map(float, d.get("offset", (0.0, 0.0)))),
        }
    return out


def mirror(keys: list[Key]) -> list[Key]:
    return [
        Key("R", k.id, k.group, k.row, k.finger, -k.x, k.y, -k.rotation, k.cutout)
        for k in keys
    ]


def all_keys(src: dict) -> tuple[list[Key], list[Key]]:
    left = left_keys(src)
    return left, mirror(left)


# ----------------------------------------------------------------- geometry


def square(cx: float, cy: float, size: float, rot_deg: float):
    a = math.radians(rot_deg)
    c, s = math.cos(a), math.sin(a)
    h = size / 2
    return [
        (cx + c * dx - s * dy, cy + s * dx + c * dy)
        for dx, dy in ((-h, -h), (h, -h), (h, h), (-h, h))
    ]


def _project(poly, axis):
    dots = [p[0] * axis[0] + p[1] * axis[1] for p in poly]
    return min(dots), max(dots)


def polygons_overlap(p, q) -> bool:
    """Separating-axis test for convex polygons (touching counts as overlap)."""
    for poly in (p, q):
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            axis = (y1 - y2, x2 - x1)
            a0, a1 = _project(p, axis)
            b0, b1 = _project(q, axis)
            if a1 < b0 or b1 < a0:
                return False
    return True


def _point_segment(p, a, b) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def polygon_gap(p, q) -> float:
    """Minimum distance between two convex polygons; 0 if they overlap."""
    if polygons_overlap(p, q):
        return 0.0
    best = math.inf
    for a, b in ((p, q), (q, p)):
        for pt in a:
            for i in range(len(b)):
                best = min(best, _point_segment(pt, b[i], b[(i + 1) % len(b)]))
    return best


def min_gaps(keys: list[Key], size_of) -> list[tuple[float, Key, Key]]:
    shapes = [square(k.x, k.y, size_of(k), k.rotation) for k in keys]
    out = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            out.append((polygon_gap(shapes[i], shapes[j]), keys[i], keys[j]))
    return sorted(out, key=lambda t: t[0])


# ------------------------------------------------------------------ outputs


CSV_FIELDS = ["name", "side", "id", "group", "row", "finger", "x_mm", "y_mm", "rotation_deg", "cutout_mm"]


def to_csv(keys: list[Key]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_FIELDS)
    for k in keys:
        w.writerow(
            [k.name, k.side, k.id, k.group, k.row, k.finger,
             f"{k.x:.5f}", f"{k.y:.5f}", f"{k.rotation:.5f}", f"{k.cutout:.5f}"]
        )
    return buf.getvalue()


def to_svg(left: list[Key], right: list[Key], keycap: float) -> str:
    """Plan view of both halves. Right half is drawn offset to the right."""
    gap = 40.0
    half_w = 170.0
    offset = {"L": -(half_w + gap) / 2, "R": (half_w + gap) / 2}
    w, h = 2 * half_w + gap + 20, 122.0 + 20
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-w/2:.2f} {-h/2:.2f} {w:.2f} {h:.2f}" '
        f'width="{w*4:.0f}" height="{h*4:.0f}" font-family="sans-serif">',
        "<!-- Generated by tools/layout.py from layout/layout.yaml. Do not edit. -->",
        f'<rect x="{-w/2:.2f}" y="{-h/2:.2f}" width="{w:.2f}" height="{h:.2f}" fill="white"/>',
    ]
    for side, keys in (("L", left), ("R", right)):
        ox = offset[side]
        parts.append(
            f'<rect x="{ox-85:.2f}" y="-61" width="170" height="122" fill="none" '
            f'stroke="#999" stroke-width="0.3"/>'
        )
        parts.append(
            f'<text x="{ox:.2f}" y="-63" font-size="4" text-anchor="middle">'
            f'{"Left" if side == "L" else "Right (mirrored)"}</text>'
        )
        for k in keys:
            # SVG y points down, so flip y and rotation.
            cx, cy = ox + k.x, -k.y
            for size, style in (
                (keycap, 'fill="#eef3fb" stroke="#7a9cc6" stroke-width="0.25" stroke-dasharray="1 0.6"'),
                (k.cutout, 'fill="none" stroke="#000" stroke-width="0.3"'),
            ):
                parts.append(
                    f'<rect x="{cx-size/2:.3f}" y="{cy-size/2:.3f}" width="{size:.3f}" '
                    f'height="{size:.3f}" transform="rotate({-k.rotation:.3f} {cx:.3f} {cy:.3f})" {style}/>'
                )
            parts.append(
                f'<text x="{cx:.3f}" y="{cy+1.2:.3f}" font-size="3" text-anchor="middle">{k.id}</text>'
            )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def generated_files(src: dict, keycap: float) -> dict[Path, str]:
    left, right = all_keys(src)
    return {
        GENERATED / "left-hand.csv": to_csv(left),
        GENERATED / "right-hand.csv": to_csv(right),
        GENERATED / "layout.svg": to_svg(left, right, keycap),
    }


# ----------------------------------------------------------------- commands


def cmd_build(args) -> int:
    src = load_source()
    GENERATED.mkdir(parents=True, exist_ok=True)
    for path, text in generated_files(src, args.keycap).items():
        path.write_text(text)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


def cmd_check(args) -> int:
    src = load_source()
    left, right = all_keys(src)
    failures = 0

    def report(ok: bool, msg: str):
        nonlocal failures
        print(("PASS " if ok else "FAIL ") + msg)
        failures += 0 if ok else 1

    for side, keys in (("left", left), ("right", right)):
        report(len(keys) == 28, f"{side}: {len(keys)} keys (expected 28)")
        names = [k.name for k in keys]
        report(len(set(names)) == len(names), f"{side}: key names unique")

        cut = min_gaps(keys, lambda k: k.cutout)[0]
        report(cut[0] > 0, f"{side}: switch cutouts do not overlap "
               f"(min web {cut[0]:.3f} mm, {cut[1].id}-{cut[2].id})")
        cap = min_gaps(keys, lambda k: args.keycap)[0]
        report(cap[0] > 0, f"{side}: {args.keycap} mm keycap outlines do not overlap "
               f"(min gap {cap[0]:.3f} mm, {cap[1].id}-{cap[2].id}; 1u KLP Lame MX size)")

    by_id = {k.id: k for k in right}
    mirror_ok = all(
        abs(by_id[k.id].x + k.x) < 1e-9 and by_id[k.id].y == k.y
        and abs(by_id[k.id].rotation + k.rotation) < 1e-9 and by_id[k.id].cutout == k.cutout
        for k in left
    )
    report(mirror_ok, "right half is the exact mirror of the left about the y axis")

    stale = [p for p, text in generated_files(src, args.keycap).items()
             if not p.exists() or p.read_text() != text]
    report(not stale, "generated files are up to date"
           + ("" if not stale else f" (stale: {', '.join(str(p.relative_to(ROOT)) for p in stale)}; run build)"))

    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


def extract_cad(fcstd: Path, sketch: str) -> dict:
    env = dict(os.environ, LAYOUT_FCSTD=str(fcstd), LAYOUT_SKETCH=sketch)
    proc = subprocess.run(
        ["FreeCADCmd", str(EXTRACTOR)], env=env, capture_output=True, text=True, errors="replace"
    )
    marker = "LAYOUT_JSON:"
    for line in (proc.stdout + "\n" + proc.stderr).replace("\r", "\n").splitlines():
        if marker in line:
            return json.loads(line.split(marker, 1)[1])
    sys.stderr.write(proc.stdout[-2000:] + proc.stderr[-2000:])
    raise SystemExit(f"FreeCADCmd produced no {marker} line (exit {proc.returncode})")


def cmd_check_cad(args) -> int:
    src = load_source()
    left = left_keys(src, adjusted=False)  # the prototype geometry
    current = {k.id: k for k in left_keys(src)}
    cad = extract_cad(Path(args.fcstd), args.sketch)
    cutouts = cad["cutouts"]
    print(f"FreeCAD {cad['freecad_version']}, {cad['file']} / {cad['sketch']}: "
          f"{len(cutouts)} cutouts, {cad['outline_count']} outline loop(s), "
          f"bound box {[round(v, 3) for v in cad['bound_box']]}")

    # The recorded defects describe the preserved prototype only; any other
    # CAD file (e.g. the corrected cad/left-hand/plate.fcstd) must match exactly.
    is_prototype = Path(args.fcstd).resolve() == PROTOTYPE_FCSTD.resolve()
    known = cad_known_defects(src) if is_prototype else {}
    failures = 0
    unmatched = list(range(len(cutouts)))
    for k in left:
        defect = known.get(k.id)
        ox, oy = defect["offset"] if defect else (0.0, 0.0)
        size = defect["cutout"] if defect and defect["cutout"] is not None else k.cutout
        ex, ey = k.x + ox, k.y + oy  # where the CAD is expected to put the centre
        j = min(unmatched, key=lambda j: math.hypot(cutouts[j]["x"] - ex, cutouts[j]["y"] - ey),
                default=None)
        if j is None:
            print(f"FAIL {k.id}: no CAD cutout left to match")
            failures += 1
            continue
        c = cutouts[j]
        unmatched.remove(j)
        dpos = math.hypot(c["x"] - ex, c["y"] - ey)
        drot = abs(((c["rotation_deg"] - k.rotation) + 45) % 90 - 45)
        dsize = max(abs(e - size) for e in c["edge_lengths"])
        ok = dpos <= POS_TOL and drot <= ROT_TOL and dsize <= SIZE_TOL and c["edge_count"] == 4 and c["closed"]
        failures += 0 if ok else 1
        label = "FAIL" if not ok else ("KNOWN" if defect else "PASS")
        if not ok or args.verbose or label == "KNOWN":
            extra = ""
            if defect:
                extra = (f", known prototype defect: cutout {size} mm (intended {k.cutout} mm), "
                         f"centre {math.hypot(ox, oy):.5f} mm from the layout")
            print(f"{label} {k.id}: dpos {dpos:.5f} mm, drot {drot:.5f} deg, "
                  f"dsize {dsize:.5f} mm, edges {c['edge_count']}, closed {c['closed']}{extra}")
    for j in unmatched:
        print(f"FAIL CAD cutout at ({cutouts[j]['x']:.3f}, {cutouts[j]['y']:.3f}) has no layout key")
        failures += 1
    if cad["outline_count"] != 1:
        print(f"FAIL expected 1 outline loop, found {cad['outline_count']}")
        failures += 1

    changed = 0
    for k in left:
        n = current[k.id]
        d = math.hypot(n.x - k.x, n.y - k.y)
        if d > 1e-9 or n.rotation != k.rotation or n.cutout != k.cutout:
            changed += 1
            print(f"CHANGED {k.id}: moved ({n.x - k.x:+.3f}, {n.y - k.y:+.3f}) mm from the CAD "
                  f"by adjustments in layout.yaml")

    print(f"\n{len(left)} layout keys vs {len(cutouts)} CAD cutouts; "
          f"tolerances {POS_TOL} mm / {ROT_TOL} deg / {SIZE_TOL} mm; {failures} failure(s); "
          f"{changed} key(s) deliberately changed from the CAD by adjustments")
    return 1 if failures else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--keycap", type=float, default=DEFAULT_KEYCAP,
                   help=f"assumed keycap base size in mm (default {DEFAULT_KEYCAP})")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").set_defaults(func=cmd_build)
    sub.add_parser("check").set_defaults(func=cmd_check)
    c = sub.add_parser("check-cad")
    c.add_argument("--fcstd", default=str(DEFAULT_FCSTD))
    c.add_argument("--sketch", default="Sketch")
    c.add_argument("-v", "--verbose", action="store_true")
    c.set_defaults(func=cmd_check_cad)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
