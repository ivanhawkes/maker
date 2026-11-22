# PCB Design Brief

Status: design started 2026-11-23. **v0 placement generated, not routed.** Generate with
`python tools/pcb_generate.py`; the boards are written to `pcb/left/left.kicad_pcb` and
`pcb/right/right.kicad_pcb`. Nothing is routed, checked for fabrication, or ordered.

v0 DRC (KiCad 10.0.8): no courtyard overlaps. Expected unrouted connections. 112
copper-to-edge warnings per board, all from the reverse-mount LED footprint's own cut-out,
whose pads sit 0.35 mm from the cut-out. This needs a rule exception checked against the fab
house's minimum. There are also minor silkscreen overlaps. This brief collects
the owner's decisions, the proposed electrical design, and how the boards will be generated
and checked. Decisions are marked **Decided**; everything else is a proposal until reviewed.

## Decisions (Owner, 2026-11-23)

- **Decided:** two separate PCBs, one per half, mirrored and generated from
  [`layout/layout.yaml`](../layout/layout.yaml). Not one reversible PCB.
- **Decided:** bare boards from JLCPCB or PCBWay (fab house still to be chosen), hand-soldered
  by the owner. Parts are chosen to be hand-solderable: no fine-pitch packages.
- **Decided:** the nice!nano sits in low-profile sockets on each half. The battery is never
  socketed. The nice!nano docs say not to fit sockets or headers to B+/B−.
- **Decided:** each half has a 2-pin JST-PH battery connector, a slide power switch and a reset
  button, all reachable from the case edge.
- **Decided earlier:** nice!nano v2, ZMK `main` at a pinned commit, Kailh Speed Bronze switches
  in Kailh MX hot-swap sockets, optional per-key LEDs. The LED supply is to be settled during
  PCB design. The keyboard must work with no LEDs fitted.

## Electrical Design (Proposal)

### Matrix

- **Size:** 4 rows × 7 columns per half. Columns C0–C5 are the finger columns. The thumb keys
  T0–T3 form column 6, one per row. That gives 28 keys and 11 GPIOs.
- **Diodes:** one per switch, oriented for ZMK `col2row`: current flows from column to row,
  with the cathode towards the row. Part: 1N4148W in SOD-123.
- **Pins:** the exact pin assignment will be chosen after placement, to keep routing short.
  Constraints:
  - Matrix lines may use the nRF52840's "low frequency I/O only" pins.
  - Avoid P0.09 and P0.10 (NFC) unless routing needs them. If used, the firmware must enable
    `nfct-pins-as-gpios`, which ZMK's nice!nano board files do not set at the pinned commit.

### nice!nano Pins

From the nRF52840 Product Specification aQFN73 table ("Low frequency I/O is a signal with a
frequency up to 10 kHz") and ZMK's Pro Micro pin map:

| Pro Micro pin | GPIO | Restriction | Proposed use |
| --- | --- | --- | --- |
| D0 | P0.08 | — | Spare |
| D1 | P0.06 | — | **LED data** (about 800 kHz needs an unrestricted pin) |
| D2 | P0.17 | — | Spare |
| D3 | P0.20 | — | Spare |
| D4 | P0.22 | — | Spare |
| D5 | P0.24 | — | Spare |
| D6 | P1.00 | — | Spare |
| D7 | P0.11 | — | Matrix if needed, otherwise spare |
| D8 | P1.04 | ≤ 10 kHz | Matrix |
| D9 | P1.06 | ≤ 10 kHz | Matrix |
| D10 | P0.09 | ≤ 10 kHz, NFC1 | Avoid (see above) |
| D16 | P0.10 | ≤ 10 kHz, NFC2 | Avoid (see above) |
| D14 | P1.11 | ≤ 10 kHz | Matrix |
| D15 | P1.13 | ≤ 10 kHz | Matrix |
| D18/A0 | P1.15 | ≤ 10 kHz | Matrix |
| D19/A1 | P0.02 | ≤ 10 kHz | Matrix |
| D20/A2 | P0.29 | ≤ 10 kHz | Matrix |
| D21/A3 | P0.31 | ≤ 10 kHz | Matrix |

That gives 8 restricted pins plus D7 and up to 2 unrestricted spares for the 11 matrix lines.
The final mapping goes in a pin table that the PCB generator and the ZMK shield both read, so
CAD, PCB and firmware cannot diverge.

### Power

```text
LiPo (protected cell) ── JST-PH ── slide switch ── nice!nano RAW (= BATTERY+)   JST − ── GND
                                                   nice!nano USB-C: charging and flashing
```

- **Battery input:** the official nice!nano v2 pinout image
  ([nicekeyboards.com](https://nicekeyboards.com/docs/nice-nano/pinout-schematic), viewed
  2026-11-23) labels the Pro Micro **RAW** pin "BATTERY+". There is also an extra B+ pad and
  an extra GND pad at the USB end, beyond the 24-pin footprint. The battery therefore reaches
  the board through the socketed RAW pin, and the extra B+/B− pads are left unused and
  unsocketed. To check on the bench: continuity between RAW and B+, and the socket pin's
  current rating against the charge and load current.
- **VCC cutoff:** the same image says "When P0.13 is set low, it will shut off power to the
  3.3V VCC pin", which agrees with ZMK's v2 `GPIO_ACTIVE_HIGH`. Its high- and low-frequency
  pin legend matches the Nordic table above.
- **Antenna:** its position on the module has not been verified. The generator puts a copper
  keep-out (no tracks, vias or fills) under the whole controller on both layers.

- **Switch placement:** the switch sits between the cell and B+. With the switch off the cell
  is fully disconnected, so it **does not charge**. This is the usual behaviour for nice!nano
  keyboards and must be stated in the operating notes. An alternative that charges while off
  is possible but more complex. **To review.**
- **Charging:** about 100 mA by default, or about 500 mA with the nice!nano's "boost" jumper.
  The cell choice must allow for the charge rate (battery design is deferred; see
  [decisions.md](decisions.md)).
- **Connector polarity:** JST-PH cells are sold with both polarities. The silkscreen will mark
  + and −. Check every cell before connecting.
- **Reset button:** connects the nice!nano RST pin to GND. Double-tap enters the UF2
  bootloader.

### Optional LEDs

- **Footprint:** a reverse-mount SK6812MINI-E position under each switch (KiCad stock
  `LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount`), daisy-chained, with data from D1/P0.06.
- **Supply:** to be decided. The options are in
  [architecture.md](architecture.md#firmware-and-pin-research-2026-11-22).
- **Requirement:** the PCB must work with the LEDs and their supply parts left unfitted.

## Parts And Footprints (Candidates, To Verify Against Datasheets)

| Part | Candidate | Footprint source | Notes |
| --- | --- | --- | --- |
| Hot-swap socket | Kailh CPG151101S11 (MX) | [marbastlib](https://github.com/ebastler/marbastlib) `SW_MX_HS_CPG151101S11_1u` / `_1.5u`, CERN-OHL-P-2.0, commit `6b0a9a7` | Check against the Kailh drawing; the 1.5u caps on T2/T3 still use a 1u switch footprint |
| Diode | 1N4148W, SOD-123 | KiCad stock `Diode_SMD` | Hand-solderable |
| Controller | nice!nano v2 on low-profile sockets, mounted components up ("USB topside") | marbastlib experimental `ProMicro_Reversible_Single` | Battery enters through RAW. Check the pad and hole sizes against the chosen low-profile socket pins |
| LED (optional) | SK6812MINI-E | KiCad stock, reverse mount | Supply open |
| Battery connector | JST-PH 2-pin (S2B-PH, side entry) | KiCad stock `Connector_JST` | Polarity marked |
| Power switch | Hand-solderable SMD or THT slide switch, edge-mounted | To choose | Rated for the cell's current |
| Reset button | Small tactile switch, edge-accessible | To choose | |

Third-party footprints will be copied into the project at a pinned commit with their licence
file, so the design is reproducible.

## How The Boards Are Made (Planned)

1. A pin table (one source) feeds both the PCB generator and the ZMK shield.
2. A Python generator using KiCad 10's `pcbnew` API (verified importable: 10.0.8) places every
   switch, diode and LED footprint from `layout/generated/*.csv`. It then places the controller,
   connector, switch and reset button, and writes the left and right boards. The right board is
   built from the mirrored layout, with its footprints placed for the right half, not copied
   mirror-image, so the parts remain real parts.
3. The schematic and netlist come from the same generator, so ERC and the
   schematic-to-PCB consistency check work.
4. Routing is first done with Freerouting (to add to the devenv) or scripted. It is then
   checked with `kicad-cli pcb drc` against the chosen fab house's rules, and reviewed.
5. Fabrication outputs (Gerbers, drill files and a BOM for hand assembly) come from
   `kicad-cli`, plus a 3D STEP of the assembled board for case design.

## Ordering Checklist

- **Owner reminder (2026-11-23):** order a **solder-paste stencil** with the PCBs (owner
  confirmed). It is a separate add-on at both fab houses, used to apply paste to the SMD pads
  of the sockets and diodes. Order one per board design (left and right). Generate the paste
  layer for the side the SMD parts are on, which is the bottom.

**Gate before ordering:** ERC and DRC are clean, every footprint is checked against its
datasheet, the matrix and pin map match the ZMK shield, the owner has reviewed the board, and
the owner has approved the order.
