# -*- coding: utf-8 -*-
"""D-36 A3 · 立柱和扶杆（Ø32 不锈钢，圣经 §4.2；握手高度 1.0–1.8 m 被握亮）。

照片：Fortepan 01–03（竖杆从地板到顶棚、座椅靠背顶的扶手管）、trolleway 的过道（看点文字）。真车的做法：
  - 管子 20 段（离眼 2 m 内 ≥ 16，D-36），弯管半径 ≈ 2.5 × 管径；
  - 立柱上下各一个法兰座（圆盘 + 3 颗螺钉），顶上的法兰贴着顶棚；
  - 顶上两根纵向扶杆用吊杆挂在顶棚上，吊杆和扶杆相交处是一个对开的管夹（两半圆 + 两颗螺栓），扶杆两端是带法兰的弯头；
  - 立柱上 1.5 m 处一个停车按钮盒（672M：“叫司机停车的按钮”）；
  - 门口扶手：两端弯进门柱、法兰固定。
所有的东西都用 parts/common.sweep（真圆角弯）和 BB.cylinder（倒角的法兰）。不锈钢的握亮由 Lanbai/Cabin 的
_HeightSmooth 做（1.62–2.42 m 以外的段落更哑）；这里不画。
"""
import math

import numpy as np

import build_bus as BB
import bus_spec as B
from parts import common as C

R_POLE = 0.016                # Ø32
SIDES = 20


def flange(name, c, axis_sign, collection, r=0.034, t=0.007):
    """a round base flange on the floor (axis_sign +1, the pole goes up) or the ceiling (-1) with 3 slotted screws."""
    x, y, z = c
    objs = [BB.cylinder(name, (x, y + axis_sign * t / 2, z), 'y', r, t, 'Steel', collection, segs=28, bevel=0.0018)]
    objs.append(BB.cylinder(name + '_Collar', (x, y + axis_sign * (t + 0.010), z), 'y', R_POLE + 0.004, 0.020, 'Steel',
                            collection, segs=SIDES, bevel=0.0015))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        objs.append(BB.cylinder(name + '_Screw%d' % k, (x + 0.025 * math.cos(a), y + axis_sign * (t + 0.001), z + 0.025 * math.sin(a)),
                                'y', 0.0042, 0.002, 'Steel', collection, segs=10, bevel=0.0007))
    return objs


def pole(name, x, z, y0, y1, collection='Cabin', button=False):
    """a floor-to-ceiling stanchion with both flanges (and the 672M stop button if asked)."""
    objs = [C.sweep(name, [(x, y0 + 0.008, z), (x, y1 - 0.008, z)], R_POLE, 'Steel', collection, sides=SIDES)]
    objs += flange(name + '_Floor', (x, y0, z), +1, collection)
    objs += flange(name + '_Ceil', (x, y1, z), -1, collection)
    if button:
        objs += stop_button(name + '_Stop', x, 1.50, z, collection)
    return objs


def stop_button(name, x, y, z, collection):
    """a small pressed-steel box clamped round the pole with a red mushroom push button facing the aisle."""
    objs = [BB.box(name + '_Box', (x - 0.028, y - 0.045, z - 0.032), (x + 0.028, y + 0.045, z - 0.010), 'Ext_Cream', collection,
                   bevel=0.006, segs=3)]
    objs.append(BB.cylinder(name + '_Clamp', (x, y, z), 'y', R_POLE + 0.0035, 0.10, 'Steel', collection, segs=SIDES, bevel=0.002))
    objs.append(BB.cylinder(name + '_Ring', (x, y, z - 0.034), 'z', 0.017, 0.005, 'Chrome', collection, segs=24, bevel=0.0012))
    objs.append(BB.cylinder(name + '_Knob', (x, y, z - 0.040), 'z', 0.013, 0.008, 'ButtonRed', collection, segs=24, bevel=0.004))
    return objs


def ceiling_rail(name, x, z0, z1, y, hangers, ceil_y_fn, collection='Cabin'):
    """a longitudinal grab rail: the rail, its end elbows up into ceiling flanges, hangers with split clamps."""
    objs = []
    path = [(x, ceil_y_fn(x) - 0.010, z0), (x, y, z0), (x, y, z1), (x, ceil_y_fn(x) - 0.010, z1)]
    objs.append(C.sweep(name, path, R_POLE, 'Steel', collection, sides=SIDES, bend=0.06, seg_per_90=10))
    for z in (z0, z1):
        objs += flange(name + '_End%.2f' % z, (x, ceil_y_fn(x), z), -1, collection, r=0.030)
    for k, z in enumerate(hangers):
        yc = ceil_y_fn(x)
        objs.append(C.sweep(name + '_Hanger%d' % k, [(x, y + R_POLE + 0.010, z), (x, yc - 0.008, z)], 0.010, 'Steel',
                            collection, sides=16))
        objs += flange(name + '_HangerTop%d' % k, (x, yc, z), -1, collection, r=0.024, t=0.006)
        objs += split_clamp(name + '_Clamp%d' % k, x, y, z, collection)
    return objs


def split_clamp(name, x, y, z, collection):
    """the T joint: a 50 mm sleeve round the rail (two halves, a seam), a socket up into the hanger, two bolt heads."""
    objs = [BB.cylinder(name + '_Sleeve', (x, y, z), 'z', R_POLE + 0.0045, 0.052, 'Steel', collection, segs=SIDES, bevel=0.002)]
    objs.append(BB.cylinder(name + '_Socket', (x, y + R_POLE + 0.010, z), 'y', 0.0145, 0.026, 'Steel', collection, segs=16,
                            bevel=0.0015))
    for dz in (-0.017, 0.017):
        objs.append(BB.cylinder(name + '_Bolt%+.3f' % dz, (x + R_POLE + 0.006, y - 0.004, z + dz), 'x', 0.0045, 0.004,
                                'Steel', collection, segs=6, bevel=0.0008))
    return objs


def door_grab(name, x_wall, z, y0, y1, collection='Cabin'):
    """the door-side grab handle: a bent tube standing off the wall by 45 mm, flanged into the wall at both ends."""
    xs = x_wall - 0.045
    path = [(x_wall - 0.004, y0, z + 0.04), (xs, y0 + 0.02, z), (xs, y1 - 0.02, z), (x_wall - 0.004, y1, z + 0.04)]
    objs = [C.sweep(name, path, 0.0125, 'Steel', collection, sides=SIDES, bend=0.035, seg_per_90=8)]
    for yy in (y0, y1):
        objs.append(BB.cylinder(name + '_Mount%.2f' % yy, (x_wall - 0.004, yy, z + 0.04), 'x', 0.022, 0.008, 'Steel',
                                collection, segs=24, bevel=0.0015))
    return objs
