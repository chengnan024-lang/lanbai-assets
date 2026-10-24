# -*- coding: utf-8 -*-
"""造车（Blender 5.0.1，bpy 模块）。所有尺寸来自 bus_spec.py；坐标写 Unity 车局部，U2B 换成 Blender。

用法：
    ~/bpy/bin/python Bus/Source/build_bus.py --out /tmp/bus/bus.blend [--fbx Bus/Models/Bus.fbx]
也可以被别的脚本 import 后调用 build()（视窗检查、参考渲染）。

车身外壳 = 一圈一圈的水平截面（每一层是圆角矩形：半宽 W(y)、前脸 Zf(y)、后脸 Zr(y)），层与层之间连四边形；
窗、门、目的地牌的开口就是把那几格四边形删掉——所以开口的边正好落在截面的站点上，玻璃 = 删掉的那几格往里挪 15 mm。
"""
import argparse
import math
import os
import sys

import bpy
import bmesh  # noqa: E402  (bmesh only imports after bpy)
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bus_spec as B  # noqa: E402

GLASS_INSET = 0.015
SHELL_T = 0.035


def U2B(p):
    return Vector((p[0], p[2], p[1]))


def srgb2lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ------------------------------------------------------------------------------------------------ materials
MATS = {}
# 名字: (反照率 sRGB, 光滑度, 金属)；圣经 §4.2 / §4.9。Unity 里由 Lanbai/Cabin、Lanbai/BusGlass 接手，这里只为白模和取景。
MAT_TABLE = {
    'Ext_Indigo': ('#34506E', 0.50, 0), 'Ext_Cream': ('#D8D2C2', 0.55, 0), 'Ext_Silver': ('#BFC2C4', 0.70, 1),
    'Ext_Black': ('#1E1F20', 0.40, 0), 'Tyre': ('#2A2A2A', 0.55, 0), 'Rim': ('#D8D2C2', 0.45, 0),
    'Chrome': ('#CFD1D3', 0.85, 1), 'Lamp_Head': ('#FFF4E0', 0.9, 0), 'Lamp_Tail': ('#8A1A1E', 0.8, 0),
    'Lamp_Amber': ('#E3D69B', 0.8, 0),          # D-28e: pale yellow, an unlit lens (not orange)
    'Int_Enamel': ('#D9D4C5', 0.45, 0), 'Int_Ceiling': ('#E2DDCF', 0.25, 0), 'Seal': ('#2B2B2B', 0.30, 0),
    'Vinyl': ('#5A2126', 0.45, 0), 'SeatFrame': ('#3C3E3D', 0.35, 0), 'Floor': ('#323634', 0.22, 0),
    'Alu': ('#B8BBBD', 0.45, 1), 'SafetyYellow': ('#C9A227', 0.40, 0), 'Steel': ('#C0C3C4', 0.55, 1),
    'TubeDiffuser': ('#D8DBD6', 0.60, 0), 'Dash': ('#353637', 0.30, 0), 'Bakelite': ('#2E2E2E', 0.45, 0),
    'RadioLeather': ('#4A2E1F', 0.45, 0), 'RadioGrille': ('#B8BBBD', 0.55, 1), 'RadioDial': ('#E8DFC8', 0.5, 0),
    'Curtain': ('#A9BCCB', 0.18, 0), 'Linen': ('#262626', 0.10, 0), 'Glass': ('#E9EFEA', 0.97, 0),
}


def mat(name):
    if name in MATS:
        return MATS[name]
    hexc, smooth, metal = MAT_TABLE[name]
    m = bpy.data.materials.new('M_Bus_' + name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*srgb2lin(hexc), 1.0)
    bs.inputs['Roughness'].default_value = 1.0 - smooth
    bs.inputs['Metallic'].default_value = float(metal)
    if name == 'Glass':
        bs.inputs['Transmission Weight'].default_value = 1.0
        bs.inputs['IOR'].default_value = 1.0          # 薄玻璃：不折射，只有 F0 0.04 量级的反射
        bs.inputs['Roughness'].default_value = 0.03
    m.diffuse_color = (*srgb2lin(hexc), 1.0)
    MATS[name] = m
    return m


# ------------------------------------------------------------------------------------------------ helpers
COLL = {}


def coll(name):
    if name not in COLL:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLL[name] = c
    return COLL[name]


def obj_from_bm(name, bm, mats, collection='Bus'):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m_ in mats:
        me.materials.append(mat(m_))
    ob = bpy.data.objects.new(name, me)
    coll(collection).objects.link(ob)
    return ob


def box(name, lo, hi, m, collection='Bus', bevel=0.0, segs=2):
    """axis-aligned box in Unity coordinates."""
    bm = bmesh.new()
    lo_b, hi_b = U2B(lo), U2B(hi)
    c = (lo_b + hi_b) / 2
    s = hi_b - lo_b
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((c.x + v.co.x * abs(s.x), c.y + v.co.y * abs(s.y), c.z + v.co.z * abs(s.z)))
    ob = obj_from_bm(name, bm, [m], collection)
    if bevel > 0:
        md = ob.modifiers.new('bevel', 'BEVEL')
        md.width = bevel
        md.segments = segs
        md.limit_method = 'NONE'
    return ob


def tube(name, pts, r, m, collection='Bus', sides=12, closed=False):
    """a round bar along a polyline of Unity points."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = max(1, sides // 4 - 1)
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        q = U2B(p)
        sp.points[i].co = (q.x, q.y, q.z, 1.0)
    sp.use_cyclic_u = closed
    ob = bpy.data.objects.new(name, cu)
    coll(collection).objects.link(ob)
    cu.materials.append(mat(m))
    return ob


def cylinder(name, c, axis, r, length, m, collection='Bus', segs=32, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r, depth=length)
    # created along Blender z; orient to the Unity axis
    ax = {'x': Vector((1, 0, 0)), 'y': Vector((0, 0, 1)), 'z': Vector((0, 1, 0))}[axis] if isinstance(axis, str) else U2B(axis).normalized()
    rot = Vector((0, 0, 1)).rotation_difference(ax).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(U2B(c)) @ rot, verts=bm.verts)
    ob = obj_from_bm(name, bm, [m], collection)
    if bevel > 0:
        md = ob.modifiers.new('bevel', 'BEVEL')
        md.width = bevel
        md.segments = 2
        md.limit_method = 'ANGLE'
    return ob


def apply_mods(ob):
    bpy.context.view_layer.objects.active = ob
    for md in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)


def boolean(ob, cutter, op='DIFFERENCE'):
    md = ob.modifiers.new('bool', 'BOOLEAN')
    md.operation = op
    md.object = cutter
    md.solver = 'EXACT'
    apply_mods(ob)


def smooth_by_angle(ob, deg=35):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(deg))
    except Exception:
        bpy.ops.object.shade_smooth()


# ------------------------------------------------------------------------------------------------ shell profile
def W_of(y):
    """outer half-width (from the centre line XC) at height y: bottom rounding, side wall with tumblehome,
    then the PAZ shoulder (a full superellipse quadrant, D-28a: 'make the shoulders full') up to the flat crown."""
    yb = B.Y_BOT + 0.08
    if y <= yb:
        t = (yb - y) / 0.08
        return B.W_HALF - 0.04 * t * t
    if y <= B.Y_SIDE_ROOF:
        return B.W_HALF - (B.W_HALF - B.W_TOPSIDE) * max(0.0, (y - B.Y_BELT)) / (B.Y_SIDE_ROOF - B.Y_BELT)
    v = min(1.0, (y - B.Y_SIDE_ROOF) / (B.Y_TOP - B.Y_SIDE_ROOF))
    return B.CROWN_HALF + (B.W_TOPSIDE - B.CROWN_HALF) * max(0.0, 1.0 - v ** B.SHOULDER_N) ** (1.0 / B.SHOULDER_N)


def Zf_of(y):
    yb = B.Y_BOT + 0.08
    if y <= yb:
        t = (yb - y) / 0.08
        return B.Z_FRONT - 0.05 * t * t
    if y <= B.Y_FRONT_ROOF:
        return B.Z_FRONT
    t = min(1.0, (y - B.Y_FRONT_ROOF) / (B.Y_TOP - B.Y_FRONT_ROOF))
    return B.Z_FRONT - B.FRONT_DOME * (1.0 - max(0.0, 1.0 - t ** B.SHOULDER_N) ** (1.0 / B.SHOULDER_N))


def Zr_of(y):
    return B.Z_REAR + (B.Z_FRONT - Zf_of(y))


def front_bulge(x_rel, xs, y):
    """D-28b: the PAZ front is round in plan (the face curves back into both corners) and the lower half swells
    forward a little. 0 at the corner tangents, so the corner arcs join smoothly."""
    if xs <= 1e-6:
        return 0.0
    k = max(0.0, 1.0 - (x_rel / xs) ** 2)
    low = 1.0 - min(1.0, max(0.0, (y - 1.05) / 0.20))
    dome = min(1.0, max(0.0, (Zf_of(y) - (B.Z_FRONT - B.FRONT_DOME)) / B.FRONT_DOME))
    return (B.FRONT_BULGE + B.FRONT_SWELL * low) * k * dome


def shell_point(col, y):
    """a point of the outer skin: col = (segment, belt-level parameter) as in build_shell."""
    seg, v = col
    XC = B.XC
    W, Zf, Zr = W_of(y), Zf_of(y), Zr_of(y)
    Rc = min(B.RC, W * 0.6)
    zs0, zs1 = Zr + Rc, Zf - Rc
    xs = W - Rc
    xs_belt = B.W_HALF - B.RC
    if seg == 'R':
        return (XC + W, y, zs0 + (v - SIDE0) / (SIDE1 - SIDE0) * (zs1 - zs0))
    if seg == 'L':
        return (XC - W, y, zs0 + (v - SIDE0) / (SIDE1 - SIDE0) * (zs1 - zs0))
    if seg == 'F':
        xr = (v - XC) / xs_belt * xs
        return (XC + xr, y, Zf + front_bulge(xr, xs, y))
    if seg == 'Bk':
        return (XC + (v - XC) / xs_belt * xs, y, Zr)
    a = v * math.pi / 2
    if seg == 'RF':
        return (XC + xs + Rc * math.cos(a), y, zs1 + Rc * math.sin(a))
    if seg == 'LF':
        return (XC - xs - Rc * math.sin(a), y, zs1 + Rc * math.cos(a))
    if seg == 'LR':
        return (XC - xs - Rc * math.cos(a), y, zs0 - Rc * math.sin(a))
    if seg == 'RR':
        return (XC + xs + Rc * math.sin(a), y, zs0 - Rc * math.cos(a))


# a continuous perimeter parameter u (arc length at the belt), so overlays (rounded window corners, gaskets, the
# cowl) can be sampled on the same surface as the skin: R (rear->front), RF, F (right->left), LF, L, LR, Bk, RR
def _segs():
    xs = B.W_HALF - B.RC
    q = math.pi / 2 * B.RC
    return [('R', SIDE0, SIDE1, SIDE1 - SIDE0), ('RF', 0.0, 1.0, q), ('F', B.XC + xs, B.XC - xs, 2 * xs), ('LF', 0.0, 1.0, q),
            ('L', SIDE1, SIDE0, SIDE1 - SIDE0), ('LR', 0.0, 1.0, q), ('Bk', B.XC - xs, B.XC + xs, 2 * xs), ('RR', 0.0, 1.0, q)]


def perim(u):
    for seg, a, b, L in _segs():
        if u <= L + 1e-9:
            return (seg, a + (b - a) * max(0.0, u) / L)
        u -= L
    seg, a, b, L = _segs()[-1]
    return (seg, b)


def perim_u(seg, v):
    u = 0.0
    for s_, a, b, L in _segs():
        if s_ == seg:
            return u + (v - a) / (b - a) * L
        u += L
    raise KeyError(seg)


def surf(u, y):
    return shell_point(perim(u), y)


def surf_n(u, y, d=0.004):
    p0, p1 = np.array(surf(u - d, y)), np.array(surf(u + d, y))
    q0, q1 = np.array(surf(u, y - d)), np.array(surf(u, y + d))
    n = np.cross(q1 - q0, p1 - p0)           # unity left-handed: (dy x du) points out for u running counter-clockwise
    n = n / (np.linalg.norm(n) + 1e-12)
    c = np.array(surf(u, y))
    if np.dot(n, c - np.array([B.XC, c[1], (B.Z_FRONT + B.Z_REAR) / 2])) < 0:
        n = -n
    return n


ROWS = sorted(set([B.Y_BOT, B.Y_BOT + 0.03, B.Y_BOT + 0.08, 0.62, 0.66, 1.05, 1.20, 0.80, 1.00, 1.15, 1.26, 1.28, 1.30, 1.36, 1.55, 1.80, 2.00, 2.18, 2.22, 2.25,
                   2.30, 2.31, 2.34, 2.38, 2.45, 2.53, 2.58, 2.64, 2.68, 2.705, 2.722, 2.733, 2.739, 2.74]))
SIDE0, SIDE1 = B.Z_REAR + B.RC, B.Z_FRONT - B.RC           # straight side span at the belt


def side_stations(windows, extra):
    zs = set([SIDE0, SIDE1] + extra)
    for z0, z1 in windows:
        zs.update([z0, z1])
    zs = sorted(zs)
    out = []
    for a, b in zip(zs[:-1], zs[1:]):
        n = max(1, int(math.ceil((b - a) / 0.30)))
        out += [a + (b - a) * k / n for k in range(n)]
    out.append(zs[-1])
    return out


def face_stations(breaks):
    """front / rear face stations in ABSOLUTE x (bus-local)."""
    xs0, xs1 = B.XC - (B.W_HALF - B.RC), B.XC + (B.W_HALF - B.RC)
    xs = sorted(set([xs0, xs1] + [b for b in breaks if xs0 < b < xs1]))
    out = []
    for a, b in zip(xs[:-1], xs[1:]):
        n = max(1, int(math.ceil((b - a) / 0.22)))
        out += [a + (b - a) * k / n for k in range(n)]
    out.append(xs[-1])
    return out


def build_shell():
    """outer skin as a grid of quads: rows = ROWS, columns = perimeter stations. Returns (bm, opening tags)."""
    sl = [z for w in B.SLOPE_R for z in w]
    R_SIDE = side_stations(B.WIN_R, [B.DOOR[0], B.DOOR[1], B.DOOR_POST[0], B.A_PILLAR_R[0]] + list(B.AXLES) + sl)
    L_SIDE = side_stations(B.WIN_L, [B.A_PILLAR_L[0]] + list(B.AXLES) + [z for w in B.SLOPE_L for z in w])
    FRONT = face_stations(list(B.WS_POST) + [x for w in B.BROWS for x in w])
    REAR = face_stations([B.REAR_WIN[0], B.REAR_WIN[1]])
    NC = 6
    cols = []
    for z in R_SIDE:                                   # right side, rear -> front
        cols.append(('R', z))
    for k in range(1, NC):
        cols.append(('RF', k / NC))
    for x in reversed(FRONT):                          # front face, right -> left
        cols.append(('F', x))
    for k in range(1, NC):
        cols.append(('LF', k / NC))
    for z in reversed(L_SIDE):                         # left side, front -> rear
        cols.append(('L', z))
    for k in range(1, NC):
        cols.append(('LR', k / NC))
    for x in REAR:                                     # rear face, left -> right
        cols.append(('Bk', x))
    for k in range(1, NC):
        cols.append(('RR', k / NC))
    point = shell_point

    bm = bmesh.new()
    grid = []
    for y in ROWS:
        grid.append([bm.verts.new(U2B(point(c, y))) for c in cols])
    nC = len(cols)

    def opening(c0, c1, y0, y1):
        ym = (y0 + y1) / 2
        s0, v0 = c0
        s1, v1 = c1
        if s0 == s1 == 'R':
            zm = (v0 + v1) / 2
            if B.DOOR[0] < zm < B.DOOR[1] and ym < B.DOOR_HEAD:
                return 'Door'
            for i, (a, b) in enumerate(B.WIN_R):
                if a < zm < b and B.WIN_SILL < ym < B.WIN_HEAD:
                    return 'WinR%d' % (i + 1)
            for i, (a, b) in enumerate(B.SLOPE_R):
                if a < zm < b and B.SLOPE_Y[0] < ym < B.SLOPE_Y[1]:
                    return 'SlopeR%d' % (i + 1)
            if zm > B.A_PILLAR_R[1] - 1e-6 and B.WS_BOT < ym < B.WS_TOP:
                return 'WindscreenR'
        if s0 == s1 == 'L':
            zm = (v0 + v1) / 2
            for i, (a, b) in enumerate(B.WIN_L):
                if a < zm < b and B.WIN_SILL < ym < B.WIN_HEAD:
                    return 'WinL%d' % i
            for i, (a, b) in enumerate(B.SLOPE_L):
                if a < zm < b and B.SLOPE_Y[0] < ym < B.SLOPE_Y[1]:
                    return 'SlopeL%d' % i
            if zm > B.A_PILLAR_L[1] - 1e-6 and B.WS_BOT < ym < B.WS_TOP:
                return 'WindscreenL'
        if s0 in ('RF', 'F', 'LF') or s1 in ('RF', 'F', 'LF'):
            if B.WS_BOT < ym < B.WS_TOP:
                if s0 == s1 == 'F':
                    xm = (v0 + v1) / 2
                    if B.WS_POST[0] < xm < B.WS_POST[1]:
                        return None                      # the centre post
                    return 'WindscreenR' if xm > B.WS_POST[1] else 'WindscreenL'
                return 'WindscreenR' if 'RF' in (s0, s1) or s0 == 'R' else 'WindscreenL'
            if s0 == s1 == 'F' and B.BROW_Y[0] < ym < B.BROW_Y[1]:
                xm = (v0 + v1) / 2
                for i, (a, b) in enumerate(B.BROWS):
                    if a < xm < b:
                        return 'DestWindow' if i == 1 else 'Brow%d' % i
        if s0 == s1 == 'Bk':
            xm = (v0 + v1) / 2
            if B.REAR_WIN[0] < xm < B.REAR_WIN[1] and B.REAR_WIN[2] < ym < B.REAR_WIN[3]:
                return 'RearWindow'
        return None

    tags = {}
    front = ('RF', 'F', 'LF')
    for i in range(len(ROWS) - 1):
        for j in range(nC):
            j1 = (j + 1) % nC
            f = bm.faces.new((grid[i][j], grid[i][j1], grid[i + 1][j1], grid[i + 1][j]))
            op = opening(cols[j], cols[j1], ROWS[i], ROWS[i + 1])
            ym = (ROWS[i] + ROWS[i + 1]) / 2
            on_front = cols[j][0] in front and cols[j1][0] in front
            if on_front:      # PAZ front (ref PAZ_02): cream face, an indigo skirt below 0.62
                f.material_index = 0 if ym < 0.66 else (2 if 1.26 < ym < 1.28 else 1)
            else:
                f.material_index = 0 if ym < 1.26 else (2 if ym < 1.28 else 1)
            if op:
                tags.setdefault(op, []).append(f)
    top = bm.faces.new(grid[-1])
    top.material_index = 1
    bot = bm.faces.new(list(reversed(grid[0])))
    bot.material_index = 0
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, tags


def make_glass_and_cut(bm, tags):
    """copy each opening's faces into a glass object (inset along -normal), then delete them from the shell."""
    glass = {}
    for name, faces in tags.items():
        if name == 'Door':
            continue
        g = bmesh.new()
        vmap = {}
        for f in faces:
            vs = []
            for v in f.verts:
                if v.index not in vmap:
                    vmap[v.index] = g.verts.new(v.co - v.normal * GLASS_INSET)
                vs.append(vmap[v.index])
            g.faces.new(vs)
        glass[name] = g
    bm.verts.index_update()
    bmesh.ops.delete(bm, geom=[f for fs in tags.values() for f in fs], context='FACES_ONLY')
    return glass


def build_body():
    bm, tags = build_shell()
    bm.verts.index_update()
    bm.normal_update()
    glass = make_glass_and_cut(bm, tags)
    body = obj_from_bm('Body', bm, ['Ext_Indigo', 'Ext_Cream', 'Ext_Silver', 'Int_Enamel', 'Int_Enamel', 'Int_Enamel',
                                    'Seal', 'Seal', 'Seal'])
    md = body.modifiers.new('solid', 'SOLIDIFY')
    md.thickness = SHELL_T
    md.offset = -1.0
    md.material_offset = 3
    md.material_offset_rim = 6
    md.use_rim = True
    md.use_even_offset = True
    apply_mods(body)
    for i, z in enumerate(B.AXLES):
        c = cylinder('ArchCut%d' % i, (B.XC, B.WHEEL_R, z), 'x', B.ARCH_R, 3.0, 'Seal', segs=48)
        boolean(body, c)
        bpy.data.objects.remove(c)
    sx, sy, sz = B.SKY_C
    h = B.SKY_HALF
    # the opening in the roof skin is splayed (bigger than the glass, most of all at the front) so the skin and the
    # coaming above the glass do not cut the view: the glass edges set the angles (D-28: +44.5 ... +58.5 held)
    c = box('HatchCut', (sx - h - 0.05, 2.55, sz - h - 0.06), (sx + h + 0.05, 3.0, sz + h + 0.20), 'Seal')
    boolean(body, c)
    bpy.data.objects.remove(c)
    smooth_by_angle(body, 40)
    gobs = []
    for name, g in glass.items():
        ob = obj_from_bm('Glass_' + name, g, ['Glass'], 'Glass')
        ob['lb_fse'] = 'BusGlass'
        gobs.append(ob)
    return body, gobs


# ------------------------------------------------------------------------------------------------ cabin
LINER_IN = 0.07       # the ceiling liner sits 7 cm inside the roof skin (frames, wiring)


def ceil_y(x):
    """perforated-board liner: flat at CEIL_Y (= the skylight glass) over the crown, then it follows the shoulder
    down to the window head."""
    return min(B.CEIL_Y, B.roof_y(abs(x - B.XC) + LINER_IN) - LINER_IN)


def slope_hole(x, z):
    """is liner point (x, z) under one of the roof-slope windows?"""
    yo = B.roof_y(abs(x - B.XC) + LINER_IN)
    if not (B.SLOPE_Y[0] + 0.01 < yo < B.SLOPE_Y[1] - 0.01):
        return False
    wins = B.SLOPE_R if x > B.XC else B.SLOPE_L
    return any(a + 0.01 < z < b - 0.01 for a, b in wins)


def ceiling():
    x0, x1 = B.XC - (B.W_TOPSIDE - LINER_IN), B.XC + (B.W_TOPSIDE - LINER_IN)
    xs = sorted(set([x0 + (x1 - x0) * k / 60 for k in range(61)]))
    zs = sorted(set([B.Z_REAR + 0.06 + (3.40 - B.Z_REAR - 0.06) * k / 86 for k in range(87)] +
                    [z for w in B.SLOPE_R + B.SLOPE_L for z in w] + [B.SKY_C[2] - B.SKY_HALF, B.SKY_C[2] + B.SKY_HALF]))
    zs = [z for z in zs if B.Z_REAR + 0.06 <= z <= 3.40]
    bm = bmesh.new()
    V = [[bm.verts.new(U2B((x, ceil_y(x), z))) for x in xs] for z in zs]
    sx, _, sz = B.SKY_C
    h = B.SKY_HALF
    for i in range(len(zs) - 1):
        for j in range(len(xs) - 1):
            xm, zm = (xs[j] + xs[j + 1]) / 2, (zs[i] + zs[i + 1]) / 2
            if abs(xm - sx) < h and abs(zm - sz) < h:
                continue
            if slope_hole(xm, zm):
                continue
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    ob = obj_from_bm('Ceiling', bm, ['Int_Ceiling'])
    smooth_by_angle(ob, 30)
    # the reveals of the slope windows (liner -> skin), enamel
    for side, wins in ((1, B.SLOPE_R), (-1, B.SLOPE_L)):
        for k, (a, b) in enumerate(wins):
            for z in (a + 0.01, b - 0.01):
                pts = []
                for t in range(9):
                    yo = B.SLOPE_Y[0] + (B.SLOPE_Y[1] - B.SLOPE_Y[0]) * t / 8
                    # x on the skin at height yo, and on the liner below it
                    u = math.sqrt(max(0.0, 1 - ((yo - B.Y_SIDE_ROOF) / (B.Y_TOP - B.Y_SIDE_ROOF)) ** 2))
                    xo = B.CROWN_HALF + (B.W_TOPSIDE - B.CROWN_HALF) * u
                    pts.append((B.XC + side * (xo - 0.02), yo))
                g = bmesh.new()
                vs_o = [g.verts.new(U2B((px, py, z))) for px, py in pts]
                vs_i = [g.verts.new(U2B((B.XC + side * ((abs(px - B.XC)) - LINER_IN), py - LINER_IN, z))) for px, py in pts]
                for t in range(len(pts) - 1):
                    g.faces.new((vs_o[t], vs_o[t + 1], vs_i[t + 1], vs_i[t]))
                obj_from_bm('SlopeReveal%s%d_%.2f' % ('R' if side > 0 else 'L', k, z), g, ['Int_Enamel'], 'Cabin')
    # front header above the windscreen, the blind box behind it
    # no header panel: from inside you see PAZ's three brow windows above the windscreen (the middle one is the back
    # of the destination blind); only the rubber lip of the windscreen and a narrow ledge under the brows
    box('HeaderLip', (B.X_IN_L, B.WS_TOP - 0.012, 3.40), (B.X_IN_R, B.WS_TOP + 0.02, 3.47), 'Seal')
    # the header band between the windscreen and the brows (in view all film long, D-28 notes): a panel seam, a row of
    # rivets every 15 cm (bible 4.2), anodised inner frames round the three brow windows
    zin = lambda x, y: front_z(x, y) - SHELL_T - 0.002
    for x in np.arange(B.X_IN_L + 0.06, B.X_IN_R - 0.05, 0.15):
        cylinder('HeaderRivet%.2f' % x, (x, B.WS_TOP + 0.035, zin(x, B.WS_TOP + 0.035) - 0.002), 'z', 0.0045, 0.006, 'Int_Enamel', 'Cabin', segs=10)
    xs_ = np.linspace(B.X_IN_L + 0.02, B.X_IN_R - 0.02, 48)
    g = bmesh.new()
    vt = [g.verts.new(U2B((x, B.WS_TOP + 0.062, zin(x, B.WS_TOP + 0.062) - 0.001))) for x in xs_]
    vb = [g.verts.new(U2B((x, B.WS_TOP + 0.056, zin(x, B.WS_TOP + 0.056) - 0.001))) for x in xs_]
    for k in range(len(xs_) - 1):
        g.faces.new((vb[k], vb[k + 1], vt[k + 1], vt[k]))
    obj_from_bm('HeaderSeam', g, ['Seal'], 'Cabin')
    for k, (bx0, bx1) in enumerate(B.BROWS):
        y0_, y1_ = B.BROW_Y
        for nm, lo, hi in (('B', (bx0 - 0.02, y0_ - 0.02, 0), (bx1 + 0.02, y0_, 0)), ('T', (bx0 - 0.02, y1_, 0), (bx1 + 0.02, y1_ + 0.02, 0)),
                           ('L', (bx0 - 0.02, y0_, 0), (bx0, y1_, 0)), ('R', (bx1, y0_, 0), (bx1 + 0.02, y1_, 0))):
            zc = zin((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
            box('BrowFrame%d%s' % (k, nm), (lo[0], lo[1], zc - 0.012), (hi[0], hi[1], zc), 'Alu', 'Cabin')
    box('BrowLedge', (B.X_IN_L, B.BROW_Y[0] - 0.035, 3.36), (B.X_IN_R, B.BROW_Y[0] - 0.02, 3.465), 'Int_Enamel', bevel=0.006)
    box('DestBlind', (B.DEST_BOX[0], B.DEST_BOX[2] - 0.01, 3.44), (B.DEST_BOX[1], B.DEST_BOX[3] + 0.01, 3.452), 'Linen')
    # hatch: aluminium frame flush in the liner, a short well up through the roof skin, glass at SKY_C.y
    fw = 0.04
    yb, yt = B.CEIL_Y - 0.012, B.CEIL_Y + 0.035
    for nm, lo, hi in (('HatchWall0', (sx - h - fw, yb, sz - h - fw), (sx + h + fw, yt, sz - h)),
                       ('HatchWall1', (sx - h - fw, yb, sz + h), (sx + h + fw, yt, sz + h + fw)),
                       ('HatchWall2', (sx - h - fw, yb, sz - h), (sx - h, yt, sz + h)),
                       ('HatchWall3', (sx + h, yb, sz - h), (sx + h + fw, yt, sz + h))):
        box(nm, lo, hi, 'Alu')
    g = bmesh.new()
    vs = [g.verts.new(U2B(p)) for p in ((sx - h, B.SKY_C[1], sz - h), (sx + h, B.SKY_C[1], sz - h),
                                        (sx + h, B.SKY_C[1], sz + h), (sx - h, B.SKY_C[1], sz + h))]
    g.faces.new(vs)
    sg = obj_from_bm('Glass_Skylight', g, ['Glass'], 'Glass')
    sg['lb_fse'] = 'BusGlass'
    # outside: the raised hatch housing (PAZ's front roof hatch, glazed) — a low coaming round the glass
    hz0, hz1, hx0, hx1 = sz - h - 0.06, sz + h + 0.20, sx - h - 0.05, sx + h + 0.05
    hz0, hz1, hx0, hx1 = sz - h - 0.06, sz + h + 0.20, sx - h - 0.05, sx + h + 0.05
    # splayed well: four sloped enamel panels from the glass edges out to the skin opening
    for (a0, a1, b0, b1) in (((sx - h, sz - h), (sx + h, sz - h), (hx1, hz0), (hx0, hz0)),
                             ((sx + h, sz + h), (sx - h, sz + h), (hx0, hz1), (hx1, hz1)),
                             ((sx - h, sz + h), (sx - h, sz - h), (hx0, hz0), (hx0, hz1)),
                             ((sx + h, sz - h), (sx + h, sz + h), (hx1, hz1), (hx1, hz0))):
        g = bmesh.new()
        vs = [g.verts.new(U2B((a0[0], B.CEIL_Y + 0.035, a0[1]))), g.verts.new(U2B((a1[0], B.CEIL_Y + 0.035, a1[1]))),
              g.verts.new(U2B((b0[0], 2.74, b0[1]))), g.verts.new(U2B((b1[0], 2.74, b1[1])))]
        g.faces.new(vs)
        obj_from_bm('HatchSplay', g, ['Int_Enamel'], 'Bus')
    # the second PAZ roof vent (closed, painted) further back
    box('RoofVent', (B.XC - 0.30, B.Y_TOP - 0.01, -1.20), (B.XC + 0.30, B.Y_TOP + 0.07, -0.70), 'Ext_Cream', bevel=0.02)


def floor():
    xl, xr = B.XC - B.W_HALF + 0.04, B.XC + B.W_HALF - 0.04
    parts = [((xl, 0.56, B.Z_REAR + 0.06), (xr, B.FLOOR_Y, B.DOOR[0])),
             ((xl, 0.56, B.DOOR[0]), (0.58, B.FLOOR_Y, B.DASH_Z0 + 0.02))]
    for i, (lo, hi) in enumerate(parts):
        fl = box('Floor%d' % i, lo, hi, 'Floor')
        for z in B.AXLES:           # the floor stops at the wheel wells
            cut = cylinder('WellCutF', (B.XC, B.WHEEL_R, z), 'x', B.ARCH_R - 0.012, 3.2, 'Seal', segs=48)
            boolean(fl, cut)
            bpy.data.objects.remove(cut)
    # the visible floor: a dense grid 1 mm above the slabs (8 cm cells) so the aisle / doorway wear and the edge dirt
    # (vertex G / R) have vertices to live on
    bm = bmesh.new()
    xs = np.arange(xl, xr + 1e-6, 0.08)
    zs = np.arange(B.Z_REAR + 0.06, B.DASH_Z0 + 0.02 + 1e-6, 0.08)
    V = [[bm.verts.new(U2B((x, B.FLOOR_Y + 0.001, z))) for x in xs] for z in zs]
    for i in range(len(zs) - 1):
        for j in range(len(xs) - 1):
            xm, zm = (xs[j] + xs[j + 1]) / 2, (zs[i] + zs[i + 1]) / 2
            if xm > 0.58 and zm > B.DOOR[0]:
                continue                      # the step well
            if any(abs(zm - za) < B.ARCH_R + 0.02 and abs(xm - B.XC) > B.TRACK_HALF - 0.22 for za in B.AXLES):
                continue                      # under the wheel boxes
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    obj_from_bm('FloorTop', bm, ['Floor'])
    z0, z1 = B.DOOR[0] + 0.01, B.DOOR[1] - 0.01
    box('StepLow', (0.80, 0.17, z0), (1.05, 0.23, z1), 'Floor')
    box('StepMid', (0.60, 0.40, z0), (1.02, 0.43, z1), 'Floor')
    box('StepRiser0', (0.80, 0.23, z0), (0.82, 0.42, z1), 'Int_Enamel')
    box('StepRiser1', (0.58, 0.43, z0), (0.60, B.FLOOR_Y, z1), 'Int_Enamel')
    box('StepWallR', (0.58, 0.17, z0 - 0.02), (1.02, B.FLOOR_Y, z0), 'Ext_Indigo')
    box('StepWallF', (0.58, 0.17, z1), (1.02, B.FLOOR_Y, z1 + 0.02), 'Ext_Indigo')
    for nm, x, y in (('NosingLow', 0.80, 0.23), ('NosingMid', 0.60, 0.43), ('NosingTop', 0.58, B.FLOOR_Y)):
        box(nm, (x - 0.005, y - 0.005, z0), (x + 0.045, y + 0.004, z1), 'Alu')
        box(nm + 'Strip', (x + 0.005, y + 0.004, z0 + 0.01), (x + 0.035, y + 0.006, z1 - 0.01), 'SafetyYellow')
    # wheel boxes inside (the hero seat sits on the front right one)
    for i, z in enumerate(B.AXLES):
        for s in (-1, 1):
            xo = B.XC + s * (B.W_HALF - 0.04)
            xi = B.XC + s * (B.TRACK_HALF - 0.22)
            if s > 0 and i == 0:
                lo, hi = (0.56, B.FLOOR_Y, z - 0.56), (xo, 1.00, z + 0.45)
            else:
                lo, hi = (min(xo, xi), B.FLOOR_Y, z - 0.56), (max(xo, xi), 1.00, z + 0.56)
            wb = box('WheelBox%d%s' % (i, 'R' if s > 0 else 'L'), lo, hi, 'Int_Enamel', bevel=0.04)
            # hollow the box along the wheel well, so from outside the arch shows only the dark liner (not cream enamel)
            cut = cylinder('WellCut', (B.XC, B.WHEEL_R, z), 'x', B.ARCH_R - 0.012, 3.2, 'Seal', segs=48)
            boolean(wb, cut)
            bpy.data.objects.remove(cut)


def pad(name, lo, hi, r, m, collection='Seats', crown=(0.0, 0.0, 0.0), cuts=8):
    """upholstered pad: a properly rounded box (radius r) with a crown on +y (cushion) or -z/+z (backrest face).
    crown = (top, front(+z), back(-z)) bulge in metres."""
    lo, hi = Vector(lo), Vector(hi)
    c, half = (lo + hi) / 2, (hi - lo) / 2
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    for v in bm.verts:
        p = Vector((v.co.x, v.co.y, v.co.z))           # here x, y, z are UNITY axes in [-1, 1]
        ph = Vector((p.x * half.x, p.y * half.y, p.z * half.z))
        inner = Vector((max(-(half.x - r), min(half.x - r, ph.x)), max(-(half.y - r), min(half.y - r, ph.y)),
                        max(-(half.z - r), min(half.z - r, ph.z))))
        d = ph - inner
        q = inner + (d.normalized() * r if d.length > 1e-9 else d)
        u2, w2, y2 = min(1, p.x * p.x), min(1, p.z * p.z), min(1, p.y * p.y)
        if p.y > 0:
            q.y += crown[0] * (1 - u2) * (1 - w2) * p.y
        if p.z > 0:
            q.z += crown[1] * (1 - u2) * (1 - y2) * p.z
        if p.z < 0:
            q.z -= crown[2] * (1 - u2) * (1 - y2) * (-p.z)
        v.co = U2B(c + q)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bm.calc_volume(signed=True) < 0:          # U2B is a reflection: make sure the pad is not inside-out
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = obj_from_bm(name, bm, [m], collection)
    for f in ob.data.polygons:
        f.use_smooth = True
    return ob


def seat(name, x0, x1, back_z, double=False, worn=1.0, cushion_y=None, collection='Seats'):
    """bus seat: crowned cushion with piping, backrest reclined 12 deg (front face crowned, back panel flat),
    chrome grab rail on top, steel frame + legs. back_z = back face of the backrest."""
    cy = cushion_y or (B.FLOOR_Y + B.SEAT_H)
    objs = []
    objs.append(pad(name + '_Cushion', (x0 + 0.015, cy - 0.11, back_z + 0.07), (x1 - 0.015, cy - 0.01, back_z + 0.50), 0.035, 'Vinyl',
                    collection, crown=(0.012, 0.0, 0.0)))
    tilt = math.radians(12)
    piv = Vector((0, cy - 0.02, back_z + 0.09))
    bk = pad(name + '_Back', (x0 + 0.015, cy - 0.02, back_z + 0.02), (x1 - 0.015, cy + 0.60, back_z + 0.12), 0.04, 'Vinyl',
             collection, crown=(0.0, 0.016, 0.0))
    shell = box(name + '_BackShell', (x0 + 0.02, cy + 0.02, back_z), (x1 - 0.02, cy + 0.57, back_z + 0.025), 'Vinyl', collection, bevel=0.02, segs=3)   # PAZ: upholstered backs
    pb = U2B(piv)
    R = Matrix.Translation(pb) @ Matrix.Rotation(-tilt, 4, 'X') @ Matrix.Translation(-pb)
    for o in (bk, shell):
        o.matrix_world = R @ o.matrix_world
    objs += [bk, shell]
    # piping along the cushion's front-top edge
    objs.append(tube(name + '_Piping', [(x0 + 0.05, cy - 0.012, back_z + 0.495), (x1 - 0.05, cy - 0.012, back_z + 0.495)], 0.005, 'Vinyl', collection))
    ty = cy - 0.02 + 0.62 * math.cos(tilt)
    tz = back_z + 0.07 - 0.62 * math.sin(tilt)
    objs.append(tube(name + '_Rail', [(x0 + 0.05, ty - 0.03, tz + 0.01), (x0 + 0.05, ty + 0.03, tz - 0.01),
                                      (x1 - 0.05, ty + 0.03, tz - 0.01), (x1 - 0.05, ty - 0.03, tz + 0.01)], 0.011, 'Chrome', collection))
    objs.append(box(name + '_Frame', (x0 + 0.03, cy - 0.15, back_z + 0.10), (x1 - 0.03, cy - 0.11, back_z + 0.46), 'SeatFrame', collection))
    for xx in ((x0 + 0.08,) if not double else (x0 + 0.08, (x0 + x1) / 2)):
        if cy - 0.15 > B.FLOOR_Y + 0.05:
            objs.append(tube(name + '_Leg%.2f' % xx, [(xx, B.FLOOR_Y, back_z + 0.40), (xx, cy - 0.15, back_z + 0.36)], 0.014, 'SeatFrame', collection))
            objs.append(box(name + '_Foot%.2f' % xx, (xx - 0.03, B.FLOOR_Y, back_z + 0.36), (xx + 0.03, B.FLOOR_Y + 0.008, back_z + 0.44), 'SeatFrame', collection))
    return objs


def seats():
    hero = None
    for i, bz in enumerate(B.RIGHT_ROWS):
        cy = (1.00 + 0.04) if i == 0 else None        # the hero seat sits on the front wheel box
        o = seat('SeatR%d' % i, B.SEAT_R_X[0], B.SEAT_R_X[1], bz, cushion_y=cy)
        if i == 0:
            hero = o
    for i, bz in enumerate(B.LEFT_ROWS):
        over_wheel = abs(bz + 0.30 - B.AXLES[1]) < 0.55
        seat('SeatL%d' % i, B.SEAT_L_X[0], B.SEAT_L_X[1], bz, double=True, cushion_y=(1.00 + 0.04) if over_wheel else None)
    seat('RearBench', B.X_IN_L + 0.03, B.X_IN_R - 0.03, B.REAR_BENCH_Z, double=True)
    dx, dz = B.DRIVER_SEAT
    seat('DriverSeat', dx - 0.25, dx + 0.25, dz - 0.30, cushion_y=B.FLOOR_Y + 0.46)
    box('DriverPedestal', (dx - 0.22, B.FLOOR_Y, dz - 0.20), (dx + 0.22, B.FLOOR_Y + 0.30, dz + 0.15), 'SeatFrame', 'Seats')
    return hero


def driver_area():
    # dashboard: a moulded plastic shelf across the front, sloping top; instrument binnacle in front of the wheel
    x0, x1 = B.X_IN_L, B.X_IN_R
    bm = bmesh.new()
    prof = [(B.DASH_Z0, 0.95), (B.DASH_Z0, B.DASH_TOP - 0.04), (B.DASH_Z0 + 0.06, B.DASH_TOP), (3.44, B.WS_BOT - 0.01), (3.44, 0.95)]
    nx = 40                                    # dense along x: the hands' wear on the edge lives on the vertices
    cols = [[bm.verts.new(U2B((x0 + (x1 - x0) * i / nx, y, z))) for z, y in prof] for i in range(nx + 1)]
    for i in range(nx):
        for k in range(len(prof) - 1):
            bm.faces.new((cols[i][k], cols[i][k + 1], cols[i + 1][k + 1], cols[i + 1][k]))
    bm.faces.new(list(reversed(cols[0])))
    bm.faces.new(cols[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj_from_bm('Dashboard', bm, ['Dash'], 'Cabin')
    box('DashLowerL', (x0, B.FLOOR_Y, B.DASH_Z0 + 0.04), (0.56, 0.95, 3.44), 'Dash', 'Cabin')
    wx, wy, wz = B.WHEEL_C
    box('Binnacle', (wx - 0.17, B.DASH_TOP - 0.02, B.DASH_Z0 - 0.02), (wx + 0.17, B.DASH_TOP + 0.09, B.DASH_Z0 + 0.14), 'Dash', 'Cabin', bevel=0.02)
    box('Gauges', (wx - 0.14, B.DASH_TOP + 0.005, B.DASH_Z0 - 0.025), (wx + 0.14, B.DASH_TOP + 0.075, B.DASH_Z0 - 0.02), 'Ext_Black', 'Cabin')
    tilt = math.radians(B.WHEEL_TILT)
    n = (0.0, math.cos(tilt), -math.sin(tilt))
    tube('SteeringColumn', [(wx, 0.80, wz + 0.30), (wx, wy, wz)], 0.03, 'Dash', 'Cabin')
    vv = Vector((0, -n[2], n[1]))
    ring = [(wx + B.WHEEL_RIM_R * math.cos(a), wy + B.WHEEL_RIM_R * math.sin(a) * vv.y, wz + B.WHEEL_RIM_R * math.sin(a) * vv.z)
            for a in [2 * math.pi * k / 48 for k in range(48)]]
    tube('SteeringWheel', ring, 0.014, 'Bakelite', 'Cabin', closed=True)
    for a in (math.radians(200), math.radians(340), math.radians(90)):
        p = (wx + B.WHEEL_RIM_R * math.cos(a), wy + B.WHEEL_RIM_R * math.sin(a) * vv.y, wz + B.WHEEL_RIM_R * math.sin(a) * vv.z)
        tube('SteeringSpoke%d' % int(math.degrees(a)), [(wx, wy, wz), p], 0.010, 'Bakelite', 'Cabin')
    cylinder('SteeringHub', (wx, wy, wz), n, 0.05, 0.03, 'Bakelite', 'Cabin', segs=24)
    tube('GearLever', [(wx + 0.40, B.FLOOR_Y, wz - 0.45), (wx + 0.44, 1.10, wz - 0.55)], 0.012, 'Steel', 'Cabin')
    cylinder('GearKnob', (wx + 0.44, 1.12, wz - 0.55), 'y', 0.025, 0.05, 'Bakelite', 'Cabin', segs=16)
    # PAZ: the front-engine cover ("doghouse") right of the driver; padded top in the same vinyl, enamel sides
    ex0, ex1, ez0, ez1, ey = B.ENGINE_COVER
    box('EngineCover', (ex0, B.FLOOR_Y, ez0), (ex1, ey - 0.04, ez1), 'Int_Enamel', 'Cabin', bevel=0.05, segs=3)
    pad('EngineCoverPad', (ex0 + 0.03, ey - 0.06, ez0 + 0.04), (ex1 - 0.03, ey, ez1 - 0.03), 0.03, 'Vinyl', 'Cabin', crown=(0.01, 0, 0))


def radio():
    """leather-cased 1970s transistor radio on a bent steel bracket off the dash (bible 4.4: az -20, el -12)."""
    cx, cy, cz = B.RADIO_C
    w, h, d = 0.14, 0.10, 0.055
    # face turned toward the hero eye (yaw about y)
    ex, ey, ez = B.EYE
    yaw = math.atan2(ex - cx, ez - cz)
    objs = []
    objs.append(box('Radio_Case', (cx - w / 2, cy - h / 2, cz - d / 2), (cx + w / 2, cy + h / 2, cz + d / 2), 'RadioLeather', 'Cabin', bevel=0.012))
    objs.append(box('Radio_Grille', (cx - w / 2 + 0.012, cy - h / 2 + 0.012, cz + d / 2), (cx + 0.01, cy + h / 2 - 0.022, cz + d / 2 + 0.003), 'RadioGrille', 'Cabin'))
    objs.append(box('Radio_Dial', (cx + 0.016, cy - h / 2 + 0.014, cz + d / 2), (cx + w / 2 - 0.012, cy + h / 2 - 0.022, cz + d / 2 + 0.004), 'RadioDial', 'Cabin'))
    for k, xx in enumerate((cx + 0.03, cx + 0.055)):
        objs.append(cylinder('Radio_Knob%d' % k, (xx, cy + h / 2 + 0.008, cz + 0.005), 'y', 0.009, 0.016, 'Chrome', 'Cabin', segs=16))
    objs.append(tube('Radio_Strap', [(cx - w / 2, cy + h / 2 - 0.01, cz), (cx - w / 2 + 0.02, cy + h / 2 + 0.05, cz),
                                     (cx + w / 2 - 0.02, cy + h / 2 + 0.05, cz), (cx + w / 2, cy + h / 2 - 0.01, cz)], 0.005, 'RadioLeather', 'Cabin'))
    piv = U2B((cx, cy, cz))
    R = Matrix.Translation(piv) @ Matrix.Rotation(-yaw, 4, 'Z') @ Matrix.Translation(-piv)
    for o in objs:
        o.matrix_world = R @ o.matrix_world
    # bracket: from the dash top down to the radio's base
    tube('Radio_Bracket', [(cx, B.DASH_TOP + 0.01, cz + 0.12), (cx, cy - h / 2 - 0.03, cz + 0.06), (cx, cy - h / 2 - 0.005, cz)], 0.008, 'Steel', 'Cabin')


W_WIN = None   # wall half-width at mid-window height (set in build)


def wall_x(side, inset):
    return B.XC + side * (W_of(1.76) - inset)


def window_trim():
    """inside: anodised alu frames round the side windows (25 mm), a sill ledge, sliding-window meeting rails."""
    t = 0.025
    for side, wins in ((1, B.WIN_R), (-1, B.WIN_L)):
        for k, (z0, z1) in enumerate(wins):
            nm = 'Trim%s%d' % ('R' if side > 0 else 'L', k)
            xo, xi = wall_x(side, SHELL_T + 0.002), wall_x(side, SHELL_T + 0.022)
            lo_x, hi_x = min(xo, xi), max(xo, xi)
            box(nm + 'Top', (lo_x, B.WIN_HEAD - 0.005, z0 - t), (hi_x, B.WIN_HEAD + t, z1 + t), 'Alu', 'Cabin')
            box(nm + 'Bot', (lo_x, B.WIN_SILL - t, z0 - t), (hi_x, B.WIN_SILL + 0.005, z1 + t), 'Alu', 'Cabin')
            box(nm + 'F', (lo_x, B.WIN_SILL, z1 - 0.005), (hi_x, B.WIN_HEAD, z1 + t), 'Alu', 'Cabin')
            box(nm + 'B', (lo_x, B.WIN_SILL, z0 - t), (hi_x, B.WIN_HEAD, z0 + 0.005), 'Alu', 'Cabin')
            lx0 = wall_x(side, SHELL_T + 0.08)
            box(nm + 'Sill', (min(lx0, xo), B.WIN_SILL - 0.05, z0 - t), (max(lx0, xo), B.WIN_SILL - t, z1 + t), 'Int_Enamel', 'Cabin', bevel=0.008)
            if z1 - z0 > 0.9:
                zm = (z0 + z1) / 2
                box(nm + 'Rail', (lo_x, B.WIN_SILL, zm - 0.012), (hi_x, B.WIN_HEAD, zm + 0.012), 'Alu', 'Cabin')
                box(nm + 'Latch', (min(xi, xi - side * 0.02), 1.72, zm - 0.03), (max(xi, xi - side * 0.02), 1.76, zm + 0.03), 'Chrome', 'Cabin', bevel=0.004)


def poles_and_guard():
    gz = B.GUARD_Z
    box('GuardPanel', (0.56, B.FLOOR_Y, gz - 0.02), (0.99, 1.20, gz + 0.01), 'Int_Enamel', 'Cabin', bevel=0.005)
    tube('GuardRail', [(0.99, 1.24, gz), (0.58, 1.24, gz), (0.58, B.FLOOR_Y, gz)], 0.016, 'Steel', 'Cabin')
    # door grab: thin (25 mm) and set back behind the post so the doorway frame stays clean (director r03 note 4)
    tube('DoorGrab', [(0.965, 0.95, B.DOOR_POST[0] - 0.06), (0.945, 1.0, B.DOOR_POST[0] - 0.10), (0.945, 1.90, B.DOOR_POST[0] - 0.10),
                      (0.965, 1.95, B.DOOR_POST[0] - 0.06)], 0.0125, 'Steel', 'Cabin')
    for x in (-0.40, 0.29):
        tube('Rail%+.2f' % x, [(x, 2.30, -3.3), (x, 2.30, 1.95)], 0.016, 'Steel', 'Cabin')
        for z in (-3.3, -1.5, 0.3, 1.95):
            tube('RailHanger%+.2f_%.1f' % (x, z), [(x, 2.30, z), (x, ceil_y(x), z)], 0.010, 'Steel', 'Cabin')
    for i, bz in enumerate(B.RIGHT_ROWS[1::2]):
        tube('PoleR%d' % i, [(0.29, B.FLOOR_Y, bz - 0.03), (0.29, ceil_y(0.29), bz - 0.03)], 0.016, 'Steel', 'Cabin')
    for i, bz in enumerate(B.LEFT_ROWS[1::2]):
        tube('PoleL%d' % i, [(-0.41, B.FLOOR_Y, bz - 0.03), (-0.41, ceil_y(-0.41), bz - 0.03)], 0.016, 'Steel', 'Cabin')


def tubes():
    """2 x 5 tube lights in diffusers (bible 4.3)."""
    out = []
    for side, x in (('L', B.TUBE_X[0]), ('R', B.TUBE_X[1])):
        zl = B.TUBE_Z_L if side == 'L' else B.TUBE_Z
        for i, (z0, z1) in enumerate(zl):
            yc = ceil_y(x)
            out.append(box('Tube%s%d' % (side, i), (x - 0.06, yc - 0.045, z0 + 0.02), (x + 0.06, yc - 0.002, z1 - 0.02), 'TubeDiffuser', 'Lights', bevel=0.02, segs=3))
    return out


def curtains():
    """bible 4.5: 3 tied half, 5 loose, the hero's fully open. Pleated panels hung from a rail at the window head."""
    wins = [('R', z0, z1) for z0, z1 in B.WIN_R[1:]] + [('L', z0, z1) for z0, z1 in B.WIN_L[1:]]
    state = ['tied', 'loose', 'loose', 'tied', 'loose', 'tied', 'loose', 'loose', 'loose']
    for k, (side, z0, z1) in enumerate(wins):
        s = 1 if side == 'R' else -1
        x = wall_x(s, SHELL_T + 0.05)
        tube('CurtainRail%s%d' % (side, k), [(x, 2.20, z0), (x, 2.20, z1)], 0.006, 'Alu', 'Curtains')
        st = state[k % len(state)]
        width = 0.34 if st == 'tied' else 0.42
        for end, zz in (('a', z0 + width / 2), ('b', z1 - width / 2)):
            bm = bmesh.new()
            nU, nV = 32, 12
            ybot = 1.42 if st == 'tied' else 1.32
            V = []
            for i in range(nV + 1):
                yy = 2.19 - (2.19 - ybot) * i / nV
                pinch = 1.0 if st == 'loose' else (1.0 - 0.55 * math.sin(math.pi * min(1.0, i / nV / 0.75)) ** 2)
                row = []
                for j in range(nU + 1):
                    u = (j / nU - 0.5) * width * pinch
                    pleat = 0.016 * math.sin(j * math.pi / 2) * (0.6 + 0.4 * pinch) * (0.7 + 0.3 * i / nV)
                    row.append(bm.verts.new(U2B((x - s * (0.015 + pleat), yy, zz + u))))
                V.append(row)
            for i in range(nV):
                for j in range(nU):
                    bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
            ob = obj_from_bm('Curtain%s%d%s' % (side, k, end), bm, ['Curtain'], 'Curtains')
            ob['lb_curtain_state'] = st
    z0, z1 = B.WIN_R[0]
    x = wall_x(1, SHELL_T + 0.05)
    tube('CurtainRailR1', [(x, 2.20, z0), (x, 2.20, z1)], 0.006, 'Alu', 'Curtains')
    box('CurtainHero', (x - 0.03, 1.36, z0 + 0.02), (x + 0.02, 2.19, z0 + 0.16), 'Curtain', 'Curtains', bevel=0.02)


# ------------------------------------------------------------------------------------------------ exterior
# ------------------------------------------------------------------------------------------------ overlays on the skin
def _corner_patch(bm, u0, y0, du, dy, r, off, n_arc=8):
    """the bit of skin between a square window corner (u0, y0) and its rounded outline: a fan from the corner.
    du, dy = +-1: the direction from the corner into the opening."""
    cu, cy = u0 + du * r, y0 + dy * r
    pts = [(u0 + du * r, y0)]
    for k in range(n_arc + 1):
        a = math.pi / 2 * k / n_arc
        pts.append((cu - du * r * math.cos(a) if False else cu - du * r * math.sin(a), cy - dy * r * math.cos(a)))
    pts.append((u0, y0 + dy * r))
    corner = bm.verts.new(U2B(np.array(surf(u0, y0)) + surf_n(u0, y0) * off))
    vs = [bm.verts.new(U2B(np.array(surf(u, y)) + surf_n(u, y) * off)) for u, y in pts]
    for a_, b_ in zip(vs[:-1], vs[1:]):
        try:
            bm.faces.new((corner, a_, b_))
        except ValueError:
            pass


def _outline(u0, u1, y0, y1, r, n_arc=8, step=0.04):
    """rounded-rectangle outline in (u, y), counter-clockwise. r = dict of corner radii keyed '00','10','11','01'."""
    out = []

    def edge(pa, pb):
        L = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
        n = max(1, int(L / step))
        for k in range(n):
            out.append((pa[0] + (pb[0] - pa[0]) * k / n, pa[1] + (pb[1] - pa[1]) * k / n))

    def arc(cu, cy, rr, a0):
        for k in range(n_arc):
            a = a0 + math.pi / 2 * k / n_arc
            out.append((cu + rr * math.cos(a), cy + rr * math.sin(a)))
    r00, r10, r11, r01 = r['00'], r['10'], r['11'], r['01']
    edge((u0 + r00, y0), (u1 - r10, y0))
    arc(u1 - r10, y0 + r10, r10, -math.pi / 2)
    edge((u1, y0 + r10), (u1, y1 - r11))
    arc(u1 - r11, y1 - r11, r11, 0.0)
    edge((u1 - r11, y1), (u0 + r01, y1))
    arc(u0 + r01, y1 - r01, r01, math.pi / 2)
    edge((u0, y1 - r01), (u0, y0 + r00))
    arc(u0 + r00, y0 + r00, r00, math.pi)
    return out


def window_dress(name, u0, u1, y0, y1, r, skin='Ext_Cream', gasket=0.022):
    """rounded window corners on the rectangular cut: skin-coloured corner fillets just proud of the skin, and a black
    rubber gasket along the rounded outline (bible 4.2: seal #2B2B2B). PAZ windows all have big round corners."""
    if u0 > u1:
        u0, u1 = u1, u0
    bm = bmesh.new()
    for (uc, yc, du, dy, key) in ((u0, y0, 1, 1, '00'), (u1, y0, -1, 1, '10'), (u1, y1, -1, -1, '11'), (u0, y1, 1, -1, '01')):
        if r[key] > 0.005:
            _corner_patch(bm, uc, yc, du, dy, r[key], 0.002)
    if len(bm.faces):
        obj_from_bm(name + '_Fillet', bm, [skin], 'Exterior')
    else:
        bm.free()
    # gasket: a ring from the outline inward by `gasket`
    o = _outline(u0, u1, y0, y1, r)
    ri = {k: max(0.0, v - gasket) for k, v in r.items()}
    i_ = _outline(u0 + gasket, u1 - gasket, y0 + gasket, y1 - gasket, ri)
    if len(o) != len(i_):
        return
    g = bmesh.new()
    vo = [g.verts.new(U2B(np.array(surf(u, y)) + surf_n(u, y) * 0.004)) for u, y in o]
    vi = [g.verts.new(U2B(np.array(surf(u, y)) + surf_n(u, y) * 0.002)) for u, y in i_]
    n = len(vo)
    for k in range(n):
        g.faces.new((vo[k], vo[(k + 1) % n], vi[(k + 1) % n], vi[k]))
    obj_from_bm(name + '_Gasket', g, ['Seal'], 'Exterior')


def dress_windows():
    rr = lambda a, b=None, c=None, d=None: dict(zip(('00', '10', '11', '01'), (a, b if b is not None else a, c if c is not None else a, d if d is not None else a)))
    for k, (z0, z1) in enumerate(B.WIN_R):
        window_dress('WinR%d' % (k + 1), perim_u('R', z0), perim_u('R', z1), B.WIN_SILL, B.WIN_HEAD, rr(0.07))
    for k, (z0, z1) in enumerate(B.WIN_L):
        window_dress('WinL%d' % k, perim_u('L', z1), perim_u('L', z0), B.WIN_SILL, B.WIN_HEAD, rr(0.07))
    # windscreen panes: big round OUTER top corners (D-28b), smaller elsewhere. u runs R side -> F (right to left) -> L side
    uR0, uR1 = perim_u('R', B.A_PILLAR_R[1]), perim_u('F', B.WS_POST[1])
    window_dress('WsR', uR0, uR1, B.WS_BOT, B.WS_TOP, dict(zip(('00', '10', '11', '01'), (0.10, 0.05, 0.06, 0.30))), gasket=0.008)
    uL0, uL1 = perim_u('F', B.WS_POST[0]), perim_u('L', B.A_PILLAR_L[1])
    window_dress('WsL', uL0, uL1, B.WS_BOT, B.WS_TOP, dict(zip(('00', '10', '11', '01'), (0.05, 0.10, 0.30, 0.06))), gasket=0.008)
    for k, (x0, x1) in enumerate(B.BROWS):
        window_dress('Brow%d' % k, perim_u('F', x1), perim_u('F', x0), B.BROW_Y[0], B.BROW_Y[1], rr(0.05))
    window_dress('RearWin', perim_u('Bk', B.REAR_WIN[0]), perim_u('Bk', B.REAR_WIN[1]), B.REAR_WIN[2], B.REAR_WIN[3], rr(0.12))
    # the sliding upper panes (D-28b #6): a horizontal transom at 1.92 and a vertical meeting rail above it, outside
    for side, wins in (('R', B.WIN_R), ('L', B.WIN_L)):
        for k, (z0, z1) in enumerate(wins):
            ua, ub = sorted((perim_u(side, z0), perim_u(side, z1)))
            g = bmesh.new()
            pts = [(u, y) for u in np.linspace(ua + 0.02, ub - 0.02, 12) for y in (1.905, 1.935)]
            V = [g.verts.new(U2B(np.array(surf(u, y)) + surf_n(u, y) * 0.006)) for u, y in pts]
            for j in range(11):
                g.faces.new((V[2 * j], V[2 * j + 2], V[2 * j + 3], V[2 * j + 1]))
            um = (ua + ub) / 2
            for y_ in (1.935,):
                q = [g.verts.new(U2B(np.array(surf(u, y)) + surf_n(u, y) * 0.006)) for u, y in ((um - 0.012, y_), (um + 0.012, y_), (um + 0.012, B.WIN_HEAD - 0.02), (um - 0.012, B.WIN_HEAD - 0.02))]
                g.faces.new(q)
            obj_from_bm('Transom%s%d' % (side, k), g, ['Alu'], 'Exterior')


def cowl():
    """D-28b: a horizontal ledge under the windscreen (the wipers park on it), wrapping both front corners."""
    u0, u1 = perim_u('R', B.A_PILLAR_R[0]), perim_u('L', B.A_PILLAR_L[0])
    us = np.linspace(u0, u1, 90)
    bm = bmesh.new()
    rows = []
    for (y, off) in ((B.WS_BOT - 0.005, 0.0), (B.WS_BOT - 0.005, 0.065), (B.WS_BOT - 0.05, 0.075), (B.WS_BOT - 0.09, 0.0)):
        rows.append([bm.verts.new(U2B(np.array(surf(u, y)) + surf_n(u, y) * off)) for u in us])
    for a_, b_ in zip(rows[:-1], rows[1:]):
        for j in range(len(us) - 1):
            bm.faces.new((a_[j], a_[j + 1], b_[j + 1], b_[j]))
    ob = obj_from_bm('Cowl', bm, ['Ext_Cream'], 'Exterior')
    smooth_by_angle(ob, 40)


def front_z(x, y):
    xs = W_of(y) - B.RC
    xr = x - B.XC
    return Zf_of(y) + front_bulge(xr, xs, y)


def rrect(cx, cy, w, h, r, n=10):
    """rounded rectangle, counter-clockwise, 4 (n + 1) points (same count for any size: frames can be bridged)."""
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    out = []
    for (ox, oy, a0) in ((cx + w / 2 - r, cy - h / 2 + r, -math.pi / 2), (cx + w / 2 - r, cy + h / 2 - r, 0.0),
                         (cx - w / 2 + r, cy + h / 2 - r, math.pi / 2), (cx - w / 2 + r, cy - h / 2 + r, math.pi)):
        for k in range(n + 1):
            a = a0 + math.pi / 2 * k / n
            out.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return out


def face_plate(name, pts_xy, z_of, dz, m, collection='Exterior', ring_inner=None):
    """a flat plate on the front face: outline pts (x, y), at z = z_of(x, y) + dz; with ring_inner = a frame."""
    bm = bmesh.new()
    vo = [bm.verts.new(U2B((x, y, z_of(x, y) + dz))) for x, y in pts_xy]
    if ring_inner is None:
        bm.faces.new(vo)
    else:
        vi = [bm.verts.new(U2B((x, y, z_of(x, y) + dz))) for x, y in ring_inner]
        n = len(vo)
        for k in range(n):
            bm.faces.new((vo[k], vo[(k + 1) % n], vi[(k + 1) % n], vi[k]))
    ob = obj_from_bm(name, bm, [m], collection)
    md = ob.modifiers.new('solid', 'SOLIDIFY')
    md.thickness = 0.012
    md.offset = 1.0
    return ob


def mesh_grille(name, cx, cy, w, h, ring=0.045, pitch=0.026, r=0.10):
    """D-28b #2: a PAZ 'eye': a big round-cornered rectangle of wire mesh in an indigo outline, set into the face."""
    face_plate(name + '_Ring', rrect(cx, cy, w + 2 * ring, h + 2 * ring, r + ring), front_z, 0.004, 'Ext_Indigo',
               ring_inner=rrect(cx, cy, w, h, r))
    face_plate(name + '_Back', rrect(cx, cy, w, h, r), front_z, -0.002, 'Ext_Black')
    z = front_z(cx, cy)

    def half_extent(d, half_main, half_other):
        e = max(0.0, abs(d) - (half_other - r))
        return half_main - r + math.sqrt(max(0.0, r * r - e * e)) if e > 0 else half_main
    for x in np.arange(cx - w / 2 + pitch / 2, cx + w / 2, pitch):
        dy = half_extent(x - cx, h / 2, w / 2) - 0.004
        box(name + '_V%.3f' % x, (x - 0.0025, cy - dy, z + 0.004), (x + 0.0025, cy + dy, z + 0.009), 'SeatFrame', 'Exterior')
    for y in np.arange(cy - h / 2 + pitch / 2, cy + h / 2, pitch):
        dx = half_extent(y - cy, w / 2, h / 2) - 0.004
        box(name + '_H%.3f' % y, (cx - dx, y - 0.0025, z + 0.008), (cx + dx, y + 0.0025, z + 0.012), 'SeatFrame', 'Exterior')


def lamp(name, x, y, r, lens):
    z = front_z(x, y)
    cylinder(name + '_Bezel', (x, y, z + 0.015), 'z', r + 0.012, 0.04, 'Chrome', 'Exterior', segs=48, bevel=0.01)
    cylinder(name + '_Lens', (x, y, z + 0.034), 'z', r, 0.012, lens, 'Exterior', segs=48)


def arch_liners():
    """dark wheel-arch liners (half shells under the skin) so the cream wheel boxes never show through the arches."""
    for i, z in enumerate(B.AXLES):
        for sgn in (-1, 1):
            xo = B.XC + sgn * (B.W_HALF - 0.005)
            xi = B.XC + sgn * (B.TRACK_HALF - 0.20)
            r = B.ARCH_R - 0.01
            bm = bmesh.new()
            n = 24
            ring_o, ring_i = [], []
            for k in range(n + 1):
                a = math.pi * k / n                      # upper half: from front (0) over the top to the back (pi)
                yy, zz = B.WHEEL_R + r * math.sin(a), z + r * math.cos(a)
                ring_o.append(bm.verts.new(U2B((xo, yy, zz))))
                ring_i.append(bm.verts.new(U2B((xi, yy, zz))))
            for k in range(n):
                bm.faces.new((ring_o[k], ring_o[k + 1], ring_i[k + 1], ring_i[k]))
            # the inner wall (wheel-box side seen through the arch)
            bm.faces.new(ring_i[::-1])
            obj_from_bm('ArchLiner%d%s' % (i, 'R' if sgn > 0 else 'L'), bm, ['Ext_Black'], 'Exterior')


def chassis():
    """D-28a: 'a bus on a truck chassis' — frame rails, axles, diff, tank, exhaust, spare wheel, mud flaps under the body."""
    XC = B.XC
    for s in (-1, 1):
        box('FrameRail%s' % ('R' if s > 0 else 'L'), (XC + s * 0.43 - 0.04, 0.36, B.Z_REAR + 0.5), (XC + s * 0.43 + 0.04, 0.54, B.Z_FRONT - 0.15), 'Ext_Black', 'Exterior')
    for z in (2.6, 0.8, -0.6, -2.4):
        box('CrossMember%.1f' % z, (XC - 0.43, 0.40, z - 0.03), (XC + 0.43, 0.50, z + 0.03), 'Ext_Black', 'Exterior')
    zf, zr = B.AXLES
    box('FrontAxle', (XC - B.TRACK_HALF + 0.10, B.WHEEL_R - 0.06, zf - 0.04), (XC + B.TRACK_HALF - 0.10, B.WHEEL_R + 0.02, zf + 0.04), 'Ext_Black', 'Exterior')
    cylinder('RearAxle', (XC, B.WHEEL_R, zr), 'x', 0.06, 2 * B.TRACK_HALF - 0.2, 'Ext_Black', 'Exterior', segs=16)
    cylinder('Diff', (XC, B.WHEEL_R, zr), 'z', 0.17, 0.26, 'Ext_Black', 'Exterior', segs=24, bevel=0.02)
    tube('PropShaft', [(XC, B.WHEEL_R + 0.02, zr + 0.13), (XC, 0.50, 2.2)], 0.035, 'Ext_Black', 'Exterior')
    for s in (-1, 1):
        for z in (zf, zr):
            box('Spring%s%.1f' % ('R' if s > 0 else 'L', z), (XC + s * 0.43 - 0.035, B.WHEEL_R + 0.03, z - 0.55), (XC + s * 0.43 + 0.035, B.WHEEL_R + 0.10, z + 0.55), 'Ext_Black', 'Exterior', bevel=0.01)
    box('FuelTank', (XC - 1.02, 0.30, -0.70), (XC - 0.55, 0.52, 0.30), 'Ext_Black', 'Exterior', bevel=0.04, segs=3)
    tube('Exhaust', [(XC + 0.25, 0.42, 2.4), (XC + 0.55, 0.32, 0.5), (XC + 0.75, 0.30, -2.8), (XC + 0.85, 0.28, B.Z_REAR - 0.05)], 0.03, 'Ext_Black', 'Exterior')
    cylinder('SpareWheel', (XC, 0.36, -2.85), 'y', 0.40, 0.22, 'Tyre', 'Exterior', segs=40, bevel=0.06)
    for s in (-1, 1):
        for z in (zf, zr):
            box('MudFlap%s%.1f' % ('R' if s > 0 else 'L', z), (XC + s * B.TRACK_HALF - 0.13, 0.18, z - B.ARCH_R - 0.02), (XC + s * B.TRACK_HALF + 0.13, B.Y_BOT + 0.05, z - B.ARCH_R + 0.0), 'Tyre', 'Exterior')


def hatch_housing():
    """D-28b #4: the skylight's housing is low and round-edged, hugging the roof curve, ≤ 8 cm above the skin
    (PAZ_04 / PAZ_05). The opening in the skin is splayed; the glass stays at SKY_C.y (contract)."""
    sx, _, sz = B.SKY_C
    h = B.SKY_HALF
    x0, x1, z0, z1 = sx - h - 0.05, sx + h + 0.05, sz - h - 0.06, sz + h + 0.20
    rr = 0.07
    loop = _outline(x0, x1, z0, z1, dict(zip(('00', '10', '11', '01'), (rr,) * 4)), n_arc=6, step=0.05)
    bm = bmesh.new()
    rings = []
    for (dxz, dy) in ((0.0, -0.02), (0.0, 0.055), (0.03, 0.07), (0.075, 0.035), (0.10, -0.015)):
        ring = []
        for (x, z) in loop:
            cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
            vx, vz = x - cx, z - cz
            L = math.hypot(vx, vz) + 1e-9
            px, pz = x + vx / L * dxz, z + vz / L * dxz
            ring.append(bm.verts.new(U2B((px, B.roof_y(px - B.XC) + dy, pz))))
        rings.append(ring)
    n = len(loop)
    for a_, b_ in zip(rings[:-1], rings[1:]):
        for k in range(n):
            bm.faces.new((a_[k], a_[(k + 1) % n], b_[(k + 1) % n], b_[k]))
    ob = obj_from_bm('HatchHousing', bm, ['Ext_Cream'], 'Exterior')
    smooth_by_angle(ob, 50)


def folding_door(open_=True):
    """D-28e: ONE glazed leaf of four 15 cm panels, all folding OUTWARD onto the REAR jamb (accordion). Open = the face of
    this door (bible: it never shuts, except in act 11 under the white mask). Open, the stack swings 75 deg out from the
    wall plane (leaning forward) and stacks rearward, outside the skin behind the door post: from the hero seat the stack
    sits at about +38.5 .. +47.4 deg, so the doorway is clear from the A-pillar (+21.8) past 庄子 8-ii (+35), with the
    dawn sun (D-12, +30) in the middle; 李白 / 济慈 (+50) stay clear."""
    xw = B.R_WALL
    p = B.DOOR_PANEL
    y0, y1 = 0.30, B.DOOR_HEAD - 0.03
    jr = B.DOOR[0] + B.DOOR_JAMB[0]
    pitch = 0.026                     # the folded panels' spacing in the stack
    swing = math.radians(B.DOOR_OPEN_SWING)

    def panel(name, k):
        objs = []
        # local panel: in the wall plane x = xw, from z 0 (its hinge edge) to z p
        objs.append(box(name + '_Stile0', (xw - 0.012, y0, 0.0), (xw + 0.012, y1, 0.025), 'Ext_Cream', 'Door'))
        objs.append(box(name + '_Stile1', (xw - 0.012, y0, p - 0.025), (xw + 0.012, y1, p), 'Ext_Cream', 'Door'))
        objs.append(box(name + '_Low', (xw - 0.012, y0, 0.0), (xw + 0.012, 0.62, p), 'Ext_Indigo', 'Door'))
        objs.append(box(name + '_Mid', (xw - 0.012, 1.26, 0.0), (xw + 0.012, 1.30, p), 'Ext_Silver', 'Door'))
        objs.append(box(name + '_Top', (xw - 0.012, y1 - 0.04, 0.0), (xw + 0.012, y1, p), 'Ext_Cream', 'Door'))
        for (ya, yb) in ((0.62, 1.26), (1.30, y1 - 0.04)):
            g = bmesh.new()
            vs = [g.verts.new(U2B(q)) for q in ((xw + 0.002, ya, 0.025), (xw + 0.002, ya, p - 0.025), (xw + 0.002, yb, p - 0.025), (xw + 0.002, yb, 0.025))]
            g.faces.new(vs)
            gl = obj_from_bm('Glass_%s_%d' % (name, int(ya * 100)), g, ['Glass'], 'Door')
            gl['lb_fse'] = 'BusGlass'
            objs.append(gl)
        if open_:
            # stacked plates, each hinged on the jamb line (z = jr + k * pitch), turned so the panel's +z (unity) points
            # outward and a little forward: unity (sin swing, 0, cos swing). Blender: rotate about z by -swing.
            hz = jr - k * pitch           # stacked REARWARD, outside the skin behind the door post
            M = Matrix.Translation(U2B((xw, 0, hz))) @ Matrix.Rotation(-swing, 4, 'Z') @ Matrix.Translation(U2B((-xw, 0, 0)))
        else:
            M = Matrix.Translation(U2B((0, 0, jr + k * p)))
        for o in objs:
            o.matrix_world = M @ o.matrix_world
        return objs

    out = []
    for k in range(4):
        out += panel('Door%d' % k, k)
    return out


def exterior():
    XC = B.XC
    for i, z in enumerate(B.AXLES):
        for s in (-1, 1):
            x = XC + s * B.TRACK_HALF
            t = 'R' if s > 0 else 'L'
            cylinder('Tyre%d%s' % (i, t), (x, B.WHEEL_R, z), 'x', B.WHEEL_R, B.WHEEL_W, 'Tyre', 'Exterior', segs=48, bevel=0.07)
            cylinder('Rim%d%s' % (i, t), (x + s * 0.10, B.WHEEL_R, z), 'x', 0.27, 0.05, 'Rim', 'Exterior', segs=36, bevel=0.012)
            cylinder('Hub%d%s' % (i, t), (x + s * 0.13, B.WHEEL_R, z), 'x', 0.10, 0.05, 'Rim', 'Exterior', segs=24, bevel=0.01)
            for k in range(6 if i == 0 else 8):
                a = 2 * math.pi * k / (6 if i == 0 else 8)
                cylinder('Nut%d%s%d' % (i, t, k), (x + s * 0.155, B.WHEEL_R + 0.065 * math.sin(a), z + 0.065 * math.cos(a)), 'x', 0.012, 0.025, 'Chrome', 'Exterior', segs=6)
    # the PAZ face (PAZ_02 / 05 / 06, D-28b): two big mesh 'eyes' toward the corners in an indigo outline, a plain centre
    # panel with one small mesh strip, 18 cm round lamps under the eyes (white lit, amber an unlit lens), a thin bumper.
    for s in (-1, 1):
        t = 'R' if s > 0 else 'L'
        mesh_grille('EyeGrille' + t, XC + s * 0.70, 1.00, 0.54, 0.40, r=0.12)
        lamp('Headlight' + t, XC + s * 0.88, 0.70, 0.09, 'Lamp_Head')
        lamp('AmberLamp' + t, XC + s * 0.64, 0.70, 0.075, 'Lamp_Amber')
        box('TailLight' + t, (XC + s * 1.02 - 0.06, 0.78, B.Z_REAR - 0.02), (XC + s * 1.02 + 0.06, 1.06, B.Z_REAR + 0.005), 'Lamp_Tail', 'Exterior', bevel=0.01)
        box('SideMarker' + t, (XC + s * B.W_HALF - 0.005, 0.86, 0.40), (XC + s * B.W_HALF + 0.005, 0.90, 0.50), 'Lamp_Amber', 'Exterior')
    mesh_grille('CentreStrip', XC, 0.86, 0.36, 0.09, ring=0.02, pitch=0.022, r=0.03)
    # thin steel bumpers, painted (PAZ_02: blue)
    for nm, z, d in (('BumperF', B.Z_FRONT + 0.05, 1), ('BumperR', B.Z_REAR - 0.05, -1)):
        pts = [(XC + s * 1.18, 0.47, z - d * 0.16) for s in (-1,)] + [(XC + x, 0.47, z + d * 0.01 * (1 - (x / 1.15) ** 2)) for x in np.linspace(-1.12, 1.12, 9)] + [(XC + 1.18, 0.47, z - d * 0.16)]
        tube(nm, pts, 0.032, 'Ext_Indigo', 'Exterior')
    # mirrors: the right one LOW (D-28c: out of the door frame, el < -5 deg, behind the front door stack), the left one on a stalk
    xw = B.R_WALL
    tube('MirrorStalkR', [(xw - 0.02, 0.86, 3.30), (xw + 0.06, 0.89, 3.62), (xw + 0.10, 0.94, 3.92)], 0.012, 'Ext_Black', 'Exterior')
    box('MirrorHeadR', (xw + 0.10 - 0.08, 0.84, 3.92), (xw + 0.10 + 0.08, 1.08, 3.96), 'Ext_Black', 'Exterior', bevel=0.02)
    xl = XC - B.W_HALF
    tube('MirrorStalkL', [(xl, 1.70, 3.30), (xl - 0.16, 1.72, 3.42), (xl - 0.22, 1.92, 3.56)], 0.012, 'Ext_Black', 'Exterior')
    box('MirrorHeadL', (xl - 0.22 - 0.09, 1.76, 3.54), (xl - 0.22 + 0.09, 2.04, 3.58), 'Ext_Black', 'Exterior', bevel=0.02)
    # wipers parked BELOW the windscreen's lower edge, lying on the cowl (PAZ; D-13 A: from the hero seat they hide
    # behind the skin under the glass, so they never cross the poem block)
    for x0, x1 in ((XC - 1.00, B.WS_POST[0] - 0.08), (B.WS_POST[1] + 0.06, 0.86)):
        y = B.WS_BOT - 0.022
        tube('Wiper%+.2f' % x0, [(x0, y, front_z(x0, y) + 0.03), (x1, y + 0.006, front_z(x1, y) + 0.03)], 0.007, 'Ext_Black', 'Exterior')
    for s in (-1, 1):
        x = XC + s * (W_of(2.33) + 0.008)
        tube('DripRail%s' % ('R' if s > 0 else 'L'), [(x, 2.33, B.Z_REAR + 0.25), (x, 2.33, B.Z_FRONT - 0.25)], 0.008, 'Chrome', 'Exterior')
    tube('RVMStalk', [(-0.05, B.WS_TOP + 0.01, 3.40), (-0.05, 2.15, 3.36)], 0.008, 'Bakelite', 'Cabin')
    box('RVMirror', (-0.16, 2.08, 3.34), (0.06, 2.15, 3.36), 'Bakelite', 'Cabin', bevel=0.01)
    dress_windows()
    cowl()
    chassis()
    arch_liners()
    hatch_housing()


def build(open_door=True, reset=True):
    if reset:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    COLL.clear()
    body, glass = build_body()
    ceiling()
    floor()
    hero = seats()
    driver_area()
    radio()
    poles_and_guard()
    window_trim()
    tubes()
    curtains()
    exterior()
    folding_door(open_door)
    # convert curves to meshes so everything is a mesh (FBX, BVH)
    for ob in list(bpy.data.objects):
        if ob.type == 'CURVE':
            bpy.context.view_layer.objects.active = ob
            for o in bpy.context.selected_objects:
                o.select_set(False)
            ob.select_set(True)
            bpy.ops.object.convert(target='MESH')
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.modifiers:
            apply_mods(ob)
    fix_inside_out()
    return dict(body=body, glass=glass)


def fix_inside_out():
    """closed meshes whose signed volume is negative are inside-out (the U2B reflection): flip them. Bakes and
    single-sided shading need outward normals."""
    n = 0
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        if all(e.is_manifold for e in bm.edges) and len(bm.faces) > 3 and bm.calc_volume(signed=True) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.to_mesh(ob.data)
            n += 1
        bm.free()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/bus/bus.blend')
    ap.add_argument('--fbx', default=None)
    ap.add_argument('--closed', action='store_true')
    a = ap.parse_args()
    build(open_door=not a.closed)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=a.out)
    if a.fbx:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Tentacles', 'Source', 'lib'))
        from export_unity import export_fbx
        export_fbx(a.fbx, [o for o in bpy.data.objects if o.type == 'MESH'])
    print('built', len(bpy.data.objects), 'objects ->', a.out)


if __name__ == '__main__':
    main()
