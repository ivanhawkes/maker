# Verification Plan

This is a planned checklist, not evidence that any test has passed. Record the date, revision, tool or equipment, method, measured result, pass/fail criteria, and remaining limitations for each check. Agree numerical thresholds with the owner before final acceptance.

## Digital And Design Review

- Inspect the original FreeCAD model and exports; record units, bounding geometry, switch coordinates and orientations, plate cutouts, and any discrepancies. Verify the right-hand mirror against the left and verify keycap and switch clearances.
- For every layout change, compare CAD, plate, electrical design, and firmware physical/matrix mappings; verify left/right orientation and key position correspondence.
- Review component data sheets, pin allocations, LED logic and supply voltages, current limits, charging and protection, antenna keep-outs, connectors, and enclosure fit.
- Run CAD validity and interference checks. For a PCB, run schematic electrical-rule and PCB design-rule checks and review manufacturing outputs against the source. For hand wiring, review and check the wiring diagram instead.
- Check the sliced parts against the verified printer build volume. Record material, nozzle, orientation, support strategy, slicer version and settings; test fit coupons, fastener retention, and print strength before a full case.
- Build all three firmware targets using recorded pinned versions; verify the keymap and build artifacts correspond to the correct controller roles. Document how to flash and recover each device.

## Physical Bring-Up

- Before connecting a cell, inspect polarity and assembly, check for shorts, and use appropriately limited power for initial checks. Verify supply rails, power switching, charging, and protection against the selected component specifications; measure charging and operating temperatures under defined conditions. Stop for unexpected current, heating, damage, or swelling.
- Verify every key and diode, simultaneous presses and releases, correct left/right mapping, and absence of stuck keys. Test USB enumeration and typing on the intended PC operating systems.
- Test initial bonding and recovery procedures, both halves reconnecting after power cycling, one half missing or reconnecting, and central USB disconnect/reconnect. Document limitations and recovery steps.
- Measure each half's active, connected-idle, and sleep current, including wake and reconnect behavior. Record measurement supply voltage, board and firmware versions, enabled peripherals, and LED state; distinguish whole-board measurements from battery-side current and avoid extrapolating from unmeasured sleep behavior.
- Verify normal keyboard operation with no LEDs populated. In an RGB-populated build, check every LED, color, brightness, available effects, and off/sleep behavior on both halves. Measure representative current and runtime with lighting on and off; record battery capacity, brightness, use pattern, and test conditions.
- Test charging and use while connected only if the selected power path supports it. Inspect cell retention, insulation, connectors, battery access, and cable strain relief.
- Verify flat and tented stability, clearances throughout the chosen adjustment range, switch fit, fasteners, and the owner's hand comfort. Check charging and USB cable access in normal use.

## Checks The Design Work Has Asked For

**First: the controller's acceptance tests** in [controller.md](controller.md#tests-to-pass).
The board bought is a clone, and two of its tests come before any cell is connected.

Specific checks that the design work to date has left for the bench. Each links to where the
question arose. None is done.

- **Charge time against the charger's safety timer.** Charge the chosen cell from its
  protection cut-off on the nice!nano, LEDs off, and time it. Note whether the orange LED goes
  out (done) or flashes at about 2 Hz (timer fault), and whether replugging USB restarts the
  charge. Expected from the datasheet: about 5 h for a 400 mAh cell, at the timer's limit
  ([pcb.md](pcb.md#charger-check-against-the-datasheet-2026-11-24)).
- **The power budget's three currents**, lighting off: deep sleep, connected and idle, and a
  key held, into the battery connector with a power profiler
  ([architecture.md](architecture.md#power-budget-2026-11-24)). In particular whether the
  lighting feature's SPI draws its 60 µA with the lighting off.
- **Charging with the lighting on.** With VLED on and the LEDs dark, confirm the charge does
  not finish; with the lighting idle (VLED off), confirm it does (same section).
- **Cell current at the brightness cap.** All 28 LEDs at white, 20 %: about 0.23 A expected,
  under the power switch's 0.3 A ([pcb.md](pcb.md#electrical-review-2026-11-23)).
- **The lighting's fades** ([firmware/README.md](../firmware/README.md#lighting)): lit for 60 s
  after the last key press, black 5 s later, supply off within a second of that; 50 ms to
  light up; a key during the fade-out brings it back. Judge whether the straight-line
  fade-out looks even, and how visible its steps are near black.
- **LED data against the supply:** with a scope, that the data pin rests low after the
  lighting goes off, and what RAW does when the LED supply switches on (soft start, R3 and C2).
- **The idle half:** switch the lighting on from one half while the other is idle; the idle
  half should stay dark until a key is pressed on it. Measure its current meanwhile (about
  28 mA expected, the dark LEDs).
- **The moulded keycaps against the published models:** measure a 1u and a 1.5u cap, and the
  gap between T2 and T3 on the plate (0.56 mm from the models;
  [layout/README.md](../layout/README.md#keycap-outlines-in-the-check-2026-11-24)).
- **The bought parts against the 1:1 prints** in `pcb/print/`, one real LED's pinout with a
  meter, the antenna's extent on the module and a socket's seated height
  ([pcb.md](pcb.md#open-items)).
- **Before an order:** `tools/pcb_check.py`, `tools/fab_generate.py` and its `--check`, then
  each zip in the board house's own viewer
  ([pcb.md](pcb.md#fabrication-outputs-2026-11-24)).

## Digital Results So Far

Computer checks only, each repeatable with the command given in the linked document.

| Date | Check | Result |
| --- | --- | --- |
| 2026-11-24 | `tools/layout.py check`, with the keycaps' real outlines | 0 failures; tightest caps T2–T3, 0.56 mm ([layout/README.md](../layout/README.md#keycap-outlines-in-the-check-2026-11-24)) |
| 2026-11-24 | `tools/pcb_check.py` | Both boards: 0 unconnected, 0 errors, parity and ERC clean ([pcb.md](pcb.md#fabrication-outputs-2026-11-24)) |
| 2026-11-24 | `tools/fab_generate.py`, and gerbonara reading the zips | Both boards pass every check ([pcb.md](pcb.md#fabrication-outputs-2026-11-24)) |
| 2026-11-24 | Firmware: four images built, `tools/zmk_generate.py --check-build`, the fade's test | All pass; compile only ([firmware/README.md](../firmware/README.md#checks)) |
| 2026-11-24 | Charger against TI's datasheet | On paper ([pcb.md](pcb.md#charger-check-against-the-datasheet-2026-11-24)) |

## Acceptance Record

No results recorded yet. The future implementation should add a dated test report with actual results and outstanding issues, and obtain the owner's comfort and usability approval before calling the design complete.