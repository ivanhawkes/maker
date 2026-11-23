# Dongle Case

Status: **generated 2026-11-23, digital checks only.** Nothing is printed and no part has been
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
- **Top:** 2 mm walls and a 1.8 mm face with a 25 × 16 mm window, centred on the display
  module. Two ledges on the back wall sit 0.3 mm over the controller's corners beside the USB
  connector, and the back wall takes the pull of unplugging. The USB opening is 13 mm wide.
- **Screws:** four M3 × 8 from below into corner blocks in the top, the heads recessed in the
  base (drill out the 0.2 mm skin), as on the keyboard case.
- **Feet:** four recesses for 10 mm stick-on feet.
- **Display:** taken as 27.8 × 27.8 mm and 3.2 mm thick with its glass, with a four-pin header
  at the top edge and its pins out of the back. There is room for the fitted header, 8.5 mm
  behind the module, and for wires soldered to it.
- **No reset hole.** The position of the nice!nano's reset button is not in any document here,
  so none is cut. To flash, take the top off, or use a bootloader key in the keymap once one
  is set up.

## Wiring

Four wires, about 30 mm of 28 to 30 AWG stranded, soldered into the controller's pads and to
the display's header pins. The pins are those the firmware is built for
(`firmware/boards/shields/split56/split56_dongle.overlay`).

| Display | nice!nano |
| --- | --- |
| GND | GND |
| VCC | VCC (3.3 V, not RAW) |
| SDA | D2 (P0.17) |
| SCL | D3 (P0.20) |

Wire by the display's printed labels: the order of its four pins differs between sellers.
Check with the dongle unplugged before first use; swapped VCC and GND can destroy the display.

## Assembly And Printing

1. Solder the four wires. Lay the controller on its pad, USB end to the back.
2. Rest the display on the pillars, header uppermost, glass up.
3. Lower the top and fit the four screws from below.

Print the base flat, and the top standing on its back wall: the face is then 60° from the bed
and the front screw blocks end in a 45° face, so neither part needs supports. Profile as for
the keyboard case ([decisions.md](decisions.md)).

## Generating And Checking

```sh
FreeCADCmd tools/dongle_generate.py   # a few seconds; exit 1 if a check fails
```

It writes `base.step`, `top.step`, `dongle.FCStd` (the parts with the controller, display and a
plug as blocks), `print/base.3mf`, `print/top.3mf` and `report.txt`.

**Results, 2026-11-23** (FreeCAD 1.1.4; `cad/dongle/report.txt`). All pass:

- Each part is one valid solid (base 9.1 cm³, top 11.4 cm³); they do not overlap; each mesh is
  closed and has its solid's volume.
- Neither part touches the blocks standing for the controller, its USB connector, a plug with
  a 12.5 × 7 mm overmould, the display or its header.
- The display's back is 0.3 mm above the pillars; the stops and fences hold it against sliding
  down the slope or sideways.
- The ledges hold the controller's USB end down, and the back wall holds it against a pull.

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
- **Wires are not modelled.** There is at least 6 mm between the display's back and the
  controller's parts.
- **Stability:** 39 mm high on feet 11 mm apart across and 31 mm front to back; a stiff cable
  may tip or drag it.
