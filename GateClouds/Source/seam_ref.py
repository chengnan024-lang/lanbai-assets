"""蓝白 / Lanbai · gate clouds kit · the arms' roots in the volume cloud (D-44 #3): a reference render, before / after.

What it renders (numpy + Cycles for the arm passes only):
  * the arms: Gate/GateArms_v4.fbx LOD0, posed at time t exactly as LanbaiGateDriver.Pose (rise -> lean -> track ->
    close, the bus frame) under GateRoot (0, 150 - h_bus, -s(t)); Cycles renders only their Position / Normal passes
    (1 spp, no shading); the arm colour is a simple stand-in for Lanbai/TentacleSway (dark albedo, moon Lambert + rim,
    the shader's LanbaiFog with the cloud-top extra), the SAME in both columns;
  * the cloud: a line-by-line port of 阿白's Lanbai/Local/VolumeCloudDeck (FromLocal/full_preview/20261025-0103/
    review_sources/LocalIntegration/Shaders/VolumeCloudDeck.shader.txt): the same 128^3 density (generate_density_only.py,
    same seed), envelope, threshold, comfort cut, 56 / 80 jittered steps ended at the scene depth, two moon samples;
  * BEFORE = TentacleSway v2.7d: clip(y - top + 5), the root dissolve (18 m), the ragged fade to _CloudTopColor
    (0.026, 0.030, 0.038) over _CloudFade 46 m;
  * AFTER = TentacleSway v2.8 + Lanbai/GateVolumeDeck: the roots reach top - RootReach (vertex stretch, only roots that
    stand shallower), clip at top - RootClip, no dissolve, the arm WET into the cloud (toward the cloud's own lit colour by
    the cloud density sampled around the surface), and the cloud's SKIRT around every arm (LanbaiCloudVolume.cginc).

  python3 seam_ref.py <shot> [--w 960] [--out dir]      shot = seat | left | right | outside | seat152 | all

If you change a number here, change it in the shaders (TentacleSway v2.8 Properties, LanbaiCloudVolume.cginc).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deck_ref as D  # noqa: E402

REPO = D.REPO
GATE = os.path.join(REPO, 'Gate')
BAKE = json.load(open(os.path.join(GATE, 'GateDriver_Bake.json')))
LAY = {it['id']: it for it in json.load(open(os.path.join(GATE, 'GateLayout_v2.json')))['instances']}
MOON = np.array(BAKE['moon_dir'], float)
MOON /= np.linalg.norm(MOON)
ss = D.ss

# ---- 阿白's VolumeCloudDeck (material defaults as in FullPreview) ---------------------------------------------------
VOL = dict(Density=0.036, Wind=(8.0, 3.0), XZ=520.0, Y=260.0, MoonE=0.38, MoonColor=np.array([0.6724, 0.7758, 1.0]),
           Amb=np.array([0.0436, 0.0504, 0.0726]), Gain=0.9, Fog=0.0006, FootPoolColor=np.array([0.7605, 0.8070, 0.8963]))
# ---- AFTER: the shared skirt + the arm's v2.8 terms (= LanbaiCloudVolume.cginc / TentacleSway v2.8 defaults) --------
NEW = dict(RootReach=150.0, RootSpan=60.0, RootClip=2010.0, RootDeep=2000.0, UnderDark=0.15,
           # skirt: x width (x r, min SkirtWmin m), climb above the top at the arm (m), soft top (m), strength
           SkirtW=1.3, SkirtWmin=22.0, SkirtClimb=26.0, SkirtBase=-24.0, SkirtSoft=18.0, SkirtK=2.2, SkirtLump=40.0,
           # wet: optical depth from the three density taps -> wet, max wet
           WetK=1.5, WetMax=0.95, WetTap0=3.0, WetTap1=15.0, WetTap2=40.0)
OLD = dict(Clip=5.0, Dissolve=18.0, Fade=46.0, TopColor=np.array([0.026, 0.030, 0.038]))
ARM = dict(Albedo=np.array([0.030, 0.029, 0.036]), MoonE=1.0, Fill=0.06, Rim=0.10, FogExtra=1.5, FogExtraH=25.0,
           Cap=0.6, CapFrom=(1300.0, 1700.0), CapH=500.0)


# ============================================================================================ the density volume
def density_tex():
    """generate_density_only.py (阿白), same seed; returns R, G as float32 [z, y, x] (Unity Texture3D byte order)"""
    cache = '/tmp/claude-0/seam/density128.npy'
    if os.path.exists(cache):
        return np.load(cache)
    size = 128
    rng = np.random.default_rng(20261025)

    def noise(n):
        grid = rng.random((n, n, n), dtype=np.float32)
        coord = np.arange(size, dtype=np.float32) * n / size
        idx = coord.astype(int)
        u = coord - idx
        u = u * u * (3 - 2 * u)
        out = np.zeros((size, size, size), np.float32)
        for x in range(2):
            for y in range(2):
                for z in range(2):
                    wx = u if x else 1 - u
                    wy = u if y else 1 - u
                    wz = u if z else 1 - u
                    out += (grid[(idx[:, None, None] + x) % n, (idx[None, :, None] + y) % n, (idx[None, None, :] + z) % n]
                            * wx[:, None, None] * wy[None, :, None] * wz[None, None, :])
        return out
    a, b, c, d = noise(4), noise(8), noise(16), noise(32)
    R = np.clip((a * .55 + b * .30 + c * .15) * 255, 0, 255).astype(np.uint8) / 255.0
    G = np.clip((c * .7 + d * .3) * 255, 0, 255).astype(np.uint8) / 255.0
    T = np.stack([R, G], -1).astype(np.float32)     # array [i, j, k] -> bytes; Unity: x = k, y = j, z = i
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.save(cache, T)
    return T


TEX = None


def tex3d(uvw):
    """tex3Dlod(uvw, 0): trilinear, wrap; uvw[..., 0] = x"""
    n = TEX.shape[0]
    f = uvw * n - 0.5
    i0 = np.floor(f).astype(np.int64)
    w = f - i0
    out = 0.0
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                wt = ((w[..., 0] if dx else 1 - w[..., 0]) * (w[..., 1] if dy else 1 - w[..., 1])
                      * (w[..., 2] if dz else 1 - w[..., 2]))
                out = out + TEX[(i0[..., 2] + dz) % n, (i0[..., 1] + dy) % n, (i0[..., 0] + dx) % n] * wt[..., None]
    return out


class Ctx:
    def __init__(self, t, eye, skirts=None):
        self.t = t
        self.eye = eye
        self.top = -D.h_bus(t)
        self.origin = D.gate_origin(t)
        self.skirts = skirts or []           # (cx, cz, r) world


def vol_shape(p, c):
    """VolumeCloudDeck density() / _Density, plus the noise R (the skirt reuses it)"""
    top = c.top
    y = (p[..., 1] - (top - 170.0)) / 200.0
    env = ss(0.0, 0.16, y) * (1.0 - ss(0.9, 1.0, y))
    xz = p[..., [0, 2]] - c.origin[[0, 2]] - np.array(VOL['Wind']) * c.t
    uvw = np.stack([xz[..., 0] / VOL['XZ'], xz[..., 1] / VOL['XZ'], (p[..., 1] - top) / VOL['Y']], -1)
    n = tex3d(uvw)
    thr = 0.14 + (0.86 - 0.14) * np.clip(y, 0, 1)
    shape = ss(thr, thr + 0.12, n[..., 0] - 0.10 * (n[..., 1] - 0.5))
    return shape * env, n


def skirt(p, c, n):
    """LanbaiGateSkirt: the cloud gathers round every arm that pierces it (x _Density, max with the deck)"""
    out = np.zeros(p.shape[:-1])
    for cx, cz, r, k in c.skirts:
        d = np.hypot(p[..., 0] - cx, p[..., 2] - cz)
        W = max(NEW['SkirtWmin'], NEW['SkirtW'] * r)
        g = np.exp(-np.maximum(d - r, 0.0) / W)
        g = g * np.clip((3.0 - np.maximum(d - r, 0.0) / W) * 2.0, 0.0, 1.0)   # the shader: tapered, 0 past 3 W
        # lumpy: the top rides the finer noise (G: 16-32 m cells), the billows too (R is 30-130 m: a smooth dome)
        sk_top = c.top + NEW['SkirtBase'] + NEW['SkirtClimb'] * g + (n[..., 1] - 0.5) * NEW['SkirtLump']
        v = ss(sk_top, sk_top - NEW['SkirtSoft'], p[..., 1]) * ss(c.top - 170.0, c.top - 120.0, p[..., 1])
        billow = ss(0.30, 0.55, n[..., 1] + 0.25 * g)
        out = np.maximum(out, NEW['SkirtK'] * k * g * v * billow)
    return out


def density(p, c, new):
    s, n = vol_shape(p, c)
    if new and c.skirts:
        s = np.maximum(s, skirt(p, c, n))
    comfort = 1.0 if c.eye[1] < c.top - 170.0 else 1.0 - ss(c.eye[1] - 40.0, c.eye[1] - 18.0, p[..., 1])
    return s * comfort * VOL['Density']


def fog_colour(V, c, tear):
    return D.band(V, c.eye, tear) + D.moon_air(V) * 0.35


def cloud_light(p, c, tear, new, facing):
    optical = density(p + MOON * 18.0, c, new) * 22.0 + density(p + MOON * 50.0, c, new) * 38.0
    illum = 0.08 + 0.92 * np.exp(-optical * 1.7)
    height = np.clip((p[..., 1] - (c.top - 120.0)) / 140.0, 0, 1)
    light = VOL['Amb'] * (.3 + height * .35)[..., None] + VOL['MoonColor'] * (VOL['MoonE'] * illum * (.65 + facing * .35))[..., None]
    foot = c.origin + np.array([0.0, -150.0, 19.0])
    dist = np.hypot((p[..., 0] - foot[0]) / 180.0, (p[..., 2] - foot[2]) / 240.0)
    light = light + VOL['FootPoolColor'] * (.09 * np.exp(-dist * dist) * height)[..., None]
    return light


def march(V, c, scene_d, new, tear, seed=0):
    """VolumeCloudDeck frag for the rays V (N, 3) with scene distance scene_d (inf = sky); returns (sum, transmission)"""
    N = V.shape[0]
    eye = c.eye
    out = np.zeros((N, 3))
    trans = np.ones(N)
    lower = c.top - 170.0
    below = eye[1] < lower                       # the deck seen from under its floor (GateVolumeDeck [D-44])
    ok = V[:, 1] > 0.0005 if below else V[:, 1] < -0.0005
    upper = c.top + 30.0 if below else min(c.top + 30.0, eye[1] - 18.0)
    with np.errstate(divide='ignore', invalid='ignore'):
        if below:
            start = (lower - eye[1]) / V[:, 1]
            end = np.minimum(4200.0, (upper - eye[1]) / V[:, 1])
        else:
            start = np.maximum(0.0, (upper - eye[1]) / V[:, 1])
            end = np.minimum(4200.0, (lower - eye[1]) / V[:, 1])
    end = np.minimum(end, scene_d)
    ok &= end > start
    idx = np.nonzero(ok)[0]
    if len(idx) == 0:
        return out, trans
    v = V[idx]
    s0, s1 = start[idx], end[idx]
    count = np.where(v[:, 1] > -0.35, 80, 56)
    L = (s1 - s0) / count
    p0 = eye + v * s0[:, None]
    jit = 0.2 + 0.6 * tex3d(p0 * 0.073)[:, 1]
    fogc = fog_colour(v, c, tear)
    facing = np.clip(v @ MOON, 0, 1) ** 5
    tr = np.ones(len(idx))
    acc = np.zeros((len(idx), 3))
    for s in range(80):
        live = (s < count) & (tr >= 0.015)
        if not live.any():
            break
        k = np.nonzero(live)[0]
        tt = s0[k] + (s + jit[k]) * L[k]
        p = eye + v[k] * tt[:, None]
        den = density(p, c, new)
        m = den > 0.00008
        if not m.any():
            continue
        km = k[m]
        pm = p[m]
        light = cloud_light(pm, c, tear, new, facing[km])
        f = (1.0 - np.exp(-VOL['Fog'] * tt[m]))[:, None]
        light = (light * VOL['Gain']) * (1 - f) + fogc[km] * f
        a = 1.0 - np.exp(-den[m] * L[km])
        acc[km] += (tr[km] * a)[:, None] * light
        tr[km] *= 1.0 - a
    out[idx] = acc
    trans[idx] = tr
    return out, trans


# ============================================================================================ the arms
def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(a, b, s):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = float(a @ b)
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        r = a + (b - a) * s
        return r / np.linalg.norm(r)
    th = math.acos(d)
    return (math.sin((1 - s) * th) * a + math.sin(s * th) * b) / math.sin(th)


def ease(e, t):
    s = min(max((t - e['t0']) / max(1e-4, e['t1'] - e['t0']), 0.0), 1.0)
    if e['profile'] == 1:
        vm = 1 / (1 - e['e'])
        if s < e['e']:
            return vm * s * s / (2 * e['e'])
        if s <= 1 - e['e']:
            return vm * (s - e['e'] / 2)
        return 1 - vm * (1 - s) ** 2 / (2 * e['e'])
    if e['profile'] == 2:
        return 1 - (1 - s) ** e['b'] * (1 + e['b'] * s)
    return s * s * (3 - 2 * s)


def pose(d, t):
    """LanbaiGateDriver.Pose -> world position, rotation matrix (GateRoot has no rotation)"""
    p = np.array(d['pos'], float)
    q = np.array(d['rot'], float)
    if d['rise']:
        p = np.array(d['rise_start']) + (p - np.array(d['rise_start'])) * ease(d['rise_ease'], t)
    if d['lean']:
        q = slerp(d['lean_start'], q, ease(d['lean_ease'], t))
    tt = d['track_t']
    if tt and t >= tt[0]:
        Q = np.array(d['track_q']).reshape(-1, 4)
        if t >= tt[-1]:
            q = Q[-1]
        else:
            for k in range(len(tt) - 1):
                if tt[k] <= t <= tt[k + 1]:
                    q = slerp(Q[k], Q[k + 1], float(ss(0, 1, (t - tt[k]) / max(1e-4, tt[k + 1] - tt[k]))))
                    break
    if d['close'] and t > d['close_ease']['t0']:
        q = slerp(q, d['close_end'], ease(d['close_ease'], t))
    hb = D.h_bus(t)
    if d['bus']:
        p = np.array([p[0], -hb + p[1], p[2] + d['drift_v'] * (t - d['drift_tref'])])
    else:
        p = p + D.gate_origin(t)
    return p, quat_mat(q)


def reveal(d, t):
    if d['reveal_kind'] == 1 and d['rev_t']:
        rt, rv = d['rev_t'], d['rev_v']
        if t <= rt[0]:
            return rv[0]
        if t >= rt[-1]:
            return rv[-1]
        for k in range(len(rt) - 1):
            if rt[k] <= t <= rt[k + 1]:
                return rv[k] + (rv[k + 1] - rv[k]) * float(ss(0, 1, (t - rt[k]) / (rt[k + 1] - rt[k])))
    return 1.0


ARMS = None


def arm_meshes(t, new):
    """world-space vertex arrays of the arms visible at t; AFTER: the root reach (TentacleSway v2.8 vertex stretch)"""
    global ARMS
    if ARMS is None:
        ARMS = np.load('/tmp/claude-0/seam/arms.npz')
    top = -D.h_bus(t)
    out = []
    for d in BAKE['inst']:
        name = d['id']
        if name + '_v' not in ARMS.files or reveal(d, t) <= 0.0:
            continue
        p, R = pose(d, t)
        sc = float(LAY[name].get('scale', 1.0))
        V = (ARMS[name + '_v'] * sc) @ R.T + p
        if V[:, 1].max() < top - 40.0:
            continue
        if new:
            V = V.copy()
            need = p[1] - (top - NEW['RootReach'])
            if need > 0:
                s = np.clip((V[:, 1] - p[1]) / NEW['RootSpan'], 0, 1)
                V[:, 1] -= need * (1 - s) ** 2
            rootY = p[1] - max(need, 0.0)
            L, target = top - 100.0, top - NEW['RootDeep']
            if target < rootY < L - 1.0:
                m = V[:, 1] < L
                V[m, 1] = L - (L - V[m, 1]) * (L - target) / (L - rootY)
        out.append((name, V, ARMS[name + '_f'], p, R, sc))
    return out


def arm_skirts(arms, top):
    """per arm: the cross-section where it passes the cloud's surface (top - 40 m): centre xz, mean radius"""
    sk = []
    for name, V, F, p, R, sc in arms:
        y0 = top - 40.0
        m = np.abs(V[:, 1] - y0) < 4.0
        if m.sum() < 8:
            continue
        P = V[m][:, [0, 2]]
        # a hand is a bundle of fingers: one skirt per finger cluster is overkill; the bundle's centre and mean radius
        cxz = P.mean(0)
        r = float(np.sqrt(((P - cxz) ** 2).sum(1)).mean())
        sk.append((float(cxz[0]), float(cxz[1]), r, name))
    return sk


SKIRT_LEVEL = 40.0          # the skirt sits where the arm crosses top - 40 m (the volume's mean visible surface)
SKIRT_TMAX = 0.6            # the baked centreline runs from the root to t = 0.6
SKIRT_N = 16


def bake_skirts():
    """GateClouds/GateClouds_Skirts.json: per arm (GateArms_v4) its centreline from the root (object space, Unity: SKIRT_N
    points, the centroid of the vertices in each t bin) and the mean radius there, + its reveal keys (the gate bake);
    LanbaiGateClouds transforms the points every frame and finds where the arm crosses top - SKIRT_LEVEL"""
    global ARMS
    if ARMS is None:
        ARMS = np.load('/tmp/claude-0/seam/arms.npz')
    out = []
    for d in BAKE['inst']:
        name = d['id']
        if name + '_v' not in ARMS.files:
            continue
        V, T = ARMS[name + '_v'], ARMS[name + '_t']
        sc = float(LAY[name].get('scale', 1.0))
        pts, rad = [], []
        edges = np.linspace(0.0, SKIRT_TMAX, SKIRT_N + 1)
        for k in range(SKIRT_N):
            m = (T >= edges[k]) & (T < edges[k + 1] + 1e-6)
            if m.sum() < 3:
                continue
            P = V[m]
            cen = P.mean(0)
            # radius: the mean distance from the centroid, across the local axis (vertical in object space near the
            # root; for the bins higher up the arm leans, the error is the cos of the lean)
            r = float(np.sqrt(((P[:, [0, 2]] - cen[[0, 2]]) ** 2).sum(1)).mean())
            pts += [round(float(x), 3) for x in cen]          # object space (TransformPoint applies the scale)
            rad.append(round(r * sc, 2))                       # world metres
        rk = []
        if d['reveal_kind'] == 1:
            for tt, vv in zip(d['rev_t'], d['rev_v']):
                rk += [tt, vv]
        out.append(dict(id=name, pts=pts, r=rad, reveal=rk))
    J = dict(about='蓝白 gate clouds: the arms\' root centrelines for the cloud skirts (GateClouds/Source/seam_ref.py bake '
                   'from Gate/GateArms_v4.fbx LOD0; pts in object space (Unity axes, before the instance scale), r in world '
                   'metres (x the scale). Read by '
                   'LanbaiGateCloudsBuilder. Do not edit by hand.',
             level=SKIRT_LEVEL, climb=NEW['SkirtClimb'], width=NEW['SkirtW'], strength=NEW['SkirtK'], arms=out)
    path = os.path.join(D.KIT, 'GateClouds_Skirts.json')
    json.dump(J, open(path, 'w'), indent=1, ensure_ascii=False)
    print('wrote', path, len(out), 'arms')
    return J


SKJ = None


def skirts_runtime(t, arms_posed, eye):
    """LanbaiGateClouds.Skirts: every arm with a crossing of top - level; the 8 nearest to the bus; x, z, strength, r"""
    global SKJ
    if SKJ is None:
        SKJ = json.load(open(os.path.join(D.KIT, 'GateClouds_Skirts.json')))
    top = -D.h_bus(t)
    yl = top - SKJ['level']
    by = {d['id']: d for d in BAKE['inst']}
    cand = []
    for a in SKJ['arms']:
        d = by[a['id']]
        k = reveal(d, t) if a['reveal'] else 1.0
        if k <= 0.0:
            continue
        p, R = pose(d, t)
        P = (np.array(a['pts']).reshape(-1, 3) * float(LAY[a['id']].get('scale', 1.0))) @ R.T + p
        r = np.array(a['r'])
        hit = None
        if P[0, 1] >= yl:
            hit = (P[0], r[0])                    # the root stands above the level: the stretched stem is vertical
        else:
            for j in range(len(P) - 1):
                if P[j, 1] <= yl <= P[j + 1, 1]:
                    f = (yl - P[j, 1]) / max(P[j + 1, 1] - P[j, 1], 1e-4)
                    hit = (P[j] + (P[j + 1] - P[j]) * f, r[j] + (r[j + 1] - r[j]) * f)
                    break
        if hit is None:
            continue
        q, rr = hit
        cand.append((float(np.hypot(q[0] - eye[0], q[2] - eye[2])), float(q[0]), float(q[2]), float(rr), float(k)))
    cand.sort()
    return [(x, z, r, k) for _, x, z, r, k in cand[:8]]


def render_arm_passes(arms, cam, w, h):
    """Cycles: Position + Normal (Unity world) per pixel; NaN where no arm"""
    import bpy
    from mathutils import Matrix
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 1
    sc.cycles.use_denoising = False
    sc.cycles.device = 'CPU'
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.film_transparent = True
    sc.render.filter_size = 0.01
    sc.view_settings.view_transform = 'Standard'
    # the passes as EMISSION (Combined of a 1 spp render with a tiny filter = the value at the pixel centre); the pass
    # flags of the multilayer EXR do not come through Blender 5's bpy module
    mat = bpy.data.materials.new('pass')
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    em = nt.nodes.new('ShaderNodeEmission')
    outn = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], outn.inputs['Surface'])
    U2B = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])
    for name, V, F, p, R, s in arms:
        me = bpy.data.meshes.new(name)
        Vb = V @ U2B.T
        me.vertices.add(len(Vb))
        me.vertices.foreach_set('co', Vb.astype(np.float32).ravel())
        me.loops.add(len(F) * 3)
        me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel())
        me.polygons.add(len(F))
        me.polygons.foreach_set('loop_start', np.arange(0, len(F) * 3, 3, dtype=np.int32))
        me.update()
        for poly in me.polygons:
            poly.use_smooth = True
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        sc.collection.objects.link(ob)
    camd = bpy.data.cameras.new('cam')
    camd.sensor_fit = 'HORIZONTAL'
    camd.angle = math.radians(cam['hfov_deg'])
    camd.clip_start, camd.clip_end = 0.5, 20000.0
    co = bpy.data.objects.new('cam', camd)
    sc.collection.objects.link(co)
    sc.camera = co
    f = D.camera_rays(dict(cam, hfov_deg=1.0), 1, 1)[0][0, 0]          # forward
    yaw = math.radians(cam['look_yaw_deg'])
    right = np.array([math.cos(yaw), 0, -math.sin(yaw)])
    up = np.cross(f, right)
    Rb = np.stack([U2B @ right, U2B @ up, -(U2B @ f)], 1)
    M = np.eye(4)
    M[:3, :3] = Rb
    M[:3, 3] = U2B @ np.array(cam['pos'], float)
    co.matrix_world = Matrix(M.tolist())
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    import OpenEXR
    res = {}
    for key, sock in (('P', 'Position'), ('N', 'Normal')):
        for l in list(em.inputs['Color'].links):
            nt.links.remove(l)
        nt.links.new(geo.outputs[sock], em.inputs['Color'])
        out = '/tmp/claude-0/seam/_pass_%s.exr' % key
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        with OpenEXR.File(out) as fexr:
            ch = fexr.channels()
            k = [x for x in ch if x in ('RGBA', 'RGB')][0]
            res[key] = np.asarray(ch[k].pixels, np.float64)
    a = res['P'][..., 3]
    P = res['P'][..., :3] @ U2B.T
    N = res['N'][..., :3] @ U2B.T
    hit = a > 0.5
    P[~hit] = np.nan
    N[~hit] = np.nan
    return P, N, hit


# ============================================================================================ value noise (the shader's VNoise)
def vnoise(p):
    i = np.floor(p)
    f = p - i
    u = f * f * (3 - 2 * f)

    def h(q):
        q = np.mod(q * 0.1031, 1.0)
        q = q + (q * (q[..., [1, 2, 0]] + 33.33)).sum(-1, keepdims=True)
        return np.mod((q[..., 0] + q[..., 1]) * q[..., 2], 1.0)
    out = 0.0
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                wt = ((u[..., 0] if dx else 1 - u[..., 0]) * (u[..., 1] if dy else 1 - u[..., 1])
                      * (u[..., 2] if dz else 1 - u[..., 2]))
                out = out + h(i + np.array([dx, dy, dz])) * wt
    return out


def shade_arm(P, N, c, tear, new):
    """TentacleSway stand-in: returns colour (N, 3) and keep mask (clip)"""
    eye = c.eye
    Vd = P - eye
    dist = np.linalg.norm(Vd, axis=-1)
    V = Vd / dist[:, None]
    n = N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-6)
    n = np.where(((n * V).sum(-1) > 0)[:, None], -n, n)
    ndl = np.clip(n @ MOON, 0, 1)
    rim = (1 - np.clip(-(n * V).sum(-1), 0, 1)) ** 4 * np.clip(V @ MOON, 0, 1)
    col = ARM['Albedo'] * (ARM['MoonE'] * ndl[:, None] * VOL['MoonColor'] + ARM['Fill'])
    col = col + VOL['MoonColor'] * (ARM['Rim'] * rim)[:, None]
    top = c.top
    pN = P - c.origin
    keep = np.ones(len(P), bool)
    wet = np.zeros(len(P))
    if not new:
        keep &= P[:, 1] - top + OLD['Clip'] >= 0
        zd = P[:, 1] - top + (vnoise(pN / 18.0) - 0.5) * 30.0
        keep &= ss(-2.0, OLD['Dissolve'], zd) - vnoise(pN / 6.0 + 17.3) >= 0
        cf = ss(OLD['Fade'] + 3.0, -2.0, zd)
        col = col + (OLD['TopColor'] - col) * cf[:, None]
    else:
        keep &= P[:, 1] - top + NEW['RootClip'] >= 0
        # wet: the cloud IN FRONT of the skin (toward the eye: 3, 15, 40 m), so an arm seen through a gap stays dark
        # and one behind the cloud's lumps fades into them by their own shape (no level, no glass column)
        pout = P - V * NEW['WetTap0']
        d0 = density(pout, c, True)
        d1 = density(P - V * NEW['WetTap1'], c, True)
        d2 = density(P - V * NEW['WetTap2'], c, True)
        tau = (d0 * 9.0 + d1 * 18.0 + d2 * 30.0) * NEW['WetK']
        wet = NEW['WetMax'] * (1.0 - np.exp(-tau))
        facing = np.clip(V @ MOON, 0, 1) ** 5
        tgt = cloud_light(pout, c, tear, True, facing) * VOL['Gain']
        col = col * (1.0 + (NEW['UnderDark'] - 1.0) * ss(top - 160.0, top - 220.0, P[:, 1]))[:, None]
        col = col + (tgt - col) * wet[:, None]
    # LanbaiFog (the cloud-top extra; AFTER: the extra fades where the arm is wet, the cloud fogs itself)
    h = np.maximum(P[:, 1] - top, 0.0)
    rho = VOL['Fog'] * (1.0 + ARM['FogExtra'] * np.exp(-h / ARM['FogExtraH']) * (1.0 - wet))
    f = 1 - np.exp(-dist * rho)
    fc = np.minimum(f, ARM['Cap']) * np.exp(-h / ARM['CapH'])
    f = f + (fc - f) * ss(ARM['CapFrom'][0], ARM['CapFrom'][1], dist)
    fcol = fog_colour(V, c, tear)
    col = col * (1 - f)[:, None] + fcol * f[:, None]
    return col, keep, dist


# ============================================================================================ shots
SHOTS = {
    # the main seat's eye (GateLayout cameras U7 eye_bus_relative), forward
    'seat152': dict(t=152.0, pos=[0.55, 1.7, 2.05], look_yaw_deg=0.0, look_pitch_deg=-4.0, hfov_deg=90.0),
    'seat': dict(t=166.0, pos=[0.55, 1.7, 2.05], look_yaw_deg=0.0, look_pitch_deg=-6.0, hfov_deg=90.0),
    # the side windows, looking DOWN where the near arms come out of the cloud (Near_0 left, Near_1 / Near_2 right)
    'left': dict(t=168.0, pos=[-0.9, 1.7, 0.0], look_yaw_deg=-80.0, look_pitch_deg=-30.0, hfov_deg=90.0),
    'right': dict(t=168.0, pos=[0.9, 1.7, 0.0], look_yaw_deg=80.0, look_pitch_deg=-30.0, hfov_deg=90.0),
    # outside the bus: beside it, 70 m down, looking across at the near arms' roots and on to the hands
    'outside': dict(t=168.0, pos=[-130.0, -45.0, -30.0], look_yaw_deg=75.0, look_pitch_deg=-9.0, hfov_deg=80.0),
}


def render(shot, w, outdir):
    global TEX
    if TEX is None:
        TEX = density_tex()
    cam = dict(SHOTS[shot])
    t = cam['t']
    h = int(round(w * 9 / 16))
    eye = np.array(cam['pos'], float)
    tear = D.gate_origin(t) + np.array([0.0, -150.0 + 0.4 * 640.0, 19.0])
    V, _ = D.camera_rays(cam, w, h)
    res = {}
    for new in (False, True):
        arms = arm_meshes(t, new)
        c = Ctx(t, eye)
        if new:
            c.skirts = skirts_runtime(t, arms, eye)
        P, N, hit = render_arm_passes(arms, cam, w, h)
        Vf = V.reshape(-1, 3)
        scene_d = np.full(Vf.shape[0], np.inf)
        col = D.band(Vf, eye, tear) + D.moon_air(Vf)
        hf = hit.reshape(-1)
        ia = np.nonzero(hf)[0]
        acol, keep, dist = shade_arm(P.reshape(-1, 3)[ia], N.reshape(-1, 3)[ia], c, tear, new)
        ia_k = ia[keep]
        col[ia_k] = acol[keep]
        scene_d[ia_k] = dist[keep] * np.einsum('ij,ij->i', Vf[ia_k], Vf[ia_k]) ** 0.5
        s, tr = march(Vf, c, scene_d, new, tear)
        img = col * tr[:, None] + s
        res[new] = img.reshape(h, w, 3)
        print(shot, 'new' if new else 'old', 'arms', len(arms), 'skirts', len(c.skirts), flush=True)
    os.makedirs(outdir, exist_ok=True)
    A = D.grade(res[False]).astype(np.uint8)
    B = D.grade(res[True]).astype(np.uint8)
    Image.fromarray(A).save(os.path.join(outdir, 'seam_%s_before.png' % shot))
    Image.fromarray(B).save(os.path.join(outdir, 'seam_%s_after.png' % shot))
    np.save(os.path.join(outdir, 'seam_%s_lin.npy' % shot), np.stack([res[False], res[True]]).astype(np.float16))
    return A, B


# ---- the continuous views (总导演 / 阿白: in the bus, beside it, from under the cloud) ----------------------------------
def seq_cam(name, f, n):
    """frame f of n: (cam dict) -- t runs on, so the cloud's wind and the bus move as in Unity"""
    u = f / max(n - 1, 1)
    if name == 'seat_pan':          # the main seat's eye, panning from the left window to the right one
        t = 165.0 + 3.0 * u
        return dict(t=t, pos=[0.55, 1.7, 2.05], look_yaw_deg=-85.0 + 170.0 * u, look_pitch_deg=-12.0, hfov_deg=90.0)
    if name == 'side_out':          # outside, beside the bus (left), tracking forward past the near arms
        t = 166.0 + 4.0 * u
        return dict(t=t, pos=[-130.0, -45.0, -110.0 + 180.0 * u], look_yaw_deg=75.0, look_pitch_deg=-9.0, hfov_deg=80.0)
    if name == 'below':             # under the deck's floor, looking up at the roots, panning
        t = 166.0 + 4.0 * u
        top = -D.h_bus(t)
        return dict(t=t, pos=[-90.0, top - 300.0, -60.0], look_yaw_deg=10.0 + 100.0 * u, look_pitch_deg=38.0, hfov_deg=90.0)
    raise KeyError(name)


def render_seq(name, n, w, outdir):
    import shutil
    import subprocess
    os.makedirs(outdir, exist_ok=True)
    for f in range(n):
        SHOTS['_seq'] = seq_cam(name, f, n)
        render('_seq', w, outdir)
        for k in ('before', 'after'):
            shutil.move(os.path.join(outdir, 'seam__seq_%s.png' % k), os.path.join(outdir, '%s_%s_%03d.png' % (name, k, f)))
        os.remove(os.path.join(outdir, 'seam__seq_lin.npy'))
    # side by side (left = now, right = D-44 #3) at 8 fps, and a contact strip of every 4th frame
    for f in range(n):
        A = Image.open(os.path.join(outdir, '%s_before_%03d.png' % (name, f)))
        B = Image.open(os.path.join(outdir, '%s_after_%03d.png' % (name, f)))
        o = Image.new('RGB', (A.width * 2 + 4, A.height), (255, 0, 0))
        o.paste(A, (0, 0))
        o.paste(B, (A.width + 4, 0))
        o.save(os.path.join(outdir, '%s_sbs_%03d.png' % (name, f)))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '8', '-i', os.path.join(outdir, name + '_sbs_%03d.png'),
                    '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-pix_fmt', 'yuv420p', '-crf', '18',
                    os.path.join(outdir, name + '.mp4')], check=True)
    pick = list(range(0, n, 4))
    A = Image.open(os.path.join(outdir, '%s_sbs_%03d.png' % (name, 0)))
    strip = Image.new('RGB', (A.width, (A.height + 4) * len(pick)), (255, 0, 0))
    for i, f in enumerate(pick):
        strip.paste(Image.open(os.path.join(outdir, '%s_sbs_%03d.png' % (name, f))), (0, i * (A.height + 4)))
    strip.save(os.path.join(outdir, name + '_strip.png'))
    print('seq', name, n, 'frames ->', os.path.join(outdir, name + '.mp4'))


if __name__ == '__main__':
    a = sys.argv[1:]
    w = int(a[a.index('--w') + 1]) if '--w' in a else 960
    outdir = a[a.index('--out') + 1] if '--out' in a else '/tmp/claude-0/seam/out'
    for k, v in (x.split('=') for x in (a[a.index('--set') + 1].split(',') if '--set' in a else [])):
        NEW[k] = float(v)
    if a[0] == 'seq':                 # seq <name> [--n 24]
        n = int(a[a.index('--n') + 1]) if '--n' in a else 24
        render_seq(a[1], n, w, outdir)
        sys.exit(0)
    if a[0] == 'bake':
        bake_skirts()
        sys.exit(0)
    shots = list(SHOTS) if a[0] == 'all' else [a[0]]
    for s in shots:
        render(s, w, outdir)
