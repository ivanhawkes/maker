# Open Decisions

No parts, firmware versions, manufacturing orders, or geometry changes are approved by this planning document. Propose options and record the owner's decision and rationale before making consequential commitments.

| Decision | Questions to resolve | Affects |
| --- | --- | --- |
| Prototype geometry | What are the verified switch count, positions, orientations, plate thickness, and export relationships? Which small changes, if any, are desired? | All subsequent design work |
| Layout and keymap | Which switch and keycap models, key sizes, legends, layers, and operating systems are required? | Fit, PCB, firmware |
| Construction | Custom PCB, hand wiring, or another approach? Soldered or hot-swap switches? Available manufacturing and assembly methods? | Electrical, case, cost, serviceability |
| Controllers and firmware | Which supported boards and pinned ZMK/Zephyr versions? Is ZMK acceptable after compatibility testing? | GPIO, charging, BLE, USB, firmware |
| Batteries and charging | Target runtime with RGB on and off, available cell space, charging connector, charging while in use, and replaceability? | Power budget, safety, case |
| RGB | One LED per key or another arrangement? Brightness, colors, effects, and default-off or on? Are per-key effects required? | Firmware, LED selection, power |
| Tenting | Removable or integrated, fixed or adjustable, preferred angles, flat-use requirements, and mounting method? | Case and stability |
| 3D printing | Confirm the exact X2D model and build volume, material, nozzle, slicer, and desired finish; what tolerances have been calibrated? | Case geometry, strength, fit |
| Desk controller | Preferred size, USB connector/cable, indicators or controls, and desk placement? | Enclosure and central hardware |
| Project constraints | Budget, location and part availability, fabrication capability, and expected maintenance? | Part and process selection |

## Decision Record

- **Confirmed:** The existing prototype is for the left hand and its layout is accepted, with possible small changes later.
- **Confirmed:** Two mirrored, independently rechargeable, BLE-connected halves with Cherry MX-compatible switches, under-key RGB, and optional tenting; a separate BLE desk controller connects to the PC by USB; firmware is open source.
- **Confirmed:** The owner intends to print the case designs on a Bambu Labs X2D; model specifications, material, and settings remain to be verified.
- **Proposed, not selected:** ZMK with the desk controller as central and both halves as peripherals. See [architecture.md](architecture.md) for supporting sources and limitations.