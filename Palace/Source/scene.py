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
DOOR_SPILL_POS = np.array([L.HALL['door_x'], L.PLAT['height_m'] + L.HALL['door_size'][1] * 0.55, L.DOOR_Z - 0.3])   # 门面外 0.3 m：门扇在它身后，不被照亮
DOOR_ACCENT_POS = np.array([L.HALL['door_x'], L.PLAT['height_m'] + 5.0, L.DOOR_Z - 7.0])
DOOR_ACCENT_TGT = np.array([L.HALL['door_x'], L.PLAT['height_m'] + 5.5, L.DOOR_Z])
PARAMS = dict(warm_I=_T['warm_I'], warm_r=_T['warm_range'], indigo_I=_T['indigo_I'], indigo_r=_T['indigo_range'])


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


def split_slot(u, slot):
    """把一个槽的面分出来（灯光链接按物体）。"""
    from kit.common import SLOTS
    a, b = UB(), UB()
    for f, sl, uv in zip(u.F, u.S, u.UV):
        dst = a if SLOTS[sl] == slot else b
        o = len(dst.V)
        dst.V.extend(u.V[i] for i in f)
        dst.F.append(tuple(range(o, o + len(f))))
        dst.S.append(sl)
        dst.UV.append(uv)
    return a, b


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
        yaw = 90.0 if l['group'] == 'que' else 0.0     # 第 8 轮：阙前的灯转 90°，灯罩的两片挡板朝 ±x，开口朝阙面和神道
        lu.merge(place(lamp.build(l['height_m']), l['pos'], yaw))
    lu.build('Lamps', col, M)
    # 大殿、阙、鱼鳞屋（模块没交时用白模盒子）
    hall = try_kit('hall')
    if hall:
        hall.build().build('Hall', col, M).pass_index = 4
    que = try_kit('que')
    if que:
        qu = que.build()
        cw, rest_q = split_slot(qu, 'Cowrie')
        rest_q.build('Que', col, M).pass_index = 5
        cw.build('QueCowrie', col, M).pass_index = 5
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
    # 第 8 轮：鱼鳞屋面单独一个物体（灯光链接按物体：挪高的“镜中灯”只照珍珠母，Unity 里是 _NacreLift 只进 M_07b_FishScale）
    from kit.common import SLOTS
    nac, rest = UB(), UB()
    for f, sl, uv in zip(hu.F, hu.S, hu.UV):
        dst = nac if SLOTS[sl] == 'FishScale' else rest
        o = len(dst.V)
        dst.V.extend(hu.V[i] for i in f)
        dst.F.append(tuple(range(o, o + len(f))))
        dst.S.append(sl)
        dst.UV.append(uv)
    rest.build('Houses', col, M).pass_index = 6
    nac.build('HousesNacre', col, M).pass_index = 7
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
        # 第 8 轮：按面实际用的材质判断（separate 以后新物体保留全部材质槽，按槽名判断会漏掉一半内衬 → 不进灯组 → post 里被涂黑）
        used = {ob.data.materials[pl.material_index].name for pl in ob.data.polygons if ob.data.materials}
        if used == {'M_07b_DoorGlow'}:
            ob.lightgroup = 'doorglow'
            ob.visible_diffuse = ob.visible_glossy = ob.visible_transmission = ob.visible_volume_scatter = ob.visible_shadow = False


def add_lights(p=PARAMS):
    lin = materials.s2l
    for i, l in enumerate(L.LAMPS):
        fp = l['flame_pos']
        gl = l.get('gain', 1.0)
        a = bl.point_light_unity('Lw_' + l['id'], fp, lin('#FF9C2F'), p['warm_I'] * gl, p['warm_r'], radius=0.10)
        a.lightgroup = 'warm'
        a.visible_glossy = False                      # 烘焙的光只有漫反射；高光由下面的解析灯给（Unity：_Udon_Lamp）
        # 第 8 轮：阙前的灯也加靛光，但不抬高、范围 5 m——暖 + 靛只在灯旁混成 #7A4A6E（“只在它的灯旁泛出”）
        b = bl.point_light_unity('Li_' + l['id'], (fp[0], fp[1] + l.get('indigo_lift', _T.get('indigo_lift', 0.3)), fp[2]), lin('#2A557B'),
                                 p['indigo_I'] * l.get('indigo_gain', gl), l.get('indigo_range', p['indigo_r']), radius=0.10)
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
        if 'HousesNacre' in bpy.data.objects:   # Unity：珍珠母的灯高光只有珍珠光带（LanbaiNacreBand），不吃普通的解析灯
            xc = bpy.data.collections.get('LinkNotHouses')
            if xc is None:
                xc = bpy.data.collections.new('LinkNotHouses')
                xc.objects.link(bpy.data.objects['HousesNacre'])
                xc.collection_objects[0].light_linking.link_state = 'EXCLUDE'
            co.light_linking.receiver_collection = xc
        # 珍珠母的高光 ×nacre_spec_gain（Unity：M_07b_FishScale 的 _LampGain）：同样的灯，灯光链接只照鱼鳞屋
        g = _T.get('nacre_spec_gain', 1.0)
        if g > 1.0 and 'HousesNacre' in bpy.data.objects:
            c2 = bpy.data.lights.new('Ln_' + l['id'], 'POINT')
            c2.color = (1.0, 1.0, 1.0)       # 第 8 轮 r6：珍珠母只取灯的亮度，颜色由虹彩给（Unity：spec 先取亮度再 × LanbaiNacre）
            c2.energy = 4.0 * math.pi ** 2 * _T.get("spec_I", 5.46) * g * 0.45     # 第 8 轮：珍珠母只吃这一盏（往上挪 nacre_lift 的“镜中灯”）
            c2.shadow_soft_size = _T.get('nacre_radius', 0.10)     # 第 8 轮：珍珠母的高光瓣放宽（Unity：_NacreSpread）
            o4 = bpy.data.objects.new('Ln_' + l['id'], c2)
            o4.location = Vector(bl.u2b((fp[0], fp[1] + _T.get('nacre_lift', 0.0), fp[2])))
            o4.visible_diffuse = False
            o4.visible_transmission = False
            o4.visible_volume_scatter = False
            o4.lightgroup = 'warm'
            bpy.context.scene.collection.objects.link(o4)
            hc = bpy.data.collections.get('LinkHouses')
            if hc is None:
                hc = bpy.data.collections.new('LinkHouses')
                hc.objects.link(bpy.data.objects['HousesNacre'])
            o4.light_linking.receiver_collection = hc
        cg = _T.get('cowrie_spec_gain', 1.0)
        if l['group'] == 'que' and cg > 1.0 and 'QueCowrie' in bpy.data.objects:   # 宝贝贴面的解析高光 ×cowrie_spec_gain（Unity：M_07b_Cowrie 的 _LampGain）
            c3 = bpy.data.lights.new('Lc_' + l['id'], 'POINT')
            c3.color = lin('#FF9C2F')
            c3.energy = 4.0 * math.pi ** 2 * _T.get('spec_I', 5.46) * (cg - 1.0)
            c3.shadow_soft_size = 0.10
            o5 = bpy.data.objects.new('Lc_' + l['id'], c3)
            o5.location = Vector(bl.u2b(fp))
            o5.visible_diffuse = o5.visible_transmission = o5.visible_volume_scatter = False
            o5.lightgroup = 'warm'
            bpy.context.scene.collection.objects.link(o5)
            qc = bpy.data.collections.get('LinkCowrie')
            if qc is None:
                qc = bpy.data.collections.new('LinkCowrie')
                qc.objects.link(bpy.data.objects['QueCowrie'])
            o5.light_linking.receiver_collection = qc
    # 门溢出的光（第 8 轮，评审 r5 #3）：门槛里一盏烘焙聚光朝外（−z），范围窗 door_spill_range —— 面光没有范围，
    # 会把整面立面描成朱红（阴影发暖）；聚光和宫灯一样是 InverseSquared + 范围窗，只照门槛、台阶顶和门框
    hall = L.HALL
    o = bl.spot_light_unity('DoorSpill', DOOR_SPILL_POS, (0, -0.35, -1), lin('#FFB74D'), _T['door_spill_I'], _T['door_spill_range'],
                            _T['door_spill_angle'], blend=0.5, radius=0.4)
    o.lightgroup = 'door'
    o.visible_glossy = False
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
    # D-31（Fins 的 smoke and mirrors）：只参与烘焙、本身看不见的面光，把门那一开间（门两侧的柱、门楣、斗拱、门前的台基面）
    # 托出来，让亮着的空门是眼睛第一个落上去的地方。门前 7 m、高 11 m，朝门，6 × 5 m，暖白偏金；只进漫反射（= 烘焙）。
    # 第 8 轮：面光 → 烘焙聚光（范围窗 door_accent_range），只托门这一开间，不再照到别的开间
    ap, tgt = DOOR_ACCENT_POS, DOOR_ACCENT_TGT
    o4 = bl.spot_light_unity('DoorAccent', ap, tgt - ap, lin('#FFD9A0'), _T['door_accent_I'], _T['door_accent_range'],
                             _T['door_accent_angle'], blend=0.6, radius=0.5)
    o4.visible_glossy = False
    o4.lightgroup = 'accent'


def setup_world():
    lin = materials.s2l
    w = bl.world_trilight(lin('#0E3050'), lin('#0A2238'), lin('#1A1422'))
    w.lightgroup = 'amb'
    vl = bpy.context.scene.view_layers[0]
    for g in ('amb', 'warm', 'indigo', 'door', 'accent', 'doorglow', 'bus'):
        if g not in vl.lightgroups:
            vl.lightgroups.add(name=g)


PAZ_SHELL = '/tmp/pal/bus/Bus_HarnessShell_new.fbx'     # main 的 Bus/Models/Bus_HarnessShell_paz672.fbx（10-25 新车厢，玻璃范围比旧车大；总导演：前方视野按新车核）


def add_bus():
    from lbh import scene as S
    if os.path.exists(PAZ_SHELL):
        objs = S.import_unity_fbx(PAZ_SHELL)
        R = Matrix.Rotation(math.pi, 4, 'Z')        # 标准台的轴 (x, z, y) → 本包的轴 (−x, −z, y)
        import bus_erosion
        amb = tuple(0.3 * c for c in materials.s2l('#0F1E30'))
        # 第 8 轮（评审 r5 新阻断 1）：车厢 = Lanbai/Cabin 在 7b 的样子——侵蚀 0.25、只吃车厢环境 #0F1E30 × 0.3（圣经 §6·7b）。
        # 第 7 轮用的是没侵蚀、被宫殿的光照着的整壳，把窗框以外全压黑，APL 掉到 12
        frame = bpy.data.objects.new('BusFrame', None)
        bpy.context.scene.collection.objects.link(frame)
        frame.matrix_world = R
        frame['lb_bus'] = 1
        dark = bus_erosion.cabin_material('M_Bus_Cabin7b', materials.s2l('#2A2C30'), amb, frame)
        for o in objs:
            o.matrix_world = R @ o.matrix_world
            o['lb_bus'] = 1
            if o.type == 'MESH':
                o.data.materials.clear()
                o.data.materials.append(dark)
                o.visible_diffuse = o.visible_glossy = o.visible_shadow = False   # 车厢不挡宫殿的光（参考图里车只给相机看）
        # 终审 10-25 #4：车底的光（圣经 7b-ii：1–2 盏实时点光在车下，#FF5A2E，车处 E 0.15；归海——参考图里先放一盏，空司机座才读得出来）
        ub = bl.point_light_unity('BusUnderLight', (0.0, -1.2, 0.0), materials.s2l('#FF5A2E'), 0.15 * 1.2 ** 2 / 0.9, 6.0, radius=0.2)
        ub.lightgroup = 'bus'
        ub['lb_bus'] = 1
        return [o for o in objs if o.type == 'MESH'] + [frame, ub]
    amb = tuple(0.3 * c for c in materials.s2l('#0F1E30'))          # 圣经 §6·7b：车厢环境 #0F1E30 × 0.3
    objs, eye = S.bus_shell('bible_v2', interior_ambient=amb)
    R = Matrix.Rotation(math.pi, 4, 'Z')          # 标准台的轴 (x, z, y) → 本包的轴 (−x, −z, y)
    objs = [o for o in bpy.data.objects if o.name.startswith('Bus_')]   # 连同切窗的棱锥一起转（布尔按世界坐标算）
    for o in objs:
        o.matrix_world = R @ o.matrix_world
        o['lb_bus'] = 1
    return objs


def set_bus(objs, t, visible, dz=0.0, dx=0.0):
    car = L.car(t) + np.array([dx, 0.0, dz])
    T = Matrix.Translation(Vector(bl.u2b(car)))
    for o in objs:
        if 'base_mw' not in o:
            o['base_mw'] = [list(r) for r in o.matrix_world]
        o.matrix_world = T @ Matrix(o['base_mw'])
        o.hide_render = not visible


def render_shot(name, out, res, spp, bus):
    from shots import SHOTS, NO_BUS, SHOT_DZ, SHOT_DX
    t, yaw, pitch, hfov, _ = SHOTS[name]
    dz = SHOT_DZ.get(name, 0.0)
    dx = SHOT_DX.get(name, 0.0)
    sc = bpy.context.scene
    set_bus(bus, t, name not in NO_BUS, dz, dx)
    cam = bl.camera_unity('Cam_' + name, L.eye(t) + np.array([dx, 0, dz]), yaw, pitch, hfov)
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
