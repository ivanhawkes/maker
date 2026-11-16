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

The owner is leaning toward ESP32-S3 and has experience with software development, so a modest porting effort is acceptable to investigate. The available hardware and purchasing lead times are recorded in [decisions.md](decisions.md). No controller or firmware version has been selected.

### ESP32-S3 Compatibility Research

Research checked on 2026-11-16; these findings are not a successful build or hardware test for this project.

- ESP32-S3 supports BLE, and [Zephyr 4.1's ESP32-S3 board documentation](https://docs.zephyrproject.org/4.1.0/boards/espressif/esp32s3_devkitc/doc/index.html) lists a Bluetooth HCI driver. Zephyr documents a separate prerequisite to fetch Espressif radio binary blobs; their licensing and the project's open-source requirements need review.
- The [ZMK supported hardware page](https://zmk.dev/docs/hardware) does not list ESP32-S3 as a preconfigured target. At research time, the ZMK development branch's [manifest](https://github.com/zmkfirmware/zmk/blob/main/app/west.yml) specified the `v4.1.0+zmk-fixes` Zephyr fork; this is not a project version selection and may change.
- A [2024 ZMK proof of concept](https://github.com/zmkfirmware/zmk/issues/2173) reported BLE operation including a split keyboard on ESP32-S3 with Zephyr 3.6, using custom board configuration. The tester reported USB device support was unavailable in that version and noted an NVS problem in that setup. These historical reports do not establish the behavior of a current build or our three-controller topology.
- The tester reported approximately 100 mA at 5 V for the whole keyboard while active, with no sleep-mode configuration or sleep current specified. This is not a measurement of our board or its battery current, and the cause was not established. [Espressif's ESP-IDF BLE low-power documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/low-power-mode/low-power-mode-ble.html) describes light-sleep and clock tradeoffs, but does not prove equivalent support in ZMK's selected Zephyr version.
- [Current Zephyr documentation](https://docs.zephyrproject.org/latest/boards/espressif/esp32s3_devkitc/doc/index.html) lists an ESP32-S3 USB OTG controller; that does not prove ZMK USB HID works with its pinned Zephyr fork or the owner's exact board. Check USB connector wiring, settings persistence, radio bonding, power management, wake behavior, and optional RGB support on the actual hardware.
- A **fallback, not selected**, is an nRF52840-based ZMK-supported board such as the nice!nano or XIAO BLE, which appears on the [ZMK hardware list](https://zmk.dev/docs/hardware). It provides BLE and USB device capability, but availability, GPIO budget, electrical design, and charging behavior still need verification.

Before a PCB commitment, use the in-stock boards to test both halves connected at once to a USB HID central, reconnect and bonding persistence, key events, and representative active, connected-idle, and sleep current. Verify the USB path on the specific board and compare against an agreed runtime target. Distinguish a compile-only result from real measurements. Consult the owner before flashing existing boards or undertaking physical testing.

## Mechanical And Layout

Inspect the FreeCAD model and exported files to establish units, geometry, switch locations and orientations, plate thickness, and reference planes. Confirm which existing file is authoritative for each feature. Preserve the accepted left-hand geometry; derive the right-hand geometry by mirroring and verify it, including thumb positions and switch/keycap clearance. Keep a documented editable layout reference so small later moves can be propagated to every affected artifact.

Design around the selected switches and keycaps, battery enclosure and retention, controller and antenna clearance, charging access, fasteners, and optional tenting. Investigate flat use, stable tenting, hand clearance, accessible connectors, repairability, and manufacturing tolerances. Mirroring the case does not automatically make component footprints, connectors, or an assembled PCB electrically interchangeable.

The owner intends to print the cases on a Bambu Labs X2D. Confirm the exact model and build volume, available materials and nozzle, and slicer with the owner before setting constraints. Plan print orientation, support strategy, layer strength, tolerances, fit coupons, fastener retention, and any needed part splitting. Record the chosen material, slicer version, settings, and measured fit; do not assume a material is safe near the battery or charger without checking actual temperatures and specifications.

### Tenting

The owner approved interchangeable printed wedges: removable supports beneath each half at different fixed angles. Aim for a broad base, non-slip feet, and a repeatable attachment or locating feature once the case geometry is known. Changing angles requires swapping parts. Approximately 5, 10, and 15 degrees are suggested trial angles, not final specifications.

Raise the inner edges to tent the halves, preserve a flat configuration, and test comfortable angles before choosing final geometry. Avoid interference with the battery, PCB, charging port, and antenna. Verify actual printability, fit, strength, and resistance to sliding and tipping.

## Electrical And Power

The owner intends to have custom PCBs made by PCBWay or JLCPCB; compare bare-board and assembly options, available parts, design rules, and outputs before selecting a service. Determine matrix dimensions and diode orientation from the actual layout and controller pins. Select the RGB LEDs and driver based on switch geometry, supply and logic voltage compatibility, controller support, brightness, and actual electrical specifications. The switch matrix, BLE, and charging must work when no LEDs are populated; specify optional LED-related components and firmware configuration independently of required keyboard circuits. If LEDs are populated, account for the selected LED chain topology and document supported population patterns rather than assuming partially populated chains work.

Each half needs a suitable rechargeable cell and a validated charging and protection design. Battery specification and design are deferred for Claude. When undertaken, assess charge current and thermal limits against the exact cell and charger specifications; provide insulation, strain relief, safe battery retention, power control, and safe charging access. Check operation while charging and USB/battery power-path behavior instead of assuming they are supported. Document power-off behavior, sleep, LED idle current and whether the LED supply needs switching. Verify radio antenna clearance and avoid placing conductive parts or batteries where the controller vendor prohibits them.

Estimate battery life only after choosing the cell, LED count, brightness, and controller: compare usable capacity with measured or defensibly estimated average current for typing, idle, sleep, and lighting states. Confirm with real measurements; do not treat theoretical estimates as runtime guarantees.

## References

- [ZMK dongle integration](https://zmk.dev/docs/hardware-integration/dongle)
- [ZMK split keyboards](https://zmk.dev/docs/features/split-keyboards)
- [ZMK lighting](https://zmk.dev/docs/features/lighting) and [RGB hardware integration](https://zmk.dev/docs/hardware-integration/lighting/underglow)
- [ZMK power profiler](https://zmk.dev/power-profiler)
- [Claude Code project instructions](https://code.claude.com/docs/en/memory)