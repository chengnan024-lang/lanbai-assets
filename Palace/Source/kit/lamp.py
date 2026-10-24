# -*- coding: utf-8 -*-
"""长信宫灯式铜灯（总导演 D-29：去掉宫女，只留灯头 —— 灯盘 + 两片可开合的弧形屏板 + 烟道 —— 立在一根素铜灯柱上）。
模块局部坐标（Unity 轴），地面 y = 0；屏板的两个开口朝 ±x（摆放时转到朝神道）。灯焰中心 = (0, H − 0.23, 0)。"""
import math

import numpy as np

from .common import UB, lathe

FLAME_DROP = 0.23        # 灯焰中心在总高以下多少（海的约定：H 1.85 → 灯焰 1.62）


def build(H=1.85, lod=0):
    u = UB()
    n = 24 if lod == 0 else 10
    ytray = H - 0.38
    # 方石座
    u.box((-0.36, 0.0, -0.36), (0.36, 0.14, 0.36), 'Stone')
    # 圆足 + 素柱（细，收分）
    lathe([(0.26, 0.14), (0.26, 0.17), (0.20, 0.21), (0.07, 0.25), (0.045, 0.30), (0.036, 0.36),
           (0.030, ytray - 0.10), (0.042, ytray - 0.06), (0.05, ytray - 0.02)], n, 'Bronze', u,
          cap_bottom=True)
    # 灯盘：浅盘 + 鎏金的沿
    lathe([(0.05, ytray - 0.03), (0.19, ytray), (0.215, ytray + 0.035), (0.205, ytray + 0.045),
           (0.18, ytray + 0.02), (0.02, ytray + 0.015)], n, 'Gilt', u)
    # 灯盘中心的铜扦子（插火烛，长信宫灯的灯盘就是这样）与盘沿的把手（灯盘可以转动；「网络搜索协助」核实，2026-10-24）
    lathe([(0.012, ytray + 0.01), (0.008, ytray + 0.07), (0.002, ytray + 0.11)], 6 if lod else 8, 'Bronze', u, cap_bottom=True)
    if lod == 0:
        hx = 0.215
        u.box((hx - 0.005, ytray + 0.012, -0.012), (hx + 0.06, ytray + 0.032, 0.012), 'Bronze')          # 把手的柄
        u.box((hx + 0.05, ytray - 0.005, -0.02), (hx + 0.075, ytray + 0.045, 0.02), 'Bronze')            # 柄端
    # 两片弧形屏板（各 130°，开口朝 ±x），内外两层壁
    yb, yt = ytray + 0.02, ytray + 0.25
    r0, r1 = 0.175, 0.188
    seg = 10 if lod == 0 else 4
    for c in (math.pi / 2, -math.pi / 2):            # 屏板中心朝 ±z
        a = np.linspace(c - math.radians(65), c + math.radians(65), seg + 1)
        for i in range(seg):
            for (r, out) in ((r1, True), (r0, False)):
                p = [(r * math.cos(a[i]), yb, r * math.sin(a[i])), (r * math.cos(a[i + 1]), yb, r * math.sin(a[i + 1])),
                     (r * math.cos(a[i + 1]), yt, r * math.sin(a[i + 1])), (r * math.cos(a[i]), yt, r * math.sin(a[i]))]
                u.add(p if not out else p, [(0, 3, 2, 1) if out else (0, 1, 2, 3)], 'Bronze')
            # 上下沿
            for y in (yb, yt):
                q = [(r0 * math.cos(a[i]), y, r0 * math.sin(a[i])), (r1 * math.cos(a[i]), y, r1 * math.sin(a[i])),
                     (r1 * math.cos(a[i + 1]), y, r1 * math.sin(a[i + 1])), (r0 * math.cos(a[i + 1]), y, r0 * math.sin(a[i + 1]))]
                u.add(q, [(0, 1, 2, 3) if y == yb else (0, 3, 2, 1)], 'Bronze')
        for ae in (a[0], a[-1]):                       # 端面
            q = [(r0 * math.cos(ae), yb, r0 * math.sin(ae)), (r1 * math.cos(ae), yb, r1 * math.sin(ae)),
                 (r1 * math.cos(ae), yt, r1 * math.sin(ae)), (r0 * math.cos(ae), yt, r0 * math.sin(ae))]
            u.add(q, [(0, 1, 2, 3)], 'Bronze')
    # 灯罩顶：扁穹 → 收进烟道
    lathe([(0.195, yt), (0.195, yt + 0.015), (0.15, yt + 0.065), (0.08, yt + 0.095), (0.055, yt + 0.11)], n, 'Bronze', u)
    # 烟道：从顶上起，向后弯一道弧再顺着柱子往下（像那只执灯的袖），截面圆，管径 0.05
    rr = 0.045
    k = 14 if lod == 0 else 6
    pts = []
    for i in range(k + 1):
        s = i / k
        ang = s * math.pi * 1.05                       # 半圈多一点
        R = 0.20
        pts.append((0.0, yt + 0.10 + R * math.sin(ang) * 0.9, -R + R * math.cos(ang) * -1.0 + 2 * R * 0.0))
    # 弧心在 z = −R：起点 (0, yt+0.10, 0)，顶点在上，终点落在柱后 z ≈ −0.40
    R = 0.15
    pts = [(0.0, yt + 0.10 + R * math.sin(s * math.pi), -R + R * math.cos(s * math.pi)) for s in np.linspace(0, 1, k + 1)]
    # 落下来，弯回去并进柱子（柱后表面 z ≈ −0.04），并在 ytray − 0.30 处
    L = pts[-1][1] - (ytray - 0.30)
    drop = [(0.0, pts[-1][1] - d, -2 * R + (2 * R - 0.035) * (d / L) ** 1.8) for d in np.linspace(L / 5, L, 5 if lod == 0 else 2)]
    path = np.array(pts + drop)
    m = 8 if lod == 0 else 5
    rings = []
    for i, p in enumerate(path):
        t = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
        t = t / np.linalg.norm(t)
        a1 = np.array([1.0, 0, 0])
        a2 = np.cross(t, a1)
        a2 /= np.linalg.norm(a2)
        r = rr * (1.0 - 0.25 * i / len(path))
        rings.append([p + r * (math.cos(2 * math.pi * j / m) * a1 + math.sin(2 * math.pi * j / m) * a2) for j in range(m)])
    V = [v for ring in rings for v in ring]
    F = []
    for i in range(len(rings) - 1):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            F.append((a, b, b + m, a + m))
    tmp = UB()
    tmp.add(V, F, 'Bronze')
    # 判断绕向：第一个面的法线应当背离管轴
    P = np.array(V)
    f0 = F[0]
    nrm = np.cross(P[f0[1]] - P[f0[0]], P[f0[3]] - P[f0[0]])
    if np.dot(nrm, P[f0[0]] - path[0]) < 0:
        tmp.F = [tuple(reversed(f)) for f in tmp.F]
        tmp.UV = [list(reversed(x)) for x in tmp.UV]
    u.merge(tmp)
    # 管末端封口（埋进柱里，看不见也封上）
    end = len(V) - m
    u.add([V[end + j] for j in range(m)] + [tuple(path[-1])], [(j, (j + 1) % m, m) for j in range(m)], 'Bronze')
    return u


def flame_y(H):
    return H - FLAME_DROP
