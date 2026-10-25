# -*- coding: utf-8 -*-
"""样板树的贴图（numpy 生成）：
  T_Tree_LeafCluster_{Albedo,Normal,Mask}.png  1024²，一张图 4 格（2×2），每格一簇叶 + 小枝：
      Albedo RGB sRGB，A = 覆盖（alpha-to-coverage 用，阈值 0.5）；Normal 切线空间（OpenGL）；
      Mask R = 透光厚度（叶薄处 1），G = 干光滑度，B = AO（簇的中心暗），A = 0
  T_Tree_Bark_{Albedo,Normal,Mask}.png         512×1024，沿树干无缝（u 绕一圈、v 沿长 2 m）
用法：python3 lt_tex.py <outdir>"""
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from lk_tex import fbm, hexlin, lin_of, normal_from_height, save_rgb, save_rgba, sstep, to_srgb  # noqa: E402


def leaf_cluster(out, N=1024, seed=5):
    rng = np.random.default_rng(seed)
    cell = N // 2
    alb = np.zeros((N, N, 3)); cov = np.zeros((N, N)); hgt = np.zeros((N, N)); thin = np.zeros((N, N)); ao = np.ones((N, N))
    yy, xx = np.mgrid[0:cell, 0:cell] + 0.5
    for ci in range(4):
        oy, ox = (ci // 2) * cell, (ci % 2) * cell
        A = np.zeros((cell, cell, 3)); C = np.zeros((cell, cell)); Hh = np.zeros((cell, cell)); T = np.zeros((cell, cell))
        # a twig from the bottom centre fanning up; leaves along it (simple, elliptic, slightly toothless)
        n_tw = 4 + ci % 2
        base = np.array([cell * 0.5, cell * 0.97])
        leaves = []
        for t in range(n_tw):
            ang = math.radians(-90 + rng.uniform(-42, 42))
            L = cell * rng.uniform(0.42, 0.68)
            p0 = base
            p1 = base + L * np.array([math.cos(ang), math.sin(ang)])
            # twig line
            for s in np.linspace(0, 1, 120):
                p = p0 + (p1 - p0) * s
                d = np.hypot(xx - p[0], yy - p[1])
                w = 2.2 * (1 - 0.7 * s)
                m = d < w
                C[m] = 1; A[m] = hexlin('#3B3026'); Hh[m] = np.maximum(Hh[m], 1 - d[m] / w)
            for s in np.linspace(0.15, 1.0, rng.integers(7, 11)):
                p = p0 + (p1 - p0) * s
                for side in (-1, 1):
                    a = ang + side * math.radians(rng.uniform(35, 70))
                    ll = cell * rng.uniform(0.07, 0.11) * (1.15 - 0.3 * s)
                    leaves.append((p + 0.55 * ll * np.array([math.cos(a), math.sin(a)]), a, ll, rng.uniform(0, 1)))
        # draw leaves back to front by random depth
        rng.shuffle(leaves)
        for (c, a, ll, tone) in leaves:
            ca, sa = math.cos(a), math.sin(a)
            u = (xx - c[0]) * ca + (yy - c[1]) * sa
            v = -(xx - c[0]) * sa + (yy - c[1]) * ca
            hw = ll * 0.32
            # leaf outline: pointed ellipse
            prof = hw * np.sqrt(np.clip(1 - (u / (0.5 * ll)) ** 2, 0, 1)) * (1 - 0.25 * np.clip(u / (0.5 * ll), 0, 1))
            m = (np.abs(v) < prof) & (np.abs(u) < 0.5 * ll)
            col = hexlin('#3A4A26') * (0.75 + 0.5 * tone) + hexlin('#4A4628') * 0.15 * (1 - tone)
            vein = np.exp(-0.5 * (v / 0.9) ** 2)
            shade = (0.85 + 0.15 * (u / (0.5 * ll))) * (1 - 0.18 * vein)
            A[m] = (col * shade[..., None])[m]
            C[m] = 1
            h = np.clip(1 - np.abs(v) / np.maximum(prof, 1e-3), 0, 1)
            Hh[m] = (0.4 + 0.6 * h + 0.3 * u / ll)[m]
            T[m] = (1 - 0.5 * vein)[m]
        alb[oy:oy + cell, ox:ox + cell] = A; cov[oy:oy + cell, ox:ox + cell] = C
        hgt[oy:oy + cell, ox:ox + cell] = Hh; thin[oy:oy + cell, ox:ox + cell] = T
        r = np.hypot(xx - cell / 2, yy - cell * 0.6) / cell
        ao[oy:oy + cell, ox:ox + cell] = 0.7 + 0.3 * np.clip(r * 2, 0, 1)
    # bleed albedo into the transparent area (mip-safe), keep coverage crisp
    from scipy import ndimage
    idx = ndimage.distance_transform_edt(cov < 0.5, return_distances=False, return_indices=True)
    alb = alb[idx[0], idx[1]]
    alb = np.clip(alb, lin_of(30), lin_of(200))
    nrm = normal_from_height(hgt * 0.0015, 0.5 / cell, 0.5 / cell)
    os.makedirs(out, exist_ok=True)
    save_rgba(os.path.join(out, 'T_Tree_LeafCluster_Albedo.png'), np.concatenate([to_srgb(alb), cov[..., None]], -1))
    save_rgb(os.path.join(out, 'T_Tree_LeafCluster_Normal.png'), nrm * 0.5 + 0.5)
    save_rgba(os.path.join(out, 'T_Tree_LeafCluster_Mask.png'), np.stack([thin, np.full((N, N), 0.35), ao, np.zeros((N, N))], -1))
    print('leaf cluster coverage %.2f, albedo sRGB mean (covered) %.0f' % (cov.mean(), (to_srgb(alb)[cov > 0.5] * 255).mean()))


def bark(out, H=1024, W=512, seed=6):
    """Furrowed bark (old deciduous, generic): vertical ridges with breaks; lichen speckles; wet = darker (x0.6)."""
    rng = np.random.default_rng(seed)
    circ, L = 1.2, 2.0
    mx, my = circ / W, L / H
    f1 = fbm((H, W), 0.02 / mx, 0.15 / mx, rng.integers(1e9), 2.0, aspect=(my * 6, mx))   # vertical-stretched
    f2 = fbm((H, W), 2, 30, rng.integers(1e9), 1.4)
    ridge = 1 - np.abs(np.tanh(f1 * 1.3))
    plates = sstep(0.35, 0.75, ridge)
    hgt = 0.012 * plates + 0.002 * f2
    alb = hexlin('#5A5048') * (0.75 + 0.35 * plates[..., None]) * (1 + 0.06 * f2[..., None])
    lich = np.clip(fbm((H, W), 3, 40, rng.integers(1e9)) - 1.4, 0, 1) * plates
    alb = alb * (1 - lich[..., None]) + hexlin('#7A8068') * lich[..., None]
    alb = np.clip(alb, lin_of(48), lin_of(150))
    nrm = normal_from_height(hgt, my, mx)
    save_rgb(os.path.join(out, 'T_Tree_Bark_Albedo.png'), to_srgb(alb))
    save_rgb(os.path.join(out, 'T_Tree_Bark_Normal.png'), nrm * 0.5 + 0.5)
    save_rgba(os.path.join(out, 'T_Tree_Bark_Mask.png'), np.stack([np.zeros((H, W)), 0.25 + 0.1 * plates, 0.6 + 0.4 * plates, 0.4 + 0.6 * (1 - plates)], -1))
    print('bark albedo sRGB mean %.0f' % (to_srgb(alb) * 255).mean())


if __name__ == '__main__':
    o = sys.argv[1]
    leaf_cluster(o)
    bark(o)
