# Open Decisions

No parts, firmware versions, manufacturing orders, or geometry changes are approved by this planning document. Propose options and record the owner's decision and rationale before making consequential commitments.

| Decision | Questions to resolve | Affects |
| --- | --- | --- |
| Prototype geometry | What are the verified switch count, positions, orientations, plate thickness, and export relationships? Which small changes, if any, are desired? | All subsequent design work |
| Layout and keymap | Which switch and keycap models, key sizes, legends, layers, and operating systems are required? | Fit, PCB, firmware |
| Construction | PCBWay or JLCPCB; bare boards or assembled? Soldered or hot-swap switches? | Electrical, case, cost, serviceability |
| Controllers and firmware | The owner is leaning toward ESP32-S3. Verify BLE, USB, power, and firmware support for the exact boards and versions, including any ZMK porting; compare supported alternatives before selection. | GPIO, charging, BLE, USB, firmware |
| Batteries and charging | Leave specification and design for Claude; target runtime, cell space, charging connector, use while charging, and replaceability remain open. | Power budget, safety, case |
| RGB | Optional LED population is required. One LED per key or another arrangement? Brightness, colors, effects, and default-off or on? Are per-key effects required? | Firmware, LED selection, power |
| Tenting | Interchangeable printed wedges are approved; determine comfortable angles, attachment method, and stability while preserving flat use. | Case and stability |
| 3D printing | Confirm the exact X2D model and build volume, material, nozzle, slicer, and desired finish; what tolerances have been calibrated? | Case geometry, strength, fit |
| Desk controller | Preferred size, USB connector/cable, indicators or controls, and desk placement? | Enclosure and central hardware |
| Project constraints | Budget, location and part availability, fabrication capability, and expected maintenance? | Part and process selection |

## Decision Record

- **Confirmed:** The existing prototype is for the left hand and its layout is accepted, with possible small changes later.
- **Confirmed:** Two mirrored, independently rechargeable, BLE-connected halves with Cherry MX-compatible switches, under-key RGB, and optional tenting; a separate BLE desk controller connects to the PC by USB; firmware is open source.
- **Confirmed:** The owner intends to print the case designs on a Bambu Labs X2D; model specifications, material, and settings remain to be verified.
- **Confirmed:** PCBs are intended to be manufactured by PCBWay or JLCPCB. The keyboard must work without any RGB LEDs populated.
- **Confirmed:** The owner has non-wireless Raspberry Pi Pico and Pico 2 boards in stock. They cannot provide the required BLE links by themselves.
- **Confirmed:** The owner also has boards from this [ESP32-S3 development board listing](https://www.aliexpress.com/item/1005006418608267.html). The listing offers N16R8 and N8R2 variants; the actual variant, USB connections, pinout, and available quantity remain to be verified on the boards.
- **Confirmed:** Other controller options require ordering from China and may take weeks to arrive.
- **Approved:** Use removable, interchangeable printed wedges for optional tenting. Trial angles of approximately 5, 10, and 15 degrees are starting points, not final specifications; test comfort and stability.
- **Preference, not selected:** ESP32-S3. Firmware and hardware compatibility must be established before committing.
- **Deferred:** Battery specification and design are for Claude to undertake later, subject to owner approval and safety review.
- **Proposed, not selected:** ZMK with the desk controller as central and both halves as peripherals. See [architecture.md](architecture.md) for supporting sources and limitations.