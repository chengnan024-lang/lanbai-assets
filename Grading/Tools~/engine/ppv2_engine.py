# -*- coding: utf-8 -*-
"""Engine-faithful model of what PPv2 3.x renders for a Lanbai scene profile
(Color Grading = High Definition Range, Tonemapper = Neutral), written from the package SOURCE.

Why this file exists (verify.md B1): the art simulator (art/lens_cine/ppv2.py grade_lut) runs the working spaces
of the ACES-tonemapper branch for every profile. In PPv2 the ACES spaces are used ONLY `#if TONEMAPPING_ACES`.
For Neutral the source does something else, and night blacks crush to #000000 with the v2 parameters.
The art simulator is still the LOOK DEFINITION (it made every screen target in calib_final); this file is the
ENGINE. Tools~/engine/solve_engine_grades.py fits engine parameters so the engine hits the look's targets.

Source (com.unity.postprocessing v2 branch = 3.0.2; the Neutral path is identical in 3.6.0):
  Uber.shader            COLOR_GRADING_HDR_3D: color *= _PostExposure (= 2^EV);
                         uvw = saturate(LUT_SPACE_ENCODE(color.rgb)); color = ApplyLut3D(_Lut3D, uvw, _Lut3D_Params)
  Colors.hlsl            LUT_SPACE_ENCODE = LinearToLogC, USE_PRECISE_LOGC 0 -> c*log10(a*x + b) + d (no linear toe)
                         ApplyLut3D: uvw * (N-1)/N + 0.5/N  (texel centres), hardware trilinear
  Lut3DBaker.compute     Eval: colorLutSpace = id / (N-1); graded = ColorGrade(colorLutSpace); _Output = max(graded, 0)
                         ColorGrade (#else branch, i.e. Neutral / None / Custom):
                           LogGrade:     Contrast(colorLog, ACEScc_MIDGRAY = 0.4135884, con)   (in LogC!)
                           LUT_SPACE_DECODE = LogCToLinear
                           LinearGrade:  WhiteBalance (LIN_2_LMS / LMS_2_LIN, linear Rec.709)
                                         *= _ColorFilter (SetComputeVectorParam: raw Color, NOT .linear)
                                         ChannelMixer: (dot(c, R), dot(c, G), dot(c, B)), rows = mixer.../100
                                         (ColorGrading.cs: _ChannelMixerRed = (RR, RG, RB) / 100 ...)
                                         LiftGammaGainHDR: c = c*gain + lift; sign(c)*pow(|c|, invgamma)
                                         max(0); RgbToHsv (EPSILON 1e-4); hue += hueShift + curve(0);
                                         HsvToRgb; Saturation(c, sat) with Luminance = Rec.709 (0.2126729, 0.7151522, 0.0721750)
                           max(0); NeutralTonemap
  ColorGrading.cs        k_Lut3DSize = 33; LUT RenderTexture format ARGBHalf (GetLutFormat)
                         lift = ColorToLift(lift * 0.2), gain = ColorToGain(gain * 0.8), invgamma = ColorToInverseGamma(gamma * 0.8)
                         hueSatCon = (hueShift/360, sat/100 + 1, con/100 + 1); balance = ComputeColorBalance(temp, tint)
  ColorUtilities.cs      ColorToLift: S - lum709(S) + w; ColorToGain: H - lum709(H) + w + 1;
                         ColorToInverseGamma: 1 / max(M - lum709(M) + w + 1, 1e-3)
Curves are the PPv2 defaults (hue-vs-sat etc. = 0.5 -> multiplier 1, hue-vs-hue offset 0), colorFilter white,
hueShift 0 in every Lanbai profile, so those terms are identities here (but kept exact). The channel mixer is used:
p['mixer'] = 9 percentages row-major (mixerRedOutRedIn, mixerRedOutGreenIn, mixerRedOutBlueIn, mixerGreenOutRedIn,
..., mixerBlueOutBlueIn), default identity (100, 0, 0, 0, 100, 0, 0, 0, 100). It lets the engine emulate the
look's AP1 working space for saturated colours (a 3x3 in linear 709 is exactly what a change of primaries is).

Numbers: sRGB 8-bit codes as a colour picker reads a screenshot (display-linear -> sRGB encode -> x255).
"""
import numpy as np

N = 33                                                   # ColorGrading.k_Lut3DSize
LOGC = dict(a=5.555556, b=0.047996, c=0.244161, d=0.386036)   # Colors.hlsl ParamsLogC (non-precise path)
ACESCC_MIDGRAY = 0.4135884
LUMA709_UTIL = np.array([0.2126, 0.7152, 0.0722])        # ColorUtilities.cs (trackballs)
LUMA709_HLSL = np.array([0.2126729, 0.7151522, 0.0721750])   # Colors.hlsl Luminance()
EPS_HSV = 1.0e-4                                         # StdLib.hlsl EPSILON
LIN_2_LMS = np.array([[3.90405e-1, 5.49941e-1, 8.92632e-3],
                      [7.08416e-2, 9.63172e-1, 1.35775e-3],
                      [2.31082e-2, 1.28021e-1, 9.36245e-1]])
LMS_2_LIN = np.array([[2.85847e+0, -1.62879e+0, -2.48910e-2],
                      [-2.10182e-1, 1.15820e+0, 3.24281e-4],
                      [-4.18120e-2, -1.18169e-1, 1.06867e+0]])

MIXER_IDENTITY = (100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0, 100.0)
DEFAULT = dict(postExposure=0.0, temperature=0.0, tint=0.0, colorFilter='#FFFFFF', hueShift=0.0, saturation=0.0,
               contrast=0.0, lift=(1, 1, 1, 0), gamma=(1, 1, 1, 0), gain=(1, 1, 1, 0), mixer=MIXER_IDENTITY)


# The test card's colour row (and key samples of the engine solve): designed saturated colours of the film, as
# scene-linear rgb before postExposure. Not bible targets; they make Unity show how it grades saturated colours.
COLOUR_PATCHES = [
    ('站牌字 sign ink', (0.018, 0.071, 0.195)),        # albedo #1D3E66 x E 1.47 (bible 5.2)
    ('裂口紫晕 wound violet', (0.223, 0.178, 0.630)),  # calib B S4 紫晕 fill #8275D0
    ('尾灯红 tail red', (0.597, 0.008, 0.002)),        # calib B S1 尾灯 #CB1500
    ('钠灯橙 sodium', (1.231, 0.248, 0.004)),          # calib B #FF7C00 @ +0.30
    ('藍 ai sea blue', (0.020, 0.100, 0.250)),         # indigo ladder L3, 30 m sea water
    ('暮玫瑰 dusk rose', (0.550, 0.250, 0.200)),
    ('湿叶绿 wet leaf', (0.040, 0.090, 0.030)),
    ('Lichtchen 暖白', (1.000, 0.750, 0.450)),
]


def full(p):
    q = dict(DEFAULT)
    q.update({k: v for k, v in p.items() if k in DEFAULT})
    return q


# ---------------------------------------------------------------- transfer functions
def lin_to_logc(x):
    return LOGC['c'] * np.log10(LOGC['a'] * np.asarray(x, np.float64) + LOGC['b']) + LOGC['d']


def logc_to_lin(t):
    return (10.0 ** ((np.asarray(t, np.float64) - LOGC['d']) / LOGC['c']) - LOGC['b']) / LOGC['a']


def srgb_encode(v):
    v = np.clip(np.asarray(v, np.float64), 0.0, 1.0)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1 / 2.4) - 0.055)


def srgb_decode(v):
    v = np.asarray(v, np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def hex_raw(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def hex8(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64)


def to_hex(codes):
    c = np.clip(np.round(np.asarray(codes, np.float64)), 0, 255).astype(int)
    return '#%02X%02X%02X' % tuple(c)


# ---------------------------------------------------------------- ColorUtilities.cs
def color_balance(temperature, tint):
    t1, t2 = temperature / 60.0, tint / 60.0
    x = 0.31271 - t1 * (0.1 if t1 < 0 else 0.05)
    y = (2.87 * x - 3.0 * x * x - 0.27509507) + t2 * 0.05
    X, Y, Z = x / y, 1.0, (1.0 - x - y) / y
    lms = np.array([0.7328 * X + 0.4296 * Y - 0.1624 * Z, -0.7036 * X + 1.6975 * Y + 0.0061 * Z,
                    0.0030 * X + 0.0136 * Y + 0.9834 * Z])
    return np.array([0.949237, 1.03542, 1.08728]) / lms


def color_to_lift(v4):
    v = np.asarray(v4, np.float64) * 0.2
    return v[:3] - v[:3] @ LUMA709_UTIL + v[3]


def color_to_gain(v4):
    v = np.asarray(v4, np.float64) * 0.8
    return v[:3] - v[:3] @ LUMA709_UTIL + v[3] + 1.0


def color_to_inv_gamma(v4):
    v = np.asarray(v4, np.float64) * 0.8
    return 1.0 / np.maximum(v[:3] - v[:3] @ LUMA709_UTIL + v[3] + 1.0, 1e-3)


# ---------------------------------------------------------------- Colors.hlsl
def rgb_to_hsv(c):
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    one = np.ones_like(r)
    gb = (b <= g)[..., None]                                   # step(c.b, c.g)
    p = np.where(gb, np.stack([g, b, 0 * one, -one / 3], -1), np.stack([b, g, -one, 2 * one / 3], -1))
    rp = (p[..., 0] <= r)[..., None]                           # step(p.x, c.r)
    q = np.where(rp, np.stack([r, p[..., 1], p[..., 2], p[..., 0]], -1), np.stack([p[..., 0], p[..., 1], p[..., 3], r], -1))
    d = q[..., 0] - np.minimum(q[..., 3], q[..., 1])
    return np.stack([np.abs(q[..., 2] + (q[..., 3] - q[..., 1]) / (6.0 * d + EPS_HSV)), d / (q[..., 0] + EPS_HSV), q[..., 0]], -1)


def hsv_to_rgb(c):
    K = np.array([1.0, 2.0 / 3.0, 1.0 / 3.0])
    t = c[..., 0:1] + K
    p = np.abs((t - np.floor(t)) * 6.0 - 3.0)
    return c[..., 2:3] * (1.0 + (np.clip(p - 1.0, 0.0, 1.0) - 1.0) * c[..., 1:2])


def rotate_hue(v):
    return np.where(v < 0.0, v + 1.0, np.where(v > 1.0, v - 1.0, v))


def neutral_tonemap(x):
    a, b, c, d, e, f = 0.2, 0.29, 0.24, 0.272, 0.02, 0.3
    curve = lambda x: ((x * (a * x + c * b) + d * e) / (x * (a * x + b) + d * f)) - e / f
    ws = 1.0 / curve(5.3)
    return curve(x * ws) * ws


# ---------------------------------------------------------------- Lut3DBaker.compute (#else branch)
def color_grade(logc, p):
    """logc: (..., 3) LUT-space (LogC) coordinates -> display-linear (the value stored in the LUT, before max 0)."""
    p = full(p)
    x = (np.asarray(logc, np.float64) - ACESCC_MIDGRAY) * (p['contrast'] / 100.0 + 1.0) + ACESCC_MIDGRAY   # LogGrade
    x = logc_to_lin(x)
    x = np.einsum('ij,...j->...i', LMS_2_LIN, np.einsum('ij,...j->...i', LIN_2_LMS, x) * color_balance(p['temperature'], p['tint']))
    cf = p['colorFilter']
    x = x * (hex_raw(cf) if isinstance(cf, str) else np.asarray(cf, np.float64))                           # raw, not .linear
    M = np.asarray(p['mixer'], np.float64).reshape(3, 3) / 100.0                                            # ChannelMixer
    x = np.einsum('ij,...j->...i', M, x)
    x = x * color_to_gain(p['gain']) + color_to_lift(p['lift'])
    x = np.sign(x) * np.abs(x) ** color_to_inv_gamma(p['gamma'])
    x = np.maximum(x, 0.0)
    hsv = rgb_to_hsv(x)
    hsv[..., 0] = rotate_hue(hsv[..., 0] + p['hueShift'] / 360.0)
    x = hsv_to_rgb(hsv)
    lum = x @ LUMA709_HLSL
    x = lum[..., None] + (p['saturation'] / 100.0 + 1.0) * (x - lum[..., None])
    x = np.maximum(x, 0.0)
    return neutral_tonemap(x)


GRID1 = np.arange(N) / (N - 1.0)


def bake_lut(p):
    """(N, N, N, 3) indexed [r, g, b]: exactly the ARGBHalf 3D texture PPv2 bakes (float16 storage)."""
    g = np.stack(np.meshgrid(GRID1, GRID1, GRID1, indexing='ij'), -1)
    return np.maximum(color_grade(g, p), 0.0).astype(np.float16).astype(np.float64)


def _corners(uvw):
    t = np.clip(uvw, 0.0, 1.0) * (N - 1)
    i0 = np.minimum(np.floor(t).astype(int), N - 2)
    return i0, t - i0


def sample_lut(L, uvw):
    i0, f = _corners(uvw)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w[..., None] * L[i0[..., 0] + dx, i0[..., 1] + dy, i0[..., 2] + dz]
    return out


def uvw_of(lin, p):
    """Uber.shader: color *= 2^postExposure; uvw = saturate(LinearToLogC(color))."""
    x = np.maximum(np.asarray(lin, np.float64), 0.0) * 2.0 ** full(p)['postExposure']
    return np.clip(lin_to_logc(x), 0.0, 1.0)


def codes(lin, p, lut=None):
    """Screen codes (float 0..255, before 8-bit rounding) PPv2 shows for scene-linear rgb (..., 3), no bloom."""
    L = bake_lut(p) if lut is None else lut
    return srgb_encode(sample_lut(L, uvw_of(lin, p))) * 255.0


def codes_sparse(lin, p):
    """Same numbers as codes() (float16 LUT, trilinear) but grades only the grid corners the inputs touch: fast enough
    to sit inside an optimiser loop."""
    uvw = uvw_of(lin, p)
    i0, f = _corners(uvw)
    flat = i0.reshape(-1, 3)
    need = set()
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                need.update(map(tuple, flat + (dx, dy, dz)))
    idx = np.array(sorted(need))
    vals = np.maximum(color_grade(idx / (N - 1.0), p), 0.0).astype(np.float16).astype(np.float64)
    table = {tuple(k): v for k, v in zip(idx, vals)}
    fr = f.reshape(-1, 3)
    out = np.zeros((flat.shape[0], 3))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (fr[:, 0] if dx else 1 - fr[:, 0]) * (fr[:, 1] if dy else 1 - fr[:, 1]) * (fr[:, 2] if dz else 1 - fr[:, 2])
                c = np.array([table[tuple(k)] for k in flat + (dx, dy, dz)])
                out += w[:, None] * c
    return (srgb_encode(out) * 255.0).reshape(np.shape(lin))


def codes_direct(lin, p):
    """No LUT (continuous): only for optimiser warm starts."""
    return srgb_encode(np.maximum(color_grade(uvw_of(lin, p), p), 0.0)) * 255.0


def screen_hex(lin, p, lut=None):
    return to_hex(codes(np.asarray(lin, np.float64)[None, :], p, lut)[0])


if __name__ == '__main__':
    # self-test: neutral profile, 18 % grey must read #767676 (bible 1.4: 0.18 -> display 118)
    print('S10 0.18 ->', screen_hex([0.18] * 3, {}), '(expect #767676 or #777777 through the 33^3 LUT)')
    print('S10 black ->', screen_hex([0, 0, 0], {}))
