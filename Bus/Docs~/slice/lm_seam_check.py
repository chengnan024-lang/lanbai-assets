# -*- coding: utf-8 -*-
"""D-40 #1 slice: lightmap seams / padding / texel density of _CabinTubeLM on the slice pieces (Seat_SeatR0, Window_R1,
Pole_R0), read off the finished bus. READ ONLY: works on a scratch copy of the blend, never saves a .blend, never writes
Bus/Textures or Bus/Models.

    ~/bpy/bin/python -I Bus/Docs~/slice/lm_seam_check.py [--blend /tmp/bus/bus_final_ext.blend] [--exr Bus/Textures/Cabin_TubeLM.exr]
                                                         [--out Bus/Docs~/slice] [--no-render] [--samples 16] [--threads 2]

Sampling is Unity's: uv layer 'UVLightmap' (= uv1 of Bus.fbx), bilinear, texel centres at (i + 0.5) / N, clamp, mip 0
(at 0.5-1 m one texel of this atlas covers ~25 px, so Unity reads mip 0; mips 1-2 are reported for grazing / far views).
'black' texel = all four channels 0 (E = 0 and AO = 0): bake background, or a face the bake saw fully enclosed.
Faces that count: VISIBLE (front-facing and unoccluded from the hero eye, every seat's eye, an aisle grid, in the
whole bus; or inside one of the six bus_slice.json close cameras with only the three pieces as occluders) and NOT METAL
(Lanbai/Cabin gives metals 4 % of albedo x E: Steel / Alu / Chrome / RadioGrille, and the part mask R >= 0.5 on the
seat). Everything is also reported for all faces.
  density   texels per metre (sqrt(uv area in texels^2 / world area)), area-weighted percentiles
  islands   uv islands (faces joined through shared (vertex, uv) corners); free texels to the nearest OTHER island of
            the whole atlas (Cabin_Static, Seat_*, Window_*, Pole_*); the black share of the 1-texel ring round the
            islands that were baked (= missing padding); folds (texels covered twice in one object by faces whose
            normals differ by > 60 deg: the bake writes one of them, the other reads the wrong light)
  bleed     per triangle, over a barycentric grid <= 0.5 texel: the largest bilinear weight from black texels, and
            from texels inside another island
  causes    the visible non-metal triangles that read >= 25 % black, by cause (black_causes): island without a texel
            centre / island thinner than a texel at that face / own texels black and the spot enclosed (24 AO-like
            rays) / own texels black although open (a texel under an attached part: screw, button, gusset, pole)
  unlit     non-metal faces sampling E = 0 texels (AO may be baked)
  seams     uv-seam edges (two faces, different uv): E on both sides at 5 points of the same 3D edge, relative jump
            |La - Lb| / max(La, Lb, 0.02), by dihedral angle (< 20 deg: an artefact on a smooth surface); '_lit' = only
            edges with no black / unlit side (the jump itself, not a black island beside a lit one)
  edge dip  island-boundary edges: E at the edge / E one texel inside the same face (< 0.75 = a dark line)
  ring      atlas.ring_outside_lit_black_frac: of the texels OUTSIDE every island that touch a non-black texel inside an
            island (4- / 8-neighbourhood), the black share (= where the bake margin did not grow)
  fill_sim  what the report's fix #1 (bake_lightmap.py) would do, simulated on a copy of the EXR in memory: black texels
            next to non-black ones take the mean of their non-black 3x3 neighbours, 3 passes, either only inside the
            islands ('inside') or inside + a 2-texel ring round them ('inside_ring2': the bilinear footprint and the bake
            margin); then the same black stats as above (atlas.fill_sim, objects.<name>.fill_sim)
Renders (Cycles CPU, emission only, linear interpolation = bilinear mip 0, Standard view; --threads, default 2: the
cores are shared): the six bus_slice.json close cameras (look at the piece's bbox centre, back off toward the hero eye
0.5 / 1.0 m, 40 x 30 deg) as E and as AO, the worst visible spots, three views in the whole bus; magenta = bilinear
weight of black texels. PNGs, each kept under 400 KB. Output: <out>/lm_seams.json + the PNGs.
"""
import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
HERO = np.array((0.55, 1.70, 2.05))
PIECES = {'seat': ['Seat_SeatR0'], 'window': ['Window_R1'], 'pillar': ['Pole_R0']}
SLICE = [n for v in PIECES.values() for n in v]
BBOX_EXTRA = {'window': ['Glass_WinR1']}           # the test's look_at_object takes every renderer under Slice_SideWindow
ATLAS_PREFIX = ('Seat_', 'Window_', 'Pole_')     # + Cabin_Static: the objects bake_lightmap.py bakes into one atlas
METAL = {'Steel', 'Alu', 'Chrome', 'RadioGrille', 'Ext_Silver'}   # LanbaiBusBuild.MatTable metallic 1
FLOOR_E = 0.02


def u2b(p):
    return Vector((float(p[0]), float(p[2]), float(p[1])))


def b2u(a):
    a = np.asarray(a)
    return a[..., [0, 2, 1]]


def lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def r3(v):
    return [round(float(x), 3) for x in v]


def matkey(name):
    k = name[6:] if name.startswith('M_Bus_') else name
    return k.split('.')[0]


# ------------------------------------------------------------------------------------------------ mesh arrays
def mesh_arrays(o, dg):
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    me.calc_loop_triangles()
    nV, nL, nP, nE, nT = len(me.vertices), len(me.loops), len(me.polygons), len(me.edges), len(me.loop_triangles)
    uvl = me.uv_layers.get('UVLightmap')
    if uvl is None:
        oe.to_mesh_clear()
        return None
    co = np.empty(nV * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world, np.float64)
    wco = (co @ M[:3, :3].T + M[:3, 3])
    lv = np.empty(nL, np.int32); me.loops.foreach_get('vertex_index', lv)
    le = np.empty(nL, np.int32); me.loops.foreach_get('edge_index', le)
    uv = np.empty(nL * 2, np.float32); uvl.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2).astype(np.float64)
    uv0 = None
    if 'UVMap' in me.uv_layers:
        uv0 = np.empty(nL * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv0); uv0 = uv0.reshape(-1, 2)
    ps = np.empty(nP, np.int32); me.polygons.foreach_get('loop_start', ps)
    pt = np.empty(nP, np.int32); me.polygons.foreach_get('loop_total', pt)
    pmi = np.empty(nP, np.int32); me.polygons.foreach_get('material_index', pmi)
    pn = np.empty(nP * 3, np.float32); me.polygons.foreach_get('normal', pn); pn = pn.reshape(-1, 3)
    Nm = np.linalg.inv(M[:3, :3]).T
    wpn = pn @ Nm.T
    wpn /= np.maximum(np.linalg.norm(wpn, axis=1, keepdims=True), 1e-12)
    tl = np.empty(nT * 3, np.int32); me.loop_triangles.foreach_get('loops', tl); tl = tl.reshape(-1, 3)
    tp = np.empty(nT, np.int32); me.loop_triangles.foreach_get('polygon_index', tp)
    ev = np.empty(nE * 2, np.int32); me.edges.foreach_get('vertices', ev); ev = ev.reshape(-1, 2)
    mats = [matkey(m.name) if m else '-' for m in me.materials]
    oe.to_mesh_clear()
    lp = np.repeat(np.arange(nP), pt)                      # loop -> polygon (loops are stored polygon by polygon)
    nxt = np.arange(nL) + 1
    nxt[ps + pt - 1] = ps
    return dict(name=o.name, wco=wco, lv=lv, le=le, uv=uv, uv0=uv0, ps=ps, pt=pt, pmi=pmi, mats=mats, lp=lp, nxt=nxt,
                wpn=wpn, tl=tl, tp=tp, ev=ev)


def islands(A, N):
    """faces sharing a (vertex, uv quantised to 1/64 texel) corner are in one island: connected components of the
    polygon - corner graph."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    q = np.round(A['uv'] * N * 64).astype(np.int64)
    key = (A['lv'].astype(np.int64) << 42) ^ ((q[:, 0] & 0x1FFFFF) << 21) ^ (q[:, 1] & 0x1FFFFF)
    _, cid = np.unique(key, return_inverse=True)
    nP = len(A['ps'])
    nC = int(cid.max()) + 1
    g = coo_matrix((np.ones(len(cid)), (A['lp'], nP + cid)), shape=(nP + nC, nP + nC))
    _, lab = connected_components(g, directed=False)
    _, isl = np.unique(lab[:nP], return_inverse=True)
    return isl                                           # polygon -> island (0..k-1)


# ------------------------------------------------------------------------------------------------ texture sampling
class LM:
    def __init__(self, arr):
        self.a = arr                                       # (H, W, 4), row 0 = v 0
        self.H, self.W = arr.shape[:2]
        self.black = (arr[..., 0] == 0) & (arr[..., 1] == 0) & (arr[..., 2] == 0) & (arr[..., 3] == 0)
        self.unlit = (arr[..., 0] == 0) & (arr[..., 1] == 0) & (arr[..., 2] == 0)

    def taps(self, uv):
        x = uv[:, 0] * self.W - 0.5
        y = uv[:, 1] * self.H - 0.5
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
        fx = x - x0; fy = y - y0
        xs = [np.clip(x0, 0, self.W - 1), np.clip(x0 + 1, 0, self.W - 1)]
        ys = [np.clip(y0, 0, self.H - 1), np.clip(y0 + 1, 0, self.H - 1)]
        w = [(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy]
        idx = [(ys[0], xs[0]), (ys[0], xs[1]), (ys[1], xs[0]), (ys[1], xs[1])]
        return idx, w

    def sample(self, uv, arr=None):
        arr = self.a if arr is None else arr
        idx, w = self.taps(uv)
        out = 0
        for (yy, xx), ww in zip(idx, w):
            v = arr[yy, xx]
            out = out + (v * ww[:, None] if v.ndim == 2 else v * ww)
        return out


def mip(arr, k):
    for _ in range(k):
        H, W = arr.shape[:2]
        arr = arr.reshape(H // 2, 2, W // 2, 2, -1).mean(axis=(1, 3))
    return arr


def fill_black(arr, target, passes=3):
    """fix #1 of the report, simulated: inside `target`, a black texel (all four channels 0) with a non-black texel in
    its 3x3 neighbourhood takes the mean of those non-black neighbours (all four channels); `passes` times, so the fill
    reaches `passes` texels from lit texels. Returns (filled copy, texels filled)."""
    from scipy import ndimage
    a = arr.copy()
    k = np.ones((3, 3), np.float32)
    n = 0
    for _ in range(passes):
        blk = (a == 0).all(-1)
        lit = (~blk).astype(np.float32)
        cnt = ndimage.convolve(lit, k, mode='constant')
        cand = target & blk & (cnt > 0)
        if not cand.any():
            break
        new = [ndimage.convolve(a[..., c] * lit, k, mode='constant')[cand] / cnt[cand] for c in range(4)]
        for c in range(4):
            a[..., c][cand] = new[c]
        n += int(cand.sum())
    return a, n


# ------------------------------------------------------------------------------------------------ rasterising (texel centres)
def raster(tri_uv_px, tri_val, idmap, clash_pairs=None):
    """write tri_val into idmap at every texel whose centre is inside the triangle (pixel coords: u * W). clash_pairs,
    if given, collects (texel y, x, previous value, new value) wherever a texel is claimed twice."""
    H, W = idmap.shape
    mn = np.floor(tri_uv_px.min(axis=1) - 0.5).astype(np.int64) + 1
    mx = np.floor(tri_uv_px.max(axis=1) - 0.5).astype(np.int64)
    nx = np.maximum(mx[:, 0] - mn[:, 0] + 1, 0)
    ny = np.maximum(mx[:, 1] - mn[:, 1] + 1, 0)
    has = (nx > 0) & (ny > 0)
    big = has & ((nx > 24) | (ny > 24))
    a, b, c = tri_uv_px[:, 0], tri_uv_px[:, 1], tri_uv_px[:, 2]

    def inside(px, py, a, b, c):
        def e(p, q):
            return (q[..., 0] - p[..., 0]) * (py - p[..., 1]) - (q[..., 1] - p[..., 1]) * (px - p[..., 0])
        e0, e1, e2 = e(a, b), e(b, c), e(c, a)
        return ((e0 > 0) & (e1 > 0) & (e2 > 0)) | ((e0 < 0) & (e1 < 0) & (e2 < 0))   # strict: shared edges count once

    def put(yi, xi, vals):
        if clash_pairs is not None:
            prev = idmap[yi, xi]
            m = (prev >= 0) & (prev != vals)
            if m.any():
                clash_pairs.append(np.stack([yi[m], xi[m], prev[m], vals[m]], 1))
        idmap[yi, xi] = vals
    for sx in range(1, 25):
        for sy in range(1, 25):
            sel = np.where(has & ~big & (nx == sx) & (ny == sy))[0]
            if len(sel) == 0:
                continue
            gx, gy = np.meshgrid(np.arange(sx), np.arange(sy), indexing='ij')
            gx = gx.ravel(); gy = gy.ravel()
            px = mn[sel, 0][:, None] + gx[None, :] + 0.5
            py = mn[sel, 1][:, None] + gy[None, :] + 0.5
            ins = inside(px, py, a[sel][:, None, :], b[sel][:, None, :], c[sel][:, None, :])
            ti, gi = np.nonzero(ins)
            xi = (mn[sel, 0][ti] + gx[gi]).clip(0, W - 1)
            yi = (mn[sel, 1][ti] + gy[gi]).clip(0, H - 1)
            put(yi, xi, tri_val[sel][ti])
    for t in np.where(big)[0]:
        gx, gy = np.meshgrid(np.arange(nx[t]), np.arange(ny[t]), indexing='ij')
        px = mn[t, 0] + gx.ravel() + 0.5
        py = mn[t, 1] + gy.ravel() + 0.5
        ins = inside(px, py, a[t], b[t], c[t])
        xi = (px[ins] - 0.5).astype(np.int64).clip(0, W - 1)
        yi = (py[ins] - 0.5).astype(np.int64).clip(0, H - 1)
        put(yi, xi, np.full(len(xi), tri_val[t]))


def tri_samples(U, max_n=48, P3=None):
    """barycentric sample grid per triangle, spacing <= 0.5 texel. Yields (tri indices, (n_tri, m, 2) points in U's
    units, (n_tri, m, 3) the same points on P3 or None)."""
    e = np.stack([np.linalg.norm(U[:, 1] - U[:, 0], axis=1), np.linalg.norm(U[:, 2] - U[:, 1], axis=1),
                  np.linalg.norm(U[:, 0] - U[:, 2], axis=1)], 1).max(1)
    n = np.clip(np.ceil(e * 2), 1, max_n).astype(int)
    for k in np.unique(n):
        sel = np.where(n == k)[0]
        bc = np.array([(i / k, j / k) for i in range(k + 1) for j in range(k + 1 - i)])
        b0 = 1 - bc[:, 0] - bc[:, 1]

        def at(X):
            return (b0[None, :, None] * X[sel, 0][:, None, :] + bc[None, :, 0, None] * X[sel, 1][:, None, :] +
                    bc[None, :, 1, None] * X[sel, 2][:, None, :])
        yield sel, at(U), (at(P3) if P3 is not None else None)


def open_points(bvh, pts, nrm, gap=0.003, reach=0.03):
    """True where a surface point (Unity coords) can be seen at all: a short ray along its normal neither starts inside a
    closed solid (first hit is a back face: the point is inside another part, e.g. where the pole runs through the
    button box) nor hits something within `gap` (a contact gap the bake sees as fully enclosed)."""
    out = np.ones(len(pts), bool)
    for i in range(len(pts)):
        n = u2b(nrm[i])
        h = bvh.ray_cast(u2b(pts[i]) + n * 1e-4, n, reach)
        if h[0] is not None and (h[3] < gap or h[1].dot(n) > 0):
            out[i] = False
    return out


# ------------------------------------------------------------------------------------------------ visibility
def bvh_of(objs, dg):
    """one BVH over several objects; base[name] = index of the object's first polygon in it."""
    verts, polys, base = [], [], {}
    for o in objs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        M = o.matrix_world
        vb = len(verts)
        base[o.name] = len(polys)
        verts += [M @ v.co for v in me.vertices]
        for p in me.polygons:
            polys.append([vb + i for i in p.vertices])
        oe.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, all_triangles=False), base


def slice_cams(objs):
    cams = []
    for piece, names in PIECES.items():
        pts = []
        for n in names + BBOX_EXTRA.get(piece, []):
            o = objs.get(n)
            if o is not None:
                pts += [b2u(np.array(o.matrix_world @ Vector(c))) for c in o.bound_box]
        if not pts:
            continue
        P = np.array(pts)
        c = (P.min(0) + P.max(0)) / 2
        d = HERO - c
        d /= np.linalg.norm(d)
        for dist, tag in ((0.5, '05m'), (1.0, '10m')):
            cams.append(dict(id='%s_%s' % (piece, tag), piece=piece, eye=c + d * dist, target=c))
    return cams


def visible(T, own_all, own_slice, bvh_all, bvh_slice, eyes, cams):
    """T: per-triangle arrays (cen, n, pts (n, 4, 3) on the face, Unity coords); own_*: the triangle's polygon index in
    each BVH. A point is seen when the first thing a ray from the eye hits is the triangle's own polygon (or a hit within
    0.3 mm of the point). Returns (vis_bus, vis_shot)."""
    n_t = len(T['cen'])
    vis_bus = np.zeros(n_t, bool)
    vis_shot = np.zeros(n_t, bool)

    def cast(bvh, own, eye, idx):
        hit = np.zeros(len(idx), bool)
        e = u2b(eye)
        for j, t in enumerate(idx):
            for p in T['pts'][t]:
                d = u2b(p) - e
                L = d.length
                if L < 1e-4:
                    continue
                h = bvh.ray_cast(e, d / L, L + 1e-3)
                if h[0] is not None and (h[2] == own[t] or h[3] >= L - 3e-4):
                    hit[j] = True
                    break
        return hit
    for eye in eyes:
        todo = np.where(~vis_bus)[0]
        if len(todo) == 0:
            break
        v = eye[None, :] - T['cen'][todo]
        front = (np.einsum('ij,ij->i', v, T['n'][todo]) > 0) & (np.linalg.norm(v, axis=1) < 8)
        idx = todo[front]
        vis_bus[idx[cast(bvh_all, own_all, eye, idx)]] = True
    for c in cams:
        f = c['target'] - c['eye']; f /= np.linalg.norm(f)
        r = np.cross([0, 1, 0], f); r /= np.linalg.norm(r)
        u = np.cross(f, r)
        todo = np.where(~vis_shot)[0]
        v = T['cen'][todo] - c['eye'][None, :]
        z = v @ f
        inside = (z > 0.02) & (np.abs(np.degrees(np.arctan2(v @ r, z))) <= 20) & (np.abs(np.degrees(np.arctan2(v @ u, z))) <= 15)
        front = np.einsum('ij,ij->i', -v, T['n'][todo]) > 0
        idx = todo[inside & front]
        vis_shot[idx[cast(bvh_slice, own_slice, c['eye'], idx)]] = True
    return vis_bus, vis_shot


# ------------------------------------------------------------------------------------------------ per-object checks
def tri_table(A, lm, part_mask):
    tri = A['tl']
    P = A['wco'][A['lv'][tri]]                                        # blender coords
    Pu = b2u(P)
    cen = Pu.mean(1)
    n = b2u(A['wpn'][A['tp']])
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    U = A['uv'][tri] * np.array([lm.W, lm.H])
    a_uv = 0.5 * np.abs((U[:, 1, 0] - U[:, 0, 0]) * (U[:, 2, 1] - U[:, 0, 1]) - (U[:, 2, 0] - U[:, 0, 0]) * (U[:, 1, 1] - U[:, 0, 1]))
    mk = np.array([A['mats'][i] if i < len(A['mats']) else '-' for i in A['pmi'][A['tp']]])
    metal = np.isin(mk, list(METAL))
    if part_mask is not None and A['uv0'] is not None:
        part = np.char.startswith(mk.astype(str), 'Part_')
        if part.any():
            c0 = A['uv0'][tri].mean(1)
            H, W = part_mask.shape
            xi = np.clip((c0[:, 0] % 1.0) * W, 0, W - 1).astype(int)
            yi = np.clip((1 - c0[:, 1] % 1.0) * H, 0, H - 1).astype(int)
            metal |= part & (part_mask[yi, xi] >= 0.5)
    inner = Pu * 0.6 + cen[:, None, :] * 0.4                          # 3 points pulled toward the centroid
    pts = np.concatenate([cen[:, None, :], inner], 1)
    return dict(cen=cen, n=n, area=area, U=U, a_uv=a_uv, mat=mk, metal=metal, pts=pts, P=Pu)


def density(A, lm):
    tri = A['tl']
    P = A['wco'][A['lv'][tri]]
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    U = A['uv'][tri] * np.array([lm.W, lm.H])
    a_uv = 0.5 * np.abs((U[:, 1, 0] - U[:, 0, 0]) * (U[:, 2, 1] - U[:, 0, 1]) - (U[:, 2, 0] - U[:, 0, 0]) * (U[:, 1, 1] - U[:, 0, 1]))
    ok = area > 1e-10
    d = np.sqrt(a_uv[ok] / area[ok])
    w = area[ok]
    o = np.argsort(d)
    cw = np.cumsum(w[o]) / w.sum()

    def pct(p):
        return float(d[o][min(np.searchsorted(cw, p), len(d) - 1)])
    return dict(p5=round(pct(0.05), 1), p50=round(pct(0.50), 1), p95=round(pct(0.95), 1),
                mm_per_texel_p50=round(1000.0 / max(pct(0.5), 1e-6), 2), area_m2=round(float(w.sum()), 4),
                uv_area_texels=round(float(a_uv.sum()), 1), zero_uv_area_tris=int(((a_uv < 1e-6) & (area > 1e-8)).sum()))


def island_gaps(A, T, lm, idmap, base, keep):
    """free texels from each island (that has a kept face) to the nearest other island of the atlas."""
    from scipy import ndimage
    tis = A['isl'][A['tp']]
    k = int(A['isl'].max()) + 1
    lo = np.full((k, 2), 1e9); hi = np.full((k, 2), -1e9)
    np.minimum.at(lo, tis, T['U'].min(axis=1)); np.maximum.at(hi, tis, T['U'].max(axis=1))
    want = np.zeros(k, bool); want[tis[keep]] = True
    H, W = idmap.shape
    gaps, sub, ring_black, ring_n, lit_isl = [], 0, 0, 0, 0
    for i in np.where(want)[0]:
        gid = base + i
        x0, y0 = int(max(lo[i, 0] - 12, 0)), int(max(lo[i, 1] - 12, 0))
        x1, y1 = int(min(hi[i, 0] + 12, W)), int(min(hi[i, 1] + 12, H))
        win = idmap[y0:y1, x0:x1]
        own = win == gid
        if not own.any():
            sub += 1
            continue
        other = (win >= 0) & (win != gid)
        if other.any():
            d = ndimage.distance_transform_cdt(~other, metric='chessboard')
            gaps.append(int(d[own].min()) - 1)
        else:
            gaps.append(99)
        if lm.black[y0:y1, x0:x1][own].mean() >= 0.5:      # a black island's margin is black too: not a padding fault
            continue
        lit_isl += 1
        ring = ndimage.binary_dilation(own, iterations=1) & ~own & ~other
        ring_black += int(lm.black[y0:y1, x0:x1][ring].sum())
        ring_n += int(ring.sum())
    g = np.array(gaps) if gaps else np.array([99])
    return dict(islands=int(want.sum()), sub_texel=sub, gap_min=int(g.min()), gap_p5=float(np.percentile(g, 5)),
                gap_le2=int((g <= 2).sum()), baked_islands=lit_isl, ring_black_frac_baked=round(ring_black / max(ring_n, 1), 4))


def folds(A, T, lm):
    """texels covered twice in this object by faces whose normals differ by > 60 deg."""
    idm = np.full((lm.H, lm.W), -1, np.int64)
    pairs = []
    raster(T['U'], np.arange(len(T['U'])), idm, pairs)
    if not pairs:
        return np.zeros(len(T['U']), bool), 0
    pr = np.concatenate(pairs)
    a, b = pr[:, 2], pr[:, 3]
    real = np.einsum('ij,ij->i', T['n'][a], T['n'][b]) < 0.5
    hit = np.zeros(len(T['U']), bool)
    hit[a[real]] = True; hit[b[real]] = True
    return hit, int(real.sum())


def bleed(A, T, lm, idmap, base, bvh, keep, extra_black=()):
    """per triangle, the largest bilinear weight of black / E = 0 / other-island texels over its samples; for the kept
    (visible, non-metal) triangles only over samples at OPEN points (open_points), so a face's part hidden inside
    another part does not count. extra_black: more black masks (the fill_sim atlases), weighed the same way."""
    gid_t = base + A['isl'][A['tp']]
    nT = len(T['U'])
    black_w = np.zeros(nT); other_w = np.zeros(nT); unlit_w = np.zeros(nT)
    extra_w = [np.zeros(nT) for _ in extra_black]
    n_open = n_pts = 0
    for sel, pts, p3 in tri_samples(T['U'], P3=T['P']):
        m = pts.shape[1]
        uv = pts.reshape(-1, 2) / np.array([lm.W, lm.H])
        idx, w = lm.taps(uv)
        g = np.repeat(gid_t[sel], m)
        bw = 0; ow = 0; uw = 0
        xw = [0] * len(extra_black)
        for (yy, xx), ww in zip(idx, w):
            bw = bw + ww * lm.black[yy, xx]
            uw = uw + ww * lm.unlit[yy, xx]
            iid = idmap[yy, xx]
            ow = ow + ww * ((iid >= 0) & (iid != g))
            for j, eb in enumerate(extra_black):
                xw[j] = xw[j] + ww * eb[yy, xx]
        bw = bw.reshape(-1, m); uw = uw.reshape(-1, m); ow = ow.reshape(-1, m)
        ok = np.ones_like(bw, bool)
        kk = keep[sel]
        if kk.any():
            q = p3[kk].reshape(-1, 3)
            nn = np.repeat(T['n'][sel][kk], m, axis=0)
            op = open_points(bvh, q, nn).reshape(-1, m)
            ok[kk] = op
            n_open += int(op.sum()); n_pts += op.size
        black_w[sel] = np.where(ok, bw, 0).max(1)
        unlit_w[sel] = np.where(ok, uw, 0).max(1)
        other_w[sel] = np.where(ok, ow, 0).max(1)
        for j in range(len(extra_black)):
            extra_w[j][sel] = np.where(ok, xw[j].reshape(-1, m), 0).max(1)
    return black_w, other_w, unlit_w, (n_open, n_pts), extra_w


def edge_table(A):
    L = np.arange(len(A['lv']))
    e = A['le']
    la, lb = L, A['nxt']
    ev = A['ev'][e]
    sw = A['lv'][la] != ev[:, 0]
    l0 = np.where(sw, lb, la); l1 = np.where(sw, la, lb)
    o = np.argsort(e, kind='stable')
    e_s = e[o]
    starts = np.r_[0, np.nonzero(np.diff(e_s))[0] + 1]
    counts = np.diff(np.r_[starts, len(e_s)])
    return o, starts, counts, A['lp'], l0, l1


def seams(A, lm, pkeep, bvh):
    """pkeep: per polygon, counted (visible and not metal). On counted edges only the OPEN sample points count."""
    o, starts, counts, p, l0, l1 = edge_table(A)
    two = starts[counts == 2]
    fa, fb = o[two], o[two + 1]
    uvs = A['uv'] * np.array([lm.W, lm.H])
    seam = (np.linalg.norm(uvs[l0[fa]] - uvs[l0[fb]], axis=1) > 0.25) | (np.linalg.norm(uvs[l1[fa]] - uvs[l1[fb]], axis=1) > 0.25)
    fa, fb = fa[seam], fb[seam]
    na, nb = A['wpn'][p[fa]], A['wpn'][p[fb]]
    ang = np.degrees(np.arccos(np.clip((na * nb).sum(1), -1, 1)))
    ts = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
    UA = A['uv'][l0[fa]][:, None] * (1 - ts[None, :, None]) + A['uv'][l1[fa]][:, None] * ts[None, :, None]
    UB = A['uv'][l0[fb]][:, None] * (1 - ts[None, :, None]) + A['uv'][l1[fb]][:, None] * ts[None, :, None]
    La = lum(lm.sample(UA.reshape(-1, 2))[:, :3]).reshape(-1, len(ts))
    Lb = lum(lm.sample(UB.reshape(-1, 2))[:, :3]).reshape(-1, len(ts))
    pa = b2u(A['wco'][A['lv'][l0[fa]]]); pb_ = b2u(A['wco'][A['lv'][l1[fa]]])
    elen = np.linalg.norm(pa - pb_, axis=1)
    both = pkeep[p[fa]] & pkeep[p[fb]]
    ok = np.zeros(La.shape, bool)
    ib = np.where(both)[0]
    if len(ib):
        P3 = (pa[ib][:, None] * (1 - ts[None, :, None]) + pb_[ib][:, None] * ts[None, :, None]).reshape(-1, 3)
        oa = open_points(bvh, P3, np.repeat(b2u(na[ib]), len(ts), axis=0))
        ob = open_points(bvh, P3, np.repeat(b2u(nb[ib]), len(ts), axis=0))
        ok[ib] = (oa & ob).reshape(-1, len(ts))
    okm = np.where(both[:, None], ok, True)
    relp = np.where(okm, np.abs(La - Lb) / np.maximum(np.maximum(La, Lb), FLOOR_E), 0)
    rel = relp.max(1)
    absd = np.where(okm, np.abs(La - Lb), 0).max(1)
    both = both & ok.any(1)
    lit = np.where(okm, (La > FLOOR_E) & (Lb > FLOOR_E), True).all(1)   # no black / unlit side at any counted point

    def stats(msk):
        if not msk.any():
            return dict(edges=0)
        r_ = rel[msk]
        return dict(edges=int(msk.sum()), length_m=round(float(elen[msk].sum()), 3), rel_p50=round(float(np.median(r_)), 3),
                    rel_p95=round(float(np.percentile(r_, 95)), 3), rel_max=round(float(r_.max()), 3),
                    over_5pct=int((r_ > 0.05).sum()), over_10pct=int((r_ > 0.10).sum()), over_25pct=int((r_ > 0.25).sum()),
                    length_over_10pct_m=round(float(elen[msk][r_ > 0.10].sum()), 3), abs_E_max=round(float(absd[msk].max()), 3))
    res = dict(all_seam_edges=int(len(fa)),
               counted_smooth_lt20=stats(both & (ang < 20)), counted_20_60=stats(both & (ang >= 20) & (ang < 60)),
               counted_smooth_lt20_lit=stats(both & (ang < 20) & lit), counted_20_60_lit=stats(both & (ang >= 20) & (ang < 60) & lit),
               all_smooth_lt20=stats(ang < 20))
    spots = []
    score = rel * both * lit * (ang < 20) * (elen > 0.004)        # the worst real jumps (both sides lit)
    for i in np.argsort(-score)[:10]:
        if score[i] < 0.05:
            break
        spots.append(dict(kind='seam', rel=round(float(rel[i]), 3), E=[round(float(La[i].mean()), 3), round(float(Lb[i].mean()), 3)],
                          dihedral=round(float(ang[i]), 1), edge_mm=round(float(elen[i] * 1000), 1),
                          at_unity=r3((pa[i] + pb_[i]) / 2), normal_unity=r3(b2u(na[i])),
                          mat=[A['mats'][A['pmi'][p[fa[i]]]], A['mats'][A['pmi'][p[fb[i]]]]]))
    return res, spots


def edge_dip(A, lm, pkeep, bvh):
    o, starts, counts, p, l0, l1 = edge_table(A)
    uvs = A['uv']
    px = 1.0 / lm.W
    rows = []
    for s, c in zip(starts, counts):
        if c == 1:
            rows.append(o[s])
        elif c == 2:
            a, b = o[s], o[s + 1]
            if (np.linalg.norm(uvs[l0[a]] - uvs[l0[b]]) * lm.W > 0.25) or (np.linalg.norm(uvs[l1[a]] - uvs[l1[b]]) * lm.W > 0.25):
                rows += [a, b]
    rows = np.array(rows, np.int64)
    rows = rows[pkeep[p[rows]]]
    if len(rows) == 0:
        return dict(boundary_edges=0), []
    cen = np.zeros((len(A['ps']), 2))
    np.add.at(cen, A['lp'], uvs)
    cen /= A['pt'][:, None]
    ts = np.array([0.25, 0.5, 0.75])
    E0 = uvs[l0[rows]][:, None] * (1 - ts[None, :, None]) + uvs[l1[rows]][:, None] * ts[None, :, None]
    dvec = cen[p[rows]][:, None, :] - E0
    dl = np.linalg.norm(dvec, axis=2, keepdims=True)
    Ein = E0 + dvec / np.maximum(dl, 1e-12) * np.minimum(px, 0.5 * dl)
    Le = lum(lm.sample(E0.reshape(-1, 2))[:, :3]).reshape(-1, len(ts))
    Li = lum(lm.sample(Ein.reshape(-1, 2))[:, :3]).reshape(-1, len(ts))
    pa = b2u(A['wco'][A['lv'][l0[rows]]]); pb_ = b2u(A['wco'][A['lv'][l1[rows]]])
    P3 = (pa[:, None] * (1 - ts[None, :, None]) + pb_[:, None] * ts[None, :, None]).reshape(-1, 3)
    op = open_points(bvh, P3, np.repeat(b2u(A['wpn'][p[rows]]), len(ts), axis=0)).reshape(-1, len(ts))
    ok = (Li > FLOOR_E) & (dl[..., 0] * lm.W > 0.75) & op
    ratio = np.where(ok, Le / np.maximum(Li, 1e-6), 1.0)
    rmin = ratio.min(1)
    elen = np.linalg.norm(pa - pb_, axis=1)
    chk = ok.any(1)
    res = dict(boundary_edges=int(len(rows)), checked=int(chk.sum()),
               ratio_p5=round(float(np.percentile(rmin[chk], 5)), 3) if chk.any() else None,
               dark_lt_90pct=int((rmin < 0.9).sum()), dark_lt_75pct=int((rmin < 0.75).sum()), dark_lt_50pct=int((rmin < 0.5).sum()),
               length_dark_lt_75pct_m=round(float(elen[rmin < 0.75].sum()), 3))
    spots = []
    for i in np.argsort(rmin)[:8]:
        if rmin[i] >= 0.75 or elen[i] < 0.004:
            continue
        spots.append(dict(kind='edge_dip', ratio=round(float(rmin[i]), 3), E_in=round(float(Li[i].max()), 3),
                          edge_mm=round(float(elen[i] * 1000), 1), at_unity=r3((pa[i] + pb_[i]) / 2),
                          normal_unity=r3(b2u(A['wpn'][p[rows[i]]])), mat=A['mats'][A['pmi'][p[rows[i]]]]))
    return res, spots


def mip_black(T, lm, keep):
    out = {}
    for k in (1, 2):
        frac = mip(lm.black.astype(np.float32)[..., None], k)[..., 0]
        sub = LM(np.zeros((lm.H >> k, lm.W >> k, 4), np.float32))
        U = T['U'] / (1 << k)
        worst = np.zeros(len(U))
        for sel, pts, _ in tri_samples(U, 24):
            m = pts.shape[1]
            idx, w = sub.taps(pts.reshape(-1, 2) / np.array([sub.W, sub.H]))
            bw = 0
            for (yy, xx), ww in zip(idx, w):
                bw = bw + ww * frac[yy, xx]
            worst[sel] = bw.reshape(-1, m).max(1)
        out['mip%d' % k] = dict(tris_gt_10pct=int((worst[keep] > 0.10).sum()), tris_gt_25pct=int((worst[keep] > 0.25).sum()),
                                area_gt_25pct_cm2=round(float(T['area'][keep][worst[keep] > 0.25].sum() * 1e4), 1))
    return out


def hemi_dirs(n=24):
    """n fixed cosine-weighted directions about +z (a Fibonacci spiral): every run gives the same numbers."""
    i = np.arange(n) + 0.5
    r = np.sqrt(i / n)
    phi = i * math.pi * (3 - math.sqrt(5))
    return np.stack([r * np.cos(phi), r * np.sin(phi), np.sqrt(1 - r * r)], 1)


def openness(bvh, pts, nrm, dirs, reach=0.5, off=1e-3):
    """per point (Unity coords): the share of cosine-weighted rays that travel `reach` (the AO bake's 0.5 m) without a
    hit, from `off` above the surface = roughly the AO the bake should have written. ~0 = the point is inside or against
    another part (the bake is right to write 0 there; if it is also visible, the geometry interpenetrates)."""
    out = np.zeros(len(pts))
    for k in range(len(pts)):
        nz = np.asarray(nrm[k], float)
        a = np.array([1.0, 0, 0]) if abs(nz[0]) < 0.9 else np.array([0, 1.0, 0])
        tx = np.cross(nz, a); tx /= np.linalg.norm(tx)
        ty = np.cross(nz, tx)
        D = dirs[:, :1] * tx + dirs[:, 1:2] * ty + dirs[:, 2:] * nz
        o = u2b(np.asarray(pts[k]) + nz * off)
        free = 0
        for d in D:
            if bvh.ray_cast(o, u2b(d), reach)[0] is None:
                free += 1
        out[k] = free / len(D)
    return out


def black_causes(A, T, lm, bvh_bake, keep, black_w, k_list=8):
    """the counted (visible, non-metal) triangles that read >= 25 % black texels, split by cause:
      no_texel   their uv island holds no texel centre at all (thinner than a texel everywhere): the bake rasteriser
                 never writes it, and with no written texel there is nothing for the margin to grow from
      thin       the island has texels, but at this face it is thinner than a texel: the face's smallest uv height is
                 <= 1.05 texel, or most of its bilinear taps (>= 50 % of its sample points) land on no texel of its own
                 island, so it reads the margin / background
      enclosed   its own texels are black and the AO the bake should see is ~0 (< 5 % of 24 rays escape 0.5 m from
                 1 mm above the surface): the face sits inside / against another part, the black is right for that
                 geometry (a modelling question if it is seen)
      open       its own texels are black although the surface is open where it is seen: texels under a part that
                 sits on the face (the stop button, piping, a screw head, a gusset) or on a hidden neighbour face of
                 the same island, bled into the visible part by the 13 mm texel and the bilinear filter"""
    isl_t = A['isl'][A['tp']]
    k = int(A['isl'].max()) + 1
    idm = np.full((lm.H, lm.W), -1, np.int64)
    raster(T['U'], isl_t, idm)
    tex = np.bincount(idm[idm >= 0], minlength=k)
    bad = np.where(keep & (black_w > 0.25))[0]
    own_frac = np.ones(len(T['U']))
    if len(bad):
        Ub = T['U'][bad]
        for sel, pts, _ in tri_samples(Ub):
            m = pts.shape[1]
            idx, w = lm.taps(pts.reshape(-1, 2) / np.array([lm.W, lm.H]))
            g = np.repeat(isl_t[bad[sel]], m)
            hit = 0
            for (yy, xx), ww in zip(idx, w):
                hit = hit | ((idm[yy, xx] == g) & (ww > 1e-6))
            own_frac[bad[sel]] = hit.reshape(-1, m).mean(1)
    dirs = hemi_dirs()
    cause = np.empty(len(bad), object)
    op = np.zeros(len(bad))
    for j, t in enumerate(bad):
        if tex[isl_t[t]] == 0:
            cause[j] = 'no_texel'
            continue
        Ut = T['U'][t]
        alt = 2 * T['a_uv'][t] / max(np.linalg.norm(Ut[[1, 2, 0]] - Ut, axis=1).max(), 1e-9)   # smallest uv height
        if own_frac[t] < 0.5 or alt <= 1.05:
            cause[j] = 'thin'
            continue
        op[j] = openness(bvh_bake, T['pts'][t], np.repeat(T['n'][t][None], len(T['pts'][t]), 0), dirs).max()
        cause[j] = 'enclosed' if op[j] < 0.05 else 'open'
    ar = T['area']
    out = {}
    for c in ('no_texel', 'thin', 'enclosed', 'open'):
        m = bad[cause == c]
        mats = {}
        for mn in np.unique(T['mat'][m]):
            mats[str(mn)] = round(float(ar[m][T['mat'][m] == mn].sum() * 1e4), 2)
        out[c] = dict(tris=int(len(m)), area_cm2=round(float(ar[m].sum() * 1e4), 2), by_material=mats)
    # the islands behind 'no_texel': size in texels (uv bbox) and in metres, where
    rows = []
    thin_bad = bad[(cause == 'no_texel') | (cause == 'thin')]
    for i in np.unique(isl_t[thin_bad]):
        sel = np.where(isl_t == i)[0]
        tb = thin_bad[isl_t[thin_bad] == i]                 # its black thin faces; the close-up looks at the largest
        U = T['U'][sel].reshape(-1, 2)
        ext = U.max(0) - U.min(0)
        rows.append(dict(island=int(i), texels=int(tex[i]), tris=int(len(sel)), area_cm2=round(float(ar[sel].sum() * 1e4), 2),
                         black_thin_cm2=round(float(ar[tb].sum() * 1e4), 2),
                         uv_bbox_texels=[round(float(ext[0]), 2), round(float(ext[1]), 2)],
                         uv_area_texels=round(float(T['a_uv'][sel].sum()), 2), mat=str(T['mat'][sel[0]]),
                         at_unity=r3(T['cen'][sel].mean(0)), spot_unity=r3(T['cen'][tb[np.argmax(ar[tb])]]),
                         spot_normal=r3(T['n'][tb[np.argmax(ar[tb])]])))
    rows.sort(key=lambda r: -r['black_thin_cm2'])
    out['thin_islands'] = dict(count=len(rows), largest=rows[:k_list])
    isl_all = np.unique(isl_t[keep])
    out['counted_islands'] = dict(count=int(len(isl_all)), without_texel=int((tex[isl_all] == 0).sum()),
                                  under_4_texels=int((tex[isl_all] < 4).sum()))
    eo = np.where(cause == 'enclosed')[0]
    out['enclosed_spots'] = [dict(at_unity=r3(T['cen'][bad[j]]), normal_unity=r3(T['n'][bad[j]]), mat=str(T['mat'][bad[j]]),
                                  area_cm2=round(float(ar[bad[j]] * 1e4), 2)) for j in eo[np.argsort(-ar[bad[eo]])][:k_list]]
    oo = np.where(cause == 'open')[0]
    out['open_spots'] = [dict(at_unity=r3(T['cen'][bad[j]]), normal_unity=r3(T['n'][bad[j]]), mat=str(T['mat'][bad[j]]),
                              area_cm2=round(float(ar[bad[j]] * 1e4), 2), escape=round(float(op[j]), 2))
                         for j in oo[np.argsort(-ar[bad[oo]])][:k_list]]
    return out, bad, cause


def face_list(T, keep, w, A, k=12):
    idx = np.where(keep & (w > 0.10))[0]
    order = idx[np.argsort(-(w[idx] * np.sqrt(T['area'][idx])))]
    rows, seen = [], []
    for t in order:
        c = T['cen'][t]
        if any(np.linalg.norm(c - s) < 0.02 for s in seen):       # one entry per 2 cm cluster
            continue
        seen.append(c)
        rows.append(dict(face=int(A['tp'][t]), weight=round(float(w[t]), 2), area_cm2=round(float(T['area'][t] * 1e4), 2),
                         mat=str(T['mat'][t]), at_unity=r3(c), normal_unity=r3(T['n'][t])))
        if len(rows) >= k:
            break
    return rows


# ------------------------------------------------------------------------------------------------ analysis
def analyse(objs, lm, part_mask):
    dg = bpy.context.evaluated_depsgraph_get()
    t0 = time.time()
    atlas = [o for o in objs.values() if o.type == 'MESH' and (o.name == 'Cabin_Static' or o.name.startswith(ATLAS_PREFIX))]
    data, base, nisl = {}, {}, 0
    for o in sorted(atlas, key=lambda o: o.name):
        A = mesh_arrays(o, dg)
        if A is None:
            continue
        A['isl'] = islands(A, lm.W)
        base[o.name] = nisl
        nisl += int(A['isl'].max()) + 1
        data[o.name] = A
    idmap = np.full((lm.H, lm.W), -1, np.int64)
    clash = []
    for n, A in data.items():
        raster(A['uv'][A['tl']] * np.array([lm.W, lm.H]), base[n] + A['isl'][A['tp']], idmap, clash)
    cross = int(sum(len(c) for c in clash))
    covered = idmap >= 0
    print('[seam] %d atlas objects, %d islands; %.1f s' % (len(data), nisl, time.time() - t0))
    from scipy import ndimage
    lit_in = covered & ~lm.black
    ring_frac = {}
    for tag, st in (('n4', ndimage.generate_binary_structure(2, 1)), ('n8', np.ones((3, 3), bool))):
        rg = ndimage.binary_dilation(lit_in, structure=st) & ~covered
        ring_frac[tag] = round(float(lm.black[rg].mean()), 4)
        ring_frac['texels_' + tag] = int(rg.sum())
    # fix #1 simulated (fill_black): inside the islands only / inside + a 2-texel ring round them
    fills = {}
    for tag, tgt in (('inside', covered), ('inside_ring2', ndimage.binary_dilation(covered, structure=np.ones((3, 3), bool), iterations=2))):
        fa, nf = fill_black(lm.a, tgt)
        fills[tag] = dict(black=(fa == 0).all(-1), filled=nf)
        del fa
    rep = dict(atlas=dict(res=[lm.W, lm.H], objects=len(data), islands=nisl, covered_frac=round(float(covered.mean()), 4),
                          nonblack_frac=round(float((~lm.black).mean()), 4),
                          texels_two_islands=cross, ring_outside_lit_black_frac=ring_frac,
                          fill_sim=dict(passes=3, neighbourhood='3x3, mean of the non-black neighbours',
                                        texels_filled={k: v['filled'] for k, v in fills.items()},
                                        black_frac_after={k: round(float(v['black'].mean()), 4) for k, v in fills.items()}),
                          uv_fill=round(sum(density(A, lm)['uv_area_texels'] for A in data.values()) / float(lm.W * lm.H), 4),
                          density_Cabin_Static=density(data['Cabin_Static'], lm) if 'Cabin_Static' in data else None,
                          density_seats_p50=[min(density(data[n], lm)['p50'] for n in data if n.startswith('Seat_')),
                                             max(density(data[n], lm)['p50'] for n in data if n.startswith('Seat_'))]),
               objects={})
    occluders = [o for o in objs.values() if o.type == 'MESH' and not o.hide_render and not o.name.startswith(('Glass_', 'Bus_Exterior'))]
    bvh_all, base_all = bvh_of(occluders, dg)
    bvh_slice, base_slice = bvh_of([objs[n] for n in SLICE if n in objs], dg)
    # what bake_lightmap.py renders: every mesh but the glass and the tube diffusers (the exterior shell included)
    bvh_bake, _ = bvh_of([o for o in objs.values() if o.type == 'MESH' and not o.hide_render
                          and not o.name.startswith(('Glass_', 'Cabin_Tubes'))], dg)
    lay = json.load(open(os.path.join(ROOT, 'Bus', 'Models', 'BusLayout.json'), encoding='utf-8'))
    eyes = [HERO] + [np.array(s['eye_approx'], float) for s in lay.get('seats', []) if s.get('eye_approx')]
    eyes += [np.array((x, y, z)) for x in (-0.15, 0.15) for y in (1.15, 1.70) for z in (-3.0, -1.5, 0.0, 1.5, 2.6)]
    cams = slice_cams(objs)
    rep['viewpoints'] = dict(bus_eyes=len(eyes), slice_cameras=[dict(id=c['id'], eye=r3(c['eye']), look_at=r3(c['target'])) for c in cams])
    spots = []
    for piece, names in PIECES.items():
        for n in names:
            if n not in data:
                rep['objects'][n] = 'missing'
                continue
            A = data[n]
            T = tri_table(A, lm, part_mask if n.startswith('Seat_') else None)
            vb, vs = visible(T, base_all.get(n, -10 ** 9) + A['tp'], base_slice[n] + A['tp'], bvh_all, bvh_slice, eyes, cams)
            vis = vb | vs
            keep = vis & ~T['metal']
            pkeep = np.zeros(len(A['ps']), bool); pkeep[A['tp'][keep]] = True
            fnames = list(fills)
            black_w, other_w, unlit_w, nopen, fill_w = bleed(A, T, lm, idmap, base[n], bvh_all, keep, [fills[k]['black'] for k in fnames])
            fold_hit, fold_tex = folds(A, T, lm)
            ar = T['area']
            r = dict(piece=piece, triangles=int(len(ar)), area_cm2=round(float(ar.sum() * 1e4), 1),
                     visible_area_cm2=round(float(ar[vis].sum() * 1e4), 1), visible_in_bus_cm2=round(float(ar[vb].sum() * 1e4), 1),
                     visible_in_slice_shots_cm2=round(float(ar[vs].sum() * 1e4), 1),
                     slice_only_cm2=round(float(ar[vs & ~vb].sum() * 1e4), 1),
                     metal_area_cm2=round(float(ar[T['metal']].sum() * 1e4), 1), counted_area_cm2=round(float(ar[keep].sum() * 1e4), 1),
                     density=density(A, lm), islands=dict(count=int(A['isl'].max()) + 1, **island_gaps(A, T, lm, idmap, base[n], keep)))
            r['folds'] = dict(texels=fold_tex, counted_tris=int((fold_hit & keep).sum()),
                              counted_area_cm2=round(float(ar[fold_hit & keep].sum() * 1e4), 2))

            def wstats(w, msk):
                return dict(tris_gt_10pct=int((w[msk] > 0.10).sum()), tris_gt_25pct=int((w[msk] > 0.25).sum()),
                            area_gt_10pct_cm2=round(float(ar[msk][w[msk] > 0.10].sum() * 1e4), 2),
                            area_gt_25pct_cm2=round(float(ar[msk][w[msk] > 0.25].sum() * 1e4), 2),
                            max=round(float(w[msk].max()) if msk.any() else 0.0, 3))
            kb = vb & ~T['metal']                    # seen in the bus: a real defect in the world
            ko = vs & ~vb & ~T['metal']              # seen only in the slice shots (Cabin_Static covers it in the bus)
            r['black'] = dict(in_bus=wstats(black_w, kb), slice_shots=wstats(black_w, vs & ~T['metal']), slice_only=wstats(black_w, ko),
                              visible_metal=wstats(black_w, vis & T['metal']), all=wstats(black_w, np.ones(len(ar), bool)))
            r['unlit_nonmetal'] = dict(in_bus=wstats(unlit_w, kb), slice_only=wstats(unlit_w, ko))
            r['fill_sim'] = {k: dict(in_bus=wstats(fw, kb), slice_shots=wstats(fw, vs & ~T['metal'])) for k, fw in zip(fnames, fill_w)}
            r['neighbour_bleed'] = dict(counted=wstats(other_w, keep), all=wstats(other_w, np.ones(len(ar), bool)))
            r['open_sample_points'] = dict(open=nopen[0], of=nopen[1])
            r['seams'], sp = seams(A, lm, pkeep, bvh_all)
            r['edge_dip'], dp = edge_dip(A, lm, pkeep, bvh_all)
            r['mip_black_counted'] = mip_black(T, lm, keep)
            r['black_causes_in_bus'], bad_t, cause_t = black_causes(A, T, lm, bvh_bake, kb, black_w)
            for k, fw in zip(fnames, fill_w):           # what the fill leaves (in bus, >= 25 %), by the cause found above
                left = fw[bad_t] > 0.25                 # the filled atlas is black only where the raw one is: left within bad
                r['fill_sim'][k]['in_bus_left_by_cause_cm2'] = {c: round(float(ar[bad_t[left & (cause_t == c)]].sum() * 1e4), 2)
                                                               for c in ('no_texel', 'thin', 'enclosed', 'open')}
            r['faces_black_in_bus'] = face_list(T, kb, black_w, A)
            r['faces_black_slice_only'] = face_list(T, ko, black_w, A, 8)
            r['faces_unlit_in_bus'] = face_list(T, kb & (black_w <= 0.10), unlit_w, A, 8)
            by_mat = {}
            for mname in np.unique(T['mat'][keep]):
                mm = keep & (T['mat'] == mname)
                by_mat[str(mname)] = dict(area_cm2=round(float(ar[mm].sum() * 1e4), 1),
                                          in_bus_black_gt_25pct_cm2=round(float(ar[mm & kb & (black_w > 0.25)].sum() * 1e4), 2),
                                          slice_only_black_gt_25pct_cm2=round(float(ar[mm & ko & (black_w > 0.25)].sum() * 1e4), 2),
                                          in_bus_unlit_gt_25pct_cm2=round(float(ar[mm & kb & (unlit_w > 0.25)].sum() * 1e4), 2))
            r['counted_by_material'] = by_mat
            rep['objects'][n] = r
            # close-ups, one per kind of fault: a thin island, black under an attached part, the worst lit seam on a
            # smooth surface, black that only the slice shows (no wall / wheel box round it)
            bc = r['black_causes_in_bus']
            cand = []
            if bc['thin_islands']['largest']:
                ti = bc['thin_islands']['largest'][0]
                cand.append(dict(kind='thin island', mat=ti['mat'], at_unity=ti['spot_unity'], normal_unity=ti['spot_normal']))
            if bc['open_spots']:
                cand.append(dict(kind='under a part', **{k: bc['open_spots'][0][k] for k in ('mat', 'at_unity', 'normal_unity')}))
            if sp:
                cand.append(dict(kind='seam %d%%' % round(100 * sp[0]['rel']), mat=sp[0]['mat'][0], at_unity=sp[0]['at_unity'],
                                 normal_unity=sp[0]['normal_unity']))
            if r['faces_black_slice_only']:
                f = r['faces_black_slice_only'][0]
                cand.append(dict(kind='slice only', **{k: f[k] for k in ('mat', 'at_unity', 'normal_unity')}))
            spots.append([dict(obj=n, piece=piece, **c) for c in cand])
            r['worst_seams'] = sp[:6]
            r['worst_edge_dips'] = dp[:4]
            print('[seam] %s: visible %.0f cm2, counted %.0f cm2; %.1f s' % (n, ar[vis].sum() * 1e4, ar[keep].sum() * 1e4, time.time() - t0))
    # six tiles: the seat's (up to four), then the first of the window and of the pillar
    rep['spots'] = ((spots[0] if spots else [])[:4] + [c[0] for c in spots[1:] if c])[:6]
    return rep, data, cams


# ------------------------------------------------------------------------------------------------ renders
def render_views(objs, lm_img, mask_img, rep, cams, out_dir, samples, threads):
    from PIL import Image, ImageDraw
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'                      # the cores are shared: a few threads only
    sc.render.threads = threads
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0
    sc.cycles.use_adaptive_sampling = False
    sc.render.film_transparent = False
    sc.render.use_compositing = False
    sc.render.use_sequencer = False
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
    sc.world = sc.world or bpy.data.worlds.new('W')
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs[0].default_value = (0.02, 0.02, 0.025, 1)
        bg.inputs[1].default_value = 1.0

    def make_mat(channel):
        mat = bpy.data.materials.new('LM_' + channel)
        mat.use_nodes = True
        nt = mat.node_tree
        for nd in list(nt.nodes):
            nt.nodes.remove(nd)
        uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVLightmap'
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = lm_img; t.interpolation = 'Linear'; t.extension = 'EXTEND'
        tm = nt.nodes.new('ShaderNodeTexImage'); tm.image = mask_img; tm.interpolation = 'Linear'; tm.extension = 'EXTEND'
        nt.links.new(uvn.outputs[0], t.inputs[0]); nt.links.new(uvn.outputs[0], tm.inputs[0])
        add = nt.nodes.new('ShaderNodeVectorMath'); add.operation = 'ADD'
        nt.links.new(t.outputs['Color' if channel == 'E' else 'Alpha'], add.inputs[0])
        nt.links.new(tm.outputs['Color'], add.inputs[1])
        em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(add.outputs[0], em.inputs[0])
        outn = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], outn.inputs[0])
        return mat
    mats = {'E': make_mat('E'), 'AO': make_mat('AO')}
    orig = {n: [matkey(m.name) if m else '-' for m in objs[n].data.materials] for n in SLICE if n in objs}
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE', 'LIGHT'):
            o.hide_render = True
    cam_d = bpy.data.cameras.new('SliceCam')
    cam_d.sensor_fit = 'HORIZONTAL'
    cam_d.angle = math.radians(40.0)
    cam_d.clip_start = 0.01
    cam = bpy.data.objects.new('SliceCam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    W = int(round(2 * math.tan(math.radians(20)) * 20 * 180 / math.pi))      # 40 x 30 deg at 20 px/deg (crop_deg + ppd)
    H = int(round(2 * math.tan(math.radians(15)) * 20 * 180 / math.pi))
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    tmpd = tempfile.mkdtemp(prefix='lmseam_r_')

    def show(names, channel):
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = o.name not in names
        for n in names:
            me = objs[n].data
            for i in range(len(me.materials)):
                me.materials[i] = mats[channel]

    def shoot(eye_u, target_u, exposure):
        e, tg = u2b(eye_u), u2b(target_u)
        cam.location = e
        cam.rotation_euler = (tg - e).to_track_quat('-Z', 'Y').to_euler()
        sc.view_settings.exposure = exposure
        p = os.path.join(tmpd, 'r.png')
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        return Image.open(p).convert('RGB').copy()

    def board(tiles, cols, fname, scale=2 / 3):
        tw, th = int(W * scale), int(H * scale)
        rows = (len(tiles) + cols - 1) // cols
        im = Image.new('RGB', (tw * cols, th * rows), (0, 0, 0))
        dr = ImageDraw.Draw(im)
        for i, (img, label) in enumerate(tiles):
            x, y = (i % cols) * tw, (i // cols) * th
            im.paste(img.resize((tw, th), Image.Resampling.LANCZOS), (x, y))
            dr.rectangle([x, y, x + tw - 1, y + th - 1], outline=(60, 60, 60))
            dr.rectangle([x, y, x + 8 + 6 * len(label), y + 14], fill=(0, 0, 0))
            dr.text((x + 4, y + 2), label, fill=(255, 255, 255))
        path = os.path.join(out_dir, fname)
        im.save(path, optimize=True)
        while os.path.getsize(path) > 380 * 1024:          # keep each PNG under 400 KB: 256-colour palette, then smaller
            im.quantize(256, dither=Image.Dither.NONE).save(path, optimize=True)
            if os.path.getsize(path) <= 380 * 1024:
                break
            im = im.resize((int(im.width * 0.85), int(im.height * 0.85)), Image.Resampling.LANCZOS)
            im.save(path, optimize=True)
        return fname
    files = []
    for channel, expo in (('E', -1.0), ('AO', 0.0)):
        tiles = []
        for c in cams:
            show(PIECES[c['piece']], channel)
            tiles.append((shoot(c['eye'], c['target'], expo), '%s  %s  (%s)' % (c['id'], channel, 'E x0.5' if channel == 'E' else 'AO')))
        files.append(board(tiles, 2, 'lm_slice_cams_%s.png' % channel))
    tiles = []
    for s in rep.get('spots', [])[:6]:
        show([s['obj']], 'E')
        p = np.array(s['at_unity']); n = np.array(s['normal_unity'])
        toh = HERO - p
        toh /= np.linalg.norm(toh)
        v = n if np.dot(n, toh) > 0 else -n
        v = v * 0.7 + toh * 0.3
        v /= np.linalg.norm(v)
        lab = '%s %s %s' % (s['piece'], s['kind'], s.get('mat', ''))
        tiles.append((shoot(p + v * 0.20, p, -1.0), lab[:60]))
    if tiles:
        files.append(board(tiles, 2, 'lm_spots_E.png'))

    # ---- on screen: of the pieces' NON-METAL pixels, the share whose _CabinTubeLM sample is >= 25 % / >= 50 % black.
    #      The six test cameras (pieces alone, as in the slice scene) and three views in the whole bus (everything else
    #      opaque drawn as an occluder): the hero toward WinR1, the SeatR1 passenger at R0's back, an aisle passenger at
    #      the stop-button box.
    def emis_mat(name, rgb=None, mask=False):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        for nd in list(nt.nodes):
            nt.nodes.remove(nd)
        em = nt.nodes.new('ShaderNodeEmission')
        if mask:
            uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVLightmap'
            tm = nt.nodes.new('ShaderNodeTexImage'); tm.image = mask_img; tm.interpolation = 'Linear'; tm.extension = 'EXTEND'
            nt.links.new(uvn.outputs[0], tm.inputs[0])
            sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tm.outputs['Color'], sep.inputs[0])
            cmb = nt.nodes.new('ShaderNodeCombineColor')
            nt.links.new(sep.outputs[0], cmb.inputs[0]); cmb.inputs[1].default_value = 1.0; cmb.inputs[2].default_value = 0.0
            nt.links.new(cmb.outputs[0], em.inputs[0])
        else:
            em.inputs[0].default_value = (*rgb, 1)
        outn = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], outn.inputs[0])
        return mat
    m_meas, m_metal, m_occ, m_ctx = emis_mat('Meas', mask=True), emis_mat('MeasMetal', (0, 0, 0)), emis_mat('Occ', (0, 0, 0)), emis_mat('Ctx', (0.03, 0.03, 0.03))
    context = [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in SLICE and not o.name.startswith(('Glass_', 'Bus_Exterior'))]

    def show_measure(names, with_context, ctx_mat):
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = not (o.name in names or (with_context and o in context))
        for n in names:
            me = objs[n].data
            for i in range(len(me.materials)):
                me.materials[i] = m_metal if orig[n][i] in METAL else m_meas
        if with_context:
            for o in context:
                for i in range(len(o.data.materials)):
                    o.data.materials[i] = ctx_mat

    def measure(eye_u, target_u):
        sc.render.image_settings.file_format = 'OPEN_EXR'
        e, tg = u2b(eye_u), u2b(target_u)
        cam.location = e
        cam.rotation_euler = (tg - e).to_track_quat('-Z', 'Y').to_euler()
        pth = os.path.join(tmpd, 'm.exr')
        sc.render.filepath = pth
        sc.view_settings.exposure = 0.0                      # the mask is read back as numbers
        smp = sc.cycles.samples
        sc.cycles.samples = 4
        bpy.ops.render.render(write_still=True)
        sc.cycles.samples = smp
        sc.render.image_settings.file_format = 'PNG'
        im = bpy.data.images.load(pth, check_existing=False)
        px = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(-1, 4)
        bpy.data.images.remove(im)
        nm = px[:, 1] > 0.5
        return dict(nonmetal_px=int(nm.sum()), black_ge25_pct=round(100.0 * float((nm & (px[:, 0] >= 0.25)).sum()) / max(nm.sum(), 1), 2),
                    black_ge50_pct=round(100.0 * float((nm & (px[:, 0] >= 0.50)).sum()) / max(nm.sum(), 1), 2))
    onscreen = {}
    for c in cams:
        show_measure(PIECES[c['piece']], False, m_occ)
        onscreen[c['id']] = measure(c['eye'], c['target'])
    lay = json.load(open(os.path.join(ROOT, 'Bus', 'Models', 'BusLayout.json'), encoding='utf-8'))
    r1 = next((s_['eye_approx'] for s_ in lay.get('seats', []) if s_.get('name', '').endswith('SeatR1') and s_.get('eye_approx')), [0.55, 1.70, 1.30])

    def yp(eye, yaw, pitch):
        a, b = math.radians(yaw), math.radians(pitch)
        return np.array(eye) + np.array([math.sin(a) * math.cos(b), math.sin(b), math.cos(a) * math.cos(b)])
    bus_views = [('hero_window_yaw61', HERO, yp(HERO, 61, -5), 90.0),
                 ('seatR1_at_R0_back', np.array(r1, float), np.array([0.55, 1.25, 1.78]), 60.0),
                 ('aisle_at_button_box', np.array([-0.10, 1.65, 0.20]), np.array([0.29, 1.50, 1.04]), 60.0)]
    W0, H0, A0 = sc.render.resolution_x, sc.render.resolution_y, cam_d.angle
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    tiles = []
    for vid, eye, tgt, fov in bus_views:
        cam_d.angle = math.radians(fov)
        show_measure(SLICE, True, m_occ)
        onscreen[vid] = measure(eye, tgt)
        show(SLICE, 'E')
        for o in context:
            o.hide_render = False
            for i in range(len(o.data.materials)):
                o.data.materials[i] = m_ctx
        tiles.append((shoot(eye, tgt, -1.0).resize((W, H)), '%s  E x0.5 (rest of the bus dark grey)' % vid))
    files.append(board(tiles, 1, 'lm_bus_views_E.png', scale=0.75))
    sc.render.resolution_x, sc.render.resolution_y, cam_d.angle = W0, H0, A0
    rep['onscreen_black'] = dict(views=onscreen, bus_views=[dict(id=v[0], eye=r3(v[1]), look_at=r3(v[2]), hfov=v[3]) for v in bus_views],
                                 note='share of the pieces\' non-metal pixels whose bilinear _CabinTubeLM sample has >= 25 % / 50 % '
                                      'weight from black texels (E = 0 and AO = 0); metal slots (Steel, Alu, Chrome) excluded')
    shutil.rmtree(tmpd, ignore_errors=True)
    rep['renders'] = dict(files=files, tile_px=[int(W * 2 / 3), int(H * 2 / 3)], rendered_px=[W, H], fov_deg=[40, 30], samples=samples,
                          note='emission only: E = _CabinTubeLM.rgb (exposure -1 EV) or AO = .a, bilinear mip 0; magenta = '
                               'bilinear weight of black texels; spots: 0.20 m from the spot')


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--blend', default='/tmp/bus/bus_final_ext.blend')
    ap.add_argument('--exr', default=os.path.join(ROOT, 'Bus', 'Textures', 'Cabin_TubeLM.exr'))
    ap.add_argument('--out', default=HERE)
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--samples', type=int, default=16)
    ap.add_argument('--threads', type=int, default=2)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='lmseam_')
    work = os.path.join(tmp, 'bus_final_ext_copy.blend')
    shutil.copyfile(a.blend, work)                         # never open (or risk saving) the original
    bpy.ops.wm.open_mainfile(filepath=work, load_ui=False)
    objs = {o.name: o for o in bpy.data.objects}
    img = bpy.data.images.load(a.exr, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    W, H = img.size
    arr = np.empty(W * H * 4, np.float32)
    img.pixels.foreach_get(arr)
    arr = arr.reshape(H, W, 4)
    lm = LM(arr)
    part_mask = None
    pm_path = os.path.join(ROOT, 'Bus', 'Textures', 'Parts', 'Part_SeatHero_Mask_2048.png')
    if os.path.exists(pm_path):
        from PIL import Image
        part_mask = np.asarray(Image.open(pm_path).convert('RGBA'))[..., 0] / 255.0
    rep, data, cams = analyse(objs, lm, part_mask)
    L = lum(arr[..., :3])
    rep['source'] = dict(blend=a.blend, exr=os.path.relpath(a.exr, ROOT), uv='UVLightmap',
                         exr_stats=dict(E_lum_max=round(float(L.max()), 3), E_lum_p99_nonblack=round(float(np.percentile(L[~lm.black], 99)), 3),
                                  texels_E_over_1=int((L > 1).sum())))
    if not a.no_render:
        mk = np.zeros_like(arr)
        mk[..., 0] = lm.black * 1.0
        mk[..., 2] = lm.black * 1.0
        mk[..., 3] = 1.0
        mimg = bpy.data.images.new('BlackMask', W, H, alpha=True, float_buffer=True)
        mimg.colorspace_settings.name = 'Non-Color'
        mimg.pixels.foreach_set(mk.ravel())
        mimg.pack()
        render_views(objs, img, mimg, rep, cams, a.out, a.samples, a.threads)
    with open(os.path.join(a.out, 'lm_seams.json'), 'w', encoding='utf-8') as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    shutil.rmtree(tmp, ignore_errors=True)
    print('[seam] wrote', os.path.join(a.out, 'lm_seams.json'))


if __name__ == '__main__':
    main()
