"""BronzeMirror 网格：单位直径的汉代博局镜（spec_conventions.md §1）。

运行：  ~/bpy/bin/python make_mesh.py
输出：  Mirrors/Models/BronzeMirror.fbx   （根空物体 BronzeMirror，子物体 BronzeMirror_LOD0/1/2）
        Mirrors/Source/BronzeMirror.blend （参考用）
核对：  verify_mesh.py （重新导入 FBX，写 Docs~/mesh_check.txt）

All geometry is generated in UNITY object space (X east, Y up = mirror face, Z north) and converted
to Blender with  Blender (bx, by, bz) = (-X, -Z, Y)  -- the inverse of what the shared FBX settings
(forward -Z, up Y, baked space transform) plus Unity's right->left-handed import do:
Blender (x, y, z) -> Unity (-x, z, -y)   (same convention as Tentacles/Source/build_library.py).
"""
import math
import os
import sys

import bpy  # noqa: F401  (must come before bmesh in the pip bpy module)
import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                         # .../Mirrors
sys.path.insert(0, os.path.join(HERE, 'lib'))
import export_unity  # noqa: E402  (copy of Tentacles/Source/lib/export_unity.py, unchanged)

FBX_PATH = os.path.join(ROOT, 'Models', 'BronzeMirror.fbx')
BLEND_PATH = os.path.join(HERE, 'BronzeMirror.blend')

# ---------------------------------------------------------------------------------------------
# Spec §1 numbers (D = 1, Unity object space, metres). Change spec_conventions.md first.
# ---------------------------------------------------------------------------------------------
R_FACE = 0.48            # polished face (spherical cap) radius
SAG = 0.015              # cap sagitta (1.5 % D)
RHO = (R_FACE ** 2 + SAG ** 2) / (2 * SAG)   # = 7.6875
R_OUT = 0.50             # outer radius
Y_BAND = 0.002           # rim band top (face side)
CHAMF = 0.001            # rim band chamfers, inner and outer (45 deg)
Y_RIM_BACK = -0.037      # back: wide flat rim
R_RIM_IN = 0.425         # back: wide rim inner edge (top of the slope)
R_SLOPE_IN = 0.415       # back: slope foot
Y_BACK = -0.015          # back: main field
R_KNOB = 0.065           # knob base radius
Y_KNOB_TOP = -0.065      # knob top
KNOB_N = 2.3             # superellipse exponent of the knob profile (2 = ellipse; >2 = fuller "mantou")
HOLE_W = 0.022           # through-hole width (along object Z)
HOLE_H = 0.014           # through-hole height (along Y)
HOLE_YC = -0.030         # through-hole centre height; axis = object X

# Region codes (vertex colour R).
REG_FACE, REG_BAND, REG_SIDE, REG_BACK, REG_KNOB = 0, 1, 2, 3, 4
REG_VALUE = [0.0, 0.25, 0.5, 0.75, 1.0]

# LODs: circumference segments / face radial rings (spec) + our own interior choices.
#   knob_seg  : knob circumference segments (knob is 13 % of the diameter -> half the rim count)
#   knob_rings: rings up the knob profile
#   back_rings: extra rings inside the flat back field (only to keep triangles from being 0.35 m slivers)
LODS = [
    dict(seg=512, rings=64, knob_seg=256, knob_rings=24, back_rings=3),
    dict(seg=256, rings=32, knob_seg=128, knob_rings=12, back_rings=1),
    dict(seg=128, rings=16, knob_seg=64, knob_rings=8, back_rings=0),
]
CAP_POWER = 1.5          # face rings: r = R_FACE * (1 - (1 - t)^p)  -> spacing ~12x finer at the rim than at the centre
SHARP_DEG = 30.0         # edges sharper than this are hard even inside a region (chamfers, hole corners)


def cap_y(r):
    return math.sqrt(RHO * RHO - r * r) - (RHO - SAG)


def knob_profile(k):
    """Knob rings from base (h = 0, r = R_KNOB) to the pole, superellipse |r/a|^n + |h/b|^n = 1."""
    a, b = R_KNOB, Y_BACK - Y_KNOB_TOP
    pts = []
    for j in range(k + 1):
        phi = 0.5 * math.pi * j / k
        c, s = math.cos(phi), math.sin(phi)
        r = a * (c ** (2.0 / KNOB_N)) if j < k else 0.0
        h = b * (s ** (2.0 / KNOB_N))
        pts.append((r, Y_BACK - h))
    return pts


def pow2_at_least(x):
    return 1 << max(0, math.ceil(math.log2(max(x, 1.0))))


def profile(lod):
    """Revolved profile: list of rings (r, y, nseg) and the region of the band between ring i and i+1.

    Runs from the face centre outward, over the rim band, down the side wall and back in along the
    back to the knob base. The knob is built separately (it needs the boolean hole)."""
    N, C = lod['seg'], lod['rings']
    rings, regions = [], []
    # Face: denser toward the rim; sparse segment counts near the centre (power-of-two steps so every
    # coarse vertex lies on a fine ring's spoke) instead of 512 needle triangles round the pole.
    rs = [R_FACE * (1.0 - (1.0 - i / C) ** CAP_POWER) for i in range(C + 1)]
    nmin = max(8, N // 16)
    for i, r in enumerate(rs):
        if i == 0:
            n = 1
        else:
            dr = rs[i] - rs[i - 1]
            n = min(N, max(nmin, pow2_at_least(2 * math.pi * r / (2.0 * dr))))
        rings.append((r, cap_y(r), n))
        if i < C:
            regions.append(REG_FACE)
    # segment counts must not decrease outward
    for i in range(len(rings) - 2, 0, -1):
        if rings[i][2] > rings[i + 1][2]:
            rings[i] = (rings[i][0], rings[i][1], rings[i + 1][2])
    # Rim band (face side): wall 0.001 up, 45 deg chamfer, flat top, 45 deg chamfer.
    for r, y, reg in [(R_FACE, Y_BAND - CHAMF, REG_BAND),
                      (R_FACE + CHAMF, Y_BAND, REG_BAND),
                      (R_OUT - CHAMF, Y_BAND, REG_BAND),
                      (R_OUT, Y_BAND - CHAMF, REG_BAND)]:
        regions.append(reg)
        rings.append((r, y, N))
    # Side wall down to the back rim.
    regions.append(REG_SIDE)
    rings.append((R_OUT, Y_RIM_BACK, N))
    # Back: wide flat rim, slope, main field (optionally subdivided), knob base.
    regions.append(REG_BACK)
    rings.append((R_RIM_IN, Y_RIM_BACK, N))
    regions.append(REG_BACK)
    rings.append((R_SLOPE_IN, Y_BACK, N))
    nb = lod['back_rings']
    for j in range(1, nb + 1):
        t = j / (nb + 1)
        r = R_SLOPE_IN + (R_KNOB - R_SLOPE_IN) * t
        regions.append(REG_BACK)
        rings.append((r, Y_BACK, N))
    regions.append(REG_BACK)
    rings.append((R_KNOB, Y_BACK, lod['knob_seg']))
    return rings, regions


def u2b(X, Y, Z):
    """Unity object space -> Blender."""
    return (-X, -Z, Y)


def ring_coords(r, y, n):
    if n == 1:
        return [u2b(0.0, y, 0.0)]
    return [u2b(r * math.cos(2 * math.pi * j / n), y, r * math.sin(2 * math.pi * j / n)) for j in range(n)]


def strip(bm, va, vb, region, reg_layer):
    """Faces between two concentric rings of power-of-two counts (len(vb) >= len(va), or a pole)."""
    na, nb = len(va), len(vb)
    faces = []
    if na == 1:
        for j in range(nb):
            faces.append(bm.faces.new((va[0], vb[j], vb[(j + 1) % nb])))
    elif nb == 1:
        for j in range(na):
            faces.append(bm.faces.new((va[(j + 1) % na], va[j], vb[0])))
    elif na == nb:
        for j in range(na):
            faces.append(bm.faces.new((va[j], vb[j], vb[(j + 1) % nb], va[(j + 1) % na])))
    else:
        if na > nb:   # walk always from the coarser ring
            return strip_rev(bm, va, vb, region, reg_layer)
        k = nb // na
        for j in range(na):
            a0, a1 = va[j], va[(j + 1) % na]
            fan = [vb[(j * k + m) % nb] for m in range(k + 1)]
            mid = k // 2
            for m in range(mid):
                faces.append(bm.faces.new((a0, fan[m], fan[m + 1])))
            faces.append(bm.faces.new((a0, fan[mid], a1)))
            for m in range(mid, k):
                faces.append(bm.faces.new((a1, fan[m], fan[m + 1])))
    for f in faces:
        f[reg_layer] = region
    return faces


def strip_rev(bm, va, vb, region, reg_layer):
    """Fine ring va -> coarse ring vb."""
    na, nb = len(va), len(vb)
    k = na // nb
    faces = []
    for j in range(nb):
        b0, b1 = vb[j], vb[(j + 1) % nb]
        fan = [va[(j * k + m) % na] for m in range(k + 1)]
        mid = k // 2
        for m in range(mid):
            faces.append(bm.faces.new((b0, fan[m + 1], fan[m])))
        faces.append(bm.faces.new((b0, b1, fan[mid])))
        for m in range(mid, k):
            faces.append(bm.faces.new((b1, fan[m + 1], fan[m])))
    for f in faces:
        f[reg_layer] = region
    return faces


def build_body(lod):
    rings, regions = profile(lod)
    bm = bmesh.new()
    reg = bm.faces.layers.int.new('region')
    vrings = [[bm.verts.new(c) for c in ring_coords(r, y, n)] for (r, y, n) in rings]
    for i in range(len(rings) - 1):
        strip(bm, vrings[i], vrings[i + 1], regions[i], reg)
    return bm, rings


def build_knob(lod, name):
    """Closed knob solid (dome + base disc) minus the X-axis box -> mesh object, base disc removed."""
    k, n = lod['knob_rings'], lod['knob_seg']
    prof = knob_profile(k)
    bm = bmesh.new()
    vr = [[bm.verts.new(c) for c in ring_coords(r, y, (n if r > 0 else 1))] for (r, y) in prof]
    reg = bm.faces.layers.int.new('region')
    for i in range(len(vr) - 1):
        strip_rev(bm, vr[i], vr[i + 1], REG_KNOB, reg) if len(vr[i + 1]) == 1 and False else None
        a, b = vr[i], vr[i + 1]
        if len(b) == 1:
            for j in range(len(a)):
                bm.faces.new((a[(j + 1) % len(a)], a[j], b[0]))[reg] = REG_KNOB
        else:
            for j in range(len(a)):
                bm.faces.new((a[j], b[j], b[(j + 1) % len(b)], a[(j + 1) % len(a)]))[reg] = REG_KNOB
    base = bm.faces.new(list(reversed(vr[0])))
    base[reg] = -1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name + '_knob')
    bm.to_mesh(me)
    bm.free()
    knob = bpy.data.objects.new(name + '_knob', me)
    bpy.context.scene.collection.objects.link(knob)

    # cutter: box along object X (Blender x), width along object Z (Blender y), height along Y (Blender z)
    cb = bmesh.new()
    bmesh.ops.create_cube(cb, size=1.0)
    for v in cb.verts:
        v.co.x *= 4 * R_KNOB
        v.co.y *= HOLE_W
        v.co.z = HOLE_YC + v.co.z * HOLE_H
    cme = bpy.data.meshes.new(name + '_cutter')
    cb.to_mesh(cme)
    cb.free()
    cutter = bpy.data.objects.new(name + '_cutter', cme)
    bpy.context.scene.collection.objects.link(cutter)

    mod = knob.modifiers.new('hole', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    dg = bpy.context.evaluated_depsgraph_get()
    res = bpy.data.meshes.new_from_object(knob.evaluated_get(dg))
    bpy.data.objects.remove(knob)
    bpy.data.objects.remove(cutter)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(cme)

    bm = bmesh.new()
    bm.from_mesh(res)
    bpy.data.meshes.remove(res)
    reg = bm.faces.layers.int.get('region') or bm.faces.layers.int.new('region')
    base_faces = [f for f in bm.faces if all(abs(v.co.z - Y_BACK) < 1e-7 for v in f.verts)]
    bmesh.ops.delete(bm, geom=base_faces, context='FACES_ONLY')
    for f in bm.faces:
        f[reg] = REG_KNOB          # hole walls come from the cutter: same region as the knob
    return bm


def merge_knob(body, knob_bm):
    """Append the knob bmesh into the body bmesh and weld the base ring."""
    reg_b = body.faces.layers.int['region']
    reg_k = knob_bm.faces.layers.int['region']
    vmap = {}
    for v in knob_bm.verts:
        vmap[v] = body.verts.new(v.co)
    for f in knob_bm.faces:
        nf = body.faces.new([vmap[v] for v in f.verts])
        nf[reg_b] = f[reg_k]
    knob_bm.free()
    ring = [v for v in body.verts
            if abs(v.co.z - Y_BACK) < 1e-7 and abs(math.hypot(v.co.x, v.co.y) - R_KNOB) < 1e-6]
    bmesh.ops.remove_doubles(body, verts=ring, dist=1e-6)


def finish(bm):
    """Triangulate, outward normals, hard edges, vertex colour, UV0."""
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='FIXED', ngon_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    reg = bm.faces.layers.int['region']
    cos_sharp = math.cos(math.radians(SHARP_DEG))
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2:
            e.smooth = False
            continue
        f0, f1 = lf
        e.smooth = not (f0[reg] != f1[reg] or f0.normal.dot(f1.normal) < cos_sharp)
    col = bm.loops.layers.float_color.new('Col')
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        rv = REG_VALUE[f[reg]]
        for lp in f.loops:
            lp[col] = (rv, 0.0, 0.0, 1.0)
            bx, by, _ = lp.vert.co
            lp[uv].uv = (-bx + 0.5, -by + 0.5)     # Unity (X, Z) + 0.5
    return bm


def build_lod(i, mat):
    name = 'BronzeMirror_LOD%d' % i
    lod = LODS[i]
    body, rings = build_body(lod)
    merge_knob(body, build_knob(lod, name))
    finish(body)
    me = bpy.data.meshes.new(name)
    body.to_mesh(me)
    body.free()
    if 'region' in me.attributes:
        me.attributes.remove(me.attributes['region'])
    me.color_attributes.active_color = me.color_attributes['Col']
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    face_n = [n for (r, y, n) in rings[:lod['rings'] + 1]]
    print('%s: %d tris, %d verts; face ring segments %s' % (name, tris, len(me.vertices), sorted(set(face_n))))
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    mat = bpy.data.materials.get('M_BronzeMirror') or bpy.data.materials.new('M_BronzeMirror')
    root = bpy.data.objects.new('BronzeMirror', None)
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = 0.1
    sc.collection.objects.link(root)
    obs = [root]
    for i in range(len(LODS)):
        ob = build_lod(i, mat)
        ob.parent = root
        if i > 0:
            ob.hide_render = True
            ob.hide_set(True)
        obs.append(ob)
    os.makedirs(os.path.dirname(FBX_PATH), exist_ok=True)
    for o in obs:
        o.hide_set(False)
    export_unity.export_fbx(FBX_PATH, obs)
    for o in obs[2:]:
        o.hide_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)
    print('wrote', FBX_PATH)
    print('wrote', BLEND_PATH)


if __name__ == '__main__':
    main()
