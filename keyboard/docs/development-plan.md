# Development Plan

This is a handoff for future work, not a claim that implementation has started. Before each phase, confirm the applicable open decisions in [decisions.md](decisions.md). Record findings, assumptions, files, tool versions, and results as work progresses.

## 1. Establish The Baseline

1. Open the FreeCAD prototype without overwriting it; inspect its feature tree, dimensions, units, switch locations, orientation, plate and baseplate, and coordinate system. Inspect the other files and establish which geometry each contains and whether it matches the source.
2. Record the verified layout in an editable, traceable form, preserving a connection to the source model. Review the left-hand baseline with the owner and record any requested small changes.
3. Generate or model the mirrored right-hand geometry and verify corresponding positions and clearances. Keep the original baseline intact.

**Gate:** owner accepts the recorded baseline and intended mirror; unresolved measurements are identified, not guessed.

## 2. Choose The Architecture

1. Compare feasible switch construction methods, supported BLE/USB controllers, firmware, RGB parts, batteries, charging/protection, and tenting approaches against requirements and budget.
2. Check the selected firmware version's two-peripheral dongle, matrix, lighting, power, and USB support against chosen hardware. Prepare an initial power budget and physical space allocation.
3. Confirm printer specifications, material and slicer choices. Present tradeoffs and request the owner's decisions. Capture the selected components, data sheets, pin budget, and rationale.

**Gate:** architecture and important constraints are agreed before ordering parts or committing to fabrication.

## 3. Design And Prototype

1. Develop editable left/right mechanical designs, assembly details, and tenting, checking component and antenna clearances. Design for the verified printer and document manufacturing settings and tolerances.
2. Create and review the electrical schematic and, if selected, PCB or wiring design, including matrix, RGB, power, charging, protection, and programming access. Check footprint orientation and mirrored geometry explicitly.
3. Implement firmware for both halves and the USB central with matching layout and matrix transforms, a user-approved keymap, lighting controls, and a documented build/flash and bonding procedure. Pin dependencies and document exact versions.
4. Run digital checks and review safety and fabrication outputs before asking for approval to procure or build. Prototype in stages, ideally proving a single switch, radio link, and LED before scaling up. Follow the selected firmware's recommended split/dongle bring-up procedure.

**Gate:** reviewed, reproducible design artifacts and a documented, approved physical build plan.

## 4. Assemble And Validate

Build and test each half and the central incrementally using [verification.md](verification.md). Record actual results, measurements, limitations, and any changes. Have the owner evaluate comfort, keymap, tenting, lighting, and battery life; revise and retest as necessary.

## Intended Deliverables

Editable CAD and corresponding verified exports, electrical schematics and PCB or wiring artifacts, component list with sourcing and safety notes, three reproducible firmware builds and flashing instructions, 3D printing and assembly instructions, operation guidance, and recorded verification results. Exact directory structure and formats should follow the tools selected during design.