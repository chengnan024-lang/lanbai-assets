# -*- coding: utf-8 -*-
"""紫贝阙预览：~/bpy/bin/python kit/preview_que.py [--lod 0] [--shots a,b] [--res 480] [--spp 16]
渲到 /tmp/pal/kit_que/*.png（灰模 + 槽位的大致颜色，一盏太阳 + 环境光；台地上表面 y = 0、边缘 x = −8、下缘 y = −13）。"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import bl  # noqa: E402
from kit import que  # noqa: E402
from kit.common import UB  # noqa: E402

SLOT_RGB = {'Lacquer': '#A3201E', 'LacquerBlack': '#1A1210', 'LacquerBand': '#3A1814', 'Gilt': '#C8A040', 'Bronze': '#8C6A3A',
            'Verdigris': '#4F8A78', 'Stone': '#9A958A', 'StoneDark': '#55524C', 'FishScale': '#D9D6E2', 'Cowrie': '#6B4252',
            'Tile': '#5A5A58', 'Wood': '#4A3426', 'Rock': '#4C4A46', 'Weed': '#3F5A2A', 'Fish': '#B0B0B0', 'DoorGlow': '#FFB74D'}


def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def materials():
    M = {}
    for s, h in SLOT_RGB.items():
        m = bpy.data.materials.new('M_07b_' + s)
        m.use_nodes = True
        p = m.node_tree.nodes['Principled BSDF']
        p.inputs['Base Color'].default_value = (*lin(h), 1)
        p.inputs['Roughness'].default_value = {'Lacquer': 0.35, 'LacquerBlack': 0.35, 'Gilt': 0.3, 'Cowrie': 0.2, 'FishScale': 0.25}.get(s, 0.75)
        if s in ('Gilt', 'Bronze'):
            p.inputs['Metallic'].default_value = 1.0
        M[s] = m
    return M


def scene_setup(res, spp):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = spp
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 4
    sc.render.resolution_x, sc.render.resolution_y = res, int(round(res * 9 / 16))
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
    w = bpy.data.worlds.new('W')
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (*lin('#6F8496'), 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.55
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 3.2
    sun.angle = math.radians(4)
    o = bpy.data.objects.new('Sun', sun)
    d = bl.Vector(bl.u2b((-0.55, -0.75, 0.35)))       # 光从 +x、上、略偏后照来（车那一侧）
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(o)


def look(eye, target):
    d = np.asarray(target, float) - np.asarray(eye, float)
    return math.degrees(math.atan2(d[0], d[2])), math.degrees(math.atan2(d[1], math.hypot(d[0], d[2])))


SHOTS = {
    # 名: (eye, yaw, pitch, hfov)
    'fwd': ((0, 4.2, 30), -38, 24, 100),             # 从车上往前（偏左）看两阙
    'left': ((0, 4.2, 41), -90, 12, 95),             # 向左看右阙 +x 面（近景，阙基 / 阙身下部）
    'left_up': ((0, 4.2, 41), -90, 52, 95),          # 同一处抬头看阙楼 / 阙顶
    'under': ((0, -14, 60),) + look((0, -14, 60), (-18, 22, 41.39)) + (75,),
    'top': ((6, 31, 22),) + look((6, 31, 22), (-12, 31, 41.39)) + (60,),
    'ridge': ((2, 39.5, 41.39),) + look((2, 39.5, 41.39), (-12, 38.5, 41.39)) + (40,),
    'overview': ((22, 12, 0),) + look((22, 12, 0), (-18, 20, 41.39)) + (55,),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lod', type=int, default=0)
    ap.add_argument('--shots', default='fwd,left,left_up,under,overview')
    ap.add_argument('--res', type=int, default=480)
    ap.add_argument('--spp', type=int, default=16)
    ap.add_argument('--out', default='/tmp/pal/kit_que')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    os.makedirs(a.out, exist_ok=True)
    bl.reset()
    M = materials()
    scene_setup(a.res, a.spp)
    u = que.build(a.lod)
    print('que lod%d tris %d' % (a.lod, u.tris()))
    u.build('Que', materials=M)
    t = UB()                                          # 台地（上表面 + 边缘岩壁）
    t.box((-90, -13, -40), (-8, 0, 140), 'Rock')
    t.build('Terrace', materials=M)
    for s in a.shots.split(','):
        eye, yaw, pitch, hfov = SHOTS[s]
        cam = bl.camera_unity('Cam_' + s, eye, yaw, pitch, hfov)
        bpy.context.scene.camera = cam
        bpy.context.scene.render.filepath = os.path.join(a.out, '%s_lod%d.png' % (s, a.lod))
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
