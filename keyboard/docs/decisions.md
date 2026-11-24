# Open Decisions

No parts, firmware versions, manufacturing orders, or geometry changes are approved by this planning document. Propose options and record the owner's decision and rationale before making consequential commitments.

| Decision | Questions to resolve | Affects |
| --- | --- | --- |
| Prototype geometry | What are the verified switch count, positions, orientations, plate thickness, and export relationships? Which small changes, if any, are desired? | All subsequent design work |
| Layout and keymap | Row roles are agreed: a number row plus three alpha rows (see [concept.md](concept.md)). Which switch and keycap models, legends, and layers? | Fit, PCB, firmware |
| Construction | Decided 2026-11-23: two mirrored PCBs, bare boards hand-soldered by the owner, the nice!nano on low-profile sockets, JST-PH battery connector, power switch and reset button (see [pcb.md](pcb.md)). Still open: JLCPCB or PCBWay. | Electrical, case, cost, serviceability |
| Controllers and firmware | The nice!nano is selected for all three parts; ZMK `main` is pinned to a commit (see the decision record). Confirm the boards are v2 on arrival. | GPIO, charging, BLE, USB, firmware |
| Batteries and charging | Target runtime is weeks per charge with RGB off, charging through the dev board's USB-C. The case is designed around the Core Electronics CE04375 (400 mAh), to be revisited when a cell is in hand (see the record below). Use while charging, replaceability and the safety review remain open. | Power budget, safety, case |
| RGB | Agreed: one optional LED per key, ambient global effects, off when idle, on while typing, fading to black after 60 s without a key press, LED power switched off in hardware. The fade is written (in over 50 ms, out over 5 s; compiled, not run: [firmware](../firmware/README.md#lighting)), the cap is 20 % and the supply is option B. Still to choose: the LED part. | Firmware, LED selection, power |
| Tenting | Interchangeable printed wedges are approved; determine comfortable angles, attachment method, and stability while preserving flat use. | Case and stability |
| 3D printing | Confirm the exact X2D model and build volume, material, nozzle, slicer, and desired finish; what tolerances have been calibrated? | Case geometry, strength, fit |
| Desk controller | A small OLED status display is agreed. Preferred size, USB connector and cable, any buttons (e.g. reset or bootloader access), and desk placement? | Enclosure and central hardware |
| Project constraints | Budget, location and part availability, fabrication capability, and expected maintenance? | Part and process selection |

## Decision Record

- **Confirmed:** The existing prototype is for the left hand and its layout is accepted, with possible small changes later. **Pinned (owner, 2026-11-23):** the reference is now [`layout/layout.yaml`](../layout/layout.yaml) as it stands, not the prototype file; designs are checked against it.
- **Confirmed:** Two mirrored, independently rechargeable, BLE-connected halves with Cherry MX-compatible switches, under-key RGB, and optional tenting; a separate BLE desk controller connects to the PC by USB; firmware is open source.
- **Confirmed:** The owner intends to print the case designs on a Bambu Labs X2D; model specifications, material, and settings remain to be verified.
- **Confirmed:** PCBs are intended to be manufactured by PCBWay or JLCPCB. The keyboard must work without any RGB LEDs populated.
- **Confirmed:** The owner has non-wireless Raspberry Pi Pico and Pico 2 boards in stock. They cannot provide the required BLE links by themselves.
- **Confirmed:** The owner also has boards from this [ESP32-S3 development board listing](https://www.aliexpress.com/item/1005006418608267.html). The listing offers N16R8 and N8R2 variants; the actual variant, USB connections, pinout, and available quantity remain to be verified on the boards.
- **Confirmed:** Other controller options require ordering from China and may take weeks to arrive.
- **Approved:** Use removable, interchangeable printed wedges for optional tenting. Trial angles of approximately 5, 10, and 15 degrees are starting points, not final specifications; test comfort and stability.
- **Decided 2026-11-22 (concept review, see [concept.md](concept.md)):**
  - Rows: a number row plus three alpha rows. The outer pinky column holds edge keys. The thumbs hold Space, Enter, Backspace, layer keys and modifiers.
  - Controllers: nice!nano (nRF52840) boards in both halves and the dongle, mounted on custom PCBs. This replaces the earlier ESP32-S3 preference because of ZMK support and battery life. The in-stock ESP32-S3 and Pico boards are not part of the build.
  - Switches: plate-mounted MX-compatible switches in Kailh hot-swap sockets.
  - RGB: optional per-key under-switch LEDs with ambient global effects only. Off by default, with LED power switched off when unused. Per-key reactive effects and layer colours are out of scope.
  - Extras: none on the halves; a small status display on the dongle.
  - Runtime target: weeks per charge with RGB off and typical daily typing. The numeric target and test conditions are still to be agreed.
  - Hosts: Linux and Windows. macOS is not a target.
  - Board: nice!nano for both halves and the dongle. The owner will order and bench-test the boards; design work assumes they are fit for purpose as a mature, widely used ZMK board.
  - RGB behaviour: expected to be used lightly, if at all. It stays off unless the owner is typing and fades to black after 60 s without a key press.
- **Decided 2026-11-22 (owner):**
  - Keycaps: [KLP Lamé](https://github.com/braindefender/KLP-Lame-Keycaps) by braindefender (CC-BY-SA-4.0), MX stem. The owner's order is a moulded set from AliExpress (item 1005010095351207), variant "MX Black 60 Keys". The listing could not be read automatically. **Owner, 2026-11-23:** the set is the MX set, meaning MX stem and MX cap size (the models in `mx-stem-mx-size/`). The Choc-size models are kept too, in case a later change of design wants them. The set is 60 pieces in black, four of them 1.5u, with "a standard mix of saddle and non-saddle keycaps, enough for saddles for all top and bottom rows" (from memory: the owner will double-check the mix supplied). The exact kinds are still **to confirm** against the published models (which caps are the tilted or homing kinds, how many of each, and whether the 1.5u caps are H or V); the owner will measure the caps within a day or two. The published models are kept in [`parts/3d/third-party/klp-lame/`](../parts/README.md). The four fanned thumb keys stay, and two of them use the wider 1.5u Thumb caps.
  - Switches: **Kailh Speed Bronze** (confirmed by the owner). Published specs ([Keychron](https://www.keychron.com/collections/all-switches/products/kailh-speed-switch?page=8), checked 2026-11-22):
    - Clicky, MX stem, 3-pin plate mount.
    - 50 ± 10 gf operating force, 1.1 ± 0.4 mm pre-travel, 3.5 ± 0.4 mm total travel. [RTINGS](https://www.rtings.com/keyboard-switch/reviews/kailh/speed-bronze) measured 1.4 mm and 57 gf.
    - Transparent PC top housing with an SMD-LED window, so it suits reverse-mount under-key LEDs.
    - Suits Kailh MX hot-swap sockets (CPG151101S11); the socket datasheet was not retrieved.
    - The MX plate specification is 1.5 ± 0.1 mm. In the printed prototype's 1.6 mm PETG plate the switches "stay in the plate well. A good fit." (owner, 2026-11-22). Long-term hold is untested.
  - Plate outline and thickness: the prototype's 170 × 122 mm outline, its 1.6 mm thickness and the test rim were only a rough template for trying the layout. They may be changed in the case design. Only the switch positions are the accepted layout. If the thickness changes, re-check switch retention with a printed test.
- **Measured 2026-11-22** from the repo's STEP files (commit `8e4b89b`, 2026-10-10) with FreeCAD 1.1.4. These are the published design models; the moulded caps should be measured on arrival before the thumb cluster is finalised.
  - MX stem, MX size: 1u Normal/Thumb 17.99 × 17.99 mm; 1.5u Thumb H/V 26.99 × 17.99 mm. About 5.7 mm tall, with the stem at the centre of each cap.
  - MX stem, Choc size: 1u 17.50 × 16.49 mm; 1.5u Thumb H 26.52 × 16.50 mm.
- **Owner's test 2026-11-22:** the two 1.5u thumb caps fit on the printed prototype when fitted vertically (long side along the finger direction). They are on T2 and T3, the two outermost thumb keys (the owner counts these as T3 and T4), with the stem centred. Using the real rounded cap outline, T2 and T3 clear each other by 0.56 mm (see [layout/README.md](../layout/README.md)). An earlier calculation with sharp-cornered rectangles wrongly predicted collisions.
- **Decided 2026-11-22 (owner): firmware, LEDs and dongle display.** Background research is in [architecture.md](architecture.md#firmware-and-pin-research-2026-11-22).
  - **ZMK:** `main`, pinned to a commit rather than v0.3.0. Initial pin: `4de313367288aad5aeaa1243890e40dc813f7008` (2026-11-14), which uses Zephyr `v4.1.0+zmk-fixes`. Re-pin deliberately and record why. Built against this commit on 2026-11-23, compile only ([firmware/README.md](../firmware/README.md)). **Decided (owner, 2026-11-23):** the shield name `split56` stands for the moment; the base layer is QWERTY; the dongle display is approved as the common 0.96" 128 × 64 SSD1306 I²C module that most ZMK dongle builds use. The thumb keys and the Fn layer in the keymap are still a first proposal.
  - **LED supply:** option B, decided by the owner 2026-11-23: the battery through a GPIO-controlled load switch (details in [pcb.md](pcb.md#optional-leds)). The PCB must still work with no LEDs fitted.
  - **Dongle display:** a 128 × 64 I²C OLED (0.96" SSD1306 or 1.3" SH1106) running [englmaxi/zmk-dongle-display](https://github.com/englmaxi/zmk-dongle-display) (MIT), tracking `main`. Initial pin: `2bb333f87136d33e94a49d86236ed9ec254a8060` (2026-02-13). The owner is choosing a display module on AliExpress.
- **Decided 2026-11-22 (owner): case design.**
  - Claude has full rein over case design. Case work starts once the PCB design is settled, and may produce more than one case design.
  - **Keyboard 1** (black KLP Lamé caps): a modern, sleek case.
  - **Keyboard 2** (being considered, with white KLP Lamé caps): a 1970s retro-futurist case, using that decade's colour palette and industrial design. The owner cites the look of Gerry Anderson productions such as *Space: 1999*, and the original *Lost in Space*.
  - Both cases share the layout, PCB and firmware. Only the printed case parts and the keycaps differ, so case designs must not move switch positions or need PCB changes.
  - The retro case is an original design inspired by that era's look. It does not reproduce any show's logos, names or specific props.
- **Found 2026-11-22** in the prototype's `test-pad.3mf`, a Bambu Studio 02.07.01.62 project. These are the slicer settings it was printed with, not a verified specification of the printer:
  - Printer: Bambu Lab X2D, 0.4 mm nozzle (two nozzles listed), profile "0.20mm Standard @BBL X2D".
  - Material: Bambu PETG Basic at 250 °C, on a textured PEI plate at 70 °C.
  - Print: 0.2 mm layers, 2 walls, 5 top and 3 bottom layers, 15% grid infill, no supports. Elephant-foot compensation 0.15 mm, no XY hole or contour compensation.
  - Build area in the profile: 256 × 256 × 261 mm.
- **Deferred:** Battery specification and design are for Claude to undertake later, subject to owner approval and safety review.
- **Decided 2026-11-24 (owner): the lighting's fades.** Fast in, slow out: the LEDs light up over 50 ms and fade out over 5 s. The fade-out starts 60 s after the last key press on that half. Written as a small driver in the firmware module, since ZMK has no fade; compiled only ([firmware/README.md](../firmware/README.md#lighting)).
- **Found 2026-11-24, on paper, for the battery choice:** the nice!nano charges at about 89 mA and its charger stops after 5 h (4 to 6) if the charge has not finished. A 400 mAh cell charged from flat is about at that limit, and a larger cell needs USB unplugged and plugged in again part-way. Not a hazard; to time on the bench ([pcb.md](pcb.md#charger-check-against-the-datasheet-2026-11-24)).
- **Decided 2026-11-23 (owner): inputs to the case design.**
  - Design from specifications, with room to adjust: the owner does not have the parts yet.
  - Claude picks a cell from Core Electronics and designs around it, with slack for differences between the listing and what can be bought. To be revisited if it does not fit.
  - The slicer profile found in the prototype's file (above) is the design constraint.
- **Decided 2026-11-23 (owner): make all three board changes the case suggested.** Done the same day as board v4 ([pcb.md](pcb.md#v4-notches-and-mounting-holes-2026-11-23)): a 13 mm notch under the USB plug; four M3 mounting holes; and a notch at the power switch, which gives its slider 1.85 mm of overhang. The 2.5 mm proposed is not possible: the switch's locating pegs are in the way. The case keeps its dovetail, since no hole fits at the board's bottom left corner.
- **Decided 2026-11-23 (owner): the wedge design.** Proposed by Claude and accepted: a cradle with a rim that the case drops into, no fasteners and no change to the tray; inner edge raised, no tilt towards or away from the user; 5°, 10° and 15°. Generated, not printed ([case.md](case.md#tenting-wedges-2026-11-23)). The angle to keep is still open.
- **Decided 2026-11-23 (owner): the dongle is hand-wired, with no dongle board.** Four wires from the nice!nano's pads to the display's header, which stays fitted. This sets aside "mounted on custom PCBs" for the dongle only. Its case was proposed by Claude and accepted: a base and a sloped top, USB at the back ([dongle-case.md](dongle-case.md)). Generated, not printed.
- **Decided 2026-11-23 (owner): the retro case.** Proposed by Claude and approved: a thick, soft-edged body; a raised hood with louvre grooves; a recessed stripe; a built-in rake of 6°; the switch plate as an inlaid panel in an accent colour. Accent colours: burnt orange, with brown and mustard also approved; avocado is not. Retro tenting wedges are left for later. Supports are not designed in: the slicer can add them, to be revisited after the first print. Generated, not printed ([case-retro.md](case-retro.md)).
- **Confirmed 2026-11-23 (owner): how the keycaps are arranged.** Saddle Tilted on the number row and the bottom row; Saddle on the two middle rows, with a homing cap on each index finger's home key; Thumb on the two inner thumb keys; 1.5U Thumb V on the two outer ones. That is 24 tilted, 22 Saddle, 2 homing, 4 Thumb and 4 of the 1.5u: 56 of the set's 60. The table is in [scenes.md](scenes.md#keycaps).
- **Decided 2026-11-23 (owner): showcase scenes, and the GPU.** Blender scenes of both keyboards, assembled and exploded, as proposed ([scenes.md](scenes.md)). Claude may render on the RTX 5060 Ti, the card on the primary display, and no other; the devenv's Blender is built with CUDA and OptiX for this since 2026-11-24. **Changed 2026-11-24 (owner):** render on both cards, the RTX 5070 Ti and the RTX 5060 Ti.
- **Decided 2026-11-23 (owner): filament for the retro case.** Colours are chosen from Bambu Lab's filament range. PETG is preferred; PLA will be considered if it gives more period-accurate colours. The specific filaments are still to choose.
- **Chosen by Claude 2026-11-23, for the case design only:** Core Electronics CE04375, 400 mAh, 38 × 25 × 6 mm, JST-PH, with a protection board. Not ordered and not safety-reviewed. The reasons, the case built around it and its limits are in [case.md](case.md).
- **Decided 2026-11-22:** ZMK firmware, with the desk controller as central and both halves as peripherals (see [concept.md](concept.md) and [architecture.md](architecture.md)). The release to pin is still open.