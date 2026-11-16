# Requirements

## Confirmed

- Design a personal keyboard as two physically separate, mirrored halves using the existing accepted left-hand prototype as the ergonomic baseline. Allow for small later adjustments.
- The accepted left-hand prototype is expected to have 28 switch holes, for 28 switches per half when mirrored.
- Fit Cherry MX-compatible mechanical switches. Exact switch and keycap models are not yet selected.
- Provide a microcontroller and rechargeable battery in each half.
- Support optional under-key RGB lighting on each half. The keyboard must work without any LEDs populated.
- Provide optional tenting with interchangeable printed wedges; final angles and attachment method remain to be determined.
- Use a third microcontroller in a small separate desk case. Each keyboard half communicates with it over BLE, and it connects to the PC by wired USB.
- Use open-source firmware. The owner's keymap, electrical construction method, and component choices are not yet specified.
- Have the custom PCBs manufactured by PCBWay or JLCPCB; the manufacturer and assembly approach are not yet selected.
- Design the cases for printing by the owner on a Bambu Labs X2D. Verify the exact printer capabilities and chosen material and settings before relying on them.

## Target Behavior

- The PC sees one usable USB keyboard via the desk controller, with keys from both halves operating together.
- Both halves reconnect after power cycling and can be charged independently. Validate startup and recovery when either half is absent or reconnects.
- When populated, RGB lighting is usable on both halves and can be switched off to conserve power; brightness and behavior require a user decision. Builds with no LEDs must retain normal keyboard operation.
- The keyboard is usable flat as well as with the selected tenting option, with a stable, non-slip base and no interference with cables or the user's hands.
- Battery, switches, electronics, and fasteners fit within the chosen case and remain serviceable according to an agreed maintenance approach.
- Layout revisions can be propagated to the case, switch plate, electronics, and firmware without silently diverging.

## Acceptance

The owner must approve physical comfort, layout, keymap, lighting, tenting, and practical battery life after a working build. Engineering acceptance also requires documented checks in [verification.md](verification.md). Numeric targets and precise test conditions remain to be agreed; none have been verified yet.