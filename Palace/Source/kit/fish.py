# -*- coding: utf-8 -*-
"""银鱼：一条鱼的网格（≈ 60 三角）+ 运动（**与 Lanbai/PalaceFish 的顶点 shader 逐行对应**，参考图和 Unity 同一套数学）。
运动：
  A 群（前 1350 条）：绕大殿的环面（中心 C、环半径 35、管半径 9），0.03 转/秒；分 6 小群，每群在管里缓慢螺旋。
  B 群（后 150 条）：河伯诗那一刻（≈720）从诗句前面游过一次（从右往左，2.2 m/s），之后远去（|t − 720| > 90 s 不画）。
lite 模式：只画前 700 条（A 群的一部分），B 群照画（它是一次性的构图）。"""
import math

import numpy as np

from .common import UB

N, N_A = 1500, 1350
REV = 0.03
SCHOOLS = 6


def hash4(i):
    """与 shader 的 frac(sin(...)) 哈希同式（float 精度下会有很小的差，不影响）。"""
    i = np.asarray(i, float)
    h = lambda k: np.modf(np.abs(np.sin(i * (12.9898 + k * 3.17) + 78.233 * (k + 1)) * 43758.5453))[0]
    return h(0), h(1), h(2), h(3)


def template(lod=0):
    """鱼：沿 +z（鼻子朝 +z），长 1（shader 里乘 12–20 cm），侧扁。返回 UB。"""
    u = UB()
    st = [(-0.50, 0.00, 0.00), (-0.38, 0.05, 0.09), (-0.15, 0.08, 0.15), (0.10, 0.085, 0.16), (0.32, 0.06, 0.12), (0.48, 0.02, 0.05)]
    m = 6
    V = []
    for z, w, h in st:
        for j in range(m):
            a = 2 * math.pi * j / m
            V.append((w * math.cos(a), h * math.sin(a), z))
    F = []
    for i in range(len(st) - 1):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            F.append((a, a + m, b + m, b))
    tip = len(V)
    V.append((0, 0, 0.52))
    for j in range(m):
        F.append(((len(st) - 1) * m + j, tip, (len(st) - 1) * m + (j + 1) % m))
    # 尾鳍：一片竖的三角（两面）
    t0 = len(V)
    V += [(0, 0, -0.48), (0, 0.13, -0.68), (0, -0.13, -0.68)]
    F += [(t0, t0 + 1, t0 + 2), (t0, t0 + 2, t0 + 1)]
    P = np.array(V)
    UV = [[((P[k][2] + 0.7) / 1.25, (P[k][1] + 0.2) / 0.4) for k in f] for f in F]
    u.add(V, F, 'Fish', UV)
    return u


def state(t, idx, centre, R=35.0, tube=9.0, poem_pt=None, v_pass=(-2.2, 0.1, 0.4)):
    """第 idx 条鱼在 t 时刻的位置、朝向（单位向量）、长度、可见（宫殿坐标）。"""
    idx = np.asarray(idx)
    r1, r2, r3, r4 = hash4(idx)
    L = 0.12 + 0.08 * r2
    C = np.asarray(centre, float)
    sch = idx % SCHOOLS
    th = 2 * math.pi * sch / SCHOOLS + 0.35 * (r1 - 0.5) + 2 * math.pi * REV * t + 0.02 * np.sin(0.7 * t + 6.283 * r3)
    ph = 2 * math.pi * sch / SCHOOLS * 1.7 + 0.15 * t + 1.2 * (r3 - 0.5)
    rho = 2.0 + (tube - 2.0) * np.sqrt(r4)
    ring = R + rho * np.cos(ph)
    pos = np.stack([C[0] + ring * np.cos(th), C[1] + rho * np.sin(ph), C[2] + ring * np.sin(th)], -1)
    # 速度方向（数值导数，shader 里用解析式）
    dth, dph = 2 * math.pi * REV, 0.15
    vel = np.stack([-ring * np.sin(th) * dth - rho * np.sin(ph) * dph * np.cos(th),
                    rho * np.cos(ph) * dph,
                    ring * np.cos(th) * dth - rho * np.sin(ph) * dph * np.sin(th)], -1)
    vis = np.ones(idx.shape, bool)
    b = idx >= N_A
    if poem_pt is not None and b.any():
        off = np.stack([(r1 - 0.5) * 6.0, (r2 - 0.5) * 2.4, (r3 - 0.5) * 4.0], -1)
        V = np.asarray(v_pass, float)
        pb = np.asarray(poem_pt, float) + (t - 720.0) * V + off
        pos = np.where(b[..., None], pb, pos)
        vel = np.where(b[..., None], V, vel)
        vis = np.where(b, abs(t - 720.0) <= 90.0, vis)
    d = vel / np.linalg.norm(vel, axis=-1, keepdims=True)
    return pos, d, L, vis


def place(t, centre, poem_pt, n=N):
    """参考渲染用：把 n 条鱼摆成一个 UB（宫殿坐标）。"""
    tmpl = template()
    pos, d, L, vis = state(t, np.arange(n), centre, poem_pt=poem_pt)
    u = UB()
    up = np.array([0.0, 1.0, 0.0])
    for i in range(n):
        if not vis[i]:
            continue
        f = d[i]
        r = np.cross(up, f)
        r /= np.linalg.norm(r) + 1e-9
        uu = np.cross(f, r)
        Mx = np.stack([r, uu, f], 1) * L[i]
        u.merge(tmpl.transformed(Mx, pos[i]))
    return u
