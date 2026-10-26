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


class Canvas:
    def __init__(self, n):
        self.n = n
        self.alb = np.zeros((n, n, 3)); self.cov = np.zeros((n, n)); self.hgt = np.zeros((n, n)); self.thin = np.zeros((n, n))
        self.tilt = np.zeros((n, n, 2))         # per-leaflet slope (dh/du, dh/dv): leaflets are not coplanar with the card
        self.rng = np.random.default_rng(n)

    def leaflet(self, c, ang, L, col, lift=0.0):
        """A pointed-elliptic leaflet, length L px, centred at c, drawn over what is there (painter's order)."""
        hw = L * 0.30
        r = int(L * 0.6) + 2
        x0, x1 = max(0, int(c[0]) - r), min(self.n, int(c[0]) + r + 1)
        y0, y1 = max(0, int(c[1]) - r), min(self.n, int(c[1]) + r + 1)
        if x0 >= x1 or y0 >= y1:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
        ca, sa = math.cos(ang), math.sin(ang)
        u = (xx - c[0]) * ca + (yy - c[1]) * sa
        v = -(xx - c[0]) * sa + (yy - c[1]) * ca
        un = u / (0.5 * L)
        prof = hw * np.sqrt(np.clip(1 - un ** 2, 0, 1)) * (1 - 0.3 * np.clip(un, 0, 1))
        m = (np.abs(v) < prof) & (np.abs(un) < 1)
        if not m.any():
            return
        vein = np.exp(-0.5 * (v / max(0.6, L * 0.02)) ** 2)
        shade = (0.86 + 0.14 * un) * (1 - 0.15 * vein)
        sl = (slice(y0, y1), slice(x0, x1))
        A = self.alb[sl]; A[m] = (col[None, None] * shade[..., None])[m]
        self.cov[sl][m] = 1
        h = np.clip(1 - np.abs(v) / np.maximum(prof, 1e-3), 0, 1)
        H = self.hgt[sl]; H[m] = (0.5 + 0.5 * h + lift)[m]
        T = self.thin[sl]; T[m] = (1 - 0.5 * vein)[m]
        tl = self.rng.normal(0, 0.30, 2)          # ~ +-17 deg: a broad wet sheen, not sparkles (no shimmer in VR)
        TT = self.tilt[sl]; TT[m] = tl

    def stalk(self, p0, p1, w0, w1, col):
        n = int(np.hypot(*(np.asarray(p1) - p0)) / 1.5) + 2
        for s in np.linspace(0, 1, n):
            p = np.asarray(p0) + (np.asarray(p1) - p0) * s
            w = w0 + (w1 - w0) * s
            r = int(w) + 2
            x0, x1 = max(0, int(p[0]) - r), min(self.n, int(p[0]) + r + 1)
            y0, y1 = max(0, int(p[1]) - r), min(self.n, int(p[1]) + r + 1)
            if x0 >= x1 or y0 >= y1:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
            d = np.hypot(xx - p[0], yy - p[1])
            m = d < w
            sl = (slice(y0, y1), slice(x0, x1))
            self.alb[sl][m] = col; self.cov[sl][m] = 1
            self.hgt[sl][m] = np.maximum(self.hgt[sl][m], 0.3 * (1 - d[m] / w))


def compound_leaf(cv, base, ang, L, leaflet, rng, tone_base):
    """Pinnate (imparipinnate) leaf: rachis of length L px from `base` along `ang`, leaflet pairs + a terminal one."""
    tip = base + L * np.array([math.cos(ang), math.sin(ang)])
    cv.stalk(base, tip, 1.3, 0.6, hexlin('#4A4232'))
    npair = rng.integers(4, 7)
    for k in range(npair):
        s = 0.25 + 0.75 * (k + 0.5) / npair
        p = base + (tip - base) * s
        for side in (-1, 1):
            a = ang + side * math.radians(rng.uniform(55, 80))
            ll = leaflet * rng.uniform(0.85, 1.1) * (1.05 - 0.2 * s)
            tone = np.clip(tone_base + rng.normal(0, 0.08), 0, 1)
            col = hexlin('#4A5232') * (0.78 + 0.45 * tone) + hexlin('#5A5038') * 0.15
            cv.leaflet(p + 0.5 * ll * np.array([math.cos(a), math.sin(a)]), a, ll, col, lift=0.2 * s)
    cv.leaflet(tip + 0.45 * leaflet * np.array([math.cos(ang), math.sin(ang)]), ang, leaflet * 1.05,
               hexlin('#4A5232') * (0.78 + 0.45 * tone_base) + hexlin('#5A5038') * 0.15)


def leaf_cluster(out, N=2048, seed=5):
    """Atlas 2x2 (cell 1024 px = one card). Cells 0-2: a twig with 12-16 pinnate leaves fanning up from the bottom
    centre (LOD0 card, ~1.25 m: a leaflet ~5 cm = ~40 px). Cell 3: a dense clump of ~60 smaller leaves inside an
    ellipse (LOD1 card, ~2.5 m) - a mass, so the far tree does not fizz (director note 2)."""
    rng = np.random.default_rng(seed)
    cell = N // 2
    full = Canvas(N)
    for ci in range(4):
        oy, ox = (ci // 2) * cell, (ci % 2) * cell
        cv = Canvas(cell)
        if ci < 3:
            base = np.array([cell * 0.5, cell * 0.98])
            cv.stalk(base, base + np.array([rng.uniform(-30, 30), -cell * 0.35]), 7, 3, hexlin('#3E352A'))
            leaves = []
            for k in range(rng.integers(22, 28)):
                ang = math.radians(-90 + rng.uniform(-75, 75))
                b0 = base + np.array([rng.uniform(-40, 40), -cell * rng.uniform(0.08, 0.45)])
                L = cell * rng.uniform(0.28, 0.42)
                leaves.append((b0, ang, L, rng.uniform(0, 1)))
            leaves.sort(key=lambda t: rng.uniform())
            for b0, ang, L, tone in leaves:
                compound_leaf(cv, b0, ang, L, cell * 0.060, rng, tone)
        else:
            for k in range(150):
                rr = rng.uniform(0, 1) ** 0.5
                a = rng.uniform(0, 2 * math.pi)
                b0 = np.array([cell * 0.5 + math.cos(a) * rr * cell * 0.24, cell * 0.52 + math.sin(a) * rr * cell * 0.21])
                ang = a + rng.normal(0, 0.6)
                compound_leaf(cv, b0 - 0.08 * cell * np.array([math.cos(ang), math.sin(ang)]), ang, cell * rng.uniform(0.15, 0.22), cell * 0.034, rng, rng.uniform(0, 1))
        # nothing may touch the cell's border: a leaf cut by the card edge shows the card as a straight-edged
        # rectangle (director 10-25, LOD1 'flat rectangles'). Keep coverage inside an ellipse with a 4 % margin;
        # the LOD0 twig enters at the bottom centre, so the bottom middle stays open there.
        yy0, xx0 = np.mgrid[0:cell, 0:cell] + 0.5
        er = np.hypot((xx0 - cell / 2) / (cell * 0.46), (yy0 - cell / 2) / (cell * 0.46))
        keep = er < 1.0
        if ci < 3:
            keep |= (np.abs(xx0 - cell / 2) < cell * 0.03) & (yy0 > cell * 0.5)
        cv.cov[~keep] = 0
        sl = (slice(oy, oy + cell), slice(ox, ox + cell))
        full.alb[sl] = cv.alb; full.cov[sl] = cv.cov; full.hgt[sl] = cv.hgt; full.thin[sl] = cv.thin; full.tilt[sl] = cv.tilt
    from scipy import ndimage
    idx = ndimage.distance_transform_edt(full.cov < 0.5, return_distances=False, return_indices=True)
    alb = full.alb[idx[0], idx[1]]
    alb = np.clip(alb, lin_of(30), lin_of(190))
    # AO: darker toward each cell's centre-bottom (inside of the cluster)
    yy, xx = np.mgrid[0:N, 0:N]
    cx = (xx % cell) / cell - 0.5; cy = (yy % cell) / cell - 0.55
    ao = np.clip(0.65 + 0.7 * np.hypot(cx, cy), 0.65, 1.0)
    nrm = normal_from_height(ndimage.gaussian_filter(full.hgt, 1.0) * 0.002, 1.25 / cell, 1.25 / cell)
    nrm[..., 0] -= full.tilt[..., 0]; nrm[..., 1] -= full.tilt[..., 1]
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    os.makedirs(out, exist_ok=True)
    save_rgba(os.path.join(out, 'T_Tree_LeafCluster_Albedo.png'), np.concatenate([to_srgb(alb), full.cov[..., None]], -1))
    save_rgb(os.path.join(out, 'T_Tree_LeafCluster_Normal.png'), nrm * 0.5 + 0.5)
    save_rgba(os.path.join(out, 'T_Tree_LeafCluster_Mask.png'), np.stack([full.thin, np.full((N, N), 0.35), ao, np.zeros((N, N))], -1))
    for ci in range(4):
        oy, ox = (ci // 2) * cell, (ci % 2) * cell
        c = full.cov[oy:oy + cell, ox:ox + cell]
        print('cell %d coverage %.2f' % (ci, c.mean()))
    print('albedo sRGB mean (covered) %.0f' % ((to_srgb(alb)[full.cov > 0.5] * 255).mean()))


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
