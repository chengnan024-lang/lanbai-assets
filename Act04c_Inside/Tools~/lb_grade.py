"""The grade every reference render of the 门内 session goes through: the Grading kit's PPv2 Neutral engine model with the
engine-solved profiles (Grading/Tools~/inputs/grades_engine.json) + the bible simulator's bloom (bloom is added to the
scene-linear image before the LUT, as in PPv2). Same path as Grading/Tools~/engine/compare_frames.render_engine.

  grade(img_lin, 'S4c', dEV=0.0, xfade=None)  -> sRGB codes 0..255 (float)
     xfade = ('S4', 'S4c', w): PPv2 parameter interpolation between two scene profiles (weight w of the newer one)
  solve_fill(target_hex, 'S4c')               -> (linear fill rgb, '#RRGGBB @ +n') that displays target_hex
  apl(codes)                                   -> mean Rec.709 luma (0..255), the bible's APL
"""
import copy
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Grading', 'Tools~', 'engine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'lens_cine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'bible_work'))
import ppv2_engine as E  # noqa: E402
import ppv2 as LD  # noqa: E402
from lutlib_core import patch_ppv2  # noqa: E402

patch_ppv2(LD)
G = json.load(open(os.path.join(REPO, 'Grading', 'Tools~', 'inputs', 'grades_engine.json'), encoding='utf-8'))
_LUTS = {}


def profile(sid):
    p = copy.deepcopy(G['profiles'][sid]['ppv2'])
    p['colorFilter'] = G['common']['colorFilter']
    p['hueShift'] = G['common']['hueShift']
    return p


def _lerp(a, b, w):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * w
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return [_lerp(x, y, w) for x, y in zip(a, b)]
    if isinstance(a, dict):
        return {k: _lerp(a[k], b[k], w) for k in a}
    if isinstance(a, str) and isinstance(b, str) and a.startswith('#'):
        ca, cb = E.hex_raw(a), E.hex_raw(b)
        c = ca + (cb - ca) * w
        return '#%02X%02X%02X' % tuple(np.clip(np.round(c * 255), 0, 255).astype(int))
    return b if w >= 0.5 else a


def blended(xfade):
    a, b, w = xfade
    return _lerp(profile(a), profile(b), float(w))


def grade(img, sid='S4c', dEV=0.0, xfade=None, bloom=True, lens=None):
    p = blended(xfade) if xfade else profile(sid)
    pg = copy.deepcopy(p)
    pg['postExposure'] = p['postExposure'] + dEV
    x = np.maximum(np.asarray(img, np.float64), 0)
    if bloom:
        x = x + LD.bloom_layer(x, LD.full(p))
    key = json.dumps(pg, sort_keys=True)
    if key not in _LUTS:
        _LUTS.clear()
        _LUTS[key] = E.bake_lut(pg)
    c = E.codes(x.reshape(-1, 3), pg, _LUTS[key]).reshape(x.shape)
    if lens is not None:                         # desktop LENS_CLEAN vignette (bible §1.4): codes x vignette mask
        c = apply_vignette(c, *lens)
    return c


def apply_vignette(c, intensity=0.20, smooth=0.40, colour='#02040A'):
    """PPv2 classic vignette (intensity, smoothness, rounded off) in display space, as the bible's simulators do."""
    h, w = c.shape[:2]
    y, x = np.mgrid[0:h, 0:w]
    d = np.stack([(x + 0.5) / w - 0.5, (y + 0.5) / h - 0.5], -1)
    d[..., 0] *= w / h * 0.0 + 1.0
    d = np.abs(d) * intensity
    d = np.power(np.clip(d, 0, None), smooth * 0 + 1)
    vf = np.power(np.clip(1.0 - np.sum(d * d, -1), 0, 1), smooth * 10 + 1e-3)[..., None]
    col = E.hex8(colour)
    return c * vf + col * (1 - vf)


def apl(codes):
    c = np.asarray(codes, float)
    return float(np.mean(c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722))


def display(lin_rgb, sid='S4c', dEV=0.0):
    """display codes of a flat scene-linear colour (no bloom: a large flat patch never blooms spatially)."""
    return E.codes(np.asarray(lin_rgb, float).reshape(1, 3), dict(profile(sid), postExposure=profile(sid)['postExposure'] + dEV))[0]


def solve_fill(target_hex, sid='S4c', start=None, keep_hue=None):
    """least-squares scene-linear fill that displays target_hex under the profile (no bloom)."""
    from scipy.optimize import least_squares
    tgt = E.hex8(target_hex)
    x0 = np.log(np.maximum(start if start is not None else E.srgb_decode(tgt / 255.0) * 2.0, 1e-5))
    f = lambda lx: display(np.exp(lx), sid) - tgt   # noqa: E731
    r = least_squares(f, x0, xtol=1e-12, ftol=1e-12)
    lin = np.exp(r.x)
    return lin, hdr_string(lin), float(np.abs(display(lin, sid) - tgt).max())


def hdr_string(lin):
    """Unity HDR colour picker notation: '#RRGGBB @ +n' (the picker's colour is sRGB of lin / 2^n, max channel 1)."""
    m = float(np.max(lin))
    n = max(0.0, np.log2(m)) if m > 1 else 0.0
    base = np.asarray(lin) / 2 ** n
    s = E.srgb_encode(np.clip(base, 0, 1))
    hx = '#%02X%02X%02X' % tuple(np.clip(np.round(s * 255), 0, 255).astype(int))
    return hx if n == 0 else '%s @ +%.2f' % (hx, n)


def parse_fill(h, n=0.0):
    return E.srgb_decode(E.hex_raw(h)) * 2.0 ** n


if __name__ == '__main__':
    for tgt, bib in (('#1D2336', '#2A3347'), ('#53606E', '#6E808D'), ('#1A2030', None), ('#FFF1DC', None)):
        lin, s, err = solve_fill(tgt)
        print(tgt, '->', s, 'lin', np.round(lin, 4), 'err', err, '| bible', bib, '->', E.to_hex(display(parse_fill(bib), 'S4c')) if bib else '')
