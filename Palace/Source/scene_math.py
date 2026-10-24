# -*- coding: utf-8 -*-
"""不依赖 bpy 的小算式（scene.py 与 gen_layout.py 共用）。"""
import math

import numpy as np

import palace_layout as L


def poem_point():
    """B 群鱼在 720 s 穿过的点：主座位眼睛往河伯诗的方向（+10°、+6°）8 m（诗在 15 m，鱼在它前面）。"""
    e = L.eye(720.0)
    az, el = math.radians(10.0), math.radians(6.0)
    d = np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
    return [round(float(x), 3) for x in e + 8.0 * d]
