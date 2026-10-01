"""Tear kit v2 meshes as plain numpy data (kit space, full opening). Shared by build_kit.py (FBX) and render_tear.py.

Per-vertex data contract (what Lanbai_Tear.shader reads; Unity names in brackets):
  UV0 [texcoord0]  texture UV
  UV1 [texcoord1]  x = a_hinge: across offset (m, full opening) of the point this vertex hangs from.
                       The shader moves the vertex by _TearAcrossOS * a_hinge * (w - 1), w = width(_Udon_TearOpen)/30 %.
                       (the lens uses its own across coordinate: it simply scales across.)
                   y = phase 0..1 (fibre sway / flap flutter / halo breathing lag)
  UV2 [texcoord2]  rips: x = window start, y = window end of _Udon_RipProgress; shafts: x = half-width (m)
  COLOR            flaps: R = tear light on the inner face, G = tear light on the outer face, B = fold->edge 0..1,
                   A = flutter weight.   (8-bit is plenty for these.)
  NORMAL           shafts: the beam axis (object space). Everything else: the surface normal.
"""
import math
import numpy as np
import tear_def as T


def _grid_faces(nu, nv, flip=False):
    F = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a, b, c, d = i * nv + j, (i + 1) * nv + j, (i + 1) * nv + j + 1, i * nv + j + 1
            F.append((a, d, c, b) if flip else (a, b, c, d))
    return np.array(F, np.int32)


def part(name, V, F, UV0, UV1=None, UV2=None, COL=None, N=None, mat=None):
    n = len(V)
    return dict(name=name, V=np.asarray(V, float), F=np.asarray(F, np.int32), UV0=np.asarray(UV0, float),
                UV1=np.zeros((n, 2)) if UV1 is None else np.asarray(UV1, float),
                UV2=np.zeros((n, 2)) if UV2 is None else np.asarray(UV2, float),
                COL=None if COL is None else np.asarray(COL, float), N=None if N is None else np.asarray(N, float),
                mat=mat or name)


# ------------------------------------------------------------------------------------------- lens
def lens(nt=120, na=9, margin=48.0):
    t = np.linspace(T.T_MIN + 4, T.T_MAX - 4, nt)
    aL, aR = T.lips(t)
    pf = T.profile(t)
    lo = np.maximum(np.minimum(aL, T.path(t)) - margin - 10 * pf, T.A_MIN + 2)
    hi = np.minimum(np.maximum(aR, T.path(t)) + margin + 10 * pf, T.A_MAX - 2)
    s = np.linspace(0, 1, na)
    A = lo[:, None] + (hi - lo)[:, None] * s[None, :]
    TT = np.repeat(t[:, None], na, 1)
    V = T.P(TT.ravel(), A.ravel())
    u = (TT.ravel() - T.T_MIN) / (T.T_MAX - T.T_MIN)
    v = (A.ravel() - T.A_MIN) / (T.A_MAX - T.A_MIN)
    UV1 = np.stack([A.ravel(), np.zeros(V.shape[0])], 1)
    return part('Tear_Lens', V, _grid_faces(nt, na, flip=False), np.stack([u, v], 1), UV1, mat='Tear_Lens')


# ------------------------------------------------------------------------------------------- flaps
FLAP_BAND = {'Tear_Flap_L': 0, 'Tear_Flap_R': 1}          # v4: two flaps (Tear_Flaps_1024: 2 bands)


def _core_point(p):
    """nearest point of the white (on the tear path, a little behind the cloth) for tear-light baking."""
    t, a = T.to_ta(p[..., 0], p[..., 2])
    t = np.clip(t, 30.0, 880.0)
    c = T.path(t)
    return T.P(t, c, -80.0)      # v3: the light leaves the hole TOWARD the bus: the everted inner faces catch it


def flap(fl, ns=72, nr=40):
    sf = T.flap_surface(fl, ns, nr)
    pos = sf['pos']
    V = pos.reshape(-1, 3)
    n_out = sf['n_out'].reshape(-1, 3)
    band = FLAP_BAND[fl['name']]
    r = sf['r']
    u = np.repeat(sf['s'][:, None], nr, 1).ravel()
    v = (band + np.clip(r / 1.1, 0, 1)).ravel() / 2.0
    # baked tear light (bible: the inner face catches the tear light #3E3C66)
    L = _core_point(V) - V
    dist = np.linalg.norm(L, axis=1)
    L = L / dist[:, None]
    near = np.clip(1.0 - (np.repeat(r, 1, 0).ravel() * fl['length']) / 420.0, 0.45, 1.0)
    inner = np.clip(np.sum(-n_out * L, 1), 0, 1) ** 0.8 * near
    outer = np.clip(np.sum(n_out * L, 1), 0, 1) ** 0.8 * near
    rn = np.clip(sf['rn'].ravel(), 0, 1)                 # v4: B = fraction of the way to the torn edge (the roll > 0.6)
    flut = rn ** 1.5
    COL = np.stack([inner, outer, rn, flut], 1)
    ah = np.repeat(sf['a_hinge'][:, None], nr, 1).ravel()
    ph = (fl['seed'] * 0.137) % 1.0
    UV1 = np.stack([ah, np.full(V.shape[0], ph)], 1)
    F = _grid_faces(ns, nr)
    a, b, c = V[F[0, 0]], V[F[0, 1]], V[F[0, 2]]
    if np.dot(np.cross(b - a, c - a), n_out[F[0, 0]]) < 0:
        F = F[:, ::-1]
    return part(fl['name'], V, F, np.stack([u, v], 1), UV1, COL=COL, N=n_out, mat='Tear_Flap')


# ------------------------------------------------------------------------------------------- rips
def rip(r, nu=96):
    pts, tan, nor, u = T.rip_centreline(r, nu)
    k = r['width'] / T.RIPS[0]['width']                 # rip B reuses rip A's texture, narrower strip
    M = T.RIP_MARGIN * k
    vs = np.linspace(0, 1, 5)
    TT, AA, U, Vv = [], [], [], []
    for i in range(nu):
        for vv in vs:
            off = (vv - 0.5) * 2 * M                     # + = row-up side in the texture = +nor
            TT.append(pts[i, 0] + nor[i, 0] * off)
            AA.append(pts[i, 1] + nor[i, 1] * off)
            U.append(u[i]); Vv.append(vv)
    TT, AA = np.array(TT), np.array(AA)
    V = T.P(TT, AA, -3.0)                                # a hair in front of the lens
    a0 = pts[0, 1]
    n = V.shape[0]
    UV1 = np.stack([np.full(n, a0), np.zeros(n)], 1)
    UV2 = np.stack([np.full(n, r['window'][0]), np.full(n, r['window'][1])], 1)
    F = _grid_faces(nu, len(vs))
    return part(r['name'], V, F, np.stack([U, Vv], 1), UV1, UV2, mat='Tear_Rip')


# ------------------------------------------------------------------------------------------- fibre cards
def fibres(n_cards=220, seed=5):
    """v3: fibre cards (bible: 2-15 m, additive, 0.3 Hz sway) ONLY at the lip notches (where the rip jumped across
    the weave), pointing out over the cloth, perpendicular to the edge (gate critique B4.1)."""
    rng = np.random.default_rng(seed)
    V, F, UV0, UV1 = [], [], [], []
    k = 0
    made = 0
    tries = 0
    while made < n_cards and tries < 200000:
        tries += 1
        side = -1 if rng.random() < 0.46 else 1
        t = rng.uniform(80.0, T.T_TOP * T.ZIP_T0)      # v4: no fibres at the foot ('grass') nor in the zipper
        _, nk = T.notch_profile(np.array([t]), side)
        if rng.random() > float(nk[0]):
            continue
        aL, aR = T.lips(np.array([t]))
        a0 = float(aR[0] if side > 0 else aL[0])
        aL2, aR2 = T.lips(np.array([t + 1.0]))
        slope = float(aR2[0] if side > 0 else aL2[0]) - a0
        L = float(np.clip(rng.lognormal(math.log(8.0), 0.45), 4.0, 15.0))
        wd = L / 7.0
        nrm = math.atan2(side * 1.0, -slope * side)
        ang = nrm + rng.normal(0, 0.25)
        dt, da = math.cos(ang), math.sin(ang)
        pt, pa = -da, dt
        col = int(rng.integers(0, 8))
        for j, f in enumerate((0.0, 0.5, 1.0)):
            ct, ca = t + dt * L * f, a0 - side * 0.8 + da * L * f
            for x in (-0.5, 0.5):
                V.append(T.P(ct + pt * wd * x, ca + pa * wd * x, -1.5 - 0.3 * f))
                UV0.append(((col + 0.5 + x * 0.98) / 8.0, f))
                UV1.append((a0, 0.0))
        base = k
        F += [(base, base + 1, base + 3, base + 2), (base + 2, base + 3, base + 5, base + 4)]
        ph = rng.random()
        for q in range(6):
            UV1[base + q] = (a0, ph)
        k += 6
        made += 1
    return part('Tear_Fibres', np.array(V).reshape(-1, 3), F, UV0, UV1, mat='Tear_Fibres')


# ------------------------------------------------------------------------------------------- halo, cloud glow
HALO_CARDS = [  # (width, height, depth behind the lens, phase lag, gain)   root scale 1
    # v3 (gate critique M12): radius <= 0.5 H so C* 35-45 sits within 2-3 deg of the lips and is gone by ~8 deg
    # v4 (tech M2): + an INNER card (radius ~0.15 H, gain 2.8): the breathing #5B57A1 at 1-3 deg from the lips
    (330.0, 620.0, 25.0, 0.04, 2.8),
    (360.0, 880.0, 40.0, 0.00, 1.0),
    (640.0, 1000.0, 60.0, 0.08, 1.0),
]
HALO_WIDE = (1500.0, 1750.0)
HALO_T = 380.0


def halo():
    """additive radial cards behind the lens; UV2.x = gain (v4: the inner card is x2.8)."""
    V, F, UV0, UV1, UV2 = [], [], [], [], []
    c_a = float(T.path(np.array([HALO_T]))[0]) + 12.0
    for i, (w, h, d, ph, g) in enumerate(HALO_CARDS):
        b = len(V)
        for (x, y) in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
            V.append(T.P(HALO_T + y * h, c_a + x * w, d)[()])
            UV0.append((x + 0.5, y + 0.5))
            UV1.append((c_a, ph))
            UV2.append((g, 0.0))
        F.append((b, b + 1, b + 2, b + 3))
    return part('Tear_Halo', np.array(V).reshape(-1, 3), F, UV0, UV1, UV2, mat='Tear_Halo')


def skyfolds(nt=34, na=36, tex=None):
    """the sky cloth round the wound (premultiplied card, just behind the lens) + the widest halo layer.
    Columns at the lip extremes so the opening deform (a += (w-1)*clamp(a)) stays piecewise-linear.
    Cells where the texture is empty are dropped (overdraw)."""
    import os
    from PIL import Image
    t = np.linspace(T.FOLD_T0, T.FOLD_T1, nt)
    lo, hi = T.FOLD_CLAMP
    a = np.unique(np.concatenate([np.linspace(T.FOLD_A0, T.FOLD_A1, na), [lo, hi]]))
    TT, AA = np.meshgrid(t, a, indexing='ij')
    V = T.P(TT.ravel(), AA.ravel(), 12.0)
    u = (TT.ravel() - T.FOLD_T0) / (T.FOLD_T1 - T.FOLD_T0)
    v = (AA.ravel() - T.FOLD_A0) / (T.FOLD_A1 - T.FOLD_A0)
    UV1 = np.stack([np.clip(AA.ravel(), lo, hi), np.zeros(V.shape[0])], 1)
    F = _grid_faces(nt, len(a))
    tex = tex or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              'deliver', 'Tear', 'Textures', 'Tear_SkyFolds_1024.png')
    if os.path.exists(tex):
        im = np.asarray(Image.open(tex)).astype(float) / 255.0
        H_, W_ = im.shape[:2]
        mx = im.max(-1)
        from scipy.ndimage import maximum_filter
        mx = maximum_filter(mx, size=9)
        keep = []
        for f in F:
            uu, vv = u[f], v[f]
            x0, x1 = int(uu.min() * (W_ - 1)), int(np.ceil(uu.max() * (W_ - 1)))
            y0, y1 = int((1 - vv.max()) * (H_ - 1)), int(np.ceil((1 - vv.min()) * (H_ - 1)))
            keep.append(mx[y0:y1 + 1, x0:x1 + 1].max() > 3.0 / 255.0)
        F = F[np.array(keep)]
    return part('Tear_SkyFolds', V, F, np.stack([u, v], 1), UV1, mat='Tear_SkyFolds')


CLOUD_GLOW_R = 1100.0


def cloud_glow():
    R = CLOUD_GLOW_R
    V = np.array([(-R, -R, 0.5), (R, -R, 0.5), (R, R, 0.5), (-R, R, 0.5)], float)
    V[:, 1] += 150.0                              # centred a little behind the foot (the foot is in front of it)
    return part('Tear_CloudGlow', V, [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)], mat='Tear_CloudGlow')


# ------------------------------------------------------------------------------------------- shafts
SHAFT_LEN = 3000.0


def shaft_layout(seed=17, n=12):
    """12 beam cards fanning from the tear toward the bus side of the sky (kit space). Each: start (t, a),
    yaw (deg, + = toward the viewer's right), pitch (deg, - = down toward the cloud sea), half-width (m), length."""
    rng = np.random.default_rng(seed)
    out = []
    yaws = np.concatenate([rng.uniform(-18, -3, n // 2), rng.uniform(3, 18, n - n // 2)])
    for i in range(n):
        t = rng.uniform(90, 560)
        aL, aR = T.lips(np.array([t]))
        a = float(aL[0] + (aR[0] - aL[0]) * rng.uniform(0.2, 0.8))
        out.append(dict(t=float(t), a=a, yaw=float(yaws[i]), pitch=float(rng.uniform(-16.0, -8.0)),
                        half_width=float(rng.uniform(12.0, 45.0)), length=float(rng.uniform(0.5, 1.0) * SHAFT_LEN),
                        flip=bool(rng.random() < 0.5)))
    return out


def shaft_axis(s):
    y, p = math.radians(s['yaw']), math.radians(s['pitch'])
    return np.array([math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)])


def unity_dir(v):
    """Blender kit-space direction -> Unity object space (FBX -Z fwd / Y up, then Unity's x flip)."""
    v = np.asarray(v, float)
    return np.array([-v[0], v[2], -v[1]])


def shafts(nl=12, w0=0.4):
    """merged beam cards. Each cross-section = 2 vertices only +-w0 apart (UV0.x 0 / 1); the shader pushes them
    apart across the view by UV2.x (half-width, m). The beam AXIS rides in COLOR.rgb = axis_unity * 0.5 + 0.5
    (normals cannot carry it: FBX/Unity may rebuild them)."""
    V, F, UV0, UV1, UV2, COL, AX = [], [], [], [], [], [], []
    for s in shaft_layout():
        ax = shaft_axis(s)
        side = np.cross(ax, np.array([0.0, 0.0, 1.0])); side /= np.linalg.norm(side)
        p0 = T.P(s['t'], s['a'], -6.0)[()]
        axu = unity_dir(ax) * 0.5 + 0.5
        b = len(V)
        for j in range(nl):
            f = j / (nl - 1)
            p = p0 + ax * s['length'] * f
            for x in (0.0, 1.0):
                V.append(p + side * (x - 0.5) * 2 * w0)
                UV0.append(((1 - x) if s['flip'] else x, f))
                UV1.append((s['a'], 0.0))
                UV2.append((s['half_width'], s['length']))
                COL.append((*axu, 1.0))
                AX.append(ax)
        for j in range(nl - 1):
            q = b + 2 * j
            F.append((q, q + 1, q + 3, q + 2))
    p = part('Tear_Shafts', np.array(V), F, UV0, UV1, UV2, COL=np.array(COL), mat='Tear_Shaft')
    p['AXIS'] = np.array(AX)
    return p


def shaft_card(w0=0.4):
    """a single beam card (for re-laying out the beams between tentacles): axis = local -Y (Blender) = +Z (Unity),
    length 1 m (scale the object's Z in Unity to the beam length), half-width 40 m in UV2.x."""
    V, F, UV0, UV2, COL = [], [], [], [], []
    nl = 12
    for j in range(nl):
        f = j / (nl - 1)
        for x in (0.0, 1.0):
            V.append(((x - 0.5) * 2 * w0, -f, 0.0))
            UV0.append((x, f))
            UV2.append((40.0, 1.0))
            COL.append((0.5, 0.5, 1.0, 1.0))
    for j in range(nl - 1):
        q = 2 * j
        F.append((q, q + 1, q + 3, q + 2))
    p = part('Tear_ShaftCard', np.array(V, float), F, UV0, None, UV2, COL=np.array(COL), mat='Tear_Shaft')
    p['AXIS'] = np.tile([0.0, -1.0, 0.0], (len(V), 1))
    return p


def all_parts():
    P = [lens()]
    P += [flap(f) for f in T.FLAPS]
    P += [rip(r) for r in T.RIPS]
    P += [fibres(), halo(), skyfolds(), cloud_glow(), shafts()]
    return P


# ------------------------------------------------------------------------------------------- shader vertex math (mirror)
ACROSS = T.AC


def deform(p, open01, cam_kit=None):
    """Apply exactly what Lanbai_Tear.shader's vertex stage does (for renders). Returns new vertex array."""
    w = T.width_mul(open01)
    V = p['V'].copy()
    if p['name'] == 'Tear_Lens':
        a = p['UV1'][:, 0]
        V = V + ACROSS[None] * (a * (w - 1.0))[:, None]
    elif p['name'] == 'Tear_CloudGlow':
        pass
    else:
        V = V + ACROSS[None] * (p['UV1'][:, 0] * (w - 1.0))[:, None]
    if p['name'] in ('Tear_Shafts', 'Tear_ShaftCard') and cam_kit is not None:
        ax = p['AXIS'] / np.linalg.norm(p['AXIS'], axis=1, keepdims=True)
        view = cam_kit[None] - V
        side = np.cross(ax, view)
        side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-9
        V = V + side * ((p['UV0'][:, 0] - 0.5) * 2 * p['UV2'][:, 0])[:, None]
    return V
