"""Render the tear kit v2 at the bible's U6 / U7 / U8 scales from a bus-height camera.

usage: python3 render_tear.py STAGE W H SAMPLES OUT_BASENAME [--nosil] [--crop x0,y0,x1,y1]
All colours are bible FILLS (scene-linear); the EXR is graded through the S4 PPv2 simulation (s4.py).
"""
import os, sys, math, time, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Matrix, Euler
import tear_def as T
import kit_mesh as K
import bl
from bl import NB, new_mat, load_img, mesh_from_numpy

LAN = os.path.dirname(os.path.dirname(HERE))
TEX = os.path.join(LAN, 'deliver', 'Tear', 'Textures')


def hexlin(h):
    h = h.lstrip('#')
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


FILL = json.load(open(os.path.join(os.path.dirname(HERE), 'tear_fills.json')))
F = {k: np.array(v['linear']) for k, v in FILL.items()}
HAZE_NEAR, HAZE_FAR, VOID = F['HazeNear'], F['HazeFar'], F['Void']
MOON_AZ, MOON_EL = -12.0, 8.0


def dir_azel(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])


LMOON = dir_azel(MOON_AZ, MOON_EL)
MOON_COL = hexlin('#D6E4FF') / hexlin('#D6E4FF').max()          # E = 1
TEARL_COL = hexlin('#A99DE1') / hexlin('#A99DE1').max() * 0.80  # E = 0.8
FILL_COL = hexlin('#5A6488') / hexlin('#5A6488').max() * 0.24   # from below
FOG_D = 0.0006


def band_color(az_deg, el_deg=2.0):
    """fill colour of the luminous haze band / void in a direction (bible §6·4)."""
    az = abs(az_deg)
    t = np.clip(az / 50.0, 0, 1); t = t * t * (3 - 2 * t)
    c = HAZE_NEAR * (1 - t) + HAZE_FAR * t
    w_az = 1 - np.clip((az - 50) / 10, 0, 1); w_az = w_az * w_az * (3 - 2 * w_az)
    w_el = 1 - np.clip((el_deg - 15) / 20, 0, 1); w_el = w_el * w_el * (3 - 2 * w_el)
    w = w_az * w_el
    return VOID * (1 - w) + c * w


# ============================================================================================ scene
def setup(W, H, samples):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0
    sc.cycles.transparent_max_bounces = 96
    sc.cycles.pixel_filter_type = 'BLACKMAN_HARRIS'
    sc.cycles.filter_width = 1.5
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 4
    return sc


def world(stars=True):
    w = bpy.data.worlds.new('TearSky')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    b = NB(nt)
    tc = b.N('ShaderNodeTexCoord')
    x, y, z = b.sep(tc.outputs['Generated'])
    el = b.math('MULTIPLY', b.math('ARCSINE', z), 180 / math.pi)
    az = b.math('ABSOLUTE', b.math('MULTIPLY', b.math('ARCTAN2', x, y), 180 / math.pi))
    band = b.mix(b.smooth(az, 0, 50), tuple(HAZE_NEAR), tuple(HAZE_FAR))
    wb = b.math('MULTIPLY', b.smooth(az, 50, 60, 1, 0), b.smooth(el, 15, 35, 1, 0))
    sky = b.mix(wb, tuple(VOID), band)
    sky = b.rgbmul(sky, b.gray(b.smooth(el, -25, 0, 0.55, 1.0)))
    # moon: 1.2 deg disc + silver halo
    md = b.vec(LMOON)
    cosang = b.vmath('DOT_PRODUCT', tc.outputs['Generated'], md)
    ang = b.math('MULTIPLY', b.math('ARCCOSINE', b.math('MINIMUM', cosang, 1.0)), 180 / math.pi)
    disc = b.smooth(ang, 0.62, 0.56)
    limb = b.smooth(ang, 0.62, 0.0, 0.78, 1.0)
    moon_c = F['MoonDisc']
    moon = b.scale(b.rgb(tuple(moon_c)), b.math('MULTIPLY', disc, limb))
    halo_i = b.math('ADD', b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', ang, -1.2)), 0.10),
                    b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', ang, -0.30)), 0.035))
    halo = b.scale(b.rgb(tuple(hexlin('#8FA3C8'))), b.math('MULTIPLY', halo_i, b.math('SUBTRACT', 1.0, disc)))
    sky = b.rgbadd(b.rgbadd(sky, moon), halo)
    if stars:
        vor = b.N('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 220.0
        b.L(tc.outputs['Generated'], vor.inputs['Vector'])
        core = b.math('POWER', b.smooth(vor.outputs['Distance'], 0.0, 0.07, 1.0, 0.0), 6.0)
        r_, g_, bb_ = b.sepc(vor.outputs['Color'])
        keep = b.math('POWER', b.smooth(r_, 0.93, 1.0), 2.0)
        st = b.math('MULTIPLY', b.math('MULTIPLY', core, keep), 0.9)
        st = b.math('MULTIPLY', st, b.smooth(el, 8, 35, 0.2, 1.0))
        sky = b.rgbadd(sky, b.gray(st))
    bg = b.N('ShaderNodeBackground'); b.L(sky, bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    o = b.N('ShaderNodeOutputWorld'); b.L(bg.outputs[0], o.inputs['Surface'])


def camera(cam_h, pitch_deg, hfov=90.0):
    cd = bpy.data.cameras.new('Cam')
    cd.sensor_fit = 'HORIZONTAL'
    cd.angle = math.radians(hfov)
    cd.clip_start = 1.0; cd.clip_end = 60000
    cam = bpy.data.objects.new('Cam', cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (0, 0, cam_h)
    cam.rotation_euler = Euler((math.radians(90 + pitch_deg), 0, 0), 'XYZ')
    bpy.context.scene.camera = cam
    return cam


# ============================================================================================ cloud sea
def worley_domes(X, Y, cell, seed, jit=0.9):
    """rounded domes from a SMOOTH nearest-point distance (log-sum-exp): soft valleys, no quilting creases."""
    gx, gy = np.floor(X / cell).astype(np.int64), np.floor(Y / cell).astype(np.int64)
    k = 0.16 * cell
    acc = np.zeros(X.shape)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx, cy = gx + dx, gy + dy
            h = (cx * 73856093 ^ cy * 19349663 ^ seed * 83492791) & 0xFFFFFF
            ox = ((h * 16807) % 2147483647 % 10000) / 10000.0
            oy = ((h * 48271) % 2147483647 % 10000) / 10000.0
            sz = 0.75 + 0.5 * (((h * 69621) % 2147483647 % 10000) / 10000.0)
            px = (cx + 0.5 + (ox - 0.5) * jit) * cell
            py = (cy + 0.5 + (oy - 0.5) * jit) * cell
            d = np.hypot(X - px, Y - py) / sz
            acc += np.exp(-d / k)
    best = -k * np.log(acc + 1e-30)
    f = np.clip(1 - (best / (cell * 0.8)) ** 2, 0, 1)
    return f ** 0.7


def rollnoise(X, Y, seed):
    rng = np.random.default_rng(seed)
    s = np.zeros(X.shape)
    for i in range(6):
        a = rng.uniform(0, np.pi); f = rng.uniform(1 / 1600, 1 / 500); ph = rng.uniform(0, 6.28)
        s += np.sin((X * np.cos(a) + Y * np.sin(a)) * f * 6.28 + ph) / 6
    return s


def cloud_height(X, Y):
    h = (30 * worley_domes(X, Y, 820.0, 1) + 15 * worley_domes(X, Y, 260.0, 2)
         + 5.5 * worley_domes(X, Y, 90.0, 3) + 1.8 * worley_domes(X, Y, 28.0, 4) + 0.6 * worley_domes(X, Y, 9.0, 5)
         + 14 * rollnoise(X, Y, 6))
    return h - 36.0


def cloud_sea(stage, cam, kit_S, kit_pos, n_r=620, n_th=1050, r0=18.0, r1=18000.0, ang=78.0):
    """polar heightfield around the camera with baked moonlit shading + aerial perspective (static camera)."""
    t0 = time.time()
    r = r0 * (r1 / r0) ** np.linspace(0, 1, n_r)
    th = np.radians(np.linspace(-ang, ang, n_th))
    R, TH = np.meshgrid(r, th, indexing='ij')
    X, Y = R * np.sin(TH), R * np.cos(TH)
    fx, fy = kit_pos[0], kit_pos[1]
    # billows heaped round the tear's foot, so the wound sinks into the cloud sea instead of being cut by a line
    def heap(Xa, Ya):
        rr = np.hypot(Xa - fx, (Ya - fy) * 0.8)
        return (38.0 * worley_domes(Xa, Ya, 150.0, 8) + 14.0 * worley_domes(Xa, Ya, 55.0, 9)) * \
            np.exp(-(rr / (520.0 * kit_S)) ** 2)
    Z = cloud_height(X, Y) + heap(X, Y)
    # normals by finite differences in (x, y)
    e = 0.6 + R * 0.004
    zf = lambda xa, ya: cloud_height(xa, ya) + heap(xa, ya)
    dzdx = (zf(X + e, Y) - zf(X - e, Y)) / (2 * e)
    dzdy = (zf(X, Y + e) - zf(X, Y - e)) / (2 * e)
    N = np.stack([-dzdx, -dzdy, np.ones_like(Z)], -1)
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    P = np.stack([X, Y, Z], -1)
    Vv = np.array(cam) [None, None] - P
    d = np.linalg.norm(Vv, axis=-1)
    Vn = Vv / d[..., None]
    ray = -Vn
    # --- light (fill space; Unity-like: albedo * E * NdotL). Night: the moon is LOW and in FRONT (behind the
    # tear), so the faces we see are mostly in shadow; crests facing the moon catch a silver line.
    alb = 0.72
    top = np.clip((Z + 36.0) / 60.0, 0, 1)                                            # crest-ness
    occ = 0.10 + 0.90 * top ** 1.8
    ndl = np.clip((np.sum(N * LMOON, -1) + 0.12) / 1.12, 0, 1)
    mu = np.sum(ray * LMOON, -1)
    g = 0.72
    hg = (1 - g * g) / (1 + g * g - 2 * g * mu) ** 1.5 / 12.566
    edge = (1 - np.clip(np.sum(N * Vn, -1), 0, 1)) ** 3.0
    # the moon path: a silver lane of forward-scattered moonlight on the crests, only toward the low moon
    az_p = np.degrees(np.arctan2(X, Y))
    lane = np.exp(-((az_p - MOON_AZ) / 9.0) ** 2) * T.smoothstep(60.0, 450.0, R) * np.exp(-R / 1800.0)
    crest = np.clip((top - 0.45) / 0.55, 0, 1) ** 1.3
    # the moon is AHEAD: each billow's far rim (normal turned away from us, toward the moon) lights up silver
    rim = (1 - np.clip(np.sum(N * Vn, -1), 0, 1)) ** 4.0 * np.clip(np.sum(N * LMOON, -1) + 0.25, 0, 1)
    moon = MOON_COL[None, None] * (alb * 0.26 * ndl * occ + 0.22 * hg * (0.1 + edge) * crest
                                   + 0.55 * rim * crest * np.exp(-R / 2500.0)
                                   + 0.30 * lane * (0.2 + edge) * top ** 2)[..., None]
    # tear light: directional-ish from the tear core, plus the bible's glow card (#696F8D fill, r ~ 1.1 km * S)
    core = np.array([kit_pos[0], kit_pos[1], 380.0 * kit_S])
    Lt = core[None, None] - P
    dt = np.linalg.norm(Lt, axis=-1); Lt /= dt[..., None]
    ndt = np.clip((np.sum(N * Lt, -1) + 0.1) / 1.1, 0, 1)
    mut = np.sum(ray * Lt, -1)
    hgt = (1 - 0.45 ** 2) / (1 + 0.45 ** 2 - 2 * 0.45 * mut) ** 1.5 / 12.566
    tear = TEARL_COL[None, None] * (alb * 0.45 * ndt * occ + 0.7 * hgt * edge * top ** 2)[..., None]
    rg = np.hypot(X - fx, Y - (fy + 150.0 * kit_S)) / (K.CLOUD_GLOW_R * kit_S)
    card = 0.62 / (1 + (rg / 0.16) ** 2) ** 1.15 + 0.38 * np.exp(-(rg / 0.55) ** 2)
    card = np.clip(card - 0.02, 0, None) * np.clip((1 - rg) / 0.28, 0, 1)
    glow = F['CloudGlow'][None, None] * (card * (0.35 + 0.65 * top))[..., None] * 0.9
    # sky ambient: the void above is nearly black, the haze band on the horizon lights the tops a little
    amb = (VOID * 1.2 + HAZE_FAR * 0.12)[None, None] * (alb * occ)[..., None]
    col = moon + tear + glow + amb
    # aerial perspective toward the band colour of that azimuth
    az = np.degrees(np.arctan2(X, Y))
    fogc = np.stack([band_color(a, 1.0) for a in np.linspace(-90, 90, 181)])
    fc = np.stack([np.interp(az, np.linspace(-90, 90, 181), fogc[:, i]) for i in range(3)], -1)
    tr = np.exp(-d * FOG_D)
    col = col * tr[..., None] + fc * (1 - tr[..., None])
    Fc = K._grid_faces(n_r, n_th, flip=True)
    Vf = P.reshape(-1, 3)
    ob = mesh_from_numpy('CloudSea', Vf, Fc, point_colors=[('Col', np.concatenate([col.reshape(-1, 3), np.ones((Vf.shape[0], 1))], 1))])
    m, b = new_mat('CloudSea')
    vc = b.attr('Col')
    b.out(b.emission(vc.outputs['Color']))
    ob.data.materials.append(m)
    print('cloud sea %.1fs, %d verts' % (time.time() - t0, Vf.shape[0]))
    return ob


# ============================================================================================ silhouettes
RAD_K = [(0, 1.0), (0.05, 1.06), (0.15, 1.0), (0.30, 0.88), (0.45, 0.72), (0.60, 0.52), (0.72, 0.33),
         (0.82, 0.18), (0.90, 0.08), (0.96, 0.03), (1, 0.006)]


def catmull(pts, n):
    pts = np.asarray(pts, float)
    P = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])
    out = []
    seg = len(pts) - 1
    for i in range(seg):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        for tt in np.linspace(0, 1, n // seg, endpoint=False):
            t2, t3 = tt * tt, tt * tt * tt
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * tt + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    c = np.array(out)
    # resample by arc length
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])
    s = np.linspace(0, L[-1], n)
    return np.stack([np.interp(s, L, c[:, i]) for i in range(3)], 1), L[-1]


RAD_COLOSSUS = [(0, 1.0), (0.1, 1.04), (0.3, 0.92), (0.5, 0.78), (0.65, 0.66), (0.8, 0.5), (0.9, 0.34),
                (0.96, 0.18), (1, 0.03)]


def tube(name, ctrl, r0, n=220, nseg=28, seed=0, colossus=False):
    c, Ltot = catmull(ctrl, n)
    u = np.linspace(0, 1, n)
    kx, ky = zip(*(RAD_COLOSSUS if colossus else RAD_K))
    rad = r0 * np.interp(u, kx, ky)
    rng = np.random.default_rng(seed)
    rad *= 1 + 0.07 * np.sin(u * rng.uniform(9, 14) + rng.uniform(0, 6)) * (1 - u)   # muscular swellings
    tng = np.gradient(c, axis=0); tng /= np.linalg.norm(tng, axis=1, keepdims=True)
    ref = np.array([0.3, 0.2, 0.93]); ref /= np.linalg.norm(ref)
    nrm = np.cross(tng, ref); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    bnm = np.cross(tng, nrm)
    ang = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    ring = (np.cos(ang)[None, :, None] * nrm[:, None] + np.sin(ang)[None, :, None] * bnm[:, None])
    V = c[:, None] + ring * rad[:, None, None]
    Nn = ring.reshape(-1, 3)
    V = V.reshape(-1, 3)
    Fc = []
    for i in range(n - 1):
        for j in range(nseg):
            a, b_, cc, d = i * nseg + j, i * nseg + (j + 1) % nseg, (i + 1) * nseg + (j + 1) % nseg, (i + 1) * nseg + j
            Fc.append((a, b_, cc, d))
    return mesh_from_numpy(name, V, np.array(Fc), normals=Nn)


def tentacle_material(name, fogcol, tear_pos, far):
    """emission-only mirror of the bible's Lanbai/Tentacle look: ink body, moon rim, tear-side rim, fog w/ cap."""
    m, b = new_mat(name)
    geo = b.N('ShaderNodeNewGeometry')
    Nw, I, Pw = geo.outputs['Normal'], geo.outputs['Incoming'], geo.outputs['Position']
    ndv = b.math('ABSOLUTE', b.vmath('DOT_PRODUCT', Nw, I))
    fres = b.math('POWER', b.math('SUBTRACT', 1.0, ndv), 4.0)
    ndm = b.vmath('DOT_PRODUCT', Nw, b.vec(LMOON))
    rim_m = b.math('MULTIPLY', fres, b.math('MINIMUM', b.math('MAXIMUM', b.math('ADD', b.math('MULTIPLY', ndm, 0.8), 0.45), 0.0), 1.0))
    # tear-side
    tp = b.vec(tear_pos)
    Lt = b.vmath('NORMALIZE', b.vmath('SUBTRACT', tp, Pw))
    ndt = b.vmath('DOT_PRODUCT', Nw, Lt)
    rim_t = b.math('MULTIPLY', fres, b.math('MINIMUM', b.math('MAXIMUM', b.math('ADD', ndt, 0.3), 0.0), 1.0))
    alb = 0.018
    diff = b.math('ADD', b.math('MULTIPLY', b.math('MAXIMUM', ndm, 0.0), alb * 1.0),
                  b.math('MULTIPLY', b.math('MAXIMUM', b.math('MULTIPLY', b.sep(Nw)[2], -1.0), 0.0), alb * 0.24))
    body = b.rgbadd(b.gray(b.math('ADD', diff, alb * 0.10)),
                    b.scale(b.rgb(tuple(TEARL_COL)), b.math('MULTIPLY', b.math('MAXIMUM', ndt, 0.0), alb * 0.9)))
    rimc = b.rgbadd(b.scale(b.rgb(tuple(hexlin('#9DB8FF') * 2.2)), rim_m),
                    b.scale(b.rgb(tuple(hexlin('#A99DE1') * 1.6)), rim_t))
    col = b.rgbadd(body, rimc)
    cd = b.N('ShaderNodeCameraData')
    dist = cd.outputs['View Distance']
    fogd = b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('MULTIPLY', dist, -FOG_D)))
    z = b.sep(Pw)[2]
    # bible: beyond 1.5 km fog cap 0.6 and x exp(-height/500 m) (never brighter than the sky at that elevation)
    capped = b.math('MULTIPLY', b.math('MINIMUM', fogd, 0.6),
                    b.math('EXPONENT', b.math('DIVIDE', b.math('MAXIMUM', z, 0.0), -500.0)))
    fogd = b.mixf(b.smooth(dist, 1300.0, 1700.0), fogd, capped)
    fogh = b.math('MULTIPLY', b.math('EXPONENT', b.math('DIVIDE', b.math('MAXIMUM', z, 0.0), -60.0)), 0.5)
    fog = b.math('SUBTRACT', 1.0, b.math('MULTIPLY', b.math('SUBTRACT', 1.0, fogd), b.math('SUBTRACT', 1.0, fogh)))
    col = b.mix(fog, col, tuple(fogcol))
    b.out(b.emission(col))
    return m


def gesture(base, target, H, style, seed, reach=0.45):
    """control points for an arm rooted at base (x, y) that rises out of the cloud sea and reaches toward target."""
    rng = np.random.default_rng(seed)
    bx, by = base
    to = np.array(target[:2]) - np.array(base); dist = np.linalg.norm(to); u = to / dist
    lat = np.array([-u[1], u[0]]) * rng.choice([-1, 1])
    R = dist * reach
    def P(f_u, f_l, f_z):
        xy = np.array(base) + u * f_u * R + lat * f_l * H
        return (xy[0], xy[1], f_z * H)
    if style == 'reach':       # rises with an S, then a long reach toward the wound, tip thinning out
        return [P(0, 0, -0.35), P(-0.06, 0.05, 0.25), P(0.02, -0.06, 0.62), P(0.28, 0.02, 0.9), P(0.62, 0.06, 1.0),
                P(0.92, 0.03, 0.93)]
    if style == 'hook':        # arcs over toward the wound, the tip hooks down
        return [P(0, 0, -0.35), P(0.02, 0.04, 0.35), P(0.18, -0.03, 0.8), P(0.45, 0.02, 1.0), P(0.68, 0.05, 0.9),
                P(0.74, 0.1, 0.72)]
    if style == 'whip':        # tall, slender, a lazy double S, the tip a thread leaning in
        return [P(0, 0, -0.35), P(0.03, -0.05, 0.3), P(-0.04, 0.05, 0.62), P(0.12, -0.02, 0.9), P(0.3, 0.03, 1.08),
                P(0.44, 0.0, 1.12)]
    return [P(0, 0, -0.35), P(0.1, 0, 0.5), P(0.5, 0, 1.0)]


def arm(base, tip, sway=0.0, rise=0.62, bury=110.0):
    """a tentacle rising out of the cloud sea and REACHING toward `tip` (x, y, z): height rises all the way into
    the tip (never an arch), the upper third leans over toward the target; `sway` bows the trunk sideways (m)."""
    b = np.array([base[0], base[1], -bury]); t = np.array(tip, float)
    d = t[:2] - b[:2]; L = np.linalg.norm(d); u = d / max(L, 1e-6); lat = np.array([-u[1], u[0]])
    zt = t[2]
    pts = [b,
           np.array([*(b[:2] + lat * sway * 0.4), 0.10 * zt]),
           np.array([*(b[:2] + u * L * 0.05 + lat * sway), rise * 0.62 * zt]),
           np.array([*(b[:2] + u * L * 0.22 + lat * sway * 0.6), rise * zt]),
           np.array([*(b[:2] + u * L * 0.55 + lat * sway * 0.2), 0.90 * zt]),
           t]
    return pts


def curl_arm(base, toward, L, th0=90.0, turn=120.0, p=1.9, sway=0.0, bury=120.0, n=18, wig=-24.0):
    """a tentacle as a clothoid-like curve: its tangent turns ever faster toward the tip, so it rises out of the
    cloud sea and curls toward `toward` (x, y) with no elbows. th0 = start angle above the horizontal (toward
    the target), turn = total bend (deg), sway = sideways bow (m)."""
    b = np.array(base, float); d = np.array(toward, float) - b
    u = d / np.linalg.norm(d); lat = np.array([-u[1], u[0]])
    s = np.linspace(0, 1, n)
    # an S before the curl (an inflection: a horn has none), then the tangent turns ever faster into the tip
    th = np.radians(th0 - turn * s ** p + wig * np.sin(np.pi * 1.7 * s) * (1 - s ** 2))
    ds = L / (n - 1)
    xu = np.concatenate([[0], np.cumsum(np.cos(th[:-1]) * ds)])
    z = np.concatenate([[0], np.cumsum(np.sin(th[:-1]) * ds)]) - bury
    lt = sway * np.sin(np.pi * s) + 0.25 * sway * s ** 3
    return [np.array([*(b + u * xu[i] + lat * lt[i]), z[i]]) for i in range(n)]


def silhouettes(stage, kit_pos, kit_S):
    """a few black arms for scale (bible: colossi 1.3-4 km heads clear / feet dissolving; mid ring 400-900 m
    round the tear foot bending toward the wound). Only for scale: not the tentacle library."""
    fx, fy = kit_pos[0], kit_pos[1]
    tear_core = (fx, fy, 380 * kit_S)
    foot = (fx, fy)
    arms = []
    def at(az, dist):
        a = math.radians(az)
        return (dist * math.sin(a), dist * math.cos(a))
    def ring(ang, rr):
        a = math.radians(ang)
        return (fx + rr * math.sin(a), fy + rr * math.cos(a))
    # S-bodies leaning toward the wound; the curl lives only in the thread-thin last ~20 % (a whip, not a horn)
    if stage == 'U6':
        arms.append(('Colossus2', curl_arm(at(-17.5, 2850), foot, 520, 84, 170, 4.5, sway=-25, wig=26, bury=150, n=24), 30, True))
        arms.append(('Colossus1', curl_arm(at(24.5, 3250), foot, 380, 88, 95, 4.0, sway=20, wig=-22, bury=150, n=24), 28, True))
    elif stage == 'U7':
        # "...und wollt' mich abweisen": colossus 2's body crosses the moon (az -12, el +8), its whip beyond
        arms.append(('Colossus2', curl_arm(at(-17.5, 1950), at(-9.0, 1860), 720, 86, 200, 4.2, sway=-30, wig=24, bury=150, n=24), 32, True))
        arms.append(('Colossus1', curl_arm(at(24.0, 3200), foot, 700, 88, 115, 4.5, sway=40, wig=-24, bury=150, n=24), 30, True))
        arms.append(('MidL', curl_arm(ring(-80, 540), foot, 440, 82, 240, 4.5, sway=30, wig=28, bury=110, n=24), 17, False))
        arms.append(('MidR', curl_arm(ring(86, 620), foot, 500, 84, 190, 4.5, sway=-35, wig=-26, bury=110, n=24), 19, False))
        arms.append(('Mid2', curl_arm(ring(-114, 860), foot, 340, 84, 80, 3.0, sway=-20, wig=22, bury=110, n=24), 13, False))
    elif stage == 'U8':
        arms.append(('MidL', curl_arm(ring(-78, 480), foot, 460, 82, 210, 4.5, sway=30, wig=28, bury=110, n=24), 19, False))
        arms.append(('Mid2', curl_arm(ring(-112, 720), foot, 340, 84, 80, 3.0, sway=-20, wig=22, bury=110, n=24), 14, False))
        arms.append(('Colossus3', curl_arm(at(30.0, 1250), (fx + 60, fy), 1050, 86, 140, 3.6, sway=50, wig=-22, bury=150, n=24), 38, True))
    obs = []
    for i, (name, ctrl, r0, far) in enumerate(arms):
        ob = tube(name, ctrl, r0, seed=i + 3, colossus=name.startswith('Colossus'))
        mid = np.mean(np.array(ctrl), 0)
        az = math.degrees(math.atan2(mid[0], mid[1]))
        fogc = band_color(az, 3.0)
        ob.data.materials.append(tentacle_material('M_' + name, fogc, tear_core, far))
        obs.append(ob)
    return obs


# ============================================================================================ tear kit
def kit_materials(stage_cfg, px_m, sky_fn=None):
    mats = {}
    em = load_img(os.path.join(TEX, 'Tear_Emission_2048x512.png'), 'sRGB', 'CHANNEL_PACKED')
    ri = load_img(os.path.join(TEX, 'Tear_Rip_1024x128.png'), 'sRGB', 'CHANNEL_PACKED')
    fi = load_img(os.path.join(TEX, 'Tear_Fibres_1024.png'), 'Non-Color', 'CHANNEL_PACKED')
    fl = load_img(os.path.join(TEX, 'Tear_Flaps_1024.png'), 'Non-Color', 'CHANNEL_PACKED')
    ha = load_img(os.path.join(TEX, 'Halo_512.png'), 'sRGB', 'CHANNEL_PACKED')
    sh = load_img(os.path.join(TEX, 'Shaft_Gradient_256x1024.png'), 'Non-Color', 'CHANNEL_PACKED')
    sf = load_img(os.path.join(TEX, 'Tear_SkyFolds_1024.png'), 'sRGB', 'CHANNEL_PACKED')
    def foot_fade(b):
        """v3: the kit dissolves into the cloud top over 40 m with billow noise (Unity: CloudFootFade(): clip below
        _Udon_CloudTop, saturate((y - cloudTop) / 40) x noise) -- Lens, Folds AND Halo (a halo card cut by the cloud
        plane drew a ruler line under the wound in the U8 forward frame)"""
        geo = b.N('ShaderNodeNewGeometry')
        nz = b.N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0 / 22.0; nz.inputs['Detail'].default_value = 3.0
        b.L(geo.outputs['Position'], nz.inputs['Vector'])
        zf = b.math('ADD', b.sep(geo.outputs['Position'])[2], b.math('MULTIPLY', b.math('SUBTRACT', nz.outputs['Fac'], 0.5), 36.0))
        return b.smooth(zf, stage_cfg.get('ctop', 4.0), stage_cfg.get('ctop', 4.0) + 40.0)

    m, b = new_mat('Tear_SkyFolds')
    uvf = b.uv('UVMap')
    tx = b.tex(sf, uvf)
    fu, fv, _ = b.sep(uvf)
    em_ = b.math('MULTIPLY', 2.0, b.math('MAXIMUM', b.math('ABSOLUTE', b.math('SUBTRACT', fu, 0.5)),
                                         b.math('ABSOLUTE', b.math('SUBTRACT', fv, 0.5))))
    k_ = b.math('MULTIPLY', b.smooth(em_, 1.0, 0.75, 0.0, 1.0), stage_cfg.get('folds', 1.0) * stage_cfg.get('intensity', 1.0))
    k_ = b.math('MULTIPLY', k_, foot_fade(b))
    b.out(b.add(b.emission(b.scale(tx.outputs['Color'], k_)),
                b.mixs(b.math('MULTIPLY', tx.outputs['Alpha'], k_), b.transparent(), b.emission((0, 0, 0)))))
    mats['Tear_SkyFolds'] = m
    I = stage_cfg.get('intensity', 1.0)

    # --- lens: premultiplied (out = rgb*4 + (1-A)*dst)
    m, b = new_mat('Tear_Lens')
    tx = b.tex(em, b.uv('UVMap'))
    # v3: the foot dissolves into the cloud top over 40 m with billow noise (Unity: clip below _Udon_CloudTop and
    # saturate((y - cloudTop) / 40) x noise in the Lens / Folds / Halo parts)
    ctop = foot_fade(b)
    rgb = b.scale(tx.outputs['Color'], b.math('MULTIPLY', ctop, T.EMISSION_SCALE * I))
    b.out(b.add(b.emission(rgb), b.mixs(b.math('MULTIPLY', tx.outputs['Alpha'], ctop), b.transparent(), b.emission((0, 0, 0)))))
    mats['Tear_Lens'] = m

    # --- rips: progress-driven reveal with a pointed running front
    m, b = new_mat('Tear_Rip')
    uv = b.uv('UVMap'); u, v, _ = b.sep(uv)
    win = b.uv('UV2'); ws, we, _ = b.sep(win)
    P = stage_cfg['rip']
    prog = b.math('MINIMUM', b.math('MAXIMUM', b.math('DIVIDE', b.math('SUBTRACT', P, ws), b.math('SUBTRACT', we, ws)), 0.0), 1.0)
    front = b.math('SUBTRACT', b.math('MULTIPLY', prog, 1.2), 0.1)
    wm = b.math('POWER', b.math('MINIMUM', b.math('MAXIMUM', b.math('DIVIDE', b.math('SUBTRACT', front, u), 0.1), 0.0), 1.0), 0.7)
    v2 = b.math('ADD', 0.5, b.math('DIVIDE', b.math('SUBTRACT', v, 0.5), b.math('MAXIMUM', wm, 0.001)))
    cxy = b.N('ShaderNodeCombineXYZ'); b.L(u, cxy.inputs[0]); b.L(v2, cxy.inputs[1])
    tx = b.tex(ri, cxy.outputs[0])
    vis = b.math('GREATER_THAN', wm, 0.0005)
    rgb = b.scale(tx.outputs['Color'], b.math('MULTIPLY', vis, T.EMISSION_SCALE * I * stage_cfg.get('rip_gain', 0.55)))
    al = b.math('MULTIPLY', tx.outputs['Alpha'], vis)     # v3b: rip_gain 0.55 (Unity: Tear_Rip material _Intensity 0.55)
    b.out(b.add(b.emission(rgb), b.mixs(al, b.transparent(), b.emission((0, 0, 0)))))
    mats['Tear_Rip'] = m

    # --- fibres: additive strands, root = fibre fill, tip -> lip glow
    m, b = new_mat('Tear_Fibres')
    uv = b.uv('UVMap'); u, v, _ = b.sep(uv)
    tx = b.tex(fi, uv)
    col = b.mix(b.math('POWER', v, 0.8), tuple(F['Fibre']), tuple(F['Glow'] * 0.75))
    k = b.math('MULTIPLY', tx.outputs['Alpha'], 0.95 * I)
    b.out(b.add(b.emission(b.scale(col, k)), b.transparent()))
    mats['Tear_Fibres'] = m

    # --- flaps v4 (gate round 3, critique B4.3 / tech M4): the sky's own cloth peeling back. OUTER face = the sky's
    #     colour behind it (Unity: LanbaiHorizon(viewDir) + the halo there, x _OuterSky 0.94) with a faint silk sheen
    #     where it turns; INNER face (seen only on the rolled lip) wound-lit #3E3C66 -> #5B5A88 x (0.15 + 0.6 R);
    #     a thin desaturated rim only along the rolled torn edge; fold bleed 0.15.
    m, b = new_mat('Tear_Flap')
    uv = b.uv('UVMap')
    tx = b.tex(fl, uv)
    tR, tG, tB = b.sepc(tx.outputs['Color'])
    cov = tx.outputs['Alpha']
    vc = b.attr('Col')
    cR, cG, cB = b.sepc(vc.outputs['Color'])
    geo = b.N('ShaderNodeNewGeometry')
    back = geo.outputs['Backfacing']
    Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
    silk = b.math('ADD', 0.94, b.math('MULTIPLY', b.math('SUBTRACT', tG, 0.5), 0.5))
    if sky_fn is not None:
        sky = sky_fn(b, Vd)
    else:
        sky = b.rgb(tuple(F['HazeNear']))
    outer = b.scale(sky, b.math('MULTIPLY', silk, stage_cfg.get('flap_outer', 0.94)))
    inner = b.scale(b.mix(cB, tuple(F['FlapInner']), tuple(F['FlapInner'] * 1.55)),
                    b.math('MULTIPLY', b.math('ADD', 0.15, b.math('MULTIPLY', cR, 0.6)), silk))
    col = b.mix(back, outer, inner)
    ndv = b.math('ABSOLUTE', b.vmath('DOT_PRODUCT', geo.outputs['Normal'], geo.outputs['Incoming']))
    sheen = b.math('MULTIPLY', b.math('POWER', b.math('SUBTRACT', 1.0, ndv), 3.0), b.math('ADD', 0.1, cR))
    col = b.rgbadd(col, b.scale(b.rgb(tuple(F['FlapInner'])), b.math('MULTIPLY', sheen, 0.5)))
    fold = b.math('POWER', b.math('MAXIMUM', b.math('SUBTRACT', 1.0, b.math('DIVIDE', cB, 0.06)), 0.0), 2.0)
    col = b.rgbadd(col, b.scale(b.rgb(tuple(F['Glow'])), b.math('MULTIPLY', fold, 0.15)))
    # rim: 1-2 px along the torn edge, only where the cloth has rolled (B > 0.75), C* <= 20
    dist_m = b.math('MULTIPLY', tR, 24.0)
    ol = b.math('SUBTRACT', 1.0, b.smooth(dist_m, px_m * 0.5, px_m * 1.5))
    ol = b.math('MULTIPLY', ol, b.smooth(cB, 0.70, 0.85))
    rimc = F['MoonRim'] * 0.35
    rimc = 0.45 * rimc + 0.55 * np.full(3, float(rimc @ np.array([0.2126, 0.7152, 0.0722])))
    col = b.mix(ol, col, tuple(rimc))
    alpha = b.math('MINIMUM', b.math('MULTIPLY', cov, foot_fade(b)), 1.0)
    b.out(b.mixs(alpha, b.transparent(), b.emission(col)))
    mats['Tear_Flap'] = m

    # --- halo: additive breathing radial cards
    m, b = new_mat('Tear_Halo')
    uvh = b.uv('UVMap')
    tx = b.tex(ha, uvh)
    hu, hv, _ = b.sep(uvh)
    em_ = b.math('MULTIPLY', 2.0, b.math('MAXIMUM', b.math('ABSOLUTE', b.math('SUBTRACT', hu, 0.5)),
                                         b.math('ABSOLUTE', b.math('SUBTRACT', hv, 0.5))))
    efade = b.math('MULTIPLY', b.smooth(em_, 1.0, 0.75, 0.0, 1.0), foot_fade(b))
    gk = b.sep(b.uv('UV2'))[0]                      # v4: per-card gain (the inner card x2.8)
    efade = b.math('MULTIPLY', efade, gk)
    b.out(b.add(b.emission(b.scale(tx.outputs['Color'], b.math('MULTIPLY', efade, stage_cfg.get('halo', 1.0) * I))), b.transparent()))
    mats['Tear_Halo'] = m

    # --- shafts: additive beams (per-vertex fade baked in 'Fade')
    m, b = new_mat('Tear_Shaft')
    tx = b.tex(sh, b.uv('UVMap'))
    fade = b.attr('Fade')
    k = b.math('MULTIPLY', tx.outputs['Alpha'], b.math('MULTIPLY', b.sepc(fade.outputs['Color'])[0], stage_cfg.get('shaft', 1.0) * I))
    beam = F['ShaftPair'] * 0.5
    b.out(b.add(b.emission(b.scale(b.rgb(tuple(beam)), k)), b.transparent()))
    mats['Tear_Shaft'] = m
    return mats


def build_kit(stage_cfg, kit_S, kit_pos, cam_world, px_m, skip=(), sky_fn=None):
    open01 = T.tear_open_param(stage_cfg['open'])
    mats = kit_materials(stage_cfg, px_m, sky_fn)
    M = Matrix.Translation(Vector(kit_pos)) @ Matrix.Scale(kit_S, 4)
    Minv = M.inverted()
    cam_kit = np.array(Minv @ Vector(cam_world))
    obs = []
    for p in K.all_parts():
        if p['name'] in skip or p['name'] == 'Tear_CloudGlow':
            continue
        V = K.deform(p, open01, cam_kit)
        uvs = [('UVMap', p['UV0']), ('UV1', p['UV1']), ('UV2', p['UV2'])]
        cols = []
        if p['COL'] is not None and p['name'] != 'Tear_Shafts':
            cols.append(('Col', p['COL']))
        if p['name'] == 'Tear_Shafts':
            ax = p['AXIS'] / np.linalg.norm(p['AXIS'], axis=1, keepdims=True)
            vd = cam_kit[None] - V; vd /= np.linalg.norm(vd, axis=1, keepdims=True)
            perp = np.sqrt(np.clip(1 - np.sum(ax * vd, 1) ** 2, 0, 1))
            fade = np.clip(perp * 1.4, 0, 1) ** 2.0
            # near-eye / soft fade toward the bus end (bible: soft 40 m) and toward the cloud top
            dcam = np.linalg.norm(cam_kit[None] - V, axis=1) * kit_S
            fade *= np.clip((dcam - 60.0) / 400.0, 0, 1)
            cols.append(('Fade', np.stack([fade, fade, fade, np.ones_like(fade)], 1)))
        ob = mesh_from_numpy(p['name'], V, p['F'], uvs=uvs, point_colors=cols,
                             normals=p['N'] if p['name'].startswith('Tear_Flap') else None)
        ob.matrix_world = M
        ob.data.materials.append(mats[p['mat']])
        ob.visible_shadow = False
        obs.append(ob)
    return obs


# ============================================================================================ main
def main():
    args = sys.argv[1:]
    stage = args[0]; W, H, S = int(args[1]), int(args[2]), int(args[3]); base = args[4]
    nosil = '--nosil' in args
    cfg = dict(T.STAGES[stage])
    for a in args:
        if a.startswith('--set='):
            for kv in a[6:].split(','):
                k, v = kv.split(':'); cfg[k] = float(v)
    t0 = time.time()
    setup(W, H, S)
    world()
    kit_S = cfg['H'] / T.H
    kit_pos = (0.0, cfg['D'], 0.0)
    cam_world = (0.0, 0.0, cfg['cam'])
    hfov = cfg.get('hfov', 90.0)
    cam = camera(cfg['cam'], cfg.get('aim', cfg['pitch']), hfov)
    if 'yaw' in cfg:
        cam.rotation_euler[2] = math.radians(-cfg['yaw'])
    px_m = cfg['D'] * math.tan(math.radians(hfov / W)) / kit_S       # metres (kit space) per pixel at the tear
    build_kit(cfg, kit_S, kit_pos, cam_world, px_m)
    cloud_sea(stage, cam_world, kit_S, kit_pos)
    if not nosil:
        silhouettes(stage, kit_pos, kit_S)
    for a in args:
        if a.startswith('--border='):
            x0, x1, y0, y1 = (float(v) for v in a[9:].split(','))
            sc = bpy.context.scene
            sc.render.use_border = True; sc.render.use_crop_to_border = True
            sc.render.border_min_x, sc.render.border_max_x = x0, x1
            sc.render.border_min_y, sc.render.border_max_y = y0, y1
    exr = base + '.exr'
    bpy.context.scene.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    print('render %.1fs' % (time.time() - t0))
    im = bpy.data.images.load(exr, check_existing=False)
    w, h = im.size
    lin = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
    np.save(base + '_lin.npy', lin.astype(np.float16))
    import s4
    d = s4.to_display(lin, bloom=True, vignette=True)
    s4.save(d, base + '.png')
    print('wrote', base + '.png')


if __name__ == '__main__':
    main()
