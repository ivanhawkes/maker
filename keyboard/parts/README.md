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
| `footprints/kicad/` | The eight KiCad stock footprints the generator uses, with `SOURCE.txt`, `LICENSE.md` and checksums |
| `footprints/marbastlib/` | The hot-swap socket and Pro Micro footprints, pinned to marbastlib commit `6b0a9a7` |
| `3d/kicad/` | STEP models for the KiCad footprints |
| `3d/third-party/` | STEP models from other open repositories, with `SOURCES.tsv` |
| `datasheets/` | Manufacturer datasheets and drawings, with `SOURCES.tsv` (URL, date, sha256, owner) |

`tools/pcb_generate.py` loads every footprint from `footprints/`; nothing comes from the
installed KiCad libraries.

## Parts

| Ref | Part | Footprint | 3D model | Datasheet |
| --- | --- | --- | --- | --- |
| SW1–28 (socket) | Kailh CPG151101S11 MX hot-swap socket | `marbastlib/marbastlib-mx.pretty/SW_MX_HS_CPG151101S11_1u` | `third-party/HS_CPG151101S11_MX.step` | `Kailh_CPG151101S11_MX_hot-swap_socket.pdf` |
| (key switch) | Kailh Speed Bronze, CPG151101D214 | Fits the socket footprint | `third-party/SW_Cherry_MX_PCB.step`, `cherry-mx-switch_ConstantinoSchillebeeckx.step` (generic MX) | `Kailh_CPG151101D214_Speed_Bronze_switch_spec.pdf` |
| D1–28 | Diodes 1N4148W-7-F | `kicad/Diode_SMD.pretty/D_SOD-123` | `kicad/D_SOD-123.step` | `Diodes_1N4148W_switching_diode_SOD-123.pdf` |
| LED1–28 | SK6812MINI-E (optional) | `kicad/LED_SMD.pretty/LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount` | `kicad/LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount.step` | `SK6812MINI-E_Opsco_rev02.pdf` |
| U1 | nice!nano v2 (nRF52840) | `marbastlib/marbastlib-xp-promicroish.pretty/ProMicro_Reversible_Single` | `third-party/Nice_Nano_V2.step` | `nice-nano_v2_pinout.png`, `nice-nano_v2_schematic.png`, `Nordic_nRF52840_Product_Specification_v1.11.pdf` |
| (U1 sockets) | Mill-Max 315-43-112-41-003000 strip, 3320-0-00-15-00-00-03-0 pins | U1's holes | — | `MillMax_310_311_315_series_socket_catalog_page.pdf`, `MillMax_3320-0-00-15-00-00-03-0_pin_DigiKey.pdf` |
| J1 | JST S2B-PH-K-S | `kicad/Connector_JST.pretty/JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal` | `kicad/JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal.step` | `JST_PH_connector_series.pdf` |
| SW_PWR | C&K PCM12SMTR | `kicad/Button_Switch_SMD.pretty/SW_SPDT_PCM12` | `kicad/SW_SPDT_PCM12.step` | `CK_PCM_series_slide_switch_PCM12.pdf` |
| SW_RST | E-Switch TL3342F160QG | `kicad/Button_Switch_SMD.pretty/SW_SPST_TL3342` | `kicad/SW_SPST_TL3342.step` | `E-Switch_TL3342_series_tactile_switch.pdf`, `E-Switch_TL3342F160QG_drawing.pdf` |
| Q1 | Diodes DMG2305UX-7 (P-MOSFET) | `kicad/Package_TO_SOT_SMD.pretty/SOT-23_Handsoldering` | `kicad/SOT-23.step` | `Diodes_DMG2305UX_P-channel_MOSFET_SOT-23.pdf` |
| Q2 | onsemi BSS138 (N-MOSFET) | Same | Same | `onsemi_BSS138_N-channel_MOSFET_SOT-23.pdf` |
| R1, R2 | Yageo RC1206FR-07100KL | `kicad/Resistor_SMD.pretty/R_1206_3216Metric_Pad1.30x1.75mm_HandSolder` | `kicad/R_1206_3216Metric.step` | `Yageo_RC_series_chip_resistors.pdf` |
| C1 | Samsung CL31A106KAHNNNE | `kicad/Capacitor_SMD.pretty/C_1206_3216Metric_Pad1.33x1.80mm_HandSolder` | `kicad/C_1206_3216Metric.step` | `Samsung_CL31A106KAHNNNE_10uF_25V_X5R_1206_spec.pdf` |
| (battery) | 1S LiPo with protection and JST-PH lead; cell not chosen | — | — | `Adafruit_1578_LiPo_500mAh_datasheet.pdf`, `Adafruit_258_LiPo_1200mAh_503562.pdf` (examples of the type) |

## Read From These Files (2026-11-23)

- **DMG2305UX** (DS36196 Rev. 8-2): −20 V, gate ±8 V, threshold −0.5 to −0.9 V, 100 mΩ maximum
  at −2.5 V. SOT-23 top view: gate and source on the two-pin side, drain alone, so pin 1 gate,
  pin 2 source, pin 3 drain, as the board has it.
- **BSS138** (Rev. 7): 50 V, 0.22 A, threshold 0.8 to 1.5 V. Pin 1 gate, 2 source, 3 drain.
- **SK6812MINI-E** (Rev. 02): body 3.2 × 2.8 mm ±0.1, leads 5.88 mm tip to tip, supply
  3.7–5.5 V, input high at 0.7 × VDD, about 1 mA when dark.
- **nRF52840 Product Specification v1.11** (2024-10-01): the source for the pins limited to
  low-frequency I/O.

## Licences

| Files | Licence or owner |
| --- | --- |
| `footprints/kicad/`, `3d/kicad/` | KiCad libraries: CC-BY-SA 4.0 with the KiCad exception (`LICENSE.md`) |
| `footprints/marbastlib/`, `3d/third-party/HS_CPG151101S11_MX.step` | marbastlib, CERN-OHL-P v2 |
| `3d/third-party/SW_Cherry_MX_PCB.step` | kiswitch, dual MIT / CC-BY-SA 4.0 |
| `3d/third-party/cherry-mx-switch_ConstantinoSchillebeeckx.step` | MIT, © 2017 Constantino Schillebeeckx |
| `3d/third-party/Nice_Nano_V2.step` | infused-kim/kb_ergogen_fp, CC BY-NC-SA 4.0: **non-commercial**. A community model, not from Nice Keyboards |
| `datasheets/` | Each manufacturer's copyright (`SOURCES.tsv`). Kept for reference. The Kailh socket specification carries a "Confidential" footer; it came from a public GitHub mirror |

## Known Gaps

- Five datasheets are distributor or community mirrors, because the manufacturer's site refused
  the download: Samsung (DigiKey), both Mill-Max (DigiKey), Kailh socket (GitHub), nRF52840
  (Farnell). `SOURCES.tsv` marks them.
- Mill-Max: the socket file is a catalogue page for the series, in inches; the exact part's
  drawing was not obtained.
- The nice!nano schematic and pinout are published as images only.
- `Nice_Nano_V2.step` is named "Flipped MCU only" inside the file: check its orientation and
  what it includes before using it for the case.
- No datasheet for the Australian battery candidates (Little Bird LB-00237 and others).
- Still to do: check each footprint against its datasheet (the open item in docs/pcb.md).
