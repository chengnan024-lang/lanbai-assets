# -*- coding: utf-8 -*-
"""bpy side of the harness (Blender 5.0.1 as a Python module): empty scene, the fixed cameras, the bus shell
placeholder, render settings, render -> scene-linear float array.

Coordinates: everything the packages hand over is in UNITY space (m, x right, y up, z forward, left-handed).
Blender is right-handed z-up. Mapping: blender (x, y, z) = (unity x, unity z, unity y) — a swap of two axes,
which also flips handedness, so a Unity point maps to the same physical place. Use U2B() for points and
unity_quat_to_blender() for rotations; FBX exported with Tentacles/Source/lib/export_unity.py comes back in
correctly with import_unity_fbx() (axis_forward='Z', axis_up='Y' inverse of the export)."""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

from . import paths


def U2B(p):
    return Vector((p[0], p[2], p[1]))


def unity_quat_to_blender(q_xyzw):
    """Unity quaternion (x, y, z, w; left-handed, y-up) -> Blender quaternion (w, x, y, z) under U2B.
    Axis swap y<->z is a reflection, so the rotation axis maps by the same swap and the angle flips sign."""
    x, y, z, w = q_xyzw
    return Quaternion((w, -x, -z, -y))


# ------------------------------------------------------------------------------------------------ scene
def new_scene(samples=64, res=(1920, 1080), denoise=True, threads=0, world_rgb=(0.0, 0.0, 0.0), world_strength=1.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.01
    sc.cycles.use_denoising = denoise
    if denoise:
        try:
            sc.cycles.denoiser = 'OPENIMAGEDENOISE'
        except TypeError:
            pass
    sc.cycles.max_bounces = 6
    sc.cycles.sample_clamp_indirect = 20.0
    sc.render.threads_mode = 'FIXED' if threads else 'AUTO'
    if threads:
        sc.render.threads = threads
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    # scene-linear out: no view transform / look / exposure (the PPv2 simulation does the display side)
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    sc.render.image_settings.exr_codec = 'ZIP'
    w = bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*world_rgb, 1.0)
    bg.inputs[1].default_value = world_strength
    return sc


def load_cameras():
    return json.load(open(paths.CAMERAS_JSON, encoding='utf-8'))['cameras']


def camera_spec(name_or_dict, **over):
    cam = dict(load_cameras()[name_or_dict]) if isinstance(name_or_dict, str) else dict(name_or_dict)
    cam.update({k: v for k, v in over.items() if v is not None})
    return cam


def add_camera(cam, name='LB_Camera', clip=(0.05, 45000.0)):
    """cam: dict with eye (Unity bus-relative), yaw_deg (+ right), pitch_deg (+ up), hfov_deg, res [w, h].
    Roll is always 0 (bible 1.8). Pinhole like Unity's camera; horizontal FOV fixed."""
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = 'HORIZONTAL'
    cd.angle = math.radians(cam['hfov_deg'])
    cd.clip_start, cd.clip_end = clip
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = U2B(cam['eye'])
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = (math.radians(90.0 + cam.get('pitch_deg', 0.0)), 0.0, math.radians(-cam.get('yaw_deg', 0.0)))
    sc = bpy.context.scene
    sc.camera = ob
    if 'res' in cam:
        sc.render.resolution_x, sc.render.resolution_y = cam['res']
    return ob


# ------------------------------------------------------------------------------------------------ materials
def hex_lin(h):
    h = h.lstrip('#')
    v = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v)


def mat_principled(name, albedo, roughness=0.5, metallic=0.0, emission=None, emission_strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*(hex_lin(albedo) if isinstance(albedo, str) else albedo), 1.0)
    b.inputs['Roughness'].default_value = roughness
    b.inputs['Metallic'].default_value = metallic
    if emission is not None:
        b.inputs['Emission Color'].default_value = (*(hex_lin(emission) if isinstance(emission, str) else emission), 1.0)
        b.inputs['Emission Strength'].default_value = emission_strength
    return m


def mat_emission(name, rgb_linear, strength=1.0):
    """an unlit / emissive surface at an exact scene-linear value (what a Unity unlit shader writes)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (*rgb_linear, 1.0)
    em.inputs[1].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def mesh_object(name, verts_unity, faces, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(U2B(v)) for v in verts_unity], [], [tuple(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat is not None:
        ob.data.materials.append(mat)
    return ob


# ------------------------------------------------------------------------------------------------ bus shell
def _dir(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)])


def _outward(ob):
    """make a closed mesh's normals point outward (the EXACT boolean needs consistent orientation)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)          # the caps are non-planar n-gons
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def _frustum(name, eye, az, el, near=0.12, far=30.0, steps=8):
    """closed prism from the eye along an angular rectangle (az0..az1, el0..el1); edges subdivided so wide
    windows (100 deg+) stay angular, not planar."""
    ring = []
    a0, a1 = az
    e0, e1 = el
    for i in range(steps):
        ring.append((a0 + (a1 - a0) * i / steps, e0))
    for i in range(steps):
        ring.append((a1, e0 + (e1 - e0) * i / steps))
    for i in range(steps):
        ring.append((a1 - (a1 - a0) * i / steps, e1))
    for i in range(steps):
        ring.append((a0, e1 - (e1 - e0) * i / steps))
    V = [eye + near * _dir(a, e) for a, e in ring] + [eye + far * _dir(a, e) for a, e in ring]
    n = len(ring)
    F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    F.append(tuple(range(n - 1, -1, -1)))
    F.append(tuple(range(n, 2 * n)))
    return _outward(mesh_object(name, V, F))


def bus_shell(preset='bible_v2', glass=False, interior_ambient=None, collection_name='BusShell'):
    """placeholder shell: a closed box (outer hull) with the preset's windows cut along rays from the preset eye.
    interior_ambient: optional linear rgb added as emission x albedo (stand-in for _Udon_CabinAmbient so the
    interior is not pure black in sky-only renders). Returns (objects, eye)."""
    J = json.load(open(paths.BUS_JSON, encoding='utf-8'))
    B = J['body']
    P = J['presets'][preset]
    eye = np.array(P['eye'], float)
    hw = B['width'] / 2.0
    z0, z1 = B['z_front'] - B['length'], B['z_front']
    y0, y1 = B['floor_y'] - 0.02, B['ceiling_y']
    t = B['wall']
    # hollow box = outer box minus inner box (walls t thick), built as two boxes + boolean
    def box(name, lo, hi):
        x0, yy0, zz0 = lo
        x1, yy1, zz1 = hi
        V = [(x0, yy0, zz0), (x1, yy0, zz0), (x1, yy1, zz0), (x0, yy1, zz0), (x0, yy0, zz1), (x1, yy0, zz1), (x1, yy1, zz1), (x0, yy1, zz1)]
        F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 4, 7, 3)]
        return _outward(mesh_object(name, V, F))
    shell = box('Bus_Hull', (-hw - t, y0 - t, z0 - t), (hw + t, y1 + t, z1 + t))
    inner = box('Bus_Inner', (-hw, y0, z0), (hw, y1, z1))
    cutters = [inner]
    for w in P['windows']:
        span = abs(w['az'][1] - w['az'][0])
        cutters.append(_frustum('Bus_Win_' + w['name'], eye, w['az'], w['el'], steps=w.get('steps', 1 if span <= 90 else 4)))
    for c in cutters:
        md = shell.modifiers.new('cut_' + c.name, 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.solver = 'EXACT'
        md.object = c
    bpy.context.view_layer.objects.active = shell
    for md in list(shell.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)
    mi = J['materials']['interior']
    m = mat_principled('Bus_Interior', mi['albedo'], mi['roughness'])
    if interior_ambient is not None:
        b = m.node_tree.nodes['Principled BSDF']
        al = hex_lin(mi['albedo'])
        b.inputs['Emission Color'].default_value = (*[a * c for a, c in zip(al, interior_ambient)], 1.0)
        b.inputs['Emission Strength'].default_value = 1.0
    shell.data.materials.append(m)
    objs = [shell]
    # mullions: thin dark posts inside the windscreen, at a fixed azimuth
    for mu in P.get('mullions', []):
        d0 = _dir(mu['az'] - mu['width_deg'] / 2, mu['el'][0])
        # place on the windscreen plane z = z_front - t
        zf = z1 - 0.01
        k = lambda d: (zf - eye[2]) / d[2]
        pts = []
        for az_, el_ in ((mu['az'] - mu['width_deg'] / 2, mu['el'][0]), (mu['az'] + mu['width_deg'] / 2, mu['el'][0]),
                         (mu['az'] + mu['width_deg'] / 2, mu['el'][1]), (mu['az'] - mu['width_deg'] / 2, mu['el'][1])):
            d = _dir(az_, el_)
            pts.append(tuple(eye + d * k(d)))
        objs.append(mesh_object('Bus_' + mu['name'], pts, [(0, 1, 2, 3)], m))
    if glass:
        objs += _glass_panes(P, eye, B, J['materials']['glass'])
    return objs, eye


def _glass_panes(P, eye, B, g):
    """a thin film over each window aperture, on the hull, as a transparent + weak fresnel mirror (no refraction)."""
    m = bpy.data.materials.new('Bus_Glass')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    tr.inputs[0].default_value = (*hex_lin(g['transmission_tint']), 1.0)
    gl = nt.nodes.new('ShaderNodeBsdfGlossy')
    gl.inputs['Roughness'].default_value = 0.02
    fr = nt.nodes.new('ShaderNodeFresnel')
    fr.inputs['IOR'].default_value = 1.5
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fr.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(gl.outputs[0], mx.inputs[2])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(mx.outputs[0], out.inputs[0])
    objs = []
    hw = B['width'] / 2.0
    z1 = B['z_front']
    for w in P['windows']:
        # project the angular rectangle on a sphere of radius r around the eye (film sits just inside the hull)
        quads, verts = [], []
        n = 8
        for i in range(n + 1):
            for j in range(n + 1):
                a = w['az'][0] + (w['az'][1] - w['az'][0]) * i / n
                e = w['el'][0] + (w['el'][1] - w['el'][0]) * j / n
                d = _dir(a, e)
                # distance to the hull box along d
                ts = []
                for axis, lim in ((0, hw), (0, -hw), (1, B['ceiling_y']), (1, B['floor_y']), (2, z1), (2, z1 - B['length'])):
                    if abs(d[axis]) > 1e-6:
                        tt = (lim - eye[axis]) / d[axis]
                        if tt > 0:
                            ts.append(tt)
                verts.append(tuple(eye + d * (min(ts) - 0.005)))
        for i in range(n):
            for j in range(n):
                a = i * (n + 1) + j
                quads.append((a, a + n + 1, a + n + 2, a + 1))
        objs.append(mesh_object('Bus_Glass_' + w['name'], verts, quads, m))
    return objs


def unity_directional(name, E, colour_hex, to_light_dir_unity, angle_deg=0.5, shadows=True):
    """a Unity directional light of linear illuminance E (VRChat: Inspector intensity = E, CONTROL §3).
    Unity's diffuse has no 1/pi (white Lambert under intensity 1 at normal incidence = 1.0); Cycles' sun strength is
    irradiance and its diffuse divides by pi, so strength = pi x E. to_light_dir_unity: unit vector from the scene
    TOWARDS the light (e.g. _Udon_MoonDir)."""
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = math.pi * E
    ld.color = hex_lin(colour_hex)
    ld.angle = math.radians(angle_deg)
    ld.use_shadow = shadows
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    d = U2B(to_light_dir_unity).normalized()
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = (-d).to_track_quat('-Z', 'Y')
    return ob


def unity_ambient_flat(rgb_linear):
    """flat ambient (Unity ambient colour / Trilight with equal colours) = a uniform world of that radiance:
    a white Lambert surface then receives exactly rgb (Cycles: L_world x pi / pi)."""
    bg = bpy.context.scene.world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*rgb_linear, 1.0)
    bg.inputs[1].default_value = 1.0


def import_unity_fbx(path):
    """FBX written by Tentacles/Source/lib/export_unity.py (or any Unity-convention FBX, metres)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, axis_forward='Z', axis_up='Y', global_scale=1.0)
    return [o for o in bpy.data.objects if o not in before]


# ------------------------------------------------------------------------------------------------ render
def render_linear(out_exr):
    """render the current scene; write the EXR; return (H, W, 3) float32 scene-linear, top row first."""
    sc = bpy.context.scene
    os.makedirs(os.path.dirname(os.path.abspath(out_exr)), exist_ok=True)
    sc.render.filepath = out_exr
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(out_exr, check_existing=False)
    W, H = img.size
    px = np.empty(W * H * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(H, W, 4)[::-1, :, :3].copy()
