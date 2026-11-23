# PCB Design Brief

Status: design started 2026-11-23. **v4 (4-layer, with the case's notches and mounting holes): both boards fully routed by script, DRC clean.**
Generate and route with `python tools/pcb_generate.py` (no autorouter; about 15 s); the boards
are written to `pcb/left/left.kicad_pcb` and `pcb/right/right.kicad_pcb`. Nothing is checked for
fabrication, or ordered, and the footprints are unverified against parts. Each half has a
[schematic](#schematic-2026-11-23) drawn from its board: ERC is clean and it matches the board.
The [electrical review](#electrical-review-2026-11-23) found no routing fault; its six proposals
were accepted and the board changes [applied](#applied-2026-11-23) the same day. Results are in [v3](#v3-scripted-routing-2026-11-23) and [v4](#v4-notches-and-mounting-holes-2026-11-23); the method, every template and the findings are in
[pcb-routing.md](pcb-routing.md). Check a generated board with `python tools/pcb_check.py`.
This brief collects
the owner's decisions, the proposed electrical design, and how the boards will be generated
and checked. Decisions are marked **Decided**; everything else is a proposal until reviewed.

## Decisions (Owner, 2026-11-23)

- **Decided (2026-11-23):** the three board changes the case design asked for: a notch under
  the USB plug, four M3 mounting holes, and more overhang for the power switch's slider
  ([v4](#v4-notches-and-mounting-holes-2026-11-23)).
- **Decided (2026-11-23):** four layers: signals outside, a GND plane (In1.Cu) and a VLED
  plane (In2.Cu) inside. Two layers left 48 and 58 connections unrouted.
- **Decided (2026-11-23):** on the right half the nice!nano mounts upside down (components
  towards the PCB), so its pins mirror and both halves route alike. To check at assembly: the
  parts on its underside clear the board on low-profile sockets.
- **Decided (2026-11-23):** routing is scripted and deterministic, not auto-routed
  ([v3](#v3-scripted-routing-2026-11-23)).
- **Decided (2026-11-23):** parts from Mouser (default) or DigiKey, except what neither sells
  (see [provisional parts list](#provisional-parts-list-2026-11-23)).
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

| Pro Micro pin | Pad | GPIO | Restriction | Use (v3, `pcb/pins.yaml`) |
| --- | --- | --- | --- | --- |
| D1 | 1 | P0.06 | — | Row R1 |
| D0 | 2 | P0.08 | — | Column C2 |
| D2 | 5 | P0.17 | — | Column C1 |
| D3 | 6 | P0.20 | — | Column C0 |
| D4 | 7 | P0.22 | — | Row R2 |
| D5 | 8 | P0.24 | — | Column C4 |
| D6 | 9 | P1.00 | — | Column C3 |
| D7 | 10 | P0.11 | — | **LED data** (about 800 kHz needs an unrestricted pin) |
| D8 | 11 | P1.04 | ≤ 10 kHz | Column C5 |
| D9 | 12 | P1.06 | ≤ 10 kHz | Row R3 |
| D21/A3 | 17 | P0.31 | ≤ 10 kHz | LED supply enable (static level) |
| D20/A2 | 18 | P0.29 | ≤ 10 kHz | Spare |
| D19/A1 | 19 | P0.02 | ≤ 10 kHz | Spare |
| D18/A0 | 20 | P1.15 | ≤ 10 kHz | Spare |
| D15 | 21 | P1.13 | ≤ 10 kHz | Thumb column T |
| D14 | 22 | P1.11 | ≤ 10 kHz | Row R4 |
| D16 | 23 | P0.10 | ≤ 10 kHz, NFC2 | Avoid (see above) |
| D10 | 24 | P0.09 | ≤ 10 kHz, NFC1 | Avoid (see above) |

The inner pads (1–12) are assigned top to bottom in the order the scripted tracks arrive beside
the controller, so no fan-in crosses another. `pcb/pins.yaml` is the single source: the PCB
generator reads it, and the ZMK shield will, so CAD, PCB and firmware cannot diverge.

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
- **Antenna:** its position on the module has not been verified. The generator's copper
  keep-outs (`CONTROLLER_KEEPOUTS`) cover the area between the two pin rows and a strip beyond
  the module's far end from USB (plan −y), where the antenna is expected. v0 kept out the whole
  controller, pads included, so no track could reach it.

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

- **Footprint:** a reverse-mount SK6812MINI-E position under each switch, daisy-chained, with
  data from D1/P0.06. KiCad's stock `LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount` with its
  pads moved 0.06 mm outward (`LED_PAD_SHIFT`): stock, they sit 0.247 mm from the cut-out,
  under the 0.3 mm copper-to-edge rule. The cut-out (3.4 × 3.0 mm) cannot shrink: the body is
  3.2 × 2.8 mm ±0.1 mm (Opsco datasheet Rev. 02, p. 4). The leads, 5.88 mm tip to tip, still
  overlap the pads by about 0.8 mm. A no-track area covers each cut-out plus 0.3 mm, because
  Freerouting does not treat a footprint's cut-out as board edge.
- **Supply: option B (Decided, owner 2026-11-23).** The battery (RAW, 3.0–4.2 V) through a
  high-side switch, off unless the firmware turns it on:

  ```text
  RAW ──┬──────┬────── Q1 source      Q1 DMG2305UX (P-MOSFET, SOT-23)
        R1     C2      Q1 drain ──┬── VLED ── LED VDD pins
        100k   1 µF               C1 10 µF ── GND
  LED_GATE ────┴────── Q1 gate
        R3 10k
  LED_GATE_DRV ─────── Q2 drain     Q2 BSS138 (N-MOSFET, SOT-23), source to GND
  LED_EN (pad 17, P0.31) ── Q2 gate, R2 100k to GND
  LED_DATA (pad 10, P0.11) ── R4 470 Ω ── LED_DIN ── first LED
  ```

  R3 and C2 are the soft start and R4 the data resistor, added after the
  [electrical review](#applied-2026-11-23). R3 and R4 are in series: each needs its resistor or
  a 0 Ω link, or the LEDs stay off. C2 may be left off.

  Q2 is needed because a 3.3 V GPIO cannot turn the P-MOSFET fully off when its source is at
  4.2 V. R2 keeps the LEDs off while the controller is off or resetting. Passives are 1206
  (owner's preferred size), with hand-solder pads.
- **Datasheet values (Rev. 02):** supply 3.7–5.5 V; DIN high at 0.7 × VDD or more (2.94 V at
  4.2 V; the controller drives 3.3 V); about 1 mA each when dark, so about 28 mA per half,
  hence the hardware switch; 12 mA per colour channel. Below 3.7 V of battery the LEDs are out
  of specification: colours may shift or fail. A brightness cap in firmware is required.
- **VLED width:** signal width (0.25 mm). At the 0.5 mm power width Freerouting could not pass
  between the LED pads.
- **To check on the bench:** DIN at a full battery (4.2 V), and the controller staying up when
  Q1 switches C1 and the LEDs on (inrush).
- **Firmware (to verify):** ZMK's external-power control on P0.31 instead of the board's
  P0.13 VCC switch.
- **Requirement:** the PCB must work with the LEDs and their supply parts left unfitted.

## Parts And Footprints (Candidates, To Verify Against Datasheets)

| Part | Candidate | Footprint source | Notes |
| --- | --- | --- | --- |
| Hot-swap socket | Kailh CPG151101S11 (MX) | [marbastlib](https://github.com/ebastler/marbastlib) `SW_MX_HS_CPG151101S11_1u` / `_1.5u`, CERN-OHL-P-2.0, commit `6b0a9a7` | Check against the Kailh drawing; the 1.5u caps on T2/T3 still use a 1u switch footprint |
| Diode | 1N4148W, SOD-123 | KiCad stock `Diode_SMD` | Hand-solderable |
| Controller | nice!nano v2 on low-profile sockets, mounted components up ("USB topside") | marbastlib experimental `ProMicro_Reversible_Single` | Battery enters through RAW. Check the pad and hole sizes against the chosen low-profile socket pins |
| LED (optional) | SK6812MINI-E | KiCad stock, reverse mount, pads moved 0.06 mm out | Supply: option B |
| LED switch (optional) | AO3401A P-MOSFET, 2N7002 N-MOSFET | KiCad stock `SOT-23_Handsoldering` | Pinout 1 G, 2 S, 3 D: check the bought parts |
| Passives (optional) | 100k resistors ×2, 10 µF 10 V X5R capacitor, 1206 | KiCad stock `*_1206_3216Metric_*_HandSolder` | |
| Battery connector | JST-PH 2-pin (S2B-PH, side entry) | KiCad stock `Connector_JST` | Polarity marked |
| Power switch | Hand-solderable SMD or THT slide switch, edge-mounted | To choose | Rated for the cell's current |
| Reset button | Small tactile switch, edge-accessible | To choose | |

Every footprint the generator uses, a 3D model for each part, and the datasheets are kept in the
project, in [`parts/`](../parts/README.md), with their sources, licences and checksums.

## How The Boards Are Made (Planned)

1. A pin table (one source) feeds both the PCB generator and the ZMK shield.
2. A Python generator using KiCad 10's `pcbnew` API (verified importable: 10.0.8) places every
   switch, diode and LED footprint from `layout/generated/*.csv`. It then places the controller,
   connector, switch and reset button, and writes the left and right boards. The right board is
   built from the mirrored layout, with its footprints placed for the right half, not copied
   mirror-image, so the parts remain real parts.
3. The schematic is drawn from the finished board by `tools/sch_generate.py`, so ERC and the
   schematic-to-PCB parity check work ([schematic](#schematic-2026-11-23)).
4. Routing is scripted in the generator ([v3](#v3-scripted-routing-2026-11-23)), then checked
   with `kicad-cli pcb drc` against both fab houses' rules, and reviewed.
5. Fabrication outputs (Gerbers, drill files and a BOM for hand assembly) come from
   `kicad-cli`, plus a 3D STEP of the assembled board for case design.

## Provisional Parts List (2026-11-23)

Provisional decisions, for the owner to review before ordering. Quantities are for both halves,
with spares. Distributor numbers are from a search on 2026-11-23 (not live stock or price);
"unverified" ones need checking on the distributor's site. Mouser is the default, DigiKey the
fallback.

| Part | Qty | MPN | Mouser | DigiKey | Notes |
| --- | --- | --- | --- | --- | --- |
| Diode, SOD-123 | 100 | Diodes 1N4148W-7-F | 621-1N4148W-F | 1N4148W-FDICT-ND | 56 used |
| Hot-swap socket, Kailh MX | — | Kailh CPG151101S11 | — | — | **Ordered by the owner from AliExpress** ("quick connects", read as these sockets; to confirm). Fallback: Adafruit 4958 (DigiKey 1528-4958-ND) |
| LED, SK6812MINI-E (optional) | 6 × 10 | Adafruit 4960 | unverified (485-4960?) | 1528-4960-ND | 56 used. Adafruit's forum reports a pin-label mismatch: check the pinout against the footprint before ordering boards |
| P-MOSFET, SOT-23 (Q1) | 5 | Diodes DMG2305UX-7 | 621-DMG2305UX-7 | DMG2305UX-7DICT-ND | −20 V, −4.2 A, Vgs(th) −0.5 to −0.9 V, Vgs ±8 V. Chosen over AO3401A, which Mouser does not list. Pinout G-S-D confirmed from the datasheet (2026-11-23) |
| N-MOSFET, SOT-23 (Q2) | 5 | onsemi BSS138 | unverified (512-BSS138?) | unverified | Threshold 0.8–1.5 V and pinout G-S-D, both from the datasheet (2026-11-23). Chosen over 2N7002, whose 2.5 V maximum threshold is marginal from a 3.3 V pin |
| Resistor 100 kΩ 1 % 1206 (R1, R2) | 10 | Yageo RC1206FR-07100KL | 603-RC1206FR-07100KL (unverified) | 311-100KFRTR-ND (reel) | |
| Capacitor 10 µF 25 V X5R 1206 (C1) | 10 | Samsung CL31A106KAHNNNE | 187-CL31A106KAHNNNE | unverified | |
| Resistor 10 kΩ 1 % 1206 (R3) | 10 | Yageo RC1206FR-0710KL (unverified) | unverified | unverified | Soft start. Value to settle on the bench; 0 Ω removes it |
| Resistor 470 Ω 1 % 1206 (R4) | 10 | Yageo RC1206FR-07470RL (unverified) | unverified | unverified | LED data |
| Capacitor 1 µF 16 V or more, X7R, 1206 (C2) | 10 | To choose | — | — | Soft start; optional |
| JST-PH 2-pin side entry (J1) | 4 | JST S2B-PH-K-S(LF)(SN) | 306-S2BPHKSLFSNPP | 455-1719-ND | |
| Slide switch SPDT (SW_PWR) | 4 | C&K PCM12SMTR | 611-PCM12SMTR | Obsolete there | Buy at Mouser. DigiKey's suggested replacement does not fit the footprint |
| Tactile switch (SW_RST) | 4 | E-Switch TL3342F160QG | 612-TL3342F160 | EG2531CT-ND | |
| Low-profile socket, 12 pin | 5 | Mill-Max 315-43-112-41-003000 | 575-3154311241003000 | No longer carried | Two per controller |
| Low-profile pins | 60 | Mill-Max 3320-0-00-15-00-00-03-0 | 575-3320000150000030 | ED1134-ND | 24 per controller |
| Controller | — | nice!nano v2 | Not sold | Not sold | **Ordered by the owner from AliExpress.** Check it is a genuine v2 (pinout, RAW as BATTERY+) before fitting |
| Key switches | — | Kailh Speed Bronze | Not sold | Not sold | **Ordered by the owner from AliExpress** |
| Battery | 2 | 1S LiPo with protection circuit and JST-PH lead | See below | See below | Battery design still deferred |

**Batteries.** The owner is in Australia. Lithium cells are hard to post, and DigiKey (and
probably Mouser) ships lithium by ground only, so not to Australia. Options, sources read
2026-11-23:

1. **Buy locally (recommended).** Australia Post carries loose lithium cells by road only
   ("Road Transport Only"), so Australian shops can send them domestically.
   - [Little Bird Electronics](https://littlebirdelectronics.com.au/products/lithium-ion-polymer-battery-3-7v-600mah)
     LB-00237: 3.7 V, 600 mAh, JST-PH, overcharge, over-discharge and short-circuit
     protection, in stock in Sydney. Its size is not read: check it against the case's bay
     before buying it instead.
   - [Core Electronics](https://core-electronics.com.au/power-batteries/liion-lipoly/2-pin.html)
     CE04375 400 mAh and CE04377 1100 mAh, JST-PH, 30–40 day lead time. The owner's usual
     shop, but its battery stock has been poor lately: check it first. **The case is designed
     around the CE04375** (38 × 25 × 6 mm; owner's instruction, 2026-11-23; [case.md](case.md)).
     Its bay takes a cell up to 42.5 × 28.5 × 7.0 mm.
   - [Altronics](https://www.altronics.com.au/power-supplies/battery-batteries/?type_1=lithium-batteries)
     S4723 400 mAh, S4724A 1200 mAh, road only; connector to check.
   - [element14 Australia](https://au.element14.com/): the owner buys there sometimes; prices
     and shipping tend to be high. Battery range not checked.
2. **Fit a JST-PH lead** to a protected cell bought locally with another connector. Polarity
   is not standard between vendors: check with a meter.
3. **Avoid RC/FPV packs:** they usually have no protection circuit.
4. **Overseas:** only cells installed in equipment may travel by air mail, so loose cells from
   overseas sellers are impractical.

Whatever the source: check the cell has a protection circuit, check its polarity against J1's
silkscreen before connecting, and check its charge rating against the nice!nano's charger
(about 100 mA, or about 500 mA with the boost jumper). The cell size must also fit the case.

## Ordering Checklist

- **Owner reminder (2026-11-23):** order a **solder-paste stencil** with the PCBs (owner
  confirmed). It is a separate add-on at both fab houses, used to apply paste to the SMD pads
  of the sockets and diodes. Order one per board design (left and right). Generate the paste
  layer for the side the SMD parts are on, which is the bottom.

**Gate before ordering:** ERC and DRC are clean, every footprint is checked against its
datasheet, the matrix and pin map match the ZMK shield, the owner has reviewed the board, and
the owner has approved the order.

## v1 Routing Results (2026-11-23)

Changes from v0 (`tools/pcb_generate.py`):

- Controller keep-outs leave the pads reachable (see Power, Antenna).
- GND poured on both layers, filled at generation time.
- `join_same_pads()`: the marbastlib hot-swap footprint gives each socket pin a plated hole and
  two overlapping SMD tabs with the same pad number. KiCad treats them as connected; Freerouting
  does not, so short tracks join them.
- Design rules now persist. A board made with `pcbnew.BOARD()` has no project, so its net
  classes were silently dropped; earlier routing used KiCad's defaults. The generator writes an
  empty `.kicad_pro`, then reloads the board in a subprocess (`--finish`) to apply and save
  the rules: in KiCad 10.0.8 `SaveBoard` writes the project file only in a process that did
  not build the board. `check_rules()` reads them back.
- `<board>.kicad_dru`: (superseded by [fab house design rules](#fab-house-design-rules-2026-11-23))
  the board-setup copper-to-edge floor was 0.2 mm because custom rules
  cannot relax it; a custom rule restores 0.3 mm everywhere except the LED cut-outs, where
  KiCad's stock SK6812MINI-E reverse-mount pads sit 0.247 mm from their own cut-out.
- Pin map (`pcb/pins.yaml`): nine matrix lines on the inner pin row, facing the keys, and two
  on pads 21 and 22 at the thumb end of the outer row. In v0, six sat on the outer row and had
  to pass the USB end.

Run on 2026-11-23 (desktop, 24 cores): KiCad 10.0.8, Freerouting 2.5.0, `FREEROUTING_PASSES=30`,
both boards routed in parallel.

| Check | Left | Right |
| --- | --- | --- |
| Generator | 89 footprints, 74 nets | 89 footprints, 74 nets |
| DRC before routing | 144 unconnected, 2 `starved_thermal`, silkscreen warnings | same |
| Freerouting | stopped after 18 passes (11 min): best was pass 1, 68 unrouted, 0 violations | 18 passes (17 min): best was pass 1, 89 unrouted |
| Result | 1030 track segments, 118 vias | 987 segments, 120 vias |
| DRC after routing: unconnected | 41 | 52 |
| DRC after routing: errors | 136 `track_width`, 9 `starved_thermal` | 102 `track_width`, 10 `starved_thermal` |
| DRC after routing: warnings | 40 `via_dangling`, 2 `track_dangling`, silkscreen | 43 `via_dangling`, silkscreen |

Findings:

- **Freerouting does not finish these boards.** Its best result is always its first pass;
  later passes get worse, and it stops when the score has not improved for about 10 passes.
  Freerouting's count is higher than KiCad's because it still lists the same-pad hot-swap joins.
- **Unrouted (KiCad DRC), left:** VLED 5, GND 7 (pour islands), the column and row nets
  (C0 4, C1 4, C5 2, T 2, R1 2, R2–R4 1 each), and single key-to-diode and LED-chain links.
  Freerouting alone reported all 28 VLED links unrouted: the 0.5 mm power width has no room
  between the LED pads. The right board is similar, plus RST.
- **Track width errors** are Freerouting's neck-downs into small pads (0.1874 mm, a few 0.15 mm),
  below the 0.2 mm board minimum. The DSN carries the correct classes (0.25 mm signal, 0.5 mm
  power). Either raise the floor to what the fab allows or stop the neck-downs.
- The routed `.kicad_pro` gains a `top_level_sheets` entry on save; harmless.

Next ideas, not yet tried: move the controller or widen the board around it (about 2 mm
beyond the USB end now); script the regular parts (straight column tracks on F.Cu at
plan-local x = 2.54 through each column, the LED chain and VLED) and leave only the fan-in to
the controller to Freerouting; route VLED at signal width, since LED current per key is small
(to check against the LED supply design).

## v3: Scripted Routing (2026-11-23)

The full method, with every template's coordinates, is in [pcb-routing.md](pcb-routing.md).

**Why.** Research on 2026-11-23:

- Freerouting 2.5.0 is not repeatable, even on one thread: its list of open connections is a
  hash set ordered by object identity ([issue 1172](https://github.com/freerouting/freerouting/issues/1172),
  fixed after 2.5.0), and it has no seed option. It also has known bugs for what these boards
  hit: SMD pads are not joined to power-layer planes ([1080](https://github.com/freerouting/freerouting/issues/1080))
  and it stops with short links open ([1031](https://github.com/freerouting/freerouting/issues/1031)).
- No existing tool routes LED chains or the controller. [kicad-kbplacer](https://github.com/adamws/kicad-kbplacer)
  (GPL-3.0) replicates a switch-to-diode template and joins rows and columns pad to pad;
  [ergogen](https://docs.ergogen.xyz/pcbs) footprints can carry per-key stubs. Both are the
  method used here: a per-key template plus scripted joins. KiCad's own router is not callable
  from Python or the IPC API.

**What.** `tools/pcb_generate.py` places every track by rule, locked; nothing is auto-routed.
Points are key-local, so one template serves every key at any rotation.

| Part | How |
| --- | --- |
| Columns | One straight F.Cu track through each finger column's pin 2 holes |
| Rows | B.Cu at key-local y = −2.35, with a jog between columns |
| Row ends | From C5's cathode to the row's pad; R4 under the antenna keep-out to pad 22 |
| Key-to-diode links | Fingers: F.Cu from pin 1 to a via under the row, then B.Cu between the row and the LED keep-out. Thumbs: B.Cu only |
| LED chain | Four templates: down a column and up a column (F.Cu in the 1 mm corridor right of the column track, a via each end), over the top and under the bottom between columns. Top and bottom differ by half, because the next column is to the left on one and the right on the other |
| LED data, thumb chain, thumb column trunk, thumb rows | Fixed paths, per half where they differ |
| Column bus | Each column runs to the controller along a B.Cu lane between two key rows (C0–C2 above the R2 keys, C3–C4 above the R3 keys), starting at a via on its column track. Lanes jog between columns in an order set by the stagger, so they never cross. C5 connects directly |
| Controller pads | Reassigned in the order the tracks arrive (see the pin table), so the fan-in has no crossings |
| Power nets and the thumb column's run to the controller | `tools/pcb_maze.py`: a small grid router (A*, 0.1 mm grid, fixed net order and tie-breaking, no rip-up) over the controller side of the board, with every clearance grown by a grid margin |

**Result** (KiCad 10.0.8; generation about 15 s for both boards, DRC about 25 s):

| Check | Left | Right |
| --- | --- | --- |
| Tracks / vias | 837 / 145 | 850 / 142 |
| DRC: unconnected | **0** | **0** |
| DRC: errors | **0** | **0** |
| DRC: warnings | silkscreen only | silkscreen only |
| Two runs compared (hash of every track, via and placement) | identical | identical |

**Found on the way.**

- **The custom rules file had been half ignored.** The `min_resolved_spokes` rule used a
  constraint KiCad 10.0.8 does not accept; KiCad stopped reading `.kicad_dru` there without
  failing the run, so the two PTH rules after it never applied. That rule is removed. Check
  `kicad-cli`'s output after any edit to the rules.
- With the PTH rules active, the hot-swap socket's plated pads (3.3 mm on a 3.0 mm hole, a
  0.15 mm ring) and the JST-PH pads (0.225 mm) failed the 0.254 mm ring. The generator widens
  them to 0.26 mm (`pth_ring`). The socket's widened pads sit 0.205 mm from its own peg holes,
  inside the 0.2 mm floor for non-plated holes.
- The keep-out between the controller's pin rows now covers the outer layers only (it is for
  parts on the module's underside). The inner planes run under the module, so every GND pin gets
  its thermal spokes; the antenna strip stays clear on all layers.
- The right half's controller had not been mirrored: see the decision above.

**Limits.** The templates assume this layout's key spacing (19.05 mm) and part offsets; a layout
change needs the DRC run again, and may need a template adjusted. The grid router has no rip-up:
its net order is fixed in the generator, longest first.

## v2.4: Nearly Routed (2026-11-23)

Scripted since v2.1, all locked tracks in `tools/pcb_generate.py`:

- **Thumb LED chain** on B.Cu below the LEDs, including the long C0R4-to-T0 link 4 mm inside the
  bottom edge. On the right half the thumb LEDs are turned 180° so the chain does not cross
  itself (LED order differs between halves; effects are whole-board only).
- **Thumb column** as an F.Cu trunk through key-local (2.54, 7.6) of each thumb, with a drop to
  each pin 2 (a straight pin-to-pin track passes 0.17 mm from the next pin 1).
- **Row ends** from C5's cathode to the controller: inner-row pads directly; R4 (outer row, pad
  22) under the antenna keep-out at y = −1.6 and up beside the outer row at x = 62.5.
- **Left LED data** from pad 10 down F.Cu at x = 41.9, under C5R4, by via into its DIN.
- **Right controller mirrored (decided by the owner later that day):** on the right half the
  nice!nano mounts upside down (components towards the PCB), the usual practice on split
  boards. The footprint is flipped, so pads 1–12 (the matrix and LED data) face the keys and
  RAW/RST face the power switch and reset, as on the left. Before this the right half's matrix
  pins faced away from the keys, which is why it routed worse and RST stayed open. To check:
  clearance for the parts on the nice!nano's underside on low-profile sockets, and the antenna
  facing the board (over the keep-out).
- `tools/pcb_route.py` also widens Freerouting's neck-downs to 0.127 mm and re-drills vias whose
  ring is under 0.13 mm (the DSN offers a 0.6/0.4 mm via).

| Check | Left | Right |
| --- | --- | --- |
| DRC after routing: unconnected | **2** | **3** |
| DRC after routing: errors | 1 `starved_thermal` (known) | 1 `starved_thermal` (known) |

**Still open:** the thumb rows R3 to T2 and R4 to T3 (left), R1 to T0 and R2 to T1 (right), and
K_C0R1 (right). Every thumb must reach a different row (`thumb_rows` in `pcb/pins.yaml`), so
some row has to cross the board to the thumbs. Options: script these links (the paths past the
load switch and the board's right edge are tight), remap `thumb_rows` per half, or finish the
few links by hand in KiCad.

## v2.1: Scripted Rows And Thumb Links (2026-11-23)

Changes from v2: the finger rows are locked B.Cu tracks at key-local y = −2.35 mm (cathode to
x = 8.6, a jog to the next column's x = −10.45, then to its cathode; columns ordered by board
position so the mirrored half works); the thumb key-to-diode links are locked B.Cu tracks (pin 1
down to y = −2.65, across to x = 5.5, down, to the anode); the LED chain runs from the controller
up C5, across to C0, then to the thumbs T0–T3, with LED data on pad 10 (P0.11) and C4 on pad 1;
`tools/pcb_route.py` removes Freerouting's dangling vias and routes in two rounds.

| Check | Left | Right |
| --- | --- | --- |
| Unconnected before routing | 80 | 80 |
| DRC after routing: unconnected | **8** | **9** |
| DRC after routing: errors | 1 `starved_thermal` | 2 `starved_thermal`, 2 `track_width` (0.125 mm neck-down), 1 `annular_width` (RAW via, 0.1 mm ring) |

- **Still unrouted, both boards:** the thumb LED chain (C0R4 to T0, T0–T1, T1–T2, T2–T3), the
  thumb column (2) and one thumb row. Right board also: RST and K_C0R1.
- Freerouting leaves the thumb links open even with 25 passes and an empty area around them; the
  short key-to-diode links there had to be scripted.
- Next: script the thumb LED chain (below the LEDs, on B.Cu); on the right board the chain runs
  the other way, so its thumb LEDs may need turning 180°. Then the right board's small errors.

## v2: Four Layers (2026-11-23)

Changes from the option B run: four layers, GND plane on In1.Cu, VLED plane on In2.Cu (both
"power" layers, which the DSN export passes on, so Freerouting keeps signals off them), no outer
pours, and a locked stub and via from every SMD pad on GND or VLED to its plane
(`Board.plane_vias`): Freerouting does not connect SMD pads to planes, and left all 63 such
links open on its own. TP_VLED is removed (C1's pads carry VLED); the PTH hole-to-copper rule is
0.3 mm (JLCPCB's inner-layer value).

Run: KiCad 10.0.8, Freerouting 2.5.0, `FREEROUTING_PASSES=8`, both boards in parallel, 8.0 min.

| Check | Left | Right |
| --- | --- | --- |
| Unconnected before routing | 104 (all signal) | 104 |
| DRC after routing: unconnected | **22** | **19** |
| DRC after routing: errors | 1 `starved_thermal` | 1 `starved_thermal`, 1 `annular_width` (a RAW via with a 0.1 mm ring) |
| DRC after routing: warnings | 47 `via_dangling`, silkscreen | 39 `via_dangling`, silkscreen |

- **Still unrouted, left:** ROW_R4 7 and ROW_R3 4 (one row does not reach across), COL_T 2, the
  last LED chain links (D24–D27, the thumb end), thumb key-to-diode links (T0, T2) and K_C0R1.
  Right: ROW_R1 7, the same thumb items, COL_C0 and RST.
- The dangling vias are Freerouting's leftovers; they need removing after import.

## v1 Routing With Option B (2026-11-23)

Changes: the option B LED load switch (Q1, Q2, R1, R2, C1 at `LOAD_SWITCH_AT`, LED_EN on pad 17);
LED pads moved 0.06 mm outward; a no-track area over each LED cut-out plus 0.3 mm; VLED at signal
width; the finger columns pre-routed as straight, locked F.Cu tracks from pin 2 to pin 2. They pass
DRC: 0.42 mm from the stem hole and 0.6 mm from the LED cut-out.

Run: KiCad 10.0.8, Freerouting 2.5.0, `FREEROUTING_PASSES=8`, both boards in parallel, 7.8 min.

| Check | Left | Right |
| --- | --- | --- |
| Unconnected before routing | 134 | 134 |
| Freerouting | 80 unrouted, 6 violations | 104 unrouted, 6 violations |
| DRC after routing: unconnected | 48 | 58 |
| DRC after routing: errors | 9 `starved_thermal` only | 10 `starved_thermal` only |

- Clearance, copper-to-edge and track-width errors are gone. Without the cut-out keep-outs,
  Freerouting put about 20 tracks per board within 0.25 mm of an LED cut-out.
- **Still unrouted, left:** VLED 6, GND 4 (pour islands), rows 7, column fan-ins to the controller
  5, COL_T 2, LED chain links 17, key-to-diode links 6, RAW 1, BAT_IN 1. The right board is similar,
  plus RST.
- Freerouting does no better than before. Its best result is its first pass, and it never reaches
  its optimiser.
- Per-key geometry checked by hand for scripting the rest: a row at key-local y = −2.35 mm
  clears the stem hole by 0.225 mm and the LED cut-out by 1 mm. The key-to-diode link and the LED
  chain cross each other's layers in the space around the LED, with margins of 0.2–0.3 mm, so
  scripting them needs a per-key layout worked out with care.

## Fab House Design Rules (2026-11-23)

Read on 2026-11-23 from [JLCPCB's PCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities)
and [PCBWay's capabilities](https://www.pcbway.com/capabilities.html), for a 2-layer, 1.6 mm FR-4
board with 1 oz outer copper. Both pages are summaries, and neither labels most limits as
standard or surcharged. For PCBWay, the "normal" column of its Advanced PCB table is used where
it is stricter than the Standard PCB table. The board is set to the stricter value in every row,
so either house can make it. The values live in `FAB_MIN` and `CUSTOM_RULES` in
`tools/pcb_generate.py`. **Re-read both pages before ordering:** they change without notice.

| Rule | JLCPCB | PCBWay | Board setting |
| --- | --- | --- | --- |
| Min track width | 0.10 mm (4 mil) | 4 mil standard; 5 mil normal (outer 1 oz) | **0.127 mm** |
| Min clearance | 0.10 mm; SMD pad to pad 0.15 mm | 4 mil standard; 6 mil normal | **0.152 mm** |
| Copper to routed edge | 0.2 mm (V-cut 0.4 mm) | 0.25 mm normal, 0.20 mm medium | **0.25 mm** floor; 0.3 mm by custom rule except LED cut-outs |
| Min drill | 0.15 mm; via 0.2–0.25 mm with pad < 0.45 mm costs more | 0.15 mm; under 0.2 mm costs extra | **0.2 mm** |
| Min via diameter | 0.25 mm; hole + 0.1 mm (0.15 mm preferred) | Not stated | **0.45 mm** |
| Via annular ring | (via diameter − hole) ≥ 0.1 mm | 5 mil normal | **0.13 mm** |
| PTH annular ring | 0.18 mm minimum, 0.25 mm recommended | 10 mil normal | **0.254 mm** (custom rule) |
| Hole to other copper | Via 0.2 mm, NPTH 0.2 mm, PTH 0.28 mm (0.35 mm recommended) | 4-layer only | **0.2 mm** floor; PTH **0.3 mm** (custom rule) |
| 4-layer: hole to inner copper | Via 0.2 mm, PTH 0.3 mm | Isolation ring 7 mil (0.178 mm) normal | Via 0.2 mm, PTH 0.3 mm (above) |
| 4-layer: inner track / space | 0.09 mm | 4/5 mil at 1 oz | No inner tracks: planes only |
| 4-layer: inner copper to edge | Not stated | Not stated | Planes keep the 0.3 mm edge rule |
| 4-layer: PTH annular ring | 0.15 mm minimum, 0.20 mm recommended | Outer only | 0.254 mm (unchanged) |
| 4-layer: default stackup, 1.6 mm | 0.5 oz inner, 7628 prepreg about 0.21 mm | 1 oz inner, 7628 prepreg about 0.19 mm | No impedance control needed |
| Hole to hole | Via 0.2 mm, pad 0.45 mm | Component hole 16 mil, via 11 mil | **0.45 mm** |
| NPTH min | 0.5 mm | Not stated | Not a KiCad rule. All NPTH here are larger |
| Slot width | Plated 0.5 mm, non-plated 1.0 mm | Plated 0.5 mm, non-plated 0.8 mm | Not a KiCad rule. No slots yet |
| Solder mask bridge | 0.10 mm green, **0.13 mm black or white** | 4 mil green, 4.5 mil black | **0.13 mm** |
| Mask opening to other copper | 0.09 mm | Not stated | **0.09 mm** |
| Silkscreen line width | 0.15 mm | 0.15 mm (etched legend: 8 mil normal) | **0.15 mm** text thickness |
| Silkscreen text height | 1.0 mm | 0.8 mm | **1.0 mm** |
| Silkscreen to pad | 0.15 mm | Not stated | **0.15 mm** |
| Hole position tolerance | ±0.075 mm | ±0.075 mm | — |
| PTH hole tolerance | +0.13 / −0.08 mm | ±0.08 mm | — |

DRC with these rules (KiCad 10.0.8, the v1 routed boards, not re-routed):

- The track-width errors from Freerouting's neck-downs are gone, apart from one 0.125 mm
  segment on the right board.
- **New: 140 `copper_edge_clearance` errors per board, all at the LED cut-outs.** KiCad's stock
  SK6812MINI-E reverse-mount pads sit 0.2467 mm from their own cut-out, 3 µm under PCBWay's
  0.25 mm. The rest are routed tracks 0.21–0.249 mm from a cut-out. Fixes, to choose: a local copy
  of the footprint with a cut-out about 0.1 mm smaller each way (measure the LED body first), or
  PCBWay's medium tier (0.20 mm, may cost more), or JLCPCB only.
- 48 `text_height` warnings per board: the controller footprint's pin labels are 0.8 mm. PCBWay
  allows this; JLCPCB's minimum is 1.0 mm, so they may print illegibly.

## Running The Tools

All from `keyboard/`, with the devenv shell's tools. When Claude Code is started inside the
devenv shell, `kicad-cli` and KiCad's Python are on `PATH` or in the Nix store,
and the generator (`--finish`) and DRC run inside Claude Code's sandbox (checked 2026-11-23).
Only starting a new `devenv shell` from inside the sandbox fails, since `~/.cache` and the
Nix store are read-only there.

- **`pcbnew` in Python.** The devenv shell's `python3` cannot import `pcbnew`. KiCad's own
  Python environment (the `python3-3.14.10-env` in `nix-store -qR` of the `kicad` package)
  works with `PYTHONPATH` set to `kicad-base-10.0.8/lib/python3.14/site-packages` plus a
  Python 3.14 PyYAML `site-packages`. On the laptop, a bare Python with the same
  `PYTHONPATH` worked; the devenv Python failed with a libprotobuf symbol error.
  Used on 2026-11-23 (the generator's `--finish` step fails without PyYAML on the path):

  ```sh
  K=$(nix-store -qR "$(dirname "$(dirname "$(readlink -f "$(which kicad-cli)")")")")
  PY=$(echo "$K" | grep 'python3-3.14.*-env$')/bin/python3
  YAML=$(dirname "$(dirname "$(python3 -c 'import yaml; print(yaml.__file__)')")")
  export PYTHONPATH=$(echo "$K" | grep 'kicad-base-10')/lib/python3.14/site-packages:$YAML
  "$PY" tools/pcb_generate.py && "$PY" tools/pcb_check.py    # about 15 s, then about 40 s
  ```
- **Datasheet PDFs.** The shell has no `pdftotext`. `nix shell nixpkgs#poppler-utils -c pdftotext
  -layout <file> -` works inside the sandbox and is the cheap way to read dimension tables. The
  BSS138 PDF's text does not extract.
- Footprints, 3D models and datasheets are local, in [`parts/`](../parts/README.md); the generator
  needs no KiCad library path.
- Routing is part of the generator since v3. The Freerouting script, `tools/pcb_route.py`, was
  removed on 2026-11-23 (it is in the git history up to commit `9cf459a`).
- Pads: `python tools/pcb_pads.py pcb/left/left.kicad_pcb SW1 LED1` prints the named footprints'
  pads as placed, for checking against a datasheet.
- Check: `python tools/pcb_check.py` runs DRC on both boards, tests that KiCad read the whole
  custom rules file, and prints a fingerprint of the routing. Exit 1 on any error.
  Pass one side per process to route both in parallel.
- Review: `python tools/pcb_review.py` reads both boards and prints the figures used in the
  [electrical review](#electrical-review-2026-11-23). It also checks the nets against
  `pcb/pins.yaml` and this brief, and exits 1 if they differ. It changes nothing.
- Schematic: `python tools/sch_generate.py` (KiCad's Python) draws both schematics from the
  boards; `tools/pcb_generate.py` runs it at the end. `tools/pcb_check.py` runs ERC and the
  parity check with the DRC.
- **Close KiCad before generating.** KiCad opens a locked project read-only and then does not
  save the design rules; the generator stops if it finds a `~*.lck` file. A lock left behind by
  a stopped `kicad-cli` can be deleted.
- DRC: `kicad-cli pcb drc --schematic-parity --format json -o <out>.json pcb/left/left.kicad_pcb`.
  Do not pass `--schematic-parity=false`: this kicad-cli rejects it and writes no report.
- Review render: `kicad-cli pcb export svg --layers F.Cu,B.Cu,Edge.Cuts --mode-single
  --fit-page-to-board --exclude-drawing-sheet`, then `magick -density 150 in.svg -background
  white -flatten out.png`.
- 1:1 prints, for laying the bought parts on: `pcb/print/<side>-front.pdf` and `<side>-back.pdf`,
  A4 landscape. The back is mirrored, so it is the board seen from below. Regenerate after any
  board change:

  ```sh
  for s in left right; do
    kicad-cli pcb export pdf --mode-single --black-and-white --ev \
      --layers F.Cu,F.SilkS,F.Fab,Edge.Cuts -o pcb/print/$s-front.pdf pcb/$s/$s.kicad_pcb
    kicad-cli pcb export pdf --mode-single --black-and-white --ev --mirror \
      --layers B.Cu,B.SilkS,B.Fab,Edge.Cuts -o pcb/print/$s-back.pdf pcb/$s/$s.kicad_pcb
  done
  ```

  Print at actual size (100 %), not "fit to page", then check the paper with a ruler: the
  controller's two pin rows are 15.24 mm apart and 27.94 mm from first pin to last. The PDF's
  scale was checked on 2026-11-23 (KiCad 10.0.8): an outline-only export with the same options,
  rasterised at 508 dpi, measures 165.65 × 114.45 mm on both boards against 165.63 × 114.42
  (the outline plus its 0.1 mm line), within one 0.05 mm pixel. No paper print is checked yet.
- FreeCAD: use the system `FreeCADCmd` (1.1.4); the devenv shell does not provide it.

## Assembly Cautions (From The Datasheets, 2026-11-23)

Read from the datasheets, not tried on parts.

- **LEDs:** fit each with its cut corner at the silkscreen triangle (pin 3, GND). They are
  moisture-sensitive (MSL 5a: 24 hours out of the bag before reflow; hand soldering is gentler,
  but keep the bag sealed until needed).
- **Battery polarity:** J1 pad 1 is battery +. With the board's top side up and the connector's
  opening facing you, + is the left pin, on both halves. Check the cell's plug with a meter
  before connecting: vendors differ.
- **Power switch:** on is the slider towards the user, on both halves. Confirm with a meter that
  the bought part joins the middle terminal to the end the slider is pushed towards.
- **Reset switch:** the two terminals of a row should be joined inside the part. If a bought part
  joins the two of a side instead, RST is shorted to ground: meter one before soldering.
- **Solder the power switch before the controller sockets:** its terminals face the socket strip,
  about 2.4 mm away.
- **Hot-swap sockets:** hand solder at 350 °C for at most 3 s. Kailh rates them for 100 switch
  insertions.
- **LED parts:** R3 and R4 are in series with the LED supply's gate drive and the LED data. Fit
  each, or a 0 Ω link in its place, or the LEDs stay off. C2 is optional.
- **Controller:** the nice!nano has 13 holes a side. The pair at the USB end (B+, B−) hangs past
  the 12-way sockets and takes no pin. Do not bridge the BOOST jumper (see the review item below).

## Electrical Review (2026-11-23)

A review by Claude of the v3 boards as generated (fingerprints left `a8ecd0e7cc062915`, right
`125e64f16522f208`; DRC re-run the same day: 0 unconnected, 0 errors). It is a paper review plus
measurements of the board files. **Nothing was tested on hardware.** Figures marked "estimate"
are hand calculations, not simulations. The measurements come from
`python tools/pcb_review.py` (KiCad 10.0.8), which only reads the boards.

**Result: no routing fault found. Six changes were proposed; the owner accepted all six on
2026-11-23 and the four that change the board are [applied](#applied-2026-11-23).** The table
and findings below describe the board as reviewed, before those changes.

### Checked And Passed

| Check | Result (left / right where they differ) |
| --- | --- |
| Nets against `pcb/pins.yaml` and this brief. There is no schematic, so this is the only independent test of the netlist | 28 keys on 28 distinct row and column pairs, 4 × 7. Every key: column → switch → diode anode, cathode → row. One LED chain of 28 from pad 10, C5R4 to T3. Battery, load switch and reset nets as drawn above |
| Battery path copper | BAT_IN and RAW are 0.5 mm throughout, vias 0.8/0.4 mm. 44 + 58 mΩ / 45 + 60 mΩ, counting every track of a net in series (an upper bound) |
| Drop from J1 to VLED at 0.3 A | Tracks 0.10 Ω, switch 0.07 Ω max, Q1 0.10 Ω max (at −2.5 V gate drive), stub, via and plane under 0.01 Ω: under 0.28 Ω, about 85 mV. The cell and its lead are extra |
| VLED plane (In2) | One piece. Copper at least 2 mm wide joins every via; at 3 mm wide, 99.9 % of it is still one piece. At about 1 mΩ per square (0.5 oz) the drop across it is a few millivolts (estimate) |
| GND plane (In1) | One piece at 3 mm wide. Each LED's GND via joins it through a neck 1 to 2 mm wide, ample for 36 mA. A 0.6 mm² sliver between controller pads 3 and 4 touches only those two pads: harmless |
| Thermal spokes, 0.4 mm | J1 pin 2: three. Controller GND pins 3, 4 and 14: two each to the main plane |
| LED data beside column tracks | The longest run on any one link is 10.9 mm at a 0.26 mm gap, on F.Cu, 0.2 mm above the GND plane. Both lines are driven (ZMK drives idle columns low; each LED re-drives the data). A few-nanosecond spike of the order of 0.1 V against more than 1 V of margin (estimate): acceptable |
| LED link lengths | 19 to 81 mm / 19 to 92 mm; controller to first LED 58 / 50 mm. Short for 800 kHz data: no termination needed |
| LED data level | The LED input draws no current, so the pin sits at its 3.3 V supply against a threshold of 2.94 V at a full battery: 0.36 V of margin, and the threshold falls with the battery. Meets the datasheet on paper; the bench check stays. It assumes 3.3 V I/O: measure a pin driven high on the bought (AliExpress) module |
| Per-LED capacitors (the datasheet calls them essential) | Not needed here. The LED outputs switch in about 100 ns (datasheet) and the supply and return are planes, so the edges produce under a millivolt (estimate). Boards without planes commonly omit them. C1 stays |

### Findings And Proposals

1. **Plane copper under the antenna.** From the official pinout image the antenna section is
   about the last 5 mm of the module (read off the image: confirm on the module). The keep-out
   clears all layers only beyond the pin rows; 54 of that section's 89 mm² has GND and VLED plane
   beneath it, on both boards. On the right half the module is face down, nearer the planes.
   Radio range will suffer; by how much is unknown. **Proposed:** keep both planes out of the
   last 5 mm of the module across its whole width (tracks to pads 11 and 12 stay). No GND pin is
   there, so nothing is lost. The case must keep the battery and any metal clear of that end too.
2. **LED data can back-power the LEDs.** The LED's input limit is VDD + 0.5 V (datasheet). With
   VLED off, VDD is 0 V, so a high on pad 10 drives current through the first LED's input into
   the whole VLED plane. The datasheet also asks for about 500 Ω in series with the data.
   **Proposed:** one 1206 resistor, 470 Ω, in LED_DIN beside pad 10, and a firmware rule: data
   low whenever LED_EN is low.
3. **Inrush when the LEDs turn on.** Q2 pulls Q1's gate down in microseconds, connecting the
   empty C1 (10 µF) to RAW, which holds 4.7 µF on the module (schematic, C6). RAW dips sharply
   for some microseconds until the cell refills it (estimate; the depth depends on the cell).
   Whether the controller rides through is already a bench check; a failure would mean a new
   board. **Proposed:** two optional 1206 footprints: R3 between Q2's drain and Q1's gate, and
   C2 across R1. With 10 kΩ and 1 µF the gate ramps over milliseconds and the peak is about
   0.2 A (estimate); with 0 Ω and C2 left off, the circuit is today's. C2 goes gate to source,
   not gate to drain: gate to drain would turn Q1 on briefly whenever the battery is connected.
4. **The switch's 0.3 A limit rests on firmware alone.** Correction to earlier notes: charge and
   LED current do not add. Q1 takes the LED supply from RAW, on the controller's side of the
   switch, so the switch carries only the cell's current: the charge current (about 0.1 A) on
   USB, or the LEDs plus the controller on battery. All 28 LEDs at full white are 1.0 A, and
   28 mA when dark (datasheet). To stay under 0.3 A on average the firmware cap must be 24 % at
   white or less. **Proposed:** cap at 20 % (about 0.23 A; the current is pulsed at 1.2 kHz, so
   peaks are higher), and keep the BOOST jumper open. An alternative, not recommended: take Q1's
   supply from BAT_IN instead. The switch then never carries LED current, but "off" no longer
   isolates the LED circuit from the cell.
5. **VLED's feed is signal-sized.** Q1's drain reaches the plane through a 1.5 mm stub 0.25 mm
   wide and one 0.6/0.3 mm via (shared with C1 on the left board). Fine at 0.3 A; thin if the
   firmware cap fails at 1.0 A. **Proposed:** power width and the 0.8/0.4 mm via for the Q1 and
   C1 stubs, a one-line change in `plane_vias`.
6. **Charging with the LEDs lit.** The module's charger is a BQ24075 (schematic image) and RAW
   is its battery pin, so the LEDs are a load on the cell, not on a system rail. From memory of
   TI's datasheet, **not re-read and to verify**: charging ends when the current falls to about
   a tenth of the charge current, so even the dark LEDs' 28 mA can stop it finishing and the
   charger's safety timer may trip. Above about 0.1 A of LED current the cell discharges while
   plugged in. With the power switch off on USB there is no cell on RAW and the LEDs will not
   run reliably. **Proposed:** firmware turns VLED off when idle; note both in the operating
   guide. No board change.

Not changed, for the owner to know: there is **no reverse-polarity protection** on J1. A series
P-MOSFET would block a reversed cell only while USB is unplugged, so the meter check in the
assembly cautions remains the protection.

**Firmware requirements from this review**, for the ZMK shield (accepted by the owner,
2026-11-23): LED brightness cap of 20 %; LED data low whenever LED_EN is low; about 50 ms
between raising LED_EN and the first data, for the soft start; VLED off when idle and in sleep;
the external-power control on P0.31. The setting names are to be verified at the pinned ZMK
commit.

**Status 2026-11-23:** verified in ZMK's source at the pinned commit and built into the shield
([firmware/README.md](../firmware/README.md#lighting)). The cap, idle-off and P0.31 are settings.
The start-up delay is not needed: ZMK resends the frame every 50 ms. Data-low rests on ZMK's
order of operations plus R4 and C2, and needs a scope to confirm. Compile-time only.

### Applied (2026-11-23)

The owner accepted all six proposals. Proposals 4 (the 20 % cap) and 6 (VLED off when idle) are
firmware and operating notes, carried in the list above. The other four are in
`tools/pcb_generate.py` and both boards were regenerated:

| Proposal | What changed on the board |
| --- | --- |
| 1. Antenna | A third rule area: no plane copper on any layer under the last 5 mm of the module, 8.9 mm either side of its centre line. Tracks to pads 11 and 12 pass through it |
| 2. Data resistor | R4 (470 Ω, 1206, bottom side) in series with the LED data. Pad 10 to R4 is the new net LED_DATA; R4 to the first LED is LED_DIN |
| 3. Soft start | R3 (10 kΩ) between Q2's drain and Q1's gate, on the new net LED_GATE_DRV, and C2 (1 µF) across R1. Both 1206, bottom side, beside the load switch |
| 5. VLED feed | The stubs from Q1's drain and C1 to the VLED plane are 0.5 mm with 0.8/0.4 mm vias |

Results (KiCad 10.0.8, `tools/pcb_check.py` and `tools/pcb_review.py`; simulation only):

| Check | Left | Right |
| --- | --- | --- |
| DRC: unconnected / errors | 0 / 0 | 0 / 0 |
| DRC warnings (silkscreen only) | 57 `silk_over_copper`, 33 `silk_overlap`, 48 `text_height`, 2 `silk_edge_clearance` | 53, 33, 48, 2 |
| Tracks / vias | 839 / 148 | 858 / 144 |
| Fingerprint, the same on three runs | `9eb48eb700d3ef4d` | `b266d5be79ed4f4b` |
| Nets, including R3, R4 and C2 | as drawn above | as drawn above |
| Plane copper under the antenna section | 0 mm² (was 54 of 89) | 0 mm² |
| Controller to R4 / R4 to first LED | 24 / 37 mm | 24 / 29 mm |
| Thermal spokes, plane widths | unchanged | unchanged |

Three things to know:

- **R4 is not beside pad 10.** It is 24 mm along the data track, at the nearest free space on
  the bottom side, below the antenna strip. It still limits the current and is in the first
  part of the link; as a damping resistor it is a little less effective there.
- **The new keep-out is the module's width, not the 9.5 mm of the strip beyond it.** At 9.5 mm
  the plane reached the reset switch's lower GND via by a sliver, which DRC still counted as
  connected. At 8.9 mm the via is in solid copper. The switch's other GND pad has its own via.
- **On the right board the soft-start links are longer** (LED_GATE 25 mm, LED_GATE_DRV 12 mm,
  against 12 and 3 mm): the parts are not mirror images, so Q2's drain faces away from R3
  there. These lines carry no current to speak of.

The soft-start values (10 kΩ, 1 µF) are estimates. Settle them on the bench: watch RAW on a
scope while LED_EN rises, with the LEDs fitted.


## Schematic (2026-11-23)

`pcb/left/left.kicad_sch` and `pcb/right/right.kicad_sch`, written by `tools/sch_generate.py`.
Open either project in KiCad to read it, or export it: `kicad-cli sch export pdf`.

**What it is.** A drawing of the board, made from the board: every footprint becomes a symbol
and every pad's net a label on the matching pin. One cell per key (diode, switch and LED) on
the matrix's rows and columns, then the controller and the power parts. Nets join by label;
there are no wires.

**What it is not.** An independent design. It cannot disagree with the board, so it does not
check the netlist; `tools/pcb_review.py` does that, against `pins.yaml` and this brief.

**What it adds.**

- **ERC**, KiCad's electrical rules check, on pin types: supplies with no source, outputs tied
  together, pins left open. Clean on both halves. GND, RAW and VLED carry a power flag, which
  states that each is fed from outside the drawing (the battery; VLED through Q1).
- **A drawing a person can check**, with pin numbers and names shown: each diode's cathode on
  its row, Q1's source on RAW and drain on VLED, each LED's four pins.
- **Schematic parity** in DRC: references, footprints and every pad's net agree, 0 differences.
  It guards against a hand edit to either file.
- A normal KiCad project: each board directory has a symbol and a footprint library table
  pointing into `parts/`.

Results (KiCad 10.0.8, `tools/pcb_check.py`; simulation only):

| Check | Left | Right |
| --- | --- | --- |
| ERC | clean | clean |
| Schematic parity differences | 0 | 0 |
| DRC: unconnected / errors | 0 / 0 | 0 / 0 |
| Tracks / vias, fingerprint | 839 / 148, `9eb48eb700d3ef4d` (unchanged) | 858 / 144, `b266d5be79ed4f4b` (unchanged) |
| New DRC warnings | 57 `lib_footprint_mismatch` | 57 |
| Two generator runs | identical files | identical files |

Both checks were tried against planted faults on a copy: a diode labelled with the wrong row
is reported by parity, and a supply with its flag removed by ERC.

**Changes to the board that came with it** (no track or via moved):

- Footprints now carry their library names, as KiCad expects. KiCad therefore notices the 57
  footprints a board that the generator alters on purpose and warns that they differ from the
  library: the 28 sockets and the battery connector (widened pads) and the 28 LEDs (moved pads,
  turned mark). `tools/pcb_check.py` fails on any other mismatch.
- The two nets that had a single pad, `VCC_3V3_SW` and `LED_DOUT_END`, are gone. Those pads, the
  five spare controller pads and the power switch's unused contact are marked unconnected in
  the schematic and carry KiCad's `unconnected-(…)` net names on the board.

**Found: KiCad's own LED symbol is numbered differently from the datasheet.** KiCad's
SK6812MINI-E symbol calls pin 1 VSS, 2 DIN, 3 VDD, 4 DOUT; the Opsco datasheet calls pin 1 VDD,
2 DOUT, 3 GND, 4 DIN. The two are the same part turned half a turn, and the part's pads are
symmetric under that turn, so both fit the footprint. This board follows the datasheet, with
the cut-corner mark moved to pad 3 to match
([footprint check](../parts/README.md#footprint-check-against-datasheets-2026-11-23)), and the
schematic's LED symbol is renumbered to the datasheet too. Nothing is wrong on the board, but
it makes the assembly rule critical: **an LED fitted with its cut corner away from the mark is
connected backwards across the supply.** Check one real LED with a meter against the board
before fitting the rest.

## v4: Notches And Mounting Holes (2026-11-23)

The owner asked for the three changes that the [case design](case.md) suggested. All are in
`tools/pcb_generate.py`; the right half mirrors the left.

| Change | What | Why it is that size |
| --- | --- | --- |
| USB notch (`USB_NOTCH`) | 13 mm wide, from the far edge back to 16.0 mm from the controller's centre | A USB-C plug's overmould is up to about 12.4 mm wide. The module ends at about 16.6 mm and its pads at 14.9 mm |
| Mounting holes H1 to H4 (`MOUNT_AT`) | ø3.2 mm, not plated, KiCad's `MountingHole_3.2mm_M3`, at plan (−43.5, 42.5), (−12, −31.5), (43, 43) and (73, −22) | The four key-free places where neither half has fixed copper within 4 mm or a part within 6 mm (4.2 mm for H3), measured on both v3 boards. The grid router takes the thumb column round H4. H3 is 0.9 mm from the USB notch |
| Power switch notch (`POWER_SWITCH_NOTCH`) | 5.7 mm wide and 0.85 mm deep in the edge, between the switch's outer mount pads | The slider now overhangs by 1.85 mm, not 1.0. **Not the 2.5 mm proposed:** the locating pegs' holes reach 0.78 mm from the switch's centre, and the notch stops at 1.3 mm, leaving 0.52 mm of board |

- The outline is no longer convex, so `tools/pcb_maze.py` now fills each grid row between
  every pair of outline crossings, not between the first and last.
- The holes are board-only footprints: they are not in the schematic, the parity check, the
  bill of materials or the placement file. `tools/sch_generate.py` skips them.
- A fab's router leaves a radius of about 0.5 to 1 mm in the notches' inside corners. The
  switch's slider needs 2.8 mm of the 5.7 mm; the USB plug's shell is narrower than its
  overmould, so neither is affected. Not confirmed with a fab house.
- Nothing else moved: no net, pin or part position changed, and the firmware shield is still
  up to date (`tools/zmk_generate.py --check`).

| Check (KiCad 10.0.8) | Left | Right |
| --- | --- | --- |
| Generator | 100 footprints, 76 nets | 100 footprints, 76 nets |
| Unconnected / DRC errors | 0 / 0 | 0 / 0 |
| Schematic parity differences / ERC | 0 / clean | 0 / clean |
| DRC warnings | As v3, but 9 `silk_edge_clearance` (was 2): silkscreen at the notches | As v3, but 9 |
| Tracks / vias | 839 / 148 | 858 / 144 |
| Fingerprint, the same on two runs | `6baa8230127f6a1d` | `2f7fbd9eff4a3a65` |
| `tools/pcb_review.py` | Passes; figures as before | Passes |

The 1:1 prints in `pcb/print/` and the case in `cad/case/` are regenerated from these boards.

## Open Items

- Done 2026-11-23: the electrical review, and its accepted changes
  ([applied](#applied-2026-11-23)), and the ZMK shield ([firmware](../firmware/README.md)),
  compile only, and the [schematic](#schematic-2026-11-23), and the outline settled with the
  case ([v4](#v4-notches-and-mounting-holes-2026-11-23)). **Next:** before any order, measure
  the bought parts against a 1:1 print of the board.
- To verify: the BQ24075's charge-termination behaviour against TI's datasheet (not in
  `parts/datasheets/`), and the antenna's extent on the bought module.
- Bench: the soft-start values (R3, C2), with a scope on RAW.
- Controller height, unread: the Mill-Max catalogue figure is ambiguous about the socket's
  seated height (0.071 in or 0.095 in). On the right half the module is face down, so its
  parts need that gap: measure a socket. The other consequence, the board under the USB plug,
  is settled: the outline is notched there
  ([v4](#v4-notches-and-mounting-holes-2026-11-23)).
- Done on paper 2026-11-23: every footprint is checked against its datasheet
  ([parts/README.md](../parts/README.md#footprint-check-against-datasheets-2026-11-23)). Two
  faults found and fixed in the generator the same day: the power switch now sits on the board
  edge with its actuator overhanging by 1.0 mm, and the LED silkscreen mark is at the part's cut
  corner (pin 3, GND). Both boards: 0 unconnected, 0 DRC errors, two runs identical (left 814
  tracks / 146 vias, right 846 / 142). New warnings: the switch's silkscreen is clipped by the
  board edge, twice a board. Still to do: measure the bought parts against a 1:1 print
  (the PDFs are in `pcb/print/`, made 2026-11-23).
- Add the real KLP Lamé keycap outlines to `tools/layout.py check` (the prototype shows they fit,
  about 2 mm apart by eye).
- After the review, in this order: the ZMK shield from `pcb/pins.yaml`, then the schematic
  (last: generated from the same script as the board, it can only agree with itself), and the
  board outline settled with the case design. The power switch follows the outline: the
  generator turns it to lie along the edge below it (`edge_pose`), 11.5° now.
- The plated ø3.0 socket holes could come out smaller than the largest socket barrel
  ([parts/README.md](../parts/README.md#footprint-check-against-datasheets-2026-11-23)). Not
  changed; decide before ordering whether to ask for non-plated holes or accept it.
