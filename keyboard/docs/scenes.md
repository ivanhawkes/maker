# Showcase Scenes

Status: **built and rendered 2026-11-23.** These are pictures of the design files, not of a
built keyboard: nothing here is evidence of fit or function. The keycaps are the published
models, not yet checked against the owner's set.

Two Blender files, `cad/scenes/kb1.blend` (keyboard 1, black) and `cad/scenes/retro.blend`
(keyboard 2, off-white with a burnt orange plate and stripe), are made by script from the
generated case files. Nothing in them is placed by hand, so a regenerated case is shown by
running the two scripts again. Do not edit the files: change `tools/scene_build.py`.

## What Is In Them

Each file has two scenes:

| Scene | Shows |
| --- | --- |
| `assembled` | Both halves on a desk, each turned 8° outwards. The retro one stands on its raked plinth |
| `exploded` | The left half taken apart along its assembly axis: screws, tray, battery, board, controller, plate, lid, switches, keycaps; and for the retro case its plinth and stripe ring |

Each scene has five cameras, bound to timeline markers: frames 1 to 5 step through them.

| Frame | Assembled | Exploded |
| --- | --- | --- |
| 1 | Hero, three-quarter from the front left | Hero, three-quarter |
| 2 | Straight down | From the side |
| 3 | Low, from the front | From the front |
| 4 | Detail: the left half's thumb keys and lid | From above |
| 5 | The rear, showing the USB openings | Detail: switches and keycaps |

Each camera stands in a fixed direction and as near as keeps its subject in frame, so the
framing follows the model. Lighting is five area lights round the subject: cool, low and
rim-lit on a dark floor for the black keyboard; warm on a brown floor for the retro one.

**What is modelled and what is a stand-in.** The printed parts are the generated case files.
The keycaps are the KLP Lamé models and the switch is kiswitch's MX model, coloured as a
Kailh Speed Bronze from memory (clear top, bronze stem; the white base is a guess). The board
is the bare outline in green, and the controller, battery and screws are plain shapes of the
right size and position, taken from the case generator's own check blocks. No diodes, sockets,
LEDs, connector or wiring are shown.

## Keycaps

Arranged as the owner's set is (owner, 2026-11-23), per half:

| Keys | Model | Count |
| --- | --- | --- |
| Number row and bottom row | Saddle Tilted, leaning towards the home row | 12 |
| The two middle rows | Saddle | 11 |
| Home row, index finger (C4R3) | Saddle Homing | 1 |
| The two inner thumb keys (T0, T1) | Thumb | 2 |
| The two outer thumb keys (T2, T3) | 1.5U Thumb V, lengthways | 2 |

A cap sits where the end of its stem hole meets the top of the switch's stem: its underside is
12.1 mm above the board and a Saddle's top 17.8 mm. Two things were my reading of the models:
the bottom row's tilted caps are turned round so they lean towards the home row, and the 1.5u
caps have their cut edge towards the user. The owner looked at the stills and said the keycaps
look right (2026-11-24). The caps themselves are still to be measured.

## Making Them

```sh
FreeCADCmd tools/scene_export.py                                 # meshes for Blender; about 1 minute
blender -b --python tools/scene_build.py                         # the two .blend files only
blender -b --python tools/scene_build.py -- --render             # and 20 stills at 1920 x 1080
blender -b --python tools/scene_build.py -- --render --size 2k   # 2560 x 1440
blender -b --python tools/scene_build.py -- --render --size 4k   # 3840 x 2160
```

`--only kb1` or `--only retro` does one keyboard. `--preview` renders small quick stills into
`cad/scenes/build/preview/` and leaves the kept files alone; use it to try a change.

Blender has no STEP import, so `tools/scene_export.py` converts the case parts, the five
keycap models and the switch to STL in `cad/scenes/build/` (not kept in git), with a manifest
of positions. Run it after any case generator. Stills go to `cad/scenes/renders/<size>/`,
named `<keyboard>-<scene>-<camera>.png`.

**Rendering uses the graphics card.** The devenv's Blender 5.2.3 is built with CUDA and OptiX
(`devenv.nix`, since 2026-11-24), and the script renders on every card that Blender finds,
together: here the RTX 5070 Ti and the RTX 5060 Ti (owner, 2026-11-24). With none it falls
back to the CPU. Measured here: the 20 stills at 4k took 10 minutes on the 5060 Ti alone and
8 minutes 35 seconds on both cards. The second card helps little because most of each
still's time is spent preparing the scene and saving the picture, not tracing it. On the CPU (a Ryzen 9 3900X) the 1080p set took 24
minutes and one 4k still 4 minutes, about eight times slower. The 1080p stills in the
repository are the CPU ones; the 2k set has not been rendered.

## Credit And Licence

The keycap models are **KLP Lamé by braindefender**
(<https://github.com/braindefender/KLP-Lame-Keycaps>), CC BY-SA 4.0. The scene files and every
picture rendered from them contain those models, so they are CC BY-SA 4.0 as well and must
carry that credit wherever they are shown. The switch model is from kiswitch (MIT / CC BY-SA
4.0). The same note is in a text block named `CREDITS` inside each `.blend` file.

## Limits

- The keycaps are the published models; the moulded set may differ. To check when measured.
- Colours are picked by eye, not matched to Bambu Lab filaments or to the caps.
- The prints are shown smooth, with a fine grain: no layer lines or bed texture.
- No power switch is shown, so its slot shows the controller's USB connector behind it as a
  bright shape.
- The retro plinth's rake and the halves' 8° turn are the only posing; no tenting wedges, no
  dongle, no cables.
- A black keyboard on a dark floor is lit for mood: detail in the shadows is lost by design.
