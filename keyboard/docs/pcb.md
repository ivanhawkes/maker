# PCB Design Brief

Status: design started 2026-11-23. **v1 placement generated and auto-routed; routing incomplete.**
Generate with `python tools/pcb_generate.py` and route with `python tools/pcb_route.py`; the boards
are written to `pcb/left/left.kicad_pcb` and `pcb/right/right.kicad_pcb`. Nothing is fully routed,
checked for fabrication, or ordered. Results are in [v1 routing results](#v1-routing-results-2026-11-23).
This brief collects
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
  RAW ──┬───────────── Q1 source      Q1 AO3401A (P-MOSFET, SOT-23)
        R1 100k        Q1 drain ──┬── VLED ── LED VDD pins, TP_VLED
        │                         C1 10 µF ── GND
  LED_GATE ─────────── Q1 gate
        └───────────── Q2 drain     Q2 2N7002 (N-MOSFET, SOT-23), source to GND
  LED_EN (pad 17, P0.31) ── Q2 gate, R2 100k to GND
  ```

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
| Hole to other copper | Via 0.2 mm, NPTH 0.2 mm, PTH 0.28 mm (0.35 mm recommended) | 4-layer only | **0.2 mm** floor; PTH **0.28 mm** (custom rule) |
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
devenv shell, `kicad-cli`, `freerouting` and KiCad's Python are on `PATH` or in the Nix store,
and the generator (`--finish`) and DRC run inside Claude Code's sandbox (checked 2026-11-23).
Only starting a new `devenv shell` from inside the sandbox fails, since `~/.cache` and the
Nix store are read-only there.

- **`pcbnew` in Python.** The devenv shell's `python3` cannot import `pcbnew`. KiCad's own
  Python environment (the `python3-3.14.10-env` in `nix-store -qR` of the `kicad` package)
  works with `PYTHONPATH` set to `kicad-base-10.0.8/lib/python3.14/site-packages` plus a
  Python 3.14 PyYAML `site-packages`. On the laptop, a bare Python with the same
  `PYTHONPATH` worked; the devenv Python failed with a libprotobuf symbol error.
- `KICAD10_FOOTPRINT_DIR`: `share/kicad/footprints` of the `kicad-footprints` package.
- Routing: `FREEROUTING_PASSES=30 FREEROUTING_HOME=<scratch dir> python tools/pcb_route.py left right`.
  Freerouting ignores `$HOME`; the script redirects `user.home` and the XDG variables.
  Pass one side per process to route both in parallel.
- DRC: `kicad-cli pcb drc --format json -o <out>.json pcb/left/left.kicad_pcb`. Do not pass
  `--schematic-parity=false`: this kicad-cli rejects it and writes no report.
- Review render: `kicad-cli pcb export svg --layers F.Cu,B.Cu,Edge.Cuts --mode-single
  --fit-page-to-board --exclude-drawing-sheet`, then `magick -density 150 in.svg -background
  white -flatten out.png`.
- FreeCAD: use the system `FreeCADCmd` (1.1.4); the devenv shell does not provide it.

## Open Items

- One controller GND pad per board has a single thermal spoke (`starved_thermal`); the custom
  rule meant to fix it does not.
- Verify the Kailh CPG151101S11 socket footprint and the low-profile socket pin holes against
  their datasheets.
- Add the real KLP Lamé keycap outlines to `tools/layout.py check` (the prototype shows they fit,
  about 2 mm apart by eye).
- Later: generate the schematic, write the ZMK shield from `pcb/pins.yaml`, and settle the
  board outline with the case design.
