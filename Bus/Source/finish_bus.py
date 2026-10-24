# -*- coding: utf-8 -*-
"""把 build_bus 搭出来的零件整理成交给 Unity 的车：分组合并、UV0（米制盒投影）、UV1（车厢光照图集）、
顶点色（R = 1（AO 在 _CabinTubeLM.a）、G = 磨亮、B = 晒褪 / 开裂）、LOD、雨刮枢轴、FBX 导出 + 读回核对、BusLayout.json。

    ~/bpy/bin/python Bus/Source/finish_bus.py --out Bus/Models [--ao-samples 32]

物体（FBX 里的名字 = Unity 里的名字）：
  Bus_Exterior_LOD0 / _LOD1   车身外皮 + 外部件（灯、保险杠、镜、雨刮以外）            Lanbai/Cabin（外观参数）
  Cabin_Static                车厢里所有不动的东西（内壁、顶棚、地板、座椅、仪表台…） Lanbai/Cabin，uv1 = _CabinTubeLM
  Cabin_Tubes                 10 个灯罩（发光 × _Udon_CabinLightmap）
  Cabin_Radio                 收音机（表盘发光 × _Udon_RadioDial）
  Cabin_DestBlind             目的地牌（第 11 幕换贴图）
  Cabin_Curtains              窗帘（Lanbai/ThinCloth；uv0 = (横向米, 离横杆的米)，顶点色 R = 0 横杆 → 1 下摆）
  Bus_DoorLeaf                车门扇，原点 = 铰链，局部 Y 旋转：0° 关、165° 开
  Wheel_FR/FL/RR/RL           轮子，原点 = 轮心（LB_Journey 转它们）
  Glass_*                     每扇玻璃一个物体，原点在玻璃中心，法线朝车外（Rain/README_Rain.md §5.1）
  WiperPivot_L / _R (+ 子物体 Wiper_*)   雨刮枢轴：局部 +Y = 停放方向，+Z = 转轴（§5.5）
"""
import argparse
import json
import math
import os
import sys

import bpy
import bmesh  # noqa: E402
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_bus as BB  # noqa: E402
import bus_spec as B  # noqa: E402

sys.path.insert(0, os.path.join(HERE, '..', '..', 'Tentacles', 'Source', 'lib'))
from export_unity import export_fbx  # noqa: E402


def U(v):        # blender -> unity
    return (v[0], v[2], v[1])


def sel(objs, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def join(name, objs):
    objs = [o for o in objs if o.type == 'MESH']
    sel(objs)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def set_origin(ob, p_blender):
    M = Matrix.Translation(-Vector(p_blender))
    ob.data.transform(M @ ob.matrix_world)
    ob.matrix_world = Matrix.Translation(Vector(p_blender))


def split_body(body):
    """the solidified body has exterior (mat 0-2), interior (3-5) and rim (6-8) faces -> two objects."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    ext = [f for f in bm.faces if f.material_index <= 2]
    bmesh.ops.delete(bm, geom=ext, context='FACES')
    me_int = bpy.data.meshes.new('BodyInner')
    bm.to_mesh(me_int)
    bm.free()
    for m in body.data.materials:
        me_int.materials.append(m)
    inner = bpy.data.objects.new('BodyInner', me_int)
    bpy.context.scene.collection.objects.link(inner)
    inner.matrix_world = body.matrix_world
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index > 2], context='FACES')
    bm.to_mesh(body.data)
    bm.free()
    body.name = 'BodyOuter'
    return body, inner


def uv0_metric(ob):
    """box projection in metres (Unity axes): x-facing -> (z, y), y-facing -> (x, z), z-facing -> (x, y)."""
    me = ob.data
    if 'UVMap' not in me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uv = me.uv_layers['UVMap'].data
    M = ob.matrix_world
    N3 = M.to_3x3().inverted().transposed()
    for p in me.polygons:
        n = U(N3 @ p.normal)
        ax = max(range(3), key=lambda k: abs(n[k]))
        for li in p.loop_indices:
            v = U(M @ me.vertices[me.loops[li].vertex_index].co)
            if ax == 0:
                uv[li].uv = (v[2] * (1 if n[0] > 0 else -1), v[1])
            elif ax == 1:
                uv[li].uv = (v[0], v[2])
            else:
                uv[li].uv = (v[0] * (-1 if n[2] > 0 else 1), v[1])


def uv1_lightmap(ob, margin=0.002):
    """uv1 = the metric box-projection charts of uv0 (undistorted, uniform texel density), packed into 0..1.
    (smart_project shredded the rounded seat pads into one-texel islands.)"""
    me = ob.data
    if 'UVLightmap' not in me.uv_layers:
        me.uv_layers.new(name='UVLightmap')
    src, dst = me.uv_layers['UVMap'].data, me.uv_layers['UVLightmap'].data
    for i in range(len(src)):
        dst[i].uv = src[i].uv
    me.uv_layers.active = me.uv_layers['UVLightmap']
    sel([ob])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    bpy.ops.uv.select_all(action='SELECT')
    try:
        bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', scale=True, margin_method='FRACTION', margin=margin,
                                shape_method='CONCAVE')
    except TypeError:
        bpy.ops.uv.pack_islands(margin=margin, rotate=True, scale=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    me.uv_layers.active = me.uv_layers['UVMap']
    me.uv_layers['UVMap'].active_render = True


def vertex_colours(ob, ao_samples=32):
    """R = 1 (AO is in _CabinTubeLM.a), G = wear / polish, B = sun-fade + crack mask."""
    me = ob.data
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT') if 'Col' not in me.color_attributes else me.color_attributes['Col']
    me.color_attributes.active_color = ca
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = ao_samples
    sc.render.bake.target = 'VERTEX_COLORS'
    sc.world = sc.world or bpy.data.worlds.new('W')
    sc.world.light_settings.distance = 0.6        # AO reach 0.6 m: contact shadow under seats, cove corners
    # AO now lives in the alpha of _CabinTubeLM (bake_lightmap.py, texture space): a vertex bake goes black on the
    # vertices buried inside overlapping parts. R stays 1.
    ao = np.ones(len(me.vertices), np.float32)
    M = ob.matrix_world
    P = np.array([U(M @ v.co) for v in me.vertices], np.float32)
    N = np.array([U((M.to_3x3() @ v.normal).normalized()) for v in me.vertices], np.float32)
    rng = np.random.default_rng(7)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    wear = np.zeros(len(P), np.float32)
    fade = np.zeros(len(P), np.float32)
    # seats: polish where people sit (cushion centre, upper back) — computed per seat row by distance to seat centres
    seat_c = [((B.SEAT_R_X[0] + B.SEAT_R_X[1]) / 2, bz) for bz in B.RIGHT_ROWS] + \
             [(xx, bz) for bz in B.LEFT_ROWS for xx in (-1.10, -0.66)] + [(xx, B.REAR_BENCH_Z) for xx in (-1.05, -0.55, 0.0, 0.55)] + \
             [(B.DRIVER_SEAT[0], B.DRIVER_SEAT[1] - 0.30)]
    for sx, bz in seat_c:
        d_cush = np.sqrt(((x - sx) / 0.16) ** 2 + ((z - (bz + 0.30)) / 0.14) ** 2)
        on_cush = (y > B.FLOOR_Y + 0.3) & (y < 1.12) & (N[:, 1] > 0.5)
        wear = np.maximum(wear, np.where(on_cush, np.clip(1.2 - d_cush, 0, 1), 0))
        d_back = np.sqrt(((x - sx) / 0.17) ** 2 + ((y - 1.45) / 0.22) ** 2)
        on_back = (np.abs(z - (bz + 0.06)) < 0.12) & (N[:, 2] > 0.4)
        wear = np.maximum(wear, np.where(on_back, np.clip(1.1 - d_back, 0, 1) * 0.8, 0))
        # sun-fade: top edge of the backrest, stronger on the window side
        side = np.sign(sx) if abs(sx) > 0.2 else 0
        win_side = np.clip(0.5 + 0.5 * side * x / 0.9, 0, 1) if side else 0.5
        topband = np.clip((y - 1.55) / 0.12, 0, 1) * (np.abs(z - bz) < 0.25) * (np.abs(x - sx) < 0.45)
        fade = np.maximum(fade, topband * win_side)
    # driver's seat is the oldest (bible 4.2): polish 1 on its cushion
    # poles: grip zone 1.0-1.8 m
    grip = np.clip(1 - np.abs(y - 1.4) / 0.4, 0, 1)
    pole_like = (np.abs(N[:, 1]) < 0.3)
    wear = np.maximum(wear, np.where(pole_like & (y > 1.0) & (y < 1.8), grip * 0.0, 0))
    # floor: aisle wear band (x -0.10..0.30) and the door step
    aisle = np.clip(1 - np.abs(x + 0.06) / 0.34, 0, 1) * (N[:, 1] > 0.9) * (np.abs(y - B.FLOOR_Y) < 0.02)
    wear = np.maximum(wear, aisle * (0.6 + 0.4 * np.clip((z - B.Z_REAR) / 6.0, 0, 1)))
    # crack seeds on the vinyl: 2-5 per seat -> random sparse points of the fade/crack mask (blue > 0.75 = crack)
    crack = (rng.random(len(P)) < 0.004).astype(np.float32) * 0.9
    fade = np.maximum(fade * 0.7, crack)
    col = np.stack([ao, wear, fade, np.ones_like(ao)], 1)
    for i, c in enumerate(ca.data):
        c.color = col[i].tolist()
    return dict(ao_mean=float(ao.mean()))


def wipers():
    """two pivots on the windscreen bottom: local +Y = parked arm direction (along the glass bottom), +Z = axis."""
    out = []
    for nm, px, d in (('L', B.XC - 1.00, 1.0), ('R', B.WS_POST[1] + 0.06, 1.0)):
        piv = bpy.data.objects.new('WiperPivot_' + nm, None)
        bpy.context.scene.collection.objects.link(piv)
        loc = BB.U2B((px, B.WS_BOT - 0.022, BB.front_z(px, B.WS_BOT - 0.022) + 0.03))
        # Unity basis: Y' = (1,0,0) (parked arm along +x), Z' = (0,0,1) (axis out of the glass, forward), X' = Y' x Z'
        Yu, Zu = Vector((1, 0, 0)), Vector((0, 0, 1))
        # convert the Unity basis to Blender: columns are images of local x,y,z under U2B; local axes stay Unity-local
        Xb, Yb, Zb = BB.U2B(Vector((0, -1, 0))), BB.U2B(Yu), BB.U2B(Zu)
        R = Matrix((Xb, Yb, Zb)).transposed().to_4x4()
        piv.matrix_world = Matrix.Translation(loc) @ R
        arm = [o for o in bpy.data.objects if o.name.startswith('Wiper') and not o.name.startswith('WiperPivot')]
        out.append(piv)
    # parent the arm meshes to the nearest pivot
    for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Wiper')]:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        cx = sum(v.x for v in bb) / 8
        p = out[0] if cx < B.WS_POST[0] else out[1]
        mw = o.matrix_world.copy()
        o.parent = p
        o.matrix_world = mw
    return out


def build_all(ao_samples):
    BB.build(open_door=True)
    objs = {o.name: o for o in bpy.data.objects}
    body = objs['Body']
    outer, inner = split_body(body)
    groups = {'ext': [], 'static': [], 'tubes': [], 'radio': [], 'blind': [], 'curt': [], 'door': [], 'glass': [], 'wheel': {}, 'wiper': []}
    for o in list(bpy.data.objects):
        if o.type != 'MESH':
            continue
        n = o.name
        cols = [c.name for c in o.users_collection]
        if 'Door' in cols:
            groups['door'].append(o)
        elif n.startswith('Glass_'):
            groups['glass'].append(o)
        elif n.startswith(('Tyre', 'Rim', 'Hub')):
            key = n[-2:]
            groups['wheel'].setdefault(key, []).append(o)
        elif n.startswith('Wiper'):
            groups['wiper'].append(o)
        elif n == 'BodyOuter' or 'Exterior' in cols or n.startswith('HatchOut'):
            groups['ext'].append(o)
        elif 'Lights' in cols:
            groups['tubes'].append(o)
        elif n.startswith('Radio'):
            groups['radio'].append(o)
        elif n == 'DestBlind':
            groups['blind'].append(o)
        elif 'Curtains' in cols and n.startswith('Curtain') and not n.startswith('CurtainRail'):
            groups['curt'].append(o)
        else:
            groups['static'].append(o)
    # curtains: uv0 = (across m, down from rail m), vertex colour R = 0 rail -> 1 hem
    for o in groups['curt']:
        me = o.data
        me.uv_layers.new(name='UVMap')
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        M = o.matrix_world
        for v, c in zip(me.vertices, ca.data):
            yy = U(M @ v.co)[1]
            c.color = (float(np.clip((2.20 - yy) / 0.9, 0, 1)), 0.0, 0.0, 1.0)
        uv = me.uv_layers['UVMap'].data
        for p in me.polygons:
            for li in p.loop_indices:
                w = U(M @ me.vertices[me.loops[li].vertex_index].co)
                uv[li].uv = (w[2], 2.20 - w[1])
    out = {}
    out['Cabin_Static'] = join('Cabin_Static', groups['static'])
    out['Bus_Exterior_LOD0'] = join('Bus_Exterior_LOD0', groups['ext'])
    out['Cabin_Tubes'] = join('Cabin_Tubes', groups['tubes'])
    out['Cabin_Radio'] = join('Cabin_Radio', groups['radio'])
    out['Cabin_DestBlind'] = join('Cabin_DestBlind', groups['blind'])
    out['Cabin_Curtains'] = join('Cabin_Curtains', groups['curt'])
    # four folding-door panels (D-28e: one leaf, all folding to the rear jamb), each its own object (act 11 closes them)
    door_parts = {pid: [o for o in groups['door'] if pid in o.name] for pid in ('Door0', 'Door1', 'Door2', 'Door3')}
    for pid, parts in door_parts.items():
        if parts:
            d = join('Bus_' + pid, parts)
            bb = [d.matrix_world @ Vector(c) for c in d.bound_box]
            set_origin(d, sum(bb, Vector()) / 8)
            out['Bus_' + pid] = d
    for key, parts in groups['wheel'].items():
        nm = {'0R': 'Wheel_FR', '0L': 'Wheel_FL', '1R': 'Wheel_RR', '1L': 'Wheel_RL'}[key]
        w = join(nm, parts)
        ax = 0 if key[0] == '0' else 1
        set_origin(w, BB.U2B((B.XC + (1 if key[1] == "R" else -1) * B.TRACK_HALF, B.WHEEL_R, B.AXLES[ax])))
        out[nm] = w
    for g in groups['glass']:
        bb = [g.matrix_world @ Vector(c) for c in g.bound_box]
        set_origin(g, sum(bb, Vector()) / 8)
        out[g.name] = g
    for o in out.values():
        if o.type == 'MESH' and not o.name.startswith('Cabin_Curtains') and 'UVMap' not in o.data.uv_layers:
            uv0_metric(o)
        elif o.type == 'MESH' and 'UVMap' in o.data.uv_layers and not o.name.startswith('Cabin_Curtains'):
            uv0_metric(o)
    piv = wipers()
    for w in groups['wiper']:
        uv0_metric(w)
    info = {}
    uv1_lightmap(out['Cabin_Static'])
    info['vc'] = vertex_colours(out['Cabin_Static'], ao_samples)
    # LOD1 of the exterior (seen only from outside, acts 1 and 12)
    lod1 = out['Bus_Exterior_LOD0'].copy()
    lod1.data = out['Bus_Exterior_LOD0'].data.copy()
    lod1.name = 'Bus_Exterior_LOD1'
    bpy.context.scene.collection.objects.link(lod1)
    md = lod1.modifiers.new('dec', 'DECIMATE')
    md.ratio = 0.35
    BB.apply_mods(lod1)
    out['Bus_Exterior_LOD1'] = lod1
    return out, piv + groups['wiper'], info


def door_pivots(objs):
    """origin of each door panel = its hinge in the OPEN state (bus_spec: rear jamb, stacked rearward). Returns the
    open / closed local transforms for the act-11 close (Unity: rotate about local +Y)."""
    jr = B.DOOR[0] + B.DOOR_JAMB[0]
    pitch = 0.026
    rows = []
    for k in range(4):
        o = objs.get('Bus_Door%d' % k)
        if o is None:
            continue
        hinge = (B.R_WALL, 0.0, jr - k * pitch)
        set_origin(o, BB.U2B(hinge))
        rows.append(dict(name=o.name, open=dict(position=list(hinge), yaw_deg=0.0),
                         closed=dict(position=[B.R_WALL, 0.0, jr + k * B.DOOR_PANEL], yaw_deg=-B.DOOR_OPEN_SWING),
                         note='FBX 里是开着的状态；关上 = 把物体移到 closed.position、绕自己的 +Y 转 closed.yaw_deg（第 11 幕，白遮罩下）'))
    return rows


def layout(out):
    """BusLayout.json: every number the Unity build script needs (CONTROL §6 pitfall 13)."""
    seats = []
    for i, bz in enumerate(B.RIGHT_ROWS):
        cy = (0.96 + 0.07) if i == 0 else B.FLOOR_Y + B.SEAT_H
        seats.append(dict(name='SeatR%d' % i, hero=(i == 0), x=(B.SEAT_R_X[0] + B.SEAT_R_X[1]) / 2, cushion_y=cy, back_z=bz))
    for i, bz in enumerate(B.LEFT_ROWS):
        for k, xx in enumerate((-1.10, -0.66)):
            seats.append(dict(name='SeatL%d%s' % (i, 'w' if k == 0 else 'a'), hero=False, x=xx, cushion_y=B.FLOOR_Y + B.SEAT_H, back_z=bz))
    for k, xx in enumerate((-1.05, -0.55, 0.0, 0.55)):
        seats.append(dict(name='RearBench%d' % k, hero=False, x=xx, cushion_y=B.FLOOR_Y + B.SEAT_H, back_z=B.REAR_BENCH_Z))
    for s in seats:
        # VRCStation: the seat's 'Station Enter Player Location' at the cushion surface, facing +Z
        s['station_pos'] = [s['x'], s['cushion_y'], s['back_z'] + 0.30]
        s['eye_approx'] = [s['x'], s['cushion_y'] + 0.68, s['back_z'] + 0.23]
    xl, xr, xm = B.XC - B.W_HALF + 0.03, B.R_WALL - 0.03, B.XC
    W2, L2, zc = 2 * B.W_HALF - 0.06, B.Z_FRONT - B.Z_REAR - 0.12, (B.Z_FRONT + B.Z_REAR) / 2
    cols = [  # invisible colliders (BoxCollider centre / size, Unity)
        dict(name='Col_Floor', c=[xm, B.FLOOR_Y - 0.03, zc], s=[W2, 0.06, L2]),
        dict(name='Col_WallL', c=[xl, 1.5, zc], s=[0.06, 1.8, L2]),
        dict(name='Col_WallR_rear', c=[xr, 1.5, (B.Z_REAR + B.DOOR[0]) / 2], s=[0.06, 1.8, B.DOOR[0] - B.Z_REAR]),
        dict(name='Col_WallR_front', c=[xr, 1.5, 3.39], s=[0.06, 1.8, 0.24]),
        dict(name='Col_Front', c=[xm, 1.5, B.Z_FRONT - 0.06], s=[W2, 1.8, 0.06]),
        dict(name='Col_Rear', c=[xm, 1.5, B.Z_REAR + 0.06], s=[W2, 1.8, 0.06]),
        dict(name='Col_Roof', c=[xm, B.CEIL_Y + 0.03, zc], s=[W2, 0.06, L2]),
        dict(name='Col_Dash', c=[xm, 0.95, 3.27], s=[W2, 0.66, 0.38]),
        dict(name='Col_EngineCover', c=[(B.ENGINE_COVER[0] + B.ENGINE_COVER[1]) / 2, (B.FLOOR_Y + B.ENGINE_COVER[4]) / 2, (B.ENGINE_COVER[2] + B.ENGINE_COVER[3]) / 2],
             s=[B.ENGINE_COVER[1] - B.ENGINE_COVER[0], B.ENGINE_COVER[4] - B.FLOOR_Y, B.ENGINE_COVER[3] - B.ENGINE_COVER[2]]),
        dict(name='Col_Guard', c=[0.775, 0.93, B.GUARD_Z], s=[0.43, 0.62, 0.04]),
        dict(name='Col_Step', c=[0.82, 0.30, (B.DOOR[0] + B.DOOR[1]) / 2], s=[0.44, 0.60, B.DOOR[1] - B.DOOR[0]]),
    ]
    return dict(
        _about='车的布局（唯一数据源 Bus/Source/bus_spec.py，由 finish_bus.py 写出）。Unity 车局部坐标：米，x 右 y 上 z 前，车头 +Z，路面 y 0。',
        eye_hero=list(B.EYE), floor_y=B.FLOOR_Y, skylight=dict(centre=list(B.SKY_C), half=B.SKY_HALF),
        door=dict(kind='one glazed leaf of four panels, all folding outward onto the rear jamb (D-28e)', open_swing_deg=B.DOOR_OPEN_SWING, panel_m=B.DOOR_PANEL,
                  jambs_m=dict(rear=B.DOOR_JAMB[0], front=B.DOOR_JAMB[1]), opening_z=list(B.DOOR),
                  note='FBX 里是开着的状态（圣经：门从不关）；第 11 幕在白的遮罩下关上。关的状态的变换在完整的车里补（WIP）'),
        wheels=dict(radius=B.WHEEL_R, names=['Wheel_FR', 'Wheel_FL', 'Wheel_RR', 'Wheel_RL'], axis='local X',
                    centres=[[B.XC + s * B.TRACK_HALF, B.WHEEL_R, z] for z in B.AXLES for s in (1, -1)]),
        tubes=[dict(row=r, x=x, z0=z0, z1=z1) for r, x, zl in (('L', B.TUBE_X[0], B.TUBE_Z_L), ('R', B.TUBE_X[1], B.TUBE_Z)) for z0, z1 in zl],
        head_fill_lights=[dict(pos=[x, 2.45, 0.0], colour='#E4F1F3', render_mode='Not Important', culling='Player + PlayerLocal',
                               note='圣经 §4.3：座位处灰卡 #585F64，强度 × _Udon_CabinLightmap') for x in B.TUBE_X],
        bus=dict(model='PAZ-672 (D-28)', centre_x=B.XC, width=2 * B.W_HALF, length=B.Z_FRONT - B.Z_REAR, height=B.Y_TOP,
                 bounds_min=[B.XC - B.W_HALF, 0.0, B.Z_REAR], bounds_max=[B.R_WALL, 2.80, B.Z_FRONT + 0.12]),
        radio=dict(centre=list(B.RADIO_C), az_el=[-20, -12]), steering_wheel=dict(centre=list(B.WHEEL_C), tilt_deg=B.WHEEL_TILT),
        seats=seats, seat_count=len(seats), colliders=cols,
        cabin_bounds=dict(min=[B.XC - B.W_HALF + 0.05, B.FLOOR_Y - 0.05, B.Z_REAR + 0.06], max=[B.R_WALL - 0.05, B.CEIL_Y, B.Z_FRONT - 0.06],
                          note='D-31：车厢内部的范围（给 LB_Journey.busMin / busMax）；Director 按玩家根位置检查，头探出玻璃 ≤ 0.6 m 不算离开'),
        instance_cap_note='D-31：实例人数上限 = seat_count（不算司机座）',
        objects=sorted(out.keys()),
    )


def readback(path, expect):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path, axis_forward='Z', axis_up='Y', global_scale=1.0)
    got = {o.name: o for o in bpy.data.objects}
    rep = {}
    for nm, (nv, bb) in expect.items():
        o = got.get(nm)
        if o is None:
            rep[nm] = 'MISSING'
            continue
        if o.type != 'MESH':
            rep[nm] = 'ok (empty)'
            continue
        bbw = [U(o.matrix_world @ Vector(c)) for c in o.bound_box]
        lo = np.min(bbw, 0)
        hi = np.max(bbw, 0)
        err = float(max(np.max(np.abs(lo - bb[0])), np.max(np.abs(hi - bb[1]))))
        uvs = [l.name for l in o.data.uv_layers]
        rep[nm] = dict(verts=len(o.data.vertices), verts_expected=nv, bbox_err_m=round(err, 5), uv_layers=uvs,
                       colours=[c.name for c in o.data.color_attributes])
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'Models'))
    ap.add_argument('--ao-samples', type=int, default=32)
    ap.add_argument('--blend', default='/tmp/bus/bus_final.blend')
    ap.add_argument('--from-blend', default=None, help='export only: re-export the FBX from a finished .blend (after the '
                    'lightmap bake and the exterior weathering added their uv1 atlases)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.from_blend:
        bpy.ops.wm.open_mainfile(filepath=a.from_blend)
        objs = [o for o in bpy.data.objects if o.type == 'MESH' or o.name.startswith('WiperPivot')]
        out = {o.name: o for o in objs if not o.name.startswith('Wiper')}
        info = {}
    else:
        out, extra, info = build_all(a.ao_samples)
        os.makedirs(os.path.dirname(a.blend), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=a.blend)
        objs = list(out.values()) + extra
    door_rows = door_pivots({o.name: o for o in objs})
    fbx = os.path.join(a.out, 'Bus.fbx')
    export_fbx(fbx, objs)
    expect = {}
    for o in objs:
        if o.type == 'MESH':
            bbw = [U(o.matrix_world @ Vector(c)) for c in o.bound_box]
            expect[o.name] = (len(o.data.vertices), (np.min(bbw, 0), np.max(bbw, 0)))
        else:
            expect[o.name] = (0, None)
    # the render harness shell 'paz672' (Engineering/render_harness: --bus fbx:Bus/Models/Bus_HarnessShell_paz672.fbx):
    # everything but the glass (an FBX glass imports opaque there) and the LOD1 copy
    shell = [o for o in objs if o.type == 'MESH' and not o.name.startswith('Glass_') and not o.name.endswith('_LOD1')]
    export_fbx(os.path.join(a.out, 'Bus_HarnessShell_paz672.fbx'), shell)
    lay = layout(out)
    lay['door_panels'] = door_rows
    lay['stats'] = {o.name: dict(verts=len(o.data.vertices), tris=sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in objs if o.type == 'MESH'}
    lay['stats_total_tris'] = sum(v['tris'] for v in lay['stats'].values())
    json.dump(lay, open(os.path.join(a.out, 'BusLayout.json'), 'w'), ensure_ascii=False, indent=1)
    rep = readback(fbx, expect)
    json.dump(rep, open(os.path.join(a.out, 'Bus_fbx_readback.json'), 'w'), ensure_ascii=False, indent=1)
    bad = [k for k, v in rep.items() if v == 'MISSING' or (isinstance(v, dict) and (v['bbox_err_m'] > 0.002 or v['verts'] < v['verts_expected']))]
    print('[finish] %d objects, %d tris total, readback problems: %s, %s' % (len(objs), lay['stats_total_tris'], bad or 'none', info))


if __name__ == '__main__':
    main()
