#!/usr/bin/env python3
"""Write and check the fabrication files for both boards: Gerbers, drill files, a placement
file, a parts list, and a zip of what a board house is sent.

    python tools/fab_generate.py           # write pcb/fab/ and check it; exit 1 on a failure
    python tools/fab_generate.py --check   # only: is pcb/fab/ made from the boards as they are now

Run it after tools/pcb_generate.py and tools/pcb_check.py, with the same Python (KiCad's
pcbnew) and kicad-cli on PATH. kicad-cli writes the files; the checks then read them back with
their own small parsers and compare them with the board as pcbnew reads it, so a wrong
export option shows up here and not at the board house. Nothing is sent anywhere.

The Gerbers carry the time they were made, so two runs differ in those lines only.
pcb/fab/report.txt records each board file's sha256: --check fails when a board has changed
since, which is the case to catch before an order.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent.parent
FAB = ROOT / "pcb" / "fab"
# What a board house is sent. The copper is in stack order: front, GND plane, VLED plane, back.
LAYERS = {"F.Cu": "F_Cu.gtl", "In1.Cu": "In1_Cu.g1", "In2.Cu": "In2_Cu.g2", "B.Cu": "B_Cu.gbl",
          "F.Paste": "F_Paste.gtp", "B.Paste": "B_Paste.gbp", "F.SilkS": "F_Silkscreen.gto",
          "B.SilkS": "B_Silkscreen.gbo", "F.Mask": "F_Mask.gts", "B.Mask": "B_Mask.gbs", "Edge.Cuts": "Edge_Cuts.gm1"}
DRILLS = {"PTH": True, "NPTH": False}   # file suffix: plated
POINT = re.compile(r"X(-?\d+)Y(-?\d+)D0([123])\*")
KEY_SWITCH = re.compile(r"SW\d+")   # their values are the key ids: one parts-list line for all of them


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def board_path(side: str) -> Path:
    return ROOT / "pcb" / side / f"{side}.kicad_pcb"


def cli(*args) -> None:
    subprocess.run(["kicad-cli", *map(str, args)], check=True, capture_output=True)


def gerber_points(path: Path) -> dict[str, set]:
    """The points of a Gerber in whole micrometres, by operation: 1 draw to, 2 move to, 3 flash."""
    text = path.read_text()
    assert "%FSLAX46Y46*%" in text and "%MOMM*%" in text, f"{path.name}: not millimetres in 4.6 format"
    points = collections.defaultdict(set)
    for x, y, op in POINT.findall(text):
        points[op].add((round(int(x) / 1000), round(int(y) / 1000)))
    return points


def drill_hits(path: Path) -> dict[float, list]:
    """The hits of an Excellon file in micrometres, by tool diameter in mm."""
    text = path.read_text()
    assert "METRIC" in text, f"{path.name}: not metric"
    tools, hits, now = {}, collections.defaultdict(list), None
    for line in text.splitlines():
        if m := re.fullmatch(r"T(\d+)C([\d.]+)", line):
            tools[m[1]] = float(m[2])
        elif m := re.fullmatch(r"T(\d+)", line):
            now = tools[m[1]]
        elif m := re.fullmatch(r"X(-?[\d.]+)Y(-?[\d.]+)", line):
            hits[now].append((round(float(m[1]) * 1000), round(float(m[2]) * 1000)))
    return hits


def board_holes(board) -> collections.Counter:
    """(plated, diameter in mm): how many, as pcbnew reads the board."""
    holes = collections.Counter()
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            holes[(True, round(t.GetDrillValue() / 1e6, 3))] += 1
    for f in board.GetFootprints():
        for p in f.Pads():
            d = p.GetDrillSize()
            if d.x:
                assert d.x == d.y, f"{f.GetReference()}: a slot, which the drill check does not read"
                holes[(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, round(d.x / 1e6, 3))] += 1
    return holes


def near(point, points) -> bool:
    """Is the point in the set, to a micrometre of rounding?"""
    return any((point[0] + dx, point[1] + dy) in points for dx in (-1, 0, 1) for dy in (-1, 0, 1))


def parts_list(board, path: Path) -> int:
    groups = collections.defaultdict(list)
    for f in sorted(board.GetFootprints(), key=lambda f: [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", f.GetReference())]):
        if not f.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM:
            ref = f.GetReference()
            value = "Key switch socket" if KEY_SWITCH.fullmatch(ref) else f.GetValue()
            groups[(value, str(f.GetFPID().GetLibItemName()))].append(ref)
    with path.open("w", newline="") as out:
        w = csv.writer(out, lineterminator="\n")
        w.writerow(["Refs", "Value", "Footprint", "Qty"])
        for (value, footprint), refs in groups.items():
            w.writerow([" ".join(refs), value, footprint, len(refs)])
    return sum(len(refs) for refs in groups.values())


def make(side: str, say) -> bool:
    """Write one board's files and check them. Returns True when every check passes."""
    source, out = board_path(side), FAB / side
    board = pcbnew.LoadBoard(str(source))
    ok = True

    def check(passed: bool, text: str):
        nonlocal ok
        say(f"{side}: {'ok  ' if passed else 'FAIL'} {text}")
        ok &= passed

    unfilled = [z.GetNetname() for z in board.Zones() if z.GetNetname() and not z.IsFilled()]
    check(not unfilled, f"every copper zone is filled as saved{': not ' + ', '.join(unfilled) if unfilled else ''}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    # --subtract-soldermask: no ink on a pad, whatever the board house does with silkscreen there
    cli("pcb", "export", "gerbers", "-o", f"{out}/", "-l", ",".join(LAYERS), "--subtract-soldermask", source)
    cli("pcb", "export", "drill", "-o", f"{out}/", "--excellon-separate-th", "-u", "mm", source)
    cli("pcb", "export", "pos", "-o", out / f"{side}-pos.csv", "--format", "csv", "--units", "mm", "--side", "both", source)
    parts = parts_list(board, out / f"{side}-bom.csv")

    gerbers = {layer: out / f"{side}-{name}" for layer, name in LAYERS.items()}
    drills = {plated: out / f"{side}-{name}.drl" for name, plated in DRILLS.items()}
    missing = [p.name for p in [*gerbers.values(), *drills.values()] if not p.exists()]
    check(not missing, f"{len(gerbers)} Gerbers and {len(drills)} drill files written{': not ' + ', '.join(missing) if missing else ''}")
    if missing:
        return False
    points = {layer: gerber_points(p) for layer, p in gerbers.items()}
    marks = {layer: len(p["1"]) + len(p["3"]) for layer, p in points.items()}
    check(all(marks[l] for l in LAYERS if l != "F.Paste"), "layers drawn: " + ", ".join(f"{l} {n}" for l, n in marks.items()))

    # The outline: the Gerber's extent is the board's (pcbnew's includes the 0.1 mm line).
    edge = points["Edge.Cuts"]["1"] | points["Edge.Cuts"]["2"]
    xs, ys = [p[0] for p in edge], [p[1] for p in edge]
    box = board.GetBoardEdgesBoundingBox()
    want = (box.GetLeft() / 1000, box.GetRight() / 1000, -box.GetBottom() / 1000, -box.GetTop() / 1000)
    got = (min(xs), max(xs), min(ys), max(ys))
    check(all(abs(a - b) <= 100 for a, b in zip(got, want)),
          f"outline {(got[1] - got[0]) / 1000:.2f} x {(got[3] - got[2]) / 1000:.2f} mm, the board's")

    # The holes: the same sizes and counts as the board, inside the outline, and each plated
    # one on a pad or via of both outer layers (so drills and copper share an origin and a hand).
    hits = {plated: drill_hits(p) for plated, p in drills.items()}
    drilled = collections.Counter({(plated, dia): len(at) for plated, by in hits.items() for dia, at in by.items()})
    check(drilled == board_holes(board), "holes as on the board: " + ", ".join(
        f"{n} x {dia:g}{'' if plated else ' NPTH'}" for (plated, dia), n in sorted(drilled.items(), key=lambda i: (not i[0][0], i[0][1]))))
    every = [at for by in hits.values() for hole in by.values() for at in hole]
    check(all(got[0] < x < got[1] and got[2] < y < got[3] for x, y in every), f"all {len(every)} holes inside the outline")
    plated = [at for hole in hits[True].values() for at in hole]
    for layer in ("F.Cu", "B.Cu"):
        off = sum(not near(at, points[layer]["3"]) for at in plated)
        check(not off, f"every plated hole is on a {layer} pad or via{f': {off} are not' if off else ''}")

    # The placement file: every part that is placed, on the side the board has it.
    with (out / f"{side}-pos.csv").open() as f:
        placed = {r["Ref"]: r["Side"] for r in csv.DictReader(f)}
    want = {f.GetReference(): "bottom" if f.IsFlipped() else "top" for f in board.GetFootprints()
            if not f.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES}
    check(placed == want, f"placement file: {len(placed)} parts, {sum(s == 'bottom' for s in placed.values())} on the bottom; parts list: {parts} parts")

    with zipfile.ZipFile(FAB / f"{side}-gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted([*gerbers.values(), *drills.values()]):
            z.write(p, p.name)
    say(f"{side}: board sha256 {sha(source)}")
    return ok


def fresh() -> bool:
    report = FAB / "report.txt"
    text = report.read_text() if report.exists() else ""
    ok = True
    for side in ("left", "right"):
        made = f"{side}: board sha256 {sha(board_path(side))}" in text
        print(f"{side}: {'ok  ' if made else 'FAIL'} pcb/fab/ is made from the board as it is now")
        ok &= made
    return ok and "FAIL" not in text


def main() -> int:
    if sys.argv[1:] == ["--check"]:
        return 0 if fresh() else 1
    lines = []

    def say(text: str):
        print(text)
        lines.append(text)

    FAB.mkdir(exist_ok=True)
    ok = all([make(side, say) for side in ("left", "right")])
    (FAB / "report.txt").write_text("\n".join(lines) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
