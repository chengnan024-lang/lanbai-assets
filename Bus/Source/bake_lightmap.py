# -*- coding: utf-8 -*-
"""烘 _CabinTubeLM（圣经 §1.6 / §4.3：只有车、只开 10 根灯管）到 Cabin_Static、各个座位（D-36：Seat_*）和切片的两件
（D-40 #1：Window_R1、Pole_R0，finish_bus.SEPARATE）的 uv1（同一张图）。
EXR 里存的数：RGB = 管灯照度 E（Unity 单位）按 sRGB 曲线编码以后的值 s = srgb_encode(E)（1 以上用同一个公式：
0.1 → 0.349，0.6 → 0.798，2.0 → 1.353）；A = AO（0.5 m），线性，不编码；RGBA half，ZIP。
Unity 采到的就是 s：导入是线性的（LanbaiCabinImport：sRGBTexture 关、RGBAHalf），Lanbai/Cabin 里
albedo × LM.rgb × _Udon_CabinLightmap 乘的 LM.rgb 就是 s；Blender 的看图、检查脚本也都按 Non-Color 直接读 s。
这一步编码以前是 image.save() 顺带做的（存成 float32，标成 sRGB），到现在通过的画面都是这个样子。这一轮定了：样子不变，
编码改成在这里用 numpy 明写，save_exr 把 s 原样写进 half EXR，不经过任何颜色管理。
校准：主座位座垫中心的 E = 0.8（圣经 §4.3，S2 下灰卡 #585F64）。光的传输对瓦数是线性的，所以烘一次、按座垫读数整体缩放。
校准和 bake_report.json 里的 E 都是线性的 E；报告另外给出存进去的数（E_stored）。

    ~/bpy/bin/python Bus/Source/bake_lightmap.py --blend /tmp/bus/bus_final.blend --out Bus/Textures --res 1024 --samples 96
输出：Cabin_TubeLM.exr（RGBA half，ZIP，内容见上）、Cabin_TubeLM_preview.png（看的）、bake_report.json
Cycles 的漫反射烘焙（直接 + 间接、不乘颜色）= 白色朗伯面的出射亮度 = E_cycles / π；灯按标准台的约定是 π × E_unity，
所以烘出来的数就是 E_unity。
After the black fill, two post-bake steps (both in bake_report.json): bracket_patch (the slice seat's wall bracket,
re-baked without the cabin shell round it; linear E) then, on the encoded values, seam_stitch (uv1 seams on smooth
surfaces, least squares on Unity's bilinear footprints).
"""
import argparse
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bus_spec as B  # noqa: E402

LUM = np.array((0.2126, 0.7152, 0.0722))   # Rec. 709 luminance (= lm_seam_check, which reads the stored values)
SLICE_SEATS = ('Seat_SeatR0',)             # D-40: the slice scene shows this one alone, on this same atlas
SEAM_UV = 0.25                             # texels: two faces' uv further apart at an end of their edge = a uv seam
STITCH_LAMBDA = 1e-2                       # pull back toward the bake; see seam_stitch
STITCH_LIT = 0.02                          # stored luminance below this on either side is ~0: darkness, not a seam
                                           # (= lm_seam_check's FLOOR_E, same units)
STITCH_FLOOR = 0.1                         # the stitch takes no texel below this x its value (nor AO above 1)
STITCH_PASSES = 8                          # active-set solves per channel, at most


def U(v):
    return (v[0], v[2], v[1])


def add_tubes(watts):
    col = (0.776, 0.882, 0.894)       # #E4F1F3 linear
    for r, x, zl in (('L', B.TUBE_X[0], B.TUBE_Z_L), ('R', B.TUBE_X[1], B.TUBE_Z)):
        for i, (z0, z1) in enumerate(zl):
            ld = bpy.data.lights.new('LM_Tube%s%d' % (r, i), 'AREA')
            ld.shape = 'RECTANGLE'
            ld.size, ld.size_y = 0.12, (z1 - z0) - 0.06
            ld.energy = watts
            ld.color = col
            o = bpy.data.objects.new(ld.name, ld)
            o.location = (x, (z0 + z1) / 2, B.CEIL_Y - 0.05)       # blender (x, z_unity, y_unity), facing down
            bpy.context.scene.collection.objects.link(o)
            # the opal diffuser also throws light sideways / up onto the ceiling round it (bible 4.3: the ceiling next to
            # the tubes reads 200-215): a weak up-facing twin, 12 % of the power
            lu = bpy.data.lights.new(ld.name + '_up', 'AREA')
            lu.shape, lu.size, lu.size_y, lu.energy, lu.color = 'RECTANGLE', 0.14, ld.size_y, watts * 0.12, col
            ou = bpy.data.objects.new(lu.name, lu)
            ou.location = (x, (z0 + z1) / 2, B.CEIL_Y - 0.04)
            ou.rotation_euler = (math.pi, 0, 0)
            bpy.context.scene.collection.objects.link(ou)


def bake(objs, img, kind, samples, margin=2):     # = finish_bus.LM_MARGIN (2 texels a side at 2048)
    """bake into one image over several objects (Cabin_Static + the D-36 seats), each on its uv1 'UVLightmap'."""
    sc = bpy.context.scene
    sc.cycles.samples = samples
    for ob in objs:
        me = ob.data
        me.uv_layers.active = me.uv_layers['UVLightmap']
        for m in me.materials:
            m.use_nodes = True
            nt = m.node_tree
            n = nt.nodes.get('LM_Target') or nt.nodes.new('ShaderNodeTexImage')
            n.name = 'LM_Target'
            n.image = img
            nt.nodes.active = n
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    sc.render.bake.margin = margin
    sc.render.bake.target = 'IMAGE_TEXTURES'
    sc.render.bake.use_selected_to_active = False
    sc.render.bake.use_clear = True
    if kind == 'DIFFUSE':
        sc.render.bake.use_pass_direct = True
        sc.render.bake.use_pass_indirect = True
        sc.render.bake.use_pass_color = False
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'})
    else:
        bpy.ops.object.bake(type='AO')
    return np.array(img.pixels[:], np.float32).reshape(img.size[1], img.size[0], 4)


def srgb_encode(e):
    """Blender's sRGB curve (what image.save() applied to this EXR up to now), the same formula above 1."""
    e = np.asarray(e, np.float64)
    return np.where(e <= 0.0031308, 12.92 * e, 1.055 * np.power(np.maximum(e, 0.0031308), 1 / 2.4) - 0.055)


def srgb_decode(s):
    s = np.asarray(s, np.float64)
    return np.where(s <= 0.04045, s / 12.92, np.power((np.maximum(s, 0.04045) + 0.055) / 1.055, 2.4))


def encode(lin):
    """linear (E, AO) -> what the EXR stores: RGB srgb_encode(E), A as it is."""
    s = lin.copy()
    s[..., :3] = srgb_encode(lin[..., :3])
    return s


def save_exr(stored, path):
    """write 'stored' as it is: RGBA half, ZIP. A Non-Color float image through save_render to OPEN_EXR gets no view
    transform / look / exposure and no premultiply (Blender 5.0.1: the file holds float16(given), colorInteropID
    'lin_rec709_scene', the same under AgX + a look). Read back and compared. -> file size (bytes)"""
    sc = bpy.context.scene
    H, W = stored.shape[:2]
    im = bpy.data.images.new('LMout', W, H, alpha=True, float_buffer=True)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(stored, np.float32).ravel())
    s = sc.render.image_settings
    s.file_format, s.color_mode, s.color_depth, s.exr_codec = 'OPEN_EXR', 'RGBA', '16', 'ZIP'
    im.save_render(path, scene=sc)
    back = bpy.data.images.load(path, check_existing=False)
    back.colorspace_settings.name = 'Non-Color'
    got = np.empty(W * H * 4, np.float32)
    back.pixels.foreach_get(got)
    assert np.array_equal(got, stored.astype(np.float16).astype(np.float32).ravel()), 'EXR read back != float16(stored)'
    bpy.data.images.remove(back)
    bpy.data.images.remove(im)
    return os.path.getsize(path)


def uv_tris(ob, res, polys=None):
    """ob's 'UVLightmap' loop triangles, (n, 3, 2) in pixels (u * res - 0.5: texel centres on integers); polys: a
    polygon mask, only those."""
    me = ob.data
    me.calc_loop_triangles()
    uv = np.empty(2 * len(me.loops), np.float32)
    me.uv_layers['UVLightmap'].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2) * res - 0.5                        # texel centres at (i + 0.5) / res
    tri = np.empty(3 * len(me.loop_triangles), np.int64)
    me.loop_triangles.foreach_get('loops', tri)
    tri = tri.reshape(-1, 3)
    if polys is not None:
        tp = np.empty(len(me.loop_triangles), np.int64)
        me.loop_triangles.foreach_get('polygon_index', tp)
        tri = tri[polys[tp]]
    return uv[tri]


def island_labels(groups, res):
    """per texel, 1 + the index of the triangle group (uv_tris of an object or a part) covering it, 0 = none (row 0 =
    v 0, like img.pixels). Islands are >= 4 texels apart, so the conservative raster (fill + outline) never overlaps."""
    from PIL import Image, ImageDraw
    assert len(groups) < 255
    im = Image.new('L', (res, res), 0)
    d = ImageDraw.Draw(im)
    for g, tris in enumerate(groups):
        for t in tris:
            d.polygon([tuple(p) for p in t], fill=g + 1, outline=g + 1)
    return np.asarray(im).astype(np.int16)


def _shift(a, dy, dx):
    out = np.zeros_like(a)
    H, W = a.shape[:2]
    ys, yd = (slice(dy, H), slice(0, H - dy)) if dy >= 0 else (slice(0, H + dy), slice(-dy, H))
    xs, xd = (slice(dx, W), slice(0, W - dx)) if dx >= 0 else (slice(0, W + dx), slice(-dx, W))
    out[ys, xs] = a[yd, xd]
    return out


def fill_black(arr, mask, ring=2, passes=3):
    """D-40 #1 seam check (Docs~/slice/光照图接缝检查.md, fix 1): texels the bake left black (E = 0 and AO = 0: faces
    thinner than a texel, texels under an attached part, the bake margin copied from them) inside the islands and in a
    ring of 'ring' texels round them take the mean of their non-black 3 x 3 neighbours, 'passes' times. A texel a
    bilinear lookup on a visible face can reach is then never black. Returns the number of texels filled."""
    m = mask.copy()
    for _ in range(ring):
        m = m | _shift(m, 1, 0) | _shift(m, -1, 0) | _shift(m, 0, 1) | _shift(m, 0, -1)
    filled = 0
    for _ in range(passes):
        black = ~np.any(arr != 0, axis=-1)
        todo = black & m
        if not todo.any():
            break
        acc = np.zeros_like(arr)
        cnt = np.zeros(arr.shape[:2], np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ok = _shift(~black, dy, dx)
                acc += _shift(arr, dy, dx) * ok[..., None]
                cnt += ok
        sel = todo & (cnt > 0)
        arr[sel] = acc[sel] / cnt[sel][:, None]
        filled += int(sel.sum())
    return filled


def _world_co(ob):
    me = ob.data
    co = np.empty(3 * len(me.vertices))
    me.vertices.foreach_get('co', co)
    M = np.array(ob.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]           # blender (x, z_unity, y_unity)


def wall_bracket(ob, wall_x=B.X_IN_R, reach=0.03):
    """polygon masks (bracket, frame) of a right-wall seat. finish_bus joins the seat into one mesh with one material
    (the part atlas), so the bracket (parts/seat.py: WallPlate, two WallBolt heads, WallArm) is found by place: the
    loose parts reaching within 3 cm of the wall (everything else of the seat stays >= 19 cm off it). frame, for
    comparison: the other loose parts reaching down to the arm's level (the frame tubes it hangs off, box brackets)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    me = ob.data
    nV = len(me.vertices)
    ev = np.empty(2 * len(me.edges), np.int64)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)
    part = connected_components(coo_matrix((np.ones(len(ev)), (ev[:, 0], ev[:, 1])), shape=(nV, nV)), directed=False)[1]
    co = _world_co(ob)
    n = part.max() + 1
    xmin, xmax, ymin = np.full(n, 1e9), np.full(n, -1e9), np.full(n, 1e9)
    np.minimum.at(xmin, part, co[:, 0])
    np.maximum.at(xmax, part, co[:, 0])
    np.minimum.at(ymin, part, co[:, 2])
    br = xmax >= wall_x - reach
    arm = np.argmax(np.where(br, xmax - xmin, -1))
    fr = ~br & (ymin <= ymin[arm] + 0.005)
    ps = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get('loop_start', ps)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get('vertex_index', lv)
    pp = part[lv[ps]]
    return br[pp], fr[pp]


def bracket_patch(out, objs, lab, k, samples):
    """D-40 slice, 'the wall fixing plate, black lightmap': in the bus the hero seat's wall bracket sits inside the
    wheel box against the side wall and bakes black (right, and unseen there); the slice scene shows the seat alone on
    this atlas, where it is a black T. Its texels (the bracket islands + the 2-texel ring nearer to them than to any
    other island) take a second bake of the seat with the shell hidden (same tubes, scale k, sample counts), unless
    black there too (a face enclosed even then); every other texel stays. The shell = Cabin_Static and every other
    mesh not on this atlas: with Cabin_Static alone hidden, Bus_Exterior_LOD0/1 still block all 50 test rays from the
    plate to the tubes. hide_render rather than shadow rays off: the median comes out the same (0.055 vs 0.054 at 16
    samples), but with the shell still in the diffuse rays the plate's back reads the unshadowed wall it is bolted
    to, which the slice does not have. A few texels lit in the bus come out unlit (E 0, AO kept; texels_newly_unlit):
    their only light was off the shell; left so, as the slice has none. lab: island_labels of objs. -> report dict."""
    from scipy import ndimage
    sc = bpy.context.scene
    bg = sc.world.node_tree.nodes['Background'].inputs[1]
    res = out.shape[0]
    rep = {}
    for name in SLICE_SEATS:
        ob = bpy.data.objects.get(name)
        if ob is None or ob not in objs:
            continue
        br, fr = wall_bracket(ob)
        if not br.any():
            continue
        mb = island_labels([uv_tris(ob, res, br)], res) > 0
        mf = island_labels([uv_tris(ob, res, fr)], res) > 0
        others = ((lab > 0) & (lab != objs.index(ob) + 1)) | (island_labels([uv_tris(ob, res, ~br)], res) > 0)
        ring = (ndimage.distance_transform_cdt(~mb, metric='taxicab') <= 2) & \
               (ndimage.distance_transform_edt(~mb) < ndimage.distance_transform_edt(~others))
        region = (mb | ring) & ~others                       # = fill_black's 2-texel ring (4-neighbour steps)
        t0 = time.time()
        shell = [o for o in bpy.data.objects if o.type == 'MESH' and o not in objs and not o.hide_render] + \
                [bpy.data.objects['Cabin_Static']]
        for o in shell:
            o.hide_render = True
        bg.default_value = 0.0
        e = bake([ob], bpy.data.images.new('LM_' + name, res, res, alpha=True, float_buffer=True), 'DIFFUSE', samples)
        bg.default_value = 1.0
        ao = bake([ob], bpy.data.images.new('AO_' + name, res, res, alpha=True, float_buffer=True), 'AO',
                  max(16, samples // 3))
        for o in shell:
            o.hide_render = False
        alone = np.zeros_like(out)
        alone[..., :3] = e[..., :3] * k
        alone[..., 3] = ao[..., 0]
        fill_black(alone, mb)
        take = region & np.any(alone != 0, axis=-1)          # black there too: keeps the bus value
        before = out.copy()
        out[take] = alone[take]
        diff = np.any(before != out, axis=-1)
        assert not diff[~region].any()                         # every other texel unchanged
        L0, L1 = before[..., :3] @ LUM, out[..., :3] @ LUM
        unlit = ~np.any(out[..., :3] != 0, axis=-1) & np.any(before[..., :3] != 0, axis=-1)
        q = lambda v, p: round(float(np.percentile(v, p)), 4)
        rep[name] = dict(bracket_faces=int(br.sum()), region_texels=int(region.sum()), texels_replaced=int(take.sum()),
                         island_texels=int(mb.sum()), texels_changed=int(diff.sum()),
                         changed_outside=int(diff[~region].sum()), texels_newly_unlit=int(unlit.sum()),
                         newly_unlit_in_islands=int((unlit & mb).sum()),
                         hidden=len(shell), E_median_before=q(L0[mb], 50), E_median_after=q(L1[mb], 50),
                         E_p75_after=q(L1[mb], 75), E_zero_frac_before=round(float((L0[mb] <= 0).mean()), 3),
                         E_zero_frac_after=round(float((L1[mb] <= 0).mean()), 3),
                         AO_median_before=q(before[..., 3][mb], 50), AO_median_after=q(out[..., 3][mb], 50),
                         frame_faces=int(fr.sum()), frame_E_median=q(L1[mf], 50), frame_E_p75=q(L1[mf], 75),
                         frame_AO_median=q(out[..., 3][mf], 50), seconds=round(time.time() - t0, 1))
        print('[bake] bracket %s: %d faces, %d texels replaced (%d lit in the bus now unlit, left so), '
              'E median %.3f -> %.3f (frame %.3f); %.0f s'
              % (name, br.sum(), take.sum(), unlit.sum(), rep[name]['E_median_before'], rep[name]['E_median_after'],
                 rep[name]['frame_E_median'], time.time() - t0))
    return rep


def _taps(uv, res):
    """Unity's bilinear at mip 0, uv in texels (u * res): texel centres at i + 0.5, clamp to edge.
    -> (n, 4) flat texel indices (row = v), (n, 4) weights."""
    x, y = uv[:, 0] - 0.5, uv[:, 1] - 0.5
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    x0, y0 = x0.astype(np.int64), y0.astype(np.int64)
    xs = np.clip(np.stack([x0, x0 + 1, x0, x0 + 1], 1), 0, res - 1)
    ys = np.clip(np.stack([y0, y0, y0 + 1, y0 + 1], 1), 0, res - 1)
    return ys * res + xs, np.stack([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy], 1)


def seam_edges(ob, res, weld=1e-5):
    """ob's 'UVLightmap' seams that should not show: edges connected in 3D (vertices welded within 1e-5 m: the
    edge-split copies) whose two faces' uv differ by > SEAM_UV texel at either end, and smooth across: smooth-shaded
    (same vertices, both faces smooth, edge not sharp) with dihedral < 60 deg, or any shading < 30 deg. Along a smooth
    edge both faces bake with the same shading normal, so E is continuous there; uv1's box-projection chunks (cut where
    the normal turns > 45 deg) put such cuts on rounded surfaces, each side baked on its own.
    -> uv in texels (u * res) at the two ends on side a and side b (a0, a1, b0, b1), edge length (m)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    me = ob.data
    nV, nL, nP, nE = len(me.vertices), len(me.loops), len(me.polygons), len(me.edges)
    co = _world_co(ob)
    pr = cKDTree(co).query_pairs(weld, output_type='ndarray')
    wid = connected_components(coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(nV, nV)), directed=False)[1]
    lv = np.empty(nL, np.int64)
    me.loops.foreach_get('vertex_index', lv)
    le = np.empty(nL, np.int64)
    me.loops.foreach_get('edge_index', le)
    ps = np.empty(nP, np.int64)
    me.polygons.foreach_get('loop_start', ps)
    pt = np.empty(nP, np.int64)
    me.polygons.foreach_get('loop_total', pt)
    lp = np.repeat(np.arange(nP), pt)
    nxt = np.arange(nL) + 1
    nxt[ps + pt - 1] = ps
    uv = np.empty(2 * nL, np.float32)
    me.uv_layers['UVLightmap'].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2).astype(np.float64) * res
    pn = np.empty(3 * nP, np.float32)
    me.polygons.foreach_get('normal', pn)
    pn = pn.reshape(-1, 3) @ np.linalg.inv(np.array(ob.matrix_world)[:3, :3])
    pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-12)

    def flag(name, n):
        f = np.zeros(n, bool)
        at = me.attributes.get(name)
        if at is not None:
            at.data.foreach_get('value', f)
        return f
    sharp_f, sharp_e = flag('sharp_face', nP), flag('sharp_edge', nE)
    # half-edges (loop l -> nxt[l]) keyed by their welded ends; a key held by exactly two is a 3D-connected edge, one
    # held by more (coincident parts) pairs the two half-edges of the same mesh edge
    wa, wb = wid[lv], wid[lv[nxt]]

    def pair(hh, kk):                                      # -> both half-edges of each key held by 2, the rest
        o = np.argsort(kk, kind='stable')
        hh, kk = hh[o], kk[o]
        first = np.r_[True, kk[1:] != kk[:-1]]
        gid = np.cumsum(first) - 1
        c = np.bincount(gid)[gid]
        i2 = np.nonzero(first & (c == 2))[0]
        return hh[i2], hh[i2 + 1], hh[c > 2]
    h = np.nonzero(wa != wb)[0]
    ha, hb, more = pair(h, np.minimum(wa[h], wb[h]) * nV + np.maximum(wa[h], wb[h]))
    if len(more):
        h2a, h2b, _ = pair(more, (np.minimum(wa[more], wb[more]) * nV + np.maximum(wa[more], wb[more])) * nE + le[more])
        ha, hb = np.r_[ha, h2a], np.r_[hb, h2b]

    def ends(x):                                           # (loop at the lower weld id, loop at the other end)
        s = wid[lv[x]] < wid[lv[nxt[x]]]
        return np.where(s, x, nxt[x]), np.where(s, nxt[x], x)
    a0, a1 = ends(ha)
    b0, b1 = ends(hb)
    fa, fb = lp[ha], lp[hb]
    seam = (np.linalg.norm(uv[a0] - uv[b0], axis=1) > SEAM_UV) | (np.linalg.norm(uv[a1] - uv[b1], axis=1) > SEAM_UV)
    ang = np.degrees(np.arccos(np.clip((pn[fa] * pn[fb]).sum(1), -1, 1)))
    smooth = (lv[a0] == lv[b0]) & (lv[a1] == lv[b1]) & ~sharp_f[fa] & ~sharp_f[fb] & ~sharp_e[le[ha]] & ~sharp_e[le[hb]]
    s = seam & (fa != fb) & ((smooth & (ang < 60)) | (ang < 30))
    a0, a1, b0, b1 = a0[s], a1[s], b0[s], b1[s]
    return uv[a0], uv[a1], uv[b0], uv[b1], np.linalg.norm(co[lv[a1]] - co[lv[a0]], axis=1)


def seam_stitch(arr, objs, owner, lam=STITCH_LAMBDA, lit=STITCH_LIT, floor=STITCH_FLOOR, passes=STITCH_PASSES):
    """Unity's 'Stitch Seams', which never runs on ours (baked in Blender). arr = the STORED values (RGB sRGB-encoded E,
    A = AO): Unity's bilinear interpolates those, so equal footprints there = no seam on screen; every luminance here
    is in those units. Along every seam_edges() edge, points every <= 0.5 texel (of the longer uv side), where the two
    sides' bilinear footprints (Unity's: 4 texels each) should read the same. Least squares over the footprint texels
    only, each channel:
        min  sum_k |bilerp_a(k) - bilerp_b(k)|^2 + lam * sum_i |x_i - x0_i|^2,   x_i >= floor * x0_i,  AO <= 1
    (normal equations, sparse LU; one system for all objects, block-diagonal as no texel is shared). The bounds by a
    primal-dual active set: a texel the solve takes below floor x its value (a dark tap beside a bright one in one
    footprint) or an AO above 1 is held at that bound (moved to the right-hand side; its points stay, its footprint
    partners take the rest), a held texel the gradient would lift off its bound is let go, and the free ones are
    solved again, until the held sets settle (<= passes solves per channel), then clipped to the bounds (floor x0 > 0
    and AO 1: never a new black texel).
    lam = 1e-2 is the largest that closes them: LAMBDA_NOTE
    Left out: points where either side reads a luminance < lit or touches an unlit / black texel (darkness is not a seam
    to blend) and points reaching another object's island. owner: per texel the index in objs of the island's object,
    -1 none. -> report dict; length_m = edge length x the share of its points stitched (length_m_edges: whole edges)."""
    from scipy import sparse
    from scipy.sparse.linalg import splu
    res = arr.shape[0]
    flat = arr.reshape(-1, 4)
    assert np.shares_memory(flat, arr)
    L = flat[:, :3].astype(np.float64) @ LUM
    own = owner.ravel()
    C, V, P, lens, npts, per = [], [], [], [], [], {}
    for oi, ob in enumerate(objs):
        a0, a1, b0, b1, elen = seam_edges(ob, res)
        n = np.ceil(2 * np.maximum(np.linalg.norm(a1 - a0, axis=1), np.linalg.norm(b1 - b0, axis=1)))
        n = np.maximum(1, n).astype(np.int64)
        e = np.repeat(np.arange(len(n)), n + 1)
        t = (np.arange(len(e)) - np.repeat(np.cumsum(n + 1) - (n + 1), n + 1)) / n[e]
        ia, wa = _taps(a0[e] + (a1 - a0)[e] * t[:, None], res)
        ib, wb = _taps(b0[e] + (b1 - b0)[e] * t[:, None], res)
        ix, w = np.concatenate([ia, ib], 1), np.concatenate([wa, -wb], 1)
        on = np.abs(w) > 1e-6
        foreign = (on & (own[ix] >= 0) & (own[ix] != oi)).any(1)
        ok = ((wa * L[ia]).sum(1) >= lit) & ((wb * L[ib]).sum(1) >= lit) & ~(on & (L[ix] <= 1e-6)).any(1) & ~foreign
        C.append(ix[ok])
        V.append(np.where(on[ok], w[ok], 0.0))             # 0: a clamped / zero-weight tap, not a variable
        P.append(np.stack([np.full(int(ok.sum()), oi), e[ok]], 1))
        lens.append(elen)
        npts.append(n + 1)
        per[ob.name] = dict(seam_edges=int(len(n)), points_dark=int((~ok & ~foreign).sum()),
                            points_foreign=int(foreign.sum()))
    seam_len = round(float(sum(ll.sum() for ll in lens)), 2)
    C, V, P = np.concatenate(C), np.concatenate(V), np.concatenate(P)
    if not len(C):
        return dict(edges_stitched=0, length_m=0.0, seam_length_m=seam_len, texels_changed=0, objects=per)
    on = V != 0
    var, cv = np.unique(C[on], return_inverse=True)
    cj = np.zeros(C.shape, np.int64)
    cj[on] = cv
    po = np.broadcast_to(P[:, :1], C.shape)[on]
    vlo, vhi = np.full(len(var), len(objs)), np.full(len(var), -1)
    np.minimum.at(vlo, cv, po)
    np.maximum.at(vhi, cv, po)
    assert ((own[var] < 0) | (own[var] == vhi)).all()      # no texel of another object's island is a variable
    shared = vlo != vhi                                    # a free texel two objects' seams reach: islands < 2 texels
    keep = ~(shared[cj] & on).any(1)                       # apart (none at >= 4); left alone
    Dk = sparse.csr_matrix((V[on], (np.nonzero(on)[0], cv)), shape=(len(C), len(var)))[keep]
    M = (Dk.T @ Dk + lam * sparse.identity(len(var))).tocsr()
    x0 = flat[var].astype(np.float64)
    b = lam * x0
    lo, hi = floor * x0, np.full_like(x0, np.inf)
    hi[:, 3] = np.maximum(1.0, x0[:, 3])
    side = np.zeros(x0.shape, np.int8)                     # -1 held at lo, 1 held at hi
    x, nlu, lus, done = x0.copy(), 0, {}, [None] * 4
    for it in range(passes):
        for c in range(4):
            held = side[:, c] != 0
            key = held.tobytes()
            if key == done[c]:                             # held set as at its last solve: x[:, c] stands
                continue
            xc = np.where(side[:, c] < 0, lo[:, c], np.where(side[:, c] > 0, hi[:, c], x0[:, c]))
            fr = np.nonzero(~held)[0]
            if key not in lus:                             # R, G, B mostly hold the same texels
                lus[key] = splu((M[fr][:, fr] if held.any() else M).tocsc())
                nlu += 1
            xc[fr] += lus[key].solve((b[:, c] - M @ xc)[fr])
            x[:, c] = xc
            done[c] = key
        lus = {kk: v for kk, v in lus.items() if kk in done}
        # held at lo: g >= 0, at hi: g <= 0, else let go. Tolerances 1e-5 / 1e-6: under the half EXR's step (at
        # 1e-9 / 1e-10 the AO channel keeps trading a few texels at its two bounds, 20 passes, same objective)
        g = M @ x - b
        new = np.where(side != 0, side, np.where(x < lo - 1e-5, -1, np.where(x > hi + 1e-5, 1, 0))).astype(np.int8)
        new[((side < 0) & (g < -1e-6)) | ((side > 0) & (g > 1e-6))] = 0
        settled = bool((new == side).all())
        if settled or it == passes - 1:
            break
        side = new
    over = np.maximum(lo - x, x - hi).max(1)               # > 1e-5 only if not settled; clipped either way
    x = np.clip(x, lo, hi)
    Dp, Dn = Dk.maximum(0), -Dk.minimum(0)

    def jump(xx):
        la, lb = Dp @ (xx[:, :3] @ LUM), Dn @ (xx[:, :3] @ LUM)
        return np.abs(la - lb) / np.maximum(np.maximum(la, lb), lit)
    j0, j1 = (jump(x0), jump(x)) if keep.any() else (np.zeros(1), np.zeros(1))
    flat[var] = x.astype(flat.dtype)
    dL = np.abs((x - x0)[:, :3] @ LUM)
    ch = np.abs(x - x0).max(1) > 1e-4
    for oi, ob in enumerate(objs):
        mo = P[:, 0] == oi
        kept = np.bincount(P[keep & mo, 1], minlength=len(lens[oi]))
        st = kept > 0
        per[ob.name].update(stitched=int(st.sum()), length_m=round(float((lens[oi] * kept / npts[oi]).sum()), 3),
                            length_m_edges=round(float(lens[oi][st].sum()), 3), points=int((keep & mo).sum()),
                            points_dropped=int((~keep & mo).sum()))
    r4 = lambda v: round(float(v), 4)
    return dict(units='stored (RGB sRGB-encoded E, A = AO)', edges_stitched=sum(p['stitched'] for p in per.values()),
                length_m=round(sum(p['length_m'] for p in per.values()), 2),
                length_m_edges=round(sum(p['length_m_edges'] for p in per.values()), 2), seam_length_m=seam_len,
                points=int(keep.sum()), points_dropped=int((~keep).sum()), texels_shared=int(shared.sum()),
                texels_in_footprints=int(len(var)), passes=it + 1, settled=settled, lu=nlu,
                held_at_floor=[int((side[:, c] < 0).sum()) for c in range(4)], held_AO_1=int((side[:, 3] > 0).sum()),
                clipped=int((over > 1e-5).sum()), clip_max=float('%.2g' % max(0.0, over.max())),
                texels_changed=int(ch.sum()), dlum_max=r4(dL.max()),
                dlum_p99=r4(np.percentile(dL[ch], 99)) if ch.any() else 0.0, AO_max_before=r4(x0[:, 3].max()),
                AO_max_after=r4(x[:, 3].max()), jump_p50_before=r4(np.median(j0)), jump_p50_after=r4(np.median(j1)),
                jump_p99_before=r4(np.percentile(j0, 99)), jump_p99_after=r4(np.percentile(j1, 99)),
                lam=lam, lit=lit, floor=floor, objects={kk: v for kk, v in per.items() if v['stitched']})


class Sampler:
    """read the baked value where a ray from 0.4 m off the surface (along n) hits any of the baked objects: uv1 at the
    hit point (barycentric), averaged over a 3 x 3 texel patch."""

    def __init__(self, objs):
        self.verts, polys, self.owner = [], [], []
        for ob in objs:
            M = ob.matrix_world
            base = len(self.verts)
            self.verts += [M @ v.co for v in ob.data.vertices]
            for p in ob.data.polygons:
                polys.append([base + i for i in p.vertices])
                self.owner.append((ob, p.index, base))
        self.bvh = BVHTree.FromPolygons(self.verts, polys, all_triangles=False)

    def __call__(self, img_arr, p_unity, n_unity=(0, 1, 0)):
        from mathutils.interpolate import poly_3d_calc
        p, n = np.array(p_unity, float), np.array(n_unity, float)
        hit, nrm, idx, dist = self.bvh.ray_cast(Vector(U(p + 0.4 * n)), Vector(U(-n)), 2.0)
        if hit is None:
            return np.zeros(4), -1.0
        ob, pi, base = self.owner[idx]
        poly = ob.data.polygons[pi]
        uvl = ob.data.uv_layers['UVLightmap'].data
        w = poly_3d_calc([self.verts[base + i] for i in poly.vertices], hit)
        u = sum(wi * uvl[li].uv[0] for wi, li in zip(w, poly.loop_indices))
        v = sum(wi * uvl[li].uv[1] for wi, li in zip(w, poly.loop_indices))
        H, W = img_arr.shape[:2]
        i0, j0 = min(H - 2, max(1, int(v * H))), min(W - 2, max(1, int(u * W)))
        return img_arr[i0 - 1:i0 + 2, j0 - 1:j0 + 2].reshape(-1, 4).mean(0), float(dist) - 0.4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--blend', default='/tmp/bus/bus_final.blend')
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'Textures'))
    ap.add_argument('--res', type=int, default=1024)
    ap.add_argument('--samples', type=int, default=96)
    ap.add_argument('--target-E', type=float, default=0.6)   # 0.8 x 0.75: the seat TOPS then read the bible's #4A2229 under S2 (measured: 0.8 gave ~#57 2E 34, pinkish); see Bus/README
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.max_bounces = 4
    sc.world = sc.world or bpy.data.worlds.new('W')
    sc.world.use_nodes = True
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0.0      # only the tubes
    sc.world.light_settings.distance = 0.5
    for o in bpy.data.objects:
        if o.name.startswith('Glass_') or o.name.startswith('Cabin_Tubes'):
            o.hide_render = True          # glass: no blocking; diffusers: the area lights stand in for them
    add_tubes(10.0)
    # everything on the joint _CabinTubeLM pack (finish_bus.uv1_lightmap_multi): Cabin_Static, the D-36 seats and the
    # D-40 #1 slice pieces finish_bus exports on their own (Window_R1, Pole_R0)
    objs = [bpy.data.objects['Cabin_Static']] + sorted((o for o in bpy.data.objects if o.name.startswith(('Seat_', 'Window_', 'Pole_'))
                                                        and o.type == 'MESH'), key=lambda o: o.name)
    sample_at = Sampler(objs)
    img = bpy.data.images.new('LM', a.res, a.res, alpha=True, float_buffer=True)
    lm = bake(objs, img, 'DIFFUSE', a.samples)
    img2 = bpy.data.images.new('AO', a.res, a.res, alpha=True, float_buffer=True)
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    ao = bake(objs, img2, 'AO', max(16, a.samples // 3))
    # calibrate on the MID-CABIN cushions (bible 4.3 'seat cushion E ~ 0.8'): the hero seat sits at the end of the
    # right tube row, beside the skylight, and is the darkest seat — calibrating on it would make the cabin 2-3x too bright
    mids = [(float(np.mean(B.SEAT_R_X)), 1.02, bz + 0.30) for bz in B.RIGHT_ROWS[2:5]] + \
           [(xx, 1.02, bz + 0.30) for bz in B.LEFT_ROWS[1:3] for xx in (-1.10, -0.66)]
    vals = [float(np.mean(sample_at(lm, p)[0][:3])) for p in mids]
    k = a.target_E / max(1e-6, float(np.mean(vals)))
    cush = (float(np.mean(B.SEAT_R_X)), 1.04, B.HERO_BACK_Z + 0.30)
    d = sample_at(lm, cush)[1]
    out = np.zeros_like(lm)
    out[..., :3] = lm[..., :3] * k
    out[..., 3] = ao[..., 0]
    lab = island_labels([uv_tris(ob, a.res) for ob in objs], a.res)
    mask = lab > 0
    black0 = int((~np.any(out != 0, axis=-1) & mask).sum())
    nfill = fill_black(out, mask)
    print('[bake] black texels inside islands %d (%.2f %% of the island texels); filled %d (islands + 2-texel ring)'
          % (black0, 100.0 * black0 / max(1, int(mask.sum())), nfill))
    # the bracket first: its new texels are then stitched like the rest
    bracket = bracket_patch(out, objs, lab, k, a.samples)
    # the values the EXR stores (top of the file); the stitch evens those, as Unity interpolates them
    stored = encode(out)
    t0 = time.time()
    stitch = seam_stitch(stored, objs, lab - 1)
    stitch['seconds'] = round(time.time() - t0, 1)
    print('[bake] stitch', json.dumps({kk: v for kk, v in stitch.items() if kk != 'objects'}))
    lin = stored.copy()                                    # linear E again, for the report and the preview
    lin[..., :3] = srgb_decode(stored[..., :3])
    # report a few gray-card points (bible 4.3: ceiling next to the tubes bright, aisle floor 30-40 display)
    pts = dict(hero_cushion=(cush, (0, 1, 0)), aisle_floor=((0.10, B.FLOOR_Y, 0.0), (0, 1, 0)),
               ceiling_centre=((0.0, B.CEIL_Y, 0.0), (0, -1, 0)), lower_wall_R=((0.99 - 0.035, 0.9, 0.6), (-1, 0, 0)))
    rep = dict(watts_per_tube=10.0 * k, scale=k, calibrated_on='mean of 7 mid-cabin cushions = %.2f' % a.target_E,
               black_in_islands=black0, filled=nfill, island_texels=int(mask.sum()), bracket=bracket, stitch=stitch)
    for nm, (p, n) in pts.items():
        vv, dd = sample_at(lin, p, n)
        rep[nm] = dict(E=[round(float(x), 3) for x in vv[:3]], AO=round(float(vv[3]), 3), dist=round(dd, 3),
                       E_stored=[round(float(x), 3) for x in sample_at(stored, p, n)[0][:3]])
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, 'Cabin_TubeLM.exr')
    nbytes = save_exr(stored, path)
    Ll, Ls = lin[..., :3] @ LUM, stored[..., :3] @ LUM
    rep['exr'] = dict(file=os.path.basename(path), bytes=nbytes, format='RGBA half, ZIP (read back = float16 of these)',
                      rgb='sRGB-encoded E: srgb_encode(E), what Unity samples', a='AO, linear',
                      E_lum_max=round(float(Ll.max()), 3), stored_lum_max=round(float(Ls.max()), 3),
                      texels_E_over_1=int((Ll > 1).sum()), AO_max=round(float(stored[..., 3].max()), 4))
    from PIL import Image
    prev = np.clip((lin[::-1, :, :3] / (1 + lin[::-1, :, :3])) ** (1 / 2.2), 0, 1)
    Image.fromarray((prev * 255).astype(np.uint8)).save(os.path.join(a.out, '..', 'Docs~', 'Cabin_TubeLM_preview.png'))
    json.dump(rep, open(os.path.join(a.out, '..', 'Docs~', 'bake_report.json'), 'w'), indent=1)
    print('[bake]', json.dumps(rep))


if __name__ == '__main__':
    main()
