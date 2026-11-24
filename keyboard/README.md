# Personal Split Keyboard

A personal keyboard project based on an accepted left-hand switch-position prototype. The goal is two mirrored, rechargeable keyboard halves communicating over Bluetooth Low Energy (BLE) with a separate desk controller connected to the PC by USB. The owner intends to print the cases on a Bambu Labs X2D.

**Status (2026-11-24):** design in progress. Both PCB halves are generated and fully routed by script, and pass KiCad's design rule check; their fabrication files are generated and checked on the computer ([PCB design](docs/pcb.md#fabrication-outputs-2026-11-24)); the firmware for both halves and the dongle compiles ([firmware](firmware/README.md)). Each half has a schematic drawn from its board, with KiCad's electrical rules check clean. Nothing has been fabricated or flashed, and there is no final case yet. Nothing here is verified on hardware.

## Prototype

The original files are preserved together in [prototype/left-hand/](prototype/left-hand/):

- [test-pad.fcstd](prototype/left-hand/test-pad.fcstd): existing FreeCAD prototype and starting point for the left-hand design.
- [test-pad.step](prototype/left-hand/test-pad.step) and [test-pad.3mf](prototype/left-hand/test-pad.3mf): existing 3D files.
- [test-pad-baseplate.dxf](prototype/left-hand/test-pad-baseplate.dxf): existing baseplate drawing; the DXF declares millimetres.

The geometry, switch count, dimensions, and relationships between the source and exports still need to be verified in FreeCAD. The layout is accepted, but small changes may be needed later.

## Documentation

- [Concept](docs/concept.md): the agreed shape of the keyboard, covering layout, electronics, firmware, mechanics and scope.
- [Requirements](docs/requirements.md): agreed goals and acceptance criteria.
- [Architecture](docs/architecture.md): proposed mechanical, electrical, and firmware approach and research links.
- [Decisions](docs/decisions.md): open questions and their design implications.
- [Development plan](docs/development-plan.md): staged work and deliverables for the future agent.
- [PCB design](docs/pcb.md): decisions, electrical design, fab rules, parts list and results.
- [PCB routing](docs/pcb-routing.md): how the boards are routed by script, and what was learned.
- [Case design](docs/case.md): the printed case for keyboard 1, how it is generated and checked, and its limits.
- [Retro case](docs/case-retro.md): the 1970s case for keyboard 2, built round the first case's insides.
- [Dongle case](docs/dongle-case.md): the printed case for the hand-wired dongle, and its wiring.
- [Showcase scenes](docs/scenes.md): the Blender files and stills of both keyboards, and how they are made.
- [Filament on hand](docs/filament-on-hand.md): the owner's spools, for choosing colours.
- [Parts](parts/README.md): local footprints, 3D models and datasheets for every part.
- [Verification plan](docs/verification.md): digital checks and physical tests to plan and record.
- [AGENTS.md](AGENTS.md): shared instructions for agents; [CLAUDE.md](CLAUDE.md) imports them for Claude Code.

## Generating Everything

Run these from `keyboard/` inside the devenv shell, in this order. Each step reads what the one
before it wrote, so after a change run that step and everything below it. Every generator
checks its own output and exits with 1 if a check fails. FreeCAD comes from the system, not
the devenv ([PCB design](docs/pcb.md#running-the-tools)).

**1. Layout** ([layout/README.md](layout/README.md))

```sh
python tools/layout.py build       # layout/generated/ from layout/layout.yaml
python tools/layout.py check       # 28 keys a half, no overlaps (cutouts, real keycap outlines), exact mirror, outputs fresh
```

**2. Boards and schematics** ([PCB design](docs/pcb.md)). These need KiCad's own Python:

```sh
K=$(nix-store -qR "$(dirname "$(dirname "$(readlink -f "$(which kicad-cli)")")")")
PY=$(echo "$K" | grep 'python3-3.14.*-env

Open this directory as the project and select the desired available model in your Claude-enabled client. In Claude Code, the root `CLAUDE.md` imports the shared instructions. Ask the agent to start with the prototype inspection and decision review in the development plan. The PCB commands are `python tools/pcb_generate.py` (boards and schematics) and `python tools/pcb_check.py` (see [PCB design](docs/pcb.md#running-the-tools)). Claude's instruction-file loading can be checked with `/context all` where supported.)/bin/python3
YAML=$(dirname "$(dirname "$(python3 -c 'import yaml; print(yaml.__file__)')")")
export PYTHONPATH=$(echo "$K" | grep 'kicad-base-10')/lib/python3.14/site-packages:$YAML

"$PY" tools/pcb_generate.py        # both boards, routed, and their schematics; about 15 s
"$PY" tools/pcb_check.py           # design rules, electrical rules, schematic parity; about 40 s
"$PY" tools/pcb_review.py          # the boards' nets against the firmware's matrix
"$PY" tools/fab_generate.py        # Gerbers, drill files, placement and parts list in pcb/fab/, checked; about 8 s

for s in left right; do            # 1:1 prints for checking parts against the board
  kicad-cli pcb export pdf --mode-single --black-and-white --ev \
    --layers F.Cu,F.SilkS,F.Fab,Edge.Cuts -o pcb/print/$s-front.pdf pcb/$s/$s.kicad_pcb
  kicad-cli pcb export pdf --mode-single --black-and-white --ev --mirror \
    --layers B.Cu,B.SilkS,B.Fab,Edge.Cuts -o pcb/print/$s-back.pdf pcb/$s/$s.kicad_pcb
done
```

**3. Firmware shield** ([firmware/README.md](firmware/README.md), which also has the build commands)

```sh
python tools/zmk_generate.py            # the ZMK shield from pcb/pins.yaml and the layout
python tools/zmk_generate.py --check    # the shield is up to date
```

**4. Cases** ([case](docs/case.md), [retro case](docs/case-retro.md), [dongle case](docs/dongle-case.md))

```sh
"$PY" tools/case_board.py                 # board outlines and part positions, for the cases
FreeCADCmd tools/case_generate.py         # keyboard 1: tray, plate, lid; about 3 minutes
FreeCADCmd tools/wedge_generate.py        # its tenting wedges; about 1 minute
FreeCADCmd tools/case_retro_generate.py   # keyboard 2, the retro case; about 4 minutes
FreeCADCmd tools/dongle_generate.py       # the dongle's case; a few seconds
```

**5. Showcase scenes** ([scenes](docs/scenes.md))

```sh
FreeCADCmd tools/scene_export.py                                 # meshes for Blender; about 1 minute
blender -b --python tools/scene_build.py                         # the two .blend files only
blender -b --python tools/scene_build.py -- --render             # and 20 stills at 1920 x 1080
blender -b --python tools/scene_build.py -- --render --size 2k   # 20 stills at 2560 x 1440
blender -b --python tools/scene_build.py -- --render --size 4k   # 20 stills at 3840 x 2160
```

Stills go to `cad/scenes/renders/1080p/`, `2k/` or `4k/`. Add `--only kb1` or `--only retro` for
one keyboard. Rendering is on both graphics cards: the 4k set took under 10 minutes here.
Without a usable graphics card it falls back to the CPU, about eight times slower.

## Starting With Claude

Open this directory as the project and select the desired available model in your Claude-enabled client. In Claude Code, the root `CLAUDE.md` imports the shared instructions. Ask the agent to start with the prototype inspection and decision review in the development plan. The PCB commands are `python tools/pcb_generate.py` (boards and schematics) and `python tools/pcb_check.py` (see [PCB design](docs/pcb.md#running-the-tools)). Claude's instruction-file loading can be checked with `/context all` where supported.