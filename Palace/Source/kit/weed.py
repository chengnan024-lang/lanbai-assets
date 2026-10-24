# -*- coding: utf-8 -*-
"""海草（30 根，2–5 m，0.15 Hz 摆动）：每根一条渐细的带子（两面），位置来自海的约定。
顶点数据给 shader 摆动用：UV1.x = 沿草的高度 0..1（根 0、梢 1），UV1.y = 每根的相位 0..1。
（UB 只存 UV0，所以摆动参数单独返回，build_bpy 时写进第二个 UV 层。）"""
import math

import numpy as np

from .common import UB


def build(weeds, lod=0):
    u = UB()
    sway = []          # 与 u.UV 同序：每个面每个角的 (h, phase)
    seg = 10 if lod == 0 else 4
    for k, w in enumerate(weeds):
        x0, y0, z0 = w['pos']
        L = w['height_m']
        ph = (k * 0.618) % 1.0
        on_wall = x0 > -9.0 and y0 < -0.5               # 长在崖壁上的：先往外再往上弯
        width = 0.22
        pts, nrm = [], []
        for i in range(seg + 1):
            s = i / seg
            bend = 0.6 * s * s
            x = x0 + (0.5 * s if on_wall else 0.15 * math.sin(3 * s + k))
            y = y0 + L * s
            z = z0 + bend * (1 if k % 2 else -1)
            pts.append((x, y, z))
        for i in range(seg):
            s0, s1 = i / seg, (i + 1) / seg
            w0, w1 = width * (1 - 0.8 * s0), width * (1 - 0.8 * s1)
            a, b = np.array(pts[i]), np.array(pts[i + 1])
            side = np.array([0.0, 0.0, 1.0]) if k % 3 else np.array([0.7, 0.0, 0.7])
            q = [a - side * w0 / 2, a + side * w0 / 2, b + side * w1 / 2, b - side * w1 / 2]
            for flip in (False, True):
                f = (0, 1, 2, 3) if not flip else (0, 3, 2, 1)
                uv = [(0, s0), (1, s0), (1, s1), (0, s1)]
                u.add(q, [f], 'Weed', [[uv[j] for j in f]])
                hs = [s0, s0, s1, s1]
                sway.append([(hs[j], ph) for j in f])
    return u, sway
