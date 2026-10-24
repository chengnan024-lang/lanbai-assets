# -*- coding: utf-8 -*-
"""不依赖 bpy 的小算式（scene.py 与 gen_layout.py 共用）。"""
import math

import numpy as np

import palace_layout as L

POEM_AZ, POEM_EL = 6.5, 6.7          # D-33 #2
POEM_BOX = (-3.25, 16.25, 3.4, 10.0)   # 方位左 / 右、仰角下 / 上（最长一行 ≤ 19.5°，顶 ≤ +10°）


def poem_point():
    """B 群鱼在 720 s 穿过的点：主座位眼睛往河伯诗的方向 8 m（诗在 15 m，鱼在它前面）。
    D-33 #2：诗块中心方位 +6.5°、顶 ≤ +10°（三行约 6.6° 高 → 中心仰角约 +6.7°）。"""
    e = L.eye(720.0)
    az, el = math.radians(POEM_AZ), math.radians(POEM_EL)
    d = np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
    return [round(float(x), 3) for x in e + 8.0 * d]
