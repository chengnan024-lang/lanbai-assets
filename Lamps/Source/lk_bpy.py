# -*- coding: utf-8 -*-
"""bpy 桥：把 lk_geom 的 Part 变成 Blender 物体；渲染场景的共用设置。
单位约定（“Unity 单位”）：Cycles 里一盏点光的照度 E_b = P / (4π d²)，白漫反射显示 albedo·E_b/π；
Unity 的 Standard 显示 albedo·E。所以要让 Blender 的像素 = Unity 场景线性，灯的功率 P = 4π²·I（I = E·d²，Unity 的
“强度”），平行光强度 = π·E；自发光两边一样（Unity HDR 颜色 = Cycles emission × strength）。"""
import math
import os

import bpy
import numpy as np

PI = math.pi


def reset_scene(w, h, spp, threads=4):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves, bpy.data.images):
        for b in list(coll):
            if b.users == 0:
                coll.remove(b)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 6
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.sample_clamp_indirect = 20.0
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = threads
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    sc.render.film_transparent = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new('W')
    sc.world.use_nodes = True
    return sc


def unity_point_power(I):
    """Unity intensity I (E = I / d^2) -> Cycles point/spot power (W)."""
    return 4.0 * PI * PI * I


def obj_from_parts(name, parts, mats, smooth_angle=40.0, collection=None):
    """parts: dict mat_name -> Part. mats: dict mat_name -> bpy material. One object, one slot per material."""
    V, F, UV, MI = [], [], [], []
    slot = {}
    for k, p in parts.items():
        o = len(V)
        V += p.v
        if k not in slot:
            slot[k] = len(slot)
        for f, uv in zip(p.f, p.uv):
            F.append(tuple(i + o for i in f)); UV.append(uv); MI.append(slot[k])
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], F)
    me.update()
    uvl = me.uv_layers.new(name='UVMap')
    flat = [c for uv in UV for t in uv for c in t]
    uvl.data.foreach_set('uv', flat)
    me.polygons.foreach_set('material_index', MI)
    for k in sorted(slot, key=slot.get):
        me.materials.append(mats.get(k) if mats else None)
    # merge coincident seam vertices so smooth shading has no seams, then auto smooth by angle
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me); bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if smooth_angle is not None:
        # Blender 4.1+: smooth by angle = per-edge sharp flags
        import bmesh as _b
        bm = _b.new(); bm.from_mesh(me)
        lim = math.radians(smooth_angle)
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > lim:
                e.smooth = False
        bm.to_mesh(me); bm.free()
    return ob


def camera(name, loc, yaw_deg, pitch_deg, hfov_deg, w, h, sc):
    """Unity-style camera: Blender world = Z up, +Y forward (= Unity +Z). yaw + to the right, pitch + up."""
    cam = bpy.data.cameras.new(name)
    cam.sensor_fit = 'HORIZONTAL'
    cam.sensor_width = 36.0
    cam.lens = 18.0 / math.tan(math.radians(hfov_deg) / 2)
    cam.clip_start = 0.05
    cam.clip_end = 5000
    ob = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(ob)
    ob.location = loc
    # default camera looks down -Z with +Y up; rotate X by 90 -> looks along +Y
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = (math.radians(90 + pitch_deg), 0.0, math.radians(-yaw_deg))
    sc.camera = ob
    return ob


def read_exr(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(im)
    return px


def render_to(path, sc=None, passes=False):
    sc = sc or bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return read_exr(path if path.endswith('.exr') else path + '.exr')
