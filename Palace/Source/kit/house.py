# -*- coding: utf-8 -*-
"""鱼鳞屋：汉式小殿，模块局部坐标（地面 y = 0，中心在原点，正面朝 −z）。

    build(w, h, d, lod=0, seed=0) -> UB
        w 面宽（x，台基）9–11.4 m；d 进深（z，台基）7–8.5 m；h 檐口高（檐下皮离地）4.8–5.6 m。

形制（research_han.md §3–6）：矮石台基（0.6–1.0 m，按 seed）、前出廊、三间、四根朱漆小八角檐柱 + 覆盆础 +
鎏金柱头箍 + 栌斗、柱头上一道 LacquerBand 檐枋；墙 StoneDark；正面一门（双扇，关着，黑漆，鎏金衔环）两窗（直棂）。
屋顶“鱼鳞屋”：seed 偶数四阿、奇数悬山；直坡、檐口平直、转角不起翘；屋面槽 FishScale（平的，鳞由贴图 + 法线），
檐口一排半圆鳞片头（几何，半径 0.35 m，比屋面陡、垂过檐板），正脊 / 垂脊 Tile，正脊两端只起翘 + 克制鱼尾。
注意：屋檐（连鳞片头）比台基每边多出约 0.5 + 0.2 m；前面的踏步伸出台基 0.3 m × (级数 − 1)。
"""
import math

import numpy as np

try:
    from .common import TILE
    from .que import KB, box, beam_x, beam_z, course, extrude, hip_ridges, hip_solid, ngon_prism, prism, ridge, _emit
except ImportError:
    from common import TILE
    from que import KB, box, beam_x, beam_z, course, extrude, hip_ridges, hip_solid, ngon_prism, prism, ridge, _emit

SLOPE = 30.0          # 屋面坡度（度）
SCALE_R = 0.35        # 檐口鳞片头半径
FASCIA = 0.15


def slab(ub, poly, nrm, t, slot):
    """平面凸多边形 poly（3D 点）沿 nrm 加厚 t 的封闭薄板。"""
    P = np.asarray(poly, float)
    n = len(P)
    nrm = np.asarray(nrm, float) / np.linalg.norm(nrm)
    V = list(P) + list(P + nrm * t)
    F = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    F += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    _emit(ub, V, F, slot)


def torus(ub, c, ax, R, r, n, m, slot):
    c, ax = np.asarray(c, float), np.asarray(ax, float) / np.linalg.norm(ax)
    a = np.cross(ax, (0, 1.0, 0)) if abs(ax[1]) < 0.9 else np.cross(ax, (1.0, 0, 0))
    a /= np.linalg.norm(a)
    b = np.cross(ax, a)
    V = []
    for i in range(n):
        th = 2 * math.pi * i / n
        rad = a * math.cos(th) + b * math.sin(th)
        for j in range(m):
            ph = 2 * math.pi * j / m
            V.append(c + rad * (R + r * math.cos(ph)) + ax * r * math.sin(ph))
    F = [(i * m + j, ((i + 1) % n) * m + j, ((i + 1) % n) * m + (j + 1) % m, i * m + (j + 1) % m) for i in range(n) for j in range(m)]
    _emit(ub, V, F, slot)


def scale_row(ub, T0, T1, s, rs=SCALE_R, nseg=7):
    """沿檐口上皮 T0→T1 排一行半圆鳞片头：板面比屋面陡（约 55°），从檐板外皮垂下、头比檐板低 ~0.15 m。
    s = 屋面向上坡的单位向量。"""
    T0, T1, s = (np.asarray(x, float) for x in (T0, T1, s))
    e = T1 - T0
    W = np.linalg.norm(e)
    e /= W
    g = -s + np.array([0, -0.95, 0])               # 向外、向下
    g /= np.linalg.norm(g)
    m = np.cross(g, e)
    if np.dot(m, -s) + m[1] < 0:                   # 让板的法线朝外上
        m = -m
    k = max(1, int(round(W / (2 * rs))))
    step = W / k
    out = -np.cross(e, (0, 1.0, 0))                 # 水平外法线（檐板外皮方向）
    if np.dot(out, -s) < 0:
        out = -out
    for i in range(k):
        c = T0 + e * step * (i + 0.5) + out * 0.03
        r = step / 2 * 1.0
        pts = [c + e * r - g * 0.14]
        for j in range(nseg + 1):
            a = math.pi * j / nseg
            pts.append(c + e * (r * math.cos(a)) + g * (r * math.sin(a)))
        pts.append(c - e * r - g * 0.14)
        slab(ub, pts, m, 0.07 if i % 2 else 0.075, 'FishScale')


def _slope_uv(P, T0, e, s, tile):
    return [(np.dot(np.asarray(p) - T0, e) / tile, np.dot(np.asarray(p) - T0, s) / tile) for p in P]


def gable_roof(ub, X, Z, ys, fascia, slope_deg):
    """悬山：檐口 z = ±Z，两山 x = ±X（出际），脊沿 x。实心坡板（厚 = fascia，竖向），下皮 Wood。返回脊高与坡面信息。"""
    tn = math.tan(math.radians(slope_deg))
    yf = ys + fascia
    yr = yf + Z * tn
    sec = [(-Z, ys), (-Z, yf), (0.0, yr), (Z, yf), (Z, ys), (0.0, yr - fascia)]   # A' A R B B' R'
    V = [(x, y, z) for x in (-X, X) for (z, y) in sec]                              # 0..5 左山，6..11 右山
    L, R = 0, 6
    F, S, UV = [], [], []
    tile = TILE['FishScale']
    # 顶面（前坡 A→R、后坡 R→B），u 沿檐（从外看向右）、v 向上坡
    sf = np.array([0, tn, 1.0]) / math.hypot(1, tn)
    sb = np.array([0, tn, -1.0]) / math.hypot(1, tn)
    f = (L + 1, R + 1, R + 2, L + 2); F.append(f); S.append('FishScale')
    UV.append(_slope_uv([V[i] for i in f], V[L + 1], np.array([1.0, 0, 0]), sf, tile))
    f = (L + 2, R + 2, R + 3, L + 3); F.append(f); S.append('FishScale')
    UV.append(_slope_uv([V[i] for i in f], V[R + 3], np.array([-1.0, 0, 0]), sb, tile))
    # 檐板
    f = (L + 0, R + 0, R + 1, L + 1); F.append(f); S.append('Wood'); UV.append(None)
    f = (L + 3, R + 3, R + 4, L + 4); F.append(f); S.append('Wood'); UV.append(None)
    # 下皮
    f = (L + 4, R + 4, R + 5, L + 5); F.append(f); S.append('Wood'); UV.append(None)
    f = (L + 5, R + 5, R + 0, L + 0); F.append(f); S.append('Wood'); UV.append(None)
    # 两山的端头（各拆两个凸四边形）
    for o, rev in ((L, False), (R, True)):
        for q in ((0, 1, 2, 5), (5, 2, 3, 4)):
            f = tuple(o + i for i in q)
            F.append(tuple(reversed(f)) if rev else f); S.append('Wood'); UV.append(None)
    _emit(ub, V, F, S, UV)
    return dict(yr=yr, yf=yf, sf=sf, sb=sb)


def build(w, h, d, lod=0, seed=0):
    rng = np.random.default_rng(seed + 7)
    hi = lod == 0
    hip = seed % 2 == 0
    tb = round(0.6 + 0.4 * rng.random(), 2)                 # 台基高
    ub = KB()
    W2, D2 = w / 2, d / 2
    # ---------------- 台基
    box(ub, (-W2, -0.3, -D2), (W2, tb - 0.12, D2), 'Stone')
    box(ub, (-W2 - 0.06, tb - 0.12, -D2 - 0.06), (W2 + 0.06, tb, D2 + 0.06), 'Stone')     # 压阑石
    if hi:                                                                                # 角柱 + 间柱（凸 0.05）
        for sx in (-1, 1):
            for z in np.linspace(-D2 + 0.2, D2 - 0.2, 4):
                box(ub, (min(sx * W2, sx * (W2 + 0.05)), 0.0, z - 0.2), (max(sx * W2, sx * (W2 + 0.05)), tb - 0.12, z + 0.2), 'Stone')
        for sz in (-1, 1):
            for x in np.linspace(-W2 + 0.2, W2 - 0.2, 6):
                if sz < 0 and abs(x) < 1.4:
                    continue
                box(ub, (x - 0.2, 0.0, min(sz * D2, sz * (D2 + 0.05))), (x + 0.2, tb - 0.12, max(sz * D2, sz * (D2 + 0.05))), 'Stone')
    n_st = max(3, int(math.ceil(tb / 0.2)))                                                # 踏步
    sh = tb / n_st
    for k in range(n_st - 1):
        box(ub, (-1.15, -0.3 if k == 0 else 0.0, -D2 - 0.3 * (n_st - 1 - k)), (1.15, sh * (k + 1), -D2 + 0.01), 'Stone')
    if hi:
        for sx in (-1, 1):                                                                 # 垂带石
            x = sx * 1.3
            # 楔形：底矩形 + 斜顶
            V = [(x - 0.15, -0.3, -D2 - 0.3 * (n_st - 1) - 0.1), (x + 0.15, -0.3, -D2 - 0.3 * (n_st - 1) - 0.1),
                 (x + 0.15, -0.3, -D2 + 0.01), (x - 0.15, -0.3, -D2 + 0.01),
                 (x - 0.15, sh + 0.08, -D2 - 0.3 * (n_st - 1) - 0.1), (x + 0.15, sh + 0.08, -D2 - 0.3 * (n_st - 1) - 0.1),
                 (x + 0.15, tb + 0.08, -D2 + 0.01), (x - 0.15, tb + 0.08, -D2 + 0.01)]
            F = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
            _emit(ub, V, F, 'Stone')

    # ---------------- 柱网 / 墙
    xc = W2 - 0.75                       # 檐柱中线
    zf = -D2 + 0.75                      # 前檐柱
    zb = D2 - 0.75                       # 后墙中线
    zw = zf + 1.2                        # 前墙（前出廊）
    ye = h                               # 檐下皮
    yb0 = ye - 0.42                      # 枋底
    yd0 = yb0 - 0.36                     # 栌斗底（柱顶）
    bay = 2 * xc / 3
    cr = 0.24                            # 八角柱外接半径（对边 ≈ 0.44，柱高的 ~1/9）

    def column(x, z, free=True):
        if hi:
            ngon_prism(ub, x, z, cr + 0.16, cr + 0.07, tb - 0.01, tb + 0.16, 8, 'Stone')        # 覆盆础
            ngon_prism(ub, x, z, cr, cr * 0.94, tb + 0.15, yd0 - 0.14, 8, 'Lacquer')
            ngon_prism(ub, x, z, cr * 0.98, cr * 0.98, yd0 - 0.16, yd0 - 0.01, 8, 'Gilt')       # 柱头箍
            ngon_prism(ub, x, z, cr * 0.94, cr * 0.94, yd0 - 0.02, yd0 + 0.01, 8, 'Lacquer')
            # 栌斗：斗欹（下收）+ 斗耳
            s0, s1 = 0.2, 0.3
            prism(ub, (x - s0, x + s0, z - s0, z + s0, yd0), (x - s1, x + s1, z - s1, z + s1, yd0 + 0.17), 'Lacquer')
            box(ub, (x - s1, yd0 + 0.17, z - s1), (x + s1, yb0, z + s1), 'Lacquer')
        else:
            ngon_prism(ub, x, z, cr, cr, tb, yb0, 6, 'Lacquer')

    for x in (-xc, -xc / 3, xc / 3, xc):
        column(x, zf)
    for sx in (-1, 1):
        for z in ((zb,) if hi else ()):
            column(sx * xc, z, free=False)
    # 墙（含后、侧、前墙；从台基面到枋底）
    box(ub, (-xc - 0.14, tb - 0.02, zw), (xc + 0.14, yb0 + 0.01, zb + 0.14), 'StoneDark')
    # 枋：墙顶一圈 + 前檐枋 + 两侧的廊枋
    course(ub, xc + 0.18, (zb + 0.18 - (zw - 0.06)) / 2, yb0, ye, 0.0, (zb + 0.18 + zw - 0.06) / 2)
    beam_x(ub, -xc - 0.45, xc + 0.45, yb0, ye, zf - 0.16, zf + 0.16)
    for sx in (-1, 1):
        beam_z(ub, zf + 0.1, zw, yb0, ye, sx * xc - 0.15, sx * xc + 0.15)

    # ---------------- 门、窗（前墙 z = zw，外面朝 −z）
    dw = min(1.9, bay * 0.62)
    dh = min(2.75, (yb0 - tb) * 0.74)
    yd = tb + 0.14
    if hi:
        box(ub, (-dw / 2 - 0.1, tb - 0.01, zw - 0.14), (dw / 2 + 0.1, yd, zw + 0.02), 'LacquerBlack')        # 门槛
        for sx in (-1, 1):
            box(ub, (min(sx * dw / 2, sx * (dw / 2 + 0.2)), tb, zw - 0.13), (max(sx * dw / 2, sx * (dw / 2 + 0.2)), yd + dh + 0.22, zw + 0.02), 'LacquerBlack')   # 门框
        box(ub, (-dw / 2 - 0.36, yd + dh, zw - 0.15), (dw / 2 + 0.36, yd + dh + 0.24, zw + 0.02), 'LacquerBlack')              # 门楣
        for sx in (-1, 1):                                                                   # 两扇（关着）
            box(ub, (min(sx * 0.012, sx * dw / 2), yd, zw - 0.07), (max(sx * 0.012, sx * dw / 2), yd + dh, zw + 0.02), 'LacquerBlack')
            # 衔环：底座 + 环（鎏金）
            cx = sx * 0.3
            cy = yd + dh * 0.5
            extrude(ub, (cx, cy, zw - 0.065), (cx, cy, zw - 0.11), (0, 1.0, 0),
                    [(0.11 * math.cos(2 * math.pi * j / 6), 0.11 * math.sin(2 * math.pi * j / 6)) for j in range(6)], 'Gilt')
            torus(ub, (cx, cy - 0.13, zw - 0.125), (0, 0, 1.0), 0.12, 0.022, 10, 4, 'Gilt')
        # 窗：左右两间各一（直棂）
        ww, wh = min(1.35, bay * 0.5), min(1.0, (yb0 - tb) * 0.28)
        wy0 = tb + min(1.35, (yb0 - tb) * 0.4)
        for sx in (-1, 1):
            wx = sx * bay
            box(ub, (wx - ww / 2, wy0, zw - 0.03), (wx + ww / 2, wy0 + wh, zw + 0.01), 'LacquerBlack')                    # 窗洞底
            fw = 0.11
            box(ub, (wx - ww / 2 - fw, wy0 - fw, zw - 0.11), (wx + ww / 2 + fw, wy0, zw + 0.01), 'LacquerBlack')        # 下框
            box(ub, (wx - ww / 2 - fw, wy0 + wh, zw - 0.11), (wx + ww / 2 + fw, wy0 + wh + fw, zw + 0.01), 'LacquerBlack')
            box(ub, (wx - ww / 2 - fw, wy0, zw - 0.11), (wx - ww / 2, wy0 + wh, zw + 0.01), 'LacquerBlack')
            box(ub, (wx + ww / 2, wy0, zw - 0.11), (wx + ww / 2 + fw, wy0 + wh, zw + 0.01), 'LacquerBlack')
            nb = max(5, int(ww / 0.16))
            for i in range(1, nb):
                bx = wx - ww / 2 + ww * i / nb
                box(ub, (bx - 0.032, wy0, zw - 0.09), (bx + 0.032, wy0 + wh, zw - 0.02), 'Wood')
    else:
        box(ub, (-dw / 2, tb, zw - 0.06), (dw / 2, yd + dh, zw + 0.02), 'LacquerBlack')

    # ---------------- 屋顶
    X, Z = xc + 1.25, zb + 1.25
    if hip:
        roof = hip_solid(ub, 0, 0, X, Z, ye, FASCIA, SLOPE, top='FishScale', fas='Wood', soffit='Wood')
        yr = roof['y_top']
        hip_ridges(ub, roof, 0.3, 0.24)
        ridge(ub, (0, 0, 0), 'x', X - Z + 0.15, yr - 0.2, 0.55, 0.36, 0.42, n_end=5 if hi else 2)
        if hi:
            for sd in roof['sides']:
                scale_row(ub, sd['T0'], sd['T0'] + sd['e'] * sd['W'], sd['s'])
    else:
        Xg = xc + 0.95                                                   # 出际
        g = gable_roof(ub, Xg, Z, ye, FASCIA, SLOPE)
        yr = g['yr']
        tn = math.tan(math.radians(SLOPE))
        # 山墙 / 廊顶：墙线以上到屋面下皮的五边形实体（封住屋架，前面兼作廊顶）
        za, zb2 = zf - 0.22, zb + 0.18
        xa = xc + 0.16
        sec = [(za, ye - 0.01), (zb2, ye - 0.01), (zb2, ye + FASCIA + (Z - zb2) * tn - FASCIA - 0.02),
               (0.0, yr - FASCIA - 0.02), (za, ye + FASCIA + (Z + za) * tn - FASCIA - 0.02)]
        V = [(x, y, z) for x in (-xa, xa) for (z, y) in sec]
        n = len(sec)
        F = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
        F += [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
        _emit(ub, V, F, 'StoneDark')
        # 垂脊（两山沿坡）+ 正脊
        for sx in (-1, 1):
            x = sx * (Xg - 0.17)
            for sz in (-1, 1):
                p0 = np.array([x, ye + FASCIA, sz * Z])
                p1 = np.array([x, yr, 0.0])
                d_ = p1 - p0
                extrude(ub, p0 - d_ * 0.01, p1, (0, 1.0, 0), [(-0.17, -0.1), (0.17, -0.1), (0.17, 0.22), (-0.17, 0.22)], 'Tile')
        ridge(ub, (0, 0, 0), 'x', Xg + 0.05, yr - 0.22, 0.55, 0.36, 0.42, n_end=5 if hi else 2)
        if hi:
            for sz in (-1, 1):
                T0 = np.array([-Xg if sz < 0 else Xg, ye + FASCIA, sz * Z])
                T1 = np.array([Xg if sz < 0 else -Xg, ye + FASCIA, sz * Z])
                s = g['sf'] if sz < 0 else g['sb']
                scale_row(ub, T0, T1, s)
    return ub


if __name__ == '__main__':
    from que import check_closed_outward
    for seed in (0, 1):
        for lod in (0, 1):
            u = build(10.2, 5.2, 7.5, lod, seed)
            bad, frac = check_closed_outward(u)
            print('house seed%d lod%d: %d tris, %d parts, bad %d, centroid %.3f' % (seed, lod, u.tris(), len(u.parts), len(bad), frac))
