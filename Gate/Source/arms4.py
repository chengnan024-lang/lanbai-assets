"""蓝白 / Lanbai · gate layout v4 (round 3) · CUSTOM-CENTRELINE ARMS.

Round-3 critique (awe B5): the library variants posed by rotation read as plants (vertical stalks from pots, leaf-blade
taper, fiddleheads, twig forks). The gate's hero arms (the two gate pillars, the two braided hand bundles, the Engel)
are now authored directly as world-space centrelines through control points, so each one can
  - leave the cloud LEANING 25-50 deg toward the wound (never vertical), or breach as a HUMP first,
  - curl over and DOWN in its upper 35 % (the tip ends >= 15 % of the length below the arm's highest point),
  - taper continuously (a swan neck from t 0.45: no 'head', no 'hair'),
  - end in a thread whip with one soft hook / a half curl / a paddle (no forks beyond 300 m),
  - braid with its siblings (a bundle = one forearm that becomes a hand).
The tube, UVs and vertex data are the library's own (build_library.make_tube: UVMap, UVSway, Col = (t, phase, r/R, 1)),
so the delivered shader and textures work unchanged. Registered as gate variants (BL.VARIANTS[key] with 'custom') and
baked per instance into GateArms_v3.fbx.
"""
import math

import numpy as np
from scipy.interpolate import PchipInterpolator

import build_library as BL

# r / R_root along the arc: a muscular root, the mass held to ~30 %, then ONE continuous concave taper (swan neck) from
# t 0.45 into a thread of 2-4 % of the root (3-8 px at 1.5 km for the big arms; the shader inflates to >= 1 px).
RAD4 = [(0.00, 1.00), (0.05, 1.05), (0.15, 1.03), (0.30, 0.95), (0.45, 0.83), (0.55, 0.69), (0.65, 0.53),
        (0.75, 0.37), (0.84, 0.235), (0.91, 0.135), (0.955, 0.075), (0.985, 0.040), (1.00, 0.022)]
_R4 = PchipInterpolator(*map(np.array, zip(*RAD4)))
CUSTOM = {}


def rad4(u, thick=1.0):
    """r / R_root at arc fraction u. thick > 1 keeps the body heavier for longer (pillars)."""
    u = np.clip(np.asarray(u, float), 0.0, 1.0)
    return _R4(u ** thick)


# ------------------------------------------------------------------------------------------------ curves
def catmull(ctrl, n_per=40, alpha=0.5):
    """centripetal Catmull-Rom through the control points (n_per samples per span)."""
    P = np.asarray(ctrl, float)
    P = np.concatenate([2 * P[:1] - P[1:2], P, 2 * P[-1:] - P[-2:-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** alpha
        ts = np.linspace(t1, t2, n_per, endpoint=False)[:, None]
        A1 = (t1 - ts) / (t1 - t0) * p0 + (ts - t0) / (t1 - t0) * p1
        A2 = (t2 - ts) / (t2 - t1) * p1 + (ts - t1) / (t2 - t1) * p2
        A3 = (t3 - ts) / (t3 - t2) * p2 + (ts - t2) / (t3 - t2) * p3
        B1 = (t2 - ts) / (t2 - t0) * A1 + (ts - t0) / (t2 - t0) * A2
        B2 = (t3 - ts) / (t3 - t1) * A2 + (ts - t1) / (t3 - t1) * A3
        out.append((t2 - ts) / (t2 - t1) * B1 + (ts - t1) / (t2 - t1) * B2)
    out.append(P[-2][None])
    return np.concatenate(out)


def resample(P, n):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    q = np.linspace(0, s[-1], n)
    return np.stack([np.interp(q, s, P[:, i]) for i in range(3)], -1)


def smooth_poly(P, sigma_pts=3.0):
    """light Gaussian smoothing of a dense polyline (ends pinned)."""
    from scipy.ndimage import gaussian_filter1d
    Q = gaussian_filter1d(P, sigma_pts, axis=0, mode='nearest')
    w = np.clip(np.minimum(np.arange(len(P)), np.arange(len(P))[::-1]) / (3 * sigma_pts), 0, 1)[:, None]
    return P * (1 - w) + Q * w


def curve(ctrl, n=1601, smooth=2.0):
    P = resample(catmull(ctrl), n)
    if smooth:
        P = resample(smooth_poly(P, smooth), n)
    return P


def frames(P):
    """centreline dict (u, s, P, T, A, B, k, L) with a rotation-minimising frame."""
    T0 = P[1] - P[0]
    T0 /= np.linalg.norm(T0)
    ref = np.array([0.0, -1.0, 0.0]) if abs(T0[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    B0 = ref - ref.dot(T0) * T0
    s, T, B, k = BL.rmf_along(P, B0 / np.linalg.norm(B0))
    A = np.cross(T, B)
    return dict(u=s / s[-1], s=s, P=P, T=T, A=A, B=B, k=k, L=float(s[-1]))


# ------------------------------------------------------------------------------------------------ tips
def hook_end(ctrl, radius, turn_deg, toward, n=5, tighten=0.4):
    """append a soft hook / half curl to a control polyline: an arc that continues the last segment's direction and
    bends toward the vector `toward` (projected perpendicular to it), turning `turn_deg` while its radius tightens
    (a whip end, not a circle)."""
    C = [np.asarray(c, float) for c in ctrl]
    d = C[-1] - C[-2]
    d /= np.linalg.norm(d)
    side = np.asarray(toward, float)
    side = side - side.dot(d) * d
    side /= np.linalg.norm(side)
    c0 = C[-1] + side * radius
    for i in range(1, n + 1):
        f = i / n
        a = math.radians(turn_deg) * f
        r = radius * (1.0 - tighten * f)
        C.append(c0 + r * (-side * math.cos(a) + d * math.sin(a)) + side * (radius - r))
    return C


# ------------------------------------------------------------------------------------------------ braid
def braid(axis_ctrl, fingers, n_axis=600, turns=0.6, rho_k=0.78, phase0=0.0, n=1601):
    """a BUNDLE = one forearm that becomes a hand. axis_ctrl runs from the shared root (under the cloud) to the wrist;
    fingers = [(R_root, [ctrl beyond the wrist...]), ...]. Along the forearm each finger winds `turns` around the axis
    at rho_k x its own radius (so they touch: no sky between them), then flows into its own control points.
    Returns one dense polyline per finger."""
    A = curve(axis_ctrl, n_axis, smooth=0)
    cl = frames(A)
    nf = len(fingers)
    out = []
    sa = cl['s'] / cl['s'][-1]
    for i, (R0, fctrl) in enumerate(fingers):
        L_est = cl['L'] + float(np.sum(np.linalg.norm(np.diff(np.vstack([A[-1:], fctrl]), axis=0), axis=1)))
        uu = cl['s'] / L_est
        rr = R0 * rad4(uu)
        phi = phase0 + 2 * math.pi * i / nf + 2 * math.pi * turns * sa
        rho = rho_k * rr * (0.55 + 0.45 * (1 - sa) ** 0.5)      # the hand narrows into the wrist
        Pb = A + rho[:, None] * (np.cos(phi)[:, None] * cl['B'] + np.sin(phi)[:, None] * cl['A'])
        idx = np.linspace(0, len(Pb) - 1, 9).astype(int)
        pts = [Pb[j] for j in idx] + [np.asarray(c, float) for c in fctrl]
        out.append(curve(pts, n, smooth=2.0))
    return out


# ------------------------------------------------------------------------------------------------ registry
def register(key, P_world, R_root, phase, lods=((40, 210), (24, 120), (12, 48)), thick=1.0, vofs=0.0):
    """register a custom gate variant: P_world = dense centreline (CF metres); the variant's local frame is the
    world frame translated to P_world[0] (instance R = I, scale = 1). Returns the root (CF)."""
    P_world = np.asarray(P_world, float)
    root = P_world[0].copy()
    cl = frames(P_world - root)
    BL.VARIANTS[key] = dict(L=cl['L'], R=float(R_root), heavy=1.0, phase=float(phase), vofs=float(vofs),
                            lods=[[tuple(l)] for l in lods], custom=True, thick=float(thick))
    BL._CLINE[key] = cl
    CUSTOM[key] = dict(thick=float(thick))
    return root


def is_custom(key):
    return key in CUSTOM


def rel_radius(key, u):
    """r / R_root of any gate variant (custom or library)."""
    if key in CUSTOM:
        return rad4(u, CUSTOM[key]['thick'])
    sp = BL.VARIANTS[key]
    return BL.radius_profile(u, sp.get('heavy', 1.0), (sp['phase'] * 7.3) % 1.0)


_orig_variant_parts = BL.variant_parts


def variant_parts(key, lod=0):
    if key not in CUSTOM:
        return _orig_variant_parts(key, lod)
    sp = BL.VARIANTS[key]
    cl = BL._CLINE[key]
    R = sp['R']
    th = CUSTOM[key]['thick']
    seg, rings = sp['lods'][lod][0]
    wseed = (sp['phase'] * 7.3) % 1.0
    p = BL.make_tube(cl, lambda uu: R * rad4(uu, th), seg, rings, R, lambda uu: np.asarray(uu, float),
                     v_offset=sp.get('vofs', 0.0), lump_seed=wseed * 6.0, sigma_frac=0.003, rmin_frac=0.012,
                     vmin_frac=0.03)
    p['name'] = 'core'
    shift = float(np.round(0.5 * (p['V'].min() + p['V'].max())))
    p['V'] = p['V'] - shift
    p['tip_v'] = p['tip_v'] - shift
    return [p], cl


BL.variant_parts = variant_parts


def self_intersection(key):
    """max over the arc of r x curvature (> ~0.85: the tube folds through itself on the inside of a bend)."""
    cl = BL._CLINE[key]
    r = BL.VARIANTS[key]['R'] * rel_radius(key, cl['u'])
    m = r * cl['k']
    i = int(np.argmax(m[5:-5])) + 5
    return float(m[i]), float(cl['u'][i])


# ------------------------------------------------------------------------------------------------ occlusion maps
COLOSSUS_KEYS = ('PR', 'PL', 'ENG', 'C2', 'C1')          # + BG*: macro undulation (wet eroded basalt), 3x skin tiling


def is_colossus(key):
    return key in COLOSSUS_KEYS or key.startswith('BG')


def occlusion_map(key, n=512):
    """T_Gate_<key>_Occlusion (the library's T_Tentacle_X_Occlusion recipe on a custom centreline): B = crease mask on
    the concave side of each bend (scaled by strain), R = macro height (colossi), G = occlusion."""
    orig = BL.radius_profile
    th = CUSTOM[key]['thick']
    BL.radius_profile = lambda u, heavy=1.0, wob_seed=0.0: rad4(u, th)
    added = False
    if is_colossus(key) and key not in BL.MACRO:
        BL.MACRO[key] = 1.0
        added = True
    try:
        return BL.occlusion_map(key, n)
    finally:
        BL.radius_profile = orig
        if added:
            BL.MACRO.pop(key, None)


def occlusion_path(key, out_dir):
    """bake on demand (gate/Textures/Occlusion/T_Gate_<key>_Occlusion.png), keyed by the centreline's hash."""
    import hashlib
    import os
    os.makedirs(out_dir, exist_ok=True)
    h = hashlib.md5(np.ascontiguousarray(BL._CLINE[key]['P'][::50]).tobytes()).hexdigest()[:8]
    fn = os.path.join(out_dir, 'T_Gate_%s_Occlusion.png' % key)
    tag = fn + '.' + h
    if not (os.path.exists(fn) and os.path.exists(tag)):
        for f in os.listdir(out_dir):
            if f.startswith('T_Gate_%s_Occlusion.png.' % key):
                os.remove(os.path.join(out_dir, f))
        BL._save_rgb(fn, occlusion_map(key))
        open(tag, 'w').write(key)
    return fn


def skin_tiling(R_m):
    """(main, detail) map tiling per instance from the root radius (m). Main maps (albedo, smoothness: the long mucus
    runs) stay coarse so a 0.5-1 km arm shows 2-4 long wet streaks several px wide (R 54 -> 2.2); the detail normal
    keeps roughly its physical scale (R 54 -> 13.5) so a giant never wears a metre-wide crosshatch (critique M16 /
    U8side). Unity: _MainTex_ST and _DetailNormalMap_ST per renderer (MPB)."""
    return float(np.clip(R_m / 25.0, 1.0, 3.0)), float(np.clip(R_m / 4.0, 1.0, 16.0))
