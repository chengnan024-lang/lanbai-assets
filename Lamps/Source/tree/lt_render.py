# -*- coding: utf-8 -*-
"""Renders of the built trees (open Trees.blend from lt_build.py, add a stage).
usage: python lt_render.py <Trees.blend> <shot> <out.exr> W H SPP [k=v ...]
shots: lineup | impostors | compare_overview | compare_right | compare_left | hero | hero_seq
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import bpy  # noqa
import numpy as np  # noqa

blend = sys.argv[1]
bpy.ops.wm.open_mainfile(filepath=blend)
import lk_bpy as B  # noqa
import lk_mats as MT  # noqa

NAMES = ['Tree_A1', 'Tree_A2', 'Tree_A3', 'Tree_B1']


def roots():
    return {n: bpy.data.objects[n] for n in NAMES if n in bpy.data.objects}


def show_lod(lod):
    for n, r in roots().items():
        for k in range(3):
            o = bpy.data.objects.get('%s_LOD%d' % (n, k))
            if o:
                o.hide_render = (k != lod)


def place(name, x, y, rot=0.0, lod=0, copy=False):
    """Instance a tree (linked duplicate of the chosen LOD) at Blender (x, y, 0)."""
    src = bpy.data.objects['%s_LOD%d' % (name, lod)]
    ob = bpy.data.objects.new('%s_at_%.0f_%.0f' % (name, x, y), src.data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, y, 0); ob.rotation_euler = (0, 0, rot)
    return ob


def hide_originals():
    for n, r in roots().items():
        for k in range(3):
            o = bpy.data.objects.get('%s_LOD%d' % (n, k))
            if o:
                o.hide_render = True


def settings(W, H, spp):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = False; sc.cycles.use_denoising = False
    sc.cycles.transparent_max_bounces = 64; sc.cycles.max_bounces = 6
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
    return sc


def unity_cam(eye_u, target_u, vfov, W, H):
    """Unity world (x, y up, z fwd) -> Blender (x, z, y)."""
    e = np.array([eye_u[0], eye_u[2], eye_u[1]]); t = np.array([target_u[0], target_u[2], target_u[1]])
    d = t - e
    yaw = math.degrees(math.atan2(d[0], d[1])); pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    hfov = 2 * math.degrees(math.atan(math.tan(math.radians(vfov) / 2) * W / H))
    return B.camera('cam', tuple(e), yaw, pitch, hfov, W, H, bpy.context.scene)


# FromLocal/trees/README.md: the 7 positions (Unity x, z) and the three cameras (vertical FOV 55, 1600x900)
POSITIONS = [((9.0, 16.0), 'Tree_A1', 20), ((12.5, 24.0), 'Tree_A2', 140), ((8.5, 33.0), 'Tree_A3', 260), ((15.0, 40.0), 'Tree_B1', 0),
             ((-8.5, 14.0), 'Tree_A3', 70), ((-11.0, 26.0), 'Tree_A1', 200), ((-9.0, 38.0), 'Tree_A2', 310)]
CAMS = {'overview': ((4.6, 1.65, -9.0), (4.0, 5.0, 30.0)), 'right': ((3.2, 1.65, 2.0), (10.0, 5.0, 24.0)),
        'left': ((-2.5, 1.65, 0.0), (-10.0, 5.0, 26.0))}


def lod_for(dist, h):
    """Unity LODGroup screen-relative-height switch (README): LOD0 > 0.25, LOD1 > 0.08, LOD2 below, at vfov 55."""
    rel = h / (2 * dist * math.tan(math.radians(55) / 2))
    return 0 if rel > 0.25 else (1 if rel > 0.08 else 2)


def night_stage(wet=1.0):
    """Act 1 / 2 rainy night (bible §6·1): sky the camera sees = zenith #09080D -> horizon #121A28 (fill values),
    ambient light on objects = Trilight sky #1A2438 (what diffuse rays see), fog in post (0.009, #161B27).
    A sodium cobra-head standard at Unity (6.3, z 11) like the local comparison shots; wet road + verges."""
    sys.path.insert(0, os.path.join(HERE, '..'))
    import lk_scene as S
    import lk_geom as G
    sc = bpy.context.scene
    w = sc.world; nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    lp = nt.nodes.new('ShaderNodeLightPath')
    cam_bg = nt.nodes.new('ShaderNodeBackground'); cam_bg.inputs[0].default_value = (*MT.hexlin('#0E1220'), 1)
    amb_bg = nt.nodes.new('ShaderNodeBackground'); amb_bg.inputs[0].default_value = (*MT.hexlin('#1A2438'), 1)
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); nt.links.new(amb_bg.outputs[0], mx.inputs[1]); nt.links.new(cam_bg.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    S.landscape(0.0, wet)
    mats = {k: MT.lampkit(k, os.environ.get('LK_TEX', '/tmp/lk/tex'), wet) for k in MT.KIT}
    # the standard on the right shoulder, arm toward the road (-x): pole at x 6.3 + 1.52
    d, info = G.road_lamp(0)
    d.pop('M_Lamps_ArcTube', None)
    M = G.trans(6.3 + 1.52, 11.0, 0) @ G.rot_z(math.pi)
    for p in d.values():
        p.transform(M)
    ac = (M @ np.r_[np.array(info['arc_centre']), 1])[:3]
    gm = MT.lampglow('glow', os.environ.get('LK_TEX', '/tmp/lk/tex'), ac - (0.06, 0, 0), ac + (0.06, 0, 0), S.HEAD_FILL,
                     tuple(np.array(S.HEAD_FILL) * np.array([2.2, 2.6, 4.0])), wet)
    allm = dict(mats); allm['M_Lamps_Refractor'] = gm
    B.obj_from_parts('stopLamp', d, allm)
    S.cobra_light('sodium', tuple(ac + (0, 0, -0.04)), 40.0, S.SODIUM)
    return ac


def main():
    shot, out, W, H, spp = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
    kw = dict(a.split('=') for a in sys.argv[7:])
    sc = settings(W, H, spp)
    w = sc.world; bg = w.node_tree.nodes['Background']
    if shot == 'lineup':
        lod = int(kw.get('lod', 0))
        hide_originals()
        for i, n in enumerate(NAMES):
            place(n, (i - 1.5) * 15.0, 0, lod=lod)
        bg.inputs[0].default_value = (0.55, 0.60, 0.66, 1); bg.inputs[1].default_value = 1.0
        sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 2.0
        so = bpy.data.objects.new('s', sun); sc.collection.objects.link(so); so.rotation_euler = (0.6, 0.3, 2.2)
        B.camera('cam', (0, -75, 7), 0, 0, 52, W, H, sc)
    elif shot.startswith('compare_'):
        cam = shot.split('_', 1)[1]
        hide_originals()
        night_stage()
        e, t = CAMS[cam]
        for (x, z), n, rot in POSITIONS:
            dist = math.hypot(x - e[0], z - e[2])
            h = float(bpy.data.objects['%s_LOD0' % n].dimensions[2])
            place(n, x, z, math.radians(rot), lod=int(kw['lod']) if 'lod' in kw else lod_for(dist, h))
        unity_cam(e, t, 55, W, H)
    elif shot.startswith('hero'):
        # the main seat (D-40b #1: Unity (0.55, 1.70, 2.05)) looking at the first right-hand tree's crown, at the
        # render-target density 20 px/deg (D-40b #2): crop 40 x 30 deg -> 800 x 600
        hide_originals()
        night_stage()
        for (x, z), n, rot in POSITIONS:
            place(n, x, z, math.radians(rot), lod=0)
        eye = [0.55, 1.70, 2.05]
        if 'sway' in kw:      # micro head motion: +-2 cm, +-1 deg, two sines (same as the Unity test tool's micro_motion)
            f = float(kw['sway'])
            eye = [eye[0] + 0.02 * math.sin(2 * math.pi * f), eye[1] + 0.01 * math.sin(2 * math.pi * 1.7 * f + 1), eye[2]]
        tgt = [9.0, 6.0, 16.0]
        cam = unity_cam(eye, tgt, 30, W, H)
        if 'sway' in kw:
            cam.rotation_euler[2] += math.radians(1.0) * math.sin(2 * math.pi * 1.3 * float(kw['sway']))
    if kw.get('coverage') == '1':
        # flicker proxy: geometry + alpha-cut coverage only (white on black), no lights, no noise from lighting;
        # BOX filter 1 px with `spp` jittered samples ~ MSAA alpha-to-coverage with spp samples
        for m in list(bpy.data.materials):
            nt = m.node_tree
            if nt is None:
                continue
            outn = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL']
            if not outn or not outn[0].inputs[0].links:
                continue
            src = outn[0].inputs[0].links[0].from_node
            em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1, 1, 1, 1)
            if src.type == 'MIX_SHADER' and any(l.from_node.type == 'BSDF_TRANSPARENT' for l in src.inputs[1].links):
                mx = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
                tr.inputs[0].default_value = (0, 0, 0, 1)
                if src.inputs[0].links:
                    nt.links.new(src.inputs[0].links[0].from_socket, mx.inputs[0])
                nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
                nt.links.new(mx.outputs[0], outn[0].inputs[0])
            else:
                emb = nt.nodes.new('ShaderNodeEmission'); emb.inputs['Color'].default_value = (0, 0, 0, 1)
                nt.links.new(emb.outputs[0], outn[0].inputs[0]) if kw.get('leaves_only') == '1' else nt.links.new(em.outputs[0], outn[0].inputs[0])
        w = sc.world; nt = w.node_tree; nt.nodes.clear()
        o = nt.nodes.new('ShaderNodeOutputWorld'); bgn = nt.nodes.new('ShaderNodeBackground')
        bgn.inputs[0].default_value = (0, 0, 0, 1); nt.links.new(bgn.outputs[0], o.inputs[0])
        for ob in bpy.data.objects:
            if ob.type == 'LIGHT':
                ob.hide_render = True
        sc.cycles.max_bounces = 0
        sc.cycles.filter_width = float(kw.get('pf', 1.0))
        sc.cycles.pixel_filter_type = 'BOX'
        sc.cycles.seed = int(kw.get('seed', 0))
    rgb = B.render_to(out, sc)
    np.save(out.replace('.exr', '.npy'), rgb[..., :3].astype(np.float32))
    if shot != 'lineup' and kw.get('coverage') != '1':
        # depth for the post fog: every material -> emission = view distance; alpha-cut leaves must stay cut, so the
        # override keeps the leaf / impostor alpha by using a holdout-free per-material swap instead of material_override
        import lk_mats as MT2
        dm = MT2.depth_material()
        for m in list(bpy.data.materials):
            if m is dm or m.node_tree is None:
                continue
            nt = m.node_tree
            outn = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL']
            if not outn:
                continue
            src = outn[0].inputs[0].links[0].from_node if outn[0].inputs[0].links else None
            cd = nt.nodes.new('ShaderNodeCameraData'); em = nt.nodes.new('ShaderNodeEmission')
            nt.links.new(cd.outputs['View Distance'], em.inputs['Strength'])
            if src is not None and src.type == 'MIX_SHADER' and any(l.from_node.type == 'BSDF_TRANSPARENT' for l in src.inputs[1].links):
                mx = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
                if src.inputs[0].links:
                    nt.links.new(src.inputs[0].links[0].from_socket, mx.inputs[0])
                nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
                nt.links.new(mx.outputs[0], outn[0].inputs[0])
            else:
                nt.links.new(em.outputs[0], outn[0].inputs[0])
        w = sc.world; nt = w.node_tree; nt.nodes.clear()
        o = nt.nodes.new('ShaderNodeOutputWorld'); bgn = nt.nodes.new('ShaderNodeBackground')
        bgn.inputs[0].default_value = (1e6, 1e6, 1e6, 1); nt.links.new(bgn.outputs[0], o.inputs[0])
        for ob in bpy.data.objects:
            if ob.type == 'LIGHT':
                ob.hide_render = True
        sc.cycles.samples = 8; sc.cycles.max_bounces = 0
        sc.cycles.transparent_max_bounces = 64
        dep = B.render_to(out.replace('.exr', '_depth.exr'), sc)
        np.save(out.replace('.exr', '_depth.npy'), dep[..., 0].astype(np.float32))


main()
