# -*- coding: utf-8 -*-
"""Build the sample trees (D-44 #6): Tree_A1..A3 (main), Tree_B1 (paddy-side accent).
For each: LOD0 (branches r >= 1.2 cm + 1.25 m leaf-cluster cards), LOD1 (limbs r >= 5 cm + 2.5 m clump cards),
LOD2 (two crossed impostor cards, the tree baked from LOD0). Writes:
    <out>/Models/<name>.fbx                 root empty <name> with children <name>_LOD0/1/2 (two materials: bark, leaves)
    <out>/Textures/T_Tree_Impostor_<name>.png   1024x512: front | side, RGB albedo x AO (sRGB), A coverage
    <out>/Source~/Trees.blend               everything, for editing
    <out>/Tree_Info.json                    heights, triangle counts, bounds
Vertex colour 'Col' (linear, Unity: mesh colors): R = flexibility 0 (trunk) .. 1 (twig / leaf), G = phase 0..1,
B = 1 on leaf cards. usage: python lt_build.py <out> [names...]"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import bpy  # noqa
import numpy as np  # noqa

import lk_bpy as B  # noqa
import lt_gen as T  # noqa
import lt_mesh as LM  # noqa
import lt_sketch as SK  # noqa


def export_fbx(path, objects):
    """Same settings as Gate/Source/export_unity.py (Blender Z-up m -> Unity Y-up m, rotation 0 / scale 1)."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    kw = dict(filepath=path, use_selection=True, object_types={'EMPTY', 'MESH'}, apply_unit_scale=True,
              apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
              use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True, add_leaf_bones=False, bake_anim=False,
              path_mode='STRIP', embed_textures=False)
    try:
        bpy.ops.export_scene.fbx(colors_type='LINEAR', **kw)
    except TypeError:
        bpy.ops.export_scene.fbx(**kw)


def make_object(name, parts, mats):
    """parts: list of (V, F, UV, COL, mat_index)."""
    V, F, UV, COL, MI = [], [], [], [], []
    for (v, f, uv, col, mi) in parts:
        o = len(V)
        V += [tuple(p) for p in v]
        F += [tuple(i + o for i in ff) for ff in f]
        UV += [tuple(t) for t in uv]
        COL += [tuple(c) for c in col]
        MI += [mi] * len(f)
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], F); me.update()
    uvl = me.uv_layers.new(name='UVMap')
    loops = [i for f in F for i in f]
    uvl.data.foreach_set('uv', np.asarray(UV, np.float32)[loops].ravel())
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    rgba = np.concatenate([np.asarray(COL, np.float32), np.ones((len(COL), 1), np.float32)], 1)
    ca.data.foreach_set('color', rgba.ravel())
    me.polygons.foreach_set('material_index', MI)
    for m in mats:
        me.materials.append(m)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def sides_lod0(r):
    return 10 if r > 0.15 else (6 if r > 0.06 else (4 if r > 0.03 else 3))


def sides_lod1(r):
    return 8 if r > 0.15 else (5 if r > 0.08 else 3)


def build_variant(name, sp, mats, wet=1.0):
    sk = T.grow(sp)
    objs = {}
    tris = {}
    for lod, (min_r, sides) in enumerate(((0.018, sides_lod0), (0.05, sides_lod1))):
        V, F, UV, COL = LM.branches(sk, sides_by_r=sides, min_r=min_r)
        cards = T.clump_cards(sk, sp, lod)
        V2, F2, UV2, COL2 = LM.leaves(cards)
        ob = make_object('%s_LOD%d' % (name, lod), [(V, F, UV, COL, 0), (V2, F2, UV2, COL2, 1)], mats)
        objs[lod] = ob
        tris[lod] = 2 * (len(F) + len(F2))
    return sk, objs, tris


def impostor(name, ob, outdir, size=512):
    """Bake LOD0 into two orthographic views (front along +Y, side along +X) under a uniform white sky
    (albedo x AO-ish), alpha = coverage. Returns (path, half-width, height)."""
    sc = bpy.context.scene
    keep = (sc.render.resolution_x, sc.render.resolution_y, sc.render.film_transparent, sc.cycles.samples)
    bb = np.array([ob.matrix_world @ __import__('mathutils').Vector(c) for c in ob.bound_box])
    hw = max(np.abs(bb[:, 0]).max(), np.abs(bb[:, 1]).max()) * 1.04
    h = bb[:, 2].max() * 1.02
    sc.render.resolution_x = size; sc.render.resolution_y = int(size * h / (2 * hw)) if h > 2 * hw else size
    sc.render.film_transparent = True
    sc.cycles.samples = 32
    w = sc.world; bg = w.node_tree.nodes['Background']; old = tuple(bg.inputs[0].default_value), bg.inputs[1].default_value
    bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 1.0
    hide = [o for o in sc.objects if o is not ob and o.type in ('MESH', 'LIGHT', 'CURVE')]
    # bake ALBEDO x AO only: no specular sheen of the white bake sky, no translucency (they made the LOD2 cards pale
    # in the local Unity check 10-25: the Unity shader lights the impostor again)
    saved = []
    for slot in ob.material_slots:
        m = slot.material
        if m is None or m.node_tree is None:
            continue
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                saved.append((n, 'Specular IOR Level', n.inputs['Specular IOR Level'].default_value))
                n.inputs['Specular IOR Level'].default_value = 0.0
            if n.type == 'BSDF_TRANSLUCENT':
                saved.append((n, 'Color', tuple(n.inputs['Color'].default_value)))
                n.inputs['Color'].default_value = (0, 0, 0, 1)
    for o in hide:
        o.hide_render = True
    views = []
    for k, (loc, rot) in enumerate((((0, -60, h / 2), (math.radians(90), 0, 0)), ((60, 0, h / 2), (math.radians(90), 0, math.radians(90))))):
        cam = bpy.data.cameras.new('imp'); cam.type = 'ORTHO'
        cam.ortho_scale = max(2 * hw, h)
        co = bpy.data.objects.new('imp', cam); sc.collection.objects.link(co)
        co.location = loc; co.rotation_euler = rot
        sc.camera = co
        sc.render.resolution_x = size; sc.render.resolution_y = size
        p = os.path.join('/tmp', 'imp_%s_%d.exr' % (name, k))
        px = B.render_to(p, sc)
        views.append(px)
        bpy.data.objects.remove(co)
    for o in hide:
        o.hide_render = False
    for n, k, v in saved:
        n.inputs[k].default_value = v
    bg.inputs[0].default_value = old[0]; bg.inputs[1].default_value = old[1]
    sc.render.resolution_x, sc.render.resolution_y, sc.render.film_transparent, sc.cycles.samples = keep
    img = np.concatenate(views, 1)                      # (size, 2 size, 4), top row first
    a = np.clip(img[..., 3], 0, 1)
    rgb = img[..., :3] / np.maximum(a[..., None], 1e-4)
    # bleed colour into the empty area for clean mips
    from scipy import ndimage
    idx = ndimage.distance_transform_edt(a < 0.5, return_distances=False, return_indices=True)
    rgb = rgb[idx[0], idx[1]]
    srgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.clip(rgb, 0, 1) ** (1 / 2.4) - 0.055)
    from PIL import Image
    path = os.path.join(outdir, 'T_Tree_Impostor_%s.png' % name)
    Image.fromarray(np.round(np.clip(np.concatenate([srgb, a[..., None]], -1), 0, 1) * 255).astype(np.uint8), 'RGBA').save(path, optimize=True)
    s = max(2 * hw, h)
    return path, s / 2, s, h / 2 - s / 2


def impostor_mesh(name, half, s, mat):
    """Two crossed quads (front: XZ plane, side: YZ plane), each with its half of the atlas; 4 tris + backfaces via
    Cull Off in the shader. Bottom at z = 0 (ortho camera centred at h/2 with ortho_scale s)."""
    z0 = s / 2 * 0 + 0.0
    zc = s / 2 * 1.0
    # the ortho view was centred at h/2 with scale s: the image spans z in [h/2 - s/2, h/2 + s/2]; we pass h/2 = zc_img
    V, F, UV, COL = [], [], [], []
    for k, (ax) in enumerate(((1, 0, 0), (0, 1, 0))):
        ax = np.array(ax, float)
        base = len(V)
        for (sx, sz) in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
            V.append(tuple(ax * sx * half + np.array([0, 0, impostor_mesh.zlo + sz * s])))
            u0 = 0.5 * k
            UV.append((u0 + 0.5 * (sx + 1) / 2, sz))
            COL.append((0.6, 0.5, 0.0))
        F.append((base, base + 1, base + 2, base + 3))
    return V, F, UV, COL


def main(out, names):
    os.makedirs(os.path.join(out, 'Models'), exist_ok=True)
    os.makedirs(os.path.join(out, 'Textures'), exist_ok=True)
    os.makedirs(os.path.join(out, 'Source~'), exist_ok=True)
    sc = B.reset_scene(512, 512, 32)
    mats = [SK.bark_mat(1.0), SK.leaf_mat(1.0)]
    info = {}
    for nm in names:
        sp = T.VARIANTS[nm]()
        sk, objs, tris = build_variant(nm, sp, mats)
        path, half, s, zlo = impostor(nm, objs[0], os.path.join(out, 'Textures'))
        h = float(sk['N'][:, 2].max())
        impostor_mesh.zlo = zlo
        V, F, UV, COL = impostor_mesh(nm, half, s, None)
        im_mat = impostor_material(nm, path)
        ob2 = make_object('%s_LOD2' % nm, [(V, F, UV, COL, 0)], [im_mat])
        root = bpy.data.objects.new(nm, None); sc.collection.objects.link(root)
        for o in (objs[0], objs[1], ob2):
            o.parent = root
        tris[2] = 4
        export_fbx(os.path.join(out, 'Models', nm + '.fbx'), [root, objs[0], objs[1], ob2])
        # spread them out in the .blend only (the FBX root stays at the origin)
        root.location = (list(T.VARIANTS).index(nm) * 16.0, 0, 0)
        bb = np.array(sk['N'])
        info[nm] = dict(height_m=round(h, 2), crown_width_m=[round(float(np.ptp(bb[:, 0])), 2), round(float(np.ptp(bb[:, 1])), 2)],
                        trunk_radius_m=round(float(sk['r'][0]), 3), tris_lod0=tris[0], tris_lod1=tris[1], tris_lod2=tris[2],
                        impostor=os.path.basename(path), impostor_half_width_m=round(half, 2), impostor_height_m=round(s, 2),
                        seed=sp.seed, scale=sp.scale)
        print(nm, info[nm], flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, 'Source~', 'Trees.blend'))
    json.dump(info, open(os.path.join(out, 'Tree_Info.json'), 'w'), indent=1)


def impostor_material(name, path):
    import lk_mats as MT
    b = MT.NB('M_Tree_Impostor_' + name)
    uv = b.N('ShaderNodeTexCoord').outputs['UV']
    A = b.tex(path, uv, 'sRGB', ext='EXTEND')
    bs = b.N('ShaderNodeBsdfPrincipled'); b.L(A.outputs['Color'], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = 0.6
    tr = b.N('ShaderNodeBsdfTransparent')
    mx = b.N('ShaderNodeMixShader'); b.L(b.math('GREATER_THAN', A.outputs['Alpha'], 0.5), mx.inputs[0])
    b.L(tr.outputs[0], mx.inputs[1]); b.L(bs.outputs[0], mx.inputs[2]); b.L(mx.outputs[0], b.out.inputs[0])
    return b.m


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:] or list(T.VARIANTS))
