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

import json as _json
_T = _json.load(open(os.path.join(HERE, 'tuning.json')))
FISH_T = 748.26
PARAMS = dict(warm_I=_T['warm_I'], warm_r=_T['warm_range'], indigo_I=_T['indigo_I'], indigo_r=_T['indigo_range'], door_W=_T['door_area_I'], pour_ratio=_T.get('pour_ratio', 0.0))


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


def build(t_fish=None, lod_far=False):
    sc = bl.reset()
    M = materials.build_all()
    col = bpy.data.collections.new('Palace')
    sc.collection.children.link(col)
    # 台地 + 海草
    tob = terrace.build().build('Terrace', col, M)
    tob.pass_index = 3
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
    fu = fish.place(t_fish if t_fish is not None else FISH_T, L.FISH['centre'], poem)
    if fu.V:
        fu.build('Fish', col, M)
    split_doorglow(col, M)
    add_cones(col)
    return M


def add_cones(col):
    """门口 3 张锥形光卡（与 export_fbx.g_door 同一几何）。"""
    import export_fbx as X
    u = X.door_cones_ub()
    m = materials.cone_material('M_07b_DoorCone', tuple(1.6 * c for c in materials.s2l('#FFB74D')), alpha=0.03)
    ob = u.build('DoorCones', col, {'DoorGlow': m})
    ob.lightgroup = 'doorglow'
    ob.visible_diffuse = ob.visible_glossy = ob.visible_transmission = ob.visible_volume_scatter = ob.visible_shadow = False


def poem_point():
    import scene_math
    return np.array(scene_math.poem_point())


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
        a.visible_glossy = False                      # 烘焙的光只有漫反射；高光由下面的解析灯给（Unity：_Udon_Lamp）
        b = bl.point_light_unity('Li_' + l['id'], (fp[0], fp[1] + _T.get('indigo_lift', 0.3), fp[2]), lin('#2A557B'),
                                 0.0 if l['group'] == 'que' else p['indigo_I'], p['indigo_r'], radius=0.10)   # 阙前的灯不加靛光（第 5 轮）
        b.lightgroup = 'indigo'
        b.data.use_shadow = False
        b.visible_glossy = False
        # 解析 GGX 宫灯：平方反比、没有范围窗、只进高光（Unity 里是离眼睛最近的 8 盏；参考图里 30 盏都算）
        c = bpy.data.lights.new('Ls_' + l['id'], 'POINT')
        c.color = lin('#FF9C2F')
        c.energy = 4.0 * math.pi ** 2 * _T.get('spec_I', 5.46)
        c.shadow_soft_size = 0.10
        co = bpy.data.objects.new('Ls_' + l['id'], c)
        co.location = Vector(bl.u2b(fp))
        co.visible_diffuse = False
        co.visible_transmission = False
        co.visible_volume_scatter = False
        co.lightgroup = 'warm'
        bpy.context.scene.collection.objects.link(co)
        # 珍珠母的高光 ×nacre_spec_gain（Unity：M_07b_FishScale 的 _LampGain）：同样的灯，灯光链接只照鱼鳞屋
        g = _T.get('nacre_spec_gain', 1.0)
        if g > 1.0:
            c2 = bpy.data.lights.new('Ln_' + l['id'], 'POINT')
            c2.color = lin('#FF9C2F')
            c2.energy = 4.0 * math.pi ** 2 * _T.get('spec_I', 5.46) * (g - 1.0)
            c2.shadow_soft_size = 0.10
            o4 = bpy.data.objects.new('Ln_' + l['id'], c2)
            o4.location = Vector(bl.u2b(fp))
            o4.visible_diffuse = False
            o4.visible_transmission = False
            o4.visible_volume_scatter = False
            o4.lightgroup = 'warm'
            bpy.context.scene.collection.objects.link(o4)
            hc = bpy.data.collections.get('LinkHouses')
            if hc is None:
                hc = bpy.data.collections.new('LinkHouses')
                hc.objects.link(bpy.data.objects['Houses'])
            o4.light_linking.receiver_collection = hc
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
    o.visible_glossy = False
    bpy.context.scene.collection.objects.link(o)
    # 门作为解析线光源（Unity：驱动写进 _Udon_Lamp7，竖直线光源 = 门洞高）：只进高光，湿石面上的亮带
    A3 = bpy.data.lights.new('DoorSpec', 'AREA')
    A3.shape = 'RECTANGLE'
    A3.size, A3.size_y = 0.3, hall['door_size'][1]
    A3.color = lin('#FFB74D')
    A3.energy = 4.0 * math.pi ** 2 * _T.get('door_spec_I', 60.0) * 0.25
    o3 = bpy.data.objects.new('DoorSpec', A3)
    o3.location = Vector(bl.u2b((hall['door_x'], L.PLAT['height_m'] + hall['door_size'][1] / 2, L.DOOR_Z + 0.9)))
    o3.rotation_euler = Vector(bl.u2b((0, 0, -1))).to_track_quat('-Z', 'Y').to_euler()
    o3.visible_diffuse = False
    o3.visible_transmission = False
    o3.visible_volume_scatter = False
    o3.lightgroup = 'door'
    bpy.context.scene.collection.objects.link(o3)
    if p.get('pour_ratio', 0.0) <= 0.0:
        return
    # 门光顺着台阶往下铺：门楣处一盏面光，朝外、向下 35°（第 3 轮；第 4 轮去掉：阴影发暖）
    A2 = bpy.data.lights.new('DoorPour', 'AREA')
    A2.shape = 'RECTANGLE'
    A2.size, A2.size_y = hall['door_size'][0] * 0.9, 1.0
    A2.color = lin('#FFB74D')
    A2.energy = p['door_W'] * p.get('pour_ratio', 0.6)
    o2 = bpy.data.objects.new('DoorPour', A2)
    o2.location = Vector(bl.u2b((hall['door_x'], L.PLAT['height_m'] + hall['door_size'][1] - 0.6, L.DOOR_Z + 0.3)))
    d = np.array([0.0, -math.sin(math.radians(35)), -math.cos(math.radians(35))])
    o2.rotation_euler = Vector(bl.u2b(d)).to_track_quat('-Z', 'Y').to_euler()
    o2.lightgroup = 'door'
    o2.visible_glossy = False
    bpy.context.scene.collection.objects.link(o2)


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
    amb = tuple(0.3 * c for c in materials.s2l('#0F1E30'))          # 圣经 §6·7b：车厢环境 #0F1E30 × 0.3
    objs, eye = S.bus_shell('bible_v2', interior_ambient=amb)
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
    from shots import SHOTS as _S
    FISH_T = _S[a.shots.split(',')[0]][0]          # 鱼按第一张机位的时刻摆
    build(t_fish=FISH_T)
    setup_world()
    add_lights()
    bus = add_bus()
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
    for s in a.shots.split(','):
        render_shot(s, a.out, a.res, a.spp, bus)
