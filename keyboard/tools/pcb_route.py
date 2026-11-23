#!/usr/bin/env python3
"""Auto-route the generated boards with Freerouting, then import the result.

    python tools/pcb_route.py [left|right ...]     # default: both

For each board: export a Specctra DSN with KiCad 10's pcbnew API, run Freerouting
headless, import the SES session back, and save the board in place. Run
tools/pcb_generate.py first. Re-running the generator discards the routing.

Needs `freerouting` on PATH (2.5.0, provided by the devenv shell) and KiCad's pcbnew
module. Freerouting's own settings and logs go under $FREEROUTING_HOME (default: a
temporary directory), not the user's home.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent.parent
MAX_PASSES = int(os.environ.get("FREEROUTING_PASSES", "8"))
# A second round on the routed board, starting afresh, finishes a few more links (2026-11-23:
# left 11 -> 8, right 10 -> 9 unconnected); more passes in one round do not.
ROUNDS = int(os.environ.get("FREEROUTING_ROUNDS", "2"))


def route(side: str) -> int:
    board_path = ROOT / "pcb" / side / f"{side}.kicad_pcb"
    board = pcbnew.LoadBoard(str(board_path))
    exe = shutil.which("freerouting")
    if not exe:
        raise SystemExit("freerouting not found on PATH")
    with tempfile.TemporaryDirectory(prefix=f"route-{side}-") as tmp:
        tmp = Path(tmp)
        dsn, ses = tmp / f"{side}.dsn", tmp / f"{side}.ses"
        if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
            raise SystemExit(f"{side}: DSN export failed")
        # Freerouting takes its user-data and log paths from Java's user.home and the XDG
        # variables, not $HOME, so redirect all of them.
        home = Path(os.environ.get("FREEROUTING_HOME", str(tmp / "home")))
        home.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / "config"),
                   XDG_STATE_HOME=str(home / "state"), XDG_DATA_HOME=str(home / "data"),
                   XDG_CACHE_HOME=str(home / "cache"),
                   JAVA_TOOL_OPTIONS=f"-Duser.home={home} -Djava.awt.headless=true")
        cmd = [exe, "-de", str(dsn), "-do", str(ses), f"--router.autorouter.max_passes={MAX_PASSES}",
               "--gui.enabled=false"]
        print(f"{side}: {' '.join(cmd)}", flush=True)
        log_path = ROOT / "pcb" / side / f"{side}-freerouting.log"
        with log_path.open("w") as log_file:
            proc = subprocess.run(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT, text=True)
        print(f"{side}: freerouting exit {proc.returncode}; log {log_path.relative_to(ROOT)}")
        for line in log_path.read_text(errors="replace").strip().splitlines()[-6:]:
            print(f"  | {line[:200]}")
        if proc.returncode != 0 or not ses.exists():
            raise SystemExit(f"{side}: freerouting failed (exit {proc.returncode})")
        if not pcbnew.ImportSpecctraSES(board, str(ses)):
            raise SystemExit(f"{side}: SES import failed")
    board.BuildConnectivity()
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):  # refill the planes around the new tracks
        raise SystemExit(f"{side}: zone refill failed")
    pcbnew.SaveBoard(str(board_path), board)
    # Freerouting leaves vias that connect to nothing on one side. Remove them (not the
    # generator's locked plane vias) from the saved board, reloaded: in the process that
    # imported the session, the connectivity check misses them.
    board = pcbnew.LoadBoard(str(board_path))
    # Freerouting necks tracks down into small pads below the fab minimum (0.125 mm) and
    # sometimes picks a 0.6/0.4 mm via the DSN offers (0.1 mm ring). Bring both back to the
    # board minimums; DRC checks the result.
    ds = board.GetDesignSettings()
    fixed = 0
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < ds.m_TrackMinWidth:
            t.SetWidth(ds.m_TrackMinWidth)
            fixed += 1
        elif t.GetClass() == "PCB_VIA" and (t.GetWidth(pcbnew.F_Cu) - t.GetDrillValue()) / 2 < ds.m_ViasMinAnnularWidth:
            t.SetDrill(t.GetWidth(pcbnew.F_Cu) - 2 * ds.m_ViasMinAnnularWidth - pcbnew.FromMM(0.02))
            fixed += 1
    print(f"{side}: widened or re-drilled {fixed} items")
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    dangling = [t for t in board.GetTracks()
                if t.GetClass() == "PCB_VIA" and not t.IsLocked() and conn.TestTrackEndpointDangling(t, False)]
    for v in dangling:
        board.Remove(v)
    board.BuildConnectivity()
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise SystemExit(f"{side}: zone refill failed")
    pcbnew.SaveBoard(str(board_path), board)
    print(f"{side}: removed {len(dangling)} dangling vias")
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    print(f"{side}: saved {board_path.relative_to(ROOT)} with {len(tracks)} track segments, {len(vias)} vias")
    return 0


def main(argv: list[str]) -> int:
    for side in argv or ["left", "right"]:
        for _ in range(ROUNDS):
            route(side)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
