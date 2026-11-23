# Parts: Footprints, 3D Models And Datasheets

Local copies of everything about the parts that the PCBs are built from, collected on
2026-11-23, so the boards can be generated, checked and understood without the network or a
particular KiCad library version. The parts themselves, quantities and distributor numbers are
in [docs/pcb.md](../docs/pcb.md#provisional-parts-list-2026-11-23).

**None of this is verified against physical parts.** Footprints have not been measured against
the bought parts, and the 3D models have not been opened or checked for scale and orientation.

## Layout

| Folder | Contents |
| --- | --- |
| `footprints/kicad/` | The nine KiCad stock footprints the generator uses, with `SOURCE.txt`, `LICENSE.md` and checksums |
| `footprints/marbastlib/` | The hot-swap socket and Pro Micro footprints, pinned to marbastlib commit `6b0a9a7` |
| `3d/kicad/` | STEP models for the KiCad footprints |
| `3d/third-party/` | STEP models from other open repositories, with `SOURCES.tsv` |
| `3d/third-party/klp-lame/` | The KLP Lamé keycap models, MX stem, in both MX and Choc size, with the repository's `LICENSE` |
| `datasheets/` | Manufacturer datasheets and drawings, with `SOURCES.tsv` (URL, date, sha256, owner) |

`tools/pcb_generate.py` loads every footprint from `footprints/`; nothing comes from the
installed KiCad libraries.

## Parts

| Ref | Part | Footprint | 3D model | Datasheet |
| --- | --- | --- | --- | --- |
| SW1–28 (socket) | Kailh CPG151101S11 MX hot-swap socket | `marbastlib/marbastlib-mx.pretty/SW_MX_HS_CPG151101S11_1u` | `third-party/HS_CPG151101S11_MX.step` | `Kailh_CPG151101S11_MX_hot-swap_socket.pdf` |
| (key switch) | Kailh Speed Bronze, CPG151101D214 | Fits the socket footprint | `third-party/SW_Cherry_MX_PCB.step`, `cherry-mx-switch_ConstantinoSchillebeeckx.step` (generic MX) | `Kailh_CPG151101D214_Speed_Bronze_switch_spec.pdf` |
| (keycaps) | KLP Lamé, MX stem, black: a moulded set of 60 with four 1.5u (owner) | — | `third-party/klp-lame/mx-stem-mx-size/` (12 kinds); `mx-stem-choc-size/` in case the set is that size | — |
| D1–28 | Diodes 1N4148W-7-F | `kicad/Diode_SMD.pretty/D_SOD-123` | `kicad/D_SOD-123.step` | `Diodes_1N4148W_switching_diode_SOD-123.pdf` |
| LED1–28 | SK6812MINI-E (optional) | `kicad/LED_SMD.pretty/LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount` | `kicad/LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount.step` | `SK6812MINI-E_Opsco_rev02.pdf` |
| U1 | nice!nano v2 (nRF52840) | `marbastlib/marbastlib-xp-promicroish.pretty/ProMicro_Reversible_Single` | `third-party/Nice_Nano_V2.step` | `nice-nano_v2_pinout.png`, `nice-nano_v2_schematic.png`, `Nordic_nRF52840_Product_Specification_v1.11.pdf` |
| (U1 sockets) | Mill-Max 315-43-112-41-003000 strip, 3320-0-00-15-00-00-03-0 pins | U1's holes | — | `MillMax_310_311_315_series_socket_catalog_page.pdf`, `MillMax_3320-0-00-15-00-00-03-0_pin_DigiKey.pdf` |
| J1 | JST S2B-PH-K-S | `kicad/Connector_JST.pretty/JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal` | `kicad/JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal.step` | `JST_PH_connector_series.pdf` |
| H1–4 | Mounting hole, M3 (no part) | `kicad/MountingHole.pretty/MountingHole_3.2mm_M3` | — | — |
| SW_PWR | C&K PCM12SMTR | `kicad/Button_Switch_SMD.pretty/SW_SPDT_PCM12` | `kicad/SW_SPDT_PCM12.step` | `CK_PCM_series_slide_switch_PCM12.pdf` |
| SW_RST | E-Switch TL3342F160QG | `kicad/Button_Switch_SMD.pretty/SW_SPST_TL3342` | `kicad/SW_SPST_TL3342.step` | `E-Switch_TL3342_series_tactile_switch.pdf`, `E-Switch_TL3342F160QG_drawing.pdf` |
| Q1 | Diodes DMG2305UX-7 (P-MOSFET) | `kicad/Package_TO_SOT_SMD.pretty/SOT-23_Handsoldering` | `kicad/SOT-23.step` | `Diodes_DMG2305UX_P-channel_MOSFET_SOT-23.pdf` |
| Q2 | onsemi BSS138 (N-MOSFET) | Same | Same | `onsemi_BSS138_N-channel_MOSFET_SOT-23.pdf` |
| R1, R2 | Yageo RC1206FR-07100KL | `kicad/Resistor_SMD.pretty/R_1206_3216Metric_Pad1.30x1.75mm_HandSolder` | `kicad/R_1206_3216Metric.step` | `Yageo_RC_series_chip_resistors.pdf` |
| C1 | Samsung CL31A106KAHNNNE | `kicad/Capacitor_SMD.pretty/C_1206_3216Metric_Pad1.33x1.80mm_HandSolder` | `kicad/C_1206_3216Metric.step` | `Samsung_CL31A106KAHNNNE_10uF_25V_X5R_1206_spec.pdf` |
| (battery) | Core Electronics CE04375, 400 mAh, 38 × 25 × 6 mm, JST-PH: the cell the case is designed around ([case.md](../docs/case.md)); not ordered | — | — | `CoreElectronics_CE04375_LiPo_400mAh_PCM_datasheet.pdf` (the protection board only; no cell datasheet is published). `Adafruit_1578_LiPo_500mAh_datasheet.pdf`, `Adafruit_258_LiPo_1200mAh_503562.pdf` are examples of the type |

## Read From These Files (2026-11-23)

- **DMG2305UX** (DS36196 Rev. 8-2): −20 V, gate ±8 V, threshold −0.5 to −0.9 V, 100 mΩ maximum
  at −2.5 V. SOT-23 top view: gate and source on the two-pin side, drain alone, so pin 1 gate,
  pin 2 source, pin 3 drain, as the board has it.
- **BSS138** (Rev. 7): 50 V, 0.22 A, threshold 0.8 to 1.5 V. Pin 1 gate, 2 source, 3 drain.
- **SK6812MINI-E** (Rev. 02): body 3.2 × 2.8 mm ±0.1, leads 5.88 mm tip to tip, supply
  3.7–5.5 V, input high at 0.7 × VDD, about 1 mA when dark.
- **SK6812MINI-E**, more: 12 mA a colour; pins 1 VDD, 2 DOUT, 3 GND (cut corner), 4 DIN; the
  application notes ask for a series resistor on the data line and a capacitor at each LED;
  moisture sensitivity level 5a (24 hours out of the bag).
- **nRF52840 Product Specification v1.11** (2024-10-01): the source for the pins limited to
  low-frequency I/O.
- **nice!nano v2 pinout image:** 13 holes a side. The pair at the USB end is B+ and B−; RAW is
  also labelled BATTERY+. P0.13 low cuts the 3.3 V VCC pin. Charging is 100 mA, or 500 mA with
  the BOOST jumper bridged (only for cells over 500 mAh).
- **Kailh CPG151101S11 socket** (KH-PS1607-10 rev. B): 12 V, 10 mA; 100 mating cycles; hand
  solder at 350 °C for 3 s; barrel ø2.90 ± 0.05; drawn for a single-sided 1.6 mm board.
- **Kailh CPG151101D214 switch** (KH-PS1705-24): 50 ± 10 gf, pre-travel 1.1 ± 0.4 mm, total
  3.5 ± 0.4 mm, 12 V 10 mA, 70 million cycles; plate cut-out 14.00 ± 0.05, plate 1.5 ± 0.1 thick,
  5.0 from plate top to board. A 5.125 dimension on the pattern drawing was not resolved.
- **Mill-Max:** 315-…-003000 (catalogue Fig. 4) has a ø0.030 in tail and accepts ø0.015–0.022 in
  pins; the 3320-0 pin is ø0.020 in, 0.250 in long.
- **JST PH:** 2 A, 100 V, for 0.8–1.6 mm boards. **PCM12:** 0.3 A at 6 V DC, 10,000 cycles.
  **TL3342F160QG:** 12 V DC 50 mA, 160 ± 50 gf, 0.25 mm travel, 100,000 cycles.
- **1N4148W** (DS30086 Rev. 32-2): SOD-123, 3.55–3.85 across the leads.

## Footprint Check Against Datasheets (2026-11-23)

Each footprint as placed on the generated boards (`python tools/pcb_pads.py <board> <refs>`,
KiCad 10.0.8) compared with the drawings in `datasheets/`. **A paper check only: nothing was
measured against a bought part.**

| Part | Datasheet says | Board has | Result |
| --- | --- | --- | --- |
| Hot-swap socket | Holes ø3.00, 6.35 apart and 2.54 offset; pads 2.55 × 2.5; body 10.90, leads 14.50 tip to tip | Holes ø3.0 at those offsets; pads 2.55 × 2.5 starting at the body edge, 0.75 mm past the lead tips | Matches. Handedness checked on both halves |
| Key switch | Pins at (3.81, 2.54) and (2.54, 5.08) from centre; centre hole ø3.99 ± 0.1; fixation holes ø1.70 ± 0.05 | Same pin positions seen from the top, on both halves (the right half is not mirror-image); ø3.988; ø1.75 at ±5.08 | Matches. LED is 5.08 from centre on the side away from the pins |
| LED | Pads 0.82 wide at 1.5 pitch; body 3.2 × 2.8 ± 0.1; leads 5.88 tip to tip; seen from the lens: 1 VDD and 2 DOUT on one side, 4 DIN and 3 GND on the other, cut corner at 3 | Pads 0.82 × 1.35 at 1.5 pitch covering 0.83 mm of each lead; cut-out 3.4 × 3.0; same pin order seen from the back | Matches. The silkscreen mark was at pin 1; the generator now draws it at pin 3, the part's cut corner (below) |
| Controller | Pinout image: 13 holes a side; the pair at the USB end is B+ and B−, then the 12 Pro Micro positions | 12 pads a side, pad 1 = D1 (P0.06), pad 13 = RAW, 15.24 between rows; left seen from the front, right seen from the back | Matches `pcb/pins.yaml` and the upside-down right half. B+ and B− get no socket |
| Controller sockets | 315-…-003000: tail ø0.030 in (0.76 mm), accepts pins ø0.015–0.022 in. 3320 pin: ø0.020 in (0.51 mm) | Holes ø1.0 | Fits, 0.24 mm clear. Seated height not read: the catalogue figure is ambiguous |
| JST S2B-PH-K-S | Holes ø0.7 +0.1, pitch 2.0; circuit 1 is 1.95 from the side wall, body 6.25 deep | Holes ø0.75, pitch 2.0, pads 1.27 × 1.75; pad 1 = battery +, opening towards the thumb keys | Matches. Battery polarity is not in any datasheet: meter it |
| PCM12 slide switch | Terminals 0.7 wide, 1–2 3.0 apart, 2–3 1.5; pegs ø0.8 in ø0.9 holes 3.0 apart; on with 1–2 joined; 0.3 A at 6 V | Same; pad 1 RAW, pad 2 battery, pad 3 open | Footprint matches. It was placed with the actuator facing the controller; fixed (below) |
| TL3342 reset | Pads 1.7 × 1.0 at ±3.15, ±1.9; the two terminals of a row are joined | Same; each row is one net (RST, GND) | Matches. Terminal numbers are "for reference only": meter one before soldering |
| 1N4148W | SOD-123, leads 3.55–3.85 overall; suggested pads 0.9 × 0.95, 4.05 overall | Pads 0.9 × 1.2, 4.2 overall; pad 1 (cathode) on the row | Matches |
| DMG2305UX, BSS138 | SOT-23, 2.25–2.55 across the leads, 0.95 pitch; 1 gate, 2 source, 3 drain | Hand-solder pads 0.8 × 1.9 covering the suggested ones; Q1 source on RAW, Q2 source on GND | Matches (BSS138 package table not read: the PDF's text does not extract) |
| 1206 resistor and capacitor | — | KiCad stock hand-solder 1206 | Not compared: standard package |

**Found.**

- **Power switch faced the wrong way. Fixed 2026-11-23.** The actuator pointed at the controller
  and, by the footprint's outline, its tip reached the socket strip, under the edge of the
  module. The generator now puts the switch on the board edge, turned 11.5° to lie along it,
  with the actuator overhanging by 1.0 mm (owner's decision). The mount pads' copper is 0.32 mm
  from the edge. On is the slider towards the user on both halves: RAW is on pad 1 on the left
  and pad 3 on the right, where the switch is turned the other way.
- **LED orientation mark. Fixed 2026-11-23.** KiCad's footprint marks pin 1 (VDD) with a
  triangle and a cut corner in the silkscreen. The part's own cut corner is at pin 3 (GND),
  diagonally opposite, so an LED fitted cut corner to cut corner would be reversed across the
  supply. The generator now turns the drawing half a turn (owner's decision): the triangle and
  cut corner are at pin 3, and the generator stops if they are not. **Fit each LED with its cut
  corner at the mark.**
- The slide switch is rated 0.3 A. Battery charging and the LED supply both pass through it, so
  it caps the LED current and rules out the nice!nano's 500 mA charge jumper. Reviewed
  2026-11-23: the two currents do not add
  ([pcb.md](../docs/pcb.md#electrical-review-2026-11-23), finding 4).
- The socket holes are plated at ø3.0, and Kailh draws ø3.00 for a single-sided board. A plated
  hole at the bottom of its tolerance (2.92) is smaller than the largest barrel (2.95). marbastlib
  boards are made this way; noted, not changed.
- The board ran past the controller's USB end by about 1 mm at one corner and 12 mm at
  the other, under the plug. **Settled 2026-11-23:** the outline is notched there, 13 mm wide
  ([pcb.md](../docs/pcb.md#v4-notches-and-mounting-holes-2026-11-23)).
- **Power switch overhang, 2026-11-23.** The edge is now notched between the switch's outer
  mount pads, so the slider overhangs by 1.85 mm. The notch stops 0.52 mm from the holes of the
  switch's two locating pegs (ø0.9 at ±1.5, 0.33 in the footprint), which is why it is not
  deeper. The body overhangs the notch by 0.3 mm.

## Symbols

`symbols/keyboard.kicad_sym` holds the schematic symbols, written by
`python tools/sch_generate.py --extract-symbols <KiCad symbols directory>` (`symbols/SOURCE.txt`
lists where each came from). Ten are copied from KiCad's libraries with derived symbols made
standalone; the controller's is generated from `pcb/pins.yaml`.

**The LED symbol is renumbered.** KiCad's SK6812MINI-E symbol numbers the part half a turn
round from the Opsco datasheet (KiCad: 1 VSS, 2 DIN, 3 VDD, 4 DOUT; datasheet: 1 VDD, 2 DOUT,
3 GND, 4 DIN). The board uses the datasheet's numbers, so the copy here does too
([details](../docs/pcb.md#schematic-2026-11-23)).

## Licences

| Files | Licence or owner |
| --- | --- |
| `footprints/kicad/`, `3d/kicad/`, `symbols/` | KiCad libraries: CC-BY-SA 4.0 with the KiCad exception (`LICENSE.md`) |
| `footprints/marbastlib/`, `3d/third-party/HS_CPG151101S11_MX.step` | marbastlib, CERN-OHL-P v2 |
| `3d/third-party/SW_Cherry_MX_PCB.step` | kiswitch, dual MIT / CC-BY-SA 4.0 |
| `3d/third-party/cherry-mx-switch_ConstantinoSchillebeeckx.step` | MIT, © 2017 Constantino Schillebeeckx |
| `3d/third-party/Nice_Nano_V2.step` | infused-kim/kb_ergogen_fp, CC BY-NC-SA 4.0: **non-commercial**. A community model, not from Nice Keyboards |
| `3d/third-party/klp-lame/` | braindefender/KLP-Lame-Keycaps, CC BY-SA 4.0 (`klp-lame/LICENSE`). Credit the author and repository wherever the models or pictures of them are shown |
| `datasheets/` | Each manufacturer's copyright (`SOURCES.tsv`). Kept for reference. The Kailh socket specification carries a "Confidential" footer; it came from a public GitHub mirror |

## Known Gaps

- Five datasheets are distributor or community mirrors, because the manufacturer's site refused
  the download: Samsung (DigiKey), both Mill-Max (DigiKey), Kailh socket (GitHub), nRF52840
  (Farnell). `SOURCES.tsv` marks them.
- Mill-Max: the socket file is a catalogue page for the series, in inches; the exact part's
  drawing was not obtained.
- The nice!nano schematic and pinout are published as images only.
- The keycap models are the published design (commit `8e4b89b`), not the moulded caps: the
  owner's set is to be measured against them when it arrives. The set of 60 is a mix of saddle
  and non-saddle caps, with enough saddles for all the top and bottom rows (owner); the exact
  kinds, and whether it is MX or Choc size, are not confirmed yet. Only the MX-stem models are
  kept here.
- `Nice_Nano_V2.step` is named "Flipped MCU only" inside the file: check its orientation and
  what it includes before using it for the case.
- No datasheet for the Australian battery candidates (Little Bird LB-00237 and others).
- The footprint check above is against datasheets only. Still to do: measure the bought parts
  against a 1:1 print of the board before ordering it. The prints are in `pcb/print/` (made
  2026-11-23; how to print and check the scale is in [pcb.md](../docs/pcb.md)). Nothing is
  measured yet.
