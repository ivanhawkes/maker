# Development Plan

This is a handoff for future work, not a claim that implementation has started. Before each phase, confirm the applicable open decisions in [decisions.md](decisions.md). Record findings, assumptions, files, tool versions, and results as work progresses.

## 1. Establish The Baseline

1. Open the FreeCAD prototype without overwriting it; inspect its feature tree, dimensions, units, switch locations, orientation, plate and baseplate, and coordinate system. Inspect the other files and establish which geometry each contains and whether it matches the source.
2. Record the verified layout in an editable, traceable form, preserving a connection to the source model. Review the left-hand baseline with the owner and record any requested small changes.
3. Generate or model the mirrored right-hand geometry and verify corresponding positions and clearances. Keep the original baseline intact.

**Gate:** owner accepts the recorded baseline and intended mirror; unresolved measurements are identified, not guessed.

**Pinned (owner, 2026-11-23):** the switch positions in [`layout/layout.yaml`](../layout/layout.yaml) as they stand are the reference. The working CAD and the generated files are checked against them; nothing is checked against the prototype any more ([layout/README.md](../layout/README.md#verification-record)).

**Inspection to date:** On 2026-11-16, `FreeCADCmd --version` reported FreeCAD 1.1.3. An initial read-only inspection terminated unexpectedly for an unknown reason; subsequent attempts opened the relocated source successfully. The prototype was moved to `prototype/left-hand/`, with matching SHA-256 checksums for all four files. The following read-only check sorted the baseplate sketch's edges into 29 closed loops: the outer boundary and 28 switch outlines. Both faces of the baseplate pad had 28 inner boundaries. Twenty-six switch outlines had a 56.000 mm perimeter and two had approximately 56.308 mm; investigate the differences and verify fit before designing around them. Switch positions, export relationships, and physical fit remain unverified. No physical test was performed.

```sh
FreeCADCmd -c 'import FreeCAD, Part; doc=FreeCAD.openDocument("prototype/left-hand/test-pad.fcstd"); sketch=doc.getObject("Sketch"); groups=Part.sortEdges(sketch.Shape.Edges); print("Sketch closed loops:", len(groups)); [print("loop", index, "edges", len(group), "closed", Part.Wire(group).isClosed(), "perimeter", round(sum(edge.Length for edge in group),3)) for index,group in enumerate(groups)]; pad=doc.getObject("Pad"); print("Baseplate faces with inner boundaries:", [(round(face.CenterOfMass.z,3), len(face.Wires)-1) for face in pad.Shape.Faces if len(face.Wires)>1])'
```

**Handoff for the two differing outlines:** A second read-only FreeCAD 1.1.3 inspection found that each has four edges of approximately 14.077116 mm, with perimeters of approximately 56.308464 mm. One has a vertex at sketch coordinate `(-57.5215, -2.6215)` mm and the other at `(-55.5302, -21.5671)` mm. These coordinates identify openings in the existing left-hand sketch, not proposed replacements. The other 26 outlines have perimeters rounding to 56.000 mm. Before changing either opening, verify its shape and switch fit, determine whether the difference is intentional, and discuss any geometry change with the owner. **Settled (owner, 2026-11-23):** not intentional. Every cutout is meant to be 14.0 mm; the two differ through rounding when the prototype was laid out by hand, and the layout source no longer records them ([layout/README.md](../layout/README.md#verification-record)).

```sh
FreeCADCmd -c 'import FreeCAD, Part; doc=FreeCAD.openDocument("prototype/left-hand/test-pad.fcstd"); groups=Part.sortEdges(doc.getObject("Sketch").Shape.Edges); [print("perimeter_mm", round(sum(edge.Length for edge in group),6), "edge_lengths_mm", [round(edge.Length,6) for edge in group], "vertices_mm", [(round(vertex.Point.x,4), round(vertex.Point.y,4)) for vertex in Part.Wire(group).Vertexes]) for group in groups if 56.1 < sum(edge.Length for edge in group) < 60]; print("body", doc.getObject("Body").Shape.BoundBox)'
```

## 2. Choose The Architecture

1. The controller (nice!nano) and firmware (ZMK) are decided. Compare PCBWay and JLCPCB fabrication and assembly options, select the ZMK release to pin, and choose the optional RGB parts against requirements and budget. Assess attachment and trial angles for the approved printed wedges. Battery specification and design are deferred for Claude.
2. Check the selected firmware version's two-peripheral dongle, matrix, lighting, power, and USB support against chosen hardware. Prepare an initial power budget and physical space allocation.
3. Confirm printer specifications, material and slicer choices. Present tradeoffs and request the owner's decisions. Capture the selected components, data sheets, pin budget, and rationale.
4. The owner orders the nice!nano boards and bench-tests them on arrival (decided 2026-11-22). PCB and firmware design proceed in parallel on the assumption that the boards work as documented. When testing, use the boards to test both BLE peripherals connected simultaneously to a USB HID central. Check pairing persistence, reconnect, representative key events, and current in active, connected-idle, and sleep states. Record exact boards, USB wiring, firmware and dependency versions, measurements, and results; test optional RGB separately.

**Gate:** architecture and important constraints are agreed and the nice!nano/ZMK combination is demonstrated on the owner's bench before committing to PCB fabrication. The controllers themselves are ordered by the owner up front. If the proof fails, document alternatives and tradeoffs for the owner.

## 3. Design And Prototype

1. Develop editable left/right mechanical designs, assembly details, and tenting, checking component and antenna clearances. Design for the verified printer and document manufacturing settings and tolerances.
2. Create and review the electrical schematic and, if selected, PCB or wiring design, including matrix, RGB, power, charging, protection, and programming access. Check footprint orientation and mirrored geometry explicitly.
3. Implement firmware for both halves and the USB central with matching layout and matrix transforms, a user-approved keymap, lighting controls, and a documented build/flash and bonding procedure. Pin dependencies and document exact versions.
4. Run digital checks and review safety and fabrication outputs before asking for approval to procure or build. Prototype in stages, ideally proving a single switch, radio link, and LED before scaling up. Follow the selected firmware's recommended split/dongle bring-up procedure.

**Gate:** reviewed, reproducible design artifacts and a documented, approved physical build plan.

**PCB progress (2026-11-23):** v1 placement is generated for both halves and auto-routed with
Freerouting 2.5.0, which does not finish them. KiCad DRC leaves 41 unconnected items on the left
and 52 on the right, plus track-width errors from Freerouting's neck-downs below the 0.2 mm
minimum. Details are in [pcb.md](pcb.md#v1-routing-results-2026-11-23). Next, in order:

1. Partly done 2026-11-23: the finger columns are scripted, option B (load switch) is on the
   board, and the board is four layers with GND and VLED planes (owner's choice). **Done
   2026-11-23:** routing is fully scripted and deterministic, with no autorouter; both boards
   have 0 unconnected items and 0 DRC errors ([v3](pcb.md#v3-scripted-routing-2026-11-23)). The
   right half's nice!nano mounts upside down (owner's decision). Next: the schematic (for ERC
   and parity), the ZMK shield from `pcb/pins.yaml`, footprint checks against real parts, and a
   review of the routes before any fabrication output. Footprints checked against datasheets
   2026-11-23 ([results](../parts/README.md#footprint-check-against-datasheets-2026-11-23)): the
   power switch faced the controller and the LED orientation mark was at the wrong corner; both
   are fixed in the generator and the boards regenerated with 0 DRC errors.
   A provisional parts list is in [pcb.md](pcb.md#provisional-parts-list-2026-11-23).
2. Done 2026-11-23: the board rules are the stricter of JLCPCB's and PCBWay's limits, so either
   can make it ([fab house design rules](pcb.md#fab-house-design-rules-2026-11-23)). The 0.127 mm
   track minimum clears all but one neck-down. The LED cut-outs failed the 0.25 mm
   copper-to-edge minimum; fixed in v3 by moving the LED pads 0.06 mm outward (`LED_PAD_SHIFT`).
3. Superseded 2026-11-23 by v3: nothing is unrouted, RST included, and every controller GND pin
   has its thermal spokes.

**Where the PCB stands (end of 2026-11-23).** Both boards are generated and routed by
`tools/pcb_generate.py`: 0 unconnected items, 0 DRC errors, identical on every run (fingerprints
in [pcb-routing.md](pcb-routing.md)). Every footprint is checked against its datasheet, on paper
only. The power switch is on the board edge, actuator overhanging 1.0 mm (1.85 mm since v4), on towards the user
on both halves; the LED silkscreen mark is at the part's cut corner. Nothing is ordered and no
fabrication output exists.

**Next, in this order** (proposed by Claude and accepted by the owner, 2026-11-23). Announce
each before starting it:

1. **Done 2026-11-23, on paper:** electrical review of the scripted routes
   ([pcb.md](pcb.md#electrical-review-2026-11-23)). No routing fault; six changes proposed, all
   accepted by the owner, and the four board changes applied and regenerated the same day:
   0 unconnected, 0 DRC errors on both boards.
2. **Done 2026-11-23, compile only:** the ZMK shield, generated from `pcb/pins.yaml` by
   `tools/zmk_generate.py`. The left, right, dongle and settings-reset images build, and the built
   pin mapping matches the pin table ([firmware/README.md](../firmware/README.md)). Nothing is
   flashed. The keymap is a placeholder.
3. **Done 2026-11-23:** the schematic, drawn from each board by `tools/sch_generate.py`. ERC is
   clean and DRC's parity check finds no difference ([pcb.md](pcb.md#schematic-2026-11-23)). As
   expected it only agrees with the board; the independent netlist checks are in
   `tools/pcb_review.py`.
4. Before any order: measure the bought parts against a 1:1 print of the board, and settle the
   outline with the case.

**Handoff (end of 2026-11-23).** Steps 1 to 3 are done and pushed: the electrical review and its
board changes, the firmware (compiles; nothing flashed) and the schematics (ERC clean, parity
exact). Step 4 is next and has two parts, neither started:

- **1:1 prints of both boards** for checking the bought parts. **Done 2026-11-23:** four PDFs in
  `pcb/print/` (front, and back seen from below, for each half); the PDF scale is checked, a
  paper print is not ([pcb.md](pcb.md)). The owner prints them and measures the parts.
- **The case design. v2 done 2026-11-23, digital checks only** ([case.md](case.md)): a tray, an
  inlaid plate and a lid for each half, generated by `tools/case_generate.py` and checked
  against both boards. The battery (Core Electronics CE04375, 400 mAh) sits beside the board
  under the lid. Nothing is printed. The owner then
  asked for the three board changes the case suggested, and they are made (board v4, 2026-11-23:
  a notch under the USB plug, four M3 mounting holes, 1.85 mm of overhang for the power switch;
  [pcb.md](pcb.md#v4-notches-and-mounting-holes-2026-11-23)). Both boards: 0 unconnected, 0 DRC
  errors, ERC clean, parity exact. The case is rebuilt on them (v2: six screws from below, four
  of them through the board) and the 1:1 prints are redone. Next: the owner prints one half as a
  fit test. Tenting wedges are generated at 5°, 10° and 15° ([case.md](case.md#tenting-wedges-2026-11-23)),
  digital checks only; print the 10° one first. The dongle's case is generated too
  ([dongle-case.md](dongle-case.md)): hand-wired, no dongle board; measure the display before
  printing it. The retro case for keyboard 2 is generated as well
  ([case-retro.md](case-retro.md)): keyboard 1's insides in a thicker shell with a hood, on a
  6° raked plinth; no board change. Not started: retro tenting wedges. The controller's
  height is still unmeasured; the case keeps 6.5 mm clear over it.

**Blender scenes that showcase the keyboard (owner, 2026-11-23). Built 2026-11-23**
([scenes.md](scenes.md)): two files, each with an assembled and an exploded scene and five
cameras, and a still for each camera. The brief was:

- Several interesting camera angles, with lighting to suit.
- Scenes of the assembled product and exploded views.
- Both keyboards: keyboard 1 in black, the retro one in off-white with its accent colour
  ([case-retro.md](case-retro.md)).
- The keycaps must be known accurate models of the KLP Lamé caps the owner will use, in place
  of the plain blocks the case generators stand in for them. The published STEP models
  ([decisions.md](decisions.md), measured 2026-11-22) are the place to start. They are in
  `parts/3d/third-party/klp-lame/` (CC BY-SA 4.0: credit the author wherever they are shown),
  and are to be checked against the owner's caps once measured. The set is 60 black caps, four
  of them 1.5u, a mix of saddle and non-saddle with enough saddles for all the top and bottom
  rows (owner); the exact kinds, and so which model goes on which key, are still to confirm. Blender has no STEP
  import: convert the models with FreeCAD.
- Blender 5.2.3 is in the devenv (`devenv.nix`) and runs headless (checked 2026-11-23).
- The scenes should be made from the generated case files, so that a regenerated case can be
  shown without rebuilding the scene by hand.

**Work that does not wait on a print or a part (listed 2026-11-24).** Everything else is
waiting on a fit-test print, or on parts being ordered, measured and tested. Announce each
before starting it. Claude's suggested order: the keycap outlines, the fabrication outputs,
then the charging check.

- Software:
  - **Done 2026-11-24:** the real KLP Lamé keycap outlines are in `tools/layout.py check`
    ([layout/README.md](../layout/README.md#keycap-outlines-in-the-check-2026-11-24)): no
    overlap, the tightest pair T2–T3 at 0.56 mm. Which cap goes where is now in
    `layout/layout.yaml`, read by the check and the scenes. The case generators keep their
    plain blocks, which contain the real outlines.
  - **Done 2026-11-24, on the computer only:** the fabrication outputs (Gerbers, drill files,
    parts list, placement files) are in `pcb/fab/`, written and checked by
    `tools/fab_generate.py` and read back with a second program
    ([pcb.md](pcb.md#fabrication-outputs-2026-11-24)). Not an approval to order: that still
    waits on measured parts, the choice of house and the owner.
  - **Done 2026-11-24, compile only:** the lighting firmware. Lit for 60 s after a half's last
    key press, then a 5 s fade to black; 50 ms to light up (owner, 2026-11-24); the 20 % cap
    now stops the build if raised ([firmware/README.md](../firmware/README.md#lighting)).
    Nothing is flashed: the look of the fade is to judge on the LEDs.
  - Retro tenting wedges, deferred by the owner ([case-retro.md](case-retro.md)); a retro
    dongle case if wanted.
- Desk research:
  - **Done 2026-11-24, on paper:** the BQ24075's charge termination against TI's datasheet,
    now in `parts/datasheets/` ([pcb.md](pcb.md#charger-check-against-the-datasheet-2026-11-24)).
    The review's point stands. New: a 400 mAh cell charged from flat at the module's 89 mA
    takes about as long as the charger's 5 h safety timer; to time on the bench.
  - Match off-white, burnt orange, brown and mustard to Bambu Lab's PETG and PLA ranges
    ([case-retro.md](case-retro.md)).
  - The position of the nice!nano's reset button, so the dongle's case can have a pen hole
    ([dongle-case.md](dongle-case.md)).
  - The power budget: "weeks per charge" has no number or test conditions yet.
- For the owner to decide:
  - The keymap: the thumb keys and the Fn layer are still a first proposal
    ([firmware/README.md](../firmware/README.md)).
  - JLCPCB or PCBWay, and whether to ask for non-plated holes for the controller's sockets
    ([pcb.md](pcb.md#open-items)).
- Housekeeping:
  - The open-items list in [pcb.md](pcb.md#open-items) still carries finished items and the old
    1.0 mm power switch overhang (1.85 mm since v4).
  - One guide to printing and assembly; it is a listed deliverable, and is spread across the
    case documents.
  - The `.FCStd` case files do not go through LFS: the pattern in `.gitattributes` is the
    lowercase `*.fcstd`.
  - The Blender change in the owner's NixOS configuration is committed there but not applied:
    `sudo nixos-rebuild switch --flake .#lythir` compiles Blender, about 45 minutes.
  - Where the 22 seconds for each 4k still goes has not been measured
    ([scenes.md](scenes.md)); the 2k set has not been rendered.

Still to verify, from the review: a full charge against the charger's safety timer (bench), the
antenna's extent on the bought module, the soft-start values on the bench, and one real LED's
pinout with a meter ([pcb.md](pcb.md#schematic-2026-11-23)). Run `python tools/pcb_check.py`,
`tools/pcb_review.py`, `tools/zmk_generate.py --check` and `tools/layout.py check` after any
change; all four pass at this commit. After a board change also run `tools/fab_generate.py`,
or `pcb/fab/` is older than the board (`--check` tells). After a board change also run `tools/case_board.py`,
`tools/case_generate.py`, `tools/wedge_generate.py` and `tools/case_retro_generate.py` ([case.md](case.md#generating-and-checking)).

## 4. Assemble And Validate

Build and test each half and the central incrementally using [verification.md](verification.md). Record actual results, measurements, limitations, and any changes. Have the owner evaluate comfort, keymap, tenting, lighting, and battery life; revise and retest as necessary.

## Intended Deliverables

Editable CAD and corresponding verified exports, electrical schematics and PCB or wiring artifacts, component list with sourcing and safety notes, three reproducible firmware builds and flashing instructions, 3D printing and assembly instructions, operation guidance, and recorded verification results, and Blender showcase scenes (above). Exact directory structure and formats should follow the tools selected during design.