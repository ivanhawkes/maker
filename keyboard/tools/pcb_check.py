#!/usr/bin/env python3
"""Check the generated boards: KiCad DRC with schematic parity, ERC, the custom rules file, and a
fingerprint of the routing.

    python tools/pcb_check.py        # exit 1 on a DRC or ERC error, a parity difference, an open
                                     # connection, an unread rule or an unexpected library mismatch

Run it after tools/pcb_generate.py, with the same Python (KiCad's pcbnew) and kicad-cli on PATH.
Per board it prints the DRC counts by type, the unconnected count and a hash of every track, via
and footprint placement. The generator is deterministic, so the hash only changes when the
routing does: compare it before and after a change that should not move anything.

It also checks that KiCad read the whole custom rules file. KiCad 10.0.8 stops reading
<board>.kicad_dru at a rule it cannot parse and says nothing (found 2026-11-23: a rule using
min_resolved_spokes had disabled the two rules after it). So a rule that must fire is appended
to a temporary copy; if it does not fire, something above it was not read.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent.parent
CANARY = '\n(rule "canary"\n  (constraint annular_width (min 9mm)))\n'
# Footprints the generator changes on purpose, so KiCad reports them as differing from their
# library copies: the sockets' and the battery connector's widened pads (pth_ring) and the LED's
# moved pads and turned mark (load_led). Any other mismatch is an error.
CHANGED_FOOTPRINTS = re.compile(r"Footprint (SW\d+|LED\d+|J1)\b")


def drc(board: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "drc.json"
        subprocess.run(["kicad-cli", "pcb", "drc", "--schematic-parity", "--format", "json", "--severity-all",
                        "-o", str(out), str(board)], check=True, capture_output=True)
        return json.loads(out.read_text())


def erc(schematic: Path) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "erc.json"
        subprocess.run(["kicad-cli", "sch", "erc", "--format", "json", "--severity-all", "-o", str(out), str(schematic)],
                       check=True, capture_output=True)
        return [v for sheet in json.loads(out.read_text())["sheets"] for v in sheet["violations"]]


def rules_read(board: Path) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        for ext in (".kicad_pcb", ".kicad_pro", ".kicad_dru", ".kicad_sch"):
            shutil.copy(board.with_suffix(ext), tmp)
        copy = Path(tmp) / board.name
        with copy.with_suffix(".kicad_dru").open("a") as f:
            f.write(CANARY)
        return any("canary" in v["description"] for v in drc(copy)["violations"])


def fingerprint(board: Path) -> tuple[str, int, int]:
    b = pcbnew.LoadBoard(str(board))
    rows = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            rows.append(("V", t.GetPosition().x, t.GetPosition().y, t.GetWidth(pcbnew.F_Cu), t.GetDrillValue(), t.GetNetname()))
        else:
            rows.append(("T", t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetWidth(), t.GetLayer(), t.GetNetname()))
    fps = sorted((f.GetReference(), f.GetPosition().x, f.GetPosition().y, f.GetOrientationDegrees(), f.IsFlipped())
                 for f in b.GetFootprints())
    vias = sum(1 for r in rows if r[0] == "V")
    return hashlib.sha256(repr((sorted(rows), fps)).encode()).hexdigest()[:16], len(rows) - vias, vias


def main() -> int:
    bad = False
    for side in ("left", "right"):
        board = ROOT / "pcb" / side / f"{side}.kicad_pcb"
        report = drc(board)
        counts = collections.Counter((v["severity"], v["type"]) for v in report["violations"])
        errors = {t: n for (sev, t), n in sorted(counts.items()) if sev == "error"}
        warnings = {t: n for (sev, t), n in sorted(counts.items()) if sev != "error"}
        unconnected = len(report["unconnected_items"])
        parity = [v["description"] for v in report.get("schematic_parity", [])]
        stray = [v["items"][0]["description"] for v in report["violations"] if v["type"] == "lib_footprint_mismatch"
                 and not CHANGED_FOOTPRINTS.match(v["items"][0]["description"])]
        rules = collections.Counter((v["severity"], v["type"]) for v in erc(board.with_suffix(".kicad_sch")))
        digest, tracks, vias = fingerprint(board)
        print(f"{side}: unconnected {unconnected}, errors {errors or 0}, warnings {warnings or 0}")
        print(f"{side}: schematic parity differences {parity or 0}; ERC {dict(rules) or 'clean'}"
              + (f"; UNEXPECTED library mismatch {stray}" if stray else ""))
        print(f"{side}: {tracks} tracks, {vias} vias, fingerprint {digest}")
        bad |= bool(errors) or unconnected > 0 or bool(parity) or bool(rules) or bool(stray)
    if not rules_read(ROOT / "pcb" / "left" / "left.kicad_pcb"):
        print("left.kicad_dru: KiCad did not read the whole rules file (a rule it cannot parse stops it)")
        bad = True
    else:
        print("custom rules: all read")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
