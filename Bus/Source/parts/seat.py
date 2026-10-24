# -*- coding: utf-8 -*-
"""D-36 A1 · 座椅模块（主座位、前排，23 个座位都用它）。

照的是 `Bus/Docs~/实物参考_车与车厢/车厢_01…03_Fortepan.jpg`（六十年代东欧公交车里）和圣经 §4.2：
  - 一根连续的弯管：从靠背两侧上来，在靠背顶上横过去当扶手（铬），弯管半径 ≈ 2.5 × 管径；
  - 软包的座垫和靠背：细分笼子做的圆鼓边（不是倒角面），座垫前沿微微卷下，中间被坐得微塌；
  - 座垫顶面一圈滚边，靠背正面一圈滚边，双人座的座垫 / 靠背中间一道缝；
  - 靠背背面是包面的背板，一圈滚边 + 腰线；
  - 座垫底下一块托盘（黑漆钢板，四角圆）、一个管框；过道侧一根斜腿落到带三颗螺栓的圆脚座上，墙侧一块螺栓固定的托架。
全部 Unity 坐标；靠背绕座垫后沿后仰 12°。

    seat_module(name, x0, x1, back_z, cushion_y, double, wall_side, on_box=False, worn=1.0) -> [objects]
"""
import math

import numpy as np
from mathutils import Matrix, Vector

import build_bus as BB
import bus_spec as B
from parts import common as C

TILT = math.radians(12)


def _hex_bolt(name, c, axis, r, h, m, collection):
    """a hex bolt head (6 sides, chamfered by a smaller second ring)."""
    return BB.cylinder(name, c, axis, r, h, m, collection, segs=6, bevel=min(0.0012, h * 0.3))


def seat_module(name, x0, x1, back_z, cushion_y=None, double=False, wall_side=1, on_box=False, worn=1.0,
                collection='Seats', lod=0):
    cy = cushion_y or (B.FLOOR_Y + B.SEAT_H)
    W = x1 - x0
    cx = (x0 + x1) / 2
    lv = 2 if lod == 0 else 1
    sides = C.SIDES_NEAR if lod == 0 else C.SIDES_FAR
    objs = []

    # ---------------------------------------------------------------- cushion (not tilted)
    z0c, z1c = back_z + 0.085, back_z + 0.49
    cu = C.cage_pad(name + '_Cushion', (x0 + 0.018, cy - 0.085, z0c), (x1 - 0.018, cy, z1c), 'Vinyl', collection,
                    edge=(0.024, 0.022, 0.024), n=(6 if double else 4, 1, 3), crown=(0.012, 0.006, 0.0, 0.003), levels=lv,
                    sag=0.006 * worn)
    objs.append(cu)
    # piping round the top panel (the seam between the top and the boxing), 4.5 mm
    # (on the rounded edge: ~4 mm in from the box side, ~6 mm below the top - where the top panel's seam is)
    hw, hd = (x1 - x0) / 2 - 0.018 - 0.004, (z1c - z0c) / 2 - 0.004
    ring = C.rrect_path(cx, (z0c + z1c) / 2, hw, hd, 0.030, cy - 0.006, n_arc=8)
    objs.append(C.sweep(name + '_CushionPiping', ring + [ring[0]], 0.0045, 'Vinyl', collection, sides=10, closed=True))
    if double:   # the bench's middle seam: a sunk welt across the top
        objs.append(C.sweep(name + '_CushionSeam', [(cx, cy + 0.006, z0c + 0.05), (cx, cy + 0.009, (z0c + z1c) / 2),
                                                     (cx, cy + 0.004, z1c - 0.04)], 0.0035, 'Vinyl', collection, sides=8))
    # pan under the cushion (rounded corners, folded lip) + the frame rectangle under it
    objs.append(BB.box(name + '_Pan', (x0 + 0.03, cy - 0.118, z0c + 0.01), (x1 - 0.03, cy - 0.094, z1c - 0.01), 'SeatFrame',
                       collection, bevel=0.008, segs=3))
    fy = cy - 0.135
    frame = [(x0 + 0.06, fy, z0c + 0.04), (x1 - 0.06, fy, z0c + 0.04), (x1 - 0.06, fy, z1c - 0.05), (x0 + 0.06, fy, z1c - 0.05)]
    objs.append(C.sweep(name + '_BaseFrame', frame + [frame[0]], 0.011, 'SeatFrame', collection, sides=12, closed=True,
                        bend=0.03))

    # ---------------------------------------------------------------- legs / mounts
    xa = x0 + 0.08 if wall_side > 0 else x1 - 0.08            # aisle side
    xw = x1 - 0.015 if wall_side > 0 else x0 + 0.015          # wall side
    if not on_box:
        # aisle leg: from the frame's aisle-front corner, slanting down and slightly forward, to a round foot
        top = (xa, fy, z1c - 0.07)
        foot = (xa, B.FLOOR_Y + 0.012, z1c - 0.01)
        objs.append(C.sweep(name + '_Leg', [(xa, fy, z0c + 0.06), top, foot], 0.0125, 'SeatFrame', collection,
                            sides=12, bend=0.05))
        objs.append(BB.cylinder(name + '_Foot', (foot[0], B.FLOOR_Y + 0.004, foot[2]), 'y', 0.038, 0.008, 'SeatFrame',
                                collection, segs=24, bevel=0.002))
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.4
            _ = objs.append(_hex_bolt(name + '_FootBolt%d' % k, (foot[0] + 0.026 * math.cos(a), B.FLOOR_Y + 0.010,
                                                              foot[2] + 0.026 * math.sin(a)), 'y', 0.0055, 0.004, 'Alu', collection))
    else:
        # the hero row sits on the wheel box: two angle brackets bolted to its top
        for zz in (z0c + 0.06, z1c - 0.06):
            objs.append(BB.box(name + '_BoxBracket%.2f' % zz, (xa - 0.02, fy - 0.03, zz - 0.02), (xa + 0.02, fy + 0.005, zz + 0.02),
                               'SeatFrame', collection, bevel=0.003, segs=2))
    # wall bracket: a plate on the wall with two bolts, the frame tube runs into it
    wy = fy
    objs.append(BB.box(name + '_WallPlate', (xw - 0.006, wy - 0.05, (z0c + z1c) / 2 - 0.07),
                       (xw + 0.006, wy + 0.05, (z0c + z1c) / 2 + 0.07), 'SeatFrame', collection, bevel=0.004, segs=2))
    for dz in (-0.045, 0.045):
        objs.append(_hex_bolt(name + '_WallBolt%+.2f' % dz, (xw - wall_side * 0.008, wy, (z0c + z1c) / 2 + dz), 'x',
                              0.006, 0.005, 'Alu', collection))
    objs.append(C.sweep(name + '_WallArm', [(x1 - 0.06 if wall_side > 0 else x0 + 0.06, fy, (z0c + z1c) / 2),
                                           (xw - wall_side * 0.008, wy, (z0c + z1c) / 2)], 0.011, 'SeatFrame', collection,
                        sides=12))

    # ---------------------------------------------------------------- backrest (tilted 12 deg about the cushion's rear)
    back = []
    bx0, bx1 = x0 + 0.036, x1 - 0.036                        # the bent tube runs outside these, along the sides
    bz0, bz1 = back_z + 0.028, back_z + 0.092
    back.append(C.cage_pad(name + '_Back', (bx0, cy - 0.01, bz0), (bx1, cy + 0.585, bz1), 'Vinyl', collection,
                           edge=(0.022, 0.03, 0.02), n=(6 if double else 4, 4, 1), crown=(0.006, 0.012, 0.0, 0.002), levels=lv))
    # front piping (in the plane of the front face, round its edge)
    zf = bz1 - 0.012
    pts = []
    hw2, hh = (bx1 - bx0) / 2 - 0.004, (0.595) / 2 - 0.004
    ccy = cy + 0.2875
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx_, ccy_ = cx + sx * (hw2 - 0.036), ccy + sy * (hh - 0.036)
        for k in range(9):
            a = math.radians(a0 + 90 * k / 8)
            pts.append((ccx_ + 0.036 * math.cos(a), ccy_ + 0.036 * math.sin(a), zf))
    back.append(C.sweep(name + '_BackPiping', pts + [pts[0]], 0.0045, 'Vinyl', collection, sides=10, closed=True))
    if double:
        back.append(C.sweep(name + '_BackSeamF', [(cx, cy + 0.03, bz1 + 0.006), (cx, cy + 0.29, bz1 + 0.012),
                                                  (cx, cy + 0.55, bz1 + 0.004)], 0.0035, 'Vinyl', collection, sides=8))
    # rear panel: a thin upholstered board with a welt round it and a lumbar seam
    back.append(C.cage_pad(name + '_BackShell', (bx0 + 0.004, cy + 0.0, back_z), (bx1 - 0.004, cy + 0.575, back_z + 0.03),
                           'Vinyl', collection, edge=0.010, n=(3, 3, 1), crown=(0.0, 0.0, 0.004, 0.0), levels=lv))
    zb = back_z - 0.002
    xa_, xb_, ya_, yb_ = bx0 + 0.03, bx1 - 0.03, cy + 0.04, cy + 0.54
    rr = 0.03
    welt = []
    for (px, py, a0) in ((xb_ - rr, yb_ - rr, 0), (xa_ + rr, yb_ - rr, 90), (xa_ + rr, ya_ + rr, 180), (xb_ - rr, ya_ + rr, 270)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            welt.append((px + rr * math.cos(a), py + rr * math.sin(a), zb))
    back.append(C.sweep(name + '_BackWelt', welt + [welt[0]], 0.0032, 'Vinyl', collection, sides=8, closed=True))
    back.append(C.sweep(name + '_BackSeam', [(xa_ + 0.004, cy + 0.24, zb), (xb_ - 0.004, cy + 0.24, zb)], 0.0026, 'Vinyl',
                        collection, sides=8))
    # the bent tube: up both sides of the back and across the top (chrome, §4.2), with clamps to the back board
    # (Fortepan 03: the tube is in plain sight along both sides of the back and ~5 cm over its top)
    rz = back_z + 0.052
    ry_top = cy + 0.635
    xl, xr = x0 + 0.020, x1 - 0.020
    u_path = [(xl, cy - 0.02, rz), (xl, ry_top, rz), (xr, ry_top, rz), (xr, cy - 0.02, rz)]
    back.append(C.sweep(name + '_Rail', u_path, 0.011, 'Chrome', collection, sides=sides, bend=0.055, seg_per_90=10))
    for xx in (xl, xr):
        for yy in (cy + 0.12, cy + 0.45):
            sg = 1 if xx > cx else -1                         # a flat strap from the tube into the back's side
            a_, b_ = sorted((xx - sg * 0.004, (bx1 if sg > 0 else bx0) - sg * 0.004))
            back.append(BB.box(name + '_Clamp%.2f_%.2f' % (xx, yy), (a_, yy - 0.011, rz - 0.009), (b_, yy + 0.011, rz + 0.009),
                               'SeatFrame', collection, bevel=0.003, segs=2))
    pb = BB.U2B((0, cy - 0.02, back_z + 0.09))
    R = Matrix.Translation(pb) @ Matrix.Rotation(-TILT, 4, 'X') @ Matrix.Translation(-pb)
    C.transform(back, R)
    objs += back
    return objs
