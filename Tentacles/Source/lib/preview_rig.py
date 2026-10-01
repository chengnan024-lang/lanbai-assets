"""Shared preview stage for Lanbai assets (art bible v2, scene 4 look).

Moon low at front-left (azimuth -12 deg, elevation +8 deg relative to the view toward the tear),
cold blue rim; the tear is an asymmetric lens of *undyed white* with pale lips, a dusk indigo-violet
halo and a cold luminous haze band on the horizon around it; void above +35 deg; AgX, Cycles + OIDN.

The camera sits on the -Y side and looks toward +Y, where the tear is (tear azimuth = 0).

Usage (inside a bpy script):
    import sys; sys.path.insert(0, LIB_DIR)
    import preview_rig as pr
    pr.setup(samples=96, res=(1600, 900))
    pr.add_tear(center=(0, 0, 40), height=90)
    pr.frame_subject(center=(0, 0, 40), size=80)   # camera looks at subject
    pr.render('/path/out.png')
"""
import math
import bpy
import numpy as np
from mathutils import Vector


def _lin(hexstr):
    """sRGB hex -> linear RGB tuple."""
    h = hexstr.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def _norm(rgb):
    m = max(rgb)
    return tuple(x / m for x in rgb)


# art bible v2, scene 4 (display targets converted to linear; AgX will not reproduce them exactly)
MOON_COLOR = _norm(_lin('#D6E4FF'))       # moonlight
MOON_RIM = _lin('#A9C2FF')
TEAR_CORE = _lin('#F5F2EC')               # undyed white
TEAR_LIP = _lin('#E2E8F3')                # lip fibres
TEAR_GLOW = _lin('#C0B9E4')               # glow just outside the lips
TEAR_HALO = _lin('#5B57A1')               # dusk indigo-violet halo
TEAR_LIGHT = _norm(_lin('#A99DE1'))       # light the tear casts on the tentacles
TEAR_COLOR = TEAR_LIGHT                   # backwards-compatible name
FILL_BELOW = _norm(_lin('#5A6488'))       # cloud-sea bounce, from below
HAZE_NEAR = _lin('#484D63')               # haze band next to the tear
HAZE_FAR = _lin('#2A3041')                # haze band 50 deg away
VOID = _lin('#070A14')                    # sky above +35 deg or beyond 60 deg azimuth
SKY_ZENITH = VOID
SKY_HORIZON = HAZE_FAR

MOON_AZ, MOON_EL = -12.0, 8.0


def _set_enum(obj, prop, *candidates):
    for c in candidates:
        try:
            setattr(obj, prop, c)
            return c
        except (TypeError, ValueError):
            continue
    return None


def setup(samples=96, res=(1600, 900), transparent=False, haze_band=True):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    _set_enum(sc.cycles, 'denoiser', 'OPENIMAGEDENOISE')
    sc.cycles.max_bounces = 8
    sc.cycles.volume_bounces = 4
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    _set_enum(sc.view_settings, 'view_transform', 'AgX')
    _set_enum(sc.view_settings, 'look', 'AgX - Medium High Contrast', 'AgX - Punchy', 'None')
    sc.view_settings.exposure = 0.0
    _world(haze_band)
    _moon()
    return sc


def _world(haze_band=True):
    w = bpy.data.worlds.get('LanbaiNight') or bpy.data.worlds.new('LanbaiNight')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new

    def m(op, a=None, b=None, clamp=False):
        n = N('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        for i, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    def smooth(v, lo, hi, to_lo=0.0, to_hi=1.0):
        n = N('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        n.inputs['From Min'].default_value = lo; n.inputs['From Max'].default_value = hi
        n.inputs['To Min'].default_value = to_lo; n.inputs['To Max'].default_value = to_hi
        L(v, n.inputs['Value'])
        return n.outputs['Result']

    def mix(fac, a, b):
        n = N('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MIX'
        L(fac, n.inputs['Factor'])
        for sock, val in ((n.inputs['A'], a), (n.inputs['B'], b)):
            if isinstance(val, tuple):
                sock.default_value = (*val, 1.0)
            else:
                L(val, sock)
        return n.outputs['Result']

    out = N('ShaderNodeOutputWorld')
    bg = N('ShaderNodeBackground')
    tc = N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs[0])
    x, y, z = sep.outputs['X'], sep.outputs['Y'], sep.outputs['Z']
    el = m('MULTIPLY', m('ARCSINE', z), 180.0 / math.pi)           # elevation in degrees
    az = m('ABSOLUTE', m('MULTIPLY', m('ARCTAN2', x, y), 180.0 / math.pi))  # |azimuth| from +Y

    if haze_band:
        # colour along the band: near the tear -> 50 deg away
        band_col = mix(smooth(az, 0.0, 50.0), HAZE_NEAR, HAZE_FAR)
        # band weight: full within 50 deg azimuth, gone by 60; full 0..15 deg elevation, gone by 35
        w_az = smooth(az, 50.0, 60.0, 1.0, 0.0)
        w_el = smooth(el, 15.0, 35.0, 1.0, 0.0)
        below = smooth(el, -25.0, 0.0, 0.55, 1.0)                   # a little darker below the horizon
        wband = m('MULTIPLY', w_az, w_el)
        sky = mix(wband, VOID, band_col)
        sky_b = N('ShaderNodeMix'); sky_b.data_type = 'RGBA'; sky_b.blend_type = 'MULTIPLY'
        sky_b.inputs['Factor'].default_value = 1.0
        L(sky, sky_b.inputs['A'])
        gb = N('ShaderNodeCombineColor'); L(below, gb.inputs[0]); L(below, gb.inputs[1]); L(below, gb.inputs[2])
        L(gb.outputs[0], sky_b.inputs['B'])
        sky = sky_b.outputs['Result']
    else:
        sky = mix(smooth(z, 0.0, 0.6), SKY_HORIZON, SKY_ZENITH)

    # sparse stars, dimmed inside the haze band (the Milky Way is saved for the star sea)
    vor = N('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 160.0
    _set_enum(vor, 'feature', 'F1')
    L(tc.outputs['Generated'], vor.inputs['Vector'])
    core = smooth(vor.outputs['Distance'], 0.0, 0.09, 1.0, 0.0)
    core = m('POWER', core, 6.0)
    sepc = N('ShaderNodeSeparateColor'); L(vor.outputs['Color'], sepc.inputs[0])
    keep = m('POWER', smooth(sepc.outputs[0], 0.88, 1.0), 2.0)
    stars = m('MULTIPLY', m('MULTIPLY', core, keep), 3.0)
    if haze_band:
        stars = m('MULTIPLY', stars, smooth(el, 10.0, 35.0, 0.15, 1.0))
    add = N('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'
    add.inputs['Factor'].default_value = 1.0
    L(sky, add.inputs['A'])
    sc_ = N('ShaderNodeCombineColor'); L(stars, sc_.inputs[0]); L(stars, sc_.inputs[1]); L(stars, sc_.inputs[2])
    L(sc_.outputs[0], add.inputs['B'])
    L(add.outputs['Result'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    L(bg.outputs[0], out.inputs['Surface'])


def _look_rot(direction):
    """Rotation (euler) so that an object's local -Z points along `direction`."""
    d = Vector(direction).normalized()
    return d.to_track_quat('-Z', 'Y').to_euler()


def _dir_from(az_deg, el_deg):
    """Unit vector pointing toward azimuth/elevation (azimuth 0 = +Y = toward the tear, positive = right/+X)."""
    a, e = math.radians(az_deg), math.radians(el_deg)
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))


def _moon():
    for o in [o for o in bpy.data.objects if o.name.startswith('PR_')]:
        bpy.data.objects.remove(o, do_unlink=True)
    ld = bpy.data.lights.new('PR_Moon', 'SUN')
    ld.color = MOON_COLOR
    ld.energy = 4.0
    ld.angle = math.radians(0.6)
    moon = bpy.data.objects.new('PR_Moon', ld)
    bpy.context.scene.collection.objects.link(moon)
    # the moon hangs low at front-left; its light travels back toward the camera -> cold rims
    moon.rotation_euler = _look_rot(-_dir_from(MOON_AZ, MOON_EL))
    # cloud-sea bounce from below: bellies just readable
    fd = bpy.data.lights.new('PR_Fill', 'SUN')
    fd.color = FILL_BELOW
    fd.energy = 0.35
    fd.use_shadow = False
    fill = bpy.data.objects.new('PR_Fill', fd)
    bpy.context.scene.collection.objects.link(fill)
    fill.rotation_euler = _look_rot((0.0, 0.15, 1.0))


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _noise1d(v, freq, seed):
    """Smooth 1-D value noise in [-0.5, 0.5] sampled at v (array), `freq` cells per unit."""
    rng = np.random.default_rng(seed)
    n = int(np.ceil(freq * 2.5)) + 4
    vals = rng.random(n) - 0.5
    t = (v + 1.25) * freq
    i = np.clip(np.floor(t).astype(int), 0, n - 2)
    f = t - np.floor(t)
    f = f * f * (3 - 2 * f)
    return vals[i] * (1 - f) + vals[i + 1] * f


def _tear_image(hx, hy, res=(1024, 2048), seed=7):
    """Float RGBA emission image for the tear plane. Plane spans u in [-hx, hx] (units of the
    widest half-width) and v in [-hy, hy] (units of the half-height)."""
    W, H = res
    xs = (np.arange(W) + 0.5) / W * 2 - 1
    ys = (np.arange(H) + 0.5) / H * 2 - 1
    X, Y = np.meshgrid(xs, ys)          # Y: -1 bottom .. +1 top (row 0 = bottom, as Blender stores pixels)
    u, v = X * hx, Y * hy
    tilt = math.radians(4.0)
    u, v = u * math.cos(tilt) - v * math.sin(tilt), u * math.sin(tilt) + v * math.cos(tilt)
    v0 = -0.2                            # widest at 40% of the height
    vp = np.where(v > v0, (v - v0) / (1 - v0), (v - v0) / (1 + v0))
    inside_len = np.clip(1.0 - vp ** 2, 0.0, 1.0)
    hw = inside_len ** 0.85              # lens: pointed ends
    us = np.where(u < 0, u / 0.90, u / 1.10)   # 45 / 55 asymmetry
    tear_n = (_noise1d(v, 1.8, seed) * 0.55 + _noise1d(v, 9.0, seed + 1) * 0.16 + _noise1d(v, 31.0, seed + 2) * 0.05)
    d = np.abs(us + tear_n * (0.35 + 0.65 * hw)) / (hw + 1e-3)
    d_s = np.abs(us) / (np.maximum(hw, 0.0) + 0.35)          # smooth distance for the halo
    ends = _smoothstep(1.02, 0.9, np.abs(vp))
    core = _smoothstep(1.0, 0.8, d) * ends
    along = 0.7 + 0.3 * (1 - np.abs(vp))                     # brightest at the widest point
    t_lip = _smoothstep(0.35, 0.95, d)
    col = (np.array(TEAR_CORE)[None, None, :] * (1 - t_lip[..., None]) + np.array(TEAR_LIP)[None, None, :] * t_lip[..., None])
    col = col * (core * along)[..., None] * 2.4
    glow = np.exp(-np.maximum(d - 0.95, 0) * 6.0) * (1 - core) * ends
    col += np.array(TEAR_GLOW)[None, None, :] * glow[..., None] * 1.1
    halo = np.exp(-np.maximum(d_s - 0.8, 0) * 1.1) * (1 - core)
    halo *= _smoothstep(1.0, 0.55, np.abs(X)) * _smoothstep(1.0, 0.5, np.abs(Y))
    col += np.array(TEAR_HALO)[None, None, :] * halo[..., None] * 1.9
    rgba = np.concatenate([col, np.ones((H, W, 1))], axis=2).astype(np.float32)
    return rgba


def add_tear(center, height, width=None, distance_behind=None, strength=18.0):
    """The tear: an asymmetric lens of undyed white behind the subject (+Y side) with pale lips,
    a dusk indigo-violet halo, and the tear light (a shadowless sun from the tear toward the camera)."""
    width = width or height * 0.30
    c = Vector(center)
    dist = distance_behind or height * 0.9
    pos = c + Vector((0, dist, 0))
    HX, HY = 5.0, 1.6
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=pos)
    slit = bpy.context.object
    slit.name = 'PR_Tear'
    slit.scale = (width * 0.5 * HX, height * 0.5 * HY, 1.0)
    slit.rotation_euler = (math.radians(90), 0, 0)
    img = bpy.data.images.new('PR_TearImg', 1024, 2048, alpha=True, float_buffer=True)
    try:
        img.colorspace_settings.name = 'Linear Rec.709'
    except TypeError:
        pass
    img.pixels.foreach_set(_tear_image(HX, HY).ravel() * (strength / 18.0))
    img.pack()
    mat = bpy.data.materials.new('PR_TearMat')
    mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.extension = 'CLIP'
    uv = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(uv.outputs['UV'], tex.inputs['Vector'])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 1.0
    nt.links.new(tex.outputs['Color'], em.inputs['Color'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(tr.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Surface'])
    slit.data.materials.append(mat)
    slit.visible_shadow = False
    # tear light: shadowless sun from the tear toward the camera (E 0.8 x moon)
    tl = bpy.data.lights.new('PR_TearLight', 'SUN')
    tl.color = TEAR_LIGHT
    tl.energy = 3.2 * (strength / 18.0)
    tl.use_shadow = False
    lo = bpy.data.objects.new('PR_TearLight', tl)
    bpy.context.scene.collection.objects.link(lo)
    lo.rotation_euler = _look_rot((0.0, -1.0, -0.12))
    # a soft local glow so surfaces right next to the wound pick up its light
    al = bpy.data.lights.new('PR_TearGlow', 'AREA')
    al.shape = 'ELLIPSE'
    al.size = width * 2.0
    al.size_y = height * 1.2
    al.color = _norm(TEAR_GLOW)
    al.energy = (strength / 18.0) * height * height * 120.0
    go = bpy.data.objects.new('PR_TearGlow', al)
    bpy.context.scene.collection.objects.link(go)
    go.location = pos + Vector((0, -1.0, 0))
    go.rotation_euler = _look_rot((0, -1, 0))
    return slit


def frame_subject(center, size, yaw_deg=0.0, pitch_deg=8.0, lens=35.0, fill=0.8):
    """Place the camera on the -Y side looking at `center`, fitting `size` metres."""
    c = Vector(center)
    cam_data = bpy.data.cameras.get('PR_Cam') or bpy.data.cameras.new('PR_Cam')
    cam_data.lens = lens
    cam_data.clip_start = 0.1
    cam_data.clip_end = 50000
    cam = bpy.data.objects.get('PR_CamObj')
    if cam is None:
        cam = bpy.data.objects.new('PR_CamObj', cam_data)
        bpy.context.scene.collection.objects.link(cam)
    fov = 2 * math.atan(36.0 / 2 / lens)
    dist = (size / fill) / 2 / math.tan(fov / 2)
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    offs = Vector((math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), -math.sin(pitch))) * dist
    cam.location = c + offs
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam
    return cam


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path
