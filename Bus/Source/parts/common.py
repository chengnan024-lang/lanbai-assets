# -*- coding: utf-8 -*-
"""D-36 零件的共用几何：软包（细分笼子）、带圆角弯的管子、沿路径的滚边 / 管子扫掠。

坐标一律是 Unity 车局部（米，x 右 y 上 z 前），进 Blender 时用 build_bus.U2B。
所有东西都是“真的”倒角 / 圆角：没有刀口边（D-36 #2）。离眼 2 m 内的圆管 ≥ 16 段（SIDES_NEAR）。
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import build_bus as BB

SIDES_NEAR = 20          # round tubes within 2 m of an eye (D-36: >= 16)
SIDES_FAR = 12


# ------------------------------------------------------------------------------------------------ meshes
def finish(ob, smooth=True, auto_smooth_deg=None):
    """shade smooth (optionally with a sharp-angle split, done by edge split so it survives FBX)."""
    for p in ob.data.polygons:
        p.use_smooth = smooth
    if auto_smooth_deg is not None:
        md = ob.modifiers.new('es', 'EDGE_SPLIT')
        md.split_angle = math.radians(auto_smooth_deg)
        md.use_edge_sharp = True
        apply_mods(ob)
    return ob


def apply_mods(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def cage_pad(name, lo, hi, m, collection='Seats', edge=0.03, n=(6, 3, 6), crown=(0.0, 0.0, 0.0, 0.0),
             levels=2, roll_front=0.0, sag=0.0, lines=None, deform=None):
    """upholstered pad as a Catmull-Clark cage: a box lattice whose first interior lines sit 'edge' in from every face,
    so the subdivided surface rounds every edge with a radius of about 'edge' (a soft sewn edge, never a bevel facet).
    lo, hi: Unity box. n = interior divisions (x, y, z) of the middle span.
    crown = (top +y, front +z, back -z, sides +-x) bulges in metres (applied as a smooth bump on the cage).
    roll_front: the front-top edge rolls forward/down (a 'waterfall' cushion front), metres.
    sag: the top dips in the middle of each half (worn seat), metres.
    lines: optional (X, Y, Z) explicit lattice coordinates (metres from the box centre, ascending, ends = +-half) -
           extra lines where a seam / channel / dent needs them.
    deform(face, i, j, k, x, y, z, half) -> (x, y, z): a last per-vertex shaping hook (metres from the centre);
           face is a set of 'x-', 'x+', 'y-', 'y+', 'z-', 'z+' the vertex lies on."""
    lo, hi = np.array(lo, float), np.array(hi, float)
    c, half = (lo + hi) / 2, (hi - lo) / 2

    def axis_lines(h, k, e):
        mid = np.linspace(-(h - e), h - e, k + 1)
        return np.concatenate([[-h], mid, [h]])

    ex, ey, ez = edge if isinstance(edge, (tuple, list)) else (edge, edge, edge)
    if lines is not None:
        X, Y, Z = (np.array(l, float) for l in lines)
    else:
        X = axis_lines(half[0], n[0], min(ex, half[0] * 0.45))
        Y = axis_lines(half[1], n[1], min(ey, half[1] * 0.45))
        Z = axis_lines(half[2], n[2], min(ez, half[2] * 0.45))
    bm = bmesh.new()
    vid = {}

    def vert(i, j, k):
        key = (i, j, k)
        if key not in vid:
            x, y, z = X[i], Y[j], Z[k]
            ux, uy, uz = x / half[0], y / half[1], z / half[2]
            fx, fz, fy = 1 - min(1, ux * ux), 1 - min(1, uz * uz), 1 - min(1, uy * uy)
            if j == len(Y) - 1:
                y += crown[0] * fx * fz - sag * fx * fz
            if k == len(Z) - 1:
                z += crown[1] * fx * fy
            if k == 0:
                z -= crown[2] * fx * fy
            if i in (0, len(X) - 1):
                x += math.copysign(crown[3] * fy * fz, x)
            if roll_front and k >= len(Z) - 2 and j >= len(Y) - 2:
                z += roll_front * 0.5
                y -= roll_front
            if deform is not None:
                face = set()
                if i == 0: face.add('x-')
                if i == len(X) - 1: face.add('x+')
                if j == 0: face.add('y-')
                if j == len(Y) - 1: face.add('y+')
                if k == 0: face.add('z-')
                if k == len(Z) - 1: face.add('z+')
                x, y, z = deform(face, i, j, k, x, y, z, half)
            vid[key] = bm.verts.new(BB.U2B(tuple(c + np.array([x, y, z]))))
        return vid[key]

    nx, ny, nz = len(X), len(Y), len(Z)
    faces = []
    for j in range(ny - 1):
        for k in range(nz - 1):
            faces.append((vert(0, j, k), vert(0, j, k + 1), vert(0, j + 1, k + 1), vert(0, j + 1, k)))
            faces.append((vert(nx - 1, j, k), vert(nx - 1, j + 1, k), vert(nx - 1, j + 1, k + 1), vert(nx - 1, j, k + 1)))
    for i in range(nx - 1):
        for k in range(nz - 1):
            faces.append((vert(i, 0, k), vert(i + 1, 0, k), vert(i + 1, 0, k + 1), vert(i, 0, k + 1)))
            faces.append((vert(i, ny - 1, k), vert(i, ny - 1, k + 1), vert(i + 1, ny - 1, k + 1), vert(i + 1, ny - 1, k)))
        for j in range(ny - 1):
            faces.append((vert(i, j, 0), vert(i, j + 1, 0), vert(i + 1, j + 1, 0), vert(i + 1, j, 0)))
            faces.append((vert(i, j, nz - 1), vert(i + 1, j, nz - 1), vert(i + 1, j + 1, nz - 1), vert(i, j + 1, nz - 1)))
    for f in faces:
        bm.faces.new(f)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = BB.obj_from_bm(name, bm, [m], collection)
    if levels:
        md = ob.modifiers.new('sub', 'SUBSURF')
        md.levels = md.render_levels = levels
        apply_mods(ob)
    return finish(ob)


# ------------------------------------------------------------------------------------------------ tubes
def fillet_path(pts, radius, seg_per_90=8):
    """polyline (Unity points) -> the same path with every interior corner rounded by an arc of 'radius'
    (a real tube bender: the bend radius is ~2-3 x the tube diameter)."""
    P = [np.array(p, float) for p in pts]
    if len(P) < 3 or radius <= 0:
        return P
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d0, d1 = (a - b), (c - b)
        l0, l1 = np.linalg.norm(d0), np.linalg.norm(d1)
        d0, d1 = d0 / l0, d1 / l1
        cosang = np.clip(np.dot(d0, d1), -1, 1)
        ang = math.acos(cosang)                       # interior angle
        if ang > math.pi - 1e-3:
            out.append(b)
            continue
        t = radius / math.tan(ang / 2)
        t = min(t, 0.45 * l0, 0.45 * l1)
        r = t * math.tan(ang / 2)
        p0, p1 = b + d0 * t, b + d1 * t
        bis = d0 + d1
        bis /= np.linalg.norm(bis)
        cen = b + bis * (r / math.sin(ang / 2))
        v0, v1 = p0 - cen, p1 - cen
        turn = math.pi - ang
        n = max(2, int(math.ceil(seg_per_90 * turn / (math.pi / 2))))
        # slerp v0 -> v1 about the centre
        for k in range(n + 1):
            s = k / n
            w = math.sin((1 - s) * turn) / math.sin(turn), math.sin(s * turn) / math.sin(turn)
            out.append(cen + w[0] * v0 + w[1] * v1)
    out.append(P[-1])
    return out


def sweep(name, pts, r, m, collection='Seats', sides=SIDES_NEAR, closed=False, caps=True, bend=0.0, seg_per_90=8,
          profile=None):
    """sweep a circle (or a 'profile' list of (x, y) in the tube's normal plane, metres) along a Unity path with
    parallel-transport frames. bend > 0 fillets the corners first. Smooth-shaded, capped with a small dome-less
    round cap (a bevelled disc)."""
    P = fillet_path(pts, bend, seg_per_90) if bend > 0 else [np.array(p, float) for p in pts]
    if closed and np.linalg.norm(P[0] - P[-1]) < 1e-6:
        P = P[:-1]
    n = len(P)
    T = []
    for i in range(n):
        if closed:
            t = P[(i + 1) % n] - P[i - 1]
        else:
            t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        T.append(t / max(np.linalg.norm(t), 1e-12))
    up = np.array([0.0, 1.0, 0.0]) if abs(T[0][1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    N = [np.cross(T[0], up)]
    N[0] /= np.linalg.norm(N[0])
    for i in range(1, n):
        v = N[-1] - np.dot(N[-1], T[i]) * T[i]
        N.append(v / max(np.linalg.norm(v), 1e-12))
    if profile is None:
        profile = [(r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
    bm = bmesh.new()
    rings = []
    for i in range(n):
        Bv = np.cross(T[i], N[i])
        rings.append([bm.verts.new(BB.U2B(tuple(P[i] + N[i] * px + Bv * py))) for px, py in profile])
    S = len(profile)
    for i in range(n - 1 + (1 if closed else 0)):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(S):
            bm.faces.new((a[k], a[(k + 1) % S], b[(k + 1) % S], b[k]))
    if caps and not closed:
        for ring, sgn in ((rings[0], -1), (rings[-1], 1)):
            f = bm.faces.new(ring if sgn > 0 else list(reversed(ring)))
            # a small inset + push makes the cap read as a rounded tube end, not a knife-cut disc
            res = bmesh.ops.inset_individual(bm, faces=[f], thickness=r * 0.25, depth=0.0)
            bmesh.ops.inset_individual(bm, faces=[f], thickness=r * 0.35, depth=0.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = BB.obj_from_bm(name, bm, [m], collection)
    return finish(ob)


def rrect_path(cx, cz, hw, hd, r, y, n_arc=8):
    """a rounded rectangle in a horizontal plane (Unity x/z), as a closed list of points."""
    pts = []
    for (sx, sz, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccz = cx + sx * (hw - r), cz + sz * (hd - r)
        for k in range(n_arc + 1):
            a = math.radians(a0 + 90 * k / n_arc)
            pts.append((ccx + r * math.cos(a), y, ccz + r * math.sin(a)))
    return pts


def transform(objs, M):
    """apply a Blender-space 4x4 to objects (e.g. a backrest's recline)."""
    for o in objs:
        o.matrix_world = M @ o.matrix_world


def resample(pts, step):
    """a polyline resampled to ~'step' metre spacing (keeps the ends)."""
    P = [np.array(p, float) for p in pts]
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return out


def drape(ob, pts, offset=0.0, from_y=3.0):
    """drop each (x, ?, z) Unity point straight down onto the mesh 'ob' (its top surface); returns Unity points at the
    hit + offset along y. Points that miss keep their y."""
    from mathutils.bvhtree import BVHTree
    M = ob.matrix_world
    me = ob.data
    bvh = BVHTree.FromPolygons([M @ v.co for v in me.vertices], [list(p.vertices) for p in me.polygons], all_triangles=False)
    out = []
    for p in pts:
        o = Vector(BB.U2B((p[0], from_y, p[2])))
        hit = bvh.ray_cast(o, Vector((0, 0, -1)), 10.0)
        if hit[0] is None:
            raise RuntimeError('drape: no surface under %s on %s' % (p, ob.name))
        y = hit[0].z + offset
        out.append((p[0], y, p[2]))
    return out
