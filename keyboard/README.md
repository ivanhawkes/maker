# Personal Split Keyboard

A personal keyboard project based on an accepted left-hand switch-position prototype. The goal is two mirrored, rechargeable keyboard halves communicating over Bluetooth Low Energy (BLE) with a separate desk controller connected to the PC by USB. The owner intends to print the cases on a Bambu Labs X2D.

**Status:** planning and research only. No PCB, firmware, final case, bill of materials, or completed keyboard has been designed or verified in this repository yet.

## Prototype

The original files are preserved together in [prototype/left-hand/](prototype/left-hand/):

- [test-pad.fcstd](prototype/left-hand/test-pad.fcstd): existing FreeCAD prototype and starting point for the left-hand design.
- [test-pad.step](prototype/left-hand/test-pad.step) and [test-pad.3mf](prototype/left-hand/test-pad.3mf): existing 3D files.
- [test-pad-baseplate.dxf](prototype/left-hand/test-pad-baseplate.dxf): existing baseplate drawing; the DXF declares millimetres.

The geometry, switch count, dimensions, and relationships between the source and exports still need to be verified in FreeCAD. The layout is accepted, but small changes may be needed later.

## Documentation

- [Requirements](docs/requirements.md): agreed goals and acceptance criteria.
- [Architecture](docs/architecture.md): proposed mechanical, electrical, and firmware approach and research links.
- [Decisions](docs/decisions.md): open questions and their design implications.
- [Development plan](docs/development-plan.md): staged work and deliverables for the future agent.
- [Verification plan](docs/verification.md): digital checks and physical tests to plan and record.
- [AGENTS.md](AGENTS.md): shared instructions for agents; [CLAUDE.md](CLAUDE.md) imports them for Claude Code.

## Starting With Claude

Open this directory as the project and select the desired available model in your Claude-enabled client. In Claude Code, the root `CLAUDE.md` imports the shared instructions. Ask the agent to start with the prototype inspection and decision review in the development plan. No build or test commands are defined yet. Claude's instruction-file loading can be checked with `/context all` where supported.