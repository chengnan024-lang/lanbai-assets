"""Rain on glass: deposition + coalescence of sessile drops on a periodic tile (metres).

Each bead = spherical cap (contact radius a, contact angle th) with a pinned, slightly irregular outline.
Deposits overlap-test against neighbours; merging conserves volume, new centre = volume-weighted, cascade until
no overlaps.  Beads larger than A_CRIT (vertical pane) leave as runners (removed) -> the real size cutoff.
"""
import numpy as np


def cap_volume(a, th):
    c = np.cos(th); s = np.sin(th)
    return np.pi * a ** 3 * (2 - 3 * c + c ** 3) / (3 * s ** 3)


def cap_radius(V, th):
    c = np.cos(th); s = np.sin(th)
    return (3 * V * s ** 3 / (np.pi * (2 - 3 * c + c ** 3))) ** (1 / 3)


class Beads:
    def __init__(self, tile, a_crit, rng, th_range=(0.62, 0.95)):
        self.tile = tile; self.a_crit = a_crit; self.rng = rng; self.th_range = th_range
        self.cell = 2.2 * a_crit
        self.nc = max(1, int(tile / self.cell))
        self.cell = tile / self.nc
        self.grid = {}
        self.b = {}          # id -> dict(x, y, a, th, V, merges, axis)
        self.next = 0
        self.runners = 0

    def _key(self, x, y):
        return (int(x / self.cell) % self.nc, int(y / self.cell) % self.nc)

    def _add(self, bid):
        d = self.b[bid]; self.grid.setdefault(self._key(d['x'], d['y']), set()).add(bid)

    def _rem(self, bid):
        d = self.b[bid]; self.grid[self._key(d['x'], d['y'])].discard(bid)

    def _neighbours(self, x, y):
        cx, cy = self._key(x, y)
        out = []
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                out.extend(self.grid.get(((cx + i) % self.nc, (cy + j) % self.nc), ()))
        return out

    def _pd(self, x0, y0, x1, y1):
        dx = (x1 - x0 + self.tile / 2) % self.tile - self.tile / 2
        dy = (y1 - y0 + self.tile / 2) % self.tile - self.tile / 2
        return dx, dy

    def deposit(self, x, y, V, th=None):
        th = th if th is not None else self.rng.uniform(*self.th_range)
        bid = self.next; self.next += 1
        self.b[bid] = dict(x=x % self.tile, y=y % self.tile, V=V, th=th, a=cap_radius(V, th), merges=0, axis=0.0, elong=0.0)
        self._add(bid)
        self._settle(bid)

    def _settle(self, bid):
        while True:
            d = self.b[bid]
            hit = None
            for o in self._neighbours(d['x'], d['y']):
                if o == bid:
                    continue
                e = self.b[o]
                dx, dy = self._pd(d['x'], d['y'], e['x'], e['y'])
                if dx * dx + dy * dy < (d['a'] + e['a']) ** 2 * 0.98:
                    hit = o; break
            if hit is None:
                break
            e = self.b[hit]
            dx, dy = self._pd(d['x'], d['y'], e['x'], e['y'])
            V = d['V'] + e['V']; w = e['V'] / V
            self._rem(bid); self._rem(hit)
            big, small = (d, e) if d['V'] >= e['V'] else (e, d)
            nx = d['x'] + dx * w; ny = d['y'] + dy * w
            th = (d['th'] * d['V'] + e['th'] * e['V']) / V
            elong = min(0.35, 0.55 * min(d['V'], e['V']) / V + 0.5 * big['elong'])   # pinned footprint stays stretched
            axis = np.arctan2(dy, dx)
            del self.b[hit]
            self.b[bid] = dict(x=nx % self.tile, y=ny % self.tile, V=V, th=th, a=cap_radius(V, th),
                               merges=d['merges'] + e['merges'] + 1, axis=axis, elong=elong)
            self._add(bid)
        if self.b[bid]['a'] > self.a_crit:                  # too heavy: it runs away down the pane
            self._rem(bid); del self.b[bid]; self.runners += 1

    def coverage(self):
        return sum(np.pi * d['a'] ** 2 for d in self.b.values()) / self.tile ** 2
