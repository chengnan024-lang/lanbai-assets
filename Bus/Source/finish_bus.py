# -*- coding: utf-8 -*-
"""把 build_bus 搭出来的零件整理成交给 Unity 的车：分组合并、UV0（米制盒投影）、UV1（车厢光照图集）、
顶点色（R = 积灰 / 发黄、G = 磨亮、B = 晒褪 / 开裂）、LOD、雨刮枢轴、FBX 导出 + 读回核对、BusLayout.json。

    ~/bpy/bin/python Bus/Source/finish_bus.py --out Bus/Models [--ao-samples 32]

物体（FBX 里的名字 = Unity 里的名字）：
  Bus_Exterior_LOD0 / _LOD1   车身外皮 + 外部件（灯、保险杠、镜、雨刮以外）            Lanbai/Cabin（外观参数）
  Cabin_Static                车厢里所有不动的东西（内壁、顶棚、地板、座椅、仪表台…） Lanbai/Cabin，uv1 = _CabinTubeLM
  Seat_*                      D-36 每个座位一个物体（uv0 = 零件图集，uv1 = _CabinTubeLM，和 Cabin_Static 同一张）
  Seat_*_LOD1 / _LOD2         每个座位减到 50 % / 25 % 的两份（导出时做，seat_lods；LanbaiBusBuild 把三份放进一个 LODGroup）
  Window_R1 / Pole_R0         D-40 #1 切片用：主座位侧窗的车厢里那一半（WinR1_*）、右边第一根立柱（PoleR0*），
                              从 Cabin_Static 里分出来（SEPARATE），uv1 = _CabinTubeLM（同一张）
                              这三类的 uv 层顺序都是 UVMap, UVLightmap, UVMetric（lm_uv_order；Unity 按层的顺序当 uv0/1/2）
  Cabin_Tubes                 10 个灯罩（发光 × _Udon_CabinLightmap）
  Cabin_Radio                 收音机（表盘发光 × _Udon_RadioDial）
  Cabin_DestBlind             目的地牌（第 11 幕换贴图）
  Cabin_Curtains              窗帘（Lanbai/ThinCloth；uv0 = (横向米, 离横杆的米)，顶点色 R = 0 横杆 → 1 下摆）
  Bus_DoorLeaf                车门扇，原点 = 铰链，局部 Y 旋转：0° 关、165° 开
  Wheel_FR/FL/RR/RL           轮子，原点 = 轮心（LB_Journey 转它们）
  Glass_*                     每扇玻璃一个物体，原点在玻璃中心，法线朝车外（Rain/README_Rain.md §5.1）
  WiperPivot_L / _R (+ 子物体 Wiper_*)   雨刮枢轴：局部 +Y = 停放方向，+Z = 转轴（§5.5）

坐标：Unity 里每个物体的位置、旋转、包围盒 = BusLayout.json 的车局部坐标（x 右 y 上 z 前）。Unity 导入 FBX 时把 x 取反，
所以 Bus.fbx 是把场景绕 Unity Y 转 180° 以后导出的（R_UNITY，只转导出那一下，转完原样转回来）；Bus_fbx_readback.json
按 Unity 的规则核对（readback）。
"""
import argparse
import json
import math
import os
import sys
import zlib

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


# the joint _CabinTubeLM atlas (D-40 #1 seam check, Docs~/slice/光照图接缝检查.md): with ~7 500 box-projection islands the
# margin, not the packer, set the density (0.002 -> 29 % of the atlas used, 80 texel/m at 2048; 0.001 -> 43 %, 96).
# 0.001 = 2 texels a side at 2048: bake_lightmap.fill_black's 2-texel ring and the bilinear footprint stay inside it.
LM_MARGIN = 0.001
LM_MIN_TEXELS = 2.5          # no island narrower than this (2 x area / perimeter; lands at >= ~2 true width) (seat piping, seal lips, the stop button were 0.1-0.4 texel)
LM_EXPECT_DENSITY = 95.0     # texel / m at 2048 after the pack (measured), to turn LM_MIN_TEXELS into metres
LM_NEAR = {'Seat_SeatR0': 1.75, 'Window_R1': 1.75, 'Pole_R0': 1.75}   # next to the hero eye: 1.75 x the texel density


def _uv_islands(me, layer):
    """the uv islands of one mesh in a uv layer: lists of loop indices (faces joined where an edge has the same uvs on
    both sides)."""
    uv = np.empty(2 * len(me.loops), np.float32)
    me.uv_layers[layer].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    parent = list(range(len(me.polygons)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    edge_side = {}
    for p in me.polygons:
        li = list(p.loop_indices)
        for k in range(len(li)):
            a_, b_ = li[k], li[(k + 1) % len(li)]
            va, vb = me.loops[a_].vertex_index, me.loops[b_].vertex_index
            key = (min(va, vb), max(va, vb))
            ua = tuple(np.round(uv[a_], 6)) if va < vb else tuple(np.round(uv[b_], 6))
            ub = tuple(np.round(uv[b_], 6)) if va < vb else tuple(np.round(uv[a_], 6))
            prev = edge_side.get(key)
            if prev is None:
                edge_side[key] = (p.index, ua, ub)
            elif prev[1] == ua and prev[2] == ub:
                ra, rb = find(prev[0]), find(p.index)
                if ra != rb:
                    parent[ra] = rb
    groups = {}
    for p in me.polygons:
        groups.setdefault(find(p.index), []).extend(p.loop_indices)
    return list(groups.values()), uv


def _lm_widen(me, scale=1.0):
    """scale the object's uv1 (metric) by 'scale', then give every island narrower than LM_MIN_TEXELS (at the expected
    density; width = 2 x area / perimeter, so a curved strip - the seat piping, a seal lip - counts as thin) that width
    by pushing its outline outward along the outline's normals. Returns how many islands were widened."""
    islands, uv = _uv_islands(me, 'UVLightmap')
    uv = uv * scale
    wmin = LM_MIN_TEXELS / LM_EXPECT_DENSITY
    loop_vert = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get('vertex_index', loop_vert)
    face_of = np.empty(len(me.loops), np.int64)
    for p in me.polygons:
        face_of[p.loop_start:p.loop_start + p.loop_total] = p.index
    n = 0
    for loops in islands:
        q = uv[loops]
        # key each uv corner by (vertex, rounded uv): the island's uv vertices
        keys = {}
        for li in loops:
            keys.setdefault((int(loop_vert[li]), round(float(uv[li, 0]), 7), round(float(uv[li, 1]), 7)), []).append(li)
        # area and boundary (edges used once inside the island, in uv)
        area = 0.0
        edges = {}
        faces = sorted(set(int(face_of[li]) for li in loops))
        for fi in faces:
            p = me.polygons[fi]
            li = list(p.loop_indices)
            pts = uv[li]
            sa = 0.5 * float(np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1]))
            area += abs(sa)
            for k in range(len(li)):
                a_, b_ = li[k], li[(k + 1) % len(li)]
                ka = (int(loop_vert[a_]), round(float(uv[a_, 0]), 7), round(float(uv[a_, 1]), 7))
                kb = (int(loop_vert[b_]), round(float(uv[b_, 0]), 7), round(float(uv[b_, 1]), 7))
                e = (min(ka, kb), max(ka, kb))
                edges.setdefault(e, []).append((ka, kb, 1.0 if sa >= 0 else -1.0))
        bound = [v[0] for v in edges.values() if len(v) == 1]
        perim = sum(float(np.hypot(kb[1] - ka[1], kb[2] - ka[2])) for ka, kb, _ in bound)
        if perim <= 1e-9:
            continue
        wid = 2.0 * area / perim
        if wid >= wmin:
            continue
        delta = 0.5 * (wmin - wid)
        normals = {}
        for ka, kb, sg in bound:
            dx, dy = kb[1] - ka[1], kb[2] - ka[2]
            L = float(np.hypot(dx, dy))
            if L < 1e-12:
                continue
            nrm = np.array((dy, -dx)) / L * sg          # outward for a counter-clockwise face
            for k_ in (ka, kb):
                normals.setdefault(k_, []).append(nrm)
        for k_, ns in normals.items():
            if len(ns) == 2:                            # a mitre: both edges move out by exactly delta (capped at 3x)
                c_ = 1.0 + float(ns[0] @ ns[1])
                off = (ns[0] + ns[1]) / max(c_, 1.0 / 3.0) * delta
            else:
                v = np.sum(ns, 0)
                L = float(np.hypot(*v))
                off = v / L * delta if L > 1e-9 else np.zeros(2)
            for li in keys.get(k_, []):
                uv[li] += off
        # slivers the mitre cannot open (a quad folded or squashed flat in the box projection): stretch across the island's
        # narrow axis to the width instead
        d_ = uv[loops] - uv[loops].mean(0)
        if len(loops) >= 3:
            _, vecs = np.linalg.eigh(d_.T @ d_)
            t_ = d_ @ vecs[:, 0]
            ext = float(t_.max() - t_.min())
            if ext < wmin:
                k = wmin / max(ext, wmin / 25.0)
                uv[loops] = uv[loops].mean(0) + d_ + np.outer(t_ * (k - 1.0), vecs[:, 0])
        n += 1
    me.uv_layers['UVLightmap'].data.foreach_set('uv', uv.reshape(-1).astype(np.float32))
    return n


def uv1_lightmap_multi(objs, margin=LM_MARGIN):
    """one _CabinTubeLM atlas over several objects (Cabin_Static + the seats): each object's uv1 starts from its metric
    chart ('UVMetric' when its uv0 is a part atlas, else 'UVMap'), the pieces next to the hero eye get a denser chart
    (LM_NEAR), no island stays narrower than LM_MIN_TEXELS, then all islands are packed together."""
    widened = {}
    for ob in objs:
        me = ob.data
        if 'UVLightmap' not in me.uv_layers:
            me.uv_layers.new(name='UVLightmap')
        srcname = 'UVMetric' if 'UVMetric' in me.uv_layers else 'UVMap'
        src, dst = me.uv_layers[srcname].data, me.uv_layers['UVLightmap'].data
        for i in range(len(src)):
            dst[i].uv = src[i].uv
        widened[ob.name] = _lm_widen(me, LM_NEAR.get(ob.name, 1.0))
        me.uv_layers.active = me.uv_layers['UVLightmap']
    print('[finish] uv1: islands widened to %.0f texels: %d (%s)' % (LM_MIN_TEXELS, sum(widened.values()),
          ', '.join('%s %d' % kv for kv in widened.items() if kv[1])))
    sel(objs)
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
    for ob in objs:
        me = ob.data
        me.uv_layers.active = me.uv_layers['UVMap']
        me.uv_layers['UVMap'].active_render = True


def vertex_colours(ob, ao_samples=32):
    """R = grime (yellowed ceiling round the tubes, window-corner dust, floor edges), G = wear / polish, B = sun-fade +
    crack seeds. AO is in _CabinTubeLM.a."""
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
    # seat edges polished by thirty years of passengers (bible 4.2 '#6A3434, 0.62-0.70'): the cushion's front edge and the
    # backrest's top edge, where hands and knees go
    for sx, bz in seat_c:
        near = (np.abs(x - sx) < 0.45) & (np.abs(z - (bz + 0.25)) < 0.40)
        front_edge = np.clip(1 - np.abs(z - (bz + 0.50)) / 0.05, 0, 1) * np.clip(1 - np.abs(y - 1.0) / 0.08, 0, 1)
        top_edge = np.clip(1 - np.abs(y - 1.60) / 0.06, 0, 1) * (np.abs(z - bz) < 0.20)
        wear = np.maximum(wear, near * np.maximum(front_edge * 0.9, top_edge * 0.75))
    # the driver's seat is the oldest: polished all over its cushion
    dx_, dz_ = B.DRIVER_SEAT
    wear = np.maximum(wear, (np.abs(x - dx_) < 0.25) * (np.abs(z - dz_) < 0.25) * (N[:, 1] > 0.5) * (y > 0.9) * (y < 1.2) * 1.0)
    on_floor = (N[:, 1] > 0.9) & (np.abs(y - B.FLOOR_Y) < 0.01)
    # floor: the aisle band, worn most toward the door; the entry (door step top, between the guard panel and the dash)
    aisle = np.clip(1 - np.abs(x + 0.06) / 0.34, 0, 1) * on_floor
    wear = np.maximum(wear, aisle * (0.55 + 0.45 * np.clip((z - B.Z_REAR) / 6.0, 0, 1)))
    entry = on_floor * np.clip(1 - np.hypot((x - 0.32) / 0.32, (z - 2.80) / 0.40), 0, 1)
    wear = np.maximum(wear, entry)
    # dash: the front edge where hands rest (right of the wheel, the radio side) and in front of the driver
    on_dash = (y > 1.0) & (y < B.DASH_TOP + 0.02) & (z > B.DASH_Z0 - 0.02) & (z < B.DASH_Z0 + 0.12)
    wear = np.maximum(wear, on_dash * np.clip(1 - np.abs(x - B.WHEEL_C[0]) / 0.45, 0, 1) * 0.8)
    # lower walls: shoe scuffs (bible 4.2 '近地鞋痕 #5B5A55')
    kick = (np.abs(N[:, 1]) < 0.3) & (y < B.FLOOR_Y + 0.25) & (y > B.FLOOR_Y + 0.01)
    wear = np.maximum(wear, kick * np.clip(rng.random(len(P)) * 1.6 - 0.6, 0, 1) * 0.7)
    # R = grime: ceiling yellowed round the tubes; dust in the window-frame corners and on the sills; dirt where the
    # floor meets the walls and the seat feet
    grime = np.zeros(len(P), np.float32)
    on_ceil = (N[:, 1] < -0.6) & (y > 2.35)
    for tx, zl in ((B.TUBE_X[0], B.TUBE_Z_L), (B.TUBE_X[1], B.TUBE_Z)):
        z0_, z1_ = zl[0][0], zl[-1][1]
        dz = np.maximum(0, np.maximum(z0_ - z, z - z1_))
        d = np.hypot(np.abs(x - tx), dz)
        grime = np.maximum(grime, on_ceil * np.exp(-d / 0.22) * 0.85)
    for side, wins in ((1, B.WIN_R), (-1, B.WIN_L)):
        xw = B.XC + side * (B.W_HALF - 0.04)
        near_wall = np.abs(x - xw) < 0.10
        for z0_, z1_ in wins:
            for zc in (z0_, z1_):
                for yc, k in ((B.WIN_SILL, 1.0), (B.WIN_HEAD, 0.5)):
                    d = np.hypot(z - zc, y - yc)
                    grime = np.maximum(grime, near_wall * np.clip(1 - d / 0.10, 0, 1) * k)
            sill = near_wall * (np.abs(y - (B.WIN_SILL - 0.02)) < 0.035) * (z > z0_ - 0.03) * (z < z1_ + 0.03)
            grime = np.maximum(grime, sill * 0.35)
    xl_, xr_ = B.XC - B.W_HALF + 0.04, B.R_WALL - 0.04
    edge = on_floor * np.clip(1 - np.minimum(np.abs(x - xl_), np.abs(x - xr_)) / 0.14, 0, 1)
    grime = np.maximum(grime, edge * 0.8)
    grime = np.maximum(grime, (y < B.FLOOR_Y + 0.06) * (np.abs(N[:, 1]) < 0.3) * 0.5)      # the skirting
    ao = grime                                    # R channel (the name kept for the return value)
    col = np.stack([ao, wear, fade, np.ones_like(ao)], 1)
    for i, c in enumerate(ca.data):
        c.color = col[i].tolist()
    return dict(grime_mean=float(grime.mean()), wear_mean=float(wear.mean()))


def wiper_basis():
    """the pivots' Blender rotation. Unity basis: Y' = (1,0,0) (parked arm along +x), Z' = (0,0,1) (axis out of the
    glass, forward), X' = Y' x Z'. The export maps a Blender local frame (x, y, z) to Unity's (x, z, y) (U2B on both
    sides of the matrix), so the Blender columns are U2B(X'), U2B(Z'), U2B(Y'): a proper rotation (90 deg about
    Blender Y). (Until 10-31 the columns were U2B(X', Y', Z'), det -1: Unity got scale -1, transform.up along the bus
    and the sweep about x.)"""
    Xu, Yu, Zu = Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))
    return Matrix((BB.U2B(Xu), BB.U2B(Zu), BB.U2B(Yu))).transposed()


def wiper_pivot_fix(objs):
    """a .blend saved before wiper_basis(): each WiperPivot gets that basis, its arm keeps its world matrix. Returns
    the names changed."""
    want = wiper_basis()
    changed = []
    for p in [o for o in objs if o.name.startswith('WiperPivot')]:
        M = p.matrix_world
        if max(abs(M[i][j] - want[i][j]) for i in range(3) for j in range(3)) < 1e-6:
            continue
        kids = [(c, c.matrix_world.copy()) for c in p.children]
        p.matrix_world = Matrix.Translation(M.translation) @ want.to_4x4()
        for c, mw in kids:
            c.matrix_world = mw
        changed.append(p.name)
    bpy.context.view_layer.update()
    return changed


def wipers():
    """two pivots on the windscreen bottom: local +Y = parked arm direction (along the glass bottom), +Z = axis."""
    out = []
    for nm, px, d in (('L', B.XC - 1.00, 1.0), ('R', B.WS_POST[1] + 0.06, 1.0)):
        piv = bpy.data.objects.new('WiperPivot_' + nm, None)
        bpy.context.scene.collection.objects.link(piv)
        loc = BB.U2B((px, B.WS_BOT - 0.022, BB.front_z(px, B.WS_BOT - 0.022) + 0.03))
        piv.matrix_world = Matrix.Translation(loc) @ wiper_basis().to_4x4()
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


# D-36 part atlases: per seat type, the game mesh's uv0 = its own atlas (the same uvs on every instance of the type),
# baked from a high-quality build of the same seat (parts/seat.py quality 'high' + parts/materials.py)
PART_RES = {'SeatHero': 2048, 'SeatR': 2048, 'DriverSeat': 2048, 'SeatL': 1024, 'SeatLBox': 1024, 'RearBench': 1024}
PARTS_INFO = {}


def part_material(ptype):
    m = bpy.data.materials.get('M_Bus_Part_' + ptype)
    if m is None:
        m = BB.mat('Vinyl').copy()
        m.name = 'M_Bus_Part_' + ptype
    return m


def seat_parts(out, seat_groups, bake=True):
    from parts import seat as SEAT, materials as MATS, texbake as TB
    seats, by_type = [], {}
    joined = {}
    for inst, parts in seat_groups.items():
        ptype = parts[0]['lb_part']
        ob = join('Seat_' + inst, parts)
        ob['lb_part'] = ptype
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        set_origin(ob, sum(bb, Vector()) / 8)
        joined[inst] = ob
    # the seats of a type share one atlas, so they must have the same mesh. The decimated pads (seat.DECIMATE_PAD) are
    # not: the collapse order depends on float noise in the world positions (SeatL1 came out 2 loops off SeatL0). The
    # seats of a type differ only by a translation, so each takes the canonical seat's mesh at its own place.
    for inst, ob in joined.items():
        canon = joined.get(BB.SEAT_TYPES[ob['lb_part']]['inst'])
        if canon is None or canon is ob:
            continue
        bb0 = np.array([tuple(c) for c in ob.bound_box])
        old = ob.data
        ob.data = canon.data.copy()
        ob.data.name = ob.name
        bpy.data.meshes.remove(old)
        err = float(np.abs(np.array([tuple(c) for c in ob.bound_box]) - bb0).max())
        if err > 0.003:
            print('[finish] WARNING: %s differs from %s by %.1f mm (bounding box) - not just a translation?' % (ob.name, canon.name, 1000 * err))
    for inst, ob in joined.items():
        ptype = ob['lb_part']
        uv0_metric(ob)
        me = ob.data
        lay = me.uv_layers.new(name='UVMetric')
        for d, s_ in zip(lay.data, me.uv_layers['UVMap'].data):
            d.uv = s_.uv
        me.uv_layers.active = me.uv_layers['UVMap']
        seat_wear(ob, inst)
        out[ob.name] = ob
        seats.append(ob)
        by_type.setdefault(ptype, []).append(ob)
    for ptype, obs in by_type.items():
        canon = out['Seat_' + BB.SEAT_TYPES[ptype]['inst']]
        res = PART_RES.get(ptype, 1024)
        mpu = TB.unwrap(canon, res=res, keep_layers=True)
        src = canon.data.uv_layers['UVMap'].data
        for ob in obs:
            if ob is canon:
                continue
            dst = ob.data.uv_layers['UVMap'].data
            assert len(dst) == len(src), '%s: %d loops vs %d in %s' % (ob.name, len(dst), len(src), canon.name)
            for d, s_ in zip(dst, src):
                d.uv = s_.uv
        pm = part_material(ptype)
        for ob in obs:
            ob.data.materials.clear()
            ob.data.materials.append(pm)
            for p in ob.data.polygons:
                p.material_index = 0
        files = None
        if bake:
            kw = {k: v for k, v in BB.SEAT_TYPES[ptype].items() if k != 'inst'}
            # the shared atlas gets a light wear (0.6): seat_wear's per-seat vertex colour adds each seat's own, so a
            # little-used seat can stay lighter than the type (D-36: no two seats alike)
            kw['worn'] = kw.get('worn', 1.0) * 0.6
            high = SEAT.seat_module('High_' + ptype, quality='high', **kw)
            MATS.apply_details(high)
            files = TB.bake_onto(canon, high, ptype, res=res)
        PARTS_INFO[ptype] = dict(type=ptype, res=res, metres_per_uv=round(mpu, 5), instances=[o.name for o in obs],
                                 baked=bool(files))
    return seats


def seat_wear(ob, inst):
    """D-36 / 总导演 / D-40 #3: no two seats wear the same, and wear only comes from what touches the seat. Vertex colour
    on the seat object, read by Lanbai/Cabin's part materials on top of the shared type atlas (the atlas is baked with
    a light wear only, seat_parts): G polish where people sit (per-seat jittered places, the aisle place more than the
    window place, the hero row and the row behind the driver more), along the cushion's front roll (thighs) and the
    back's shoulder band; B sun-fade on the window side of the back's top and the cushion's window edge; R grime in the
    crease between cushion and back (crumbs and dust collect there - not a random dirt overlay); A which of the type's
    seam-crack candidates are open on this seat (2-5 of them, parts/seat.crack_on; the atlas mask B has their shapes).
    RGB only on the red vinyl (the cream piping, the black sleeve, the painted frame and board get no red tint); A on
    vinyl, piping and sleeve."""
    from parts import seat as SEAT
    kw = BB.SEAT_INSTS[inst]
    g = SEAT._geom(**kw)
    x0, x1 = kw['x0'], kw['x1']
    cy, z0c, z1c, H = g['cy'], g['z0c'], g['z1c'], g['H']
    O, Uax, Wax = g['F']
    ws = kw.get('wall_side', 0)
    rnd = np.random.default_rng(zlib.crc32(inst.encode()))
    use = float(rnd.uniform(0.55, 1.15)) * (1.25 if inst in ('SeatR0', 'SeatR1', 'SeatL0', 'DriverSeat') else 1.0)
    spots = SEAT._sit_spots(x0, x1, kw.get('double', False), ws, kw.get('places'))
    spots = [(xs + float(rnd.normal(0, 0.03)), w * float(rnd.uniform(0.7, 1.2))) for xs, w in spots]
    sites = SEAT.crack_sites(**{k: v for k, v in kw.items() if k != 'type'})
    open_ = [np.array(sites[i]) for i in SEAT.crack_on(inst, len(sites))]
    me = ob.data
    ca = me.color_attributes.get('Col') or me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    M = ob.matrix_world
    win_x = x1 if ws > 0 else x0
    slots = [m.name if m else '' for m in me.materials]
    red = np.zeros(len(me.vertices), bool)
    soft = np.zeros(len(me.vertices), bool)              # every leatherette: red vinyl, piping, sleeve (cracks)
    for p in me.polygons:
        nm = slots[p.material_index]
        if 'Vinyl' in nm:
            red[list(p.vertices)] = True
        if 'Vinyl' in nm or 'Piping' in nm or 'Sleeve' in nm:
            soft[list(p.vertices)] = True
    zm = (z0c + z1c) / 2
    for vi, (v, c) in enumerate(zip(me.vertices, ca.data)):
        if not soft[vi]:
            c.color = (0.0, 0.0, 0.0, 0.0)
            continue
        q = np.array(U(M @ v.co))
        a = 0.0
        for sp in open_:
            d2 = float(np.dot(q - sp, q - sp))
            if d2 < 0.0225:
                a = max(a, math.exp(-d2 / 0.05 ** 2))     # wide: it only gates the atlas's crack shape
        if not red[vi]:
            c.color = (0.0, 0.0, 0.0, a)
            continue
        x, y, z = q
        gp = r = b = 0.0
        if z0c - 0.01 < z < z1c + 0.03 and cy - SEAT.CUSH_T - 0.01 < y < cy + 0.03:          # the cushion
            for xs, w in spots:
                gp = max(gp, w * math.exp(-((x - xs) / 0.13) ** 2 - ((z - zm + 0.03) / 0.14) ** 2))
            gp = max(gp, 0.8 * math.exp(-((z - z1c) / 0.035) ** 2) * max(math.exp(-((x - xs) / 0.18) ** 2) for xs, _ in spots))
            r = max(r, 0.6 * math.exp(-((z - z0c) / 0.03) ** 2) * (1.0 if y > cy - 0.025 else 0.3))
            if ws != 0:
                b = max(b, 0.5 * math.exp(-((x - win_x) / 0.06) ** 2) * (1.0 if y > cy - 0.02 else 0.3))
        rel = q - O
        u, w_ = float(np.dot(rel, Uax)), float(np.dot(rel, Wax))
        if -0.04 < u < H + 0.03 and -0.02 < w_ < SEAT.BACK_D + 0.03:                        # the back
            gp = max(gp, 0.5 * math.exp(-((u - 0.82 * H) / 0.06) ** 2))                      # shoulders
            if ws != 0:
                b = max(b, math.exp(-((x - win_x) / 0.10) ** 2) * math.exp(-((u - H) / 0.07) ** 2))
            r = max(r, 0.5 * math.exp(-(u / 0.03) ** 2))                                      # the crease at its foot
        c.color = (min(1.0, r), min(1.0, gp * use), min(0.75, b * 0.7 * use), a)


# D-40 #1 the Unity slice (Bus/Editor/LanbaiBusSliceBuilder.cs: hero seat + hero side window + first right stanchion):
# like the D-36 seats, these leave Cabin_Static and are exported as their own objects. Only parts in the 'Cabin'
# collection: the exterior WinR1_Fillet / WinR1_Gasket ('Exterior') stay on the skin. (name, prefixes, exact names)
SEPARATE = (('Window_R1', ('WinR1_',), ()),                      # parts/window.py via build_bus.window_trim
            ('Pole_R0', ('PoleR0_',), ('PoleR0',)))              # parts/poles.py via build_bus.poles_and_guard
# BusLayout.json 'slice': what LanbaiBusSliceBuilder takes out of Bus.fbx (lists of FBX object names)
SLICE = dict(seat=['Seat_SeatR0'], window=['Window_R1', 'Glass_WinR1'], pillar=['Pole_R0'])


def separate_of(n, cols):
    if 'Cabin' not in cols:
        return None
    for name, prefixes, exact in SEPARATE:
        if n in exact or n.startswith(prefixes):
            return name
    return None


def separate_parts(out, sep_groups):
    """the SEPARATE objects: joined, origin at the bbox centre, uv0 = metric box projection (as in Cabin_Static).
    The 'UVMetric' copy is added after uv1_lightmap_multi (separate_metric_copy); lm_uv_order then checks the order
    Unity needs (UVLightmap second)."""
    obs = []
    for name, _, _ in SEPARATE:
        parts = sep_groups.get(name)
        if not parts:
            print('[finish] WARNING: no parts for %s (window_trim / poles_and_guard renamed?)' % name)
            continue
        ob = join(name, parts)
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        set_origin(ob, sum(bb, Vector()) / 8)
        uv0_metric(ob)
        out[name] = ob
        obs.append(ob)
    return obs


def separate_metric_copy(obs):
    for ob in obs:
        me = ob.data
        lay = me.uv_layers.get('UVMetric') or me.uv_layers.new(name='UVMetric')
        for d, s_ in zip(lay.data, me.uv_layers['UVMap'].data):
            d.uv = s_.uv
        me.uv_layers.active = me.uv_layers['UVMap']
        me.uv_layers['UVMap'].active_render = True


# Unity takes the FBX uv sets in Blender's layer order (uv0, uv1, uv2) and Lanbai/Cabin reads _CabinTubeLM from uv1,
# so every lightmapped separate object (on the joint pack with Cabin_Static, baked by bake_lightmap.py) carries its
# layers in this order. The D-36 seats get UVMetric before the pack (seat_parts: UVMap, UVMetric, UVLightmap = the
# metric chart on uv1, the bug the slice builder found); lm_uv_order puts them right. Cabin_Static has UVMap, UVLightmap.
LM_UV_ORDER = ('UVMap', 'UVLightmap', 'UVMetric')
LM_SEPARATE = ('Seat_', 'Window_', 'Pole_')


def lm_uv_order(objs):
    """Seat_* / Window_* / Pole_*: uv layers in LM_UV_ORDER (any other layer after those three, with a warning).
    Blender cannot move a uv layer, so from the first layer out of place on, the layers are read by name, removed and
    added again in order with the same uvs. Every script reads them by name (bake_lightmap.py 'UVLightmap', texbake
    'UVMap', the material nodes), so only the FBX order changes. Idempotent. Returns the names of the objects changed."""
    changed = []
    for ob in objs:
        if ob.type != 'MESH' or not ob.name.startswith(LM_SEPARATE):
            continue
        me = ob.data
        names = [l.name for l in me.uv_layers]
        if 'UVLightmap' not in names or 'UVMap' not in names:
            print('[finish] WARNING: %s has uv layers %s: no UVMap / UVLightmap, not on _CabinTubeLM' % (ob.name, names))
            continue
        want = [n for n in LM_UV_ORDER if n in names] + [n for n in names if n not in LM_UV_ORDER]
        if want[:3] != list(LM_UV_ORDER) or len(want) > 3:
            print('[finish] WARNING: %s has uv layers %s, wants exactly %s' % (ob.name, names, list(LM_UV_ORDER)))
        if names != want:
            k = next(i for i, (a, b) in enumerate(zip(names, want)) if a != b)
            uvs = {}
            for n in names[k:]:
                a = np.empty(2 * len(me.loops), np.float32)
                me.uv_layers[n].data.foreach_get('uv', a)
                uvs[n] = a
            for n in names[k:]:
                me.uv_layers.remove(me.uv_layers[n])
            for n in want[k:]:
                me.uv_layers.new(name=n, do_init=False).data.foreach_set('uv', uvs[n])
            got = [l.name for l in me.uv_layers]
            assert got == want, '%s: uv layers %s after the reorder, wanted %s' % (ob.name, got, want)
            changed.append(ob.name)
        me.uv_layers.active = me.uv_layers['UVMap']
        me.uv_layers['UVMap'].active_render = True
    return changed


# D-48 (director 10-26): the hero row's head fill - front-upper-right of the hero seat (with the tubes and the window), so
# the hero's hands and body sit ~0.3 EV under the mid-cabin heads (hands -0.30, lap -0.36, chest -0.25, head -0.15 EV;
# before it -1.2 .. -1.6 EV), with Unity's vertex point-light attenuation 1 / (1 + 25 d^2 / r^2). Lights only avatars.
HERO_FILL = ((0.95, 1.95, 3.35), 0.646, 5.0)        # position (unity), intensity, range


# D-36 budget: every seat gets two lighter copies, Seat_<inst>_LOD1 (50 %) and _LOD2 (25 %); LanbaiBusBuild puts the
# three in one LODGroup (LOD1 from about 3 m, LOD2 from about 8 m)
SEAT_LODS = ((1, 0.5), (2, 0.25))


def seat_lods(objs):
    """Seat_<inst>_LOD1 / _LOD2: the seat collapse-decimated, uvs, uv1 and the per-seat colour carried along by the
    collapse. Checked by rendering the albedo atlas (and _CabinTubeLM on uv1) on LOD0 and on the copy from the same
    camera: SeatR at 3 m on LOD1 differs by 0.7 / 255 on average (p99 11), at 8 m on LOD2 by 1.0 (p99 11). Made at
    export, after bake_lightmap.py is done with the .blend, so the copies never shadow their LOD0 in the light map."""
    made = []
    for ob in [o for o in objs if o.type == 'MESH' and o.name.startswith('Seat_') and '_LOD' not in o.name]:
        for k, ratio in SEAT_LODS:
            c = ob.copy()
            c.data = ob.data.copy()
            c.name = c.data.name = '%s_LOD%d' % (ob.name, k)
            bpy.context.scene.collection.objects.link(c)
            md = c.modifiers.new('dec', 'DECIMATE')
            md.ratio = ratio
            BB.apply_mods(c)
            made.append(c)
    return made


def build_all(ao_samples, bake_parts=True):
    BB.build(open_door=True)
    objs = {o.name: o for o in bpy.data.objects}
    body = objs['Body']
    outer, inner = split_body(body)
    groups = {'ext': [], 'static': [], 'tubes': [], 'radio': [], 'blind': [], 'curt': [], 'door': [], 'glass': [], 'wheel': {}, 'wiper': [],
              'seat': {}, 'sep': {}}
    for o in list(bpy.data.objects):
        if o.type != 'MESH':
            continue
        n = o.name
        cols = [c.name for c in o.users_collection]
        if 'lb_part' in o:                     # D-36 seat module: one object per seat, its own part atlas
            groups['seat'].setdefault(o['lb_inst'], []).append(o)
        elif 'Door' in cols:
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
        elif separate_of(n, cols):             # D-40 #1 slice pieces (were part of Cabin_Static)
            groups['sep'].setdefault(separate_of(n, cols), []).append(o)
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
        # per-PANEL constants (review r2: a world-cell hash tore panels that crossed a cell): uv1 = rail midpoint
        # (x, z), uv2 = (rail y, panel random 0..1). ThinCloth's phase, release spread and eye cap read these.
        ws = np.array([U(M @ v.co) for v in me.vertices])
        mid = (ws.min(0) + ws.max(0)) / 2
        rnd = (zlib.crc32(o.name.encode()) % 10007) / 10007.0                 # deterministic (hash() is salted)
        for nm_, val in (('UVPanel', (mid[0], mid[2])), ('UVPanel2', (2.20, rnd))):
            lay = me.uv_layers.new(name=nm_)
            for d_ in lay.data:
                d_.uv = val
        me.uv_layers.active = me.uv_layers['UVMap']
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
        # the panes are their own Glass_DoorK (Lanbai/BusGlass in Unity, review r2: joined in they became opaque
        # Lanbai/Cabin slabs); the build script parents each to its Bus_DoorK so the act-11 close carries it
        panes = [o for o in parts if o.name.startswith('Glass_')]
        parts = [o for o in parts if not o.name.startswith('Glass_')]
        if panes:
            g = join('Glass_' + pid, panes)
            bb = [g.matrix_world @ Vector(c) for c in g.bound_box]
            set_origin(g, sum(bb, Vector()) / 8)
            out[g.name] = g
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
    seats = seat_parts(out, groups['seat'], bake_parts)
    info['parts'] = PARTS_INFO
    sep = separate_parts(out, groups['sep'])
    uv1_lightmap_multi([out['Cabin_Static']] + seats + sep)
    separate_metric_copy(sep)
    info['uv_order_fixed'] = lm_uv_order(seats + sep)      # before the .blend is saved: the bake and --from-blend see it
    info['vc'] = vertex_colours(out['Cabin_Static'], ao_samples)
    # the separate pieces get the same position-driven vertex colours they had inside Cabin_Static (window-corner
    # dust on the frame, wear by the seats)
    info['vc_separate'] = {ob.name: vertex_colours(ob, ao_samples) for ob in sep}
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


def dest_blind_uv(db):
    # the destination blind: uv0 = 0..1 over the blind, u left -> right as seen from OUTSIDE (Bus_DestBlind_1024x296.png)
    uvl = db.data.uv_layers['UVMap'].data
    x0, x1, y0, y1 = B.DEST_BOX
    for p in db.data.polygons:
        for li in p.loop_indices:
            w = U(db.matrix_world @ db.data.vertices[db.data.loops[li].vertex_index].co)
            uvl[li].uv = ((x1 - w[0]) / (x1 - x0), (w[1] - y0) / (y1 - y0))


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
                               intensity=0.5, range=6.0,
                               note='圣经 §4.3：座位处灰卡 #585F64，强度 × _Udon_CabinLightmap') for x in B.TUBE_X] +
                         [dict(pos=list(HERO_FILL[0]), colour='#E4F1F3', render_mode='Not Important', culling='Player + PlayerLocal',
                               intensity=HERO_FILL[1], range=HERO_FILL[2],
                               note='D-48（总导演 10-26）：主座位那一排的补光，从前上方偏右来；主座位上的手和身体比车厢中段的头像暗约 0.3 EV'
                                    '（Unity 逐顶点点光的衰减 1 / (1 + 25 d² / r²) 算的）。只照人（Player 层），座垫上不会有新亮斑和影子')],
        bus=dict(model='PAZ-672 (D-28)', centre_x=B.XC, width=2 * B.W_HALF, length=B.Z_FRONT - B.Z_REAR, height=B.Y_TOP,
                 bounds_min=[B.XC - B.W_HALF, 0.0, B.Z_REAR], bounds_max=[B.R_WALL, 2.80, B.Z_FRONT + 0.12]),
        radio=dict(centre=list(B.RADIO_C), az_el=[-20, -12]), steering_wheel=dict(centre=list(B.WHEEL_C), tilt_deg=B.WHEEL_TILT),
        seats=seats, seat_count=len(seats), colliders=cols,
        cabin_bounds=dict(min=[B.XC - B.W_HALF + 0.05, B.FLOOR_Y - 0.05, B.Z_REAR + 0.06], max=[B.R_WALL - 0.05, B.CEIL_Y, B.Z_FRONT - 0.06],
                          note='D-31：车厢内部的范围（给 LB_Journey.busMin / busMax）；Director 按玩家根位置检查，头探出玻璃 ≤ 0.6 m 不算离开'),
        instance_cap_note='D-31：实例人数上限 = seat_count（不算司机座）',
        objects=sorted(out.keys()),
        slice=dict(SLICE, missing=[n for v in SLICE.values() for n in v if n not in out],
                   note='D-40 #1：菜单「蓝白/Build/车 切片」（Bus/Editor/LanbaiBusSliceBuilder.cs）从 Bus.fbx 里取这几个物体，'
                        '车局部坐标不变（车在原点）。missing 不空 = 这个 FBX 是旧的，要重跑 finish_bus.py'),
    )


# Unity's FBX import mirrors x: Unity = (-x, y, z) of the file (FromLocal 10-26, views/bus_axes_before.txt). export_unity
# ('-Z' forward, 'Y' up) writes Blender (x, y, z) as (x, z, -y), so Bus.fbx came in turned 180 deg about Y (Seat_SeatR0
# at (-0.65, 1.18, -2.02), BusLayout's hero station at (0.55, 1.03, 2.12)). Bus.fbx is written from the scene turned by
# R_UNITY (180 deg about Blender Z = Unity Y, through the origin): Unity then sees U(Blender). The file's axes header
# stays the standard Y-up one (what Unity does with another is unknown). The harness shell is read by Blender's
# importer, which honours that header, so it is exported unturned.
R_UNITY = Matrix.Diagonal((-1.0, -1.0, 1.0, 1.0))
U4 = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))     # U on a frame: Unity matrix = U4 M U4


def _flip(m):
    """R_UNITY @ m @ R_UNITY for a 4x4: the entries with exactly one of row, column in x / y change sign (exact)."""
    m = m.copy()
    for i in range(4):
        for j in range(4):
            if (i < 2) != (j < 2):
                m[i][j] = -m[i][j]
    return m


def _vsum(me):
    co = np.empty(3 * len(me.vertices), np.float32)
    me.vertices.foreach_get('co', co)
    return zlib.crc32((co + np.float32(0)).tobytes())          # + 0: -0.0 and 0.0 count the same


def turn_for_unity(objs, back=None):
    """R_UNITY on objs for the Bus.fbx export: matrix_world -> R M R for each object (and its parents), each mesh by R
    once. Done on the local transforms (location and euler x, y change sign, the parent inverse is conjugated, scale
    stays): every local rotation stays as authored (the doors, the wiper pivots and the wheels turn at runtime on top
    of it; a baked 180 deg would be overwritten) and a second call restores the scene bit for bit. back = what the
    first call returned: the second call asserts every matrix_world and each mesh's vertex checksum are back."""
    vl = bpy.context.view_layer
    vl.update()
    obs = []
    for o in objs:
        while o is not None and o not in obs:
            obs.append(o)
            o = o.parent
    meshes = []
    for o in obs:
        if o.type == 'MESH' and o.data not in meshes:
            meshes.append(o.data)
    first = back is None
    if first:
        back = dict(M={o.name: np.array(o.matrix_world) for o in objs}, v={me.name: _vsum(me) for me in meshes})
    for o in obs:
        assert not o.constraints and (o.parent is None or o.parent_type == 'OBJECT'), o.name
        o.location = (-o.location.x, -o.location.y, o.location.z)
        o.delta_location = (-o.delta_location.x, -o.delta_location.y, o.delta_location.z)
        for k in ('rotation_euler', 'delta_rotation_euler'):
            e = getattr(o, k)
            setattr(o, k, (-e.x, -e.y, e.z))
        for k in ('rotation_quaternion', 'delta_rotation_quaternion'):
            q = getattr(o, k)
            setattr(o, k, (q.w, -q.x, -q.y, q.z))
        a_ = o.rotation_axis_angle
        o.rotation_axis_angle = (a_[0], -a_[1], -a_[2], a_[3])
        o.matrix_parent_inverse = _flip(o.matrix_parent_inverse)
    for me in meshes:
        me.transform(R_UNITY, shape_keys=True)
        me.update()
    vl.update()
    Rn = np.array(R_UNITY)
    if first:                                                  # turned: R M R
        err = max(float(np.abs(np.array(o.matrix_world) - Rn @ back['M'][o.name] @ Rn).max()) for o in objs)
        assert err < 1e-5, 'turn_for_unity: matrix_world off R M R by %.2g' % err
    else:                                                      # back: M, exactly
        moved = [o.name for o in objs if not np.array_equal(np.array(o.matrix_world), back['M'][o.name])]
        assert not moved, 'turn_for_unity: matrix_world not restored: %s' % moved[:5]
        changed = [me.name for me in meshes if _vsum(me) != back['v'][me.name]]
        assert not changed, 'turn_for_unity: vertices not restored: %s' % changed[:5]
    return back


# what Unity makes of Bus.fbx, from Blender's re-import: Blender reads the standard header (Y up, -Z forward) as
# Blender = (x, -z, y) of the file and Unity mirrors x, so a point read back at p is at C_UNITY p in Unity, and a node
# read back with matrix_world W (its mesh data = the file's) has the Unity matrix C_UNITY W S_UNITY. Checked against
# 阿白's measurements on the unturned Bus.fbx (Seat_SeatR0, Window_R1, Pole_R0, Bus_Door0 bounds to 0.1 mm).
C_UNITY = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
S_UNITY = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
FBX_AXES = dict(UpAxis=1, UpAxisSign=1, FrontAxis=2, FrontAxisSign=1, CoordAxis=0, CoordAxisSign=1)


def fbx_axes(path):
    """the axes header (GlobalSettings) of an FBX."""
    import addon_utils
    addon_utils.enable('io_scene_fbx')
    from io_scene_fbx import parse_fbx
    root, _ = parse_fbx.parse(path)
    gs = next(e for e in root.elems if e.id == b'GlobalSettings')
    p70 = next(e for e in gs.elems if e.id == b'Properties70')
    return {e.props[0].decode(): e.props[4] for e in p70.elems if e.props[0].decode() in FBX_AXES}


def unity_pose(W):
    """position, eulerAngles (Unity's: Quaternion.Euler(x, y, z) = Ry Rx Rz), lossy scale of a Unity matrix (a mirror
    shows as scale -1, the way Blender's decompose and the FBX write it)."""
    M3 = W.to_3x3()
    sc = np.array([M3.col[k].length for k in range(3)]) * (-1 if M3.determinant() < 0 else 1)
    R = np.array([[M3[i][j] / sc[j] for j in range(3)] for i in range(3)])
    eul = (math.degrees(math.asin(max(-1.0, min(1.0, -R[1, 2])))), math.degrees(math.atan2(R[0, 2], R[2, 2])),
           math.degrees(math.atan2(R[1, 0], R[1, 1])))
    return [round(v, 5) for v in W.translation], [round(v % 360.0, 3) % 360.0 for v in eul], [round(float(v), 5) for v in sc], R


def readback(path, expect, lay):
    """Bus.fbx read back with Blender's importer and mapped to what Unity will see (C_UNITY; world = the model at the
    origin, identity): per object the Unity bounds against U(the Blender model), the Unity matrix against U4 M U4 (so
    a baked turn shows), the pose, the uv / colour layers; under '_unity' the axes header, the hero seat against
    BusLayout (as LanbaiBusBuild's AlignModelToLayout tests it), the door panels with BusLayout's open / closed poses
    (as LanbaiCabinDriver.WriteDoor sets them), the wiper pivots' frame (LanbaiWipers: +Y = arm at rest, +Z = axis)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)                    # the axes come from the file's header
    got = {o.name: o for o in bpy.data.objects}
    rep = {}
    pts = {}
    for nm, ex in expect.items():
        o = got.get(nm)
        if o is None:
            rep[nm] = 'MISSING'
            continue
        W = C_UNITY @ o.matrix_world @ S_UNITY
        merr = max(abs(W[i][j] - ex['unity_matrix'][i][j]) for i in range(3) for j in range(4))
        pos, eul, sc, _ = unity_pose(W)
        r = dict(unity_position=pos, unity_euler=eul, unity_scale=sc, matrix_err=round(merr, 6))
        if o.type == 'MESH':
            co = np.empty(3 * len(o.data.vertices), np.float64)
            o.data.vertices.foreach_get('co', co)
            M = np.array(C_UNITY @ o.matrix_world)
            p = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
            pts[nm] = p
            lo, hi = p.min(0), p.max(0)
            err = float(max(np.max(np.abs(lo - ex['bounds'][0])), np.max(np.abs(hi - ex['bounds'][1]))))
            r.update(verts=len(o.data.vertices), verts_expected=ex['verts'], bbox_err_m=round(err, 5),
                     unity_bounds=[[round(float(v), 4) for v in lo], [round(float(v), 4) for v in hi]],
                     uv_layers=[l.name for l in o.data.uv_layers], colours=[c.name for c in o.data.color_attributes])
        rep[nm] = r
    chk = dict(axes=fbx_axes(path), axes_expected=FBX_AXES)
    hero = next((s for s in lay['seats'] if s['hero']), None)
    if hero and 'Seat_' + hero['name'] in pts:
        p = pts['Seat_' + hero['name']]
        c = (p.min(0) + p.max(0)) / 2
        want = np.array((hero['x'], hero['back_z'] + 0.25))
        chk['hero_seat'] = dict(name='Seat_' + hero['name'], centre_xz=[round(float(c[0]), 4), round(float(c[2]), 4)],
                                layout_xz=want.tolist(), direct_m=round(float(np.hypot(*(c[[0, 2]] - want))), 4),
                                reversed_m=round(float(np.hypot(*(-c[[0, 2]] - want))), 4))
    doors = []
    for d in lay.get('door_panels', []):
        o = got.get(d['name'])
        if o is None or d['name'] not in pts:
            continue
        W = C_UNITY @ o.matrix_world @ S_UNITY
        pos, eul, sc, Rq = unity_pose(W)
        y0 = math.radians(d['open']['yaw_deg'])
        Ro = np.array([[math.cos(y0), 0, math.sin(y0)], [0, 1, 0], [-math.sin(y0), 0, math.cos(y0)]])
        # LanbaiCabinDriver.WriteDoor: localPosition = closed.position, localRotation = open rotation * Euler(0, yaw, 0)
        y1 = math.radians(d['closed']['yaw_deg'])
        Ry = np.array([[math.cos(y1), 0, math.sin(y1)], [0, 1, 0], [-math.sin(y1), 0, math.cos(y1)]])
        loc = (pts[d['name']] - np.array(pos)) @ Rq                    # Unity local x scale
        q = loc @ (Rq @ Ry).T + np.array(d['closed']['position'])
        doors.append(dict(name=d['name'], closed_position=d['closed']['position'],
                          open_pos_err_m=round(float(np.abs(np.array(pos) - d['open']['position']).max()), 5),
                          open_rot_err=round(float(np.abs(Rq - Ro).max()), 5),
                          closed_x=[round(float(q[:, 0].min()), 4), round(float(q[:, 0].max()), 4)],
                          closed_z=[round(float(q[:, 2].min()), 4), round(float(q[:, 2].max()), 4)]))
    chk['door_panels'] = doors
    wip = []
    for nm in ('WiperPivot_L', 'WiperPivot_R'):
        o = got.get(nm)
        arm = [k for k in pts if o is not None and got[k].parent == o]
        if o is None or not arm:
            continue
        pos, eul, sc, Rq = unity_pose(C_UNITY @ o.matrix_world @ S_UNITY)
        p = pts[arm[0]]
        far = p[np.argmax(np.linalg.norm(p - np.array(pos), axis=1))] - np.array(pos)   # the blade's far end
        wip.append(dict(name=nm, arm=arm[0], scale=sc, up=[round(float(v), 4) for v in Rq[:, 1]],
                        forward=[round(float(v), 4) for v in Rq[:, 2]],
                        up_dot_arm=round(float(Rq[:, 1] @ far / np.linalg.norm(far)), 4)))
    chk['wiper_pivots'] = wip
    rep['_unity'] = chk
    return rep


def readback_problems(rep, lay):
    bad = [k for k, v in rep.items() if v == 'MISSING']
    obs = {k: v for k, v in rep.items() if isinstance(v, dict) and not k.startswith('_')}
    # what Unity will see: bounds and transforms in BusLayout's frame (the 180 deg turn of 10-26 shows here as ~4 m)
    bad += ['%s Unity bbox off by %.3f m' % (k, v['bbox_err_m']) for k, v in obs.items() if v.get('bbox_err_m', 0) > 0.002]
    bad += ['%s Unity transform off by %.4f' % (k, v['matrix_err']) for k, v in obs.items() if v['matrix_err'] > 0.002]
    bad += ['%s verts %d < %d' % (k, v['verts'], v['verts_expected']) for k, v in obs.items()
            if 'verts' in v and v['verts'] < v['verts_expected']]
    # what Unity will see: uv1 = UVLightmap on every lightmapped separate object (read back from the FBX)
    bad += ['%s uv %s' % (k, v['uv_layers']) for k, v in obs.items()
            if k.startswith(LM_SEPARATE) and 'uv_layers' in v and v['uv_layers'] != list(LM_UV_ORDER)]
    # what Unity will see: mesh.colors = the first colour set, which must be 'Col'
    bad += ['%s colours %s' % (k, v['colours']) for k, v in obs.items() if v.get('colours') and v['colours'][0] != 'Col']
    chk = rep.get('_unity', {})
    if chk.get('axes') != FBX_AXES:
        bad.append('FBX axes header %s, not the standard %s' % (chk.get('axes'), FBX_AXES))
    h = chk.get('hero_seat')
    if h is None or h['direct_m'] > 0.5:
        bad.append('hero seat vs BusLayout: %s' % h)
    if len(chk.get('door_panels', [])) != len(lay.get('door_panels', [])):
        bad.append('door panels missing: %s' % [d['name'] for d in chk.get('door_panels', [])])
    for d in chk.get('door_panels', []):
        z0 = d['closed_position'][2]
        # closed: in the wall plane (x = R_WALL), from closed.position forward by one panel
        if d['open_pos_err_m'] > 0.002 or d['open_rot_err'] > 1e-3 or max(abs(x - B.R_WALL) for x in d['closed_x']) > 0.03 \
                or not (z0 - 0.01 < d['closed_z'][0] and d['closed_z'][1] < z0 + B.DOOR_PANEL + 0.03):
            bad.append('door %s: %s' % (d['name'], d))
    if len(chk.get('wiper_pivots', [])) != 2:
        bad.append('wiper pivots / arms missing: %s' % chk.get('wiper_pivots'))
    for w in chk.get('wiper_pivots', []):
        if min(w['scale']) < 0 or w['up_dot_arm'] < 0.95 or abs(w['forward'][2]) < 0.95:
            bad.append('wiper %s frame: %s' % (w['name'], w))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'Models'))
    ap.add_argument('--ao-samples', type=int, default=32)
    ap.add_argument('--blend', default='/tmp/bus/bus_final.blend')
    ap.add_argument('--from-blend', default=None, help='export only: re-export the FBX from a finished .blend (after the '
                    'lightmap bake and the exterior weathering added their uv1 atlases)')
    ap.add_argument('--no-part-bake', action='store_true', help='D-36: unwrap the part atlases but keep the textures '
                    'already in Bus/Textures/Parts (the unwrap is deterministic)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.from_blend:
        bpy.ops.wm.open_mainfile(filepath=a.from_blend)
        objs = [o for o in bpy.data.objects if o.type == 'MESH' or o.name.startswith('WiperPivot')]
        out = {o.name: o for o in objs if not o.name.startswith('Wiper')}
        # a .blend saved before the uv order fix (seats UVMap, UVMetric, UVLightmap): same uvs, only the order changes,
        # so the light map baked from it stays valid
        info = dict(uv_order_fixed=lm_uv_order(objs))
    else:
        out, extra, info = build_all(a.ao_samples, bake_parts=not a.no_part_bake)
        bpy.context.scene['lb_parts'] = json.dumps(PARTS_INFO)
        os.makedirs(os.path.dirname(a.blend), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=a.blend)
        objs = list(out.values()) + extra
    door_rows = door_pivots({o.name: o for o in objs})
    lods = seat_lods(objs)
    objs += lods
    # every mesh gets a vertex colour: without one Unity feeds white and Lanbai/Cabin reads full grime / wear / fade
    # (review r2). Zero = clean; Cabin_Static and the curtains keep theirs.
    for o in objs:
        if o.type == 'MESH' and 'Col' not in o.data.color_attributes:
            ca = o.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
            for c in ca.data:
                c.color = (0.0, 0.0, 0.0, 1.0)
    # Unity imports only the FIRST vertex colour set of an FBX mesh: drop every set but 'Col' (the D-36 parts carry
    # 'Zone', the Blender-only authoring channel that drives their detail materials), so mesh.colors is always 'Col'
    for o in objs:
        if o.type == 'MESH':
            for ca in [c for c in o.data.color_attributes if c.name != 'Col']:
                o.data.color_attributes.remove(ca)
            if 'Col' in o.data.color_attributes:
                o.data.color_attributes.active_color = o.data.color_attributes['Col']
                o.data.color_attributes.render_color_index = list(o.data.color_attributes).index(o.data.color_attributes['Col'])
    if 'Cabin_DestBlind' in out:
        dest_blind_uv(out['Cabin_DestBlind'])
    # the render harness shell 'paz672' (Engineering/render_harness: --bus fbx:Bus/Models/Bus_HarnessShell_paz672.fbx):
    # everything but the glass (an FBX glass imports opaque there) and the LOD copies. Blender reads it: not turned.
    shell = [o for o in objs if o.type == 'MESH' and not o.name.startswith('Glass_') and not o.name.endswith(('_LOD1', '_LOD2'))]
    export_fbx(os.path.join(a.out, 'Bus_HarnessShell_paz672.fbx'), shell)
    # a .blend from before wiper_basis(): the pivots for Bus.fbx (after the shell: it has no pivots, its arms stay as
    # they were, bit for bit)
    info['wiper_pivots_fixed'] = wiper_pivot_fix(objs)
    fbx = os.path.join(a.out, 'Bus.fbx')
    back = turn_for_unity(objs)                 # R_UNITY: Unity sees U(Blender)
    try:
        export_fbx(fbx, objs)
    finally:
        turn_for_unity(objs, back)              # and back, checked, before the layout and the readback
    # what Unity must see: U(the Blender model)
    expect = {}
    for o in objs:
        ex = dict(verts=0, bounds=None, unity_matrix=[list(r) for r in U4 @ o.matrix_world @ U4])
        if o.type == 'MESH':
            co = np.empty(3 * len(o.data.vertices), np.float64)
            o.data.vertices.foreach_get('co', co)
            M = np.array(U4 @ o.matrix_world)
            p = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
            ex.update(verts=len(o.data.vertices), bounds=(p.min(0), p.max(0)))
        expect[o.name] = ex
    lay = layout(out)
    lay['door_panels'] = door_rows
    # D-36 part atlases (LanbaiBusBuild: M_Bus_Part_<type> -> _UsePart, Textures/Parts/Part_<type>_*_<res>.png;
    # the leather grain detail tiles at metres_per_uv / 0.30 on the atlas uv)
    lay['parts'] = list(json.loads(bpy.context.scene.get('lb_parts', '{}')).values())
    lay['stats'] = {o.name: dict(verts=len(o.data.vertices), tris=sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in objs if o.type == 'MESH'}
    lay['stats_total_tris'] = sum(v['tris'] for v in lay['stats'].values())
    # what is drawn up close: every LOD0 (the LOD1 / LOD2 copies take over only further away)
    lay['stats_lod0_tris'] = sum(v['tris'] for k, v in lay['stats'].items() if not k.endswith(('_LOD1', '_LOD2')))
    lay['seat_lods'] = dict(ratios={'LOD%d' % k: r for k, r in SEAT_LODS}, objects=[o.name for o in lods])
    json.dump(lay, open(os.path.join(a.out, 'BusLayout.json'), 'w'), ensure_ascii=False, indent=1)
    rep = readback(fbx, expect, lay)
    json.dump(rep, open(os.path.join(a.out, 'Bus_fbx_readback.json'), 'w'), ensure_ascii=False, indent=1)
    bad = readback_problems(rep, lay)
    print('[finish] %d objects, %d tris total (%d in LOD0), readback problems: %s, %s'
          % (len(objs), lay['stats_total_tris'], lay['stats_lod0_tris'], bad or 'none', info))
    if bad:                                     # never silently (set -e in the chain stops here)
        sys.exit('[finish] READBACK FAILED: %d problems (Bus_fbx_readback.json)' % len(bad))


if __name__ == '__main__':
    main()
