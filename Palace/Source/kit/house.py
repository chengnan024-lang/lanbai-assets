# -*- coding: utf-8 -*-
"""鱼鳞屋：汉式小殿，模块局部坐标（地面 y = 0，中心在原点，正面朝 −z）。

    build(w, h, d, lod=0, seed=0) -> UB
        w × d：占地（x 面宽 9–11.4 m，z 进深 7–8.5 m）—— 第 10 轮起是**檐口外皮**的范围（屋檐不再伸出 w × d；
        只有前面踏步伸出约 0.3 m × 级数）。h：layout 给的名义檐高 4.8–5.6 m，实际墙高按类型取 0.74–0.8 h。

第 10 轮（终审“带白花边的矮棚子”）：
  · 檐口：去掉一排大半圆鳞片头（scale_row，r 0.35，垂过檐板 = “白花边”）。改成一道平直檐板（Wood，高 FASCIA）
    + 檐板上皮一排小鳞尖（≤ 0.12 m，躺在坡面上，尖点在檐板上皮，不垂下）。
  · 汉式屋顶分量：屋顶高（檐口到脊顶）≥ 墙高（地面到檐下皮）；出檐 ≈ 墙高 / 3（从檐柱 / 墙中线算）；
    直坡、檐口平直、转角不起翘、正脊两端只略起翘。坡度按这个算出来（约 38–45°，比原来 30° 陡）。
    挑梁（LOD0）：柱头上伸出的方木头托出檐（汉代出檐靠挑梁 / 插拱）。
  · 三类（按 seed % 3）：
      B 标准三间：四根檐柱、前出廊、一门两窗；四阿（seed // 3 偶）或悬山（奇）。
      A 小屋：占地 ~0.62 w × 0.86 d，两间 + 中柱（孝堂山石祠式，汉代偶数开间），悬山，门偏一间、另一间开窗。
      C 重檐楼：下层同 B（墙略矮），下檐是一圈腰檐（截头四阿），上面一层矮楼身 + 直棂窗，再一层四阿顶；最高。
屋面槽 FishScale（平的，鳞由贴图 + 法线），脊 Tile；“鱼鳞”只在下檐一圈出小鳞尖（research_han §6 建议，非汉制）。
形制细节（research_han.md §3–6）：矮石台基（0.6–1.0 m，按 seed）、朱漆小八角檐柱 + 覆盆础 + 鎏金柱头箍 + 栌斗、
LacquerBand 檐枋；墙 StoneDark；板门双扇（黑漆，鎏金衔环），直棂窗。
"""
import math

import numpy as np

try:
    from .common import TILE
    from .que import KB, box, beam_x, beam_z, course, extrude, hip_ridges, hip_solid, ngon_prism, prism, ridge, sweep2d, _emit
except ImportError:
    from common import TILE
    from que import KB, box, beam_x, beam_z, course, extrude, hip_ridges, hip_solid, ngon_prism, prism, ridge, sweep2d, _emit

FASCIA = 0.3          # 檐板高（屋面实体檐口的竖直外皮）
TIP_PITCH = 0.24      # 小鳞尖：中距（半宽 0.12）
TIP = 0.1             # 小鳞尖：尖长（沿坡）
TIP_BAND = 0.16       # 鳞尖后面压在坡面上的一条（同一实体）
RIDGE_H = 0.75        # 正脊高（汉脊较高）
RIDGE_LIFT = 0.3      # 正脊两端只略起翘
SLOPE_MIN, SLOPE_MAX = 32.0, 45.0
CLASSES = 'BAC'       # seed % 3 → 类型


def variant(seed):
    """(类型, 是否四阿)。"""
    cls = CLASSES[seed % 3]
    hip = cls == 'C' or (cls == 'B' and (seed // 3) % 2 == 0)
    return cls, hip


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


def scale_tips(ub, T0, e, s, W, a=0.0):
    """檐口小鳞尖：一条躺在坡面上的锯齿带（一个封闭实体）。T0 = 檐板上皮外角，e 沿檐，s 向上坡；
    尖点正好在檐板上皮外沿（v = 0），不垂下；两端各让 a（四阿的戗脊、悬山的垂脊）。"""
    T0, e, s = (np.asarray(x, float) for x in (T0, e, s))
    n = np.cross(e, s)
    if n[1] < 0:
        n = -n
    L = W - 2 * a
    k = max(1, int(round(L / TIP_PITCH)))
    step = L / k
    P, Q = [], []
    for i in range(2 * k + 1):
        u = a + step * i / 2
        P.append((u, 0.0 if i % 2 else TIP))           # 尖 / 谷
        Q.append((u, TIP + TIP_BAND))
    sweep2d(ub, P, Q, T0, e, s, n, 0.004, 0.045, 'FishScale')


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
    cls, hip = variant(seed)
    tb = round(0.6 + 0.4 * rng.random(), 2)                 # 台基高
    ub = KB()
    W2, D2 = w / 2, d / 2
    rtop = RIDGE_H - 0.2                                   # 正脊顶比坡顶高出的量（脊底埋进 0.2）
    # ---------------- 类型 → 檐口范围 X × Z、墙高 ye、坡度
    if cls == 'A':
        X, Z, ye = 0.62 * W2, 0.86 * D2, 0.74 * h
    elif cls == 'B':
        X, Z, ye = W2 - 0.05, D2 - 0.05, 0.8 * h
    else:
        X, Z, ye = W2 - 0.05, D2 - 0.05, 0.74 * h
    if cls != 'C':
        # 屋顶高（檐下皮→脊顶）= FASCIA + Z·tan + rtop ≥ 1.04 墙高；太陡就压低墙
        tn = (1.04 * ye - FASCIA - rtop) / Z
        tn = min(max(tn, math.tan(math.radians(SLOPE_MIN))), math.tan(math.radians(SLOPE_MAX)))
        ye = min(ye, (FASCIA + Z * tn + rtop) / 1.04)
        slope = math.degrees(math.atan(tn))
    ov = ye / 3                                            # 出檐 ≈ 墙高 / 3
    ye = round(ye, 3)

    # ---------------- 柱网
    xc = X - (0.8 if not hip else ov)                       # 檐柱中线（悬山两山只出际 0.8）
    zf, zb = -Z + ov, Z - ov                                # 前檐柱 / 后墙中线
    zw = zf + (1.0 if cls == 'A' else 1.15)                 # 前墙（前出廊）
    yb0 = ye - 0.42                                         # 枋底
    yd0 = yb0 - 0.36                                        # 栌斗底（柱顶）
    if cls == 'A':
        xs = [-xc, 0.0, xc]                                 # 两间 + 中柱
        bay = xc
        side = 1 if (seed // 3) % 2 else -1
        door_x, win_xs = side * xc / 2, [-side * xc / 2]
    else:
        xs = [-xc, -xc / 3, xc / 3, xc]
        bay = 2 * xc / 3
        door_x, win_xs = 0.0, [-bay, bay]
    cr = 0.24 if cls != 'A' else 0.22                       # 八角柱外接半径
    PX, PZ = xc + 0.55, zb + 0.55                           # 台基半宽 / 半深

    # ---------------- 台基
    box(ub, (-PX, -0.3, -PZ), (PX, tb - 0.12, PZ), 'Stone')
    box(ub, (-PX - 0.06, tb - 0.12, -PZ - 0.06), (PX + 0.06, tb, PZ + 0.06), 'Stone')     # 压阑石
    if hi:                                                                                # 角柱 + 间柱（凸 0.05）
        for sx in (-1, 1):
            for z in np.linspace(-PZ + 0.2, PZ - 0.2, 3 if cls == 'A' else 4):
                box(ub, (min(sx * PX, sx * (PX + 0.05)), 0.0, z - 0.2), (max(sx * PX, sx * (PX + 0.05)), tb - 0.12, z + 0.2), 'Stone')
        for sz in (-1, 1):
            for x in np.linspace(-PX + 0.2, PX - 0.2, 4 if cls == 'A' else 6):
                if sz < 0 and abs(x - door_x) < 1.4:
                    continue
                box(ub, (x - 0.2, 0.0, min(sz * PZ, sz * (PZ + 0.05))), (x + 0.2, tb - 0.12, max(sz * PZ, sz * (PZ + 0.05))), 'Stone')
    n_st = max(3, int(math.ceil(tb / 0.2)))                                                # 踏步（对着门）
    sh = tb / n_st
    sw = 1.15 if cls != 'A' else 0.95
    for k in range(n_st - 1):
        box(ub, (door_x - sw, -0.3 if k == 0 else 0.0, -PZ - 0.3 * (n_st - 1 - k)), (door_x + sw, sh * (k + 1), -PZ + 0.01), 'Stone')
    if hi:
        for sx in (-1, 1):                                                                 # 垂带石（楔形）
            x = door_x + sx * (sw + 0.15)
            z0 = -PZ - 0.3 * (n_st - 1) - 0.1
            V = [(x - 0.15, -0.3, z0), (x + 0.15, -0.3, z0), (x + 0.15, -0.3, -PZ + 0.01), (x - 0.15, -0.3, -PZ + 0.01),
                 (x - 0.15, sh + 0.08, z0), (x + 0.15, sh + 0.08, z0), (x + 0.15, tb + 0.08, -PZ + 0.01), (x - 0.15, tb + 0.08, -PZ + 0.01)]
            F = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
            _emit(ub, V, F, 'Stone')

    # ---------------- 柱、墙、枋
    def column(x, z):
        if hi:
            ngon_prism(ub, x, z, cr + 0.16, cr + 0.07, tb - 0.01, tb + 0.16, 8, 'Stone')        # 覆盆础
            ngon_prism(ub, x, z, cr, cr * 0.94, tb + 0.15, yd0 - 0.14, 8, 'Lacquer')
            ngon_prism(ub, x, z, cr * 0.98, cr * 0.98, yd0 - 0.16, yd0 - 0.01, 8, 'Gilt')       # 柱头箍
            ngon_prism(ub, x, z, cr * 0.94, cr * 0.94, yd0 - 0.02, yd0 + 0.01, 8, 'Lacquer')
            s0, s1 = 0.2, 0.3                                                                   # 栌斗：斗欹 + 斗耳
            prism(ub, (x - s0, x + s0, z - s0, z + s0, yd0), (x - s1, x + s1, z - s1, z + s1, yd0 + 0.17), 'Lacquer')
            box(ub, (x - s1, yd0 + 0.17, z - s1), (x + s1, yb0, z + s1), 'Lacquer')
        else:
            ngon_prism(ub, x, z, cr, cr, tb, yb0, 6, 'Lacquer')

    for x in xs:
        column(x, zf)
    if hi:
        for sx in (-1, 1):
            column(sx * xc, zb)
    box(ub, (-xc - 0.14, tb - 0.02, zw), (xc + 0.14, yb0 + 0.01, zb + 0.14), 'StoneDark')       # 墙
    course(ub, xc + 0.18, (zb + 0.18 - (zw - 0.06)) / 2, yb0, ye, 0.0, (zb + 0.18 + zw - 0.06) / 2)
    beam_x(ub, -xc - 0.45, xc + 0.45, yb0, ye, zf - 0.16, zf + 0.16)                           # 前檐枋
    for sx in (-1, 1):
        beam_z(ub, zf + 0.1, zw, yb0, ye, sx * xc - 0.15, sx * xc + 0.15)                       # 廊枋
    if hi:                                                                                      # 挑梁：托出檐
        for x in xs:
            beam_z(ub, -Z + 0.25, zf + 0.12, yb0 + 0.12, ye, x - 0.11, x + 0.11)
            beam_z(ub, zb + 0.1, Z - 0.25, yb0 + 0.12, ye, x - 0.11, x + 0.11)
        if hip:
            for sx in (-1, 1):
                for z in (zf, zb):
                    beam_x(ub, min(sx * (xc + 0.12), sx * (X - 0.25)), max(sx * (xc + 0.12), sx * (X - 0.25)), yb0 + 0.12, ye, z - 0.11, z + 0.11)

    # ---------------- 门、窗
    def window(wx, wy0, ww, wh, zface):
        """直棂窗（外面朝 −z，zface = 墙外皮）。"""
        box(ub, (wx - ww / 2, wy0, zface - 0.03), (wx + ww / 2, wy0 + wh, zface + 0.01), 'LacquerBlack')     # 窗洞底
        fw = 0.11
        box(ub, (wx - ww / 2 - fw, wy0 - fw, zface - 0.11), (wx + ww / 2 + fw, wy0, zface + 0.01), 'LacquerBlack')
        box(ub, (wx - ww / 2 - fw, wy0 + wh, zface - 0.11), (wx + ww / 2 + fw, wy0 + wh + fw, zface + 0.01), 'LacquerBlack')
        box(ub, (wx - ww / 2 - fw, wy0, zface - 0.11), (wx - ww / 2, wy0 + wh, zface + 0.01), 'LacquerBlack')
        box(ub, (wx + ww / 2, wy0, zface - 0.11), (wx + ww / 2 + fw, wy0 + wh, zface + 0.01), 'LacquerBlack')
        nb = max(4, int(ww / 0.16))
        for i in range(1, nb):
            bx = wx - ww / 2 + ww * i / nb
            box(ub, (bx - 0.032, wy0, zface - 0.09), (bx + 0.032, wy0 + wh, zface - 0.02), 'Wood')

    dw = min(1.9 if cls != 'A' else 1.5, bay * 0.62)
    dh = min(2.75, (yb0 - tb) * 0.78)
    yd = tb + 0.14
    if hi:
        box(ub, (door_x - dw / 2 - 0.1, tb - 0.01, zw - 0.14), (door_x + dw / 2 + 0.1, yd, zw + 0.02), 'LacquerBlack')      # 门槛
        for sx in (-1, 1):
            x0, x1 = door_x + sx * dw / 2, door_x + sx * (dw / 2 + 0.2)
            box(ub, (min(x0, x1), tb, zw - 0.13), (max(x0, x1), yd + dh + 0.22, zw + 0.02), 'LacquerBlack')          # 门框
        box(ub, (door_x - dw / 2 - 0.36, yd + dh, zw - 0.15), (door_x + dw / 2 + 0.36, yd + dh + 0.24, zw + 0.02), 'LacquerBlack')   # 门楣
        for sx in (-1, 1):                                                                   # 两扇（关着）
            x0, x1 = door_x + sx * 0.012, door_x + sx * dw / 2
            box(ub, (min(x0, x1), yd, zw - 0.07), (max(x0, x1), yd + dh, zw + 0.02), 'LacquerBlack')
            cx, cy = door_x + sx * min(0.3, dw * 0.16), yd + dh * 0.5                         # 衔环
            extrude(ub, (cx, cy, zw - 0.065), (cx, cy, zw - 0.11), (0, 1.0, 0),
                    [(0.11 * math.cos(2 * math.pi * j / 6), 0.11 * math.sin(2 * math.pi * j / 6)) for j in range(6)], 'Gilt')
            torus(ub, (cx, cy - 0.13, zw - 0.125), (0, 0, 1.0), 0.12, 0.022, 10, 4, 'Gilt')
        ww, wh = min(1.35, bay * 0.5), min(1.0, (yb0 - tb) * 0.3)
        wy0 = tb + min(1.3, (yb0 - tb) * 0.4)
        for wx in win_xs:
            window(wx, wy0, ww, wh, zw)
    else:
        box(ub, (door_x - dw / 2, tb, zw - 0.06), (door_x + dw / 2, yd + dh, zw + 0.02), 'LacquerBlack')

    # ---------------- 屋顶
    info = dict(cls=cls, hip=hip, wall=ye, overhang=round(ov, 2))
    if cls == 'C':
        # 下檐：一圈腰檐（截头四阿，30°），上面矮楼身 + 上檐四阿
        Zi = max(1.3, 0.4 * Z)
        r = Z - Zi
        Xi = X - r
        lo = hip_solid(ub, 0, 0, X, Z, ye, FASCIA, 30.0, inner=(Xi, Zi), top='FishScale', fas='Wood', soffit='Wood')
        hip_ridges(ub, lo, 0.28, 0.2)
        if hi:
            a = (TIP + TIP_BAND) * math.cos(math.radians(30.0)) + 0.18
            for sd in lo['sides']:
                scale_tips(ub, sd['T0'], sd['e'], sd['s'], sd['W'], a)
        yi = lo['y_top']
        Xu, Zu = Xi + 0.1, Zi + 0.1                                # 上层楼身（略大于腰檐内口，盖住平顶）
        ye2 = yi + max(1.25, 0.3 * ye)
        box(ub, (-Xu, ye + 0.2, -Zu), (Xu, ye2 - 0.34, Zu), 'StoneDark')
        course(ub, Xu + 0.06, Zu + 0.06, ye2 - 0.34, ye2)
        if hi:
            uh = min(0.75, ye2 - 0.34 - yi - 0.3)
            for k in (-1, 0, 1):
                window(k * Xu * 0.6, yi + 0.2, min(1.1, Xu * 0.45), uh, -Zu)
        ov2 = 0.95
        X2, Z2 = Xu + ov2, Zu + ov2
        roof = hip_solid(ub, 0, 0, X2, Z2, ye2, FASCIA, 40.0, top='FishScale', fas='Wood', soffit='Wood')
        yr = roof['y_top']
        hip_ridges(ub, roof, 0.3, 0.26)
        ridge(ub, (0, 0, 0), 'x', X2 - Z2 + 0.15, yr - 0.2, RIDGE_H, 0.42, RIDGE_LIFT, n_end=5 if hi else 2)
        info.update(slope='30/40', ye2=round(ye2, 2))
    elif hip:
        roof = hip_solid(ub, 0, 0, X, Z, ye, FASCIA, slope, top='FishScale', fas='Wood', soffit='Wood')
        yr = roof['y_top']
        hip_ridges(ub, roof, 0.3, 0.26)
        ridge(ub, (0, 0, 0), 'x', X - Z + 0.15, yr - 0.2, RIDGE_H, 0.42, RIDGE_LIFT, n_end=5 if hi else 2)
        if hi:
            a = (TIP + TIP_BAND) * math.cos(math.radians(slope)) + 0.18
            for sd in roof['sides']:
                scale_tips(ub, sd['T0'], sd['e'], sd['s'], sd['W'], a)
        info.update(slope=round(slope, 1))
    else:
        Xg = X                                                           # 悬山出际到 X
        g = gable_roof(ub, Xg, Z, ye, FASCIA, slope)
        yr = g['yr']
        tn = math.tan(math.radians(slope))
        # 山墙 / 廊顶：墙线以上到屋面下皮的五边形实体
        za, zb2 = zf - 0.22, zb + 0.18
        xa = xc + 0.16
        sec = [(za, ye - 0.01), (zb2, ye - 0.01), (zb2, ye + (Z - zb2) * tn - 0.02),
               (0.0, yr - FASCIA - 0.02), (za, ye + (Z + za) * tn - 0.02)]
        V = [(x, y, z) for x in (-xa, xa) for (z, y) in sec]
        n = len(sec)
        F = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
        F += [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
        _emit(ub, V, F, 'StoneDark')
        for sx in (-1, 1):                                               # 垂脊（两山沿坡）
            x = sx * (Xg - 0.17)
            for sz in (-1, 1):
                p0 = np.array([x, ye + FASCIA, sz * Z])
                p1 = np.array([x, yr, 0.0])
                d_ = p1 - p0
                extrude(ub, p0 - d_ * 0.01, p1, (0, 1.0, 0), [(-0.17, -0.1), (0.17, -0.1), (0.17, 0.24), (-0.17, 0.24)], 'Tile')
        ridge(ub, (0, 0, 0), 'x', Xg + 0.05, yr - 0.2, RIDGE_H, 0.42, RIDGE_LIFT, n_end=5 if hi else 2)
        if hi:
            for sz in (-1, 1):
                T0 = np.array([-Xg if sz < 0 else Xg, ye + FASCIA, sz * Z])
                e = np.array([1.0 if sz < 0 else -1.0, 0, 0])
                scale_tips(ub, T0, e, g['sf'] if sz < 0 else g['sb'], 2 * Xg, 0.36)
        info.update(slope=round(slope, 1))
    info['roof'] = round(yr - 0.2 + RIDGE_H - ye, 2)                       # 檐下皮 → 脊顶（不含端头起翘）
    info['top'] = round(yr - 0.2 + RIDGE_H, 2)
    ub.info = info
    return ub


if __name__ == '__main__':
    from que import check_closed_outward
    for (w, h, d) in ((9.0, 4.8, 7.0), (10.2, 5.2, 7.5), (11.4, 5.6, 8.0), (9.6, 5.6, 7.0)):
        for seed in range(6):
            for lod in (0, 1):
                u = build(w, h, d, lod, seed)
                bad, frac = check_closed_outward(u)
                print('house %4.1f×%3.1f×%3.1f seed%d lod%d: %5d tris, %3d parts, bad %d, centroid %.3f  %s'
                      % (w, h, d, seed, lod, u.tris(), len(u.parts), len(bad), frac, u.info if lod == 0 else ''))
