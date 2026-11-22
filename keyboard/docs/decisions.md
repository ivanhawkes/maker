# Open Decisions

No parts, firmware versions, manufacturing orders, or geometry changes are approved by this planning document. Propose options and record the owner's decision and rationale before making consequential commitments.

| Decision | Questions to resolve | Affects |
| --- | --- | --- |
| Prototype geometry | What are the verified switch count, positions, orientations, plate thickness, and export relationships? Which small changes, if any, are desired? | All subsequent design work |
| Layout and keymap | Row roles are agreed: a number row plus three alpha rows (see [concept.md](concept.md)). Which switch and keycap models, legends, and layers? | Fit, PCB, firmware |
| Construction | Hot-swap sockets and a dev board on a custom PCB are agreed. PCBWay or JLCPCB? Bare boards, or assembled with sockets, diodes and LEDs? | Electrical, case, cost, serviceability |
| Controllers and firmware | The nice!nano is selected for all three parts. Which pinned ZMK release? | GPIO, charging, BLE, USB, firmware |
| Batteries and charging | Target runtime is weeks per charge with RGB off, charging through the dev board's USB-C. Cell size, use while charging, and replaceability remain open. The design is deferred to Claude. | Power budget, safety, case |
| RGB | Agreed: one optional LED per key, ambient global effects, off when idle, on while typing, fading to black after 60 s without a key press, LED power switched off in hardware. Still to choose: the LED part, a brightness cap, how to handle the LED supply voltage, and how to implement the fade. | Firmware, LED selection, power |
| Tenting | Interchangeable printed wedges are approved; determine comfortable angles, attachment method, and stability while preserving flat use. | Case and stability |
| 3D printing | Confirm the exact X2D model and build volume, material, nozzle, slicer, and desired finish; what tolerances have been calibrated? | Case geometry, strength, fit |
| Desk controller | A small OLED status display is agreed. Preferred size, USB connector and cable, any buttons (e.g. reset or bootloader access), and desk placement? | Enclosure and central hardware |
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
- **Decided 2026-11-22 (concept review, see [concept.md](concept.md)):**
  - Rows: a number row plus three alpha rows. The outer pinky column holds edge keys. The thumbs hold Space, Enter, Backspace, layer keys and modifiers.
  - Controllers: nRF52840 dev boards (nice!nano-class) in both halves and the dongle, mounted on custom PCBs. This replaces the earlier ESP32-S3 preference because of ZMK support and battery life. The in-stock ESP32-S3 and Pico boards are not part of the build. The exact board is not yet chosen.
  - Switches: plate-mounted MX-compatible switches in Kailh hot-swap sockets.
  - RGB: optional per-key under-switch LEDs with ambient global effects only. Off by default, with LED power switched off when unused. Per-key reactive effects and layer colours are out of scope.
  - Extras: none on the halves; a small status display on the dongle.
  - Runtime target: weeks per charge with RGB off and typical daily typing. The numeric target and test conditions are still to be agreed.
  - Hosts: Linux and Windows. macOS is not a target.
  - Board: nice!nano for both halves and the dongle. The owner will order and bench-test the boards; design work assumes they are fit for purpose as a mature, widely used ZMK board.
  - RGB behaviour: expected to be used lightly, if at all. It stays off unless the owner is typing and fades to black after 60 s without a key press.
- **Deferred:** Battery specification and design are for Claude to undertake later, subject to owner approval and safety review.
- **Proposed, not selected:** ZMK with the desk controller as central and both halves as peripherals. See [architecture.md](architecture.md) for supporting sources and limitations.