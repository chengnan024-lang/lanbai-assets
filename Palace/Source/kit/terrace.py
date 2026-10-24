# -*- coding: utf-8 -*-
"""台地（宫殿坐标，绝对）：顶面 y = 0；崖口 x = −8，竖直石壁到下缘 y = −13；**下缘以下没有底面**（D-17 / D-29）。
从下面看不许有切开的边：下缘处石壁向里卷进去 6 m、再往上收 4 m，收口藏在 _Udon_PalaceVeil 的雾带里（带 = y −13..0）。
神道铺石：x −28.5…−8.5，z 42.4…334.1，高出 0.12 m。顶面其余是起伏很小的淤泥地（Rock）。"""
import math

import numpy as np

from .common import UB


def _noise(x, z, seed=0):
    r = np.random.default_rng(seed)
    k = r.normal(size=(6, 4))
    v = 0.0
    for i in range(6):
        f = 0.02 * 1.9 ** i
        v += math.sin(f * (k[i, 0] * x + k[i, 1] * z) + k[i, 2] * 6) * (0.55 ** i)
    return v


def build(lod=0, edge_x=-8.0, lip_y=-13.0, z0=-120.0, z1=520.0, x_far=-260.0):
    u = UB()
    # ---- 顶面：x 方向从崖口到远处，z 方向全长。网格密度：崖口附近密
    dz = 8.0 if lod == 0 else 32.0
    zs = np.arange(z0, z1 + 0.01, dz)
    xs = np.array([edge_x, edge_x - 1.0, -28.5, -34, -45, -60, -85, -120, -170, x_far])
    H = np.zeros((len(xs), len(zs)))
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            if x <= -34:
                H[i, j] = 0.35 * _noise(x, z, 1) * min(1.0, (-34 - x) / 20)
    V = [(x, H[i, j], z) for i, x in enumerate(xs) for j, z in enumerate(zs)]
    F = []
    nz = len(zs)
    for i in range(len(xs) - 1):
        for j in range(nz - 1):
            a = i * nz + j
            F.append((a, a + 1, a + nz + 1, a + nz))
    tmp = UB()
    tmp.add(V, F, 'Rock')
    _orient_up(tmp)
    u.merge(tmp)
    # ---- 神道铺石（抬高 0.12，四周有边）
    u.box((-28.5, 0.0, 42.4), (-8.5, 0.12, 334.1), 'Stone', skip=('-y',))
    # ---- 崖壁：x = edge_x，从 y 0 到 lip_y，带起伏（横向 1–2 m 的岩石凸凹）；下缘往里卷
    rows = [0.0, -0.6, -2.0, -4.0, -6.5, -9.0, -11.0, -12.4, lip_y]
    dzw = 4.0 if lod == 0 else 16.0
    zw = np.arange(z0, z1 + 0.01, dzw)
    def wx(y, z):
        if y >= -0.01:
            return edge_x
        a = 1.2 * _noise(y * 3.0, z, 7) + 0.6 * _noise(z, y * 5.0, 9)
        return edge_x + 0.25 + 0.45 * a        # 石壁略向外凸出、起伏（≥ 8 m 离眼睛：眼 x 0.55，石壁 ≤ −7）
    curl = []        # 第 2 轮：下缘不往里卷（卷进去的面从下面挡住了宫灯）。下缘是参差的岩口，见下面 lip_jag
    Vw, Fw = [], []
    prof = [(y, None) for y in rows] + [(y, dx) for (y, dx) in curl]
    for (y, dx) in prof:
        for z in zw:
            x = wx(y, z) if dx is None else edge_x + dx + 0.3 * _noise(z, y, 11)
            if y <= lip_y + 1e-3:
                # 参差的岩口：下缘高度沿 z 起伏 ±1.2 m，并且往里收 0.6 m（不是一刀切的直边）
                y = lip_y + 1.2 * _noise(z * 1.7, 3.0, 13)
                x = x - 0.6
            Vw.append((min(x, edge_x + 0.9), y, z))
    m = len(zw)
    for i in range(len(prof) - 1):
        for j in range(m - 1):
            a = i * m + j
            Fw.append((a, a + m, a + m + 1, a + 1))
    tmp = UB()
    tmp.add(Vw, Fw, 'Rock')
    # 朝外（+x，朝深渊）；卷进去的部分朝下 / 朝外
    P = np.array(Vw)
    f = Fw[m // 2]
    n = np.cross(P[f[1]] - P[f[0]], P[f[3]] - P[f[0]])
    if n[0] < 0:
        tmp.F = [tuple(reversed(x)) for x in tmp.F]
        tmp.UV = [list(reversed(x)) for x in tmp.UV]
    u.merge(tmp)
    # 两端封口（z0、z1 的石壁端面），免得从斜下方看见内部
    for zz, sgn in ((z0, -1), (z1, 1)):
        q = [(edge_x, 0.0, zz), (x_far, 0.0, zz), (x_far, lip_y, zz), (edge_x, lip_y, zz)]
        u.add(q, [(0, 1, 2, 3) if sgn < 0 else (0, 3, 2, 1)], 'Rock')
    return u


def _orient_up(u):
    P = np.array(u.V)
    f = u.F[0]
    n = np.cross(P[f[1]] - P[f[0]], P[f[3]] - P[f[0]])
    if n[1] < 0:
        u.F = [tuple(reversed(x)) for x in u.F]
        u.UV = [list(reversed(x)) for x in u.UV]
