"""Numpy emulation of Unity Post Processing Stack v2 (3.x) colour path, HDR grading mode.

Order (matches Uber.shader + Lut3DBaker.compute, HDR mode):
  scene-linear -> bloom added (threshold on pre-exposure values) -> vignette
  -> *2^postExposure -> [LUT: unity->ACES(AP0) -> ACEScc log contrast -> ACEScg:
     white balance (LMS), colour filter, lift/gamma/gain, clamp>=0, hue shift, saturation (AP1 luma)
     -> ACEScg->unity -> Neutral tonemap] -> display-linear -> sRGB encode.
Close enough to predict screenshots within a few 8-bit codes (LUT quantisation and grain aside).
"""
import numpy as np

# ---------- transfer functions ----------
def srgb_to_lin(v):
    v = np.asarray(v, np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)

def lin_to_srgb(v):
    v = np.clip(np.asarray(v, np.float64), 0, None)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1 / 2.4) - 0.055)

def hex_to_lin(h):
    h = h.lstrip('#')
    return srgb_to_lin(np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]))

def lin_to_hex(c):
    s = np.clip(lin_to_srgb(c), 0, 1)
    return '#%02X%02X%02X' % tuple(int(round(x * 255)) for x in s)

def srgb_to_hex(s):
    s = np.clip(s, 0, 1)
    return '#%02X%02X%02X' % tuple(int(round(x * 255)) for x in s)

# ---------- matrices (Unity ACES.hlsl / Colors.hlsl) ----------
sRGB_2_AP0 = np.array([[0.4397010, 0.3829780, 0.1773350],
                       [0.0897923, 0.8134230, 0.0967616],
                       [0.0175440, 0.1115440, 0.8707040]])
AP0_2_AP1 = np.array([[1.4514393161, -0.2365107469, -0.2149285693],
                      [-0.0765537734, 1.1762296998, -0.0996759264],
                      [0.0083161484, -0.0060324498, 0.9977163014]])
AP1_2_AP0 = np.linalg.inv(AP0_2_AP1)
AP1_2_sRGB = np.array([[1.70505, -0.62179, -0.08326],
                       [-0.13026, 1.14080, -0.01055],
                       [-0.00324, -0.00969, 1.01293]])
AP1_LUMA = np.array([0.2722287168, 0.6740817658, 0.0536895174])
LIN_2_LMS = np.array([[3.90405e-1, 5.49941e-1, 8.92632e-3],
                      [7.08416e-2, 9.63172e-1, 1.35775e-3],
                      [2.31082e-2, 1.28021e-1, 9.36245e-1]])
LMS_2_LIN = np.array([[2.85847e+0, -1.62879e+0, -2.48910e-2],
                      [-2.10182e-1, 1.15820e+0, 3.24281e-4],
                      [-4.18120e-2, -1.18169e-1, 1.06867e+0]])
ACEScc_MIDGRAY = 0.4135884
LUMA709 = np.array([0.2126, 0.7152, 0.0722])

def _m(M, c):
    return np.einsum('ij,...j->...i', M, c)

def aces_to_acescc(x):
    x = np.clip(x, 0, 65504)
    return np.where(x < 2 ** -15, (np.log2(2 ** -16 + x * 0.5) + 9.72) / 17.52, (np.log2(np.maximum(x, 1e-30)) + 9.72) / 17.52)

def acescc_to_aces(x):
    return np.where(x < -0.3013698630, (2 ** (x * 17.52 - 9.72) - 2 ** -16) * 2, np.where(x < (np.log2(65504) + 9.72) / 17.52, 2 ** (x * 17.52 - 9.72), 65504))

# ---------- PPv2 parameter conversions (ColorUtilities.cs) ----------
def color_balance(temperature, tint):
    t1, t2 = temperature / 60.0, tint / 60.0
    x = 0.31271 - t1 * (0.1 if t1 < 0 else 0.05)
    y = 2.87 * x - 3 * x * x - 0.27509507 + t2 * 0.05
    X, Y = x / y, 1.0
    Z = (1 - x - y) / y
    L = 0.7328 * X + 0.4296 * Y - 0.1624 * Z
    M = -0.7036 * X + 1.6975 * Y + 0.0061 * Z
    S = 0.0030 * X + 0.0136 * Y + 0.9834 * Z
    w1 = np.array([0.949237, 1.03542, 1.08728])
    return w1 / np.array([L, M, S])

def wb_equiv_cct(temperature, tint=0.0):
    """CCT (K) of the white the grade treats as neutral (McCamy). >6504 K => image made warmer."""
    t1, t2 = temperature / 60.0, tint / 60.0
    x = 0.31271 - t1 * (0.1 if t1 < 0 else 0.05)
    y = 2.87 * x - 3 * x * x - 0.27509507 + t2 * 0.05
    n = (x - 0.3320) / (0.1858 - y)
    return 449 * n ** 3 + 3525 * n ** 2 + 6823.3 * n + 5520.33

def _lift(v):
    v = np.asarray(v, np.float64) * 0.2
    s = v[:3] - np.dot(v[:3], LUMA709)
    return s + v[3]

def _gain(v):
    v = np.asarray(v, np.float64) * 0.8
    s = v[:3] - np.dot(v[:3], LUMA709)
    return s + v[3] + 1.0

def _invgamma(v):
    v = np.asarray(v, np.float64) * 0.8
    s = v[:3] - np.dot(v[:3], LUMA709)
    return 1.0 / np.maximum(s + v[3] + 1.0, 1e-3)

# ---------- tonemappers ----------
def _neutral_curve(x, a=0.2, b=0.29, c=0.24, d=0.272, e=0.02, f=0.3):
    return ((x * (a * x + c * b) + d * e) / (x * (a * x + b) + d * f)) - e / f

def neutral_tonemap(x):
    ws = 1.0 / _neutral_curve(5.3)
    x = _neutral_curve(np.asarray(x) * ws)
    return x * ws

def neutral_inverse(y, lo=0.0, hi=5.3):
    """numeric inverse of neutral_tonemap for scalars/arrays in [0,1)."""
    y = np.asarray(y, np.float64)
    a, b = np.full_like(y, lo), np.full_like(y, hi)
    for _ in range(60):
        m = 0.5 * (a + b)
        big = neutral_tonemap(m) > y
        b = np.where(big, m, b)
        a = np.where(big, a, m)
    return 0.5 * (a + b)

# ---------- grade ----------
DEFAULT = dict(postExposure=0.0, temperature=0.0, tint=0.0, colorFilter='#FFFFFF', hueShift=0.0,
               saturation=0.0, contrast=0.0, lift=(1, 1, 1, 0), gamma=(1, 1, 1, 0), gain=(1, 1, 1, 0),
               bloom=dict(intensity=0.0, threshold=1.0, softKnee=0.5, diffusion=7.0, color='#FFFFFF'),
               vignette=dict(intensity=0.0, smoothness=0.2, roundness=1.0, color='#000000'))

def full(params):
    p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT.items()}
    for k, v in params.items():
        if isinstance(v, dict) and k in p:
            p[k].update(v)
        else:
            p[k] = v
    return p

def grade_lut(c, p):
    """the LUT part: input = post-exposed scene-linear (unity primaries), output display-linear."""
    aces = _m(sRGB_2_AP0, c)
    cc = aces_to_acescc(aces)
    cc = (cc - ACEScc_MIDGRAY) * (p['contrast'] / 100 + 1) + ACEScc_MIDGRAY
    aces = acescc_to_aces(cc)
    cg = _m(AP0_2_AP1, aces)
    bal = color_balance(p['temperature'], p['tint'])
    cg = _m(LMS_2_LIN, _m(LIN_2_LMS, cg) * bal)
    cg = cg * hex_to_lin(p['colorFilter']) if isinstance(p['colorFilter'], str) else cg * np.asarray(p['colorFilter'])
    lift, gain, ig = _lift(p['lift']), _gain(p['gain']), _invgamma(p['gamma'])
    cg = cg * gain + lift
    cg = np.sign(cg) * np.abs(cg) ** ig
    cg = np.maximum(cg, 0)
    if p['hueShift']:
        cg = _hue_rotate(cg, p['hueShift'] / 360.0)
    luma = np.einsum('...j,j->...', cg, AP1_LUMA)[..., None]
    cg = luma + (p['saturation'] / 100 + 1) * (cg - luma)
    lin = _m(AP1_2_sRGB, cg)
    return np.clip(neutral_tonemap(np.maximum(lin, 0)), 0, 1)

def _hue_rotate(c, dh):
    import colorsys
    shp = c.shape
    flat = c.reshape(-1, 3)
    mx = flat.max(1, keepdims=True)
    scale = np.where(mx > 0, mx, 1)
    out = np.array([colorsys.hsv_to_rgb((colorsys.rgb_to_hsv(*px)[0] + dh) % 1.0, *colorsys.rgb_to_hsv(*px)[1:]) for px in flat / scale]) * scale
    return out.reshape(shp)

def gamma_to_lin_scalar(t):
    return t ** 2.2

def bloom_layer(img, p, levels=None):
    """approximation of PPv2 bloom: quadratic threshold (gamma-space threshold), dual-filter pyramid summed."""
    from scipy.ndimage import gaussian_filter
    b = p['bloom']
    if b['intensity'] <= 0:
        return np.zeros_like(img)
    thr = gamma_to_lin_scalar(b['threshold'])
    knee = thr * b['softKnee'] + 1e-5
    curve = (thr - knee, knee * 2, 0.25 / knee)
    br = img.max(-1)
    rq = np.clip(br - curve[0], 0, curve[1])
    rq = curve[2] * rq * rq
    pre = img * (np.maximum(rq, br - thr) / np.maximum(br, 1e-5))[..., None]
    h, w = img.shape[:2]
    logh = np.log2(max(h, w)) + min(b['diffusion'], 10) - 10
    n = int(np.clip(np.floor(logh), 1, 16)) if levels is None else levels
    acc = np.zeros_like(img)
    for i in range(n):
        s = 2.0 ** (i + 1) * 0.9
        acc += gaussian_filter(pre, sigma=(s, s, 0), mode='nearest')
    k = 2 ** (b['intensity'] / 10) - 1
    return acc * k * hex_to_lin(b['color'])

def vignette(img, p):
    v = p['vignette']
    if v['intensity'] <= 0:
        return img
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.stack([(xx / w - 0.5) * 2 * (w / h if v['roundness'] >= 1 else 1), (yy / h - 0.5) * 2], -1)
    d = np.abs(d) * v['intensity']
    f = np.clip(1 - (d ** 2).sum(-1), 0, 1) ** (v['smoothness'] * 5 + 1e-5)
    col = hex_to_lin(v['color'])
    return img * (col + (1 - col) * f[..., None])

def render(img_lin, params, with_bloom=True, with_vignette=False):
    p = full(params)
    x = img_lin.astype(np.float64)
    if with_bloom:
        x = x + bloom_layer(x, p)
    if with_vignette:
        x = vignette(x, p)
    x = x * 2 ** p['postExposure']
    return lin_to_srgb(grade_lut(x, p))

def display_of(lin_rgb, params):
    """display sRGB (0-1) of one scene-linear colour through the grade (no bloom)."""
    p = full(params)
    x = np.asarray(lin_rgb, np.float64) * 2 ** p['postExposure']
    return lin_to_srgb(grade_lut(x[None, :], p))[0]

# ---------- colour temperature ----------
def _g(l, mu, s1, s2):
    s = np.where(l < mu, s1, s2)
    return np.exp(-0.5 * ((l - mu) / s) ** 2)

def cmf(l):
    x = 1.056 * _g(l, 599.8, 37.9, 31.0) + 0.362 * _g(l, 442.0, 16.0, 26.7) - 0.065 * _g(l, 501.1, 20.4, 26.2)
    y = 0.821 * _g(l, 568.8, 46.9, 40.5) + 0.286 * _g(l, 530.9, 16.3, 31.1)
    z = 1.217 * _g(l, 437.0, 11.8, 36.0) + 0.681 * _g(l, 459.0, 26.0, 13.8)
    return x, y, z

XYZ_2_sRGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])

def kelvin_lin(K):
    """linear sRGB (D65-balanced) of a blackbody at K, max channel = 1."""
    l = np.arange(380, 781, 1.0)
    lm = l * 1e-9
    B = 1 / (lm ** 5 * (np.exp(1.4388e-2 / (lm * K)) - 1))
    x, y, z = cmf(l)
    XYZ = np.array([(B * x).sum(), (B * y).sum(), (B * z).sum()])
    rgb = XYZ_2_sRGB @ XYZ
    rgb = np.maximum(rgb, 0)
    rgb = rgb / rgb.max()
    # normalise so that 6504K-ish is neutral: divide by D65 blackbody-ish response
    return rgb

def kelvin_hex(K):
    ref = kelvin_lin(6504.0)
    c = kelvin_lin(K) / ref
    return lin_to_hex(c / c.max())

if __name__ == '__main__':
    for v in [0.01, 0.02, 0.05, 0.1, 0.18, 0.3, 0.5, 1, 2, 3, 5.3]:
        print('neutral(%.3f) = %.4f lin  -> sRGB %.1f' % (v, neutral_tonemap(v), lin_to_srgb(neutral_tonemap(v)) * 255))
    for K in [1900, 2100, 2700, 3200, 4000, 4300, 5000, 5600, 6500, 7500, 9000, 12000, 16000]:
        print(K, kelvin_hex(K))
    for T in [-40, -30, -20, -10, 10, 20, 30]:
        print('temp', T, round(wb_equiv_cct(T)))
