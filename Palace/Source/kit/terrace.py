# -*- coding: utf-8 -*-
"""台地（宫殿坐标，绝对）：顶面 y = 0；崖口 x = −8，顶边风化成斜坡（最后 0.8 m 往下 1.6 m，终审 10-25 #3），竖直石壁到下缘 y = −13；**下缘以下没有底面**（D-17 / D-29）。
从下面看不许有切开的边：下缘处石壁向里卷进去 6 m、再往上收 4 m，收口藏在 _Udon_PalaceVeil 的雾带里（带 = y −13..0）。
神道铺石：x −28.5…−8.5，z 42.4…334.1，高出 0.12 m。顶面其余是起伏很小的淤泥地（Rock）。"""
import math

import numpy as np

from .common import UB, palace_frame

import os

CHAMFER_W, CHAMFER_D = 0.8, 1.6
# 复核 r10c 的试样（总导演未定）：PALACE_CHAMFER="3.5,6" 把崖口斜坡加大到“最后 3.5 m 往下 6 m”——
# 神道左移 3.0 m 以后近列灯离崖口 4 m，下唇以下看它的视线在崖口处低于崖顶，被石壁挡住
BIG = [float(v) for v in os.environ['PALACE_CHAMFER'].split(',')] if os.environ.get('PALACE_CHAMFER') else None
PAVE_X0 = palace_frame()['avenue']['paving']['x'][0]


def _noise(x, z, seed=0):
    r = np.random.default_rng(seed)
    k = r.normal(size=(6, 4))
    v = 0.0
    for i in range(6):
        f = 0.02 * 1.9 ** i
        v += math.sin(f * (k[i, 0] * x + k[i, 1] * z) + k[i, 2] * 6) * (0.55 ** i)
    return v


def _ss(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def slope_wd(z):
    """崖口斜坡在 z 处的（宽 W、深 D）。默认处处 0.8 / 1.6。
    PALACE_CHAMFER="W,D"（复核 r10c 的 A，总导演 10-26 要的试样）：只在神道灯那一段（z 约 50…300）加大，
    阙（Que_R 阙基外侧到 x −8.05、z 36…47）和台基（x 到 −11、z 325 起）那里不动，两头 6–10 m 过渡；
    宽、深沿 z 慢慢起伏（被水蚀的崖边，不是挖出来的一道坡）。"""
    if not BIG:
        return CHAMFER_W, CHAMFER_D
    w = _ss(48.0, 54.0, z) * (1.0 - _ss(296.0, 306.0, z))
    n1, n2 = _noise(z, 3.0, 21), _noise(z * 1.3, 7.0, 23)
    W = 0.8 + w * (BIG[0] - 0.8 + 0.3 * min(1.0, abs(n1)))      # 坡顶最多退到 x −11.8，近列灯（x −12）站在坡顶后面
    D = 1.6 + w * (BIG[1] - 1.6 + 0.6 * abs(n2))
    return W, D


def _profile(k):
    """斜坡的剖面：k 0 在坡顶、1 在坡底（崖口）。坡顶是圆的（前 15% 从平慢慢转下去），下面是直坡。"""
    kr = 0.15
    s = k * k / (2 * kr) if k < kr else k - kr / 2
    return s / (1 - kr / 2)


def build(lod=0, edge_x=-8.0, lip_y=-13.0, z0=-120.0, z1=520.0, x_far=-260.0):
    u = UB()
    # ---- 顶面：x 方向从崖口到远处，z 方向全长。网格密度：崖口附近密
    dz = (8.0 if not BIG else 2.0) if lod == 0 else 32.0
    zs = np.arange(z0, z1 + 0.01, dz)
    # 终审 10-25 #3：崖口顶边是风化的斜坡（最后 W m 往下 D m），不是直角——从下唇以下按真位置看，
    # 离崖口 1 m 的那一列灯焰正好越过崖顶（深度不作弊；眼睛在 −29 m 以上都看得见），远处那一列照样被台地挡住。
    ks = (1.0, 0.5, 0.0) if not BIG else (1.0, 0.9, 0.8, 0.65, 0.5, 0.35, 0.22, 0.12, 0.05, 0.0)
    Wmax = max(slope_wd(z)[0] for z in zs)
    xfix = [x for x in [PAVE_X0, -34, -45, -60, -85, -120, -170, x_far] if x < edge_x - Wmax - 1.0]
    nx = len(ks) + 1 + len(xfix)
    X = np.zeros((nx, len(zs)))
    H = np.zeros((nx, len(zs)))
    for j, z in enumerate(zs):
        W, D = slope_wd(z)
        col = [edge_x - W * (1 - k) for k in ks] + [edge_x - W - (0.2 if not BIG else 0.6)] + xfix
        for i, x in enumerate(col):
            X[i, j] = x
            if x <= -34:
                H[i, j] = 0.35 * _noise(x, z, 1) * min(1.0, (-34 - x) / 20)
            elif i < len(ks):
                k = ks[i]
                if not BIG:
                    H[i, j] = -D * k ** 1.5 + 0.08 * _noise(z, 2.0, 5) * k
                else:
                    H[i, j] = -D * _profile(k) + (0.08 + 0.25 * (W > 1.5)) * _noise(z * 1.7, 2.0 + 3 * k, 5) * math.sin(math.pi * k)
    xs = X
    V = [(X[i, j], H[i, j], z) for i in range(nx) for j, z in enumerate(zs)]
    F = []
    nz = len(zs)
    for i in range(nx - 1):
        for j in range(nz - 1):
            a = i * nz + j
            F.append((a, a + 1, a + nz + 1, a + nz))
    tmp = UB()
    tmp.add(V, F, 'Rock')
    _orient_up(tmp)
    u.merge(tmp)
    # ---- 神道铺石（抬高 0.12，四周有边）
    pv = palace_frame()['avenue']['paving']                 # 第 10 轮 (c)：按海的约定
    u.box((pv['x'][0], 0.0, pv['z'][0]), (min(pv['x'][1], edge_x - Wmax), 0.12, pv['z'][1]), 'Stone', skip=('-y',))   # 铺石不伸到斜坡上
    # ---- 崖壁：x = edge_x，从 y 0 到 lip_y，带起伏（横向 1–2 m 的岩石凸凹）；下缘往里卷
    rows = [-2.4, -4.0, -6.5, -9.0, -11.0, -12.4, lip_y]
    dzw = (4.0 if not BIG else 2.0) if lod == 0 else 16.0
    zw = np.arange(z0, z1 + 0.01, dzw)
    def wx(y, z, D):
        if y >= -D - 0.01:
            return edge_x
        a = 1.2 * _noise(y * 3.0, z, 7) + 0.6 * _noise(z, y * 5.0, 9)
        ramp = min(1.0, (-D - y) / 4.4)      # 坡底往下 4.4 m 内凸凹从 0 长到满：凸出的岩不挡越过崖顶的视线
        return edge_x + ramp * (0.25 + 0.45 * a)     # 石壁略向外凸出、起伏（≥ 8 m 离眼睛：眼 x 0.55，石壁 ≤ −7）
    curl = []        # 第 2 轮：下缘不往里卷（卷进去的面从下面挡住了宫灯）。下缘是参差的岩口，见下面 lip_jag
    Vw, Fw = [], []
    prof = [(None, None)] + [(y, None) for y in rows] + [(y, dx) for (y, dx) in curl]
    for ri, (y0, dx) in enumerate(prof):
        y = y0
        for z in zw:
            D = slope_wd(z)[1]
            if y0 is None:
                y = -D                                   # 第一排 = 坡底
            elif y0 > lip_y + 1e-3:
                y = min(y0, -D - 0.3 * ri)               # 坡深的地方，上面几排往下挤，保持次序
            # 下缘那一排沿用上一个 z 的 y（原来的写法就是这样，岩口的参差由它而来；保持已过终审的形状不变）
            x = wx(y, z, D) if dx is None else edge_x + dx + 0.3 * _noise(z, y, 11)
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
