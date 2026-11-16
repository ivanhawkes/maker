# Proposed Architecture

This document records a direction for investigation, not a finalized design. Confirm hardware, component specifications, firmware version, and user choices before implementation.

```text
Left half                     Desk controller                     Right half
MX switches + RGB             BLE central                        MX switches + RGB
MCU + rechargeable battery  -- BLE -->  MCU  <-- BLE --  MCU + rechargeable battery
                                      |
                                  USB keyboard
                                      |
                                      PC
```

Each half scans its own switches and controls its lighting. The desk controller receives events from both halves, applies the keymap, and exposes a USB HID keyboard to the PC. This is a proposed logical topology; the precise hardware and wireless pairing behavior must be verified.

## Firmware Research

[ZMK](https://zmk.dev/) is a strong open-source candidate: its [split keyboard documentation](https://zmk.dev/docs/features/split-keyboards) describes a BLE central connected to multiple peripherals, and its [dongle guide](https://zmk.dev/docs/hardware-integration/dongle) describes a USB-connected central with both halves as peripherals. The guide calls for matching physical layouts and matrix transforms across parts and a mock key scanner on a keyless central. Follow the documentation for the chosen, pinned version; do not assume development documentation exactly matches a release.

ZMK's [lighting documentation](https://zmk.dev/docs/features/lighting) says its RGB underglow feature can also drive per-key addressable LEDs. This does not by itself establish support for arbitrary per-key effects or the desired LED, voltage, and controller combination. Verify the desired controls and power behavior with the selected parts. The halves cannot operate as independent host keyboards in the described ZMK peripheral configuration without changing the architecture or firmware.

Choose a ZMK-supported BLE controller for each half and a controller that supports both BLE and USB device operation for the central. Evaluate available GPIO, antenna placement, power consumption, charging circuitry, LED interface, physical size, availability, and open documentation. No board has been selected.

## Mechanical And Layout

Inspect the FreeCAD model and exported files to establish units, geometry, switch locations and orientations, plate thickness, and reference planes. Confirm which existing file is authoritative for each feature. Preserve the accepted left-hand geometry; derive the right-hand geometry by mirroring and verify it, including thumb positions and switch/keycap clearance. Keep a documented editable layout reference so small later moves can be propagated to every affected artifact.

Design around the selected switches and keycaps, battery enclosure and retention, controller and antenna clearance, charging access, fasteners, and optional tenting. Investigate flat use, stable tenting, hand clearance, accessible connectors, repairability, and manufacturing tolerances. Mirroring the case does not automatically make component footprints, connectors, or an assembled PCB electrically interchangeable.

The owner intends to print the cases on a Bambu Labs X2D. Confirm the exact model and build volume, available materials and nozzle, and slicer with the owner before setting constraints. Plan print orientation, support strategy, layer strength, tolerances, fit coupons, fastener retention, and any needed part splitting. Record the chosen material, slicer version, settings, and measured fit; do not assume a material is safe near the battery or charger without checking actual temperatures and specifications.

## Electrical And Power

The method of interconnecting switches and LEDs is open: compare a custom PCB with hand wiring or other practical options. Determine matrix dimensions and diode orientation from the actual layout and controller pins. Select the RGB LEDs and driver based on switch geometry, supply and logic voltage compatibility, controller support, brightness, and actual electrical specifications.

Each half needs a suitable rechargeable cell and a validated charging and protection design. Assess charge current and thermal limits against the exact cell and charger specifications; provide insulation, strain relief, safe battery retention, power control, and safe charging access. Check operation while charging and USB/battery power-path behavior instead of assuming they are supported. Document power-off behavior, sleep, LED idle current and whether the LED supply needs switching. Verify radio antenna clearance and avoid placing conductive parts or batteries where the controller vendor prohibits them.

Estimate battery life only after choosing the cell, LED count, brightness, and controller: compare usable capacity with measured or defensibly estimated average current for typing, idle, sleep, and lighting states. Confirm with real measurements; do not treat theoretical estimates as runtime guarantees.

## References

- [ZMK dongle integration](https://zmk.dev/docs/hardware-integration/dongle)
- [ZMK split keyboards](https://zmk.dev/docs/features/split-keyboards)
- [ZMK lighting](https://zmk.dev/docs/features/lighting) and [RGB hardware integration](https://zmk.dev/docs/hardware-integration/lighting/underglow)
- [ZMK power profiler](https://zmk.dev/power-profiler)
- [Claude Code project instructions](https://code.claude.com/docs/en/memory)