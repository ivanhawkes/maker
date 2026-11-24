# Keyboard Concept

This is the agreed concept (2026-11-22). It says *what* the keyboard is. The
other documents cover *how* it will be designed and verified. Items marked
**to verify** are design intentions, not checked facts.

## In One Paragraph

The keyboard is a 56-key split column-stagger keyboard made of two mirrored
28-key halves. Each half has 6 columns × 4 rows plus a 4-key thumb arc,
MX-compatible switches in hot-swap sockets, and optional per-key RGB under the
switches. Each half is a battery-powered BLE peripheral built around an
nice!nano (nRF52840) soldered to a custom PCB. A third nRF52840 sits in a small
desk dongle with a status display. It is the ZMK central and connects to the PC
by USB. The PC sees a single ordinary USB keyboard. The keyboard should run for
weeks per charge with lighting off. It can be used flat or tented on swappable
printed wedges, and it must work well on Linux and Windows.

## Layout (Left Half, From The Prototype)

Switch centres come from a read-only extraction of `Sketch` in
`prototype/left-hand/test-pad.fcstd` (FreeCAD 1.1.3, 2026-11-22). The values
are in mm, measured from the sketch origin at the centre of the
170 × 122 mm plate outline. The x axis points towards the user's right and the
y axis away from the user. The angles are the rotation of the square cutouts
modulo 90°. For the thumb keys the sign was inferred from the fan pattern
(**to verify** in the GUI).

| Column (finger) | x of top key | Rows (y, top→bottom) | Rotation | Notes |
| --- | --- | --- | --- | --- |
| C0 outer pinky | −72.76 | 27.05, 8.10, −10.84, −29.79 | 6° | splayed |
| C1 pinky | −53.80 | 28.96, 10.02, −8.89, −27.83 | 6° | bottom two cutouts are 14.077 mm (others 14.000) |
| C2 ring | −27.05 | 42.00, 22.95, 3.90, −15.15 | 0° | |
| C3 middle | −8.00 | 48.00, 28.95, 9.90, −9.15 | 0° | highest column |
| C4 index | 11.05 | 44.00, 24.95, 5.90, −13.15 | 0° | |
| C5 inner index | 30.10 | 42.00, 22.95, 3.90, −15.15 | 0° | |

| Thumb key | Centre (x, y) | Rotation |
| --- | --- | --- |
| T0 (innermost under index) | 10.46, −36.67 | +14° |
| T1 | 30.54, −34.20 | 0° |
| T2 | 50.62, −36.67 | −14° |
| T3 (outermost) | 69.51, −43.92 | −28° |

C2 to C5 are on a 19.05 mm (0.75 in) pitch, and every column uses a 19.05 mm
row pitch. The right half is the mirror image about x. These numbers are a
reading of the prototype, not a new source of truth. The editable layout
source required by the development plan should be derived from them and
checked against the CAD.

### Row Roles

- **Row 1:** numbers and symbols.
- **Rows 2–4:** top, home and bottom alpha rows. QWERTY is assumed until a
  keymap is agreed.
- **C0 outer pinky:** edge keys such as Esc, Tab, Ctrl and Shift.
- **Thumbs:** Space, Enter, Backspace, layer keys and modifiers.

With a number row, layers are only needed for function keys, navigation and
symbols, not for everyday typing. The keymap itself is still open and will be
tried on the test print.

## Electronics

| Part | Concept | To verify |
| --- | --- | --- |
| Controller ×3 | **nice!nano** (nRF52840, Pro Micro footprint), selected 2026-11-22. The owner orders and bench-tests the boards. The design assumes they are fit for purpose because the board is mature and widely used with ZMK | Pin assignment against the published pinout. Use the board's switchable VCC output for LED power |
| Integration | The dev board solders or sockets onto a custom half PCB (JLCPCB or PCBWay) | Mounting height against the case, antenna overhang/keep-out, USB-C access from the case edge |
| Switches | Kailh Speed Bronze (confirmed; MX-compatible, clicky), plate-mounted, Kailh hot-swap sockets on the PCB. The two 14.077 mm cutouts were a CAD defect, fixed in `cad/left-hand/plate.fcstd` | The 1.6 mm printed PETG plate holds the switches well (owner). The plate's outline and thickness were only a template and may change; re-test retention if the thickness changes |
| Keycaps | KLP Lamé, MX stem, 17.99 mm 1u. Two of the four thumb keys use 1.5u Thumb caps The 1.5u caps are on T2 and T3 (the owner's T3/T4), fitted vertically, and fit on the printed prototype (owner's test; real-outline calculation gives a 0.56 mm gap). Measure the moulded caps on arrival |
| Matrix | 28 keys per half, e.g. 4 rows × 7 columns (11 GPIO) with diodes | Pin budget leaves room for LED data, battery sense and LED power control |
| RGB | Optional per-key reverse-mount LEDs (e.g. SK6812MINI-E class) on one chain per half | LED minimum supply voltage vs. LiPo discharge range, logic level at 3.3 V, current cap |
| Power | One LiPo with protection per half, charged by USB-C through the dev board, plus a power switch | Cell size and fit, charge current vs. cell rating, case temperature while charging |
| Dongle | The same nRF52840 board in a small desk case, USB-C to PC, with a small OLED status display (layer, battery of each half, connection) | ZMK dongle display support in the pinned version (may need a community module) |

The halves are optimised for battery life. The dongle is USB-powered, so it
has no power constraint and handles the keymap, the display and USB.

## Firmware

- ZMK, pinned to a release, with three builds: left peripheral, right
  peripheral, and dongle central with a mock key scanner and display.
- The keymap is held on the dongle, so changing it means flashing only the
  dongle.
- Lighting is expected to be used lightly, if at all. It uses ZMK's global
  RGB effects and has this behaviour:
  - It stays off while the keyboard is idle and comes on when typing starts.
  - It fades to black after **60 s** without a key press.
  - LED power is switched off at the hardware level whenever the lighting is
    dark or the board is asleep.
  - Per-key reactive effects and layer colours are out of scope.
- **To verify:** Stock ZMK can turn underglow off when idle and back on when
  activity resumes (`CONFIG_ZMK_RGB_UNDERGLOW_AUTO_OFF_IDLE`), using the idle
  timeout (`CONFIG_ZMK_IDLE_TIMEOUT`, set to 60000 ms). A gradual fade rather
  than an instant cut may need a small custom change or module. Check the
  pinned release. Each half tracks its own activity, so a half that isn't
  being typed on may go dark independently. **Done 2026-11-24, compile only:** a small driver
  in the firmware module fades the lighting out over 5 s from 60 s after the last key press,
  and in over 50 ms (owner's times; [firmware/README.md](../firmware/README.md#lighting)).
  Each half still goes dark on its own.
- Hosts are Linux and Windows. macOS is not a target.

## Mechanics

- The stack is keycaps → switches → printed or fabricated plate (the
  prototype plate is the baseline) → PCB with hot-swap sockets → battery and
  controller space → printed bottom case. The case is printed on the X2D.
- Case styling (owner, 2026-11-22): a modern, sleek case for the black-cap keyboard. A
  possible second keyboard with white caps would get a 1970s retro-futurist case, inspired by
  Gerry Anderson-era and original *Lost in Space* industrial design. Both share one PCB and
  layout, and the case design starts once the PCB is settled.
- The halves have no encoders, displays or pointing devices. This keeps them
  thin and simple.
- Tenting uses swappable printed wedges with trial angles of about 5°, 10° and
  15°. Each half also needs a flat, non-slip configuration.
- The battery, controller, power switch and USB-C port must stay reachable
  without removing the switches.

## Explicitly Out Of Scope (For Now)

- Encoders, displays or pointing devices on the halves.
- Wired use of a half as a standalone USB keyboard. (Note: the board has
  USB-C for charging and flashing, but ZMK runs each half as a dongle
  peripheral.)
- Per-key reactive or layer-indicating RGB.
- macOS support.
- ESP32-S3 and Raspberry Pi Pico controllers. The in-stock boards are not part
  of the build.

## Next Steps This Concept Unlocks

1. Turn the coordinates above into the editable layout source (e.g. a
   key-position table or ZMK physical layout) and cross-check it against the
   FreeCAD model, including the thumb rotation signs and the two 14.077 mm
   cutouts.
2. Assign the matrix, LED data and LED power pins from the nice!nano pinout.
3. The owner orders the nice!nanos and bench-tests them on arrival. PCB and
   firmware design proceed in parallel, assuming the boards work as
   documented.
4. Choose a cell size that fits the space under the plate and meets the
   "weeks" runtime target, using the ZMK power profiler and then measurements.
   Estimated 2026-11-24: about 27 weeks on the 400 mAh cell
   ([power budget](architecture.md#power-budget-2026-11-24)); measurements to come.
