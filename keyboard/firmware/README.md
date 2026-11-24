# Firmware

ZMK configuration for the three parts: the left half, the right half and the desk dongle.

**Status (2026-11-24): all four images compile, the halves with the lighting fade. Nothing has been flashed or run on hardware.**
Consult the owner before flashing a board ([architecture](../docs/architecture.md)).

| Part | Role | Shield | Image size (flash) |
| --- | --- | --- | --- |
| Left half | Split peripheral: scans its keys, drives its LEDs | `split56_left` | 198 068 B, 24 % |
| Right half | Split peripheral | `split56_right` | 198 068 B, 24 % |
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
| `src/led_strip_fade.c`, `dts/bindings/led-strip-fade.yaml`, `CMakeLists.txt` | The lighting fade: a small driver between ZMK and the LED chain ([lighting](#lighting)) | Hand |
| `src/led_strip_fade_level.h`, `src/led_strip_fade_test.c` | The fade's arithmetic, and its test, which runs on the computer | Hand |
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
cc -o /tmp/fade_test firmware/src/led_strip_fade_test.c && /tmp/fade_test   # the fade's arithmetic
```

Results on 2026-11-23 (compile-time checks only):

- All four images build, exit 0.
- `--check-build`: on both halves the built devicetree resolves the rows to P0.06, P0.22,
  P1.06 and P1.11, the columns to P0.20, P0.17, P0.08, P1.00, P0.24, P1.04 and P1.13, LED data
  to P0.11 and the LED supply enable to P0.31, through ZMK's own Pro Micro pin map. All match
  `pins.yaml`. 28 LEDs a half, brightness cap 20 %. The dongle is a central for two peripherals
  with the display on.
- 2026-11-24, with the fade: all four images build again, the fade driver without a warning.
  `--check-build` also finds each half's lighting going through the fade, 50 ms in and
  5000 ms out, ending at that half's idle timeout of 65 000 ms. The fade's test passes. The
  dongle and reset images are the same size as before.
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

What the firmware does with the settings here. Read from ZMK's source at this commit and from
the fade driver, and compiled; **not observed on hardware.**

- **Brightness cap, 20 %.** Set in the shield (`CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX=20`): every
  effect is scaled by it. The reason is the power switch's 0.3 A rating
  ([electrical review](../docs/pcb.md#electrical-review-2026-11-23)). **Corrected 2026-11-24:**
  `config/split56.conf` is merged after the shield's settings and can override them (tried: a
  cap of 30 there was built in). The fade driver now stops the build if the cap is above 20
  (tried: it does), and `--check-build` checks the built value.
- **Off by default; lit while typing.** Lighting starts off. Once switched on, a half is lit at
  full for 60 s after the last key press **on that half**, then fades to black over 5 s
  (owner, 2026-11-24). At 65 s ZMK calls the half idle and switches the lighting and the LED
  supply off (within a second: ZMK looks once a second). The next key press on that half
  brings it back.
- **Fade in over 50 ms** (owner, 2026-11-24), whenever the lighting comes on: after idle, or
  with its key. A key pressed during the fade-out brings the level back up at the same rate,
  starting with ZMK's next frame, at most 50 ms later.
- **How.** ZMK has no fade. `src/led_strip_fade.c` is a led strip driver that ZMK is given in
  place of the LED chain (`zmk,underglow` in the shield). It passes every frame on, dimmed by
  a level worked out from the time since the half's last key press, and while lighting up it
  repeats the frame every 10 ms (ZMK's own frames are 50 ms apart): black, then five steps.
  It only ever dims, so the cap holds, and it keeps no state that is saved. The times are
  `HOLD_MS`, `FADE_IN_MS` and `FADE_OUT_MS` in `tools/zmk_generate.py`, which writes them to
  the shield with the halves' idle timeout (the 60 s plus the fade-out).
- **The fade-out is a straight line in LED value.** At the 20 % cap a colour has at most 51
  levels, so the fade has at most 51 steps in 5 s, and they will show most near black. Whether
  a straight line looks even is to judge on the LEDs; the curve is one line in
  `src/led_strip_fade_level.h`.
- **Each half on its own.** ZMK does not share activity between the halves, so the idle half
  fades out while the other is still typing.
- **Switching the lighting on from the other half while this one is idle** leaves this one
  black with its LED supply on (about 28 mA) until a key is pressed on it or it sleeps. Stock
  ZMK would light it at full there instead.
- **On and off keys, not a toggle** (see the keymap): each part keeps its own state.
- **The dongle carries a one-LED dummy strip**, with no fade. ZMK relays a lighting key to the
  halves only if the lighting behaviour exists on the central. The dummy's data pin is P0.11,
  unconnected. Its display blanks after 60 s.
- **The LED supply is on at start-up for a moment.** ZMK's external-power driver switches on
  when it starts, then applies the saved state. On the very first start nothing is saved, so the
  supply (with dark LEDs, about 28 mA) stays on until the half first goes idle, 65 s.
- **Data against the supply.** When lighting goes off ZMK switches the supply off and then
  sends one all-off frame. C2 on the board holds the supply up for about 0.1 s (estimate), so
  the frame arrives while the LEDs are powered; R4 limits the current if it does not. The fade
  driver sends nothing of its own once ZMK has the lighting off. Whether the data pin then
  rests low is **to check with a scope**.
- ZMK repeats the frame every 50 ms while lighting is on, so data sent during the soft start
  is simply sent again; no start-up delay is needed. The fade-in's first frames fall in the
  soft start too: on hardware the LEDs may light a little later than 50 ms.

## Not Verified

- Nothing has run on hardware: no flashing, pairing, key event, LED or current measurement.
- The fade is compiled and its arithmetic tested on the computer. Its timing, its look and
  the frames every 10 ms while lighting up are untried on LEDs.
- The keymap's thumb keys and Fn layer are a first proposal, untried.
- The display is the common 0.96 in 128 × 64 SSD1306 I²C module (owner, 2026-11-23), at address
  0x3C. Its devicetree properties are the usual ones for that module, from memory: check them
  on the part.
- The display module is pinned at a commit nine months older than the ZMK pin. It compiles;
  whether it runs correctly is unknown.
- The halves' Bluetooth names are ZMK's defaults.
