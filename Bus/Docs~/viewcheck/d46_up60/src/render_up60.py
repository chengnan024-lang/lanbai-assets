# D-46 look-up renders: the hero_up60 camera (Engineering/render_harness/cameras.json) in the bus from
# Bus/Source/build_bus.build(), every non-glass material eroded by erode.osl (s < 0 -> Transparent BSDF), Glass_* fully
# transparent, the underwater Snell window as the world. Cycles CPU + OSL.
#   ~/bpy/bin/python render_up60.py [--times 380,387,446,506] [--samples 24] [--res 960x540] [--threads 3]
import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402
import cabin_numpy as CN  # noqa: E402

SNELL_EL = 90.0 - math.degrees(math.asin(1.0 / 1.333))       # 41.4 deg, as Bus/Source/snell_check.py
AMB = tuple(float(v) * 0.6 for v in CN.srgb2lin('#6186A7'))   # act 7a cabin ambient, linear x 0.6
EMI = 0.10                                                    # + base x 0.10 emission, so dark surfaces still read
FACING = 0.35                                                 # flat ambient x (1 - 0.35 facing): a little form
SKY = (0.55 * 2, 0.75 * 2, 0.95 * 2)
WATER = (0.02, 0.05, 0.09)


def camera_spec(name='hero_up60'):
    d = json.load(open(os.path.join(C.REPO, 'Engineering', 'render_harness', 'cameras.json'), encoding='utf-8'))
    return d['cameras'][name]


def make_camera(sc, spec, W, H):
    cd = bpy.data.cameras.new('hero_up60')
    cd.type = 'PERSP'
    cd.sensor_fit = 'HORIZONTAL'
    cd.angle = math.radians(spec['hfov_deg'])
    cd.clip_start, cd.clip_end = 0.01, 200.0
    cam = bpy.data.objects.new('hero_up60', cd)
    sc.collection.objects.link(cam)
    e = spec['eye']
    cam.location = (e[0], e[2], e[1])                               # U2B
    # Blender camera looks down -Z: X +90 = level toward +Y (unity +z); + pitch = up; yaw + = right (-Z rotation)
    cam.rotation_euler = (math.radians(90.0 + spec['pitch_deg']), 0.0, math.radians(-spec['yaw_deg']))
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    return cam


def make_world(sc):
    wd = bpy.data.worlds.new('SnellWindow')
    wd.use_nodes = True
    nt = wd.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tc = nt.nodes.new('ShaderNodeTexCoord')                          # world 'Generated' = the ray direction
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    asn = nt.nodes.new('ShaderNodeMath')
    asn.operation = 'ARCSINE'
    asn.use_clamp = False
    nt.links.new(sep.outputs['Z'], asn.inputs[0])                    # Blender z = unity up: elevation
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs['From Min'].default_value = math.radians(SNELL_EL - 0.5)
    mr.inputs['From Max'].default_value = math.radians(SNELL_EL + 0.5)
    mr.inputs['To Min'].default_value = 0.0
    mr.inputs['To Max'].default_value = 1.0
    nt.links.new(asn.outputs[0], mr.inputs['Value'])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MIX'
    mix.inputs['A'].default_value = (*WATER, 1.0)
    mix.inputs['B'].default_value = (*SKY, 1.0)
    nt.links.new(mr.outputs['Result'], mix.inputs['Factor'])
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = 1.0
    nt.links.new(mix.outputs['Result'], bg.inputs['Color'])
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    sc.world = wd


def eroding_material(src, resist):
    """flat ambient (act 7a) on the material's base colour, cut by erode.osl: removed -> Transparent BSDF."""
    bs = src.node_tree.nodes.get('Principled BSDF') if src.use_nodes else None
    base = tuple(bs.inputs['Base Color'].default_value[:3]) if bs else tuple(src.diffuse_color[:3])
    m = bpy.data.materials.new('D46_' + src.name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    sn = C.script_node(nt)
    sn.inputs['resist'].default_value = resist
    flat = tuple(b * a + b * EMI for b, a in zip(base, AMB))
    rgb = nt.nodes.new('ShaderNodeRGB')
    rgb.outputs[0].default_value = (*flat, 1.0)
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    k = nt.nodes.new('ShaderNodeMath')
    k.operation = 'MULTIPLY_ADD'                                    # 1 - FACING x facing
    k.inputs[1].default_value = -FACING
    k.inputs[2].default_value = 1.0
    nt.links.new(lw.outputs['Facing'], k.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(rgb.outputs[0], em.inputs['Color'])
    nt.links.new(k.outputs[0], em.inputs['Strength'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    tr.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(sn.outputs['removed'], mx.inputs['Fac'])
    nt.links.new(em.outputs[0], mx.inputs[1])
    nt.links.new(tr.outputs[0], mx.inputs[2])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m, sn


def clear_material():
    m = bpy.data.materials.new('D46_GlassClear')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    tr.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(tr.outputs[0], out.inputs['Surface'])
    return m


def setup_materials():
    obs = [o for o in bpy.data.objects if o.type == 'MESH']
    clear = clear_material()
    made, nodes = {}, []
    n_glass = 0
    for o in obs:
        if o.name.startswith('Glass_'):
            for s in o.material_slots:
                s.material = clear
            n_glass += 1
            continue
        for s in o.material_slots:
            src = s.material
            if src is None or src.name.startswith('D46_'):
                continue
            if src.name not in made:
                resist = 0.30 if 'Steel' in src.name else 0.0
                made[src.name] = eroding_material(src, resist)
                nodes.append(made[src.name][1])
            s.material = made[src.name][0]
    return nodes, n_glass, sorted(made)


def zenith_circle(sc, cam, eye_u, el=70.0, step=0.5):
    """pixel coordinates (x right, y down) of the 20-deg circle round the zenith; None where behind the camera."""
    bpy.context.view_layer.update()                                 # the camera's matrix_world
    W, H = sc.render.resolution_x, sc.render.resolution_y
    eye_b = Vector((eye_u[0], eye_u[2], eye_u[1]))
    pts = []
    for az in np.arange(0.0, 360.0 + step / 2, step):
        a, e = math.radians(az), math.radians(el)
        d = (math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a))
        v = world_to_camera_view(sc, cam, eye_b + Vector((d[0], d[2], d[1])) * 5.0)
        pts.append(None if v.z <= 0 else (v.x * W, (1.0 - v.y) * H))
    z = world_to_camera_view(sc, cam, eye_b + Vector((0, 0, 5.0)))
    return pts, (z.x * W, (1.0 - z.y) * H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--times', default='380,387,446,506')
    ap.add_argument('--zen', default='1,0')
    ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--res', default='960x540')
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--view', default='Standard')
    ap.add_argument('--suffix', default='')
    ap.add_argument('--save-blend', default='')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    W, H = [int(v) for v in a.res.split('x')]
    import build_bus
    t0 = time.time()
    build_bus.build()
    print('[up60] build %.1f s' % (time.time() - t0))
    sc = bpy.context.scene
    C.cycles_osl(sc, samples=a.samples, threads=a.threads)
    cy = sc.cycles
    cy.max_bounces = 2                    # emission only: no light bounces needed
    cy.transparent_max_bounces = 64
    cy.use_denoising = True
    cy.denoiser = 'OPENIMAGEDENOISE'
    cy.pixel_filter_type = 'BLACKMAN_HARRIS'
    cy.filter_width = 1.5
    sc.view_settings.view_transform = a.view
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    spec = camera_spec()
    cam = make_camera(sc, spec, W, H)
    make_world(sc)
    nodes, n_glass, made = setup_materials()
    print('[up60] %d eroding materials (%s), %d Glass_* objects clear' % (len(made), ', '.join(made), n_glass))
    circle, zen_px = zenith_circle(sc, cam, spec['eye'])
    os.makedirs(C.OUT, exist_ok=True)
    json.dump(dict(camera=spec, res=[W, H], zenith_px=zen_px, circle20_px=circle),
              open(os.path.join(C.OUT, 'up60_circle.json'), 'w'), indent=0)
    print('[up60] zenith projects to px (%.1f, %.1f) of %dx%d' % (zen_px[0], zen_px[1], W, H))
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
    log = []
    for t in [float(v) for v in a.times.split(',')]:
        fade, hole = float(CN.fade(t)), float(CN.hole(t))
        for zen in [int(v) for v in a.zen.split(',')]:
            for sn in nodes:
                sn.inputs['fade'].default_value = fade
                sn.inputs['hole_open'].default_value = hole
                sn.inputs['zen_on'].default_value = float(zen)
            path = os.path.join(C.OUT, 'up60_%d_%s%s.png' % (round(t), 'd46' if zen else 'before', a.suffix))
            sc.render.filepath = path
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            dt = time.time() - t1
            log.append(dict(t=t, fade=round(fade, 4), hole=hole, zen_on=zen, png=path, render_s=round(dt, 1)))
            print('[up60] t %.0f fade %.4f zen_on %d -> %s (%.1f s)' % (t, fade, zen, path, dt))
    json.dump(dict(samples=a.samples, res=[W, H], view=a.view, ambient_lin=AMB, emission=EMI, facing=FACING, sky=SKY,
                   water=WATER, snell_el=SNELL_EL, renders=log),
              open(os.path.join(C.OUT, 'up60_render%s.json' % a.suffix), 'w'), indent=1)


if __name__ == '__main__':
    main()
