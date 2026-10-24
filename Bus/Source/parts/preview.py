# -*- coding: utf-8 -*-
"""D-36 近景检查图：一个零件放在一段地板和墙前，按 VR 像素密度（Index ≈ 20 px/°：1280 px 宽 = 64° 水平视角）
从几个机位渲，和真车照片拼成一张对照板。

    ~/bpy/bin/python Bus/Source/parts/preview.py --part seat [--views a,b] [--samples 64] [--out /tmp/bus/parts]

光：两条管灯（1.2 × 0.12 m 面光，冷白 #E4F1F3），在座垫处约 E 0.6（和车厢光照图的标定一样），加很弱的环境。
乙烯用真实扫描的皮纹法线（Cabin_SeatLeather_N_0.30m，0.35），其余材质是 MAT_TABLE 的底色。这是看形的图，
不是最终的车厢光。
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
ROOT = os.path.normpath(os.path.join(SRC, '..', '..'))
sys.path.insert(0, SRC)
import build_bus as BB  # noqa: E402
import bus_spec as B  # noqa: E402
from parts import seat as SEAT  # noqa: E402

TEX = os.path.join(ROOT, 'Bus', 'Textures')
REF = os.path.join(ROOT, 'Bus', 'Docs~', '实物参考_车与车厢')


def lin(h):
    return BB.srgb2lin(h)


def detail_normal(m, img_name, tile_m, strength):
    nt = m.node_tree
    bs = nt.nodes.get('Principled BSDF')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / tile_m, 1 / tile_m, 1 / tile_m)
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = bpy.data.images.load(os.path.join(TEX, img_name))
    tx.image.colorspace_settings.name = 'Non-Color'
    tx.projection = 'BOX'
    tx.projection_blend = 0.3
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = strength
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], tx.inputs['Vector'])
    nt.links.new(tx.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])


def daylight(wall_x):
    """windows along the wall: a long bright panel just outside it (the wall gets a window cut) + a cool sky fill,
    so the comparison with the daylight reference photos is fair."""
    ld = bpy.data.lights.new('Window', 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = 0.75, 4.0
    ld.color = lin('#F2F4F6')
    ld.energy = 900.0
    lo = bpy.data.objects.new('Window', ld)
    lo.location = BB.U2B((wall_x + 0.4, 1.75, 0.6))
    lo.rotation_euler = (0, -1.5708 if wall_x > 0 else 1.5708, 0)
    bpy.context.scene.collection.objects.link(lo)
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 2.5
    sun.angle = 0.02
    so = bpy.data.objects.new('Sun', sun)
    so.rotation_euler = (0.9, 0.0, 2.2 if wall_x > 0 else -2.2)
    bpy.context.scene.collection.objects.link(so)


def stage(wall_x=1.0, floor=True, day=False, shell=False):
    if shell:     # the real bus shell is in the scene (windows): sky + sun outside, the tube lights inside
        sun = bpy.data.lights.new('Sun', 'SUN')
        sun.energy, sun.angle = 3.0, 0.02
        so = bpy.data.objects.new('Sun', sun)
        so.rotation_euler = (0.85, 0.0, 2.0)
        bpy.context.scene.collection.objects.link(so)
        w = bpy.data.worlds.new('W')
        w.use_nodes = True
        w.node_tree.nodes['Background'].inputs[0].default_value = (*lin('#BCCADB'), 1)
        w.node_tree.nodes['Background'].inputs[1].default_value = 1.2 if day else 0.02
        bpy.context.scene.world = w
        BB.box('PreviewGround', (-30, -0.02, -30), (30, 0.0, 30), 'Floor', 'Preview')
        return
    if floor:
        BB.box('PreviewFloor', (-1.5, B.FLOOR_Y - 0.02, -2.0), (1.5, B.FLOOR_Y, 3.0), 'Floor', 'Preview')
    if day:   # the wall below the sill, a window band (open), the wall above
        BB.box('PreviewWall', (wall_x, B.FLOOR_Y, -2.0), (wall_x + 0.02, 1.35, 3.0), 'Int_Enamel', 'Preview')
        BB.box('PreviewWallTop', (wall_x, 2.15, -2.0), (wall_x + 0.02, 2.6, 3.0), 'Int_Enamel', 'Preview')
        daylight(wall_x)
    else:
        BB.box('PreviewWall', (wall_x, B.FLOOR_Y, -2.0), (wall_x + 0.02, 2.6, 3.0), 'Int_Enamel', 'Preview')
    for k, x in enumerate((-0.73, 0.37)):
        ld = bpy.data.lights.new('Tube%d' % k, 'AREA')
        ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = 0.12, 1.2
        ld.color = lin('#E4F1F3')
        ld.energy = 40.0
        lo = bpy.data.objects.new('Tube%d' % k, ld)
        lo.location = BB.U2B((x, 2.58, 1.0))
        bpy.context.scene.collection.objects.link(lo)
        ld2 = ld.copy()
        lo2 = bpy.data.objects.new('Tube%db' % k, ld2)
        lo2.location = BB.U2B((x, 2.58, -0.4))
        bpy.context.scene.collection.objects.link(lo2)
    w = bpy.data.worlds.new('W')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (*lin('#30343A'), 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.35
    bpy.context.scene.world = w


def camera(eye, target, hfov=64.0, res=(1280, 720)):
    cd = bpy.data.cameras.new('Cam')
    cd.sensor_fit = 'HORIZONTAL'
    cd.angle = math.radians(hfov)
    cd.clip_start = 0.02
    ob = bpy.data.objects.new('Cam', cd)
    bpy.context.scene.collection.objects.link(ob)
    e, t = Vector(BB.U2B(eye)), Vector(BB.U2B(target))
    ob.location = e
    ob.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    sc = bpy.context.scene
    sc.camera = ob
    sc.render.resolution_x, sc.render.resolution_y = res
    return ob


def _window_scene():
    from parts import window as WIN
    body, glass = BB.build_body()
    BB.floor()
    objs = []
    for k, (z0, z1) in enumerate(B.WIN_R[:2]):
        objs += WIN.side_window('R', k + 1, z0, z1)
    return objs


def _poles_scene():
    body, glass = BB.build_body()
    BB.ceiling()
    BB.floor()
    before = set(bpy.data.objects)
    BB.poles_and_guard()
    return [o for o in bpy.data.objects if o not in before]


PARTS = {
    # name: (builder, views {view: (eye, target)}, reference photos)
    'poles': dict(
        build=_poles_scene, wall=None, shell=True,
        views={
            'aisle_2m': ((0.0, 1.65, 2.2), (-0.1, 1.55, -0.5)),             # down the aisle: stanchions + ceiling rails
            'flange_0.8m': ((0.02, 1.20, 1.55), (0.29, 0.64, 1.07)),       # the floor flange of the first pole
            'clamp_0.6m': ((0.10, 1.95, 0.70), (0.29, 2.30, 0.30)),        # a hanger clamp on the right ceiling rail
            'button_0.6m': ((-0.10, 1.55, 0.60), (0.29, 1.50, 1.07)),      # the stop button on the first right pole
        },
        refs=['车厢_03_Fortepan.jpg', '车厢_01_Fortepan.jpg'],
    ),
    'window': dict(
        build=_window_scene, wall=None, shell=True,
        views={
            'hero_61deg': ((0.55, 1.70, 2.05), (1.07, 1.60, 2.34)),       # the hero window, where the side poems sit
            'latch_0.4m': ((0.70, 2.02, 1.98), (1.02, 2.07, 1.93)),        # the sash latch and the transom
            'corner_0.5m': ((0.62, 1.55, 2.20), (1.05, 1.32, 2.50)),       # the frame corner, gasket and sill
            'row_2m': ((0.20, 1.70, -0.20), (1.00, 1.75, 1.40)),           # the side windows down the row
        },
        refs=['车厢_01_Fortepan.jpg', '车厢_02_Fortepan.jpg'],
    ),
    'seat': dict(
        build=lambda: SEAT.seat_module('SeatT', 0.31, 0.79, 1.0, double=False, wall_side=1, wall_x=0.99)
        + SEAT.seat_module('SeatD', -1.33, -0.43, 1.0, double=True, wall_side=-1, wall_x=-1.35)
        + SEAT.seat_module('SeatB', 0.31, 0.79, 0.28, double=False, wall_side=1, wall_x=0.99),
        wall=0.99,
        views={
            'overview_2m': ((-0.70, 1.75, 2.60), (0.20, 0.95, 0.90)),     # whole seats, for shape
            'back_0.7m': ((0.45, 1.70, 0.10), (0.55, 1.35, 0.80)),        # the seat back in front of you, 0.7 m
            'front34_1.0m': ((0.05, 1.45, 2.25), (0.60, 0.95, 1.40)),     # cushion + back from the front, 3/4
            'aisle_1.2m': ((-0.25, 1.20, 1.70), (0.55, 0.85, 1.25)),      # legs, foot, frame from the aisle
            'double_1.0m': ((-0.40, 1.50, 2.30), (-0.90, 0.95, 1.30)),    # the double seat
            'rail_0.5m': ((0.35, 1.75, 0.80), (0.60, 1.62, 1.05)),        # the grab rail and clamps up close
        },
        refs=['车厢_03_Fortepan.jpg', '车厢_01_Fortepan.jpg', '车厢_02_Fortepan.jpg'],
    ),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', default='seat')
    ap.add_argument('--views', default='')
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--out', default='/tmp/bus/parts')
    ap.add_argument('--light', default='day', choices=['day', 'tubes'])
    ap.add_argument('--flat', action='store_true', help='MAT_TABLE colours only (no detail materials)')
    a = ap.parse_args()
    P = PARTS[a.part]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    objs = P['build']()
    stage(P['wall'], day=a.light == 'day', shell=P.get('shell', False))
    if not a.flat:
        from parts import materials as MATS
        MATS.apply_details(objs)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects
               if o.type == 'MESH' and not o.name.startswith('Preview'))
    os.makedirs(a.out, exist_ok=True)
    views = [v for v in P['views'] if not a.views or v in a.views.split(',')]
    outs = []
    for v in views:
        eye, tgt = P['views'][v]
        cam = camera(eye, tgt)
        sc.render.filepath = os.path.join(a.out, '%s_%s_%s.png' % (a.part, v, a.light))
        bpy.ops.render.render(write_still=True)
        outs.append(sc.render.filepath)
        bpy.data.objects.remove(cam, do_unlink=True)
    json.dump(dict(part=a.part, tris_in_scene=tris, views=outs, refs=P['refs']),
              open(os.path.join(a.out, '%s.json' % a.part), 'w'), ensure_ascii=False, indent=1)
    print('[parts] %s: %d tris in the preview scene, %d views -> %s' % (a.part, tris, len(outs), a.out))


if __name__ == '__main__':
    main()
