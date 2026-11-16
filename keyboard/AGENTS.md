# Project Instructions

- The development environment is NixOS with Niri. For software that is not installed, use the Nix package manager, a `devenv.nix` development shell, or a Nix flake; prefer reproducible project-local environments and ask before changing system-wide configuration.
- This is a personal, mirrored split keyboard project. The accepted prototype is for the left hand; preserve its ergonomics while allowing small future layout changes.
- Begin with `README.md` and the relevant documents in `docs/`. Distinguish user requirements, recommendations, assumptions, and decisions that remain open.
- Preserve the existing prototype files in `prototype/left-hand/`. Inspect the FreeCAD source and verify dimensions, units, orientation, switch count, and export relationships before using or changing geometry. Do not invent measurements.
- Maintain a traceable, editable source of switch positions and a consistent mapping among CAD, PCB or wiring, and firmware. Derive and verify the right half by mirroring; don't assume an electrical PCB can be mirrored without checking component footprints and routing.
- Target two independently rechargeable, BLE-connected halves with Cherry MX-compatible switches and under-key RGB, optional tenting, and a separate USB-connected BLE central. Consider ZMK first, but verify support in the selected version and hardware before committing to it.
- The owner plans to print the cases on a Bambu Labs X2D. Verify the exact printer specifications, material, and slicer settings before using them as design constraints.
- Ask the owner before locking in consequential unknowns or ordering, fabricating, or purchasing anything. Document proposed alternatives and tradeoffs.
- Treat battery charging, protection, isolation, wiring, and thermal safety as engineering requirements. Never present unverified designs or estimates as safe or production-ready.
- For each implementation step, record commands, versions, assumptions, checks, and actual results; distinguish simulation from physical testing. Keep source files and reproducible exports together and update the relevant documentation.
- Do not overwrite or discard existing work. No implementation, build, or test commands are established yet.