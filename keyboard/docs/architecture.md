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

### Controller

**Decided 2026-11-22:** the nice!nano (nRF52840) is used for both halves and the desk controller; see [concept.md](concept.md). It is on the [ZMK hardware list](https://zmk.dev/docs/hardware) and provides BLE, USB device support and on-board LiPo charging. The pinned ZMK release is not yet selected. The GPIO budget, charging behaviour and electrical integration still need checking against the published pinout and schematic. (Earlier ESP32-S3 research is in git history before this change; those boards and the in-stock Pico boards are not part of the build.)

Before a PCB commitment, use the ordered nice!nanos to test both halves connected at once to a USB HID central (the dongle build), reconnect and bonding persistence, key events, and representative active, connected-idle, and sleep current. Compare against an agreed runtime target. Distinguish a compile-only result from real measurements. Consult the owner before flashing boards or undertaking physical testing.

### Firmware And Pin Research (2026-11-22)

This is desk research from published sources and the ZMK repository. Nothing has been built,
flashed or measured.

**ZMK version.** From the GitHub API and repository files on 2026-11-22:

| Ref | Date | Zephyr | Dongle docs | `ZMK_RGB_UNDERGLOW_AUTO_OFF_IDLE`, `_EXT_POWER`, `ZMK_IDLE_TIMEOUT` | nice!nano board |
| --- | --- | --- | --- | --- | --- |
| `v0.3.0` (latest release) | 2025-08-01 | `v3.5.0+zmk-fixes` | Yes (`docs/development/hardware-integration/dongle.mdx`) | All present | `nice_nano_v2` (Zephyr hardware model v1) |
| `main` (active; last commit 2026-11-14) | rolling | `v4.1.0+zmk-fixes` | Yes (`docs/hardware-integration/dongle.mdx`) | All present | `nice_nano` with revision `2.0.0` (hardware model v2) |

- **Tradeoff:** v0.3.0 is the only stable release, but it is 15 months old and uses
  Zephyr 3.5. `main` uses Zephyr 4.1 and is where development happens, but it would have
  to be pinned to a specific commit. The board names and some configuration differ between
  them.
- **Toolchain risk:** the devenv shell provides GCC 15 (`gcc-arm-embedded` 15.3) rather
  than the Zephyr SDK, and building Zephyr 3.5 with GCC 15 is unverified. ZMK's standard
  GitHub Actions build, which uses a pinned container image, is the fallback.
- **Gradual fade:** neither ref has a built-in fade-to-black. `AUTO_OFF_IDLE` switches the
  lighting off when the keyboard goes idle.

**Dongle display.** [englmaxi/zmk-dongle-display](https://github.com/englmaxi/zmk-dongle-display)
(MIT; last push 2026-02-21) replaces the status screen on a ZMK dongle.

- **Displays:** 128 × 64 I²C OLEDs, either the 0.96" SSD1306 or the 1.3" SH1106. 128 × 32
  works with some widgets removed.
- **Shows:** active modifiers, layer name, output status and the halves' battery levels.
- **Versions:** it tracks ZMK `main`, and its README says to use its `v0.3` branch with ZMK
  v0.3. For a nice!nano, use `pro_micro_i2c`.

**nice!nano.** Sources: ZMK board files at both refs, and
[nicekeyboards.com docs](https://nicekeyboards.com/docs/nice-nano/).

| | v1 | v2 |
| --- | --- | --- |
| VCC switch (P0.13) | `GPIO_ACTIVE_LOW`: high turns VCC off. The docs' "set it to high" note is the v1 behaviour | `GPIO_ACTIVE_HIGH` (ZMK definition) |
| Battery sense | Voltage divider on P0.04/AIN2, which uses that pin | Internal VDDH monitor (`zmk,battery-nrf-vddh`); no pin |

- **Check on arrival:** the board revision, because firmware differs. Bench-check the VCC
  switch polarity.
- **GPIO:** 18 on the Pro Micro edge, plus 3 on the underside (21 in total, per the docs).
  The edge pins map to P0.08, P0.06, P0.17, P0.20, P0.22, P0.24, P1.00, P0.11, P1.04, P1.06,
  P0.09, P0.10, P1.11, P1.13, P1.15, P0.02, P0.29 and P0.31.
- **Pin use:** P0.09 and P0.10 are the nRF52840's NFC pins. Which pins Nordic limits to
  low-frequency I/O must be checked in the nRF52840 Product Specification before the LED data
  pin is chosen. LED data runs at about 800 kHz.
- **Power:** VCC is "3.3V", with the regulator's current limit not stated. The board charges
  a "3.7v" LiPo from USB-C at about 100 mA, or about 500 mA with the "boost" jumper; the docs
  suggest 100–500 mAh cells at the default rate and up to 2000 mAh. The docs warn LEDs "can eat
  1mA each even when off".
- **Assembly:** do not socket B+ or B−.

**Pin budget per half (proposal, not a pin assignment).**

| Function | Pins | Notes |
| --- | --- | --- |
| 4 × 7 matrix with diodes | 11 | Matrix scanning is low-frequency |
| LED data | 1 | Use a pin Nordic does not restrict |
| LED power | 0 | The board's P0.13-switched VCC, if the LED supply question is settled that way |
| Battery sense | 0 | v2 internal monitor |
| **Total** | **12 of 18** | 6 spare |

**LED supply (option B decided 2026-11-23; see [pcb.md](pcb.md#optional-leds)).** The SK6812MINI-E is rated for 3.7–5.5 V
([datasheet mirror](https://akizukidenshi.com/goodsaffix/sk6812mini-e.pdf)), with VIH ≥ 0.7 VDD.
The nice!nano's switched VCC is 3.3 V, below that range. The options:

| Option | Approach | Tradeoffs |
| --- | --- | --- |
| A | SK6812MINI-E on the 3.3 V switched VCC | Common hobby practice, but out of specification; colour and brightness may suffer. Simplest. Bench test before relying on it |
| B | LEDs on the battery through a GPIO-controlled load switch | 3.0–4.2 V, so in specification only above 3.7 V; the 3.3 V data meets VIH at 4.2 V. One extra part |
| C | 5 V boost plus a level shifter, both switched off when dark | Within specification; more parts and board area |
| D | A reverse-mount addressable LED rated for 3.3 V | None found in this search; needs more research |

- **Current:** whichever option is chosen, lighting needs a brightness cap. 28 LEDs at full
  white draw far more than a small LiPo or the 3.3 V regulator is known to supply.
- **Owner context:** lighting is expected to be used lightly, if at all.

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