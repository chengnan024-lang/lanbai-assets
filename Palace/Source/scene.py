# -*- coding: utf-8 -*-
"""宫殿参考场景：读 palace_layout（= 海的约定），用 kit/ 的模块建几何，材质 materials.py，烘焙灯按 Unity 的衰减，
灯组分开（post.py 里调强度不重渲），车壳 = 渲染标准台的 bible_v2（D-28：paz672 来之前）。
~/bpy/bin/python scene.py --shots F7,F5p --res 960 --spp 48 --out /tmp/pal/r01"""
import argparse
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Engineering', 'render_harness'))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import bl  # noqa: E402
import materials  # noqa: E402
import palace_layout as L  # noqa: E402
from kit import fish, lamp, terrace, weed  # noqa: E402
from kit.common import UB  # noqa: E402

PARAMS = dict(warm_I=5.46, warm_r=4.0, indigo_I=4.0, indigo_r=12.0, door_W=900.0)


def try_kit(name):
    try:
        return importlib.import_module('kit.' + name)
    except Exception as e:  # 模块还没交
        print('kit.%s 不可用：%s' % (name, e))
        return None


def place(ub, pos, yaw_deg=0.0):
    a = math.radians(yaw_deg)
    R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])   # Unity 绕 y（左手系，正 = 从上看顺时针）
    return ub.transformed(R, pos)


def build(t_fish=748.26, lod_far=False):
    sc = bl.reset()
    M = materials.build_all()
    col = bpy.data.collections.new('Palace')
    sc.collection.children.link(col)
    # 台地 + 海草
    terrace.build().build('Terrace', col, M)
    w, sway = weed.build(L.WEEDS)
    w.build('Weeds', col, M)
    # 灯
    lu = UB()
    for l in L.LAMPS:
        yaw = 0.0
        lu.merge(place(lamp.build(l['height_m']), l['pos'], yaw))
    lu.build('Lamps', col, M)
    # 大殿、阙、鱼鳞屋（模块没交时用白模盒子）
    hall = try_kit('hall')
    if hall:
        hall.build().build('Hall', col, M)
    que = try_kit('que')
    if que:
        que.build().build('Que', col, M)
    house = try_kit('house')
    hu = UB()
    for i, h in enumerate(L.HOUSES):
        wdt, hh, dep = h['size']
        if house:
            m = house.build(wdt, hh, dep, seed=i)
        else:
            m = UB()
            m.box((-wdt / 2, 0, -dep / 2), (wdt / 2, hh, dep / 2), 'StoneDark')
        hu.merge(place(m, h['pos'], h['yaw_deg'] + 180.0))     # 模块正面朝 −z；转到朝神道（+x）
    hu.build('Houses', col, M)
    # 门里的光（若大殿模块没有 DoorGlow 槽，补一块）
    for ob in col.objects:
        if 'M_07b_DoorGlow' in [m.name for m in ob.data.materials]:
            pass
    # 鱼
    poem = poem_point()
    fu = fish.place(t_fish, L.FISH['centre'], poem)
    if fu.V:
        fu.build('Fish', col, M)
    split_doorglow(col, M)
    return M


def poem_point():
    e = L.eye(720.0)
    az, el = math.radians(10.0), math.radians(6.0)
    d = np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
    return e + 8.0 * d


def split_doorglow(col, M):
    """把 DoorGlow 面拆成单独的物体：只给相机看、进 doorglow 灯组（post 里按 _FogMode 2 处理）。"""
    for ob in list(col.objects):
        mats = [m.name for m in ob.data.materials]
        if 'M_07b_DoorGlow' not in mats or len(mats) == 1:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        ob.active_material_index = mats.index('M_07b_DoorGlow')
        bpy.ops.object.material_slot_select()
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
    for ob in col.objects:
        if [m.name for m in ob.data.materials] == ['M_07b_DoorGlow'] or (ob.data.materials and all(m.name == 'M_07b_DoorGlow' for m in ob.data.materials if m)):
            ob.lightgroup = 'doorglow'
            ob.visible_diffuse = ob.visible_glossy = ob.visible_transmission = ob.visible_volume_scatter = ob.visible_shadow = False


def add_lights(p=PARAMS):
    lin = materials.s2l
    for i, l in enumerate(L.LAMPS):
        fp = l['flame_pos']
        a = bl.point_light_unity('Lw_' + l['id'], fp, lin('#FF9C2F'), p['warm_I'], p['warm_r'], radius=0.10)
        a.lightgroup = 'warm'
        b = bl.point_light_unity('Li_' + l['id'], (fp[0], fp[1] + 0.3, fp[2]), lin('#2A557B'), p['indigo_I'], p['indigo_r'], radius=0.10)
        b.lightgroup = 'indigo'
        b.data.use_shadow = False
    # 门溢出的光：门洞里一盏面光朝外（−z）
    hall = L.HALL
    A = bpy.data.lights.new('DoorSpill', 'AREA')
    A.shape = 'RECTANGLE'
    A.size, A.size_y = hall['door_size'][0] * 0.95, hall['door_size'][1] * 0.95
    A.color = lin('#FFB74D')
    A.energy = p['door_W']
    o = bpy.data.objects.new('DoorSpill', A)
    o.location = Vector(bl.u2b((hall['door_x'], L.PLAT['height_m'] + hall['door_size'][1] / 2, L.DOOR_Z + 0.6)))
    o.rotation_euler = Vector(bl.u2b((0, 0, -1))).to_track_quat('-Z', 'Y').to_euler()
    o.lightgroup = 'door'
    bpy.context.scene.collection.objects.link(o)


def setup_world():
    lin = materials.s2l
    w = bl.world_trilight(lin('#0E3050'), lin('#0A2238'), lin('#1A1422'))
    w.lightgroup = 'amb'
    vl = bpy.context.scene.view_layers[0]
    for g in ('amb', 'warm', 'indigo', 'door', 'doorglow', 'bus'):
        if g not in vl.lightgroups:
            vl.lightgroups.add(name=g)


def add_bus():
    from lbh import scene as S
    objs, eye = S.bus_shell('bible_v2', interior_ambient=None)
    R = Matrix.Rotation(math.pi, 4, 'Z')          # 标准台的轴 (x, z, y) → 本包的轴 (−x, −z, y)
    objs = [o for o in bpy.data.objects if o.name.startswith('Bus_')]   # 连同切窗的棱锥一起转（布尔按世界坐标算）
    for o in objs:
        o.matrix_world = R @ o.matrix_world
        o['lb_bus'] = 1
    return objs


def set_bus(objs, t, visible):
    car = L.car(t)
    T = Matrix.Translation(Vector(bl.u2b(car)))
    for o in objs:
        if 'base_mw' not in o:
            o['base_mw'] = [list(r) for r in o.matrix_world]
        o.matrix_world = T @ Matrix(o['base_mw'])
        o.hide_render = not visible


def render_shot(name, out, res, spp, bus):
    from shots import SHOTS, NO_BUS
    t, yaw, pitch, hfov, _ = SHOTS[name]
    sc = bpy.context.scene
    set_bus(bus, t, name not in NO_BUS)
    cam = bl.camera_unity('Cam_' + name, L.eye(t), yaw, pitch, hfov)
    sc.camera = cam
    bl.render_setup(res, int(round(res * 9 / 16)), spp)
    sc.render.filepath = os.path.join(out, name + '.exr')
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default='F7')
    ap.add_argument('--res', type=int, default=960)
    ap.add_argument('--spp', type=int, default=48)
    ap.add_argument('--out', default='/tmp/pal/r01')
    ap.add_argument('--save-blend', default='')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    os.makedirs(a.out, exist_ok=True)
    build()
    setup_world()
    add_lights()
    bus = add_bus()
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
    for s in a.shots.split(','):
        render_shot(s, a.out, a.res, a.spp, bus)
