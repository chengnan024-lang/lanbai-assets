# -*- coding: utf-8 -*-
"""Sea-kit lookdev scene for the render harness (Engineering/render_harness, pkg/engineering).
  ~/bpy/bin/python <harness>/lbh_render.py --scene Sea/Docs~/lookdev/scene_kit.py --cam hero --set frame=K2 --pitch 60 \
      --grade S7a --act 07a --t 367.21 --out /tmp/sea/K2_r01 --note "..."
The exterior (sea, sky, fog, sun disc) is computed for the EXACT harness camera with Sea/Tools~/sea_numpy.py (= the
shader's maths) and fed to Blender as a world background seen by camera rays only, mapped in window space; the bus shell
of the harness occludes it. Frames K1..K5: Sea/Docs~/lookdev_brief.md. Extra knobs: --set k=v (see FRAMES[...] keys)."""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..', '..'))
REPO = os.path.dirname(KIT)
sys.path.insert(0, os.path.join(KIT, 'Tools~'))
sys.path.insert(0, os.path.join(REPO, 'Act07_Sea', 'Tools~'))
import sea_numpy as S  # noqa: E402
import act07_motion as AM  # noqa: E402

HD = os.path.join(REPO, 'FromLocal', 'hdri', 'hdr')


def lin(h, ev=0.0):
    c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4) * 2.0 ** ev


def dir_az_el(az, el):
    az, el = math.radians(az), math.radians(el)
    return np.array([math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az)])


_ENV = {}
_SYNTH = {}


def env_dawn():
    if 'dawn' not in _ENV:
        h = S.read_hdr(os.path.join(HD, 'syferfontein_6d_clear_puresky_1k.hdr'))
        e = S.equirect_from_hdr(h, 45.0)
        env = S.Env(e)
        k = float(lin('#5B7ED7') @ [0.2126, 0.7152, 0.0722]) / float(env.lookup(np.array([[0.0, 1.0, 0.0]]))[0] @ [0.2126, 0.7152, 0.0722])
        _ENV['dawn'] = S.Env(S.clamp_max_channel(e * k, 16.0))
    return _ENV['dawn']


def env_dusk_synth(kind):
    """the bible's 8-i dusk sky as fills (§6·8 大气 / 色板): sun band #FFB070, rose band (back to the sun) fill #FF9396 @ +0.92,
    mid-sky fill #92A3DF, zenith fill #4B5997; 'lower' = the other sky (-x, -y, z) x 0.82 x (0.92, 0.95, 1.05), 'upper' = below the
    horizon the horizon colour fading to the other-sky nadir fill #3B4A78. Sun: az 0, el +0.5, 0.9 deg, fill #FF9167 @ +2.74."""
    key = 'synth_' + kind
    if key in _ENV:
        return _ENV[key]
    H, W = 512, 1024
    lat = (np.arange(H) + 0.5) / H * np.pi - np.pi / 2
    lon = (np.arange(W) + 0.5) / W * 2 * np.pi - np.pi
    LON, LAT = np.meshgrid(lon, lat)
    sun_band, rose = lin('#FFB070', 0.9), lin('#FF9396', 0.92)
    mid, zen, nadir = lin('#92A3DF'), lin('#4B5997'), lin('#3B4A78')

    def sky(lo, la):
        el = np.degrees(la)[..., None]
        towards = (0.5 + 0.5 * np.cos(lo))[..., None] ** 3                      # 1 at the sun's azimuth
        hor = rose + (sun_band - rose) * towards
        glow = lin('#FF855C', 1.37) * (np.exp(-np.abs(el) / 2.0) * towards ** 4)  # the bright slot at the sun (天缝 #F2A56B)
        c = np.where(el < 25, hor + (mid - hor) * S.smoothstep(0.0, 25.0, el), mid + (zen - mid) * S.smoothstep(25.0, 90.0, el))
        return c + glow
    up = sky(LON, np.maximum(LAT, 0.0))
    if kind == 'lower':
        mir = sky(-LON, np.maximum(-LAT, 0.0)) * np.array([0.92, 0.95, 1.05]) * 0.82
        w = S.smoothstep(0.0, math.radians(1.0), -LAT)[..., None]
        out = up * (1 - w) + mir * w
    else:
        hz = sky(LON, np.zeros_like(LAT))
        w = S.smoothstep(0.0, math.radians(float(_SYNTH.get('below_deg', 5.0))), -LAT)[..., None]
        out = np.where(LAT[..., None] >= 0, up, hz * (1 - w) + nadir * w)
    d = np.stack([np.cos(LAT) * np.sin(LON), np.sin(LAT), np.cos(LAT) * np.cos(LON)], -1)
    sunc = lin('#FF9167', 2.74)
    for el, g in ((0.5, 1.0), (-0.5, 0.82 if kind == 'lower' else 0.0)):
        if g:
            ang = np.degrees(np.arccos(np.clip(d @ dir_az_el(0.0, el), -1, 1)))
            out = out + sunc[None, None, :] * g * (1.0 - S.smoothstep(0.42, 0.48, ang))[..., None]
    _ENV[key] = S.Env(S.clamp_max_channel(out, 16.0))
    return _ENV[key]


def env_dusk(kind):
    key = 'dusk_' + kind
    if key not in _ENV:
        h = S.read_hdr(os.path.join(HD, 'syferfontein_0d_clear_puresky_1k.hdr'))
        e = S.equirect_from_hdr(h, 0.0)
        base = S.Env(e)
        k = float(lin('#4B5997') @ [0.2126, 0.7152, 0.0722]) / float(base.lookup(np.array([[0.0, 1.0, 0.0]]))[0] @ [0.2126, 0.7152, 0.0722])
        H, W = e.shape[:2]
        lat = (np.arange(H) + 0.5) / H * np.pi - np.pi / 2
        lon = (np.arange(W) + 0.5) / W * 2 * np.pi - np.pi
        LON, LAT = np.meshgrid(lon, lat)
        d = np.stack([np.cos(LAT) * np.sin(LON), np.sin(LAT), np.cos(LAT) * np.cos(LON)], -1)
        up = e * k
        if kind == 'lower':                     # the 'other sky' below: (-x, -y, z) x 0.82 x tint (bible 8-ii)
            mir = base.lookup(d * np.array([-1.0, -1.0, 1.0])) * k * np.array([0.92, 0.95, 1.05]) * 0.82
            w = S.smoothstep(0.0, math.sin(math.radians(1.0)), -d[..., 1:2])
            out = up * (1 - w) + mir * w
        else:                                   # 8-i below the horizon: horizon colour -> nadir #3B4A78 (fill)
            hor = base.lookup(S.normalize(d * np.array([1.0, 0.0, 1.0]) + np.array([0.0, 0.02, 0.0]))) * k
            w = S.smoothstep(0.0, 1.0, -d[..., 1:2])
            out = np.where(d[..., 1:2] >= 0, up, hor * (1 - w) + lin('#3B4A78') * w)
        # the bible's procedural sun (8: az 0, el +0.5, 0.9 deg, fill #FF9167 @ +2.74) and, below, its other self
        sunc = lin('#FF9167', 2.74)
        for el, g in ((0.5, 1.0), (-0.5, 0.82 if kind == 'lower' else 0.0)):
            if g <= 0:
                continue
            c = np.clip(d @ dir_az_el(0.0, el), -1, 1)
            ang = np.degrees(np.arccos(c))
            out = out + sunc[None, None, :] * g * (1.0 - S.smoothstep(0.42, 0.48, ang))[..., None]
        _ENV[key] = S.Env(S.clamp_max_channel(out, 16.0).astype(np.float32))
    return _ENV[key]


def env_lamps_above(points, base_rgb):
    """an 'up' environment for 7c's dark mirror: rose-dark water + the palace lamps (gaussian points, warm)"""
    H, W = 1024, 2048
    lat = (np.arange(H) + 0.5) / H * np.pi - np.pi / 2
    lon = (np.arange(W) + 0.5) / W * 2 * np.pi - np.pi
    LON, LAT = np.meshgrid(lon, lat)
    d = np.stack([np.cos(LAT) * np.sin(LON), np.sin(LAT), np.cos(LAT) * np.cos(LON)], -1)
    out = np.broadcast_to(np.asarray(base_rgb, np.float32), d.shape).copy()
    for p, gain in points:
        c = np.clip(d @ S.normalize(np.asarray(p, float)), -1, 1)
        ang = np.degrees(np.arccos(c))
        out += (lin('#FF5E2A', 3.11) * gain)[None, None, :] * np.exp(-(ang / float(_SYNTH.get('lamp_deg', 0.8))) ** 2)[..., None]
    return S.Env(out.astype(np.float32))


def sun_disc(rays, sdir, rgb, deg=0.9):
    c = rays @ S.normalize(sdir)
    ang = np.degrees(np.arccos(np.clip(c, -1, 1)))
    return np.asarray(rgb)[None, None, :] * (1.0 - S.smoothstep(deg / 2 - 0.03, deg / 2 + 0.03, ang))[..., None]


def horizon_fog_fn(env):
    def fn(d):
        dh = S.normalize(d * np.array([1.0, 0.0, 1.0]) + np.array([0.0, 0.03, 0.0]))
        return env.lookup(dh)
    return fn


# ------------------------------------------------------------------------------------------------------------ frames
def frame_K1(rays, eye, t, a):
    """act 6d sea mirror, ~350 s, eye 70 m above the sea (bible 6d: 352.06 = 53 m; 345.36 = 149 m)"""
    h = float(a.get('height', 70.0))
    env = env_dawn()
    sdir = dir_az_el(45, 6)
    sunc = lin('#FFCE9E', 2.55)
    M = dict(SunColor=tuple(sunc), SunDir=tuple(sdir), CalmAll=float(a.get('calm', 0.85)), SunGlitterRough=float(a.get('glitter', 0.12)), ReflClamp=float(a.get('clamp', sunc.max() * 2 ** -1.3)),
             WaterColor=tuple(lin('#304F7A') * float(a.get('body', 0.55))))
    rgb, alpha, hit, P = S.shade_plane(eye, rays, eye[1] - h, 'above', t, M, env=env)
    sky = env.lookup(rays) + sun_disc(rays, sdir, sunc)
    fogc = lin('#FFE4F0', 0.31)                              # bible §6·6 大气: Exp 0.00012, fill #FFE4F0 @ +0.31
    fog_fn = (lambda d: np.broadcast_to(fogc, d.shape)) if a.get('fogsrc', 'bible') == 'bible' else horizon_fog_fn(env)
    rgb = S.fog(rgb, P, eye, 0.00012, fog_fn)
    rgb = S.purple_guard(rgb, dict(S.DEFAULTS, **M))
    return np.where(hit[..., None], rgb, sky), dict(sea_level=eye[1] - h, sun_peak=float(sunc.max()))


WATER = dict(up=lin('#294B72'), mid=lin('#77A0D2'), down=(0.0159, 0.0733, 0.1275))   # r03: up = the TIR mirror's fill (bible: '圆盘之外 ... 暗镜 #11395E'), mid = fog 0-15 m, down = dome bottom


def frame_K2(rays, eye, t, a):
    """7a F3: Snell's window from the bus, depth from act07_motion"""
    d_eye = AM.depth(t) - 1.70
    level = eye[1] + d_eye
    M = dict(WindowGain=float(a.get('wgain', 1.0)), WindowTint=tuple(float(x) for x in a.get('wtint', '1,1,1').split(',')),
             TIRColor=tuple(lin('#294B72')), ReflClamp=float(a.get('clamp', 2.4)),
             WindowRadial=tuple(float(x) for x in a.get('wradial', '1,2').split(',')))
    rgb, alpha, hit, P = S.shade_plane(eye, rays, level, 'below', t, M, window_env=env_dawn())
    up = WATER['up'] * float(a.get('fogup', 0.75))
    fog_fn = S.water_horizon(up, WATER['mid'], WATER['down'])
    dens = float(a.get('fog', 0.040))
    rgb = S.fog(rgb, P, eye, dens, fog_fn)
    rgb = S.purple_guard(rgb, dict(S.DEFAULTS, **M))
    return np.where(hit[..., None], rgb, fog_fn(rays)), dict(eye_depth=d_eye, level=level)


def frame_K3(rays, eye, t, a):
    """7c 897.96: the inverted window below the bus; the palace lamps above, reflected in the dark mirror"""
    import json
    plane_depth = AM.depth(AM.EXIT) + 1.70           # the EYE crosses the plane at the exit
    level = eye[1] - (plane_depth - AM.depth(t))
    PF = json.load(open(os.path.join(REPO, 'Act07_Sea', 'PalaceFrame_约定.json'), encoding='utf-8'))
    bus = np.array([0.0, PF['frame']['bus_origin_y_stop'] + (AM.depth(AM.L['F7']) - AM.depth(t)), AM.fwd(t)])
    fade = float(a.get('lampfade', 0.5))             # F8: the constellation dims lamp by lamp
    _SYNTH['lamp_deg'] = float(a.get('lampdeg', 0.8))
    pts = [(np.asarray(L['flame_pos']) - bus, fade) for L in PF['lamps']]
    rg = PF['specks']['region']; rs = np.random.default_rng(7)
    for _ in range(int(a.get('specks', 240))):                 # the drowned city's far lights (PalaceSpecks), dim
        q = np.array([rs.uniform(*rg['x']), rs.uniform(*rg['y']), rs.uniform(*rg['z'])])
        pts.append((q - bus, 0.08 * rs.uniform(0.4, 1.0)))
    fogc = lin('#3E2C2B')
    refl = env_lamps_above(pts, fogc * 0.6)
    sunc = lin(a.get('wsuncol', '#FFB27A'), 2.74) * 0.82 * float(a.get('wsun', 1.0))      # rose-gold, the other sun (x0.82, bible 8-ii)
    M = dict(WindowSunColor=tuple(sunc), WindowSunDir=tuple(dir_az_el(0.0, -float(a.get('wsundip', 3.0)))) + (float(a.get('wsunel', 1.2)),), WindowSunSpread=float(a.get('wsunaz', 14.0)),
             AirSide=-1.0, WindowTint=tuple(float(x) for x in a.get('wtint', '1,1,1').split(',')), WindowGain=float(a.get('wgain', 1.0)), WindowRadial=tuple(float(x) for x in a.get('wradial', '1,2').split(',')), TIRColor=tuple(fogc * 0.5), TIRCubeGain=1.0,
             WaveAmp=float(a.get('wave', 0.3)), ReflClamp=float(a.get('clamp', 8.0)))
    rgb, alpha, hit, P = S.shade_plane(eye, rays, level, 'below', t, M, env=refl, window_env=env_dusk('lower'))
    fog_fn = S.water_horizon(fogc * 1.15, fogc, fogc * 0.9)
    rgb = S.fog(rgb, P, eye, float(a.get('fog', 0.018)), fog_fn)
    rgb = S.purple_guard(rgb, dict(S.DEFAULTS, **M))
    return np.where(hit[..., None], rgb, fog_fn(rays)), dict(level=level)


def frame_K4(rays, eye, t, a):
    """act 8-i: the sea ceiling at height h above the bus; F9b = 148 m"""
    h = float(a.get('h', 148.0))
    sdir = dir_az_el(0.0, 0.5)
    sunc = lin('#FF9167', 2.74)
    M = dict(WaterColor=(0.0116, 0.0296, 0.0683), DiscCenter=(0, 0, 2700, float(a.get('band', 800.0))), NormalStrength=float(a.get('nstr', 0.25)),
             DissolveTime=float(a.get('dissolve', -1.0)), ReflClamp=float(a.get('clamp', 8.0)),
             MirrorTint=tuple(float(x) for x in a.get('mtint', '1,1,1').split(',')), PurpleGuard=(float(a.get('guard', 1.0)), 0.02, 252.0))
    _SYNTH['below_deg'] = a.get('below', 5.0)
    E = env_dusk_synth if a.get('sky', 'synth') == 'synth' else env_dusk
    rgb, alpha, hit, P = S.shade_plane(eye, rays, eye[1] + h, 'ceiling', t, M, env=E('lower'), behind_env=E('upper'))
    sky = S.purple_guard(E('upper').lookup(rays), dict(PurpleGuard=(1.0, 0.02, 252.0)))   # stand-in sky: the bible's other-sky nadir #2E3C66 sits on the violet edge (Sky's call)
    fogc = lin('#DE9692')                                    # bible §6·8 大气: Exp 0.00015, fill #DE9692
    # height falloff (LanbaiFog _FogHeightFalloff, metres): the fog thins above the eye, so the deep-blue water overhead
    # is not tinted by the warm horizon fog (2 % of #DE9692 over #10263F reads violet). Unity: the ceiling material's
    # _FogHeightFalloff = this value (README_Sea §4).
    Hf = float(a.get('fogH', 120.0))
    dy = np.maximum(P[..., 1] - eye[1], 0.0)
    dist = np.linalg.norm(P - eye, axis=-1)
    tau = 0.00015 * dist * np.where(dy > 1e-3, Hf * (1 - np.exp(-dy / Hf)) / np.maximum(dy, 1e-3), 1.0)
    f = (1.0 - np.exp(-tau))[..., None]
    rgb = rgb * (1 - f) + fogc * f
    rgb = S.purple_guard(rgb, dict(S.DEFAULTS, **M))
    # the palace's 20-30 golden points INSIDE the ceiling (bible 8-i), Lanbai/SeaSpecks: 25 lamps 40-200 m above the
    # surface, seen through it (x (1 - F) ~ 0.98 overhead), absorbed by the water (exp(-0.02 d_water)), fading LAST in
    # the dissolve (LanbaiCeilingLampProgress)
    rs = np.random.default_rng(11)
    lampc = lin('#FF5E2A', 3.11)
    spk = np.zeros_like(rgb)
    dmid = M['DissolveTime']
    for _ in range(int(a.get('lamps', 25))):
        q = np.array([rs.uniform(-260, 260), eye[1] + h + rs.uniform(40, 200), rs.uniform(-320, 220)])
        v = q - eye; dist = np.linalg.norm(v); d = v / dist
        dw = (q[1] - eye[1] - h) / max(d[1], 1e-3)
        ang = np.degrees(np.arccos(np.clip(rays @ d, -1, 1)))
        g = float(a.get('lampgain', 0.6)) * np.exp(-0.02 * dw) * np.exp(-(ang / float(a.get('lampdeg', 0.17))) ** 2)
        if dmid >= 0:
            el = math.degrees(math.asin(max(min(d[1], 1.0), 0.0)))
            pp = min(max((dmid - 4.0 * el / 90.0) / 5.0, 0.0), 1.0)
            g = g * (1.0 - min(max((pp - 0.3) / 0.7, 0.0), 1.0))
        spk += lampc[None, None, :] * g[..., None]
    a_ = (alpha * hit)[..., None]
    return (rgb + spk) * a_ + sky * (1 - a_), dict(h=h)


FRAMES = dict(K1=frame_K1, K2=frame_K2, K3=frame_K3, K4=frame_K4)


def _rot(d, yaw, pitch):
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    d = np.array([d[0], d[1] * cp + d[2] * sp, -d[1] * sp + d[2] * cp])
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return np.array([d[0] * cy + d[2] * sy, d[1], -d[0] * sy + d[2] * cy])


def build(ctx):
    a = ctx['args']
    fr = a.get('frame', 'K2')
    cam = ctx['cam']
    W, H = cam['res']
    t = ctx['t'] if ctx['t'] is not None else 367.21
    eye = np.asarray(cam['eye'], np.float64)
    rays = S.camera_rays(W, H, cam['hfov_deg'], cam.get('yaw_deg', 0.0) or 0.0, cam.get('pitch_deg', 0.0) or 0.0)
    img, info = FRAMES[fr](rays, eye, t, a)
    img = np.nan_to_num(np.asarray(img, np.float32), nan=0.0, posinf=64.0)
    print('[scene_kit]', fr, 'exterior mean', img.mean(axis=(0, 1)), 'max', img.max(), info)
    # Blender image (rows bottom-up, RGBA float) on a frustum-filling emissive card 20 km out, visible to camera rays only:
    # through the windows of the bus shell the camera sees exactly the numpy exterior for its own pixel.
    import tempfile
    tmp = bpy.data.images.new('SeaExteriorTmp', W, H, alpha=True, float_buffer=True)
    # (measured: this Blender build hands the float texture to Cycles sRGB-ENCODED whatever colour space is set, 0.19 ->
    #  0.472; so the card gets the inverse (extended sRGB decode) and Cycles sees exactly img. Checked by --set check=1)
    dec = np.where(img <= 0.04045, img / 12.92, ((np.maximum(img, 0) + 0.055) / 1.055) ** 2.4).astype(np.float32)
    tmp.pixels.foreach_set(np.concatenate([np.flipud(dec), np.ones((H, W, 1), np.float32)], -1).ravel())
    path = os.path.join(tempfile.gettempdir(), 'lanbai_sea_exterior_%d.exr' % os.getpid())
    tmp.filepath_raw = path
    tmp.file_format = 'OPEN_EXR'
    tmp.save()
    im = bpy.data.images.load(path)
    im.colorspace_settings.name = 'Linear Rec.709'
    D = 20000.0
    tx = math.tan(math.radians(cam['hfov_deg']) / 2); ty = tx * H / W
    corners = []
    for (u, v) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        d = S.normalize(np.array([u * tx, v * ty, 1.0]))
        d = _rot(d, cam.get('yaw_deg', 0.0) or 0.0, cam.get('pitch_deg', 0.0) or 0.0)
        f = _rot(np.array([0.0, 0.0, 1.0]), cam.get('yaw_deg', 0.0) or 0.0, cam.get('pitch_deg', 0.0) or 0.0)
        corners.append(tuple(eye + d * (D / float(d @ f))))
    LS = ctx['lbh_scene']
    mat = bpy.data.materials.new('SeaExteriorMat'); mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = im; tex.extension = 'EXTEND'; tex.interpolation = 'Closest'
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 1.0
    nt.links.new(tex.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    ob = LS.mesh_object('SeaExterior', corners, [(0, 1, 2, 3)], mat)
    uvl = ob.data.uv_layers.new(name='UVMap')
    for poly in ob.data.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            uvl.data[li].uv = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))[vi]
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        setattr(ob, attr, False)
    info = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in info.items()}
    return dict(what='sea kit %s' % fr, frame=fr, **info)
