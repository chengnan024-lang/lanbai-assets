"""RainSplash_Flip4x4_512: crown splash of a 2.2 mm drop at 5 m/s on a 0.3 mm film (wet asphalt), 16 frames.
Rendered in Cycles as water geometry lit by a cool overhead-back tube (the stop lamp), black world; frames are
LUMINANCE (glints) + ALPHA.  Frame 0 top-left, row-major.  Frame covers 48 mm x 48 mm; impact point at
(0.5, 0.125) of the frame (u, v with v up) -> pivot for a Vertical Billboard.  Real time 0-32 ms, played over
0.12 s (3x slow-motion, the eye cannot see 40 ms)."""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rainpaths as RP
OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else RP.out_dir()
FR = 16; PX = 384
rng = np.random.default_rng(5)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 64
sc.cycles.use_denoising = False
sc.render.threads_mode = 'FIXED'; sc.render.threads = 3
sc.render.resolution_x = sc.render.resolution_y = PX
sc.render.film_transparent = True
sc.cycles.film_transparent_glass = False
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8; sc.cycles.glossy_bounces = 6
sc.cycles.caustics_reflective = True; sc.cycles.caustics_refractive = True

world = bpy.data.worlds.new('W'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.004, 0.006, 0.011, 1); bg.inputs[1].default_value = 1.0

water = bpy.data.materials.new('water'); water.use_nodes = True
nt = water.node_tree; nt.nodes.clear()
o = nt.nodes.new('ShaderNodeOutputMaterial'); g = nt.nodes.new('ShaderNodeBsdfGlass')
g.inputs['IOR'].default_value = 1.333; g.inputs['Roughness'].default_value = 0.03
nt.links.new(g.outputs[0], o.inputs[0])

# lamp: 1.2 m tube 3.5 m above and 1.5 m behind the splash (seen from the camera side: back-lit, as under the stop lamp)
bpy.ops.object.light_add(type='AREA', location=(0, 1.6, 3.4))
L = bpy.context.object; L.data.shape = 'RECTANGLE'; L.data.size = 1.2; L.data.size_y = 0.05
L.data.energy = 900; L.data.color = (0.89, 0.95, 0.96)
L.rotation_euler = (math.radians(25), 0, 0)
bpy.ops.object.light_add(type='AREA', location=(0.8, -1.2, 1.6))           # faint front fill (door light)
F = bpy.context.object; F.data.size = 0.6; F.data.energy = 160; F.data.color = (0.89, 0.95, 0.96)
F.rotation_euler = (math.radians(55), 0, math.radians(35))

cam_data = bpy.data.cameras.new('C'); cam_data.type = 'ORTHO'; cam_data.ortho_scale = 0.048
cam = bpy.data.objects.new('C', cam_data); sc.collection.objects.link(cam); sc.camera = cam
el = math.radians(14)
# frame centre is 0.375*48 mm = 18 mm above the impact point (impact at v = 0.125)
cam.location = (0, -1.0 * math.cos(el), 1.0 * math.sin(el) + 0.018)
cam.rotation_euler = (math.pi / 2 - el, 0, 0)

D = 0.0022; V0 = 5.0
N_FING = 16
fing_phase = rng.uniform(0, 2 * np.pi, N_FING)
fing_len = rng.uniform(0.6, 1.3, N_FING)
# secondary droplets: detach times, launch from finger tips
drops = []
for i in range(N_FING):
    for j in range(rng.integers(1, 3)):
        td = rng.uniform(0.004, 0.011)
        drops.append(dict(i=i, td=td, vr=rng.uniform(0.35, 0.9), vz=rng.uniform(0.35, 1.05), r=rng.uniform(0.00016, 0.00036),
                          dphi=rng.normal(0, 0.05)))
# fine mist from the first lamella jet
for k in range(26):
    drops.append(dict(i=-1, td=rng.uniform(0.0006, 0.002), vr=rng.uniform(1.0, 1.8), vz=rng.uniform(0.25, 0.7),
                      r=rng.uniform(0.00008, 0.00014), dphi=rng.uniform(0, 2 * np.pi)))


def crown(t):
    Rc = 0.0013 + 0.0048 * math.sqrt(t / 0.010)
    Hc = 0.0046 * (t / 0.007) * math.exp(1 - t / 0.007)
    return Rc, Hc


def build(t):
    for ob in [o for o in sc.objects if o.name.startswith('S_')]:
        bpy.data.objects.remove(ob, do_unlink=True)
    Rc, Hc = crown(t)
    bm = bmesh.new()
    if Hc > 0.0003:
        nseg, nh = 96, 14
        rows = []
        for k in range(nh + 1):
            s = k / nh
            ring = []
            for m in range(nseg):
                phi = 2 * math.pi * m / nseg
                flare = 1 + 0.35 * s * s                                  # crown opens outward
                fing = sum(max(0.0, math.cos(N_FING / 2 * (phi - fing_phase[i]) ) ) ** 12 * fing_len[i] for i in range(0, 1))
                tip = 0.0
                for i in range(N_FING):
                    d = (phi - 2 * math.pi * i / N_FING - 0.2 * math.sin(fing_phase[i]) + math.pi) % (2 * math.pi) - math.pi
                    tip += fing_len[i] * math.exp(-(d / 0.07) ** 2)
                h = Hc * s * (1 + 0.45 * tip * s ** 3 * min(1.0, t / 0.006))
                r = Rc * flare * (1 + 0.08 * tip * s ** 2)
                ring.append(bm.verts.new((r * math.cos(phi), r * math.sin(phi), h)))
            rows.append(ring)
        for k in range(nh):
            for m in range(nseg):
                bm.faces.new((rows[k][m], rows[k][(m + 1) % nseg], rows[k + 1][(m + 1) % nseg], rows[k + 1][m]))
        me = bpy.data.meshes.new('S_crown'); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new('S_crown', me); sc.collection.objects.link(ob); me.materials.append(water)
        mod = ob.modifiers.new('sol', 'SOLIDIFY'); mod.thickness = 0.00012
        for p in me.polygons: p.use_smooth = True
        # rim torus
        bpy.ops.mesh.primitive_torus_add(major_radius=Rc * 1.35, minor_radius=0.00018 + 0.0001 * min(1, t / 0.006),
                                         location=(0, 0, Hc), major_segments=96, minor_segments=10)
        tor = bpy.context.object; tor.name = 'S_rim'; tor.data.materials.append(water)
        for p in tor.data.polygons: p.use_smooth = True
    # droplets (ellipsoids stretched along velocity = 1/400 s persistence)
    for d in drops:
        if t < d['td']:
            continue
        tt = t - d['td']
        if d['i'] >= 0:
            phi = 2 * math.pi * d['i'] / N_FING - 0.2 * math.sin(fing_phase[d['i']]) + d['dphi']
            Rc0, Hc0 = crown(d['td'])
            p0 = Vector((Rc0 * 1.4 * math.cos(phi), Rc0 * 1.4 * math.sin(phi), Hc0 * 1.3))
        else:
            phi = d['dphi']; p0 = Vector((0.0012 * math.cos(phi), 0.0012 * math.sin(phi), 0.0002))
        vel = Vector((d['vr'] * math.cos(phi), d['vr'] * math.sin(phi), d['vz'] - 9.81 * tt))
        p = p0 + Vector((d['vr'] * math.cos(phi) * tt, d['vr'] * math.sin(phi) * tt, d['vz'] * tt - 4.905 * tt * tt))
        if p.z < -0.0001:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(radius=d['r'], location=p, segments=16, ring_count=8)
        s = bpy.context.object; s.name = 'S_d'; s.data.materials.append(water)
        stretch = 1 + vel.length * 0.0025 / (2 * d['r'])
        s.scale = (1, 1, min(stretch, 6))
        s.rotation_mode = 'QUATERNION'
        s.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(vel.normalized())
        for pp in s.data.polygons: pp.use_smooth = True


times = [0.032 * (k / (FR - 1)) ** 1.3 + 0.0005 for k in range(FR)]
for k, t in enumerate(times):
    build(t)
    sc.render.filepath = os.path.join(OUT, 'splash_frames', 'f%02d.exr' % k)
    bpy.ops.render.render(write_still=True)
    print('frame', k, 't_ms %.1f' % (t * 1e3), flush=True)
