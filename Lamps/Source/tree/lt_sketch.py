# -*- coding: utf-8 -*-
"""Shape sketches for the reference board: each candidate species, (a) grey silhouette against a pale sky
(form, gaps), (b) at night 20 m away under a sodium lamp at the road side (bible §6·2 light #FF941D).
usage: python lt_sketch.py <outdir> [species ...]"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import bpy  # noqa
import numpy as np  # noqa

import lk_bpy as B  # noqa
import lk_mats as MT  # noqa
import lt_gen as T  # noqa
import lt_mesh as LM  # noqa

TEX = os.environ.get('LT_TEX', '/tmp/lt/tex')


def mesh(name, V, F, UV, COL, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in V], [], F); me.update()
    uv = me.uv_layers.new(name='UVMap')
    loops = [i for f in F for i in f]
    uv.data.foreach_set('uv', np.asarray(UV)[loops].ravel())
    me.materials.append(mat)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def bark_mat(wet):
    b = MT.NB('Bark')
    uv = b.N('ShaderNodeTexCoord').outputs['UV']
    A = b.tex(os.path.join(TEX, 'T_Tree_Bark_Albedo.png'), uv, 'sRGB')
    Nn = b.tex(os.path.join(TEX, 'T_Tree_Bark_Normal.png'), uv)
    bs = b.N('ShaderNodeBsdfPrincipled')
    k = 1 - 0.4 * wet                                     # bible §1.6: bark x0.6 when wet
    b.L(b.mixc(1.0, A.outputs['Color'], (k, k, k, 1), 'MULTIPLY'), bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 1 - (0.25 + (0.45 - 0.25) * wet)
    nm = b.N('ShaderNodeNormalMap'); b.L(Nn.outputs['Color'], nm.inputs['Color']); nm.inputs['Strength'].default_value = 1 - 0.4 * wet
    b.L(nm.outputs[0], bs.inputs['Normal'])
    b.L(bs.outputs[0], b.out.inputs[0])
    return b.m


def leaf_mat(wet, clip=0.5):
    """Alpha-tested leaf card (Unity: alpha-to-coverage, threshold 0.5): albedo, translucency from Mask.R,
    wet smoothness 0.55-0.65 (bible §1.6)."""
    b = MT.NB('Leaf')
    uv = b.N('ShaderNodeTexCoord').outputs['UV']
    A = b.tex(os.path.join(TEX, 'T_Tree_LeafCluster_Albedo.png'), uv, 'sRGB')
    M = b.tex(os.path.join(TEX, 'T_Tree_LeafCluster_Mask.png'), uv)
    Nn = b.tex(os.path.join(TEX, 'T_Tree_LeafCluster_Normal.png'), uv)
    thin, g, ao = b.sep(M.outputs['Color'])
    bs = b.N('ShaderNodeBsdfPrincipled')
    nm = b.N('ShaderNodeNormalMap'); b.L(Nn.outputs['Color'], nm.inputs['Color']); nm.inputs['Strength'].default_value = 1.0
    b.L(nm.outputs[0], bs.inputs['Normal'])
    alb = b.mixc(1.0, A.outputs['Color'], b.comb(ao, ao, ao), 'MULTIPLY')
    b.L(alb, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 1 - (0.35 + (0.60 - 0.35) * wet)
    # translucency (Lanbai/Tree _Translucency): thin leaf blades pass ~20 % of the light, yellow-green
    tl = b.N('ShaderNodeBsdfTranslucent'); tl.inputs['Color'].default_value = (*MT.hexlin('#8C9A4A'), 1)
    mx = b.N('ShaderNodeMixShader'); b.L(b.math('MULTIPLY', thin, 0.22), mx.inputs[0]); b.L(bs.outputs[0], mx.inputs[1]); b.L(tl.outputs[0], mx.inputs[2])
    cut = b.math('GREATER_THAN', A.outputs['Alpha'], clip)
    tr = b.N('ShaderNodeBsdfTransparent')
    fin = b.N('ShaderNodeMixShader'); b.L(cut, fin.inputs[0]); b.L(tr.outputs[0], fin.inputs[1]); b.L(mx.outputs[0], fin.inputs[2])
    b.L(fin.outputs[0], b.out.inputs[0])
    return b.m


def build(sp, wet):
    sk = T.grow(sp)
    V, F, UV, C = LM.branches(sk, sides=6, sides_by_r=lambda r: 10 if r > 0.08 else (6 if r > 0.025 else 4))
    mesh('branches', V, F, UV, C, bark_mat(wet))
    cards = T.leaf_cards(sk, sp)
    V2, F2, UV2, C2 = LM.leaves(cards)
    mesh('leaves', V2, F2, UV2, C2, leaf_mat(wet))
    return sk, len(F) * 2 + len(F2) * 2


def shot(sp, out, mode, W=600, H=800):
    sc = B.reset_scene(W, H, 48 if mode == 'night' else 24)
    sc.cycles.transparent_max_bounces = 48
    sk, tris = build(sp, 1.0 if mode == 'night' else 0.0)
    h = sk['N'][:, 2].max()
    w = sc.world; bg = w.node_tree.nodes['Background']
    if mode == 'clay':
        bg.inputs[0].default_value = (0.55, 0.60, 0.66, 1); bg.inputs[1].default_value = 1.0
        sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 2.0
        so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so); so.rotation_euler = (0.6, 0.3, 2.2)
        cam = B.camera('cam', (0, -28, h * 0.45), 0, 0, 34, W, H, sc)
    else:
        bg.inputs[0].default_value = (*MT.hexlin('#060405'), 1); bg.inputs[1].default_value = 1.0
        # the road lamp: 6.5 m high, 9 m in front-left of the tree (the tree on the far verge, lamp across the road)
        import lk_scene as S
        S.spot('sodium', (-7.0, -4.0, 6.6), 40.0, S.SODIUM, size_deg=178, blend=0.9, rot=(0, 0, 0), radius=0.06)
        S.point('up', (-7.0, -4.0, 6.6), 40.0 * 0.06, S.SODIUM, radius=0.1)
        gr = MT.ground_noise('G', '#2B3A22', '#1E2618', 0.45, scale=3, bump=0.6)
        S.plane('ground', -60, 60, -60, 120, 0.0, gr, 1, 1)
        cam = B.camera('cam', (-4.0, -22, 1.7), 10, 12, 50, W, H, sc)
    rgb = B.render_to(out + '.exr', sc)
    return rgb, tris, h


if __name__ == '__main__':
    outdir = sys.argv[1]
    names = sys.argv[2:] or list(T.SPECIES)
    os.makedirs(outdir, exist_ok=True)
    import json
    info = {}
    for nm in names:
        for mode in ('clay', 'night'):
            rgb, tris, h = shot(T.SPECIES[nm], os.path.join(outdir, '%s_%s' % (nm, mode)), mode)
            np.save(os.path.join(outdir, '%s_%s.npy' % (nm, mode)), rgb[..., :3].astype(np.float32))
            info[nm] = dict(tris=int(tris), height=float(h))
    json.dump(info, open(os.path.join(outdir, 'sketch_info.json'), 'w'), indent=1)
    print(info)
