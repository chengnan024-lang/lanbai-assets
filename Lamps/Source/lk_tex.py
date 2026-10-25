# -*- coding: utf-8 -*-
"""蓝白 · 灯与杆套件的贴图（numpy 生成，确定性；不依赖网络素材）。

每套材质 3 张（全部 2 的幂）：
  *_Albedo.png   sRGB 反照率（守 §1.6：非金属 48–231，任何东西 ≤ 235）
  *_Normal.png   切线空间法线（OpenGL，+Y = 贴图上方 = UV v 增大的方向），线性
  *_Mask.png     线性数据：R = 金属度（0/1），G = 干的光滑度，B = 腔体 AO，A = 湿润时“水走的路”（0 = 表面只是潮，
                 1 = 水流过的地方：更暗、更亮的膜）。shader（Lanbai/LampKit）按 _Udon_Wetness 用它（见 README §3）。
用法：python3 lk_tex.py <outdir> [set ...]
"""
import os
import sys

import numpy as np
from PIL import Image

RNG_SEED = 20261022


def lin_of(s):
    s = np.asarray(s, float) / 255.0
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)


def to_srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


def hexlin(h):
    h = h.lstrip('#')
    return lin_of([int(h[i:i + 2], 16) for i in (0, 2, 4)])


def fbm(shape, lmin, lmax, seed, beta=2.0, aspect=(1.0, 1.0)):
    """Periodic band-limited noise, unit std. lmin/lmax in pixels (isotropic in metres given aspect = metres/px (y, x))."""
    H, W = shape
    r = np.random.default_rng(seed)
    F = np.fft.rfft2(r.normal(size=shape))
    ky = np.fft.fftfreq(H, aspect[0])[:, None]
    kx = np.fft.rfftfreq(W, aspect[1])[None, :]
    k = np.hypot(kx, ky)
    amp = np.where((k >= 1 / lmax) & (k <= 1 / lmin), np.maximum(k, 1e-9) ** (-beta / 2), 0)
    f = np.fft.irfft2(F * amp, s=shape)
    return f / (f.std() + 1e-12)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def normal_from_height(h, mpp_y, mpp_x, strength=1.0, wrap=True):
    """h in metres. Returns OpenGL normal (y up = row decreasing? no: our arrays are stored row 0 = TOP of the PNG =
    v = 1). dh/dv: v increases upward = toward row 0."""
    if wrap:
        dhx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * mpp_x)
        dhy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) / (2 * mpp_y)     # +v = up the image
    else:
        dhx = np.gradient(h, mpp_x, axis=1)
        dhy = -np.gradient(h, mpp_y, axis=0)
    n = np.stack([-dhx * strength, -dhy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n


def save_rgb(path, rgb01):
    Image.fromarray(np.round(np.clip(rgb01, 0, 1) * 255).astype(np.uint8), 'RGB').save(path, optimize=True)


def save_rgba(path, rgba01):
    Image.fromarray(np.round(np.clip(rgba01, 0, 1) * 255).astype(np.uint8), 'RGBA').save(path, optimize=True)


def save_set(out, name, alb_lin, nrm, metal, smooth, ao, flow):
    os.makedirs(out, exist_ok=True)
    srgb = to_srgb(alb_lin)
    save_rgb(os.path.join(out, name + '_Albedo.png'), srgb)
    save_rgb(os.path.join(out, name + '_Normal.png'), nrm * 0.5 + 0.5)
    save_rgba(os.path.join(out, name + '_Mask.png'), np.stack([metal, smooth, ao, flow], -1))
    s8 = np.round(srgb * 255)
    print('%-26s albedo sRGB mean %5.1f  p1 %5.1f  p99 %5.1f  max %3.0f' % (name, s8.mean(), np.percentile(s8, 1), np.percentile(s8, 99), s8.max()))


# ---------------------------------------------------------------------------------------------- streaks
def streak_field(H, W, mpp_y, mpp_x, sources, rng, wrap_u=True):
    """Water / rust streaks running DOWN the surface (rows increase downward = v decreasing).
    sources: list of dict(u, row0, length_m, width_m, strength, wobble_m). Returns intensity 0..1 (H, W)."""
    out = np.zeros((H, W))
    xs = np.arange(W)
    for s in sources:
        r0 = int(s['row0'])
        n = int(s['length_m'] / mpp_y)
        rows = np.arange(r0, min(H, r0 + n))
        if len(rows) == 0:
            continue
        t = (rows - r0) / max(n, 1)
        # wobbly centre line (random walk, smoothed)
        walk = np.cumsum(rng.normal(0, 1, len(rows)))
        k = max(3, int(0.15 / mpp_y))
        walk = np.convolve(walk, np.ones(k) / k, mode='same')
        walk = walk / (np.abs(walk).max() + 1e-9) * s['wobble_m'] / mpp_x
        cx = s['u'] * W + walk
        wpx = np.maximum(s['width_m'] / mpp_x * (1 - 0.6 * t), 0.6)
        # intensity fades with distance and breaks up
        brk = 0.55 + 0.45 * np.clip(np.convolve(rng.normal(0, 1, len(rows)), np.ones(9) / 9, mode='same') * 2.5, -1, 1)
        amp = s['strength'] * (1 - t) ** s.get('fade', 1.3) * brk
        d = xs[None, :] - cx[:, None]
        if wrap_u:
            d = (d + W / 2) % W - W / 2
        prof = np.exp(-0.5 * (d / wpx[:, None]) ** 2)
        out[rows] = np.maximum(out[rows], prof * amp[:, None])
    return np.clip(out, 0, 1)


# ---------------------------------------------------------------------------------------------- concrete pole
def concrete_pole(out, name, fixtures, H=4096, W=512, height=9.0, circ=None, periodic=False, seed=1):
    """fixtures: list of (u, z_m, kind) where water and rust run down from (crossarm clamp, lamp arm clamps).
    u = angle / 2pi (u 0 = +X = toward the road)."""
    rng = np.random.default_rng(RNG_SEED + seed)
    circ = circ or 2 * np.pi * 0.118          # mean circumference (m)
    mpp_x = circ / W
    mpp_y = height / H
    row_of = lambda z: (1 - z / height) * H   # row 0 = top of the pole
    z = (1 - (np.arange(H) + 0.5) / H)[:, None] * height
    u = ((np.arange(W) + 0.5) / W)[None, :]
    # base: spun concrete, smooth with laitance; low-frequency mottling (blotchy cement), fine sand speckle
    mott = fbm((H, W), 0.25 / mpp_y, 3.0 / mpp_y, rng.integers(1e9), 2.2, aspect=(1, mpp_x / mpp_y))
    fine = fbm((H, W), 1.5, 12.0, rng.integers(1e9), 1.0)
    rings = np.sin(z / 0.031 * 2 * np.pi + 2.0 * fbm((H, 1), 30, 600, rng.integers(1e9))) * 0.5 + 0.5   # spinning rings
    base = 0.22 * (1 + 0.07 * mott + 0.035 * fine) * (1 - 0.025 * rings)
    # mould seams (two, 180 deg apart, at u 0.25 / 0.75 = facing along the road): a 3 mm ridge, slightly lighter
    seam = np.zeros((1, W))
    for us in (0.25, 0.75):
        d = (u - us + 0.5) % 1 - 0.5
        seam = np.maximum(seam, np.exp(-0.5 * (d * circ / 0.0012) ** 2))
    seam = seam * (0.7 + 0.3 * np.clip(fbm((H, 1), 40, 800, rng.integers(1e9)), -1, 1))
    base = base * (1 + 0.06 * seam)
    # bug holes (air voids, 1-3 mm): dark dots
    holes = np.zeros((H, W))
    nh = int(height * circ * 260)
    hy = rng.integers(0, H, nh); hx = rng.integers(0, W, nh)
    holes[hy, hx] = rng.uniform(0.4, 1.0, nh)
    from scipy import ndimage
    holes = ndimage.gaussian_filter(holes, 0.7, mode='wrap') * 3
    holes = np.clip(holes, 0, 1)
    # through-holes for fittings (Ø 20 mm), a few pairs on the X faces
    bolt = np.zeros((H, W))
    yy, xx = np.mgrid[0:H, 0:W]
    for zb in ((7.6, 7.85, 8.25) if not periodic else ()):
        for ub in (0.0, 0.5):
            dy = (yy - row_of(zb)) * mpp_y
            dx = (((xx + 0.5) / W - ub + 0.5) % 1 - 0.5) * circ
            r = np.hypot(dx, dy)
            bolt = np.maximum(bolt, sstep(0.011, 0.009, r))
    # splash zone (bottom 0.6 m): darker, dirtier, a little moss (desaturated olive)
    splash = sstep(0.75, 0.05, z) * (0.8 + 0.2 * np.clip(fbm((H, W), 20, 400, rng.integers(1e9)), -1, 1)) if not periodic else np.zeros((H, 1))
    moss = np.clip(fbm((H, W), 4, 60, rng.integers(1e9)) - 1.2, 0, 1) * sstep(0.45, 0.0, z) if not periodic else np.zeros((H, W))
    # water streaks: generic thin dark dirt streaks everywhere + heavier ones under fixtures, rust under steel
    srcs = []
    for _ in range(int(height * 9)):
        z0 = rng.uniform(0.3, height)
        srcs.append(dict(u=rng.uniform(0, 1), row0=row_of(z0), length_m=rng.uniform(0.6, 3.5), width_m=rng.uniform(0.002, 0.007),
                         strength=rng.uniform(0.25, 0.7), wobble_m=rng.uniform(0.002, 0.01), fade=1.0))
    rust_srcs = []
    for (uf, zf, kind) in fixtures:
        for k in range(14 if kind == 'clamp' else 8):
            uu = uf + rng.normal(0, 0.06 if kind == 'clamp' else 0.035)
            srcs.append(dict(u=uu % 1, row0=row_of(zf - 0.02), length_m=rng.uniform(1.5, 5.0), width_m=rng.uniform(0.004, 0.012),
                             strength=rng.uniform(0.5, 1.0), wobble_m=rng.uniform(0.003, 0.012), fade=0.9))
            if rng.uniform() < 0.7:
                rust_srcs.append(dict(u=uu % 1, row0=row_of(zf - 0.03), length_m=rng.uniform(0.25, 1.4), width_m=rng.uniform(0.002, 0.007),
                                      strength=rng.uniform(0.45, 0.9), wobble_m=rng.uniform(0.002, 0.006), fade=1.6))
    # the pole top: water runs off the cap all round
    if not periodic:
        for k in range(40):
            srcs.append(dict(u=rng.uniform(0, 1), row0=row_of(height - 0.01), length_m=rng.uniform(0.8, 4.5), width_m=rng.uniform(0.003, 0.012),
                             strength=rng.uniform(0.4, 0.9), wobble_m=0.006, fade=1.0))
    dirt = streak_field(H, W, mpp_y, mpp_x, srcs, rng)
    rust = streak_field(H, W, mpp_y, mpp_x, rust_srcs, rng)
    # broad grey wash streaks (wide, faint) from the top
    wash = np.clip(fbm((H, W), 0.03 / mpp_x, 0.25 / mpp_x, rng.integers(1e9), 1.5, aspect=(30 * mpp_y / mpp_x, 1)), -2, 2) * 0.5 + 0.5
    wash = sstep(0.55, 0.9, wash)
    # compose albedo (linear)
    alb = np.repeat(base[..., None], 3, -1) * np.array([1.0, 1.0, 0.985])
    alb = alb * (1 - 0.30 * dirt[..., None]) * (1 - 0.10 * wash[..., None])
    rust_col = hexlin('#8A4524')
    alb = alb * (1 - 0.45 * rust[..., None]) + rust_col * (0.45 * rust[..., None])
    alb = alb * (1 - 0.35 * splash[..., None]) + hexlin('#4A4A3A') * 0.0
    alb = alb * (1 - moss[..., None] * 0.6) + hexlin('#3F4A2A') * (moss[..., None] * 0.6)
    alb = alb * (1 - 0.55 * holes[..., None]) * (1 - 0.85 * bolt[..., None])
    alb = np.clip(alb, lin_of(48), lin_of(225))
    alb[bolt > 0.5] = np.minimum(alb[bolt > 0.5], lin_of(40))     # the hole is dark, not a colour
    # height (m) -> normal
    hgt = 0.0004 * mott + 0.00008 * fine + 0.0025 * seam - 0.0015 * holes - 0.012 * bolt + 0.00012 * rings
    nrm = normal_from_height(hgt, mpp_y, mpp_x, 1.0)
    metal = np.zeros((H, W))
    smooth = np.clip(0.26 + 0.05 * mott - 0.08 * splash - 0.1 * holes + 0.06 * seam, 0.12, 0.40) * np.ones((H, W))
    ao = 1 - 0.6 * holes - 0.8 * bolt - 0.15 * splash
    flow = np.clip(0.25 + 0.75 * np.maximum(dirt, rust) + 0.3 * wash + 0.4 * splash, 0, 1) * np.ones((H, W))
    save_set(out, name, alb, nrm, metal, smooth, np.clip(ao, 0, 1), flow)


# ---------------------------------------------------------------------------------------------- the cobra head's painted aluminium
def housing(out, name='T_Lamps_Housing', N=512, seed=2):
    """UV of lk_geom.cobra_head: u 0..0.75 = the top arc from +Y rim over the crown to -Y rim; 0.80..1 = underside;
    v 0..1 = fitter -> nose (0.68 m)."""
    rng = np.random.default_rng(RNG_SEED + seed)
    H = W = N
    mpp_v = 0.68 / H; mpp_u = 0.75 / W
    v = (1 - (np.arange(H) + 0.5) / H)[:, None]
    u = ((np.arange(W) + 0.5) / W)[None, :]
    top = np.clip(1 - np.abs(u - 0.375) / 0.375, 0, 1)                    # 1 on the crown, 0 at the rims
    chalk = fbm((H, W), 3, 120, rng.integers(1e9), 1.8)
    base = hexlin('#7C807E') * (1 + 0.05 * chalk[..., None])
    base = base * (1 - top[..., None] * 0.0) + (hexlin('#8A8D8A') - hexlin('#7C807E')) * (sstep(0.3, 0.9, top))[..., None]
    # streaks of grime running from the crown down the flanks (along u away from 0.375) — u is "down" here
    g = np.zeros((H, W))
    for side in (-1, 1):
        for _ in range(60):
            v0 = rng.uniform(0.15, 0.95); w = rng.uniform(0.004, 0.012) / mpp_v
            L = rng.uniform(0.1, 0.35)
            uu = 0.375 + side * np.linspace(0.05, 0.05 + L, 200)
            vv = v0 + np.cumsum(rng.normal(0, 0.0015, 200))
            for a, b, k in zip(uu, vv, np.linspace(1, 0, 200)):
                if not (0 <= a <= 0.75):
                    continue
                ci, ri = int(a * W), int((1 - b) * H)
                if 0 <= ri < H:
                    r0, r1 = max(0, ri - int(w * 2)), min(H, ri + int(w * 2) + 1)
                    rr = np.arange(r0, r1)
                    g[rr, ci] = np.maximum(g[rr, ci], k * np.exp(-0.5 * ((rr - ri) / max(w, 0.7)) ** 2))
    from scipy import ndimage
    g = ndimage.gaussian_filter(g, (0.6, 1.5))
    grime = np.clip(g * 0.8, 0, 1)
    # underside & rim lip: darker, dirtier
    under = sstep(0.76, 0.80, u) * np.ones((H, W))
    rim = (np.exp(-0.5 * ((u - 0.75) / 0.012) ** 2) + np.exp(-0.5 * (u / 0.012) ** 2)) * np.ones((H, W))
    alb = base * (1 - 0.35 * grime[..., None]) * (1 - 0.30 * under[..., None]) * (1 - 0.25 * rim[..., None])
    # rust bloom at the fitter bolts (v ~ 0.05-0.12, crown)
    rust = np.clip(fbm((H, W), 2, 25, rng.integers(1e9)) - 1.0, 0, 1) * sstep(0.18, 0.06, v) * sstep(0.2, 0.6, top)
    alb = alb * (1 - rust[..., None]) + hexlin('#6B3A1E') * rust[..., None]
    alb = np.clip(alb, lin_of(50), lin_of(200))
    # height: cast aluminium (very soft orange peel), the door seam (a groove at u 0.78, v 0.30-0.95), cooling fins? no
    hgt = 0.00015 * fbm((H, W), 2, 20, rng.integers(1e9), 1.0)
    seam = np.exp(-0.5 * ((u - 0.785) / 0.002) ** 2) * sstep(0.25, 0.3, v) * sstep(0.97, 0.92, v)
    hgt -= 0.0008 * seam
    # a cast parting line along the crown
    hgt += 0.0004 * np.exp(-0.5 * ((u - 0.375) / 0.0025) ** 2) * sstep(0.12, 0.2, v)
    nrm = normal_from_height(hgt, mpp_v, mpp_u)
    smooth = np.clip(0.45 - 0.12 * top - 0.12 * grime - 0.1 * rust, 0.15, 0.5)
    ao = np.clip(1 - 0.4 * seam - 0.25 * under, 0, 1)
    flow = np.clip(0.3 + 0.7 * grime + 0.3 * top, 0, 1)
    save_set(out, name, alb, nrm, np.zeros((H, W)), smooth, ao, flow)


# ---------------------------------------------------------------------------------------------- small steel / porcelain / enamel
def steel(out, name, col_hex, rust_amt, N=256, seed=3, galv=False):
    """Weathered steel (painted or galvanised): metallic 0 everywhere except 1-2 px bright edge flecks (§1.6)."""
    rng = np.random.default_rng(RNG_SEED + seed)
    H = W = N
    n1 = fbm((H, W), 2, 60, rng.integers(1e9), 1.6)
    n2 = fbm((H, W), 1.5, 10, rng.integers(1e9), 1.0)
    base = hexlin(col_hex) * (1 + 0.08 * n1[..., None])
    rust = np.clip(fbm((H, W), 3, 80, rng.integers(1e9), 1.8) * 0.8 + rust_amt * 3 - 2.0, 0, 1)
    alb = base * (1 - rust[..., None]) + hexlin('#6B3A1E') * rust[..., None] * (1 + 0.15 * n2[..., None])
    alb = np.clip(alb, lin_of(52), lin_of(200))
    hgt = 0.0002 * n2 + 0.0004 * rust * n1
    nrm = normal_from_height(hgt, 0.5 / H, 0.5 / W)
    smooth = np.clip((0.38 if galv else 0.42) - 0.2 * rust + 0.03 * n1, 0.12, 0.5)
    ao = np.ones((H, W))
    flow = np.clip(0.4 + 0.4 * rust, 0, 1)
    save_set(out, name, alb, nrm, np.zeros((H, W)), smooth, ao, flow)


def porcelain(out, name='T_Lamps_Porcelain', N=128, seed=4):
    rng = np.random.default_rng(RNG_SEED + seed)
    H = W = N
    v = (1 - (np.arange(H) + 0.5) / H)[:, None]
    dirt = np.clip(fbm((H, W), 2, 40, rng.integers(1e9)) * 0.5 + 0.5, 0, 1) * sstep(0.8, 0.2, v)   # grime under the sheds
    alb = hexlin('#D6D8D4') * (1 - 0.25 * dirt[..., None])
    alb = np.clip(alb, lin_of(60), lin_of(225))
    nrm = np.dstack([np.zeros((H, W)), np.zeros((H, W)), np.ones((H, W))])
    save_set(out, name, alb, nrm, np.zeros((H, W)), np.full((H, W), 0.88) - 0.2 * dirt, np.ones((H, W)), np.full((H, W), 0.6))


def enamel_trough(out, name='T_Lamps_Enamel', N=512, seed=5):
    """Trough reflector (bible §5.4): outside dark green-grey #3E4A45 / 0.6 with chips (dark base coat #2E3238 +
    rust core), inside white enamel. UV of lk_geom: u 0..0.5 = outer surface (lip -> crown -> lip), 0.5..1 = inner;
    v = along the trough (1.3 m)."""
    rng = np.random.default_rng(RNG_SEED + seed)
    H, W = N, N
    u = ((np.arange(W) + 0.5) / W)[None, :]
    inner = (u > 0.5).astype(float) * np.ones((H, W))
    n1 = fbm((H, W), 2, 60, rng.integers(1e9), 1.6)
    outc = hexlin('#3E4A45') * (1 + 0.06 * n1[..., None])
    inc = hexlin('#DCDDD6') * (1 + 0.02 * n1[..., None])
    alb = outc * (1 - inner[..., None]) + inc * inner[..., None]
    # chips: blobs; base coat ring + rust core; concentrated at the lips (u near 0, 0.5, 1)
    lip = np.maximum.reduce([np.exp(-0.5 * (u / 0.04) ** 2), np.exp(-0.5 * ((u - 0.5) / 0.04) ** 2), np.exp(-0.5 * ((u - 1) / 0.04) ** 2)]) * np.ones((H, W))
    ch = fbm((H, W), 1.5, 14, rng.integers(1e9), 0.8)
    chip = sstep(2.0, 2.3, ch + 1.2 * lip)
    core = sstep(2.3, 2.7, ch + 1.2 * lip)
    alb = alb * (1 - chip[..., None]) + hexlin('#2E3238') * (chip - core)[..., None] + hexlin('#7A4220') * core[..., None]
    # inside: a soft tan of dust and a few dead insects? (no: those are in the cabin tubes) - brown dust near the ends
    dust = sstep(0.6, 1.0, np.abs((np.arange(H)[:, None] + 0.5) / H - 0.5) * 2) * inner
    alb = alb * (1 - 0.2 * dust[..., None]) + hexlin('#8A7A60') * 0.2 * dust[..., None]
    alb = np.clip(alb, lin_of(40), lin_of(225))
    hgt = -0.0006 * chip + 0.00004 * n1
    nrm = normal_from_height(hgt, 1.3 / H, 0.4 / W)
    smooth = np.where(inner > 0, 0.86, 0.6) - 0.35 * chip
    save_set(out, name, alb, nrm, np.zeros((H, W)), np.clip(smooth, 0.2, 0.9), 1 - 0.3 * chip, np.full((H, W), 0.5))


def refractor_dirt(out, name='T_Lamps_RefractorDirt', N=256, seed=6):
    """Refractor (drop glass bowl): R = dust film (yellow-brown film thickness 0..1, thicker toward the bottom),
    G = water-bead coverage, B = dead-insect specks inside (dark dots), A = 1. UV: u = azimuth, v = 0 rim .. 1 bottom."""
    rng = np.random.default_rng(RNG_SEED + seed)
    H = W = N
    v = (1 - (np.arange(H) + 0.5) / H)[:, None]
    dust = np.clip(0.35 + 0.45 * v + 0.15 * fbm((H, W), 2, 60, rng.integers(1e9)), 0, 1)
    beads = np.zeros((H, W))
    nb = 900
    by = rng.integers(0, H, nb); bx = rng.integers(0, W, nb)
    beads[by, bx] = 1
    from scipy import ndimage
    beads = np.clip(ndimage.gaussian_filter(beads, 1.2, mode='wrap') * 9, 0, 1) * sstep(0.2, 0.8, v)
    specks = np.zeros((H, W))
    ns = 14
    sy = rng.integers(int(H * 0.0), int(H * 0.5), ns); sx = rng.integers(0, W, ns)
    specks[sy, sx] = 1
    specks = np.clip(ndimage.gaussian_filter(specks, 1.6, mode='wrap') * 14, 0, 1)
    img = np.stack([dust, beads, specks, np.ones((H, W))], -1)
    save_rgba(os.path.join(out, name + '.png'), img)
    print(name, 'dust mean %.2f' % dust.mean())


SETS = {
    'pole_road': lambda o: concrete_pole(o, 'T_Lamps_PoleRoad', fixtures=[(0.25, 8.66, 'clamp'), (0.0, 6.58, 'clamp'), (0.0, 6.36, 'clamp'), (0.0, 9.0, 'top')], seed=11),
    'pole_stop': lambda o: concrete_pole(o, 'T_Lamps_PoleStop', fixtures=[(0.25, 8.66, 'clamp'), (0.0, 4.31, 'clamp'), (0.0, 4.09, 'clamp'), (0.0, 9.0, 'top')], seed=12),
    'pole_long': lambda o: concrete_pole(o, 'T_Lamps_PoleLong', fixtures=[], periodic=True, seed=13),
    'housing': lambda o: housing(o),
    'steel': lambda o: steel(o, 'T_Lamps_Steel', '#6E716F', 0.35, galv=True),
    'armsteel': lambda o: steel(o, 'T_Lamps_ArmSteel', '#5A4A40', 0.55, seed=7),
    'porcelain': lambda o: porcelain(o),
    'enamel': lambda o: enamel_trough(o),
    'refractor': lambda o: refractor_dirt(o),
}

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Textures')
    which = sys.argv[2:] or list(SETS)
    for k in which:
        SETS[k](out)
