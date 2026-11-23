"""Deterministic grid router for the few irregular connections of the keyboard PCBs.

The regular routing is scripted in pcb_generate.py. This routes what is left (the power nets
and the thumb column's run to the controller) with A* on a 0.1 mm grid over a window of the
board, in a fixed net order with fixed tie-breaking, so the result is the same on every run.

Obstacles are taken from the board as it stands: pads (as their bounding boxes), tracks, vias,
holes, rule areas (as bounding boxes) and the outline, each grown by the net's clearance plus
half its track width plus a grid margin, so anything it routes should pass DRC; DRC is still
the check. It is not a general autorouter: no rip-up, no push and shove.
"""

from __future__ import annotations

import heapq
import math

import pcbnew

RES = 0.1          # grid pitch, mm
MARGIN = 0.08      # grid slack added to every clearance, mm (a little over half a cell diagonal)
VIA_COST = 60.0    # in cells: prefer staying on a layer
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)


class Maze:
    def __init__(self, board: pcbnew.BOARD, window: tuple[float, float, float, float],
                 outline: list[tuple[float, float]], clearance: float, edge: float):
        """window is (x0, y0, x1, y1) and outline a polygon (notches allowed), both in board mm."""
        self.b = board
        self.x0, self.y0 = window[0], window[1]
        self.w = int(round((window[2] - window[0]) / RES)) + 1
        self.h = int(round((window[3] - window[1]) / RES)) + 1
        self.outline, self.clearance, self.edge = outline, clearance, edge
        self.shapes: list[tuple] = []   # (net name, layer index, kind, geometry)
        self.added: list[tuple] = []    # shapes routed here, to add to later nets' obstacles
        self._collect()

    # ---- geometry ---------------------------------------------------------------------
    def _collect(self) -> None:
        mmv = pcbnew.ToMM
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                net, pos = p.GetNetname(), p.GetPosition()
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    for li in (0, 1):
                        self.shapes.append((None, li, "circle", (mmv(pos.x), mmv(pos.y), mmv(p.GetDrillSize().x) / 2)))
                    continue
                bb = p.GetBoundingBox()
                rect = (mmv(bb.GetLeft()), mmv(bb.GetTop()), mmv(bb.GetRight()), mmv(bb.GetBottom()))
                for li, layer in enumerate(LAYERS):
                    if p.IsOnLayer(layer):
                        self.shapes.append((net, li, "rect", rect))
        for t in self.b.GetTracks():
            net = t.GetNetname()
            if t.GetClass() == "PCB_VIA":
                pos = t.GetPosition()
                for li in (0, 1):
                    self.shapes.append((net, li, "circle", (mmv(pos.x), mmv(pos.y), mmv(t.GetWidth(pcbnew.F_Cu)) / 2)))
            else:
                s, e = t.GetStart(), t.GetEnd()
                li = LAYERS.index(t.GetLayer()) if t.GetLayer() in LAYERS else None
                if li is not None:
                    self.shapes.append((net, li, "capsule", (mmv(s.x), mmv(s.y), mmv(e.x), mmv(e.y), mmv(t.GetWidth()) / 2)))
        for z in self.b.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():  # a fills-only area does not stop tracks
                bb = z.GetBoundingBox()
                rect = (mmv(bb.GetLeft()), mmv(bb.GetTop()), mmv(bb.GetRight()), mmv(bb.GetBottom()))
                for li in (0, 1):
                    self.shapes.append((None, li, "keepout", rect))

    def _stamp(self, grid: bytearray, kind: str, g: tuple, grow: float) -> None:
        """Mark the cells within grow of the shape."""
        if kind == "circle":
            x0, y0, x1, y1, r = g[0], g[1], g[0], g[1], g[2] + grow
        elif kind == "capsule":
            x0, y0, x1, y1, r = min(g[0], g[2]), min(g[1], g[3]), max(g[0], g[2]), max(g[1], g[3]), g[4] + grow
        else:
            x0, y0, x1, y1, r = g[0], g[1], g[2], g[3], grow
        i0 = max(0, int(math.floor((x0 - r - self.x0) / RES)))
        i1 = min(self.w - 1, int(math.ceil((x1 + r - self.x0) / RES)))
        j0 = max(0, int(math.floor((y0 - r - self.y0) / RES)))
        j1 = min(self.h - 1, int(math.ceil((y1 + r - self.y0) / RES)))
        r2 = r * r
        ax = ay = dx = dy = ll = 0.0
        if kind == "capsule":
            ax, ay = g[0], g[1]
            dx, dy = g[2] - ax, g[3] - ay
            ll = dx * dx + dy * dy
        for j in range(j0, j1 + 1):
            py = self.y0 + j * RES
            row = j * self.w
            for i in range(i0, i1 + 1):
                px = self.x0 + i * RES
                if kind == "circle":
                    d2 = (px - g[0]) ** 2 + (py - g[1]) ** 2
                elif kind == "capsule":
                    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
                    d2 = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
                else:
                    ex = max(g[0] - px, 0.0, px - g[2])
                    ey = max(g[1] - py, 0.0, py - g[3])
                    d2 = ex * ex + ey * ey
                if d2 <= r2:
                    grid[row + i] = 1

    def _blocked(self, net: str, half_width: float) -> list[bytearray]:
        """Per layer, the cells a track centre of this net may not use."""
        grow = half_width + self.clearance + MARGIN
        grids = [bytearray(self.w * self.h), bytearray(self.w * self.h)]
        for snet, li, kind, g in self.shapes + self.added:
            if snet == net:
                continue
            # A rule area forbids copper inside it, not near it: grow by the track only.
            self._stamp(grids[li], kind, g, half_width + MARGIN if kind == "keepout" else grow)
        # Outside the outline, or within the edge clearance of it.
        pts = self.outline
        edge_grow = half_width + self.edge + MARGIN
        for li in (0, 1):
            for a, b in zip(pts, pts[1:] + pts[:1]):
                self._stamp(grids[li], "capsule", (a[0], a[1], b[0], b[1], 0.0), edge_grow)
        for j in range(self.h):
            py = self.y0 + j * RES
            xs = []
            for a, b in zip(pts, pts[1:] + pts[:1]):
                if (a[1] <= py < b[1]) or (b[1] <= py < a[1]):
                    xs.append(a[0] + (py - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
            # Even-odd: the row is inside the board between each pair of crossings, and blocked
            # elsewhere (the outline has notches, so a row can cross it more than twice).
            xs.sort()
            row = j * self.w
            start = 0   # first cell of the next blocked stretch
            for lo, hi in list(zip(xs[::2], xs[1::2])) + [(1e9, 1e9)]:
                end = max(start, min(self.w, int(math.ceil((lo - self.x0) / RES))))
                for li in (0, 1):
                    grids[li][row + start:row + end] = b"\x01" * (end - start)
                start = max(end, min(self.w, int(math.floor((hi - self.x0) / RES)) + 1))
        return grids

    def _cell(self, x: float, y: float) -> tuple[int, int]:
        return int(round((x - self.x0) / RES)), int(round((y - self.y0) / RES))

    # ---- routing ----------------------------------------------------------------------
    def route(self, net: pcbnew.NETINFO_ITEM, terminals: list[tuple[float, float, tuple[int, ...]]],
              width: float, via: tuple[float, float]) -> None:
        """Join the terminals (x, y, layer indices) of one net, adding locked tracks and vias."""
        name = net.GetNetname()
        hw = width / 2
        blocked = self._blocked(name, hw)
        w, h = self.w, self.h
        ring = max(1, int(math.ceil((via[0] / 2 - hw) / RES)))  # via is wider than the track by this many cells

        def via_ok(i: int, j: int) -> bool:
            for li in (0, 1):
                g = blocked[li]
                for dj in (-ring, 0, ring):
                    for di in (-ring, 0, ring):
                        ii, jj = i + di, j + dj
                        if not (0 <= ii < w and 0 <= jj < h) or g[jj * w + ii]:
                            return False
            return True

        def cells_of(t) -> list[tuple[int, int, int]]:
            i, j = self._cell(t[0], t[1])
            return [(li, i, j) for li in t[2]]

        tree: dict[tuple[int, int, int], None] = dict.fromkeys(cells_of(terminals[0]))
        todo = list(terminals[1:])
        moves = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                 (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142))
        while todo:
            targets = {c: t for t in todo for c in cells_of(t)}
            tpts = [self._cell(t[0], t[1]) for t in todo]

            def hfun(i: int, j: int) -> float:
                best = 1e18
                for ti, tj in tpts:
                    dx, dy = abs(i - ti), abs(j - tj)
                    best = min(best, max(dx, dy) + 0.4142 * min(dx, dy))
                return best

            dist = {c: 0.0 for c in tree}
            prev: dict = {}
            heap = [(hfun(c[1], c[2]), 0.0, c) for c in sorted(tree)]
            heapq.heapify(heap)
            found = None
            while heap:
                _, gc, c = heapq.heappop(heap)
                if gc > dist.get(c, 1e18):
                    continue
                if c in targets:
                    found = c
                    break
                li, i, j = c
                g = blocked[li]
                for di, dj, cost in moves:
                    ii, jj = i + di, j + dj
                    if not (0 <= ii < w and 0 <= jj < h) or g[jj * w + ii]:
                        continue
                    if di and dj and (g[j * w + ii] or g[jj * w + i]):
                        continue  # no cutting corners
                    n = (li, ii, jj)
                    ng = gc + cost
                    if ng < dist.get(n, 1e18):
                        dist[n] = ng
                        prev[n] = c
                        heapq.heappush(heap, (ng + hfun(ii, jj), ng, n))
                n = (1 - li, i, j)
                ng = gc + VIA_COST
                if ng < dist.get(n, 1e18) and via_ok(i, j):
                    dist[n] = ng
                    prev[n] = c
                    heapq.heappush(heap, (ng + hfun(i, j), ng, n))
            if found is None:
                raise SystemExit(f"maze: no route for {name} to {[(round(t[0], 2), round(t[1], 2)) for t in todo]}")
            path = [found]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            path.reverse()
            self._emit(net, path, width, via, terminals, targets[found])
            tree.update(dict.fromkeys(path))
            todo.remove(targets[found])
            tree.update(dict.fromkeys(cells_of(targets[found])))

    def _emit(self, net, path, width, via, terminals, hit) -> None:
        """Turn a cell path into tracks and vias, with stubs to the exact terminal points."""
        name = net.GetNetname()

        def xy(c):
            return self.x0 + c[1] * RES, self.y0 + c[2] * RES

        def add_track(a, b, li):
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-6:
                return
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(b[0]), pcbnew.FromMM(b[1])))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(LAYERS[li])
            t.SetNet(net)
            t.SetLocked(True)
            self.b.Add(t)
            self.added.append((name, li, "capsule", (a[0], a[1], b[0], b[1], width / 2)))

        # Stubs from the grid to the exact terminal points at both ends (inside the pads).
        for end, cell in ((0, path[0]), (-1, path[-1])):
            cands = [t for t in terminals if self._cell(t[0], t[1]) == (cell[1], cell[2])] if end == 0 else [hit]
            if cands:
                add_track(xy(cell), (cands[0][0], cands[0][1]), cell[0])
        run = [path[0]]
        for c in path[1:]:
            last = run[-1]
            if c[0] != last[0]:  # layer change: a via here
                if len(run) > 1:
                    add_track(xy(run[0]), xy(last), last[0])
                v = pcbnew.PCB_VIA(self.b)
                x, y = xy(last)
                v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                v.SetWidth(pcbnew.FromMM(via[0]))
                v.SetDrill(pcbnew.FromMM(via[1]))
                v.SetNet(net)
                v.SetLocked(True)
                self.b.Add(v)
                for li in (0, 1):
                    self.added.append((name, li, "circle", (x, y, via[0] / 2)))
                run = [c]
                continue
            if len(run) > 1:
                d0 = (run[-1][1] - run[-2][1], run[-1][2] - run[-2][2])
                d1 = (c[1] - last[1], c[2] - last[2])
                if d0 != d1:  # a bend: close the straight run
                    add_track(xy(run[0]), xy(last), last[0])
                    run = [last]
            run.append(c)
        if len(run) > 1:
            add_track(xy(run[0]), xy(run[-1]), run[-1][0])
