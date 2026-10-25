"""蓝白 · 白铜镜的 numpy 移植：驱动的逻辑（MirrorSchedule.json → 每面镜此刻的高度、可见度、凝聚、溶解）+
Lanbai/BronzeMirror、Lanbai/MirrorStars、Lanbai/MirrorDust 的数学（同名、同数），画在第 9 幕的天上
（天 = Act09_StarSea/Tools~/act09_renders.py 的同一套：Sky 的 CPU shader + 星表 + S9a/S9b 调色，总导演 10-24 第 1 条）。

    from mirror_port import frame
    codes, info = frame(t, yaw, pitch, w=960, h=540)       # sRGB 码值 (h, w, 3)，info = 量出的数

不是 Unity：没有车厢（标准台的车壳另合成）、反射没有粗糙度模糊（抛光纹在 Unity 里只改光滑度）。
镜背、镜缘乳钉、铭文 / 栉齿 / 锯齿 / 流云带读真贴图（back_port.py，r3 #6）。
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Act09_StarSea', 'Tools~'))
sys.path.insert(0, os.path.join(REPO, 'Sky', 'Tools~', 'render'))
import act09_renders as A9                      # noqa: E402  (state(t), the sky material and globals)
import sky_cpu as S, grade as G, stars_cpu as SC   # noqa: E402
from shader_cpu import camera_dirs              # noqa: E402
import back_port as BP                           # noqa: E402

SCH = json.load(open(os.path.join(REPO, 'Mirrors', 'MirrorSchedule.json'), encoding='utf-8'))
WHITE = json.load(open(os.path.join(REPO, 'Act10_White', 'WhiteSchedule.json'), encoding='utf-8'))
EYE = np.array(SCH['conventions']['eye'])
# spec §1 / LanbaiMirror.cginc
FACE_R, SAG, RHO = 0.48, 0.015, 7.6875
F0_FACE = G.hexlin('#D6CCB4'); F0_RIM = G.hexlin('#C9A873')
BACK_ALB = G.hexlin('#4F7A66'); AMB_GND = G.hexlin('#0E1830')
BACK_FILL = np.array([0.0105, 0.027, 0.0164])   # = _BackFill: the silhouette reads #16302A under S9a/S9b
EDGE = G.hexlin('#CDBF9C') * 0.8
BREAK_AMP, EDGE_W, APPEAR_S = 5.0, 0.3, 3.0
TONE = np.array([1.262, 0.974, 0.484])     # solved so that S9a / S9b show #CDBF9C (review r1 #5)
BRONZE_TONE = 1.0
RIM_SCHEME = 'JSON'       # the schedule's rim_soft; mirror13_study.py overrides it for the comparison schemes
RIM_SOFT_FROM = {'A': 0.80, 'C': 0.55, 'D': 0.55, 'E': 0.35, 'F': 0.25, 'G': 0.25, 'H': 0.80, 'JSON': 0.35}
FAR_UNTIL, FAR_SECONDS, FAR_DIM = 1135.31, 4.0, float(os.environ.get('FAR_DIM', 0.6))   # = LanbaiMirrorsDriver farUntil / farSeconds / farDim (M-4)
RIM_GLOW = float(os.environ.get('RIM_GLOW', 0.06)) * np.array([0.8, 0.9, 1.0])   # = LanbaiMirrorsDriver rimGlow: mirror 13's ring while far (bible: rim screen luma 60-90, #4E545E)


# ------------------------------------------------------------------------------------------------- driver logic
def herm(kn, t):
    kn = np.asarray(kn, float)
    x, y, m = kn[:, 0], kn[:, 1], kn[:, 2]
    t = min(max(t, x[0]), x[-1])
    i = min(max(np.searchsorted(x, t) - 1, 0), len(x) - 2)
    h = x[i + 1] - x[i]; s = (t - x[i]) / h
    return ((2 * s ** 3 - 3 * s ** 2 + 1) * y[i] + (s ** 3 - 2 * s ** 2 + s) * h * m[i] + (-2 * s ** 3 + 3 * s ** 2) * y[i + 1]
            + (s ** 3 - s ** 2) * h * m[i + 1])


def lin_knots(kn, t):
    kn = np.asarray(kn, float)
    return float(np.interp(t, kn[:, 0], kn[:, 1]))


def mirror_state(m, t):
    """what LanbaiMirrorsDriver computes for mirror m at time t (None = renderer off)."""
    ov = OVERRIDE.get(m['index'])                                # lookdev only (render_r6.py): freeze dissolve / appear
    st = _mirror_state(m, t)
    if st is not None and ov:
        st.update(ov)
    return st


OVERRIDE = {}


def _mirror_state(m, t):
    a0, a1 = m['active']
    if not (a0 <= t <= a1):
        return None
    D = m['diameter_m']; R = D / 2
    y_car = herm(m['motion']['knots'], t)
    cx, cz = m['centre_xz']
    r_car = math.hypot(EYE[0] - cx, EYE[2] - cz) / D             # object units
    f = lambda r: math.sqrt(RHO * RHO - r * r) - (RHO - SAG)
    y_edge = y_car - f(min(r_car, FACE_R)) * D                  # world y of the face edge (object y = 0)
    vis = lin_knots(m['visibility_knots'], t)
    join = m['visibility_knots'][0][0]
    appear = min(max((t - join) / APPEAR_S, 0), 1)
    dis = 0.0 if m['dissolve'] is None else min(max((t - m['t_cross']) / (m['dissolve']['end'] - m['t_cross']), 0), 1)
    extra = 0.0
    if m['index'] == 13:
        extra = lin_knots(WHITE['mirror13_face_extra']['EV_knots'], t)
    rimsoft = 0.0
    if m['index'] == 13:
        rs = m.get('rim_soft') if RIM_SCHEME == 'JSON' else None
        if RIM_SCHEME == 'JSON':   # 终审 M-4: no soft rim (the bible's rim is a lit ring, luma 60-90); the far state is 'far' below
            rimsoft = 0.0
        elif RIM_SCHEME == 'H':
            rimsoft = 1.0 - min(max((t - 1135.31) / 4.0, 0), 1)
        elif RIM_SCHEME == 'G':
            rimsoft = 1.0 - min(max((t - 1142.9) / 1.0, 0), 1)
        elif RIM_SCHEME == 'F':
            rimsoft = 1.0 - min(max((t - 1143.6) / 1.0, 0), 1)
        elif RIM_SCHEME == 'E':
            rimsoft = 1.0 - min(max((t - 1143.3) / 1.0, 0), 1)
        elif RIM_SCHEME == 'D':
            rimsoft = 1.0 - min(max((t - 1142.9) / 1.0, 0), 1)
        elif RIM_SCHEME == 'C':
            rimsoft = 1.0 - min(max((t - 1145.5) / 2.0, 0), 1)
        else:
            rimsoft = 1.0 - min(max((t - (m['t_cross'] - 10.0)) / 4.0, 0), 1)
    return dict(D=D, R=R, c=np.array([cx, y_edge, cz]), y_car=y_car, vis=vis, appear=appear, dissolve=dis, extra=extra,
                k=m['emission_k'], index=m['index'], rimsoft=rimsoft,
                far=(1.0 - min(max((t - FAR_UNTIL) / FAR_SECONDS, 0), 1)) if (m['index'] == 13 and RIM_SCHEME == 'JSON') else 0.0)


def pulse_ev(t):
    ev = 0.0
    for m in SCH['mirrors']:
        if m['pulse_EV'] <= 0:
            continue
        x = t - m['t_cross']
        if -0.08 < x <= 0:
            ev = max(ev, 0.35 * (x + 0.08) / 0.08)
        elif 0 < x < 0.35:
            ev = max(ev, 0.35 * (1 - x / 0.35))
    return ev


def white_sat(t):
    if not (WHITE['labels']['mirror12'] <= t < WHITE['labels']['F16_cut2']):
        return 0.0
    return lin_knots(WHITE['white_sat']['knots'], t)


def white_bloom(t):
    if not (WHITE['labels']['mirror12'] <= t < WHITE['labels']['F16_cut2']):
        return 0.0
    return lin_knots(WHITE['white_bloom']['knots'], t)


_GD = None


def grade_white(img, sid, ev, sat_w, bloom_w):
    """G.grade with the WHITE_SAT (saturation -30) and WHITE_BLOOM (intensity 12, threshold 0.8, knee 0.8, diffusion 9)
    helper volumes blended in by weight, the way PPv2 interpolates a global volume's overridden parameters (r3 C3)."""
    global _GD
    if _GD is None:
        _GD = {e['id']: e for e in json.load(open(os.path.join(REPO, 'Grading', 'Tools~', 'compile_check', 'dump.json'), encoding='utf-8'))['entries']}
    if sat_w <= 0 and bloom_w <= 0:
        return G.grade(img, sid, ev=ev)
    p = G.profile(sid)
    p['postExposure'] = p.get('postExposure', 0) + ev
    p['saturation'] = p.get('saturation', 0) * (1 - sat_w) + _GD['WHITE_SAT']['saturation'] * sat_w
    bp = G.bloom_params(sid)
    wb = _GD['WHITE_BLOOM']
    for k, kk in (('bloomIntensity', 'intensity'), ('bloomThreshold', 'threshold'), ('bloomSoftKnee', 'softKnee'), ('bloomDiffusion', 'diffusion')):
        bp['bloom'][kk] = bp['bloom'][kk] * (1 - bloom_w) + wb[k] * bloom_w
    x = img.astype(np.float64)
    x = x + G.LD.bloom_layer(x, G.LD.full(bp))
    return G.E.codes(x, p, G.E.bake_lut(p))


def white_ev(t):
    return lin_knots(WHITE['exposure']['dEV_knots'], t) if t < WHITE['labels']['F16_cut2'] else 0.0


# ------------------------------------------------------------------------------------------------- shader maths
def _hash(p):
    p = np.mod(p * 0.1031, 1.0)
    p = p + np.sum(p * (p[..., [1, 2, 0]] + 33.33), -1, keepdims=True)
    return np.mod((p[..., 0] + p[..., 1]) * p[..., 2], 1.0)


def noise(x):
    i = np.floor(x); f = x - i; u = f * f * (3 - 2 * f)
    def h(o):
        return _hash(i + np.array(o, float))
    nx00 = h((0, 0, 0)) * (1 - u[..., 0]) + h((1, 0, 0)) * u[..., 0]
    nx10 = h((0, 1, 0)) * (1 - u[..., 0]) + h((1, 1, 0)) * u[..., 0]
    nx01 = h((0, 0, 1)) * (1 - u[..., 0]) + h((1, 0, 1)) * u[..., 0]
    nx11 = h((0, 1, 1)) * (1 - u[..., 0]) + h((1, 1, 1)) * u[..., 0]
    return (nx00 * (1 - u[..., 1]) + nx10 * u[..., 1]) * (1 - u[..., 2]) + (nx01 * (1 - u[..., 1]) + nx11 * u[..., 1]) * u[..., 2]


def fbm(pM):
    return (noise(pM / 8.0) * 0.55 + noise(pM / 2.7 + 17.1) * 0.30 + noise(pM / 0.9 + 41.7) * 0.15) * 2 - 1


def _hash2(p):
    q = np.stack([p[..., 0], p[..., 1], p[..., 0]], -1) * np.array([0.1031, 0.1030, 0.0973])
    q = q - np.floor(q)
    q = q + (q * (q[..., [1, 2, 0]] + 33.33)).sum(-1, keepdims=True)
    a = (q[..., [0, 0]] + q[..., [1, 2]]) * q[..., [2, 1]]
    return a - np.floor(a)


def cells(x):
    """LanbaiMirrorCells: F1, F2, id of a 2D Voronoi (3 x 3 neighbourhood)."""
    i = np.floor(x); f = x - i
    F1 = np.full(x.shape[:-1], 8.0); F2 = np.full(x.shape[:-1], 8.0); ID = np.zeros(x.shape[:-1])
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            g = np.array([dx, dy], float)
            o = _hash2(i + g)
            d = np.linalg.norm(g + o - f, axis=-1)
            idn = (o[..., 0] * 7.31 + o[..., 1] * 3.17) % 1.0
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d)); ID = np.where(closer, idn, ID); F1 = np.where(closer, d, F1)
    return F1, F2, ID


def breakup(sd, xz, cellM, bandM):
    """LanbaiMirrorBreakup (终审 M-3)."""
    glow = np.zeros_like(sd)
    m = (sd > 0) & (sd < bandM)
    if not m.any():
        return sd, glow
    s = sd[m] / bandM
    F1, F2, ID = cells(xz[m] / cellM)
    edge = (F2 - F1) * 0.5
    gap = 0.18 * (1 - s) ** 2
    gone = ID - (s * 1.3 - 0.1)
    keep = np.minimum(edge - gap, -gone)
    g = (1 - s) * np.clip(1 - (edge - gap) / 0.06, 0, 1) * (keep >= 0)
    out = sd.copy(); out[m] = np.where(keep >= 0, sd[m], -1.0)
    glow[m] = g
    return out, glow


def schlick(f0, c):
    m = 1 - np.clip(c, 0, 1)
    return f0 + (1 - f0) * (m ** 5)[..., None]


_GLOW = [False]


def sky(dirs, mat, gl):
    if not _GLOW[0]:
        S.renderer().tex.clear(); S.set_tex('_GlowTex', S.load_glow(1)); _GLOW[0] = True
    return S.render(dirs.reshape(-1, 3).astype(np.float32), mat, gl).reshape(dirs.shape)


_BLUR = {}


_CUBE = {}


def sky_broad(dirs, mat, gl, key):
    """the back's 'sky behind' (终审 M-2): floor + gain x scale x cube(V)^2, the same pole-free cube as the shader
    (Mirrors/Textures/T_MirrorBackSky_Cube.png, bake_back_sky.py)."""
    if not _CUBE:
        from PIL import Image
        im = np.asarray(Image.open(os.path.join(REPO, 'Mirrors', 'Textures', 'T_MirrorBackSky_Cube.png')), np.float32) / 255.0
        n = im.shape[0] // 3
        pos = {0: (1, 2), 1: (1, 0), 2: (0, 1), 3: (2, 1), 4: (1, 1), 5: (1, 3)}
        _CUBE['faces'] = [im[r * n:(r + 1) * n, c * n:(c + 1) * n] for f, (r, c) in sorted(pos.items())]
        _CUBE['scale'] = json.load(open(os.path.join(REPO, 'Mirrors', 'Docs~', 'T_MirrorBackSky_Cube.json')))['scale']
    d = dirs / np.linalg.norm(dirs, axis=-1, keepdims=True)
    ax = np.abs(d); n = _CUBE['faces'][0].shape[0]
    out = np.zeros(len(d))
    major = np.argmax(ax, -1)
    for f in range(6):
        a = f // 2; sgn = 1 if f % 2 == 0 else -1
        m = (major == a) & (np.sign(d[:, a]) == sgn)
        if not m.any():
            continue
        x, y, z = d[m, 0], d[m, 1], d[m, 2]
        if f == 0: u, v = -z / x, -y / x
        elif f == 1: u, v = -z / x, y / x
        elif f == 2: u, v = x / y, z / y
        elif f == 3: u, v = -x / y, z / y
        elif f == 4: u, v = x / z, -y / z
        else: u, v = x / z, y / z
        iu = np.clip(((u + 1) / 2 * n).astype(int), 0, n - 1); iv = np.clip(((v + 1) / 2 * n).astype(int), 0, n - 1)
        out[m] = _CUBE['faces'][f][iv, iu]
    floor = MP_floor(gl, mat) @ np.array([0.2126, 0.7152, 0.0722])
    gain = gl['_Udon_GalaxyGain'][0]
    return np.maximum(floor, gain * _CUBE['scale'] * out * out)


def MP_floor(gl, mat):
    """the star floor: in the port, the port sky itself at galaxy gain 0 (its _Udon_ZenithColor is not what the port's sky
    draws; Unity's shader reads _Udon_ZenithColor, which act 9 writes as that same floor)."""
    return sky(np.array([[0.0, 1.0, 0.0]]), mat, dict(gl, _Udon_GalaxyGain=[0.0, 0, 0, 1]))[0]


# ------------------------------------------------------------------------------------------------- the frame
def frame(t, yaw=0.0, pitch=0.0, w=960, h=540, ss=1, cabin=None, dust=True, extra_ev=None, eye=None, fov=90.0, white=True):
    EYE = np.array(eye, float) if eye is not None else globals()['EYE']
    gl, mat, star, first, prof = A9.state(t)
    W, H = w * ss, h * ss
    d = camera_dirs(W, H, fov, yaw, pitch).reshape(H, W, 3).astype(np.float64)
    img = sky(d, mat, gl)
    depth = np.full((H, W), np.inf)
    owner = np.full((H, W), -1)
    face_mask = {}
    info = dict(t=t, mirrors=[])
    states = [(m, mirror_state(m, t)) for m in SCH['mirrors']]
    pxang = math.radians(fov) / W
    for m, st in states:
        if st is None:
            continue
        D, R, c = st['D'], st['R'], st['c']
        Cs = c + np.array([0, (SAG - RHO) * D, 0])               # face sphere centre
        rho = RHO * D
        # ray / sphere (from the eye)
        oc = EYE - Cs
        b = (d * oc).sum(-1); cc = (oc * oc).sum() - rho * rho
        disc = b * b - cc
        sq = np.sqrt(np.maximum(disc, 0))
        tn = -b - sq
        under = tn <= 0                                          # the eye is inside the face sphere: the face is seen from below
        tt = np.where(under, -b + sq, tn)
        hit = (disc > 0) & (tt > 0) & ~under                     # Cull Back: inside the slab the eye sees through it
        P = EYE + d * tt[..., None]
        rr = np.hypot(P[..., 0] - c[0], P[..., 2] - c[2])
        face = hit & (rr <= FACE_R * D) & (P[..., 1] >= c[1] - 1e-6)
        # rim band (annulus plane at the band top) and the back (plane at the field, seen from below)
        yb = c[1] + 0.002 * D
        tb = (yb - EYE[1]) / np.where(np.abs(d[..., 1]) > 1e-9, d[..., 1], 1e-9)
        Pb = EYE + d * tb[..., None]; rb = np.hypot(Pb[..., 0] - c[0], Pb[..., 2] - c[2])
        band = (tb > 0) & (rb >= FACE_R * D) & (rb <= 0.5 * D) & (EYE[1] > yb)
        yk = c[1] - 0.015 * D
        tk = (yk - EYE[1]) / np.where(np.abs(d[..., 1]) > 1e-9, d[..., 1], 1e-9)
        Pk = EYE + d * tk[..., None]; rk = np.hypot(Pk[..., 0] - c[0], Pk[..., 2] - c[2])
        back = (tk > 0) & (rk <= 0.5 * D) & (EYE[1] < yk)       # only from below (Cull Back)
        # the knob (终审 M-1: it was never drawn): the mesh's superellipse dome, base radius 0.065 D, hanging 0.05 D below
        # the back, as a half ellipsoid (radii 0.065 D, 0.05 D) under the back plane
        ka, kb = 0.065 * D, 0.05 * D
        kc = np.array([c[0], yk, c[2]])
        sc_ = np.array([1.0 / ka, 1.0 / kb, 1.0 / ka])
        o_ = (EYE - kc) * sc_; dd_ = d * sc_
        qa = (dd_ * dd_).sum(-1); qb = (o_ * dd_).sum(-1); qc = (o_ * o_).sum() - 1.0
        kd = qb * qb - qa * qc
        tkn = (-qb - np.sqrt(np.maximum(kd, 0))) / np.maximum(qa, 1e-12)
        Pkn = EYE + d * tkn[..., None]
        knob = (kd > 0) & (tkn > 0) & (Pkn[..., 1] <= yk + 1e-6)
        rkn = np.hypot(Pkn[..., 0] - c[0], Pkn[..., 2] - c[2])
        # dissolve / appear front (object-anchored noise, metres)
        def keep(Pw, rM):
            sc = max(1.0, R / 40.0)                             # the breakup grows with the mirror (shader MirrorFront, r3 #5)
            pM = (Pw - c) / sc
            amp = BREAK_AMP * sc
            n1 = fbm(pM); n2 = fbm(pM + 71.3)
            sdD = (R + amp - st['dissolve'] * (R + 2 * amp)) - (rM + amp * n1)
            sdA = (-amp + st['appear'] * (R + 2 * amp)) - (rM + amp * n2)
            cg = np.zeros_like(sdD)
            if st['dissolve'] > 0.0005:                         # 终审 M-3: the breakup band (LanbaiMirrorBreakup)
                sdD, cg = breakup(sdD, (Pw - c)[..., [0, 2]], 1.2 * sc, 3.0 * amp)
            sd = np.minimum(sdD, sdA)
            act = float(st['dissolve'] > 0.0005 or st['appear'] < 0.9995)
            return sd > 0, np.maximum(np.clip(1 - sd / EDGE_W, 0, 1) * act, cg)
        for kind, mask, Pw, rM, tdist in (('face', face, P, rr, tt), ('band', band, Pb, rb, tb), ('back', back, Pk, rk, tk),
                                          ('knob', knob, Pkn, rkn, tkn)):
            if not mask.any():
                continue
            ok, edge = keep(Pw[mask], rM[mask])
            sel = np.zeros_like(mask); sel[mask] = ok
            nearer = sel & (tdist < depth)
            if not nearer.any():
                continue
            idx = nearer[mask]
            Pn = Pw[nearer]; dn = d[nearer]
            if kind == 'face' and under.any() and under[nearer].all():
                col = np.broadcast_to(BACK_FILL + BACK_ALB * AMB_GND, dn.shape).copy()
            elif kind == 'face':
                n = Pn - Cs; n /= np.linalg.norm(n, axis=-1, keepdims=True)
                rdir = dn - 2 * (dn * n).sum(-1, keepdims=True) * n
                sk = sky(rdir, mat, gl)
                if st.get('far', 0) > 0:                         # M-4: the far disc's reflection is blurred (_FaceSoft)
                    bl = sky_broad(rdir, mat, gl, round(t, 3))
                    lum = sk @ np.array([0.2126, 0.7152, 0.0722])
                    sk = sk * ((1 - st['far']) + st['far'] * bl / np.maximum(lum, 1e-6))[:, None]
                F = schlick(F0_FACE, -(dn * n).sum(-1))
                col = sk * F + sk * (st['k'] * st['vis'] * 2 ** st['extra'])
                lum = col @ np.array([0.2126, 0.7152, 0.0722])
                col = lum[:, None] * (1 - BRONZE_TONE + BRONZE_TONE * TONE[None, :]) * (1 - (1 - FAR_DIM) * st.get('far', 0))   # white-bronze tone; M-4 far dim (#CDBF9C), chroma from the tone only (r3: a blue/warm mix went lavender)
            elif kind == 'band':                                  # 连珠乳钉: LanbaiMirrorBeadNormalOS
                fp = tdist[nearer] * pxang / np.maximum(np.abs(dn[:, 1]), 0.05)
                n, cover = BP.bead_normal(Pn - c, D, fp)
                rdir = dn - 2 * (dn * n).sum(-1, keepdims=True) * n
                col = sky(rdir, mat, gl) * schlick(F0_RIM, -(dn * n).sum(-1))
                if st.get('far', 0) > 0:                         # M-4: the far ring glows cool grey (_RimGlow x far)
                    col = col + RIM_GLOW[None, :] * st['far']
            else:                                                 # opaque bronze, luminance following the sky behind (r3 #5)
                fp = tdist[nearer] * pxang / np.maximum(np.abs(dn[:, 1]), 0.05)
                Lsky = sky_broad(dn, mat, gl, round(t, 3))
                col = BP.back_color(Pn - c, D, fp, Lsky)
            if kind == 'knob':
                Lsky = sky_broad(dn, mat, gl, round(t, 3))
                nk = (Pn - kc) * sc_ * sc_; nk /= np.linalg.norm(nk, axis=-1, keepdims=True)
                col = BP.knob_color(nk, Lsky)
            near = np.clip((tdist[nearer] - 5.0) / 20.0, 0, 1)
            col = col + EDGE * (edge[idx] * near)[:, None]
            if st['rimsoft'] > 0:                                # only the comparison schemes (D-38 / r3 C4: none in the schedule)
                s0 = RIM_SOFT_FROM.get(RIM_SCHEME, 0.80)
                soft = np.clip((rM[nearer] / (0.5 * D) - s0) / (1.0 - s0), 0, 1)
                soft = soft * soft * (3 - 2 * soft) * st['rimsoft']
                col = col * (1 - soft[:, None]) + img[nearer] * soft[:, None]
            img[nearer] = col
            depth[nearer] = tdist[nearer]
            owner[nearer] = st['index'] * 10 + {'face': 0, 'band': 1, 'back': 2, 'knob': 3}[kind]
        face_mask[st['index']] = (st, Cs, rho)
        info['mirrors'].append(dict(index=st['index'], y_car=round(st['y_car'], 2), vis=round(st['vis'], 3),
                                    appear=round(st['appear'], 3), dissolve=round(st['dissolve'], 3), extra_EV=round(st['extra'], 3)))
    # stars: the sky's own stars where the sky is visible, and their convex-mirror images inside each face (MirrorStars)
    cat = SC.catalogue()
    fw_true = A9.FWHM * w / 960 * ss * 90.0 / fov
    fw = max(fw_true, 1.6)                  # never sub-pixel (a sub-pixel splat swings in brightness as it crosses pixels) ...
    flux_k = (fw_true / fw) ** 2            # ... but the FLUX is kept: a star blown up to 1.6 px is dimmer by the area (r3 C2)
    if star['gain'] > 0:
        pk = SC.flux(cat['mag'], cat['rank'], 1.6, 0.0, 0.5, star['count'], star['boost']) * star['gain'] * flux_k
        sky_layer = np.zeros_like(img)
        SC.splat(sky_layer, W, H, fov, yaw, pitch, cat['dir'], pk, cat['col'], fw)
        img += sky_layer * (owner < 0)[..., None]
        for idx, (st, Cs, rho) in (face_mask.items() if not os.environ.get('NO_REFL_STARS') else []):
            dd = cat['dir']
            # convex-mirror image (same as Lanbai/MirrorStars): start from the flat mirror, then refine with the normal at
            # the hit point: v = reflect(d, n) is the look direction, P = ray(E, v) on the face sphere, n = normal at P
            n = np.broadcast_to(np.array([0, 1.0, 0]), dd.shape).copy()
            oc = EYE - Cs
            cc = (oc * oc).sum() - rho * rho
            for k in range(12):
                v = dd - 2 * (dd * n).sum(-1, keepdims=True) * n
                b = (v * oc).sum(-1)
                tq = -b - np.sqrt(np.maximum(b * b - cc, 0))
                P = EYE + v * tq[:, None]
                if k < 11:                                       # damped (the plain iteration oscillates near grazing)
                    n = 0.5 * n + 0.5 * (P - Cs) / rho
                    n /= np.linalg.norm(n, axis=-1, keepdims=True)
            n = (P - Cs) / rho; toE = EYE - P; toE /= np.linalg.norm(toE, axis=-1, keepdims=True)
            rr_ = -toE - 2 * ((-toE) * n).sum(-1, keepdims=True) * n
            ok = ((dd * n).sum(-1) > 0) & ((toE * n).sum(-1) > 0)
            ce = (rr_ * dd).sum(-1)
            conv = np.clip((ce - math.cos(math.radians(1.0))) / (math.cos(math.radians(0.3)) - math.cos(math.radians(1.0))), 0, 1)
            F = schlick(F0_FACE, (n * toE).sum(-1))
            graze = np.clip(((toE * n).sum(-1) - 0.03) / 0.12, 0, 1); graze = graze * graze * (3 - 2 * graze)
            gain = (F + st['k'] * st['vis'] * 2 ** st['extra']) * (conv * graze * (1 - st.get('far', 0)))[:, None]   # M-4: no sharp star images in the blurred far disc   # unconverged / grazing images fade (flash sequence wf_H)
            gain = (gain @ np.array([0.2126, 0.7152, 0.0722]))[:, None] * (1 - BRONZE_TONE + BRONZE_TONE * TONE[None, :])
            appd = -toE                                          # the image's direction from the eye
            layer = np.zeros_like(img)
            SC.splat(layer, W, H, fov, yaw, pitch, appd[ok], pk[ok], cat['col'][ok] * gain[ok], fw)
            img += layer * (owner == idx * 10)[..., None]
    # dust (Lanbai/MirrorDust, closed form)
    if dust:
        for m in SCH['mirrors'][:12]:
            x = t - m['t_cross']
            if not (0 <= x <= m['dissolve']['end'] - m['t_cross'] + 4.0):
                continue
            D = m['diameter_m']; R = D / 2; cx, cz = m['centre_xz']
            rng = np.random.default_rng(1000 + m['dissolve']['dust_slot'])
            u1, u2, u3, u4 = rng.random((4, 250))
            a = 2 * np.pi * u2
            car = np.array([EYE[0] - cx, EYE[2] - cz])
            nearP = car[None, :] + np.stack([np.cos(a), np.sin(a)], -1) * (np.sqrt(u1) * min(60.0, R))[:, None]
            anyP = np.stack([np.cos(a), np.sin(a)], -1) * (np.sqrt(u1) * R)[:, None]
            p = np.where((u3 < 0.9)[:, None], nearP, anyP)   # 终审 M-3: 90 % within 60 m
            l = np.linalg.norm(p, axis=-1); p = np.where((l > 0.985 * R)[:, None], p * (0.985 * R / np.maximum(l, 1e-6))[:, None], p)
            q = np.linalg.norm(p, axis=-1) / R
            tb = m['t_cross'] + 2.0 * (1 - q); age = t - tb
            alive = (age >= 0) & (age <= 4.0)
            vrise = m['speed_cross_mps']
            yb = EYE[1] + vrise * np.maximum(tb - m['t_cross'], 0)
            pos = np.stack([cx + p[:, 0], yb + 0.6 * (0.6 + 0.4 * u4) * age, cz + p[:, 1]], -1)
            xx = np.clip(age / 4.0, 0, 1)
            br = np.clip(age / 0.25, 0, 1) * (1 - xx) ** 2
            col = G.hexlin('#CDBF9C')[None, :] * (1 - xx[:, None]) + G.hexlin('#F2F6FF')[None, :] * xx[:, None]
            dirs = pos - EYE; dist = np.linalg.norm(dirs, axis=-1); dirs /= dist[:, None]
            rmin = 1.4 / 1.4133 * pxang * dist
            peak = 6.0 * np.minimum(0.05 / rmin, 1) ** 2 * br * alive * np.clip((dist - 0.3) / 0.7, 0, 1)
            layer = np.zeros_like(img)
            SC.splat(layer, W, H, fov, yaw, pitch, dirs, peak, col, fw)
            img += layer
    if cabin is not None:
        img = cabin(img, d, yaw, pitch)
    if ss > 1:
        img = img.reshape(h, ss, w, ss, 3).mean((1, 3))
    ev = (pulse_ev(t) + white_ev(t)) if extra_ev is None else extra_ev
    a, b, wgt = prof
    sw, bw = (white_sat(t), white_bloom(t)) if white else (0.0, 0.0)
    ca = np.clip(grade_white(img, a, ev, sw, bw), 0, 255)
    cb = ca if b == a else np.clip(grade_white(img, b, ev, sw, bw), 0, 255)
    info['WHITE_SAT'] = round(sw, 3); info['WHITE_BLOOM'] = round(bw, 3)
    codes = ca * (1 - wgt) + cb * wgt
    info['APL'] = round(G.apl(codes), 1)
    info['EV'] = round(ev, 3)
    info['owner'] = owner if ss == 1 else owner[::ss, ::ss]
    return codes, info


if __name__ == '__main__':
    from PIL import Image
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 1030.4
    yaw = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    pitch = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    c, info = frame(t, yaw, pitch)
    out = sys.argv[4] if len(sys.argv) > 4 else '/tmp/mirror_%.2f.png' % t
    Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).save(out)
    print(out, info['APL'], info['mirrors'])
