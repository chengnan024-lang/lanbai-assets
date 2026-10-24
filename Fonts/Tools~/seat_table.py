# -*- coding: utf-8 -*-
"""D-37 (main f0fea3f): every seat's poem positions, solved OFFLINE on the bus's 1° seat grids; the runtime only looks up.

For every seat s (the main seat 0 keeps D-33's default: it is part of the film's composition), every poem p that may move
(not Zhuangzi, not Tianwen) and every player key k:
  * candidates: block centre azimuth anywhere on the circle (1°), block centre elevation -15…+10° (1°), the block's own
    width and height (layout[k].block);
  * blocked share from the seat's grid (summed-area table, columns wrap around);
  * among candidates with blocked <= 10 %: prefer >= 12° from the act's focus (poem 'focus', if known), then the nearest
    to the target (angular distance, azimuth scaled by cos(elevation)); none <= 10 % -> the least blocked (never "back
    to the default");
  * target = the default direction (as seen from that seat) for the default table, and for the gaze table the gaze rule's
    position for each of 24 facings (15° cells): round(yaw / 15) * 15 + 20° toward the default.
Output (Fonts/seat_positions.json): {seats, poems, keys, facings, default[s][p][k] = [az, el, blocked],
gaze[s][p][k][f] = [az, el, blocked]} and a summary. Re-run build_fonts.py whenever the bus updates the grid.
"""
import json
import math
import numpy as np

LIMIT = 0.10
EL_MIN, EL_MAX = -15, 10
FOCUS_CLEAR = 12.0
FACINGS = 24


class SeatGrid:
    def __init__(self, g, s):
        self.nAz, self.nEl, self.az0, self.el0 = g['n_az'], g['n_el'], g['az0'], g['el0']
        occ = np.frombuffer(g['seats'][s]['occ'].encode('ascii'), dtype=np.uint8) == ord('1')
        occ = occ.reshape(self.nEl, self.nAz).astype(np.int32)
        wrap = np.concatenate([occ, occ], axis=1)                  # columns wrap around the circle
        self.sat = np.zeros((self.nEl + 1, 2 * self.nAz + 1), np.int64)
        self.sat[1:, 1:] = wrap.cumsum(0).cumsum(1)

    def blocked(self, az_c, el_c, w, h):
        """vectorised: az_c, el_c arrays of block centres (deg); the same cell rule as LanbaiPoemDriver.Blocked."""
        a0, a1 = az_c - w / 2.0, az_c + w / 2.0
        c0 = np.floor(a0).astype(int) - self.az0
        c1 = np.ceil(a1).astype(int) - self.az0
        r0 = np.clip(np.floor(el_c - h / 2.0).astype(int) - self.el0, 0, self.nEl)
        r1 = np.clip(np.ceil(el_c + h / 2.0).astype(int) - self.el0, 0, self.nEl)
        shift = np.floor_divide(c0, self.nAz) * self.nAz            # bring c0 into [0, nAz)
        c0, c1 = c0 - shift, c1 - shift
        c1 = np.minimum(c1, c0 + self.nAz)
        S = self.sat
        tot = S[r1, c1] - S[r0, c1] - S[r1, c0] + S[r0, c0]
        n = (r1 - r0) * (c1 - c0)
        return np.where(n > 0, tot / np.maximum(n, 1), 0.0)


def ang(az1, el1, az2, el2):
    d = (az1 - az2 + 180.0) % 360.0 - 180.0
    return np.hypot(d * np.cos(np.radians((el1 + el2) / 2.0)), el1 - el2)


def solve(grid, w, h, target_az, target_el, focus):
    AZ, EL = np.meshgrid(np.arange(-180, 180, 1.0), np.arange(EL_MIN, EL_MAX + 1, 1.0))
    AZ, EL = AZ.ravel(), EL.ravel()
    b = grid.blocked(AZ, EL, w, h)
    dist = ang(AZ, EL, target_az, target_el)
    ok = b <= LIMIT
    if ok.any():
        pool = ok
        if focus is not None:
            far = ok & (ang(AZ, EL, focus[0], focus[1]) >= FOCUS_CLEAR)
            if far.any():
                pool = far
        i = np.flatnonzero(pool)[np.argmin(dist[pool])]
    else:
        i = int(np.lexsort((dist, b))[0])                          # least blocked, then the nearest
    return float(AZ[i]), float(EL[i]), float(b[i])


def run(layouts, poems, grid_path, keys):
    g = json.load(open(grid_path, encoding='utf-8'))
    P = {p['id']: p for p in poems}
    pids = [p['id'] for p in poems]
    seats = [s['name'] for s in g['seats']]
    default = [[[None] * len(keys) for _ in pids] for _ in seats]
    gaze = [[[None] * len(keys) for _ in pids] for _ in seats]
    rows = []
    for s in range(len(seats)):
        grid = SeatGrid(g, s)
        for pi, pid in enumerate(pids):
            p = P[pid]
            fixed = bool(p.get('mirror') or p.get('picture'))
            focus = p.get('focus')
            for ki, k in enumerate(keys):
                lay = layouts[pid][k]
                b = lay['block']
                w, h = b['width_deg'], b['el'][1] - b['el'][0]
                caz, cel = lay['anchor'][0], (b['el'][0] + b['el'][1]) / 2.0
                b0 = float(grid.blocked(np.array([caz]), np.array([cel]), w, h)[0])
                if s == 0 or fixed:
                    res = (caz, cel, b0)
                else:
                    res = solve(grid, w, h, caz, cel, focus)
                default[s][pi][ki] = [round(res[0], 1), round(res[1], 1), round(res[2], 3)]
                rows.append(dict(seat=seats[s], s=s, poem=pid, key=k, fixed=fixed, default_az=caz, default_el=round(cel, 2),
                                 blocked_default=round(b0, 3), az=res[0], el=res[1], blocked=round(res[2], 3)))
                if fixed:
                    gaze[s][pi][ki] = None
                    continue
                gl = []
                thr = p.get('gaze_deg', 50.0)
                for f in range(FACINGS):
                    yaw = -180.0 + 15.0 * f
                    d = (caz - yaw + 180.0) % 360.0 - 180.0
                    if abs(d) <= thr:
                        gl.append(default[s][pi][ki])               # the rule keeps the default for this facing
                        continue
                    t_az = round(yaw / 15.0) * 15.0 + (20.0 if d > 0 else -20.0)
                    r = solve(grid, w, h, t_az, cel, focus)
                    gl.append([round(r[0], 1), round(r[1], 1), round(r[2], 3)])
                gaze[s][pi][ki] = gl
    return dict(seats=seats, eyes=[sd['eye'] for sd in g['seats']], poems=pids, keys=list(keys), facings=FACINGS, limit=LIMIT, el_range=[EL_MIN, EL_MAX],
                default=default, gaze=gaze, rows=rows, grid_about=g.get('_about', ''))


def summary(T):
    rows = [r for r in T['rows'] if not r['fixed']]
    per_seat = {}
    for r in rows:
        per_seat.setdefault(r['seat'], []).append(r['blocked'])
    mean = {k: sum(v) / len(v) for k, v in per_seat.items()}
    others = [b for k, v in per_seat.items() if k != T['seats'][0] for b in v]
    worst = sorted(rows, key=lambda r: -r['blocked'])[:12]
    n_moved = sum(1 for r in rows if abs(r['az'] - r['default_az']) > 0.5 or abs(r['el'] - r['default_el']) > 0.5)
    S, Pn, K, F = len(T['seats']), len(T['poems']), len(T['keys']), T['facings']
    return dict(mean_by_seat={k: round(v, 3) for k, v in mean.items()},
                mean_others=round(sum(others) / len(others), 3) if others else 0.0,
                over_limit=sum(1 for b in others if b > LIMIT), checks_others=len(others),
                moved=n_moved, worst=[(r['seat'], r['poem'], r['key'], r['blocked']) for r in worst],
                table_entries=dict(default=S * Pn * K, gaze=S * Pn * K * F,
                                   floats=2 * (S * Pn * K + S * Pn * K * F)))
