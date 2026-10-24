# -*- coding: utf-8 -*-
"""D-36 A2 · 侧窗（车里看）：主座位旁边的 WinR1 在 0.5 m，全片都在画面里。

照片：`Bus/Docs~/实物参考_车与车厢/车厢_01…03_Fortepan.jpg`（窗的上半截是两扇推拉小窗，窗扣在横档上）、
`实物参考_PAZ细节/D06`（没有玻璃的后窗框：框的断面）、`D08`（窗框边的胶条和金属条）；Kolesa：推拉气窗的窗扣
“像马自达的转子”。
  - 铝窗框：L 形断面（贴在内墙上的 30 mm 面 + 伸进窗洞的 20 mm 内衬），四角跟外面一样是 R 70 的大圆角；
  - 胶条：玻璃里侧一道带唇的黑胶条，唇压在玻璃上；
  - 横档：玻璃上 1.905–1.935 m 的双槽铝轨（推拉窗在里面滑）；
  - 上扇：两扇推拉小窗，各有一个 16 mm 的铝扇框，里外错开一层；相会处的竖梃上一个转子形窗扣 + 对面的扣座；
  - 窗台：带圆鼻的窗台板（奶白搪瓷）。
**视窗合同不能变坏**：所有东西伸进窗洞的量 ≤ 外面胶条（22 mm）的投影；全高的竖中梃去掉了（只在上扇有），
下扇的净玻璃只会变大。组装后重跑 viewcheck（15/15、hero_occlusion）。

坐标：沿车身周长的 u + 高度 y（build_bus.perim_u / surf / surf_n），深度 d 从外皮往里量（外皮 0、玻璃 0.015、
内墙 SHELL_T = 0.035），i 从窗洞边往窗洞里量（正 = 伸进窗洞）。
"""
import math

import bmesh
import numpy as np

import build_bus as BB
import bus_spec as B
from parts import common as C

R_CORNER = 0.07


def _wall_frame(u, y):
    """outer-skin point, outward normal, and the in-plane unit vectors along u and y (Unity, numpy)."""
    p = np.array(BB.surf(u, y))
    n = np.array(BB.surf_n(u, y))
    du = np.array(BB.surf(u + 0.002, y)) - np.array(BB.surf(u - 0.002, y))
    du /= np.linalg.norm(du)
    dy = np.cross(n, du)
    if dy[1] < 0:
        dy = -dy
    return p, n, du, dy


def sweep_framed(name, rails, profile, m, collection='Cabin', closed=True):
    """rails: list of (origin, axis_d, axis_i) (Unity numpy): the profile [(d, i), ...] (a closed polygon) is placed at
    origin + axis_d * d + axis_i * i at every rail point and skinned. Hard edges (the profile's corners) stay sharp
    by duplicated profile points; everything else is smooth-shaded."""
    bm = bmesh.new()
    rings = [[bm.verts.new(BB.U2B(tuple(o + ad * d + ai * i))) for d, i in profile] for o, ad, ai in rails]
    S, N = len(profile), len(rings)
    for k in range(N - (0 if closed else 1)):
        a, b = rings[k], rings[(k + 1) % N]
        for j in range(S):
            try:
                bm.faces.new((a[j], a[(j + 1) % S], b[(j + 1) % S], b[j]))
            except ValueError:
                pass
    if not closed:
        for ring in (rings[0], list(reversed(rings[-1]))):
            try:
                bm.faces.new(ring)
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = BB.obj_from_bm(name, bm, [m], collection)
    return C.finish(ob, auto_smooth_deg=50)


def _round(poly, r=0.0015, n=2):
    """round every corner of a small closed (d, i) polygon by r (keeps the profiles from being knife-edged)."""
    out = []
    P = [np.array(p, float) for p in poly]
    for k in range(len(P)):
        a, b, c = P[k - 1], P[k], P[(k + 1) % len(P)]
        u, v = a - b, c - b
        lu, lv = np.linalg.norm(u), np.linalg.norm(v)
        if lu < 1e-9 or lv < 1e-9:
            continue
        rr = min(r, 0.45 * lu, 0.45 * lv)
        p0, p1 = b + u / lu * rr, b + v / lv * rr
        for t in np.linspace(0, 1, n + 2):
            q = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t ** 2 * p1      # quadratic bezier through the corner
            out.append(tuple(q))
    return out


def _outline_rails(seg, z0, z1, y0, y1, r, offset_i=0.0, step=0.02, n_arc=10):
    """the window outline (rounded rect in u / y), each point with its depth axis (into the cabin) and its i axis
    (into the opening). offset_i moves the outline out (-) / in (+)."""
    ua, ub = sorted((BB.perim_u(seg, z0), BB.perim_u(seg, z1)))
    o = -offset_i
    rr = {k: max(0.0, r + o) for k in ('00', '10', '11', '01')}
    pts = BB._outline(ua - o, ub + o, y0 - o, y1 + o, rr, n_arc=n_arc, step=step)
    cu, cy = (ua + ub) / 2, (y0 + y1) / 2
    rails = []
    for u, y in pts:
        p, n, du, dy = _wall_frame(u, y)
        rails.append([p, -n, du, dy, (u, y)])
    out = []
    M = len(rails)
    for k, (p, nd, du, dy, (u, y)) in enumerate(rails):
        u1, y1_ = rails[(k + 1) % M][4]
        u0_, y0_ = rails[k - 1][4]
        t = np.array([u1 - u0_, y1_ - y0_])
        t /= max(np.linalg.norm(t), 1e-12)
        nin = np.array([-t[1], t[0]])                         # ccw outline: left normal points inside
        ai = du * nin[0] + dy * nin[1]
        ai /= np.linalg.norm(ai)
        out.append((p, nd, ai))
    return out


# profiles (d, i): d from the outer skin into the cabin, i from the opening edge into the opening
FRAME = _round([(BB.SHELL_T + 0.0045, -0.030), (BB.SHELL_T + 0.0045, 0.007), (0.021, 0.007), (0.021, 0.0045),
                (BB.SHELL_T + 0.0015, 0.0045), (BB.SHELL_T + 0.0015, -0.030)], 0.0012)
GASKET = _round([(0.0153, -0.006), (0.0153, 0.010), (0.0168, 0.011), (0.0200, 0.006), (0.0222, 0.002),
                 (0.0222, -0.006)], 0.0012)


def side_window(seg, k, z0, z1, quality='low', collection='Cabin'):
    """everything on the inside of one side window. seg 'R' / 'L'."""
    y0, y1 = B.WIN_SILL, B.WIN_HEAD
    nm = 'Win%s%d' % (seg, k)
    objs = []
    step = 0.012 if quality == 'high' else 0.025
    objs.append(sweep_framed(nm + '_Frame', _outline_rails(seg, z0, z1, y0, y1, R_CORNER, step=step), FRAME, 'Alu', collection))
    objs.append(sweep_framed(nm + '_GasketIn', _outline_rails(seg, z0, z1, y0, y1, R_CORNER, step=step), GASKET, 'Seal', collection))
    ua, ub = sorted((BB.perim_u(seg, z0), BB.perim_u(seg, z1)))
    um = (ua + ub) / 2
    us = np.linspace(ua + 0.004, ub - 0.004, max(8, int((ub - ua) / 0.05)))
    # transom: a double-track alu rail across the glass (inside), 1.905-1.935 (= the outside transom)
    TR = _round([(0.016, -0.0105), (0.031, -0.0105), (0.031, -0.004), (0.027, -0.004), (0.027, 0.004), (0.031, 0.004),
                 (0.031, 0.0105), (0.016, 0.0105)], 0.001)          # (no taller than the outside transom: the contract band)
    rails = []
    for u in us:
        p, n, du, dy = _wall_frame(u, 1.92)
        rails.append((p, -n, dy))
    objs.append(sweep_framed(nm + '_Transom', rails, TR, 'Alu', collection, closed=False))
    # sill board with a rounded nose (cream enamel), under the frame
    SILL = _round([(BB.SHELL_T, -0.006), (0.092, -0.006), (0.098, -0.014), (0.098, -0.030), (0.090, -0.036),
                   (BB.SHELL_T, -0.036)], 0.004, 3)
    rails = []
    for u in np.linspace(ua - 0.03, ub + 0.03, max(8, int((ub - ua) / 0.05))):
        p, n, du, dy = _wall_frame(u, y0 - 0.032)
        rails.append((p, -n, dy))
    objs.append(sweep_framed(nm + '_Sill', rails, SILL, 'Int_Enamel', collection, closed=False))
    # the two upper sashes: 16 mm alu frames, the rear one inside the front one, meeting 30 mm past the middle
    ys0, ys1 = 1.937, y1 - 0.004
    SASH = _round([(0.0, -0.008), (0.0, 0.008), (0.008, 0.008), (0.008, -0.008)], 0.0015)
    for s_, (a_, b_), dd in ((0, (ua + 0.006, um + 0.018), 0.024), (1, (um - 0.018, ub - 0.006), 0.017)):
        ra = {'00': 0.006, '10': 0.006, '11': 0.006 if s_ == 0 else R_CORNER - 0.01,
              '01': R_CORNER - 0.01 if s_ == 0 else 0.006}
        pts = BB._outline(a_, b_, ys0, ys1, ra, n_arc=8, step=step)
        rails = []
        M = len(pts)
        for j, (u, y) in enumerate(pts):
            p, n, du, dy = _wall_frame(u, y)
            u1, y1_ = pts[(j + 1) % M]
            u0_, y0_ = pts[j - 1]
            t = np.array([u1 - u0_, y1_ - y0_])
            t /= max(np.linalg.norm(t), 1e-12)
            ai = du * -t[1] + dy * t[0]
            ai /= np.linalg.norm(ai)
            rails.append((p - n * dd, -n, ai))
        objs.append(sweep_framed(nm + '_Sash%d' % s_, rails, SASH, 'Alu', collection))
    # the 'rotor' latch (a Reuleaux triangle knob on a base plate) on the inner sash's meeting stile, and its keeper
    yl = (ys0 + ys1) / 2
    p, n, du, dy = _wall_frame(um + 0.018 - 0.008, yl)
    base = p - n * 0.032
    objs.append(_reuleaux(nm + '_Latch', base, -n, du, dy, 0.016, 0.007, 'Chrome', collection))
    p2, n2, du2, dy2 = _wall_frame(um - 0.03, yl)
    objs.append(_plate(nm + '_Keeper', p2 - n2 * 0.025, -n2, du2, dy2, 0.010, 0.014, 0.005, 'Chrome', collection))
    return objs


def _plate(name, c, nd, du, dy, hu, hy, t, m, collection):
    """a small rounded plate (a box in the wall's local frame, bevelled)."""
    bm = bmesh.new()
    corners = []
    for sd in (0, 1):
        for su, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            corners.append(bm.verts.new(BB.U2B(tuple(c + nd * (t * sd) + du * (hu * su) + dy * (hy * sy)))))
    f = lambda *ix: bm.faces.new([corners[i] for i in ix])
    f(0, 1, 2, 3); f(4, 7, 6, 5); f(0, 4, 5, 1); f(1, 5, 6, 2); f(2, 6, 7, 3); f(3, 7, 4, 0)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=min(t, hu, hy) * 0.3, segments=2, affect='EDGES')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.finish(BB.obj_from_bm(name, bm, [m], collection), auto_smooth_deg=45)


def _reuleaux(name, c, nd, du, dy, r, t, m, collection, n=12):
    """a Reuleaux-triangle knob ('like a Mazda rotor', Kolesa) of width r, thickness t, on a round boss."""
    bm = bmesh.new()
    V = [np.array([math.cos(a), math.sin(a)]) * r / math.sqrt(3) for a in (math.pi / 2, math.pi / 2 + 2.094, math.pi / 2 + 4.189)]
    pts2 = []
    for k in range(3):
        cen = V[(k + 2) % 3]
        a0 = math.atan2(*(V[k] - cen)[::-1])
        a1 = math.atan2(*(V[(k + 1) % 3] - cen)[::-1])
        if a1 < a0:
            a1 += 2 * math.pi
        if a1 - a0 > math.pi:
            a1 -= 2 * math.pi
        for s in np.linspace(0, 1, n, endpoint=False):
            a = a0 + (a1 - a0) * s
            pts2.append(cen + r * np.array([math.cos(a), math.sin(a)]))
    lo = [bm.verts.new(BB.U2B(tuple(c + du * q[0] + dy * q[1]))) for q in pts2]
    hi = [bm.verts.new(BB.U2B(tuple(c + nd * t + du * q[0] + dy * q[1]))) for q in pts2]
    N = len(pts2)
    for k in range(N):
        bm.faces.new((lo[k], lo[(k + 1) % N], hi[(k + 1) % N], hi[k]))
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > 0.6],
                    offset=0.0012, segments=2, affect='EDGES')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.finish(BB.obj_from_bm(name, bm, [m], collection), auto_smooth_deg=40)
