# -*- coding: utf-8 -*-
"""每个座位的遮挡网格（D-33 #7b，格式由总工程师定）：Bus/Docs~/viewcheck/seats_occlusion_1deg.json

    {"step": 1, "az0": -180, "el0": EL0, "n_az": 360, "n_el": N_EL,
     "seats": [{"name": "SeatR0", "eye": [x, y, z], "occ": "0101..."}, ...]}

occ = n_el 行（从 el0 往上）× n_az 格（从 az0 往右）连起来；'1' = 从这个座位的眼睛穿过格子中心
（az0 + j + 0.5, el0 + i + 0.5）的射线碰到车的不透明件（玻璃不算，穿过去）。座位顺序 = BusLayout.json 的
seats 顺序（主座位 SeatR0 在第 0 个）= SetSeat(座位号)。用完整、未侵蚀、门开着的车（侵蚀是运行时的事）。
主座位的眼睛用合同眼位 bus_spec.EYE (0.55, 1.70, 2.05)；别的座位用 BusLayout 的 eye_approx（座垫 + 0.68、靠背前 0.23）。

    ~/bpy/bin/python Bus/Source/seat_occlusion.py [--el0 -30 --el1 30]
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bus_spec as B  # noqa: E402
import build_bus  # noqa: E402
import viewcheck as V  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', default=os.path.join(HERE, '..', 'Models', 'BusLayout.json'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'Docs~', 'viewcheck', 'seats_occlusion_1deg.json'))
    ap.add_argument('--el0', type=int, default=-30)
    ap.add_argument('--el1', type=int, default=30)
    a = ap.parse_args()
    L = json.load(open(a.layout, encoding='utf-8'))
    build_bus.build()
    bvh, owner = V.scene_bvh()
    n_az, n_el = 360, a.el1 - a.el0
    seats = []
    for k, s in enumerate(L['seats']):
        eye = list(B.EYE) if s.get('hero') else list(s['eye_approx'])
        eb = V.U2B(eye)
        rows = []
        for i in range(n_el):
            el = a.el0 + i + 0.5
            row = []
            for j in range(n_az):
                az = -180 + j + 0.5
                _, opq = V.cast(bvh, owner, eb, V.U2B(B.dir_az_el(az, el)))
                row.append('1' if opq is not None else '0')
            rows.append(''.join(row))
        occ = ''.join(rows)
        seats.append(dict(name=s['name'], eye=[round(v, 4) for v in eye], occ=occ))
        print('[seat_occ] %2d %-10s blocked %.1f%%' % (k, s['name'], 100.0 * occ.count('1') / len(occ)))
    assert seats and L['seats'][0].get('hero'), 'the hero seat must be seat 0 (BusLayout order)'
    out = dict(step=1, az0=-180, el0=a.el0, n_az=n_az, n_el=n_el,
               _about='D-33 #7b. occ: n_el rows from el0 upward, n_az cells from az0 rightward; 1 = opaque bus part on the '
                      'ray through the cell centre (glass passes). Full, uneroded bus, door open. az 0 = forward, + = right '
                      '(door side); el + = up; degrees. Seat order = BusLayout.json seats = SetSeat index; hero = 0.',
               seats=seats)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('[seat_occ] %d seats -> %s (%.0f KB)' % (len(seats), a.out, os.path.getsize(a.out) / 1024))


if __name__ == '__main__':
    main()
