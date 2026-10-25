# -*- coding: utf-8 -*-
"""标准台场景：载入整理好的车（finish_bus.py 存的 .blend：分组合并、uv1 图集），给外观贴上做旧图集（uv1），
给车厢贴上 _CabinTubeLM（uv1，RGB = 管灯照度 E，A = AO）当作自发光 × 反照率（= Unity 里 Lanbai/Cabin 的那一项）。
    --set blend=/tmp/bus/bus_final_ext.blend --set tex=Bus/Textures --set mode=clay|night [--set eye=x,y,z]
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'Source'))
sys.path.insert(0, HERE)
import build_bus  # noqa: E402


def load_blend(path):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    for o in dst.objects:
        if o is not None and o.type in ('MESH', 'EMPTY'):
            bpy.context.scene.collection.objects.link(o)
    return {o.name: o for o in dst.objects if o is not None}


def img_node(nt, path, non_color=False):
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(path)
    if non_color:
        n.image.colorspace_settings.name = 'Non-Color'
    uv = nt.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UVLightmap'
    nt.links.new(uv.outputs[0], n.inputs[0])
    return n


def exterior_material(ob, tex_dir, res):
    alb = os.path.join(tex_dir, 'Bus_Exterior_Albedo_%d.png' % res)
    msk = os.path.join(tex_dir, 'Bus_Exterior_Mask_%d.png' % res)
    if not os.path.exists(alb):
        raise FileNotFoundError(alb)
    m = bpy.data.materials.new('M_Bus_ExteriorAtlas')
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    a = img_node(nt, alb)
    k = img_node(nt, msk, True)
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(k.outputs['Color'], sep.inputs[0])
    inv = nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs[1], inv.inputs[1])
    nt.links.new(a.outputs['Color'], bs.inputs['Base Color'])
    nt.links.new(inv.outputs[0], bs.inputs['Roughness'])
    nt.links.new(sep.outputs[0], bs.inputs['Metallic'])
    me = ob.data
    me.materials.clear()
    me.materials.append(m)


def cabin_lightmapped(ob, lm_path, gain=1.0):
    """Cabin_Static: emission = albedo x _CabinTubeLM.rgb x gain (the Lanbai/Cabin tube term), added to the original
    Principled (which then only sees the small ambient: speculars / shape)."""
    lm = bpy.data.images.load(lm_path)
    lm.colorspace_settings.name = 'Non-Color'
    for i, m in enumerate(ob.data.materials):
        nm = m.copy()
        nt = nm.node_tree
        bs = nt.nodes.get('Principled BSDF')
        out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = lm
        uv = nt.nodes.new('ShaderNodeUVMap')
        uv.uv_map = 'UVLightmap'
        nt.links.new(uv.outputs[0], t.inputs[0])
        mul = nt.nodes.new('ShaderNodeMix')
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs[0].default_value = 1.0
        c = bs.inputs['Base Color'].default_value
        mul.inputs[6].default_value = (c[0] * gain, c[1] * gain, c[2] * gain, 1)
        nt.links.new(t.outputs['Color'], mul.inputs[7])
        em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(mul.outputs[2], em.inputs['Color'])
        add = nt.nodes.new('ShaderNodeAddShader')
        nt.links.new(bs.outputs[0], add.inputs[0])
        nt.links.new(em.outputs[0], add.inputs[1])
        nt.links.new(add.outputs[0], out.inputs[0])
        ob.data.materials[i] = nm


def build(ctx):
    S = ctx['lbh_scene']
    a = ctx['args']
    if 'eye' in a:
        ctx['cam']['eye'] = [float(v) for v in a['eye'].split(',')]
        ctx['eye'] = ctx['cam']['eye']
    objs = load_blend(a.get('blend', '/tmp/bus/bus_final_ext.blend'))
    for n, o in objs.items():
        if n.endswith('_LOD1'):
            o.hide_render = True
    tex = a.get('tex', 'Bus/Textures')
    tex = tex if os.path.isabs(tex) else os.path.join(ROOT, tex)
    if 'Bus_Exterior_LOD0' in objs:
        exterior_material(objs['Bus_Exterior_LOD0'], tex, int(a.get('res', 2048)))
    import scene_bus as SB
    mode = a.get('mode', 'clay')
    # the tube diffusers in the finished file are one object (Cabin_Tubes): give the area lights by the spec
    build_bus.MATS.clear()
    if mode == 'night':
        # act 1-2, tubes on (bible 4.8: _Udon_CabinLightmap = 1): the cabin lit by the baked tube lightmap; a dark night
        S.unity_ambient_flat(tuple(0.25 * c for c in build_bus.srgb2lin('#1B2230')))
        cabin_lightmapped(objs['Cabin_Static'], os.path.join(tex, 'Cabin_TubeLM.exr'), float(a.get('tubes', 1.0)))
        for n in ('Cabin_Tubes',):
            if n in objs:
                e = bpy.data.materials.new('TubeGlow')
                e.use_nodes = True
                nt = e.node_tree
                for nd in list(nt.nodes):
                    nt.nodes.remove(nd)
                em = nt.nodes.new('ShaderNodeEmission')
                em.inputs[0].default_value = (*build_bus.srgb2lin('#E7FEFF'), 1)
                em.inputs[1].default_value = 2.04 * float(a.get('tubes', 1.0))
                o_ = nt.nodes.new('ShaderNodeOutputMaterial')
                nt.links.new(em.outputs[0], o_.inputs[0])
                objs[n].data.materials.clear()
                objs[n].data.materials.append(e)
    if mode == 'clay':
        S.unity_ambient_flat((0.30, 0.31, 0.33))
        S.unity_directional('Sun', 1.4, '#FFF3E2', (0.55, 0.45, 0.70))
        g = bpy.data.materials.new('Ground')
        g.use_nodes = True
        g.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.08, 0.08, 0.085, 1)
        S.mesh_object('Ground', [(-80, 0, -120), (80, 0, -120), (80, 0, 120), (-80, 0, 120)], [(0, 1, 2, 3)], g)
    return dict(what='finished bus, %s' % mode)
