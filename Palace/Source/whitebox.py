# -*- coding: utf-8 -*-
"""白模：按 palace_layout 摆盒子，看构图与尺度。所有尺寸按 Unity 宫殿坐标写，进 Blender 时用 u2b 换算。
~/bpy/bin/python whitebox.py --shots F7,F5p --res 960 --spp 32 --out /tmp/pal/wb"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import bl  # noqa: E402
import palace_layout as L  # noqa: E402
from grade import srgb_to_lin  # noqa: E402
from shots import SHOTS, NO_BUS  # noqa: E402

Y0 = L.SHINDAO_Y
LIP_Y = 1.70 - L.LIP_DROP


class UB:
    """在 Unity 坐标里攒盒子 / 棱柱，建成 Blender 物体。"""

    def __init__(self):
        self.mb = bl.MeshBuilder()

    def box(self, lo, hi, mi=0):
        V, F = bl.box_vf(lo, hi)
        self.add(V, F, mi)

    def add(self, V_u, F, mi=0):
        V = (bl.U2B @ np.asarray(V_u, float).T).T
        F = [tuple(reversed(f)) for f in F]          # 反射换算会翻转绕向
        self.mb.add(V, F, mi)

    def hip_roof(self, x0, x1, z0, z1, y0, h, mi=0):
        """四阿顶（直坡）：檐口矩形 (x0..x1, z0..z1) 在 y0，脊高 h，脊沿长边。"""
        w, d = x1 - x0, z1 - z0
        if w >= d:
            r = d / 2
            V = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (x0 + r, y0 + h, (z0 + z1) / 2), (x1 - r, y0 + h, (z0 + z1) / 2)]
            F = [(0, 1, 5, 4), (2, 3, 4, 5), (3, 0, 4), (1, 2, 5), (0, 3, 2, 1)]
        else:
            r = w / 2
            V = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), ((x0 + x1) / 2, y0 + h, z0 + r), ((x0 + x1) / 2, y0 + h, z1 - r)]
            F = [(0, 1, 4), (2, 3, 5), (3, 0, 4, 5), (1, 2, 5, 4), (0, 3, 2, 1)]
        self.add(V, [tuple(reversed(f)) for f in F], mi)

    def build(self, name, mats, col=None):
        return self.mb.build(name, mats, col)


def lin(h):
    return tuple(srgb_to_lin(h))


def build_scene():
    sc = bl.reset()
    M = {
        'stone': bl.principled('stone', lin('#3B3F3A'), 0.7),
        'rock': bl.principled('rock', lin('#33362F'), 0.85),
        'lacq': bl.principled('lacq', lin('#A3201E'), 0.25),
        'black': bl.principled('black', lin('#282426'), 0.3),
        'roof': bl.principled('roof', lin('#4A4C48'), 0.6),
        'nacre': bl.principled('nacre', lin('#CFCBC4'), 0.14),
        'cowrie': bl.principled('cowrie', lin('#5B2A4E'), 0.08),
        'bronze': bl.principled('bronze', lin('#BA926A'), 0.45, 1.0),
        'bus': bl.principled('bus', lin('#3A3D42'), 0.6),
        'seat': bl.principled('seat', lin('#5A2126'), 0.5),
    }
    # ---------------- 台地（神道面、崖、下缘之下的内收）
    t = UB()
    zA, zB = -460.0, 160.0
    t.box((-170, LIP_Y, zA), (L.EDGE_X, Y0, zB))                        # 神道这一段的台地，到下缘
    t.box((L.EDGE_X, LIP_Y, L.PROMONTORY_Z), (50, Y0, zB))              # 托住大殿的伸出部分
    t.box((-170, -320, zA), (L.EDGE_X - 14, LIP_Y, zB))                # 下缘之下内收 14 m
    t.box((L.EDGE_X - 14, -320, L.PROMONTORY_Z + 14), (36, LIP_Y, zB))
    t.build('Plateau', [M['rock']])
    # ---------------- 灯（两列 12 + 台基 6）
    lamps = []
    for z in L.lamp_z():
        lamps += [(L.COL_R_X, z), (L.COL_L_X, z)]
    lm = UB()
    for x, z in lamps:
        lm.box((x - 0.35, Y0, z - 0.35), (x + 0.35, Y0 + 0.25, z + 0.35))
        lm.box((x - 0.12, Y0, z - 0.12), (x + 0.12, Y0 + 1.5, z + 0.12))
        lm.box((x - 0.3, Y0 + 1.5, z - 0.3), (x + 0.3, Y0 + 2.0, z + 0.3))
    pod_top = Y0 + L.PODIUM_H
    pod_z0 = L.DOOR_Z - 12.0
    pod_lamps = [(x, pod_z0 + 1.0) for x in (-43, -33, -23, -13, -3, 7)]
    for x, z in pod_lamps:
        lm.box((x - 0.12, pod_top, z - 0.12), (x + 0.12, pod_top + 1.5, z + 0.12))
        lm.box((x - 0.3, pod_top + 1.5, z - 0.3), (x + 0.3, pod_top + 2.0, z + 0.3))
    lm.build('Lamps', [M['bronze']])
    # ---------------- 紫贝阙一对（宽 7 m、深 12 m，缝 4 m）
    qz = L.que_z()
    q = UB()
    for (xa, xb) in [(-16.0, -9.0), (-27.0, -20.0)]:
        h = Y0
        q.box((xa - 1, h, qz - 7), (xb + 1, h + 3.2, qz + 7), 0)                      # 阙基
        q.box((xa, h + 3.2, qz - 6), (xb, h + 22.0, qz + 6), 1)                       # 阙身（宝贝贴面）
        q.box((xa - 1.2, h + 22.0, qz - 7.2), (xb + 1.2, h + 25.2, qz + 7.2), 2)      # 枋头层
        q.box((xa - 2.0, h + 25.2, qz - 8.0), (xb + 2.0, h + 30.8, qz + 8.0), 2)      # 斗拱层
        q.hip_roof(xa - 3.5, xb + 3.5, qz - 9.5, qz + 9.5, h + 30.8, 3.0, 3)          # 下檐
        q.box((xa - 0.8, h + 33.0, qz - 6.8), (xb + 0.8, h + 34.5, qz + 6.8), 2)
        q.hip_roof(xa - 2.0, xb + 2.0, qz - 8.0, qz + 8.0, h + 34.5, 5.5, 3)          # 上檐，到 40 m
    q.box((-34.0, Y0, qz - 5), (-27.0, Y0 + 3.0, qz + 5), 0)                         # 左阙的子阙（外侧）
    q.box((-33.5, Y0 + 3, qz - 4.5), (-27.0, Y0 + 15.0, qz + 4.5), 1)
    q.hip_roof(-36.0, -26.0, qz - 6.5, qz + 6.5, Y0 + 15.0, 7.6, 3)
    q.box((-8.0, Y0 - 16.0, qz - 4.5), (-4.5, Y0 + 2.0, qz + 4.5), 1)                # 右阙的子阙：贴着崖壁往下长
    q.hip_roof(-9.0, -3.5, qz - 6.0, qz + 6.0, Y0 + 2.0, 3.5, 3)
    q.build('Que', [M['stone'], M['cowrie'], M['lacq'], M['roof']])
    # ---------------- 台基 + 大殿（九间，正中一间开门）
    p = UB()
    xa, xb = -63.0, 27.0
    p.box((xa, Y0, pod_z0), (xb, pod_top, pod_z0 + 52), 0)
    for k in range(16):                                                  # 阶（左墄）
        p.box((-32, Y0 + k * 6.0 / 16, pod_z0 - 12 + k * 0.75), (-24, Y0 + (k + 1) * 6.0 / 16, pod_z0), 0)
    V = [(-16, Y0, pod_z0 - 14), (-10, Y0, pod_z0 - 14), (-10, pod_top, pod_z0), (-16, pod_top, pod_z0),
         (-16, Y0, pod_z0), (-10, Y0, pod_z0)]
    p.add(V, [(0, 1, 2, 3), (1, 5, 2), (0, 3, 4)], 0)                    # 坡（右平）
    hx0, hx1 = L.AXIS_X - L.HALL_W / 2, L.AXIS_X + L.HALL_W / 2
    zf, zb = L.DOOR_Z, L.DOOR_Z + 26.0
    bay = L.HALL_W / 9
    for i in range(10):
        x = hx0 + i * bay
        p.box((x - 0.55, pod_top, zf - 4.0 - 0.55), (x + 0.55, pod_top + 9.0, zf - 4.0 + 0.55), 1)    # 前檐柱
    p.box((hx0, pod_top + 9.0, zf - 4.6), (hx1, pod_top + 10.4, zb), 1)                          # 额枋 + 斗拱层
    dl, dr = L.AXIS_X - 2.5, L.AXIS_X + 2.5
    p.box((hx0, pod_top, zf), (dl, pod_top + 9.0, zf + 0.8), 1)                                    # 前墙（门两侧）
    p.box((dr, pod_top, zf), (hx1, pod_top + 9.0, zf + 0.8), 1)
    p.box((dl, pod_top + 8.0, zf), (dr, pod_top + 9.0, zf + 0.8), 1)                              # 门楣
    p.box((hx0, pod_top, zb - 0.8), (hx1, pod_top + 9.0, zb), 1)
    p.box((hx0, pod_top, zf), (hx0 + 0.8, pod_top + 9.0, zb), 1)
    p.box((hx1 - 0.8, pod_top, zf), (hx1, pod_top + 9.0, zb), 1)
    p.hip_roof(hx0 - 4.5, hx1 + 4.5, zf - 9.0, zb + 4.5, pod_top + 10.4, 6.0, 2)                 # 下檐
    p.box((hx0 + 3, pod_top + 14.0, zf - 1.0), (hx1 - 3, pod_top + 17.0, zb - 3.0), 1)          # 上层
    p.hip_roof(hx0 - 1.0, hx1 + 1.0, zf - 5.0, zb + 1.0, pod_top + 17.0, 13.0, 2)                # 上檐，脊到 30 m
    p.box((dl, pod_top, zf + 6.0), (dr, pod_top + 8.0, zf + 6.3), 3)                               # 门里的暖光（屏）
    p.build('Hall', [M['stone'], M['lacq'], M['roof'], M['black']])
    door = bl.emissive('doorglow', tuple(np.array(lin('#FFB74D')) * 3.0))
    dg = UB()
    dg.box((dl + 0.1, pod_top + 0.01, zf + 0.85), (dr - 0.1, pod_top + 7.9, zf + 5.9))
    o = dg.build('DoorGlow', [door])
    o.pass_index = 2
    o.lightgroup = 'doorglow'
    o.visible_diffuse = o.visible_glossy = o.visible_transmission = o.visible_volume_scatter = False
    o.visible_shadow = False
    # ---------------- 鱼鳞屋 24 座（神道另一侧两排）
    hs = UB()
    lz = L.lamp_z()
    for row, (xc, yb) in enumerate([(-38.0, Y0), (-53.0, Y0 + 2.5)]):
        for i, z in enumerate(lz):
            zc = z + 9.0 * (1 if row == 0 else -1) + (0 if row == 0 else 4)
            w, d, hh = 9.0, 7.5, 6.0
            if yb > Y0:
                hs.box((xc - w / 2 - 1, Y0, zc - d / 2 - 1), (xc + w / 2 + 1, yb, zc + d / 2 + 1), 0)
            hs.box((xc - w / 2, yb, zc - d / 2), (xc + w / 2, yb + hh, zc + d / 2), 0)
            hs.hip_roof(xc - w / 2 - 1.5, xc + w / 2 + 1.5, zc - d / 2 - 1.5, zc + d / 2 + 1.5, yb + hh, 4.0, 1)
    hs.build('Houses', [M['stone'], M['nacre']])
    # ---------------- 车（主座位视角的壳）
    b = UB()
    FZ, HW, FY, CY = 3.35, 1.04, 0.62, 2.45
    b.box((-HW, FY - 0.1, -7.0), (HW, FY, FZ + 0.15))                     # 地板
    b.box((-HW, FY, FZ - 0.35), (HW, 1.36, FZ + 0.15))                    # 仪表台
    b.box((-HW, 2.24, FZ - 0.25), (HW, CY + 0.1, FZ + 0.15))              # 前沿（目的地牌）
    for sx in (-1, 1):
        b.box((sx * HW - 0.07, FY, FZ - 0.05), (sx * HW + 0.07, CY, FZ + 0.15))   # A 柱
    b.box((-HW, CY, -7.0), (HW, CY + 0.1, 2.5))                           # 顶（天窗在 2.5–3.1）
    b.box((-HW, CY, 3.1), (HW, CY + 0.1, FZ + 0.15))
    b.box((-HW, CY, 2.5), (0.25, CY + 0.1, 3.1))
    b.box((0.85, CY, 2.5), (HW, CY + 0.1, 3.1))
    b.box((-HW - 0.05, FY, -7.0), (-HW, 1.30, FZ))                        # 左侧墙下半
    b.box((HW, FY, -7.0), (HW + 0.05, 1.30, 1.4))                         # 右侧墙下半（门在 1.4–3.3）
    for z in (-6.0, -4.8, -3.6, -2.4, -1.2, 0.0, 1.2):
        b.box((-HW - 0.05, 1.30, z - 0.06), (-HW + 0.02, CY, z + 0.06))
        b.box((HW - 0.02, 1.30, z - 0.06), (HW + 0.05, CY, z + 0.06))
    b.box((-HW - 0.05, 2.12, -7.0), (-HW + 0.02, CY, FZ))
    b.box((HW - 0.02, 2.12, -7.0), (HW + 0.05, CY, FZ))
    b.box((1.38, FY, 1.4), (1.42, CY, 1.46))
    bus = b.build('Bus', [M['bus']])
    s = UB()
    s.box((-0.80, FY, 2.25), (-0.30, 1.10, 2.75))                         # 空着的司机座
    s.box((-0.80, 1.10, 2.25), (-0.30, 1.75, 2.35))
    s.box((-0.80, 0.95, 2.80), (-0.30, 1.0, 3.0))
    seats = s.build('Seats', [M['seat']])
    return {'bus': [bus, seats], 'lamps': lamps, 'pod_lamps': pod_lamps}


def add_lights(info, warm_I=5.46, indigo_I=1.93):
    for i, (x, z) in enumerate(info['lamps'] + info['pod_lamps']):
        y = (Y0 + L.LAMP_FLAME_H) if i < len(info['lamps']) else (Y0 + L.PODIUM_H + L.LAMP_FLAME_H)
        a = bl.point_light_unity('Lw%02d' % i, (x, y, z), lin('#FF9C2F'), warm_I, 4.0, radius=0.12)
        a.lightgroup = 'warm'
        b = bl.point_light_unity('Li%02d' % i, (x, y, z), lin('#2A557B'), indigo_I, 12.0, radius=0.12)
        b.lightgroup = 'indigo'
    # 门溢出的暖光：门洞里一盏烘焙面光（宽 5、高 8，朝外）
    A = bpy.data.lights.new('DoorSpill', 'AREA')
    A.shape = 'RECTANGLE'
    A.size, A.size_y = 4.8, 7.8
    A.color = lin('#FFB74D')
    A.energy = 2500.0
    o = bpy.data.objects.new('DoorSpill', A)
    o.location = bl.Vector(bl.u2b((L.AXIS_X, Y0 + L.PODIUM_H + 4.0, L.DOOR_Z + 1.0)))
    o.rotation_euler = bl.Vector(bl.u2b((0, 0, -1))).to_track_quat('-Z', 'Y').to_euler()
    o.lightgroup = 'door'
    bpy.context.scene.collection.objects.link(o)


def setup_world():
    w = bl.world_trilight(lin('#0E3050'), lin('#0A2238'), lin('#1A1422'))
    w.lightgroup = 'amb'
    vl = bpy.context.scene.view_layers[0]
    for g in ('amb', 'warm', 'indigo', 'door', 'doorglow'):
        if g not in vl.lightgroups:
            vl.lightgroups.add(name=g)


def render_shot(name, out, res, spp, bus_visible=True):
    t, yaw, pitch, hfov, _ = SHOTS[name]
    e = L.eye(t)
    sc = bpy.context.scene
    # 宫殿坐标里车在动：把车壳放到车的位置
    car = L.car(t)
    for o in bpy.data.objects:
        if o.name in ('Bus', 'Seats'):
            o.location = bl.Vector(bl.u2b(car))
            o.hide_render = not bus_visible
    cam = bl.camera_unity('Cam_' + name, e, yaw, pitch, hfov)
    sc.camera = cam
    bl.render_setup(res, int(round(res * 9 / 16)), spp)
    sc.render.filepath = os.path.join(out, name + '.exr')
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default='F7')
    ap.add_argument('--res', type=int, default=960)
    ap.add_argument('--spp', type=int, default=32)
    ap.add_argument('--out', default='/tmp/pal/wb')
    ap.add_argument('--save-blend', default='')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    os.makedirs(a.out, exist_ok=True)
    info = build_scene()
    setup_world()
    add_lights(info)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
    for s in a.shots.split(','):
        render_shot(s, a.out, a.res, a.spp, bus_visible=s not in NO_BUS)
