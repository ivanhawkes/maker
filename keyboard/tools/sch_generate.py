#!/usr/bin/env python3
"""Generate each half's KiCad schematic from its generated board.

    python tools/sch_generate.py                    # write pcb/{left,right}/{left,right}.kicad_sch
    python tools/sch_generate.py --extract-symbols DIR   # rebuild parts/symbols/ from KiCad's libraries

Needs KiCad's pcbnew (docs/pcb.md, "Running the tools") and PyYAML. Run after
tools/pcb_generate.py, which calls it.

The schematic is drawn from the board: every footprint becomes a symbol and every pad's net a
label on the matching pin. So it cannot disagree with the board, and it is not an independent
design check; tools/pcb_review.py holds those. What it adds: KiCad's electrical rules check
(pin types, undriven supplies, unconnected pins), a drawing a person can read, with each
diode's and transistor's pins shown, and a project KiCad can open and compare ("schematic
parity" in DRC).

Layout: one cell per key (diode, switch, LED) on the matrix's rows and columns, then the
controller and the power parts. Nets join by label; there are no wires.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SYMBOLS = ROOT / "parts" / "symbols" / "keyboard.kicad_sym"
LIB = "keyboard"  # the symbol library's nickname in each project's sym-lib-table
# Our symbol name -> (KiCad library file, symbol there). Copied flat into parts/symbols/.
STOCK = {
    "R": ("Device", "R"), "C": ("Device", "C"), "D": ("Device", "D"),
    "SW_Push": ("Switch", "SW_Push"), "SW_SPDT": ("Switch", "SW_SPDT"),
    "SK6812MINI-E": ("LED", "SK6812MINI-E"),
    "Q_PMOS_GSD": ("Transistor_FET", "Q_PMOS_GSD"), "Q_NMOS_GSD": ("Transistor_FET", "Q_NMOS_GSD"),
    "Conn_01x02": ("Connector_Generic", "Conn_01x02"), "PWR_FLAG": ("power", "PWR_FLAG"),
}
CONTROLLER = "nice_nano_v2"
# KiCad's SK6812MINI-E symbol and footprint number the part half a turn round from the Opsco
# datasheet (KiCad pin 1 is VSS, at the cut corner; the datasheet's pin 1 is VDD and the cut corner
# is pin 3). The board assigns its pads by the datasheet's numbers and marks the cut corner at
# pad 3 (tools/pcb_generate.py, load_led), so the symbol here is renumbered to the datasheet too.
LED_PINS = {"VDD": "1", "DOUT": "2", "VSS": "3", "DIN": "4"}
GRID = 1.27


# ----------------------------------------------------------------- s-expressions

class Q(str):
    """A quoted string, as opposed to a bare token."""


def parse(text: str):
    pos, n = 0, len(text)

    def node():
        nonlocal pos
        out = []
        while pos < n:
            c = text[pos]
            if c.isspace():
                pos += 1
            elif c == "(":
                pos += 1
                out.append(node())
            elif c == ")":
                pos += 1
                return out
            elif c == '"':
                end, buf = pos + 1, []
                while text[end] != '"':
                    if text[end] == "\\":
                        buf.append(text[end:end + 2])
                        end += 2
                    else:
                        buf.append(text[end])
                        end += 1
                out.append(Q("".join(buf)))  # escapes kept as written
                pos = end + 1
            else:
                end = pos
                while end < n and not text[end].isspace() and text[end] not in "()":
                    end += 1
                out.append(text[pos:end])
                pos = end
        return out

    return node()[0]


def dump(x, depth: int = 0) -> str:
    if not isinstance(x, list):
        if isinstance(x, float):
            return f"{x:.4f}".rstrip("0").rstrip(".")
        return f'"{x}"' if isinstance(x, Q) else str(x)
    flat = "(" + " ".join(dump(i) for i in x) + ")"
    if len(flat) <= 100 and not any(isinstance(i, list) and any(isinstance(j, list) for j in i) for i in x):
        return flat
    pad = "\t" * (depth + 1)
    head = [dump(i) for i in x if not isinstance(i, list)]
    body = [pad + dump(i, depth + 1) for i in x if isinstance(i, list)]
    return "(" + " ".join(head) + "\n" + "\n".join(body) + "\n" + "\t" * depth + ")"


def find(node: list, key: str) -> list | None:
    return next((i for i in node if isinstance(i, list) and i and i[0] == key), None)


# ------------------------------------------------------------------ symbol library

def extract_symbols(kicad_dir: Path) -> None:
    """Copy the stock symbols we use into parts/symbols/, with derived symbols made standalone."""
    pins = yaml.safe_load((ROOT / "pcb" / "pins.yaml").read_text())
    out = ["kicad_symbol_lib", ["version", "20251024"], ["generator", Q("sch_generate")], ["generator_version", Q("10.0")]]
    for name, (lib, stock) in STOCK.items():
        symbols = {s[1]: s for s in parse((kicad_dir / f"{lib}.kicad_sym").read_text()) if isinstance(s, list) and s[0] == "symbol"}
        sym = symbols[stock]
        parent = find(sym, "extends")
        units_name = stock
        if parent:  # the parent's drawing and pins, with this symbol's own properties on top
            base = symbols[parent[1]]
            assert not find(base, "extends"), f"{stock}: more than one level of extends"
            own = {p[1]: p for p in sym if isinstance(p, list) and p[0] == "property"}
            body = [own.pop(i[1], i) if isinstance(i, list) and i[0] == "property" else i for i in base[2:]]
            units = [b for b in body if isinstance(b, list) and b[0] == "symbol"]
            sym = ["symbol", Q(stock), *[b for b in body if b not in units], *own.values(), *units]
            units_name = parent[1]
        flat = ["symbol", Q(name)]
        for item in sym[2:]:
            if isinstance(item, list) and item[0] == "symbol":
                item = ["symbol", Q(name + item[1][len(units_name):]), *item[2:]]
                if name == "SK6812MINI-E":
                    for pin in (p for p in item if isinstance(p, list) and p[0] == "pin"):
                        find(pin, "number")[1] = Q(LED_PINS[find(pin, "name")[1]])
            flat.append(item)
        out.append(flat)
    out.append(controller_symbol(pins))
    SYMBOLS.parent.mkdir(parents=True, exist_ok=True)
    SYMBOLS.write_text(dump(out) + "\n")
    (SYMBOLS.parent / "SOURCE.txt").write_text(
        "keyboard.kicad_sym: written by tools/sch_generate.py --extract-symbols.\n"
        f"Stock symbols copied from KiCad's symbol libraries ({kicad_dir}):\n"
        + "".join(f"  {name}: {lib}.kicad_sym, {stock}\n" for name, (lib, stock) in STOCK.items())
        + f"  {CONTROLLER}: generated from pcb/pins.yaml (not a KiCad symbol)\n"
        "Licence: KiCad libraries, CC-BY-SA 4.0 with the KiCad exception (parts/footprints/kicad/LICENSE.md).\n")
    print(f"wrote {SYMBOLS.relative_to(ROOT)}: {len(out) - 4} symbols")


def text_effects(size: float = 1.27, hide: bool = False, justify: str | None = None) -> list:
    out = ["effects", ["font", ["size", size, size]]]
    if justify:
        out.append(["justify", justify])
    if hide:
        out.append(["hide", "yes"])
    return out


def controller_symbol(pins: dict) -> list:
    """The nice!nano as a box: pads 1-12 down the left side, 13-24 down the right, as on the module."""
    kinds = {"GND": "power_in", "RAW": "power_in", "VCC": "power_out", "RST": "input"}
    unit = ["symbol", Q(f"{CONTROLLER}_1_1"),
            ["rectangle", ["start", -12.7, 16.51], ["end", 12.7, -16.51], ["stroke", ["width", 0.254], ["type", "default"]],
             ["fill", ["type", "background"]]]]
    for pad, (name, _, gpio, _) in pins["controller"]["pads"].items():
        left = pad <= 12
        y = 13.97 - 2.54 * ((pad - 1) % 12)
        label = f"{name}/{gpio}" if gpio else {"RAW": "RAW/BAT+", "VCC": "VCC/3V3"}.get(name, name)
        unit.append(["pin", kinds.get(name, "bidirectional"), "line", ["at", -15.24 if left else 15.24, y, 0 if left else 180],
                     ["length", 2.54], ["name", Q(label), text_effects(1.0)], ["number", Q(str(pad)), text_effects(1.0)]])
    props = [("Reference", "U", (0, 19.05), False), ("Value", CONTROLLER, (0, -19.05), False), ("Footprint", "", (0, 0), True),
             ("Datasheet", "https://nicekeyboards.com/docs/nice-nano/pinout-schematic", (0, 0), True),
             ("Description", "nice!nano v2 (nRF52840), Pro Micro footprint; pins from pcb/pins.yaml", (0, 0), True)]
    return ["symbol", Q(CONTROLLER), ["pin_names", ["offset", 1.016]], ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
            *[["property", Q(k), Q(v), ["at", x, y, 0], text_effects(hide=hide)] for k, v, (x, y), hide in props], unit]


def load_symbols() -> dict[str, dict]:
    """name -> {"node": the library symbol, "pins": {number: (x, y, angle)}}, pin ends in symbol axes (y up)."""
    out = {}
    for sym in parse(SYMBOLS.read_text()):
        if isinstance(sym, list) and sym[0] == "symbol":
            pins = {}
            for unit in sym:
                if isinstance(unit, list) and unit[0] == "symbol":
                    for pin in unit:
                        if isinstance(pin, list) and pin[0] == "pin":
                            at = find(pin, "at")
                            pins[str(find(pin, "number")[1])] = (float(at[1]), float(at[2]), int(float(at[3])))
            out[sym[1]] = {"node": sym, "pins": pins}
    return out


# ------------------------------------------------------------------------ drawing

class Sheet:
    def __init__(self, side: str, symbols: dict):
        self.side, self.symbols = side, symbols
        self.uuid = self.uid("sheet")
        self.items: list = []
        self.used: set[str] = set()
        self.flags = 0

    def uid(self, *parts) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "/".join(["keyboard", self.side, *map(str, parts)])))

    def place(self, name: str, ref: str, value: str, x: float, y: float, nets: dict[str, str], footprint: str = "",
              bom: bool = True, pos: bool = True, ref_at=(0.0, -5.08), value_at=(0.0, 5.08), no_connect=(), angles=None,
              justify: str | None = None):
        """Put a symbol at (x, y) with a label on each pin: nets maps pin number to net name.

        angles overrides a pin's label direction (degrees on the sheet), or drops its label with
        None, for a pin that touches another symbol's pin and shares that one's label.
        """
        assert abs(x / GRID - round(x / GRID)) < 1e-6 and abs(y / GRID - round(y / GRID)) < 1e-6, f"{ref} is off the grid"
        sym = self.symbols[name]
        self.used.add(name)

        def prop(key, text, at, hide=False, size=1.27):
            return ["property", Q(key), Q(text), ["at", round(x + at[0], 4), round(y + at[1], 4), 0],
                    text_effects(size, hide, None if hide else justify)]

        self.items.append(
            ["symbol", ["lib_id", Q(f"{LIB}:{name}")], ["at", x, y, 0], ["unit", 1], ["exclude_from_sim", "no"],
             ["in_bom", "yes" if bom else "no"], ["on_board", "yes"], ["in_pos_files", "yes" if pos else "no"], ["dnp", "no"],
             ["uuid", Q(self.uid("symbol", ref))],
             prop("Reference", ref, ref_at), prop("Value", value, value_at, size=1.0), prop("Footprint", footprint, (0, 0), hide=True),
             prop("Datasheet", "", (0, 0), hide=True), prop("Description", "", (0, 0), hide=True),
             *[["pin", Q(n), ["uuid", Q(self.uid("pin", ref, n))]] for n in sorted(sym["pins"], key=lambda s: (len(s), s))],
             ["instances", ["project", Q(self.side), ["path", Q(f"/{self.uuid}"), ["reference", Q(ref)], ["unit", 1]]]]])
        for number, (px, py, angle) in sym["pins"].items():
            end = (round(x + px, 4), round(y - py, 4))  # the sheet's y axis points down
            if number in no_connect:
                self.items.append(["no_connect", ["at", *end], ["uuid", Q(self.uid("nc", ref, number))]])
            elif nets.get(number):
                # Away from the body. A pin's angle points from its end into the symbol.
                turn = (angles or {}).get(number, (angle + 180) % 360)
                if turn is not None:
                    self.label(nets[number], end, turn, (ref, number))

    def label(self, net: str, at: tuple[float, float], angle: int, key) -> None:
        self.items.append(["global_label", Q(net), ["shape", "passive"], ["at", at[0], at[1], angle],
                           text_effects(1.0, justify="right" if angle in (180, 270) else "left"),
                           ["uuid", Q(self.uid("label", *key))]])

    def flag(self, net: str, x: float, y: float) -> None:
        """A PWR_FLAG: tells the rules check this net is powered from outside the drawing."""
        self.flags += 1
        self.place("PWR_FLAG", f"#FLG{self.flags:02d}", "PWR_FLAG", x, y, {"1": net}, ref_at=(0, -3.81), value_at=(0, -6.35))

    def text(self, body: str, x: float, y: float, size: float = 2.0) -> None:
        self.items.append(["text", Q(body), ["exclude_from_sim", "no"], ["at", x, y, 0], text_effects(size, justify="left"),
                           ["uuid", Q(self.uid("text", body))]])

    def render(self, title: str) -> str:
        libs = [["symbol", Q(f"{LIB}:{name}"), *self.symbols[name]["node"][2:]] for name in sorted(self.used)]
        doc = ["kicad_sch", ["version", "20260306"], ["generator", Q("sch_generate")], ["generator_version", Q("10.0")],
               ["uuid", Q(self.uuid)], ["paper", Q("A2")],
               ["title_block", ["title", Q(title)], ["comment", 1, Q("Generated from the board by tools/sch_generate.py. Do not edit.")]],
               ["lib_symbols", *libs], *self.items, ["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
        return dump(doc) + "\n"


def components(side: str) -> dict[str, dict]:
    import pcbnew
    board = pcbnew.LoadBoard(str(ROOT / "pcb" / side / f"{side}.kicad_pcb"))
    out = {}
    for fp in board.GetFootprints():
        if fp.GetAttributes() & pcbnew.FP_BOARD_ONLY:   # mounting holes: not in the schematic
            continue
        nets: dict[str, str] = {}
        for p in fp.Pads():
            if p.GetNumber():
                assert nets.setdefault(p.GetNumber(), p.GetNetname()) == p.GetNetname(), f"{fp.GetReference()}.{p.GetNumber()}"
        out[fp.GetReference()] = {
            "value": fp.GetValue(), "footprint": fp.GetFPIDAsString(), "nets": nets,
            "bom": not fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM, "pos": not fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES}
    return out


def draw(side: str) -> str:
    pins = yaml.safe_load((ROOT / "pcb" / "pins.yaml").read_text())
    comps = components(side)
    sheet = Sheet(side, load_symbols())
    done: set[str] = set()

    def put(name, ref, x, y, **kw):
        c = comps[ref]
        # A pad the board leaves without a net is an unused pin: mark it, so the rules check knows.
        nc = [n for n in sheet.symbols[name]["pins"] if not c["nets"].get(n) or c["nets"][n].startswith("unconnected-")]
        sheet.place(name, ref, c["value"], x, y, c["nets"], c["footprint"], c["bom"], c["pos"], no_connect=nc, **kw)
        done.add(ref)

    # The key matrix: a cell per key at its row and column. Diode and switch touch, so
    # the row label, diode, switch and column label read along one line; the key's LED is below.
    rows, cols = list(pins["rows"]), list(pins["columns"])
    keys = {c["value"]: ref for ref, c in comps.items() if ref.startswith("SW") and ref[2:].isdigit()}
    sheet.text(f"Key matrix, {len(rows)} rows by {len(cols)} columns: column -> switch -> diode -> row (ZMK col2row). "
               "Each key's LED is drawn under it; the LED_D nets chain them.", 25.4, 20.32, 2.5)
    for ref in sorted(keys.values(), key=lambda r: int(r[2:])):  # a fixed order: the board's own varies between saves
        n = ref[2:]
        col = comps[ref]["nets"]["2"].removeprefix("COL_")
        row = comps[f"D{n}"]["nets"]["1"].removeprefix("ROW_")
        x0, y0 = 25.4 + 50.8 * cols.index(col), 30.48 + 50.8 * rows.index(row)
        # The diode's anode pin ends on the switch's pin 1: one label, pointing down, names that net.
        put("SW_Push", ref, x0 + 26.67, y0 + 7.62, ref_at=(0, -7.62), value_at=(0, -5.08), angles={"1": 270})
        put("D", f"D{n}", x0 + 17.78, y0 + 7.62, ref_at=(-1.27, -3.81), value_at=(-1.27, 3.81), angles={"2": None})
        put("SK6812MINI-E", f"LED{n}", x0 + 22.86, y0 + 33.02, ref_at=(10.16, -8.89), value_at=(12.7, 8.89))

    # Controller, battery path, LED supply switch.
    x0 = 406.4
    sheet.text("Controller (socketed nice!nano v2). Unused pins are marked.", x0, 20.32, 2.5)
    put(CONTROLLER, "U1", x0 + 50.8, 55.88, ref_at=(0, -19.05), value_at=(0, 19.05))
    put("SW_Push", "SW_RST", x0 + 127.0, 43.18, ref_at=(0, -7.62), value_at=(0, -5.08))
    sheet.text("Battery: connector, power switch, then RAW (the module's battery pin).", x0, 99.06, 2.5)
    put("Conn_01x02", "J1", x0 + 25.4, 114.3, ref_at=(1.27, -5.08), value_at=(1.27, 7.62))
    put("SW_SPDT", "SW_PWR", x0 + 76.2, 114.3, ref_at=(0, -7.62), value_at=(0, 7.62))
    sheet.text("LED supply: Q1 switches RAW to VLED; Q2 drives its gate from LED_EN.", x0, 142.24, 2.5)
    sheet.text("R3 and C2 slow the turn-on. Q1's source (pin 2) is on RAW.", x0, 147.32, 2.5)
    side_text = dict(ref_at=(5.08, -1.27), value_at=(5.08, 1.27), justify="left")
    put("R", "R1", x0 + 12.7, 170.18, **side_text)
    put("C", "C2", x0 + 63.5, 170.18, **side_text)
    put("Q_PMOS_GSD", "Q1", x0 + 119.38, 170.18, **side_text)
    put("C", "C1", x0 + 12.7, 205.74, **side_text)
    put("R", "R3", x0 + 63.5, 205.74, **side_text)
    put("Q_NMOS_GSD", "Q2", x0 + 119.38, 205.74, **side_text)
    put("R", "R2", x0 + 12.7, 241.3, **side_text)
    sheet.text("LED data: R4 in series, controller to the first LED.", x0 + 50.8, 231.14, 2.5)
    put("R", "R4", x0 + 63.5, 248.92, **side_text)
    sheet.text("Supplies that come from outside this drawing (the battery; VLED through Q1).", x0, 276.86, 2.5)
    for i, net in enumerate(("GND", "RAW", "VLED")):
        sheet.flag(net, x0 + 25.4 + 38.1 * i, 297.18)

    missing = set(comps) - done
    assert not missing, f"{side}: footprints with no symbol: {sorted(missing)}"
    return sheet.render(f"Split keyboard, {side} half")


def name_unconnected(side: str) -> int:
    """Give the board's unused pads the net names KiCad derives for unconnected pins.

    KiCad names the net of a pin marked unconnected "unconnected-(...)" and expects the pad to carry
    it; without it the parity check warns for every unused pad. The names are read from KiCad's own
    netlist of the schematic, not rebuilt here. Returns the number of pads changed.
    """
    import pcbnew
    sch = ROOT / "pcb" / side / f"{side}.kicad_sch"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "netlist.net"
        subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", str(out), str(sch)],
                       check=True, capture_output=True)
        nets = find(parse(out.read_text()), "nets")
    board = pcbnew.LoadBoard(str(sch.with_suffix(".kicad_pcb")))
    changed = 0
    for net in nets[1:]:
        name = find(net, "name")[1]
        if not name.startswith("unconnected-"):
            continue
        for node in (n for n in net if isinstance(n, list) and n[0] == "node"):
            for pad in board.FindFootprintByReference(find(node, "ref")[1]).Pads():
                if pad.GetNumber() == find(node, "pin")[1] and pad.GetNetname() != name:
                    item = board.FindNet(name)
                    if item is None:
                        item = pcbnew.NETINFO_ITEM(board, name)
                        board.Add(item)
                    pad.SetNet(item)
                    changed += 1
    if changed:
        pcbnew.SaveBoard(str(sch.with_suffix(".kicad_pcb")), board)
    return changed


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--extract-symbols":
        extract_symbols(Path(sys.argv[2]))
        return 0
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    for side in ("left", "right"):
        out = ROOT / "pcb" / side / f"{side}.kicad_sch"
        out.write_text(draw(side))
        (out.parent / "sym-lib-table").write_text(
            '(sym_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/../../parts/symbols/keyboard.kicad_sym")'
            '(options "")(descr "The symbols this keyboard uses"))\n)\n' % LIB)
        print(f"wrote {out.relative_to(ROOT)}; named {name_unconnected(side)} unused pads on the board")
    return 0


if __name__ == "__main__":
    sys.exit(main())
