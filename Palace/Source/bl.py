# -*- coding: utf-8 -*-
"""bpy 小工具：Unity ↔ Blender 坐标、建网格、材质、相机、渲染设置。
Unity (x 右, y 上, z 前) 与 Blender 的换算沿用门的约定：Unity = (−x_b, z_b, −y_b)，即 Blender = (−x_u, −z_u, y_u)。"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

U2B = np.array([[-1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])     # Blender = U2B @ Unity
B2U = U2B.T


def u2b(p):
    return U2B @ np.asarray(p, float)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    return sc


def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c) if c.name not in (parent or bpy.context.scene.collection).children else None
    return c


def mesh_obj(name, V, F, mat=None, collection=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in np.asarray(V, float)], [], [tuple(int(i) for i in f) for f in F])
    me.validate()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    return ob


def box_vf(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    V = np.array([[lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]], [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
                  [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]]])
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 4, 7, 3)]
    return V, F


class MeshBuilder:
    """攒顶点和面（Blender 坐标），最后一次性建成一个物体。材质按面索引。"""

    def __init__(self):
        self.V, self.F, self.M = [], [], []

    def add(self, V, F, mi=0):
        o = len(self.V)
        self.V.extend([tuple(v) for v in np.asarray(V, float)])
        self.F.extend([tuple(int(i) + o for i in f) for f in F])
        self.M.extend([mi] * len(F))

    def box(self, lo, hi, mi=0):
        self.add(*box_vf(lo, hi), mi=mi)

    def build(self, name, mats, collection=None, smooth=False):
        ob = mesh_obj(name, self.V, self.F, None, collection, smooth)
        for m in mats:
            ob.data.materials.append(m)
        if len(mats) > 1:
            ob.data.polygons.foreach_set('material_index', self.M)
        return ob


def principled(name, base, rough=0.5, metal=0.0, emit=None, emit_strength=1.0, spec=0.5):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Specular IOR Level'].default_value = spec
    if emit is not None:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    return m


def emissive(name, rgb_lin):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*rgb_lin, 1)
    e.inputs['Strength'].default_value = 1.0
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs[0], o.inputs['Surface'])
    return m


def point_light_unity(name, pos_u, color_lin, intensity, rng, collection=None, radius=0.05):
    """Unity 烘焙点光（InverseSquared + 范围窗 (1−(d/r)^4)^2）：在白 Lambert 上输出 = albedo × I × win / d²。
    Blender 点光 P = 4π² I（Cycles：白 Lambert 输出辐亮度 = P/(4π²)/d²）；窗口用 Light Path 的 Ray Length 做。"""
    L = bpy.data.lights.new(name, 'POINT')
    L.color = tuple(color_lin)
    L.energy = 4.0 * math.pi ** 2 * intensity
    L.shadow_soft_size = radius
    L.use_nodes = True
    nt = L.node_tree
    em = nt.nodes['Emission']
    lp = nt.nodes.new('ShaderNodeLightPath')

    def m(op, a=None, b=None, clamp=False):
        n = nt.nodes.new('ShaderNodeMath')
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    w = m('POWER', m('SUBTRACT', 1.0, m('POWER', m('DIVIDE', lp.outputs['Ray Length'], rng), 4.0), clamp=True), 2.0)
    nt.links.new(w, em.inputs['Strength'])
    ob = bpy.data.objects.new(name, L)
    ob.location = Vector(u2b(pos_u))
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def camera_unity(name, eye_u, yaw_deg=0.0, pitch_deg=0.0, hfov=90.0, aspect=16 / 9):
    cam = bpy.data.cameras.new(name)
    cam.sensor_fit = 'HORIZONTAL'
    cam.angle = math.radians(hfov)
    cam.clip_start = 0.05
    cam.clip_end = 5000.0
    ob = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(ob)
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    fwd_u = np.array([math.sin(y) * math.cos(p), math.sin(p), math.cos(y) * math.cos(p)])
    d = Vector(u2b(fwd_u))
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    ob.location = Vector(u2b(eye_u))
    return ob


def world_trilight(sky, equator, ground):
    """Unity Trilight 的近似：按方向的 z 在 天 / 赤道 / 地 之间插值（线性颜色）。"""
    sc = bpy.context.scene
    w = bpy.data.worlds.new('W')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    mp = nt.nodes.new('ShaderNodeMapRange')
    mp.inputs[1].default_value = -1.0
    mp.inputs[2].default_value = 1.0
    nt.links.new(sep.outputs['Z'], mp.inputs[0])
    nt.links.new(mp.outputs[0], ramp.inputs[0])
    cr = ramp.color_ramp
    cr.elements[0].color = (*ground, 1)
    cr.elements[1].color = (*sky, 1)
    e = cr.elements.new(0.5)
    e.color = (*equator, 1)
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 1.0
    return w


def render_setup(w=960, h=540, samples=64, passes=True):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transparent_max_bounces = 4
    sc.cycles.use_light_tree = True
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.threads_mode = 'AUTO'
    sc.view_settings.view_transform = 'Standard'
    if hasattr(sc.render.image_settings, 'media_type'):
        sc.render.image_settings.media_type = 'MULTI_LAYER_IMAGE'
    else:
        sc.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
    sc.render.image_settings.color_depth = '32'
    vl = sc.view_layers[0]
    vl.use_pass_combined = True
    vl.use_pass_position = True
    vl.use_pass_z = True
    vl.use_pass_object_index = True
    vl.use_pass_diffuse_color = True
    return sc
