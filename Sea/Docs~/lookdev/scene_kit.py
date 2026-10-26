# -*- coding: utf-8 -*-
"""Sea-kit lookdev scene for the render harness (Engineering/render_harness, pkg/engineering).
  ~/bpy/bin/python <harness>/lbh_render.py --scene Sea/Docs~/lookdev/scene_kit.py --cam hero --set frame=K2 --pitch 60 \
      --grade S7a --act 07a --t 367.21 --out /tmp/sea/K2_r01 --note "..."
The exterior (sea, sky, fog, sun disc) is computed for the EXACT harness camera with Sea/Tools~/sea_numpy.py (= the
shader's maths) and fed to Blender as a world background seen by camera rays only, mapped in window space; the bus shell
of the harness occludes it. Frames K1..K5: Sea/Docs~/lookdev_brief.md. Extra knobs: --set k=v (see FRAMES[...] keys)."""
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..', '..'))
REPO = os.path.dirname(KIT)
sys.path.insert(0, os.path.join(KIT, 'Tools~'))  # sea_numpy, grade
sys.path.insert(0, os.path.join(REPO, 'Act07_Sea', 'Tools~'))
import sea_numpy as S  # noqa: E402
import act07_motion as AM  # noqa: E402

HD = os.path.join(REPO, 'FromLocal', 'hdri', 'hdr')
MATS = json.load(open(os.path.join(KIT, 'SeaMaterials.json'), encoding='utf-8'))


def material(name, a=None, **extra):
    """numpy material dict from Sea/SeaMaterials.json (the same numbers the Unity menu writes), then --set M.Key=v,v overrides"""
    ent = [m for m in MATS['materials'] if m['name'] == name][0]
    sets = list(ent['set']); texs = list(ent['tex'])
    if ent.get('ceiling'):
        cc = MATS['ceiling_common']
        sets = cc['set'] + cc[ent['ceiling']] + sets
        texs = cc['tex'] + texs
    M = {}
    for e in sets:
        k = e['k'].lstrip('_')
        ref = S.DEFAULTS.get(k)
        v = e['v']
        M[k] = float(v[0]) if len(v) == 1 else tuple(float(x) for x in (v if ref is None or isinstance(ref, float) or len(ref) >= len(v) else v[:len(ref)]))
    for e in texs:
        if e['k'] == '_PurpleCeiling':
            M['PurpleCeiling'] = 'S11' if e['path'].endswith('_S11.png') else 'main'
    M.update(extra)
    for k, v in (a or {}).items():
        if k.startswith('M.'):
            xs = [float(x) for x in str(v).split(',')]
            M[k[2:]] = xs[0] if len(xs) == 1 else tuple(xs)
    return M


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
        e = S.equirect_from_hdr(h, 30.0)                      # D-12: dawn sun azimuth +30
        env = S.Env(e)
        k = float(lin('#5B7ED7') @ [0.2126, 0.7152, 0.0722]) / float(env.lookup(np.array([[0.0, 1.0, 0.0]]))[0] @ [0.2126, 0.7152, 0.0722])
        _ENV['dawn'] = S.Env(S.clamp_max_channel(e * k, 16.0))
    return _ENV['dawn']


def lower_clouds(LON, LAT):
    """7c (D-23): the other sky below has CLOUDS, so the waves have something to ripple in the inverted window (the
    stand-in for ReflCube_DuskLower until the real dusk HDRI is baked; the bible 8-ii: 'the other sky, other clouds').
    A thin cirrus layer seen from above it: the direction projected on a plane below, streaks stretched across the sun
    line, lit gold toward the sun (#F2A56B family, the slot) and the bible's cloud shadow indigo #363D59 (fill #424B6A)
    away from it. Off within 4 deg of the horizon (act 8's mirror band keeps its look). Returns an ADDED radiance."""
    dep = np.maximum(-LAT, 1e-3)
    u = np.cos(LAT) * np.sin(LON) / np.sin(dep); v = np.cos(LAT) * np.cos(LON) / np.sin(dep)
    n = (np.sin(4.1 * u + 1.2 * v + 0.7) * np.sin(1.1 * v - 0.6 * u + 1.9) * 0.50
         + np.sin(9.3 * u - 2.7 * v + 2.3) * np.sin(2.7 * v + 0.9 * u) * 0.30
         + np.sin(23.0 * u + 6.3 * v + 0.4) * 0.20)
    dens = S.smoothstep(0.18, 0.55, n) * S.smoothstep(math.radians(4.0), math.radians(14.0), dep)
    towards = (0.5 + 0.5 * np.cos(-LON)) ** 2
    lit = lin('#F2A56B', -1.2) * towards[..., None] + lin('#424B6A', -0.6) * (1 - towards)[..., None]
    return lit * (0.55 * dens)[..., None]


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
        mir = mir + (lower_clouds(LON, LAT) if _SYNTH.get('clouds', 1) else 0.0)
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


LAMP_GOLD = {}


def lamp_gold(sid):
    """the palace lamp POINT in the dark (final review #2): screen target gold #E0A860 (h_ab 74) under grade sid, solved
    back to linear (Sea/README_Sea接口.md §2.6). Never the full-flame fill #FF5E2A @ +3.11: dimmed, it shows its red."""
    if sid not in LAMP_GOLD:
        import grade as G
        LAMP_GOLD[sid] = np.asarray(G.fill_for('#E0A860', sid), np.float64)
    return LAMP_GOLD[sid]


def env_lamps_above(points, base_rgb, lamp_rgb, lamp_deg=0.3):
    """an 'up' environment for 7c's dark mirror: the water above + the palace lamps (gaussian points, gold)"""
    H, W = 1024, 2048
    lat = (np.arange(H) + 0.5) / H * np.pi - np.pi / 2
    lon = (np.arange(W) + 0.5) / W * 2 * np.pi - np.pi
    LON, LAT = np.meshgrid(lon, lat)
    d = np.stack([np.cos(LAT) * np.sin(LON), np.sin(LAT), np.cos(LAT) * np.cos(LON)], -1)
    out = np.broadcast_to(np.asarray(base_rgb, np.float32), d.shape).copy()
    out = out * (0.75 + 0.5 * S.smoothstep(-0.2, 0.6, d[..., 1:2]))     # the water above is a little lighter toward the palace
    for p, gain in points:
        c = np.clip(d @ S.normalize(np.asarray(p, float)), -1, 1)
        ang = np.degrees(np.arccos(c))
        out += (np.asarray(lamp_rgb) * gain)[None, None, :] * np.exp(-(ang / lamp_deg) ** 2)[..., None]
    return S.Env(out.astype(np.float32))


def sun_disc(rays, sdir, rgb, deg=0.53):
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
    """act 6d sea mirror, ~350 s, eye 'height' m above the sea (bible 6d: 352.06 = 53 m; 345.36 = 149 m). M_06_Sea."""
    h = float(a.get('height', 70.0))
    env = env_dawn()
    M = material('M_06_Sea', a)
    sdir = np.asarray(M['SunDir'][:3])
    sunc = np.asarray(M['SunColor'][:3])
    rgb, alpha, hit, P = S.shade_plane(eye, rays, eye[1] - h, 'above', t, M, env=env)
    sky = env.lookup(rays) + sun_disc(rays, sdir, sunc)
    fogc = lin('#FFE4F0', 0.31)                              # bible §6·6 大气: Exp 0.00012, fill #FFE4F0 @ +0.31
    fog_fn = (lambda d: np.broadcast_to(fogc, d.shape)) if a.get('fogsrc', 'bible') == 'bible' else horizon_fog_fn(env)
    rgb = S.fog(rgb, P, eye, 0.00012, fog_fn)
    rgb = S.purple_guard(rgb, M)
    return np.where(hit[..., None], rgb, sky), dict(sea_level=eye[1] - h, sun_peak=float(sunc.max()))


WATER_FOGUP = 0.38                  # the driver's _Udon_WaterFogUp = #294B72 x 0.38 (README_Sea接口 §3)
WATER = dict(up=lin('#294B72'), mid=lin('#77A0D2'), down=(0.0159, 0.0733, 0.1275))   # r03: up = the TIR mirror's fill (bible: '圆盘之外 ... 暗镜 #11395E'), mid = fog 0-15 m, down = dome bottom


def frame_K2(rays, eye, t, a):
    """7a F3: Snell's window from the bus, depth from act07_motion. M_07a_SeaSurface; water fog = README_Sea接口 §3"""
    d_eye = AM.depth(t) - 1.70
    level = eye[1] + d_eye
    M = material('M_07a_SeaSurface', a)
    rgb, alpha, hit, P = S.shade_plane(eye, rays, level, 'below', t, M, window_env=env_dawn())
    up = WATER['up'] * float(a.get('fogup', WATER_FOGUP))
    fog_fn = S.water_horizon(up, WATER['mid'], WATER['down'])
    dens = float(a.get('fog', 0.040))
    rgb = S.fog(rgb, P, eye, dens, fog_fn, S.tir_keep(alpha, M))
    rgb = S.purple_guard(rgb, M)
    return np.where(hit[..., None], rgb, fog_fn(rays)), dict(eye_depth=d_eye, level=level)


K3_FOG = dict(up=0.75, mid=1.0, down=1.45)     # 7c water fog around #3E2C2B: darker above, the rose glow from the window below
# r17 (D-23 layering): looking DOWN the fog is a dark neutral (the window's indigo is not drowned in rose), level = the bible's
# rose (#3E2C2B fill), up = x 0.75; the fog thins in 7c (bible F8c '雾在变薄'): 0.010 / m at 897.96 (it was 0.018)
K3_FOG_DOWN = '#383545'
K3_FOG_DENSITY = 0.010


def frame_K3(rays, eye, t, a):
    """7c 897.96 (after F8b): the inverted window below the bus; the palace lamps above, reflected in the dark mirror.
    M_07c_SeaMirror; the window shows the bible's 'other sky' (the synthetic 8-i dusk, mirrored, x 0.82)."""
    plane_depth = AM.depth(AM.EXIT) + 1.70           # the EYE crosses the plane at the exit
    level = eye[1] - (plane_depth - AM.depth(t))
    PF = json.load(open(os.path.join(REPO, 'Act07_Sea', 'PalaceFrame_约定.json'), encoding='utf-8'))
    yb = PF['frame']['bus_origin_y_stop']            # the palace in the bus frame, with the F7 right turn (bus_turn)
    fade = float(a.get('lampfade', 0.5))             # F8: the constellation dims lamp by lamp
    pts = [(AM.palace_to_bus(L['flame_pos'], t, yb), fade) for L in PF['lamps']]
    rg = PF['specks']['region']; rs = np.random.default_rng(7)
    for _ in range(int(a.get('specks', 240))):                 # the drowned city's far lights (PalaceSpecks), dim
        q = np.array([rs.uniform(*rg['x']), rs.uniform(*rg['y']), rs.uniform(*rg['z'])])
        pts.append((AM.palace_to_bus(q, t, yb), float(a.get('speckgain', 0.5)) * rs.uniform(0.4, 1.0)))
    fogc = lin('#3E2C2B')
    refl = env_lamps_above(pts, fogc * 0.6, lamp_gold('S7b') * float(a.get('lampgain', 14.0)), float(a.get('lampdeg', 0.25)))
    M = material('M_07c_SeaMirror', a, TIRColor=tuple(fogc * 0.5))
    rgb, alpha, hit, P = S.shade_plane(eye, rays, level, 'below', t, M, env=refl, window_env=env_dusk_synth('lower'))
    fu, fm, fd = (float(a.get('fog' + k, K3_FOG[k])) for k in ('up', 'mid', 'down'))
    fog_up = lin(a['fogupcol']) if 'fogupcol' in a else fogc * fu
    fog_down = lin(a.get('fogdowncol', K3_FOG_DOWN)) if a.get('fogdowncol', K3_FOG_DOWN) != 'rose' else fogc * fd
    fog_fn = S.water_horizon(fog_up, fogc * fm, fog_down)
    rgb = S.fog(rgb, P, eye, float(a.get('fog', K3_FOG_DENSITY)), fog_fn, S.tir_keep(alpha, M), M.get('FogChroma'))
    rgb = S.purple_guard(rgb, M)
    return np.where(hit[..., None], rgb, fog_fn(rays)), dict(level=level)


def ceiling_points(rays, eye, h, dissolve, a, sid='S8'):
    """the palace's 20-30 golden points INSIDE the ceiling (bible 8-i), as Lanbai/SeaSpecks draws them: 25 lamps 40-200 m
    above the surface, colour = the dark-lamp screen target gold #E0A860 solved under S8 (README_Sea接口 §2.6), dimmed by
    the water they shine through (_WaterAtten rgb: red absorbed most -> cooler, never redder), ADDED on top of the ceiling
    (queue 2995) and fading only by their own progress (LanbaiCeilingLampProgress): 'the palace lamps go last'."""
    rs = np.random.default_rng(11)
    gold = lamp_gold(sid) * float(a.get('lampgain', 12.0))
    att = np.array([0.024, 0.020, 0.017])
    spk = np.zeros(rays.shape)
    for _ in range(int(a.get('lamps', 25))):
        q = np.array([rs.uniform(-260, 260), eye[1] + h + rs.uniform(40, 200), rs.uniform(-320, 220)])
        v = q - eye; dist = np.linalg.norm(v); d = v / dist
        dw = (q[1] - eye[1] - h) / max(d[1], 1e-3)
        ang = np.degrees(np.arccos(np.clip(rays @ d, -1, 1)))
        g = np.exp(-(ang / float(a.get('lampdeg', 0.17))) ** 2)
        if dissolve >= 0:
            el = math.degrees(math.asin(max(min(d[1], 1.0), 0.0)))
            pp = min(max((dissolve - 4.0 * el / 90.0) / 5.0, 0.0), 1.0)
            g = g * (1.0 - min(max((pp - 0.3) / 0.7, 0.0), 1.0))
        spk += (gold * np.exp(-att * dw))[None, None, :] * g[..., None]
    return spk


def frame_K4(rays, eye, t, a):
    """act 8-i: the sea ceiling at height h above the bus; F9b = 148 m. M_08_SeaCeilingEdge's disc alpha over the whole plane
    equals Inner (alpha 1 inside 2.3 km) + Edge (2.3 .. 3.2 km); the dissolve uses M_08_SeaCeilingFade's numbers."""
    h = float(a.get('h', 148.0))
    M = material('M_08_SeaCeilingEdge', a, DissolveTime=float(a.get('dissolve', -1.0)))
    _SYNTH['below_deg'] = a.get('below', 5.0)
    E = env_dusk_synth if a.get('sky', 'synth') == 'synth' else env_dusk
    rgb, alpha, hit, P = S.shade_plane(eye, rays, eye[1] + h, 'ceiling', t, M, env=E('lower'), behind_env=E('upper'))
    sky = S.purple_guard(E('upper').lookup(rays), dict(PurpleMask=(0, 0, 0, 1)))   # stand-in sky (the Sky's call), guarded like the sea
    fogc = lin('#DE9692')                                    # bible §6·8 大气: Exp 0.00015, fill #DE9692
    # height falloff (LanbaiFog _FogHeightFalloff, metres): the fog thins above the eye, so the deep-blue water overhead
    # is not tinted by the warm horizon fog. Unity: the ceiling materials' _FogHeightFalloff (SeaMaterials.json).
    Hf = float(M['FogHeightFalloff']) if 'FogHeightFalloff' in M else 120.0
    dy = np.maximum(P[..., 1] - eye[1], 0.0)
    dist = np.linalg.norm(P - eye, axis=-1)
    tau = 0.00015 * dist * np.where(dy > 1e-3, Hf * (1 - np.exp(-dy / Hf)) / np.maximum(dy, 1e-3), 1.0)
    f = (1.0 - np.exp(-tau))[..., None]
    rgb = rgb * (1 - f) + fogc * f
    rgb = S.purple_guard(rgb, M)
    spk = ceiling_points(rays, eye, h, M['DissolveTime'], a)
    a_ = (alpha * hit)[..., None]
    return rgb * a_ + sky * (1 - a_) + spk, dict(h=h)


def frame_K6(rays, eye, t, a):
    """act 11 (1178-1240 s): the hanging sea 80 m over the night road, M_11_SeaHanging (#0F283C fill, three Gerstner
    swells, the street lamps' GGX glints in Rain's convention). Stand-ins: 8 lamps along the road (x +-6 m, 6 m high,
    every 25 m; sodium, I 15 = E 1.0 on the road 3.9 m below, radius 0.1 m, omni), the night below as a flat dark env.
    --set glints=0 turns the glints off (the frame the bible wants first: for 8-20 s it must read as night sky)."""
    h = float(a.get('h', 80.0))
    M = material('M_11_SeaHanging', a)
    col = tuple(lin('#FFB060'))
    lamps = []
    for i in range(8):
        lamps.append(((6.0 if i % 2 else -6.0, 6.0, -40.0 + 25.0 * i), 15.0, col, 0.1))
    M['Lamps'] = tuple(lamps)
    if a.get('glints', '1') in ('0', 'off'):
        M['LampGlints'] = 0.0
    night = S.Env(np.broadcast_to(lin('#0B0E16').astype(np.float32), (64, 128, 3)).copy())
    rgb, alpha, hit, P = S.shade_plane(eye, rays, eye[1] + h, 'ceiling', t, M, env=night, behind_env=night)
    rgb = S.purple_guard(rgb, M)
    return np.where(hit[..., None], rgb, night.lookup(rays)), dict(h=h, glints=M['LampGlints'])


FRAMES = dict(K1=frame_K1, K2=frame_K2, K3=frame_K3, K4=frame_K4, K6=frame_K6)


def _rot(d, yaw, pitch):
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    d = np.array([d[0], d[1] * cp + d[2] * sp, -d[1] * sp + d[2] * cp])
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return np.array([d[0] * cy + d[2] * sy, d[1], -d[0] * sy + d[2] * cy])


def roof_hole(ctx, el0):
    """7a: the cabin erodes from the skylight's edge, then the roof (bible §4 车厢侵蚀). For the VR APL check
    (final review #5) the bible_v2 shell gets one more 'window': everything above elevation el0, all azimuths."""
    import tempfile
    LS = ctx['lbh_scene']
    J = json.load(open(LS.paths.BUS_JSON, encoding='utf-8'))
    J['presets']['bible_v2']['windows'].append(dict(name='roof_eroded', az=[-180.0, 180.0], el=[el0, 89.9], steps=8))
    tmp = os.path.join(tempfile.gettempdir(), 'lanbai_sea_bus_roofhole_%d.json' % os.getpid())
    json.dump(J, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
    LS.paths.BUS_JSON = tmp


def build(ctx):
    a = ctx['args']
    if 'roofhole' in a:
        roof_hole(ctx, float(a['roofhole']))
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
