# Handover for the next Claude Code session (2026-11-23)

Written by Claude at the end of a session on the owner's laptop. The owner is continuing on
their main desktop. Read this, then `AGENTS.md`, `README.md` and `docs/pcb.md`. Delete this
file once its contents are absorbed into the docs.

## Owner instructions that still apply

These were saved as memories on the laptop, which do not travel with the repo:

- **Announce major work first.** Before starting any major piece of work, tell the owner
  what it is and suggest a model and effort level.
- **Reminder:** when the PCBs are ordered, remind the owner to order a **solder-paste
  stencil**, one per board design. The paste goes on the bottom side.
- **Reminder:** later, add the real KLP Lamé keycap outlines to `tools/layout.py check`. The
  prototype already proves the caps fit; the owner estimates about 2 mm between caps, by eye.
- **Case design:** the owner has given Claude full rein, starting once the PCB is settled.
  - Black-cap board: a modern, sleek case.
  - Possible second, white-cap board: a 1970s retro-futurist case in the spirit of Gerry
    Anderson, Space: 1999 or the original Lost in Space. It must be original: no logos,
    names or props.
- **Plate:** thickness and outline may change. The switches fit well in the 1.6 mm PETG
  plate.
- **Pinky columns:** their vertical offset is provisional; the 6° fan-out is good.
- **Commits:** commit and push only when asked. Never stage the sandbox dotfiles
  (`.bashrc`, `.zshrc`, `.gitconfig`, and so on) or `.claude/` inside `keyboard/`.
- **Other limits:** ask before system-wide config changes, never run sudo for the owner,
  and keep the owner's email private.

## State of the work

Committed and pushed (latest commits):

- `cb0875f`: Freerouting added to the devenv shell.
- `a6eeec8`: FreeCAD removed from the devenv shell; use the system FreeCAD (1.1.4).
- `18a2244`: PCB brief, pin table, v0 placement.

The devenv shell builds, and every tool in it reports a version: KiCad 10.0.8,
Blender 5.2.3, Bambu Studio 02.08.00.50, Arm GCC 15.3, CMake, Ninja, dtc, protoc, west,
tio and the Python modules.

### Uncommitted: PCB v1 placement rework, in progress

Check `git status` and `git diff` first; these may have been committed before the hand-over.

1. **`tools/pcb_generate.py`**
   - **Controller keep-out.** v0's keep-out covered the controller's pads, so no track
     could reach the controller. The new keep-outs (`CONTROLLER_KEEPOUTS`) cover only the
     area between the two pin rows and a strip beyond the antenna end. The antenna end is
     plan −y: the footprint marks USB at plan +y.
   - **GND pours** on both layers, filled at generation time.
   - **`join_same_pads()`.** The marbastlib hot-swap footprint gives each socket pin a
     plated hole and two overlapping SMD tabs with the same pad number. KiCad treats them as
     connected; Freerouting reported them as unrouted. Short tracks now join them.
   - **Design rules now persist.** A board created with `pcbnew.BOARD()` has no project
     file, so its net classes and rules were silently dropped, and every earlier routing
     run used KiCad's defaults. The generator now writes an empty `.kicad_pro`, loads the
     board in a subprocess (`--finish`), applies the rules and saves.
     - In KiCad 10.0.8, `SaveBoard` writes the project file only in a process that did not
       build the board, hence the subprocess.
     - `check_rules()` reads the rules back from `.kicad_pro` to confirm them.
   - **`CUSTOM_RULES`**, written to `<board>.kicad_dru`:
     - **Copper to edge.** The board-setup minimum is a floor that custom rules cannot
       relax. It is set to 0.2 mm, and a custom rule restores 0.3 mm everywhere except at
       the LED cut-outs. KiCad's stock SK6812MINI-E reverse-mount footprint puts its pads
       0.247 mm from its own cut-out. Check 0.2 mm against the chosen fab house's minimum.
     - **Controller GND spokes.** This rule does *not* clear the warning: one controller
       GND pad per board still has only one thermal spoke. Unresolved and minor.
   - The board label now reads "v1 placement".
2. **`tools/pcb_route.py`** (new): exports DSN, runs Freerouting headless, imports SES,
   refills the zones and saves.
   - Freerouting ignores `$HOME`. The script redirects `JAVA_TOOL_OPTIONS=-Duser.home` and
     the XDG variables to `$FREEROUTING_HOME`.
   - The pass count comes from `FREEROUTING_PASSES` (default 60). Runs used 30.
3. **`pcb/pins.yaml`.** The matrix pins were just reassigned. Nine lines now use the inner
   pin row, which faces the keys, and two use pads 21 and 22 at the bottom of the outer row,
   next to the thumbs. In v0, six lines sat on the outer row and had to squeeze past the USB
   end. **The boards have not been regenerated with this map yet.** No ZMK shield exists
   yet, so firmware cannot diverge.
4. **Generated files.** `pcb/*/*.kicad_pcb` were generated with the old pin map and are not
   routed. New files `pcb/*/*.kicad_pro` and `pcb/*/*.kicad_dru` hold the rules; commit
   them.
5. **`.gitignore`:** a `*-freerouting.log` entry.

### Routing results so far (all with the old pin map)

- **v0, KiCad default rules, keep-out over the pads.** Left board: 66 unrouted after
  18 passes (about 50 minutes on the laptop).
- **v1 rules not yet saved, old pins.** Left board: KiCad's DRC found 48 unconnected items.
  It also found 0.15 mm tracks and edge violations, because of the wrong rules.
- **Freerouting behaviour.** It stops once its best score has not improved for about
  10 passes. Each pass takes 50–80 s per board when the laptop CPU is free.

## Next steps

1. Regenerate: `python tools/pcb_generate.py`. Expect 89 footprints and 74 nets per board,
   plus the "+ .kicad_pro rules" line.
2. Run DRC before routing:
   `kicad-cli pcb drc --format json -o <out>.json pcb/left/left.kicad_pcb`.
   - Do not pass `--schematic-parity=false`; this kicad-cli rejects it and writes no
     report. One stale report already misled me this way.
   - Expected before routing: about 144 unconnected items, 2 `starved_thermal`, and
     silkscreen warnings only.
3. Route:
   `FREEROUTING_PASSES=30 FREEROUTING_HOME=<scratch dir> python tools/pcb_route.py left right`.
   Freerouting is in the devenv shell.
4. Run DRC on the routed boards. Render them for review with:
   `kicad-cli pcb export svg --layers F.Cu,B.Cu,Edge.Cuts --mode-single --fit-page-to-board --exclude-drawing-sheet`
   and convert with ImageMagick. Report what is still unrouted.
5. If routing still fails, the next ideas are:
   - Move the controller or widen the board around it. Its outline currently allows only
     about 2 mm beyond the USB end.
   - Script the regular parts of the routing, such as straight column tracks on F.Cu at
     plan-local x = 2.54 through each column, and leave only the fan-in to the controller
     to Freerouting.
6. Update `docs/pcb.md`. It still describes v0. Record the keep-out change, the pin-map
   change and the DRC results.

## Environment gotchas

- **`pcbnew` in Python.** On the laptop, the devenv shell's Python could not import
  `pcbnew`: a libprotobuf symbol error from the Python environment's protobuf. A
  matching bare Python with `PYTHONPATH` set to `kicad-base/lib/python3.14/site-packages`
  plus PyYAML worked. On the desktop, try KiCad's own Python first.
  - Set `KICAD10_FOOTPRINT_DIR` to the `share/kicad/footprints` directory of the
    `kicad-footprints` package.
- **Sandbox.** In Claude Code's sandbox, git writes, nix builds and FreeCAD saves need the
  sandbox disabled: `.git`, `~/.cache` and the nix store are read-only there.
- **FreeCAD.** Use the system `FreeCADCmd` (1.1.4). devenv's patched nixpkgs has no cached
  FreeCAD or VTK build, so it would compile them for hours.

## Open decisions (owner)

- **LED supply.** The SK6812MINI-E needs 3.7–5.5 V; the nice!nano VCC is 3.3 V. Options
  A–D are in `docs/architecture.md`. The board ends the VLED net at the placeholder pad
  `TP_VLED`.
- **Fab house:** JLCPCB or PCBWay.
- **Footprint checks.** Verify the Kailh CPG151101S11 socket footprint and the low-profile
  socket pin holes against their datasheets.
- **Later work:** generate the schematic, write the ZMK shield from `pcb/pins.yaml`, and
  settle the board outline together with the case design.
- **Ordering.** Ask before ordering anything. Battery and charging safety are engineering
  requirements.
