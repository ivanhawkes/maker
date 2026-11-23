# Development Plan

This is a handoff for future work, not a claim that implementation has started. Before each phase, confirm the applicable open decisions in [decisions.md](decisions.md). Record findings, assumptions, files, tool versions, and results as work progresses.

## 1. Establish The Baseline

1. Open the FreeCAD prototype without overwriting it; inspect its feature tree, dimensions, units, switch locations, orientation, plate and baseplate, and coordinate system. Inspect the other files and establish which geometry each contains and whether it matches the source.
2. Record the verified layout in an editable, traceable form, preserving a connection to the source model. Review the left-hand baseline with the owner and record any requested small changes.
3. Generate or model the mirrored right-hand geometry and verify corresponding positions and clearances. Keep the original baseline intact.

**Gate:** owner accepts the recorded baseline and intended mirror; unresolved measurements are identified, not guessed.

**Inspection to date:** On 2026-11-16, `FreeCADCmd --version` reported FreeCAD 1.1.3. An initial read-only inspection terminated unexpectedly for an unknown reason; subsequent attempts opened the relocated source successfully. The prototype was moved to `prototype/left-hand/`, with matching SHA-256 checksums for all four files. The following read-only check sorted the baseplate sketch's edges into 29 closed loops: the outer boundary and 28 switch outlines. Both faces of the baseplate pad had 28 inner boundaries. Twenty-six switch outlines had a 56.000 mm perimeter and two had approximately 56.308 mm; investigate the differences and verify fit before designing around them. Switch positions, export relationships, and physical fit remain unverified. No physical test was performed.

```sh
FreeCADCmd -c 'import FreeCAD, Part; doc=FreeCAD.openDocument("prototype/left-hand/test-pad.fcstd"); sketch=doc.getObject("Sketch"); groups=Part.sortEdges(sketch.Shape.Edges); print("Sketch closed loops:", len(groups)); [print("loop", index, "edges", len(group), "closed", Part.Wire(group).isClosed(), "perimeter", round(sum(edge.Length for edge in group),3)) for index,group in enumerate(groups)]; pad=doc.getObject("Pad"); print("Baseplate faces with inner boundaries:", [(round(face.CenterOfMass.z,3), len(face.Wires)-1) for face in pad.Shape.Faces if len(face.Wires)>1])'
```

**Handoff for the two differing outlines:** A second read-only FreeCAD 1.1.3 inspection found that each has four edges of approximately 14.077116 mm, with perimeters of approximately 56.308464 mm. One has a vertex at sketch coordinate `(-57.5215, -2.6215)` mm and the other at `(-55.5302, -21.5671)` mm. These coordinates identify openings in the existing left-hand sketch, not proposed replacements. The other 26 outlines have perimeters rounding to 56.000 mm. Before changing either opening, verify its shape and switch fit, determine whether the difference is intentional, and discuss any geometry change with the owner.

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
   board, and the board is four layers with GND and VLED planes (owner's choice). Rows, row ends,
   the thumb cluster and the LED chain's long links are scripted; the right half's controller
   is mirrored (provisional). 2 (left) and 3 (right) links remain, all thumb rows bar one
   ([results](pcb.md#v24-nearly-routed-2026-11-23)). Next: the owner reviews the mirrored
   controller; then finish the last links and fix the controller's starved thermal.
   A provisional parts list is in [pcb.md](pcb.md#provisional-parts-list-2026-11-23).
2. Done 2026-11-23: the board rules are the stricter of JLCPCB's and PCBWay's limits, so either
   can make it ([fab house design rules](pcb.md#fab-house-design-rules-2026-11-23)). The 0.127 mm
   track minimum clears all but one neck-down. New: the LED cut-outs fail the 0.25 mm
   copper-to-edge minimum, and a fix needs choosing.
3. If routing still fails, move the controller or widen the board around it. There is about
   2 mm of board beyond the USB end now.
4. Find out why RST is unrouted on the right board, and fix the controller GND pad that has a
   single thermal spoke.

## 4. Assemble And Validate

Build and test each half and the central incrementally using [verification.md](verification.md). Record actual results, measurements, limitations, and any changes. Have the owner evaluate comfort, keymap, tenting, lighting, and battery life; revise and retest as necessary.

## Intended Deliverables

Editable CAD and corresponding verified exports, electrical schematics and PCB or wiring artifacts, component list with sourcing and safety notes, three reproducible firmware builds and flashing instructions, 3D printing and assembly instructions, operation guidance, and recorded verification results. Exact directory structure and formats should follow the tools selected during design.