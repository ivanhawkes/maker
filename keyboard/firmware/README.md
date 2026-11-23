# Firmware

ZMK configuration for the three parts: the left half, the right half and the desk dongle.

**Status (2026-11-23): all four images compile. Nothing has been flashed or run on hardware.**
Consult the owner before flashing a board ([architecture](../docs/architecture.md)).

| Part | Role | Shield | Image size (flash) |
| --- | --- | --- | --- |
| Left half | Split peripheral: scans its keys, drives its LEDs | `split56_left` | 197 324 B, 24 % |
| Right half | Split peripheral | `split56_right` | 197 324 B, 24 % |
| Dongle | Split central: keymap, USB keyboard, display | `split56_dongle dongle_display` | 355 936 B, 44 % |
| Any | Clears bonds and saved settings | `settings_reset` (ZMK's own) | 51 372 B, 6 % |

The name `split56` (shown to the PC as "Split56") stands for the moment (owner, 2026-11-23). To
change it, change `SHIELD` and `NAME` in [`tools/zmk_generate.py`](../tools/zmk_generate.py) and
rename the files in `config/`.

## Files

| Path | What | Edited by |
| --- | --- | --- |
| `config/west.yml` | The pinned ZMK and display-module commits | Hand; re-pin deliberately ([decisions](../docs/decisions.md)) |
| `config/split56.keymap` | The keymap. QWERTY base, accepted by the owner (2026-11-23); the thumb keys and Fn layer are a first proposal | Hand |
| `config/split56.conf` | User settings for all three parts | Hand |
| `boards/shields/split56/` | The shield: matrix, key positions, LED chain, LED supply switch, dongle | **Generated**: `python tools/zmk_generate.py` |
| `zephyr/module.yml`, `build.yaml` | Makes this directory a ZMK module; the list of builds | Hand |
| `workspace/` | ZMK, Zephyr and the build output. Not in git (2.9 GB) | `west` |

The shield is generated from [`pcb/pins.yaml`](../pcb/pins.yaml), the same pin table the PCB
generator reads, and from the layout's generated key positions. Do not edit it by hand.

## Versions

- ZMK `4de313367288aad5aeaa1243890e40dc813f7008` (main, 2026-11-14), which brings Zephyr
  `v4.1.0+zmk-fixes`.
- [zmk-dongle-display](https://github.com/englmaxi/zmk-dongle-display)
  `2bb333f87136d33e94a49d86236ed9ec254a8060` (2026-02-13).
- Built on 2026-11-23 with the devenv shell's tools: Arm GNU Toolchain 15.3.Rel1 (GCC 15.3.1),
  west 1.5.0, CMake 4.4.4, Python 3.14. There is no Zephyr SDK; `ZEPHYR_TOOLCHAIN_VARIANT` is
  `gnuarmemb` (set by the devenv shell). The build prints GCC 15 warnings in picolibc and
  mbedTLS, and for the halves a Kconfig warning that USB is off, which is right for a
  peripheral.
- Board: `nice_nano//zmk`, which defaults to revision 2.0.0 (the nice!nano v2).

## Building

From `keyboard/`, inside the devenv shell. Once, to fetch the sources (about 2.9 GB, two
minutes here):

```sh
mkdir -p firmware/workspace/config
ln -sf ../../config/west.yml firmware/workspace/config/west.yml
(cd firmware/workspace && west init -l config && west update --narrow -o=--depth=1)
```

The workspace is a directory of its own because `west` puts Zephyr in `zephyr/` beside the
manifest, where this module's own `zephyr/module.yml` already is.

Then, for each image (about 25 s each here):

```sh
python tools/zmk_generate.py          # after any change to pins.yaml or the layout
cd firmware/workspace
build() {  # build <directory> <shields>
  west build -p -s zmk/app -d "build/$1" -b nice_nano//zmk -- -DSHIELD="$2" \
    -DZMK_CONFIG="$PWD/../config" -DZMK_EXTRA_MODULES="$PWD/.." \
    -DZephyr_DIR="$PWD/zephyr/share/zephyr-package/cmake"
}
build left   split56_left
build right  split56_right
build dongle "split56_dongle dongle_display"
build reset  settings_reset
```

Each image is `firmware/workspace/build/<directory>/zephyr/zmk.uf2`. `Zephyr_DIR` is passed
because `west zephyr-export` would write to the home directory.

## Checks

```sh
python tools/zmk_generate.py --check         # the shield matches pins.yaml and the layout
python tools/zmk_generate.py --check-build   # what the builds resolved, against pins.yaml
python tools/pcb_review.py                   # KiCad's Python: board nets against the firmware matrix
```

Results on 2026-11-23 (compile-time checks only):

- All four images build, exit 0.
- `--check-build`: on both halves the built devicetree resolves the rows to P0.06, P0.22,
  P1.06 and P1.11, the columns to P0.20, P0.17, P0.08, P1.00, P0.24, P1.04 and P1.13, LED data
  to P0.11 and the LED supply enable to P0.31, through ZMK's own Pro Micro pin map. All match
  `pins.yaml`. 28 LEDs a half, brightness cap 20 %. The dongle is a central for two peripherals
  with the display on.
- `pcb_review.py`: every key's row and column nets on both boards are the firmware's matrix
  position for that key.

## Flashing And Pairing (From ZMK's Documentation; Not Yet Done)

1. Put a nice!nano into its bootloader: double-press reset (on the PCB, or bridge RST to GND
   twice on a bare dongle). It appears as a USB drive. Copy the `.uf2` onto it; it restarts
   by itself.
2. First flash `reset/zephyr/zmk.uf2` to each of the three boards. This clears old bonds.
3. Then flash each board's own image: left, right, dongle.
4. Power all three. The halves bond to the dongle by themselves the first time all are on. If
   one does not, reset it and the dongle at about the same time.
5. To start again, repeat from step 2: flashing ordinary firmware does not clear bonds.

Record the boards, images and what happened in [verification](../docs/verification.md) when this
is first done.

## Lighting

What stock ZMK at this commit does with the settings here, read from its source, not observed:

- **Brightness cap, 20 %.** Fixed in the shield (`CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX=20`): every
  effect is scaled by it. It cannot be raised from `config/`. The reason is the power switch's
  0.3 A rating ([electrical review](../docs/pcb.md#electrical-review-2026-11-23)).
- **Off by default, and off when idle.** Lighting starts off. A half's lighting, and its LED
  supply, go off after 60 s without a key press **on that half**: ZMK does not share activity
  between the halves, so the idle half goes dark while the other is still typing. They come
  back on the next key press on that half if lighting was on.
- **No fade.** The lighting cuts off; ZMK has no fade to black.
- **On and off keys, not a toggle** (see the keymap): each part keeps its own state.
- **The dongle carries a one-LED dummy strip.** ZMK relays a lighting key to the halves only if
  the lighting behaviour exists on the central. The dummy's data pin is P0.11, unconnected.
- **The LED supply is on at start-up for a moment.** ZMK's external-power driver switches on
  when it starts, then applies the saved state. On the very first start nothing is saved, so the
  supply (with dark LEDs, about 28 mA) stays on until the half first goes idle, 60 s.
- **Data against the supply.** When lighting goes off ZMK switches the supply off and then
  sends one all-off frame. C2 on the board holds the supply up for about 0.1 s (estimate), so
  the frame arrives while the LEDs are powered; R4 limits the current if it does not. Whether
  the data pin then rests low is **to check with a scope**.
- ZMK repeats the frame every 50 ms while lighting is on, so data sent during the soft start
  is simply sent again; no start-up delay is needed.

## Not Verified

- Nothing has run on hardware: no flashing, pairing, key event, LED or current measurement.
- The keymap's thumb keys and Fn layer are a first proposal, untried.
- The display is the common 0.96 in 128 × 64 SSD1306 I²C module (owner, 2026-11-23), at address
  0x3C. Its devicetree properties are the usual ones for that module, from memory: check them
  on the part.
- The display module is pinned at a commit nine months older than the ZMK pin. It compiles;
  whether it runs correctly is unknown.
- The halves' Bluetooth names are ZMK's defaults.
