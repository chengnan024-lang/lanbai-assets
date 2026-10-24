# -*- coding: utf-8 -*-
"""Sea kit textures (bible §8.1 #7). Deterministic (fixed seeds). numpy + pillow only.

  SeaN_Large_1024.png   tileable FFT ocean normal, 64 m tile (wind waves)
  SeaN_Small_1024.png   tileable FFT ocean normal, 9 m tile (ripples / short gravity-capillary waves)
  SeaMacro_512.png      1.5 km tile: R = rippled (1) / calm slick (0), wind-streaked; G = swell / wind-gust variation
  Caustics_8x8_2048.png 64-frame LOOPING caustics flipbook (8 x 8 frames of 256^2, R8), one tile = 1 m of sea floor,
                        loop = 1 / 0.3 Hz = 3.333 s; made by refracting sunlight through an animated FFT surface and
                        splatting the photons on a plane (real focusing, not noise)
  ShaftStreaks_256.png  light-shaft streaks (R: streaks across U, smooth along V; G: second, finer set)
  sea_textures_meta.json  slope rms of each normal map and the UNRESOLVED slope variance per mip level (the shader's
                        Toksvig term: what the mip chain averages away goes into the GGX roughness instead)

NORMAL MAP CONVENTION (both maps): the texture stores the tangent-space normal of a horizontal plane whose U runs along
world +x and V along world +z: n_ts = normalize(-dh/dx, -dh/dz, 1) (OpenGL style, G = +z). The shader unpacks it with
UnpackNormal and builds the WORLD normal itself as (n.x, n.z, n.y) -- it never uses mesh tangents.
PNG row 0 is the TOP of the image = V = 1 (Unity's convention), so arrays indexed [iz, ix] are flipped on save.
"""
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
OUT = os.path.join(KIT, 'Textures')
G = 9.81


def kgrid(n, tile):
    k1 = 2.0 * np.pi * np.fft.fftfreq(n, d=tile / n)
    kx, kz = np.meshgrid(k1, k1, indexing='xy')      # arrays [iz, ix]
    return kx, kz


def phillips(kx, kz, wind, wind_dir, small_cut, dir_pow=2.0, swell_suppress=0.15):
    k = np.sqrt(kx ** 2 + kz ** 2)
    k = np.where(k == 0, 1e-9, k)
    Lw = wind ** 2 / G
    wd = np.array(wind_dir, float) / np.linalg.norm(wind_dir)
    c = (kx * wd[0] + kz * wd[1]) / k
    dirf = np.abs(c) ** dir_pow
    dirf = np.where(c < 0, dirf * swell_suppress, dirf)          # waves running against the wind are weak
    P = np.exp(-1.0 / (k * Lw) ** 2) / k ** 4 * dirf * np.exp(-(k * small_cut) ** 2)
    P[0, 0] = 0.0
    return P


def spectrum_field(n, tile, wind, wind_dir, small_cut, seed, target_rms_slope, dir_pow=2.0):
    """returns h0 (complex, [iz, ix]) scaled so that the total rms slope = target, plus kx, kz, P"""
    rng = np.random.default_rng(seed)
    kx, kz = kgrid(n, tile)
    P = phillips(kx, kz, wind, wind_dir, small_cut, dir_pow)
    xi = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) / np.sqrt(2.0)
    h0 = xi * np.sqrt(P)
    # rms slope of the realised (Hermitian, real) field at t = 0
    sx, sz = slopes_at(h0, kx, kz, 0.0)
    rms = np.sqrt(np.mean(sx ** 2 + sz ** 2))
    h0 *= target_rms_slope / rms
    return h0, kx, kz, P * (target_rms_slope / rms) ** 2


def slopes_at(h0, kx, kz, t=0.0, loop=None, slow=1.0):
    """real slope fields at time t. Hermitian-symmetric evolution h(k,t) = h0 e^{iwt} + conj(h0(-k)) e^{-iwt}.
    loop: if set, w is quantised to multiples of 2 pi / loop so the animation repeats exactly."""
    k = np.sqrt(kx ** 2 + kz ** 2)
    w = np.sqrt(G * k + 0.074 / 1000.0 * k ** 3)                # gravity-capillary dispersion
    if loop:
        w0 = 2.0 * np.pi / loop
        w = np.maximum(np.round(w * slow / w0), 1.0) * w0
    n = h0.shape[0]
    idx = (-np.arange(n)) % n
    h0m = np.conj(h0[np.ix_(idx, idx)])
    ht = h0 * np.exp(1j * w * t) + h0m * np.exp(-1j * w * t)
    sx = np.real(np.fft.ifft2(1j * kx * ht))
    sz = np.real(np.fft.ifft2(1j * kz * ht))
    return sx, sz


def unresolved_variance(P_scaled, kx, kz, n):
    """slope variance carried by frequencies a mip level can no longer represent: mip m keeps |k_axis| < pi*n/(tile*2^m).
    Returned relative to the per-texel kx, kz units (rad/m) -> slope variance (dimensionless)."""
    k2 = kx ** 2 + kz ** 2
    # the spectrum P is per FFT bin; slope variance = sum(k^2 P) * (normalisation of ifft2) -> compute empirically
    total = np.sum(k2 * P_scaled)
    kmax = np.max(np.abs(kx))
    out = []
    for m in range(int(np.log2(n)) + 1):
        cut = kmax / 2 ** m
        kept = (np.abs(kx) < cut) & (np.abs(kz) < cut)
        out.append(float(np.sum(k2 * P_scaled * (~kept)) / total))
    return out          # fraction of the total slope variance that is unresolved at mip m


def save_normal(sx, sz, path, slope_scale=1.0):
    nx, nz = -sx * slope_scale, -sz * slope_scale
    ny = np.ones_like(nx)
    ln = np.sqrt(nx ** 2 + nz ** 2 + ny ** 2)
    img = np.stack([nx / ln, nz / ln, ny / ln], -1) * 0.5 + 0.5          # R = x, G = z (V), B = up
    img = np.flipud(img)                                                  # row 0 = V 1
    Image.fromarray(np.clip(np.round(img * 255.0), 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)


def make_normals(meta):
    specs = [
        # name, tile m, wind m/s, wind dir (x, z), small-scale cutoff m, seed, target rms slope, dir power
        ('SeaN_Large_1024', 64.0, 7.5, (1.0, 0.35), 0.02, 11, 0.11, 2.0),
        ('SeaN_Small_1024', 9.0, 2.6, (0.7, 1.0), 0.004, 23, 0.09, 1.0),
    ]
    n = 1024
    for name, tile, wind, wd, cut, seed, rms, dp in specs:
        h0, kx, kz, P = spectrum_field(n, tile, wind, wd, cut, seed, rms, dp)
        sx, sz = slopes_at(h0, kx, kz, 0.0)
        save_normal(sx, sz, os.path.join(OUT, name + '.png'))
        unres = unresolved_variance(np.abs(h0) ** 2, kx, kz, n)
        meta[name] = dict(tile_m=tile, wind_ms=wind, wind_dir_xz=list(wd), rms_slope=round(float(np.sqrt(np.mean(sx ** 2 + sz ** 2))), 4),
                          slope_var_total=round(float(np.mean(sx ** 2 + sz ** 2)), 6),
                          unresolved_fraction_per_mip=[round(u, 5) for u in unres],
                          note='slopes stored at x1 (n_ts = normalize(-sx, -sz, 1)); _NormalStrength scales them in the shader')
        print(name, 'rms slope', meta[name]['rms_slope'], 'unresolved by mip', meta[name]['unresolved_fraction_per_mip'][:8])


def fbm_tile(n, octaves, seed, aniso=(1.0, 1.0), base=4):
    """tileable anisotropic fractal noise via filtered random spectrum, 0..1"""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n) * n
    fx, fz = np.meshgrid(f, f, indexing='xy')
    r = np.sqrt((fx * aniso[0]) ** 2 + (fz * aniso[1]) ** 2)
    r[0, 0] = 1.0
    amp = np.where((r >= base * 0.5) & (r < base * 2 ** octaves), r ** -1.6, 0.0)
    ph = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    x = np.real(np.fft.ifft2(ph * amp))
    x = (x - x.mean()) / (x.std() + 1e-9)
    return x


def make_macro(meta):
    n = 512
    # wind-aligned slicks: stretched along the wind (x) -> aniso compresses x frequencies
    a = fbm_tile(n, 5, 101, aniso=(2.6, 1.0), base=3)
    b = fbm_tile(n, 4, 102, aniso=(1.0, 1.0), base=2)
    ripple = 1.0 / (1.0 + np.exp(-(a * 1.15 + 0.55) * 2.2))         # ~70 % rippled, soft-edged calm slicks
    gust = 0.5 + 0.5 * np.tanh(b * 0.8)
    img = np.stack([ripple, gust, np.zeros_like(ripple)], -1)
    Image.fromarray(np.clip(np.round(np.flipud(img) * 255), 0, 255).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'SeaMacro_512.png'), optimize=True)
    meta['SeaMacro_512'] = dict(tile_m=1500.0, R='rippled 1 / calm 0', G='gust variation 0..1', rippled_fraction=round(float(np.mean(ripple > 0.5)), 3))
    print('macro rippled fraction', meta['SeaMacro_512']['rippled_fraction'])


def band_field(n, tile, lam0, sigma, seed, target_rms_slope, aniso=(1.0, 0.4)):
    """isotropic-ish band-pass spectrum around wavelength lam0 (pool / shallow-sea caustic ripples)"""
    rng = np.random.default_rng(seed)
    kx, kz = kgrid(n, tile)
    k = np.sqrt(kx ** 2 + kz ** 2)
    k = np.where(k == 0, 1e-9, k)
    k0 = 2 * np.pi / lam0
    c = np.abs(kx * aniso[0] + kz * aniso[1]) / (k * np.hypot(*aniso))
    P = np.exp(-0.5 * (np.log(k / k0) / sigma) ** 2) / k ** 2 * (0.45 + 0.55 * c ** 2)
    P[0, 0] = 0
    xi = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) / np.sqrt(2.0)
    h0 = xi * np.sqrt(P)
    sx, sz = slopes_at(h0, kx, kz, 0.0)
    h0 *= target_rms_slope / np.sqrt(np.mean(sx ** 2 + sz ** 2))
    return h0, kx, kz


def make_caustics(meta, rms_slope=0.065, lam0=0.32, depth=2.2, n_s=1024, jit=4):
    """64 frames, loop 1/0.3 Hz. Surface tile 1 m, n_s^2 x jit photons per frame, floor plane `depth` below,
    sun at 70 deg elevation (bible 7a). Time is dream-slowed: every wave runs at 1-3 x 0.3 Hz instead of its real
    (~3 Hz) frequency, so the net drifts and breathes rather than flickering (VR comfort; bible '0.3 Hz')."""
    n_t, frames, tile = 256, 64, 1.0
    loop = 1.0 / 0.3
    h0, kx, kz = band_field(n_s, tile, lam0, 0.45, 77, rms_slope)
    sun = np.array([np.cos(np.radians(70.0)) * 0.7, -np.sin(np.radians(70.0)), np.cos(np.radians(70.0)) * 0.7])
    sun /= np.linalg.norm(sun)
    eta = 1.0 / 1.333
    xs = (np.arange(n_s) + 0.5) / n_s * tile
    X, Z = np.meshgrid(xs, xs, indexing='xy')
    rng = np.random.default_rng(5)
    atlas = np.zeros((8 * n_t, 8 * n_t), np.float32)
    peaks, means = [], []
    kf = np.fft.fftfreq(n_t)
    gx = np.exp(-0.5 * (2 * np.pi * kf * 0.9) ** 2)
    for f in range(frames):
        t = loop * f / frames
        sx, sz = slopes_at(h0, kx, kz, t, loop=loop, slow=0.09)
        nrm = np.stack([-sx, np.ones_like(sx), -sz], -1)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
        cosi = -(nrm @ sun)
        kk = 1.0 - eta ** 2 * (1.0 - cosi ** 2)
        T = eta * sun[None, None, :] + (eta * cosi - np.sqrt(np.maximum(kk, 0)))[..., None] * nrm
        s = depth / -T[..., 1]
        acc = np.zeros(n_t * n_t, np.float64)
        for j in range(jit):
            jx = (rng.random(X.shape) - 0.5) * tile / n_s
            jz = (rng.random(X.shape) - 0.5) * tile / n_s
            px = ((X + jx + T[..., 0] * s) / tile % 1.0) * n_t - 0.5
            pz = ((Z + jz + T[..., 2] * s) / tile % 1.0) * n_t - 0.5
            ix, iz = np.floor(px).astype(int), np.floor(pz).astype(int)
            fx, fz = (px - ix).ravel(), (pz - iz).ravel()
            ix, iz = ix.ravel(), iz.ravel()
            for dx, wx in ((0, 1 - fx), (1, fx)):
                for dz, wz in ((0, 1 - fz), (1, fz)):
                    acc += np.bincount(((iz + dz) % n_t) * n_t + (ix + dx) % n_t, weights=wx * wz, minlength=n_t * n_t)
        acc = acc.reshape(n_t, n_t)
        acc /= acc.mean()
        acc = np.real(np.fft.ifft2(np.fft.fft2(acc) * gx[None, :] * gx[:, None]))
        peaks.append(float(np.percentile(acc, 99.9)))
        means.append(float(np.percentile(acc, 50)))
        enc = np.tanh(acc / 4.0)            # stored = tanh(I / 4): mean 1 -> 0.245; shader: I = 4 atanh(stored)
        r, c = divmod(f, 8)
        atlas[r * n_t:(r + 1) * n_t, c * n_t:(c + 1) * n_t] = np.flipud(enc)
    Image.fromarray(np.clip(np.round(atlas * 255), 0, 255).astype(np.uint8), 'L').save(os.path.join(OUT, 'Caustics_8x8_2048.png'), optimize=True)
    meta['Caustics_8x8_2048'] = dict(frames=64, grid=[8, 8], frame_px=n_t, tile_m=tile, loop_s=round(loop, 4), floor_depth_m=depth,
                                     ripple_wavelength_m=lam0, ripple_rms_slope=rms_slope,
                                     encoding='stored = tanh(I / 4), I = mean-1 caustic irradiance; decode I = 4 atanh(min(s, 0.999))',
                                     frame_uv='frame f: u0 = (f % 8)/8, v0 = 1 - (f//8 + 1)/8 (Unity v up)',
                                     p999=round(float(np.mean(peaks)), 2), median=round(float(np.mean(means)), 3), sun_elevation_deg=70)
    print('caustics p99.9', meta['Caustics_8x8_2048']['p999'], 'median', meta['Caustics_8x8_2048']['median'])


def make_streaks(meta):
    n = 256
    rng = np.random.default_rng(9)
    f = np.fft.fftfreq(n) * n
    # streaks: noise varying across U only (plus a very slow V drift)
    a = np.zeros(n, complex)
    for s, w in ((2, 1.0), (5, 0.7), (11, 0.45), (23, 0.3), (41, 0.18)):
        a[s] = w * np.exp(1j * rng.uniform(0, 2 * np.pi))
        a[-s] = np.conj(a[s])
    u = np.real(np.fft.ifft(a)) * n
    u = (u - u.min()) / (u.max() - u.min())
    v = np.sin(np.linspace(0, 2 * np.pi, n, endpoint=False))[:, None] * 0.06
    R = np.clip(np.broadcast_to(u[None, :] ** 1.6, (n, n)) + v, 0, 1)
    b = np.zeros(n, complex)
    for s, w in ((7, 1.0), (17, 0.8), (31, 0.6), (57, 0.4)):
        b[s] = w * np.exp(1j * rng.uniform(0, 2 * np.pi))
        b[-s] = np.conj(b[s])
    u2 = np.real(np.fft.ifft(b)) * n
    u2 = (u2 - u2.min()) / (u2.max() - u2.min())
    Gc = np.broadcast_to(u2[None, :] ** 2.0, (n, n))
    img = np.stack([R, Gc, np.zeros((n, n))], -1)
    Image.fromarray(np.clip(np.round(img * 255), 0, 255).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'ShaftStreaks_256.png'), optimize=True)
    meta['ShaftStreaks_256'] = dict(R='coarse streaks across U (mean %.2f)' % float(R.mean()), G='fine streaks across U', V='nearly constant (tile along the shaft)')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    meta = {}
    make_normals(meta)
    make_macro(meta)
    make_streaks(meta)
    make_caustics(meta)
    json.dump(meta, open(os.path.join(OUT, 'sea_textures_meta.json'), 'w'), indent=1)
    print('done')
