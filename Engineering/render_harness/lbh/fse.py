# -*- coding: utf-8 -*-
"""Transparent overdraw in full-screen equivalents (FSE), measured on the same camera as the reference frame.

FSE of a transparent object = the fraction of the frame where its triangles are rasterised AND pass the depth test
against the opaque scene (what the GPU pays for an alpha-blended draw: alpha = 0 texels still cost a fragment).
So the object is rendered as a solid white emitter, every other object as a holdout (an opaque occluder that writes
nothing), and the covered pixels are counted. One render per object (1 sample, small resolution): the per-pixel sum
gives the layer count (bible §1.9: any pixel <= 8 layers).

Which objects are transparent: a custom property  lb_fse = "<layer name>"  on the object (set it in the scene script),
or --fse-pattern regexes on object names (layer = the pattern). The cabin glass is NOT here (the harness shell has none
unless --glass; the ledger counts it as 0.7 every act).
Back faces: Cull Off cards cover the same pixels from either side; for Cull Back objects whose back faces would be culled,
set lb_fse_cull = "back" and the object's back faces are made invisible (the backface-culling flag in Cycles)."""
import json
import os
import re

import bpy
import numpy as np


def _white():
    m = bpy.data.materials.get('__lbh_fse_white')
    if m is None:
        m = bpy.data.materials.new('__lbh_fse_white')
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        e = nt.nodes.new('ShaderNodeEmission')
        e.inputs[0].default_value = (1, 1, 1, 1)
        e.inputs[1].default_value = 1.0
        o = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(e.outputs[0], o.inputs[0])
    return m


def tagged(patterns=()):
    out = {}
    for ob in bpy.context.scene.objects:
        if ob.type not in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            continue
        lay = ob.get('lb_fse')
        if lay is None:
            for p in patterns:
                if re.search(p, ob.name):
                    lay = p
                    break
        if lay is not None:
            out[ob.name] = str(lay)
    return out


def measure(out_dir, res=(480, 270), patterns=()):
    """renders the coverage of every tagged object; returns the report dict (also written to out_dir/fse.json)."""
    sc = bpy.context.scene
    objs = tagged(patterns)
    if not objs:
        return dict(note='no transparent objects tagged (lb_fse / --fse-pattern)', total=0.0)
    saved = dict(res=(sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage), samples=sc.cycles.samples,
                 denoise=sc.cycles.use_denoising, film=sc.render.film_transparent, path=sc.render.filepath,
                 fmt=sc.render.image_settings.file_format, world=sc.world)
    state = {ob.name: (ob.hide_render, ob.is_holdout, [s.material for s in ob.material_slots],
                       getattr(ob, 'visible_camera', True)) for ob in sc.objects}
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = res[0], res[1], 100
    sc.cycles.samples = 1
    sc.cycles.use_denoising = False
    sc.cycles.use_adaptive_sampling = False
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'OPEN_EXR'
    w = bpy.data.worlds.new('__lbh_fse_black')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.0
    sc.world = w
    white = _white()
    per_obj, layers = {}, {}
    acc = np.zeros((res[1], res[0]), np.float32)
    try:
        for name, lay in sorted(objs.items()):
            for ob in sc.objects:
                if ob.type == 'LIGHT':
                    continue
                if ob.name == name:
                    ob.hide_render = False
                    ob.is_holdout = False
                    for s in ob.material_slots:
                        s.material = white
                    if not ob.material_slots:
                        ob.data.materials.append(white)
                    if ob.get('lb_fse_cull') == 'back':
                        white.use_backface_culling = True
                elif ob.name in objs:
                    ob.hide_render = True                    # other transparents do not occlude (no z-write)
                else:
                    ob.is_holdout = True                     # opaque occluders
            p = os.path.join(out_dir, '__fse_%s.exr' % re.sub(r'\W', '_', name))
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(p, check_existing=False)
            px = np.empty(res[0] * res[1] * 4, np.float32)
            img.pixels.foreach_get(px)
            bpy.data.images.remove(img)
            os.remove(p)
            cov = (px.reshape(res[1], res[0], 4)[::-1, :, 0] > 0.5).astype(np.float32)
            acc += cov
            f = float(cov.mean())
            per_obj[name] = round(f, 4)
            layers[lay] = round(layers.get(lay, 0.0) + f, 4)
            white.use_backface_culling = False
            for ob in sc.objects:                            # restore before the next object
                hr, ho, mats, vc = state[ob.name]
                ob.hide_render, ob.is_holdout = hr, ho
                for s, m in zip(ob.material_slots, mats):
                    s.material = m
    finally:
        for ob in sc.objects:
            hr, ho, mats, vc = state[ob.name]
            ob.hide_render, ob.is_holdout = hr, ho
            for s, m in zip(ob.material_slots, mats):
                s.material = m
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = saved['res']
        sc.cycles.samples = saved['samples']
        sc.cycles.use_denoising = saved['denoise']
        sc.render.film_transparent = saved['film']
        sc.render.filepath = saved['path']
        sc.render.image_settings.file_format = saved['fmt']
        sc.world = saved['world']
        bpy.data.worlds.remove(w)
    rep = dict(total=round(float(acc.mean()), 3), layers=layers, objects=per_obj,
               max_layers_per_pixel=int(acc.max()), pixels_over_8_layers_pct=round(float((acc > 8).mean() * 100), 3),
               res=list(res), method='coverage of each transparent object, depth-tested against the opaque scene (holdouts), 1 spp')
    json.dump(rep, open(os.path.join(out_dir, 'fse.json'), 'w'), indent=1)
    try:
        from PIL import Image
        v = np.clip(acc / 8.0, 0, 1)
        Image.fromarray((np.stack([v, v ** 0.5 * 0.6, 1 - v], -1) * 255).astype(np.uint8)).save(os.path.join(out_dir, 'fse_layers.png'))
    except Exception:
        pass
    return rep
