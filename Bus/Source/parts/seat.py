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
                collection='Seats', quality='low', wall_x=None):
    """wall_side +1 / -1: the wall is on +x / -x (bracket + arm to wall_x); 0: no wall (rear bench, driver).
    quality 'high' = the bake source (subdivision 3, 24-sided tubes); 'low' = the game mesh (subdivision 1,
    16-sided tubes: D-36 >= 16 within 2 m) that gets the high one's detail through the baked normal / AO."""
    cy = cushion_y or (B.FLOOR_Y + B.SEAT_H)
    W = x1 - x0
    cx = (x0 + x1) / 2
    hi = quality == 'high'
    lv = 3 if hi else 1
    sides = 24 if hi else 16
    small = 12 if hi else 6                                   # piping / welts (4-5 mm: the normal map carries them)
    frame_s = 16 if hi else 10
    objs = []

    # ---------------------------------------------------------------- cushion (not tilted)
    z0c, z1c = back_z + 0.085, back_z + 0.49
    objs += _cushion(name, x0, x1, cx, cy, z0c, z1c, double, worn, wall_side, lv, small, collection)
    # pan under the cushion (rounded corners, folded lip) + the frame rectangle under it
    objs.append(BB.box(name + '_Pan', (x0 + 0.03, cy - 0.118, z0c + 0.01), (x1 - 0.03, cy - 0.094, z1c - 0.01), 'SeatFrame',
                       collection, bevel=0.008, segs=3))
    fy = cy - 0.135
    frame = [(x0 + 0.06, fy, z0c + 0.04), (x1 - 0.06, fy, z0c + 0.04), (x1 - 0.06, fy, z1c - 0.05), (x0 + 0.06, fy, z1c - 0.05)]
    objs.append(C.sweep(name + '_BaseFrame', frame + [frame[0]], 0.011, 'SeatFrame', collection, sides=frame_s, closed=True,
                        bend=0.03))

    # ---------------------------------------------------------------- legs / mounts
    xa = x0 + 0.08 if wall_side >= 0 else x1 - 0.08           # aisle side
    if wall_x is None:
        wall_x = x1 if wall_side > 0 else x0
    xw = wall_x - wall_side * 0.006                           # the bracket plate on the wall
    if not on_box:
        # legs: one on the aisle side (wall seats); both ends + the middle when there is no wall (rear bench)
        legs = [xa] if wall_side != 0 else [x0 + 0.08, (x0 + x1) / 2, x1 - 0.08]
        for li, xl_ in enumerate(legs):
            top = (xl_, fy, z1c - 0.07)
            foot = (xl_, B.FLOOR_Y + 0.012, z1c - 0.01)
            objs.append(C.sweep(name + '_Leg%d' % li, [(xl_, fy, z0c + 0.06), top, foot], 0.0125, 'SeatFrame', collection,
                                sides=frame_s, bend=0.05))
            objs.append(BB.cylinder(name + '_Foot%d' % li, (foot[0], B.FLOOR_Y + 0.004, foot[2]), 'y', 0.038, 0.008, 'SeatFrame',
                                    collection, segs=24 if hi else 16, bevel=0.002))
            for k in range(3):
                a = 2 * math.pi * k / 3 + 0.4
                objs.append(_hex_bolt(name + '_FootBolt%d_%d' % (li, k), (foot[0] + 0.026 * math.cos(a), B.FLOOR_Y + 0.010,
                                                                       foot[2] + 0.026 * math.sin(a)), 'y', 0.0055, 0.004, 'Alu', collection))
    else:
        # the hero row sits on the wheel box: two angle brackets bolted to its top
        for zz in (z0c + 0.06, z1c - 0.06):
            objs.append(BB.box(name + '_BoxBracket%.2f' % zz, (xa - 0.02, fy - 0.03, zz - 0.02), (xa + 0.02, fy + 0.005, zz + 0.02),
                               'SeatFrame', collection, bevel=0.003, segs=2))
    # wall bracket: a plate on the wall with two bolts, the frame tube runs into it
    wy = fy
    if wall_side != 0:
        objs += _wall_bracket(name, x0, x1, xw, wy, z0c, z1c, wall_side, fy, frame_s, collection)
    return _backrest(objs, name, x0, x1, cx, cy, back_z, double, lv, sides, small, hi, collection, wall_side)


def _wall_bracket(name, x0, x1, xw, wy, z0c, z1c, wall_side, fy, frame_s, collection):
    objs = []
    objs.append(BB.box(name + '_WallPlate', (xw - 0.006, wy - 0.05, (z0c + z1c) / 2 - 0.07),
                       (xw + 0.006, wy + 0.05, (z0c + z1c) / 2 + 0.07), 'SeatFrame', collection, bevel=0.004, segs=2))
    for dz in (-0.045, 0.045):
        objs.append(_hex_bolt(name + '_WallBolt%+.2f' % dz, (xw - wall_side * 0.008, wy, (z0c + z1c) / 2 + dz), 'x',
                              0.006, 0.005, 'Alu', collection))
    objs.append(C.sweep(name + '_WallArm', [(x1 - 0.06 if wall_side > 0 else x0 + 0.06, fy, (z0c + z1c) / 2),
                                           (xw - wall_side * 0.008, wy, (z0c + z1c) / 2)], 0.011, 'SeatFrame', collection,
                        sides=frame_s))
    return objs


def _sit_spots(x0, x1, double, wall_side):
    """where people sit: one dent per place; the window place is used a little less than the aisle one."""
    if not double:
        return [((x0 + x1) / 2, 1.0)]
    q = (x1 - x0) / 4
    xs = [x0 + q, x1 - q]
    if wall_side > 0:
        w = [1.0, 0.8]          # aisle on the -x side
    elif wall_side < 0:
        w = [0.8, 1.0]
    else:
        w = [1.0, 1.0]
    return list(zip(xs, w))


def _cushion(name, x0, x1, cx, cy, z0c, z1c, double, worn, wall_side, lv, small, collection):
    """a THIN bus cushion (7.5 cm): the top crowned, the front rolled over and tucked back under (the 'waterfall'
    edge of Fortepan 03), sat-in dents where people sit (Soviet foam goes flat in a few years)."""
    objs = []
    lo = (x0 + 0.018, cy - 0.075, z0c)
    hi_ = (x1 - 0.018, cy, z1c)
    hx, hy, hz = (hi_[0] - lo[0]) / 2, (hi_[1] - lo[1]) / 2, (hi_[2] - lo[2]) / 2
    ccx, ccz = (lo[0] + hi_[0]) / 2, (lo[2] + hi_[2]) / 2
    nmx = 11 if double else 7
    X = np.concatenate([[-hx, -hx + 0.016], np.linspace(-hx + 0.05, hx - 0.05, nmx), [hx - 0.016, hx]])
    Y = np.array([-hy, -hy + 0.014, 0.0, hy - 0.028, hy])
    Z = np.concatenate([[-hz, -hz + 0.016], np.linspace(-hz + 0.06, hz - 0.12, 6), [hz - 0.07, hz - 0.03, hz]])
    spots = _sit_spots(x0, x1, double, wall_side)

    def deform(face, i, j, k, x, y, z, half):
        ux, uz = x / half[0], z / half[2]
        fx, fz = 1 - min(1, ux * ux), 1 - min(1, uz * uz)
        if 'y+' in face or j == len(Y) - 2:
            top = 1.0 if 'y+' in face else 0.6
            y += 0.016 * fx * fz * top                                   # crown
            if 'y+' in face:
                for xs, w in spots:                                       # sat-in dents (behind the middle)
                    d = math.exp(-((x + ccx - xs) / 0.16) ** 2 - ((z + 0.04) / 0.15) ** 2)
                    y -= 0.016 * worn * w * d
        if 'z+' in face or k >= len(Z) - 3:                               # the front rolls over and tucks under
            t = min(max((y + half[1]) / (2 * half[1]), 0.0), 1.0)         # 0 bottom .. 1 top
            wz = {len(Z) - 1: 1.0, len(Z) - 2: 0.7, len(Z) - 3: 0.3}[k]
            z -= 0.034 * (1 - t) ** 1.5 * wz
            y -= 0.010 * t * wz                                           # the front edge is lower than the crown
        if 'x+' in face or 'x-' in face:
            ty = min(max((y + half[1]) / (2 * half[1]), 0.0), 1.0)
            x += math.copysign(0.004 * fz * math.sin(math.pi * ty), x)    # the boxing bulges a little
        return x, y, z

    cu = C.cage_pad(name + '_Cushion', lo, hi_, 'Vinyl', collection, lines=(X, Y, Z), deform=deform, levels=lv)
    objs.append(cu)
    # piping: a U round the two sides and the front, where the top panel meets the boxing (the back edge is under the
    # back), draped onto the cushion's actual surface (it follows the crown, the dents and the rolled front)
    xl, xr = lo[0] + 0.013, hi_[0] - 0.013          # (the subdivided surface sits ~1 cm inside the cage box)
    zf = hi_[2] - 0.040
    path = C.fillet_path([(xl, 0, z0c + 0.03), (xl, 0, zf), (xr, 0, zf), (xr, 0, z0c + 0.03)], 0.03, 6)
    path = C.drape(cu, [tuple(p) for p in C.resample(path, 0.02)], -0.0015)
    objs.append(C.sweep(name + '_CushionPiping', path, 0.0045, 'Vinyl', collection, sides=small))
    if double:   # the bench's middle seam: a sunk welt across the top
        seam = C.drape(cu, [(cx, 0, z) for z in np.linspace(z0c + 0.05, z1c - 0.03, 12)], -0.002)
        objs.append(C.sweep(name + '_CushionSeam', seam, 0.0035, 'Vinyl', collection, sides=small))
    return objs


def _backrest(objs, name, x0, x1, cx, cy, back_z, double, lv, sides, small, hi, collection, wall_side=1):
    """the back: a channel-stitched pad (three puffed horizontal bands, Soviet bus seats), piping round its front, a
    hard painted board on its rear with screws (the row behind gets its knees into it), the bent tube up the sides
    and over the top, and on the 672M a padded bumper sleeve on the tube's aisle-side top corner."""
    back = []
    bx0, bx1 = x0 + 0.036, x1 - 0.036                        # the bent tube runs outside these, along the sides
    bz0, bz1 = back_z + 0.012, back_z + 0.082
    y0b, y1b = cy - 0.01, cy + 0.585
    hxb, hyb, hzb = (bx1 - bx0) / 2, (y1b - y0b) / 2, (bz1 - bz0) / 2
    seams_y = [-hyb + 0.20, -hyb + 0.38]                     # two stitched channels -> three bands (lumbar wider)
    Yb = [-hyb, -hyb + 0.03]
    for sy in seams_y:
        Yb += [sy - 0.03, sy - 0.006, sy, sy + 0.006, sy + 0.03]
    Yb += [hyb - 0.06, hyb - 0.03, hyb]
    Yb = np.array(sorted(set(round(v, 5) for v in Yb)))
    nmx = 8 if double else 5
    Xb = np.concatenate([[-hxb, -hxb + 0.022], np.linspace(-hxb + 0.06, hxb - 0.06, nmx), [hxb - 0.022, hxb]])
    if double:
        Xb = np.array(sorted(set(list(np.round(Xb, 5)) + [-0.006, 0.0, 0.006])))
    Zb = np.array([-hzb, -hzb + 0.012, hzb - 0.016, hzb])

    def deform_b(face, i, j, k, x, y, z, half):
        if 'z+' in face or k == len(Zb) - 2:
            w = 1.0 if 'z+' in face else 0.4
            ux = x / half[0]
            fx = 1 - min(1, ux * ux)
            z += 0.012 * fx * w                                        # the bands puff forward
            for sy in seams_y:
                if abs(y - sy) < 1e-4:
                    z -= 0.014 * w                                     # the stitched channel pulls in
            if double and abs(x) < 1e-4:
                z -= 0.012 * w
        return x, y, z

    back.append(C.cage_pad(name + '_Back', (bx0, y0b, bz0), (bx1, y1b, bz1), 'Vinyl', collection,
                           lines=(Xb, Yb, Zb), deform=deform_b, levels=lv))
    # front piping round the pad's front edge
    zf = bz1 - 0.008
    pts = []
    hw2, hh = hxb - 0.004, hyb - 0.004
    ccy = (y0b + y1b) / 2
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx_, ccy_ = cx + sx * (hw2 - 0.03), ccy + sy * (hh - 0.03)
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            pts.append((ccx_ + 0.03 * math.cos(a), ccy_ + 0.03 * math.sin(a), zf))
    back.append(C.sweep(name + '_BackPiping', pts + [pts[0]], 0.0045, 'Vinyl', collection, sides=small, closed=True))
    # the rear: a 6 mm hard board, painted, screwed on (2 x 4 slotted round-head screws)
    back.append(BB.box(name + '_BackBoard', (bx0 + 0.006, y0b + 0.02, back_z), (bx1 - 0.006, y1b - 0.015, back_z + 0.012),
                       'SeatFrame', collection, bevel=0.003, segs=2))
    for yy in (y0b + 0.05, y1b - 0.045):
        for xx in np.linspace(bx0 + 0.04, bx1 - 0.04, 4 if not double else 6):
            back.append(BB.cylinder(name + '_Screw%.2f_%.2f' % (xx, yy), (xx, yy, back_z - 0.0008), 'z', 0.0045, 0.0022,
                                    'Alu', collection, segs=10 if not hi else 16, bevel=0.0008))
    # the bent tube: up both sides of the back and across the top (chrome, §4.2), with clamps to the back board
    # (Fortepan 03: the tube is in plain sight along both sides of the back and ~5 cm over its top)
    rz = back_z + 0.047
    ry_top = cy + 0.635
    xl, xr = x0 + 0.020, x1 - 0.020
    u_path = [(xl, cy - 0.02, rz), (xl, ry_top, rz), (xr, ry_top, rz), (xr, cy - 0.02, rz)]
    back.append(C.sweep(name + '_Rail', u_path, 0.011, 'Chrome', collection, sides=sides, bend=0.055, seg_per_90=10 if hi else 6))
    # 672M: a padded bumper sleeve (vinyl over foam, black) over the tube's aisle-side top corner
    ends = [] if wall_side == 0 and not double else ([xl] if wall_side > 0 else [xr] if wall_side < 0 else [xl, xr])
    for xe in ends:
        sg = 1 if xe < cx else -1
        sp = [(xe, ry_top - 0.14, rz), (xe, ry_top, rz), (xe + sg * 0.14, ry_top, rz)]
        back.append(C.sweep(name + '_Bumper%+d' % sg, sp, 0.019, 'Seal', collection, sides=sides, bend=0.055,
                            seg_per_90=10 if hi else 6))
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
