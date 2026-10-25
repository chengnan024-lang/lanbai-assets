# -*- coding: utf-8 -*-
"""大殿（朱宫）+ 台基 —— 河伯宫。

**直接用宫殿坐标**（Unity 轴，x 右、y 上、z 前，米；正面朝 −z），数据见 Act07_Sea/PalaceFrame_约定.json 的 `hall`。
build(lod=0) -> UB；不碰 bpy。

形制（research_han.md + 总导演裁决）：汉制，直坡重檐四阿，檐口平直、转角不起翘，只在檐口最外 1/5 折缓 5°（反宇）；
正脊两端起翘 + 瓦当相叠（第 6 轮：考据核实后去掉鱼尾，D-29 #3 / 总导演 10-24）；只在柱头放斗拱（栌斗 + 一斗二升 / 一斗三升，端柱曲栱）；八角柱、覆盆础；
钩阑：望柱 + 寻杖 + 斜格 / 卧棂（相间）；板门双扇向里开 70°，铺首只留鎏金圆环。
所有部件都是封闭实体（有底面）；check() 逐件验证流形 + 体积为正（法线朝外）。
"""
import math

import numpy as np

try:
    from .common import UB, lathe, TILE
except ImportError:  # 直接当脚本 / sys.path 里有 kit/
    from common import UB, lathe, TILE

# ------------------------------------------------------------------ 约定数据（PalaceFrame_约定.json · hall）
X0, X1 = -68.0, -8.0            # 殿身
ZF, DEPTH = 342.6, 28.0         # 前檐墙 / 进深
ZB = ZF + DEPTH                 # 后墙 370.6
H_TOTAL = 30.0
BAYS = 9
BAY = (X1 - X0) / BAYS          # 6.667
DOOR_X, DOOR_W, DOOR_H = -18.0, 4.2, 7.5
MINGJIAN = 11.5                 # 门廊明间宽（终审 10-25 #4；原来是一个开间 6.67）
PX0, PX1, PZ0, PZ1, PY = -72.0, -8.0, 334.1, 376.6, 6.0   # 台基
SX0, SX1, SZ0, SZ1 = -22.0, -14.0, 325.1, 334.1           # 阶（墄）
RIDGE_TOP = PY + H_TOTAL        # 36

# ------------------------------------------------------------------ 设计取值
T_IN, T_OUT = math.tan(math.radians(30.0)), math.tan(math.radians(25.0))   # 坡 30°，反宇段 25°（两层同坡）
WALL_T = 0.8                    # 前墙厚
COL_Z = ZF - 3.8                # 檐柱中线 338.8
COL_INSET = 1.1                 # 两端柱内收（不然 x=−8 那根的柱础要悬出崖口）
COL_FLAT0, COL_FLAT1 = 1.1, 1.0 # 八角柱对边宽（底 / 顶）
COL_TOP = PY + 9.0              # 柱顶 15.0
ROOF_T = 0.45                   # 屋面板厚（竖向）
# 下檐（腰檐，一圈）：外缘 = 前檐柱外 4.5 m、两侧及后墙外 4.5 m
LO_RECT = (X0 - 4.5, X1 + 4.5, COL_Z - 4.5, ZB + 4.5)
LO_BRK = 0.9                    # 反宇段平面长（出檐 4.5 的 1/5）
LO_TIP = 19.05 - (LO_BRK * T_OUT + (4.5 - LO_BRK) * T_IN)  # 檐柱缝上屋面顶 = 19.05
LO_DTOP = 8.645                 # 腰檐上缘内收（上层殿身前墙 ≈ 下层前墙）
LO_TOPY = LO_TIP + LO_BRK * T_OUT + (LO_DTOP - LO_BRK) * T_IN   # 腰檐上缘（接上层殿身）≈ 21.44
# 上层殿身（重檐的上层墙）= 腰檐上缘内框
UP_BODY = (LO_RECT[0] + LO_DTOP, LO_RECT[1] - LO_DTOP, LO_RECT[2] + LO_DTOP, LO_RECT[3] - LO_DTOP)
UP_OUT = 4.0
UP_RECT = (UP_BODY[0] - UP_OUT, UP_BODY[1] + UP_OUT, UP_BODY[2] - UP_OUT, UP_BODY[3] + UP_OUT)
UP_BRK = 0.8
UP_DTOP = (UP_RECT[3] - UP_RECT[2]) / 2
UP_APEX = RIDGE_TOP - 1.5       # 屋面顶（正脊底）34.5
UP_TIP = UP_APEX - (UP_BRK * T_OUT + (UP_DTOP - UP_BRK) * T_IN)
TILE_PITCH = 1.1
TILE_R = 0.27


def roof_h(d, tip, brk):
    """屋面顶面高度：d = 到檐口的平面距离。"""
    return tip + (d * T_OUT if d <= brk else brk * T_OUT + (d - brk) * T_IN)


def lo_under(x, z):
    """腰檐底面高度（任意平面点）。"""
    x0, x1, z0, z1 = LO_RECT
    d = min(x - x0, x1 - x, z - z0, z1 - z)
    return roof_h(d, LO_TIP, LO_BRK) - ROOF_T


# ================================================================== 几何小工具
def _newell(P):
    P = np.asarray(P, float)
    n = np.zeros(3)
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
    return n


def volume(ub):
    V = np.asarray(ub.V, float)
    s = 0.0
    for f in ub.F:
        p0 = V[f[0]]
        for i in range(1, len(f) - 1):
            s += np.dot(p0, np.cross(V[f[i]], V[f[i + 1]]))
    return s / 6.0


def solid(ub):
    """整体翻成法线朝外（体积为正）。"""
    if volume(ub) < 0:
        ub.F = [tuple(reversed(f)) for f in ub.F]
        ub.UV = [list(reversed(u)) for u in ub.UV]
    return ub


def box(lo, hi, slot):
    u = UB()
    u.box(lo, hi, slot)
    return u


def frame_box(p0, p1, w, h, slot, up=(0, 1, 0), band=False):
    """沿 p0→p1 的方梁：截面 w（水平侧向）× h（近似竖向），中心线 = p0→p1。band：沿梁 UV（u = 米/4，v = 0..1）。"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    a = p1 - p0
    L = np.linalg.norm(a)
    a /= L
    up = np.asarray(up, float)
    if abs(np.dot(up, a)) > 0.95:
        up = np.array([0, 0, 1.0])
    u = up - np.dot(up, a) * a
    u /= np.linalg.norm(u)
    s = np.cross(a, u)
    loc = UB()
    loc.box((0, -h / 2, -w / 2), (L, h / 2, w / 2), slot)
    if band:
        V = np.asarray(loc.V)
        for k, f in enumerate(loc.F):
            P = V[list(f)]
            n = _newell(P)
            ax = int(np.argmax(np.abs(n)))
            if ax == 2:
                loc.UV[k] = [(p[0] / 4.0, (p[1] + h / 2) / h) for p in P]
            elif ax == 1:
                loc.UV[k] = [(p[0] / 4.0, (p[2] + w / 2) / w) for p in P]
            else:
                loc.UV[k] = [((p[2] + w / 2) / 4.0, (p[1] + h / 2) / h) for p in P]
    M = np.column_stack([a, u, s])
    return solid(loc.transformed(M, p0))


def beam_x(x0, x1, y0, y1, z0, z1, slot='LacquerBand'):
    """沿 x 的枋（LacquerBand 给沿梁 UV）。"""
    yc, zc = (y0 + y1) / 2, (z0 + z1) / 2
    return frame_box((x0, yc, zc), (x1, yc, zc), z1 - z0, y1 - y0, slot, band=(slot == 'LacquerBand'))


def beam_z(z0, z1, y0, y1, x0, x1, slot='LacquerBand'):
    yc, xc = (y0 + y1) / 2, (x0 + x1) / 2
    return frame_box((xc, yc, z0), (xc, yc, z1), x1 - x0, y1 - y0, slot, band=(slot == 'LacquerBand'))


def _tri2d(P):
    """耳切三角化（P 逆时针）。"""
    P = [np.asarray(p, float) for p in P]
    idx = list(range(len(P)))
    out = []

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = P[i0], P[i1], P[i2]
            if cr(a, b, c) <= 1e-12:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                p = P[j]
                if cr(a, b, p) >= -1e-12 and cr(b, c, p) >= -1e-12 and cr(c, a, p) >= -1e-12:
                    ok = False
                    break
            if ok:
                out.append((i0, i1, i2))
                idx.pop(k)
                break
        else:
            break
    out.append(tuple(idx[:3]))
    return out


def extrude(P2, o, eu, ev, ew, w0, w1, slot):
    """平面多边形 P2（u,v）沿 ew 从 w0 挤到 w1 的封闭棱柱。"""
    P2 = [tuple(p) for p in P2]
    area = sum(P2[i][0] * P2[(i + 1) % len(P2)][1] - P2[(i + 1) % len(P2)][0] * P2[i][1] for i in range(len(P2)))
    if area < 0:
        P2 = P2[::-1]
    o, eu, ev, ew = (np.asarray(v, float) for v in (o, eu, ev, ew))
    n = len(P2)
    V = [o + u * eu + v * ev + w0 * ew for u, v in P2] + [o + u * eu + v * ev + w1 * ew for u, v in P2]
    F = []
    for t in _tri2d(P2):
        F.append((t[0] + n, t[1] + n, t[2] + n))
        F.append((t[2], t[1], t[0]))
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, j + n, i + n))
    u = UB()
    u.add(V, F, slot)
    return solid(u)


def sweep(rings, slot, cap=True):
    """把一串同拓扑的截面环（每环 m 点）连成封闭管。"""
    rings = [np.asarray(r, float) for r in rings]
    m = len(rings[0])
    w = rings[-1].mean(0) - rings[0].mean(0)
    if np.dot(_newell(rings[0]), w) < 0:
        rings = [r[::-1] for r in rings]
    V = np.concatenate(rings)
    F = []
    for k in range(len(rings) - 1):
        for i in range(m):
            j = (i + 1) % m
            F.append((k * m + i, k * m + j, (k + 1) * m + j, (k + 1) * m + i))
    if cap:
        F.append(tuple(range(m))[::-1])
        F.append(tuple((len(rings) - 1) * m + i for i in range(m)))
    u = UB()
    u.add(V, F, slot)
    return solid(u)


def lathe_solid(profile, n, slot, center, angle0=0.0):
    u = UB()
    lathe(profile, n, slot, u, center=center, angle0=angle0, cap_top=True, cap_bottom=True)
    return solid(u)


def sq_lathe(profile_hw, slot, center):
    """方形“回转体”（斗）：profile = [(半宽, y)]。"""
    return lathe_solid([(r * math.sqrt(2), y) for r, y in profile_hw], 4, slot, center, angle0=math.pi / 4)


def octa(flat0, flat1, y0, y1, slot, x, z):
    k = 0.5 / math.cos(math.pi / 8)
    return lathe_solid([(flat0 * k, 0.0), (flat1 * k, y1 - y0)], 8, slot, (x, y0, z), angle0=math.pi / 8)


def torus(R, r, n, m, slot, M, t):
    """圆环（局部 x-y 平面，法线 z），再变换 M / t。"""
    V, F = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        for j in range(m):
            b = 2 * math.pi * j / m
            rr = R + r * math.cos(b)
            V.append((rr * math.cos(a), rr * math.sin(a), r * math.sin(b)))
    for i in range(n):
        for j in range(m):
            i2, j2 = (i + 1) % n, (j + 1) % m
            F.append((i * m + j, i2 * m + j, i2 * m + j2, i * m + j2))
    u = UB()
    u.add(V, F, slot)
    return solid(solid(u).transformed(M, t))


def oriented_face(ub, P, want, slot):
    P = [tuple(map(float, p)) for p in P]
    Q = [P[0]]
    for p in P[1:]:
        if np.linalg.norm(np.subtract(p, Q[-1])) > 1e-9:
            Q.append(p)
    if len(Q) > 2 and np.linalg.norm(np.subtract(Q[0], Q[-1])) < 1e-9:
        Q.pop()
    if len(Q) < 3:
        return
    if np.dot(_newell(Q), want) < 0:
        Q = Q[::-1]
    ub.add(Q, [tuple(range(len(Q)))], slot)


# ================================================================== 屋顶
def _levels(rect, tip, brk, dtop):
    x0, x1, z0, z1 = rect
    out = []
    for d in (0.0, brk, dtop):
        y = roof_h(d, tip, brk)
        out.append([(x0 + d, y, z0 + d), (x1 - d, y, z0 + d), (x1 - d, y, z1 - d), (x0 + d, y, z1 - d)])
    return out


def roof_slab(rect, tip, brk, dtop, ring, slot='Tile'):
    """直坡四阿（ring=False，顶为正脊）或一圈腰檐（ring=True，顶为内框）的封闭板。"""
    L = _levels(rect, tip, brk, dtop)
    Lb = [[(p[0], p[1] - ROOF_T, p[2]) for p in lv] for lv in L]
    cx, cz = (rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2
    u = UB()
    for k in range(2):
        for j in range(4):
            j2 = (j + 1) % 4
            oriented_face(u, [L[k][j], L[k][j2], L[k + 1][j2], L[k + 1][j]], (0, 1, 0), slot)
            oriented_face(u, [Lb[k][j], Lb[k][j2], Lb[k + 1][j2], Lb[k + 1][j]], (0, -1, 0), slot)
    for j in range(4):
        j2 = (j + 1) % 4
        mid = np.add(L[0][j], L[0][j2]) / 2
        out = (mid[0] - cx, 0, mid[2] - cz)
        oriented_face(u, [L[0][j], L[0][j2], Lb[0][j2], Lb[0][j]], out, slot)
        if ring:
            mid = np.add(L[2][j], L[2][j2]) / 2
            oriented_face(u, [L[2][j], L[2][j2], Lb[2][j2], Lb[2][j]], (cx - mid[0], 0, cz - mid[2]), slot)
    return solid(u)


def roof_tiles(rect, tip, brk, dtop, parts, rows=True, nd=12):
    """筒瓦垄（中距 1.1）+ 檐口瓦当。"""
    x0, x1, z0, z1 = rect
    C = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    nseg = 7
    for j in range(4):
        a, b = np.array(C[j]), np.array(C[(j + 1) % 4])
        L = np.linalg.norm(b - a)
        e = (b - a) / L
        nin = np.array([-e[1], e[0]])          # 平面里向内
        if np.dot(nin, np.array([(x0 + x1) / 2, (z0 + z1) / 2]) - a) < 0:
            nin = -nin
        n = int(L // TILE_PITCH)
        s0 = (L - (n - 1) * TILE_PITCH) / 2
        e3, nin3 = np.array([e[0], 0, e[1]]), np.array([nin[0], 0, nin[1]])
        for i in range(n):
            s = s0 + i * TILE_PITCH
            dmax = min(s, L - s, dtop) - 0.05
            if dmax < 0.6:
                continue
            ds = [0.0, brk, dmax] if dmax > brk + 0.05 else [0.0, dmax]
            rings = []
            for d in ds:
                p = a + e * s + nin * d
                c = np.array([p[0], roof_h(d, tip, brk) - 0.08, p[1]])
                rings.append([c + e3 * TILE_R * math.cos(math.pi * q / (nseg - 1)) +
                              np.array([0, 1, 0]) * TILE_R * math.sin(math.pi * q / (nseg - 1)) for q in range(nseg)])
            if rows:
                parts.append(('tile', sweep(rings, 'Tile')))
            # 瓦当：正对檐口的八边形圆盘
            p = a + e * s
            c = np.array([p[0], roof_h(0, tip, brk) - 0.08, p[1]])
            disc = []
            for dd in (-0.07, 0.04):
                disc.append([c + nin3 * dd + e3 * 0.3 * math.cos(2 * math.pi * q / nd) +
                             np.array([0, 1, 0]) * 0.3 * math.sin(2 * math.pi * q / nd) for q in range(nd)])
            parts.append(('wadang', sweep(disc, 'Tile')))


def rafters(rect, tip, brk, dreach, parts, pitch=1.1, w=0.26):
    """檐下椽子：贴着屋面板底，从檐口伸到 dreach（墙 / 檐枋缝），转角处随戗线截短（汉式平行椽，不做扇形）。"""
    x0, x1, z0, z1 = rect
    C = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    for j in range(4):
        a, b = np.array(C[j]), np.array(C[(j + 1) % 4])
        L = np.linalg.norm(b - a)
        e = (b - a) / L
        nin = np.array([-e[1], e[0]])
        if np.dot(nin, np.array([(x0 + x1) / 2, (z0 + z1) / 2]) - a) < 0:
            nin = -nin
        e3 = np.array([e[0], 0, e[1]])
        n = int(L // pitch)
        s0 = (L - (n - 1) * pitch) / 2
        for i in range(n):
            s = s0 + i * pitch
            dmax = min(s, L - s, dreach)
            if dmax < 0.5:
                continue
            ds = [0.12, brk, dmax] if dmax > brk + 0.05 else [0.12, dmax]
            rings = []
            for d in ds:
                p = a + e * s + nin * d
                y = roof_h(d, tip, brk) - ROOF_T + 0.02
                c = np.array([p[0], y, p[1]])
                rings.append([c + e3 * w / 2, c - e3 * w / 2, c - e3 * w / 2 - (0, w, 0), c + e3 * w / 2 - (0, w, 0)])
            parts.append(('rafter', sweep(rings, 'LacquerBlack')))


def hip_ridges(rect, tip, brk, dtop, w=0.7, h=0.7):
    """垂脊：沿四条戗线（平面 45°），直，不起翘。"""
    L = _levels(rect, tip, brk, dtop)
    cx, cz = (rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2
    out = []
    for j in range(4):
        pts = [np.array(L[k][j]) for k in range(3)]
        dirp = pts[2] - pts[0]
        side = np.array([-dirp[2], 0, dirp[0]])
        side /= np.linalg.norm(side)
        rings = []
        for p in pts:
            rings.append([p + side * w / 2 + (0, -0.25, 0), p - side * w / 2 + (0, -0.25, 0),
                          p - side * w * 0.35 + (0, h, 0), p + side * w * 0.35 + (0, h, 0)])
        out.append(sweep(rings, 'Tile'))
        # 脊头瓦当
        p0 = pts[0]
        outd = np.array([p0[0] - cx, 0, p0[2] - cz])
        outd /= np.linalg.norm(outd)
        c = p0 + np.array([0, 0.1, 0])
        disc = [[c + outd * dd + side * 0.38 * math.cos(2 * math.pi * q / 8 + math.pi / 8) +
                 np.array([0, 0.38, 0]) * math.sin(2 * math.pi * q / 8 + math.pi / 8) for q in range(8)] for dd in (-0.05, 0.06)]
        out.append(sweep(disc, 'Tile'))
    return out


def _fin_map(o, sgn, u, v, w, k=0.9):
    """鱼尾局部 (u 向外, v 向上, w 沿 z) → 世界；先向内弯（v 越高越往脊中收），再缩放。"""
    u = u - 0.22 * (max(v, 0.0) / 1.5) ** 2
    return o + np.array([sgn * u * k, v * k, w * k])


def fish_tail(o, sgn):
    out = []
    # 鳍身：一层层水平透镜截面（内缘 / 外缘 / 半厚）
    lv = [(-0.5, -1.9, 0.35, 0.20), (0.05, -1.9, 0.42, 0.20), (0.2, -1.15, 0.44, 0.19), (0.4, -0.72, 0.45, 0.17),
          (0.6, -0.48, 0.43, 0.15), (0.85, -0.32, 0.46, 0.13), (1.1, -0.15, 0.52, 0.11)]
    rings = []
    for v, ui, uo, t in lv:
        sp = uo - ui
        sec = [(ui, 0), (ui + 0.3 * sp, t), (uo - 0.25 * sp, t), (uo, 0), (uo - 0.25 * sp, -t), (ui + 0.3 * sp, -t)]
        rings.append([_fin_map(o, sgn, u, v, w) for u, w in sec])
    out.append(sweep(rings, 'Tile'))
    # 两叉：沿弯的中线，宽和厚都收到梢（梢全厚 0.08）
    for path, hw in (([(0.28, 0.95), (0.48, 1.2), (0.66, 1.38), (0.84, 1.56)], [0.2, 0.16, 0.1, 0.035]),
                     ([(-0.02, 0.95), (-0.1, 1.12), (-0.17, 1.27), (-0.22, 1.38)], [0.17, 0.13, 0.08, 0.03])):
        ts = [0.11, 0.09, 0.065, 0.04]
        rings = []
        P = np.array(path)
        for k in range(len(P)):
            T = P[min(k + 1, len(P) - 1)] - P[max(k - 1, 0)]
            T /= np.linalg.norm(T)
            N = np.array([-T[1], T[0]])
            p, h, t = P[k], hw[k], ts[k]
            sec = [(p + N * h, 0), (p + N * h * 0.4, t), (p - N * h * 0.4, t), (p - N * h, 0), (p - N * h * 0.4, -t), (p + N * h * 0.4, -t)]
            rings.append([_fin_map(o, sgn, q[0], q[1], w) for q, w in sec])
        out.append(sweep(rings, 'Tile'))
    return out


def stacked_wadang(o, sgn, n=3, r=0.34, t=0.14):
    """瓦当相叠：n 枚圆瓦当（半径 r、厚 t），面朝外（±x），竖着叠，每枚高 0.62 r·2、往外探 0.06。"""
    out = []
    Rm = np.array([[0, sgn, 0], [-sgn, 0, 0], [0, 0, 1.0]])       # lathe 的 y 轴（盘的法线）→ ±x
    for k in range(n):
        c = o + np.array([sgn * 0.06 * k, k * r * 1.25, 0.0])
        disc = lathe_solid([(r, 0.0), (r, t), (r * 0.82, t + 0.03), (r * 0.25, t + 0.05)], 16, 'Tile', (0, 0, 0))
        out.append(solid(disc.transformed(Rm, c)))
    return out


def main_ridge(lod):
    """正脊：高 1.5，两端起翘约 0.75 m，端头三枚瓦当相叠（汉制；第 6 轮去掉了鱼尾）。"""
    x0, x1, z0, z1 = UP_RECT
    xa, xb = x0 + UP_DTOP, x1 - UP_DTOP
    zc = (z0 + z1) / 2
    y0 = UP_APEX - 0.5
    out = []
    # 下层叠瓦（宽）
    out.append(box((xa - 0.6, y0, zc - 0.65), (xb + 0.6, UP_APEX + 0.7, zc + 0.65), 'Tile'))
    # 上层脊身：两端 3 m 内起翘
    top = RIDGE_TOP
    rise, Lr = 0.75, 3.2
    prof = [(xa - 0.6, y0), (xb + 0.6, y0)]
    nn = 5
    for i in range(nn + 1):           # 右端，向内
        t = 1 - i / nn
        prof.append((xb + 0.6 - (1 - t) * Lr, top + rise * t ** 2))
    for i in range(nn + 1):           # 左端，向外
        t = i / nn
        prof.append((xa - 0.6 + (1 - t) * Lr, top + rise * t ** 2))
    prof = [prof[0], prof[1]] + [prof[2]] + prof[3:]
    # 去重相邻点
    P = []
    for p in prof:
        if not P or abs(p[0] - P[-1][0]) + abs(p[1] - P[-1][1]) > 1e-6:
            P.append(p)
    out.append(extrude(P, (0, 0, zc), (1, 0, 0), (0, 1, 0), (0, 0, 1), -0.45, 0.45, 'Tile'))
    # 脊端（第 6 轮，考据核实：汉代“脊端以瓦當相疊為飾，或翹起，或伸出，正式鴟尾則未見也”——梁思成；
    # 鸱尾最早见于东晋 385 年）：正脊照旧起翘，端头叠三枚无字卷云瓦当，朝外，一枚比一枚高、略往外探
    for sgn, xe, xr in ((1, xb + 0.6, xb), (-1, xa - 0.6, xa)):
        o = np.array([xe - 0.25 * sgn, top + rise - 0.15, zc])
        out.extend(stacked_wadang(o, sgn))
        # 脊头：堵住两条垂脊在正脊端头汇合处的缝
        lo_x, hi_x = sorted((xr - 1.2 * sgn, xr + 1.1 * sgn))
        out.append(box((lo_x, UP_APEX - 0.7, zc - 0.95), (hi_x, UP_APEX + 0.75, zc + 0.95), 'Tile'))
    return out


# ================================================================== 斗拱
def gong_profile(L, H, curved):
    """栱的侧面轮廓（u 沿栱，v 向上），两端卷杀；curved = 曲栱（两臂向上弯）。"""
    P_bot, P_top = [], []
    n = 8
    for i in range(n + 1):
        u = -L / 2 + L * i / n
        t = abs(u) / (L / 2)
        if curved:
            vb = 0.42 * t ** 2
            vt = vb + H * (1.0 - 0.15 * t)
        else:
            vb = 0.0 if t < 0.6 else 0.2 * ((t - 0.6) / 0.4) ** 1.5
            vt = H
        P_bot.append((u, vb))
        P_top.append((u, vt))
    return P_bot + P_top[::-1], P_top


def bracket(x, z, y0, scale, kind, along_z=False, projecting=0.0):
    """柱头斗拱：栌斗 + 栱 + 升。kind: 2 / 3 / 'qu'。返回 (parts, 升顶 y)。"""
    s = scale
    out = []
    lu = [(0.5, 0.0), (0.55, 0.2), (0.62, 0.33), (0.7, 0.45), (0.7, 0.85)]
    out.append(sq_lathe([(r * s, v * s) for r, v in lu], 'Lacquer', (x, y0, z)))
    yg = y0 + 0.85 * s
    L, H = 3.6 * s, 0.45 * s
    P, top = gong_profile(L, H, kind == 'qu')
    if along_z:
        out.append(extrude(P, (x, yg, z), (0, 0, 1), (0, 1, 0), (-1, 0, 0), -0.3 * s, 0.3 * s, 'LacquerBlack'))
    else:
        out.append(extrude(P, (x, yg, z), (1, 0, 0), (0, 1, 0), (0, 0, 1), -0.3 * s, 0.3 * s, 'LacquerBlack'))
    sh = [(0.25, 0.0), (0.3, 0.14), (0.35, 0.22), (0.35, 0.45)]
    us = [-1.45 * s, 1.45 * s] + ([0.0] if kind == 3 else [])
    ytop = yg + H + 0.45 * s
    for u in us:
        t = abs(u) / (L / 2)
        vt = (0.42 * t ** 2 + H * (1 - 0.15 * t)) if kind == 'qu' else H
        c = (x, yg + vt - 0.02, z + u) if along_z else (x + u, yg + vt - 0.02, z)
        out.append(sq_lathe([(r * s, v * s) for r, v in sh], 'Lacquer', c))
    # 向前挑出的插栱（只半边：从柱心伸出 projecting 米）+ 头上一个升
    if projecting > 0:
        Pp = [(0.0, 0.0), (projecting - 0.5, 0.0), (projecting, 0.2 * s), (projecting, H), (0.0, H)]
        out.append(extrude(Pp, (x, yg, z), (0, 0, -1), (0, 1, 0), (1, 0, 0), -0.28 * s, 0.28 * s, 'LacquerBlack'))
        out.append(sq_lathe([(r * s, v * s) for r, v in sh], 'Lacquer', (x, yg + H - 0.02, z - projecting + 0.35 * s)))
    return out, ytop


# ================================================================== 钩阑
def balustrade(p0, p1, y, H, low, detail):
    """从 p0 到 p1（平面 (x,z)）的一段钩阑。low = 矮栏（崖口那面）。"""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    L = np.linalg.norm(p1 - p0)
    e = (p1 - p0) / L
    out = []
    n = max(1, int(math.ceil(L / 2.4)))
    step = L / n
    pw = 0.25 if not low else 0.22

    def P(s, h):
        q = p0 + e * s
        return (q[0], y + h, q[1])

    for i in range(n + 1):
        q = p0 + e * i * step
        top = H + 0.12
        out.append(box((q[0] - pw / 2, y, q[1] - pw / 2), (q[0] + pw / 2, y + top, q[1] + pw / 2), 'Lacquer'))
        out.append(box((q[0] - pw / 2 - 0.04, y + top, q[1] - pw / 2 - 0.04), (q[0] + pw / 2 + 0.04, y + top + 0.08, q[1] + pw / 2 + 0.04), 'Lacquer'))
    # 寻杖、盆唇、地栿（通长）
    out.append(frame_box(P(0, H - 0.06), P(L, H - 0.06), 0.13, 0.12, 'Lacquer'))
    out.append(frame_box(P(0, 0.07), P(L, 0.07), 0.18, 0.14, 'Lacquer'))
    if low:
        out.append(frame_box(P(0, H * 0.5), P(L, H * 0.5), 0.08, 0.08, 'Lacquer'))
        return out
    yb0, yb1 = 0.14, 0.62
    out.append(frame_box(P(0, yb1 + 0.04), P(L, yb1 + 0.04), 0.1, 0.08, 'Lacquer'))
    if not detail:
        return out
    # 盆唇上、寻杖下：短蜀柱
    for i in range(n):
        s = (i + 0.5) * step
        out.append(frame_box(P(s, yb1 + 0.08), P(s, H - 0.12), 0.08, 0.08, 'Lacquer', up=(e[0], 0, e[1])))
    # 栏板：斜格 / 卧棂 相间
    hh = yb1 - yb0
    for i in range(n):
        sa, sb = i * step + pw / 2, (i + 1) * step - pw / 2
        Lp = sb - sa
        if i % 2 == 0:      # 斜格
            pitch = hh
            for sign in (1, -1):
                c = -hh
                while c < Lp:
                    # 直线 u = c + v*sign*1（45°），在 [0,Lp]×[0,hh] 内裁
                    pts = []
                    for v in (0.0, hh):
                        u = c + (v if sign > 0 else hh - v)
                        pts.append((u, v))
                    (ua, va), (ub, vb) = pts
                    # 裁到 u∈[0,Lp]
                    def clip(ua, va, ub, vb):
                        if ua < 0:
                            t = (0 - ua) / (ub - ua)
                            ua, va = 0.0, va + t * (vb - va)
                        if ub > Lp:
                            t = (Lp - ua) / (ub - ua)
                            ub, vb = Lp, va + t * (vb - va)
                        return ua, va, ub, vb
                    if ub < ua:
                        ua, va, ub, vb = ub, vb, ua, va
                    if ub > 0 and ua < Lp:
                        ua, va, ub, vb = clip(ua, va, ub, vb)
                        if ub - ua > 0.05:
                            out.append(frame_box(P(sa + ua, yb0 + va), P(sa + ub, yb0 + vb), 0.06, 0.06, 'Lacquer'))
                    c += pitch
        else:               # 卧棂
            for v in (0.16, 0.32):
                out.append(frame_box(P(sa, yb0 + v), P(sb, yb0 + v), 0.06, 0.06, 'Lacquer'))
            for u in (Lp / 3, 2 * Lp / 3):
                out.append(frame_box(P(sa + u, yb0), P(sa + u, yb1), 0.06, 0.06, 'Lacquer', up=(e[0], 0, e[1])))
    return out


# ================================================================== 主体
def _parts(lod=0):
    D = lod == 0
    parts = []

    def add(name, u):
        if isinstance(u, (list, tuple)):
            for x in u:
                parts.append((name, x))
        else:
            parts.append((name, u))

    # ---------------------------------------------------------- 台基
    add('platform', box((PX0, 0, PZ0), (PX1, PY, PZ1), 'Stone'))
    if D:
        # 台帽（压阑石，挑出 0.3；崖口那面不挑）、台脚、腰带、壁柱（间距约 3 m）
        add('platform', box((PX0 - 0.3, PY - 0.45, PZ0 - 0.3), (PX1, PY, PZ1 + 0.3), 'Stone'))
        add('platform', box((PX0 - 0.35, 0, PZ0 - 0.35), (PX1, 0.4, PZ1 + 0.35), 'Stone'))
        faces = [('f', PX0, PX1), ('b', PX0, PX1), ('l', PZ0, PZ1)]
        for f, a, b in faces:
            n = int(round((b - a) / 3.0))
            for i in range(n + 1):
                t = a + (b - a) * i / n
                w = 0.9 if i in (0, n) else 0.65
                if f == 'f' and SX0 - 0.5 < t < SX1 + 0.5:
                    continue
                if f in ('f', 'b') and i == n:
                    continue          # x = −8 那一角是崖口，不出壁柱
                if f == 'f':
                    add('platform', box((t - w / 2 if i else t, 0.4, PZ0 - 0.25), (t + w / 2, PY - 0.45, PZ0), 'Stone'))
                elif f == 'b':
                    add('platform', box((t - w / 2 if i else t, 0.4, PZ1), (t + w / 2, PY - 0.45, PZ1 + 0.25), 'Stone'))
                else:
                    add('platform', box((PX0 - 0.25, 0.4, max(PZ0, t - w / 2)), (PX0, PY - 0.45, min(PZ1, t + w / 2)), 'Stone'))
            if f == 'f':      # 隔一格加浅浮石板（上下两块，被腰带隔开），不做花纹
                for i in range(0, n, 2):
                    ta, tb = a + (b - a) * i / n, a + (b - a) * (i + 1) / n
                    if tb > SX0 - 0.5 and ta < SX1 + 0.5:
                        continue
                    xa_, xb_ = ta + 0.55 + (0.12 if i == 0 else 0.0), tb - 0.55
                    for y0_, y1_ in ((0.75, 2.6), (3.5, PY - 0.75)):
                        add('platform', box((xa_, y0_, PZ0 - 0.07), (xb_, y1_, PZ0), 'Stone'))
        # 横带
        add('platform', box((PX0, 2.9, PZ0 - 0.12), (SX0, 3.2, PZ0), 'Stone'))
        add('platform', box((SX1, 2.9, PZ0 - 0.12), (PX1, 3.2, PZ0), 'Stone'))
        add('platform', box((PX0, 2.9, PZ1), (PX1, 3.2, PZ1 + 0.12), 'Stone'))
        add('platform', box((PX0 - 0.12, 2.9, PZ0), (PX0, 3.2, PZ1), 'Stone'))
    # 阶（左墄）：30 级 × 0.2 m，踏面 0.3 m；两侧垂带
    nst = 30
    tread = (SZ1 - SZ0) / nst
    cw = 0.6
    if D:
        for k in range(nst):
            add('stair', box((SX0 + cw, 0, SZ0 + k * tread), (SX1 - cw, (k + 1) * PY / nst, SZ1), 'StoneWet'))
    else:
        add('stair', extrude([(SZ0, 0), (SZ1, 0), (SZ1, PY)], (0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), SX0 + cw, SX1 - cw, 'StoneWet'))   # 终审 #4：湿的台阶（门的线光源在上面反光）
    for xa in (SX0, SX1 - cw):
        add('stair', extrude([(SZ0, 0), (SZ1, 0), (SZ1, PY + 0.35), (SZ0, 0.35)], (0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0),
                             xa, xa + cw, 'Stone'))

    # ---------------------------------------------------------- 钩阑（台边内收 0.15）
    if D:
        e = 0.15
        yb = PY
        segs = [((PX0 + e, PZ0 + e), (SX0 - 0.1, PZ0 + e), False),
                ((SX1 + 0.1, PZ0 + e), (PX1 - e, PZ0 + e), False),
                ((PX0 + e, PZ0 + e), (PX0 + e, PZ1 - e), False),
                ((PX0 + e, PZ1 - e), (PX1 - e, PZ1 - e), False),
                ((PX1 - e, PZ0 + e), (PX1 - e, ZF - 0.05), True),       # 崖口那面：矮
                ((PX1 - e, ZB + 0.05), (PX1 - e, PZ1 - e), True)]
        for a, b, low in segs:
            add('goulan', balustrade(a, b, yb, 0.55 if low else 1.1, low, D))

    # ---------------------------------------------------------- 殿身
    core_top = lo_under(X0, ZF + 5) + 0.06
    zc0 = ZF + WALL_T
    cav_x0, cav_x1, cav_z1, cav_y1 = DOOR_X - 3.0, DOOR_X + 3.0, ZF + 6.0, PY + DOOR_H + 1.0
    add('body', box((X0, PY, zc0), (cav_x0, core_top, ZB), 'StoneDark'))
    add('body', box((cav_x1, PY, zc0), (X1, core_top, ZB), 'StoneDark'))
    add('body', box((cav_x0, PY, cav_z1), (cav_x1, core_top, ZB), 'StoneDark'))
    add('body', box((cav_x0, cav_y1, zc0), (cav_x1, core_top, cav_z1), 'Wood'))
    # 前墙：下段按开间留窗 / 门洞，上段一整块，顶边贴腰檐底
    dx0, dx1 = DOOR_X - DOOR_W / 2, DOOR_X + DOOR_W / 2
    ylow = PY + DOOR_H
    wy0, wy1, ww = PY + 3.2, PY + 6.6, 3.6
    door_bay = int((DOOR_X - X0) // BAY)
    for i in range(BAYS):
        xa, xb = X0 + i * BAY, X0 + (i + 1) * BAY
        if i == door_bay:
            add('wall', box((xa, PY, ZF), (dx0, ylow, zc0), 'StoneDark'))
            add('wall', box((dx1, PY, ZF), (xb, ylow, zc0), 'StoneDark'))
            continue
        cx = (xa + xb) / 2
        w0, w1 = cx - ww / 2, cx + ww / 2
        add('wall', box((xa, PY, ZF), (xb, wy0, zc0), 'StoneDark'))
        add('wall', box((xa, wy0, ZF), (w0, wy1, zc0), 'StoneDark'))
        add('wall', box((w1, wy0, ZF), (xb, wy1, zc0), 'StoneDark'))
        add('wall', box((xa, wy1, ZF), (xb, ylow, zc0), 'StoneDark'))
        # 直棂窗：窗后封闭暗板（Wood），窗格 LacquerBlack，朱漆窗框
        add('window', box((w0, wy0, ZF + 0.45), (w1, wy1, zc0 + 0.02), 'Wood'))
        if D:
            fw = 0.22
            add('window', box((w0 - fw, wy0 - fw, ZF - 0.12), (w1 + fw, wy0, ZF + 0.05), 'Lacquer'))
            add('window', box((w0 - fw, wy1, ZF - 0.12), (w1 + fw, wy1 + fw, ZF + 0.05), 'Lacquer'))
            add('window', box((w0 - fw, wy0, ZF - 0.12), (w0, wy1, ZF + 0.05), 'Lacquer'))
            add('window', box((w1, wy0, ZF - 0.12), (w1 + fw, wy1, ZF + 0.05), 'Lacquer'))
            nb = 13
            for k in range(nb):
                bx = w0 + ww * (k + 0.5) / nb
                add('window', frame_box((bx, wy0, ZF + 0.12), (bx, wy1, ZF + 0.12), 0.13, 0.13, 'LacquerBlack', up=(0, 0, 1)))
            add('window', box((w0, (wy0 + wy1) / 2 - 0.08, ZF + 0.02), (w1, (wy0 + wy1) / 2 + 0.08, ZF + 0.22), 'LacquerBlack'))
        else:
            add('window', box((w0, wy0, ZF + 0.1), (w1, wy1, ZF + 0.2), 'LacquerBlack'))
    xb0 = LO_RECT[0] + (ZF - LO_RECT[2])
    xb1 = LO_RECT[1] - (ZF - LO_RECT[2])
    yt = lo_under(X0 + 30, ZF) + 0.1
    ye = lo_under(X0, ZF) + 0.06
    add('wall', extrude([(X0, ylow), (X1, ylow), (X1, ye), (xb1, yt), (xb0, yt), (X0, ye)],
                        (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), ZF, zc0, 'StoneDark'))
    if D:
        # 壁柱（朱）+ 墙裙（黑）+ 墙头枋带
        posts = [(X0 + i * BAY, 'f') for i in range(BAYS + 1)] + [(X0 + i * BAY, 'b') for i in range(BAYS + 1)]
        for x, f in posts:
            if f == 'f':
                add('wall', box((x - 0.35, PY, ZF - 0.2), (x + 0.35, PY + 10.6, ZF), 'Lacquer'))
            else:
                add('wall', box((x - 0.35, PY, ZB), (x + 0.35, PY + 10.6, ZB + 0.2), 'Lacquer'))
        for k in range(5):
            z = ZF + k * DEPTH / 4
            add('wall', box((X0 - 0.2, PY, z - 0.35 if k else z), (X0, PY + 10.6, z + 0.35 if k < 4 else z), 'Lacquer'))
            add('wall', box((X1, PY, z - 0.35 if k else z), (X1 + 0.2, PY + 10.6, z + 0.35 if k < 4 else z), 'Lacquer'))
        dado = PY + 0.55
        add('wall', box((X0, PY, ZF - 0.08), (dx0 - 0.4, dado, ZF), 'LacquerBlack'))
        add('wall', box((dx1 + 0.4, PY, ZF - 0.08), (X1, dado, ZF), 'LacquerBlack'))
        add('wall', box((X0, PY, ZB), (X1, dado, ZB + 0.08), 'LacquerBlack'))
        add('wall', box((X0 - 0.08, PY, ZF), (X0, dado, ZB), 'LacquerBlack'))
        add('wall', box((X1, PY, ZF), (X1 + 0.08, dado, ZB), 'LacquerBlack'))
    yb0, yb1 = PY + 10.6, PY + 11.6
    add('wall', beam_x(X0 - 0.3, X1 + 0.3, yb0, yb1, ZF - 0.3, ZF + 0.1))
    add('wall', beam_x(X0 - 0.3, X1 + 0.3, yb0, yb1, ZB - 0.1, ZB + 0.3))
    add('wall', beam_z(ZF - 0.3, ZB + 0.3, yb0, yb1, X0 - 0.3, X0 + 0.1))
    add('wall', beam_z(ZF - 0.3, ZB + 0.3, yb0, yb1, X1 - 0.1, X1 + 0.3))

    # ---------------------------------------------------------- 门
    fr = 0.35
    add('door', box((dx0 - fr, PY, ZF - 0.15), (dx0, ylow, ZF + 0.1), 'LacquerBlack'))
    add('door', box((dx1, PY, ZF - 0.15), (dx1 + fr, ylow, ZF + 0.1), 'LacquerBlack'))
    add('door', box((dx0 - fr, ylow, ZF - 0.15), (dx1 + fr, ylow + 0.5, ZF + 0.1), 'LacquerBlack'))
    add('door', box((dx0, PY, ZF - 0.1), (dx1, PY + 0.22, ZF + 0.25), 'LacquerBlack'))      # 门槛（低）
    lw, lt, hz = DOOR_W / 2, 0.16, ZF + 0.42
    th = math.radians(70.0)
    c, s = math.cos(th), math.sin(th)
    for side in ('L', 'R'):
        leaf = UB()
        leaf.box((0, 0, -lt / 2), (lw - 0.02, DOOR_H - 0.03, lt / 2), 'Wood', skip=('-z',))
        leaf.quad((0, 0, -lt / 2), (0, DOOR_H - 0.03, -lt / 2), (lw - 0.02, DOOR_H - 0.03, -lt / 2), (lw - 0.02, 0, -lt / 2), 'Lacquer')
        lp = [('door', solid(leaf))]
        if D:
            # 两道朱漆横带（门板加固的“楅”）
            for yy in (1.4, 5.6):
                lp.append(('door', box((0.05, yy, -lt / 2 - 0.05), (lw - 0.07, yy + 0.3, -lt / 2 + 0.01), 'Lacquer')))
            # 铺首衔环：圆座 + 鎏金圆环（无兽面）
            ux, uy = lw - 0.55, 3.75
            Mz = np.array([[1, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])     # lathe 的 y 轴 → 门面外法线 −z
            base = lathe_solid([(0.2, 0.0), (0.2, 0.05), (0.12, 0.1)], 12, 'Gilt', (0, 0, 0))
            lp.append(('door', solid(base.transformed(Mz, (ux, uy, -lt / 2 + 0.005)))))
            lp.append(('door', torus(0.27, 0.045, 16, 6, 'Gilt', np.eye(3), (ux, uy - 0.28, -lt / 2 - 0.08))))
        if side == 'L':
            M = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])
            t = (dx0, PY, hz)
        else:
            M = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]) @ np.diag([-1.0, 1, 1])
            t = (dx1, PY, hz)
        for nm, u in lp:
            add(nm, solid(u.transformed(M, t)))
    # 门里的暖光（第 4 轮，美术评审 r3 阻断 1）：整个门后暗腔的内衬都发光（背面、两侧、顶、地），朝里；
    # 门扇在它前面读成暗剪影，从任何角度看门洞里都是光，看不见实体墙。UV0.y = (y − 台基面) / 门高（shader 的竖向渐变）。
    lx0, lx1 = -21.0 + 0.02, -15.0 - 0.02
    ly0, ly1 = PY + 0.02, PY + 8.5 - 0.02
    lz0, lz1 = ZF + WALL_T + 0.02, 348.6 - 0.02
    g = UB()
    V = [(lx0, ly0, lz0), (lx1, ly0, lz0), (lx1, ly1, lz0), (lx0, ly1, lz0), (lx0, ly0, lz1), (lx1, ly0, lz1), (lx1, ly1, lz1), (lx0, ly1, lz1)]
    faces = [(4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (1, 5, 6, 2), (0, 3, 7, 4)]   # 朝里：后、地、顶、右、左（前面是门洞，不封）
    for f in faces:
        P = [V[i] for i in f]
        uv = [((p[0] + p[2]) / 4.0, (p[1] - PY) / DOOR_H) for p in P]
        g.add(P, [(0, 1, 2, 3)], 'DoorGlow', [uv])
    add('doorglow', g)

    # ---------------------------------------------------------- 前檐柱廊
    xs = [X0 + i * BAY for i in range(BAYS + 1)]
    xs[0] += COL_INSET
    xs[-1] -= COL_INSET
    # 终审 10-25 #4：明间（门那一间）加宽到 11.5 m——从车里 −40° 斜看时门不再被门廊自己的两根柱子挡成 1° 的缝
    db = int((DOOR_X - X0) // BAY)
    xs[db], xs[db + 1] = DOOR_X - MINGJIAN / 2, DOOR_X + MINGJIAN / 2
    ye0, ye1 = COL_TOP - 0.8, COL_TOP
    for i, x in enumerate(xs):
        if D:
            add('column', box((x - 0.85, PY, COL_Z - 0.85), (x + 0.85, PY + 0.2, COL_Z + 0.85), 'Stone'))
            add('column', lathe_solid([(0.8, 0.0), (0.78, 0.1), (0.72, 0.2), (0.62, 0.28), (0.57, 0.32)], 16, 'Stone', (x, PY + 0.2, COL_Z)))
            add('column', octa(COL_FLAT0 + 0.08, COL_FLAT0 + 0.08, PY + 0.5, PY + 0.72, 'Gilt', x, COL_Z))
            add('column', octa(COL_FLAT1 + 0.08, COL_FLAT1 + 0.08, ye0 - 0.45, ye0 - 0.2, 'Gilt', x, COL_Z))
        add('column', octa(COL_FLAT0, COL_FLAT1, PY + (0.45 if D else 0.0), COL_TOP, 'Lacquer', x, COL_Z))
        kind = 'qu' if i in (0, len(xs) - 1) else (3 if i % 2 else 2)
        if D:
            bp, ytop = bracket(x, COL_Z, COL_TOP, 1.0, kind, projecting=2.4)
            add('dougong', bp)
        else:
            add('dougong', box((x - 0.7, COL_TOP, COL_Z - 0.7), (x + 0.7, COL_TOP + 0.85, COL_Z + 0.7), 'Lacquer'))
            add('dougong', box((x - 1.8, COL_TOP + 0.85, COL_Z - 0.3), (x + 1.8, COL_TOP + 1.75, COL_Z + 0.3), 'LacquerBlack'))
        # 穿插枋：柱头连到墙
        add('beam', box((x - 0.22, ye0 + 0.1, COL_Z), (x + 0.22, ye1 - 0.05, ZF), 'Lacquer'))
    yg = COL_TOP + 0.85 + 0.45 + 0.45      # 升顶
    add('beam', beam_x(xs[0] - 0.6, xs[-1] + 0.6, ye0, ye1, COL_Z - 0.25, COL_Z + 0.25))           # 额枋
    add('beam', beam_x(xs[0] - 2.0, xs[-1] + 2.0, yg, yg + 1.15, COL_Z - 0.3, COL_Z + 0.3))         # 檐枋
    add('beam', box((xs[0] - 2.0, yg + 1.15, COL_Z - 0.25), (xs[-1] + 2.0, yg + 1.8, COL_Z + 0.25), 'LacquerBlack'))  # 替木
    if D:
        add('beam', beam_x(xs[0] - 1.6, xs[-1] + 1.6, COL_TOP + 1.3, COL_TOP + 2.3, COL_Z - 2.4 + 0.1, COL_Z - 2.4 + 0.6, 'Lacquer'))  # 撩檐枋

    # ---------------------------------------------------------- 腰檐（下檐）
    add('roof', roof_slab(LO_RECT, LO_TIP, LO_BRK, LO_DTOP, True))
    add('ridge', hip_ridges(LO_RECT, LO_TIP, LO_BRK, LO_DTOP, 0.6, 0.55))
    if D:
        roof_tiles(LO_RECT, LO_TIP, LO_BRK, LO_DTOP, parts)
        rafters(LO_RECT, LO_TIP, LO_BRK, 4.6, parts)
    else:
        roof_tiles(LO_RECT, LO_TIP, LO_BRK, LO_DTOP, parts, rows=False, nd=6)

    # ---------------------------------------------------------- 上层殿身（重檐之间）
    bx0, bx1, bz0, bz1 = UP_BODY
    up_under = roof_h(UP_OUT, UP_TIP, UP_BRK) - ROOF_T
    add('upper', box((bx0, LO_TOPY - 0.6, bz0), (bx1, up_under + 0.08, bz1), 'StoneDark'))
    # 围脊（腰檐上缘那一圈）
    add('ridge', box((bx0 - 0.45, LO_TOPY - 0.3, bz0 - 0.45), (bx1 + 0.45, LO_TOPY + 0.55, bz1 + 0.45), 'Tile'))
    band0, band1 = up_under - 2.3, up_under - 1.5
    add('upper', beam_x(bx0 - 0.3, bx1 + 0.3, band0, band1, bz0 - 0.3, bz0 + 0.1))
    add('upper', beam_x(bx0 - 0.3, bx1 + 0.3, band0, band1, bz1 - 0.1, bz1 + 0.3))
    add('upper', beam_z(bz0 - 0.3, bz1 + 0.3, band0, band1, bx0 - 0.3, bx0 + 0.1))
    add('upper', beam_z(bz0 - 0.3, bz1 + 0.3, band0, band1, bx1 - 0.1, bx1 + 0.3))
    if D:
        upx = [bx0] + [x for x in [X0 + i * BAY for i in range(1, BAYS)] if bx0 + 1 < x < bx1 - 1] + [bx1]
        nz = 4
        upz = [bz0 + (bz1 - bz0) * k / nz for k in range(nz + 1)]
        for x in upx:
            for zf, sgn in ((bz0, -1), (bz1, 1)):
                add('upper', box((x - 0.35, LO_TOPY, min(zf, zf + 0.25 * sgn)), (x + 0.35, band0, max(zf, zf + 0.25 * sgn)), 'Lacquer'))
                bp, _ = bracket(x, zf + 0.55 * sgn, band1, 0.55, 2)
                add('dougong', bp)
        for z in upz[1:-1]:
            for xf, sgn in ((bx0, -1), (bx1, 1)):
                add('upper', box((min(xf, xf + 0.25 * sgn), LO_TOPY, z - 0.35), (max(xf, xf + 0.25 * sgn), band0, z + 0.35), 'Lacquer'))
                bp, _ = bracket(xf + 0.55 * sgn, z, band1, 0.55, 2, along_z=True)
                add('dougong', bp)
        # 前面一排小直棂窗（高窗，后面是实墙）
        for a, b in zip(upx[:-1], upx[1:]):
            cx = (a + b) / 2
            w = min(2.8, (b - a) - 1.6)
            y0, y1 = LO_TOPY + 1.4, LO_TOPY + 2.8
            add('upper', box((cx - w / 2 - 0.18, y0 - 0.18, bz0 - 0.14), (cx + w / 2 + 0.18, y1 + 0.18, bz0), 'Lacquer'))
            add('upper', box((cx - w / 2, y0, bz0 - 0.2), (cx + w / 2, y1, bz0 - 0.14), 'Wood'))
            nb = 9
            for k in range(nb):
                bxk = cx - w / 2 + w * (k + 0.5) / nb
                add('upper', box((bxk - 0.06, y0, bz0 - 0.3), (bxk + 0.06, y1, bz0 - 0.18), 'LacquerBlack'))

    # ---------------------------------------------------------- 上檐
    add('roof', roof_slab(UP_RECT, UP_TIP, UP_BRK, UP_DTOP, False))
    add('ridge', hip_ridges(UP_RECT, UP_TIP, UP_BRK, UP_DTOP, 0.75, 0.75))
    add('ridge', main_ridge(lod))
    if D:
        roof_tiles(UP_RECT, UP_TIP, UP_BRK, UP_DTOP, parts)
        rafters(UP_RECT, UP_TIP, UP_BRK, UP_OUT + 0.1, parts)
    else:
        roof_tiles(UP_RECT, UP_TIP, UP_BRK, UP_DTOP, parts, rows=False, nd=6)
    return parts


def build(lod=0):
    ub = UB()
    for _, u in _parts(lod):
        ub.merge(u)
    return ub


# ================================================================== 自检
def check(lod=0, verbose=True):
    """逐件：每条边恰好两个面、方向相反（封闭流形），体积 > 0（法线朝外）。"""
    bad = []
    for name, u in _parts(lod):
        V = np.round(np.asarray(u.V, float), 4)
        key = {}
        ids = [key.setdefault(tuple(v), len(key)) for v in V]
        E = {}
        for f in u.F:
            g = [ids[i] for i in f]
            for i in range(len(g)):
                a, b = g[i], g[(i + 1) % len(g)]
                E[(a, b)] = E.get((a, b), 0) + 1
        ok = all(E.get((b, a), 0) == n for (a, b), n in E.items()) and all(n == 1 for n in E.values())
        vol = volume(u)
        if not ok or vol <= 0:
            bad.append((name, ok, vol))
    if verbose:
        print('check lod%d: %d parts bad' % (lod, len(bad)), bad[:10])
    return bad


def stats(lod=0):
    from collections import Counter
    c = Counter()
    for name, u in _parts(lod):
        c[name] += u.tris()
    return c


if __name__ == '__main__':
    for l in (0, 1):
        print('LOD%d tris' % l, build(l).tris(), dict(stats(l)))
        check(l)
    print('LO_TIP %.2f LO_DTOP %.2f UP_BODY %s UP_RECT %s UP_TIP %.2f' % (LO_TIP, LO_DTOP, UP_BODY, UP_RECT, UP_TIP))
