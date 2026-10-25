# -*- coding: utf-8 -*-
"""Act 7a reference frames for the render harness (Engineering/render_harness):
  ~/bpy/bin/python <harness>/lbh_render.py --scene Act07_Sea/Docs~/lookdev/scene_7a.py --cam hero --pitch 60 --t 367.21 \
      --bus bible_v2 --grade S7a --act 07a --interior-ambient 0.0723,0.1351,0.2219 --out ...
Everything comes from Act07_Sea/Act07_Layout.json (the package's single data source) and Sea/SeaMaterials.json; the sea
plane is the Sea kit's numpy port (Sea/Tools~/sea_numpy.py = LanbaiSea.cginc), and the shafts, particles, ridge and warm
point below are numpy copies of Lanbai/SeaShaft, Lanbai/SeaParticles, Lanbai/SeaRidge and Lanbai/SeaSpecks (same
formulas, same JSON numbers). The exterior is put on a frustum card visible to camera rays only (as scene_kit.py), so
the harness's bus shell occludes it.
Knobs (--set k=v): vr=1 (the VR window ceiling, as the driver does in VR: by the cabin erosion), roofhole=EL (an extra
'window' in the shell above elevation EL; roofhole=auto: the erosion of t, README_Act07a §4), M.<prop>=v (a material
override), noparticles=1, noshafts=1."""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.normpath(os.path.join(HERE, '..', '..'))
REPO = os.path.dirname(PKG)
sys.path.insert(0, os.path.join(REPO, 'Sea', 'Tools~'))
sys.path.insert(0, os.path.join(REPO, 'Sea', 'Docs~', 'lookdev'))
sys.path.insert(0, os.path.join(PKG, 'Tools~'))
import sea_numpy as S  # noqa: E402
import scene_kit as SK  # noqa: E402
import act07_motion as AM  # noqa: E402

LAY = json.load(open(os.environ.get('LB_ACT07_LAYOUT', os.path.join(PKG, 'Act07_Layout.json')), encoding='utf-8'))   # env: try a layout variant
U = LAY['unity']
P_LAY = LAY['particles']


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def keys_smooth(t, kt, kv):
    if t <= kt[0]:
        return kv[0]
    for i in range(1, len(kt)):
        if t < kt[i]:
            return kv[i - 1] + (kv[i] - kv[i - 1]) * float(smooth((t - kt[i - 1]) / max(kt[i] - kt[i - 1], 1e-4)))
    return kv[-1]


def water_at(depth):
    W = LAY['water']['keys']
    ds = [k['depth'] for k in W]
    if depth <= ds[0]:
        i, f = 0, 0.0
    elif depth >= ds[-1]:
        i, f = len(ds) - 2, 1.0
    else:
        i = max(j for j in range(len(ds)) if ds[j] <= depth)
        i = min(i, len(ds) - 2)
        f = (depth - ds[i]) / (ds[i + 1] - ds[i])
    lerp = lambda a, b: np.asarray(a) * (1 - f) + np.asarray(b) * f  # noqa: E731
    k0, k1 = W[i], W[i + 1]
    return lerp(k0['density'], k1['density']), lerp(k0['up'], k1['up']), lerp(k0['mid'], k1['mid']), lerp(k0['down'], k1['down'])


def erosion(t):
    return 0.25 * min(max((t - U['erosion_t0']) / (U['erosion_t1'] - U['erosion_t0']), 0.0), 1.0)


# ------------------------------------------------------------------------------------------------ the sea + fog
def keys_lin(t, kt, kv):
    kv = np.asarray(kv, float)
    if t <= kt[0]:
        return kv[0]
    for i in range(1, len(kt)):
        if t < kt[i]:
            return kv[i - 1] + (kv[i] - kv[i - 1]) * (t - kt[i - 1]) / max(kt[i] - kt[i - 1], 1e-4)
    return kv[-1]


_LAMPS = {}


def lamps_env(t, a):
    """7c: what the dark mirror reflects (stand-in for the baked _Udon_ReflCube Refl_S7c): the water above + the palace
    lamps, as the Sea kit's K3 frame builds it (PalaceFrame_约定.json, gold #E0A860 under S7b x 14, 0.25 deg)"""
    key = round(t, 1)
    if key in _LAMPS:
        return _LAMPS[key]
    PF = json.load(open(os.path.join(PKG, 'PalaceFrame_约定.json'), encoding='utf-8'))
    bus = np.array([0.0, PF['frame']['bus_origin_y_stop'] + (AM.depth(AM.L['F7']) - AM.depth(t)), AM.fwd(t)])
    fade = float(a.get('lampfade', 0.5))
    pts = [(np.asarray(L_['flame_pos']) - bus, fade) for L_ in PF['lamps']]
    rg = PF['specks']['region']; rs = np.random.default_rng(7)
    for _ in range(240):
        q = np.array([rs.uniform(*rg['x']), rs.uniform(*rg['y']), rs.uniform(*rg['z'])])
        pts.append((q - bus, 0.5 * rs.uniform(0.4, 1.0)))
    env = SK.env_lamps_above(pts, SK.lin('#3E2C2B') * 0.6, SK.lamp_gold('S7b') * 14.0, 0.25)
    _LAMPS.clear(); _LAMPS[key] = env
    return env


def sea_7c(rays, eye, t, a):
    """7c (README §9): the mirror below (M_07c_SeaMirror at the water y the eye crosses at the exit), the fog by time"""
    depth = AM.depth(t)
    level = depth + U['c7_mirror_y']
    w = float(keys_smooth(t, U['c7_win_t'], U['c7_win_v']))
    M = SK.material('M_07c_SeaMirror', a, TIRColor=tuple(SK.lin('#3E2C2B') * 0.5))
    M['WaveAmp'] = float(keys_smooth(t, U['c7_wave_t'], U['c7_wave_v']))
    M['WindowGain'] = M['WindowGain'] * w
    M['WindowSunGain'] = M['WindowSunGain'] * w
    ft = U['c7_fog_t']
    dens = float(keys_lin(t, ft, U['c7_fog_density']))
    up, mid, down = (keys_lin(t, ft, np.asarray(U['c7_fog_' + k]).reshape(-1, 3)) for k in ('up', 'mid', 'down'))
    rgb, alpha, hit, P = S.shade_plane(eye, rays, level, 'below', t, M, env=lamps_env(t, a), window_env=SK.env_dusk_synth('lower'))
    fog_fn = S.water_horizon(up, mid, down)
    rgb = S.fog(rgb, P, eye, dens, fog_fn, S.tir_keep(alpha, M), M.get('FogChroma'))
    rgb = S.purple_guard(rgb, M)
    dist = np.where(hit, np.linalg.norm(P - eye, axis=-1), np.inf)
    out = np.where(hit[..., None], rgb, fog_fn(rays))
    return out, dist, (dens, fog_fn), depth


def sea_and_water(rays, eye, t, a):
    if t >= U['F8']:
        return sea_7c(rays, eye, t, a)
    depth = AM.depth(t)
    level = depth                                  # the plane's world y (bus origin at 0)
    M = SK.material('M_07a_SeaSurface', a)
    M['WindowGain'] = M['WindowGain'] * keys_smooth(t, U['win_gain_t'], U['win_gain_v'])
    if a.get('vr', '0') == '1':
        s = float(smooth(erosion(t) / 0.25))
        M['WindowCore'] = tuple(np.asarray(U['core_desktop']) * (1 - s) + np.asarray(U['core_vr']) * s)
    dens, up, mid, down = water_at(depth)
    rgb, alpha, hit, P = S.shade_plane(eye, rays, level, 'below', t, M, window_env=SK.env_dawn())
    fog_fn = S.water_horizon(up, mid, down)
    rgb = S.fog(rgb, P, eye, float(dens), fog_fn, S.tir_keep(alpha, M))
    rgb = S.purple_guard(rgb, M)
    dist = np.where(hit, np.linalg.norm(P - eye, axis=-1), np.inf)
    out = np.where(hit[..., None], rgb, fog_fn(rays))
    return out, dist, (float(dens), fog_fn), depth


def fog_amount(dist, dens):
    return 1.0 - np.exp(-dens * dist)


# ------------------------------------------------------------------------------------------------ the ridge (Lanbai/SeaRidge)
def ridge(rays, eye, t, depth, water, zbuf, img):
    R = LAY['ridge']; g = R['grid']
    # D-44 #5 P3: the mesh is the grid turned by yaw about the bus's vertical axis (x' = x cos + z sin, z' = -x sin + z cos);
    # march in the GRID's frame: turn the eye and the rays back (the bus axis is the pivot: the bus point stays put)
    yaw = math.radians(R.get('yaw_deg', 0.0))
    if yaw != 0.0:
        cy, sy = math.cos(yaw), math.sin(yaw)
        pz = -AM.fwd(t)                               # the water origin's z in the bus frame (0 in 7a)

        def back(v, pivot):
            x, z = v[..., 0], v[..., 2] - pivot
            return np.stack([x * cy - z * sy, v[..., 1], x * sy + z * cy + pivot], -1)
        eye = back(np.asarray(eye, float), pz)
        rays = back(rays, 0.0)
    X = np.asarray(R['x']).reshape(g['ny'], g['nz'])
    fwd = AM.fwd(t)

    def hx(yw, zw):
        """the heightfield x(y, z), bilinear (the mesh's triangles, near enough)"""
        fy = np.clip((yw - g['y0']) / g['dy'], 0, g['ny'] - 1.0001); fz = np.clip((zw - g['z0']) / g['dz'], 0, g['nz'] - 1.0001)
        iy, iz = np.floor(fy).astype(int), np.floor(fz).astype(int); ay, az = fy - iy, fz - iz
        return (X[iy, iz] * (1 - ay) * (1 - az) + X[iy + 1, iz] * ay * (1 - az)
                + X[iy, iz + 1] * (1 - ay) * az + X[iy + 1, iz + 1] * ay * az)

    def inb(yw, zw):
        return (yw >= g['y0']) & (yw <= g['y0'] + g['dy'] * (g['ny'] - 1)) & (zw >= g['z0']) & (zw <= g['z0'] + g['dz'] * (g['nz'] - 1))

    # march the ray through the slab x_min .. x_max of the heightfield; the first sample past the surface, then bisect
    dx = rays[..., 0]
    ok = dx > 1e-4
    sa = np.where(ok, (X.min() - eye[0]) / np.maximum(dx, 1e-4), np.inf)
    sb = np.where(ok, (X.max() - eye[0]) / np.maximum(dx, 1e-4), np.inf)
    hit = np.zeros(dx.shape, bool); s_hit = np.full(dx.shape, np.inf)
    lo = np.where(ok, sa, 0.0)
    NST = 96
    for k in range(1, NST + 1):
        sk = np.where(ok, sa + (sb - sa) * k / NST, 0.0)
        P = eye + rays * sk[..., None]
        yw = P[..., 1] - depth; zw = P[..., 2] + fwd
        past = ok & ~hit & inb(yw, zw) & (P[..., 0] >= hx(yw, zw))
        if past.any():
            a, b = lo[past], sk[past]
            r = rays[past]
            for _ in range(10):
                m_ = 0.5 * (a + b)
                Pm = eye + r * m_[:, None]
                inside_ = Pm[:, 0] >= hx(Pm[:, 1] - depth, Pm[:, 2] + fwd)
                b = np.where(inside_, m_, b); a = np.where(inside_, a, m_)
            s_hit[past] = b
            hit |= past
        lo = np.where(hit, lo, sk)
    s = s_hit
    inside = hit & (s < zbuf)
    if not inside.any():
        return img, zbuf
    P = eye + rays * np.where(inside, s, 0.0)[..., None]
    yw = P[..., 1] - depth; zw = P[..., 2] + fwd
    # the normal of the bilinear surface x = h(y, z): (-1, dh/dy, dh/dz), central differences (smooth, like the mesh normals)
    e = 0.35
    gy = (hx(yw + e, zw) - hx(yw - e, zw)) / (2 * e); gz = (hx(yw, zw + e) - hx(yw, zw - e)) / (2 * e)
    N = S.normalize(np.stack([-np.ones_like(yw), gy, gz], -1))
    m = LAY['ridge']['material']
    bus = np.array([0.0, 1.2, 0.0])
    toBus = bus - P
    dd = np.linalg.norm(toBus, axis=-1)
    facing = np.clip((np.sum(N * toBus, -1) / np.maximum(dd, 1e-3) + m['rim_wrap']) / (1.0 + m['rim_wrap']), 0, 1)
    V = S.normalize(eye - P)
    edge = (1.0 - np.clip(np.sum(N * V, -1), 0, 1)) ** m['rim_edge']
    gain = 1.0 if t >= U['F4'] else 0.0
    fall = np.exp(-np.maximum(dd - m['rim_near_m'], 0.0) / m['rim_reach_m'])
    rim = facing * fall * (m['rim_face'] + (1.0 - m['rim_face']) * edge) * gain
    col = np.asarray(m['base']) + np.asarray(m['rim']) * rim[..., None]
    dens, fog_fn = water
    f = fog_amount(np.linalg.norm(P - eye, axis=-1), dens)[..., None]
    col = col * (1 - f) + fog_fn(rays) * f
    img = np.where(inside[..., None], col, img)
    zbuf = np.where(inside, s, zbuf)
    return img, zbuf


# ------------------------------------------------------------------------------------------------ shafts (Lanbai/SeaShaft)
_STREAKS = {}


def streaks():
    if 'a' not in _STREAKS:
        from PIL import Image
        im = np.asarray(Image.open(os.path.join(REPO, 'Sea', 'Textures', 'ShaftStreaks_256.png')).convert('RGB'), np.float64) / 255.0
        _STREAKS['a'] = np.flipud(im)
    return _STREAKS['a']


def tex_repeat(im, u, v):
    h, w = im.shape[:2]
    x = (np.floor(u * w).astype(int)) % w; y = (np.floor(v * h).astype(int)) % h
    return im[y, x]


def one_shaft(rays, eye, c, axis, hw, length, seed, alpha, gain, t, water, zbuf, colour):
    toEye = eye - c
    side = np.cross(axis, toEye); sl = np.linalg.norm(side)
    side = side / sl if sl > 1e-4 else np.array([1.0, 0.0, 0.0])
    n = S.normalize(np.cross(axis, side)[None, :])[0]
    dn = rays @ n
    s = np.where(np.abs(dn) > 1e-5, ((c - eye) @ n) / np.where(np.abs(dn) > 1e-5, dn, 1.0), -1.0)
    ok = (s > 0) & (s < zbuf)
    P = eye + rays * np.maximum(s, 0)[..., None]
    across = ((P - c) @ side) / hw
    along = ((P - c) @ axis) / length + 0.5
    ok &= (np.abs(across) <= 1) & (along >= 0) & (along <= 1)
    if not ok.any():
        return 0.0
    prof = (1 - across ** 2) ** 2
    ends = smooth(along / 0.18) * (1 - smooth((along - 0.55) / 0.45))
    st_im = streaks()
    su = across * 0.5 + 0.5 + seed * 7.13
    sv = along * 0.15
    stc = tex_repeat(st_im, su + 0.020 * t, sv)[..., 0] * 0.7 + tex_repeat(st_im, su * 1.7 - 0.035 * t, sv)[..., 1] * 0.6
    edgeon = min(1.0, float(np.linalg.norm(np.cross(axis, toEye / max(np.linalg.norm(toEye), 1e-6)))) * 1.25) ** 1.5
    aa = alpha * prof * ends * (0.35 + stc) * edgeon * gain
    near = np.clip((np.linalg.norm(P - eye, axis=-1) - 0.3) / 0.7, 0, 1)
    dens, _ = water
    fa = fog_amount(np.linalg.norm(P - eye, axis=-1), dens)
    aa = aa * near * (1.0 - 0.6 * fa)
    return np.where(ok, aa, 0.0)[..., None] * np.asarray(colour)[None, None, :]


def shafts(rays, eye, t, depth, water, zbuf):
    out = np.zeros(rays.shape)
    under = t >= U['eye_under']
    g = 1 - min(max((depth - U['shaft_depth_full']) / (U['shaft_depth_gone'] - U['shaft_depth_full']), 0), 1)
    gather = float(smooth((t - U['gather_t0']) / (U['gather_t1'] - U['gather_t0'])))
    if t > U['gather_t0']:
        g = g + (1 - g) * gather                 # they gather and come back up: F4p is their brightest
    if t > U['gather_t1']:
        g *= 1 - float(smooth((t - U['gather_t1']) / (U['shafts_gone_t'] - U['gather_t1'])))
    col = U['shaft_colour']
    if under and g > 1e-3:
        Rsea = np.array([0.0, depth, -AM.fwd(t)])
        gp_obj = np.asarray(U['gather_point_bus']) - Rsea
        for i in range(len(U['shaft_half_width'])):
            c = np.asarray(U['shaft_centre'][3 * i:3 * i + 3])
            gg = gp_obj + (c - gp_obj) * 0.12
            c = c + (gg - c) * gather
            out = out + one_shaft(rays, eye, c + Rsea, np.asarray(U['shaft_axis'][3 * i:3 * i + 3]), U['shaft_half_width'][i], U['shaft_length'][i],
                                  U['shaft_seed'][i], U['shaft_alpha'][i], g, t, water, zbuf, col)
    u = t - U['last_t0']; tot = U['last_in'] + U['last_sweep'] + U['last_out']
    if 0 < u < tot:
        aa = float(smooth(u / U['last_in']) * (1 - smooth((u - U['last_in'] - U['last_sweep']) / U['last_out'])))
        sw = float(smooth((u - U['last_in'] * 0.5) / (U['last_sweep'] + U['last_in'])))
        c = np.asarray(U['last_from']) * (1 - sw) + np.asarray(U['last_to']) * sw
        foot = np.asarray(U['last_target']) * (1 - sw) + np.asarray(U['last_target_to']) * sw
        ax = S.normalize((foot - c)[None, :])[0]
        c = c + ax * (0.5 * U['last_length'] - U['last_top'])      # the quad's centre (its top is last_top above the moving point)
        out = out + one_shaft(rays, eye, c, ax, U['last_half_width'], U['last_length'], 0.37, U['last_alpha'], aa, t, water, zbuf, col)
    return out


# ------------------------------------------------------------------------------------------------ particles (Lanbai/SeaParticles)
def hash11(x):
    return np.modf(np.sin(x * 127.1 + 311.7) * 43758.5453)[0] % 1.0


def splat(img_add, img_over, rays_shape, cam, eye, P, radius, rgb, alpha, kind, water, zbuf, min_px=None):
    """project point sprites (shader: quad facing the centre eye, inflated to min_px, coverage^2 energy) and accumulate.
    additive kinds: img_add += rgb * shape * cov^2 * (1 - fog); premultiplied: over-composite (in depth order, far first)."""
    H, W = rays_shape[:2]
    yaw, pitch = math.radians(cam.get('yaw_deg', 0.0) or 0.0), math.radians(cam.get('pitch_deg', 0.0) or 0.0)
    tx = math.tan(math.radians(cam['hfov_deg']) / 2); ty = tx * H / W
    f_px = (W / 2) / tx
    pix_ang = 2 * tx / W
    v = P - eye
    # world -> camera (inverse of SK._rot: yaw then pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    x1 = v[:, 0] * cy - v[:, 2] * sy; z1 = v[:, 0] * sy + v[:, 2] * cy; y1 = v[:, 1]
    cp, sp = math.cos(pitch), math.sin(pitch)
    yc = y1 * cp - z1 * sp; zc = y1 * sp + z1 * cp; xc = x1
    vis = zc > 0.05
    dist = np.linalg.norm(v, axis=-1)
    u = W / 2 + xc / np.maximum(zc, 1e-6) * f_px
    vv = H / 2 - yc / np.maximum(zc, 1e-6) * f_px
    if min_px is None:
        min_px = P_LAY['min_px']
    rmin = 0.5 * min_px * pix_ang * dist
    rdraw = np.maximum(radius, rmin)
    cov = radius / np.maximum(rdraw, 1e-6)
    rpx = rdraw / np.maximum(zc, 1e-6) * f_px
    dens, fog_fn = water
    fa = fog_amount(dist, dens)
    near = np.clip((dist - 0.3) / 0.5, 0, 1)
    order = np.argsort(-dist)
    for i in order:
        if not vis[i] or alpha[i] <= 0 or (rgb[i].max() <= 0 and kind != 'SNOW'):
            continue
        r = max(rpx[i], 0.5)
        x0, x1_ = int(math.floor(u[i] - r)), int(math.ceil(u[i] + r)); y0, y1_ = int(math.floor(vv[i] - r)), int(math.ceil(vv[i] + r))
        if x1_ < 0 or y1_ < 0 or x0 >= W or y0 >= H:
            continue
        xs = np.arange(max(x0, 0), min(x1_ + 1, W)); ys = np.arange(max(y0, 0), min(y1_ + 1, H))
        if len(xs) == 0 or len(ys) == 0:
            continue
        XX, YY = np.meshgrid(xs + 0.5, ys + 0.5)
        r2 = ((XX - u[i]) ** 2 + (YY - vv[i]) ** 2) / (r * r)
        if kind == 'SNOW':
            shape = np.exp(-r2 * 3.0) * (1 - r2)
        elif kind == 'SPECK':
            shape = np.exp(-r2 * 5.5) * (1 - r2)
        else:
            shape = np.exp(-r2 * 9.0) + 0.18 * np.exp(-r2 * 2.0) * (1 - r2)
        shape = np.where(r2 <= 1, shape, 0.0)
        # depth test against the sea / ridge (sprites behind the plane are hidden)
        zt = zbuf[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
        shape = np.where(dist[i] < zt, shape, 0.0)
        if kind in ('SEED', 'TRAIL', 'SPECK'):
            k = (alpha[i] * cov[i] ** 2 * near[i] * (1 - (fa[i] if kind != 'SPECK' else 0.0)))
            img_add[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1] += shape[..., None] * (rgb[i] * k)[None, None, :]
        else:
            aa = alpha[i] * cov[i] ** 2 * near[i] * shape
            c = rgb[i] * (1 - fa[i]) + fog_fn(S.normalize(v[i:i + 1]))[0] * fa[i]
            sub = img_over[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
            img_over[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1] = sub * (1 - aa[..., None]) + (c * aa[..., None])
    return img_add, img_over


def particles(img, rays, cam, eye, t, depth, water, zbuf):
    P_ = LAY['particles']
    busw = np.array([0.0, -depth, AM.fwd(t)])
    add = np.zeros(img.shape)
    under = t >= U['eye_under']
    if under:
        Sn = P_['snow']
        pw = np.asarray(Sn['positions']).reshape(-1, 3) - np.array([0.0, P_['snow_sink'] * t, 0.0])
        d = pw - busw
        bx, sph = U['snow_box'], U['snow_sphere']
        rel = (np.modf(d / bx + 0.5)[0] % 1.0 - 0.5) * bx
        a = np.asarray(Sn['alpha']) * (1 - smooth((np.linalg.norm(rel, axis=-1) - 0.8 * sph) / (0.2 * sph)))
        lit = U['snow_lit_deep'] + (U['snow_lit'] - U['snow_lit_deep']) * (1.0 - float(smooth((depth - U['snow_lit_d0']) / (U['snow_lit_d1'] - U['snow_lit_d0']))))
        rgb = np.tile(np.asarray(Sn['colour']) * lit, (len(a), 1))
        add, img = splat(add, img, rays.shape, cam, eye, rel, np.asarray(Sn['radius']), rgb, a, 'SNOW', water, zbuf)
    if t >= U['F3i'] - 0.1:
        Sd = P_['seeds']
        rel = np.asarray(Sd['positions']).reshape(-1, 3) - busw
        age = t - np.asarray(Sd['birth_t'])
        flash = np.exp(-np.maximum(age, 0) / 0.1)
        st = np.asarray(Sd['steady'])
        bright = np.where(age < 0, 0.0, st + 7.0 * st * flash)
        rgb = np.asarray(Sd['colour'])[None, :] * bright[:, None]
        add, img = splat(add, img, rays.shape, cam, eye, rel, np.asarray(Sd['radius']), rgb, np.ones(len(bright)), 'SEED', water, zbuf)
    if t >= U['F4']:
        f0, f1 = U['trails_front_fade']
        sets = [(P_['trails'], 1.0 - float(smooth((t - U['F8b']) / 20.0))),       # the sides: fade as the 7c rose comes up
                (P_.get('trails_front'), 1.0 - float(smooth((t - f0) / (f1 - f0))))]  # the front (D-44 #5 P5): out before F5
        for Tr, tg in sets:
            if Tr is None or tg <= 0.0:
                continue
            period = Tr['pool'] / Tr['rate']
            ph = np.asarray(Tr['phase']); life = np.asarray(Tr['life']); seed = np.asarray(Tr['seed'])
            x = (t - Tr['T0']) / period - ph
            cyc = np.floor(x); age = (x - cyc) * period
            alive = (t >= Tr['T0'] + ph * period).astype(float)
            h = hash11(seed * 91.7 + cyc * 1.31)
            jit = (np.stack([hash11(h * 13.1), hash11(h * 17.9), hash11(h * 23.3)], -1) - 0.5) * 0.25
            vel = np.array([0.0, -AM.SINK.v(t), AM.FWD.v(t) if t > AM.FWD.T0 else 0.0])
            rel = np.asarray(Tr['positions']).reshape(-1, 3) + jit - vel[None, :] * age[:, None] + np.array([0.0, 0.02, 0.0]) * age[:, None]
            uu = age / np.maximum(life, 1e-3)
            bright = alive * np.where(age < life, smooth(uu / 0.08) * (1 - smooth((uu - 0.35) / 0.65)), 0.0)
            rgb = np.asarray(Tr['colour'])[None, :] * (bright * tg)[:, None]
            add, img = splat(add, img, rays.shape, cam, eye, rel, np.asarray(Tr['radius']), rgb, np.ones(len(bright)), 'TRAIL', water, zbuf)
    if t >= U['F5'] - 0.01:
        g = float(smooth((t - U['F5']) / U['warm_fade']))
        p = np.asarray(U['warm_position']) - busw
        dist = np.linalg.norm(p - eye)
        k = U['warm_flux'] * g * math.exp(-dist * 0.004)
        rgb = (np.asarray(U['warm_colour']) * k)[None, :]
        add, img = splat(add, img, rays.shape, cam, eye, p[None, :], np.array([U['warm_radius']]), rgb, np.ones(1), 'SPECK', water, zbuf, min_px=1.5)
        rgbh = (np.asarray(U['warm_colour']) * U['warm_halo_flux'] * g * math.exp(-dist * 0.004))[None, :]
        add, img = splat(add, img, rays.shape, cam, eye, p[None, :], np.array([U['warm_halo_radius']]), rgbh, np.ones(1), 'SPECK', water, zbuf, min_px=1.5)
    return img + add


# ------------------------------------------------------------------------------------------------ build
def frame(rays, eye, t, a, cam):
    img, zbuf, water, depth = sea_and_water(rays, eye, t, a)
    img, zbuf = ridge(rays, eye, t, depth, water, zbuf, img)
    if a.get('noshafts', '0') != '1':
        img = img + shafts(rays, eye, t, depth, water, zbuf)
    if a.get('noparticles', '0') != '1':
        img = particles(img, rays, cam, eye, t, depth, water, zbuf)
    return img, dict(depth=round(depth, 2), fog=round(water[0], 4), erosion=round(erosion(t), 3))


def build(ctx):
    a = ctx['args']
    t = float(ctx['t'])
    fh = a.get('floorhole')
    if fh is not None:
        # D-26: the cabin floor in front of the main seat erodes from F8b (README §9.1); the hole as a window cut from the
        # eye, like the roof hole: 'az0,az1,el0,el1' (deg, from the main eye; el negative = below the horizon)
        az0, az1, el0, el1 = (float(x) for x in str(fh).split(','))
        import tempfile
        LS = ctx['lbh_scene']
        J = json.load(open(LS.paths.BUS_JSON, encoding='utf-8'))
        J['presets']['bible_v2']['windows'].append(dict(name='floor_eroded', az=[az0, az1], el=[el0, el1], steps=8))
        tmp = os.path.join(tempfile.gettempdir(), 'lanbai_sea_bus_floorhole_%d.json' % os.getpid())
        json.dump(J, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
        LS.paths.BUS_JSON = tmp
    rh = a.get('roofhole')
    if rh is not None:
        el0 = (70.0 - 120.0 * erosion(t)) if rh == 'auto' else float(rh)
        SK.roof_hole(ctx, el0)
    cam = ctx['cam']
    W, H = cam['res']
    eye = np.asarray(cam['eye'], np.float64)
    rays = S.camera_rays(W, H, cam['hfov_deg'], cam.get('yaw_deg', 0.0) or 0.0, cam.get('pitch_deg', 0.0) or 0.0)
    img, info = frame(rays, eye, t, a, cam)
    ctx2 = dict(ctx)
    ctx2['args'] = dict({k: v for k, v in a.items() if k not in ('roofhole', 'floorhole')}, frame='__7a__')
    SK.FRAMES['__7a__'] = lambda r, e, tt, aa: (img, info)
    out = SK.build(ctx2)
    out.update(what='act 7a', **info)
    return out
