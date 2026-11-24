# Target Controller

**The owner's choice (2026-11-24), subject to passing testing:** the board bought for both
halves and the dongle is a Tenstar Robot **"ProMicro NRF52840"**, AliExpress item
[1005009890279520](https://www.aliexpress.com/item/1005009890279520.html). It is a
nice!nano-compatible clone, not a genuine nice!nano v2, which is what the design documents
assumed until now. Nothing here is tested: no board has arrived or been measured.

![Both faces of the ProMicro NRF52840, from the listing](../parts/datasheets/Tenstar_ProMicro_NRF52840_listing_photo.png)

The photo is the owner's screenshot of the listing
(`parts/datasheets/Tenstar_ProMicro_NRF52840_listing_photo.png`). The listing's text could not be read automatically, so its
stated specifications are not recorded here.

## What The Photo Shows

- Silkscreen "TENSTAR ROBOT" and "ProMicro NRF52840"; a red board; an nRF52840 in the QIAA
  package.
- **Pads as the nice!nano v2:** 13 a side. One row reads B+, RAW, GND, RST, VCC, 031, 029,
  002, 115, 113, 111, 010, 009; the other B−, 006, 008, GND, GND, 017, 020, 022, 024, 100,
  011, 104, 106. Pad for pad these are the GPIOs in [`pcb/pins.yaml`](../pcb/pins.yaml)
  (pads 13 to 24 and 1 to 12), so the boards and the firmware need no change **if the labels
  are true**.
- Three more holes, 101, 102 and 107, in a row across the board near the antenna end, and
  four programming pads (VDD, DIO, CLK, GND) on the back. The keyboard uses none of them.
- **No BQ24075.** There is no small square charger chip: the power parts are SOT-23 size.
- A ceramic chip antenna at the end away from USB, where the boards' copper keep-out expects
  the antenna.
- **The USB-C socket is sunk through the board**: its shell shows on both faces.

## What Others Report About This Kind Of Board

Read 2026-11-24. These are community notes about "SuperMini" or "ProMicro" nRF52840 boards
from several makers and batches. None is verified on the boards bought, and the batches differ.

| Subject | Report | Source |
| --- | --- | --- |
| Charger | LTH7R or TP4054, a plain linear charger, not the nice!nano's power-path charger. Sellers give 100 mA | [nRFMicro wiki](https://github.com/joric/nrfmicro/wiki/Alternatives) |
| Battery pins | B+ and B− are said to be the same nets as RAW and GND. This came through a web search summary of the same wiki, not a passage read directly | Search, 2026-11-24 |
| 3.3 V regulator | A separate regulator with an enable pin; the part differs by batch. P0.13 low switches VCC off, as on the nice!nano v2 | nRFMicro wiki |
| Current with VCC off | **About 700 µA on early batches**, from a 5.6 kΩ pull-up on the VCC control; under 20 µA with it removed. Batches after April 2024 are said to have 10 MΩ there | nRFMicro wiki |
| Sleep current | 4 µA on good boards; **60 µA** on boards where a Schottky diode was replaced by an ordinary one | [sasodoma/nrf52840-promicro](https://github.com/sasodoma/nrf52840-promicro), nRFMicro wiki |
| Battery measurement | The schematic puts a divider on P0.04, but one maker found it on **P0.24**; the wiki says it is not fitted. With USB in, VDDH is said to rise to 5 V, so the battery level cannot be read while charging | Both |
| LEDs | Colours swapped against the nice!nano: red is the user LED, blue the charger's | nRFMicro wiki |
| Radio | Complaints about the 32.768 kHz crystal, and a warning from ZMK's community not to trust these boards in a real keyboard | nRFMicro wiki |
| Firmware | Built as a nice!nano v2 in ZMK. A power cycle after flashing is said to be needed before deep sleep works again | nRFMicro wiki |

## What It Changes In This Design

- **The battery reaches the controller through the socketed RAW pin**
  ([pcb.md](pcb.md)). That is right only if RAW is the battery's net on this board, as it is
  on a nice!nano v2. If RAW were the USB supply, plugging in USB would put 5 V on the cell.
  **Check with a meter before any cell is connected** (tests 1 and 2 below).
- **The [charger check](pcb.md#charger-check-against-the-datasheet-2026-11-24) is about the
  genuine nice!nano's BQ24075 and does not apply to this board**: no power path, and the
  5 hour safety timer and the figures there are not this charger's. With no power path the
  controller and the LEDs both run from the cell's node while charging, so "LED supply off
  when idle" matters at least as much. The charger's own datasheet is not yet in
  `parts/datasheets/`, because the part on the bought boards is not known.
- **The [power budget](architecture.md#power-budget-2026-11-24) uses ZMK's figures for genuine
  nice!nanos.** This firmware switches VCC off (P0.13 low) whenever the lighting is off, which
  is exactly the state the 700 µA report is about. At 700 µA more, a 400 mAh cell lasts under
  3 weeks and the 8 week target fails; at 60 µA more it is about 15 weeks and passes; at 4 µA
  the budget stands. So the sleep and VCC-off currents decide whether the board passes. If only
  the VCC-off state is bad, P0.13 can be taken out of the shield's power control, since
  nothing on these PCBs uses the VCC pin.
- **Column C4 is on P0.24** (pad 8). A battery divider on that pin, if fitted, would load the
  column and draw from the cell all the time (test 4).
- **The sunk USB socket** stands below the board as well as above it. The PCBs are notched
  under the plug, not under the socket's body, and on the right half the controller is fitted
  face down: the heights need measuring against the sockets' gap (test 7).
- **Battery level reports** may read wrong while USB is in. Not a fault of the keyboard.
- **No change is made to the boards, the firmware or the cases.** The pin table keeps
  "nice!nano v2", which is what ZMK builds this board as.

## Tests To Pass

In this order; stop at a failure. Record the results in [verification.md](verification.md).
Tests 1 and 2 come before any cell is connected to a board.

1. **Unpowered, with a meter:** RAW to B+ is a short, and GND to B−. RAW is not shorted to
   VCC or to the USB socket's supply pin.
2. **On USB, no cell, then with a cell watched by a meter:** note the voltage on RAW. Then,
   with a protected cell on B+ and B−, the cell must never be taken above 4.25 V, and
   charging must stop at about 4.2 V. Note the charge current and which LED shows it.
3. **Pins:** flash the left or right image and check every pad the keyboard uses does what
   `pcb/pins.yaml` says (rows, columns, LED data on P0.11, LED enable on P0.31, P0.13
   switching VCC).
4. **P0.24:** resistance from pad 8 to RAW and to GND with the board unpowered: no divider.
5. **Currents, from the cell, lighting off:** deep sleep; connected and idle; a key held; and
   idle with VCC switched off. **Pass: the average for the power budget's day is 253 µA or
   less.** Power-cycle the board after flashing before measuring sleep.
6. **Radio:** both halves connected to the dongle for a working day without drop-outs; note
   the range against the case's battery position.
7. **Size:** against the 1:1 prints in `pcb/print/`: pad pitch and row spacing, length, where
   the antenna ends, how far the USB socket stands below and above the board, and the tallest
   part, for the right half's face-down fitting.

If it fails: a genuine nice!nano v2 fits the same footprint, pin table and firmware.
