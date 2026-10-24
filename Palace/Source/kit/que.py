# -*- coding: utf-8 -*-
"""紫贝阙：一对单阙（不做子阙），宫殿坐标（绝对）。

    build(lod=0) -> UB

形制（research_han.md §1、§4–6，高颐阙 / 冯焕阙的分段，按 40 m 放大）：
    阙基   y 0–3      石，比阙身各边宽 0.8 m；壁柱 + 凹板 + 压顶石
    阙身   y 3–22     紫贝贴面（Cowrie），每侧收 0.4 m；石的角倚柱、中倚柱（长面）、横枋带；
                      下段（3.6–8.3，近景）每块贴面有一道石的压边框
    阙楼   y 22–29.7  枋头层（两排出挑枋头，朱漆）+ 斗拱层（四角一斗二升、长面正中曲栱）；
                      三道 LacquerBand 枋（A、B、C），C 比阙身宽 1.8 m
    阙顶   y 29.7–40  重檐四阿：腰檐（出 2.7 m）+ 上层阙楼 + 上檐（出 2.0 m，自阙身顶算 ~2.1 / 3 m），
                      直坡，筒瓦垄 + 瓦当，转角不起翘；正脊两端起翘 + 克制的鱼尾
坐标：Unity 轴（x 右、y 上、z 前），两阙中心 (−12, 0, 41.39)、(−24, 0, 41.39)，阙身 6 (x) × 10 (z)。
本文件里还有几个小几何工具（prism / extrude / sweep2d / ...），house.py 也用它们。
每个部件都是封闭实体；_emit 按有符号体积统一翻正绕向，KB.parts 记录每个部件的面范围（给法线测试用）。
"""
import math

import numpy as np

try:
    from .common import UB, TILE, auto_uv
except ImportError:          # 直接当脚本 import
    from common import UB, TILE, auto_uv

RIDGE_LIFT = 1.05
QUE_POS = [(-12.0, 0.0, 41.39), (-24.0, 0.0, 41.39)]


# ===================================================================== 几何工具
class KB(UB):
    """UB + 部件表（每个封闭部件的面范围），只用于测试；对 Unity / Blender 没有影响。"""

    def __init__(self):
        super().__init__()
        self.parts = []

    def shifted(self, t):
        u = KB()
        u.V = [tuple(np.asarray(v) + np.asarray(t, float)) for v in self.V]
        u.F, u.S, u.UV, u.parts = list(self.F), list(self.S), list(self.UV), list(self.parts)
        return u

    def merge(self, other):
        n = len(self.F)
        super().merge(other)
        for a, b in getattr(other, 'parts', []):
            self.parts.append((a + n, b + n))


def signed_volume(V, F):
    V = np.asarray(V, float)
    s = 0.0
    for f in F:
        a = V[f[0]]
        for i in range(1, len(f) - 1):
            s += np.dot(a, np.cross(V[f[i]], V[f[i + 1]]))
    return s / 6.0


def _emit(ub, V, F, slots, UV=None):
    """加一个封闭实体：V (n,3)，F 面（彼此绕向一致即可，整体方向按体积自动翻正），
    slots = 一个槽名或每个面一个；UV = None 或每个面一组（None 的面自动投影）。"""
    V = np.asarray(V, float)
    F = [tuple(f) for f in F]
    if isinstance(slots, str):
        slots = [slots] * len(F)
    UV = list(UV) if UV is not None else [None] * len(F)
    if signed_volume(V, F) < 0:
        F = [tuple(reversed(f)) for f in F]
        UV = [list(reversed(u)) if u is not None else None for u in UV]
    f0 = len(ub.F)
    for slot in dict.fromkeys(slots):
        idx = [k for k in range(len(F)) if slots[k] == slot]
        used = sorted({i for k in idx for i in F[k]})
        remap = {o: n for n, o in enumerate(used)}
        Fs = [tuple(remap[i] for i in F[k]) for k in idx]
        UVs = [UV[k] if UV[k] is not None else auto_uv(V[list(F[k])], TILE[slot]) for k in idx]
        ub.add(V[used], Fs, slot, UVs)
    if hasattr(ub, 'parts'):
        ub.parts.append((f0, len(ub.F)))


BOX_F = {'-z': (0, 3, 2, 1), '+z': (4, 5, 6, 7), '-y': (0, 1, 5, 4), '+y': (2, 3, 7, 6), '+x': (1, 2, 6, 5), '-x': (0, 4, 7, 3)}


def prism(ub, b, t, slot, faces=None, uvfun=None):
    """六面体：底 b = (x0, x1, z0, z1, y0)，顶 t = (x0, x1, z0, z1, y1)（可收分 / 错位）。
    faces: {面名: 槽} 覆盖个别面的槽；uvfun(面名, 顶点) -> UV 或 None。"""
    bx0, bx1, bz0, bz1, y0 = b
    tx0, tx1, tz0, tz1, y1 = t
    V = [(bx0, y0, bz0), (bx1, y0, bz0), (tx1, y1, tz0), (tx0, y1, tz0),
         (bx0, y0, bz1), (bx1, y0, bz1), (tx1, y1, tz1), (tx0, y1, tz1)]
    F, S, UV = [], [], []
    for k, f in BOX_F.items():
        F.append(f)
        S.append((faces or {}).get(k, slot))
        UV.append(uvfun(k, [V[i] for i in f]) if uvfun else None)
    _emit(ub, V, F, S, UV)


def box(ub, lo, hi, slot, faces=None, uvfun=None):
    prism(ub, (lo[0], hi[0], lo[2], hi[2], lo[1]), (lo[0], hi[0], lo[2], hi[2], hi[1]), slot, faces, uvfun)


def band_uv(y0, y1):
    """LacquerBand：侧面 u = 沿梁米 / 4（从外面看向右增大），v = 截面 0..1；顶、底面自动。"""
    def f(k, P):
        if k in ('+y', '-y'):
            return None
        out = []
        for x, y, z in P:
            u = {'-z': x, '+z': -x, '+x': z, '-x': -z}[k]
            out.append((u / 4.0, (y - y0) / (y1 - y0)))
        return out
    return f


def course(ub, X, Z, y0, y1, cx=0.0, cz=0.0):
    """一圈枋（实心块）：侧面 LacquerBand，顶 / 底 Lacquer。"""
    box(ub, (cx - X, y0, cz - Z), (cx + X, y1, cz + Z), 'LacquerBand', {'+y': 'Lacquer', '-y': 'Lacquer'}, band_uv(y0, y1))


def beam_x(ub, x0, x1, y0, y1, z0, z1):
    """沿 x 的梁（LacquerBand 侧面 + 朱漆端头 / 顶底）。"""
    def f(k, P):
        if k in ('-z', '+z'):
            return [((x if k == '-z' else -x) / 4.0, (y - y0) / (y1 - y0)) for x, y, z in P]
        return None
    box(ub, (x0, y0, z0), (x1, y1, z1), 'Lacquer', {'-z': 'LacquerBand', '+z': 'LacquerBand'}, f)


def beam_z(ub, z0, z1, y0, y1, x0, x1):
    def f(k, P):
        if k in ('-x', '+x'):
            return [((z if k == '+x' else -z) / 4.0, (y - y0) / (y1 - y0)) for x, y, z in P]
        return None
    box(ub, (x0, y0, z0), (x1, y1, z1), 'Lacquer', {'-x': 'LacquerBand', '+x': 'LacquerBand'}, f)


def _basis(d, up):
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    up = np.asarray(up, float)
    side = np.cross(up, d)
    if np.linalg.norm(side) < 1e-6:
        side = np.cross((1.0, 0, 0), d)
    side /= np.linalg.norm(side)
    upv = np.cross(d, side)
    return d, side, upv


def extrude(ub, p0, p1, up, sec, slot, slot_caps=None):
    """把截面 sec [(s, u), ...]（s 沿 side，u 沿 up，凸多边形或星形）从 p0 拉到 p1，两端封口。"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d, side, upv = _basis(p1 - p0, up)
    n = len(sec)
    V = [p + s * side + u * upv for p in (p0, p1) for (s, u) in sec]
    F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    F += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    S = [slot] * n + [slot_caps or slot] * 2
    _emit(ub, V, F, S)


def ngon_prism(ub, cx, cz, r0, r1, y0, y1, n, slot, a0=None, caps_slot=None):
    """竖直 n 棱柱 / 棱台（外接半径 r0 底、r1 顶）。"""
    a0 = math.pi / n if a0 is None else a0
    V = []
    for r, y in ((r0, y0), (r1, y1)):
        for i in range(n):
            a = a0 + 2 * math.pi * i / n
            V.append((cx + r * math.cos(a), y, cz + r * math.sin(a)))
    F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    F += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    _emit(ub, V, F, [slot] * n + [caps_slot or slot] * 2)


def sweep2d(ub, P, Q, origin, au, av, an, d0, d1, slot, faces=None):
    """平面轮廓带：一串站点 (P_i 下沿, Q_i 上沿)，P/Q 是 (u, v) 二维点，
    3D = origin + u·au + v·av + w·an，w ∈ [d0, d1]（厚度方向）。faces: {'front','back','strip','caps'} 覆盖槽。"""
    o, au, av, an = (np.asarray(x, float) for x in (origin, au, av, an))
    m = len(P)
    V = []
    for w in (d1, d0):                # 0..m−1 P 前，m..2m−1 Q 前，2m.. P 后，3m.. Q 后
        for pts in (P, Q):
            for (u, v) in pts:
                V.append(o + u * au + v * av + w * an)
    Pf, Qf, Pb, Qb = (lambda i: i), (lambda i: m + i), (lambda i: 2 * m + i), (lambda i: 3 * m + i)
    F, S = [], []
    fs = faces or {}
    for i in range(m - 1):
        F.append((Pf(i), Pf(i + 1), Qf(i + 1), Qf(i))); S.append(fs.get('front', slot))
        F.append((Pb(i), Qb(i), Qb(i + 1), Pb(i + 1))); S.append(fs.get('back', slot))
        F.append((Pb(i), Pb(i + 1), Pf(i + 1), Pf(i))); S.append(fs.get('strip', slot))
        F.append((Qf(i), Qf(i + 1), Qb(i + 1), Qb(i))); S.append(fs.get('strip', slot))
    F.append((Pb(0), Pf(0), Qf(0), Qb(0))); S.append(fs.get('caps', slot))
    F.append((Pf(m - 1), Pb(m - 1), Qb(m - 1), Qf(m - 1))); S.append(fs.get('caps', slot))
    _emit(ub, V, F, S)


def ridge(ub, c, axis, half, yb, h, thick, lift, slot='Tile', n_end=6):
    """正脊：沿 axis（'x' 或 'z'）长 2·half，底 yb、高 h、厚 thick；两端只起翘 + 克制的鱼尾
    （端头沿一段圆弧向上弯约 70°，上沿内凹，尖向里收），lift ≈ 端头比脊顶高出的量。"""
    au = np.array([1.0, 0, 0]) if axis == 'x' else np.array([0, 0, 1.0])
    an = np.array([0, 0, 1.0]) if axis == 'x' else np.array([1.0, 0, 0])
    av = np.array([0, 1.0, 0])
    yc = yb + h / 2
    R = max(lift * 1.05, h * 0.75)
    u0 = half - R * 0.55                        # 弧从这里开始
    P, Q = [], []
    if n_end:
        # 左端（反向）、中段、右端：先算右半边，再镜像
        right = []
        right.append(((0.0, yb), (0.0, yb + h)))
        right.append(((u0, yb), (u0, yb + h)))
        phimax = math.radians(62)
        for k in range(1, n_end + 1):
            ph = phimax * k / n_end
            cu, cv = u0 + R * math.sin(ph), yc + R * (1 - math.cos(ph))
            nu, nv = -math.sin(ph), math.cos(ph)
            hw = h / 2 * (1 - 0.45 * (k / n_end) ** 1.5)
            # 上沿（Q，内侧）比下沿（P，外侧）收得快 → 上沿内凹，尖向里勾
            right.append(((cu - nu * hw, cv - nv * hw), (cu + nu * hw * 0.8, cv + nv * hw * 0.8)))
        # 尖：外沿再顺切线伸出一点
        ph = phimax
        tu, tv = math.cos(ph), math.sin(ph)
        pu, pv = right[-1][0]
        qu, qv = right[-1][1]
        right.append(((pu + tu * h * 0.3, pv + tv * h * 0.3), (qu + tu * h * 0.1, qv + tv * h * 0.1)))
        left = [((-p[0], p[1]), (-q[0], q[1])) for p, q in reversed(right[1:])]
        st = left + right
    else:
        st = [((-half, yb), (-half, yb + h)), ((half, yb), (half, yb + h))]
    P = [s[0] for s in st]
    Q = [s[1] for s in st]
    sweep2d(ub, P, Q, c, au, av, an, -thick / 2, thick / 2, slot)


# ===================================================================== 屋顶
def hip_solid(ub, cx, cz, X, Z, ys, fascia, slope_deg, inner=None, top='Tile', fas='Tile', soffit='Wood'):
    """四阿顶（或腰檐 = 截头四阿）的封闭实体。檐口矩形半宽 X、Z，底面（檐下）ys，檐口厚 fascia，直坡。
    inner=(Xi, Zi)：截头（平顶在内矩形），要求 X−Xi == Z−Zi（45° 戗）。
    返回每个坡面的信息（给瓦垄 / 鳞片 / 垂脊用）。"""
    tn = math.tan(math.radians(slope_deg))
    yf = ys + fascia
    C = [(-X, -Z), (X, -Z), (X, Z), (-X, Z)]
    B = [(cx + x, ys, cz + z) for x, z in C]
    T = [(cx + x, yf, cz + z) for x, z in C]
    if inner:
        Xi, Zi = inner
        yi = yf + (X - Xi) * tn
        R = [(cx + x * Xi / X, yi, cz + z * Zi / Z) for x, z in C]
        Rid = [0, 1, 2, 3]
        y_top = yi
    else:
        if X <= Z:
            yr = yf + X * tn
            E, Fp = (cx, yr, cz - (Z - X)), (cx, yr, cz + (Z - X))
            R, Rid = [E, Fp], [0, 0, 1, 1]
        else:
            yr = yf + Z * tn
            E, Fp = (cx - (X - Z), yr, cz), (cx + (X - Z), yr, cz)
            R, Rid = [E, Fp], [0, 1, 1, 0]
        y_top = yr
    V = B + T + list(R)
    b, t, r = 0, 4, 8
    F, S, UV = [], [], []
    F.append((0, 1, 2, 3)); S.append(soffit); UV.append(None)
    sides = []
    for i in range(4):
        j = (i + 1) % 4
        F.append((b + i, t + i, t + j, b + j)); S.append(fas); UV.append(None)
        ri, rj = r + Rid[i], r + Rid[j]
        f = (t + i, ri, t + j) if ri == rj else (t + i, ri, rj, t + j)
        # 坡面 UV：u 沿檐、v 沿坡向上（米 / TILE）
        Ti, Tj = np.array(V[t + i]), np.array(V[t + j])
        e = (Tj - Ti) / np.linalg.norm(Tj - Ti)
        up = np.array(V[ri]) - Ti
        s = up - e * np.dot(up, e)
        s /= np.linalg.norm(s)
        F.append(f); S.append(top)
        tile = TILE[top]
        UV.append([(np.dot(np.array(V[k]) - Ti, e) / tile, np.dot(np.array(V[k]) - Ti, s) / tile) for k in f])
        nrm = np.cross(e, s)
        if nrm[1] < 0:
            nrm = -nrm
        W = float(np.linalg.norm(Tj - Ti))
        depth = (X - inner[0]) if inner else min(X, Z)
        sides.append(dict(T0=Ti, e=e, s=s, n=nrm, W=W, depth=depth, cos=math.cos(math.radians(slope_deg)),
                          R0=np.array(V[ri]), R1=np.array(V[rj])))
    if inner:
        F.append((r + 3, r + 2, r + 1, r + 0)); S.append(top); UV.append(None)
    _emit(ub, V, F, S, UV)
    return dict(sides=sides, y_top=y_top, yf=yf, R=[np.array(p) for p in R], T=[np.array(p) for p in T])


def tile_rolls(ub, side, pitch, rr, hip=True, dangdang=True, n_sec=3):
    """一个坡面上的筒瓦垄 + 瓦当。hip=True 时两端按 45° 戗截短。"""
    W, depth = side['W'], side['depth']
    e, s, n, T0 = side['e'], side['s'], side['n'], side['T0']
    k = max(1, int(round(W / pitch)))
    step = W / k
    sec = [(rr * math.cos(math.pi * i / n_sec), rr * math.sin(math.pi * i / n_sec)) for i in range(n_sec + 1)]
    sec = [(sec[0][0], -0.04)] + sec[1:-1] + [(sec[-1][0], -0.04)]
    for i in range(k):
        t = step * (i + 0.5)
        plan = min(t, W - t, depth) if hip else depth
        plan -= rr * 0.6 if hip and plan < depth else 0.0
        if plan < 0.35:
            continue
        L = plan / side['cos']
        p0 = T0 + e * t - s * 0.05
        p1 = p0 + s * L
        extrude(ub, p0, p1, n, sec, 'Tile')
        if dangdang:
            c = p0 + n * rr * 0.42
            extrude(ub, c + s * 0.06, c - s * 0.07, n,
                    [(rr * 1.12 * math.cos(2 * math.pi * j / 6 + math.pi / 6), rr * 1.12 * math.sin(2 * math.pi * j / 6 + math.pi / 6)) for j in range(6)],
                    'Tile')


def hip_ridges(ub, roof, w, h, slot='Tile'):
    """四条戗脊（垂脊）：从檐角到脊端 / 内角。"""
    sides = roof['sides']
    for i in range(4):
        a, b_ = sides[i - 1], sides[i]
        up = a['n'] + b_['n']
        p0 = roof['T'][i]
        p1 = b_['R0']
        d = p1 - p0
        L = np.linalg.norm(d)
        p1 = p0 + d * (L - 0.05) / L
        extrude(ub, p0 - d / L * 0.05, p1, up, [(-w / 2, -0.12), (w / 2, -0.12), (w / 2, h), (-w / 2, h)], slot)


# ===================================================================== 阙
def _que_local(lod=0):
    ub = KB()
    hi = lod == 0
    # ---------------- 阙基 y 0–3
    BX, BZ = 3.8, 5.8
    box(ub, (-BX - 0.2, -0.4, -BZ - 0.2), (BX + 0.2, 0.3, BZ + 0.2), 'Stone')                 # 脚石
    if hi:
        box(ub, (-BX + 0.14, 0.3, -BZ + 0.14), (BX - 0.14, 2.55, BZ - 0.14), 'Stone')        # 凹板
        pw = 0.5
        for sx in (-1, 1):                                                                   # 壁柱：长面（±x）
            n = 5
            for i in range(n):
                z = -BZ + pw / 2 + (2 * BZ - pw) * i / (n - 1)
                x0 = sx * BX
                box(ub, (min(x0, x0 - sx * 0.5), 0.3, z - pw / 2), (max(x0, x0 - sx * 0.5), 2.55, z + pw / 2), 'Stone')
        for sz in (-1, 1):                                                                   # 短面（±z）中间两根
            for x in (-BX / 3, BX / 3):
                z0 = sz * BZ
                box(ub, (x - pw / 2, 0.3, min(z0, z0 - sz * 0.5)), (x + pw / 2, 2.55, max(z0, z0 - sz * 0.5)), 'Stone')
        # 板心上的横带（汉画像石台座常见的上下两道）
        box(ub, (-BX + 0.04, 0.3, -BZ + 0.04), (BX - 0.04, 0.55, BZ - 0.04), 'Stone')
        box(ub, (-BX + 0.06, 2.35, -BZ + 0.06), (BX - 0.06, 2.55, BZ - 0.06), 'Stone')
    else:
        box(ub, (-BX, 0.3, -BZ), (BX, 2.55, BZ), 'Stone')
    box(ub, (-BX - 0.1, 2.55, -BZ - 0.1), (BX + 0.1, 2.8, BZ + 0.1), 'Stone')                # 压顶石
    box(ub, (-BX, 2.8, -BZ), (BX, 3.0, BZ), 'Stone')

    # ---------------- 阙身 y 3–22（每侧收 0.4 m）
    Y0, Y1 = 3.0, 22.0

    def HX(y):
        return 3.0 - 0.4 * (y - Y0) / (Y1 - Y0)

    def HZ(y):
        return 5.0 - 0.4 * (y - Y0) / (Y1 - Y0)

    def tap(fx0, fx1, fz0, fz1, y0, y1, slot, faces=None):
        prism(ub, (fx0(y0), fx1(y0), fz0(y0), fz1(y0), y0), (fx0(y1), fx1(y1), fz0(y1), fz1(y1), y1), slot, faces)

    prism(ub, (-HX(Y0), HX(Y0), -HZ(Y0), HZ(Y0), Y0), (-HX(Y1), HX(Y1), -HZ(Y1), HZ(Y1), Y1), 'Cowrie',
          {'+y': 'Stone', '-y': 'Stone'})

    def ring(y0, y1, p, slot='Stone'):
        tap(lambda y: -HX(y) - p, lambda y: HX(y) + p, lambda y: -HZ(y) - p, lambda y: HZ(y) + p, y0, y1, slot)

    ring(3.0, 3.6, 0.16)                         # 地栿
    ring(21.35, 22.0, 0.16)                      # 顶枋（石）
    if hi:
        ring(8.3, 8.7, 0.11)
    PC, PP = 0.62, 0.13                          # 角倚柱宽、凸出
    ya, yb = 3.6, 21.35
    for sx in (-1, 1):
        for sz in (-1, 1):
            tap(lambda y, sx=sx: min(sx * (HX(y) + PP), sx * (HX(y) - PC)), lambda y, sx=sx: max(sx * (HX(y) + PP), sx * (HX(y) - PC)),
                lambda y, sz=sz: min(sz * (HZ(y) + PP), sz * (HZ(y) - PC)), lambda y, sz=sz: max(sz * (HZ(y) + PP), sz * (HZ(y) - PC)),
                ya, yb, 'Stone')
    if hi:
        # 长面（±x）中倚柱（只在下段，上段是一整片贴面）
        for sx in (-1, 1):
            tap(lambda y, sx=sx: min(sx * (HX(y) + 0.1), sx * (HX(y) - 0.3)), lambda y, sx=sx: max(sx * (HX(y) + 0.1), sx * (HX(y) - 0.3)),
                lambda y: -0.27 * HZ(y) / 5.0, lambda y: 0.27 * HZ(y) / 5.0, ya, 8.3, 'Stone')
        # 下段贴面的压边框（近景）：每块板一圈 0.14 宽、凸 0.06 的石条，离倚柱 / 枋 0.22
        bw, bp = 0.14, 0.06

        def frame_x(sx, za, zb, fy0, fy1):        # za, zb：在 y=3 时的 z 范围（随收分按比例缩）
            def zf(v):
                return lambda y: v * HZ(y) / 5.0
            xo = lambda y: max(sx * (HX(y) + bp), sx * (HX(y) - 0.08))
            xi = lambda y: min(sx * (HX(y) + bp), sx * (HX(y) - 0.08))
            tap(xi, xo, zf(za), zf(za + bw), fy0, fy1, 'Stone')
            tap(xi, xo, zf(zb - bw), zf(zb), fy0, fy1, 'Stone')
            tap(xi, xo, zf(za + bw), zf(zb - bw), fy0, fy0 + bw, 'Stone')
            tap(xi, xo, zf(za + bw), zf(zb - bw), fy1 - bw, fy1, 'Stone')

        def frame_z(sz, xa, xb, fy0, fy1):
            def xf(v):
                return lambda y: v * HX(y) / 3.0
            zo = lambda y: max(sz * (HZ(y) + bp), sz * (HZ(y) - 0.08))
            zi = lambda y: min(sz * (HZ(y) + bp), sz * (HZ(y) - 0.08))
            tap(xf(xa), xf(xa + bw), zi, zo, fy0, fy1, 'Stone')
            tap(xf(xb - bw), xf(xb), zi, zo, fy0, fy1, 'Stone')
            tap(xf(xa + bw), xf(xb - bw), zi, zo, fy0, fy0 + bw, 'Stone')
            tap(xf(xa + bw), xf(xb - bw), zi, zo, fy1 - bw, fy1, 'Stone')

        g = 0.22
        for sx in (-1, 1):
            frame_x(sx, -5.0 + PC + g, -0.27 - g, 3.6 + g, 8.3 - g)
            frame_x(sx, 0.27 + g, 5.0 - PC - g, 3.6 + g, 8.3 - g)
            frame_x(sx, -5.0 + PC + g, 5.0 - PC - g, 8.7 + g, 21.35 - g)      # 上段整片的压边
        for sz in (-1, 1):
            frame_z(sz, -3.0 + PC + g, 3.0 - PC - g, 3.6 + g, 8.3 - g)
            frame_z(sz, -3.0 + PC + g, 3.0 - PC - g, 8.7 + g, 21.35 - g)

    # ---------------- 阙楼 y 22–29.7
    course(ub, 2.88, 4.88, 22.0, 22.6)                                       # 枋 A
    box(ub, (-2.7, 22.6, -4.7), (2.7, 24.6, 4.7), 'StoneDark')              # 枋头层的墙
    if hi:
        # 两排枋头（井干式的梁头），上排挑得远，下排错半格
        for row, (y0, y1, out, off) in enumerate(((23.0, 23.5, 0.75, 0.5), (24.0, 24.6, 1.15, 0.0))):
            bwid, pitch = 0.42, 0.95
            for sx in (-1, 1):                     # ±x 面：沿 z 排
                k = int((2 * 4.7 - 1.0) / pitch)
                for i in range(k + 1):
                    z = -4.7 + 0.5 + (i + off) * (2 * 4.7 - 1.0) / k
                    if z > 4.7 - 0.45:
                        continue
                    xa, xb = sx * 2.4, sx * (2.7 + out)
                    box(ub, (min(xa, xb), y0, z - bwid / 2), (max(xa, xb), y1, z + bwid / 2), 'Lacquer')
            for sz in (-1, 1):                     # ±z 面：沿 x 排
                k = int((2 * 2.7 - 1.0) / pitch)
                for i in range(k + 1):
                    x = -2.7 + 0.5 + (i + off) * (2 * 2.7 - 1.0) / k
                    if x > 2.7 - 0.45:
                        continue
                    za, zb = sz * 4.4, sz * (4.7 + out)
                    box(ub, (x - bwid / 2, y0, min(za, zb)), (x + bwid / 2, y1, max(za, zb)), 'Lacquer')
            # 转角：两向的梁头十字出头
            for sx in (-1, 1):
                for sz in (-1, 1):
                    x, z = sx * (2.7 - 0.25), sz * (4.7 - 0.25)
                    box(ub, (min(sx * 2.0, sx * (2.7 + out)), y0, z - bwid / 2), (max(sx * 2.0, sx * (2.7 + out)), y1, z + bwid / 2), 'Lacquer')
                    box(ub, (x - bwid / 2, y0, min(sz * 4.0, sz * (4.7 + out))), (x + bwid / 2, y1, max(sz * 4.0, sz * (4.7 + out))), 'Lacquer')
    course(ub, 3.65, 5.65, 24.6, 25.2)                                      # 枋 B
    box(ub, (-3.1, 25.2, -5.1), (3.1, 29.0, 5.1), 'StoneDark')              # 斗拱层的墙
    if hi:
        _brackets(ub)
    else:
        for sx in (-1, 1):                         # 远看：只留斗拱的大块
            for sz in (-1, 1):
                box(ub, (min(sx * 3.0, sx * 4.15), 27.2, min(sz * 3.2, sz * 4.4)), (max(sx * 3.0, sx * 4.15), 29.0, max(sz * 3.2, sz * 4.4)), 'Lacquer')
                box(ub, (min(sx * 1.6, sx * 2.8), 27.2, min(sz * 5.0, sz * 6.15)), (max(sx * 1.6, sx * 2.8), 29.0, max(sz * 5.0, sz * 6.15)), 'Lacquer')
    course(ub, 4.4, 6.4, 29.0, 29.7)                                        # 枋 C（比阙身顶宽 1.8 m）

    # ---------------- 阙顶：重檐四阿 y 29.7–40
    low = hip_solid(ub, 0, 0, 5.4, 7.4, 29.7, 0.4, 28.0, inner=(2.7, 4.7))  # 腰檐
    y_core0 = low['y_top'] - 0.05
    box(ub, (-2.7, y_core0, -4.7), (2.7, 34.25, 4.7), 'StoneDark')           # 上层阙楼
    course(ub, 2.95, 4.95, 34.25, 34.85)                                      # 枋 D
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(ub, (sx * 2.7 - 0.22, y_core0, sz * 4.7 - 0.22), (sx * 2.7 + 0.22, 34.25, sz * 4.7 + 0.22), 'Lacquer')
            if hi:   # 角上的小一斗二升（上层）
                box(ub, (sx * 2.7 - 0.35, 33.8, sz * 4.7 - 0.35), (sx * 2.7 + 0.35, 34.25, sz * 4.7 + 0.35), 'Lacquer')
    if hi:
        for sx in (-1, 1):
            for z in (-1.6, 0.0, 1.6):
                box(ub, (min(sx * 2.6, sx * 2.82), y_core0, z - 0.17), (max(sx * 2.6, sx * 2.82), 34.25, z + 0.17), 'Lacquer')
    top = hip_solid(ub, 0, 0, 4.9, 6.9, 34.85, 0.45, 36.0)                     # 上檐
    if hi:
        for sd in low['sides']:
            tile_rolls(ub, sd, 0.92, 0.2)
        for sd in top['sides']:
            tile_rolls(ub, sd, 0.92, 0.2)
        hip_ridges(ub, low, 0.42, 0.34)
        hip_ridges(ub, top, 0.46, 0.4)
    else:
        hip_ridges(ub, top, 0.46, 0.4)
    yr = top['y_top']
    ridge(ub, (0, 0, 0), 'z', 6.9 - 4.9 + 0.35, yr - 0.45, 1.45, 0.62, RIDGE_LIFT, n_end=6 if hi else 3)
    return ub


def _brackets(ub):
    """斗拱层：四角一斗二升（每个面两朵，离角 1.3 m），长面（±x）正中一朵曲栱。
    构件从墙里（面内 0.15）挑到外面；墙面 X=3.1 / Z=5.1，枋 C 外皮 4.4 / 6.4。"""
    y_post, y_dou, y_gong, y_sheng, y_top = 25.2, 27.2, 27.9, 28.5, 29.0

    def face_sets():
        # (法线轴, 符号, 面半长, 墙面位置, 沿面的轴)
        for sx in (-1, 1):
            yield ('x', sx, 5.1, 3.1)
        for sz in (-1, 1):
            yield ('z', sz, 3.1, 5.1)

    for ax, sg, half, wall in face_sets():
        an = np.array([sg, 0, 0.0]) if ax == 'x' else np.array([0, 0, sg * 1.0])
        au = np.array([0, 0, sg * 1.0]) if ax == 'x' else np.array([-sg * 1.0, 0, 0])   # 从外看向右
        av = np.array([0, 1.0, 0])
        o = an * wall

        def blk(u0, u1, y0, y1, d0, d1, slot='Lacquer', taper=0.0):
            """面坐标的小块：u 沿面，d 出墙距离；taper>0 时底比顶窄（斗欹）。"""
            P = [(u0 + taper, y0), (u1 - taper, y0)]
            Q = [(u0, y1), (u1, y1)]
            # 用 sweep2d：两站（左、右）
            sweep2d(ub, [P[0], P[1]], [Q[0], Q[1]], o, au, av, an, d0, d1, slot)

        corners = (-(half - 1.3), half - 1.3)
        mids = (0.0,) if ax == 'x' else ()
        for uc in corners:
            blk(uc - 0.28, uc + 0.28, y_post, y_dou, -0.15, 0.48)                         # 短倚柱
            blk(uc - 0.55, uc + 0.55, y_dou, y_dou + 0.32, -0.15, 0.92, taper=0.17)        # 栌斗：斗欹
            blk(uc - 0.55, uc + 0.55, y_dou + 0.32, y_gong, -0.15, 0.92)                   # 斗耳
            # 栱：两端下沿卷杀（向上收成弧）
            L, hgt = 1.25, y_sheng - y_gong
            us = np.linspace(-L, L, 13)
            P = []
            for u in us:
                k = max(0.0, (abs(u) - (L - 0.55)) / 0.55)
                P.append((uc + u, y_gong + hgt * 0.55 * (1 - math.sqrt(max(0.0, 1 - k * k)))))
            Q = [(uc + u, y_sheng) for u in us]
            sweep2d(ub, P, Q, o, au, av, an, -0.15, 1.0, 'Lacquer')
            for su in (-1, 1):                                                          # 两升
                uu = uc + su * (L - 0.3)
                blk(uu - 0.3, uu + 0.3, y_sheng, y_sheng + 0.2, -0.15, 1.05, taper=0.08)
                blk(uu - 0.3, uu + 0.3, y_sheng + 0.2, y_top, -0.15, 1.05)
        for uc in mids:                                                                 # 曲栱
            blk(uc - 0.25, uc + 0.25, y_post, y_dou + 0.1, -0.15, 0.45)
            blk(uc - 0.5, uc + 0.5, y_dou + 0.1, y_dou + 0.4, -0.15, 0.85, taper=0.15)
            blk(uc - 0.5, uc + 0.5, y_dou + 0.4, y_dou + 0.68, -0.15, 0.85)
            L, th = 1.75, 0.36
            us = np.linspace(-L, L, 17)
            P, Q = [], []
            for u in us:
                yc = y_dou + 0.55 + 0.95 * (abs(u) / L) ** 1.6
                P.append((uc + u, yc - th / 2))
                Q.append((uc + u, min(yc + th / 2, y_top + 0.05)))
            # 中段压在栌斗上：P 不低于斗耳顶
            sweep2d(ub, P, Q, o, au, av, an, -0.15, 0.95, 'Lacquer')
            for su in (-1, 1):
                uu = uc + su * (L - 0.15)
                blk(uu - 0.22, uu + 0.22, y_top - 0.42, y_top, -0.15, 1.0)


def build(lod=0):
    """一对紫贝阙（宫殿绝对坐标）。"""
    one = _que_local(lod)
    out = KB()
    for p in QUE_POS:
        out.merge(one.shifted(p))
    return out


# ===================================================================== 测试
def check_closed_outward(ub, tol=1e-4):
    """对每个部件：焊接同位顶点后，每条有向边都恰好有反向边配对（封闭、绕向一致），且有符号体积 > 0（法线朝外）。
    另附 BRIEF 的简单测试：面法线 · (面中心 − 部件中心) > 0 的比例（凸部件应为 100%）。返回 (坏部件列表, 简单测试通过率)。"""
    V = np.asarray(ub.V, float)
    key = np.round(V / tol).astype(np.int64)
    _, weld = np.unique(key, axis=0, return_inverse=True)
    weld = weld.ravel()
    parts = getattr(ub, 'parts', None) or [(0, len(ub.F))]
    bad, ok_s, tot_s = [], 0, 0
    for pi, (a, b) in enumerate(parts):
        F = ub.F[a:b]
        edges = {}
        for f in F:
            g = [weld[i] for i in f]
            for i in range(len(g)):
                e = (g[i], g[(i + 1) % len(g)])
                if e[0] == e[1]:
                    continue
                edges[e] = edges.get(e, 0) + 1
        open_e = sum(1 for e, c in edges.items() if edges.get((e[1], e[0]), 0) != c)
        vol = signed_volume(V, F)
        if open_e or vol <= 0:
            bad.append((pi, open_e, vol))
        idx = sorted({i for f in F for i in f})
        cen = V[idx].mean(0)
        for f in F:
            P = V[list(f)]
            n = np.zeros(3)
            for i in range(1, len(f) - 1):
                n += np.cross(P[i] - P[0], P[i + 1] - P[0])
            tot_s += 1
            ok_s += np.dot(n, P.mean(0) - cen) > 0
    return bad, ok_s / max(tot_s, 1)


if __name__ == '__main__':
    for lod in (0, 1):
        u = build(lod)
        bad, frac = check_closed_outward(u)
        print('que lod%d: %d tris, %d parts, bad %d, centroid-test %.3f' % (lod, u.tris(), len(u.parts), len(bad), frac))
        if bad:
            print(bad[:10])
