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
    'Lamp_Amber': ('#C9822A', 0.8, 0),
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
    then the PAZ shoulder (a quarter ellipse) up to the flat crown."""
    if y <= 0.50:
        t = (0.50 - y) / 0.08
        return B.W_HALF - 0.04 * t * t
    if y <= B.Y_SIDE_ROOF:
        return B.W_HALF - (B.W_HALF - B.W_TOPSIDE) * max(0.0, (y - B.Y_BELT)) / (B.Y_SIDE_ROOF - B.Y_BELT)
    v = min(1.0, (y - B.Y_SIDE_ROOF) / (B.Y_TOP - B.Y_SIDE_ROOF))
    return B.CROWN_HALF + (B.W_TOPSIDE - B.CROWN_HALF) * math.sqrt(max(0.0, 1.0 - v * v))


def Zf_of(y):
    if y <= 0.50:
        t = (0.50 - y) / 0.08
        return B.Z_FRONT - 0.05 * t * t
    if y <= B.Y_FRONT_ROOF:
        return B.Z_FRONT
    t = min(1.0, (y - B.Y_FRONT_ROOF) / (B.Y_TOP - B.Y_FRONT_ROOF))
    return B.Z_FRONT - B.FRONT_DOME * (1.0 - math.sqrt(max(0.0, 1.0 - t * t)))


def Zr_of(y):
    return B.Z_REAR + (B.Z_FRONT - Zf_of(y))


ROWS = sorted(set([0.42, 0.45, 0.50, 0.62, 0.80, 1.00, 1.15, 1.26, 1.28, 1.30, 1.36, 1.55, 1.80, 2.00, 2.18, 2.22, 2.25,
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
    XC = B.XC

    def point(col, y):
        seg, v = col
        W, Zf, Zr = W_of(y), Zf_of(y), Zr_of(y)
        Rc = min(B.RC, W * 0.6)
        zs0, zs1 = Zr + Rc, Zf - Rc
        xs = W - Rc
        xs_belt = B.W_HALF - B.RC

        def side_z(z):
            return zs0 + (z - SIDE0) / (SIDE1 - SIDE0) * (zs1 - zs0)
        if seg == 'R':
            return (XC + W, y, side_z(v))
        if seg == 'L':
            return (XC - W, y, side_z(v))
        if seg == 'F':
            return (XC + (v - XC) / xs_belt * xs, y, Zf)
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
                f.material_index = 0 if ym < 0.62 else (2 if 1.26 < ym < 1.28 else 1)
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
    zs = sorted(set([B.Z_REAR + 0.06 + (3.16 - B.Z_REAR - 0.06) * k / 84 for k in range(85)] +
                    [z for w in B.SLOPE_R + B.SLOPE_L for z in w] + [B.SKY_C[2] - B.SKY_HALF, B.SKY_C[2] + B.SKY_HALF]))
    zs = [z for z in zs if B.Z_REAR + 0.06 <= z <= 3.16]
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
    box('Header', (B.X_IN_L, B.WS_TOP + 0.005, 3.14), (B.X_IN_R, B.CEIL_Y + 0.01, 3.18), 'Int_Enamel')
    box('HeaderLip', (B.X_IN_L, B.WS_TOP - 0.012, 3.40), (B.X_IN_R, B.WS_TOP + 0.02, 3.47), 'Seal')
    box('HeaderShelf', (B.X_IN_L, B.WS_TOP + 0.005, 3.17), (B.X_IN_R, B.WS_TOP + 0.02, 3.40), 'Int_Enamel')
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
    for nm, lo, hi in (('HatchOut0', (hx0 - 0.04, 2.55, hz0 - 0.04), (hx1 + 0.04, 2.77, hz0)),
                       ('HatchOut1', (hx0 - 0.04, 2.55, hz1), (hx1 + 0.04, 2.77, hz1 + 0.04)),
                       ('HatchOut2', (hx0 - 0.04, 2.55, hz0), (hx0, 2.77, hz1)),
                       ('HatchOut3', (hx1, 2.55, hz0), (hx1 + 0.04, 2.77, hz1))):
        box(nm, lo, (hi[0], 2.765, hi[2]), 'Alu', bevel=0.012)
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
        box('Floor%d' % i, lo, hi, 'Floor')
    z0, z1 = B.DOOR[0] + 0.01, B.DOOR[1] - 0.01
    box('StepLow', (0.80, 0.17, z0), (1.05, 0.23, z1), 'Floor')
    box('StepMid', (0.60, 0.40, z0), (1.02, 0.43, z1), 'Floor')
    box('StepRiser0', (0.80, 0.23, z0), (0.82, 0.42, z1), 'Int_Enamel')
    box('StepRiser1', (0.58, 0.43, z0), (0.60, B.FLOOR_Y, z1), 'Int_Enamel')
    box('StepWallR', (0.58, 0.17, z0 - 0.02), (1.02, B.FLOOR_Y, z0), 'Int_Enamel')
    box('StepWallF', (0.58, 0.17, z1), (1.02, B.FLOOR_Y, z1 + 0.02), 'Int_Enamel')
    for nm, x, y in (('NosingLow', 0.80, 0.23), ('NosingMid', 0.60, 0.43), ('NosingTop', 0.58, B.FLOOR_Y)):
        box(nm, (x - 0.005, y - 0.005, z0), (x + 0.045, y + 0.004, z1), 'Alu')
        box(nm + 'Strip', (x + 0.005, y + 0.004, z0 + 0.01), (x + 0.035, y + 0.006, z1 - 0.01), 'SafetyYellow')
    # wheel boxes inside (the hero seat sits on the front right one)
    for i, z in enumerate(B.AXLES):
        for s in (-1, 1):
            xo = B.XC + s * (B.W_HALF - 0.04)
            xi = B.XC + s * (B.TRACK_HALF - 0.22)
            if s > 0 and i == 0:
                lo, hi = (0.56, B.FLOOR_Y, z - 0.52), (xo, 0.96, z + 0.45)
            else:
                lo, hi = (min(xo, xi), B.FLOOR_Y, z - 0.52), (max(xo, xi), 0.96, z + 0.52)
            box('WheelBox%d%s' % (i, 'R' if s > 0 else 'L'), lo, hi, 'Int_Enamel', bevel=0.04)


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
    shell = box(name + '_BackShell', (x0 + 0.02, cy + 0.02, back_z), (x1 - 0.02, cy + 0.57, back_z + 0.025), 'SeatFrame', collection, bevel=0.02, segs=3)
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
        cy = (0.96 + 0.07) if i == 0 else None        # the hero seat sits on the front wheel box
        o = seat('SeatR%d' % i, B.SEAT_R_X[0], B.SEAT_R_X[1], bz, cushion_y=cy)
        if i == 0:
            hero = o
    for i, bz in enumerate(B.LEFT_ROWS):
        over_wheel = abs(bz + 0.30 - B.AXLES[1]) < 0.55
        seat('SeatL%d' % i, B.SEAT_L_X[0], B.SEAT_L_X[1], bz, double=True, cushion_y=(0.96 + 0.07) if over_wheel else None)
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
    left = [bm.verts.new(U2B((x0, y, z))) for z, y in prof]
    right = [bm.verts.new(U2B((x1, y, z))) for z, y in prof]
    for k in range(len(prof) - 1):
        bm.faces.new((left[k], left[k + 1], right[k + 1], right[k]))
    bm.faces.new(list(reversed(left)))
    bm.faces.new(right)
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
    tube('DoorGrab', [(0.95, 0.95, B.DOOR_POST[0] - 0.02), (0.92, 1.0, B.DOOR_POST[0] - 0.05), (0.92, 1.90, B.DOOR_POST[0] - 0.05),
                      (0.95, 1.95, B.DOOR_POST[0] - 0.02)], 0.016, 'Steel', 'Cabin')
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
def framed(name, cx, cy, w, h, z, ring=0.035, slats=5):
    """a PAZ 'eye' grille: indigo outline ring (ref PAZ_02), dark recessed mesh, thin horizontal slats."""
    box(name + '_Ring', (cx - w / 2 - ring, cy - h / 2 - ring, z - 0.01), (cx + w / 2 + ring, cy + h / 2 + ring, z + 0.012), 'Ext_Indigo', 'Exterior', bevel=min(0.08, h / 3), segs=6)
    box(name + '_Mesh', (cx - w / 2, cy - h / 2, z + 0.005), (cx + w / 2, cy + h / 2, z + 0.016), 'Ext_Black', 'Exterior', bevel=min(0.06, h / 3.5), segs=5)
    for k in range(slats):
        yy = cy - h / 2 + h * (k + 0.5) / slats
        box(name + '_Slat%d' % k, (cx - w / 2 + 0.02, yy - 0.006, z + 0.016), (cx + w / 2 - 0.02, yy + 0.006, z + 0.024), 'Chrome', 'Exterior')


def exterior():
    XC, zf = B.XC, B.Z_FRONT
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
    # the PAZ face: two 'eye' grilles with an indigo outline, a small centre grille, paired round lamps (white lit +
    # amber unlit, D-28), a cream bumper. No badge, no plate, no letters (D-28 / bible 6.1).
    for s in (-1, 1):
        t = 'R' if s > 0 else 'L'
        framed('EyeGrille' + t, XC + s * 0.68, 1.00, 0.52, 0.44, zf, ring=0.045, slats=7)
        cylinder('HeadRing' + t, (XC + s * 0.88, 0.66, zf + 0.012), 'z', 0.095, 0.03, 'Chrome', 'Exterior', segs=40, bevel=0.008)
        cylinder('Headlight' + t, (XC + s * 0.88, 0.66, zf + 0.026), 'z', 0.082, 0.012, 'Lamp_Head', 'Exterior', segs=40)
        cylinder('AmberRing' + t, (XC + s * 0.66, 0.66, zf + 0.012), 'z', 0.075, 0.03, 'Chrome', 'Exterior', segs=36, bevel=0.008)
        cylinder('AmberLens' + t, (XC + s * 0.66, 0.66, zf + 0.026), 'z', 0.064, 0.012, 'Lamp_Amber', 'Exterior', segs=36)
        box('TailLight' + t, (XC + s * 1.02 - 0.06, 0.70, B.Z_REAR - 0.02), (XC + s * 1.02 + 0.06, 1.00, B.Z_REAR + 0.005), 'Lamp_Tail', 'Exterior', bevel=0.01)
        box('SideMarker' + t, (XC + s * B.W_HALF - 0.005, 0.80, 0.40), (XC + s * B.W_HALF + 0.005, 0.84, 0.50), 'Lamp_Amber', 'Exterior')
    framed('CentreGrille', XC, 0.72, 0.42, 0.12, zf, ring=0.025, slats=2)
    box('BumperF', (XC - 1.18, 0.34, zf - 0.02), (XC + 1.18, 0.50, zf + 0.12), 'Rim', 'Exterior', bevel=0.04, segs=3)
    box('BumperR', (XC - 1.18, 0.34, B.Z_REAR - 0.12), (XC + 1.18, 0.50, B.Z_REAR + 0.02), 'Rim', 'Exterior', bevel=0.04, segs=3)
    # mirrors on long stalks from the A-pillars
    for s in (-1, 1):
        t = 'R' if s > 0 else 'L'
        xw = XC + s * B.W_HALF
        tube('MirrorStalk' + t, [(xw, 1.70, 3.30), (xw + s * 0.16, 1.72, 3.42), (xw + s * 0.22, 1.92, 3.56)], 0.012, 'Ext_Black', 'Exterior')
        box('MirrorHead' + t, (xw + s * 0.22 - 0.09, 1.76, 3.54), (xw + s * 0.22 + 0.09, 2.04, 3.58), 'Ext_Black', 'Exterior', bevel=0.02)
    # wipers parked along the bottom of each pane (outside)
    for x0, x1 in ((XC - 1.00, B.WS_POST[0] - 0.08), (B.WS_POST[1] + 0.06, 0.86)):
        tube('Wiper%+.2f' % x0, [(x0, B.WS_BOT + 0.04, zf + 0.015), (x1, B.WS_BOT + 0.09, zf + 0.015)], 0.007, 'Ext_Black', 'Exterior')
    # drip rail along the roof edge (PAZ: a thin bright gutter over the windows)
    for s in (-1, 1):
        x = XC + s * (W_of(2.33) + 0.008)
        tube('DripRail%s' % ('R' if s > 0 else 'L'), [(x, 2.33, B.Z_REAR + 0.25), (x, 2.33, B.Z_FRONT - 0.25)], 0.008, 'Chrome', 'Exterior')
    # interior rear-view mirror on its stalk
    tube('RVMStalk', [(-0.05, B.WS_TOP + 0.01, 3.40), (-0.05, 2.15, 3.36)], 0.008, 'Bakelite', 'Cabin')
    box('RVMirror', (-0.16, 2.08, 3.34), (0.06, 2.15, 3.36), 'Bakelite', 'Cabin', bevel=0.01)


def door_leaf(angle_deg=165.0):
    """front-hinged outward swing door (glazed upper + lower panel). Pivot = hinge at the front jamb. Open = 165 deg."""
    z0, z1 = B.DOOR
    w = z1 - z0 - 0.01
    hinge = (B.R_WALL + 0.01, 0.0, z1)
    objs = []
    objs.append(box('DoorLeaf_Low', (B.R_WALL - 0.01, 0.30, z1 - w), (B.R_WALL + 0.02, 1.15, z1), 'Ext_Indigo', 'Door', bevel=0.008))
    objs.append(box('DoorLeaf_Frame', (B.R_WALL - 0.01, 1.15, z1 - w), (B.R_WALL + 0.02, B.DOOR_HEAD - 0.02, z1 - w + 0.05), 'Ext_Cream', 'Door'))
    objs.append(box('DoorLeaf_Frame2', (B.R_WALL - 0.01, 1.15, z1 - 0.05), (B.R_WALL + 0.02, B.DOOR_HEAD - 0.02, z1), 'Ext_Cream', 'Door'))
    objs.append(box('DoorLeaf_Head', (B.R_WALL - 0.01, B.DOOR_HEAD - 0.07, z1 - w), (B.R_WALL + 0.02, B.DOOR_HEAD - 0.02, z1), 'Ext_Cream', 'Door'))
    objs.append(box('DoorLeaf_Mid', (B.R_WALL - 0.01, 1.15, z1 - w), (B.R_WALL + 0.02, 1.20, z1), 'Ext_Silver', 'Door'))
    g = bmesh.new()
    vs = [g.verts.new(U2B(p)) for p in ((B.R_WALL + 0.005, 1.20, z1 - w + 0.05), (B.R_WALL + 0.005, 1.20, z1 - 0.05),
                                        (B.R_WALL + 0.005, B.DOOR_HEAD - 0.07, z1 - 0.05), (B.R_WALL + 0.005, B.DOOR_HEAD - 0.07, z1 - w + 0.05))]
    g.faces.new(vs)
    gl = obj_from_bm('Glass_DoorLeaf', g, ['Glass'], 'Door')
    gl['lb_fse'] = 'BusGlass'
    objs.append(gl)
    piv = U2B(hinge)
    # the leaf points to unity -z from the hinge; +angle about blender z swings it outward (+x) and forward
    R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(angle_deg), 4, 'Z') @ Matrix.Translation(-piv)
    for o in objs:
        o.matrix_world = R @ o.matrix_world
    return objs


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
    door_leaf(165.0 if open_door else 0.0)
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
    return dict(body=body, glass=glass)


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
