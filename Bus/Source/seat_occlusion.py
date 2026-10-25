# -*- coding: utf-8 -*-
"""每个座位的遮挡网格（D-33 #7b，格式由总工程师定）：Bus/Docs~/viewcheck/seats_occlusion_1deg.json

    {"step": 1, "az0": -180, "el0": EL0, "n_az": 360, "n_el": N_EL,
     "seats": [{"name": "SeatR0", "eye": [x, y, z], "occ": "0101..."}, ...]}

occ = n_el 行（从 el0 往上）× n_az 格（从 az0 往右）连起来；'1' = 从这个座位的眼睛穿过格子中心
（az0 + j + 0.5, el0 + i + 0.5）的射线碰到车的不透明件（玻璃不算，穿过去）。座位顺序 = BusLayout.json 的
seats 顺序（主座位 SeatR0 在第 0 个）= SetSeat(座位号)。用完整、未侵蚀、门开着的车（侵蚀是运行时的事）。
主座位的眼睛用合同眼位 bus_spec.EYE (0.55, 1.70, 2.05)；别的座位用 BusLayout 的 eye_approx（座垫 + 0.68、靠背前 0.23）。

    ~/bpy/bin/python Bus/Source/seat_occlusion.py [--el0 -30 --el1 30]

D-45（总导演 10-25，`Art/字幕方案_D-45.md` C.2）：--subtitle-depth 出字幕深度表 Bus/Docs~/viewcheck/subtitle_depth.json
（字体包拷到 Fonts/）。23 个座位 × 偏航 24 格（每格 15°，格心 −180、−165 … +165，各管 ±7.5°）× 俯仰 9 格（格心 −40 … +40，
各管 ±5°）。每格按 1° 打 150 条射线；每条记第一个碰到的不透明件（玻璃穿过去，--opaque-glass 列出的除外）和距离。
d_near = 在这一格里当“第一个碰到的”占 ≥ 10 % 射线的那些件里，最近的一次碰撞距离（细柱这类不到 10 % 的不算，交给
ZTest Always）；depth = clamp(0.92 × d_near, 0.45, 1.0) m；这一格没有够格的件（看出去是窗外）就是 1.0。
    ~/bpy/bin/python Bus/Source/seat_occlusion.py --subtitle-depth [--opaque-glass Glass_Windshield,...]
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


def first_opaque(bvh, owner, eye_b, d_b, opaque_glass=(), maxd=40.0):
    """walk through glass (except the panes in opaque_glass): (name, distance) of the first opaque hit, or (None, None)."""
    from mathutils import Vector
    o, d = Vector(eye_b), Vector(d_b).normalized()
    start = Vector(eye_b)
    for _ in range(12):
        hit = bvh.ray_cast(o, d, maxd)
        if hit[0] is None:
            return None, None
        nm = owner[hit[2]]
        if V.classify(nm) is None or nm in opaque_glass:
            return nm, (hit[0] - start).length
        o = hit[0] + d * 1e-4
    return None, None


def subtitle_depth(L, bvh, owner, out, opaque_glass=()):
    YAW0, YSTEP, NY = -180.0, 15.0, 24
    P0, PSTEP, NP = -40.0, 10.0, 9
    seats = []
    for k, s in enumerate(L['seats']):
        eye = list(B.EYE) if s.get('hero') else list(s['eye_approx'])
        eb = V.U2B(eye)
        depth, dnear, who = [], [], []
        for j in range(NY):
            yc = YAW0 + YSTEP * j
            drow, nrow, wrow = [], [], []
            for i in range(NP):
                pc = P0 + PSTEP * i
                hits = {}
                n = 0
                for dy in np.arange(-7.0, 7.01, 1.0):
                    for dp in np.arange(-4.5, 4.51, 1.0):
                        n += 1
                        nm, dist = first_opaque(bvh, owner, eb, V.U2B(B.dir_az_el(yc + dy, pc + dp)), opaque_glass)
                        if nm is not None:
                            h = hits.setdefault(nm, [0, 1e9])
                            h[0] += 1
                            h[1] = min(h[1], dist)
                good = [(v[1], nm) for nm, v in hits.items() if v[0] >= 0.10 * n]
                if good:
                    dn, nm = min(good)
                    drow.append(round(float(min(max(0.92 * dn, 0.45), 1.0)), 3))
                    nrow.append(round(float(dn), 3))
                    wrow.append(nm)
                else:
                    drow.append(1.0)
                    nrow.append(None)
                    wrow.append(None)
            depth.append(drow)
            dnear.append(nrow)
            who.append(wrow)
        seats.append(dict(name=s['name'], eye=[round(v, 4) for v in eye], depth=depth, d_near=dnear, nearest_part=who))
        flat = [v for r in depth for v in r]
        print('[subtitle_depth] %2d %-10s depth min %.2f  median %.2f  cells at 0.45: %d / %d'
              % (k, s['name'], min(flat), float(np.median(flat)), sum(1 for v in flat if v <= 0.4501), len(flat)))
    assert seats and L['seats'][0].get('hero'), 'the hero seat must be seat 0 (BusLayout order)'
    res = dict(_about='D-45 subtitle depth (Art/字幕方案_D-45.md C.2; seat_occlusion.py --subtitle-depth). depth[seat][yaw][pitch] '
                      'in metres = clamp(0.92 x d_near, 0.45, 1.0); d_near = the nearest hit of any opaque part that is the first '
                      'hit for >= 10 % of the cell\'s 1-degree rays (glass passes, except opaque_glass); 1.0 where no part '
                      'qualifies. Full, uneroded bus, door open, the current Bus/Source build. Seat order = BusLayout.json seats '
                      '= SetSeat index; hero = 0. Yaw 0 = forward, + = right (door side); pitch + = up.',
               yaw0=YAW0, yaw_step=YSTEP, n_yaw=NY, pitch0=P0, pitch_step=PSTEP, n_pitch=NP,
               cells='yaw cell j: centre yaw0 + yaw_step * j (covers +-7.5 deg); pitch cell i: centre pitch0 + pitch_step * i '
                     '(covers +-5 deg)',
               runtime='take the minimum of the cell and its two yaw neighbours (no interpolation)',
               opaque_glass=sorted(opaque_glass), seats=seats)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('[subtitle_depth] %d seats -> %s (%.0f KB)' % (len(seats), out, os.path.getsize(out) / 1024))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', default=os.path.join(HERE, '..', 'Models', 'BusLayout.json'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'Docs~', 'viewcheck', 'seats_occlusion_1deg.json'))
    ap.add_argument('--el0', type=int, default=-30)
    ap.add_argument('--el1', type=int, default=30)
    ap.add_argument('--subtitle-depth', action='store_true', help='D-45: write the subtitle depth table instead')
    ap.add_argument('--depth-out', default=os.path.join(HERE, '..', 'Docs~', 'viewcheck', 'subtitle_depth.json'))
    ap.add_argument('--opaque-glass', default='', help='comma list of Glass_* panes that count as opaque (rain film, dirt)')
    a = ap.parse_args()
    L = json.load(open(a.layout, encoding='utf-8'))
    build_bus.build()
    bvh, owner = V.scene_bvh()
    if a.subtitle_depth:
        subtitle_depth(L, bvh, owner, a.depth_out, tuple(x for x in a.opaque_glass.split(',') if x))
        return
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
