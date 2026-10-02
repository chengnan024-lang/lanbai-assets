"""蓝白 / Lanbai: TENTACLE LIBRARY v2.1 for the tentacle gate (Blender 5.0.1 as the bpy module).

One script regenerates everything from scratch:

    python3 build_library.py                      # textures, 8 variants x 3 LODs, FBX, all renders
    python3 build_library.py --only tex,fbx       # just the assets
    python3 build_library.py --only lineup --res 960 540 --samples 32 --tag _test   # quick test render

Outputs (default --out = <lanbai>/deliver/Tentacles, or the folder above Source/ when run from there):
    Textures/T_Tentacle_Albedo.png             2048^2  sRGB
    Textures/T_Tentacle_Normal.png             2048^2  tangent space, OpenGL (+Y = +V)
    Textures/T_Tentacle_MetallicSmoothness.png 2048^2  R = metallic (0), A = smoothness
    Textures/T_Tentacle_DetailNormal.png       1024^2  tangent space, OpenGL; tiling (4, 4.6)
    Textures/T_Tentacle_<X>_Occlusion.png      1024^2  per variant, at (U, t): B crease mask, R macro, G occl.
    FBX/Tentacle_A.fbx .. Tentacle_H.fbx       Empty Tentacle_X + Tentacle_X_LOD0/1/2
    Renders/lineup.png, flyby.png (library renders); gate.png (the gate stage)
    GateLayout.json                            the gate composition (ART BIBLE v2 distance table), Unity space

Design v2.1 ("生 Living skin", ART BIBLE v2 §6·4 + the v1 art / tech verification; these override older numbers):
    * a real animal's arm, slender (length / root radius 30-46): a muscular swell above the root, a heavy body
      to ~45 % of the length, a CONCAVE neck after 57 % and from 87 % on a THREAD of nearly constant thinness
      (2-5 % of the root: a whip lash, never a cone -- a cone reads as a claw, a horn, a grass blade);
      2-3 muscle swellings + asymmetric muscle lumps in the section; no suckers;
    * centrelines integrated from curvature (wide clothoid bends, stronger toward the thin end), in a
      rotation-minimising frame (+ optional corkscrew that opens as it rises); a smoothed twist keeps the U seam
      on local -Y;
    * 8 variants, 8 different WHOLE-BODY gestures (whip, droop, corkscrew, broad C + open coil, double S +
      forked tip, wave crest, colossus swan neck + braid, colossus reach with a frayed end) and varied tips
      (straight threads with S-waves, half curl, forked tongue, fray, hooks; one coil only);
    * skin: albedo sRGB 30-44 with blue-plum mottling; smoothness ~0.63 base, wet / dry patches, soft
      longitudinal mucus runs to 0.86-0.92; compression wrinkles drawn as individual staggered, tapered,
      8-20 deg helical strokes, shown ONLY on the concave side by a per-variant curvature-baked mask
      (T_Tentacle_X_Occlusion.b) that scales the MAIN normal only -- the detail normal (the hide's fine
      relief) is everywhere, so the taut convex side is skin, not rubber; no rings, no Voronoi, no scales;
      colossi get 2-8 m macro undulation and no fine creases beyond 1.5 km.

Mesh contract (SPEC + fix): origin at the root centre, growing along +Z; UV0 'UVMap' U around (seam on
local -Y), V along, conformal, centred on 0; UV1 'UVSway' = (t, phase) at float precision (the Unity
shader sways from it: vertex colours are 8-bit there); 'Col' (linear) R = t root->tip, G = per-variant
phase, B = radius / root radius, A = 1; LOD0 <= 6000, LOD1 <= 2000, LOD2 <= 600 triangles; closed tip,
hard-split root cap.
"""
import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_lib():
    cands = [os.environ.get('LANBAI_LIB', ''), os.path.join(HERE, 'lib'), os.path.join(HERE, '..', 'lib'),
             os.path.join(HERE, '..', '..', 'lib'), os.path.join(HERE, '..', '..', '..', 'lib')]
    for c in cands:
        if c and os.path.exists(os.path.join(c, 'export_unity.py')):
            return os.path.abspath(c)
    raise SystemExit('lib/ (export_unity.py, preview_rig.py) not found; set LANBAI_LIB')


LIB = _find_lib()
sys.path.insert(0, LIB)


def _default_out():
    if os.path.basename(HERE) == 'Source':
        return os.path.abspath(os.path.join(HERE, '..'))
    return os.path.abspath(os.path.join(HERE, '..', '..', 'deliver', 'Tentacles'))


OUT = _default_out()
WORK = os.path.join(HERE, 'work')          # preview-only files (texture mips)
WIP = os.path.join(HERE, 'wip')

import numpy as np
from PIL import Image

try:
    import bpy
    from mathutils import Vector, Matrix, Quaternion
except ImportError:          # texture / shape code also runs in plain python
    bpy = None

TEX_N = 2048
DET_N = 1024
DETAIL_TILING = (4.0, 4.6)   # U must be an integer (seam); V deliberately not (breaks repetition)


# =============================================================================================
# 1. TEXTURES  (numpy only; every layer is built on the torus, so the maps tile exactly)
# =============================================================================================
class Torus:
    """Periodic noise toolbox on an n x n grid; arrays are [j, i] with j = V (along), i = U (around)."""

    def __init__(self, n, aspect_v=1.0):
        self.n = n
        c = (np.arange(n) + 0.5) / n
        self.U, self.V = np.meshgrid(c, c)
        f = np.fft.fftfreq(n, 1.0 / n)
        self.KX = f[None, :]                   # cycles per tile along U
        self.KY = f[:, None] / aspect_v        # along V, in "surface" units (detail map is stretched)

    def noise(self, f_lo, f_hi, beta=1.0, ax=1.0, ay=1.0, seed=0):
        """Band-limited noise, std 1. ax > 1 = finer along U, ay > 1 = finer along V."""
        g = np.random.default_rng(seed)
        k = np.sqrt((self.KX / ax) ** 2 + (self.KY / ay) ** 2)
        filt = np.where(k > 0, np.maximum(k, 1e-6) ** (-beta), 0.0)
        filt *= np.exp(-(k / f_hi) ** 2) * (1 - np.exp(-(k / max(f_lo, 1e-3)) ** 2))
        x = np.real(np.fft.ifft2(np.fft.fft2(g.standard_normal((self.n, self.n))) * filt))
        return (x - x.mean()) / (x.std() + 1e-12)

    def streaks(self, seed, f_across, bw_across, bw_along, angle_deg=0.0):
        """Noise streaky ALONG V (sinew / fibre grain), with a slight spiral angle."""
        g = np.random.default_rng(seed)
        a = math.radians(angle_deg)
        du, dv = math.sin(a), math.cos(a)                 # along-grain direction in (u, v)
        ka = self.KX * du + self.KY * dv
        kn = self.KX * dv - self.KY * du
        env = np.exp(-(ka / bw_along) ** 2) * np.exp(-((np.abs(kn) - f_across) / bw_across) ** 2)
        spec = (g.standard_normal((self.n, self.n)) + 1j * g.standard_normal((self.n, self.n))) * env
        x = np.fft.ifft2(spec).real
        return (x - x.mean()) / (x.std() + 1e-12)

    def blur(self, x, sigma):
        ker = np.exp(-2 * (np.pi * sigma) ** 2 * ((self.KX / self.n) ** 2 + (self.KY / self.n) ** 2))
        return np.real(np.fft.ifft2(np.fft.fft2(x) * ker))

    def splat(self, ij, heights, sigma):
        img = np.zeros((self.n, self.n))
        np.add.at(img, (ij[:, 0] % self.n, ij[:, 1] % self.n), heights)
        n = self.n
        kx = np.fft.fftfreq(n, 1.0 / n)[None, :]
        ky = np.fft.fftfreq(n, 1.0 / n)[:, None]
        ker = np.exp(-2 * (np.pi * sigma) ** 2 * ((kx / n) ** 2 + (ky / n) ** 2))
        return np.real(np.fft.ifft2(np.fft.fft2(img) * ker))


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _fold_profile(phase, crest=0.5):
    """Annular fold: 0 in the crease at integer phase, 1 on the crest. A raised cosine (soft, round
    crests AND soft creases: the old sharp asymmetric quadratic sawtoothed the rim light)."""
    f = phase - np.floor(phase)
    return 0.5 - 0.5 * np.cos(2 * np.pi * f)


def _vwarp(V, amps, seed):
    """Monotonic periodic re-parametrisation of V: fold spacing varies 0.6x..2.5x along the tile,
    so folds come in groups with smooth stretches between (no bead chain)."""
    rng = np.random.default_rng(seed)
    d = np.zeros_like(V)
    for k, a in enumerate(amps, 1):
        d += a * np.sin(2 * np.pi * k * V + rng.uniform(0, 2 * np.pi)) / (2 * np.pi * k)
    return V + d


def _vnoise(V, U, seed, kmax=4, helix=0):
    """Smooth periodic 1-D noise along the (helical) fold direction, 0..1: gives each fold its own
    depth without indexing folds by id (an id jumps at the U seam once the folds are helical)."""
    rng = np.random.default_rng(seed)
    x = np.zeros_like(V)
    for k in range(1, kmax + 1):
        x += rng.normal() / k * np.sin(2 * np.pi * k * V + rng.uniform(0, 2 * np.pi))
    x = (x - x.min()) / (x.max() - x.min() + 1e-9)
    return x


def _wrap(x):
    """Signed periodic distance on the unit torus axis."""
    return x - np.round(x)


def _crease_strokes(n, seed=5, rows_mean=15.0):
    """COMPRESSION WRINKLES as individual strokes (v2: replaces the annular fold rings, which read as a
    hose / earthworm). Rows of transverse wrinkles at pitch 0.25-0.6 x the local radius (+-40 %),
    each row broken into staggered strokes 12-40 % of the circumference long that taper like crescents,
    tilted 8-20 deg (helical, mostly one hand), each with its own depth (many shallow, few deep), a
    soft skin roll on either side, plus short oblique bridges that fork between neighbouring rows.
    The per-variant crease mask (Occlusion.B) decides where any of this shows (concave side only).
    Returns height H (<= 0 in grooves), groove weight G (0..1) and roll weight P (0..1)."""
    rng = np.random.default_rng(seed)
    c = (np.arange(n) + 0.5) / n
    H = np.zeros((n, n))
    G = np.zeros((n, n))
    P = np.zeros((n, n))
    pitch = rng.uniform(0.6, 1.4, int(rows_mean))
    pitch = pitch / pitch.sum()                                   # rows tile exactly in V
    v_rows = np.cumsum(pitch) - pitch / 2 + rng.uniform(0, 1)
    strokes = []
    for k, v0 in enumerate(v_rows):
        pk = pitch[k]
        u = rng.uniform(0, 1)
        end = u + 1.0
        while u < end - 0.04:
            ln = rng.uniform(0.12, 0.40)
            ln = min(ln, end - u)
            tilt = math.radians(rng.uniform(8, 20)) * (1 if rng.random() < 0.8 else -1)
            depth = float(np.clip(rng.lognormal(math.log(0.55), 0.55), 0.12, 1.6))
            strokes.append((u + ln / 2, v0 + rng.normal(0, 0.12) * pk, ln, tilt, depth, pk, rng.uniform(0, 6.28),
                            rng.uniform(0.6, 1.3)))
            u += ln + rng.uniform(-0.03, 0.07)                   # small gaps, some overlaps
        # oblique bridges toward the next row: the wrinkles fork and merge
        for _ in range(rng.integers(1, 4)):
            strokes.append((rng.uniform(0, 1), v0 + 0.5 * pk, rng.uniform(0.03, 0.07),
                            math.radians(rng.uniform(30, 60)) * (1 if rng.random() < 0.5 else -1),
                            float(rng.uniform(0.2, 0.5)), pk, rng.uniform(0, 6.28), 0.8))
    for (uc, vc, ln, tilt, depth, pk, wph, wsc) in strokes:
        half = ln / 2
        i0 = int(math.floor((uc - half) * n)) - 2
        i1 = int(math.ceil((uc + half) * n)) + 2
        cols = np.arange(i0, i1) % n
        du = _wrap(c[cols] - uc)                                   # -half..half along the stroke
        x = np.clip(du / half, -1, 1)
        env = np.clip(1 - x * x, 0, 1) ** 0.8                      # crescent taper
        wob = 0.10 * pk * np.sin(2 * np.pi * du / ln * 1.3 + wph)
        vline = vc + math.tan(tilt) * du + wob
        sig = 0.10 * pk * wsc
        span = 0.8 * pk + abs(math.tan(tilt)) * half + 0.15 * pk
        j0 = int(math.floor((vc - span) * n))
        j1 = int(math.ceil((vc + span) * n))
        rows = np.arange(j0, j1) % n
        dv = _wrap(c[rows][:, None] - vline[None, :])
        g = np.exp(-(dv / sig) ** 2) * env[None, :]
        roll = np.exp(-((np.abs(dv) - 0.42 * pk) / (0.20 * pk)) ** 2) * env[None, :]
        ix = np.ix_(rows, cols)
        H[ix] += depth * (-g + 0.28 * roll)
        G[ix] = np.maximum(G[ix], np.clip(depth, 0, 1) * g)
        P[ix] = np.maximum(P[ix], roll * min(depth, 1.0))
    return H, np.clip(G, 0, 1), np.clip(P, 0, 1)


def tex_fields(n=TEX_N):
    """ART BIBLE v2 skin (「生」 v2), the shared tiled layer. Two regimes, chosen per variant by the
    curvature-baked crease mask (T_Tentacle_X_Occlusion.b):
      * CONCAVE side of a bend: staggered compression wrinkles (_crease_strokes), not rings;
      * CONVEX side and straight stretches: taut, smooth hide: faint long muscle bundles under the skin
        (elongated along V, random angle, patchy), sparse low papillae, a few pores. The long mucus streaks
        live in the smoothness (tex_smoothness). No evenly spaced rings, no Voronoi, no scales."""
    T = Torus(n)
    rng = np.random.default_rng(7)
    Hc, groove, roll = _crease_strokes(n)
    # ---- taut hide: muscle bundles under the skin (long, soft, low), patchy ------------------------------
    bund = T.noise(2, 14, 1.3, ax=1.0, ay=0.28, seed=14)
    bund2 = T.noise(3, 10, 1.2, ax=1.0, ay=0.4, seed=18)
    patch = np.clip(0.5 + 0.5 * T.noise(1, 5, 1.0, seed=15), 0.0, 1.0)
    H_b = 0.55 * bund + 0.30 * bund2 * patch
    # ---- papillae (sparse, low) and pores -----------------------------------------------------------------
    dens = np.clip(0.5 + 0.5 * T.noise(1, 8, 1.0, seed=10), 0.05, 1.0)
    dens = dens / dens.sum()
    H_pap = np.zeros((n, n))
    pap = np.zeros((n, n))
    for count, sig, amp in ((5000, 1.6, 0.4), (1400, 3.0, 0.8)):
        idx = rng.choice(n * n, size=count, p=dens.ravel())
        ij = np.stack([idx // n, idx % n], -1)
        H_pap += T.splat(ij, amp * (0.6 + 0.4 * rng.random(count)), sig)
        pap += T.splat(ij, np.ones(count), sig)
    H_pap = np.minimum(H_pap / np.percentile(H_pap, 99.5), 1.0)
    pap = np.clip(pap / np.percentile(pap, 99.5), 0, 1)
    idx = rng.integers(0, n * n, 1200)
    pores = T.splat(np.stack([idx // n, idx % n], -1), 0.5 + rng.random(1200), 1.0)
    pores = np.clip(pores / np.percentile(pores, 99.8), 0, 1)
    fine = T.noise(40, 160, 0.7, seed=16)
    H = 6.0 * T.blur(Hc, 1.0) + 0.9 * H_b + 0.35 * H_pap - 0.12 * pores + 0.05 * fine
    # ---- mucus streaks (smoothness): 5-20 cm wide on a mid arm, long, running along V, breaking up -----------
    st = np.zeros((n, n))
    mea = T.noise(1, 4, 1.2, ax=1.0, ay=0.6, seed=38)                                      # the runs meander
    for i, (fa, bw) in enumerate(((14.0, 6.0), (22.0, 9.0))):
        s_ = T.streaks(31 + i, fa, bw, 0.9 + 0.4 * i, angle_deg=(-4.0, 5.0)[i])
        s_ = np.roll(s_, 0, axis=1)
        brk = np.clip(0.05 + 1.0 * T.noise(1, 5, 1.0, ax=0.3, seed=35 + i), 0, 1)       # long runs, gaps
        st = np.maximum(st, _smoothstep(1.1, 2.3, s_) * brk)
    # warp across the body by the meander field (runs of mucus are never ruler-straight), then soften
    iu = (np.arange(n)[None, :] + np.round(18.0 * mea).astype(int)) % n
    st = np.take_along_axis(st, iu, axis=1)
    st = T.blur(st, 4.0)
    st = st / (st.max() + 1e-9)
    wet = T.noise(1, 4, 1.3, seed=35)
    crease = np.clip(groove, 0, 1)
    return dict(H=H, crease=crease, pap=pap, pores=pores, streak=np.clip(st, 0, 1), wet=wet, groove=groove,
                roll=roll, T=T)


def normal_from_height(H, strength=1.0):
    gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5
    gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5
    nrm = np.stack([-strength * gx, -strength * gy, np.ones_like(H)], -1)
    return nrm / np.linalg.norm(nrm, axis=-1, keepdims=True)


def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)


def srgb2lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


ALBEDO_LIN = (0.013, 0.025)        # ART BIBLE v2: tentacle albedo sRGB 30-44 (the ink comes from the specular)


def tex_albedo(f):
    """sRGB 30-44 (linear 0.013-0.025): a dark blue-black hide with 20-30 % blue-plum MOTTLING
    (slate-blue and plum patches 0.3-3 m across on a mid arm, like whale / eel skin), sparse darker
    freckles; creases a touch darker, wet streaks a touch deeper. Clamped to the bible's range."""
    T = f['T']
    base = np.array([0.0150, 0.0152, 0.0192])
    slate = np.array([0.0148, 0.0172, 0.0246])
    plum = np.array([0.0212, 0.0153, 0.0208])
    m1 = _smoothstep(-0.4, 1.3, T.noise(1, 5, 1.4, ax=0.8, seed=21))              # slate-blue patches
    m2 = _smoothstep(-0.1, 1.5, T.noise(1, 7, 1.3, ax=1.2, seed=36))              # plum patches
    m2 = m2 * (1 - 0.6 * m1)
    col = base[None, None] * (1 - m1 - m2)[..., None] + slate * m1[..., None] + plum * m2[..., None]
    col = col * (1.0 + 0.06 * T.noise(3, 24, 1.1, seed=22))[..., None]                # breaks the patches up
    frk = _smoothstep(1.6, 2.6, T.noise(60, 220, 0.6, seed=23))                        # sparse dark freckles
    col *= (1.0 - 0.18 * frk)[..., None]
    col *= (1.0 - 0.08 * f['crease'])[..., None]         # (shared tile: not masked, keep faint)
    col *= (1.0 - 0.07 * f['streak'])[..., None]
    col += np.array([0.0015, 0.0016, 0.0022]) * (f['pap'] ** 1.5)[..., None]
    col *= (1.0 + 0.03 * T.noise(200, 700, 0.3, seed=25))[..., None]
    return np.clip(col, ALBEDO_LIN[0], ALBEDO_LIN[1])


def tex_smoothness(f):
    """ART BIBLE v2 + fix: base ~0.66 with low-frequency WET / DRY patches (+-0.10), LONGITUDINAL mucus
    streaks along V up to 0.90 (5-20 cm wide, long runs that break up), water held in the creases
    (0.85), the rolled crests between creases drier; never constant over more than ~30 cm."""
    T = f['T']
    s = 0.63 + 0.11 * np.tanh(1.2 * f['wet'])
    s = s + (0.86 - s) * f['streak']
    s = np.maximum(s, s + 0.08 * f['groove'])                            # creases hold a little water (faint:
    s -= 0.03 * f['roll'] * (1 - f['streak'])                             # not masked, must not draw rings)
    s += 0.015 * T.noise(20, 120, 0.8, ax=0.5, seed=37)                    # no constant areas
    s -= 0.05 * f['pap'] ** 1.2
    return np.clip(s, 0.52, 0.92)


def tex_detail(n=DET_N):
    """Detail normal, tiled (4, 4.6) on UV0: an ISOTROPIC fine skin relief -- a faint meandering network of
    shallow micro-grooves (contour lines of band-limited noise, like the back of a hand; no parallel lines,
    no cells), micro papillae and pores. Authored with the V stretch compensated, so it is isotropic on the
    skin. Subtle: it only holds up where the bus passes within metres."""
    T = Torus(n, aspect_v=DETAIL_TILING[1] / DETAIL_TILING[0])
    rng = np.random.default_rng(77)
    net = T.noise(6, 30, 1.0, seed=51)
    msk = np.clip(0.35 + 0.65 * T.noise(1, 4, 1.0, seed=61), 0.0, 1.0)
    H = -0.35 * np.exp(-(net / 0.22) ** 2) * msk
    H += 0.10 * T.noise(12, 90, 0.7, seed=52)
    idx = rng.integers(0, n * n, 2200)
    ij = np.stack([idx // n, idx % n], -1)
    H += 0.45 * np.minimum(T.splat(ij, 0.6 + 0.4 * rng.random(len(idx)), 1.4) / 0.8, 1.0)
    idx = rng.integers(0, n * n, 700)
    ij = np.stack([idx // n, idx % n], -1)
    H -= 0.40 * np.clip(T.splat(ij, 1.0, 0.9) / 0.5, 0, 1)
    return normal_from_height(H * 2.2)


OCC_N = 1024
MACRO = {'G': 1.0, 'H': 1.0}          # colossi: 2-8 m macro undulation (scar grooves, wet eroded basalt)


def occlusion_map(key, n=OCC_N):
    """T_Tentacle_X_Occlusion (per variant, sampled at (U, t) = (UV0.x, UV1.x), NOT tiled):
      B = curvature-baked CREASE MASK: 1 on the concave (compressed) side of a bend, 0 on the convex side
          and on straight stretches (ART BIBLE v2: creases only where the skin is compressed);
      R = macro height (colossi: 2-8 m scar grooves like wet eroded basalt; 0.5 = flat for A-F);
      G = occlusion (a little darker in the creases) for Standard's _OcclusionMap.
    Rows = t (root at the bottom row, as Unity samples V), columns = U."""
    sp = VARIANTS[key]
    cl = centreline(key)
    u, s, T, Bv = cl['u'], cl['s'], cl['T'], cl['B']
    n1, n2, _ = seam_frames(T, Bv, s, max(sp.get('seam_sigma', 0.003) * s[-1], 0.05))
    kv = np.gradient(T, s, axis=0)                                  # curvature vector (toward the centre)
    km = np.linalg.norm(kv, axis=1)
    sig = max(3, int(len(s) * 0.004))                               # smooth over ~0.4 % of the length
    ker = np.exp(-0.5 * (np.arange(-3 * sig, 3 * sig + 1) / sig) ** 2); ker /= ker.sum()
    kv = np.stack([np.convolve(np.pad(kv[:, i], 3 * sig, mode='edge'), ker, 'valid') for i in range(3)], -1)
    km = np.linalg.norm(kv, axis=1)
    khat = kv / np.maximum(km, 1e-9)[:, None]
    r = sp['R'] * radius_profile(u, sp.get('heavy', 1.0), (sp['phase'] * 7.3) % 1.0)
    strain = r * km                                                 # compressive strain on the inner side ~ r / R_bend
    tq = (np.arange(n) + 0.5) / n
    uq = (np.arange(n) + 0.5) / n
    rows = lambda a: np.stack([np.interp(tq, u, a[:, i]) for i in range(3)], -1)
    N1, N2, K = rows(n1), rows(n2), rows(khat)
    st = np.interp(tq, u, strain)
    th = 2 * np.pi * uq
    dirs = np.cos(th)[None, :, None] * N1[:, None, :] + np.sin(th)[None, :, None] * N2[:, None, :]
    conc = np.einsum('tuk,tk->tu', dirs, K)                          # +1 = inner (concave) side
    mask = _smoothstep(0.20, 0.80, conc) * _smoothstep(0.02, 0.12, st)[:, None]      # crescent: +-70 deg of the inner line
    mask *= _smoothstep(0.995, 0.93, tq)[:, None]                    # nothing on the last thread
    from scipy.ndimage import gaussian_filter
    mask = gaussian_filter(mask, (2.0, 3.0), mode=('nearest', 'wrap'))
    macro = np.full((n, n), 0.5)
    if key in MACRO:
        Tm = Torus(n)
        # wet eroded basalt: pits and lumps in every direction (v1's grooves along the body read as tree bark)
        kseed = sum(ord(c) for c in key)            # (gate v4: multi-letter custom keys)
        g1 = Tm.noise(6, 30, 1.2, ax=1.0, ay=0.85, seed=80 + kseed)
        g2 = Tm.noise(16, 70, 1.0, ax=1.0, ay=1.0, seed=90 + kseed)
        ridged = 0.7 * g1 / 2.5 - 0.30 * np.abs(g2) / 2.5
        fade = _smoothstep(0.02, 0.10, tq) * _smoothstep(0.85, 0.65, tq)
        macro = 0.5 + 0.5 * np.clip((ridged - ridged.mean()) / (3 * ridged.std()), -1, 1) * fade[:, None] * MACRO[key]
    occ = 1.0 - 0.35 * mask
    return np.stack([macro, occ, mask], -1)


def build_occlusion_maps(out_dir, keys=None):
    os.makedirs(out_dir, exist_ok=True)
    for k in (keys or ORDER):
        m = occlusion_map(k)
        _save_rgb(os.path.join(out_dir, 'T_Tentacle_%s_Occlusion.png' % k), m)
        print('occlusion %s: crease-mask coverage %.1f %%  (>0.5: %.1f %%)' % (k, 100 * m[..., 2].mean(), 100 * (m[..., 2] > 0.5).mean()))


def _save_rgb(path, arr):
    Image.fromarray(np.ascontiguousarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)[::-1]), 'RGB').save(path)


def build_textures(out_dir, n=TEX_N, stats=True):
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    f = tex_fields(n)
    nrm = normal_from_height(f['H'])
    alb = tex_albedo(f)
    sm = tex_smoothness(f)
    _save_rgb(os.path.join(out_dir, 'T_Tentacle_Albedo.png'), lin2srgb(alb))
    _save_rgb(os.path.join(out_dir, 'T_Tentacle_Normal.png'), nrm * 0.5 + 0.5)
    ms = np.zeros((n, n, 4), np.uint8)
    ms[..., 3] = (sm * 255 + 0.5).astype(np.uint8)
    Image.fromarray(np.ascontiguousarray(ms[::-1]), 'RGBA').save(os.path.join(out_dir, 'T_Tentacle_MetallicSmoothness.png'))
    det = tex_detail()
    _save_rgb(os.path.join(out_dir, 'T_Tentacle_DetailNormal.png'), det * 0.5 + 0.5)
    build_occlusion_maps(out_dir)
    if stats:
        tilt = np.degrees(np.arccos(np.clip(nrm[..., 2], -1, 1)))
        dt = np.degrees(np.arccos(np.clip(det[..., 2], -1, 1)))
        print('tex: normal tilt mean %.1f p95 %.1f | detail mean %.1f p95 %.1f | albedo lin mean %s | '
              'smooth mean %.3f min %.2f max %.2f | %.0fs' % (
                  tilt.mean(), np.percentile(tilt, 95), dt.mean(), np.percentile(dt, 95),
                  np.round(alb.reshape(-1, 3).mean(0), 4), sm.mean(), sm.min(), sm.max(), time.time() - t0))
    build_mips(out_dir)
    return f


def build_mips(tex_dir):
    """Box-filtered mip levels 2/4/6 (what Unity's importer generates); PREVIEW ONLY (Cycles has no
    texture mips, so without these sub-pixel papillae alias into glitter Unity would never show)."""
    os.makedirs(os.path.join(WORK, 'mips'), exist_ok=True)
    for fn in ('T_Tentacle_Albedo', 'T_Tentacle_MetallicSmoothness', 'T_Tentacle_Normal'):
        im = Image.open(os.path.join(tex_dir, fn + '.png'))
        a = np.asarray(im).astype(np.float64) / 255
        if fn.endswith('Albedo'):
            a = srgb2lin(a)
        for lv in (2, 4, 6):
            k = 2 ** lv
            b = a.reshape(a.shape[0] // k, k, a.shape[1] // k, k, -1).mean((1, 3))
            if fn.endswith('Albedo'):
                b = lin2srgb(b)
            Image.fromarray((np.clip(b, 0, 1) * 255 + 0.5).astype(np.uint8).squeeze(), im.mode).save(
                os.path.join(WORK, 'mips', '%s_%d.png' % (fn, lv)))


def texture_sheet(tex_dir, path):
    """Look at the maps: 2x2 tiles of albedo (exposed up), the normal map lit by a grazing light, and
    smoothness; plus a 1:1 crop. For eyes only."""
    alb = np.asarray(Image.open(os.path.join(tex_dir, 'T_Tentacle_Albedo.png'))).astype(float) / 255
    nrm = np.asarray(Image.open(os.path.join(tex_dir, 'T_Tentacle_Normal.png'))).astype(float) / 255 * 2 - 1
    ms = np.asarray(Image.open(os.path.join(tex_dir, 'T_Tentacle_MetallicSmoothness.png'))).astype(float) / 255
    L = np.array([0.55, 0.45, 0.70]); L /= np.linalg.norm(L)
    Vd = np.array([0, 0, 1.0])
    Hh = (L + Vd) / np.linalg.norm(L + Vd)
    nd = np.clip(nrm @ L, 0, 1)
    sm = ms[..., 3]
    spec = np.clip(nrm @ Hh, 0, 1) ** (2 + 400 * sm ** 4)
    lit = 0.25 * nd + 0.8 * spec
    a = np.clip(srgb2lin(alb) * 22, 0, 1)
    tiles = [np.tile(x, (2, 2, 1))[::4, ::4] if x.ndim == 3 else np.tile(x, (2, 2))[::4, ::4] for x in
             (lin2srgb(a), lit, sm)]
    tiles[1] = np.repeat(lin2srgb(np.clip(tiles[1], 0, 1))[..., None], 3, -1)
    tiles[2] = np.repeat(tiles[2][..., None], 3, -1)
    crop = np.repeat(lin2srgb(np.clip(lit[:1024, :1024], 0, 1))[..., None], 3, -1)
    row = np.concatenate(tiles + [crop], 1)
    Image.fromarray((row * 255).astype(np.uint8)).save(path)
    print('sheet', path)


# =============================================================================================
# 2. SHAPES  (pure numpy)
# =============================================================================================
# The centreline is integrated from its CURVATURE along the arc length in a rotation-minimising
# frame (a, b) that starts as a = +X, b = -Y (Blender). A bend event turns the tangent by `deg`
# degrees around arc position u (Gaussian of width w) toward direction psi in that frame:
#     psi = 0 -> +X (right), 90 -> -Y (forward = toward the tear; Unity +Z), 180 -> -X, -90 -> +Y.
# Tip behaviours are clothoid ramps (curvature grows like a power of the arc length) plus a release
# and an optional counter-flick (出锋), so curls are never tidy circles.

# base radius profile of the family: muscular swell above the root, a heavy body that keeps its mass
# to ~45 % of the length, then a LATE concave taper into the thread (fix: the old near-linear cone read
# as horn / thorn / grass blade)
RAD_K = [(0.00, 1.00), (0.05, 1.06), (0.15, 1.00), (0.30, 0.90), (0.45, 0.76), (0.57, 0.57),
         (0.65, 0.38), (0.71, 0.23), (0.76, 0.135), (0.81, 0.080), (0.86, 0.052), (0.91, 0.036), (0.95, 0.026),
         (0.98, 0.015), (1.00, 0.004)]
# v2: from 87 % on the arm is a THREAD of nearly constant thinness (2-5 % of the root): a whip lash that
# cannot read as a claw, a horn's point or a grass blade (a long cone does)


def _pchip(keys):
    from scipy.interpolate import PchipInterpolator
    k = np.array(keys, float)
    return PchipInterpolator(k[:, 0], k[:, 1])


_RAD = None


def swellings(wob_seed):
    """2-3 soft muscular swellings (+6..8 %) and one faint constriction per variant: (u, width, amp)."""
    g = np.random.default_rng(int(wob_seed * 1e6) + 11)
    n = 2 + int(g.random() < 0.6)
    us = np.sort(0.16 + 0.54 * (np.arange(n) + g.uniform(0.15, 0.85, n)) / n)
    out = [(float(u), float(g.uniform(0.045, 0.06)), float(g.uniform(0.06, 0.08))) for u in us]
    out.append((float(g.uniform(0.2, 0.62)), 0.035, -0.045))
    return out


def radius_profile(u, heavy=1.0, wob_seed=0.0):
    """r / R_root at normalised arc length u. heavy > 1 keeps the body thick for longer."""
    global _RAD
    if _RAD is None:
        _RAD = _pchip(RAD_K)
    u = np.asarray(u, float)
    uu = np.clip(u, 0, 1) ** heavy
    r = _RAD(uu)
    env = np.clip(u / 0.08, 0, 1) * np.clip((0.86 - u) / 0.16, 0, 1)
    wob = 0.012 * np.sin(2 * np.pi * (7.3 * u + 0.17 + wob_seed))
    for (uc, w, a) in swellings(wob_seed):
        wob = wob + a * np.exp(-((u - uc) / w) ** 2)
    return r * (1.0 + env * wob)


def _rot(v, axis, ang):
    c, s = np.cos(ang), np.sin(ang)
    return v * c + np.cross(axis, v) * s + axis * np.dot(axis, v) * (1 - c)


def curvature_field(u, spec, L):
    """k1 (toward a), k2 (toward b) in rad/m at normalised arc positions u."""
    k1 = np.zeros_like(u)
    k2 = np.zeros_like(u)
    ds = L * (u[1] - u[0])
    for (uc, w, deg, psi) in spec.get('bends', []):
        g = np.exp(-((u - uc) / w) ** 2)
        k = math.radians(deg) * g / (g.sum() * ds)
        k1 += k * math.cos(math.radians(psi))
        k2 += k * math.sin(math.radians(psi))
    for tip in spec.get('tips', []):
        u0, u1 = tip['u0'], tip.get('u1', 0.985)
        x = np.clip((u - u0) / (u1 - u0), 0, 1)
        ramp = np.where(u >= u0, x ** tip.get('p', 1.4), 0.0)
        release = 1.0 - _smoothstep(u1, min(u1 + tip.get('rel', 0.012), 1.0), u)
        shape = ramp * release
        k = math.radians(tip['deg']) * shape / (shape.sum() * ds)
        # the bend direction rotates along the ramp: an out-of-plane (helical) curl
        psi = np.radians(tip['psi'] + tip.get('twist', 0.0) * x)
        k1 += k * np.cos(psi)
        k2 += k * np.sin(psi)
        if tip.get('flick'):
            fu, fdeg, fpsi = tip['flick']
            g = np.exp(-((u - fu) / 0.008) ** 2)
            kf = math.radians(fdeg) * g / (g.sum() * ds)
            k1 += kf * math.cos(math.radians(fpsi))
            k2 += kf * math.sin(math.radians(fpsi))
    return k1, k2


def integrate(L, spec, n=6001, T0=(0, 0, 1), a0=(1, 0, 0), P0=(0, 0, 0), u_range=(0.0, 1.0)):
    """Centreline + rotation-minimising frame. Returns dict u, s, P, T, A, B (n x 3)."""
    u = np.linspace(u_range[0], u_range[1], n)
    k1, k2 = curvature_field(np.linspace(0, 1, n), spec, L * (u_range[1] - u_range[0])) if spec.get('local') \
        else curvature_field(u, spec, L)
    ds = L * (u[1] - u[0])
    P = np.zeros((n, 3)); T = np.zeros((n, 3)); A = np.zeros((n, 3)); B = np.zeros((n, 3))
    t = np.array(T0, float); t /= np.linalg.norm(t)
    a = np.array(a0, float); a -= a.dot(t) * t; a /= np.linalg.norm(a)
    b = np.cross(t, a)                    # a = +X, t = +Z -> b = Z x X = +Y ... we want -Y:
    b = -b                                # frame (a, b) = (+X, -Y) at the root
    p = np.array(P0, float)
    for i in range(n):
        P[i], T[i], A[i], B[i] = p, t, a, b
        kv = k1[i] * a + k2[i] * b
        kk = np.linalg.norm(kv)
        if kk > 1e-12:
            ax = np.cross(t, kv / kk)
            ax /= np.linalg.norm(ax)
            ang = kk * ds
            t2, a2, b2 = _rot(t, ax, ang), _rot(a, ax, ang), _rot(b, ax, ang)
        else:
            t2, a2, b2 = t, a, b
        p = p + 0.5 * (t + t2) * ds
        t = t2 / np.linalg.norm(t2)
        a = a2 - a2.dot(t) * t; a /= np.linalg.norm(a)
        b = b2 - b2.dot(t) * t - b2.dot(a) * a; b /= np.linalg.norm(b)
    return dict(u=u, s=(u - u[0]) * L, P=P, T=T, A=A, B=B, k=np.hypot(k1, k2), L=L)


def rmf_along(P, B0):
    """Arc length, unit tangent, rotation-minimising normal (double reflection) and curvature of a
    polyline P, starting from normal B0."""
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    T = np.gradient(P, s, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    B = np.zeros_like(P)
    b = B0 - B0.dot(T[0]) * T[0]
    B[0] = b / np.linalg.norm(b)
    for j in range(len(P) - 1):
        v1 = P[j + 1] - P[j]
        c1 = v1.dot(v1)
        rL = B[j] - (2 / c1) * v1.dot(B[j]) * v1
        tL = T[j] - (2 / c1) * v1.dot(T[j]) * v1
        v2 = T[j + 1] - tL
        c2 = v2.dot(v2)
        rr = rL - (2 / c2) * v2.dot(rL) * v2 if c2 > 1e-14 else rL
        B[j + 1] = rr / np.linalg.norm(rr)
    k = np.linalg.norm(np.gradient(T, s, axis=0), axis=1)
    return s, T, B, k


def apply_helix(cl, hx):
    """CORKSCREW body: displace the integrated centreline around itself in its own frame,
    `turns` turns of radius a (fraction of L) between u0 and u1, eased in and out, then rebuild the
    frame. u is re-normalised to the new arc length (so Col.R = t stays arc length)."""
    u, P, A, Bv = cl['u'], cl['P'], cl['A'], cl['B']
    u0, u1, ease = hx['u0'], hx['u1'], hx.get('ease', 0.08)
    w = _smoothstep(u0, u0 + ease, u) * (1 - _smoothstep(u1 - ease, u1, u))
    x = np.clip((u - u0) / (u1 - u0), 0, 1)
    ph = hx.get('phase', 0.0) + 2 * np.pi * hx['turns'] * x * hx.get('hand', 1)
    a = hx['a'] * cl['L'] * w * (1.0 - hx.get('grow', 0.0) * (1.0 - x))     # grow: the coil opens toward the tip
    Q = P + a[:, None] * (np.cos(ph)[:, None] * A + np.sin(ph)[:, None] * Bv)
    Q -= Q[0] - P[0]
    s, T, B, k = rmf_along(Q, Bv[0])
    A2 = np.cross(T, B)
    return dict(u=s / s[-1], s=s, P=Q, T=T, A=A2, B=B, k=k, L=float(s[-1]))


_CLINE = {}


def centreline(key):
    """The final centreline of variant `key` (curvature integration + optional corkscrew)."""
    if key not in _CLINE:
        sp = VARIANTS[key]
        cl = integrate(sp['L'], sp)
        if sp.get('helix'):
            cl = apply_helix(cl, sp['helix'])
        _CLINE[key] = cl
    return _CLINE[key]


def seam_frames(T, Bv, s, sigma_m):
    """Section frame (n1 = U 0 direction, n2 = T x n1). n1 is the RMF vector b twisted by a smoothed
    angle so that it sits on local -Y projected onto the section plane (the SPEC seam), without the
    flips the plain projection has where the tangent passes near +-Y (graft from ink)."""
    ref = np.array([0.0, -1.0, 0.0])
    p = ref[None] - (T @ ref)[:, None] * T
    w = np.linalg.norm(p, axis=1)
    pn = p / np.maximum(w, 1e-9)[:, None]
    phi = np.arctan2(np.einsum('ij,ij->i', np.cross(Bv, pn), T), np.einsum('ij,ij->i', Bv, pn))
    phi = np.unwrap(phi)
    wt = np.clip((w - 0.15) / 0.5, 0, 1) ** 2 + 1e-6
    ds = s[1] - s[0]
    k = max(int(sigma_m / ds * 3), 1)
    x = np.arange(-k, k + 1) * ds
    ker = np.exp(-0.5 * (x / sigma_m) ** 2)
    num = np.convolve(np.pad(phi * wt, k, mode='edge'), ker, 'valid')
    den = np.convolve(np.pad(wt, k, mode='edge'), ker, 'valid')
    phs = num / den
    n1 = np.array([_rot(Bv[i], T[i], phs[i]) for i in range(len(T))])
    n1 -= np.einsum('ij,ij->i', n1, T)[:, None] * T
    n1 /= np.linalg.norm(n1, axis=1, keepdims=True)
    n2 = np.cross(T, n1)
    drift = np.degrees(np.arctan2(np.einsum('ij,ij->i', np.cross(n1, pn), T), np.einsum('ij,ij->i', n1, pn)))
    drift = np.where(w > 0.35, drift, 0.0)
    return n1, n2, float(np.abs(drift).max())


def ring_positions(u, r, k, n_rings, u_last=0.996, seg_deg=7.0, r_min=0.0):
    """Adaptive ring layout: density ~ 1/r (square quads) + a curvature term (round curls)."""
    rr = np.maximum(r, r_min)
    dens = 1.0 / (0.30 * rr) + k / math.radians(seg_deg)
    m = max(len(u) // 150, 3)
    dens = np.convolve(np.pad(dens, m, mode='edge'), np.ones(2 * m + 1) / (2 * m + 1), 'valid')
    cum = np.concatenate([[0], np.cumsum(0.5 * (dens[1:] + dens[:-1]) * np.diff(u))])
    sel = u <= u_last
    cum_l = cum[sel] / cum[sel][-1]
    return np.interp(np.linspace(0, 1, n_rings), cum_l, u[sel])


def _interp_rows(x, xs, Y):
    return np.stack([np.interp(x, xs, Y[:, i]) for i in range(Y.shape[1])], -1)


def make_tube(cl, rfun, n_seg, n_rings, R_root, t_map, lumps=True, oval=(1.03, 0.95), v_offset=0.0,
              lump_seed=0.0, rmin_frac=0.03, vmin_frac=0.035, sigma_frac=0.003, u_last=0.996, tip_len=0.6):
    """One closed tube around the centreline dict `cl` (from integrate or a strand path).
    rfun(u) -> radius (m) along the tube; t_map(u) -> Col.R. Returns arrays for the mesh builder."""
    u, P, T = cl['u'], cl['P'], cl['T']
    Bv = cl['B']
    s = cl['s']
    r_d = rfun(u)
    ur = ring_positions(u, r_d, cl['k'], n_rings, u_last=u_last, r_min=rmin_frac * R_root)
    n1_d, n2_d, drift = seam_frames(T, Bv, s, max(sigma_frac * s[-1], 0.05))
    C = _interp_rows(ur, u, P)
    Tr = _interp_rows(ur, u, T)
    Tr /= np.linalg.norm(Tr, axis=1, keepdims=True)
    n1 = _interp_rows(ur, u, n1_d)
    n1 -= np.einsum('ij,ij->i', n1, Tr)[:, None] * Tr
    n1 /= np.linalg.norm(n1, axis=1, keepdims=True)
    n2 = np.cross(Tr, n1)
    r = rfun(ur)
    th = 2 * np.pi * np.arange(n_seg) / n_seg
    rad = np.ones((len(ur), n_seg)) * r[:, None]
    if lumps:     # slow irregular muscle bulges: a body, not a lathe (fade out on the whip)
        fade = (1 - _smoothstep(0.66, 0.84, ur))[:, None]
        lump = (0.050 * np.cos(2 * th[None] + 2.1 * np.sin(9.0 * ur[:, None] + lump_seed) + 0.5 + lump_seed)
                + 0.034 * np.cos(3 * th[None] - 5.0 * ur[:, None] + 1.3 + 2 * lump_seed)
                + 0.020 * np.cos(5 * th[None] + 13.0 * ur[:, None] + 3 * lump_seed)
                + 0.012 * np.cos(7 * th[None] + 29.0 * ur[:, None] + 5 * lump_seed))
        rad = rad * (1 + lump * fade)
    cx = oval[0] * np.cos(th)
    cy = oval[1] * np.sin(th)
    verts = C[:, None, :] + rad[..., None] * (cx[None, :, None] * n1[:, None, :] + cy[None, :, None] * n2[:, None, :])
    # conformal V: dV = ds / (2 pi r), r clamped so the thread-thin whip does not eat the texture
    rv = np.maximum(r_d, vmin_frac * R_root)
    dv = np.gradient(s) / (2 * np.pi * rv)
    Vd = np.concatenate([[0], np.cumsum(0.5 * (dv[1:] + dv[:-1]))])
    V = np.interp(ur, u, Vd) + v_offset
    tip = C[-1] + Tr[-1] * r[-1] * tip_len
    tip_v = V[-1] + r[-1] * tip_len / (2 * np.pi * vmin_frac * R_root)
    return dict(verts=verts, V=V, colR=t_map(ur), colB=r / R_root, tip=tip, tip_v=tip_v, tipR=t_map(1.0),
                C=C, T=Tr, n1=n1, n2=n2, r=r, ur=ur, drift=drift, cap=True)


# ---------------------------------------------------------------------------------------------
# the eight variants.  L = arc length (m), R = root radius (m), heavy = body stays thick longer.
# bends: (u centre, width, degrees, psi).  tips: clothoid ramps.  LODs: (segments, rings) per tube.
# ---------------------------------------------------------------------------------------------
VARIANTS = {
    # A: WHIP. A slim arm with a gentle double S that throws its last quarter out as a straight,
    #    thread-thin whip with a tiny counter-flick at the very end. No curl. (near layer; the far tide)
    'A': dict(L=25.0, R=0.70, heavy=1.0, phase=0.137, vofs=0.13,
              bends=[(0.10, 0.10, 22, 235), (0.40, 0.16, 52, 70), (0.66, 0.12, 44, 250)],
              tips=[dict(u0=0.82, u1=0.975, deg=26, psi=98, p=1.2, flick=(0.984, -40, 98))],
              lods=[[(32, 93)], [(20, 50)], [(12, 25)]]),
    # B: DROOP. Rises leaning out to one side, arches over forward and lets its end hang below the
    #    horizontal under its own weight; the very end closes into a short raptor hook.
    'B': dict(L=32.0, R=0.95, heavy=1.0, phase=0.853, vofs=0.57, seam_sigma=0.02,
              bends=[(0.10, 0.10, 26, 15), (0.33, 0.14, 52, 105), (0.56, 0.14, 74, 80)],
              tips=[dict(u0=0.85, u1=0.975, deg=80, psi=115, twist=-45, p=1.8)],
              lods=[[(32, 93)], [(20, 50)], [(12, 25)]]),
    # C: CORKSCREW. The body winds 1.5 turns round its own axis, the coil opening as it rises (a wrung
    #    muscle, not a spring), then runs out into a whip that half-curls sideways.
    'C': dict(L=50.0, R=1.35, heavy=1.0, phase=0.421, vofs=0.31,
              bends=[(0.08, 0.06, 14, 200), (0.40, 0.20, 34, 70)],
              helix=dict(u0=0.16, u1=0.86, turns=1.5, a=0.095, ease=0.12, grow=0.6),
              tips=[dict(u0=0.86, u1=0.985, deg=150, psi=200, twist=70, p=1.3)],
              lods=[[(32, 93)], [(20, 50)], [(12, 25)]]),
    # D: BROAD C + OPEN COIL. The body sweeps sideways in one broad C; its end rolls into a big, open,
    #    out-of-plane coil (diameter > 0.2 L) and releases the whip outward. The only real coil.
    'D': dict(L=72.0, R=2.00, heavy=1.0, phase=0.694, vofs=0.77,
              bends=[(0.08, 0.08, 18, 200), (0.32, 0.20, 52, 25), (0.50, 0.12, 24, 110)],
              tips=[dict(u0=0.44, u1=0.965, deg=265, psi=75, twist=-100, p=0.55, rel=0.02,
                         flick=(0.975, -60, 70))],
              lods=[[(32, 93)], [(20, 50)], [(12, 25)]]),
    # E: DOUBLE-S + FORKED TIP. The body doubles back on itself twice; near its end it splits into two
    #    thread whips that part like a forked tongue, each curling its own way.
    'E': dict(L=100.0, R=2.75, heavy=1.0, phase=0.288, vofs=0.05,
              bends=[(0.09, 0.09, 28, 40), (0.28, 0.11, 62, 215), (0.48, 0.11, 60, 50), (0.67, 0.10, 36, 175)],
              tips=[dict(u0=0.86, u1=0.98, deg=55, psi=60, twist=30, p=1.5)],
              branches=[dict(u=0.79, side=150, out=24, len=0.21, r0=0.85, heavy=1.0,
                             bends=[(0.35, 0.20, 14, -30)],
                             tips=[dict(u0=0.55, u1=0.97, deg=70, psi=200, twist=-40, p=1.4)])],
              lods=[[(28, 90), (12, 39)], [(18, 46), (8, 18)], [(12, 20), (6, 6)]]),
    # F: WAVE CREST. A long body leaning into the wind crests over like a breaking wave and pours into a
    #    long thread whip with a small counter-flick (the reaching giant; the flyby arm).
    'F': dict(L=140.0, R=3.9, heavy=1.05, phase=0.566, vofs=0.44,
              bends=[(0.07, 0.08, 14, 262), (0.25, 0.18, 42, 80), (0.46, 0.12, 16, 245), (0.66, 0.14, 92, 96)],
              tips=[dict(u0=0.76, u1=0.86, deg=34, psi=120, p=1.2, rel=0.03),
                    dict(u0=0.86, u1=0.93, deg=-46, psi=115, p=1.1, rel=0.02),
                    dict(u0=0.93, u1=0.985, deg=40, psi=130, twist=30, p=1.3, flick=(0.988, -30, 110))],
              lods=[[(32, 93)], [(20, 50)], [(12, 25)]]),
    # G: COLOSSUS · SWAN NECK + BRAID. Leaves the cloud leaning back, rises in a long S and throws its
    #    upper third forward over the wound like a swan's neck; the end hangs with a slight sideways hook.
    #    A strand spirals up the lower body, lifts off once (light through the gap) and sinks back in.
    'G': dict(L=300.0, R=10.0, heavy=1.1, phase=0.019, vofs=0.66,
              bends=[(0.05, 0.06, 26, 262), (0.28, 0.16, 44, 82), (0.52, 0.13, 50, 278), (0.75, 0.12, 112, 92)],
              tips=[dict(u0=0.88, u1=0.98, deg=55, psi=35, twist=-40, p=1.5)],
              strands=[dict(w0=0.6, turns=1.35, u_end=0.55, r0=0.34,
                            lift=[(0.0, 0.80), (0.05, 0.66), (0.14, 0.58), (0.24, 0.62), (0.30, 1.70),
                                  (0.37, 1.70), (0.44, 0.60), (0.55, 0.15)])],
              lods=[[(24, 96), (14, 49)], [(16, 50), (10, 20)], [(10, 24), (6, 10)]]),
    # H: COLOSSUS · THE REACH. A leaning pillar that twists a quarter turn as it rises and bends its upper
    #    half over toward the wound, horizontal, like an arm reaching to close it; the end frays into four
    #    thin, wavering threads (a torn rope, not twigs).
    'H': dict(L=430.0, R=12.5, heavy=1.1, phase=0.745, vofs=0.92,
              bends=[(0.05, 0.06, 14, 290), (0.40, 0.25, 26, 95), (0.74, 0.16, 58, 85)],
              helix=dict(u0=0.10, u1=0.82, turns=0.85, a=0.065, ease=0.15, grow=0.5, hand=-1),
              tips=[dict(u0=0.86, u1=0.975, deg=40, psi=70, twist=30, p=1.4)],
              frays=[dict(u=0.905, side=s, out=o, len=ln, r0=0.62, heavy=1.0, bends=[(0.4, 0.3, b, s + 90)],
                          tips=[dict(u0=0.45, u1=0.97, deg=d, psi=ps, twist=tw, p=1.3)])
                     for (s, o, ln, b, d, ps, tw) in ((20, 16, 0.085, 18, 70, 100, 40), (140, 22, 0.07, 22, 110, 210, -60),
                                                      (250, 14, 0.095, 12, 45, 300, 20), (320, 26, 0.06, 26, 150, 20, 90))],
              lods=[[(20, 118), (6, 26), (6, 26), (6, 26), (6, 26)], [(14, 50), (4, 12), (4, 12), (4, 12), (4, 12)],
                    [(10, 23), (3, 5), (3, 5), (3, 5), (3, 5)]]),
}
ORDER = 'ABCDEFGH'


def variant_parts(key, lod=0):
    """All tubes of one variant at one LOD (list of make_tube dicts)."""
    sp = VARIANTS[key]
    L, R = sp['L'], sp['R']
    heavy = sp.get('heavy', 1.0)
    wseed = (sp['phase'] * 7.3) % 1.0
    segs = sp['lods'][lod]
    cl = centreline(key)
    rfun = lambda uu: R * radius_profile(uu, heavy, wseed)
    parts = [make_tube(cl, rfun, segs[0][0], segs[0][1], R, lambda uu: np.asarray(uu, float),
                       v_offset=sp.get('vofs', 0.0), lump_seed=wseed * 6.0, sigma_frac=sp.get('seam_sigma', 0.003))]
    parts[0]['name'] = 'core'
    k = 1
    for br in sp.get('branches', []) + sp.get('frays', []):     # frays: thin threads splitting off the end
        parts.append(_branch(cl, br, sp, rfun, segs[k][0], segs[k][1], R, k))
        k += 1
    for st in sp.get('strands', []):
        parts.append(_strand(cl, st, sp, rfun, segs[k][0], segs[k][1], R))
        k += 1
    # centre V on 0 by a whole number of tiles (invisible: the main maps repeat every 1 in V). Keeps
    # |V| <= ~17 so a half-precision UV0 (Unity Vertex Compression on TexCoord0) errs half as much.
    vs = np.concatenate([np.r_[p['V'], p['tip_v']] for p in parts])
    shift = float(np.round(0.5 * (vs.min() + vs.max())))
    for p in parts:
        p['V'] = p['V'] - shift
        p['tip_v'] = p['tip_v'] - shift
    return parts, cl


def _branch(cl, br, sp, rfun, n_seg, n_rings, R, k):
    """An arm that grows out of the body at u = br['u'] (its root is embedded in the body)."""
    i = int(np.clip(np.searchsorted(cl['u'], br['u']), 0, len(cl['u']) - 1))
    T, A, Bv, P = cl['T'][i], cl['A'][i], cl['B'][i], cl['P'][i]
    side = math.radians(br['side'])
    d = math.cos(side) * A + math.sin(side) * Bv
    rb = float(rfun(br['u']))
    r0 = br['r0'] * rb
    T0 = _rot(T, np.cross(T, d) / np.linalg.norm(np.cross(T, d)), math.radians(br['out']))
    P0 = P + d * (rb - 0.75 * r0) - T * 0.4 * rb
    Lb = br['len'] * sp['L']
    clb = integrate(Lb, br, T0=T0, a0=A, P0=P0)
    rf = lambda uu: r0 * radius_profile(uu, br.get('heavy', 1.0)) / radius_profile(0.0, br.get('heavy', 1.0))
    ub = br['u']
    tube = make_tube(clb, rf, n_seg, n_rings, R, lambda uu: ub + (1.0 - ub) * np.asarray(uu, float),
                     lumps=False, v_offset=0.37 * k, rmin_frac=0.012, vmin_frac=0.02)
    tube['name'] = 'branch%d' % k
    return tube


def _strand(cl, st, sp, rfun, n_seg, n_rings, R):
    """A root strand spiralling up the core (graft from root): splays at the base, hugs the core in a
    crease, lifts off once (light through the gap) and sinks back into the core."""
    u = cl['u']
    ue = st['u_end']
    n = 3001
    us = np.linspace(0, ue, n)
    C = _interp_rows(us, u, cl['P'])
    A = _interp_rows(us, u, cl['A'])
    Bv = _interp_rows(us, u, cl['B'])
    rc = rfun(us)
    lk = np.array(st['lift'], float)
    e = np.interp(us, lk[:, 0], lk[:, 1])
    from scipy.interpolate import PchipInterpolator
    e = PchipInterpolator(lk[:, 0], lk[:, 1])(us)
    xr = us / ue
    rs = st['r0'] * R * np.clip(1.0 - 0.55 * xr - 0.45 * _smoothstep(0.75, 1.0, xr), 0.02, 1)
    d = rc + e * rs
    # twist: constant turns, eased at both ends so the strand leaves and rejoins smoothly
    w = st['w0'] + 2 * np.pi * st['turns'] * (xr - 0.12 * np.sin(2 * np.pi * xr) / (2 * np.pi))
    Q = C + d[:, None] * (np.cos(w)[:, None] * A + np.sin(w)[:, None] * Bv)
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    Tq = np.gradient(Q, s, axis=0)
    Tq /= np.linalg.norm(Tq, axis=1, keepdims=True)
    # an RMF along the strand for the seam frame
    Bq = np.zeros_like(Q)
    b = Bv[0] - Bv[0].dot(Tq[0]) * Tq[0]
    Bq[0] = b / np.linalg.norm(b)
    for j in range(n - 1):
        v1 = Q[j + 1] - Q[j]
        c1 = v1.dot(v1)
        rL = Bq[j] - (2 / c1) * v1.dot(Bq[j]) * v1
        tL = Tq[j] - (2 / c1) * v1.dot(Tq[j]) * v1
        v2 = Tq[j + 1] - tL
        c2 = v2.dot(v2)
        rr = rL - (2 / c2) * v2.dot(rL) * v2 if c2 > 1e-14 else rL
        Bq[j + 1] = rr / np.linalg.norm(rr)
    kq = np.linalg.norm(np.gradient(Tq, s, axis=0), axis=1)
    ua = s / s[-1]
    scl = dict(u=ua, s=s, P=Q, T=Tq, B=Bq, k=kq)
    rf = lambda uu: np.interp(uu, ua, rs)
    tube = make_tube(scl, rf, n_seg, n_rings, R, lambda uu: np.interp(uu, ua, us),
                     lumps=False, v_offset=0.71, rmin_frac=0.02, vmin_frac=0.02, u_last=0.995, tip_len=1.5)
    tube['name'] = 'strand'
    return tube


def plot_variants(path, keys=ORDER, px_per_m=None):
    """Orthographic silhouettes of every variant: front (X-Z, as seen from -Y) and side (Y-Z,
    -Y = forward = toward the tear on the right). Circles along each tube, for eyes only."""
    from PIL import ImageDraw
    rows = []
    for key in keys:
        parts, cl = variant_parts(key, 0)
        allv = np.concatenate([p['verts'].reshape(-1, 3) for p in parts])
        rows.append((key, parts, allv))
    H = 700
    ims = []
    for key, parts, allv in rows:
        lo, hi = allv.min(0), allv.max(0)
        span = max(hi[2] - lo[2], hi[0] - lo[0], hi[1] - lo[1])
        sc = (H - 60) / span
        W = int((hi[0] - lo[0] + hi[1] - lo[1]) * sc + 90)
        im = Image.new('RGB', (W, H), (228, 226, 220))
        dr = ImageDraw.Draw(im)
        for view, ox in ((0, 20 - lo[0] * sc), (1, 60 + (hi[0] - lo[0]) * sc + hi[1] * sc)):
            for p in parts:
                for j in range(len(p['C'])):
                    c = p['C'][j]
                    x = ox + (c[0] * sc if view == 0 else -c[1] * sc)
                    y = H - 30 - (c[2] - lo[2]) * sc
                    rr = max(p['r'][j] * sc, 0.6)
                    dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(14, 14, 18))
                # fill between rings for a solid silhouette
                for j in range(len(p['C']) - 1):
                    for a in np.linspace(0, 1, 6)[1:-1]:
                        c = p['C'][j] * (1 - a) + p['C'][j + 1] * a
                        rr = max((p['r'][j] * (1 - a) + p['r'][j + 1] * a) * sc, 0.6)
                        x = ox + (c[0] * sc if view == 0 else -c[1] * sc)
                        y = H - 30 - (c[2] - lo[2]) * sc
                        dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(14, 14, 18))
        dr.text((8, 6), '%s  L=%gm R=%gm  front | side(-Y right)' % (key, VARIANTS[key]['L'], VARIANTS[key]['R']),
                fill=(0, 0, 0))
        ims.append(im)
    rows_ = [ims[:4], ims[4:]]
    Wt = max(sum(i.width for i in r) for r in rows_)
    sheet = Image.new('RGB', (Wt, H * len(rows_)), (255, 255, 255))
    for ri, r in enumerate(rows_):
        x = 0
        for i in r:
            sheet.paste(i, (x, ri * H)); x += i.width
    sheet.save(path)
    print('plot', path, sheet.size)


def silhouette_sheet(path, keys=ORDER, mask_u=0.85, views=(0.0, 90.0, 45.0), H=330):
    """ACCEPTANCE TEST for the shape language: every variant as a flat black silhouette with its tips
    (t > mask_u) cut off, in three views (azimuth deg about Z: 0 = seen from -Y). If two variants look
    alike here, the family is not varied enough. Scaled to equal height (shape, not size)."""
    from PIL import ImageDraw
    cols = []
    for key in keys:
        parts, _ = variant_parts(key, 1)
        cells = []
        for az in views:
            a = math.radians(az)
            R2 = np.array([[math.cos(a), math.sin(a), 0], [0, 0, 1]])        # screen x, y
            segs = []
            for p in parts:
                keep = p['colR'] <= mask_u
                C2 = p['C'] @ R2.T
                segs.append((C2[keep], p['r'][keep]))
            allp = np.concatenate([s[0] for s in segs if len(s[0])])
            lo, hi = allp.min(0), allp.max(0)
            sc = (H - 30) / max(hi[1] - lo[1], (hi[0] - lo[0]) * 0.8, 1e-6)
            Wc = int((hi[0] - lo[0]) * sc + 30)
            im = Image.new('L', (max(Wc, 60), H), 255)
            dr = ImageDraw.Draw(im)
            for C2, rr in segs:
                for j in range(len(C2)):
                    for f in (np.linspace(0, 1, 5)[:-1] if j < len(C2) - 1 else [0.0]):
                        c = C2[j] * (1 - f) + (C2[j + 1] * f if j < len(C2) - 1 else 0)
                        r = (rr[j] * (1 - f) + (rr[j + 1] * f if j < len(C2) - 1 else 0)) * sc
                        x, y = 15 + (c[0] - lo[0]) * sc, H - 15 - (c[1] - lo[1]) * sc
                        dr.ellipse([x - r, y - r, x + r, y + r], fill=0)
            cells.append(im)
        cols.append((key, cells))
    Wt = sum(max(c.width for c in cells) + 10 for _, cells in cols)
    sheet = Image.new('RGB', (Wt, H * len(views) + 20), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    x = 0
    for key, cells in cols:
        w = max(c.width for c in cells)
        dr.text((x + 4, 2), key, fill=(200, 0, 0))
        for i, c in enumerate(cells):
            sheet.paste(c.convert('RGB'), (x + (w - c.width) // 2, 20 + i * H))
        x += w + 10
    sheet.save(path)
    print('silhouettes', path, sheet.size)


def coil_diameter(key, u0):
    """Largest extent of the curled end (u > u0) of the core, as a fraction of the length."""
    cl = centreline(key)
    Q = cl['P'][cl['u'] >= u0][::5]
    d = np.sqrt(((Q[:, None, :] - Q[None, :, :]) ** 2).sum(-1)).max()
    return float(d / VARIANTS[key]['L'])


# =============================================================================================
# 3. MESHES (bpy)
# =============================================================================================
def build_mesh(name, parts, phase):
    """One mesh from the tubes: quads, a closed fan tip, a hard-split flat root cap per tube."""
    allv, faces, uvs, smooth, cols = [], [], [], [], []
    base = 0
    for p in parts:
        R_, S = p['verts'].shape[:2]
        V = p['V']
        allv.append(p['verts'].reshape(-1, 3))
        tip_i = base + R_ * S
        cap0 = tip_i + 1
        cap_c = cap0 + S
        allv.append(p['tip'][None])
        allv.append(p['verts'][0])
        allv.append(p['C'][:1])
        for i in range(R_ - 1):
            for j in range(S):
                j1 = (j + 1) % S
                faces.append((base + i * S + j, base + i * S + j1, base + (i + 1) * S + j1, base + (i + 1) * S + j))
                u0, u1 = j / S, (j + 1) / S
                uvs.append(((u0, V[i]), (u1, V[i]), (u1, V[i + 1]), (u0, V[i + 1])))
                smooth.append(True)
        last = base + (R_ - 1) * S
        for j in range(S):
            j1 = (j + 1) % S
            faces.append((last + j, last + j1, tip_i))
            uvs.append(((j / S, V[-1]), ((j + 1) / S, V[-1]), ((j + 0.5) / S, p['tip_v'])))
            smooth.append(True)
        th = 2 * np.pi * np.arange(S) / S
        for j in range(S):
            j1 = (j + 1) % S
            faces.append((cap_c, cap0 + j1, cap0 + j))
            a0, a1 = th[j], (th[j1] if j1 else 2 * np.pi)
            uvs.append(((0.5, 0.5), (0.5 - 0.1 * math.cos(a1), 0.5 + 0.1 * math.sin(a1)),     # U mirrored:
                        (0.5 - 0.1 * math.cos(a0), 0.5 + 0.1 * math.sin(a0))))    # same handedness as the body
            smooth.append(False)
        t_v = np.concatenate([np.repeat(p['colR'], S), [p['tipR']], np.full(S, p['colR'][0]), [p['colR'][0]]])
        b_v = np.concatenate([np.repeat(p['colB'], S), [0.0], np.full(S, p['colB'][0]), [p['colB'][0]]])
        cols.append(np.stack([t_v, np.full_like(t_v, phase), b_v, np.ones_like(t_v)], -1))
        base = cap_c + 1
    allv = np.concatenate(allv)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in allv], [], faces)
    me.update()
    uvl = me.uv_layers.new(name='UVMap')
    flat = [uv for fuv in uvs for uv in fuv]
    uvl.data.foreach_set('uv', np.array(flat, np.float32).ravel())
    # UV1 'UVSway' = (t, phase) at FULL float precision: Unity stores FBX vertex colours as UNorm8
    # (256 levels: the thread-thin tips would sway as a staircase), but TexCoord1 as float32.
    colv = np.concatenate(cols).astype(np.float32)
    lvi = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lvi)
    uv2 = me.uv_layers.new(name='UVSway')
    uv2.data.foreach_set('uv', np.stack([colv[lvi, 0], colv[lvi, 1]], -1).ravel())
    me.uv_layers.active = uvl
    uvl.active_render = True
    me.polygons.foreach_set('use_smooth', smooth)
    col = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    col.data.foreach_set('color', colv.ravel())
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_report(ob):
    me = ob.data
    me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices])
    tris = np.array([t.vertices[:] for t in me.loop_triangles])
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    vol = np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6.0
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    return dict(tris=len(tris), min_area=float(area.min()), volume=float(vol), boundary_edges=boundary,
                bbox=[np.round(co.min(0), 1).tolist(), np.round(co.max(0), 1).tolist()])


def variant_object(key, lod=0, name=None):
    parts, _ = variant_parts(key, lod)
    return build_mesh(name or 'Tentacle_%s_LOD%d' % (key, lod), parts, VARIANTS[key]['phase'])


# =============================================================================================
# 4. PREVIEW MATERIAL  (reads only the delivered PNGs; every extra mirrors a line of the Unity shader)
# =============================================================================================
def _hex_lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


TIP_TINT = (0.86, 0.80, 1.10)        # albedo x this toward the tip (indigo drift)   = _TipTint
TIP_TINT_FROM, TIP_TINT_TO = 0.22, 0.02
TRANSLUCENT = _hex_lin('#5B57A1')    # ART BIBLE v2: thin-tip transmission = (1 - B)^2 x tear light x #5B57A1
TRANS_GAIN = 2.2                     # = _TipGlow
RIM = dict(moon_color=_hex_lin('#9DB8FF'), moon=0.80, tear_color=_hex_lin('#A99DE1'), tear=0.08,
           tear_near=200.0, tear_far=1200.0)                              # = _RimMoon*, _RimTear*
RIM_WET = (0.25, 1.0)                # = _RimWet: rim x lerp(0.25, 1, saturate((smoothness - 0.58) / 0.30))
DETAIL_STRENGTH = 1.0                # = _DetailNormalMapScale (the hide relief, NOT masked by the crease mask)
GRAZING_FLATTEN = 0.50                                            # = _GrazingFlatten
GRAZING_RANGE = (0.05, 0.50)                                      # smoothstep on N.V
COLOSSUS_TILING = 3.0               # colossi (G, H): main maps tiled (3, 3), detail (12, 13.8): no metre-wide 'bark' runs
CONVEX_KEEP = 0.06                   # = _ConvexCrease: crease normals kept on the convex side (mask 0)
MACRO_BUMP = 0.35                    # = _MacroStrength (colossi)
# LanbaiFog (ART BIBLE v2 §1.6, §6·4): exponential fog 0.0006 whose colour in every direction is the
# luminous haze band of the sky (identical to lib/preview_rig.py's world): #484D63 next to the tear ->
# #2A3041 50 deg away, void #070A14 above +35 deg / beyond 60 deg; extra density low over the cloud sea;
# beyond 1.5 km the fog is capped at 0.6 and falls off with height (no ghost brighter than the sky).
FOG = dict(density=0.0006, extra=0.5, extra_h=60.0, cap=0.6, cap_from=(1300.0, 1700.0), cap_h=500.0,
           z_cloud=0.0, near=_hex_lin('#484D63'), far=_hex_lin('#2A3041'), void=_hex_lin('#070A14'),
           band_az=(50.0, 60.0), band_el=(15.0, 35.0), below=(-25.0, 0.0, 0.55))


def _img(path, noncolor):
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    try:
        im.alpha_mode = 'CHANNEL_PACKED'
    except Exception:
        pass
    return im


def _band_colour(nt, view, fg):
    """LanbaiFog / LanbaiHorizon(view): the haze-band sky colour in world direction `view` (camera ->
    point). Azimuth is measured from world +Y (the tear), exactly like lib/preview_rig.py's world."""
    N, L = nt.nodes.new, nt.links.new

    def m(op, a, b=None):
        n = N('ShaderNodeMath'); n.operation = op
        for i, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    def smooth(v, lo, hi, a=0.0, b=1.0):
        n = N('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        n.inputs['From Min'].default_value = lo; n.inputs['From Max'].default_value = hi
        n.inputs['To Min'].default_value = a; n.inputs['To Max'].default_value = b
        L(v, n.inputs['Value'])
        return n.outputs['Result']

    def mix(fac, a, b):
        n = N('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MIX'; n.clamp_factor = True
        L(fac, n.inputs['Factor'])
        for sock, val in ((n.inputs['A'], a), (n.inputs['B'], b)):
            if isinstance(val, tuple):
                sock.default_value = (*val, 1.0)
            else:
                L(val, sock)
        return n.outputs['Result']

    sep = N('ShaderNodeSeparateXYZ'); L(view, sep.inputs[0])
    el = m('MULTIPLY', m('ARCSINE', m('MINIMUM', m('MAXIMUM', sep.outputs['Z'], -1.0), 1.0)), 180.0 / math.pi)
    az = m('ABSOLUTE', m('MULTIPLY', m('ARCTAN2', sep.outputs['X'], sep.outputs['Y']), 180.0 / math.pi))
    band = mix(smooth(az, 0.0, fg['band_az'][0]), tuple(fg['near']), tuple(fg['far']))
    w = m('MULTIPLY', smooth(az, fg['band_az'][0], fg['band_az'][1], 1.0, 0.0),
          smooth(el, fg['band_el'][0], fg['band_el'][1], 1.0, 0.0))
    sky = mix(w, tuple(fg['void']), band)
    below = smooth(el, fg['below'][0], fg['below'][1], fg['below'][2], 1.0)
    sc = N('ShaderNodeVectorMath'); sc.operation = 'SCALE'; L(sky, sc.inputs[0]); L(below, sc.inputs['Scale'])
    return sc.outputs[0]


def _fog_factor(nt, fg, dist, zpos, density_scale=1.0, cap=None, cap_h=True):
    """ART BIBLE v2 fog amount: 1 - exp(-d * rho * (1 + extra * exp(-h / 60 m))); beyond ~1.5 km
    min(f, cap) * exp(-h / 500 m). h = height above the cloud-sea top at the shaded point."""
    N, L = nt.nodes.new, nt.links.new

    def m(op, a, b=None):
        n = N('ShaderNodeMath'); n.operation = op
        for i, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    h = m('MAXIMUM', m('SUBTRACT', zpos, fg['z_cloud']), 0.0)
    rho = m('MULTIPLY', m('ADD', 1.0, m('MULTIPLY', m('EXPONENT', m('DIVIDE', h, -fg['extra_h'])), fg['extra'])),
            fg['density'] * density_scale)
    f = m('SUBTRACT', 1.0, m('EXPONENT', m('MULTIPLY', m('MULTIPLY', dist, rho), -1.0)))
    capv = fg['cap'] if cap is None else cap
    far = N('ShaderNodeMapRange'); far.interpolation_type = 'SMOOTHSTEP'; far.clamp = True
    far.inputs['From Min'].default_value, far.inputs['From Max'].default_value = fg['cap_from']
    L(dist, far.inputs['Value'])
    fc = m('MINIMUM', f, capv)
    if cap_h:
        fc = m('MULTIPLY', fc, m('EXPONENT', m('DIVIDE', h, -fg['cap_h'])))
    mx = N('ShaderNodeMix'); mx.data_type = 'FLOAT'; mx.clamp_factor = True
    L(far.outputs['Result'], mx.inputs['Factor']); L(f, mx.inputs['A']); L(fc, mx.inputs['B'])
    return mx.outputs['Result']


THIN_K = (0.12, 0.40)            # gate round 8: thin parts (b = r / R_root) lose the main maps' tile period
THIN_SMOOTH = 0.84                # ... one continuous wet sheen (the moon rim's wet term reads it too: no beads)
THIN_ALBEDO = (0.017, 0.017, 0.022)   # ... the albedo map's mean (linear)


def make_material(name='M_Tentacle', tex_dir=None, pix_angle=None, fog=None, rim_dir=None, rim=None,
                  translucency=1.0, tear_pos=(0.0, 1800.0, 300.0), occl=None, colossus=False, tide=False,
                  tiling=None, detail_tiling=None):
    """The preview of Lanbai/TentacleSway v2 (every extra mirrors a line of the Unity shader).
    occl = this variant's T_Tentacle_X_Occlusion.png (crease mask in B, macro height in R), sampled at
    (UV0.x, UVSway.x) = (U, t). fog = FOG-like dict (LanbaiFog); rim_dir = direction toward the moon.
    colossus: macro undulation bump + no fine creases beyond 1.5 km. tide: fog cap 0.92, no height falloff.
    Labelled nodes ('rim_dir', 'tear_pos') are re-aimed per shot by aim_material()."""
    tex_dir = tex_dir or os.path.join(OUT, 'Textures')
    rim = dict(RIM, **(rim or {}))
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new

    def mathn(op, a, b=None, clamp=False):
        n = N('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        for i, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    def vmath(op, a, b=None, scale=None, label=None):
        n = N('ShaderNodeVectorMath'); n.operation = op
        if label:
            n.label = label
        L(a, n.inputs[0]) if not isinstance(a, tuple) else setattr(n.inputs[0], 'default_value', a)
        if b is not None:
            L(b, n.inputs[1]) if not isinstance(b, tuple) else setattr(n.inputs[1], 'default_value', b)
        if scale is not None:
            if isinstance(scale, (int, float)):
                n.inputs['Scale'].default_value = scale
            else:
                L(scale, n.inputs['Scale'])
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH') else n.outputs['Vector']

    def sstep(v, lo, hi, a=0.0, b=1.0):
        n = N('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        n.inputs['From Min'].default_value = lo; n.inputs['From Max'].default_value = hi
        n.inputs['To Min'].default_value = a; n.inputs['To Max'].default_value = b
        L(v, n.inputs['Value'])
        return n.outputs['Result']

    out = N('ShaderNodeOutputMaterial')
    uv = N('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    uvs = N('ShaderNodeUVMap'); uvs.uv_map = 'UVSway'
    attr = N('ShaderNodeAttribute'); attr.attribute_name = 'Col'
    sepc = N('ShaderNodeSeparateColor'); L(attr.outputs['Color'], sepc.inputs[0])
    colB = sepc.outputs['Blue']
    geo = N('ShaderNodeNewGeometry')
    cam = N('ShaderNodeCameraData')
    sp = N('ShaderNodeSeparateXYZ'); L(geo.outputs['Position'], sp.inputs[0])

    # ---- mip emulation (preview only; Unity's trilinear mips do this by themselves) --------------
    lod = None
    if pix_angle:
        oi = N('ShaderNodeObjectInfo')
        so = N('ShaderNodeSeparateColor'); L(oi.outputs['Color'], so.inputs[0])
        r = mathn('MULTIPLY', mathn('MAXIMUM', colB, 0.035), so.outputs['Red'])     # metres (obj colour R = R_root x scale)
        texel = mathn('MULTIPLY', r, 2 * math.pi / TEX_N / (tiling or (COLOSSUS_TILING if colossus else 1.0)))
        foot = mathn('MULTIPLY', cam.outputs['View Distance'], pix_angle)
        foot.node.label = 'pix_angle'
        lod = mathn('LOGARITHM', mathn('MAXIMUM', mathn('DIVIDE', foot, texel), 1.0), 2.0)

    til = tiling or (COLOSSUS_TILING if colossus else 1.0)   # colossi: the shared skin 3x finer (Unity: _MainTex tiling
    # 3, 3); gate v4 (round 3, critique M16): per instance, the skin density follows the arm's girth (tiling override)
    uvt = uv.outputs['UV']
    if til != 1.0:
        mpt = N('ShaderNodeMapping'); mpt.inputs['Scale'].default_value = (til, til, 1.0)
        L(uv.outputs['UV'], mpt.inputs['Vector'])
        uvt = mpt.outputs['Vector']

    def tex(fn, noncolor, interp='Linear'):
        levels = [os.path.join(tex_dir, fn + '.png')]
        if lod is not None:
            levels += [os.path.join(WORK, 'mips', '%s_%d.png' % (fn, lv)) for lv in (2, 4, 6)]
        outs = []
        for pth in levels:
            t = N('ShaderNodeTexImage'); t.image = _img(pth, noncolor); t.interpolation = interp
            L(uvt, t.inputs['Vector'])
            outs.append(t)
        col, alpha = outs[0].outputs['Color'], outs[0].outputs['Alpha']
        if lod is not None:
            lh = mathn('MULTIPLY', lod, 0.5)
            for i, t in enumerate(outs[1:]):
                w = mathn('MINIMUM', mathn('MAXIMUM', mathn('SUBTRACT', lh, float(i)), 0.0), 1.0)
                mc = N('ShaderNodeMix'); mc.data_type = 'RGBA'; mc.blend_type = 'MIX'
                L(w, mc.inputs['Factor']); L(col, mc.inputs['A']); L(t.outputs['Color'], mc.inputs['B'])
                ma = N('ShaderNodeMix'); ma.data_type = 'FLOAT'
                L(w, ma.inputs['Factor']); L(alpha, ma.inputs['A']); L(t.outputs['Alpha'], ma.inputs['B'])
                col, alpha = mc.outputs['Result'], ma.outputs['Result']
        return col, alpha

    alb, _ = tex('T_Tentacle_Albedo', False)
    ms, ms_a = tex('T_Tentacle_MetallicSmoothness', True)
    nrm, _ = tex('T_Tentacle_Normal', True, 'Cubic')

    # ---- detail normal (Standard "Secondary Normal Map", tiling 4 x 4.6), faded like its mips ----
    mp = N('ShaderNodeMapping')
    dtil = detail_tiling or til         # gate v4: the hide relief keeps its physical scale on the giants
    mp.inputs['Scale'].default_value = (DETAIL_TILING[0] * dtil, DETAIL_TILING[1] * dtil, 1.0)
    L(uv.outputs['UV'], mp.inputs['Vector'])
    dt = N('ShaderNodeTexImage'); dt.image = _img(os.path.join(tex_dir, 'T_Tentacle_DetailNormal.png'), True)
    dt.interpolation = 'Cubic'
    L(mp.outputs['Vector'], dt.inputs['Vector'])
    det_w = 1.0 if lod is None else mathn('SUBTRACT', 1.0, mathn('DIVIDE', mathn('ADD', lod, 1.0), 3.0), clamp=True)
    n1 = vmath('SUBTRACT', vmath('SCALE', nrm, scale=2.0), (1.0, 1.0, 1.0))
    n2 = vmath('SUBTRACT', vmath('SCALE', dt.outputs['Color'], scale=2.0), (1.0, 1.0, 1.0))
    s1 = N('ShaderNodeSeparateXYZ'); L(n1, s1.inputs[0])
    s2 = N('ShaderNodeSeparateXYZ'); L(n2, s2.inputs[0])

    # ---- per-variant crease mask + macro height at (U, t) ------------------------------------------
    occ = None
    if occl and os.path.exists(occl):
        su = N('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], su.inputs[0])
        st = N('ShaderNodeSeparateXYZ'); L(uvs.outputs['UV'], st.inputs[0])
        cv = N('ShaderNodeCombineXYZ'); L(su.outputs['X'], cv.inputs['X']); L(st.outputs['X'], cv.inputs['Y'])
        occ = N('ShaderNodeTexImage'); occ.image = _img(occl, True); occ.extension = 'EXTEND'
        L(cv.outputs[0], occ.inputs['Vector'])
        oc = N('ShaderNodeSeparateColor'); L(occ.outputs['Color'], oc.inputs[0])

    # ---- normal strengths (= the shader): MAIN map (creases + muscle bundles) x grazing flatten x crease
    #      mask (concave side only) x far fade (colossi); DETAIL map (the hide: fine relief, papillae,
    #      pores) x grazing flatten only -- the taut convex side is smooth, not polished rubber
    ndv = mathn('ABSOLUTE', vmath('DOT_PRODUCT', geo.outputs['Normal'], geo.outputs['Incoming']))
    graze = mathn('ADD', 1.0 - GRAZING_FLATTEN, mathn('MULTIPLY', sstep(ndv, *GRAZING_RANGE), GRAZING_FLATTEN))
    # gate round 8 (tech r4 B2, awe r4 M5: one texture tile = one circumference, so on the whips every row-coherent
    # feature repeated as evenly spaced RINGS / BEADS): thin parts fade the main maps out. thinK = smoothstep(0.12,
    # 0.40, b): main normal x thinK, smoothness -> one continuous wet 0.84, albedo -> its mean (Unity: TentacleSway v2.7)
    thinK = sstep(colB, THIN_K[0], THIN_K[1])
    keep = mathn('MULTIPLY', graze, thinK)
    if occ is not None:
        keep = mathn('MULTIPLY', keep, mathn('ADD', CONVEX_KEEP, mathn('MULTIPLY', oc.outputs['Blue'], 1.0 - CONVEX_KEEP)))
    if colossus:        # no fine creases beyond 1.5 km
        keep = mathn('MULTIPLY', keep, sstep(cam.outputs['View Distance'], 1000.0, 1500.0, 1.0, 0.0))
    kd = mathn('MULTIPLY', mathn('MULTIPLY', graze, det_w), DETAIL_STRENGTH) if not isinstance(det_w, float) else \
        mathn('MULTIPLY', graze, DETAIL_STRENGTH)
    cb = N('ShaderNodeCombineXYZ')
    L(mathn('ADD', mathn('MULTIPLY', s1.outputs['X'], keep), mathn('MULTIPLY', s2.outputs['X'], kd)), cb.inputs['X'])
    L(mathn('ADD', mathn('MULTIPLY', s1.outputs['Y'], keep), mathn('MULTIPLY', s2.outputs['Y'], kd)), cb.inputs['Y'])
    L(mathn('MULTIPLY', s1.outputs['Z'], s2.outputs['Z']), cb.inputs['Z'])
    nb = vmath('NORMALIZE', cb.outputs[0])
    nb_col = vmath('ADD', vmath('SCALE', nb, scale=0.5), (0.5, 0.5, 0.5))
    nmap = N('ShaderNodeNormalMap'); nmap.space = 'TANGENT'; nmap.uv_map = 'UVMap'
    nmap.inputs['Strength'].default_value = 1.0
    L(nb_col, nmap.inputs['Color'])
    normal = nmap.outputs['Normal']
    if colossus and occ is not None:   # 2-8 m macro undulation: scar grooves (height in Occlusion.r)
        bump = N('ShaderNodeBump'); bump.inputs['Strength'].default_value = MACRO_BUMP
        bump.inputs['Distance'].default_value = 1.0
        L(oc.outputs['Red'], bump.inputs['Height']); L(normal, bump.inputs['Normal'])
        normal = bump.outputs['Normal']

    bsdf = N('ShaderNodeBsdfPrincipled')
    sepm = N('ShaderNodeSeparateColor'); L(ms, sepm.inputs[0])
    L(sepm.outputs[0], bsdf.inputs['Metallic'])
    smoothV = N('ShaderNodeMix'); smoothV.data_type = 'FLOAT'
    L(thinK, smoothV.inputs[0]); smoothV.inputs[2].default_value = THIN_SMOOTH; L(ms_a, smoothV.inputs[3])
    ms_a = smoothV.outputs[0]
    L(mathn('SUBTRACT', 1.0, ms_a), bsdf.inputs['Roughness'])
    L(normal, bsdf.inputs['Normal'])
    try:
        bsdf.inputs['Specular IOR Level'].default_value = 0.5      # F0 0.04, Unity's dielectric
        bsdf.inputs['IOR'].default_value = 1.5
    except KeyError:
        pass
    tint_f = mathn('SUBTRACT', 1.0, sstep(colB, TIP_TINT_TO, TIP_TINT_FROM))
    albT = N('ShaderNodeMix'); albT.data_type = 'RGBA'; albT.blend_type = 'MIX'
    L(thinK, albT.inputs['Factor']); albT.inputs['A'].default_value = (*THIN_ALBEDO, 1.0); L(alb, albT.inputs['B'])
    alb = albT.outputs['Result']
    mix = N('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    L(tint_f, mix.inputs['Factor']); L(alb, mix.inputs['A'])
    mix.inputs['B'].default_value = (*TIP_TINT, 1)
    L(mix.outputs['Result'], bsdf.inputs['Base Color'])
    surf = bsdf.outputs[0]
    # ---- tear position / direction ------------------------------------------------------------------
    tp = N('ShaderNodeCombineXYZ'); tp.label = 'tear_pos'
    for i, c in enumerate('XYZ'):
        tp.inputs[c].default_value = tear_pos[i]
    tvec = vmath('SUBTRACT', tp.outputs[0], geo.outputs['Position'])
    to_tear = vmath('NORMALIZE', tvec)
    tdist = vmath('LENGTH', tvec)
    facing_t = sstep(vmath('DOT_PRODUCT', geo.outputs['Normal'], to_tear), -0.1, 0.6)
    # ---- thin-tip transmission: (1 - B)^2 x tear light x #5B57A1, only on the tear-facing side ------
    if translucency > 0:
        ib = mathn('SUBTRACT', 1.0, colB)
        thin = mathn('MULTIPLY', mathn('MULTIPLY', ib, ib), sstep(colB, 0.10, 0.35, 1.0, 0.0))
        amt = mathn('MULTIPLY', mathn('MULTIPLY', thin, facing_t), TRANS_GAIN * translucency)
        tcol = N('ShaderNodeVectorMath'); tcol.operation = 'SCALE'
        tcol.inputs[0].default_value = TRANSLUCENT
        L(amt, tcol.inputs['Scale'])
        trans = N('ShaderNodeBsdfTranslucent')
        L(tcol.outputs[0], trans.inputs['Color']); L(normal, trans.inputs['Normal'])
        add = N('ShaderNodeAddShader'); L(surf, add.inputs[0]); L(trans.outputs[0], add.inputs[1])
        surf = add.outputs[0]
    # ---- rims (ART BIBLE v2): moon side #9DB8FF x pow(1 - N.V, 5) x saturate(0.3 - N.L_moon);
    #      tear side #A99DE1 x pow(1 - N.V, 4) x tear-facing x proximity (1 < 200 m, 0 > 1.2 km) ----------
    fr = lambda p: mathn('POWER', mathn('SUBTRACT', 1.0, ndv, clamp=True), p)
    # the moon rim beads along the wet streaks (a grazing reflection: wet 1, dry ~0.45) instead of a sticker line
    wetk = mathn('ADD', RIM_WET[0], mathn('MULTIPLY', mathn('MULTIPLY', mathn('SUBTRACT', ms_a, 0.58), 1.0 / 0.30, clamp=True), 1.0 - RIM_WET[0]))
    if rim_dir is not None and rim['moon'] > 0:
        nl = vmath('DOT_PRODUCT', geo.outputs['Normal'], tuple(rim_dir), label='rim_dir')
        e = mathn('MULTIPLY', mathn('MULTIPLY', mathn('MULTIPLY', fr(5.0), mathn('SUBTRACT', 0.3, nl, clamp=True)), rim['moon']), wetk)
        em = N('ShaderNodeEmission'); em.inputs['Color'].default_value = (*rim['moon_color'], 1)
        L(e, em.inputs['Strength'])
        add = N('ShaderNodeAddShader'); L(surf, add.inputs[0]); L(em.outputs[0], add.inputs[1])
        surf = add.outputs[0]
    if rim['tear'] > 0:
        prox = sstep(tdist, rim['tear_near'], rim['tear_far'], 1.0, 0.0)
        e = mathn('MULTIPLY', mathn('MULTIPLY', mathn('MULTIPLY', fr(4.0), facing_t), prox), rim['tear'])
        em = N('ShaderNodeEmission'); em.inputs['Color'].default_value = (*rim['tear_color'], 1)
        L(e, em.inputs['Strength'])
        add = N('ShaderNodeAddShader'); L(surf, add.inputs[0]); L(em.outputs[0], add.inputs[1])
        surf = add.outputs[0]
    # ---- LanbaiFog: rims and speculars are inside `surf`, so they fade with the fog ----------------------
    if fog:
        fg = dict(FOG, **fog)
        f = _fog_factor(nt, fg, cam.outputs['View Distance'], sp.outputs['Z'], density_scale=fg.get('density_scale', 1.0),
                        cap=0.92 if tide else None, cap_h=not tide)
        view = vmath('SCALE', geo.outputs['Incoming'], scale=-1.0)
        em = N('ShaderNodeEmission'); L(_band_colour(nt, view, fg), em.inputs['Color'])
        mx = N('ShaderNodeMixShader')
        L(f, mx.inputs[0]); L(surf, mx.inputs[1]); L(em.outputs[0], mx.inputs[2])
        surf = mx.outputs[0]
    L(surf, out.inputs['Surface'])
    return m


def aim_material(mat, to_moon=None, tear_pos=None, cam_pos=None):
    """Re-aim the labelled nodes of a tentacle material for the current shot."""
    for n in mat.node_tree.nodes:
        if n.label == 'rim_dir' and to_moon is not None:
            n.inputs[1].default_value = tuple(to_moon)
        elif n.label == 'tear_pos' and tear_pos is not None:
            for i, c in enumerate('XYZ'):
                n.inputs[c].default_value = tear_pos[i]


# =============================================================================================
# 5. FBX EXPORT + re-import check
# =============================================================================================
LOD_BUDGET = (6000, 2000, 600)


def export_variants(keys=ORDER, out=None):
    import export_unity
    out = out or os.path.join(OUT, 'FBX')
    os.makedirs(out, exist_ok=True)
    report = {}
    for key in keys:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mat = bpy.data.materials.new('M_Tentacle')          # slot name only; Unity makes its own material
        root = bpy.data.objects.new('Tentacle_%s' % key, None)
        bpy.context.scene.collection.objects.link(root)
        obs = [root]
        rep = {}
        for lod in range(3):
            ob = variant_object(key, lod)
            ob.data.materials.append(mat)
            ob.parent = root
            obs.append(ob)
            r = mesh_report(ob)
            assert r['tris'] <= LOD_BUDGET[lod], (key, lod, r['tris'])
            assert r['volume'] > 0 and r['min_area'] > 0, (key, lod, r)
            rep['LOD%d' % lod] = r
        path = os.path.join(out, 'Tentacle_%s.fbx' % key)
        export_unity.export_fbx(path, obs)
        rep['fbx'] = path
        report[key] = rep
        print('FBX %s  tris %s  vol %.0f  min_area %.2g  bbox %s' % (
            key, [rep['LOD%d' % i]['tris'] for i in range(3)], rep['LOD0']['volume'],
            min(rep['LOD%d' % i]['min_area'] for i in range(3)), rep['LOD0']['bbox']))
    return report


def check_fbx(keys=ORDER, out=None):
    """Re-import every FBX (linear colours, like Unity reads them) and print what the importer sees."""
    out = out or os.path.join(OUT, 'FBX')
    res = {}
    for key in keys:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        kw = dict(filepath=os.path.join(out, 'Tentacle_%s.fbx' % key))
        try:
            bpy.ops.import_scene.fbx(colors_type='LINEAR', **kw)
        except TypeError:
            bpy.ops.import_scene.fbx(**kw)
        info = {}
        for o in sorted(bpy.context.scene.objects, key=lambda o: o.name):
            if o.type != 'MESH':
                info[o.name] = dict(type=o.type, children=sorted(c.name for c in o.children))
                continue
            me = o.data
            me.calc_loop_triangles()
            ca = me.color_attributes.get('Col') or (me.color_attributes[0] if len(me.color_attributes) else None)
            c = np.array([d.color[:] for d in ca.data])
            uvd = np.array([d.uv[:] for d in me.uv_layers[0].data])
            info[o.name] = dict(tris=len(me.loop_triangles), uv=[u.name for u in me.uv_layers], col=ca.name,
                                R=(round(c[:, 0].min(), 3), round(c[:, 0].max(), 3)), G=round(float(c[:, 1].mean()), 3),
                                B=(round(c[:, 2].min(), 3), round(c[:, 2].max(), 3)), A=round(float(c[:, 3].min()), 3),
                                U=(round(uvd[:, 0].min(), 2), round(uvd[:, 0].max(), 2)),
                                rot=tuple(round(math.degrees(x), 2) for x in o.rotation_euler),
                                scale=tuple(round(x, 3) for x in o.scale),
                                zmax=round(max((o.matrix_world @ Vector(b)).z for b in o.bound_box), 1))
        res[key] = info
        print('reimport', key, json.dumps(info))
    return res


# =============================================================================================
# 6. STAGING + RENDERS  (preview only; everything goes through lib/preview_rig.py)
# =============================================================================================
def _look_rot(direction):
    return Vector(direction).normalized().to_track_quat('-Z', 'Y').to_euler()


def set_moon(to_moon, energy=None, color=None, angle_deg=None):
    """Point the rig's moon: `to_moon` = world direction toward the moon."""
    moon = bpy.data.objects['PR_Moon']
    moon.rotation_euler = _look_rot(-Vector(to_moon))
    if energy is not None:
        moon.data.energy = energy
    if color is not None:
        moon.data.color = color
    if angle_deg is not None:
        moon.data.angle = math.radians(angle_deg)
    return Vector(to_moon).normalized()


def face_tear(slit, cam_loc, subject):
    """The rip faces the approaching bus: turn the rig's tear plane (and its light) to the camera."""
    slit.rotation_euler = (Vector(cam_loc) - slit.location).to_track_quat('Z', 'Y').to_euler()
    lo = bpy.data.objects['PR_TearLight']
    lo.location = slit.location + (Vector(cam_loc) - slit.location).normalized() * 1.0
    lo.rotation_euler = (Vector(subject) - lo.location).to_track_quat('-Z', 'Y').to_euler()


def instance(key, mesh_cache, mat, loc, rot_q, scale=1.0, name=None, lod=0):
    """A linked duplicate of variant `key` at LOD `lod` (shares the mesh). rot_q: mathutils Quaternion."""
    ck = (key, lod, mat.name)
    if ck not in mesh_cache:
        ob = variant_object(key, lod, name='SRC_%s%d_%s' % (key, lod, mat.name))
        ob.data.materials.append(mat)
        mesh_cache[ck] = ob.data
        bpy.context.scene.collection.objects.unlink(ob)
    ob = bpy.data.objects.new(name or 'T_%s' % key, mesh_cache[ck])
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = rot_q
    ob.location = loc
    ob.scale = (scale, scale, scale)
    ob.color = (VARIANTS[key]['R'] * scale, 1, 1, 1)     # texel scale for the mip emulation
    return ob


def add_box(name, size, loc, rot_z=0.0, windows=True):
    """The bus as a scale reference: an 8 m dark box with a strip of warm lit windows."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    b = bpy.context.object
    b.name = name
    b.scale = size
    b.rotation_euler = (0, 0, rot_z)
    m = bpy.data.materials.new(name + '_M')
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (0.02, 0.022, 0.026, 1)
    bs.inputs['Roughness'].default_value = 0.45
    b.data.materials.append(m)
    if windows:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        w = bpy.context.object
        w.name = name + '_Windows'
        w.scale = (size[0] * 0.86, size[1] * 1.02, size[2] * 0.26)
        w.location = Vector(loc) + Vector((0, 0, size[2] * 0.12))
        w.rotation_euler = (0, 0, rot_z)
        mw = bpy.data.materials.new(name + '_W')
        mw.use_nodes = True
        nt = mw.node_tree
        nt.nodes.clear()
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (1.0, 0.62, 0.30, 1)
        em.inputs['Strength'].default_value = 6.0
        o = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], o.inputs['Surface'])
        w.data.materials.append(mw)
        w.visible_shadow = False
    return b


def _placed_bbox(parts_or_ob):
    bpy.context.view_layer.update()
    ob = parts_or_ob
    vs = ob.data.vertices
    co = np.array([(ob.matrix_world @ vs[i].co)[:] for i in range(0, len(vs), 7)])
    return co.min(0), co.max(0)


TIP_NAMES = {'A': ('whip', '甩鞭：细线鞭 + 末端反挑'), 'B': ('droop', '垂：前拱、下垂、猛禽钩'),
             'C': ('corkscrew', '拧绳：身体拧 1.5 圈，半卷'), 'D': ('broad C + open coil', '大 C + 出平面的松卷'),
             'E': ('double S + forked tip', '双 S + 分叉的舌尖'), 'F': ('wave crest', '浪头：前倾、卷过、泻成鞭'),
             'G': ('colossus · swan neck + braid', '巨像 · 天鹅颈 + 辫'), 'H': ('colossus · the reach', '巨像 · 探：盘旋上升、磨散的尖')}
TIP_SHORT = {k: v[0] for k, v in TIP_NAMES.items()}
# per-variant turn about the vertical so every gesture reads side-on (D's coil and H's reach face-on)
LINEUP_TURN = {'A': 20.0, 'C': 25.0, 'D': 160.0, 'E': 30.0, 'G': 10.0, 'H': -15.0}
LINEUP_LOOK = dict(moon=(-0.45, 0.55, 0.70), moon_energy=5.0, moon_angle=4.0, tear=(1.0, 0.35, 0.10), tear_energy=2.2,
                   fill_energy=0.7, fill_angle=80.0, front=(-0.35, -1.0, 0.45), front_energy=0.55, front_angle=25.0,
                   cloud_gain=0.55, exposure=-0.35)
FONT_DIRS = [os.environ.get('LANBAI_FONTS', ''), os.path.join(HERE, 'fonts'), os.path.join(HERE, '..', '..', '..', 'fonts'),
             os.path.join(HERE, '..', '..', '..', '..', 'fonts'), os.path.join(LIB, '..', '..', 'fonts')]   # Barlow + 思源黑体 (OFL)


def _backdrop(name, Wm, Hm, cx, zc, y, ground_z, moon_uv=(0.07, 0.86), tear_side=1.0):
    """The lineup's night sky, camera rays only: the v2 haze band at the horizon (#484D63 toward the tear on the
    right, #2A3041 away from it) fading to the void #070A14 by ~45 % of the height, the tear's dusk-indigo glow
    (#5B57A1) rising off the right edge, a small moon (#D6E4FF) with its silver halo (#5A6A88) top left, sparse
    stars. Values x 1.9 like the gate preview's sky (AgX + S4 compensation, README 5.3)."""
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(cx, y, zc))
    p = bpy.context.object
    p.name = name
    p.rotation_euler = (math.radians(90), 0, 0)
    p.scale = (Wm * 1.02, Hm * 1.02, 1)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputMaterial')
    tc = N('ShaderNodeTexCoord')
    sp = N('ShaderNodeSeparateXYZ'); L(tc.outputs['UV'], sp.inputs[0])

    def mth(op, a, b=None):
        n = N('ShaderNodeMath'); n.operation = op
        for i, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    def mr(v, a, b, c=0.0, d=1.0):
        n = N('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b
        n.inputs['To Min'].default_value = c; n.inputs['To Max'].default_value = d
        L(v, n.inputs['Value'])
        return n.outputs['Result']

    def mix(f, a, b):
        n = N('ShaderNodeMix'); n.data_type = 'RGBA'; n.clamp_factor = True
        L(f, n.inputs['Factor'])
        for s_, v in ((n.inputs['A'], a), (n.inputs['B'], b)):
            if isinstance(v, tuple):
                s_.default_value = (*v, 1.0)
            else:
                L(v, s_)
        return n.outputs['Result']
    g = 1.9
    X, Yv = sp.outputs['X'], sp.outputs['Y']
    hz = (ground_z - (zc - Hm / 2)) / Hm                                     # horizon line in v
    above = mth('SUBTRACT', Yv, hz)
    band = mix(mr(X, 0.15, 1.0), tuple(c * g for c in _hex_lin('#2A3041')), tuple(c * g for c in _hex_lin('#484D63')))
    sky = mix(mr(above, 0.0, 0.42), band, tuple(c * g for c in _hex_lin('#070A14')))
    sky = mix(mr(above, -0.02, -0.25), sky, tuple(c * g * 0.55 for c in _hex_lin('#2A3041')))     # below the horizon
    # the tear's glow off the right edge, low
    dx = mth('SUBTRACT', X, 1.08)
    dy = mth('MULTIPLY', mth('SUBTRACT', Yv, hz + 0.16), 1.7)
    rr = mth('SQRT', mth('ADD', mth('MULTIPLY', dx, dx), mth('MULTIPLY', dy, dy)))
    glow = mth('MULTIPLY', mth('EXPONENT', mth('MULTIPLY', rr, -4.2)), 1.25 * tear_side)
    gl = N('ShaderNodeVectorMath'); gl.operation = 'SCALE'; gl.inputs[0].default_value = tuple(c * g for c in _hex_lin('#5B57A1'))
    L(glow, gl.inputs['Scale'])
    ad = N('ShaderNodeVectorMath'); ad.operation = 'ADD'; L(sky, ad.inputs[0]); L(gl.outputs[0], ad.inputs[1])
    col = ad.outputs[0]
    # moon disc + halo (aspect-corrected radius in v units)
    asp = Wm / Hm
    mx_ = mth('MULTIPLY', mth('SUBTRACT', X, moon_uv[0]), asp)
    my_ = mth('SUBTRACT', Yv, moon_uv[1])
    md = mth('SQRT', mth('ADD', mth('MULTIPLY', mx_, mx_), mth('MULTIPLY', my_, my_)))
    disc = mr(md, 0.0105, 0.0085)
    halo = mth('ADD', mth('MULTIPLY', mth('EXPONENT', mth('MULTIPLY', md, -38.0)), 0.55),
               mth('MULTIPLY', mth('EXPONENT', mth('MULTIPLY', md, -9.0)), 0.18))
    hc = N('ShaderNodeVectorMath'); hc.operation = 'SCALE'; hc.inputs[0].default_value = tuple(c * g for c in _hex_lin('#5A6A88'))
    L(halo, hc.inputs['Scale'])
    dc = N('ShaderNodeVectorMath'); dc.operation = 'SCALE'; dc.inputs[0].default_value = (2.3, 2.5, 2.8)
    nz = N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 260.0; L(tc.outputs['UV'], nz.inputs['Vector'])
    L(mth('MULTIPLY', disc, mth('ADD', 0.78, mth('MULTIPLY', nz.outputs['Fac'], 0.4))), dc.inputs['Scale'])
    for v_ in (hc.outputs[0], dc.outputs[0]):
        a2 = N('ShaderNodeVectorMath'); a2.operation = 'ADD'; L(col, a2.inputs[0]); L(v_, a2.inputs[1]); col = a2.outputs[0]
    # sparse stars in the void only (tiny, fixed size in pixels of the final frame)
    vo = N('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 90.0
    mp = N('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (asp, 1.0, 1.0); L(tc.outputs['UV'], mp.inputs['Vector'])
    L(mp.outputs['Vector'], vo.inputs['Vector'])
    sc_ = N('ShaderNodeSeparateColor'); L(vo.outputs['Color'], sc_.inputs[0])
    star = mth('MULTIPLY', mr(vo.outputs['Distance'], 0.0035, 0.0), mr(sc_.outputs[0], 0.80, 1.0))
    star = mth('MULTIPLY', star, mr(above, 0.18, 0.40))
    st = N('ShaderNodeVectorMath'); st.operation = 'SCALE'; st.inputs[0].default_value = (0.9, 0.95, 1.1)
    L(star, st.inputs['Scale'])
    a3 = N('ShaderNodeVectorMath'); a3.operation = 'ADD'; L(col, a3.inputs[0]); L(st.outputs[0], a3.inputs[1])
    em = N('ShaderNodeEmission'); L(a3.outputs[0], em.inputs['Color'])
    L(em.outputs[0], out.inputs['Surface'])
    p.data.materials.append(m)
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        setattr(p, attr, False)
    return p


def _lineup_scene(res, samples, keys, bus=True, gap_frac=0.10, min_gap=6.0, ground=0.22, look=None):
    """Variants side by side at true scale (reaching right, toward the tear beyond the right edge), an
    orthographic camera fitted to them, the painted night backdrop, roots buried in the moon cloud-sea
    cards, the 8 m bus hovering over the clouds. Returns (placed list, camera params) for the labels."""
    import preview_rig as pr
    k = dict(LINEUP_LOOK, **(look or {}))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = pr.setup(samples=samples, res=res)
    sc.view_settings.exposure = k['exposure']
    sc.cycles.transparent_max_bounces = 32
    wnt = sc.world.node_tree                    # the world lights and reflects; no stars in it here
    for nd in [n_ for n_ in wnt.nodes if n_.type == 'MIX' and n_.blend_type == 'ADD']:
        for i_ in [i_ for i_ in nd.inputs if i_.name == 'B' and i_.is_linked]:
            if i_.links[0].from_node.type == 'COMBINE_COLOR':
                wnt.links.remove(i_.links[0])
                i_.default_value = (0.0, 0.0, 0.0, 1.0)
    to_moon = set_moon(k['moon'], energy=k['moon_energy'], angle_deg=k['moon_angle'])
    fill = bpy.data.objects['PR_Fill']
    fill.data.energy = k['fill_energy']; fill.data.angle = math.radians(k['fill_angle'])
    fd = bpy.data.lights.new('LU_Front', 'SUN')             # soft cold fill from the camera side: the skin reads
    fd.color = _hex_lin('#C9D6F0'); fd.energy = k['front_energy']; fd.angle = math.radians(k['front_angle'])
    fo = bpy.data.objects.new('LU_Front', fd); bpy.context.scene.collection.objects.link(fo)
    fo.rotation_euler = _look_rot(-Vector(k['front']))
    tex_dir = os.path.join(OUT, 'Textures')
    mats = {k_: make_material('M_Tentacle_%s' % k_, pix_angle=1e-4, rim_dir=to_moon, colossus=k_ in 'GH',
                              occl=os.path.join(tex_dir, 'T_Tentacle_%s_Occlusion.png' % k_)) for k_ in keys}
    cache = {}
    x = 0.0
    placed = []
    for key in keys:
        qk = Quaternion((0, 0, 1), math.radians(90 + LINEUP_TURN.get(key, 0.0)))
        ob = instance(key, cache, mats[key], (0, 0, 0), qk, name='T_' + key)
        lo, hi = _placed_bbox(ob)
        w = hi[0] - lo[0]
        sink = 0.035 * VARIANTS[key]['L']                     # roots sunk into the cloud sea
        ob.location = (x - lo[0], 0.0, -sink)
        placed.append(dict(key=key, ob=ob, x0=x, x1=x + w, top=hi[2] - sink, depth=(lo[1], hi[1])))
        x += w + max(min_gap, gap_frac * VARIANTS[key]['L'])
    width = x
    zmax = max(p['top'] for p in placed)
    bus_x = -max(min_gap, 0.10 * VARIANTS[keys[0]]['L']) - 4.0
    xmin = bus_x - 10.0 if bus else -min_gap
    aspect = res[0] / res[1]
    Wm = max((width - xmin) * 1.04, zmax * 1.16 * aspect / (1.0 - ground))
    Hm = Wm / aspect
    cx = (xmin + width) / 2
    zc = Hm * 0.5 - Hm * ground
    ymin = min(p['depth'][0] for p in placed)
    ymax = max(p['depth'][1] for p in placed)
    dist = 10.0 * Hm
    bpy.ops.object.camera_add(location=(cx, ymin - dist, zc), rotation=(math.radians(90), 0, 0))
    cam = bpy.context.object
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = Wm
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.clip_start = 1.0
    cam.data.clip_end = dist * 3
    sc.camera = cam
    for m_ in mats.values():
        for nd in m_.node_tree.nodes:                     # mip emulation: the real texel footprint (ortho)
            if nd.label == 'pix_angle':
                nd.inputs[1].default_value = Wm / res[0] / dist
    _backdrop('LU_Sky', Wm, Hm, cx, zc, ymax + 0.4 * Hm, 0.0)
    # the cloud sea the roots rise from: ONE consistent row of the delivered moon cloud-sea cards (same texel
    # scale everywhere), flattened to a thin distant layer in front of the roots, and a darker row behind
    meta = _cloud_meta()
    wc = 0.42 * Wm
    n_c = int(math.ceil(Wm / (0.55 * wc))) + 2
    for j in range(n_c):
        for row, (yy, br, zf) in enumerate(((ymin - 3.0, 1.0, 0.0), (ymax + 25.0, 0.75, 0.004))):
            loc = (cx - Wm / 2 + (j - 0.5 + 0.37 * row) * 0.55 * wc, yy - 0.3 * j, -0.030 * Hm + zf * Hm)
            c_ = add_cloud_card('LU_Cloud_%d_%d' % (row, j), 'CloudSea_%d_moon' % (1 + (j + row) % 2), loc, wc,
                                (loc[0], loc[1] - 100.0, loc[2]), brightness=k['cloud_gain'] * br, mirror=bool((j + row) % 2),
                                tint=(0.95, 1.0, 1.08), meta=meta, feather=0.25)
            c_.scale.y *= k.get('cloud_flat', 0.30)
            c_.location.z = loc[2] + (c_.location.z - loc[2]) * k.get('cloud_flat', 0.30)
    if bus:
        add_box('Bus', (8.0, 2.5, 3.0), (bus_x, 0, 0.08 * zmax + 3.0))
    tl = bpy.data.lights.new('LU_Tear', 'SUN')             # the tear light, from the right (the rip is off-frame right)
    tl.color = pr.TEAR_LIGHT; tl.energy = k['tear_energy']; tl.use_shadow = False
    to = bpy.data.objects.new('LU_Tear', tl); bpy.context.scene.collection.objects.link(to)
    to.rotation_euler = _look_rot(-Vector(k['tear']))
    tear_pos = (width + 3.0 * zmax, 0.35 * zmax, zmax * 0.3)
    for m_ in mats.values():
        aim_material(m_, to_moon=to_moon, tear_pos=tear_pos)
    return placed, dict(cx=cx, Wm=Wm, Hm=Hm, zc=zc, bus_x=bus_x if bus else None)


def _font(size, kind='latin', bold=False):
    from PIL import ImageFont
    names = {'latin': ['BarlowSemiCondensed-SemiBold.ttf' if bold else 'BarlowSemiCondensed-Medium.ttf'],
             'cjk': ['SourceHanSansCN-Medium.otf' if bold else 'SourceHanSansCN-Regular.otf']}[kind]
    for d in FONT_DIRS:
        for nm in names:
            f = os.path.join(d, nm)
            if os.path.exists(f):
                return ImageFont.truetype(f, size)
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/TTF/DejaVuSans.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def shot_lineup(res, samples, out, inset=True, look=None):
    """All eight variants side by side at true scale (smallest to largest) with the 8 m bus, a 100 m scale
    bar, names, lengths and gestures (EN + 中文); an inset magnifies the four small ones next to the bus."""
    import preview_rig as pr
    from PIL import ImageDraw
    placed, cp = _lineup_scene(res, samples, ORDER, gap_frac=0.20, min_gap=12.0, ground=0.22, look=look)
    pr.render(out)
    im = Image.open(out).convert('RGB')
    W, H = im.size
    px = lambda X: (X - (cp['cx'] - cp['Wm'] / 2)) / cp['Wm'] * W
    zb = H * (0.5 + cp['zc'] / cp['Hm'])
    dr = ImageDraw.Draw(im)
    s = W / 1920.0
    fN, fL, fC = _font(int(26 * s), bold=True), _font(int(17 * s)), _font(int(16 * s), 'cjk')
    ink, sub, cjk = (226, 232, 246), (150, 162, 194), (178, 186, 212)
    y0 = zb + H * 0.045
    for n, p in enumerate(placed[4:]):
        xc = px((p['x0'] + p['x1']) / 2)
        yy = y0 + (n % 2) * H * 0.085
        if n % 2:
            dr.line([(xc, zb + H * 0.03), (xc, yy - 4 * s)], fill=(80, 90, 120), width=1)
        en, zh = TIP_NAMES[p['key']]
        dr.text((xc, yy), 'Tentacle_%s' % p['key'], fill=ink, font=fN, anchor='mt')
        dr.text((xc, yy + 31 * s), '%.0f m  ·  %s' % (centreline(p['key'])['L'], en), fill=sub, font=fL, anchor='mt')
        dr.text((xc, yy + 53 * s), zh, fill=cjk, font=fC, anchor='mt')
    xa = px(0.5 * (placed[0]['x0'] + placed[3]['x1']))
    ya = y0 + H * 0.085
    dr.line([(xa, zb + H * 0.03), (xa, ya - 4 * s)], fill=(80, 90, 120), width=1)
    dr.text((xa, ya), 'A  B  C  D', fill=ink, font=fN, anchor='mt')
    dr.text((xa, ya + 31 * s), '25–72 m  ·  see inset', fill=sub, font=fL, anchor='mt')
    dr.text((xa, ya + 53 * s), '近层 / 中层（放大见左上）', fill=cjk, font=fC, anchor='mt')
    bx0 = W * 0.035
    bx1 = bx0 + 100.0 / cp['Wm'] * W
    by = H * 0.955
    dr.line([(bx0, by), (bx1, by)], fill=(200, 205, 225), width=max(1, int(2 * s)))
    for bx in (bx0, bx1):
        dr.line([(bx, by - 5 * s), (bx, by + 5 * s)], fill=(200, 205, 225), width=max(1, int(2 * s)))
    dr.text(((bx0 + bx1) / 2, by - 8 * s), '100 m', fill=(200, 205, 225), font=fL, anchor='mb')
    dr.text((W - 24 * s, H - 20 * s), '蓝白 · 触手库 v2.1   ·   true scale, orthographic   ·   bus 8 m',
            fill=(120, 130, 160), font=_font(int(15 * s), 'cjk'), anchor='rb')
    if inset:
        iw, ih = int(W * 0.40), int(H * 0.46)
        tmp = out.replace('.png', '_inset.png')
        placed_i, ci = _lineup_scene((iw, ih), samples, 'ABCD', bus=True, gap_frac=0.55, min_gap=14.0, ground=0.36, look=look)
        pr.render(tmp)
        ins = Image.open(tmp).convert('RGB')
        di = ImageDraw.Draw(ins)
        pxi = lambda X: (X - (ci['cx'] - ci['Wm'] / 2)) / ci['Wm'] * iw
        zbi = ih * (0.5 + ci['zc'] / ci['Hm'])
        g1, g2, g3 = _font(int(21 * s), bold=True), _font(int(14 * s)), _font(int(13 * s), 'cjk')
        for n, p in enumerate(placed_i):
            xc = pxi((p['x0'] + p['x1']) / 2)
            yy = zbi + ih * 0.06 + (n % 2) * ih * 0.13
            if n % 2:
                di.line([(xc, zbi + ih * 0.04), (xc, yy - 3 * s)], fill=(80, 90, 120), width=1)
            en, zh = TIP_NAMES[p['key']]
            di.text((xc, yy), 'Tentacle_%s' % p['key'], fill=ink, font=g1, anchor='mt')
            di.text((xc, yy + 25 * s), '%.0f m · %s' % (centreline(p['key'])['L'], en), fill=sub, font=g2, anchor='mt')
            di.text((xc, yy + 43 * s), zh, fill=cjk, font=g3, anchor='mt')
        di.text((pxi(ci['bus_x']), zbi - ih * 0.13), 'bus 8 m', fill=(240, 205, 160), font=g2, anchor='mb')
        di.text((10 * s, 8 * s), 'A–D  ×%.1f' % (cp['Wm'] / ci['Wm'] * iw / W), fill=(200, 205, 225), font=g2)
        di.rectangle([0, 0, iw - 1, ih - 1], outline=(96, 106, 146), width=max(1, int(2 * s)))
        im.paste(ins, (int(W * 0.018), int(H * 0.03)))
        os.remove(tmp)
    im.save(out)
    return out


def body_frame(key, u, mw):
    """World position, tangent and radius of variant `key` at arc fraction u under matrix mw."""
    sp = VARIANTS[key]
    cl = centreline(key)
    i = int(np.clip(np.searchsorted(cl['u'], u), 0, len(cl['u']) - 1))
    M3 = mw.to_3x3()
    sc = M3.col[0].length
    P = mw @ Vector(cl['P'][i])
    T = (M3 @ Vector(cl['T'][i])).normalized()
    r = float(sp['R'] * radius_profile(u, sp.get('heavy', 1.0), (sp['phase'] * 7.3) % 1.0)) * sc
    return P, T, r


# ---------------------------------------------------------------------------------------------
# THE GATE (ART BIBLE v2 §6·4, the U7 frame): world metres, Blender Z-up. The cloud-sea top at z = 0,
# the bus (camera) 50 m above it looking 7 deg up through the windscreen, the tear at azimuth 0 (+Y),
# 1.8 km ahead, 635 m tall, its foot torn down into the cloud sea. Four depth layers (v2 distance table):
#   near      2 arms, 8-20 m, library A-D, moving WITH the bus toward the tear;
#   mid       a ring of 30 arms 400-900 m round the tear's foot (D-F x1.6-1.8), bending into the wound,
#             their fingertips interlacing over its lower half as if closing it;
#   colossi   3 choreographed (440 m at 3.2 km +24 deg; 450 m at 1.9 km -16 deg, beside the moon;
#             one leaning in at the right lip) + 8 in the background at 1.3-4 km, heads clear, feet gone;
#   tide      400 arms 5-12 km out within +-70 deg (preview stand-ins: LOD2; Unity: impostor atlas).
# Unless a roll is given, every arm is rolled so its END points at the tear (auto-roll).
# ---------------------------------------------------------------------------------------------
GATE = dict(
    cam=(0.0, 0.0, 50.0), pitch=7.0, yaw=0.0, lens=24.0, aspect=2.39, rise=0.3,
    tear=(0.0, 1800.0, 297.0), tear_h=635.0, tear_w=0.22,
    # (variant, azimuth deg (+ = right), distance m, root z, scale, reach, roll deg or None = auto[, extra])
    # extra: dict(aim=(x, y, z) world point the chord points at, lod=k, mat='colossus'|'tide', layer=...)
    polar=[
        # near: moving with the bus, rising out of the cloud sea beside it (nothing ever touches the bus)
        # (poses from a search: closest approach 12-14 m, rising past the windscreen corners, 70-71 m long)
        ('A', -45.0, 14.14, -5.0, 2.8, 1.0, None, dict(aim=(-6.3, 17.9, 94.6), layer='near')),
        ('C', 45.0, 14.14, -5.0, 1.2, 1.0, None, dict(aim=(6.3, 17.9, 94.6), layer='near', flyby=True)),
        # the three choreographed colossi
        ('H', 24.0, 3200.0, -60.0, 1.023, 0.12, None, dict(mat='colossus', layer='colossus')),     # colossus 1, 440 m
        ('G', -17.0, 1900.0, -50.0, 1.5, 0.10, None, dict(mat='colossus', layer='colossus')),     # colossus 2, 450 m
        ('H', 13.0, 1500.0, -60.0, 0.90, 0.40, None, dict(mat='colossus', layer='colossus')),     # colossus 3, at the right lip
    ],
    ring=dict(n=30, seed=5, radius=(400.0, 900.0), theta=(-150.0, 150.0), keys='DEFEF', scale=(1.6, 1.8),
              z=(-30.0, -8.0), aim_z=(260.0, 560.0), aim_x=(-60.0, 60.0), reach=(0.7, 0.85), min_px=60.0,
              min_px_key=dict(D=28.0)),        # D's loose coil is compact: let a few half-curls into the ring
    background=dict(n=8, seed=9, dist=(1300.0, 4000.0), az=(-48.0, 48.0), clear=10.0, keys='GHG',
                    scale=(0.7, 1.0), z=(-70.0, -40.0), reach=(0.10, 0.35)),
    tide=dict(n=400, seed=13, dist=(5000.0, 12000.0), az=(-70.0, 70.0), keys='ACEFFE', size=(150.0, 600.0),
              z=(-60.0, -20.0), reach=(0.75, 0.95)),
)


def _polar_xy(g, az, dist):
    a = math.radians(az + g.get('yaw', 0.0))
    return g['cam'][0] + dist * math.sin(a), g['cam'][1] + dist * math.cos(a)


def gate_ring(g):
    """Mid layer: a ring round the tear's foot, every arm bending into the lower half of the wound (its
    fingertips interlacing with the others' as if closing it); only arms that show >= min_px survive."""
    c = g['ring']
    rng = np.random.default_rng(c['seed'])
    tx, ty, tz = g['tear']
    out, tries = [], 0
    while len(out) < c['n'] and tries < 3000:
        tries += 1
        th = math.radians(rng.uniform(*c['theta']))
        rad = rng.uniform(*c['radius'])
        x, y = tx + rad * math.sin(th), ty - rad * math.cos(th)
        key = c['keys'][rng.integers(len(c['keys']))]
        sc = rng.uniform(*c['scale'])
        z = rng.uniform(*c['z'])
        # rise out of the cloud sea (blend with vertical) and bend into the wound
        tgt = np.array((tx + rng.uniform(*c['aim_x']), ty, rng.uniform(*c['aim_z'])))
        d = tgt - np.array((x, y, z)); d /= np.linalg.norm(d)
        rc = rng.uniform(*c['reach'])
        d = (1 - rc) * np.array((0.0, 0.0, 1.0)) + rc * d
        aim = tuple(np.array((x, y, z)) + 100.0 * d / np.linalg.norm(d))
        jit = float(rng.uniform(-25, 25))
        if visible_length_px(key, (x, y, z), sc, 1.0, None, g, aim=aim, jitter=jit) < c.get('min_px_key', {}).get(key, c['min_px']):
            continue
        dx, dy = x - g['cam'][0], y - g['cam'][1]
        out.append((key, math.degrees(math.atan2(dx, dy)), math.hypot(dx, dy), z, sc, 1.0, None,
                    dict(aim=aim, jitter=jit, layer='mid')))
    return out


def gate_background(g):
    c = g['background']
    rng = np.random.default_rng(c['seed'])
    out, tries = [], 0
    while len(out) < c['n'] and tries < 500:
        tries += 1
        az = rng.uniform(*c['az'])
        if abs(az) < c['clear']:
            continue
        key = c['keys'][rng.integers(len(c['keys']))]
        out.append((key, float(az), float(rng.uniform(*c['dist'])), float(rng.uniform(*c['z'])),
                    float(rng.uniform(*c['scale'])), float(rng.uniform(*c['reach'])), None,
                    dict(mat='colossus', layer='colossus_bg', lod=1, jitter=float(rng.uniform(-30, 30)))))
    return out


def gate_tide(g):
    c = g['tide']
    rng = np.random.default_rng(c['seed'])
    out = []
    for i in range(c['n']):
        az = float(np.clip(rng.normal(0, 30), *c['az']))
        key = c['keys'][rng.integers(len(c['keys']))]
        size = rng.uniform(*c['size'])
        sc = size / centreline(key)['L']
        out.append((key, az, float(rng.uniform(*c['dist'])), float(rng.uniform(*c['z'])), float(sc),
                    float(rng.uniform(*c['reach'])), None, dict(mat='tide', layer='tide', lod=2, jitter=float(rng.uniform(-40, 40)))))
    return out


def gate_camera_basis(g):
    yaw, pitch = math.radians(g['yaw']), math.radians(g['pitch'])
    fwd = np.array([math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
    right = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
    up = np.cross(right, fwd)
    return np.array(g['cam'], float), fwd, right, up


_CL_CACHE = {}


def _variant_cl(key):
    if key not in _CL_CACHE:
        parts, cl = variant_parts(key, 2)
        _CL_CACHE[key] = (parts, cl)
    return _CL_CACHE[key]


def visible_length_px(key, root, scale, reach, roll, g, aim=None, jitter=0.0, W=1920, z_cloud=12.0):
    """Projected length (px at W wide) of the part of an arm that rises above the cloud tops inside the frame."""
    proj, f, Hh = gate_projector(g, W)
    q = gate_rotation(key, root, scale, reach, roll, g, aim=aim, jitter=jitter)
    cl = centreline(key)
    C = cl['P'][::40] @ (np.array(q.to_matrix()) * scale).T + np.array(root)
    S = np.array([proj(p) for p in C])
    vis = (C[:, 2] > z_cloud) & (S[:, 2] > 1) & (S[:, 0] > 0) & (S[:, 0] < W) & (S[:, 1] > 0) & (S[:, 1] < Hh)
    seg = np.linalg.norm(np.diff(S[:, :2], axis=0), axis=1)
    return float(seg[vis[1:] & vis[:-1]].sum())


_GATE_CACHE = {}


def _gate_inst(g):
    key_ = json.dumps({k: g[k] for k in ('cam', 'pitch', 'yaw', 'lens', 'tear', 'polar', 'ring', 'background', 'tide')
                       if k in g}, default=str, sort_keys=True)
    if key_ in _GATE_CACHE:
        return _GATE_CACHE[key_]
    out = []
    rows = list(g['polar']) + (gate_ring(g) if g.get('ring') else []) + \
        (gate_background(g) if g.get('background') else []) + (gate_tide(g) if g.get('tide') else [])
    for row in rows:
        key, az, dist, z, sc, reach, roll = row[:7]
        extra = row[7] if len(row) > 7 else {}
        x, y = _polar_xy(g, az, dist)
        out.append((key, x, y, z, sc, reach, roll, extra))
    _GATE_CACHE[key_] = out
    return out


def _aim_dir(key, root, scale, reach, g, aim=None):
    cam, fwd, right, up = gate_camera_basis(g)
    if aim is not None:
        return Vector((np.array(aim) - np.array(root)).tolist()).normalized()
    tear = np.array(g['tear'])
    Hs = VARIANTS[key]['L'] * scale
    depth = (np.array(root) - cam) @ fwd + 0.35 * Hs
    f = min(depth / ((tear - cam) @ fwd), 1.0)
    target = cam + (tear - cam) * f + np.array([0.0, 0.0, g.get('rise', 0.5) * Hs])   # surge UP toward the rip
    return Vector((0, 0, 1)).lerp(Vector((target - np.array(root)).tolist()).normalized(), reach).normalized()


def gate_rotation(key, root, scale, reach, roll, g, aim=None, jitter=0.0):
    """Quaternion that aims variant `key`'s chord at the camera->tear ray at its own depth (or at
    `aim`), rolled by `roll` about that axis; roll None = auto: the roll whose END (last 12 % of the
    arm) points most nearly at the tear, + jitter."""
    parts, cl = _variant_cl(key)
    ch = Vector((cl['P'][-1] - cl['P'][0]).tolist()).normalized()
    d = _aim_dir(key, root, scale, reach, g, aim)
    q0 = ch.rotation_difference(d)
    if roll is None:
        i = int(0.88 * (len(cl['P']) - 1))
        tipT = Vector((cl['P'][-1] - cl['P'][i]).tolist()).normalized()
        tipP = Vector(cl['P'][-1].tolist())
        tear = Vector(g['tear'])
        best, broll = -9.0, 0.0
        for r_ in range(0, 360, 6):
            q = Quaternion(d, math.radians(r_)) @ q0
            tp = Vector(root) + (q @ tipP) * scale
            s_ = (q @ tipT).dot((tear - tp).normalized())
            if s_ > best:
                best, broll = s_, float(r_)
        roll = broll + jitter
    return Quaternion(d, math.radians(roll)) @ q0


def gate_instances(g=GATE):
    out = []
    for n, (key, x, y, z, sc, reach, roll, extra) in enumerate(_gate_inst(g)):
        q = Quaternion(extra['rot']) if extra.get('rot') is not None else \
            gate_rotation(key, (x, y, z), sc, reach, roll, g, aim=extra.get('aim'), jitter=extra.get('jitter', 0.0))
        out.append(dict(name='Gate_%03d_%s' % (n, key), key=key, loc=(x, y, z), scale=sc, rot=q,
                        lod=extra.get('lod', 0), mat=extra.get('mat', 'default'), flyby=extra.get('flyby', False),
                        layer=extra.get('layer', 'mid')))
    return out


def gate_projector(g, W):
    Hh = W / g['aspect']
    cam, fwd, right, up = gate_camera_basis(g)
    f = g['lens'] / 36.0 * W

    def proj(p):
        d = np.asarray(p, float) - cam
        z = d @ fwd
        return W / 2 + f * (d @ right) / z, Hh / 2 - f * (d @ up) / z, z
    return proj, f, Hh


def plan_gate(path, g=GATE, W=1200):
    """Fast screen-space silhouette plan of the gate (numpy + Pillow): depth-shaded bodies, the tear,
    the moon, the cloud-sea horizon. For composing before any Cycles render."""
    from PIL import ImageDraw
    proj, f, Hh = gate_projector(g, W)
    Hh = int(Hh)
    cam, fwd, right, up = gate_camera_basis(g)
    im = Image.new('RGB', (W, Hh), (7, 10, 20))
    dr = ImageDraw.Draw(im)
    hz = proj(cam + np.array([0, 1e6, -cam[2]]))[1]
    dr.rectangle([0, hz, W, Hh], fill=(55, 62, 86))
    # tear: pointed lens, tilted
    t = np.array(g['tear'])
    h, w = g['tear_h'], g['tear_h'] * g['tear_w']
    tl = math.radians(g.get('tear_tilt', 4.0))
    ax_v = np.array([math.sin(tl), 0, math.cos(tl)])
    ax_u = np.array([math.cos(tl), 0, -math.sin(tl)])
    pts = []
    for s in np.linspace(-1, 1, 60):
        hw = (1 - s * s) ** 1.3
        pts.append(proj(t + ax_v * s * h / 2 + ax_u * hw * w / 2)[:2])
    for s in np.linspace(1, -1, 60):
        hw = (1 - s * s) ** 1.3
        pts.append(proj(t + ax_v * s * h / 2 - ax_u * hw * w / 2)[:2])
    dr.polygon(pts, fill=(230, 200, 255))
    a_, e_ = math.radians(-12.0), math.radians(8.0)            # ART BIBLE v2 moon: -12 / +8 deg from the tear
    mvec = np.array([math.sin(a_) * math.cos(e_), math.cos(a_) * math.cos(e_), math.sin(e_)])
    mx, my, _ = proj(cam + mvec * 1e5)
    rr = f * math.radians(1.3) / 2
    dr.ellipse([mx - rr, my - rr, mx + rr, my + rr], fill=(230, 240, 255))
    items = []
    labels = []
    for it in gate_instances(g):
        parts, cl = _variant_cl(it['key'])
        M = np.array(it['rot'].to_matrix()) * it['scale']
        for p in parts:
            C = p['C'] @ M.T + np.array(it['loc'])
            if p['name'] == 'core' and it['layer'] in ('near', 'colossus'):
                labels.append((C[-1], it['name'][5:]))
            for j in range(len(C)):
                items.append((C[j], p['r'][j] * it['scale']))
            for j in range(len(C) - 1):
                for a in np.linspace(0, 1, 7)[1:-1]:
                    items.append((C[j] * (1 - a) + C[j + 1] * a, (p['r'][j] * (1 - a) + p['r'][j + 1] * a) * it['scale']))
    pts = np.array([i[0] for i in items]); rr = np.array([i[1] for i in items])
    d = pts - cam
    z = d @ fwd
    order = np.argsort(-z)
    for i in order:
        if z[i] < 1 or pts[i][2] < 0:
            continue
        x = W / 2 + f * (d[i] @ right) / z[i]
        y = Hh / 2 - f * (d[i] @ up) / z[i]
        r = max(f * rr[i] / z[i], 0.5)
        dd_ = np.linalg.norm(d[i])
        fog = 1 - math.exp(-dd_ * 0.0006)
        if dd_ > 1500:
            fog = min(fog, 0.6) * math.exp(-max(pts[i][2], 0) / 500.0) if dd_ < 4500 else min(fog, 0.92)
        c = np.array([12, 13, 18]) * (1 - fog) + np.array([72, 77, 99]) * fog
        dr.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(v) for v in c))
    for P, name in labels:
        x, y, zz = proj(P)
        if zz > 1:
            dr.text((x + 3, y - 10), name, fill=(255, 220, 90))
    im.save(path)
    print('plan', path)


# ---------------------------------------------------------------------------------------------
# aerial perspective shared by every staging material (tentacles have the same block inline)
# ---------------------------------------------------------------------------------------------
def _fog_nodes(nt, fg, density_scale=1.0, use_height=True):
    """(fog factor, fog colour) sockets for staging materials (cloud cards, cloud sea): LanbaiFog band
    colour, exponential density (+ the low extra density), no cap (the cap is for far tentacles)."""
    cam = nt.nodes.new('ShaderNodeCameraData')
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sp.inputs[0])
    fg = dict(FOG, **fg)
    if not use_height:
        fg['extra'] = 0.0
    f = _fog_factor(nt, fg, cam.outputs['View Distance'], sp.outputs['Z'], density_scale, cap=1.0, cap_h=False)
    view = nt.nodes.new('ShaderNodeVectorMath'); view.operation = 'SCALE'; view.inputs['Scale'].default_value = -1.0
    nt.links.new(geo.outputs['Incoming'], view.inputs[0])
    return f, _band_colour(nt, view.outputs[0], fg)


def add_moon_disc(k, to_moon):
    """The rig's v2 world (luminous haze band round the tear, void above 35 deg, sparse stars) + the moon
    itself, camera rays only: a 1.2 deg disc with faint maria and a small silver halo (#5A6A88).
    The rig's sun lamp does the lighting."""
    w = bpy.context.scene.world
    nt = w.node_tree
    N, L = nt.nodes.new, nt.links.new
    bg = [n for n in nt.nodes if n.type == 'BACKGROUND'][0]
    src_sock = bg.inputs['Color'].links[0].from_socket
    tc = [n for n in nt.nodes if n.type == 'TEX_COORD'][0]
    d = tc.outputs['Generated']                  # the ray direction (world shaders: 'Normal' points back)

    def mathn(op, a, b=None):
        n = N('ShaderNodeMath'); n.operation = op
        for i, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    dm = N('ShaderNodeVectorMath'); dm.operation = 'DOT_PRODUCT'; L(d, dm.inputs[0]); dm.inputs[1].default_value = tuple(to_moon)
    cm = mathn('MAXIMUM', dm.outputs['Value'], 0.0)
    halo_w = mathn('ADD', mathn('MULTIPLY', mathn('POWER', cm, 300.0), k['moon_halo'][0]),
                   mathn('MULTIPLY', mathn('POWER', cm, 3000.0), k['moon_halo'][1]))
    gain = k.get('sky_gain', 1.0)
    halo = N('ShaderNodeVectorMath'); halo.operation = 'SCALE'
    halo.inputs[0].default_value = tuple(c / gain for c in k['moon_halo_col'])
    L(halo_w, halo.inputs['Scale'])
    cr = math.cos(math.radians(k['moon_disc_deg'] / 2))
    cr2 = math.cos(math.radians(k['moon_disc_deg'] / 2 * 0.86))
    disc = N('ShaderNodeMapRange'); disc.clamp = True; disc.interpolation_type = 'SMOOTHSTEP'
    disc.inputs['From Min'].default_value = cr; disc.inputs['From Max'].default_value = cr2
    L(dm.outputs['Value'], disc.inputs['Value'])
    nz = N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900.0; nz.inputs['Detail'].default_value = 3.0
    L(d, nz.inputs['Vector'])
    maria = mathn('ADD', 0.80, mathn('MULTIPLY', mathn('SUBTRACT', nz.outputs['Fac'], 0.5), 0.5))
    dcol = N('ShaderNodeVectorMath'); dcol.operation = 'SCALE'
    dcol.inputs[0].default_value = tuple(c / gain for c in k['moon_disc_col'])
    L(mathn('MULTIPLY', disc.outputs['Result'], maria), dcol.inputs['Scale'])
    ex = N('ShaderNodeVectorMath'); ex.operation = 'ADD'; L(halo.outputs[0], ex.inputs[0]); L(dcol.outputs[0], ex.inputs[1])
    lp = N('ShaderNodeLightPath')
    exc = N('ShaderNodeVectorMath'); exc.operation = 'SCALE'; L(ex.outputs[0], exc.inputs[0]); L(lp.outputs['Is Camera Ray'], exc.inputs['Scale'])
    tot = N('ShaderNodeVectorMath'); tot.operation = 'ADD'; L(src_sock, tot.inputs[0]); L(exc.outputs[0], tot.inputs[1])
    L(tot.outputs[0], bg.inputs['Color'])
    # camera rays see the sky x sky_gain (preview calibration: the band must READ #484D63 -> #2A3041 on
    # screen after AgX + S4, like the bible's fill values do in Unity); other rays keep sky_light
    gain = k.get('sky_gain', 1.0)
    strength = mathn('ADD', mathn('MULTIPLY', lp.outputs['Is Camera Ray'], gain - k['sky_light']), k['sky_light'])
    L(strength, bg.inputs['Strength'])


def light_separately(ob, lights):
    """Exclude `ob` from the rig's lights and light it with scaled copies ({rig light name: scale}).
    The rig is tuned to rim near-black bodies; bright clouds / haze need far less light."""
    name = ob.name
    ex = bpy.data.collections.new('LL_Ex_' + name)
    ex.objects.link(ob)
    inc = bpy.data.collections.new('LL_In_' + name)
    inc.objects.link(ob)
    ex.collection_objects[0].light_linking.link_state = 'EXCLUDE'
    for n, k in lights.items():
        src = bpy.data.objects.get(n)
        if src is None:
            continue
        rc = src.light_linking.receiver_collection
        if rc is None:
            src.light_linking.receiver_collection = ex
        elif ob.name not in rc.objects:
            rc.objects.link(ob)
            for co in rc.collection_objects:
                co.light_linking.link_state = 'EXCLUDE'
        if k > 0:
            ld = src.data.copy()
            ld.energy = src.data.energy * k
            lo = bpy.data.objects.new('ST_%s_%s' % (n, name), ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.matrix_world = src.matrix_world
            lo.light_linking.receiver_collection = inc
    return inc


GATE_LOOK = dict(
    # ART BIBLE v2 lights: the rig's moon (sun, #D6E4FF, -12 / +8 deg from the tear) and tear light
    # (shadowless sun from the tear toward the bus, #A99DE1, E = 0.8 x moon) + the fill from below.
    tear_strength=18.0, tear_light=1.0, moon_energy=4.0, fill_energy=0.96,      # fill = bible E 0.24 x moon
    moon_disc_deg=1.2, moon_disc_col=(2.6, 2.8, 3.1), moon_halo=(0.25, 1.2), moon_halo_col=_hex_lin('#5A6A88'),
    fog=None, cloud_fog_scale=0.55,
    sea_albedo=0.55, sea_moon=0.35, sea_tear=0.25, exposure=-0.5, letterbox=True,
    rays=dict(strength=0.20, decay=0.975, n=90, span=0.62, thr=0.62, colour=(0.42, 0.44, 0.72), window=0.28),
    cloud_gain=0.62, cloud_rim=0.45, cloud_top=0.4, sea_rows=False, sea_mist=0.18, cloud_top_z=8.0,
    # per-layer LanbaiFog knobs (Unity: _FogDensityScale / _FogCapHeight on the layer's material):
    # the mid ring's crowns must stay DARK in front of the bright haze (L* 10-16) while the colossi's
    # crowns sit 35-45 % in the fog (L* 18-26): heads clear, feet dissolving
    fog_layers=dict(default=dict(density_scale=0.25), colossus=dict(cap_h=1600.0)),
    sky_gain=1.9, sky_light=1.9, field=True, field_albedo=0.6, field_translucency=0.45, field_sheen=0.25,
    field_spill=0.6, field_fog_scale=1.0, field_moon=0.8, field_tear=0.35, field_glow=0.3, field_bump=0.35,
    field_ms=0.12, field_soft=0.45, field_fbm=1.0, tide_impostors=True,
    grade=1.0, window=True)


def shot_gate(res, samples, out, g=None, look=None, only=None, fly=None):
    """The key art (ART BIBLE v2 §6·4, U7): from the bus 50 m above the cloud sea, through the
    windscreen, at the tear. With `fly`, the same gate from a camera riding beside one of its arms."""
    import preview_rig as pr
    global CLOUD_GLOSSY_DIM
    g = dict(GATE, **(g or {}))
    k = dict(GATE_LOOK, **(look or {}))
    CLOUD_GLOSSY_DIM = k.get('cloud_glossy_dim', 0.65)
    W = res[0]
    Hl = int(round(W / g['aspect'])) if k['letterbox'] else res[1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = pr.setup(samples=samples, res=(W, Hl))            # v2 world (haze band) + moon + fill
    sc.view_settings.exposure = k['exposure']
    sc.cycles.transparent_max_bounces = 64
    cam_p, fwd, right, up = gate_camera_basis(g)
    cam = pr.frame_subject(center=(0, 100, 50), size=10, lens=g['lens'])
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.clip_end = 60000
    lens = g['lens']
    insts = gate_instances(g)
    if fly:
        it = [i for i in insts if (i['name'] == fly['inst'] if fly.get('inst') else i['flyby'])][0]
        mw = Matrix.Translation(it['loc']) @ it['rot'].to_matrix().to_4x4() @ Matrix.Scale(it['scale'], 4)
        P, T, r = body_frame(it['key'], fly['u'], mw)
        if fly.get('cam') is not None:          # from the bus: a seat by the window, looking yaw / pitch
            cam.location = Vector(g['cam']) + Vector(fly['cam'])
            yw, pt = math.radians(fly['yaw']), math.radians(fly['pitch'])
            aim = cam.location + Vector((math.sin(yw) * math.cos(pt), math.cos(yw) * math.cos(pt), math.sin(pt))) * 100.0
        else:
            D = Vector(fly['cam_dir']) if fly.get('cam_dir') != 'gate' else (Vector(g['cam']) - P).normalized()
            if fly.get('cam_turn'):
                D = Matrix.Rotation(math.radians(fly['cam_turn']), 3, T) @ D
            D = (D - D.dot(T) * T).normalized()
            cam.location = P + D * (r + fly['dist']) - T * fly['back'] + Vector((0, 0, fly.get('lift', 0.0)))
            tv = (Vector(g['tear']) - cam.location).normalized()
            av = (P + T * 25.0 - cam.location).normalized()
            tv = (tv * (1 - fly.get('look_mix', 0.0)) + av * fly.get('look_mix', 0.0)).normalized()
            aim = cam.location + tv * 100.0 + Vector((0, 0, fly.get('aim_up', 0.0)))
        qc = (aim - cam.location).to_track_quat('-Z', 'Y')              # horizon level
        qc = qc @ Matrix.Rotation(math.radians(fly.get('roll', 0.0)), 4, 'Z').to_quaternion()
        cam.rotation_euler = qc.to_euler()
        lens = fly['lens']
        bpy.context.view_layer.update()
        M = cam.matrix_world.to_3x3()
        fwd, right, up = np.array(-M.col[2]), np.array(M.col[0]), np.array(M.col[1])
        k['fly_body'] = (P, r, T, it['name'])
        if fly.get('blur_m'):        # the bus is moving: real camera motion blur (near arm streaks, far stays sharp)
            sc.render.use_motion_blur = True
            sc.render.motion_blur_shutter = 0.5
            mv = Vector((0.0, 1.0, 0.0)) * fly['blur_m'] * 2.0
            cam.location = cam.location - mv * 0.5
            cam.keyframe_insert('location', frame=1)
            cam.location = cam.location + mv
            cam.keyframe_insert('location', frame=2)
            sc.frame_set(1)
    else:
        cam.location = Vector(cam_p.tolist())
        cam.rotation_euler = Vector(fwd.tolist()).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    moon = bpy.data.objects['PR_Moon']
    moon.data.energy = k['moon_energy']
    if k.get('moon_angle'):
        moon.data.angle = math.radians(k['moon_angle'])
    if k.get('fill_energy') is not None:
        bpy.data.objects['PR_Fill'].data.energy = k['fill_energy']
    if k.get('fill_angle'):          # the cloud-sea bounce is a huge soft source: a wide sun -> broad wet sheen
        bpy.data.objects['PR_Fill'].data.angle = math.radians(k['fill_angle'])
    to_moon = pr._dir_from(pr.MOON_AZ, pr.MOON_EL)
    add_moon_disc(k, to_moon)
    tear = Vector(g['tear'])
    fg = dict(FOG, **(k.get('fog') or {}))
    for c_ in ('near', 'far', 'void'):                     # fog colour = the sky exactly as the camera sees it
        fg[c_] = tuple(v * k.get('sky_gain', 1.0) for v in fg[c_])
    tex_dir = os.path.join(OUT, 'Textures')
    mats = {}

    def mat_for(key, kind):
        if (key, kind) not in mats:
            fgk = dict(fg, **(k.get('fog_layers') or {}).get(kind, {}))
            mats[(key, kind)] = make_material('M_Tentacle_%s%s' % (key, '' if kind == 'default' else '_' + kind),
                                              pix_angle=36.0 / lens / W, rim_dir=to_moon, fog=fgk, tear_pos=tuple(tear),
                                              rim=k.get('rim'),
                                              occl=os.path.join(tex_dir, 'T_Tentacle_%s_Occlusion.png' % key),
                                              colossus=kind == 'colossus', tide=kind == 'tide')
        return mats[(key, kind)]
    cache = {}
    for it in insts:
        if only and it['key'] not in only:
            continue
        if it['layer'] == 'tide' and k.get('tide_impostors'):
            continue                                    # the far tide = the Lanbai/TentacleTide billboards
        instance(it['key'], cache, mat_for(it['key'], it['mat']), it['loc'], it['rot'], it['scale'], name=it['name'],
                 lod=it['lod'])
    if k.get('tide_impostors'):
        add_tide_billboards(g, fg, tex_dir, tuple(cam.location))
    # the tear (v2 rig): undyed-white asymmetric lens, pale lips, dusk indigo-violet halo; its light is a
    # shadowless sun from the tear toward the bus (E 0.8 x moon) + a soft local glow
    slit = pr.add_tear(center=tear - Vector((0, 10.0, 0)), height=g['tear_h'], width=g['tear_h'] * g['tear_w'],
                       distance_behind=10.0, strength=k['tear_strength'])
    bpy.data.objects['PR_TearLight'].data.energy *= k['tear_light']
    if fly:
        P, r, T, nm = k['fly_body']
        ob = bpy.data.objects.get(nm)
        if ob:
            dmin = min((ob.matrix_world @ v.co - cam.location).length for v in ob.data.vertices)
            print('flyby: nearest surface vertex %.1f m, body radius %.2f m' % (dmin, r))
    sea = add_cloud_sea(-14.0 if k.get('field') else 0.0, fog=fg, albedo=k['sea_albedo'])
    if k.get('field'):
        k['_tear_pos'] = tuple(tear)
        fld = add_cloud_field(cam.location, math.degrees(math.atan2(fwd[0], fwd[1])), fg, k)
        light_separately(fld, {'PR_Moon': k['field_moon'], 'PR_TearLight': k['field_tear'], 'PR_Fill': 0.0,
                               'PR_TearGlow': k.get('field_glow', 1.0)})
    if k.get('clouds', True):
        add_gate_clouds(g, fg, k, to_moon, cam.location, right, up, fwd_yaw=math.degrees(math.atan2(fwd[0], fwd[1])),
                        cards=GATE_CLOUDS + list(k.get('extra_clouds', [])))
    light_separately(sea, {'PR_Moon': k['sea_moon'], 'PR_TearLight': k['sea_tear'], 'PR_Fill': 0.0, 'PR_TearGlow': 0.0})
    for lo_ in [o_ for o_ in bpy.data.objects if o_.name.startswith('ST_PR_') and o_.name.endswith('ST_CloudSea')]:
        try:
            lo_.data.use_shadow = False
        except AttributeError:
            pass
    for m_ in mats.values():
        aim_material(m_, to_moon=to_moon, tear_pos=tuple(tear))
    if k.get('border'):              # test renders: only a region of the frame (xmin, xmax, ymin, ymax; 0..1 from bottom-left)
        sc.render.use_border = True
        sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = k['border']
    raw = out if not k['letterbox'] else out.replace('.png', '_raw.png')
    pr.render(raw)
    if k.get('rays'):
        from bpy_extras.object_utils import world_to_camera_view
        c2 = world_to_camera_view(sc, cam, tear)
        god_rays(raw, c2.x, 1.0 - c2.y, **k['rays'])
    if k.get('grade', 1.0) > 0:
        cinematic_grade(raw, k.get('grade', 1.0))
    if k.get('window'):
        bus_window(raw, **(k.get('window_kw') or {}))
    if k['letterbox']:
        im = Image.open(raw).convert('RGB')
        H = int(round(W * 9 / 16))
        canvas = Image.new('RGB', (W, H), (0, 0, 0))
        canvas.paste(im, (0, (H - im.height) // 2))
        canvas.save(out)
        os.remove(raw)
    return out


def god_rays(path, cx, cy, strength=0.3, decay=0.97, n=80, span=0.6, thr=0.5, colour=(0.6, 0.36, 1.0), window=0.3):
    """Light pouring BETWEEN the arms: occlusion-aware screen-space light shafts (GPU Gems 3 style).
    The bright pixels of the rip (cut by every silhouette in front of it) are smeared radially away
    from the rip centre (cx, cy in 0..1), so each arm and fibre in front of the light
    casts a dark shaft and the light streams through the gaps. Preview look target; Unity: 6-10
    additive shaft cards or a screen-space shafts effect (README 7)."""
    from scipy.ndimage import map_coordinates, zoom
    im = np.asarray(Image.open(path).convert('RGB')).astype(np.float64) / 255.0
    H, W = im.shape[:2]
    s = 2
    sm = im[::s, ::s]
    h, w = sm.shape[:2]
    lum = sm @ np.array([0.2126, 0.7152, 0.0722])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    px, py = cx * w, cy * h
    rr = np.hypot((xx - px) / w, (yy - py) / w)
    mask = _smoothstep(thr, 0.95, lum) * np.exp(-(rr / window) ** 2)
    acc = np.zeros((h, w))
    wsum = 0.0
    for i in range(n):
        f = 1.0 - span * i / n
        wgt = decay ** i
        acc += wgt * map_coordinates(mask, [py + (yy - py) * f, px + (xx - px) * f], order=1, mode='constant')
        wsum += wgt
    acc /= wsum
    acc = zoom(acc, (H / h, W / w), order=1)[:H, :W]
    im = 1 - (1 - im) * (1 - strength * acc[..., None] * np.array(colour))      # screen blend
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)
    return path


def cinematic_grade(path, strength=1.0, vignette=0.22, grain=0.010, seed=3, bloom=(0.80, 0.30, 0.012, 0.004)):
    """ART BIBLE v2 grade S4, applied display-referred in numpy as a preview of the PPv2 profile:
    saturation -10, contrast +16 (S-curve about 0.35), temperature -6 / tint +2 (cooler, a hair
    magenta), lift 0.006, gamma (0.98, 0.98, 1), bloom from ~0.8 display (threshold 1.93 / T0 2.12 in
    scene terms) so only the tear core glows, soft vignette, fine grain. Unity: LUT Lanbai_S4_04_gate."""
    from scipy.ndimage import gaussian_filter
    im = np.asarray(Image.open(path).convert('RGB')).astype(np.float64) / 255.0
    H, W = im.shape[:2]
    thr, amt, s1, s2 = bloom
    lum = im @ np.array([0.2126, 0.7152, 0.0722])
    hot = np.clip(im - thr, 0, None) / (1 - thr)
    bl = sum(np.stack([gaussian_filter(hot[..., c], s * W) for c in range(3)], -1) for s in (s1, s2)) * 0.5
    im = im + strength * amt * bl
    lum = im @ np.array([0.2126, 0.7152, 0.0722])
    im = lum[..., None] + (im - lum[..., None]) * (1 - 0.10 * strength)            # saturation -10
    pivot = 0.35
    span = np.where(im < pivot, pivot, 1 - pivot)
    im = im + strength * 0.16 * (im - pivot) * np.clip(1 - ((im - pivot) / span) ** 2, 0, 1)     # contrast +16
    im = im * (1 + strength * np.array([-0.018, -0.004, 0.022]))                   # temp -6, tint +2
    im = np.clip(im, 0, 1) ** (1 / np.array([0.98, 0.98, 1.0]))                     # gamma
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) / math.sqrt(2)
    im = im * (1 - vignette * strength * np.clip(r - 0.35, 0, 1) ** 1.6 / 0.65 ** 1.6)[..., None]
    # lift (0.99, 0.99, 1, 0.006): PPv2 adds it in LINEAR light before the tonemapper, so the black floor
    # becomes a faint blue-black (~L* 5, the bible's near-body #0F1116), not a display offset of 1.5/255
    lin = srgb2lin(np.clip(im, 0, 1))
    lin = lin + strength * np.array([0.0056, 0.0058, 0.0080]) * (1 - lin)
    im = lin2srgb(np.clip(lin, 0, 1))
    g = np.random.default_rng(seed).normal(0, 1, (H, W))
    im = im + (grain * strength * (0.4 + 0.6 * np.sin(np.pi * np.clip(lum, 0, 1))))[..., None] * g[..., None]
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)
    return path


def bus_window(path, seed=5, pillar='right', n_drops=0, streaks=0, pillar_w=0.040, header=0.0, drop_scale=1.0,
               warm=0.12):
    """Post pass: we are INSIDE the bus. A soft, out-of-focus window pillar at the frame edge with a
    warm glint of the cabin tubes on its inner edge, and rain left on the glass from the stop: small
    drops (each a tiny inverted lens of the scene, dark rim, cold glint) and a few wind-driven trails.
    Scale cue + point of view. Unity: the bus model's real window frame + a rain-on-glass decal."""
    from scipy.ndimage import gaussian_filter, map_coordinates
    im = np.asarray(Image.open(path).convert('RGB')).astype(np.float64) / 255.0
    H, W = im.shape[:2]
    rng = np.random.default_rng(seed)
    s = W / 1920.0
    blur = np.stack([gaussian_filter(im[..., c], 7 * s) for c in range(3)], -1)
    over = np.zeros((H, W, 3))
    alpha = np.zeros((H, W))
    yy, xx = np.mgrid[0:H, 0:W]

    def drop(cx, cy, r, k=3.2, bright=1.3):
        x0, x1 = int(max(cx - r - 2, 0)), int(min(cx + r + 3, W))
        y0, y1 = int(max(cy - r * 1.1 - 2, 0)), int(min(cy + r * 1.1 + 3, H))
        if x1 <= x0 or y1 <= y0:
            return
        X, Y = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]
        dx, dy = (X - cx) / r, (Y - cy) / (r * 1.06)
        rr = np.sqrt(dx * dx + dy * dy)
        a = np.clip((1.0 - rr) * r * 0.5, 0, 1) * 0.8
        # inverted, wide-angle view through the drop
        sx = np.clip(cx - dx * r * k, 0, W - 1)
        sy = np.clip(cy - dy * r * k * 0.9 - r * 1.5, 0, H - 1)
        c = np.stack([map_coordinates(blur[..., ch], [sy, sx], order=1) for ch in range(3)], -1) * bright
        ring = np.clip((rr - 0.62) / 0.38, 0, 1) ** 1.5
        c = c * (1 - 0.30 * ring)[..., None] + 0.10 * np.clip(1 - np.abs(rr - 0.8) / 0.15, 0, 1)[..., None] * \
            np.clip(dy, 0, 1)[..., None] * c                          # light gathered on the lower rim
        # glints: cold (the moon side, upper left), warm (cabin light, lower right)
        g1 = np.exp(-(((dx + 0.38) ** 2 + (dy + 0.40) ** 2) / 0.018))
        g2 = np.exp(-(((dx - 0.40) ** 2 + (dy - 0.42) ** 2) / 0.03))
        c = c + g1[..., None] * np.array([0.55, 0.62, 0.75]) * 0.12 + g2[..., None] * np.array([0.9, 0.55, 0.28]) * warm * 0.2
        o = over[y0:y1, x0:x1]
        al = alpha[y0:y1, x0:x1]
        o[:] = o * (1 - a[..., None]) + c * a[..., None]
        al[:] = np.maximum(al, a)

    for i in range(n_drops):
        r = drop_scale * s * float(np.clip(rng.lognormal(math.log(6.0), 0.45), 3.0, 16.0))
        cx = rng.uniform(0, W)
        cy = rng.uniform(0, H)
        drop(cx, cy, r)
    for i in range(streaks):           # wind-driven trails: a head drop and a thinning tail
        cx, cy = rng.uniform(0.1 * W, 0.9 * W), rng.uniform(0.05 * H, 0.7 * H)
        ang = math.radians(rng.uniform(15, 35)) * (1 if rng.random() < 0.5 else -1)
        ln = rng.uniform(40, 120) * s
        r0 = rng.uniform(3.5, 6.0) * s * drop_scale
        for j in range(int(ln / (1.2 * s))):
            f_ = j / (ln / (1.2 * s))
            drop(cx - math.sin(ang) * f_ * ln, cy - math.cos(ang) * f_ * ln, max(r0 * (1 - 0.8 * f_), 0.9 * s), k=2.0, bright=1.05)
    over = np.stack([gaussian_filter(over[..., c], 1.4 * s) for c in range(3)], -1)
    alpha = gaussian_filter(alpha, 1.4 * s) * 0.8
    im = im * (1 - alpha[..., None]) + over * alpha[..., None]
    # the pillar (out of focus, just inside the frame edge) with a warm glint on its inner edge
    if pillar:
        edge = W * (1 - pillar_w) if pillar == 'right' else W * pillar_w
        tilt = 0.035 * W
        e_y = edge + tilt * (yy / H - 0.5) * (1 if pillar == 'right' else -1)
        dist = (xx - e_y) if pillar == 'right' else (e_y - xx)
        soft = 14 * s
        pm = 1 / (1 + np.exp(-dist / soft))
        glint = np.exp(-((dist + 10 * s) / (12 * s)) ** 2) * (0.5 + 0.5 * np.sin(yy / H * 3.1 + 0.4)) ** 2
        pillar_col = np.array([0.012, 0.012, 0.018])
        im = im * (1 - pm[..., None]) + pillar_col * pm[..., None]
        im = im + glint[..., None] * np.array([1.0, 0.62, 0.32]) * warm * 0.35
    if header > 0:
        hm = 1 / (1 + np.exp(-((header * H) - yy) / (10 * s)))
        im = im * (1 - hm[..., None]) + np.array([0.010, 0.010, 0.015]) * hm[..., None]
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)
    return path


# THE FLYBY (ART BIBLE v2 §6·4, U8 *Ach nein!*): the bus, 40-60 m above the cloud sea, passes 14-18 m under
# the crest of an F arm that rises out of the clouds on the right and arcs over the roof toward the tear,
# pouring its whip down ahead on the left. We see its underside -- the concave, compressed side of the
# bend (the only place the skin creases) -- under the cold moon rim and the cloud-sea bounce, and beyond
# it a small ring of mid arms round the rip's foot and two colossi in the haze. Its own composition
# (the gate composition belongs to the gate stage); same staging code as gate.png.
FLY = dict(key='F', scale=1.10, u=0.62, clear=16.0, behind=72.0, off_az=-150.0, reach_az=-30.0, lean=-28.0,
           root_z=-30.0, yaw=28.0, pitch=19.0, lens=18.0, blur_m=0.30,
           ring=None,
           # (variant, azimuth, distance m, root z, scale, reach, fog layer): hand-placed in front of the haze band
           # (the band spans +-50-60 deg round the tear; beyond it the void would swallow a dark arm)
           # (at the bible's colossus distances, 1.3-4 km, an 18 mm frame shrinks a 450 m colossus to a grey spike on
           # the clouds -- the rejected 'sprout' read -- so this shot keeps the near arm alone; see gate.png for the crowd)
           extras=[])
FLY_LOOK = dict(letterbox=False, moon_energy=4.0, moon_angle=5.0, tear_light=0.8, cloud_glossy_dim=0.2,
                fill_angle=80.0, field_fog_scale=2.5, field_ms=0.20,
                # wisps drifting over the near cloud sea (the delivered volumetric moon cards; rows as GATE_CLOUDS)
                extra_clouds=[('Cloud_Wisp_moon', 5.0, 520.0, -60.0, 700.0, 0.75, False),
                              ('Cloud_Strato_moon', 40.0, 620.0, -70.0, 900.0, 0.70, True),
                              ('Cloud_Wisp_moon', 58.0, 380.0, -45.0, 520.0, 0.65, True),
                              ('Cloud_Strato_moon', -20.0, 700.0, -70.0, 900.0, 0.70, False)],
                window_kw=dict(pillar='left', pillar_w=0.030, seed=9, n_drops=9, streaks=2, drop_scale=1.9))


def flyby_hero(fly, g=GATE):
    """Place the hero arm so that the bus sits `clear` m from its surface at arc fraction u, on the
    CONCAVE side of the bend but `behind` deg back from the bend's centre toward -Y (away from the tear),
    so the crest arcs over the roof just ahead of the bus. The root goes under the cloud sea at root_z and
    the bus height follows (bible 40-60 m). Returns (polar row, camera position)."""
    key, sc = fly['key'], fly['scale']
    cl = centreline(key)
    sp = VARIANTS[key]
    i = int(np.clip(np.searchsorted(cl['u'], fly['u']), 1, len(cl['u']) - 2))
    P = cl['P'][i]
    kv = np.gradient(cl['T'], cl['s'], axis=0)[i]
    kh = kv / (np.linalg.norm(kv) + 1e-12)                            # toward the centre of the bend
    r = float(sp['R'] * radius_profile(fly['u'], sp.get('heavy', 1.0), (sp['phase'] * 7.3) % 1.0)) * sc
    th = math.radians(fly['reach_az'])
    qz = Quaternion((0, 0, 1), math.pi - th)          # local reach (-Y) -> world azimuth reach_az (0 = +Y, - = left)
    q = Quaternion(qz @ Vector((0, -1, 0)), math.radians(fly.get('lean', 0.0))) @ qz
    Pw = q @ Vector((P * sc).tolist())
    khw = q @ Vector(kh.tolist())
    b = math.radians(fly.get('behind', 50.0))
    oa = math.radians(fly.get('off_az', 180.0))                      # horizontal offset direction (180 = back)
    dirw = (khw * math.cos(b) + Vector((math.sin(oa), math.cos(oa), 0.0)) * math.sin(b)).normalized()
    Cw = Pw + dirw * (r + fly['clear'])
    cam = Vector((g['cam'][0], g['cam'][1], fly['root_z'] + Cw.z))
    root = cam - Cw
    dx, dy = root.x - g['cam'][0], root.y - g['cam'][1]
    row = (key, math.degrees(math.atan2(dx, dy)), math.hypot(dx, dy), root.z, sc, 1.0, 0.0,
           dict(rot=tuple(q), layer='near', flyby=True))
    return row, cam


def shot_flyby(res, samples, out, fly=None, look=None):
    """The bus passing 14-18 m under the crest of an F arm (see FLY): the skin of its compressed underside
    under the cold rim, the whip pouring down toward the rip, a ring of mid arms and two colossi beyond."""
    fly = dict(FLY, **(fly or {}))
    row, cam = flyby_hero(fly)
    print('flyby: bus at z %.1f m above the cloud-sea top (bible 40-60)' % cam.z)
    rows = [row] + [(k_, az, d_, z_, s_, rc, None, dict(mat=m_, layer='colossus'))
                    for (k_, az, d_, z_, s_, rc, m_) in fly['extras']]
    g = dict(GATE, polar=rows, ring=fly['ring'], background=None, tide=GATE['tide'])
    fcam = dict(inst=None, cam=(0.0, 0.0, cam.z - GATE['cam'][2]), yaw=fly['yaw'], pitch=fly['pitch'],
                roll=0.0, lens=fly['lens'], blur_m=fly.get('blur_m'), u=fly['u'])
    return shot_gate(res, samples, out, g=g, fly=fcam, look=dict(FLY_LOOK, **(look or {})))


# ---------------------------------------------------------------------------------------------
# cloud cards (the delivered moon-preset cards of the cloud workshop, used the way Unity will:
# unlit alpha-blended billboards, mirrored so their baked moon matches this scene's moon)
# ---------------------------------------------------------------------------------------------
CLOUD_DIR = os.path.abspath(os.path.join(OUT, '..', 'Clouds'))
CLOUD_GLOSSY_DIM = 0.65      # clouds seen in the arms' wet reflections are dimmed by this (look key cloud_glossy_dim)
# (card, azimuth deg, distance m, base z, width m, brightness, mirror)
GATE_CLOUDS = [
    # towering cumulus and banks far behind the gate (scale for the colossi; mostly swallowed by the haze)
    ('Cloud_Congestus_moon', -34.0, 7500.0, -600.0, 3800.0, 0.55, True),
    ('Cloud_Congestus_moon', 33.0, 8200.0, -620.0, 3400.0, 0.50, False),
    ('Cloud_Bank_moon', -16.0, 6200.0, -340.0, 5400.0, 0.55, True),
    ('Cloud_Bank_moon', 19.0, 5800.0, -320.0, 5000.0, 0.55, True),
    # the cloud-sea horizon
    ('CloudSea_1_moon', -26.0, 4200.0, -700.0, 6000.0, 0.75, True),
    ('CloudSea_2_moon', 24.0, 4000.0, -690.0, 6000.0, 0.75, True),
    ('CloudSea_1_moon', 1.0, 4500.0, -720.0, 5600.0, 0.75, False),
    # wisps in front of the colossi's roots (feet dissolving)
    ('Cloud_Wisp_moon', -17.0, 1720.0, -170.0, 1100.0, 0.80, False),     # colossus 2
    ('Cloud_Wisp_moon', 13.0, 1350.0, -160.0, 900.0, 0.80, True),        # colossus 3
    ('Cloud_Strato_moon', 24.0, 3000.0, -300.0, 2200.0, 0.80, True),     # colossus 1
    ('Cloud_Strato_moon', -34.0, 2600.0, -290.0, 2400.0, 0.80, True),
    ('Cloud_Strato_moon', 36.0, 2400.0, -280.0, 2200.0, 0.80, True),
]


def cloud_sea_rows(g, rows=((240.0, 3), (330.0, 3), (460.0, 3), (640.0, 4), (880.0, 4), (1220.0, 4), (1700.0, 4),
                                (2400.0, 4), (3300.0, 4)), top_z=8.0, az_span=46.0, seed=21):
    """The sea of clouds as a receding field: rows of the delivered cloud-sea strip cards (volumetric
    renders) at growing distance, each ~1:1 texel on screen, their tops just under eye level, so the
    plain recedes to the horizon in layers (and hides the roots). Returns GATE_CLOUDS-style rows."""
    rng = np.random.default_rng(seed)
    out = []
    for ri, (d, n) in enumerate(rows):
        w = 2 * d * math.tan(math.radians(az_span)) / n * 1.8
        for j in range(n):
            az = -az_span + (j + 0.5) * 2 * az_span / n + rng.uniform(-4, 4)
            card = 'CloudSea_1_moon' if (ri + j) % 2 else 'CloudSea_2_moon'
            base = top_z + rng.uniform(-4, 6) - 0.145 * w
            # back-lit: the near cloud tops show us their shadowed side; they brighten toward the horizon
            out.append((card, float(az), d * rng.uniform(0.96, 1.04), float(base), float(w),
                        0.22 + 0.46 * ri / (len(rows) - 1), bool((ri + j) % 3 == 0)))
    return out


def _cloud_meta():
    try:
        return json.load(open(os.path.join(CLOUD_DIR, 'clouds_meta.json')))
    except Exception:
        return {}


def add_cloud_card(name, card, loc, width, face_to, brightness=1.0, mirror=False, tint=(1, 1, 1),
                   fog=None, meta=None, moon_screen=None, rim=0.0, top=0.0, fog_scale=1.0, feather=0.0, mist=0.0,
                   tear_tint=None):
    """tear_tint = (tint rgb, extra brightness, tear direction from the camera, power): the violet spill
    near the rip is evaluated PER PIXEL from the view direction (per-card tints left seams where cards overlap)."""
    """Vertical billboard facing `face_to` (yaw only), straight-alpha PNG, unlit (emission).
    rim_uv = direction toward the moon in the card's UV space: the cloud's edges that face the moon
    get a silver lining (alpha gradient toward the moon), and its moonlit tops are lifted (`top`)."""
    path = os.path.join(CLOUD_DIR, card + '.png')
    im = bpy.data.images.load(path, check_existing=True)
    im.alpha_mode = 'STRAIGHT'
    w, h = im.size
    height = width * h / w
    base_v = (meta or {}).get(card, {}).get('cloud_base_v', 0.15)
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    p = bpy.context.object
    p.name = name
    p.scale = (width, height, 1)
    d = Vector(face_to) - Vector(loc)
    d.z = 0
    yaw = math.atan2(d.x, d.y)
    p.rotation_euler = (math.radians(90), 0, -yaw + math.pi)
    p.location = Vector(loc) + Vector((0, 0, height * (0.5 - base_v)))
    if mirror:
        p.scale.x = -p.scale.x
    rim_uv = None
    if moon_screen is not None:            # (moon right, moon up, camera right vector) -> UV direction
        bpy.context.view_layer.update()
        xw = p.matrix_world.to_3x3().col[0]
        sx = 1.0 if xw.dot(Vector(tuple(moon_screen[2]))) > 0 else -1.0
        rim_uv = (moon_screen[0] * sx, moon_screen[1])
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputMaterial')
    uvn = N('ShaderNodeTexCoord')
    tx = N('ShaderNodeTexImage'); tx.image = im; tx.interpolation = 'Cubic'; tx.extension = 'CLIP'
    L(uvn.outputs['UV'], tx.inputs['Vector'])
    em = N('ShaderNodeEmission')
    col = tx.outputs['Color']
    tm = N('ShaderNodeMix'); tm.data_type = 'RGBA'; tm.blend_type = 'MULTIPLY'
    tm.inputs['Factor'].default_value = 1.0
    L(col, tm.inputs['A'])
    if tear_tint is None:
        tm.inputs['B'].default_value = (*tint, 1)
    else:
        trgb, tbr, tdir, tpow = tear_tint
        gi = N('ShaderNodeNewGeometry')
        vv = N('ShaderNodeVectorMath'); vv.operation = 'SCALE'; vv.inputs['Scale'].default_value = -1.0
        L(gi.outputs['Incoming'], vv.inputs[0])
        dd = N('ShaderNodeVectorMath'); dd.operation = 'DOT_PRODUCT'; L(vv.outputs[0], dd.inputs[0]); dd.inputs[1].default_value = tuple(tdir)
        mxz = N('ShaderNodeMath'); mxz.operation = 'MAXIMUM'; L(dd.outputs['Value'], mxz.inputs[0]); mxz.inputs[1].default_value = 0.0
        pw = N('ShaderNodeMath'); pw.operation = 'POWER'; L(mxz.outputs[0], pw.inputs[0]); pw.inputs[1].default_value = tpow
        tc = N('ShaderNodeMix'); tc.data_type = 'RGBA'; tc.clamp_factor = True
        L(pw.outputs[0], tc.inputs['Factor']); tc.inputs['A'].default_value = (*tint, 1)
        tc.inputs['B'].default_value = tuple(trgb[i] * (1 + tbr) for i in range(3)) + (1,)
        L(tc.outputs['Result'], tm.inputs['B'])
    col = tm.outputs['Result']
    if top > 0:               # lift the moonlit tops: x (1 + top * smoothstep(lum))
        bw = N('ShaderNodeRGBToBW'); L(tx.outputs['Color'], bw.inputs[0])
        mr = N('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'; mr.clamp = True
        mr.inputs['From Min'].default_value = 0.06; mr.inputs['From Max'].default_value = 0.30
        mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = 1.0 + top
        L(bw.outputs[0], mr.inputs['Value'])
        sc_ = N('ShaderNodeVectorMath'); sc_.operation = 'SCALE'; L(col, sc_.inputs[0]); L(mr.outputs['Result'], sc_.inputs['Scale'])
        col = sc_.outputs[0]
    if rim > 0 and rim_uv is not None:       # silver lining where the edge faces the moon
        al2 = []
        for o_ in (0.008, 0.02, 0.04):
            off = N('ShaderNodeVectorMath'); off.operation = 'ADD'
            L(uvn.outputs['UV'], off.inputs[0]); off.inputs[1].default_value = (rim_uv[0] * o_, rim_uv[1] * o_ * w / h, 0)
            tx2 = N('ShaderNodeTexImage'); tx2.image = im; tx2.interpolation = 'Linear'; tx2.extension = 'CLIP'
            L(off.outputs[0], tx2.inputs['Vector'])
            al2.append(tx2.outputs['Alpha'])
        avg = N('ShaderNodeMath'); avg.operation = 'ADD'; L(al2[0], avg.inputs[0]); L(al2[1], avg.inputs[1])
        avg2 = N('ShaderNodeMath'); avg2.operation = 'MULTIPLY_ADD'; L(avg.outputs[0], avg2.inputs[0])
        avg2.inputs[1].default_value = 1.0 / 3.0; L(al2[2], avg2.inputs[2])
        avg3 = N('ShaderNodeMath'); avg3.operation = 'SUBTRACT'
        L(avg2.outputs[0], avg3.inputs[0]); L(al2[2], avg3.inputs[1])
        avg4 = N('ShaderNodeMath'); avg4.operation = 'MULTIPLY_ADD'; L(al2[2], avg4.inputs[0])
        avg4.inputs[1].default_value = 1.0 / 3.0; L(avg3.outputs[0], avg4.inputs[2])      # (a0 + a1 + a2) / 3
        dif = N('ShaderNodeMath'); dif.operation = 'SUBTRACT'; dif.use_clamp = True
        L(tx.outputs['Alpha'], dif.inputs[0]); L(avg4.outputs[0], dif.inputs[1])
        rc = N('ShaderNodeVectorMath'); rc.operation = 'SCALE'; rc.inputs[0].default_value = (0.62, 0.72, 1.0)
        rm = N('ShaderNodeMath'); rm.operation = 'MULTIPLY'; rm.inputs[1].default_value = rim
        L(dif.outputs[0], rm.inputs[0]); L(rm.outputs[0], rc.inputs['Scale'])
        ad = N('ShaderNodeVectorMath'); ad.operation = 'ADD'; L(col, ad.inputs[0]); L(rc.outputs[0], ad.inputs[1])
        col = ad.outputs[0]
    L(col, em.inputs['Color'])
    # seen in a wet arm's grazing reflection the bright cloud tops clipped to a hueless white band:
    # glossy rays see the clouds at 35 %
    lpc = N('ShaderNodeLightPath')
    gl = N('ShaderNodeMath'); gl.operation = 'MULTIPLY_ADD'
    L(lpc.outputs['Is Glossy Ray'], gl.inputs[0]); gl.inputs[1].default_value = -CLOUD_GLOSSY_DIM * brightness
    gl.inputs[2].default_value = brightness
    L(gl.outputs[0], em.inputs['Strength'])
    surf = em.outputs[0]
    if fog:
        fogf, fcol = _fog_nodes(nt, fog, density_scale=fog_scale, use_height=False)
        if mist > 0:          # a thin mist lying on the cloud sea (softens the near cloud tops)
            mm = N('ShaderNodeMath'); mm.operation = 'MULTIPLY_ADD'
            L(fogf, mm.inputs[0]); mm.inputs[1].default_value = 1.0 - mist; mm.inputs[2].default_value = mist
            fogf = mm.outputs[0]
        fe = N('ShaderNodeEmission'); L(fcol, fe.inputs['Color'])
        mx = N('ShaderNodeMixShader'); L(fogf, mx.inputs[0]); L(surf, mx.inputs[1]); L(fe.outputs[0], mx.inputs[2])
        surf = mx.outputs[0]
    alpha = tx.outputs['Alpha']
    if feather > 0:           # soft card ends: no straight vertical edges where two cards meet
        su = N('ShaderNodeSeparateXYZ'); L(uvn.outputs['UV'], su.inputs[0])
        e1 = N('ShaderNodeMapRange'); e1.interpolation_type = 'SMOOTHSTEP'; e1.clamp = True
        e1.inputs['From Min'].default_value = 0.03; e1.inputs['From Max'].default_value = feather
        L(su.outputs['X'], e1.inputs['Value'])
        e2 = N('ShaderNodeMapRange'); e2.interpolation_type = 'SMOOTHSTEP'; e2.clamp = True
        e2.inputs['From Min'].default_value = 0.97; e2.inputs['From Max'].default_value = 1.0 - feather
        L(su.outputs['X'], e2.inputs['Value'])
        m1 = N('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L(e1.outputs['Result'], m1.inputs[0]); L(e2.outputs['Result'], m1.inputs[1])
        m2 = N('ShaderNodeMath'); m2.operation = 'MULTIPLY'; L(m1.outputs[0], m2.inputs[0]); L(alpha, m2.inputs[1])
        alpha = m2.outputs[0]
    tr = N('ShaderNodeBsdfTransparent')
    ma = N('ShaderNodeMixShader')
    L(alpha, ma.inputs[0]); L(tr.outputs[0], ma.inputs[1]); L(surf, ma.inputs[2])
    L(ma.outputs[0], out.inputs['Surface'])
    p.data.materials.append(m)
    p.visible_shadow = False
    p.visible_diffuse = False
    p.visible_glossy = True
    return p


def add_gate_clouds(g, fog, k, to_moon, cam_loc, right, up, tear_tint=(1.02, 1.0, 1.28), moon_tint=(0.95, 1.0, 1.08),
                    cards=None, fwd_yaw=0.0):
    meta = _cloud_meta()
    cam = Vector(g['cam'])
    tear_az = math.degrees(math.atan2(g['tear'][0] - cam.x, g['tear'][1] - cam.y))
    mx, my = float(np.dot(np.array(to_moon), right)), float(np.dot(np.array(to_moon), up))
    ml = math.hypot(mx, my) + 1e-9
    obs = []
    rows_ = [(r, False) for r in (cards or GATE_CLOUDS)] + \
            ([(r, True) for r in cloud_sea_rows(g, top_z=k.get('cloud_top_z', 8.0))] if k.get('sea_rows') else [])
    rc = Vector(cam_loc)
    for n, ((card, az, dist, zb, width, br, mir), local) in enumerate(rows_):
        # the fixed banks sit round the gate camera; the cloud-sea rows round whichever camera renders
        c0, yaw0 = (rc, fwd_yaw) if local else (cam, g.get('yaw', 0.0))
        a = math.radians(az + yaw0)
        loc = (c0.x + dist * math.sin(a), c0.y + dist * math.cos(a), zb)
        tdir = (Vector(g['tear']) - rc).normalized()            # violet spill at the foot of the rip (per pixel)
        tint = moon_tint
        obs.append(add_cloud_card('ST_Cloud_%02d' % n, card, loc, width, rc, k['cloud_gain'] * br, mir,
                                  tint, fog, meta, moon_screen=(mx / ml, my / ml, tuple(right)), rim=k['cloud_rim'],
                                  top=k['cloud_top'], fog_scale=k['cloud_fog_scale'],
                                  feather=0.22 if local else 0.0, mist=k.get('sea_mist', 0.0) if local else 0.0,
                                  tear_tint=(tear_tint, 0.45, tuple(tdir), 25.0)))
    return obs


def add_cloud_sea(z=0.0, size=30000.0, fog=None, albedo=0.55):
    """The moonlit sea of clouds under the gate: a physically lit diffuse plane with large billows
    (bump), lit by the moon (silver) and by the tear (violet near the rip), in the same aerial
    perspective as everything else. Preview stand-in for the cloud-sea cards the main build uses."""
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    p = bpy.context.object
    p.name = 'ST_CloudSea'
    m = bpy.data.materials.new('ST_CloudSea')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputMaterial')
    bs = N('ShaderNodeBsdfPrincipled')
    bs.inputs['Roughness'].default_value = 1.0
    try:
        bs.inputs['Specular IOR Level'].default_value = 0.0
    except KeyError:
        pass
    geo = N('ShaderNodeNewGeometry')
    mp = N('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / 260.0, 1 / 180.0, 1.0)
    L(geo.outputs['Position'], mp.inputs['Vector'])
    nz = N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0
    nz.inputs['Detail'].default_value = 8.0; nz.inputs['Roughness'].default_value = 0.62
    L(mp.outputs['Vector'], nz.inputs['Vector'])
    bump = N('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.9
    bump.inputs['Distance'].default_value = 60.0
    L(nz.outputs['Fac'], bump.inputs['Height'])
    L(bump.outputs['Normal'], bs.inputs['Normal'])
    ramp = N('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (albedo * 0.45, albedo * 0.5, albedo * 0.62, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (albedo * 0.85, albedo * 0.9, albedo, 1)
    L(nz.outputs['Fac'], ramp.inputs['Fac'])
    L(ramp.outputs['Color'], bs.inputs['Base Color'])
    surf = bs.outputs[0]
    if fog:
        fogf, fcol = _fog_nodes(nt, fog, density_scale=0.85, use_height=False)
        em = N('ShaderNodeEmission'); L(fcol, em.inputs['Color'])
        mx = N('ShaderNodeMixShader')
        L(fogf, mx.inputs[0]); L(surf, mx.inputs[1]); L(em.outputs[0], mx.inputs[2])
        surf = mx.outputs[0]
    lpc = N('ShaderNodeLightPath')
    gl = N('ShaderNodeMath'); gl.operation = 'MULTIPLY_ADD'
    L(lpc.outputs['Is Glossy Ray'], gl.inputs[0]); gl.inputs[1].default_value = -CLOUD_GLOSSY_DIM; gl.inputs[2].default_value = 1.0
    blk = N('ShaderNodeBsdfTransparent'); blk.inputs['Color'].default_value = (0, 0, 0, 1)
    dim = N('ShaderNodeMixShader'); L(gl.outputs[0], dim.inputs[0]); L(blk.outputs[0], dim.inputs[1]); L(surf, dim.inputs[2])
    surf = dim.outputs[0]
    L(surf, out.inputs['Surface'])
    p.data.materials.append(m)
    p.visible_shadow = False
    p.visible_diffuse = False          # no grey bounce onto the black arms; dimmed in reflections
    return p


_VN = {}


def _value_noise2(x, y, cell, seed):
    """Smooth 2-D value noise (bicubic spline through a wrapped 512^2 random lattice), ~N(0, 0.5)."""
    from scipy.ndimage import map_coordinates, spline_filter
    if seed not in _VN:
        g = np.random.default_rng(seed).normal(0, 1, (512, 512))
        _VN[seed] = spline_filter(g, order=3, mode='grid-wrap')
    return map_coordinates(_VN[seed], [np.ravel(y) / cell, np.ravel(x) / cell], order=3, mode='grid-wrap',
                           prefilter=False).reshape(np.shape(x)) * 0.5


_DOME = {}


def _dome_octave(X, Y, cell, seed, rfrac=(0.55, 0.95), hfrac=(0.2, 0.4)):
    """Union (max) of jittered spherical-cap puffs, one per cell: rounded tops, crevices between."""
    if seed not in _DOME:
        _DOME[seed] = np.random.default_rng(seed).uniform(0, 1, (4, 1024, 1024))
    J = _DOME[seed]
    gx, gy = np.floor(X / cell).astype(np.int64), np.floor(Y / cell).astype(np.int64)
    h = np.zeros_like(X)
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            cx, cy = gx + ox, gy + oy
            ix, iy = cx % 1024, cy % 1024
            px = (cx + 0.15 + 0.7 * J[0, iy, ix]) * cell
            py = (cy + 0.15 + 0.7 * J[1, iy, ix]) * cell
            r = cell * (rfrac[0] + (rfrac[1] - rfrac[0]) * J[2, iy, ix])
            hh = r * (hfrac[0] + (hfrac[1] - hfrac[0]) * J[3, iy, ix])
            q = 1.0 - ((X - px) ** 2 + (Y - py) ** 2) / (r * r)
            h = np.maximum(h, hh * np.sqrt(np.clip(q, 0.0, None)))
    return h


def cloud_field_heights(X, Y, step, seed=31):
    """Cumulus tops of the sea of clouds: broad swells + three octaves of puffs (unions of rounded caps,
    each octave riding on the one below: the cauliflower of a cumulus top, crevices at every scale).
    Octaves finer than ~5 grid steps fade out, so the far field stays smooth instead of aliasing.
    Mean top ~ 0 m (the cloud-sea top the fog and the layout use), puffs to ~ +30 m, crevices ~ -20 m."""
    h = 10.0 * _value_noise2(X + 7000, Y, 1600.0, seed) + 5.0 * _value_noise2(X, Y + 3000, 600.0, seed + 1)
    for i, (cell, wgt, hf) in enumerate(((170.0, 0.8, (0.12, 0.3)), (62.0, 0.8, (0.2, 0.45)),
                                         (23.0, 0.7, (0.3, 0.6)), (9.0, 0.5, (0.35, 0.65)))):
        w = np.clip(cell / (5.0 * step) - 1.0, 0.0, 1.0)
        h = h + w * wgt * _dome_octave(X, Y, cell, seed + 10 + i, hfrac=hf)
        if i == 0:              # ... riding on a warped fBm, so the puffs never sit on a flat floor
            h = h + 7.0 * _value_noise2(X + 311.0, Y - 97.0, 120.0, seed + 5) + 3.0 * _value_noise2(X, Y, 45.0, seed + 6)
    return h - 34.0


def add_cloud_field(cam_loc, yaw_deg, fog, k, r=(35.0, 12000.0), n_r=640, az_span=100.0, n_az=1500, seed=31):
    """The sea of clouds seen from 40-60 m above it: a polar heightfield of cumulus tops around the
    rendering camera (radial spacing grows with distance so every cell is a few pixels on screen), a
    soft diffuse + translucent cloud material in the same LanbaiFog as the arms (extra density low over
    the tops, so roots dissolve), lit by the moon from the left front (backlit domes: dark faces, silver
    crests) and the tear light; the rip's own spill on the sea below it (the bible's additive decal,
    #495270 on screen) is an emission term falling off over ~1 km from the tear foot."""
    cx, cy = float(cam_loc[0]), float(cam_loc[1])
    rr = r[0] * (r[1] / r[0]) ** (np.arange(n_r) / (n_r - 1.0))
    aa = np.radians(yaw_deg + np.linspace(-az_span, az_span, n_az))
    R_, A_ = np.meshgrid(rr, aa, indexing='ij')
    X, Y = cx + R_ * np.sin(A_), cy + R_ * np.cos(A_)
    step = np.maximum(R_ * math.log(r[1] / r[0]) / (n_r - 1), R_ * (aa[1] - aa[0]))
    Z = cloud_field_heights(X, Y, step, seed)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3).astype(np.float32)
    i0 = (np.arange(n_r - 1)[:, None] * n_az + np.arange(n_az - 1)[None]).ravel()
    quads = np.stack([i0, i0 + 1, i0 + n_az + 1, i0 + n_az], -1).astype(np.int32)
    me = bpy.data.meshes.new('ST_CloudField')
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set('vertex_index', quads.ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4, dtype=np.int32))
    me.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new('ST_CloudField', me)
    bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.new('ST_CloudField')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputMaterial')
    geo = N('ShaderNodeNewGeometry')
    alb = k.get('field_albedo', 0.75)
    # the finest puffs (below the mesh resolution) as a bump: two octaves of rounded caps (cell-noise
    # distance -> sqrt(1 - d^2)), 9 m and 3.5 m, warped by a little noise so the cells never read
    hsum = None
    for sc_, wt_ in ((1.0 / 9.0, 1.0), (1.0 / 3.5, 0.45)):
        wn = N('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = sc_ * 0.5
        wn.inputs['Detail'].default_value = 2.0
        L(geo.outputs['Position'], wn.inputs['Vector'])
        wv = N('ShaderNodeVectorMath'); wv.operation = 'MULTIPLY_ADD'
        L(wn.outputs['Color'], wv.inputs[0]); wv.inputs[1].default_value = (0.6 / sc_,) * 3
        L(geo.outputs['Position'], wv.inputs[2])
        vo = N('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = sc_
        L(wv.outputs[0], vo.inputs['Vector'])
        q = N('ShaderNodeMath'); q.operation = 'MULTIPLY'; L(vo.outputs['Distance'], q.inputs[0]); L(vo.outputs['Distance'], q.inputs[1])
        q2 = N('ShaderNodeMath'); q2.operation = 'SUBTRACT'; q2.use_clamp = True; q2.inputs[0].default_value = 1.0
        L(q.outputs[0], q2.inputs[1])
        q3 = N('ShaderNodeMath'); q3.operation = 'POWER'; L(q2.outputs[0], q3.inputs[0]); q3.inputs[1].default_value = 0.5
        q4 = N('ShaderNodeMath'); q4.operation = 'MULTIPLY'; L(q3.outputs[0], q4.inputs[0]); q4.inputs[1].default_value = wt_ / sc_
        if hsum is None:
            hsum = q4.outputs[0]
        else:
            ad_ = N('ShaderNodeMath'); ad_.operation = 'ADD'; L(hsum, ad_.inputs[0]); L(q4.outputs[0], ad_.inputs[1])
            hsum = ad_.outputs[0]
    fb = N('ShaderNodeTexNoise'); fb.inputs['Scale'].default_value = 1.0 / 14.0
    fb.inputs['Detail'].default_value = 7.0; fb.inputs['Roughness'].default_value = 0.62
    fb.inputs['Distortion'].default_value = 0.4
    L(geo.outputs['Position'], fb.inputs['Vector'])
    fbm = N('ShaderNodeMath'); fbm.operation = 'MULTIPLY_ADD'; L(fb.outputs['Fac'], fbm.inputs[0])
    fbm.inputs[1].default_value = 14.0 * k.get('field_fbm', 1.0); L(hsum, fbm.inputs[2])
    bump = N('ShaderNodeBump'); bump.inputs['Strength'].default_value = k.get('field_bump', 0.6)
    bump.inputs['Distance'].default_value = 0.35
    L(fbm.outputs[0], bump.inputs['Height'])
    df = N('ShaderNodeBsdfPrincipled'); df.inputs['Base Color'].default_value = (alb * 0.92, alb * 0.95, alb, 1)
    df.inputs['Roughness'].default_value = 1.0
    for nm_, v_ in (('Specular IOR Level', 0.0), ('Sheen Weight', k.get('field_sheen', 0.8)), ('Sheen Roughness', 0.35)):
        try:
            df.inputs[nm_].default_value = v_
        except KeyError:
            pass
    L(bump.outputs['Normal'], df.inputs['Normal'])
    tl = N('ShaderNodeBsdfTranslucent'); tl.inputs['Color'].default_value = (alb * 0.92, alb * 0.95, alb, 1)
    L(bump.outputs['Normal'], tl.inputs['Normal'])
    # a cloud is not a rock: multiple scattering keeps the faces turned from the moon softly lit and only
    # the crevices go dark -> albedo ramps with height (deep crevices 35 %, tops 100 %) and a faint
    # in-scatter glow rises with height
    sz = N('ShaderNodeSeparateXYZ'); L(geo.outputs['Position'], sz.inputs[0])
    hr = N('ShaderNodeMapRange'); hr.interpolation_type = 'SMOOTHSTEP'; hr.clamp = True
    hr.inputs['From Min'].default_value = -24.0; hr.inputs['From Max'].default_value = 14.0
    hr.inputs['To Min'].default_value = 0.35; hr.inputs['To Max'].default_value = 1.0
    L(sz.outputs['Z'], hr.inputs['Value'])
    hc = N('ShaderNodeVectorMath'); hc.operation = 'SCALE'; hc.inputs[0].default_value = (alb * 0.92, alb * 0.95, alb)
    L(hr.outputs['Result'], hc.inputs['Scale'])
    L(hc.outputs[0], df.inputs['Base Color']); L(hc.outputs[0], tl.inputs['Color'])
    mxs = N('ShaderNodeMixShader'); mxs.inputs[0].default_value = k.get('field_translucency', 0.3)
    L(df.outputs[0], mxs.inputs[1]); L(tl.outputs[0], mxs.inputs[2])
    surf = mxs.outputs[0]
    if k.get('field_ms', 0.0) > 0:
        ems = N('ShaderNodeEmission'); ems.inputs['Color'].default_value = (*_hex_lin('#5A6A88'), 1.0)
        mh = N('ShaderNodeMath'); mh.operation = 'MULTIPLY'; mh.inputs[1].default_value = k['field_ms']
        L(hr.outputs['Result'], mh.inputs[0]); L(mh.outputs[0], ems.inputs['Strength'])
        ad0 = N('ShaderNodeAddShader'); L(surf, ad0.inputs[0]); L(ems.outputs[0], ad0.inputs[1])
        surf = ad0.outputs[0]
    # the rip's spill on the sea below it (additive decal in Unity): falls off over ~1 km from the tear foot
    tear = k.get('_tear_pos')
    if tear is not None and k.get('field_spill', 0.0) > 0:
        vm = N('ShaderNodeVectorMath'); vm.operation = 'DISTANCE'
        L(geo.outputs['Position'], vm.inputs[0]); vm.inputs[1].default_value = (tear[0], tear[1], 0.0)
        fall = N('ShaderNodeMapRange'); fall.interpolation_type = 'SMOOTHSTEP'; fall.clamp = True
        fall.inputs['From Min'].default_value = 0.0; fall.inputs['From Max'].default_value = 1100.0
        fall.inputs['To Min'].default_value = 1.0; fall.inputs['To Max'].default_value = 0.0
        L(vm.outputs['Value'], fall.inputs['Value'])
        em = N('ShaderNodeEmission'); em.inputs['Color'].default_value = (*_hex_lin('#495270'), 1.0)
        mul = N('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = k['field_spill']
        L(fall.outputs['Result'], mul.inputs[0]); L(mul.outputs[0], em.inputs['Strength'])
        ad = N('ShaderNodeAddShader'); L(surf, ad.inputs[0]); L(em.outputs[0], ad.inputs[1])
        surf = ad.outputs[0]
    if fog:
        fogf, fcol = _fog_nodes(nt, fog, density_scale=k.get('field_fog_scale', 1.0), use_height=True)
        em2 = N('ShaderNodeEmission'); L(fcol, em2.inputs['Color'])
        mx = N('ShaderNodeMixShader')
        L(fogf, mx.inputs[0]); L(surf, mx.inputs[1]); L(em2.outputs[0], mx.inputs[2])
        surf = mx.outputs[0]
    lpc = N('ShaderNodeLightPath')               # dimmed in the arms' wet reflections (a grey mirror otherwise)
    gl = N('ShaderNodeMath'); gl.operation = 'MULTIPLY_ADD'
    L(lpc.outputs['Is Glossy Ray'], gl.inputs[0]); gl.inputs[1].default_value = -CLOUD_GLOSSY_DIM; gl.inputs[2].default_value = 1.0
    blk = N('ShaderNodeBsdfTransparent'); blk.inputs['Color'].default_value = (0, 0, 0, 1)
    dim = N('ShaderNodeMixShader'); L(gl.outputs[0], dim.inputs[0]); L(blk.outputs[0], dim.inputs[1]); L(surf, dim.inputs[2])
    surf = dim.outputs[0]
    if k.get('field_soft', 0.0) > 0:            # soft, see-through crests (a cloud has no hard silhouette)
        lw = N('ShaderNodeLayerWeight'); L(bump.outputs['Normal'], lw.inputs['Normal'])
        edge = N('ShaderNodeMapRange'); edge.interpolation_type = 'SMOOTHSTEP'; edge.clamp = True
        edge.inputs['From Min'].default_value = 1.0 - k['field_soft']; edge.inputs['From Max'].default_value = 1.0
        L(lw.outputs['Facing'], edge.inputs['Value'])
        tr = N('ShaderNodeBsdfTransparent')
        sm = N('ShaderNodeMixShader'); L(edge.outputs['Result'], sm.inputs[0]); L(surf, sm.inputs[1]); L(tr.outputs[0], sm.inputs[2])
        surf = sm.outputs[0]
    L(surf, out.inputs['Surface'])
    ob.data.materials.append(m)
    ob.visible_diffuse = False                   # no grey bounce onto the black arms
    return ob


# =============================================================================================
# 7. GATE LAYOUT -> Unity (JSON)
# =============================================================================================
# Blender (x, y, z) -> Unity (-x, z, -y): what the shared FBX settings (forward -Z, up Y, baked
# space transform) plus Unity's right-to-left-handed import do to every vertex.
B2U = np.array([[-1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
# the layout is also turned 180 deg about Unity Y so the bus looks down Unity +Z (its natural forward)
LAYOUT_U = np.diag([-1.0, 1.0, -1.0]) @ B2U          # Blender world -> Unity layout: (x, z, y)


def _quat_from_matrix(R):
    m = np.asarray(R, float)
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        w, x, y, z = 0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w, x, y, z = (m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w, x, y, z = (m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w, x, y, z = (m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s
    q = np.array([x, y, z, w])
    return q / np.linalg.norm(q)


def _unity_euler(R):
    """Unity eulerAngles (degrees) for a rotation matrix in Unity coordinates: R = Ry * Rx * Rz."""
    m = np.asarray(R, float)
    x = math.asin(max(-1.0, min(1.0, -m[1, 2])))
    if abs(math.cos(x)) > 1e-6:
        y = math.atan2(m[0, 2], m[2, 2])
        z = math.atan2(m[1, 0], m[1, 1])
    else:
        y = math.atan2(-m[2, 0], m[0, 0])
        z = 0.0
    return [round(math.degrees(a) % 360.0, 3) for a in (x, y, z)]


def gate_layout_json(path, g=GATE, look=GATE_LOOK):
    """GateLayout.json v2 (ART BIBLE v2 distance table): every arm of the gate key art in Unity layout
    space + the LanbaiFog / light / tear parameters the renders use (one source of truth)."""
    import preview_rig as pr
    cam, fwd, right, up = gate_camera_basis(g)
    to_moon = np.array(pr._dir_from(pr.MOON_AZ, pr.MOON_EL), float)
    to_moon /= np.linalg.norm(to_moon)
    U = lambda v: [round(float(c), 3) for c in (LAYOUT_U @ np.asarray(v, float))]
    lin = lambda c: [round(float(x), 5) for x in c]
    layers = look.get('fog_layers') or {}
    inst = []
    for it in gate_instances(g):
        Rb = np.array(it['rot'].to_matrix())
        Ru = LAYOUT_U @ Rb @ B2U.T                    # FBX mesh local = B2U @ Blender local
        assert abs(np.linalg.det(Ru) - 1.0) < 1e-4
        loc = np.array(it['loc'])
        kind = it['mat']
        mat = 'M_Tentacle_%s%s' % (it['key'], {'colossus': '_Colossus', 'tide': '_Tide'}.get(kind, ''))
        inst.append(dict(name=it['name'], prefab='Tentacle_%s' % it['key'], variant=it['key'], layer=it['layer'],
                         material=mat, force_lod=it['lod'] if it['lod'] else None,
                         cast_shadows=it['layer'] == 'near', impostor=it['layer'] == 'tide',
                         flyby_subject=bool(it['flyby']) or None,
                         position=U(loc), rotation_quaternion_xyzw=[round(float(c), 6) for c in _quat_from_matrix(Ru)],
                         rotation_euler_deg=_unity_euler(Ru), scale=round(float(it['scale']), 4),
                         length_m=round(centreline(it['key'])['L'] * it['scale'], 1),
                         distance_from_camera_m=round(float(np.linalg.norm(loc - cam)), 1)))
    fg = dict(FOG, **(look.get('fog') or {}))
    fog = dict(
        _FogDensity=fg['density'], _FogExtra=[fg['extra'], fg['extra_h']], _CloudTopY=fg['z_cloud'],
        _FogCap=fg['cap'], _FogCapFrom=list(fg['cap_from']), _FogCapHeight=fg['cap_h'],
        _HazeNear=lin(fg['near']), _HazeFar=lin(fg['far']), _Void=lin(fg['void']),
        _BandAz=list(fg['band_az']), _BandEl=list(fg['band_el']), _BelowHorizon=list(fg['below']),
        per_layer=dict(near=dict(_FogDensityScale=layers.get('default', {}).get('density_scale', 1.0)),
                       mid=dict(_FogDensityScale=layers.get('default', {}).get('density_scale', 1.0)),
                       colossus=dict(_FogCapHeight=layers.get('colossus', {}).get('cap_h', fg['cap_h'])),
                       colossus_bg=dict(_FogCapHeight=layers.get('colossus', {}).get('cap_h', fg['cap_h'])),
                       tide=dict(_FogCap=0.92, _FogCapHeight=0.0, note='no height falloff: the tide is 80-92 % in the haze')),
        preview_sky_gain=look.get('sky_gain', 1.0),
        note='LanbaiFog: f = 1 - exp(-d * _FogDensity * _FogDensityScale * (1 + _FogExtra.x * exp(-h / _FogExtra.y))), '
             'h = height above _CloudTopY; beyond _FogCapFrom (smoothstep) f = min(f, _FogCap) * exp(-h / _FogCapHeight). '
             'Fog colour = the haze band in the view direction (identical to the sky): _HazeNear next to the tear -> '
             '_HazeFar 50 deg away (azimuth from the tear), fading to _Void above _BandEl / beyond _BandAz. '
             'Colours are LINEAR and are the bible\'s SCREEN values; preview_sky_gain is what the Blender preview '
             'multiplies sky + fog by so that, after AgX + the S4 grade, the band reads #484D63 -> #2A3041 on screen '
             '(in Unity use the bible\'s fill values, e.g. #67697D next to the tear, and let S4 bring them down).')
    counts = {}
    for i in inst:
        counts[i['layer']] = counts.get(i['layer'], 0) + 1
    tear_h, tear_w = g['tear_h'], g['tear_h'] * g['tear_w']
    data = dict(
        about='蓝白 tentacle gate v2 (ART BIBLE v2 §6·4, U7 frame of the gate key art). Unity layout space, metres: '
              'Blender world (x, y, z) -> (x, z, y); the bus camera looks down +Z; the tear is at azimuth 0. '
              'Place prefab Tentacle_X at position with rotation_quaternion_xyzw (authoritative; eulers are Unity ZXY) '
              'and uniform scale, under ONE parent that moves with the world speed v_g (cloud sea, arms and tide '
              'share it; the near layer instead moves WITH the bus, relative speed <= 1.05 x distance). '
              'layer: near (8-20 m, 2-3 arms, the only shadow casters) / mid (ring 400-900 m round the tear foot) / '
              'colossus (3 choreographed) / colossus_bg (6-10 at 1.3-4 km) / tide (5-12 km, impostors: use the '
              'TentacleTide atlas billboards, not the FBX; force_lod 2 here is only the preview stand-in).',
        counts=counts,
        cloud_sea_top_y=0.0,
        camera=dict(position=U(cam), forward=U(fwd), up=U(up), height_above_cloud_top_m=float(g['cam'][2]),
                    pitch_deg=g['pitch'], vertical_fov_deg=round(math.degrees(2 * math.atan(18.0 / g['lens'] / g['aspect'])), 2),
                    lens_mm=g['lens'], aspect=g['aspect']),
        tear=dict(centre=U(g['tear']), height_m=tear_h, widest_m=round(tear_w, 1), widest_at_height_frac=0.40,
                  left_right_half_width=[0.45, 0.55], axis_tilt_deg=4.0, foot_sinks_into_cloud_sea=True,
                  core_screen='#F5F2EC', lips='#E2E8F3', lip_glow='#C0B9E4', halo='#5B57A1',
                  note='U7: 635 m tall at 1.8 km (top +18 deg). Preview = lib/preview_rig.add_tear; the tear kit '
                       '(lens, flaps, branch rips) is its own deliverable.'),
        moon=dict(azimuth_deg=pr.MOON_AZ, elevation_deg=pr.MOON_EL, direction_toward_moon=U(to_moon),
                  directional_light_forward=U(-to_moon), colour='#D6E4FF', disc_deg=look['moon_disc_deg'],
                  note='Directional Light forward = -direction_toward_moon; also the shader _RimDir'),
        tear_light=dict(colour='#A99DE1', directional_light_forward=U([0.0, -1.0, -0.12]), shadows=False,
                        intensity_vs_moon=0.8, _TearPos=U(g['tear'])),
        fill=dict(colour='#5A6488', from_below=True, intensity_vs_moon=0.24, not_important=True),
        rims=dict(moon=dict(colour=RIM['moon_color'], formula='#9DB8FF x pow(1 - N.V, 5) x saturate(0.3 - N.L_moon)'),
                  tear=dict(colour=RIM['tear_color'], proximity_m=[RIM.get('tear_near', 200.0), RIM.get('tear_far', 1200.0)]),
                  transmission=dict(colour='#5B57A1', formula='(1 - B)^2 x tear light x #5B57A1 (thin tips)')),
        lanbai_fog=fog,
        instances=inst)
    with open(path, 'w') as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print('layout', path, len(inst), 'instances', counts, 'rimdir', U(to_moon), 'tearpos', U(g['tear']))
    return data


# =============================================================================================
# 6b. THE FAR TIDE (ART BIBLE v2 §6·4 / §8.1 #5): impostor atlases + one billboard mesh
# =============================================================================================
# Three 512 x 2048 atlases, 8 silhouettes each (2 columns x 4 rows of 256 x 512), drawn from the library
# itself (variant, turn about the root axis, lean toward the tear), the moon / tear rim painted in on the
# side that leans toward the wound. Every arm LEANS RIGHT in the atlas; arms right of the tear use the
# cell mirrored (baked into the mesh UVs), so the whole tide surges toward the rip.
TIDE_ATLAS = {
    'A': [('A', 0, 24), ('C', 40, 30), ('E', 0, 18), ('F', 200, 26), ('A', 120, 34), ('E', 150, 22), ('F', 30, 30), ('C', 250, 20)],
    'B': [('B', 30, 26), ('D', 0, 20), ('E', 90, 30), ('F', 120, 22), ('A', 250, 28), ('C', 140, 32), ('F', 300, 18), ('E', 210, 26)],
    'C': [('F', 60, 34), ('A', 300, 20), ('D', 160, 26), ('E', 330, 24), ('C', 80, 28), ('B', 200, 22), ('F', 250, 30), ('A', 30, 26)],
}
TIDE_CELL = (256, 512)
TIDE_BODY = '#0F1116'            # the bible's near-body colour (the tide is 80-92 % in the haze anyway)
TIDE_RIM = '#A9C2FF'             # moon rim, 1-3 px


def _tide_silhouette(key, yaw, lean, ss=4):
    """(RGBA float array ch x cw, meta) of one cell, rasterised at ss x and box-filtered."""
    from PIL import ImageDraw
    cw, ch = TIDE_CELL
    W, H = cw * ss, ch * ss
    parts, _ = variant_parts(key, 1)
    a, l = math.radians(yaw), math.radians(lean)
    R2 = np.array([[math.cos(a), math.sin(a), 0.0], [0.0, 0.0, 1.0]])
    Rl = np.array([[math.cos(l), math.sin(l)], [-math.sin(l), math.cos(l)]])        # lean toward +x (right)
    segs = [((p['C'] @ R2.T) @ Rl.T, p['r']) for p in parts]
    allp = np.concatenate([s[0] for s in segs])
    rmax = max(s[1].max() for s in segs)
    lo, hi = allp.min(0) - rmax, allp.max(0) + rmax
    m = 10 * ss
    sc = min((W - 2 * m) / (hi[0] - lo[0]), (H - m) / (hi[1] - lo[1]))
    im = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(im)
    x_of = lambda x: m + (x - lo[0]) * sc
    y_of = lambda y: H - (y - min(lo[1], 0.0)) * sc
    for C2, rr in segs:
        for j in range(len(C2)):
            for f in (np.linspace(0, 1, 6)[:-1] if j < len(C2) - 1 else [0.0]):
                c = C2[j] * (1 - f) + (C2[j + 1] * f if j < len(C2) - 1 else 0)
                r = max((rr[j] * (1 - f) + (rr[j + 1] * f if j < len(C2) - 1 else 0)) * sc, 0.6 * ss)
                x, y = x_of(c[0]), y_of(c[1])
                dr.ellipse([x - r, y - r, x + r, y + r], fill=255)
    A = np.asarray(im).astype(np.float32) / 255.0
    # rim on the edges that face the lean side (+x, a little up), ~1.5 px wide at the final size
    d = np.array([math.cos(math.radians(20)), -math.sin(math.radians(20))]) * 1.6 * ss
    from scipy.ndimage import shift as ndshift
    rim = np.clip(A - ndshift(A, (-d[1], -d[0]), order=1, mode='constant'), 0, 1)
    body, rc = np.array(srgb2lin(np.array(_hex_srgb(TIDE_BODY)))), np.array(srgb2lin(np.array(_hex_srgb(TIDE_RIM))))
    col = body[None, None] * (1 - rim[..., None]) + rc[None, None] * rim[..., None] * 0.9
    pre = np.concatenate([col * A[..., None], A[..., None]], -1)
    pre = pre.reshape(ch, ss, cw, ss, 4).mean((1, 3))
    a_ = pre[..., 3:4]
    rgb = np.where(a_ > 1e-4, pre[..., :3] / np.maximum(a_, 1e-4), body[None, None])
    out = np.concatenate([lin2srgb(rgb), a_], -1)
    root_u = x_of(0.0) / W
    L = centreline(key)['L']
    meta = dict(variant=key, yaw_deg=yaw, lean_deg=lean, root_u=round(float(root_u), 4),
                cell_height_in_lengths=round(float(H / sc / L), 4))
    return out, meta


def _hex_srgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def build_tide_atlases(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    cw, ch = TIDE_CELL
    cells = []
    for name, spec in TIDE_ATLAS.items():
        atlas = np.zeros((4 * ch, 2 * cw, 4), np.float32)
        for i, (key, yaw, lean) in enumerate(spec):
            px, meta = _tide_silhouette(key, yaw, lean)
            col, row = i % 2, i // 2                  # row 0 = TOP of the image
            atlas[row * ch:(row + 1) * ch, col * cw:(col + 1) * cw] = px
            v1 = 1.0 - row * ch / (4 * ch)
            meta.update(atlas='TentacleTide_Atlas_%s' % name, index=i,
                        uv_rect=[col / 2.0, v1 - 0.25, (col + 1) / 2.0, v1])     # u0, v0, u1, v1 (Unity: v up)
            cells.append(meta)
        Image.fromarray((np.clip(atlas, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(
            os.path.join(out_dir, 'TentacleTide_Atlas_%s.png' % name))
        print('tide atlas', name, atlas.shape[1::-1])
    with open(os.path.join(out_dir, 'TentacleTide_Atlas.json'), 'w') as fh:
        json.dump(dict(cell_px=list(TIDE_CELL), layout='2 columns x 4 rows per atlas, index = row * 2 + col, row 0 at the top',
                       note='every silhouette leans RIGHT (toward the tear for arms left of it); the root sits at '
                            '(root_u, 0) of its cell; a quad of height cell_height_in_lengths x arm length shows the '
                            'arm at its true size; moon rim painted on the leaning side', cells=cells), fh, indent=1)
    return cells


def tide_quads(cells, g=GATE, cam=None):
    """Per tide arm: its atlas cell and the 4 corners (GateLayout / Unity layout space) of the quad that
    stands on its root facing `cam` (Blender world; default the gate camera) about the vertical axis,
    mirrored for arms right of the tear so every silhouette leans toward it. Shared by the FBX and the
    preview renders (so gate.png shows exactly what the billboard shader draws)."""
    rng = np.random.default_rng(77)
    cam_u = LAYOUT_U @ np.array(g['cam'] if cam is None else cam, float)
    tear_u = LAYOUT_U @ np.array(g['tear'], float)
    byvar = {}
    for c in cells:
        byvar.setdefault(c['variant'], []).append(c)
    out = []
    for it in gate_instances(g):
        if it['layer'] != 'tide':
            continue
        pool = byvar.get(it['key']) or cells
        c = pool[rng.integers(len(pool))]
        Lm = centreline(it['key'])['L'] * it['scale']
        Hq = c['cell_height_in_lengths'] * Lm
        Wq = Hq * TIDE_CELL[0] / TIDE_CELL[1]
        base = LAYOUT_U @ np.array(it['loc'], float)
        d = base[[0, 2]] - cam_u[[0, 2]]
        d /= np.linalg.norm(d)
        r = np.array([d[1], 0.0, -d[0]])
        mirror = np.dot(r[[0, 2]], tear_u[[0, 2]] - base[[0, 2]]) < 0     # the tear is to its left: lean left
        u0, v0, u1, v1 = c['uv_rect']
        ru = c['root_u']
        offs = (-(1 - ru) * Wq, ru * Wq) if mirror else (-ru * Wq, (1 - ru) * Wq)
        us = (u1, u0) if mirror else (u0, u1)
        corners, uv, hs, os_ = [], [], [], []
        for (o, u), (hy, vv) in (((offs[0], us[0]), (0.0, v0)), ((offs[1], us[1]), (0.0, v0)),
                                 ((offs[1], us[1]), (Hq, v1)), ((offs[0], us[0]), (Hq, v1))):
            corners.append(base + r * o + np.array([0.0, hy, 0.0]))
            uv.append((u, vv)); hs.append(hy / Hq); os_.append(o)
        out.append(dict(atlas=c['atlas'], corners=np.array(corners), uv=uv, hfrac=hs, off=os_, base=base,
                        phase=float(np.linalg.norm(base[[0, 2]] - tear_u[[0, 2]]) / 600.0)))
    return out


def build_tide_mesh(cells, out_dir, g=GATE):
    """TentacleTide.fbx: one mesh, 400 quads (2 triangles each), 3 sub-meshes = the 3 atlases. Vertices are
    in the GateLayout (Unity layout) space; the billboard shader re-faces every quad to the camera about its
    own root (UV2 = root x, z; UV3 = root y, signed horizontal offset), UV1 = (height fraction, sway phase =
    distance to the tear / 600 m)."""
    import export_unity
    bpy.ops.wm.read_factory_settings(use_empty=True)
    verts, faces, uv0, uv1, uv2, uv3, mats = [], [], [], [], [], [], []
    atl = sorted(TIDE_ATLAS)
    quads = tide_quads(cells, g)
    for qd in quads:
        k0 = len(verts)
        for j in range(4):
            verts.append(B2U.T @ qd['corners'][j])      # the FBX export (B2U) brings it back to layout space
            uv0.append(qd['uv'][j]); uv1.append((qd['hfrac'][j], qd['phase']))
            uv2.append((qd['base'][0], qd['base'][2])); uv3.append((qd['base'][1], qd['off'][j]))
        faces.append((k0, k0 + 1, k0 + 2, k0 + 3))
        mats.append(atl.index(qd['atlas'][-1]))
    n = len(quads)
    me = bpy.data.meshes.new('TentacleTide')
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    for nm, data in (('UVMap', uv0), ('TideSway', uv1), ('TideRootXZ', uv2), ('TideRootYOffset', uv3)):
        lay = me.uv_layers.new(name=nm)
        lv = np.zeros(len(me.loops), np.int32)
        me.loops.foreach_get('vertex_index', lv)
        lay.data.foreach_set('uv', np.array(data, np.float32)[lv].ravel())
    me.uv_layers.active = me.uv_layers['UVMap']
    for a_ in atl:
        me.materials.append(bpy.data.materials.new('M_TentacleTide_%s' % a_))
    me.polygons.foreach_set('material_index', mats)
    me.polygons.foreach_set('use_smooth', [False] * len(faces))
    me.validate()
    ob = bpy.data.objects.new('TentacleTide', me)
    bpy.context.scene.collection.objects.link(ob)
    os.makedirs(os.path.join(out_dir, 'FBX'), exist_ok=True)
    path = os.path.join(out_dir, 'FBX', 'TentacleTide.fbx')
    export_unity.export_fbx(path, [ob])
    print('tide mesh', path, n, 'quads', 2 * n, 'triangles', 'per atlas', {a_: mats.count(i) for i, a_ in enumerate(atl)})
    return path


def add_tide_billboards(g, fg, tex_dir, cam_loc):
    """Preview of Lanbai/TentacleTide: the 400 atlas quads facing the rendering camera, unlit atlas colour
    in LanbaiFog with _FogCap 0.92 and no height falloff (alpha blended, invisible to lighting)."""
    meta = os.path.join(tex_dir, 'TentacleTide_Atlas.json')
    if not os.path.exists(meta):
        build_tide_atlases(tex_dir)
    cells = json.load(open(meta))['cells']
    quads = tide_quads(cells, g, cam=tuple(cam_loc))
    atl = sorted(TIDE_ATLAS)
    verts, faces, uvs, mats = [], [], [], []
    for qd in quads:
        k0 = len(verts)
        verts += [tuple(LAYOUT_U.T @ c) for c in qd['corners']]
        faces.append((k0, k0 + 1, k0 + 2, k0 + 3))
        uvs += qd['uv']
        mats.append(atl.index(qd['atlas'][-1]))
    me = bpy.data.meshes.new('ST_Tide')
    me.from_pydata(verts, [], faces)
    me.update()
    lay = me.uv_layers.new(name='UVMap')
    lv = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    lay.data.foreach_set('uv', np.array(uvs, np.float32)[lv].ravel())
    for a_ in atl:
        m = bpy.data.materials.new('ST_Tide_%s' % a_)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        N, L = nt.nodes.new, nt.links.new
        out = N('ShaderNodeOutputMaterial')
        tx = N('ShaderNodeTexImage')
        tx.image = bpy.data.images.load(os.path.join(tex_dir, 'TentacleTide_Atlas_%s.png' % a_), check_existing=True)
        tx.image.alpha_mode = 'STRAIGHT'
        tx.extension = 'CLIP'
        uvn = N('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'; L(uvn.outputs['UV'], tx.inputs['Vector'])
        em = N('ShaderNodeEmission'); L(tx.outputs['Color'], em.inputs['Color'])
        cam = N('ShaderNodeCameraData'); geo = N('ShaderNodeNewGeometry')
        sp = N('ShaderNodeSeparateXYZ'); L(geo.outputs['Position'], sp.inputs[0])
        f = _fog_factor(nt, fg, cam.outputs['View Distance'], sp.outputs['Z'], cap=0.92, cap_h=False)
        view = N('ShaderNodeVectorMath'); view.operation = 'SCALE'; view.inputs['Scale'].default_value = -1.0
        L(geo.outputs['Incoming'], view.inputs[0])
        emf = N('ShaderNodeEmission'); L(_band_colour(nt, view.outputs[0], fg), emf.inputs['Color'])
        mx = N('ShaderNodeMixShader'); L(f, mx.inputs[0]); L(em.outputs[0], mx.inputs[1]); L(emf.outputs[0], mx.inputs[2])
        tr = N('ShaderNodeBsdfTransparent')
        ma = N('ShaderNodeMixShader'); L(tx.outputs['Alpha'], ma.inputs[0]); L(tr.outputs[0], ma.inputs[1]); L(mx.outputs[0], ma.inputs[2])
        L(ma.outputs[0], out.inputs['Surface'])
        me.materials.append(m)
    me.polygons.foreach_set('material_index', mats)
    ob = bpy.data.objects.new('ST_Tide', me)
    bpy.context.scene.collection.objects.link(ob)
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    return ob


def tide_sheet(tex_dir, path):
    """Preview of the three atlases over the haze colour (with the fog they get at 5-12 km)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ims = [Image.open(os.path.join(tex_dir, 'TentacleTide_Atlas_%s.png' % a_)).convert('RGBA') for a_ in sorted(TIDE_ATLAS)]
    W = sum(i.width for i in ims) + 40
    sheet = Image.new('RGBA', (W, ims[0].height), (72, 77, 99, 255))
    x = 10
    for i in ims:
        sheet.alpha_composite(i, (x, 0))
        x += i.width + 10
    sheet.convert('RGB').resize((W // 2, ims[0].height // 2), Image.LANCZOS).save(path)
    print('tide sheet', path)


# =============================================================================================
# 8. MAIN
# =============================================================================================
SHOT_SAMPLES = dict(gate=64, flyby=64, lineup=64)          # + OIDN denoising


def main(argv=None):
    import shutil
    global OUT, CLOUD_DIR
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--only', default='tex,fbx,check,layout,tide,lineup,flyby,gate',
                    help='comma list of: tex, fbx, check, layout, tide, lineup, flyby, gate, plot, source')
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--res', nargs=2, type=int, default=[1920, 1080])
    ap.add_argument('--samples', type=int, default=0, help='0 = per-shot default (gate 64, flyby 64, lineup 64)')
    ap.add_argument('--tag', default='', help='suffix for render file names (tests)')
    a = ap.parse_args(argv)
    OUT = os.path.abspath(a.out)
    CLOUD_DIR = os.path.abspath(os.path.join(OUT, '..', 'Clouds'))
    todo = a.only.split(',')
    for d in (WORK, WIP, OUT):
        os.makedirs(d, exist_ok=True)
    tex_dir = os.path.join(OUT, 'Textures')
    t0 = time.time()
    if 'tex' in todo or not os.path.exists(os.path.join(tex_dir, 'T_Tentacle_Normal.png')):
        build_textures(tex_dir)
    elif not os.path.exists(os.path.join(WORK, 'mips', 'T_Tentacle_Normal_6.png')):
        build_mips(tex_dir)
    if 'plot' in todo:
        plot_variants(os.path.join(WIP, 'variants_plot.png'))
        silhouette_sheet(os.path.join(WIP, 'silhouettes_tips_cut.png'))          # the acceptance test
        silhouette_sheet(os.path.join(WIP, 'silhouettes_full.png'), mask_u=1.01)
    if 'fbx' in todo:
        rep = export_variants()
        with open(os.path.join(WORK, 'mesh_report.json'), 'w') as fh:
            json.dump(rep, fh, indent=1)
    if 'check' in todo:
        res = check_fbx()
        with open(os.path.join(WORK, 'fbx_reimport.json'), 'w') as fh:
            json.dump(res, fh, indent=1)
    if 'layout' in todo:
        gate_layout_json(os.path.join(OUT, 'GateLayout.json'))
    if 'tide' in todo:
        cells = build_tide_atlases(tex_dir)
        build_tide_mesh(cells, OUT)
        tide_sheet(tex_dir, os.path.join(OUT, 'Renders', 'tide_atlases.png'))
    os.makedirs(os.path.join(OUT, 'Renders'), exist_ok=True)
    for shot in ('lineup', 'flyby', 'gate'):
        if shot in todo:
            spp = a.samples or SHOT_SAMPLES[shot]
            path = os.path.join(OUT, 'Renders', '%s%s.png' % (shot, a.tag))
            t1 = time.time()
            globals()['shot_' + shot](tuple(a.res), spp, path)
            print('RENDER %s  %dx%d  %d spp  %.0fs' % (path, a.res[0], a.res[1], spp, time.time() - t1))
    if 'source' in todo or a.only == ap.get_default('only'):
        src = os.path.join(OUT, 'Source')
        os.makedirs(os.path.join(src, 'lib'), exist_ok=True)
        if os.path.abspath(__file__) != os.path.abspath(os.path.join(src, 'build_library.py')):
            shutil.copy2(os.path.abspath(__file__), os.path.join(src, 'build_library.py'))
        for fn in ('export_unity.py', 'preview_rig.py'):
            if os.path.abspath(os.path.join(LIB, fn)) != os.path.abspath(os.path.join(src, 'lib', fn)):
                shutil.copy2(os.path.join(LIB, fn), os.path.join(src, 'lib', fn))
    print('done in %.0fs' % (time.time() - t0))


if __name__ == '__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    main()
