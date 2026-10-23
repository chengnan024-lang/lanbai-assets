"""Textures for act 4c (all tileable along u, linear data, imported with sRGB OFF):

Inside_Fringe_2048x256.png   the torn edge's fibres: u = along the edge (one tile = FRINGE_TILE_M metres), v = 0 at the
                             cloth edge .. 1 at the longest fibre tips.  R = fibre brightness, G = fibre coverage
                             (alpha for the dark threads), B = clump id noise (per-clump brightness), A = 1.
Inside_Weave_1024.png        the inner face of the cloth: R = warp streaks (vertical, 2-6 m wide at the shader's
                             tiling), G = fine weave (0.3 m), B = slow blotches. Tileable in both directions.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inside_def as D  # noqa: E402

TEX = os.path.join(D.KIT, 'Textures')
os.makedirs(TEX, exist_ok=True)
FRINGE_TILE_M = 64.0      # metres of edge per fringe tile (the mesh writes u = arclength / 64)


def wrap_noise(shape, sigma, seed):
    r = np.random.default_rng(seed).standard_normal(shape)
    f = gaussian_filter(r, sigma, mode='wrap')
    return f / (f.std() + 1e-9)


def fringe(W=2048, Hh=256, seed=7):
    """bundles of torn weft ends: clumps of 3-12 strands, lengths 15-100 % of the tile height, some broken short,
    tips thinner and dimmer, slight wave; a dense band at the very edge (the cut weave)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((Hh, W), np.float32)
    cov = np.zeros((Hh, W), np.float32)
    v = (np.arange(Hh) + 0.5)[:, None] / Hh
    x = np.arange(W)[None, :].astype(np.float32)
    clump_b = np.zeros(W, np.float32)
    pos = 0.0
    while pos < W:
        n = int(rng.integers(2, 8))
        cw = rng.uniform(6, 26)                                  # clump width (px)
        cb = rng.uniform(0.45, 1.0)
        # r03: most torn weft ends are short; a few long ones (a fur of equal-length fibres read as frost)
        L0 = rng.uniform(0.55, 1.0) if rng.random() < 0.12 else rng.uniform(0.06, 0.30)
        lean = rng.normal(0, 0.06)
        for _ in range(n):
            xc = pos + rng.uniform(0, cw)
            L = np.clip(L0 * rng.uniform(0.55, 1.15), 0.05, 1.0)
            w0 = rng.uniform(0.45, 1.3)                           # strand half width at the root (px)
            amp, fr, ph = rng.uniform(0, 3.0), rng.uniform(1, 4), rng.uniform(0, 6.28)
            b = cb * rng.uniform(0.6, 1.0)
            xs = xc + lean * v[:, 0] * Hh + amp * np.sin(fr * v[:, 0] * 6.283 + ph) * v[:, 0]
            wv = w0 * (1.0 - 0.75 * (v[:, 0] / L)) * (v[:, 0] < L)
            for dx in (-W, 0, W):
                d = np.abs(x - (xs[:, None] + dx))
                prof = np.clip(1.0 - d / (wv[:, None] + 0.6), 0, 1) * (wv[:, None] > 0)
                tipfade = np.clip((L - v) / 0.12, 0, 1) ** 0.7
                img = np.maximum(img, prof * b * (0.55 + 0.45 * tipfade))
                cov = np.maximum(cov, prof)
        lo, hi = int(pos), int(min(W, pos + cw))
        clump_b[lo:hi] = cb
        pos += cw + rng.uniform(25, 140)       # r04: half the density
    # the cut weave at the edge: a dense, slightly broken band
    band = np.clip(1.0 - v / 0.07, 0, 1) ** 1.5 * (0.6 + 0.4 * np.clip(wrap_noise((1, W), (0, 3), seed + 1), -1, 1))
    img = np.maximum(img, band * 0.9)
    cov = np.maximum(cov, np.clip(band * 1.4, 0, 1))
    blur = gaussian_filter(img, 0.6, mode='wrap')
    out = np.zeros((Hh, W, 4), np.uint8)
    out[..., 0] = np.clip(blur * 255 + 0.5, 0, 255)
    out[..., 1] = np.clip(gaussian_filter(cov, 0.6, mode='wrap') * 255 + 0.5, 0, 255)
    out[..., 2] = np.clip(np.tile(clump_b[None, :], (Hh, 1)) * 255, 0, 255)
    out[..., 3] = 255
    return out[::-1]            # PNG top row = v 1 (Unity samples row 0 at the bottom)


def weave(N=1024, seed=11):
    warp = wrap_noise((N, N), (60.0, 2.2), seed) * 0.65 + wrap_noise((N, N), (30.0, 0.9), seed + 1) * 0.35
    fine = wrap_noise((N, N), (1.2, 0.5), seed + 2) * 0.6 + wrap_noise((N, N), (0.6, 2.5), seed + 3) * 0.4
    blot = wrap_noise((N, N), (90.0, 70.0), seed + 4)
    f = lambda a: np.clip(a * 0.22 + 0.5, 0, 1)   # noqa: E731
    out = np.stack([f(warp), f(fine), f(blot), np.ones((N, N))], -1)
    return (out * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    Image.fromarray(fringe(), 'RGBA').save(os.path.join(TEX, 'Inside_Fringe_2048x256.png'))
    Image.fromarray(weave(), 'RGBA').save(os.path.join(TEX, 'Inside_Weave_1024.png'))
    print('textures ->', TEX)
