#!/usr/bin/env python3
"""Electrical review figures for the generated boards. Read-only: it changes nothing.

    python tools/pcb_review.py            # both boards; exit 1 if a netlist check fails

Needs KiCad 10's pcbnew and PyYAML (docs/pcb.md, "Running the tools"). There is no schematic
yet, so the netlist checks here are the only independent test that the board's nets are the
matrix, LED chain and power circuit that docs/pcb.md describes. The rest are measurements
for the review in docs/pcb.md: copper resistance, plane necks, thermal spokes, LED data
running beside other nets, and plane copper under the module's antenna end.
"""

from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import pcbnew
import yaml

from zmk_generate import COLS, ROWS, matrix_rc, read_keys

ROOT = Path(__file__).resolve().parent.parent
MM = pcbnew.ToMM
RHO = 1.72e-8        # ohm metre, copper at 20 C
OUTER = 35e-6        # 1 oz finished outer copper
INNER = 17.5e-6      # JLCPCB's 0.5 oz inner copper, the thinner of the two fab houses
# The nice!nano is 17.8 x 33.4 mm; from the official pinout image the antenna section is
# about the last 5 mm at the end away from USB. Read off an image, not measured.
MODULE_HALF_W, MODULE_END, ANTENNA_LEN = 8.9, 16.7, 5.0


def dist_seg(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / n))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def kind(net: str) -> str:
    for prefix in ("COL_", "ROW_", "K_", "LED_D"):
        if net.startswith(prefix):
            return {"COL_": "column", "ROW_": "row", "K_": "key-to-diode", "LED_D": "LED data"}[prefix]
    return net


def review(side: str) -> list[str]:
    board = pcbnew.LoadBoard(str(ROOT / "pcb" / side / f"{side}.kicad_pcb"))
    pins = yaml.safe_load((ROOT / "pcb" / "pins.yaml").read_text())
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    bad: list[str] = []

    def net_name(pad):
        # KiCad's placeholder for a pin the schematic marks unconnected counts as no net.
        return "" if pad.GetNetname().startswith("unconnected-") else pad.GetNetname()

    def nets_of(ref, number):
        return {net_name(p) for p in fps[ref].Pads() if p.GetNumber() == number}

    def net_of(ref, number):
        nets = nets_of(ref, number)
        if len(nets) != 1:
            bad.append(f"{ref}.{number}: nets {sorted(nets)}")
        return next(iter(nets), "")

    members = defaultdict(set)
    for ref, fp in fps.items():
        for p in fp.Pads():
            if net_name(p):
                members[net_name(p)].add(f"{ref}.{p.GetNumber()}")
    print(f"\n===== {side} =====")

    # --- netlist: controller pads against pins.yaml
    want = {pad: f"ROW_{r}" for r, pad in pins["rows"].items()}
    want |= {pad: f"COL_{c}" for c, pad in pins["columns"].items()}
    want |= {pins["led_data"]: "LED_DATA", pins["led_power_enable"]: "LED_EN", pins["power"]["rst"]: "RST",
             pins["power"]["raw"]: "RAW"}  # the 3.3 V output pad is unused: no net
    want |= {pad: "GND" for pad in pins["power"]["gnd"]}
    for pad in pins["controller"]["pads"]:
        got = net_of("U1", str(pad))
        if got != want.get(pad, ""):
            bad.append(f"U1.{pad}: net {got!r}, pins.yaml says {want.get(pad, '')!r}")

    # --- netlist: matrix. Column -> switch pin 2, pin 1 -> anode, cathode -> row.
    matrix = {}
    n_keys = sum(1 for r in fps if r.startswith("SW") and r[2:].isdigit())
    for i in range(1, n_keys + 1):
        col, k, anode, row = net_of(f"SW{i}", "2"), net_of(f"SW{i}", "1"), net_of(f"D{i}", "2"), net_of(f"D{i}", "1")
        if not (col.startswith("COL_") and row.startswith("ROW_") and k == anode and members[k] == {f"SW{i}.1", f"D{i}.2"}):
            bad.append(f"SW{i}: column {col}, key net {k} {sorted(members[k])}, anode {anode}, row {row}")
        if (row, col) in matrix:
            bad.append(f"SW{i} and {matrix[(row, col)]} share {row}/{col}")
        matrix[(row, col)] = f"SW{i}"
    # The firmware's matrix position of each key (tools/zmk_generate.py) against the board's nets.
    layout = read_keys(side)
    for (row, col), sw in matrix.items():
        r, c = matrix_rc(pins, "L", layout[fps[sw].GetValue()])
        if (row, col) != (f"ROW_{ROWS[r]}", f"COL_{COLS[c]}"):
            bad.append(f"{sw} ({fps[sw].GetValue()}): board {row}/{col}, firmware ROW_{ROWS[r]}/COL_{COLS[c]}")
    print(f"matrix: {n_keys} keys on {len(matrix)} distinct row/column pairs, "
          f"{len({r for r, _ in matrix})} rows x {len({c for _, c in matrix})} columns, as the firmware's transform")

    # --- netlist: LED chain, walked from R4, the series resistor on the controller's data pad
    if {net_of("R4", "1"), net_of("R4", "2")} != {"LED_DATA", "LED_DIN"} or len(members["LED_DATA"]) != 2:
        bad.append(f"R4: nets {net_of('R4', '1')}, {net_of('R4', '2')}; LED_DATA {sorted(members['LED_DATA'])}")
    led_din = {net_of(r, "4"): r for r in fps if r.startswith("LED")}
    chain, net = [], "LED_DIN"
    while net in led_din:
        led = led_din[net]
        chain.append(led)
        if net_of(led, "1") != "VLED" or net_of(led, "3") != "GND":
            bad.append(f"{led}: supply pads on {net_of(led, '1')}, {net_of(led, '3')}")
        if len(members[net]) != 2:
            bad.append(f"{net}: {sorted(members[net])}")
        net = net_of(led, "2")
    if len(chain) != n_keys or net != "":  # the last LED's output has no net
        bad.append(f"LED chain: {len(chain)} LEDs, ends on {net!r}")
    print(f"LED chain: {len(chain)} LEDs in one chain from U1.{pins['led_data']} through R4, "
          f"{chain[0]} ({fps['SW' + chain[0][3:]].GetValue()}) to {chain[-1]} ({fps['SW' + chain[-1][3:]].GetValue()})")

    # --- netlist: power and the load switch
    on_pad = "1" if side == "left" else "3"
    expect = {
        "BAT_IN": {"J1.1", "SW_PWR.2"},
        "RAW": {f"SW_PWR.{on_pad}", f"U1.{pins['power']['raw']}", "Q1.2", "R1.1", "C2.1"},
        "LED_GATE": {"Q1.1", "R1.2", "C2.2"},     # and one end of R3, checked below
        "LED_GATE_DRV": {"Q2.3"},                 # and the other
        "LED_EN": {f"U1.{pins['led_power_enable']}", "Q2.1", "R2.1"},
        "RST": {f"U1.{pins['power']['rst']}", "SW_RST.1"},
        "VLED": {"Q1.3", "C1.1"} | {f"{l}.1" for l in chain},
        "GND": {"J1.2", "Q2.2", "R2.2", "C1.2", "SW_RST.2"} | {f"U1.{p}" for p in pins["power"]["gnd"]} | {f"{l}.3" for l in chain},
    }
    if {net_of("R3", "1"), net_of("R3", "2")} != {"LED_GATE", "LED_GATE_DRV"}:
        bad.append(f"R3: nets {net_of('R3', '1')}, {net_of('R3', '2')}")
    for net, pads in expect.items():
        if members[net] - {"R3.1", "R3.2"} != pads:
            bad.append(f"{net}: extra {sorted(members[net] - pads)}, missing {sorted(pads - members[net])}")
    print("power nets:", "as docs/pcb.md" if not bad else "see FAILED below")

    # --- copper: tracks and vias per net
    tracks = defaultdict(list)   # net -> (layer, a, b, width mm)
    vias = defaultdict(list)     # net -> (pos, diameter, drill)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            vias[t.GetNetname()].append(((MM(t.GetPosition().x), MM(t.GetPosition().y)), MM(t.GetWidth(pcbnew.F_Cu)), MM(t.GetDrillValue())))
        else:
            tracks[t.GetNetname()].append((t.GetLayer(), (MM(t.GetStart().x), MM(t.GetStart().y)), (MM(t.GetEnd().x), MM(t.GetEnd().y)), MM(t.GetWidth())))

    def copper(net):
        length = sum(math.hypot(a[0] - b[0], a[1] - b[1]) for _, a, b, _ in tracks[net])
        ohms = sum(RHO * math.hypot(a[0] - b[0], a[1] - b[1]) * 1e-3 / (w * 1e-3 * OUTER) for _, a, b, w in tracks[net])
        return length, ohms, sorted({w for *_, w in tracks[net]}), sorted({(d, h) for _, d, h in vias[net]})

    print("copper (all of a net's tracks in series: an upper bound on any one path):")
    for net in ("BAT_IN", "RAW", "LED_GATE", "LED_GATE_DRV", "LED_EN", "LED_DATA", "LED_DIN", "RST"):
        length, ohms, widths, vs = copper(net)
        print(f"  {net:12s} {length:6.1f} mm, widths {widths} mm, {ohms * 1e3:5.1f} mohm, {len(vias[net])} vias {vs}")
    links = [(copper(n)[0], n, len(vias[n])) for n in members if n.startswith("LED_D") and n not in ("LED_DATA", "LED_DIN", "LED_DOUT_END")]
    print(f"  LED chain links: {len(links)}, {min(links)[0]:.1f} to {max(links)[0]:.1f} mm (longest {max(links)[1]}, {max(links)[2]} vias)")
    # VLED and GND stubs to the planes
    for net in ("VLED", "GND"):
        by_ref = defaultdict(list)
        for fp in fps.values():
            for p in fp.Pads():
                if p.GetNetname() == net and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                    pos = (MM(p.GetPosition().x), MM(p.GetPosition().y))
                    for _, a, b, w in tracks[net]:
                        if min(math.dist(pos, a), math.dist(pos, b)) < 0.01:
                            by_ref["LED" if fp.GetReference().startswith("LED") else fp.GetReference()].append((round(math.dist(a, b), 2), w))
        stubs = {ref: sorted(set(v)) for ref, v in by_ref.items()}
        print(f"  {net} pad stubs (length, width mm): {stubs}; vias {sorted({(d, h) for _, d, h in vias[net]})}")

    # --- planes: islands, necks, thermal spokes
    for zone in board.Zones():
        if zone.GetIsRuleArea():
            continue
        net, layer = zone.GetNetname(), zone.GetLayer()
        fill = pcbnew.SHAPE_POLY_SET(zone.GetFilledPolysList(layer))
        fill.Simplify()
        targets = [v for v in vias[net]]
        def area(poly, i):
            return pcbnew.SHAPE_POLY_SET(poly.Polygon(i)).Area() / 1e12

        pieces = sorted((round(area(fill, i), 1) for i in range(fill.OutlineCount())), reverse=True)
        line = f"plane {net} on {board.GetLayerName(layer)}: pieces {pieces} mm2;"
        main_piece = max(range(fill.OutlineCount()), key=lambda i: area(fill, i))
        for i in range(fill.OutlineCount()):
            if i != main_piece:
                bb = fill.Outline(i).BBox()
                print(f"  island of {area(fill, i):.2f} mm2 at board ({MM(bb.GetCenter().x):.2f}, {MM(bb.GetCenter().y):.2f}), "
                      f"U1-relative ({MM(bb.GetCenter().x - fps['U1'].GetPosition().x):.2f}, {MM(bb.GetCenter().y - fps['U1'].GetPosition().y):.2f})")
        for w in (1.0, 2.0, 3.0):
            # Shrink the plane by w/2: what survives in one piece is joined by copper at least
            # w wide. A via counts if it is within 1 mm of that piece's edge.
            core = pcbnew.SHAPE_POLY_SET(fill)
            core.Deflate(pcbnew.FromMM(w / 2), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcbnew.FromMM(0.01))
            best = max(range(core.OutlineCount()), key=lambda i: area(core, i))
            n = sum(1 for (x, y), _, _ in targets
                    if core.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)), best, pcbnew.FromMM(w / 2 + 1.0)))
            line += f" at >= {w} mm wide: one piece holds {100 * area(core, best) / (core.Area() / 1e12):.1f} % and {n}/{len(targets)} vias;"
        print(line)
        if net == "GND":
            for ref, fp in sorted(fps.items()):
                for p in fp.Pads():
                    if p.GetNetname() != net or p.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                        continue
                    ring = pcbnew.SHAPE_POLY_SET(p.GetEffectivePolygon(layer, pcbnew.ERROR_INSIDE))
                    ring.Inflate(pcbnew.FromMM(0.15), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcbnew.FromMM(0.005))
                    o = ring.Outline(0)
                    pts = [o.CPoint(i) for i in range(o.PointCount())]
                    inside = []
                    for a, b in zip(pts, pts[1:] + pts[:1]):
                        steps = max(1, int(math.hypot(a.x - b.x, a.y - b.y) / pcbnew.FromMM(0.02)))
                        inside += [fill.Contains(pcbnew.VECTOR2I(int(a.x + (b.x - a.x) * s / steps), int(a.y + (b.y - a.y) * s / steps)), main_piece) for s in range(steps)]
                    spokes = sum(1 for a, b in zip(inside, inside[1:] + inside[:1]) if b and not a)
                    print(f"  {ref}.{p.GetNumber()} thermal spokes to the main GND plane: {spokes}")

    # --- LED data beside other nets on the same layer (centre lines under 0.8 mm apart)
    led_nets = [n for n in tracks if n.startswith("LED_D")]
    beside = defaultdict(float)      # aggressor kind -> mm
    worst = defaultdict(float)       # (LED net, other net) -> mm
    nearest = {}
    for net in led_nets:
        for layer, a, b, w in tracks[net]:
            length = math.dist(a, b)
            steps = max(1, int(length / 0.25))
            for s in range(steps):
                p = (a[0] + (b[0] - a[0]) * (s + 0.5) / steps, a[1] + (b[1] - a[1]) * (s + 0.5) / steps)
                hit = None
                for other, segs in tracks.items():
                    if other == net:
                        continue
                    for l2, a2, b2, w2 in segs:
                        if l2 == layer and abs(a2[0] - p[0]) < 30 and abs(a2[1] - p[1]) < 30:
                            d = dist_seg(p, a2, b2)
                            if d < 0.8 and (hit is None or d < hit[0]):
                                hit = (d, other, d - (w + w2) / 2)
                if hit:
                    beside[kind(hit[1])] += length / steps
                    worst[(net, hit[1])] += length / steps
                    nearest[kind(hit[1])] = min(nearest.get(kind(hit[1]), 9.9), hit[2])
    print("LED data beside other nets, same layer, centre lines under 0.8 mm apart:")
    for k, v in sorted(beside.items(), key=lambda kv: -kv[1]):
        print(f"  {k:13s} {v:6.1f} mm in all, smallest gap {nearest[k]:.3f} mm")
    (a, b), v = max(worst.items(), key=lambda kv: kv[1])
    print(f"  longest single run: {a} beside {b}, {v:.1f} mm")

    # --- plane copper under the module's antenna end (the end away from USB: board +y)
    u = fps["U1"]
    c = u.GetPosition()
    box = pcbnew.SHAPE_POLY_SET()
    box.NewOutline()
    for dx, dy in ((-MODULE_HALF_W, MODULE_END - ANTENNA_LEN), (MODULE_HALF_W, MODULE_END - ANTENNA_LEN), (MODULE_HALF_W, MODULE_END), (-MODULE_HALF_W, MODULE_END)):
        box.Append(c.x + pcbnew.FromMM(dx), c.y + pcbnew.FromMM(dy))
    usb_up = min(p.GetPosition().y for p in u.Pads() if p.GetNumber() in ("1", "13")) < c.y
    for zone in board.Zones():
        if not zone.GetIsRuleArea():
            under = pcbnew.SHAPE_POLY_SET(zone.GetFilledPolysList(zone.GetLayer()))
            under.BooleanIntersection(box)
            print(f"antenna end ({2 * MODULE_HALF_W} x {ANTENNA_LEN} mm, USB end {'away' if usb_up else 'WRONG SIDE'}): "
                  f"{under.Area() / 1e12:.1f} mm2 of the {zone.GetNetname()} plane under it")
    n_tr = sum(1 for segs in tracks.values() for _, a, b, _ in segs
               if any(abs(q[0] - MM(c.x)) < MODULE_HALF_W and MODULE_END - ANTENNA_LEN < q[1] - MM(c.y) < MODULE_END for q in (a, b)))
    print(f"  track ends inside that area: {n_tr}; U1 is on {board.GetLayerName(u.GetLayer())}")
    return bad


def main() -> int:
    bad = [f"{side}: {b}" for side in ("left", "right") for b in review(side)]
    for b in bad:
        print("FAILED", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
