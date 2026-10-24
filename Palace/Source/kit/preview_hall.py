# -*- coding: utf-8 -*-
"""预览大殿：~/bpy/bin/python kit/preview_hall.py [--lod 0] [--out /tmp/pal/kit_hall] [--res 480] [--spp 16]
灰模 + 槽位大致颜色，太阳 + 环境光 + 门里的暖光，渲 3 张：front / q34 / low。"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hall  # noqa: E402

COL = {'Lacquer': '#A3201E', 'LacquerBlack': '#1A1210', 'LacquerBand': '#4A1A14', 'Gilt': '#D4A64A',
       'Bronze': '#8C6A3A', 'Stone': '#8E887C', 'StoneDark': '#B8AC94', 'Tile': '#5A5A58', 'Wood': '#3B2A1E',
       'DoorGlow': '#FFB74D'}


def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def u2b(p):
    return Vector((-p[0], -p[2], p[1]))


def materials():
    M = {}
    for k, h in COL.items():
        m = bpy.data.materials.new('M_07b_' + k)
        m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = lin(h)
        b.inputs['Roughness'].default_value = 0.35 if k in ('Lacquer', 'LacquerBlack', 'LacquerBand', 'Gilt') else 0.8
        if k == 'Gilt':
            b.inputs['Metallic'].default_value = 1.0
        if k == 'DoorGlow':
            b.inputs['Emission Color'].default_value = lin(h)
            b.inputs['Emission Strength'].default_value = 6.0
        M[k] = m
    return M


def look(name, eye, target, lens=24):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 2000
    o = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(o)
    e, t = u2b(eye), u2b(target)
    o.location = e
    o.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    return o


SHOTS = {
    'front': ((-38.0, 4.0, 300.0), (-38.0, 19.5, 350.0), 20),
    'q34': ((12.0, 22.0, 298.0), (-38.0, 15.0, 352.0), 26),
    'low': ((0.0, -15.0, 307.0), (-28.0, 14.0, 345.0), 22),
    'door': ((-14.0, 8.0, 322.0), (-19.0, 11.0, 342.0), 30),
    'eave': ((-58.0, 7.6, 331.0), (-66.0, 16.0, 339.0), 18),
    'rend': ((-17.0, 37.5, 343.0), (-23.9, 35.0, 354.7), 30),
    'ridge': ((-8.0, 42.0, 330.0), (-26.0, 36.0, 354.0), 35),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lod', type=int, default=0)
    ap.add_argument('--out', default='/tmp/pal/kit_hall')
    ap.add_argument('--res', type=int, default=480)
    ap.add_argument('--spp', type=int, default=16)
    ap.add_argument('--shots', default='front,q34,low')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    M = materials()
    ub = hall.build(a.lod)
    print('tris', ub.tris())
    ub.build('Hall', materials=M)
    # 世界 + 太阳 + 门洞暖光
    w = bpy.data.worlds.new('W')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = lin('#3A5A78')
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.6
    sc.world = w
    sd = bpy.data.lights.new('Sun', 'SUN')
    sd.energy = 3.0
    so = bpy.data.objects.new('Sun', sd)
    so.rotation_euler = (math.radians(50), 0, math.radians(200))
    sc.collection.objects.link(so)
    pd = bpy.data.lights.new('Fill', 'SUN')
    pd.energy = 0.8
    po = bpy.data.objects.new('Fill', pd)
    po.rotation_euler = (math.radians(110), 0, math.radians(20))   # 从下往上补一点，看底面
    sc.collection.objects.link(po)
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = a.spp
    sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 4
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = a.res, int(round(a.res * 9 / 16))
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX' if 'AgX' in [x.identifier for x in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    for s in a.shots.split(','):
        eye, tgt, lens = SHOTS[s]
        sc.camera = look('Cam_' + s, eye, tgt, lens)
        sc.render.filepath = os.path.join(a.out, '%s_lod%d.png' % (s, a.lod))
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
