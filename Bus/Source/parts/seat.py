# -*- coding: utf-8 -*-
"""D-36 A1 · 座椅模块 r5：照确定的 PAZ-672M 做。

依据：`Bus/Docs~/实物参考_PAZ细节/README.md` §6（Kolesa 那辆 1989 年的 672M 回答了座椅五问）和总导演 10-25；结构照
`flickr/F01–F04`（trolleway 那辆多半是 672，结构和 672M 一样，颜色不照）。总导演 r4 五条里 1（缝边紧、顶面软、侧面竖直
微鼓、真滚条）、2（光泽分区，见 materials.vinyl）、3（薄托板、看得见管框）照做；4（扶手角橡胶套）和 5（铝 U 型包边）
被 672M 实物替代：整条黑色人造革管套、四边压凸边的冲压背板。

  - 一根漆过的 Ø25 弯管做侧框和靠背框（不镀铬；颜色先用圣经“座椅框架”一行 #3C3E3D，等总导演定）：
    后腿顶 → 后腿下去 → 沿地往前 → 前腿上来 → 座垫侧下面往后 → 拐上去沿靠背侧 → 到顶拐弯横贯整个靠背 →
    另一侧对称下来（F04 的侧框是一个圈：前腿、地上一段、后腿；地上两块小脚板各两颗螺栓）。
  - 横的那一段整条套黑色人造革管套 Ø55，一道缝，两头收口；两头弯角露漆管（672M 和 672 的区别）。
  - 座垫 100 mm 厚，前沿圆；靠背 60 mm；各一整块枣红人造革，边上一圈米白嵌线（Ø3.8 mm 的真滚条，缝边处紧、
    滚条下压出一道细阴影），没有绗缝。
  - 背板：一整块冲压薄钢板，四边压出一圈凸边、中间凹，和管子同色；凸边上几颗不一样的小螺钉（槽口方向各不同，
    两颗被漆盖住，两颗拧歪，一颗没拧到底）。
  - 靠背后仰 10°（r1–r4 的旋转符号错了，靠背其实是往前倾的；这一版改正）。靠背顶（连管套）比座垫面高 0.45 m，
    按真车比例（总导演 10-25 第二次裁决：不和我们压低了的窗台对齐）；参数 BACK_RISE。
  - 轮罩上的座（SeatLBox）没有顶管：两根侧管到靠背顶封口；车尾长椅靠背贴后墙，没有上半个框。
全部 Unity 坐标。每个零件写一个 'Zone' 顶点色（R 磨亮 / 蹭亮，G 晒褪 / 漆磨穿），parts/materials 读它。

    seat_module(name, x0, x1, back_z, cushion_y, double, wall_side, on_box=False, worn=1.0, ...) -> [objects]
"""
import math

import bpy
import numpy as np
from mathutils import Matrix

import build_bus as BB
import bus_spec as B
from parts import common as C

TILT = math.radians(10)          # the back reclines 10 deg (F04)
R_T = 0.0125                     # Ø25 painted tube
BEND = 0.06                      # bend radius at the two top corners (~2.4 x the diameter)
R_SLEEVE = 0.0275                # Ø55 black leatherette sleeve (672M)
CUSH_T = 0.10                    # cushion thickness ('座垫厚，前沿圆')
BACK_D = 0.06                    # back pad thickness
W_T = 0.020                      # the side tubes run 20 mm in front of the back pad's rear face
BACK_RISE = 0.45                 # top of the back (with the sleeve) above the cushion top: the real 672M proportion
                                 # (director 10-25, second ruling: not lined up with our lowered window sill)
R_WELT = 0.0019                  # Ø3.8 mm piping
DECIMATE_PAD = 0.5               # the game mesh's cushion and back pad after a quadric collapse (cabin LOD0 budget)


def _hex_bolt(name, c, axis, r, h, m, collection):
    """a hex bolt head (6 sides, chamfered by a smaller second ring)."""
    return BB.cylinder(name, c, axis, r, h, m, collection, segs=6, bevel=min(0.0012, h * 0.3))


def _sit_spots(x0, x1, double, wall_side, places=None):
    """where people sit: one dent per place; the window place is used a little less than the aisle one."""
    n = places or (2 if double else 1)
    if n == 1:
        return [((x0 + x1) / 2, 1.0)]
    q = (x1 - x0) / (2 * n)
    xs = [x0 + q * (2 * i + 1) for i in range(n)]
    if n == 2 and wall_side > 0:
        w = [1.0, 0.8]          # aisle on the -x side
    elif n == 2 and wall_side < 0:
        w = [0.8, 1.0]
    else:
        w = [1.0] * n
    return list(zip(xs, w))


def _zone_attr(ob, fn):
    """the per-vertex 'Zone' colour read by parts/materials: R polish / rub, G sun-fade (vinyl) or paint worn through
    (painted steel), B an open seam crack (vinyl). fn(x, y, z) -> (r, g[, b]) on Unity positions (before any later
    transform of the object)."""
    me = ob.data
    ca = me.color_attributes.get('Zone') or me.color_attributes.new('Zone', 'FLOAT_COLOR', 'POINT')
    M = ob.matrix_world
    for v, c in zip(me.vertices, ca.data):
        w = M @ v.co
        v = fn(w.x, w.z, w.y)
        r, g, b = (v[0], v[1], v[2] if len(v) > 2 else 0.0)
        c.color = (min(1.0, max(0.0, r)), min(1.0, max(0.0, g)), min(1.0, max(0.0, b)), 1.0)


GUSSET_GAP = 0.002     # the slice seam check (D-40 #1): the gusset sat inside the cushion's rear-lower corner


def _gusset_clear(c, v1, v2, y_bottom, z_rear, gap=GUSSET_GAP):
    """the rear-corner gusset triangle (c, v1 forward along the run, v2 up the back tube), with the part that would be
    inside the cushion (above its bottom AND in front of its rear face) cut away, 'gap' clear of both: the hypotenuse
    gets a notch round the cushion's corner. Unity (x, y, z) points; the plate's plane is x = const."""
    yb, zr = y_bottom - gap, z_rear - gap
    d = v2 - v1
    if abs(d[1]) < 1e-9 or abs(d[2]) < 1e-9:
        return [c, v1, v2]
    ta = (yb - v1[1]) / d[1]                  # the hypotenuse reaches the cushion's bottom
    tb = (zr - v1[2]) / d[2]                  # ... and passes behind its rear face
    inside = lambda p: p[1] > yb and p[2] > zr
    if not (0.0 < ta < tb < 1.0) or inside(c) or inside(v1) or inside(v2):
        return [c, v1, v2]
    A, B_ = v1 + ta * d, v1 + tb * d
    K = np.array((c[0], yb, zr))
    return [c, v1, A, K, B_, v2]


def _plate(name, pts, x, t, collection):
    """a flat plate (a polygon in a plane x = const, Unity (y, z) from pts) t thick, chamfered edges."""
    import bmesh
    bm = bmesh.new()
    a = [bm.verts.new(BB.U2B((x - t / 2, float(p[1]), float(p[2])))) for p in pts]
    b = [bm.verts.new(BB.U2B((x + t / 2, float(p[1]), float(p[2])))) for p in pts]
    n = len(pts)
    if n == 6:         # the notched gusset (_gusset_clear: c, v1, A, K, B, v2): two convex quads sharing c-K
        for q in ((0, 1, 2, 3), (0, 3, 4, 5)):
            bm.faces.new([a[k] for k in q])
            bm.faces.new([b[k] for k in reversed(q)])
    else:
        bm.faces.new(a)
        bm.faces.new(list(reversed(b)))
    for k in range(n):
        bm.faces.new((a[k], b[k], b[(k + 1) % n], a[(k + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = BB.obj_from_bm(name, bm, ['SeatFrame'], collection)
    md = ob.modifiers.new('bevel', 'BEVEL')
    md.width, md.segments, md.limit_method = 0.0008, 1, 'ANGLE'
    C.apply_mods(ob)
    return C.finish(ob, smooth=False)


def _back_frame(cy, back_z):
    """the back's frame: origin at the bottom of the back pad's rear face, u up the back (reclined 10 deg towards -z),
    w forward out of it."""
    O = np.array((0.0, cy - 0.03, back_z))
    U = np.array((0.0, math.cos(TILT), -math.sin(TILT)))
    W = np.array((0.0, math.sin(TILT), math.cos(TILT)))
    return O, U, W


def _bp(F, x, u, w):
    O, U, W = F
    p = O + U * u + W * w
    return (x, float(p[1]), float(p[2]))


def _geom(x0, x1, back_z, cushion_y=None, double=False, wall_side=1, top_tube=True, wall_back=False, back_top=None, **_):
    """the numbers every part of a seat hangs off (also used by crack_sites and finish_bus.seat_wear)."""
    g = {}
    g['cy'] = cy = cushion_y or (B.FLOOR_Y + B.SEAT_H)
    g['cx'] = (x0 + x1) / 2
    g['F'] = F = _back_frame(cy, back_z)
    O = F[0]
    g['z0c'], g['z1c'] = back_z + 0.066, back_z + 0.466       # cushion depth 0.40, 6 mm behind it the back pad
    g['xs'] = xs = [x0 + R_T + 0.006, x1 - R_T - 0.006]       # the two side frames, under the cushion's side edges
    g['yu'] = yu = cy - CUSH_T - 0.003 - R_T                  # the run under the cushion (the 3 mm pan rests on it)
    g['u0'] = (yu - O[1] - W_T * math.sin(TILT)) / math.cos(TILT)   # where the side tube meets the run under the cushion
    y_c = (back_top or (cy + BACK_RISE)) - (R_SLEEVE if top_tube else 0.03)
    g['u_top'] = u_top = (y_c - O[1] - W_T * math.sin(TILT)) / math.cos(TILT)
    g['H'] = u_top - 0.012 if top_tube else u_top + 0.02      # back pad height (along the back)
    if wall_back:
        g['bx'] = (x0 + 0.01, x1 - 0.01)
    else:
        g['bx'] = (xs[0] + R_T + 0.003, xs[1] - R_T - 0.003)
    g['aisle'] = [0] if wall_side > 0 else [1] if wall_side < 0 else [0, 1]
    g['sleeve_x'] = (xs[0] + BEND + 0.003, xs[1] - BEND - 0.003)
    return g


def _recline(F, p):
    """an upright back-group point (x, O.y + u, O.z + w) -> where it is after the 10 deg recline."""
    O, U, W = F
    return _bp(F, p[0], p[1] - O[1], p[2] - O[2])


def _crack_sites(g, x0, x1, double=False, wall_side=1, top_tube=True, wall_back=False, places=None, **_):
    """bible §4.2 '接缝开裂（露出底布）每座 2–5 处': the places where vinyl splits on a bus seat - where a seam flexes
    or something rubs it: the cushion's front corners and front roll under each thigh, the back's bottom corners
    and the top of its welt (shoulders), the sleeve's two gathered ends. [(group, upright-or-world point)]: group
    'seat' = world, 'back' = upright back-group coordinates (reclined later)."""
    cy, O, H = g['cy'], g['F'][0], g['H']
    z0c, z1c = g['z0c'], g['z1c']
    bx0, bx1 = g['bx']
    s = [('seat', (x0 + 0.03, cy, z1c - 0.02)), ('seat', (x1 - 0.03, cy, z1c - 0.02))]
    s += [('seat', (xx, cy - 0.025, z1c + 0.004)) for xx, _w in _sit_spots(x0, x1, double, wall_side, places)]
    s += [('seat', (x0 + 0.05, cy, z0c + 0.03)), ('seat', (x1 - 0.05, cy, z0c + 0.03))]
    s += [('back', (bx0 + 0.03, O[1] + 0.06, O[2] + BACK_D)), ('back', (bx1 - 0.03, O[1] + 0.06, O[2] + BACK_D)),
          ('back', ((bx0 + bx1) / 2, O[1] + H, O[2] + BACK_D))]
    if top_tube and not wall_back:
        yc, zc = O[1] + g['u_top'], O[2] + W_T
        s += [('back', (g['sleeve_x'][0] + 0.012, yc + 0.01, zc)), ('back', (g['sleeve_x'][1] - 0.012, yc + 0.01, zc))]
    return s


def crack_sites(**kw):
    """world positions of a seat's crack candidates (finish_bus.seat_wear switches 2-5 of them on per seat)."""
    g = _geom(**kw)
    return [(_recline(g['F'], p) if grp == 'back' else p) for grp, p in _crack_sites(g, **kw)]


def crack_on(inst, n):
    """which of a seat's n crack candidates are open on this seat: 2-5 of them, the same choice in Blender and in
    finish_bus (seeded by the instance name). The bake source ('High_<type>') has them all (the atlas carries every
    candidate's shape; the per-seat vertex alpha picks)."""
    if inst.startswith('High_'):
        return list(range(n))
    import zlib
    rng = np.random.default_rng(zlib.crc32(('crack:' + inst).encode()))
    k = int(rng.integers(2, 6))
    return sorted(int(i) for i in rng.choice(n, size=min(k, n), replace=False))


def _blob(sites, r=0.025):
    def f(x, y, z):
        v = 0.0
        for p in sites:
            d2 = (x - p[0]) ** 2 + (y - p[1]) ** 2 + (z - p[2]) ** 2
            if d2 < 9 * r * r:
                v = max(v, math.exp(-d2 / (r * r)))
        return v
    return f


def seat_module(name, x0, x1, back_z, cushion_y=None, double=False, wall_side=1, on_box=False, worn=1.0,
                collection='Seats', quality='low', wall_x=None, top_tube=True, wall_back=False, places=None,
                back_top=None, cushion_split=None):
    """wall_side +1 / -1: the wall is on +x / -x (a bracket arm to wall_x); 0: no wall (rear bench, driver).
    top_tube: the 672M bent tube over the top with its black sleeve (False: the side tubes stop at the back's top).
    wall_back: the back is fixed to a wall (rear bench): no upper frame, no back board.
    cushion_split: places per cushion pad, e.g. (2, 1, 2) for the rear bench (trolleway F03: three pads, one back).
    quality 'high' = the bake source (subdivision 3, 24-sided tubes); 'low' = the game mesh (subdivision 1, 16-sided
    tubes: D-36 >= 16 within 2 m) that gets the high one's detail through the baked normal / AO."""
    g = _geom(x0, x1, back_z, cushion_y, double, wall_side, top_tube, wall_back, back_top)
    cy, cx, F = g['cy'], g['cx'], g['F']
    hi = quality == 'high'
    lv = 3 if hi else 1
    sides = 24 if hi else 16
    small = 12 if hi else 4                                   # piping (Ø3.8: the normal map carries it on the game mesh)
    spq = 10 if hi else 4
    objs = []
    O = F[0]
    z0c, z1c, xs, yu = g['z0c'], g['z1c'], g['xs'], g['yu']
    # crack candidates (bible §4.2): this seat's open ones -> 'Zone' B on the vinyl, sleeve and piping
    sites = _crack_sites(g, x0, x1, double, wall_side, top_tube, wall_back, places)
    on = crack_on(name, len(sites))
    crack_seat = _blob([p for i, (grp, p) in enumerate(sites) if i in on and grp == 'seat'])
    crack_back = _blob([p for i, (grp, p) in enumerate(sites) if i in on and grp == 'back'])
    if wall_back and x1 - x0 > 1.2:
        xs_extra = [cx]                                       # the long bench gets a third (middle) leg frame
    else:
        xs_extra = []
    aisle = g['aisle']
    if wall_x is None:
        wall_x = x1 if wall_side > 0 else x0

    # ---------------------------------------------------------------- cushion + pan
    if cushion_split:
        n_all = float(sum(cushion_split))
        xa = x0 + 0.002
        for k, n in enumerate(cushion_split):
            xb = xa + (x1 - x0 - 0.004) * n / n_all
            objs += _cushion(name + '_%d' % k if k else name, xa + (0.002 if k else 0.0), xb - (0.002 if k < len(cushion_split) - 1 else 0.0),
                             (xa + xb) / 2, cy, z0c, z1c, n > 1, worn, 0, lv, small, collection, hi, n, crack_seat)
            xa = xb
    else:
        objs += _cushion(name, x0 + 0.002, x1 - 0.002, cx, cy, z0c, z1c, double, worn, wall_side, lv, small, collection, hi,
                         places, crack_seat)
    pt = yu + R_T
    objs.append(BB.box(name + '_Pan', (x0 + 0.004, pt, z0c + 0.004), (x1 - 0.004, pt + 0.003, z1c - 0.010), 'SeatFrame',
                       collection, bevel=0.0012, segs=2))
    objs.append(BB.box(name + '_PanLip', (x0 + 0.004, pt - 0.012, z1c - 0.013), (x1 - 0.004, pt + 0.003, z1c - 0.010),
                       'SeatFrame', collection, bevel=0.001, segs=1))
    # the tray's pressed side strips: the cushion sits in them, its bottom 25 mm hidden (F01, F04: the painted strip
    # along the foot of the cushion's side, ending at the rear corner's gusset)
    for sx, xa_ in (('L', x0 - 0.0005), ('R', x1 - 0.0015)):
        objs.append(BB.box(name + '_PanSide' + sx, (xa_, pt - 0.004, z0c + 0.004), (xa_ + 0.002, cy - CUSH_T + 0.025, z1c - 0.016),
                           'SeatFrame', collection, bevel=0.0008, segs=1))

    # ---------------------------------------------------------------- the bent tube
    u0, u_top, H = g['u0'], g['u_top'], g['H']
    zf, zr = z1c - 0.05, z0c + 0.045                          # front leg (leans back going down, F04), rear leg
    yfl = B.FLOOR_Y + 0.030                                   # the floor run, on its foot tabs
    Rr = [_bp(F, x, u0, W_T) for x in xs]                     # rear corners: the run bends up into the back
    Tt = [_bp(F, x, u_top, W_T) for x in xs]                  # top corners

    def lower(x, rear_pt):
        """the side frame's lower loop from the rear leg's top (inside the run) round to the run's rear corner."""
        if on_box:
            return [(x, yu, zf + 0.03), rear_pt], [0.04]
        return [(x, yu, zr), (x, yfl, zr - 0.01), (x, yfl, zf - 0.03), (x, yu, zf), rear_pt], [0.035, 0.035, 0.035, 0.04]

    if top_tube and not wall_back:
        p0, r0 = lower(xs[0], Rr[0])
        p1, r1 = lower(xs[1], Rr[1])
        path = p0 + [Tt[0], Tt[1]] + list(reversed(p1))
        radii = r0 + [BEND, BEND] + list(reversed(r1))
        tubes = [(name + '_Frame', path, radii)]
    else:
        tubes = []
        for i, x in enumerate(xs):
            p, r = lower(x, Rr[i])
            if not wall_back:                                 # side tube up to the back's top, capped
                p, r = p + [Tt[i]], r
            else:
                p, r = p[:-1] + [(x, yu, z0c + 0.01)], r[:-1]
            tubes.append((name + '_Frame%d' % i, p, r))
    for x in xs_extra:
        p, r = lower(x, Rr[0])
        tubes.append((name + '_FrameMid', p[:-1] + [(x, yu, z0c + 0.01)], r[:-1]))
    frame_objs = []
    for tn, p, r in tubes:
        rr = r[:len(p) - 2]
        # the two top bends are 0.5-0.7 m from the eye behind: 8 segments per 90 deg on the game mesh (silhouette error
        # < 1 px at 20 px/deg), the bends down by the floor 4
        sq = [spq if rad != BEND else max(spq, 8) for rad in rr]
        frame_objs.append(C.sweep(tn, p, R_T, 'SeatFrame', collection, sides=sides, bend=rr, seg_per_90=sq))
    # cross tubes under the cushion (front and rear), 20 mm
    for tag, zz in (('F', zf - 0.035), ('R', z0c + 0.035)):
        frame_objs.append(C.sweep(name + '_Cross' + tag, [(xs[0], yu, zz), (xs[1], yu, zz)], 0.010, 'SeatFrame', collection,
                                  sides=12 if hi else 8))
    # frame wear (D-40 #3: hands, feet): the paint is worn through on the exposed aisle top corner (the hand that steadies
    # you walking down the aisle), shoe scuffs on the front legs and the floor run, calves rub the run's front corner
    hand = [Tt[i] for i in aisle] if top_tube and not wall_back else []

    def zone_f(x, y, z):
        g = 0.0
        for t in hand:
            g = max(g, math.exp(-(((x - t[0]) ** 2 + (y - t[1]) ** 2 + (z - t[2]) ** 2) / 0.045 ** 2)))
        r = 0.0
        if y < B.FLOOR_Y + 0.16:
            r = max(r, 0.7 * math.exp(-((z - zf - 0.02) / 0.06) ** 2) + 0.35)
            g = max(g, 0.35 * math.exp(-((z - zf - 0.02) / 0.04) ** 2) * math.exp(-((y - B.FLOOR_Y - 0.06) / 0.05) ** 2))
        r = max(r, 0.6 * math.exp(-((y - yu) / 0.03) ** 2 - ((z - zf) / 0.05) ** 2))
        return r, g
    # the rear corner's pressed gusset on the outer face of each side frame (F01: the plate where the cushion strip,
    # the run and the back tube meet), and two small domed screws up each back tube holding the back pad (F01, F04)
    if not wall_back:
        U_, W_ = F[1], F[2]
        for i, x in enumerate(xs):
            out = -1.0 if i == 0 else 1.0
            xo = x + out * (R_T - 0.003)
            c0 = np.array(Rr[i])
            v1 = c0 + np.array((0.0, 0.004, 0.10))
            v2 = c0 + U_ * 0.10 + np.array((0.0, 0.0, 0.004))
            v3 = c0 + np.array((0.0, 0.004, 0.0)) + U_ * 0.004
            frame_objs.append(_plate(name + '_Gusset%d' % i, _gusset_clear(v3, v1, v2, cy - CUSH_T, z0c), xo, 0.003, collection))
            for k, uu in enumerate((0.35 * H, 0.75 * H)):
                if uu > 0.04:
                    pc = _bp(F, x + out * (R_T + 0.0006), uu, W_T)
                    frame_objs.append(BB.cylinder(name + '_TubeScrew%d_%d' % (i, k), pc, 'x', 0.0035, 0.0018, 'SeatFrame',
                                                  collection, segs=12 if hi else 8, bevel=0.0007 if hi else 0.0))
    for o in frame_objs:
        _zone_attr(o, zone_f)
    objs += frame_objs

    # ---------------------------------------------------------------- feet, box brackets, wall bracket
    if not on_box:
        for x in xs + xs_extra:
            for tag, zz in (('F', zf - 0.075), ('R', zr + 0.03)):
                objs.append(BB.box(name + '_Foot%s%.2f' % (tag, x), (x - 0.022, B.FLOOR_Y, zz - 0.026),
                                   (x + 0.022, B.FLOOR_Y + 0.005, zz + 0.026), 'SeatFrame', collection, bevel=0.0015, segs=2))
                objs.append(BB.box(name + '_FootWeb%s%.2f' % (tag, x), (x - 0.0025, B.FLOOR_Y + 0.005, zz - 0.020),
                                   (x + 0.0025, yfl, zz + 0.020), 'SeatFrame', collection, bevel=0.0008, segs=1))
                for dx in (-0.014, 0.014):
                    objs.append(_hex_bolt(name + '_FootBolt%s%.2f%+.3f' % (tag, x, dx), (x + dx, B.FLOOR_Y + 0.007, zz), 'y',
                                          0.0050, 0.004, 'Alu', collection))
    else:
        for x in xs:
            for zz in (z0c + 0.06, z1c - 0.08):
                objs.append(BB.box(name + '_BoxBracket%.2f_%.2f' % (x, zz), (x - 0.02, yu - 0.06, zz - 0.02),
                                   (x + 0.02, yu - R_T + 0.002, zz + 0.02), 'SeatFrame', collection, bevel=0.003, segs=2))
    if wall_side != 0:
        xw = wall_x - wall_side * 0.006
        xi = xs[1] if wall_side > 0 else xs[0]
        zm = (z0c + z1c) / 2
        objs.append(BB.box(name + '_WallPlate', (xw - 0.006, yu - 0.05, zm - 0.07), (xw + 0.006, yu + 0.05, zm + 0.07),
                           'SeatFrame', collection, bevel=0.004, segs=2))
        for dz in (-0.045, 0.045):
            objs.append(_hex_bolt(name + '_WallBolt%+.2f' % dz, (xw - wall_side * 0.008, yu, zm + dz), 'x', 0.006, 0.005,
                                  'Alu', collection))
        objs.append(C.sweep(name + '_WallArm', [(xi, yu, zm), (xw - wall_side * 0.008, yu, zm)], 0.010, 'SeatFrame',
                            collection, sides=12 if hi else 8))

    # ---------------------------------------------------------------- the back (built upright, then reclined)
    bx0, bx1 = g['bx']
    back = _back_pad(name, bx0, bx1, O, H, cy, worn, wall_side, lv, small, collection, hi, crack_back)
    if not wall_back:
        back += _back_board(name, bx0, bx1, O, H, cx, cy, double, hi, collection)
    if top_tube and not wall_back:
        back += _sleeve(name, xs, O, u_top, aisle, hi, collection, crack_back)
    pb = BB.U2B((0.0, O[1], O[2]))
    C.transform(back, Matrix.Translation(pb) @ Matrix.Rotation(TILT, 4, 'X') @ Matrix.Translation(-pb))
    objs += back
    return objs


def _cushion(name, x0, x1, cx, cy, z0c, z1c, double, worn, wall_side, lv, small, collection, hi=False, places=None,
             crack=None):
    """a 100 mm cushion, one piece of leatherette (672M): pulled TIGHT at the piped top seam (r4 #1), the top soft with
    sat-in dents, the boxing vertical with a slight bulge, the front rounded and rolling under at the bottom."""
    objs = []
    lo = (x0, cy - CUSH_T, z0c)
    hi_ = (x1, cy, z1c)
    hx, hy, hz = (hi_[0] - lo[0]) / 2, (hi_[1] - lo[1]) / 2, (hi_[2] - lo[2]) / 2
    ccx, ccz = (lo[0] + hi_[0]) / 2, (lo[2] + hi_[2]) / 2
    nmx = max(4, int((x1 - x0) / (0.06 if hi else 0.11)))
    X = np.concatenate([[-hx, -hx + 0.004, -hx + 0.02], np.linspace(-hx + 0.06, hx - 0.06, nmx), [hx - 0.02, hx - 0.004, hx]])
    Y = np.array([-hy, -hy + 0.026, -0.01, hy - 0.022, hy - 0.006, hy]) if hi else np.array([-hy, -hy + 0.026, hy - 0.022, hy - 0.006, hy])
    Z = np.concatenate([[-hz, -hz + 0.016], np.linspace(-hz + 0.06, hz - 0.12, 6 if hi else 2), [hz - 0.06, hz - 0.02, hz - 0.004, hz]])
    spots = _sit_spots(x0, x1, double, wall_side, places)
    jt = len(Y) - 2                                           # the boxing line just under the seam

    def deform(face, i, j, k, x, y, z, half):
        ux, uz, uy = x / half[0], z / half[2], y / half[1]
        fx, fz, fy = 1 - min(1, ux * ux), 1 - min(1, uz * uz), 1 - min(1, uy * uy)
        if 'y+' in face:
            y += 0.010 * fx * fz                                         # soft crown
            for xs_, w in spots:                                          # sat-in dents (behind the middle)
                d = math.exp(-((x + ccx - xs_) / 0.16) ** 2 - ((z + 0.04) / 0.15) ** 2)
                y -= 0.016 * worn * w * d
        if j == jt and ('x+' in face or 'x-' in face or 'z+' in face):  # the crease under the welt
            if 'x+' in face or 'x-' in face:
                x -= math.copysign(0.0025, x)
            if 'z+' in face:
                z -= 0.0025
        if 'z+' in face and 0 < j < jt:
            z += 0.008 * fy * fx                                         # the front is round ('前沿圆')
        if 'z+' in face or k >= len(Z) - 3:                               # ... and rolls under at the bottom
            t = min(max((y + half[1]) / (2 * half[1]), 0.0), 1.0)
            wz = {len(Z) - 1: 1.0, len(Z) - 2: 0.6, len(Z) - 3: 0.25}[k]
            z -= 0.026 * (1 - t) ** 2 * wz
        if ('x+' in face or 'x-' in face) and 0 < j < jt:
            x += math.copysign(0.0035 * fz, x)                           # the boxing bulges a little, stays vertical
        return x, y, z

    cu = C.cage_pad(name + '_Cushion', lo, hi_, 'Vinyl', collection, lines=(X, Y, Z), deform=deform, levels=lv,
                    round_plan=('xz', 0.04))
    objs.append(cu)
    win_x = hi_[0] if wall_side > 0 else lo[0] if wall_side < 0 else None

    def zone(x, y, z):
        pol = 0.0
        for xs_, w in spots:
            pol = max(pol, w * math.exp(-((x - xs_) / 0.15) ** 2 - ((z - ccz + 0.03) / 0.15) ** 2))
        pol = max(pol, 0.7 * math.exp(-((z - z1c) / 0.03) ** 2) * (1 if y > cy - 0.03 else 0.4))   # thighs over the front
        sun = 0.0 if win_x is None else 0.6 * math.exp(-((x - win_x) / 0.06) ** 2) * (1 if y > cy - 0.02 else 0.3)
        return pol * worn, sun, (crack(x, y, z) if crack else 0.0)
    _zone_attr(cu, zone)
    # the welt round the two sides and the front, in the tight seam: probes on the plan outline at the top's height
    outline = C.fillet_path([(lo[0], cy, z0c + 0.012), (lo[0], cy, hi_[2]), (hi_[0], cy, hi_[2]), (hi_[0], cy, z0c + 0.012)],
                            0.04, 10)
    outline = C.resample(outline, 0.010 if hi else 0.04)
    wp = C.sweep(name + '_CushionPiping', C.welt(cu, outline, R_WELT), R_WELT, 'Piping', collection, sides=small)
    _zone_attr(wp, zone)
    objs.append(wp)
    if not hi:
        C.decimate(cu, DECIMATE_PAD)        # the game mesh (cabin budget): the bake carries the fine shape
    return objs


def _back_pad(name, bx0, bx1, O, H, cy, worn, wall_side, lv, small, collection, hi, crack=None):
    """the back pad, upright in the back's frame (x, y = O.y + u, z = O.z + w): one piece of leatherette, tight at the
    piped front seam, the front a little full, plan corners round; the cream welt all round the front."""
    back = []
    lo = (bx0, O[1], O[2])
    hi_ = (bx1, O[1] + H, O[2] + BACK_D)
    hxb, hyb, hzb = (bx1 - bx0) / 2, H / 2, BACK_D / 2
    nmx = max(3, int((bx1 - bx0) / (0.06 if hi else 0.12)))
    nmy = max(2, int(H / (0.06 if hi else 0.12)))
    e = [0.0, 0.004, 0.022]
    Xb = np.array(sorted(set(np.round([-hxb + v for v in e] + list(np.linspace(-hxb + 0.06, hxb - 0.06, nmx)) + [hxb - v for v in e], 6))))
    Yb = np.array(sorted(set(np.round([-hyb + v for v in e] + list(np.linspace(-hyb + 0.06, hyb - 0.06, nmy)) + [hyb - v for v in e], 6))))
    Zb = np.array([-hzb, -hzb + 0.012, hzb - 0.016, hzb - 0.004, hzb])

    def deform_b(face, i, j, k, x, y, z, half):
        fx = 1 - min(1, (x / half[0]) ** 2)
        fy = 1 - min(1, (y / half[1]) ** 2)
        if 'z+' in face or k == len(Zb) - 2:
            z += 0.007 * fx * fy                                       # the front a little full (the seam goes with it)
        if k == len(Zb) - 2:                                           # the crease under the welt
            if 'x+' in face or 'x-' in face:
                x -= math.copysign(0.0025, x)
            if 'y+' in face or 'y-' in face:
                y -= math.copysign(0.0025, y)
        if ('x+' in face or 'x-' in face) and 0 < k < len(Zb) - 2:
            x += math.copysign(0.002 * fy, x)
        return x, y, z

    bk = C.cage_pad(name + '_Back', lo, hi_, 'Vinyl', collection, lines=(Xb, Yb, Zb), deform=deform_b, levels=lv,
                    round_plan=('xy', 0.03))
    back.append(bk)
    wxb = bx1 if wall_side > 0 else bx0 if wall_side < 0 else None

    def zone_b(x, y, z):
        pol = 0.5 * math.exp(-((y - (O[1] + H * 0.82)) / 0.06) ** 2) + 0.3 * math.exp(-((y - (O[1] + H * 0.35)) / 0.08) ** 2)
        sun = 0.0 if wxb is None else math.exp(-((x - wxb) / 0.08) ** 2) * math.exp(-((y - O[1] - H) / 0.08) ** 2)
        return pol * worn, sun, (crack(x, y, z) if crack else 0.0)
    _zone_attr(bk, zone_b)
    # the welt all round the front panel (probes on the box's front edge, plan corners round like the pad)
    yb0, yb1 = O[1], O[1] + H
    zf = O[2] + BACK_D
    rr = [(bx0, yb0, zf), (bx1, yb0, zf), (bx1, yb1, zf), (bx0, yb1, zf)]
    mid = ((bx0 + bx1) / 2, yb0, zf)
    ol = C.fillet_path([mid] + rr[1:] + [rr[0], mid], 0.03, 10)[:-1]
    ol = C.resample(ol + [ol[0]], 0.010 if hi else 0.04)[:-1]
    bp = C.sweep(name + '_BackPiping', C.welt(bk, ol, R_WELT, closed=True), R_WELT, 'Piping', collection, sides=small,
                 closed=True)
    _zone_attr(bp, zone_b)
    back.append(bp)
    if not hi:
        C.decimate(bk, DECIMATE_PAD)
    return back


def _back_board(name, bx0, bx1, O, H, cx, cy, double, hi, collection):
    """the 672M back board: one pressed steel sheet (2.5 mm) on the pad's rear, a raised rim on all four edges and the
    middle recessed, painted like the tube; a few small slotted screws on the rim, not all alike."""
    back = []
    xa, xb = bx0 + 0.002, bx1 - 0.002
    ya, yb = O[1] + 0.012, O[1] + H - 0.004
    za, zb = O[2] - 0.0025, O[2]
    hx, hy = (xb - xa) / 2, (yb - ya) / 2
    cxb, cyb = (xa + xb) / 2, (ya + yb) / 2
    RB = 0.025
    RIM_H, RIM_IN = 0.0045, 0.024                         # the rim stands 4.5 mm proud; flat 6-14 mm in, gone by 24 mm

    def rim(d):
        if d < 0.006:
            return RIM_H * (0.45 + 0.55 * (d / 0.006))
        if d < 0.014:
            return RIM_H
        if d < RIM_IN:
            t = (d - 0.014) / (RIM_IN - 0.014)
            return RIM_H * (1 - t * t * (3 - 2 * t))
        return 0.0

    def dist(x, y):
        qx, qy = abs(x) - (hx - RB), abs(y) - (hy - RB)
        if qx > 0 and qy > 0:
            return RB - math.hypot(qx, qy)
        return min(hx - abs(x), hy - abs(y))

    def side_lines(h, step):
        e = [0.0, 0.003, 0.006, 0.010, 0.014, 0.019, RIM_IN] if hi else [0.0, 0.006, 0.014, RIM_IN]
        n_mid = max(2, int((2 * h - 2 * RIM_IN) / step))
        mid = np.linspace(-h + RIM_IN, h - RIM_IN, n_mid + 1)[1:-1]
        return np.array(sorted(set(np.round([-h + v for v in e] + list(mid) + [h - v for v in e], 6))))
    Xd, Yd = side_lines(hx, 0.035 if hi else 0.12), side_lines(hy, 0.035 if hi else 0.12)
    Zd = np.array([-0.00125, 0.00125])
    bd = C.cage_pad(name + '_BackBoard', (xa, ya, za), (xb, yb, zb), 'SeatFrame', collection, lines=(Xd, Yd, Zd),
                    deform=lambda f, i, j, k, x, y, z, h: (x, y, z - rim(dist(x, y))), levels=1 if hi else 0,
                    round_plan=('xy', RB))
    # knee scuffs from the row behind (D-40 #3: wear from what touches it): at seated knee height, one pair per place
    kn = [cx] if not double else [cx - (bx1 - bx0) / 4, cx + (bx1 - bx0) / 4]
    _zone_attr(bd, lambda x, y, z: (max(math.exp(-((abs(x - k_) - 0.09) / 0.06) ** 2 - ((y - (cy + 0.13)) / 0.07) ** 2)
                                        for k_ in kn), 0.0))
    back.append(bd)
    # screws on the rim: along the top, one per side, two at the bottom
    d = 0.010
    n_top = 4 if double else 3
    pts = [(x, yb - d) for x in np.linspace(xa + 0.05, xb - 0.05, n_top)]
    pts += [(xa + d, cyb), (xb - d, cyb)]
    pts += [(x, ya + d) for x in (xa + 0.06, xb - 0.06)]
    rng = np.random.default_rng(672 + (17 if double else 0))   # the same for every seat of a type (shared atlas)
    for k, (xx, yy) in enumerate(pts):
        painted, crooked, proud = k in (1, n_top + 1), k in (0, n_top + 2), k == n_top
        zf = za - RIM_H - (0.0007 if proud else 0.0)            # the rim's rear face
        sc = BB.cylinder(name + '_Screw%d' % k, (xx, yy, zf - 0.0008), 'z', 0.0042, 0.0022,
                         'SeatFrame' if painted else 'Alu', collection, segs=16 if hi else 8, bevel=0.0008 if hi else 0.0)
        piv = BB.U2B((xx, yy, zf))
        if hi and not painted:      # the slot, 0.7 mm into the head (the normal map carries it on the game mesh)
            sl = BB.box(name + '_Slot%d' % k, (xx - 0.0046, yy - 0.0006, zf - 0.0035), (xx + 0.0046, yy + 0.0006, zf - 0.0012),
                        'Seal', collection)
            ang = float(rng.uniform(0, math.pi))
            sl.matrix_world = Matrix.Translation(piv) @ Matrix.Rotation(ang, 4, 'Y') @ Matrix.Translation(-piv)
            BB.boolean(sc, sl)
            bpy.data.objects.remove(sl, do_unlink=True)
        if crooked:
            ax = Matrix.Rotation(float(rng.uniform(0, 2 * math.pi)), 3, 'Y') @ BB.U2B((1.0, 0.0, 0.0))
            sc.matrix_world = (Matrix.Translation(piv) @ Matrix.Rotation(math.radians(float(rng.uniform(4, 7))), 4, ax)
                               @ Matrix.Translation(-piv) @ sc.matrix_world)
        back.append(sc)
    return back


def _sleeve(name, xs, O, u_top, aisle, hi, collection, crack=None):
    """672M: the horizontal run of the top tube in a black leatherette sleeve (Ø55 over foam), one seam underneath at the
    rear, both ends drawn in round the tube; the bends stay bare painted tube."""
    out = []
    yc, zc = O[1] + u_top, O[2] + W_T
    xa, xb = xs[0] + BEND + 0.003, xs[1] - BEND - 0.003
    L = xb - xa
    n_mid = max(4, int(L / (0.02 if hi else 0.06)))
    end = [(0.0, R_T + 0.0015), (0.0015, 0.020), (0.005, 0.0255), (0.010, R_SLEEVE - 0.0003), (0.014, R_SLEEVE - 0.0016),
           (0.018, R_SLEEVE)]                                 # the drawn-in end, then the gather groove 14 mm in
    prof = [(xa + t, r) for t, r in end]
    rng = np.random.default_rng(55)
    for t in np.linspace(0.024, L - 0.024, n_mid):
        prof.append((xa + t, R_SLEEVE + float(rng.normal(0, 0.0003))))   # foam under vinyl is never a perfect cylinder
    prof += [(xb - t, r) for t, r in reversed(end)]
    sl = C.lathe_x(name + '_Sleeve', prof, yc, zc, 'Sleeve', collection, sides=32 if hi else 16)
    xa_ = [xs[i] for i in aisle]

    def zone_s(x, y, z):
        top = 1.0 if y > yc else 0.35
        r = 0.25 + max([0.75 * math.exp(-((x - xx) / 0.16) ** 2) for xx in xa_] + [0.0])
        return r * top, 0.0, (crack(x, y, z) if crack else 0.0)
    _zone_attr(sl, zone_s)
    out.append(sl)
    a = math.radians(225)                                     # the seam: underneath, at the rear (w < 0, u < 0)
    sy, sz = yc + (R_SLEEVE - 0.0004) * math.sin(a), zc + (R_SLEEVE - 0.0004) * math.cos(a)
    out.append(C.sweep(name + '_SleeveSeam', [(xa + 0.016, sy, sz), (xb - 0.016, sy, sz)], 0.0009, 'Sleeve', collection,
                       sides=6))
    return out
