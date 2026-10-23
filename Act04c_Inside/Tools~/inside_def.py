"""Lanbai act 4c (inside the tear): the ONE definition every other script imports (layout, meshes, textures,
numpy renderer, checks). Pure numpy (no bpy).

Units: metres, Unity axes (x right, y up, z forward = the bus heading). The bus sits at the origin; the world
moves toward -z. InsideRoot (R_Inside) is at world (0, 0, -s(t)); lip k sits at InsideRoot-local (x_k, y_k, s_k).
An opening outline is defined in its own 2-D frame (u right, v up) in units of its height H (v spans 1.0),
centred on the bounding-box centre, BEFORE the lip's roll about the path axis.
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)                      # Act04c_Inside/
REPO = os.path.dirname(KIT)

# ------------------------------------------------------------------------------------------------ cues
_C = json.load(open(os.path.join(REPO, 'FromLocal', 'cues.json'), encoding='utf-8'))
CUE = {k: v['t'] for k, v in _C['U'].items()}
CUE.update({k: v['t'] for k, v in _C['U_sub'].items()})
CUE.update({k: v['t'] for k, v in _C['F'].items()})
U9, U10, U11, U12 = CUE['U9'], CUE['U10'], CUE['U11'], CUE['U12']
VOICE_END = CUE['U_voiceEnd']
LIP_T = [CUE['LIP%d' % k] for k in range(1, 9)]
U6 = CUE['U6']
V_G = 2700.0 / (U9 - U6)                         # 59.0164 m/s (gate README §2; bible rounds to 59.02)
V_END = 12.0
T_DECEL = VOICE_END - U9                          # 54.25 s
LICHT_DIAL_T = 196.10                             # bible §6·4c (cues.json note says 193.1; the bible wins, README lists it)
STOP_T = U12 - 2.25                               # 246.39: everything stops changing
FLASH_T0 = U12 - 0.75                             # 247.89
SLEEVE_EXIT_T = 231.0                             # bible: ~231.0, the long note ends


def ss(x):
    x = np.clip(np.asarray(x, float), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def smootherstep(x):
    x = np.clip(np.asarray(x, float), 0.0, 1.0)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


# ------------------------------------------------------------------------------------------------ motion
def speed(t):
    """world speed (m/s): v_g before U9, one smoothstep 59.02 -> 12 over U9 -> voice end, then 12."""
    t = np.asarray(t, float)
    x = (t - U9) / T_DECEL
    v = V_G + (V_END - V_G) * ss(x)
    return np.where(t < U9, V_G, v)


def dist(t):
    """s(t): metres travelled since U9 (negative before). Closed form: int_0^x ss = x^3 - x^4 / 2."""
    t = np.asarray(t, float)
    tau = t - U9
    x = np.clip(tau / T_DECEL, 0.0, 1.0)
    s_dec = V_G * np.minimum(tau, T_DECEL) + (V_END - V_G) * T_DECEL * (x ** 3 - 0.5 * x ** 4)
    s_end = V_G * T_DECEL + (V_END - V_G) * T_DECEL * 0.5
    s = np.where(tau <= T_DECEL, s_dec, s_end + V_END * (tau - T_DECEL))
    return np.where(tau < 0.0, V_G * tau, s)


def accel(t):
    t = np.asarray(t, float)
    x = np.clip((t - U9) / T_DECEL, 0.0, 1.0)
    a = (V_END - V_G) / T_DECEL * 6.0 * x * (1.0 - x)
    return np.where((t < U9) | (t > VOICE_END), 0.0, a)


S_LIP = [float(dist(t)) for t in LIP_T]
S_SLEEVE_EXIT = float(dist(SLEEVE_EXIT_T))      # 1892.5
SLEEVE_DEPTH = S_SLEEVE_EXIT - S_LIP[7]          # 85.5 m

# ------------------------------------------------------------------------------------------------ the bus
HERO_EYE = np.array([0.55, 1.70, 2.05])          # Gate/GateLayout_v2.json cameras.U7 (the renders use this one)
HERO_EYE_LBJ = np.array([0.70, 1.77, 0.20])      # LB_Journey.heroEye (written into the JSON as well)
BUS_HALF_W, BUS_Y0, BUS_Y1 = 1.04, 0.42, 2.74    # gate_context.md: width 2.08, shell y 0.42 .. 2.74
BUS_Z0, BUS_Z1 = -3.5, 3.5
FLOOR_Y = 0.62

# ------------------------------------------------------------------------------------------------ colour
def hex_srgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255.0


def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, float), 0.0, None)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def hexlin(h):
    return srgb_to_lin(hex_srgb(h))


_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_WP = np.array([0.95047, 1.0, 1.08883])


def srgb_to_lab(c):
    xyz = (_M @ srgb_to_lin(c)[..., None])[..., 0] / _WP
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_srgb(lab):
    lab = np.asarray(lab, float)
    fy = (lab[..., 0] + 16) / 116
    fx = fy + lab[..., 1] / 500
    fz = fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f > 6 / 29, f ** 3, 3 * (6 / 29) ** 2 * (f - 4 / 29)) * _WP
    lin = (np.linalg.inv(_M) @ xyz[..., None])[..., 0]
    return lin_to_srgb(np.clip(lin, 0, None))


def to_hex(c):
    c = np.clip(np.round(np.asarray(c, float) * 255.0), 0, 255).astype(int)
    return '#%02X%02X%02X' % tuple(c)


def lab_mix(h0, h1, f):
    return to_hex(lab_to_srgb(srgb_to_lab(hex_srgb(h0)) * (1 - f) + srgb_to_lab(hex_srgb(h1)) * f))


# bible §6·4c screen targets
FIBRE_SCREEN_KEYS = {1: '#E6E1F2', 4: '#D9DFEE', 8: '#C2D8E2'}
FIBRE_FILL_BIBLE = {1: ('#DFCFFF', 1.96), 4: ('#CBD8FF', 1.78), 8: ('#BCEAFF', 1.29)}
FOG_SCREEN_FIRST, FOG_SCREEN_LAST = '#1D2336', '#53606E'
FOG_FILL_BIBLE = {'#1D2336': '#2A3347', '#53606E': '#6E808D'}
CLOTH_SCREEN = '#1A2030'          # the inner face of the torn cloth (outside the lips)
CABIN_SILHOUETTE = '#0C0E14'
DOT_SCREEN, DOT_FILL = '#FFF1DC', ('#FFC187', 2.79)
DIAL_LICHT_SCREEN = '#F2B169'
CABIN_AMBIENT = ('#B5C3DB', 0.30)
TRILIGHT = ('#3D4863', '#4C5979', '#1F283B')     # sky / equator / ground
FOG_DENSITY = 0.0035


def fibre_screen(k):
    """lip k (1..8): Lab steps between the bible's three keys (1, 4, 8)."""
    if k <= 4:
        return lab_mix(FIBRE_SCREEN_KEYS[1], FIBRE_SCREEN_KEYS[4], (k - 1) / 3.0)
    return lab_mix(FIBRE_SCREEN_KEYS[4], FIBRE_SCREEN_KEYS[8], (k - 4) / 4.0)


def zone_fraction(k):
    """zone k = the air between lip k and k+1 (zone 8 = after the last lip and the coda)."""
    return (LIP_T[k - 1] - LIP_T[0]) / (LIP_T[7] - LIP_T[0])


def fog_screen(k):
    return lab_mix(FOG_SCREEN_FIRST, FOG_SCREEN_LAST, zone_fraction(k))


FOG_XFADE = (1.5, 2.5)            # zone change: crossing - 1.5 s .. + 2.5 s, smoothstep (4 s, bible §1.6: 2-6 s)


def fog_zone_weights(t):
    """continuous zone index z(t) in 1..8 (1 before / at U9). Returns (k, frac): fog = mix(zone k, zone k+1, frac)."""
    t = float(t)
    z = 1.0
    for k in range(2, 9):
        z += float(ss((t - (LIP_T[k - 1] - FOG_XFADE[0])) / (FOG_XFADE[0] + FOG_XFADE[1])))
    k = int(min(np.floor(z), 7))
    return k, z - k


# ------------------------------------------------------------------------------------------------ noise
_TAB = {}


def vnoise(x, seed):
    if seed not in _TAB:
        _TAB[seed] = np.random.default_rng(seed).random(4096) * 2.0 - 1.0
    tab = _TAB[seed]
    x = np.asarray(x, float)
    xi = np.floor(x).astype(np.int64)
    f = x - xi
    f = f * f * f * (f * (f * 6 - 15) + 10)
    return tab[xi % 4096] + (tab[(xi + 1) % 4096] - tab[xi % 4096]) * f


def fbm(x, seed, octaves=4, lac=2.07, gain=0.5):
    s, a, n = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + a * vnoise(np.asarray(x) * lac ** o + 13.7 * o, seed + 97 * o)
        n += a
        a *= gain
    return s / n


def jogs(x, seed, n, amp, soft, lo=0.0, hi=1.0):
    """torn cloth jumps from one yarn to the next: a sum of soft steps (x in lo..hi)."""
    rng = np.random.default_rng(seed)
    pos = np.sort(rng.uniform(lo, hi, n))
    jump = rng.normal(0, amp, n)
    x = np.asarray(x, float)
    s = np.zeros_like(x)
    for p, j in zip(pos, jump):
        s = s + j * (0.5 + 0.5 * np.tanh((x - p) / soft))
    return s - (s.max() + s.min()) * 0.5


# ------------------------------------------------------------------------------------------------ openings
# Torn cloth does not tear in smooth leaves: it runs straight along a yarn, jumps to the next one (a jog), runs on at a
# new angle. Every opening is built from such runs (piecewise-straight lips with jogs), never from ellipses / lenses.
def _runs(n_knots, rng, lo=0.0, hi=1.0):
    k = np.sort(rng.uniform(lo, hi, n_knots))
    return np.concatenate([[lo], k, [hi]])


def _lip_polyline(ts, xs, jog_at, jog_amp, rng, sub=10):
    """piecewise-straight lip through (x(t), t); at the knots in jog_at a sideways jog (two points 0.4 % H apart)."""
    out = []
    for i in range(len(ts) - 1):
        for f in np.linspace(0, 1, sub, endpoint=False):
            out.append((xs[i] + (xs[i + 1] - xs[i]) * f, ts[i] + (ts[i + 1] - ts[i]) * f))
        if i + 1 in jog_at:
            j = rng.choice([-1, 1]) * rng.uniform(0.4, 1.0) * jog_amp
            out.append((xs[i + 1], ts[i + 1] - 0.002))
            xs = xs.copy()
            xs[i + 1:] = xs[i + 1:] + j * np.r_[1.0, np.linspace(1.0, 0.0, len(xs) - i - 2)][: len(xs) - i - 1]
    out.append((xs[-1], ts[-1]))
    return np.array(out)


def slit_polygon(rng, width, skew, tw, hook_top, hook_bot, jog_amp=0.020, v0=-0.5, v1=0.5, tip_w=0.006):
    """one torn slit from v0 to v1 (H units): left / right lips are separate piecewise-straight runs."""
    ts = _runs(5, rng, 0.08, 0.92)
    prof = np.interp(ts, [0, tw, 1], [0, 1, 0])
    prof = np.clip(prof ** rng.uniform(0.6, 0.85, len(ts)) * rng.uniform(0.82, 1.12, len(ts)), 0, 1.15)
    prof[0] = prof[-1] = 0
    cen = rng.normal(0, 0.035, len(ts)) * np.sin(np.pi * ts) ** 0.5
    cen[-1] += hook_top
    cen[0] += hook_bot
    wl = width * skew * prof
    wr = width * (1 - skew) * prof
    wl[0] = wl[-1] = wr[0] = wr[-1] = tip_w * 0.5
    jl = set(rng.choice(np.arange(1, len(ts) - 1), 2, replace=False))
    jr = set(rng.choice(np.arange(1, len(ts) - 1), 3, replace=False))
    vs = v0 + (v1 - v0) * ts
    L = _lip_polyline(vs, cen - wl, jl, jog_amp, rng)
    R = _lip_polyline(vs, cen + wr, jr, jog_amp, rng)
    return np.concatenate([R, L[::-1]], 0)


def _clean(geom):
    from shapely.geometry import Polygon
    if geom.geom_type == 'MultiPolygon':
        geom = max(geom.geoms, key=lambda g: g.area)
    return geom


def poly_single(seed):
    rng = np.random.default_rng(seed)
    P = slit_polygon(rng, rng.uniform(0.40, 0.46), rng.uniform(0.38, 0.47), rng.uniform(0.34, 0.46),
                     rng.choice([-1, 1]) * rng.uniform(0.05, 0.09), rng.choice([-1, 1]) * rng.uniform(0.03, 0.06))
    return P


def poly_branched(seed):
    from shapely.geometry import Polygon
    from shapely import affinity
    rng = np.random.default_rng(seed)
    side = rng.choice([-1, 1])
    main = Polygon(slit_polygon(rng, rng.uniform(0.42, 0.48), 0.5 - side * 0.05, rng.uniform(0.42, 0.52),
                                -side * 0.06, side * 0.04)).buffer(0)
    vj = -0.5 + rng.uniform(0.48, 0.58)
    blen = rng.uniform(0.42, 0.50)
    br = Polygon(slit_polygon(rng, rng.uniform(0.15, 0.19), 0.5, 0.22, side * 0.04, 0.0, jog_amp=0.012,
                              v0=0.0, v1=blen)).buffer(0)
    br = affinity.rotate(br, -side * rng.uniform(28, 38), origin=(0, 0))
    br = affinity.translate(br, 0.0, vj)
    # the junction is pulled open by the two rips: a wide torn triangle between them
    jx = side * rng.uniform(0.14, 0.20)
    tri = Polygon([(-side * 0.14, vj - 0.16), (jx + side * 0.09, vj + 0.10), (side * 0.02, vj + 0.22)]).buffer(0)
    g = _clean(main.union(br).union(tri).buffer(0.012, join_style=2).buffer(-0.012, join_style=2))
    return np.array(g.exterior.coords)[:-1]


def poly_hole(seed, aspect=0.90):
    """punched through and pulled open (review r1: no star, no >= 4-fold radial arrangement): an irregular hole with
    uneven torn runs, ONE large flap hanging down from the upper edge along the warp, one small curl elsewhere, and two
    corners pointing in. The flaps are cloth tongues reaching into the opening."""
    from shapely.geometry import Polygon
    rng = np.random.default_rng(seed)
    n = int(rng.integers(7, 11))
    th = np.sort(rng.uniform(0, 2 * np.pi, n))
    while np.diff(np.r_[th, th[0] + 2 * np.pi]).max() > 1.6 or np.diff(np.r_[th, th[0] + 2 * np.pi]).min() < 0.25:
        th = np.sort(rng.uniform(0, 2 * np.pi, n))
    r = rng.uniform(0.38, 0.52, n)
    P = np.stack([r * np.cos(th) * aspect, r * np.sin(th)], -1)
    g = Polygon(P).buffer(0)
    # the big flap: hangs from the upper edge, a little off-centre, 18-26 % wide, 22-32 % long, its free end ragged
    x0 = rng.choice([-1, 1]) * rng.uniform(0.10, 0.24)      # off-centre: a centred bite reads as a heart
    w = rng.uniform(0.20, 0.30)
    L = rng.uniform(0.34, 0.46)
    top = 0.62
    flap = Polygon([(x0 - w / 2, top), (x0 + w / 2, top), (x0 + w * rng.uniform(0.15, 0.4), top - L * rng.uniform(0.8, 1.0)),
                    (x0 + w * rng.uniform(-0.1, 0.1), top - L), (x0 - w * rng.uniform(0.2, 0.45), top - L * rng.uniform(0.75, 0.95))])
    g = g.difference(flap)
    # the small curl: a short tongue from a random side, not opposite the big flap
    a0 = rng.uniform(-2.6, -0.5) if rng.random() < 0.5 else rng.uniform(0.3, 1.0) + np.pi
    c = np.array([np.cos(a0) * 0.6 * aspect, np.sin(a0) * 0.6])
    tip = c * rng.uniform(0.45, 0.55)
    nrm = np.array([-c[1], c[0]]) / np.linalg.norm(c)
    ww = rng.uniform(0.06, 0.10)
    curl = Polygon([c + nrm * ww, c - nrm * ww, tip - nrm * ww * 0.2])
    g = g.difference(curl)
    # one pointed inward corner (a tear run that jumped)
    a1 = a0 + np.pi * rng.uniform(0.6, 1.0)
    c1 = np.array([np.cos(a1) * 0.6 * aspect, np.sin(a1) * 0.6])
    t1 = c1 * rng.uniform(0.62, 0.7)
    n1 = np.array([-c1[1], c1[0]]) / np.linalg.norm(c1)
    g = g.difference(Polygon([c1 + n1 * 0.12, c1 - n1 * 0.03, t1]))
    if g.geom_type == 'MultiPolygon':
        g = max(g.geoms, key=lambda q: q.area)
    return np.array(g.exterior.coords)[:-1]


def radial_symmetry(pts):
    """largest normalised Fourier power of the radius at k >= 4 (a star / flower has a strong single k)."""
    c = pts.mean(0)
    d = pts - c
    th = np.arctan2(d[:, 1], d[:, 0])
    r = np.hypot(d[:, 0], d[:, 1])
    o = np.argsort(th)
    g = np.linspace(-np.pi, np.pi, 256, endpoint=False)
    rr = np.interp(g, th[o], r[o], period=2 * np.pi)
    F = np.abs(np.fft.rfft(rr - rr.mean()))
    return float(F[4:12].max() / (F[1:12].sum() + 1e-9))


POLYS = {'single': poly_single, 'branched': poly_branched, 'hole': poly_hole}


def tear_runs(P, seed, min_len=0.06):
    """every long straight edge becomes a torn run: a slight bow (cloth under tension), and a jog part-way."""
    rng = np.random.default_rng(seed + 900)
    out = []
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        L = np.linalg.norm(b - a)
        out.append(a)
        if L < min_len:
            continue
        d = (b - a) / L
        nrm = np.array([-d[1], d[0]])
        bow = rng.normal(0, 0.035) * L
        fj = rng.uniform(0.3, 0.7)
        jog = rng.choice([-1, 1]) * rng.uniform(0.004, 0.012)
        for f in np.linspace(0, 1, max(int(L / 0.012), 3))[1:-1]:
            off = bow * 4 * f * (1 - f) + (jog if f > fj else 0.0)
            out.append(a + d * L * f + nrm * off)
    return np.array(out)


def fix_polygon(pts):
    """make a simple (non self-intersecting) CCW ring: shapely buffer(0), largest part, no duplicate points."""
    from shapely.geometry import Polygon
    g = Polygon(pts).buffer(0)
    if g.geom_type == 'MultiPolygon':
        g = max(g.geoms, key=lambda q: q.area)
    q = np.array(g.exterior.coords)[:-1]
    keep = np.r_[True, np.linalg.norm(np.diff(q, axis=0), axis=1) > 1e-9]
    q = q[keep]
    a = 0.5 * np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1])
    return q if a > 0 else q[::-1]


def outline(kind, seed):
    """closed outline (N, 2) in H units, counter-clockwise, vertical extent 1.0, bounding box centred on (0, 0)."""
    pts = fix_polygon(tear_runs(fix_polygon(np.asarray(POLYS[kind](seed), float)), seed))
    a = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
    if a < 0:
        pts = pts[::-1]
    lo, hi = pts.min(0), pts.max(0)
    return (pts - (lo + hi) * 0.5) / (hi[1] - lo[1])


def resample(pts, ds):
    seg = np.linalg.norm(np.roll(pts, -1, 0) - pts, axis=1)
    L = np.concatenate([[0], np.cumsum(seg)])
    n = max(int(L[-1] / ds), 32)
    s = np.linspace(0, L[-1], n, endpoint=False)
    P = np.concatenate([pts, pts[:1]], 0)
    return np.stack([np.interp(s, L, P[:, 0]), np.interp(s, L, P[:, 1])], -1), L[-1]


def normals(pts, smooth=0):
    P = pts
    if smooth > 0:
        from scipy.ndimage import gaussian_filter1d
        P = np.stack([gaussian_filter1d(pts[:, 0], smooth, mode='wrap'), gaussian_filter1d(pts[:, 1], smooth, mode='wrap')], -1)
    tg = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    tg /= np.linalg.norm(tg, axis=1, keepdims=True) + 1e-12
    return np.stack([tg[:, 1], -tg[:, 0]], -1)            # outward for a CCW outline


def torn_edge(pts, H, seed, amp_m=(0.006, 0.0025), ds_m=None):
    """resample to a metric spacing and add the torn jag along the outward normal (amplitudes in H units)."""
    ds = (ds_m or max(0.9, 0.0035 * H)) / H
    P, L = resample(pts, ds)
    s = np.arange(len(P)) * ds
    n = normals(P, smooth=3)
    j = amp_m[0] * fbm(s / 0.035, seed, 3) + amp_m[1] * fbm(s / 0.009, seed + 1, 2)
    Q = fix_polygon(P + n * j[:, None])
    Q, _ = resample(Q, ds)
    return Q, ds * H


def point_in_poly(pts, poly):
    """even-odd rule, vectorised (pts (M, 2), poly (N, 2))."""
    x, y = pts[:, 0][:, None], pts[:, 1][:, None]
    x0, y0 = poly[:, 0][None, :], poly[:, 1][None, :]
    x1, y1 = np.roll(poly[:, 0], -1)[None, :], np.roll(poly[:, 1], -1)[None, :]
    c = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-30) + x0)
    return (np.sum(c, axis=1) % 2) == 1


# ------------------------------------------------------------------------------------------------ the lips
def lip_roll_matrix(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def tear_outline_lip1(n=900):
    """lip 1 = the gate's own lens (Tear kit tear_def, full opening, H 1000 m), seen as an outline in the lip frame:
    u right, v up, in METRES relative to the path (the entry point is at the bus origin, 150 m above the cloud top)."""
    import sys
    sys.path.insert(0, os.path.join(REPO, 'Tear', 'Source'))
    import tear_def as TD
    t = np.linspace(TD.T_BOT + 0.5, TD.T_TOP - 0.5, n)
    aL, aR = TD.lips(t)
    left = TD.P(t, aL)          # kit: x across (+ right), y depth, z up
    right = TD.P(t, aR)
    ring = np.concatenate([right[:, [0, 2]], left[::-1][:, [0, 2]]], 0)
    ring[:, 1] -= 150.0          # cloud top is 150 m below the entry point
    a = 0.5 * np.sum(ring[:, 0] * np.roll(ring[:, 1], -1) - np.roll(ring[:, 0], -1) * ring[:, 1])
    return ring if a > 0 else ring[::-1]


# the dot (bible §6·4c): a sky object fixed in bus coordinates
DOT_AZ_DEG, DOT_EL_DEG = -5.0, 3.0
DOT_DIST = 2300.0
DOT_GLOW_DEG = (4.0, 12.0)
DOT_CORE_DEG = (0.3, 0.9)
DOT_APPEAR = (LIP_T[3], 2.5)                      # LIP4, 2.5 s EV-linear from -6 EV
DOT_GROW = (U11, STOP_T)


def dot_dir():
    az, el = math.radians(DOT_AZ_DEG), math.radians(DOT_EL_DEG)
    return np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])


def dot_size(t):
    """(core diameter deg, glow diameter deg, gain linear) at time t."""
    t = float(min(t, STOP_T))
    g = float(smootherstep((t - DOT_GROW[0]) / (DOT_GROW[1] - DOT_GROW[0])))
    core = DOT_CORE_DEG[0] + (DOT_CORE_DEG[1] - DOT_CORE_DEG[0]) * g
    glow = DOT_GLOW_DEG[0] + (DOT_GLOW_DEG[1] - DOT_GLOW_DEG[0]) * g
    x = np.clip((t - DOT_APPEAR[0]) / DOT_APPEAR[1], 0.0, 1.0)
    gain = 0.0 if t < DOT_APPEAR[0] else float(2.0 ** (-6.0 * (1.0 - x)))
    return core, glow, gain


# the cabin light bands (bible §6·4c table): start, sweep duration
BAND_START = [180.15] + LIP_T[1:]
BAND_SWEEP = [1.2, 1.2, 1.3, 1.5, 1.7, 1.9, 2.1, 2.4]
BAND_HALF_W = 0.9
SLEEVE_BAND_END = SLEEVE_EXIT_T                    # lip 8: in 2.4 s, hold, out 2.4 s, ends at 231.0


if __name__ == '__main__':
    for k, t in enumerate(LIP_T, 1):
        print('LIP%d t %.2f s %.1f v %.2f fibre %s fog-zone %s' % (k, t, dist(t), speed(t), fibre_screen(k), fog_screen(k)))
    print('sleeve exit', S_SLEEVE_EXIT, 'depth', SLEEVE_DEPTH, 'U12 s', float(dist(U12)), 'peak a', float(np.abs(accel(np.linspace(U9, VOICE_END, 2001))).max()))
