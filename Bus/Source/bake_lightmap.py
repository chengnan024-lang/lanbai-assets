# -*- coding: utf-8 -*-
"""烘 _CabinTubeLM（圣经 §1.6 / §4.3：只有车、只开 10 根灯管）到 Cabin_Static、各个座位（D-36：Seat_*）和切片的两件
（D-40 #1：Window_R1、Pole_R0，finish_bus.SEPARATE）的 uv1（同一张图）。
RGB = 管灯照度 E（Unity 单位，线性；Lanbai/Cabin 里 albedo × LM.rgb × _Udon_CabinLightmap），A = AO（0.5 m）。
校准：主座位座垫中心的 E = 0.8（圣经 §4.3，S2 下灰卡 #585F64）。光的传输对瓦数是线性的，所以烘一次、按座垫读数整体缩放。

    ~/bpy/bin/python Bus/Source/bake_lightmap.py --blend /tmp/bus/bus_final.blend --out Bus/Textures --res 1024 --samples 96
输出：Cabin_TubeLM.exr（RGBA half）、Cabin_TubeLM_preview.png（看的）、bake_report.json
Cycles 的漫反射烘焙（直接 + 间接、不乘颜色）= 白色朗伯面的出射亮度 = E_cycles / π；灯按标准台的约定是 π × E_unity，
所以烘出来的数就是 E_unity。
"""
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bus_spec as B  # noqa: E402


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


def island_mask(objs, res):
    """the texels the objects' 'UVLightmap' triangles cover (row 0 = v 0, like img.pixels)."""
    from PIL import Image, ImageDraw
    im = Image.new('L', (res, res), 0)
    d = ImageDraw.Draw(im)
    for ob in objs:
        me = ob.data
        me.calc_loop_triangles()
        uv = np.empty(2 * len(me.loops), np.float32)
        me.uv_layers['UVLightmap'].data.foreach_get('uv', uv)
        uv = uv.reshape(-1, 2) * res - 0.5                    # texel centres at (i + 0.5) / res
        tri = np.empty(3 * len(me.loop_triangles), np.int64)
        me.loop_triangles.foreach_get('loops', tri)
        for t in uv[tri].reshape(-1, 3, 2):
            d.polygon([tuple(p) for p in t], fill=255, outline=255)
    return np.asarray(im) > 0


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
    mask = island_mask(objs, a.res)
    black0 = int((~np.any(out != 0, axis=-1) & mask).sum())
    nfill = fill_black(out, mask)
    print('[bake] black texels inside islands %d (%.2f %% of the island texels); filled %d (islands + 2-texel ring)'
          % (black0, 100.0 * black0 / max(1, int(mask.sum())), nfill))
    # report a few gray-card points (bible 4.3: ceiling next to the tubes bright, aisle floor 30-40 display)
    pts = dict(hero_cushion=(cush, (0, 1, 0)), aisle_floor=((0.10, B.FLOOR_Y, 0.0), (0, 1, 0)),
               ceiling_centre=((0.0, B.CEIL_Y, 0.0), (0, -1, 0)), lower_wall_R=((0.99 - 0.035, 0.9, 0.6), (-1, 0, 0)))
    rep = dict(watts_per_tube=10.0 * k, scale=k, calibrated_on='mean of 7 mid-cabin cushions = %.2f' % a.target_E,
               black_in_islands=black0, filled=nfill, island_texels=int(mask.sum()))
    for nm, (p, n) in pts.items():
        vv, dd = sample_at(out, p, n)
        rep[nm] = dict(E=[round(float(x), 3) for x in vv[:3]], AO=round(float(vv[3]), 3), dist=round(dd, 3))
    os.makedirs(a.out, exist_ok=True)
    res = bpy.data.images.new('LMout', a.res, a.res, alpha=True, float_buffer=True)
    res.pixels[:] = out.ravel().tolist()
    res.filepath_raw = os.path.join(a.out, 'Cabin_TubeLM.exr')
    res.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '16'
    res.save()
    from PIL import Image
    prev = np.clip((out[::-1, :, :3] / (1 + out[::-1, :, :3])) ** (1 / 2.2), 0, 1)
    Image.fromarray((prev * 255).astype(np.uint8)).save(os.path.join(a.out, '..', 'Docs~', 'Cabin_TubeLM_preview.png'))
    json.dump(rep, open(os.path.join(a.out, '..', 'Docs~', 'bake_report.json'), 'w'), indent=1)
    print('[bake]', json.dumps(rep))


if __name__ == '__main__':
    main()
