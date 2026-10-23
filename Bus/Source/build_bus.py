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
    if y <= 0.50:
        t = (0.50 - y) / 0.08
        return B.W_HALF - 0.04 * t * t
    if y <= B.Y_SIDE_ROOF:
        return B.W_HALF - (B.W_HALF - B.W_TOPSIDE) * max(0.0, (y - B.Y_BELT)) / (B.Y_SIDE_ROOF - B.Y_BELT)
    t = min(1.0, (y - B.Y_SIDE_ROOF) / (B.Y_TOP - B.Y_SIDE_ROOF))
    return B.W_TOPSIDE * max(0.0, 1.0 - t ** B.ROOF_N) ** (1.0 / B.ROOF_N)


def Zf_of(y):
    if y <= 0.50:
        t = (0.50 - y) / 0.08
        return B.L_HALF - 0.05 * t * t
    if y <= B.Y_FRONT_ROOF:
        return B.L_HALF
    t = min(1.0, (y - B.Y_FRONT_ROOF) / (B.Y_TOP - B.Y_FRONT_ROOF))
    return B.L_HALF - B.FRONT_DOME * (1.0 - max(0.0, 1.0 - t ** B.ROOF_N) ** (1.0 / B.ROOF_N))


ROWS = sorted(set([0.42, 0.45, 0.50, 0.62, 0.80, 1.00, 1.15, 1.26, 1.28, 1.30, 1.36, 1.55, 1.80, 2.00, 2.18, 2.22, 2.25,
                   2.30, 2.31, 2.36, 2.42, 2.48, 2.53, 2.58, 2.62, 2.655, 2.685, 2.705, 2.72, 2.73, 2.736]))


def side_stations(windows, extra):
    zs = set([-3.36, 3.36] + extra)
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
    xs = sorted(set([-0.90, 0.90] + breaks))
    out = []
    for a, b in zip(xs[:-1], xs[1:]):
        n = max(1, int(math.ceil((b - a) / 0.25)))
        out += [a + (b - a) * k / n for k in range(n)]
    out.append(xs[-1])
    return out


def build_shell():
    """outer skin as a grid of quads: rows = ROWS, columns = perimeter stations. Returns (bm, opening tags)."""
    R_SIDE = side_stations(B.WIN_R, [B.DOOR[0], B.DOOR[1], B.DOOR_POST[0], B.A_PILLAR_R[0], -0.02, 0.08] + list(B.AXLES))
    L_SIDE = side_stations(B.WIN_L, [B.A_PILLAR_L[0]] + list(B.AXLES))
    FRONT = face_stations([B.DEST_BOX[0], B.DEST_BOX[1]])
    REAR = face_stations([B.REAR_WIN[0], B.REAR_WIN[1]])
    NC = 5
    # each column: (segment, normalized param) — the belt-level positions, scaled per ring
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

    def point(col, y):
        seg, v = col
        W, Zf = W_of(y), Zf_of(y)
        Zr = -Zf
        Rc = min(B.RC, W * 0.6, 0.6 * (Zf - 0.0))
        zs0, zs1 = Zr + Rc, Zf - Rc            # straight side span at this ring
        xs = W - Rc

        def side_z(z):
            return zs0 + (z - (-3.36)) / 6.72 * (zs1 - zs0)
        if seg == 'R':
            return (W, y, side_z(v))
        if seg == 'L':
            return (-W, y, side_z(v))
        if seg == 'F':
            return (v / 0.90 * xs, y, Zf)
        if seg == 'Bk':
            return (v / 0.90 * xs, y, Zr)
        a = v * math.pi / 2
        if seg == 'RF':
            return (xs + Rc * math.cos(a), y, zs1 + Rc * math.sin(a))
        if seg == 'LF':
            return (-xs - Rc * math.sin(a), y, zs1 + Rc * math.cos(a))
        if seg == 'LR':
            return (-xs - Rc * math.cos(a), y, zs0 - Rc * math.sin(a))
        if seg == 'RR':
            return (xs + Rc * math.sin(a), y, zs0 - Rc * math.cos(a))

    bm = bmesh.new()
    grid = []
    for y in ROWS:
        grid.append([bm.verts.new(U2B(point(c, y))) for c in cols])
    nC = len(cols)

    def opening(c0, c1, y0, y1):
        """which opening (if any) a face between columns c0..c1 and rows y0..y1 belongs to."""
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
            if zm > B.A_PILLAR_R[1] - 1e-6 and B.WS_BOT < ym < B.WS_TOP:
                return 'Windscreen'
        if s0 == s1 == 'L':
            zm = (v0 + v1) / 2
            for i, (a, b) in enumerate(B.WIN_L):
                if a < zm < b and B.WIN_SILL < ym < B.WIN_HEAD:
                    return 'WinL%d' % i
            if zm > B.A_PILLAR_L[1] - 1e-6 and B.WS_BOT < ym < B.WS_TOP:
                return 'Windscreen'
        if s0 in ('RF', 'F', 'LF') or s1 in ('RF', 'F', 'LF'):
            if (s0, s1) in (('R', 'RF'),) or (s0, s1) in (('LF', 'L'),):
                pass
            if B.WS_BOT < ym < B.WS_TOP:
                return 'Windscreen'
            if s0 == s1 == 'F':
                xm = (v0 + v1) / 2
                if B.DEST_BOX[0] < xm < B.DEST_BOX[1] and B.DEST_BOX[2] < ym < B.DEST_BOX[3]:
                    return 'DestWindow'
        if s0 == s1 == 'Bk':
            xm = (v0 + v1) / 2
            if B.REAR_WIN[0] < xm < B.REAR_WIN[1] and B.REAR_WIN[2] < ym < B.REAR_WIN[3]:
                return 'RearWindow'
        return None

    tags = {}
    paint = bm.faces.layers.int.new('paint')
    for i in range(len(ROWS) - 1):
        for j in range(nC):
            j1 = (j + 1) % nC
            f = bm.faces.new((grid[i][j], grid[i][j1], grid[i + 1][j1], grid[i + 1][j]))
            op = opening(cols[j], cols[j1], ROWS[i], ROWS[i + 1])
            ym = (ROWS[i] + ROWS[i + 1]) / 2
            f.material_index = 0 if ym < 1.26 else (2 if ym < 1.28 else 1)
            if op:
                tags.setdefault(op, []).append(f)
    # caps: roof (top ring) and floor pan (bottom ring)
    top = bm.faces.new(grid[-1])
    top.material_index = 1
    bot = bm.faces.new(list(reversed(grid[0])))
    bot.material_index = 0
    bm.normal_update()
    # make normals point outward
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
                    n = v.normal
                    vmap[v.index] = g.verts.new(v.co - n * GLASS_INSET)
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
    # wheel arches + skylight hatch through the roof
    for i, z in enumerate(B.AXLES):
        c = cylinder('ArchCut%d' % i, (0, 0.40, z), 'x', B.ARCH_R, 2.6, 'Seal', segs=40)
        boolean(body, c)
        bpy.data.objects.remove(c)
    sx, sy, sz = B.SKY_C
    h = B.SKY_HALF
    c = box('HatchCut', (sx - h, 2.50, sz - h), (sx + h, 3.0, sz + h), 'Seal')
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
def ceil_y(x):
    """flat ceiling to |x| 0.90 (the hatch is wholly in the flat), then a tight cove down to the window head."""
    a = max(0.0, abs(x) - 0.90) / 0.085
    return B.CEIL_Y - 0.21 * min(1.0, a) ** 1.4


def ceiling():
    """perforated-board ceiling liner: flat 2.45 over the aisle, coves down to the window head; hole for the hatch."""
    xs = sorted(set([-0.985 + 1.97 * k / 40 for k in range(41)] + [-0.95, -0.92, 0.92, 0.95]))
    zs = [-3.44 + 6.6 * k / 66 for k in range(67)]            # to z 3.16 (the front header)

    yc = ceil_y
    bm = bmesh.new()
    V = [[bm.verts.new(U2B((x, yc(x), z))) for x in xs] for z in zs]
    sx, _, sz = B.SKY_C
    h = B.SKY_HALF
    for i in range(len(zs) - 1):
        for j in range(len(xs) - 1):
            xm, zm = (xs[j] + xs[j + 1]) / 2, (zs[i] + zs[i + 1]) / 2
            if abs(xm - sx) < h and abs(zm - sz) < h:
                continue
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    ob = obj_from_bm('Ceiling', bm, ['Int_Ceiling'])
    smooth_by_angle(ob, 30)
    # front header (vertical panel above the windscreen, inside) with the blind box behind it
    box('Header', (-0.99, B.WS_TOP + 0.005, 3.14), (0.99, B.CEIL_Y + 0.01, 3.18), 'Int_Enamel')
    box('HeaderLip', (-0.99, B.WS_TOP - 0.01, 3.14), (0.99, B.WS_TOP + 0.02, 3.47), 'Seal')
    # the blind: back of the destination box seen through the gap above the header? no: behind the header (bible 4.7)
    box('DestBlind', (B.DEST_BOX[0], B.DEST_BOX[2] - 0.01, 3.44), (B.DEST_BOX[1], B.DEST_BOX[3] + 0.01, 3.452), 'Linen')
    # hatch well (4 walls from the ceiling up to the glass) + aluminium frame + glass at SKY_C.y
    fw = 0.04
    for nm, lo, hi in (('HatchWall0', (sx - h - fw, B.CEIL_Y - 0.012, sz - h - fw), (sx + h + fw, 2.66, sz - h)),
                       ('HatchWall1', (sx - h - fw, B.CEIL_Y - 0.012, sz + h), (sx + h + fw, 2.66, sz + h + fw)),
                       ('HatchWall2', (sx - h - fw, B.CEIL_Y - 0.012, sz - h), (sx - h, 2.66, sz + h)),
                       ('HatchWall3', (sx + h, B.CEIL_Y - 0.012, sz - h), (sx + h + fw, 2.66, sz + h))):
        box(nm, lo, hi, 'Alu')
    g = bmesh.new()
    vs = [g.verts.new(U2B(p)) for p in ((sx - h, B.SKY_C[1], sz - h), (sx + h, B.SKY_C[1], sz - h),
                                        (sx + h, B.SKY_C[1], sz + h), (sx - h, B.SKY_C[1], sz + h))]
    g.faces.new(vs)
    sg = obj_from_bm('Glass_Skylight', g, ['Glass'], 'Glass')
    sg['lb_fse'] = 'BusGlass'
    # outside: raised hatch frame on the roof
    for nm, lo, hi in (('HatchOut0', (sx - h - 0.06, 2.66, sz - h - 0.06), (sx + h + 0.06, 2.77, sz - h)),
                       ('HatchOut1', (sx - h - 0.06, 2.66, sz + h), (sx + h + 0.06, 2.77, sz + h + 0.06)),
                       ('HatchOut2', (sx - h - 0.06, 2.66, sz - h), (sx - h, 2.77, sz + h)),
                       ('HatchOut3', (sx + h, 2.66, sz - h), (sx + h + 0.06, 2.77, sz + h))):
        box(nm, lo, hi, 'Alu', bevel=0.01)


def floor():
    sx0, sx1 = 0.58, 1.04
    parts = [((-1.0, 0.56, -3.44), (1.0, B.FLOOR_Y, B.DOOR[0])),
             ((-1.0, 0.56, B.DOOR[0]), (sx0, B.FLOOR_Y, B.DASH_Z0 + 0.02))]
    for i, (lo, hi) in enumerate(parts):
        box('Floor%d' % i, lo, hi, 'Floor')
    # door steps: step box below the body + an intermediate tread; aluminium nosings with the yellow strip
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
    # wheel boxes inside (the hero seat sits on the front one)
    for i, z in enumerate(B.AXLES):
        for s in (-1, 1):
            if s > 0 and i == 0:
                box('WheelBox%d%s' % (i, 'R'), (0.56, B.FLOOR_Y, z - 0.50), (1.0, 0.94, z + 0.45), 'Int_Enamel', bevel=0.03)
            else:
                lo, hi = (s * 0.56, B.FLOOR_Y, z - 0.50), (s * 1.0, 0.94, z + 0.50)
                box('WheelBox%d%s' % (i, 'R' if s > 0 else 'L'), tuple(min(a, b) for a, b in zip(lo, hi)),
                    tuple(max(a, b) for a, b in zip(lo, hi)), 'Int_Enamel', bevel=0.03)


def seat(name, x0, x1, back_z, double=False, worn=1.0, cushion_y=None, collection='Seats'):
    """bus seat: cushion, reclined backrest, chrome grab rail on top, frame + legs. back_z = back face of the backrest."""
    cy = cushion_y or (B.FLOOR_Y + B.SEAT_H)
    objs = []
    objs.append(box(name + '_Cushion', (x0 + 0.01, cy - 0.10, back_z + 0.06), (x1 - 0.01, cy, back_z + 0.50), 'Vinyl', collection, bevel=0.035, segs=3))
    # backrest: a slab tilted back 12 deg about its bottom edge
    bk = box(name + '_Back', (x0 + 0.01, cy - 0.02, back_z), (x1 - 0.01, cy + 0.60, back_z + 0.10), 'Vinyl', collection, bevel=0.035, segs=3)
    piv = U2B((0, cy, back_z + 0.08))
    bk.matrix_world = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-12), 4, 'X') @ Matrix.Translation(-piv)
    objs.append(bk)
    top_y = cy + 0.60
    tz = back_z + 0.08 - 0.60 * math.sin(math.radians(12))
    ty = cy - 0.02 + 0.60 * math.cos(math.radians(12))
    objs.append(tube(name + '_Rail', [(x0 + 0.04, ty - 0.02, tz - 0.02), (x0 + 0.04, ty + 0.04, tz - 0.04),
                                      (x1 - 0.04, ty + 0.04, tz - 0.04), (x1 - 0.04, ty - 0.02, tz - 0.02)], 0.011, 'Chrome', collection))
    objs.append(box(name + '_Frame', (x0 + 0.03, cy - 0.16, back_z + 0.10), (x1 - 0.03, cy - 0.10, back_z + 0.46), 'SeatFrame', collection))
    for xx in ((x0 + 0.08,) if not double else (x0 + 0.08, (x0 + x1) / 2)):
        if cy - 0.16 > B.FLOOR_Y + 0.05:
            objs.append(box(name + '_Leg%.2f' % xx, (xx, B.FLOOR_Y, back_z + 0.36), (xx + 0.04, cy - 0.16, back_z + 0.40), 'SeatFrame', collection))
    return objs


def seats():
    hero = None
    for i, bz in enumerate(B.RIGHT_ROWS):
        cy = None
        if i == 0:
            cy = 0.94 + 0.08        # on the front wheel box
        o = seat('SeatR%d' % i, B.SEAT_R_X[0], B.SEAT_R_X[1], bz, cushion_y=cy)
        if i == 0:
            hero = o
    for i, bz in enumerate(B.LEFT_ROWS):
        seat('SeatL%d' % i, B.SEAT_L_X[0], B.SEAT_L_X[1], bz, double=True,
             cushion_y=(0.94 + 0.08) if abs(bz + 0.45 - B.AXLES[1]) < 0.55 else None)
    seat('RearBench', -0.97, 0.97, B.REAR_BENCH_Z, double=True)
    # driver's seat (oldest), on a pedestal
    dx, dz = B.DRIVER_SEAT
    seat('DriverSeat', dx - 0.25, dx + 0.25, dz - 0.30, cushion_y=B.FLOOR_Y + 0.46)
    box('DriverPedestal', (dx - 0.22, B.FLOOR_Y, dz - 0.20), (dx + 0.22, B.FLOOR_Y + 0.30, dz + 0.15), 'SeatFrame', 'Seats')
    return hero


def driver_area():
    # dashboard: a moulded plastic shelf across the front, sloping top; instrument binnacle in front of the wheel
    x0, x1 = -0.99, 0.99
    bm = bmesh.new()
    prof = [(B.DASH_Z0, 0.95), (B.DASH_Z0, B.DASH_TOP - 0.04), (B.DASH_Z0 + 0.06, B.DASH_TOP), (3.44, B.WS_BOT - 0.01), (3.44, 0.95)]
    left = [bm.verts.new(U2B((x0, y, z))) for z, y in prof]
    right = [bm.verts.new(U2B((x1, y, z))) for z, y in prof]
    for k in range(len(prof) - 1):
        bm.faces.new((left[k], left[k + 1], right[k + 1], right[k]))
    bm.faces.new(list(reversed(left)))
    bm.faces.new(right)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    d = obj_from_bm('Dashboard', bm, ['Dash'], 'Cabin')
    # the door-side half of the dash is cut away above the step well
    box('DashLowerL', (x0, B.FLOOR_Y, B.DASH_Z0 + 0.04), (0.56, 0.95, 3.44), 'Dash', 'Cabin')
    wx, wy, wz = B.WHEEL_C
    box('Binnacle', (wx - 0.17, B.DASH_TOP - 0.02, B.DASH_Z0 - 0.02), (wx + 0.17, B.DASH_TOP + 0.09, B.DASH_Z0 + 0.14), 'Dash', 'Cabin', bevel=0.02)
    box('Gauges', (wx - 0.14, B.DASH_TOP + 0.005, B.DASH_Z0 - 0.025), (wx + 0.14, B.DASH_TOP + 0.075, B.DASH_Z0 - 0.02), 'Ext_Black', 'Cabin')
    # steering column + thin big bakelite wheel (tilted, bus-style)
    tilt = math.radians(B.WHEEL_TILT)
    n = (0.0, math.cos(tilt), -math.sin(tilt))       # wheel normal: up and back toward the driver
    col_base = (wx, 0.80, wz + 0.30)
    tube('SteeringColumn', [col_base, (wx, wy, wz)], 0.03, 'Dash', 'Cabin')
    # rim as a torus-ish ring
    u = Vector((1, 0, 0))
    vv = Vector((0, -n[2], n[1]))       # in-plane vector (unity) perpendicular to x and n
    ring = [(wx + B.WHEEL_RIM_R * math.cos(a) * u.x + B.WHEEL_RIM_R * math.sin(a) * vv.x,
             wy + B.WHEEL_RIM_R * math.sin(a) * vv.y,
             wz + B.WHEEL_RIM_R * math.sin(a) * vv.z) for a in [2 * math.pi * k / 48 for k in range(48)]]
    tube('SteeringWheel', ring, 0.014, 'Bakelite', 'Cabin', closed=True)
    for a in (math.radians(200), math.radians(340), math.radians(90)):
        p = (wx + B.WHEEL_RIM_R * math.cos(a), wy + B.WHEEL_RIM_R * math.sin(a) * vv.y, wz + B.WHEEL_RIM_R * math.sin(a) * vv.z)
        tube('SteeringSpoke%d' % int(math.degrees(a)), [(wx, wy, wz), p], 0.010, 'Bakelite', 'Cabin')
    cylinder('SteeringHub', (wx, wy, wz), n, 0.05, 0.03, 'Bakelite', 'Cabin', segs=24)
    # gear lever
    tube('GearLever', [(wx + 0.38, B.FLOOR_Y, wz - 0.45), (wx + 0.42, 1.10, wz - 0.55)], 0.012, 'Steel', 'Cabin')
    cylinder('GearKnob', (wx + 0.42, 1.12, wz - 0.55), 'y', 0.025, 0.05, 'Bakelite', 'Cabin', segs=16)


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


def poles_and_guard():
    # guard panel in front of the hero seat (knees behind it); lower enamel, upper rail
    gz = B.GUARD_Z
    box('GuardPanel', (0.56, B.FLOOR_Y, gz - 0.02), (0.99, 1.20, gz + 0.01), 'Int_Enamel', 'Cabin', bevel=0.005)
    tube('GuardRail', [(0.99, 1.24, gz), (0.58, 1.24, gz), (0.58, B.FLOOR_Y, gz)], 0.016, 'Steel', 'Cabin')
    # vertical grab handle on the door's rear post (hidden behind the post from the hero seat)
    tube('DoorGrab', [(0.95, 0.95, B.DOOR_POST[0] - 0.02), (0.92, 1.0, B.DOOR_POST[0] - 0.05), (0.92, 1.90, B.DOOR_POST[0] - 0.05),
                      (0.95, 1.95, B.DOOR_POST[0] - 0.02)], 0.016, 'Steel', 'Cabin')
    # overhead grab rails along the aisle + stanchions at every second row on the aisle side
    for x in (-0.16, 0.36):
        tube('Rail%+.2f' % x, [(x, 2.16, -3.2), (x, 2.16, 1.95)], 0.016, 'Steel', 'Cabin')
    for i, bz in enumerate(B.RIGHT_ROWS[1::2]):
        tube('PoleR%d' % i, [(0.30, B.FLOOR_Y, bz - 0.03), (0.30, B.CEIL_Y, bz - 0.03)], 0.016, 'Steel', 'Cabin')
    for i, bz in enumerate(B.LEFT_ROWS[1::2]):
        tube('PoleL%d' % i, [(-0.10, B.FLOOR_Y, bz - 0.03), (-0.10, B.CEIL_Y, bz - 0.03)], 0.016, 'Steel', 'Cabin')
    # the stanchion behind the driver (where the radio used to be in v1)
    tube('PoleDriver', [(-0.12, B.FLOOR_Y, 2.20), (-0.12, B.CEIL_Y, 2.20)], 0.016, 'Steel', 'Cabin')


def tubes():
    """2 x 5 tube lights in diffusers (bible 4.3)."""
    out = []
    for side, x in (('L', B.TUBE_X[0]), ('R', B.TUBE_X[1])):
        zl = B.TUBE_Z_L if side == 'L' else B.TUBE_Z
        for i, (z0, z1) in enumerate(zl):
            yc = ceil_y(x)
            o = box('Tube%s%d' % (side, i), (x - 0.06, yc - 0.045, z0 + 0.02), (x + 0.06, yc - 0.002, z1 - 0.02), 'TubeDiffuser', 'Lights', bevel=0.02, segs=3)
            out.append(o)
    return out


def curtains():
    """bible 4.5: 3 tied half, 5 loose, the hero's fully open. Simple pleated panels hung from a rail at the window head."""
    wins = [('R', z0, z1) for z0, z1 in B.WIN_R[1:]] + [('L', z0, z1) for z0, z1 in B.WIN_L[1:]]
    state = ['tied', 'loose', 'loose', 'tied', 'loose', 'tied', 'loose', 'loose', 'loose']
    for k, (side, z0, z1) in enumerate(wins):
        s = 1 if side == 'R' else -1
        x = s * 0.955
        tube('CurtainRail%s%d' % (side, k), [(x, 2.20, z0), (x, 2.20, z1)], 0.006, 'Alu', 'Curtains')
        st = state[k % len(state)]
        width = 0.34 if st == 'tied' else 0.42
        for end, zz in (('a', z0 + width / 2), ('b', z1 - width / 2)):
            bm = bmesh.new()
            nU, nV = 16, 10
            ybot = 1.42 if st == 'tied' else 1.32
            V = []
            for i in range(nV + 1):
                yy = 2.19 - (2.19 - ybot) * i / nV
                pinch = 1.0 if st == 'loose' else (1.0 - 0.55 * math.sin(math.pi * min(1.0, i / nV / 0.75)) ** 2)
                row = []
                for j in range(nU + 1):
                    u = (j / nU - 0.5) * width * pinch
                    pleat = 0.012 * math.sin(j * math.pi * 1.0) * (0.6 + 0.4 * pinch)
                    row.append(bm.verts.new(U2B((x - s * (0.015 + pleat), yy, zz + u))))
                V.append(row)
            for i in range(nV):
                for j in range(nU):
                    bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
            ob = obj_from_bm('Curtain%s%d%s' % (side, k, end), bm, ['Curtain'], 'Curtains')
            ob['lb_curtain_state'] = st
    # the hero's curtain: fully open, bunched at the rear end of window R1
    z0, z1 = B.WIN_R[0]
    tube('CurtainRailR1', [(0.955, 2.20, z0), (0.955, 2.20, z1)], 0.006, 'Alu', 'Curtains')
    box('CurtainHero', (0.925, 1.36, z0 + 0.02), (0.975, 2.19, z0 + 0.16), 'Curtain', 'Curtains', bevel=0.02)


# ------------------------------------------------------------------------------------------------ exterior
def exterior():
    # wheels: tyre (torus-ish cylinder with bevel), cream-painted rim, hub
    for i, z in enumerate(B.AXLES):
        for s in (-1, 1):
            x = s * B.TRACK_HALF
            cylinder('Tyre%d%s' % (i, 'R' if s > 0 else 'L'), (x, B.WHEEL_R, z), 'x', B.WHEEL_R, B.WHEEL_W, 'Tyre', 'Exterior', segs=40, bevel=0.06)
            cylinder('Rim%d%s' % (i, 'R' if s > 0 else 'L'), (x + s * 0.09, B.WHEEL_R, z), 'x', 0.25, 0.05, 'Rim', 'Exterior', segs=32, bevel=0.01)
            cylinder('Hub%d%s' % (i, 'R' if s > 0 else 'L'), (x + s * 0.12, B.WHEEL_R, z), 'x', 0.09, 0.04, 'Chrome', 'Exterior', segs=24)
    # bumpers
    box('BumperF', (-1.02, 0.36, 3.49), (1.02, 0.52, 3.62), 'Chrome', 'Exterior', bevel=0.03)
    box('BumperR', (-1.02, 0.36, -3.62), (1.02, 0.52, -3.49), 'Chrome', 'Exterior', bevel=0.03)
    # grille + round headlights (two each side) + amber indicators
    box('Grille', (-0.55, 0.62, 3.499), (0.55, 0.95, 3.52), 'Ext_Black', 'Exterior', bevel=0.01)
    for s in (-1, 1):
        for k, x in enumerate((0.70, 0.86)):
            cylinder('HeadRing%d%s' % (k, 'R' if s > 0 else 'L'), (s * x, 0.80, 3.505), 'z', 0.075, 0.03, 'Chrome', 'Exterior', segs=32)
            cylinder('Headlight%d%s' % (k, 'R' if s > 0 else 'L'), (s * x, 0.80, 3.515), 'z', 0.065, 0.02, 'Lamp_Head', 'Exterior', segs=32)
        box('Indicator%s' % ('R' if s > 0 else 'L'), (s * 0.70 - 0.06, 0.60, 3.50), (s * 0.70 + 0.06, 0.66, 3.52), 'Lamp_Amber', 'Exterior', bevel=0.005)
        box('TailLight%s' % ('R' if s > 0 else 'L'), (s * 0.90 - 0.07, 0.62, -3.52), (s * 0.90 + 0.07, 0.92, -3.50), 'Lamp_Tail', 'Exterior', bevel=0.008)
        box('SideMarker%s' % ('R' if s > 0 else 'L'), (s * 1.04 - 0.005, 0.70, 0.40), (s * 1.04 + 0.005, 0.74, 0.50), 'Lamp_Amber', 'Exterior')
    # mirrors on stalks
    for s in (-1, 1):
        base = (s * 1.04, 1.70, 3.30)
        tip = (s * 1.24, 1.92, 3.55)
        tube('MirrorStalk%s' % ('R' if s > 0 else 'L'), [base, (s * 1.20, 1.72, 3.40), tip], 0.012, 'Ext_Black', 'Exterior')
        box('MirrorHead%s' % ('R' if s > 0 else 'L'), (s * 1.24 - 0.09, 1.76, 3.54), (s * 1.24 + 0.09, 2.02, 3.58), 'Ext_Black', 'Exterior', bevel=0.02)
    # wipers parked along the windscreen bottom (outside)
    for x0, x1 in ((-0.90, -0.12), (0.06, 0.84)):
        tube('Wiper%+.2f' % x0, [(x0, B.WS_BOT + 0.04, 3.515), (x1, B.WS_BOT + 0.09, 3.515)], 0.007, 'Ext_Black', 'Exterior')
    # interior rear-view mirror on its stalk
    tube('RVMStalk', [(-0.05, B.WS_TOP + 0.01, 3.40), (-0.05, 2.15, 3.36)], 0.008, 'Bakelite', 'Cabin')
    box('RVMirror', (-0.16, 2.08, 3.34), (0.06, 2.15, 3.36), 'Bakelite', 'Cabin', bevel=0.01)


def door_leaf(angle_deg=165.0):
    """front-hinged outward swing door (glazed upper + lower panel). Pivot = hinge at the front jamb. Open = 165 deg."""
    z0, z1 = B.DOOR
    w = z1 - z0 - 0.01
    hinge = (B.W_HALF + 0.01, 0.0, z1)
    objs = []
    objs.append(box('DoorLeaf_Low', (B.W_HALF - 0.01, 0.30, z1 - w), (B.W_HALF + 0.02, 1.15, z1), 'Ext_Indigo', 'Door', bevel=0.008))
    objs.append(box('DoorLeaf_Frame', (B.W_HALF - 0.01, 1.15, z1 - w), (B.W_HALF + 0.02, B.DOOR_HEAD - 0.02, z1 - w + 0.05), 'Ext_Cream', 'Door'))
    objs.append(box('DoorLeaf_Frame2', (B.W_HALF - 0.01, 1.15, z1 - 0.05), (B.W_HALF + 0.02, B.DOOR_HEAD - 0.02, z1), 'Ext_Cream', 'Door'))
    objs.append(box('DoorLeaf_Head', (B.W_HALF - 0.01, B.DOOR_HEAD - 0.07, z1 - w), (B.W_HALF + 0.02, B.DOOR_HEAD - 0.02, z1), 'Ext_Cream', 'Door'))
    objs.append(box('DoorLeaf_Mid', (B.W_HALF - 0.01, 1.15, z1 - w), (B.W_HALF + 0.02, 1.20, z1), 'Ext_Silver', 'Door'))
    g = bmesh.new()
    vs = [g.verts.new(U2B(p)) for p in ((B.W_HALF + 0.005, 1.20, z1 - w + 0.05), (B.W_HALF + 0.005, 1.20, z1 - 0.05),
                                        (B.W_HALF + 0.005, B.DOOR_HEAD - 0.07, z1 - 0.05), (B.W_HALF + 0.005, B.DOOR_HEAD - 0.07, z1 - w + 0.05))]
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
