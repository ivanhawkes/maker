# PCB Routing: Method And Findings

Status: 2026-11-23. Both boards are fully routed by script, with no autorouter: 0 unconnected
items, 0 DRC errors, and the same tracks on every run. This document records how that was
reached, how the routing works, and what was learned, so the work can be repeated or changed.
The board design itself (parts, nets, rules, decisions) is in [pcb.md](pcb.md).

Everything here is simulation: KiCad geometry and DRC. Nothing has been fabricated, and the
routes have had no electrical review.

## Summary

- An autorouter (Freerouting 2.5.0) never finished these boards and cannot give the same result
  twice. Each piece of routing moved into the generator made the result better and faster.
- The method is the one keyboard tools already use: a **per-key template**, written in the key's
  own coordinates and stamped on every key, plus scripted joins between keys.
- The few irregular links (power, one thumb net) go to a **small grid router** with a fixed order.
- **KiCad DRC is the judge.** Paths were worked out by hand, then run through DRC; a run takes
  about 40 s, so iterating is cheap.

| Stage (all 2026-11-23) | Left unconnected | Right unconnected | Time per run |
| --- | --- | --- | --- |
| 2 layers, Freerouting, 30 passes | 41 | 52 | 11–17 min |
| + LED supply option B, columns scripted | 48 | 58 | 8 min |
| 4 layers, GND and VLED planes, scripted plane vias | 22 | 19 | 8 min |
| + rows scripted, LED chain reordered | 12 | 12 | 7 min (25 passes: no better) |
| + thumb key-to-diode links, two Freerouting rounds | 8 | 9 | 12 min |
| + thumb LED chain | 7 | 7 | 12 min |
| + thumb column trunk | 5 | 6 | 11 min |
| + row ends, right controller mirrored | 5 | 4 | 11 min |
| + long LED link and left LED data | 2 | 3 | 11 min |
| **Templates for every key, no Freerouting** | 19, then 17 | 19, then 17 | 40 s |
| **+ column bus, controller pads reordered** | 11 | 11 | 40 s |
| **+ grid router for the remainder** | **0** | **0** | 40 s |

## Why Not An Autorouter

What Freerouting 2.5.0 did on these boards (observed):

- Its best result was always its first pass; more passes (8, 25, 30) did not help. A second run
  on the routed board finished two or three more links.
- It left short links open in empty areas: thumb key-to-diode links a few millimetres long, with
  nothing near them, stayed open at every setting.
- It did not join SMD pads to the inner planes: all 63 GND and VLED pad connections per board
  stayed open until the generator added a stub and via for each.
- It ran tracks within 0.25 mm of the LED cut-outs: a footprint's own Edge.Cuts shape is not a
  board edge to it. A no-track area over each cut-out fixed that.
- It necked tracks down to 0.125 mm at small pads (under the 0.127 mm minimum), chose a
  0.6/0.4 mm via with a 0.1 mm ring that the DSN export offers, and left vias connected to
  nothing.
- With four layers it counted 84 to 91 "pre-existing clearance violations" that KiCad did not.

What the research found (sources read 2026-11-23; nothing was run to confirm them):

- **Not repeatable.** Even on one thread, 2.5.0 can route the same board differently: its list
  of open connections is a hash set ordered by object identity
  ([issue 1172](https://github.com/freerouting/freerouting/issues/1172), fixed after 2.5.0).
  There is no seed option in 2.5.0.
- **Known bugs match the failures.** SMD pads are not connected to power-layer planes
  ([1080](https://github.com/freerouting/freerouting/issues/1080)); 2.5.0 stops with nets open
  that an older version routed, and more passes cannot extend the run
  ([1031](https://github.com/freerouting/freerouting/issues/1031)).
- **No tool routes this for us.** [kicad-kbplacer](https://github.com/adamws/kicad-kbplacer)
  (GPL-3.0) copies a hand-routed switch-to-diode template to every key and joins rows and
  columns pad to pad; it does not route LEDs or the controller.
  [ergogen](https://docs.ergogen.xyz/pcbs) leaves boards unrouted, though its footprints can
  carry per-key stubs. KiCad's push-and-shove router cannot be called from the pcbnew Python
  API or the IPC API. Small open autorouters exist (grid A*), mostly with few users.

So: per-key templates for the regular parts, and a router we control for the rest.

## Coordinates

- **Plan coordinates** (mm): x to the right, y away from the user, as in `layout/layout.yaml`.
  The KiCad position is (150 + x, 100 − y).
- **Key-local coordinates**: plan coordinates relative to a key's centre, rotated with the key.
  A template written in key-local coordinates fits every key at any rotation.
- **The right half** is built from the mirrored layout, but its footprints are real parts, not
  mirror images. So the key-local geometry is the same on both halves, while the neighbours are
  on opposite sides: the next column towards the controller is at key-local +x on the left half
  and −x on the right. Templates inside one key or one column are shared; anything that goes to
  a neighbouring column or the controller has a variant per half.

Key-local facts the templates rely on (from the placed footprints, KiCad 10.0.8; the row line
and the vias are the generator's own):

| Feature | Key-local position (mm) |
| --- | --- |
| Switch pin 1 / pin 2 plated holes | (−3.81, 2.54) / (2.54, 5.08); 3.0 mm holes, pads widened to 3.52 mm |
| Hot-swap socket tabs (B.Cu) | Pin 1 side out to x = −8.64 (y 1.29–3.79); pin 2 side out to x = 7.37 (y 3.83–6.33) |
| Stem hole, peg holes (non-plated) | r 2.0 at (0, 0); r 0.875 at (±5.08, 0) |
| Diode (B.Cu) | Cathode (7, −2.35), anode (7, −5.65) |
| LED pads (B.Cu) | VDD (2.785, −5.83), DOUT (2.785, −4.33), GND (−2.785, −4.33), DIN (−2.785, −5.83) |
| LED no-track area (all layers) | \|x\| ≤ 2.1, y −6.98 to −3.18 |
| Plane vias | VLED (3.92, −6.14), GND (−4.02, −4.0) |
| Row track (B.Cu) | y = −2.35 |
| Column track (F.Cu) | x = 2.54 |

On the right half the thumb LEDs are turned 180°, which swaps their pads left to right.

## Layer Plan

- **F.Cu: vertical.** Column tracks, the LED chain's runs between keys of a column, the drop
  from switch pin 1, the thumb column trunk, thumb row taps.
- **B.Cu: horizontal.** Rows, the column bus lanes, the links inside a key (all SMD pads are on
  the bottom).
- **In1.Cu: GND plane. In2.Cu: VLED plane.** Marked as power layers. Every SMD pad on GND or VLED
  gets a short stub and a via to its plane (`Board.plane_vias`).

Because the layers cross at right angles, a link that must cross a row or a column changes
layer with a via; the templates below say where.

## The Templates

All in `tools/pcb_generate.py`, in the section "scripted routing". Every track is locked.
Coordinates are key-local unless marked "plan"; "next" means the next key's frame.

**Columns.** One straight F.Cu track through the pin 2 holes of each finger column (the keys of
a column are collinear).

**Rows.** B.Cu from each cathode to (8.6, −2.35), between the diode and the next column's
socket, across to the next column's (−10.45, −2.35), then along y = −2.35 to its cathode.
Columns are taken in board order, so the mirrored half works.

**Row ends.** From C5's cathode to the row's controller pad: out to plan x = ±40.3, then angled
to 2 mm short of an inner-row pad. R4, on the outer pin row, goes down to plan y = −1.6 (under
the antenna keep-out), across to x = ±62.5 and up to pad 22.

**Key-to-diode link.**

- Fingers: F.Cu from pin 1 down to (−3.81, −2.5) and a via at (−3.2, −3.1), under the row; then
  B.Cu (−2.6, −3.0) → (5.5, −3.0) → (5.5, −4.6) → anode. The row is in the way on B.Cu, hence
  the via.
- Thumbs (no row passes through): B.Cu only, pin 1 → (−3.81, −2.65) → (5.5, −2.65) →
  (5.5, −4.6) → anode.

**LED chain** (DOUT of one LED to DIN of the next). The order is C5 upwards from the controller,
then down C4, up C3, down C2, up C1, down C0, then the thumbs T0 to T3. DOUT leaves to the
right, between the VLED via and the key-to-diode link; DIN is entered from below-left, at
x = −4.1.

| Link | Path |
| --- | --- |
| Down a column | B.Cu DOUT → (4.85, −4.33) → (4.85, −8.3), via. F.Cu to next (4.85, 2.75) → (3.05, 1.45) → (3.05, −8.5) → (3.2, −9.15), via. B.Cu → (−4.1, −9.15) → (−4.1, −5.83) → DIN |
| Up a column | B.Cu DOUT → (4.75, −4.33), via. F.Cu (3.05, −2.6) → (3.05, 1.3) → (4.7, 2.9) → next (4.7, −8.3), via. B.Cu → (−4.1, −8.3) → (−4.1, −5.83) → DIN |
| Over the top, left half | As "up" to (4.7, 2.9), then F.Cu (4.7, 8.6) → next (−6.5, 8.6) → next (−6.5, −5.83), via, B.Cu to DIN |
| Under the bottom, left half | B.Cu DOUT → (4.85, −4.33) → (4.85, −10.2) → (−5.5, −10.2) → next (11.0, −10.2) → next (−4.1, −10.2) → (−4.1, −5.83) → DIN |
| Over the top, right half | B.Cu DOUT → (4.85, −4.33) → (4.85, −7.0) → next (−4.1, −8.3) → (−4.1, −5.83) → DIN. Where the next column is lower (C3 to C2), two extra points, (8.0, −9.1) and next (−8.45, −3.1), keep it above the column bus |
| Under the bottom, right half | B.Cu DOUT → (4.85, −4.33) → (4.85, −8.3) → next (−4.1, −8.3) → (−4.1, −5.83) → DIN. Across the gap between C2 and C1, an extra point next (−12.0, −8.3) keeps it left of the row's jog |
| C0R4 to the first thumb | B.Cu, a long run about 3 mm inside the bottom edge: out by (4.85, −9.5) on the left half; by (4.85, −9.8) → (−5.5, −9.8) on the right, under C0R4's own incoming link |
| Thumb to thumb | B.Cu below the LEDs: (4.85, −4.33) → (4.85, −8.3) → next (−4.1, −8.3) → (−4.1, −5.83); mirrored in x on the right half |

The F.Cu runs use a corridor about 1 mm wide to the right of the column track: x = 4.85 past the
next key's pin 2 pad, then x = 3.05 between the column track and the peg hole.

**LED data.** F.Cu from pad 10 to plan x = ±41.0, down to y = −24.5, to a via at C5R4's
(−4.1, −8.3); B.Cu into its DIN.

**Thumb column.** An F.Cu trunk through (2.54, 7.6) of each thumb, with a drop to each pin 2.
A straight pin-to-pin track would pass 0.17 mm from the next thumb's pin 1.

**Thumb rows.** Each thumb is on a different row (`thumb_rows` in pins.yaml), so the rows
must cross the board to them. A thumb's cathode is reached down its x = 8.6, from (8.6, 8.5),
right of the socket tabs and the diode.

| Row | Left half | Right half |
| --- | --- | --- |
| R1 → T0 | Via on the row at plan (1.5, 41.65); F.Cu down the gap between C3 and C4 to y = −24.0; via; B.Cu into T0 | Same, at plan x = −1.5 from y = 45.65 |
| R2 → T1 | Via at plan (20.8, 20.6); F.Cu down the gap between C4 and C5 to y = −25.5; via; B.Cu into T1 | Same, at plan x = −20.6 from y = 22.6 to −24.5 |
| R3 → T2 | F.Cu from pad 12 to plan x = 42.1, down to y = −26.5, across to (59.5, −26.5); via; B.Cu into T2 | F.Cu from pad 12 to plan x = −42.1, down to y = −23.2; via; B.Cu into T2 |
| R4 → T3 | B.Cu from R4's corner at plan (40.3, −17.5) down to y = −25.0, across to x = 64.0, into T3 | B.Cu from R4's corner at plan (−62.5, −1.6) to (−68.5, −7.6), down to y = −27.0, into T3 |

The gaps differ by half because the cathodes, hence the row tracks, sit on each key's right.

**Column bus.** Each column runs to the controller along a B.Cu lane between two key rows.

- The free band is above a key's socket and below the LED links of the key above: key-local
  y 7.06 to 9.45 of the lower key. Lanes are at y = 7.3, 8.05 and 8.8 (0.75 mm apart, so a via
  on one lane clears the next).
- C0, C1 and C2 run above the R2 keys; C3 and C4 above the R3 keys. A lane starts at a via on
  its column track, at (2.54, lane y), and a column further out takes a lower lane.
- Between two columns the lanes jog in the 2 mm between one column's diode and the next's
  socket, at x = 8.2, 8.95 and 9.7 of the left cell. Which lane takes which x follows the
  stagger: where the right-hand column is higher the top lane turns first, otherwise the bottom
  lane. Lanes then never cross.
- Beside the controller the lanes turn at plan x = ±40.5, 41.2 and 41.9, again in an order that
  avoids crossings, and run to their pads.
- C5 is next to the controller: B.Cu from its pad straight to C5R3's pin 2.

**Controller pads.** The inner pads are assigned top to bottom in the order the tracks arrive:
R1, C2, C1, C0, R2, C4, C3, LED data, C5, R3 (pads 1, 2, 5, 6, 7, 8, 9, 10, 11, 12). The fan-in
is then crossing-free. LED data needs an unrestricted pin and has one (P0.11). The single source
is `pcb/pins.yaml`; the ZMK shield must be generated from it.

## The Grid Router

`tools/pcb_maze.py`, for what has no regular shape: BAT_IN, RAW, RST, LED_EN, LED_GATE, and
the thumb column's run from its trunk to pad 21.

- A* on a 0.1 mm grid over the controller side of the board (plan x 36 to 86, mirrored on the
  right; y −52 to 40), two layers, 8 directions, vias at a cost of 60 cells.
- Obstacles come from the board as it stands: pads (as bounding boxes), tracks, vias, holes,
  rule areas (as bounding boxes) and the outline. Each is grown by the net's clearance, half
  its track width and a 0.08 mm grid margin; items of the same net are not obstacles.
- Deterministic: a fixed net order (COL_T, RST, LED_EN, BAT_IN, RAW, LED_GATE; longest first)
  and fixed tie-breaking. Power nets use the 0.5 mm track and 0.8/0.4 mm via.
- No rip-up and no push and shove. The order matters: with the power nets first, the right
  half's thumb column could not reach its pad.
- It stops with an error naming the net if it finds no route.

## Verification

Commands, from `keyboard/`, with KiCad's Python (see "Running The Tools" in
[pcb.md](pcb.md#running-the-tools)):

```bash
python tools/pcb_generate.py     # both boards: placement, nets, routing, planes (about 15 s)
python tools/pcb_check.py        # DRC, the rules-file check and the fingerprint (about 40 s)
```

Result on 2026-11-23, KiCad 10.0.8:

| Check | Left | Right |
| --- | --- | --- |
| Unconnected | 0 | 0 |
| DRC errors | 0 | 0 |
| DRC warnings | 56 `silk_over_copper`, 34 `silk_overlap`, 48 `text_height` | 52, 34, 48, and 1 `silk_edge_clearance` |
| Tracks / vias | 837 / 145 | 850 / 142 |
| Fingerprint | `27ca349965833f2f` | `575f199c05a9dda2` |
| Custom rules all read | yes | (same file) |

- The **fingerprint** is a hash of every track, via and footprint placement. Two generator runs
  gave the same fingerprints. KiCad writes fresh UUIDs each time, so the files themselves differ.
- The **working loop** was: change a template, generate, run DRC, read the violations (each
  names the two items and their position), adjust. Margins were first worked out by hand in
  key-local coordinates; DRC found the three places the arithmetic was wrong (a via 0.085 mm
  from a column track, a link 0.3 mm from the board edge, a link crossing the bus).

Tightest margins in the templates, by hand (DRC enforces the limits, not these figures):

| Where | Margin | Limit |
| --- | --- | --- |
| Row track to the stem hole | 0.225 mm | 0.2 mm (non-plated hole) |
| Socket's widened pin 1 pad to its peg hole | 0.205 mm | 0.2 mm |
| LED chain's incoming via to the column track | 0.235 mm | 0.2 mm |
| LED chain on F.Cu to the column track (x = 3.05) | 0.26 mm | 0.2 mm |
| Pin 1 drop on F.Cu to the peg hole | 0.27 mm | 0.2 mm |
| Finger key-to-diode link (y = −3.0) to the LED no-track area | 0.055 mm | no overlap |

## Findings

1. **A bad rule silently disables the rest of the rules file.** KiCad 10.0.8 does not accept the
   `min_resolved_spokes` constraint; it stopped reading `.kicad_dru` at that rule, printed
   nothing, and exited normally. The two plated-hole rules after it had never applied.
   `tools/pcb_check.py` now tests for this with a rule that must fire.
2. **Plated pad rings.** Once those rules applied, the hot-swap socket's plated pads (3.3 mm on a
   3.0 mm hole: 0.15 mm ring) and KiCad's JST-PH pads (0.225 mm) failed the 0.254 mm ring
   (PCBWay's normal tier for component holes). The generator widens such pads to a 0.26 mm ring
   (`pth_ring`).
3. **The hole-to-copper rule** as first written also matched a plated pad's copper against a
   non-plated hole. Its condition now leaves that pair to the 0.2 mm board minimum.
4. **The right half's controller was not mirrored.** Its matrix pins faced away from the keys,
   which is why that half always routed worse and RST stayed open. The owner's decision: the
   right nice!nano mounts upside down, so its footprint is flipped and both halves match.
5. **Thermal spokes.** The no-copper area between the controller's pin rows cut the inner planes
   too, leaving one GND pin a single spoke. It now applies to the outer layers only; the antenna
   strip stays clear on all four.
6. **LED footprint.** KiCad's reverse-mount SK6812MINI-E pads sit 0.247 mm from the cut-out. The
   cut-out cannot shrink (body 3.2 × 2.8 mm ±0.1, datasheet), so the pads move 0.06 mm outward.
7. **Design rules need a project.** A board built with `pcbnew.BOARD()` has no project, so
   net classes and rules are dropped on save; the generator reloads each board in a second
   process to apply them. In the process that imports a Freerouting session, KiCad's dangling
   check also missed vias that the reloaded board showed.
8. **Pin choice is a routing tool.** Reassigning the controller pads to the arrival order removed
   every fan-in crossing; moving LED data to the pad nearest the chain's start removed a run
   across the board.
9. **LED chain order matters.** Ending the finger columns at the bottom, next to the thumbs,
   replaced a board-long link with a short one.

## Limits And Open Points

- The templates assume this layout: 19.05 mm key pitch, these part offsets, six finger columns
  and four thumbs. After any layout change, regenerate and run the check; a template or a
  per-half variant may need adjusting. The thumb row and LED data paths use plan coordinates
  and are the most layout-specific.
- The grid router has no rip-up. If a part near the controller moves and it reports no route,
  change the net order or the placement.
- DRC passes, but there has been **no electrical review**: LED data runs beside column tracks
  for about 10 mm at 0.26 mm; VLED and its return are planes; the 0.25 mm signal tracks carry
  only matrix and LED data. Review in KiCad before any fabrication output.
- More silkscreen now overlaps copper (the widened pads reach under footprint outlines), and the
  controller footprint's 0.8 mm pin labels are under JLCPCB's 1.0 mm text height. Warnings only.
- No schematic yet, so no ERC and no schematic-to-board parity check.
