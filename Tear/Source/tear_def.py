"""Lanbai tear kit v2: the ONE geometric definition of the tear (textures, meshes and renders all import this).

KIT SPACE (Blender, metres, root scale 1 = tear height H 1000 m above the cloud top, at FULL opening = 30 % of H):
  x = across (+ = the viewer's right), y = depth (+ = away from the bus, into the sky), z = up.
  z = 0 is the cloud-top level. The pivot is the axis point at z = 0. Every part faces -y (toward the bus).
  The lens axis is tilted 4 deg (top leans right). t = distance along that axis from the pivot,
  a = signed distance across it (left -, right +):  P(t, a, d) = t*AX + a*AC + d*(0,1,0).

Bible §6·4: asymmetric lens, widest at 40 % of the height, left 45 % / right 55 % of the width, axis tilted 4 deg,
width 18 % -> 30 % of H driven by _Udon_TearOpen (meshes are modelled at 30 %; the shader scales `a`).
"""
import math
import numpy as np

TILT = math.radians(4.0)
AX = np.array([math.sin(TILT), 0.0, math.cos(TILT)])
AC = np.array([math.cos(TILT), 0.0, -math.sin(TILT)])
DEPTH = np.array([0.0, 1.0, 0.0])

H = 1000.0
T_TOP = H / math.cos(TILT)            # top tip (z = 1000)
T_BOT = -150.0                        # bottom tip, buried in the cloud sea ("the foot rips on down into the clouds")
T_W = 0.40 * H / math.cos(TILT)       # widest point, 40 % of the height
OPEN_MAX = 0.30
OPEN_MIN = 0.18
W_TOT = OPEN_MAX * H                  # 300 m at full opening
W_L = 0.45 * W_TOT                    # 135 m left of the tear path
W_R = 0.55 * W_TOT                    # 165 m right of it
WK = 0.963                            # calibration so the TORN lens (jag, fold bulges) measures 30 % at its widest

# Tear_Emission_2048x512 covers this rectangle (axis coordinates, full opening)
T_MIN, T_MAX = T_BOT - 30.0, T_TOP + 40.0     # 1332 m -> 2048 px (0.65 m/px)
A_MIN, A_MAX = -215.0, 245.0                  # 460 m -> 512 px (0.90 m/px)
EMISSION_SCALE = 4.0                          # PNG stores linear fill / 4 (sRGB-encoded); shader multiplies by 4


def P(t, a, d=0.0):
    t = np.asarray(t, float)[..., None]
    a = np.asarray(a, float)[..., None]
    d = np.asarray(d, float)[..., None]
    return t * AX + a * AC + d * DEPTH


def to_ta(x, z):
    return x * AX[0] + z * AX[2], x * AC[0] + z * AC[2]


# ---------------------------------------------------------------------------------------------- noise
def _tab(seed, n=8192):
    return np.random.default_rng(seed).random(n) * 2.0 - 1.0


_TABS = {}


def vnoise(x, seed):
    """smooth 1-D value noise in [-1, 1], one cell per unit."""
    if seed not in _TABS:
        _TABS[seed] = _tab(seed)
    tab = _TABS[seed]
    x = np.asarray(x, float)
    xi = np.floor(x).astype(np.int64)
    f = x - xi
    f = f * f * f * (f * (f * 6 - 15) + 10)
    a = tab[xi % len(tab)]
    b = tab[(xi + 1) % len(tab)]
    return a + (b - a) * f


def fbm(x, seed, octaves=4, lac=2.13, gain=0.5):
    s, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + amp * vnoise(x * lac ** o + 17.3 * o, seed + 101 * o)
        norm += amp
        amp *= gain
    return s / norm


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------- lens
def profile(t):
    """0 at both tips, 1 at the widest point. Lower part blunt (it vanishes into the cloud sea), upper part a long
    needle: the tear is still running upward."""
    t = np.asarray(t, float)
    lo = np.clip((T_W - t) / (T_W - T_BOT), 0, 1)
    hi = np.clip((t - T_W) / (T_TOP - T_W), 0, 1)
    f_lo = np.clip(1 - lo ** 1.7, 0, 1) ** 0.95
    f_hi = np.clip(1 - hi ** 1.45, 0, 1) ** 1.42
    f = np.where(t <= T_W, f_lo, f_hi)
    return np.where((t < T_BOT) | (t > T_TOP), 0.0, f)


def _steps(t, seed, n=26, amp=7.0, soft=3.0):
    """a torn cloth path jogs sideways where the tear jumps from one yarn to the next."""
    rng = np.random.default_rng(seed)
    pos = np.sort(rng.uniform(T_BOT, T_TOP, n))
    jump = rng.normal(0, amp, n)
    t = np.asarray(t, float)
    s = np.zeros_like(t)
    for p, j in zip(pos, jump):
        s = s + j * (0.5 + 0.5 * np.tanh((t - p) / soft))
    return s - s.mean() if s.size > 1 else s


_T_REF = np.linspace(T_BOT, T_TOP, 4001)
_STEP_REF = _steps(_T_REF, 71)


def path(t):
    """centre line the cloth tore along (across offset, m). Both lips follow it, so their kinks are complementary."""
    t = np.asarray(t, float)
    stp = np.interp(t, _T_REF, _STEP_REF)
    wander = 16.0 * fbm(t / 260.0, 11, 3) + 5.5 * fbm(t / 55.0, 12, 3) + 1.6 * fbm(t / 13.0, 13, 2)
    # the path must still meet the two tips: fade the slow wander toward them
    env = 0.35 + 0.65 * smoothstep(0.0, 0.25, profile(t))
    return (wander + stp * 0.8) * env


# flap spans along each lip (the lip there is the HINGE line of a peeled flap, pushed outward; see FLAPS)
FLAPS = [
    # v4 (gate round 3, critique B4.3): exactly TWO thin, welded flaps that are the sky's own cloth peeling back.
    #   hinge t0..t1 along the lip (the lens lip there runs on the hinge line: the white extends under the flap),
    #   length = flat width of the cloth (hinge -> torn edge, m), lift = how far it is lifted toward the bus at its
    #   middle (deg; 0 at both ends: welded), roll = the curl of its torn edge back outward (deg over the last ~40 %),
    #   peak = where along the hinge the torn tongue is longest. The bus sees mostly the OUTER face (the sky's colour)
    #   and a sliver of the wound-lit inner face on the rolled lip only.
    # (resume fix: the v4 draft pushed the right lip out by 190 m, past the emission texture; the peel's flat width
    #  now lies INSIDE the lens' 30 % width: hinge span 250 m at 35-60 % H, flat width 130 m; the left curl 15-25 % H)
    dict(name='Tear_Flap_L', side=-1, t0=150.0, t1=255.0, length=80.0, lift=40.0, roll=190.0, peak=0.45, seed=211),
    dict(name='Tear_Flap_R', side=+1, t0=350.0, t1=600.0, length=135.0, lift=50.0, roll=200.0, peak=0.52, seed=213),
]
FLAP_FLAT = 0.30      # fraction of the flap's flat width by which the lens lip is pushed out (white under the flap)


def flap_bump(t, side):
    """how far (m, full opening) the lip is pushed outward along a flap's hinge span: the flap's cloth used to lie
    there, so the hole now runs to the hinge line (smoothly welded at both ends)."""
    t = np.asarray(t, float)
    b = np.zeros_like(t)
    for f in FLAPS:
        if f['side'] != side:
            continue
        sp = (t - f['t0']) / (f['t1'] - f['t0'])
        w = np.where((sp > 0) & (sp < 1), np.sin(np.clip(sp, 0, 1) * math.pi) ** 0.9, 0.0)
        b = np.maximum(b, FLAP_FLAT * f['length'] * w * flap_outline(f, np.clip(sp, 0, 1)))
    return b


# ---------------------------------------------------------------------------------------------- lips (v3)
# Round 2 (gate critique B4): the v2 lip was a fine sawtooth with a regular fur fringe = the visual language of an
# electric discharge. v3: each side runs as SMOOTH, gently curved cloth edge broken by 3-5 irregular NOTCHES (3-8 %
# of H deep): a few cut back into the cloth (the rip jumped), a few cloth tongues left standing into the hole. Fine
# jag and fibres only AT the notches.
#   (side, t centre, width m, depth m (+ = outward cut, - = tongue into the hole), skew (-1..1: which flank is sharp))
NOTCHES = [
    # v4 (critique B4.2): the LEFT edge is long and clean (a tear along the weave): one gentle curve, 2 small notches;
    # the RIGHT edge is ragged: 4 notches, a fine torn jag all along it, and the big peel.
    (-1, 300.0, 110.0, 16.0, 0.6), (-1, 640.0, 90.0, -12.0, -0.5),
    (+1, 95.0, 120.0, 34.0, 0.5), (+1, 245.0, 110.0, -26.0, -0.6), (+1, 700.0, 110.0, 30.0, 0.7),
    (+1, 820.0, 80.0, -16.0, -0.4),
]


def _jog(x, skew):
    """a torn JOG, not a spike: x in -1..1 over the notch width. The sharp flank (12 % of the width) is where the
    rip jumped across the weave; then the edge runs on at the new offset (a ragged plateau) and tears back along a
    long diagonal. skew > 0: sharp flank at the low-t end."""
    x = np.asarray(x, float)
    xs = np.where(skew > 0, x, -x)                     # sharp flank at xs = -1
    up = smoothstep(-1.0, -0.76, xs)                   # sharp
    down = 1.0 - smoothstep(-0.05, 1.0, xs) ** 0.8     # long return
    return up * down


def notch_profile(t, side, notches=None, scale=1.0):
    """(offset m outward, notchiness 0..1) of one lip from its notches (+ = a bay cut into the cloth, - = a cloth
    tongue left standing into the hole), narrowing toward the needle with the lens profile."""
    t = np.asarray(t, float)
    off = np.zeros_like(t)
    nk = np.zeros_like(t)
    for (sd, tc, w, dep, skew) in (NOTCHES if notches is None else notches):
        if sd != side:
            continue
        tc, w, dep = tc * scale, w * scale, dep * scale
        x = (t - tc) / (0.5 * w)
        v = _jog(np.clip(x, -1.0, 1.0), skew) * (np.abs(x) <= 1.0)
        f = profile(np.array([tc]))[0] ** 0.6
        off = off + dep * v * f
        xs = x if skew > 0 else -x
        nk = np.maximum(nk, np.exp(-((xs + 0.85) / 0.22) ** 2) + 0.35 * v)     # fibres at the sharp flank
    return off, np.clip(nk, 0, 1)


def lips(t, notches=None, jag_seed=0):
    """(aL, aR): across offsets of the left / right lip at full opening. aL < 0 < aR. v3: smooth runs + notches."""
    t = np.asarray(t, float)
    f = profile(t)
    c = path(t)
    bl, br = flap_bump(t, -1), flap_bump(t, +1)
    nl, kl = notch_profile(t, -1, notches)
    nr, kr = notch_profile(t, +1, notches)
    # fine torn jag ONLY in the notches (yarn ends where the rip jumped), never along the smooth runs
    jl = (1.6 * fbm(t / 6.0, 31 + jag_seed, 2) + 2.6 * fbm(t / 19.0, 32 + jag_seed, 2)) * kl * 0.6
    # v4: the right edge is ragged ALL along (yarn ends), the left clean except its two notches
    jr = (1.6 * fbm(t / 6.0, 41 + jag_seed, 2) + 2.6 * fbm(t / 19.0, 42 + jag_seed, 2)) * np.maximum(kr, 0.55)
    wl = W_L * WK * f * (1.0 + 0.03 * fbm(t / 260.0, 33, 2)) + bl * f ** 0.25
    wr = W_R * WK * f * (1.0 + 0.06 * fbm(t / 140.0, 43, 2)) + br * f ** 0.25
    aL = c - wl - nl * np.minimum(1, f * 4) + jl * np.minimum(1, f * 6)
    aR = c + wr + nr * np.minimum(1, f * 4) + jr * np.minimum(1, f * 6)
    aL = np.minimum(aL, c - 0.5)
    aR = np.maximum(aR, c + 0.5)
    return aL, aR


# v4 (critique B4.1): NO nested inner lips (the concentric almond read as anatomy / a stargate). Depth inside comes
# from (a) the bible's falloff (100 % at 40 % H, 70 % at the ends), (b) a visible THICKNESS on the right edge (the
# reverse face of the torn cloth seen in perspective, 4-8 % of the lens width, #3E3C66 -> #5B5A88) and (c) 3-4 soft
# VEILS deep inside, each a different torn shape (a slant, a hole, a fork, a flag), offset 6-15 % of the width and
# tilted 10-25 deg, never sharing the lens outline. Veil = (kind, t centre, across centre as a fraction of the half
# width (+ right), size t (m), size a (fraction of the width), tilt deg, seed)
VEILS = [
    ('slant', 230.0, -0.30, 330.0, 0.70, 18.0, 501),
    ('slant', 650.0, 0.25, 210.0, 0.60, -22.0, 502),      # (resume: the 'hole' veil read as a disc: replaced)
    ('fork', 430.0, 0.15, 260.0, 0.85, 12.0, 503),
    ('flag', 110.0, 0.35, 160.0, 0.55, -24.0, 504),
]
THICK_FRAC = 0.065       # right-edge cloth thickness, fraction of the local lens width
ZIP_T0 = 0.84            # the zipper of bridging threads: the top 16 % of the lens (fraction of T_TOP)
ZIP_N = 9                # threads (2 of them snapped)
ZIP_SNAPPED = (3, 6)
ZIP_W = 6.0              # thread width (m at full scale; >= 0.15 deg from the U7b bus)


def zipper_threads(seed=77):
    """[(t_left, t_right, sag m, width m, snapped bool)] of the bridging threads across the top of the lens."""
    rng = np.random.default_rng(seed)
    ts = np.linspace(ZIP_T0 * T_TOP + 12.0, T_TOP - 18.0, ZIP_N) + rng.uniform(-6, 6, ZIP_N)
    out = []
    for i, t in enumerate(ts):
        skew = rng.uniform(-4.0, 4.0)          # nearly square to the axis: stitches, never an X pattern
        out.append((float(t - skew), float(t + skew), float(rng.uniform(0.8, 2.0)), float(ZIP_W * rng.uniform(0.8, 1.15)),
                    i in ZIP_SNAPPED))
    return out


# inner ply: a second torn layer beneath the indigo (lavender-white, a little dimmer than the core). It is NOT a
# lens inside the lens (bible 4c: never concentric almonds): its torn edge runs DIAGONALLY across the hole, so the
# ply shows as a shelf along the left lip low down and along the right lip high up; the deepest white is beside it.
def ply_shelves(t):
    """(eL, eR): the ply's two torn edges. The ply fills [aL, eL] (a shelf hanging off the LEFT lip, low down) and
    [eR, aR] (a shelf off the RIGHT lip, high up). Where a shelf is absent its edge sits on its lip."""
    t = np.asarray(t, float)
    aL, aR = lips(t)
    w = aR - aL
    k = np.minimum(1, profile(t) * 5)
    # left shelf: from the cloud top up to t ~ 560, widest ~ t 200, a torn tongue at its top end
    sl = smoothstep(-60.0, 60.0, t) * smoothstep(560.0, 330.0, t) ** 0.8
    gl = sl * (0.36 + 0.08 * fbm(t / 90.0, 51, 2))
    jl = (1.6 * fbm(t / 5.0, 53, 2) + 4.5 * fbm(t / 36.0, 54, 2)) * k * sl
    # right shelf: from t ~ 330 up into the needle
    sr = smoothstep(300.0, 470.0, t) * smoothstep(930.0, 760.0, t) ** 0.7
    gr = sr * (0.40 + 0.08 * fbm(t / 80.0, 55, 2))
    jr = (1.6 * fbm(t / 5.0, 57, 2) + 4.5 * fbm(t / 36.0, 58, 2)) * k * sr
    return aL + w * gl + jl, aR - w * gr + jr


# ---------------------------------------------------------------------------------------------- rips
RIPS = [
    # bible: 170 m and 260 m (at U7, H 635 m => root scale 0.635), 6-12 m wide, 25-40 deg off the axis.
    # v4 (critique B4.6): dark-lipped lenses (Tear_Rip v4 texture), a smooth path (no zigzag), from the upper end.
    dict(name='Tear_Rip_Branch_A', side=+1, t0=815.0, length=260.0 / 0.635, off=31.0, bend=7.0, width=15.0, seed=301,
         window=(0.0, 0.75), jog=0.6),
    dict(name='Tear_Rip_Branch_B', side=-1, t0=745.0, length=170.0 / 0.635, off=35.0, bend=-6.0, width=12.0, seed=302,
         window=(0.25, 1.0), jog=0.6),
    # the HAIRLINE: the rip still running on up from the needle into the dark, 1-2 px, no glow; 2 tiny side twigs
    dict(name='Tear_Rip_Hairline', side=0, t0=T_TOP - 6.0, length=340.0, off=2.0, bend=-3.0, width=2.6, seed=303,
         window=(0.05, 0.9), jog=0.35, axis_start=True),
    dict(name='Tear_Rip_Twig_1', side=+1, t0=T_TOP + 120.0, length=60.0, off=38.0, bend=10.0, width=1.8, seed=304,
         window=(0.45, 0.9), jog=0.3, on='Tear_Rip_Hairline'),
    dict(name='Tear_Rip_Twig_2', side=-1, t0=T_TOP + 215.0, length=45.0, off=33.0, bend=-8.0, width=1.6, seed=305,
         window=(0.6, 1.0), jog=0.3, on='Tear_Rip_Hairline'),
]
RIP_MARGIN = 34.0     # half-width of the rip strip (m) incl. its glow


def rip_centreline(r, n=160):
    """(pts_ta[n,2], tangent_ta[n,2], normal_ta[n,2], u[n]) in axis coordinates (t, a)."""
    t0 = r['t0']
    if r.get('axis_start'):
        a0 = float(path(np.array([min(t0, T_TOP)]))[0])
    elif r.get('on'):
        host = [h for h in RIPS if h['name'] == r['on']][0]
        hp, _, _, hu = rip_centreline(host, 200)
        k = int(np.argmin(np.abs(hp[:, 0] - t0)))
        t0, a0 = float(hp[k, 0]), float(hp[k, 1])
    else:
        aL, aR = lips(t0)
        a0 = float(aR if r['side'] > 0 else aL) - r['side'] * 3.0
    u = np.linspace(0, 1, n)
    sd = r['side'] if r['side'] != 0 else 1
    ang = np.radians(r['off'] + r['bend'] * u ** 1.5 + 1.2 * fbm(u * 4, r['seed'], 2))   # from the axis
    dt = np.cos(ang)
    da = sd * np.sin(ang)
    L = r['length']
    ds = L / (n - 1)
    tt = t0 + np.concatenate([[0], np.cumsum(dt[:-1] * ds)])
    aa = a0 + np.concatenate([[0], np.cumsum(da[:-1] * ds)])
    tan = np.stack([dt, da], 1)
    nor = np.stack([-da, dt], 1) * sd
    jog = 2.2 * r.get('jog', 1.0) * fbm(u * 9, r['seed'] + 5, 2) * np.minimum(1, u * 8)
    pts = np.stack([tt, aa], 1) + nor * jog[:, None]
    return pts, tan, nor, u


def rip_width(r, u):
    """full width of the open crack (m, root scale 1) along u."""
    u = np.asarray(u, float)
    w = r['width'] * np.clip(1 - u ** 1.25, 0, 1) ** 1.05 * (0.82 + 0.18 * (1 + fbm(u * 9, r['seed'] + 9, 2)) * 0.5)
    return w * smoothstep(0.0, 0.04, u) * 0.6 + w * 0.4


# ---------------------------------------------------------------------------------------------- flaps
def flap_outline(fl, s):
    """normalized torn-edge distance (0..1 of fl['length']) along s in 0..1: one irregular torn tongue."""
    s = np.asarray(s, float)
    p = fl['peak']
    tri = np.where(s < p, (s / p) ** 0.7, ((1 - s) / (1 - p)) ** 0.8)
    tri = np.clip(tri, 0, 1)
    sd = fl['seed']
    tear = 1.0 + 0.10 * fbm(s * 4, sd, 3) + 0.025 * fbm(s * 19, sd + 1, 2)
    rng = np.random.default_rng(sd)
    c = rng.uniform(0.25, 0.75)
    tear = tear - rng.uniform(0.10, 0.18) * np.exp(-((s - c) / rng.uniform(0.04, 0.07)) ** 2)
    return np.clip(tri * tear, 0, 1.05) * smoothstep(0.0, 0.05, s) * smoothstep(1.0, 0.95, s)


def flap_frame(fl, s):
    """hinge point (t, a) and outward unit vector (dt, da) in axis coords, for s in 0..1 along the flap's hinge."""
    t = fl['t0'] + (fl['t1'] - fl['t0']) * np.asarray(s, float)
    aL, aR = lips(t)
    a = aR if fl['side'] > 0 else aL
    eps = 1.0
    aL2, aR2 = lips(t + eps)
    a2 = aR2 if fl['side'] > 0 else aL2
    da_dt = (a2 - a) / eps
    nt, na = -da_dt * fl['side'], 1.0 * fl['side']
    n = np.sqrt(nt ** 2 + na ** 2)
    return t, a, nt / n, na / n


# the fingertips that hook the flaps / lip (gate layout v4): (side, flap name or None = the lip itself, s along the
# hinge (or t for the lip), r along the flap (fraction of its torn length), tent m, pull (out, toward bus, down))
GRIPS = [
    (-1, 'Tear_Flap_L', 0.30, 0.93, 14.0), (-1, 'Tear_Flap_L', 0.66, 0.93, 12.0), (-1, None, 370.0, 0.0, 0.0),
    (+1, 'Tear_Flap_R', 0.30, 0.95, 22.0), (+1, 'Tear_Flap_R', 0.52, 0.96, 26.0), (+1, 'Tear_Flap_R', 0.74, 0.95, 20.0),
]


def flap_surface(fl, ns=72, nr=40, grips=True):
    """v4: the flap is the sky's cloth peeled off the lip. Its hinge runs on the (pushed-out) lip; flat, it would lie
    INWARD from the hinge over the hole. It is lifted toward the bus by lift(s) (0 at both ends: welded), then its
    last ~40 % ROLLS back outward over itself (the rolled lip, radius ~L x 0.45 / roll). The bus sees the OUTER face
    on the lifted sheet and the wound-lit inner face only on the roll. Where a fingertip grips the rolled lip the
    cloth is TENTED toward the bus and outward (Gaussian along s), with a crease running from the grip into the flap.
    Thin cloth, smooth (facets <= 8 deg at ns x nr)."""
    s = np.linspace(0, 1, ns)
    t, a, ot, oa = flap_frame(fl, s)
    out3 = ot[:, None] * AX[None] + oa[:, None] * AC[None]
    out3 = out3 / np.linalg.norm(out3, axis=1, keepdims=True)
    in3 = -out3
    view3 = -DEPTH
    L = fl['length']
    edge = flap_outline(fl, s)
    rmax = np.clip(edge, 0.03, 1.05)
    r = np.linspace(0, 1, nr)[None, :] * rmax[:, None]
    lift = np.radians(fl['lift']) * np.sin(np.pi * s) ** 0.8
    rn = np.clip(r / np.maximum(rmax[:, None], 1e-3), 0, 1)
    rollf = smoothstep(0.52, 1.0, rn) ** 1.25
    phi = lift[:, None] + np.radians(fl['roll']) * rollf * (0.85 + 0.3 * np.clip(rmax[:, None], 0, 1))
    dr = np.diff(r, axis=1, prepend=0.0) * L
    cx = np.cumsum(np.cos(phi) * dr, axis=1)          # inward (over the hole)
    cy = np.cumsum(np.sin(phi) * dr, axis=1)          # toward the bus
    base = P(t, a)
    pos = base[:, None, :] + cx[..., None] * in3[:, None, :] + cy[..., None] * view3[None, None, :]
    # soft silk drape along the hinge (long, low: cloth, not foil)
    rng = np.random.default_rng(fl['seed'] + 99)
    span = fl['t1'] - fl['t0']
    lam = rng.uniform(110.0, 160.0)
    wav = s[:, None] * span / lam * 6.283 + rng.uniform(0, 6.28) + 0.6 * fbm(s[:, None] * 3 + r, fl['seed'] + 12, 2)
    fold = np.sin(wav) * 4.0 * np.clip(rn, 0, None) ** 1.2
    pos = pos + fold[..., None] * view3[None, None, :]
    if grips:
        for (sd, nm, sg, rg, tent) in GRIPS:
            if nm != fl['name']:
                continue
            g = np.exp(-((s[:, None] - sg) / 0.11) ** 2) * smoothstep(0.35, 1.0, rn)      # resume: broader, softer tents
            pull = (0.55 * view3[None, None, :] + 0.6 * out3[:, None, :] - 0.35 * np.array([0, 0, 1.0])[None, None, :])
            pos = pos + (tent * g)[..., None] * pull / np.linalg.norm(pull, axis=-1, keepdims=True)
            crease = np.exp(-((s[:, None] - sg) / 0.035) ** 2) * smoothstep(0.1, 0.8, rn) * 3.0
            pos = pos + crease[..., None] * view3[None, None, :]
    # the OUTER (dyed, sky-side) face looks at the bus while the sheet is only lifted (phi < 90): n = cos(phi) view - sin(phi) in
    # (resume fix: the v4 draft had the sign reversed, so the bus saw the wound-lit inner face everywhere)
    n_ana = np.cos(phi)[..., None] * view3[None, None, :] - np.sin(phi)[..., None] * in3[:, None, :]
    dPs = np.gradient(pos, axis=0)
    dPr = np.gradient(pos, axis=1)
    n_out = np.cross(dPs, dPr)
    n_out /= np.linalg.norm(n_out, axis=-1, keepdims=True) + 1e-12
    sgn = np.sign(np.sum(n_out * n_ana, -1, keepdims=True))
    sgn[sgn == 0] = 1
    n_out = n_out * np.median(sgn)
    return dict(pos=pos, n_out=n_out, s=s, r=r, rn=rn, rmax=rmax, edge=edge, psi=phi, a_hinge=a, t_hinge=t)


def grip_kit(k):
    """kit-space position (full opening) and a_hinge of grip k (GRIPS order): the fingertip's contact point."""
    sd, nm, sg, rg, tent = GRIPS[k]
    if nm is None:
        aL, aR = lips(np.array([sg]))
        a = float(aR[0] if sd > 0 else aL[0])
        return P(sg, a + sd * 4.0, -8.0)[()], a
    fl = [f for f in FLAPS if f['name'] == nm][0]
    sf = flap_surface(fl, 121, 61)
    i = int(round(sg * 120))
    j = int(round(rg * 60))
    return sf['pos'][i, j], float(sf['a_hinge'][i])


# ---------------------------------------------------------------------------------------------- stage table
STAGES = {
    # bible §6·4 table. D = distance bus -> tear foot, H = height, open = width fraction, cam = bus above cloud top
    'U6': dict(D=2700.0, H=565.0, open=0.18, cam=40.0, rip=0.0, pitch=0.0),
    'U7': dict(D=1800.0, H=635.0, open=0.22, cam=50.0, rip=0.55, pitch=0.0),
    'U8': dict(D=900.0, H=875.0, open=0.30, cam=60.0, rip=1.0, pitch=18.0),
}


def tear_open_param(frac):
    """_Udon_TearOpen for a width fraction (0.18 -> 0, 0.30 -> 1)."""
    return (frac - OPEN_MIN) / (OPEN_MAX - OPEN_MIN)


def width_mul(open01):
    return (OPEN_MIN + (OPEN_MAX - OPEN_MIN) * open01) / OPEN_MAX


# ---------------------------------------------------------------------------------------------- sky-cloth folds
# The sky around the wound is the cloth itself: pulled apart sideways it wrinkles ALONG the pull (horizontal folds
# leaving the lips) and fans out from the top tip where the stress runs on as the two rips.
FOLD_T0, FOLD_T1 = -150.0, 1500.0
FOLD_A0, FOLD_A1 = -900.0, 900.0
FOLD_CLAMP = (-W_L, W_R)       # across offsets that move with the opening (vertex shader: a += (w-1)*clamp(a))
