# Requirements

## Confirmed

- Design a personal keyboard as two physically separate, mirrored halves using the existing accepted left-hand prototype as the ergonomic baseline. Allow for small later adjustments.
- The accepted left-hand prototype is expected to have 28 switch holes, for 28 switches per half when mirrored.
- Fit Cherry MX-compatible mechanical switches. Exact switch and keycap models are not yet selected.
- Provide a microcontroller and rechargeable battery in each half.
- Support optional under-key RGB lighting on each half. The keyboard must work without any LEDs populated.
- Provide optional tenting with interchangeable printed wedges; final angles and attachment method remain to be determined.
- Use a third microcontroller in a small separate desk case. Each keyboard half communicates with it over BLE, and it connects to the PC by wired USB.
- Use open-source firmware. The keymap is not yet specified.
- Use a number row plus three alpha rows on each half (see [concept.md](concept.md)).
- Use nice!nano (nRF52840) boards for both halves and the desk controller. The halves mount theirs on custom PCBs, with switches in hot-swap sockets; the desk controller is hand-wired to its display, with no board (owner, 2026-11-23).
- Give the desk controller a small status display. Put no encoders, displays, or pointing devices on the halves.
- Work with Linux and Windows hosts.
- Have the custom PCBs manufactured by PCBWay or JLCPCB; the manufacturer and assembly approach are not yet selected.
- Design the cases for printing by the owner on a Bambu Labs X2D. Verify the exact printer capabilities and chosen material and settings before relying on them.

## Target Behavior

- The PC sees one usable USB keyboard via the desk controller, with keys from both halves operating together.
- Each half runs for weeks per charge with RGB off and typical daily typing. The numeric target is still to be agreed. Proposed 2026-11-24, for the owner to decide: at least 8 weeks at 8 hours awake a day on the 400 mAh cell, an average of 253 µA or less; the estimate is about 27 weeks ([power budget](architecture.md#power-budget-2026-11-24)).
- Both halves reconnect after power cycling and can be charged independently. Validate startup and recovery when either half is absent or reconnects.
- When populated, RGB lighting is usable on both halves and can be switched off to conserve power; lighting is ambient (global effects). It stays off unless the owner is typing, fades to black after 60 s without a key press, and its power is switched off when dark. Builds with no LEDs must retain normal keyboard operation.
- The keyboard is usable flat as well as with the selected tenting option, with a stable, non-slip base and no interference with cables or the user's hands.
- Battery, switches, electronics, and fasteners fit within the chosen case and remain serviceable according to an agreed maintenance approach.
- Layout revisions can be propagated to the case, switch plate, electronics, and firmware without silently diverging.

## Acceptance

The owner must approve physical comfort, layout, keymap, lighting, tenting, and practical battery life after a working build. Engineering acceptance also requires documented checks in [verification.md](verification.md). Numeric targets and precise test conditions remain to be agreed; none have been verified yet.