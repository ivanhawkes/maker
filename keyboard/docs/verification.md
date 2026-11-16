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

## Acceptance Record

No results recorded yet. The future implementation should add a dated test report with actual results and outstanding issues, and obtain the owner's comfort and usability approval before calling the design complete.