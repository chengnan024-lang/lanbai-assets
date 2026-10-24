# -*- coding: utf-8 -*-
"""导出 Unity 用的 FBX（Palace/Models/）。导出设置 = Tentacles/Source/lib/export_unity.py（Blender Z-up → Unity Y-up，
旋转 0 / 缩放 1）。**所有网格的顶点都在宫殿坐标里**（R_Palace 的局部），物体变换为单位：搭建脚本把它们挂在 R_Palace 下、
局部变换不动。每个 FBX 里每个 LOD 一个物体 <名>_LOD0 / _LOD1（Unity 只在 FBX 根上建 LODGroup，§6 第 4 条 → 搭建脚本自己建）。
UV 通道（Unity 的 uv / uv2 / uv3）：
  一般网格：UV0 = 世界尺度贴图坐标；uv2 由 Unity 导入时生成（光照贴图）。
  海草：UV0、UV1（占位，导入时被光照贴图 UV 覆盖）、UV2 = (沿草高度, 相位)。
  鱼：UV0 = 鱼身、UV1.x = 鱼的编号（不生成光照贴图 UV）。
  灯焰：UV0 = 角（−1..1）、UV1 = (0 火 / 1 晕, 相位)（不生成光照贴图 UV）。
~/bpy/bin/python export_fbx.py [组名 ...]"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Tentacles', 'Source', 'lib'))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import bl  # noqa: E402
import palace_layout as L  # noqa: E402
from export_unity import export_fbx  # noqa: E402
from kit import fish, lamp, terrace, weed  # noqa: E402
from kit.common import UB, SLOTS  # noqa: E402

OUT = os.path.join(REPO, 'Palace', 'Models')
STATS = {}


def mats():
    return {s: (bpy.data.materials.get('M_07b_' + s) or bpy.data.materials.new('M_07b_' + s)) for s in SLOTS}


def place(ub, pos, yaw_deg=0.0):
    a = math.radians(yaw_deg)
    R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    return ub.transformed(R, pos)


def add_uv(ob, name, per_loop):
    me = ob.data
    l = me.uv_layers.new(name=name)
    l.data.foreach_set('uv', [c for uv in per_loop for c in uv])


def write(name, objs):
    path = os.path.join(OUT, name + '.fbx')
    export_fbx(path, objs)
    STATS[name] = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
    print('wrote', path, STATS[name])


def chunks(items, key, n):
    items = sorted(items, key=key)
    k = math.ceil(len(items) / n)
    return [items[i:i + k] for i in range(0, len(items), k)]


def g_terrace(M):
    a = terrace.build(0).build('Terrace_LOD0', None, M)
    b = terrace.build(1).build('Terrace_LOD1', None, M)
    write('Palace_Terrace', [a, b])


def g_weeds(M):
    u, sway = weed.build(L.WEEDS)
    ob = u.build('Weeds_LOD0', None, M)
    flat = [uv for f in u.UV for uv in reversed(f)]          # build() 把每个面的角反序了，UV 跟着反
    add_uv(ob, 'UVLightmap', flat)
    sw = [s for f in sway for s in reversed(f)]
    add_uv(ob, 'UVSway', sw)
    write('Palace_Weeds', [ob])


def g_lamps(M):
    groups = chunks(L.LAMPS, lambda l: (l['pos'][2], l['pos'][0]), 6)
    objs = []
    for gi, g in enumerate(groups):
        for lod in (0, 1):
            u = UB()
            for l in g:
                u.merge(place(lamp.build(l['height_m'], lod), l['pos'], 90.0 if l['pos'][0] > L.AXIS_X else -90.0))
            objs.append(u.build('Lamps%d_LOD%d' % (gi, lod), None, M))
    write('Palace_Lamps', objs)


def g_module(M, mod, name):
    m = importlib.import_module('kit.' + mod)
    objs = [m.build(lod=0).build(name + '_LOD0', None, M), m.build(lod=1).build(name + '_LOD1', None, M)]
    write('Palace_' + name, objs)


def g_houses(M):
    house = importlib.import_module('kit.house')
    idx = list(range(len(L.HOUSES)))
    groups = chunks(idx, lambda i: L.HOUSES[i]['pos'][2], 4)
    objs = []
    for gi, g in enumerate(groups):
        for lod in (0, 1):
            u = UB()
            for i in g:
                h = L.HOUSES[i]
                w, hh, d = h['size']
                u.merge(place(house.build(w, hh, d, lod=lod, seed=i), h['pos'], h['yaw_deg'] + 180.0))
            objs.append(u.build('Houses%d_LOD%d' % (gi, lod), None, M))
    write('Palace_Houses', objs)


def g_fish(M):
    tm = fish.template()
    u = UB()
    ids = []
    for i in range(fish.N):
        u.merge(tm)
        ids += [[(float(i), 0.0)] * len(f) for f in tm.F]
    ob = u.build('Fish_LOD0', None, M)
    add_uv(ob, 'UVFish', [c for f in ids for c in f])
    write('Palace_Fish', [ob])


def g_flames(M):
    V, F, uv0, uv1 = [], [], [], []
    for k, l in enumerate(L.LAMPS):
        c = l['flame_pos']
        ph = (k * 0.618034) % 1.0
        for kind in (0.0, 1.0):
            o = len(V)
            V += [c, c, c, c]
            F.append((o, o + 1, o + 2, o + 3))
            uv0.append([(-1, -1), (1, -1), (1, 1), (-1, 1)])
            uv1.append([(kind, ph)] * 4)
    u = UB()
    u.add(V, F, 'DoorGlow', uv0)                     # 槽名无所谓，搭建脚本换成 M_07b_Flame
    ob = u.build('Flames_LOD0', None, M)
    add_uv(ob, 'UVKind', [c for f in uv1 for c in reversed(f)])
    write('Palace_Flames', [ob])


def g_door(M):
    H = L.HALL
    x0, x1 = H['door_x'] - H['door_size'][0] / 2, H['door_x'] + H['door_size'][0] / 2
    y0 = L.PLAT['height_m']
    y1 = y0 + H['door_size'][1]
    z = L.DOOR_Z + 5.0
    # 门里的光（第 4 轮）是大殿网格里 DoorGlow 槽的暗腔内衬，这里只导出门口的 3 张锥形光卡
    cones = door_cones_ub().build('DoorCones_LOD0', None, M)
    write('Palace_Door', [cones])


def door_cones_ub():
    """3 张门口的锥形光卡：从门口向外（−z）20 m，顺着台阶往下铺；UV.y = 沿锥 0..1。"""
    H = L.HALL
    y0 = L.PLAT['height_m']
    c = UB()
    zc = L.DOOR_Z - 0.3
    for k, ang in enumerate((-7.0, 0.0, 7.0)):
        a = math.radians(ang)
        w0, w1 = H['door_size'][0] * 0.45, H['door_size'][0] * 1.6
        dirx, dirz = math.sin(a) * 0.35, -1.0
        n = math.hypot(dirx, dirz)
        dirx, dirz = dirx / n * 20.0, dirz / n * 20.0
        yb = y0 + 0.05
        yt = y0 + H['door_size'][1] * 0.9
        # 两张斜的：从门洞中部起，顺着台阶斜下来铺到阶前的地上（y 0），向两侧张开一点
        ym = y0 + H['door_size'][1] * 0.45
        quad = [(H['door_x'] - w0, ym, zc), (H['door_x'] + w0, ym, zc),
                (H['door_x'] + dirx + w1, y0 - 5.6, zc + dirz), (H['door_x'] + dirx - w1, y0 - 5.6, zc + dirz)]
        # 竖的那张：从门洞的上沿斜下来铺到地上
        if k == 1:
            quad = [(H['door_x'] - w0, yt, zc), (H['door_x'] + w0, yt, zc), (H['door_x'] + w1, y0 - 5.8, zc - 20.0), (H['door_x'] - w1, y0 - 5.8, zc - 20.0)]
        c.add(quad, [(0, 1, 2, 3)], 'DoorGlow', [[(0, 0), (1, 0), (1, 1), (0, 1)]])
    return c


def g_specks(M):
    """PalaceSpecks_Points：远处被淹没的城的灯点（海的约定 specks：240 个，x −650…−60、y 0.5…30、z −150…900）。
    网格约定 = Lanbai/SeaSpecks（海的 shader 头注）：每点 4 个顶点同一位置、UV0 = 角（−1..1）；UV1 = (flux, 半径 m)；
    COLOR rgb = 线性颜色、a = 闪烁量（0：远处的灯是稳的）；UV2 = (闪烁相位, Hz)。金 #E0A860 在 S7b 下的线性值 (1.396, 0.536, 0.142)
    （海 README §2.6）：FBX 的顶点色进 Unity 会被夹到 1，所以颜色归一成 (1, 0.384, 0.102)、亮度 1.396 乘进 flux：12 × 1.396。"""
    S = L.FRAME['specks']
    rg = S['region']
    rng = np.random.default_rng(97)
    n = S['count']
    pts = []
    while len(pts) < n:
        p = [rng.uniform(*rg['x']), rng.uniform(*rg['y']), rng.uniform(*rg['z'])]
        # 小群：灯点三五成团（远处的街巷），不要均匀的雨
        if rng.random() < 0.6 and pts:
            q = pts[rng.integers(len(pts))]
            p = [q[0] + rng.normal(0, 6), max(rg['y'][0], q[1] + rng.normal(0, 1.5)), q[2] + rng.normal(0, 6)]
        pts.append(p)
    V, F, uv0, uv1 = [], [], [], []
    for k, c in enumerate(pts):
        o = len(V)
        V += [c, c, c, c]
        F.append((o, o + 1, o + 2, o + 3))
        uv0.append([(-1, -1), (1, -1), (1, 1), (-1, 1)])
        uv1.append([(12.0 * 1.396, 0.3)] * 4)
    u = UB()
    u.add(V, F, 'DoorGlow', uv0)
    ob = u.build('PalaceSpecks_Points', None, M)
    add_uv(ob, 'UVFlux', [c for f in uv1 for c in reversed(f)])
    add_uv(ob, 'UVFlicker', [((k // 4) * 0.618034 % 1.0, 0.0) for k in range(4 * len(F))])
    me = ob.data
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    gold = (1.0, 0.536 / 1.396, 0.142 / 1.396, 0.0)
    ca.data.foreach_set('color', list(gold) * len(me.loops))
    path = os.path.join(OUT, 'PalaceSpecks_Points.fbx')
    export_fbx(path, [ob])
    STATS['PalaceSpecks_Points'] = {ob.name: len(F) * 2}
    print('wrote', path)


GROUPS = {'specks': g_specks, 'terrace': g_terrace, 'weeds': g_weeds, 'lamps': g_lamps, 'fish': g_fish, 'flames': g_flames, 'door': g_door,
          'hall': lambda M: g_module(M, 'hall', 'Hall'), 'que': lambda M: g_module(M, 'que', 'Que'), 'houses': g_houses}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    which = [a for a in sys.argv[1:] if not a.startswith('-')] or list(GROUPS)
    import json
    for w in which:
        bl.reset()
        M = mats()
        try:
            GROUPS[w](M)
        except ModuleNotFoundError as e:
            print('skip', w, e)
    sp = os.path.join(OUT, 'tri_counts.json')
    old = json.load(open(sp)) if os.path.exists(sp) else {}
    old.update(STATS)
    json.dump(old, open(sp, 'w'), indent=1, ensure_ascii=False)
