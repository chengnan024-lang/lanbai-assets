# -*- coding: utf-8 -*-
"""D-36 #3：把零件的程序材质烘成 Unity 用的三张贴图（零件自己的展开，uv0）。

    bake_part(objs, name, res=2048, px_per_m=None) -> dict(files, metres_per_uv, tris)

  1. 把零件的物体拷一份并成一个网格，按统一的纹素密度展开（smart project + 打包；1 个 uv 单位 = metres_per_uv 米），
     写成 uv0（Unity 只按 uv0 算切线，法线图必须在 uv0 上）。
  2. 用 Cycles 烘：底色（DIFFUSE color）、法线（切线空间，含材质里的 bump / 皮纹）、粗糙度、AO、金属（发射法）。
  3. 合成：<name>_Albedo（sRGB）、<name>_Normal（OpenGL，Unity 当 Normal map 导入）、
     <name>_Mask（R 金属、G 光滑、B 接缝开裂的候选形状（座椅：每座用顶点色 alpha 挑开哪几处，圣经 §4.2）、A AO）——和外观图集的遮罩同一个约定。
贴图写进 Bus/Textures/Parts/。烘的时候不需要任何灯（这些通道都和光无关）。
"""
import math
import os

import bmesh
import bpy
import numpy as np

import build_bus as BB

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', '..', 'Textures', 'Parts'))


def _join_copy(objs, name):
    dup = []
    for o in objs:
        if o.type != 'MESH':
            continue
        c = o.copy()
        c.data = o.data.copy()
        bpy.context.scene.collection.objects.link(c)
        dup.append(c)
    bpy.ops.object.select_all(action='DESELECT')
    for c in dup:
        c.select_set(True)
    bpy.context.view_layer.objects.active = dup[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return ob


def unwrap(ob, margin_px=8, res=2048, keep_layers=False):
    """smart project (islands split at 55 deg), then pack at one uniform density, into 'UVMap' (made active);
    returns metres per uv unit. keep_layers: leave the other uv layers (UVMetric, UVLightmap) alone."""
    me = ob.data
    if not keep_layers:
        for l in list(me.uv_layers):
            me.uv_layers.remove(l)
    if 'UVMap' not in me.uv_layers:
        me.uv_layers.new(name='UVMap')
    me.uv_layers.active = me.uv_layers['UVMap']
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.0, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=margin_px / res, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    # metres per uv unit from total 3D area vs total uv area (uniform after average_islands_scale)
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv['UVMap']
    a3 = sum(f.calc_area() for f in bm.faces)
    a2 = 0.0
    for f in bm.faces:
        uv = [l[uvl].uv for l in f.loops]
        for i in range(1, len(uv) - 1):
            a2 += abs((uv[i].x - uv[0].x) * (uv[i + 1].y - uv[0].y) - (uv[i + 1].x - uv[0].x) * (uv[i].y - uv[0].y)) / 2
    bm.free()
    return math.sqrt(a3 / max(a2, 1e-12))


def _image(name, res, non_color=True, float_=True):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, res, res, alpha=False, float_buffer=float_)
    im.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    return im


def _bake(ob, im, kind, src=None, **kw):
    """bake onto 'ob' (its active uv); with 'src', from that high-detail object (selected-to-active)."""
    sc = bpy.context.scene
    for m in ob.data.materials:
        nt = m.node_tree
        tn = nt.nodes.get('__bake__') or nt.nodes.new('ShaderNodeTexImage')
        tn.name = '__bake__'
        tn.image = im
        nt.nodes.active = tn
    bpy.ops.object.select_all(action='DESELECT')
    if src is not None:
        src.select_set(True)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bk = sc.render.bake
    bk.margin = 16
    bk.use_clear = True
    bk.use_selected_to_active = src is not None
    if src is not None:
        bk.cage_extrusion = 0.008
        bk.max_ray_distance = 0.03
    if kind == 'DIFFUSE':
        bk.use_pass_direct = False
        bk.use_pass_indirect = False
        bk.use_pass_color = True
    bpy.ops.object.bake(type=kind, **kw)
    a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)
    return a


def _emit_socket(ob, socket='Metallic', colour=False):
    """temporarily route each material's Principled input (linked or constant) into an Emission shader, for an
    EMIT bake of exactly that value (the DIFFUSE colour pass is black on metals, so albedo goes this way too)."""
    saved = []
    for m in ob.data.materials:
        nt = m.node_tree
        out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
        bs = nt.nodes.get('Principled BSDF')
        old = out.inputs[0].links[0].from_socket if out.inputs[0].links else None
        em = nt.nodes.new('ShaderNodeEmission')
        mv = bs.inputs[socket]
        if mv.links:
            nt.links.new(mv.links[0].from_socket, em.inputs['Color'])
        elif colour:
            em.inputs['Color'].default_value = tuple(mv.default_value)
        else:
            em.inputs['Color'].default_value = (mv.default_value,) * 3 + (1.0,)
        nt.links.new(em.outputs[0], out.inputs[0])
        saved.append((nt, out, old, em))
    return saved


def _emit_node(ob, node_name):
    """like _emit_socket, but emit the first output of the node called node_name (black where a material has none)."""
    saved = []
    for m in ob.data.materials:
        nt = m.node_tree
        out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
        old = out.inputs[0].links[0].from_socket if out.inputs[0].links else None
        em = nt.nodes.new('ShaderNodeEmission')
        src = nt.nodes.get(node_name)
        if src is not None:
            nt.links.new(src.outputs[0], em.inputs['Color'])
        else:
            em.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
        nt.links.new(em.outputs[0], out.inputs[0])
        saved.append((nt, out, old, em))
    return saved


def _emit_ao(ob, dist=0.06, samples=16):
    """emit an Ambient Occlusion node's AO (only_local: the object's own geometry) from every material."""
    saved = []
    for m in ob.data.materials:
        nt = m.node_tree
        out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
        old = out.inputs[0].links[0].from_socket if out.inputs[0].links else None
        ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
        ao.only_local = True
        ao.samples = samples
        ao.inputs['Distance'].default_value = dist
        em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(ao.outputs['AO'], em.inputs['Color'])
        nt.links.new(em.outputs[0], out.inputs[0])
        saved.append((nt, out, old, em))
        saved.append((nt, out, None, ao))
    return saved


def _set_value_nodes(ob, node_name, v):
    for m in ob.data.materials:
        n = m.node_tree.nodes.get(node_name)
        if n is not None:
            n.outputs[0].default_value = v


def _emit_metal(ob):
    return _emit_socket(ob, 'Metallic')


def _restore(saved):
    for nt, out, old, em in saved:
        if old is not None:
            nt.links.new(old, out.inputs[0])
        nt.nodes.remove(em)


def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def bake_part(objs, name, res=2048, samples=32, out_dir=OUT, high=None):
    """objs: the game (low) mesh parts; high: the same part built at 'high' quality (bake source), or None to bake
    each surface's own material (bump included)."""
    from PIL import Image
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    ob = _join_copy(objs, 'Part_' + name)
    hs = _join_copy(high, 'PartHigh_' + name) if high else None
    mpu = unwrap(ob, res=res)
    if hs is not None and not ob.data.materials:
        ob.data.materials.append(BB.mat('Vinyl'))
    sc.cycles.samples = 1
    saved = _emit_socket(hs if hs is not None else ob, 'Base Color', colour=True)
    alb = _bake(ob, _image(name + '_alb', res, non_color=False), 'EMIT', src=hs)
    _restore(saved)
    sc.cycles.samples = samples
    nrm = _bake(ob, _image(name + '_nrm', res), 'NORMAL', src=hs, normal_space='TANGENT')
    rgh = _bake(ob, _image(name + '_rgh', res), 'ROUGHNESS', src=hs)
    src = hs if hs is not None else ob
    sc.cycles.samples = 1
    saved = _emit_node(src, 'crack_mask')
    crk = _bake(ob, _image(name + '_crk', res), 'EMIT', src=hs)
    _restore(saved)
    sc.cycles.samples = max(samples, 32)
    saved = _emit_ao(src, 0.06)                 # the part's own AO only (see bake_onto)
    ao = _bake(ob, _image(name + '_ao', res), 'EMIT', src=hs)
    _restore(saved)
    sc.cycles.samples = 1
    saved = _emit_metal(hs if hs is not None else ob)
    met = _bake(ob, _image(name + '_met', res), 'EMIT', src=hs)
    _restore(saved)
    if hs is not None:
        bpy.data.objects.remove(hs, do_unlink=True)
    os.makedirs(out_dir, exist_ok=True)
    flip = lambda a: a[::-1]
    files = {}
    p = os.path.join(out_dir, 'Part_%s_Albedo_%d.png' % (name, res))
    Image.fromarray((lin2srgb(flip(alb)[..., :3]) * 255 + 0.5).astype(np.uint8)).save(p)
    files['albedo'] = p
    p = os.path.join(out_dir, 'Part_%s_Normal_%d.png' % (name, res))
    Image.fromarray((np.clip(flip(nrm)[..., :3], 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)
    files['normal'] = p
    mask = np.stack([flip(met)[..., 0], 1.0 - flip(rgh)[..., 0], flip(crk)[..., 0], flip(ao)[..., 0]], -1)
    p = os.path.join(out_dir, 'Part_%s_Mask_%d.png' % (name, res))
    Image.fromarray((np.clip(mask, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(p)
    files['mask'] = p
    tris = sum(len(f.vertices) - 2 for f in ob.data.polygons)
    return dict(object=ob, files=files, metres_per_uv=mpu, tris=tris, texel_px_per_m=res / mpu)


def bake_onto(target, high, name, res=2048, samples=16, out_dir=OUT):
    """bake the high-quality part 'high' (detail materials applied) onto an existing, already unwrapped game object
    'target' (its 'UVMap'); writes the three maps, returns the file paths."""
    from PIL import Image
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    hs = _join_copy(high, 'PartHigh_' + name)
    for o in high:
        bpy.data.objects.remove(o, do_unlink=True)
    me = target.data
    me.uv_layers.active = me.uv_layers['UVMap']
    sc.cycles.samples = 1
    _set_value_nodes(hs, 'crack_show', 0.0)    # seam cracks: colour + gloss per seat in Unity (mask.b x vertex alpha)
    saved = _emit_socket(hs, 'Base Color', colour=True)
    alb = _bake(target, _image(name + '_alb', res, non_color=False), 'EMIT', src=hs)
    _restore(saved)
    sc.cycles.samples = samples
    nrm = _bake(target, _image(name + '_nrm', res), 'NORMAL', src=hs, normal_space='TANGENT')
    rgh = _bake(target, _image(name + '_rgh', res), 'ROUGHNESS', src=hs)
    _set_value_nodes(hs, 'crack_show', 1.0)
    sc.cycles.samples = 1
    saved = _emit_node(hs, 'crack_mask')
    crk = _bake(target, _image(name + '_crk', res), 'EMIT', src=hs)
    _restore(saved)
    # AO of the part on itself only (an AO node, only_local, 6 cm): the Cycles 'AO' bake type counts every object in
    # the scene - the low-poly target wrapped round the high one, the rest of the bus - and came out ~0 (r1-r4 atlases)
    sc.cycles.samples = max(samples, 32)
    saved = _emit_ao(hs, 0.06)
    ao = _bake(target, _image(name + '_ao', res), 'EMIT', src=hs)
    _restore(saved)
    # where the part is leatherette (vinyl, piping, sleeve): the albedo's alpha, so Unity puts the leather grain detail
    # only there and not on the painted tube and board
    sc.cycles.samples = 1
    saved = _emit_node(hs, 'leather_flag')
    lea = _bake(target, _image(name + '_lea', res), 'EMIT', src=hs)
    _restore(saved)
    sc.cycles.samples = 1
    saved = _emit_socket(hs, 'Metallic')
    met = _bake(target, _image(name + '_met', res), 'EMIT', src=hs)
    _restore(saved)
    bpy.data.objects.remove(hs, do_unlink=True)
    for m in target.data.materials:            # drop the bake image node again
        n = m.node_tree.nodes.get('__bake__')
        if n:
            m.node_tree.nodes.remove(n)
    bpy.context.scene.render.bake.use_selected_to_active = False
    os.makedirs(out_dir, exist_ok=True)
    flip = lambda a: a[::-1]
    files = {}
    p = os.path.join(out_dir, 'Part_%s_Albedo_%d.png' % (name, res))
    rgba = np.concatenate([lin2srgb(flip(alb)[..., :3]), np.clip(flip(lea)[..., :1], 0, 1)], -1)
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA').save(p)
    files['albedo'] = p
    p = os.path.join(out_dir, 'Part_%s_Normal_%d.png' % (name, res))
    Image.fromarray((np.clip(flip(nrm)[..., :3], 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)
    files['normal'] = p
    mask = np.stack([flip(met)[..., 0], 1.0 - flip(rgh)[..., 0], flip(crk)[..., 0], flip(ao)[..., 0]], -1)
    p = os.path.join(out_dir, 'Part_%s_Mask_%d.png' % (name, res))
    Image.fromarray((np.clip(mask, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(p)
    files['mask'] = p
    return files
