# Dongle Case

Status: **generated 2026-11-23, the reset switch added 2026-11-24, digital checks only.** Nothing is printed and no part has been
measured. The controller's and the display's sizes come from product pages and common listings,
with slack, because the parts are not here.

The dongle is hand-wired: there is no dongle board (owner, 2026-11-23). The case is generated
by `tools/dongle_generate.py`; the files are in `cad/dongle/`.

## What It Is

Two printed parts, 38.0 × 50.3 mm in plan and 39.4 mm high, with the display on a face sloped
at 30° towards the user and the USB-C port at the back.

```
side view, front on the left                         z, mm
                                        ___
                               ___----  |      36  top of the face
                      ___----  header   |
             ___----  display          |
    ___----  [stop][pillar]   [pillar] |
   |[block]                    [block] |=== USB  0.2 to 8.2
   |        [== nice!nano on its pad ==]|       3.4 controller's underside
   |__________________________________|        0   base's top
   |________________base______________|       -3.4
```

- **Base:** a 3.4 mm plate. The bare nice!nano lies flat on a raised pad between its pin rows,
  3.4 mm up, so wire ends under its pads and a plug's overmould clear the plate. A stop at its
  front end and a guide each side locate it. Four pillars carry the display at its corners;
  the lower two have a stop so it cannot slide down the slope, and all four a fence at the side.
  A tunnel through the pad holds the reset switch.
- **Top:** 2 mm walls and a 1.8 mm face with a 25 × 16 mm window, centred on the display
  module. Two ledges on the back wall sit 0.3 mm over the controller's corners beside the USB
  connector, and the back wall takes the pull of unplugging. The USB opening is 13 mm wide.
- **Screws:** four M3 × 8 from below into corner blocks in the top, the heads recessed in the
  base (drill out the 0.2 mm skin), as on the keyboard case.
- **Feet:** four recesses for 10 mm stick-on feet.
- **Display:** taken as 27.8 × 27.8 mm and 3.2 mm thick with its glass, with a four-pin header
  at the top edge and its pins out of the back. There is room for the fitted header, 8.5 mm
  behind the module, and for wires soldered to it.
- **Reset, from the underside with a paper clip** (owner, 2026-11-24). The controller has no
  reset button, only an RST pad: none is on either face in the listing photo
  ([controller.md](controller.md)). A bootloader key in the keymap cannot reach the dongle
  either: ZMK's `&bootloader` acts on the part whose key was pressed, and the dongle has no
  keys. The keymap lives on the dongle, so it is flashed at every keymap change.
  - **Switch:** an E-Switch TL3342F160QG, the halves' reset switch, hand-wired. It lies on its
    back, actuator down, in a tunnel through the pad: 5.8 mm wide, 2.4 mm high, open at both
    ends, centred 18 mm from the controller's USB end.
  - **Hole:** ø2.8 mm through the base, on the centre line of the underside, 5.4 mm from the
    nearest foot recess. The switch's ø2.0 mm actuator hangs in it, so the floor never holds
    the switch pressed.
  - **Pressing:** the clip meets the actuator about 3 mm in and lifts the switch up to 1.2 mm
    against the tunnel's 1.0 mm roof, on which the controller lies; then the switch clicks.
    Twice quickly for the bootloader.

## Wiring

Six wires of 28 to 30 AWG stranded: four of about 30 mm, soldered into the controller's pads and
to the display's header pins, and two from the reset switch to the controller's RST pad and a
GND pad. The pins are those the firmware is built for
(`firmware/boards/shields/split56/split56_dongle.overlay`).

| Display | nice!nano |
| --- | --- |
| GND | GND |
| VCC | VCC (3.3 V, not RAW) |
| SDA | D2 (P0.17) |
| SCL | D3 (P0.20) |

| Reset switch | nice!nano |
| --- | --- |
| One lead at an end | RST |
| The other lead at that end | GND |

The two leads at one end of the switch are its two contacts; each is joined inside to the lead
at the other end of its side, which is left bare. That is from the drawing: meter the part
before soldering, as for the halves ([pcb.md](pcb.md)).

Wire by the display's printed labels: the order of its four pins differs between sellers.
Check with the dongle unplugged before first use; swapped VCC and GND can destroy the display.

## Assembly And Printing

1. Solder two wires to the reset switch, flat along the leads and no more than 0.6 mm proud of
   them. Slide it into the tunnel, actuator down, until the actuator drops into the hole, the
   wires out of the end nearer the controller's RST pad.
2. Solder the wires to the controller and the display. Lay the controller on its pad, USB end
   to the back.
3. Rest the display on the pillars, header uppermost, glass up.
4. Lower the top and fit the four screws from below.

Print the base flat (the tunnel's roof is a 5.8 mm bridge), and the top standing on its back wall: the face is then 60° from the bed
and the front screw blocks end in a 45° face, so neither part needs supports. Profile as for
the keyboard case ([decisions.md](decisions.md)).

## Generating And Checking

```sh
FreeCADCmd tools/dongle_generate.py   # a few seconds; exit 1 if a check fails
```

It writes `base.step`, `top.step`, `dongle.FCStd` (the parts with the controller, display and a
plug as blocks), `print/base.3mf`, `print/top.3mf` and `report.txt`.

**Results, 2026-11-24** (FreeCAD 1.1.4; `cad/dongle/report.txt`). All pass:

- Each part is one valid solid (base 9.0 cm³, top 11.4 cm³); they do not overlap; each mesh is
  closed and has its solid's volume.
- Neither part touches the blocks standing for the controller, its USB connector, a plug with
  a 12.5 × 7 mm overmould, the display, its header or the reset switch at rest.
- The display's back is 0.3 mm above the pillars; the stops and fences hold it against sliding
  down the slope or sideways.
- The ledges hold the controller's USB end down, and the back wall holds it against a pull.
- The reset switch, lifted 1.2 mm, is against the tunnel's roof. The tunnel and the hole take
  the switch at the top of its ± 0.25 mm tolerances (the generator stops if not).

## Limits And Open Items

None is tested.

- **The display module is a guess.** Board size, thickness, where the glass sits on the board
  and the header's position all vary between sellers. A thinner module than 3.2 mm is loose by
  the difference: pad it with foam tape. If the picture is not centred on the board the window
  is off; it has about 2.5 mm of margin up and down. Buy the display, measure it, and
  regenerate before printing.
- **The controller's front end is held only by its weight, the wires and the plug.** Only the
  USB end is under the ledges.
- **The controller's parts** are taken as 1.6 mm high between the pin rows, and the USB
  connector as centred on the board's thickness (the nice!nano is 3.2 mm thick overall).
- **The reset switch is loose in its tunnel.** Only its actuator in the hole and its two wires
  keep it over the hole; if it wanders, put a dab of hot glue on the wires at the tunnel's
  mouth. Its sizes are from E-Switch's drawing, not a measured part, and where the RST pad is
  along the controller has not been measured. The hole is out of sight: turn the dongle over,
  cable in.
- **Wires are not modelled.** There is at least 6 mm between the display's back and the
  controller's parts.
- **Stability:** 39 mm high on feet 11 mm apart across and 31 mm front to back; a stiff cable
  may tip or drag it.
