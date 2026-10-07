# -*- coding: utf-8 -*-
"""Scene 8 (暮 · 另一片天) background for the proofs, from the bible's §6·8 targets, with NO purple (§1.3.4).

Sun at azimuth 0°, elevation +0.5° (dead ahead, the only symmetric frame of the film). Warm lives only in the light
(sun band #FFB070, seam amber #F2A56B, sun line #FFE2B0); away from the sun the horizon is a low-chroma sand, and the
climb to the mid-sky #808AB2 and zenith #3D4A80 goes through warm grey -> neutral -> indigo-grey, never through rose
(rose + blue = the lavender that v1 had). The rose band is on the ANTI-sun side (az 180°) and never in these views.
8-ii lower hemisphere = the other sky: HDRI sampled at (-x, -y, z) (x 0.82, tint (0.92, 0.95, 1.05)), 1° soft seam,
different clouds (70 %). Clouds: flat dusk streaks, shadows #363D59 (indigo stone), sun-side rims amber, never pink.
All blending in linear light. Returns linear RGB float arrays.
"""
import numpy as np
from scipy import ndimage as ndi


def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def s2l(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# vertical profile far from the sun (display targets, interpolated in linear light)
BASE = [(0.0, '#C9B29A'), (1.5, '#BFB09F'), (4.0, '#B0ABA2'), (8.0, '#A0A4AC'), (14.0, '#8F99AF'),
        (24.0, '#808AB2'), (46.0, '#5B6795'), (90.0, '#3D4A80')]
SUN_BAND = '#FFB070'
SEAM = '#F2A56B'
SUN_LINE = '#FFE2B0'
CLOUD_SHADOW = '#363D59'
RIM = '#F4B27E'
OTHER_TINT = np.array([0.92, 0.95, 1.05]) * 0.82


def _interp_stops(el, stops):
    e = np.array([s[0] for s in stops])
    cols = np.array([s2l(hx(s[1])) for s in stops])
    return np.stack([np.interp(el, e, cols[:, i]) for i in range(3)], -1)


def sky_upper(az, el, sun_line=1.0, line_half=10.0):
    """az, el in degrees (arrays, same shape), el >= 0 meaningful. Linear RGB. line_half = the sun line's half-width
    (§6·8b: ±10°, collapsing to a point over 6 s at F12)."""
    ela = np.abs(el)
    img = _interp_stops(ela, BASE)
    daz = np.abs((az + 180.0) % 360.0 - 180.0)
    # broad warm glow around the sun, hugging the horizon (amber / gold only)
    g1 = np.exp(-(daz / 38.0) ** 2) * np.exp(-ela / 5.5)
    g2 = np.exp(-(daz / 70.0) ** 2) * np.exp(-ela / 14.0)
    img = img + (0.55 * g1)[..., None] * s2l(hx(SUN_BAND)) + (0.10 * g2)[..., None] * s2l(hx(SEAM))
    # seam amber right at the horizon, and the burning line near the sun (§6·8: sun and its other self fuse)
    seam = np.exp(-(ela / 1.1) ** 2) * (0.35 + 0.65 * np.exp(-(daz / 45.0) ** 2))
    img = img + (0.30 * seam)[..., None] * s2l(hx(SEAM))
    line = np.exp(-(el / 0.35) ** 2) * np.exp(-(daz / max(0.9 * line_half, 0.3)) ** 2) * sun_line
    img = img + (1.4 * line)[..., None] * s2l(hx(SUN_LINE))
    return img


def sun_disc(img, az, el, sun_el=0.5, r=0.45):
    d = np.sqrt(az ** 2 + (el - sun_el) ** 2)
    core = np.clip((r + 0.08 - d) / 0.16, 0, 1)
    halo = np.exp(-(d / 2.2) ** 2)
    return img + (3.0 * core + 0.35 * halo)[..., None] * s2l(hx(SUN_LINE))


def streaks(h, w, seed, aspect=14.0, scales=(9, 4.0, 1.8)):
    r = np.random.default_rng(seed)
    acc = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for sc in scales:
        n = ndi.gaussian_filter(r.standard_normal((h, w)), (sc, sc * aspect), mode='wrap')
        n /= n.std() + 1e-9
        acc += amp * n
        tot += amp
        amp *= 0.5
    return acc / tot


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def clouds(img, az, el, daz, seed, lower=False, density=1.0):
    """flat dusk streaks between ~1.5° and ~16° from the horizon; shadow indigo-stone, sun-side rim amber."""
    h, w = el.shape
    n = streaks(h, w, seed)
    ela = np.abs(el)
    band = smooth(1.0, 2.6, ela) * smooth(19.0, 8.0, ela)
    # perspective: streaks get thinner and denser toward the horizon
    thr = (0.35 if not lower else 0.6) + 0.02 * ela
    c = smooth(thr, thr + 0.9, n) * band * density
    sh = s2l(hx(CLOUD_SHADOW))
    # lit rim: the edge that faces the horizon (the sun is at the horizon), stronger near the sun
    towards = 1 if not lower else -1
    edge = np.clip(c - ndi.shift(c, (-towards * 3, 0), order=1, mode='nearest'), 0, 1)
    warm = np.exp(-(daz / 40.0) ** 2)
    a = 0.42 * c
    img = img * (1 - a[..., None]) + a[..., None] * sh
    img = img + (edge * (0.10 + 0.55 * warm))[..., None] * s2l(hx(RIM))
    return img


def dusk_view(w, h, az_left, el_top, dpp, mode='8-ii', seed=5, sun=True, line_half=10.0):
    """Equirectangular crop: x -> azimuth (az_left + x * dpp), y -> elevation (el_top - y * dpp).
    mode '8-ii': the other sky below the horizon. mode '8-i': below the horizon is the dusk sky as well (the bus has
    just fallen out of the sea's underside; the sea ceiling above is only drawn above +1.5°)."""
    xs = az_left + (np.arange(w) + 0.5) * dpp
    ys = el_top - (np.arange(h) + 0.5) * dpp
    az, el = np.meshgrid(xs, ys)
    daz = np.abs((az + 180.0) % 360.0 - 180.0)
    fade = min(1.0, line_half / 10.0) ** 0.5        # F12: the line and the sun shrink to a point and go out
    up = sky_upper(az, el, sun_line=fade, line_half=line_half)
    up = clouds(up, az, el, daz, seed, lower=False)
    dn = sky_upper(-az, -el, sun_line=fade, line_half=line_half) * OTHER_TINT   # (-x, -y, z): the other sky
    dn = clouds(dn, -az, -el, daz, seed + 101, lower=True, density=0.7)
    t = np.clip(0.5 + el / 1.0, 0, 1)[..., None]   # 1° soft blend at the seam
    img = dn * (1 - t) + up * t
    # the burning line crosses the seam unbroken (sun + its other self)
    line = np.exp(-(el / 0.28) ** 2) * np.exp(-(daz / max(line_half, 0.3)) ** 2) * fade
    img = img + (0.9 * line)[..., None] * s2l(hx(SUN_LINE))
    if sun:
        img = sun_disc(img, az, el, r=0.45 * max(fade, 0.2)) if fade < 1 else sun_disc(img, az, el)
    if mode == '8-i':
        # sea ceiling (8-i): starts ~1.5° above the horizon; Fresnel rose-gold mirror near grazing -> deep blue overhead
        ce = smooth(1.2, 2.2, el)
        fres = np.exp(-(np.clip(el - 1.5, 0, None) / 6.0))
        ceil = s2l(hx('#10263F')) * (1 - fres[..., None]) + s2l(hx('#C98A7A')) * fres[..., None] * 0.9
        img = img * (1 - ce[..., None]) + ce[..., None] * ceil
    return img, az, el


# ---------------------------------------------------------------------------------------- purple meter
def srgb_u8_to_lab(u8):
    c = u8.astype(np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T
    wp = np.array([0.95047, 1.0, 1.08883])
    t = xyz / wp
    f = np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    Lc = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return Lc, a, b


def purple_fraction(u8, hmin=290.0, hmax=325.0, cmin=15.0):
    """bible §1.3.4: share of the frame with h_ab in [hmin, hmax] and C* > cmin (scene 6: 285-330, C* > 12)."""
    Lc, a, b = srgb_u8_to_lab(u8)
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360
    m = (h >= hmin) & (h <= hmax) & (C > cmin)
    return float(m.mean())


def hue_chroma(hexc):
    u8 = (hx(hexc) * 255).round().astype(np.uint8)[None, None, :]
    Lc, a, b = srgb_u8_to_lab(u8)
    return float(Lc[0, 0]), float(np.hypot(a, b)[0, 0]), float(np.degrees(np.arctan2(b, a))[0, 0] % 360)
