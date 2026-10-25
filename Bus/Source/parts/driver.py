# -*- coding: utf-8 -*-
"""D-36 A4 · 司机区：仪表台 1.0 m、方向盘和司机座 0.8–1.5 m，全片都在主座位的左前方。

照片和文字：`实物参考_PAZ细节/D07`（吉尔吉斯一辆废车的司机区：一整条横台、矩形仪表板、带状车速表、右边一个
圆表、一排拨杆开关、拉钮；方向盘大而细，缠着带棱的把套，三根扁辐条），Kolesa 试驾（仪表台和莫斯科人 412
的一样；发动机在司机右边，机罩被压凹；方向盘相对座椅偏右；车门是真空助力，司机用一个手柄开关），
1980 年使用手册的“操纵件”（只给链接）。圣经 §4.2：仪表台 #353637 纹理塑料 0.30（细橘皮），仪表微弱青绿发光、
**无数字**；方向盘 #2E2E2E 电木 0.45，握处 0.72；司机座同乙烯，最旧。

零件：
  - 仪表台：沿 x 扫出的圆角断面（台面、前缘鼓边、下垂面），不是直角盒；
  - 仪表板：方向盘后面一块倾斜的浅灰金属板 + 眉罩；带状车速表的长窗（刻线无数字，D-28 #4）、右边 Ø60 圆表、
    一排 4 个指示灯、5 个拨杆开关、2 个拉钮、钥匙孔；
  - 方向盘：Ø460 细轮缘（高模带把套的棱，低模靠法线）、三根扁辐条、中间喇叭按钮；转向柱 + 左边转向灯拨杆；
  - 三个踏板（离合、刹车、油门）、带橡胶护套的长变速杆、座位左边的手刹；
  - 真空门控手柄：仪表台右端一个扇形盒 + 拨杆（Kolesa：位置别扭）；
  - 发动机罩：司机右边，乙烯包面 + 三道绗缝，顶面被压凹；
  - 司机身后的隔板（Kolesa）：低于主座位眼高，不挡视窗（组装后 viewcheck）。
"""
import math

import numpy as np
from mathutils import Matrix, Vector

import build_bus as BB
import bus_spec as B
from parts import common as C
from parts import window as W


def _extrude_x(name, x0, x1, profile, m, collection, nseg=2):
    """a (y, z) profile swept straight along x (the dash): rails along x with depth axis = y, i axis = z."""
    rails = []
    for x in np.linspace(x0, x1, nseg + 1):
        rails.append((np.array([x, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])))
    return W.sweep_framed(name, rails, profile, m, collection, closed=False)


def dashboard(collection='Cabin', hi=False):
    objs = []
    z0, top = B.DASH_Z0, B.DASH_TOP
    ws = B.WS_BOT - 0.01
    # (y, z) cross-section: lower face down to the knee line, a rolled front edge, the shelf rising to the windscreen
    prof = W._round([(0.95, z0 + 0.03), (top - 0.055, z0 - 0.005), (top - 0.02, z0 - 0.012), (top + 0.005, z0 + 0.010),
                     (top + 0.012, z0 + 0.06), (ws, 3.40), (ws, 3.44), (0.95, 3.44)], 0.012, 3)
    objs.append(_extrude_x('Dash_Shelf', B.X_IN_L, B.X_IN_R, prof, 'Dash', collection, nseg=40))
    # knee panel under the shelf, left half (the driver's side), with a rolled lower lip
    prof2 = W._round([(B.FLOOR_Y + 0.02, z0 + 0.06), (0.95, z0 + 0.03), (0.95, 3.44), (B.FLOOR_Y + 0.02, 3.44)], 0.01, 2)
    objs.append(_extrude_x('Dash_Knee', B.X_IN_L, 0.56, prof2, 'Dash', collection, nseg=12))
    return objs


def instrument_panel(collection='Cabin', hi=False):
    """the cluster face behind the wheel: a tilted light-grey metal plate with a hood, ribbon speedo, a round gauge,
    lamps, toggles, knobs. Built flat in its own frame (u right, v up, w out toward the driver), then placed."""
    wx, wy, wz = B.WHEEL_C
    c = np.array([wx + 0.02, B.DASH_TOP + 0.035, B.DASH_Z0 - 0.002])
    tilt = math.radians(28)                                   # leaning back toward the windscreen
    u = np.array([1.0, 0.0, 0.0])
    v = np.array([0.0, math.cos(tilt), math.sin(tilt)])
    w = np.cross(u, v)
    if w[2] > 0:
        w = -w                                               # out toward the driver (-z)
    P = lambda a, b, d=0.0: tuple(c + u * a + v * b + w * d)
    objs = []

    def plate(name, a0, a1, b0, b1, d0, d1, m, bevel=0.003):
        return W._plate(name, np.array(P((a0 + a1) / 2, (b0 + b1) / 2, d0)), w, u, v, (a1 - a0) / 2, (b1 - b0) / 2,
                        d1 - d0, m, collection) if False else _oriented_box(name, P, a0, a1, b0, b1, d0, d1, m, collection, bevel)

    objs.append(plate('Cluster_Face', -0.23, 0.23, -0.075, 0.075, -0.012, 0.0, 'Alu', 0.004))
    objs.append(plate('Cluster_Hood', -0.25, 0.25, 0.070, 0.085, -0.012, 0.06, 'Dash', 0.006))
    # ribbon speedometer: a long window, a dark recess, a cream scale strip (graduations only), a red ribbon
    objs.append(plate('Speedo_Bezel', -0.17, 0.10, 0.005, 0.050, 0.0, 0.004, 'Chrome', 0.002))
    objs.append(plate('Speedo_Scale', -0.16, 0.09, 0.012, 0.043, 0.0, 0.0045, 'RadioDial', 0.0005))
    objs.append(plate('Speedo_Ribbon', -0.16, -0.08, 0.020, 0.026, 0.0, 0.0050, 'ButtonRed', 0.0003))
    objs.append(plate('Speedo_Glass', -0.165, 0.095, 0.008, 0.047, 0.0045, 0.0055, 'Glass', 0.001))
    # the round gauge (temperature / fuel), right
    objs.append(_disc('Gauge_Bezel', P(0.165, 0.025, 0.0), w, 0.033, 0.006, 'Chrome', collection, hi))
    objs.append(_disc('Gauge_Face', P(0.165, 0.025, 0.004), w, 0.028, 0.003, 'RadioDial', collection, hi))
    objs.append(_needle('Gauge_Needle', P(0.165, 0.025, 0.0075), u, v, w, 0.022, collection))
    # warning lamps (4), toggles (5), pull knobs (2), key slot
    for k in range(4):
        objs.append(_disc('Lamp%d' % k, P(-0.15 + 0.035 * k, -0.025, 0.0), w, 0.008, 0.005,
                          ('Lamp_Amber', 'ButtonRed', 'Lamp_Amber', 'Glass')[k], collection, hi))
    for k in range(5):
        a = -0.03 + 0.032 * k
        objs.append(_disc('ToggleBase%d' % k, P(a, -0.050, 0.0), w, 0.007, 0.004, 'Chrome', collection, hi))
        objs.append(_toggle('Toggle%d' % k, P(a, -0.050, 0.004), w, v, collection, down=(k % 2 == 0)))
    for k, a in enumerate((0.15, 0.19)):
        objs.append(_disc('KnobStem%d' % k, P(a, -0.05, 0.0), w, 0.004, 0.012, 'Chrome', collection, hi))
        objs.append(_disc('Knob%d' % k, P(a, -0.05, 0.012), w, 0.010, 0.010, 'Bakelite', collection, hi))
    objs.append(_disc('KeyBarrel', P(0.11, -0.05, 0.0), w, 0.011, 0.006, 'Chrome', collection, hi))
    return objs


def _oriented_box(name, P, a0, a1, b0, b1, d0, d1, m, collection, bevel):
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new(BB.U2B(P(a, b, d))) for d in (d0, d1) for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
    F = lambda *ix: bm.faces.new([vs[i] for i in ix])
    F(0, 3, 2, 1); F(4, 5, 6, 7); F(0, 1, 5, 4); F(1, 2, 6, 5); F(2, 3, 7, 6); F(3, 0, 4, 7)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=min(bevel, 0.45 * min(abs(a1 - a0), abs(b1 - b0), abs(d1 - d0))),
                        segments=2, affect='EDGES')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return C.finish(BB.obj_from_bm(name, bm, [m], collection), auto_smooth_deg=40)


def _disc(name, c, axis, r, t, m, collection, hi=False):
    return BB.cylinder(name, tuple(np.array(c) + np.array(axis) * t / 2), tuple(axis), r, t, m, collection,
                       segs=32 if hi else 20, bevel=min(0.0012, t * 0.3))


def _needle(name, c, u, v, w, L, collection):
    a = math.radians(40)
    d = u * math.cos(a) + v * math.sin(a)
    return C.sweep(name, [tuple(np.array(c)), tuple(np.array(c) + d * L)], 0.0011, 'ButtonRed', collection, sides=6)


def _toggle(name, c, w, v, collection, down=False):
    """a bat-handle toggle: a short lever from its bushing, tipped up or down."""
    d = w * math.cos(0.35) + v * (math.sin(0.35) * (-1 if down else 1))
    c = np.array(c)
    return C.sweep(name, [tuple(c), tuple(c + d * 0.016)], 0.0022, 'Chrome', collection, sides=8)


def steering(collection='Cabin', hi=False):
    """the big thin wheel: a 460 mm rim with a ribbed grip wrap (geometry on the high build, the normal map on the
    game mesh), three flat spokes, the horn boss; the column with its shroud and a turn-signal stalk."""
    wx, wy, wz = B.WHEEL_C
    tilt = math.radians(B.WHEEL_TILT)
    n = np.array([0.0, math.cos(tilt), -math.sin(tilt)])                # the wheel's axis (toward the driver, up)
    a1 = np.array([1.0, 0.0, 0.0])
    a2 = np.cross(n, a1)
    c = np.array([wx, wy, wz])
    R = B.WHEEL_RIM_R
    objs = []
    N = 96 if hi else 48
    ring = [tuple(c + R * (a1 * math.cos(t) + a2 * math.sin(t))) for t in np.linspace(0, 2 * math.pi, N, endpoint=False)]
    if hi:                       # the grip wrap: 140 ribs round the rim
        prof = []
        for k in range(24):
            ang = 2 * math.pi * k / 24
            prof.append((0.0125 * math.cos(ang), 0.0125 * math.sin(ang)))
        objs.append(C.sweep('Wheel_Rim', ring + [ring[0]], 0.0125, 'Bakelite', collection, sides=24, closed=True))
        for k in range(140):
            t = 2 * math.pi * k / 140
            p = c + R * (a1 * math.cos(t) + a2 * math.sin(t))
            tan = -a1 * math.sin(t) + a2 * math.cos(t)
            objs.append(BB.cylinder('Wheel_Rib%d' % k, tuple(p), tuple(tan), 0.0138, 0.0025, 'Bakelite', collection,
                                    segs=20, bevel=0.0009))
    else:
        objs.append(C.sweep('Wheel_Rim', ring + [ring[0]], 0.0130, 'Bakelite', collection, sides=16, closed=True))
    for k, deg in enumerate((180, 0, 270)):
        t = math.radians(deg)
        tip = c + (R - 0.008) * (a1 * math.cos(t) + a2 * math.sin(t))
        mid = c + 0.06 * (a1 * math.cos(t) + a2 * math.sin(t)) - n * 0.025       # dished toward the column
        flat = [(0.0035 * math.cos(q), 0.011 * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 16 if hi else 10, endpoint=False)]
        objs.append(C.sweep('Wheel_Spoke%d' % k, [tuple(mid), tuple(tip)], 0.01, 'Bakelite', collection, profile=flat))
    objs.append(BB.cylinder('Wheel_Boss', tuple(c - n * 0.03), tuple(n), 0.050, 0.04, 'Bakelite', collection,
                            segs=40 if hi else 24, bevel=0.008))
    objs.append(BB.cylinder('Wheel_Horn', tuple(c - n * 0.006), tuple(n), 0.034, 0.012, 'Chrome', collection,
                            segs=40 if hi else 24, bevel=0.004))
    col0 = c - n * 0.05
    col1 = np.array([wx, 0.80, wz + 0.30])
    objs.append(C.sweep('Wheel_Column', [tuple(col0), tuple(col1)], 0.028, 'Dash', collection, sides=20 if hi else 14))
    objs.append(C.sweep('Wheel_Shroud', [tuple(col0 - (col0 - col1) * 0.05), tuple(col0 - (col0 - col1) * 0.30)], 0.040,
                        'Dash', collection, sides=24 if hi else 16))
    sp = col0 - (col0 - col1) * 0.12
    objs.append(C.sweep('Wheel_Stalk', [tuple(sp), tuple(sp - a1 * 0.14 - n * 0.02)], 0.0045, 'Bakelite', collection,
                        sides=10))
    objs.append(BB.cylinder('Wheel_StalkTip', tuple(sp - a1 * 0.145 - n * 0.02), (1, 0, 0), 0.008, 0.03, 'Bakelite',
                            collection, segs=12, bevel=0.003))
    return objs


def pedals_and_levers(collection='Cabin', hi=False):
    wx, wy, wz = B.WHEEL_C
    objs = []
    fz = B.DASH_Z0 + 0.02
    for k, (dx, w_, h_) in enumerate(((-0.12, 0.07, 0.06), (0.0, 0.07, 0.06), (0.13, 0.05, 0.11))):
        x = wx + dx
        top = (x, 0.95, fz)
        pad_c = (x, B.FLOOR_Y + 0.17, fz - 0.19)
        objs.append(C.sweep('Pedal_Arm%d' % k, [top, (x, 0.80, fz - 0.10), pad_c], 0.008, 'SeatFrame', collection,
                            sides=10, bend=0.05))
        objs.append(BB.box('Pedal_Pad%d' % k, (x - w_ / 2, pad_c[1] - h_ / 2, pad_c[2] - 0.012),
                           (x + w_ / 2, pad_c[1] + h_ / 2, pad_c[2] + 0.004), 'Tyre', collection, bevel=0.006, segs=2))
    # gear lever: floor boot, a long bent rod, a black ball
    gx, gz = wx + 0.42, wz - 0.50
    objs.append(BB.cylinder('Gear_Boot', (gx, B.FLOOR_Y + 0.05, gz), 'y', 0.06, 0.10, 'Tyre', collection, segs=24, bevel=0.03))
    objs.append(C.sweep('Gear_Rod', [(gx, B.FLOOR_Y + 0.08, gz), (gx + 0.01, 0.85, gz - 0.04), (gx + 0.04, 1.12, gz - 0.12)],
                        0.010, 'Steel', collection, sides=12, bend=0.12))
    objs.append(BB.cylinder('Gear_Knob', (gx + 0.04, 1.14, gz - 0.12), 'y', 0.024, 0.04, 'Bakelite', collection,
                            segs=24, bevel=0.016))
    # handbrake left of the seat: a ratchet lever with a grip
    hx, hz = B.DRIVER_SEAT[0] - 0.30, B.DRIVER_SEAT[1] + 0.05
    objs.append(BB.box('Handbrake_Base', (hx - 0.03, B.FLOOR_Y, hz - 0.08), (hx + 0.03, B.FLOOR_Y + 0.06, hz + 0.08),
                       'SeatFrame', collection, bevel=0.01, segs=2))
    objs.append(C.sweep('Handbrake_Lever', [(hx, B.FLOOR_Y + 0.05, hz - 0.04), (hx, 0.90, hz + 0.10)], 0.012, 'SeatFrame',
                        collection, sides=12))
    objs.append(BB.cylinder('Handbrake_Grip', (hx, 0.93, hz + 0.115), (0, 0.35, 0.94), 0.017, 0.10, 'Tyre', collection,
                            segs=16, bevel=0.006))
    # the vacuum door control: a quadrant box on the dash's right end of the driver's reach, a lever with a ball
    qx, qy, qz = -0.42, B.DASH_TOP - 0.02, B.DASH_Z0 - 0.02
    objs.append(BB.box('DoorCtl_Box', (qx - 0.05, qy - 0.06, qz - 0.03), (qx + 0.05, qy + 0.01, qz + 0.02), 'SeatFrame',
                       collection, bevel=0.008, segs=3))
    objs.append(C.sweep('DoorCtl_Lever', [(qx, qy - 0.02, qz - 0.03), (qx + 0.05, qy + 0.06, qz - 0.10)], 0.006, 'Chrome',
                        collection, sides=10))
    objs.append(BB.cylinder('DoorCtl_Ball', (qx + 0.055, qy + 0.068, qz - 0.108), 'y', 0.016, 0.03, 'Bakelite', collection,
                            segs=20, bevel=0.012))
    return objs


def engine_cover(collection='Cabin', hi=False):
    """the doghouse right of the driver: a vinyl-covered hump with three quilted channels, dented on top
    (Kolesa: 'on many buses the cover is pressed in'), enamel plinth."""
    ex0, ex1, ez0, ez1, ey = B.ENGINE_COVER
    objs = [BB.box('EngineCover_Plinth', (ex0, B.FLOOR_Y, ez0), (ex1, B.FLOOR_Y + 0.06, ez1), 'Int_Enamel', collection,
                   bevel=0.01, segs=2)]
    hx, hy, hz = (ex1 - ex0) / 2, (ey - B.FLOOR_Y - 0.06) / 2, (ez1 - ez0) / 2
    seams = [-hz + (2 * hz) * f for f in (1 / 3, 2 / 3)]
    Z = [-hz, -hz + 0.04]
    for s in seams:
        Z += [s - 0.01, s, s + 0.01]
    Z += [hz - 0.04, hz]
    X = list(np.linspace(-hx, hx, 9 if hi else 5))
    X = [-hx, -hx + 0.05] + X[1:-1] + [hx - 0.05, hx]
    Y = [-hy, -hy + 0.03, hy - 0.06, hy]

    def deform(face, i, j, k, x, y, z, half):
        if 'y+' in face:
            fx = 1 - min(1, (x / half[0]) ** 2)
            fz = 1 - min(1, (z / half[2]) ** 2)
            y += 0.02 * fx * fz
            y -= 0.025 * math.exp(-((x + 0.06) / 0.10) ** 2 - ((z - 0.05) / 0.12) ** 2)      # the dent
            for s in seams:
                if abs(z - s) < 1e-5:
                    y -= 0.012
        return x, y, z

    lo = (ex0 + 0.01, B.FLOOR_Y + 0.06, ez0 + 0.01)
    hi_ = (ex1 - 0.01, ey, ez1 - 0.01)
    objs.append(C.cage_pad('EngineCover_Hood', lo, hi_, 'Vinyl', collection, lines=(sorted(set(np.round(X, 5))), Y,
                           sorted(set(np.round(Z, 5)))), deform=deform, levels=2 if hi else 1))
    return objs


def partition(collection='Cabin'):
    """the low board behind the driver (Kolesa) with a tube along its top. Kept below the hero's sight lines."""
    z = B.DRIVER_SEAT[1] - 0.42
    objs = [BB.box('DriverPartition', (B.X_IN_L + 0.01, B.FLOOR_Y, z - 0.008), (-0.56, 1.32, z + 0.008), 'Int_Enamel',
                   collection, bevel=0.004, segs=2)]
    objs.append(C.sweep('DriverPartition_Rail', [(B.X_IN_L + 0.01, 1.34, z), (-0.56, 1.34, z), (-0.56, B.FLOOR_Y + 0.01, z)],
                        0.014, 'Steel', collection, sides=16, bend=0.04))
    return objs


def driver_area(quality='low', collection='Cabin'):
    hi = quality == 'high'
    objs = []
    objs += dashboard(collection, hi)
    objs += instrument_panel(collection, hi)
    objs += steering(collection, hi)
    objs += pedals_and_levers(collection, hi)
    objs += engine_cover(collection, hi)
    objs += partition(collection)
    return objs
