# -*- coding: utf-8 -*-
"""宫殿套件的公共约定（每个模块都 import 它）。

坐标：模块一律在 **Unity 轴的模块局部坐标**里写（x 右、y 上、z 前，米），**“正面”朝 −z**（朝来车的方向）。
地面 y = 0（模块落在自己的地面上）。UB.build() 换算成 Blender（Blender = (−x, −z, y)），绕向自动翻正。
材质：只用下面 SLOTS 里的名字（= Unity 里的材质名去掉 M_07b_ 前缀），一个面一个槽。
UV0：世界尺度平铺 —— 1 UV 单位 = 该材质贴图一个平铺的边长 TILE[slot]（米）。用 UB 的 box / quad 自动给，
     自己写的面用 uv_planar / uv_cyl。UV1（光照贴图）由 Unity 导入时生成，不用管。
"""
import math

import numpy as np

SLOTS = ['Lacquer', 'LacquerBlack', 'LacquerBand', 'Gilt', 'Bronze', 'Verdigris', 'Stone', 'StoneDark',
         'FishScale', 'Cowrie', 'Tile', 'Wood', 'Rock', 'Weed', 'Fish', 'DoorGlow', 'StoneWet']   # StoneWet：殿前湿台阶（终审 10-25 #4）
TILE = {'Lacquer': 2.0, 'LacquerBlack': 2.0, 'LacquerBand': 4.0, 'Gilt': 1.0, 'Bronze': 0.5, 'Verdigris': 0.5,
        'Stone': 4.0, 'StoneDark': 4.0, 'FishScale': 2.0, 'Cowrie': 1.0, 'Tile': 3.0, 'Wood': 2.0, 'Rock': 8.0,
        'Weed': 1.0, 'Fish': 1.0, 'DoorGlow': 4.0, 'StoneWet': 4.0}
def palace_frame():
    """海的宫殿约定（Act07_Sea/PalaceFrame_约定.json）；环境变量 PALACE_FRAME 可指到另一份（例如 pkg/sea 上还没合的新约定）。"""
    import json
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    pinned = os.path.normpath(os.path.join(here, '..', 'PalaceFrame_约定_pkg_sea_f85c4b8.json'))
    p = (os.environ.get('PALACE_FRAME') or (pinned if os.path.exists(pinned) else None)
         or os.path.normpath(os.path.join(here, '..', '..', '..', 'Act07_Sea', 'PalaceFrame_约定.json')))
    return json.load(open(p, encoding='utf-8'))


U2B = np.array([[-1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])


class UB:
    """攒几何（Unity 模块坐标）。V: 顶点；F: 面（逆时针 = 从外面看，Unity 左手系里写成从外看顺时针也行——
    这里约定：按“从外面看逆时针”给，在 Unity 左手系里就是正面朝外；build 时统一处理）。"""

    def __init__(self):
        self.V, self.F, self.S, self.UV = [], [], [], []

    # ---- 低层
    def add(self, V, F, slot, UV=None):
        """V (n,3) Unity 坐标；F 面列表（从外面看逆时针，右手法则法线朝外 —— 按 Unity 坐标当成右手系来想即可）；
        UV 每个面一组 (len(face), 2)，None = 按面的法线自动三向投影。"""
        assert slot in SLOTS, slot
        o = len(self.V)
        V = np.asarray(V, float)
        self.V.extend([tuple(v) for v in V])
        for k, f in enumerate(F):
            self.F.append(tuple(int(i) + o for i in f))
            self.S.append(SLOTS.index(slot))
            if UV is not None:
                self.UV.append([tuple(u) for u in UV[k]])
            else:
                self.UV.append(auto_uv(V[list(f)], TILE[slot]))

    def box(self, lo, hi, slot, skip=()):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        V = np.array([[lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]], [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
                      [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]]])
        faces = {'-z': (0, 3, 2, 1), '+z': (4, 5, 6, 7), '-y': (0, 1, 5, 4), '+y': (2, 3, 7, 6), '+x': (1, 2, 6, 5), '-x': (0, 4, 7, 3)}
        F = [f for k, f in faces.items() if k not in skip]
        self.add(V, F, slot)

    def quad(self, a, b, c, d, slot):
        self.add([a, b, c, d], [(0, 1, 2, 3)], slot)

    def tri(self, a, b, c, slot):
        self.add([a, b, c], [(0, 1, 2)], slot)

    def transformed(self, M=None, t=(0, 0, 0)):
        """返回一个变换过的副本（M 3×3，t 平移；det(M) < 0 时自动翻绕向）。"""
        M = np.eye(3) if M is None else np.asarray(M, float)
        u = UB()
        u.V = [tuple(M @ np.asarray(v) + np.asarray(t, float)) for v in self.V]
        u.F = [tuple(reversed(f)) if np.linalg.det(M) < 0 else f for f in self.F]
        u.UV = [list(reversed(uv)) if np.linalg.det(M) < 0 else uv for uv in self.UV]
        u.S = list(self.S)
        return u

    def merge(self, other):
        o = len(self.V)
        self.V.extend(other.V)
        self.F.extend([tuple(i + o for i in f) for f in other.F])
        self.S.extend(other.S)
        self.UV.extend(other.UV)

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    # ---- 建 Blender 物体
    def build(self, name, collection=None, materials=None):
        import bpy
        Vb = (U2B @ np.asarray(self.V, float).T).T if self.V else np.zeros((0, 3))
        # Unity → Blender 是反射（det −1），所以绕向要翻
        Fb = [tuple(reversed(f)) for f in self.F]
        UVb = [list(reversed(uv)) for uv in self.UV]
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in Vb], [], Fb)
        used = sorted(set(self.S))
        for s in used:
            m = (materials or {}).get(SLOTS[s]) or bpy.data.materials.get('M_07b_' + SLOTS[s]) or bpy.data.materials.new('M_07b_' + SLOTS[s])
            me.materials.append(m)
        me.polygons.foreach_set('material_index', [used.index(s) for s in self.S])
        uvl = me.uv_layers.new(name='UVMap')
        flat = [c for uv in UVb for c in uv]
        uvl.data.foreach_set('uv', [x for c in flat for x in c])
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        return ob


def auto_uv(P, tile):
    """面的三向投影（按面法线的主轴），米 / tile。"""
    P = np.asarray(P, float)
    n = np.cross(P[1] - P[0], P[2] - P[0])
    if len(P) > 3:
        n = n + np.cross(P[2] - P[0], P[3] - P[0])
    ax = int(np.argmax(np.abs(n)))
    if ax == 0:
        uv = P[:, [2, 1]] * np.array([np.sign(n[0]) or 1, 1])
    elif ax == 1:
        uv = P[:, [0, 2]]
    else:
        uv = P[:, [0, 1]] * np.array([-(np.sign(n[2]) or 1), 1])
    return [tuple(u) for u in uv / tile]


def lathe(profile, n, slot, ub, center=(0, 0, 0), angle0=0.0, cap_top=False, cap_bottom=False, tile=None):
    """回转体：profile = [(r, y), ...] 从下到上；n 段。UV：u = 弧长 / tile，v = 母线长 / tile。"""
    tile = tile or TILE[slot]
    cx, cy, cz = center
    prof = np.asarray(profile, float)
    m = len(prof)
    ang = angle0 + np.linspace(0, 2 * math.pi, n + 1)
    V, UV, F = [], [], []
    s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(prof[:, 0]), np.diff(prof[:, 1])))])
    for i in range(n + 1):
        for j in range(m):
            r, y = prof[j]
            V.append((cx + r * math.cos(ang[i]), cy + y, cz + r * math.sin(ang[i])))
    rmax = max(prof[:, 0].max(), 1e-3)
    for i in range(n):
        for j in range(m - 1):
            a, b, c, d = i * m + j, (i + 1) * m + j, (i + 1) * m + j + 1, i * m + j + 1
            F.append((a, d, c, b))
            u0, u1 = rmax * (ang[i] - angle0) / tile, rmax * (ang[i + 1] - angle0) / tile
            UV.append([(u0, s[j] / tile), (u0, s[j + 1] / tile), (u1, s[j + 1] / tile), (u1, s[j] / tile)])
    ub.add(V, F, slot, UV)
    for cap, j, flip in ((cap_bottom, 0, False), (cap_top, m - 1, True)):
        if cap and prof[j, 0] > 1e-4:
            r, y = prof[j]
            ring = [(cx + r * math.cos(a), cy + y, cz + r * math.sin(a)) for a in ang[:-1]]
            c = (cx, cy + y, cz)
            for i in range(n):
                f = (c, ring[(i + 1) % n], ring[i]) if flip else (c, ring[i], ring[(i + 1) % n])
                ub.tri(*f, slot)


def hip_roof(ub, x0, x1, z0, z1, y0, h, slot, ridge_ratio=None):
    """四阿顶（直坡）。四个坡面（不含底），法线朝外上。"""
    tmp = UB()
    _hip(tmp, x0, x1, z0, z1, y0, h, slot, ridge_ratio)
    tmp.F = [tuple(reversed(f)) for f in tmp.F]
    tmp.UV = [list(reversed(uv)) for uv in tmp.UV]
    ub.merge(tmp)


def _hip(ub, x0, x1, z0, z1, y0, h, slot, ridge_ratio=None):
    w, d = x1 - x0, z1 - z0
    if w >= d:
        r = d / 2 if ridge_ratio is None else ridge_ratio
        A, B, C, D = (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)
        E, Fp = (x0 + r, y0 + h, (z0 + z1) / 2), (x1 - r, y0 + h, (z0 + z1) / 2)
        ub.add([A, B, Fp, E], [(0, 1, 2, 3)], slot)
        ub.add([C, D, E, Fp], [(0, 1, 2, 3)], slot)
        ub.add([D, A, E], [(0, 1, 2)], slot)
        ub.add([B, C, Fp], [(0, 1, 2)], slot)
    else:
        r = w / 2
        A, B, C, D = (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)
        E, Fp = ((x0 + x1) / 2, y0 + h, z0 + r), ((x0 + x1) / 2, y0 + h, z1 - r)
        ub.add([A, B, E], [(0, 1, 2)], slot)
        ub.add([C, D, Fp], [(0, 1, 2)], slot)
        ub.add([D, A, E, Fp], [(0, 1, 2, 3)], slot)
        ub.add([B, C, Fp, E], [(0, 1, 2, 3)], slot)
