# -*- coding: utf-8 -*-
"""蓝白 · 灯与杆套件的几何（纯 numpy，不依赖 bpy）。

坐标：Blender 习惯，Z 上；杆立在原点，**+X 指向路**（灯臂伸出的方向），+Y = 沿路（车头方向）。
导出到 Unity 时 (x, y, z)_blender -> (x, z, y)_unity（见 lk_export.py），所以 +X 仍是“朝路”。
单位：米。每个部件 = (verts, faces, uvs, mat)：faces 是三角 / 四边的顶点下标，uvs 是每个面角的 UV（loop 顺序）。

部件与圣经：
  pole()         离心混凝土杆 §5.4：9 m，Ø280 → 190 mm，顶帽
  crossarm()     L63×6 镀锌角钢横担 1.5 m + 两道抱箍 + 两根斜撑（lookdev_brief §1.3）
  insulator()    针式瓷瓶（车床剖面）
  cobra_head()   眼镜蛇灯头（扁长铝壳 + 下垂棱镜罩 + 光控器 + 套管座），+X 朝灯头鼻子
  arm()          灯臂：Ø48 mm 钢管 1.0 m，仰 8°，根部底板 + 两道抱箍
  stop_lamp()    站灯：1.2 m 钢臂 + 搪瓷槽形反射罩 + T8 灯管（§5.4）
"""
import math
import numpy as np


# ---------------------------------------------------------------------------------------------- mesh accumulator
class Part:
    """一个材质的一块网格。faces 是 list[tuple]；uv 按 loop。"""

    def __init__(self, mat):
        self.mat = mat
        self.v = []
        self.f = []
        self.uv = []          # list of list[(u, v)] parallel to f

    def add_vert(self, p):
        self.v.append(tuple(float(c) for c in p))
        return len(self.v) - 1

    def add_face(self, idx, uvs):
        self.f.append(tuple(idx))
        self.uv.append([tuple(map(float, t)) for t in uvs])

    def merge(self, other):
        o = len(self.v)
        self.v += other.v
        self.f += [tuple(i + o for i in f) for f in other.f]
        self.uv += other.uv
        return self

    def transform(self, M):
        V = np.asarray(self.v, float)
        if len(V) == 0:
            return self
        V = V @ M[:3, :3].T + M[:3, 3]
        self.v = [tuple(p) for p in V]
        return self

    def tris(self):
        return sum(len(f) - 2 for f in self.f)


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    M = np.eye(4); M[:2, :2] = [[c, -s], [s, c]]; return M


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    M = np.eye(4); M[0, 0] = c; M[0, 2] = s; M[2, 0] = -s; M[2, 2] = c; return M


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    M = np.eye(4); M[1, 1] = c; M[1, 2] = -s; M[2, 1] = s; M[2, 2] = c; return M


def trans(x, y, z):
    M = np.eye(4); M[:3, 3] = (x, y, z); return M


def grid_surface(part, P, U, V, close_u=False):
    """P: (nv, nu, 3) points; U, V: (nv, nu) uv. Quads between rows. close_u: last column wraps to the first
    (the uv seam keeps its own column, so pass P with the seam column duplicated and close_u False)."""
    nv, nu = P.shape[:2]
    idx = np.empty((nv, nu), int)
    for j in range(nv):
        for i in range(nu):
            idx[j, i] = part.add_vert(P[j, i])
    for j in range(nv - 1):
        for i in range(nu - 1):
            a, b, c, d = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
            part.add_face((a, b, c, d), [(U[j, i], V[j, i]), (U[j, i + 1], V[j, i + 1]),
                                         (U[j + 1, i + 1], V[j + 1, i + 1]), (U[j + 1, i], V[j + 1, i])])
    return idx


def disc_cap(part, ring_pts, centre, uv_c, uv_r, flip=False):
    """Fan cap. ring_pts (n, 3) without duplicate seam point."""
    c = part.add_vert(centre)
    n = len(ring_pts)
    ids = [part.add_vert(p) for p in ring_pts]
    for i in range(n):
        a, b = ids[i], ids[(i + 1) % n]
        t0 = 2 * math.pi * i / n; t1 = 2 * math.pi * (i + 1) / n
        uvs = [(uv_c[0], uv_c[1]), (uv_c[0] + uv_r * math.cos(t0), uv_c[1] + uv_r * math.sin(t0)),
               (uv_c[0] + uv_r * math.cos(t1), uv_c[1] + uv_r * math.sin(t1))]
        if flip:
            part.add_face((c, b, a), [uvs[0], uvs[2], uvs[1]])
        else:
            part.add_face((c, a, b), uvs)


def lathe(part, prof, segs, uv_rect=(0, 0, 1, 1), axis_frame=None, cap_bottom=False, cap_top=False):
    """prof: list of (r, z) bottom -> top (outward normals when going up the outside). Revolve about Z."""
    prof = np.asarray(prof, float)
    th = np.linspace(0, 2 * math.pi, segs + 1)
    P = np.zeros((len(prof), segs + 1, 3))
    P[..., 0] = prof[:, :1] * np.cos(th)[None]
    P[..., 1] = prof[:, :1] * np.sin(th)[None]
    P[..., 2] = prof[:, 1:2]
    # v along arc length of profile
    seg = np.r_[0, np.cumsum(np.hypot(np.diff(prof[:, 0]), np.diff(prof[:, 1])))]
    s = seg / max(seg[-1], 1e-9)
    u0, v0, u1, v1 = uv_rect
    U = np.broadcast_to(u0 + (u1 - u0) * th[None] / (2 * math.pi), P.shape[:2])
    V = np.broadcast_to((v0 + (v1 - v0) * s)[:, None], P.shape[:2])
    if axis_frame is not None:
        P = P @ axis_frame[:3, :3].T + axis_frame[:3, 3]
    grid_surface(part, P, U, V)
    return P


def tube_path(part, pts, radius, segs, uv_v_scale=1.0, uv_u=(0, 1), up=(0, 0, 1)):
    """Sweep a circle along a polyline (parallel-transport frames). radius: scalar or per-point."""
    pts = np.asarray(pts, float)
    n = len(pts)
    r = np.broadcast_to(np.asarray(radius, float), (n,))
    T = np.gradient(pts, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.asarray(up, float)
    N0 = np.cross(T[0], up)
    if np.linalg.norm(N0) < 1e-6:
        N0 = np.cross(T[0], (1, 0, 0))
    N0 /= np.linalg.norm(N0)
    Ns = [N0]
    for k in range(1, n):
        v = Ns[-1] - np.dot(Ns[-1], T[k]) * T[k]
        Ns.append(v / np.linalg.norm(v))
    Ns = np.array(Ns)
    Bs = np.cross(T, Ns)
    th = np.linspace(0, 2 * math.pi, segs + 1)
    P = pts[:, None] + r[:, None, None] * (np.cos(th)[None, :, None] * Ns[:, None] + np.sin(th)[None, :, None] * Bs[:, None])
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    U = np.broadcast_to(uv_u[0] + (uv_u[1] - uv_u[0]) * th[None] / (2 * math.pi), P.shape[:2])
    V = np.broadcast_to((L * uv_v_scale)[:, None], P.shape[:2])
    grid_surface(part, P, U, V)
    return P


def box(part, c, half, uv_rect=(0, 0, 1, 1), M=None):
    c = np.asarray(c, float); h = np.asarray(half, float)
    corners = np.array([[sx, sy, sz] for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)], float) * h + c
    if M is not None:
        corners = corners @ M[:3, :3].T + M[:3, 3]
    ids = [part.add_vert(p) for p in corners]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    u0, v0, u1, v1 = uv_rect
    for f in faces:
        part.add_face(tuple(ids[i] for i in f), [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


# ---------------------------------------------------------------------------------------------- 杆
POLE_H = 9.0
POLE_R0 = 0.140
POLE_R1 = 0.095


def pole_radius(z, h=POLE_H):
    return POLE_R0 + (POLE_R1 - POLE_R0) * np.clip(z / h, 0, 1)


def pole(segs=24, rings=None, h=POLE_H, r0=POLE_R0, r1=POLE_R1, uv_len=POLE_H, z0=0.0):
    """Tapered spun-concrete pole. UV: u = angle / 2pi (u 0 = +X, the road side), v = z / uv_len (texture covers
    one 9 m pole: v 0..1). The long act-11 pole (73 m) reuses the texture with v wrapping (uv_len 9)."""
    part = Part('M_Lamps_Concrete')
    if rings is None:
        rings = max(2, int(math.ceil(h / 1.5)) + 1)
    zs = np.linspace(0, h, rings)
    prof = [(r0 + (r1 - r0) * z / h, z0 + z) for z in zs]
    th = np.linspace(0, 2 * math.pi, segs + 1)
    P = np.zeros((len(prof), segs + 1, 3))
    pr = np.asarray(prof)
    P[..., 0] = pr[:, :1] * np.cos(th)[None]
    P[..., 1] = pr[:, :1] * np.sin(th)[None]
    P[..., 2] = pr[:, 1:2]
    U = np.broadcast_to(th[None] / (2 * math.pi), P.shape[:2])
    V = np.broadcast_to((zs / uv_len)[:, None], P.shape[:2])
    grid_surface(part, P, U, V)
    # top cap: a shallow dome (cement cap) mapped to a corner of the texture (v > 1 is wrapped; use u 0..1, v 0.995..1)
    top = z0 + h
    ring = P[-1, :-1]
    cap_ring = np.c_[ring[:, 0] * 0.6, ring[:, 1] * 0.6, np.full(len(ring), top + 0.012)]
    ids0 = [part.add_vert(p) for p in ring]
    ids1 = [part.add_vert(p) for p in cap_ring]
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        part.add_face((ids0[i], ids0[j], ids1[j], ids1[i]), [(i / n, 0.996), ((i + 1) / n, 0.996), ((i + 1) / n, 0.999), (i / n, 0.999)])
    disc_cap(part, cap_ring, (0, 0, top + 0.02), (0.5, 0.999), 0.0005)
    return part


# ---------------------------------------------------------------------------------------------- 横担、瓷瓶
def angle_profile(a=0.063, t=0.006):
    """L-section in the (y, z) plane, the heel at the origin, legs along +y (horizontal leg, on top) and -z."""
    return [(0, 0), (a, 0), (a, -t), (t, -t), (t, -a), (0, -a)]


def extrude_poly(part, poly2d, length, axis='x', uv_scale=1.0):
    """Extrude a closed 2D polygon (y, z) along +X from -length/2..+length/2. Side faces + end caps (fan)."""
    poly = np.asarray(poly2d, float)
    n = len(poly)
    xs = (-length / 2, length / 2)
    ids = [[part.add_vert((x, p[0], p[1])) for p in poly] for x in xs]
    per = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1))]
    for i in range(n):
        j = (i + 1) % n
        part.add_face((ids[0][i], ids[0][j], ids[1][j], ids[1][i]),
                      [(per[i] * uv_scale, 0), (per[i + 1] * uv_scale, 0), (per[i + 1] * uv_scale, length * uv_scale), (per[i] * uv_scale, length * uv_scale)])
    for k, flip in ((0, True), (1, False)):
        cid = part.add_vert((xs[k], poly[:, 0].mean(), poly[:, 1].mean()))
        for i in range(n):
            j = (i + 1) % n
            f = (cid, ids[k][i], ids[k][j]) if not flip else (cid, ids[k][j], ids[k][i])
            part.add_face(f, [(0.0, 0.0), (0.01, 0.0), (0.0, 0.01)])


def crossarm(z=8.70, length=1.5, lod=0):
    """Galvanised L63x6 across the road direction (along X), bolted to the pole's -Y face? No: the crossarm sits on
    the pole's side facing along the road (+Y face) and spans X. Returns Part (M_Lamps_Steel)."""
    part = Part('M_Lamps_Steel')
    rz = pole_radius(z)
    arm = Part('M_Lamps_Steel')
    # profile: heel at the top-outer corner, horizontal leg pointing +Y (away from the pole), vertical leg down
    extrude_poly(arm, angle_profile(), length, uv_scale=1.0)
    arm.transform(trans(0, rz + 0.002, z))
    part.merge(arm)
    if lod <= 1:
        # two band clamps around the pole (flat bar 50 x 6 mm) just below the arm
        for dz in (-0.035,):
            b = Part('M_Lamps_Steel')
            r = pole_radius(z + dz) + 0.004
            lathe(b, [(r + 0.006, z + dz - 0.025), (r + 0.006, z + dz + 0.025), (r, z + dz + 0.025), (r, z + dz - 0.025), (r + 0.006, z + dz - 0.025)],
                  12 if lod == 0 else 8, uv_rect=(0, 0.9, 1, 1))
            part.merge(b)
        # two flat-bar braces from the arm (x = +-0.5) down to the pole at z - 0.55
        for sx in (-1, 1):
            p0 = np.array([sx * 0.50, rz + 0.03, z - 0.06])
            zb = z - 0.55
            p1 = np.array([sx * (pole_radius(zb) + 0.01), pole_radius(zb) * 0.5 + 0.03, zb])
            d = p1 - p0; L = np.linalg.norm(d); d /= L
            # flat bar 40 x 5 mm: box along d
            ang = math.atan2(d[2], d[0])
            M = trans(*((p0 + p1) / 2)) @ rot_y(-ang)
            box(part, (0, 0, 0), (L / 2, 0.020, 0.0025), M=M)
    return part


INS_PROFILE = [  # (r, z) of a small porcelain pin insulator (two sheds), z from the pin top up; bottom -> top, outside
    (0.016, 0.000), (0.055, 0.020), (0.056, 0.027), (0.028, 0.036),
    (0.040, 0.068), (0.041, 0.075), (0.028, 0.084), (0.028, 0.104), (0.034, 0.112),
    (0.022, 0.126), (0.0, 0.130)]


def insulator(pos, segs=16):
    part = Part('M_Lamps_Porcelain')
    lathe(part, INS_PROFILE, segs, axis_frame=trans(*pos))
    # steel pin under it
    pin = Part('M_Lamps_Steel')
    lathe(pin, [(0.010, -0.09), (0.010, 0.0), (0.0, 0.002)], 8, axis_frame=trans(*pos))
    return part, pin


def insulator_tops(z=8.70, length=1.5):
    """Where the conductors sit (top groove of each insulator): two on the arm, one on the pole top."""
    rz = pole_radius(z)
    yy = rz + 0.002 + 0.035
    zt = z + 0.09 + 0.104
    return [(-0.66, yy, zt), (0.66, yy, zt), (0.0, 0.0, POLE_H + 0.18 + 0.104)]


def insulator_bases(z=8.70):
    rz = pole_radius(z)
    yy = rz + 0.002 + 0.035
    return [(-0.66, yy, z + 0.09), (0.66, yy, z + 0.09), (0.0, 0.0, POLE_H + 0.18)]


# ---------------------------------------------------------------------------------------------- 眼镜蛇灯头
HEAD_L = 0.68
REF_C = 0.43          # refractor centre along the head (from the fitter end)
REF_A = 0.200         # refractor semi-length
REF_B = 0.125         # refractor semi-width
REF_D = 0.085         # refractor depth below the housing rim


def _head_section(x):
    """Half-width w, rim height zb (bottom, local), top height zt at station x in [0, HEAD_L].
    Fitter neck (tube Ø76) for x < 0.12, then the body swells to w 0.16 at x 0.42 and rounds into the nose."""
    xn = np.clip(x / HEAD_L, 0, 1)
    # plan outline: neck 0.038 -> body 0.160 -> nose (ellipse)
    neck = 0.040
    if x < 0.10:
        w = neck
    elif x < 0.46:
        t = (x - 0.10) / 0.36
        w = neck + (0.160 - neck) * (1 - (1 - t) ** 2.2)
    else:
        t = (x - 0.46) / (HEAD_L - 0.46)
        w = 0.160 * math.sqrt(max(0.0, 1 - t ** 2.0))
    # side elevation: bottom rim flat at 0 (body), neck centred on the arm axis (z 0.05)
    if x < 0.10:
        zb, zt = 0.012, 0.088
    else:
        t = min(1.0, (x - 0.10) / 0.12)
        zb = 0.012 * (1 - t)
        # top: rises to 0.150 around x 0.30, falls to the nose
        u = (x - 0.10) / (HEAD_L - 0.10)
        zt = 0.088 + (0.150 - 0.088) * math.sin(math.pi * min(1.0, u / 0.55) / 2) if u < 0.55 else \
            0.150 * math.sqrt(max(0.0, 1 - ((u - 0.55) / 0.45) ** 2.6)) + 0.0 * u
        zt = max(zt, zb + 0.004)
    return w, zb, zt


def cobra_head(nx=26, nt=18, lod=0):
    """Returns dict of Parts: housing, refractor, photocell, arc tube. Local frame: fitter at x = 0 (slips onto the
    arm tip), nose at +X, rim plane z = 0, up +Z. The arm axis enters at (0, 0, 0.05)."""
    if lod == 1:
        nx, nt = 14, 10
    elif lod >= 2:
        nx, nt = 7, 6
    housing = Part('M_Lamps_Housing')
    xs = np.r_[np.linspace(0.0, 0.10, 3 if lod == 0 else 2)[:-1], np.linspace(0.10, HEAD_L, nx)]
    # cross-section: superellipse top arc from (+w, zb) over (0, zt) to (-w, zb), then the flat bottom back.
    ts = np.linspace(0, math.pi, nt)
    P = np.zeros((len(xs), nt + 2, 3))
    U = np.zeros(P.shape[:2]); V = np.zeros(P.shape[:2])
    for i, x in enumerate(xs):
        w, zb, zt = _head_section(x)
        n_exp = 2.6
        for k, t in enumerate(ts):
            c, s = math.cos(t), math.sin(t)
            yy = w * np.sign(c) * abs(c) ** (2 / n_exp)
            zz = zb + (zt - zb) * abs(s) ** (2 / n_exp)
            P[i, k] = (x, yy, zz)
        # bottom: rim, inset 6 mm (the door frame), back to start
        P[i, nt] = (x, -w * 0.96, zb - 0.004)
        P[i, nt + 1] = (x, w * 0.96, zb - 0.004)
        U[i] = np.r_[ts / math.pi * 0.75, 0.80, 0.95]
        V[i] = x / HEAD_L
    grid_surface(housing, P, U, V)
    # close the bottom ring (last column -> first column)
    # (the bottom face between rim lines: quads from column nt+1 to column 0)
    base = len(housing.v) - P.shape[0] * P.shape[1]
    ncol = P.shape[1]
    for i in range(len(xs) - 1):
        a = base + i * ncol + (ncol - 1); b = base + i * ncol + 0
        c = base + (i + 1) * ncol + 0; d = base + (i + 1) * ncol + (ncol - 1)
        housing.add_face((a, b, c, d), [(0.95, V[i, 0]), (1.0, V[i, 0]), (1.0, V[i + 1, 0]), (0.95, V[i + 1, 0])])
    # fitter end cap (the arm goes in)
    ring = P[0, :, :]
    disc_cap(housing, ring, ring.mean(0), (0.9, 0.05), 0.04, flip=True)
    # nose: degenerate already (w -> 0)
    parts = {'housing': housing}
    # refractor: half ellipsoid below the rim, centre (REF_C, 0, 0). UV: u = azimuth / 2pi, v = 0 (rim) .. 1 (pole)
    ref = Part('M_Lamps_Refractor')
    na = 28 if lod == 0 else (14 if lod == 1 else 8)
    nr = 9 if lod == 0 else (5 if lod == 1 else 3)
    az = np.linspace(0, 2 * math.pi, na + 1)
    el = np.linspace(0, math.pi / 2, nr + 1)[:-1]
    PR = np.zeros((nr + 1, na + 1, 3)); UR = np.zeros(PR.shape[:2]); VR = np.zeros(PR.shape[:2])
    for j, e in enumerate(el):
        for i, a in enumerate(az):
            PR[j, i] = (REF_C + REF_A * math.cos(e) * math.cos(a), REF_B * math.cos(e) * math.sin(a), -0.004 - REF_D * math.sin(e))
            UR[j, i] = a / (2 * math.pi); VR[j, i] = e / (math.pi / 2)
    # the bottom pole: tiny ring
    for i, a in enumerate(az):
        PR[nr, i] = (REF_C + REF_A * 0.06 * math.cos(a), REF_B * 0.06 * math.sin(a), -0.004 - REF_D * 0.998)
        UR[nr, i] = a / (2 * math.pi); VR[nr, i] = 0.98
    # orientation: rows go from rim (top) to bottom, outward normal must point down/out: reverse column order
    grid_surface(ref, PR[:, ::-1], UR[:, ::-1], VR[:, ::-1])
    disc_cap(ref, PR[nr, :-1], (REF_C, 0, -0.004 - REF_D), (0.5, 1.0), 0.001, flip=False)
    parts['refractor'] = ref
    if lod <= 1:
        # photocell: a short cylinder + dome on top of the housing at x 0.26
        pc = Part('M_Lamps_Photocell')
        _, _, zt = _head_section(0.26)
        lathe(pc, [(0.034, zt - 0.01), (0.036, zt + 0.030), (0.034, zt + 0.042), (0.024, zt + 0.054), (0.0, zt + 0.058)],
              12 if lod == 0 else 8, axis_frame=trans(0.26, 0, 0))
        parts['photocell'] = pc
    # arc tube (HPS, 100 mm, Ø9) inside the refractor: emissive core (only LOD0/1; LOD2 relies on the refractor glow)
    if lod <= 1:
        arc = Part('M_Lamps_ArcTube')
        tube_path(arc, [(REF_C - 0.06, 0, -0.030), (REF_C + 0.06, 0, -0.030)], 0.0045, 8)
        parts['arc'] = arc
    return parts


# ---------------------------------------------------------------------------------------------- 灯臂
ARM_LEN = 1.0
ARM_TILT = math.radians(8.0)
ARM_R = 0.024


def arm(root_z, lod=0):
    """Ø48 steel pipe from the pole surface along +X, rising 8 deg; a 0.30 m back plate with two band clamps.
    Returns (Part, tip) where tip = the point the head's fitter axis attaches to."""
    part = Part('M_Lamps_ArmSteel')
    r = pole_radius(root_z)
    p0 = np.array([r + 0.03, 0.0, root_z])
    d = np.array([math.cos(ARM_TILT), 0.0, math.sin(ARM_TILT)])
    p1 = p0 + d * ARM_LEN
    n = 6 if lod == 0 else 2
    pts = [p0 + d * ARM_LEN * t for t in np.linspace(0, 1, n)]
    tube_path(part, pts, ARM_R, 12 if lod == 0 else (8 if lod == 1 else 6), uv_v_scale=1.0)
    # end caps of the pipe (cheap fan)
    if lod <= 1:
        # back plate (vertical, against the pole), 0.30 x 0.10 x 0.008
        box(part, (r + 0.012, 0, root_z), (0.008, 0.05, 0.15))
        for dz in (-0.11, 0.11):
            rr = pole_radius(root_z + dz) + 0.004
            lathe(part, [(rr + 0.006, root_z + dz - 0.022), (rr + 0.006, root_z + dz + 0.022), (rr, root_z + dz + 0.022),
                         (rr, root_z + dz - 0.022), (rr + 0.006, root_z + dz - 0.022)], 12 if lod == 0 else 8, uv_rect=(0, 0.9, 1, 1))
    return part, p1


def road_lamp(lod=0, head_bottom_z=6.5):
    """The whole act-2 lamp standard: pole + crossarm + 3 insulators + arm + cobra head.
    head_bottom_z = height of the refractor's lowest point above the road (bible §6·2: 6.5 m).
    Returns (dict mat -> Part, info)."""
    parts = []
    parts.append(pole(segs=(24, 12, 6)[lod]))
    parts.append(crossarm(lod=lod))
    if lod <= 1:
        for p in insulator_bases():
            a, b = insulator(p, segs=(12, 8)[lod])
            parts += [a, b]
    # head: rotate so the head's local frame sits at the arm tip with the same 8 deg tilt; the fitter axis is at
    # local z 0.05, so the refractor bottom = tip_z - 0.05 + (-0.004 - REF_D) after the small tilt
    # solve root_z so that the refractor's lowest point lands at head_bottom_z
    drop = 0.05 + 0.004 + REF_D
    tip_rise = ARM_LEN * math.sin(ARM_TILT)
    # the tilt lifts the nose: lowest point of the refractor ~ at x REF_C: + REF_C*sin(tilt)
    low_extra = REF_C * math.sin(ARM_TILT) * 0.5
    root_z = head_bottom_z + drop - tip_rise - low_extra
    ap, tip = arm(root_z, lod=lod)
    parts.append(ap)
    H = cobra_head(lod=lod)
    M = trans(*tip) @ rot_y(-ARM_TILT) @ trans(-0.06, 0, -0.05)   # 6 cm of arm inside the fitter
    head_parts = []
    for k, p in H.items():
        p.transform(M)
        head_parts.append(p)
    parts += head_parts
    # measure
    refr = H['refractor']
    Vr = np.asarray(refr.v)
    info = dict(root_z=root_z, tip=tuple(tip), refractor_centre=tuple(Vr.mean(0)),
                refractor_low=float(Vr[:, 2].min()),
                arc_centre=tuple(np.asarray(H['arc'].v).mean(0)) if 'arc' in H else tuple(Vr.mean(0)),
                insulator_tops=insulator_tops())
    return merge_by_material(parts), info


def merge_by_material(parts):
    out = {}
    for p in parts:
        if p.mat in out:
            out[p.mat].merge(p)
        else:
            q = Part(p.mat); q.merge(p); out[p.mat] = q
    return out


# ---------------------------------------------------------------------------------------------- 站灯（§5.4）
STOP_ARM_Z = 4.2
STOP_ARM_LEN = 1.2
TUBE_LEN = 1.2
TUBE_R = 0.013
TROUGH_L = 1.30


def trough_section(w=0.20, h=0.075, t=0.0012):
    """Enamel trough reflector cross-section (y, z): an open, flared channel (outside then inside, one closed loop
    with a rolled lip). Opening downward. z = 0 at the lips."""
    ys = np.linspace(-1, 1, 15)
    outer = [(w / 2 * y, h * (1 - abs(y) ** 1.6)) for y in ys]          # top curve, lips at z 0
    inner = [(p[0] * 0.985, p[1] - 0.004) for p in outer[::-1]]
    return outer + inner


def stop_lamp(lod=0):
    """Station lamp on the same pole: 1.2 m horizontal steel arm at 4.2 m (+X), an enamel trough (along Y, i.e.
    along the road) hung under the arm's end, and a bare 1.2 m T8 tube in it. Returns (dict, info)."""
    parts = [pole(segs=(24, 12, 6)[lod]), crossarm(lod=lod)]
    if lod <= 1:
        for p in insulator_bases():
            a, b = insulator(p, segs=(12, 8)[lod])
            parts += [a, b]
    armp = Part('M_Lamps_ArmSteel')
    r = pole_radius(STOP_ARM_Z)
    p0 = np.array([r + 0.03, 0, STOP_ARM_Z]); p1 = p0 + np.array([STOP_ARM_LEN, 0, 0])
    tube_path(armp, [p0, p1], ARM_R, (12, 8, 6)[lod])
    if lod <= 1:
        box(armp, (r + 0.012, 0, STOP_ARM_Z), (0.008, 0.05, 0.15))
    parts.append(armp)
    # trough: runs along the arm (+X, across the road), hung 0.12 m under it on two hangers, so from the spawn point
    # and from the bus door the 1.2 m tube is seen side-on (bible §6·1: the brightest thing in the world)
    tr = Part('M_Lamps_Enamel')
    sec = np.asarray(trough_section())
    secc = np.vstack([sec, sec[:1]])
    per = np.r_[0, np.cumsum(np.linalg.norm(np.diff(secc, axis=0), axis=1))]
    xc = r + 0.15 + TROUGH_L / 2          # trough centre: starts 0.15 m off the pole, overhangs the arm tip by ~0.2 m
    xs = np.array([-TROUGH_L / 2, TROUGH_L / 2])
    P = np.zeros((2, len(secc), 3)); U = np.zeros(P.shape[:2]); V = np.zeros(P.shape[:2])
    for i, x in enumerate(xs):
        for k, (yy, zz) in enumerate(secc):
            P[i, k] = (x, yy, zz)
            U[i, k] = per[k] / per[-1]; V[i, k] = (x + TROUGH_L / 2) / TROUGH_L
    grid_surface(tr, P[::-1], U[::-1], V[::-1])
    for x, flip in ((-TROUGH_L / 2, True), (TROUGH_L / 2, False)):
        c = tr.add_vert((x, 0, 0.03))
        ids = [tr.add_vert((x, yy, zz)) for yy, zz in sec[:len(sec) // 2]]
        for i in range(len(ids) - 1):
            f = (c, ids[i], ids[i + 1]) if not flip else (c, ids[i + 1], ids[i])
            tr.add_face(f, [(0.5, 0.5), (0.51, 0.5), (0.5, 0.51)])
    hang = 0.195
    trough_z = STOP_ARM_Z - hang - 0.075
    tr.transform(trans(xc, 0, trough_z))
    parts.append(tr)
    if lod <= 1:
        for dx in (-0.45, 0.40):
            tube_path(armp, [(xc + dx, 0, STOP_ARM_Z), (xc + dx, 0, trough_z + 0.07)], 0.007, 6)
    # tube + two lamp holders
    tube = Part('M_Lamps_Tube')
    tz = trough_z - 0.030
    n = 8 if lod == 0 else 4
    tube_path(tube, [(xc + x, 0, tz) for x in np.linspace(-TUBE_LEN / 2, TUBE_LEN / 2, n)], TUBE_R, (12, 8, 6)[lod],
              uv_v_scale=1.0 / TUBE_LEN)
    parts.append(tube)
    if lod <= 1:
        hold = Part('M_Lamps_Bakelite')
        for x in (-TUBE_LEN / 2 - 0.02, TUBE_LEN / 2 + 0.02):
            box(hold, (xc + x, 0, tz + 0.012), (0.02, 0.018, 0.028))
        parts.append(hold)
    p1 = np.array([r + 0.03 + STOP_ARM_LEN, 0, STOP_ARM_Z])
    info = dict(tube_centre=(float(xc), 0.0, float(tz)), tube_axis='X', tube_len=TUBE_LEN,
                trough_lip_z=float(trough_z), arm_tip=tuple(map(float, p1)),
                drip_lip=(float(xc + TROUGH_L / 2), float(sec[0][0]), float(trough_z)),
                insulator_tops=insulator_tops())
    return merge_by_material(parts), info


# ---------------------------------------------------------------------------------------------- 电线
def catenary(p0, p1, sag, n=24):
    """Points of a hanging conductor from p0 to p1 with mid-span sag `sag` (m, positive = downward).
    Uses the parabola-equivalent catenary through both supports (exact enough at f/L < 3 %).
    Negative sag = the wire bows UP (act 11, the world upside down)."""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    t = np.linspace(0, 1, n)
    L = np.linalg.norm((p1 - p0)[:2])
    # catenary parameter a from sag: f = a (cosh(L/2a) - 1)
    if abs(sag) < 1e-6:
        dz = np.zeros(n)
    else:
        f = abs(sag)
        lo, hi = 0.1, 1e5
        for _ in range(80):
            a = 0.5 * (lo + hi)
            if a * (math.cosh(L / (2 * a)) - 1) > f:
                lo = a
            else:
                hi = a
        s = (t - 0.5) * L
        dz = -(f - a * (np.cosh(s / a) - 1)) * np.sign(sag)
    P = p0[None] + t[:, None] * (p1 - p0)[None]
    P[:, 2] += dz
    return P


def tri_count(d):
    return sum(p.tris() for p in d.values())


if __name__ == '__main__':
    for lod in (0, 1, 2):
        d, info = road_lamp(lod)
        print('road lamp LOD%d tris %d' % (lod, tri_count(d)), {k: p.tris() for k, p in d.items()})
    print(info)
    for lod in (0, 1, 2):
        d, info = stop_lamp(lod)
        print('stop lamp LOD%d tris %d' % (lod, tri_count(d)))
    print(info)
