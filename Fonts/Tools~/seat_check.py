# -*- coding: utf-8 -*-
"""D-33 #7b: every poem, every player key, every seat, at its DEFAULT position, through the same avoidance the runtime
does (Runtime/LanbaiPoemDriver.cs Blocked / Avoid, ported line for line): blocked share of the block on the bus's 1° seat
grid; > 10 % -> move sideways 1° at a time, toward the default first, at most ±15°, the nearest ≤ 10 %; none -> default.

The grid: pkg/bus Bus/Docs~/viewcheck/seats_occlusion_1deg.json ({step, az0, el0, n_az, n_el, seats[{name, eye, occ}]},
rows from el0 upward, columns from az0 rightward, '1' = a bus part). Re-run build_fonts.py whenever the bus updates it.
run(layouts, poems, grid_path) -> dict(rows=[...], summary=...)
"""
import json
import math

LIMIT = 0.10
SEARCH = 15


def load(path):
    g = json.load(open(path, encoding='utf-8'))
    return g


def blocked(g, seat, w, el0, el1, a):
    nAz, nEl, az0, e0 = g['n_az'], g['n_el'], g['az0'], g['el0']
    occ = g['seats'][seat]['occ']
    a0, a1 = a - w * 0.5, a + w * 0.5
    c0, c1 = math.floor(a0) - az0, math.ceil(a1) - az0
    r0, r1 = max(0, math.floor(el0) - e0), min(nEl, math.ceil(el1) - e0)
    n = hit = 0
    for r in range(r0, r1):
        row = r * nAz
        for c in range(c0, c1):
            cc = c % nAz
            n += 1
            if occ[row + cc] == '1':
                hit += 1
    return hit / n if n else 0.0


def avoid(g, seat, w, el0, el1, a, default):
    b = blocked(g, seat, w, el0, el1, a)
    if b <= LIMIT:
        return a, b
    d = 1.0 if default > a else -1.0
    for k in range(1, SEARCH + 1):
        for cand in (a + d * k, a - d * k):
            bb = blocked(g, seat, w, el0, el1, cand)
            if bb <= LIMIT:
                return cand, bb
    return default, b


def run(layouts, poems, grid_path):
    g = load(grid_path)
    P = {p['id']: p for p in poems}
    rows = []
    for pid, per in layouts.items():
        p = P[pid]
        fixed = bool(p.get('mirror') or p.get('picture'))
        for key, lay in per.items():
            b = lay['block']
            w, el0, el1 = b['width_deg'], b['el'][0], b['el'][1]
            default = lay['anchor'][0]
            for s, seat in enumerate(g['seats']):
                b0 = blocked(g, s, w, el0, el1, default)
                if fixed:
                    a, bb = default, b0
                else:
                    a, bb = avoid(g, s, w, el0, el1, default, default)
                rows.append(dict(poem=pid, key=key, seat=s, seat_name=seat['name'], default_az=default,
                                 blocked_default=round(b0, 3), az=a, moved=round(a - default, 1),
                                 blocked=round(bb, 3), fixed=fixed, unresolved=bb > LIMIT))
    moved = [r for r in rows if r['moved'] != 0]
    unresolved = [r for r in rows if r['unresolved']]
    summary = dict(seats=len(g['seats']), checks=len(rows),
                   moved=len(moved), moved_seats=sorted({r['seat_name'] for r in moved}),
                   moved_poems=sorted({r['poem'] for r in moved}),
                   unresolved=len(unresolved), unresolved_list=sorted({(r['poem'], r['seat_name']) for r in unresolved}),
                   grid_about=g.get('_about', ''))
    return dict(rows=rows, summary=summary)
