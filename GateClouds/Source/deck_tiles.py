"""蓝白 / Lanbai · gate clouds kit · the CLOUD DECK height tiles (numpy, no Blender).

The gate's cloud sea is drawn in Unity by Lanbai/GateCloudDeck: a soft volume over a HEIGHT FIELD (the cumulus heads of
a moonlit deck), ray-marched per pixel. This script bakes the two periodic tiles it samples, with the gate's moon
(GateLayout_v2.json lights.moon: az -12, el +8, fixed in the cloud-sea frame: GateRoot never rotates) baked in:

  Deck_Detail_1024.png   period 960 m (0.9375 m / texel), linear RGBA8:
      R = height  (H_DETAIL_MIN .. H_DETAIL_MAX m about the cloud top)
      G = moon optical path at the surface (0 .. TAU_MAX_D metres of soft cloud between the point and the moon)
      B = sky ambient occlusion (0 .. 1)
      A = moon-facing (Lambert) term of the surface: (N.L + 0.08) / 1.08 from the smoothed height's normal
  Deck_Macro_512.png     period 6400 m (12.5 m / texel), linear RGBA8:
      R = macro swell height (H_MACRO_MIN .. H_MACRO_MAX m), G = macro moon path (0 .. TAU_MAX_M m),
      B = detail amplitude as a 0..1 field (normalised from AMP_MIN .. AMP_MAX; the SHADER maps it to its own
          _AmpRange 0.3 .. 0.8, the range the look was tuned with)
      A = brightness variation (0.75 .. 1.15)

  /tmp/claude-0/venv/bin/python deck_tiles.py [--out ../Textures] [--seed 3]

The numbers the shader needs are written to deck_tiles.json next to the PNGs (and are the shader defaults).
"""
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))

# the moon in the cloud-sea frame (Unity world axes: x right, y up, z ahead)
MOON = np.array([-0.2059, 0.1392, 0.9686])
MOON = MOON / np.linalg.norm(MOON)

P_D, N_D = 960.0, 1024
P_M, N_M = 6400.0, 512
H_DETAIL_MIN, H_DETAIL_MAX = -12.0, 44.0
H_MACRO_MIN, H_MACRO_MAX = -12.0, 12.0
TAU_MAX_D, TAU_MAX_M = 160.0, 400.0
AMP_MIN, AMP_MAX = 0.35, 1.2
EDGE_D = 2.5                # soft skin (m) used for the baked moon path
EDGE_M = 8.0


# ---- periodic noise ------------------------------------------------------------------------------------------------
def fbm_periodic(n, cells, octaves, rng, gain=0.5):
    """periodic value-ish noise from random Fourier phases (band-limited octaves), in [-1, 1] roughly."""
    k = np.fft.fftfreq(n) * n
    kx, ky = np.meshgrid(k, k, indexing='xy')
    kr = np.sqrt(kx ** 2 + ky ** 2)
    out = np.zeros((n, n))
    amp = 1.0
    for o in range(octaves):
        c = cells * 2 ** o
        band = np.exp(-((kr - c) / (0.5 * c + 0.5)) ** 2)
        spec = band * np.exp(2j * math.pi * rng.random((n, n)))
        f = np.real(np.fft.ifft2(spec))
        f /= f.std() + 1e-9
        out += amp * f
        amp *= gain
    return out / 2.0


def stamp_spheres(H, spheres, period, n):
    """H = max(H, top of each sphere) on a periodic grid. spheres: (x, y, z, r) in metres."""
    px = period / n
    for x, y, z, r in spheres:
        rp = r / px
        cx, cy = x / px, y / px
        i0, i1 = int(math.floor(cx - rp)), int(math.ceil(cx + rp)) + 1
        j0, j1 = int(math.floor(cy - rp)), int(math.ceil(cy + rp)) + 1
        ii = np.arange(i0, i1)
        jj = np.arange(j0, j1)
        dx = (ii + 0.5 - cx) * px
        dy = (jj + 0.5 - cy) * px
        d2 = dy[:, None] ** 2 + dx[None, :] ** 2
        top = z + np.sqrt(np.maximum(r * r - d2, 0.0))
        top = np.where(d2 < r * r, top, -1e9)
        sub = H[np.ix_(jj % n, ii % n)]
        H[np.ix_(jj % n, ii % n)] = np.maximum(sub, top)


def cumulus_heads(rng, period, coverage, n_heads, r_range):
    """a field of cumulus heads: parents (big domes, mostly sunk) with cauliflower children on their upper sides."""
    out = []
    n = coverage.shape[0]
    tries = 0
    while len(out) < n_heads and tries < n_heads * 20:
        tries += 1
        x, y = rng.random(2) * period
        c = coverage[int(y / period * n) % n, int(x / period * n) % n]
        if rng.random() > c:
            continue
        r = rng.uniform(*r_range) * (0.65 + 0.55 * c)
        z = -0.18 * r + rng.normal(0, 0.10) * r + 5.0 * (c - 0.5) - 6.0
        out.append((x, y, z, r, 0))
    kids = []
    for x, y, z, r, _ in out:
        stack = [(x, y, z, r, 0)]
        while stack:
            px_, py_, pz_, pr_, lv = stack.pop()
            if lv >= 3 or pr_ < 1.6:
                continue
            for _ in range(rng.integers(3, 7) if lv == 0 else rng.integers(2, 5)):
                el = math.radians(rng.uniform(18, 72))
                az = rng.uniform(0, 2 * math.pi)
                cr = pr_ * rng.uniform(0.34, 0.58)
                dist = pr_ * rng.uniform(0.62, 0.92)
                cx = px_ + dist * math.cos(el) * math.cos(az)
                cy = py_ + dist * math.cos(el) * math.sin(az)
                cz = pz_ + dist * math.sin(el)
                kids.append((cx, cy, cz, cr))
                stack.append((cx, cy, cz, cr, lv + 1))
    return [(x, y, z, r) for x, y, z, r, _ in out] + kids


def periodic_sample(A, period, X, Y):
    n = A.shape[0]
    return ndimage.map_coordinates(A, [Y / period * n - 0.5, X / period * n - 0.5], order=1, mode='grid-wrap')


def moon_path(H, period, edge, s_max, ds):
    """metres of soft cloud between each surface texel and the moon (horizontal step ds along the moon's azimuth)."""
    n = H.shape[0]
    px = period / n
    g = (np.arange(n) + 0.5) * px
    X, Y = np.meshgrid(g, g, indexing='xy')
    dh = MOON[[0, 2]] / np.linalg.norm(MOON[[0, 2]])
    tan_el = MOON[1] / np.linalg.norm(MOON[[0, 2]])
    tau = np.zeros_like(H)
    seg = ds / math.cos(math.atan(tan_el))
    for s in np.arange(ds * 0.5, s_max, ds):
        h = periodic_sample(H, period, X + dh[0] * s, Y + dh[1] * s)
        over = h - (H + s * tan_el)
        tau += np.clip(over / edge + 0.5, 0.0, 1.0) * seg
    return tau


def sky_ao(H, period, radii):
    """occlusion of the sky dome: how far the surroundings rise above the point, at several radii."""
    n = H.shape[0]
    px = period / n
    ao = np.ones_like(H)
    for r in radii:
        sig = r / px
        m = ndimage.gaussian_filter(H, sig, mode='wrap')
        mx = ndimage.maximum_filter(H, size=max(3, int(2 * sig) | 1), mode='wrap')
        rise = np.clip((0.6 * m + 0.4 * mx) - H, 0.0, None)
        ao *= 1.0 / (1.0 + rise / (1.6 * r))
    return ao


def to8(a):
    return np.clip(np.round(a * 255.0), 0, 255).astype(np.uint8)


def main():
    a = sys.argv[1:]
    out = os.path.abspath(a[a.index('--out') + 1]) if '--out' in a else os.path.join(os.path.dirname(HERE), 'Textures')
    seed = int(a[a.index('--seed') + 1]) if '--seed' in a else 3
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(seed)
    t0 = time.time()

    # ---- detail tile -------------------------------------------------------------------------------------------------
    cov = fbm_periodic(N_D, 9, 3, rng)
    cov = np.clip(0.50 + 0.85 * cov, 0.08, 1.0)
    base = -11.0 + 3.0 * fbm_periodic(N_D, 6, 4, rng)
    H = base.copy()
    heads = cumulus_heads(rng, P_D, cov, 1700, (10.0, 26.0))
    stamp_spheres(H, heads, P_D, N_D)
    H += 0.7 * fbm_periodic(N_D, 120, 3, rng)          # cauliflower grain
    H = ndimage.gaussian_filter(H, 0.6, mode='wrap')
    print('detail heads %d  H %.1f .. %.1f  mean %.1f  (%.0fs)' % (len(heads), H.min(), H.max(), H.mean(), time.time() - t0))
    tau = moon_path(H, P_D, EDGE_D, 360.0, 1.0)
    tau = ndimage.gaussian_filter(tau, 2.0, mode='wrap')     # multiple scattering softens the moon's shadow lanes
    print('detail tau p50 %.1f p95 %.1f max %.1f (%.0fs)' % (np.percentile(tau, 50), np.percentile(tau, 95), tau.max(),
                                                          time.time() - t0))
    ao = sky_ao(H, P_D, (3.0, 10.0, 28.0))
    Hs = ndimage.gaussian_filter(H, 1.0, mode='wrap')
    px = P_D / N_D
    gx = (np.roll(Hs, -1, 1) - np.roll(Hs, 1, 1)) / (2 * px)
    gz = (np.roll(Hs, -1, 0) - np.roll(Hs, 1, 0)) / (2 * px)
    nrm = np.stack([-gx, np.ones_like(H), -gz], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    fr = np.clip((nrm @ MOON + 0.08) / 1.08, 0.0, 1.0)
    img = np.stack([(H - H_DETAIL_MIN) / (H_DETAIL_MAX - H_DETAIL_MIN), np.clip(tau / TAU_MAX_D, 0, 1),
                    np.clip(ao, 0, 1), np.clip(fr, 0, 1)], -1)
    Image.fromarray(to8(img), 'RGBA').save(os.path.join(out, 'Deck_Detail_1024.png'))

    # ---- macro tile --------------------------------------------------------------------------------------------------
    Mh = 7.0 * fbm_periodic(N_M, 5, 4, rng)
    Mh = np.clip(Mh, H_MACRO_MIN + 1, H_MACRO_MAX - 1)
    mtau = ndimage.gaussian_filter(moon_path(Mh, P_M, EDGE_M, 2400.0, 12.5), 1.5, mode='wrap')
    amp = np.clip(0.85 + 0.45 * fbm_periodic(N_M, 7, 3, rng) + 0.012 * Mh, AMP_MIN, AMP_MAX)
    var = np.clip(0.95 + 0.12 * fbm_periodic(N_M, 11, 2, rng), 0.75, 1.15)
    img = np.stack([(Mh - H_MACRO_MIN) / (H_MACRO_MAX - H_MACRO_MIN), np.clip(mtau / TAU_MAX_M, 0, 1),
                    (amp - AMP_MIN) / (AMP_MAX - AMP_MIN), (var - 0.75) / 0.40], -1)
    Image.fromarray(to8(img), 'RGBA').save(os.path.join(out, 'Deck_Macro_512.png'))
    meta = dict(period_detail_m=P_D, period_macro_m=P_M, h_detail=[H_DETAIL_MIN, H_DETAIL_MAX],
                h_macro=[H_MACRO_MIN, H_MACRO_MAX], tau_max=[TAU_MAX_D, TAU_MAX_M], amp_field_from=[AMP_MIN, AMP_MAX],
                shader_amp_range=[0.3, 0.8],
                var=[0.75, 1.15], moon_dir=MOON.round(4).tolist(), seed=seed,
                detail_stats=dict(h_mean=float(H.mean()), h_p95=float(np.percentile(H, 95))))
    json.dump(meta, open(os.path.join(out, 'deck_tiles.json'), 'w'), indent=1)
    print('done %.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
