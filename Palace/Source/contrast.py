# -*- coding: utf-8 -*-
"""终审 10-25 #1(4) 的量法：建筑对旁边的水的线性 Weber 对比（调色后）。
建筑 = Object Index（4 大殿、5 阙、6 鱼鳞屋的墙等、7 鱼鳞屋的屋面）；大殿上层屋顶和屋脊 = 大殿里宫殿 y ≥ 22 m 的像素。
旁边的水 = 建筑外 14 px 以内、没有命中任何几何的像素。亮度 = 调色后 sRGB 码 → 线性的 Rec.709 亮度。
weber 用均值；weber_median 用中位数（屋面上那条珍珠光带很亮、只占几个像素，均值会被它拉正）。
用法：PYTHONPATH=. ~/bpy/bin/python contrast.py <dir> [shot,...]"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

import post

CLASSES = {'hall_upper': (4, 22.0), 'hall': (4, None), 'que': (5, None), 'que_top': (5, 29.7), 'houses': (6, None), 'house_roofs': (7, None)}


def lin_luma(codes):
    c = np.clip(codes / 255.0, 0, 1)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def measure(d, shot):
    exr = post.read_exr(os.path.join(d, shot + '.exr'))
    L = lin_luma(np.asarray(Image.open(os.path.join(d, shot + '.png'))).astype(float)[..., :3])
    hit = exr['Depth.Z'] < 1e6
    idx = np.round(exr['Object Index.X']) if 'Object Index.X' in exr else np.zeros_like(L)
    Pu = np.stack([exr['Position.X'], exr['Position.Y'], exr['Position.Z']], -1) @ post.B2U.T
    out = {}
    for name, (k, ymin) in CLASSES.items():
        m = (idx == k) & hit
        if ymin is not None:
            m &= Pu[..., 1] >= ymin
        if m.sum() < 30:
            continue
        ring = binary_dilation(m, iterations=14) & ~hit
        if ring.sum() < 30:
            continue
        lb, lw = float(L[m].mean()), float(L[ring].mean())
        med = float(np.median(L[m])) / max(float(np.median(L[ring])), 1e-6) - 1
        out[name] = dict(weber=round(lb / max(lw, 1e-6) - 1, 3), weber_median=round(med, 3), px=int(m.sum()))
    return out


if __name__ == '__main__':
    d = sys.argv[1]
    shots = sys.argv[2].split(',') if len(sys.argv) > 2 else [f[:-4] for f in sorted(os.listdir(d)) if f.endswith('.exr')]
    res = {s: measure(d, s) for s in shots}
    for s, r in res.items():
        print(s, {k: (v['weber'], v['weber_median']) for k, v in r.items()})
    json.dump(res, open(os.path.join(d, 'contrast.json'), 'w'), indent=1)
