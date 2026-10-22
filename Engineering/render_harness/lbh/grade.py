# -*- coding: utf-8 -*-
"""Scene-linear frame -> what PPv2 3.4 (HDR, Neutral) shows on a desktop screen, for one Lanbai grade state.

Colour grade: Grading/Tools~/engine/ppv2_engine.py (engine-faithful 33^3 float16 LUT, LogC, trilinear).
Bloom, vignette: written here from the PPv2 3.x source (Bloom.cs, Bloom.shader, Sampling.hlsl, Uber.shader):
  Bloom.cs   tw = floor(W / 2), th = floor(H / 2); s = max(tw, th); logs = log2(s) + min(diffusion, 10) - 10;
             iterations = clamp(floor(logs), 1, 16); sampleScale = 0.5 + logs - floor(logs)
             lthresh = GammaToLinearSpace(threshold); knee = lthresh * softKnee + 1e-5;
             _Threshold = (lthresh, lthresh - knee, 2 knee, 0.25 / knee); _Params.x = GammaToLinearSpace(clamp)
             intensity = 2^(intensity / 10) - 1; colour = settings.color.linear, set with MaterialPropertyBlock.SetColor
             (which linearises again in Linear colour space -> the effective tint is linearised twice)
             mip0 = Prefilter4(source) (half res); mip i = Downsample4(mip i-1), size max(floor(/2), 1);
             up = mip last; for i = it-2 .. 0: up = UpsampleBox(up, sampleScale) + mip i
  fastMode   (every Lanbai profile): *4Tap / UpsampleBox passes, Uber keyword BLOOM_LOW
  Prefilter  color = min(_Params.x, color * autoExposure(=1)); QuadraticThreshold:
             br = max3(c); rq = clamp(br - curve.x, 0, curve.y); rq = curve.z rq^2; c *= max(rq, br - thr) / max(br, 1e-4)
  Uber       color *= autoExposure; color += UpsampleBox(bloomTex, uv, bloomTexel, sampleScale) * intensity * colour;
             vignette (classic): d = |uv - c| * 3 I; d.x *= rounded ? aspect : 1; d = pow(sat(d), (1 - r) * 6 + r);
             f = pow(sat(1 - dot(d, d)), 5 s); color *= lerp(vigColour.linear, 1, f)
             then colour grading: color *= 2^postExposure -> LogC -> LUT  (ppv2_engine.codes)
Sampling is bilinear with clamp addressing; destination texel centres; the 4-tap filters are separable, so they are
evaluated as two 1-D passes (exact for a product of bilinear taps).
Volume blending: PPv2 ParameterOverride.Interp = lerp(current, override, weight), volumes in priority order, starting
from the defaults (bloom intensity 0 = off). Grain is not simulated (it is noise; Unity screenshots are compared on
APL / means, where grain averages out)."""
import json

import numpy as np

from . import paths

E = paths.import_engine()

# -------------------------------------------------------------------------------------------------- data
_GRADES = None


def grades():
    global _GRADES
    if _GRADES is None:
        _GRADES = json.load(open(paths.GRADES_ENGINE, encoding='utf-8'))
    return _GRADES


def gamma01(c):
    """hex '#RRGGBB' or a 0..1 gamma triplet -> np.array of gamma components 0..1."""
    if isinstance(c, str):
        h = c.lstrip('#')
        return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return np.asarray(c, float)


def hex_lin(c):
    v = gamma01(c)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def gamma_to_linear_space(x):
    """Mathf.GammaToLinearSpace (Unity ColorSpaceConversion): sRGB curve below 1, pow 2.2 at and above 1
    (bible 1.4: threshold 1.93 -> 4.248 linear, T0 = 4.248 x (1 - 0.5) = 2.124 for S4; clamp 4.24 -> 24.0)."""
    x = float(x)
    if x <= 0.04045:
        return x / 12.92
    if x < 1.0:
        return ((x + 0.055) / 1.055) ** 2.4
    return x ** 2.2


# PPv2 defaults for the overridden parameter set (what a weight-0 volume blends from)
DEFAULT_STATE = dict(postExposure=0.0, temperature=0.0, tint=0.0, saturation=0.0, contrast=0.0,
                     lift=[1.0, 1.0, 1.0, 0.0], gamma=[1.0, 1.0, 1.0, 0.0], gain=[1.0, 1.0, 1.0, 0.0],
                     mixer=list(E.MIXER_IDENTITY),
                     bloom=dict(intensity=0.0, threshold=1.0, softKnee=0.5, diffusion=7.0, color='#FFFFFF', clamp=65472.0),
                     vignette=dict(intensity=0.0, smoothness=0.2, roundness=1.0, rounded=False, color='#000000'))


def _lerp(a, b, w):
    if isinstance(a, str) or isinstance(b, str):   # colours: ColorParameter.Interp lerps the raw (gamma) floats, no rounding
        ca, cb = gamma01(a), gamma01(b)
        return [float(x) for x in ca + (cb - ca) * w]
    if isinstance(a, (list, tuple)):
        return [x + (y - x) * w for x, y in zip(a, b)]
    if isinstance(a, bool):
        return b if w > 0 else a
    return a + (b - a) * w


def profile_overrides(key):
    """The overridden parameters of a profile / helper / lens layer, as a flat dict in DEFAULT_STATE's shape."""
    G = grades()
    if key in G['profiles']:
        p = dict(G['profiles'][key]['ppv2'])
        b = dict(p.get('bloom', {}))
        b['clamp'] = G['common']['bloom']['clamp']
        p['bloom'] = b
        p['vignette'] = dict(intensity=0.0)       # every scene profile overrides vignette intensity 0 (bible 1.4)
        return p
    if key in G['helpers'] and 'ppv2' in G['helpers'][key]:
        return dict(G['helpers'][key]['ppv2'])
    if key in G['lens_desktop_only']:
        v = G['lens_desktop_only'][key]['vignette']
        return dict(vignette=dict(intensity=v['intensity'], smoothness=v['smoothness'], roundness=v['roundness'],
                                  rounded=v['rounded'], color=v['color']))
    raise KeyError('unknown grade key %r (profiles: %s)' % (key, ', '.join(G['profiles'])))


def priority(key):
    G = grades()
    for grp in ('profiles', 'helpers', 'lens_desktop_only'):
        if key in G[grp]:
            return G[grp][key]['priority']
    raise KeyError(key)


def blend(weights):
    """weights: {key: w} or [(key, w), ...]. Volumes are applied in priority order (low first), each
    param = lerp(param, override, w) for every parameter that volume overrides (PPv2 semantics)."""
    items = list(weights.items()) if isinstance(weights, dict) else list(weights)
    items.sort(key=lambda kw: priority(kw[0]))
    st = json.loads(json.dumps(DEFAULT_STATE))
    for key, w in items:
        if w <= 0:
            continue
        w = min(float(w), 1.0)                       # PostProcessManager: Mathf.Clamp01(volume.weight)
        ov = profile_overrides(key)
        for k, v in ov.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    st[k][kk] = _lerp(st[k][kk], vv, w)
            else:
                st[k] = _lerp(st[k], v, w)
    return st


def state_for(spec):
    """'S4' | 'S4+LENS_CLEAN' | {'S3':1,'S4':0.4} | [('S3',1),('EXPO_UP',0.1)] | an already blended state dict."""
    if isinstance(spec, dict) and 'postExposure' in spec:
        return spec
    if isinstance(spec, str):
        return blend({k: 1.0 for k in spec.split('+')})
    return blend(spec)


def expo_weight(dEV, b):
    """bible 1.4: w = dEV / (4 - b) on EXPO_UP, or -dEV / (b + 4) on EXPO_DOWN."""
    if dEV >= 0:
        return 'EXPO_UP', dEV / (4.0 - b)
    return 'EXPO_DOWN', -dEV / (b + 4.0)


# -------------------------------------------------------------------------------------------------- sampling
def _sample1d(img, axis, pos):
    """bilinear-in-one-axis sample, clamp addressing. pos = texel-space coordinates (centre of texel i = i + 0.5)."""
    n = img.shape[axis]
    x = np.clip(pos - 0.5, 0.0, n - 1.0)
    i0 = np.floor(x).astype(int)
    i1 = np.minimum(i0 + 1, n - 1)
    f = (x - i0)
    a = np.take(img, i0, axis=axis)
    b = np.take(img, i1, axis=axis)
    shp = [1] * img.ndim
    shp[axis] = -1
    f = f.reshape(shp)
    return a + (b - a) * f


def _four_tap(src, out_w, out_h, off_src_texels):
    """average of 4 bilinear taps at dst-centre-uv +- off (in SOURCE texels), resampled to (out_h, out_w)."""
    h, w = src.shape[:2]
    ux = (np.arange(out_w) + 0.5) / out_w * w
    uy = (np.arange(out_h) + 0.5) / out_h * h
    o = off_src_texels
    tx = 0.5 * (_sample1d(src, 1, ux - o) + _sample1d(src, 1, ux + o))
    return 0.5 * (_sample1d(tx, 0, uy - o) + _sample1d(tx, 0, uy + o))


def bloom_pyramid(lin, b):
    """PPv2 fastMode bloom: returns the full-res bloom term already multiplied by intensity and colour (linear)."""
    if b['intensity'] <= 0:
        return np.zeros_like(lin)
    H, W = lin.shape[:2]
    tw, th = W // 2, H // 2
    s = max(tw, th)
    logs = np.log2(s) + min(b['diffusion'], 10.0) - 10.0
    logs_i = int(np.floor(logs))
    iterations = int(np.clip(logs_i, 1, 16))
    sample_scale = 0.5 + logs - logs_i
    lthresh = gamma_to_linear_space(b['threshold'])
    knee = lthresh * b['softKnee'] + 1e-5
    curve = (lthresh - knee, knee * 2.0, 0.25 / knee)
    lclamp = gamma_to_linear_space(b.get('clamp', 65472.0))
    mips = []
    cur = lin
    for i in range(iterations):
        d = _four_tap(cur, tw, th, 1.0)
        if i == 0:
            d = np.minimum(lclamp, d)
            br = d.max(-1)
            rq = np.clip(br - curve[0], 0.0, curve[1])
            rq = curve[2] * rq * rq
            d = d * (np.maximum(rq, br - lthresh) / np.maximum(br, 1e-4))[..., None]
        mips.append(d)
        cur = d
        tw, th = max(tw // 2, 1), max(th // 2, 1)
    up = mips[-1]
    for i in range(iterations - 2, -1, -1):
        hh, ww = mips[i].shape[:2]
        up = _upsample_box(up, ww, hh, sample_scale) + mips[i]
    final = _upsample_box(up, W, H, sample_scale)
    k = 2.0 ** (b['intensity'] / 10.0) - 1.0
    # Bloom.cs: linearColor = color.linear, then uberSheet.properties.SetColor(_Bloom_Color, linearColor):
    # MaterialPropertyBlock.SetColor converts sRGB -> linear AGAIN in a Linear-space project, so the tint the
    # Uber shader sees is GammaToLinear(GammaToLinear(c)) (white unaffected). Verified against the 3.4.0 source.
    c = np.array([gamma_to_linear_space(v) for v in hex_lin(b['color'])])
    return final * k * c


def _upsample_box(src, out_w, out_h, sample_scale):
    """UpsampleBox: 4 taps at +-(sampleScale / 2) SOURCE texels around the destination uv."""
    return _four_tap(src, out_w, out_h, 0.5 * sample_scale)


def vignette_mul(H, W, v):
    if v['intensity'] <= 0:
        return None
    yy, xx = np.mgrid[0:H, 0:W]
    u = (xx + 0.5) / W
    vv = (yy + 0.5) / H
    dx = np.abs(u - 0.5) * v['intensity'] * 3.0
    dy = np.abs(vv - 0.5) * v['intensity'] * 3.0
    if v.get('rounded'):
        dx = dx * (W / float(H))
    r = v.get('roundness', 1.0)
    p = (1.0 - r) * 6.0 + r
    dx, dy = np.clip(dx, 0, 1) ** p, np.clip(dy, 0, 1) ** p
    f = np.clip(1.0 - (dx * dx + dy * dy), 0.0, 1.0) ** (v['smoothness'] * 5.0)
    col = hex_lin(v['color'])
    return col[None, None, :] + (1.0 - col[None, None, :]) * f[..., None]


# -------------------------------------------------------------------------------------------------- the frame
def grade(lin, spec, bloom=True, lens=True):
    """lin: (H, W, 3) scene-linear float (what the camera writes into the ARGBHalf target before PPv2).
    spec: see state_for(). lens=False drops vignette even if the spec has a LENS layer.
    Returns (codes float 0..255 (H, W, 3), state, bloom term)."""
    st = state_for(spec)
    x = np.maximum(np.nan_to_num(np.asarray(lin, np.float64)[..., :3], nan=0.0, posinf=65504.0), 0.0)
    x = np.minimum(x, 65504.0)          # SafeHDR: min(c, HALF_MAX)
    bl = bloom_pyramid(x, st['bloom']) if bloom else np.zeros_like(x)
    x = x + bl
    if lens:
        vm = vignette_mul(x.shape[0], x.shape[1], st['vignette'])
        if vm is not None:
            x = x * vm
    p = {k: st[k] for k in ('postExposure', 'temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain', 'mixer')}
    lut = E.bake_lut(p)
    out = np.empty_like(x)
    step = 256                                   # rows per chunk (memory)
    for r0 in range(0, x.shape[0], step):
        out[r0:r0 + step] = E.codes(x[r0:r0 + step], p, lut)
    return out, st, bl


def to_u8(codes):
    return np.clip(np.round(codes), 0, 255).astype(np.uint8)
