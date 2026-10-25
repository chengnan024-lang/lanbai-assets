# -*- coding: utf-8 -*-
"""参考图的后期：场景线性 EXR（Unity 单位，见 lk_bpy）→ 雾（Exp，按深度；天不吃雾）→ PPv2 bloom → PPv2 Neutral 调色
（引擎模型 Grading/Tools~/engine/ppv2_engine.py + grades_engine.json）→ 8 位 sRGB。
另外量数：APL（Rec.709 luma 均值，含 bloom）、最亮点在哪、指定区域的中位色、暖色进阴影的比例、紫的占比。

用法（模块）：
    import lk_post as P
    png, m = P.grade('x.exr', 'S2', fog=(0.008, '#0D0F15'), out='x.png', regions={'head': mask})
"""
import copy
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Grading', 'Tools~', 'engine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'lens_cine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'bible_work'))
import ppv2_engine as E  # noqa: E402
import ppv2 as LD  # noqa: E402
from lutlib_core import patch_ppv2  # noqa: E402
patch_ppv2(LD)

GE = json.load(open(os.path.join(REPO, 'Grading', 'Tools~', 'inputs', 'grades_engine.json'), encoding='utf-8'))
_LUTS = {}


def profile(sid):
    P = copy.deepcopy(GE['profiles'][sid]['ppv2'])
    P['colorFilter'] = GE['common']['colorFilter']
    P['hueShift'] = GE['common']['hueShift']
    return P


def hexlin(h):
    h = h.lstrip('#')
    s = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)


def fill(h, ev=0.0):
    """Unity HDR colour picker value '#RRGGBB @ +ev' -> scene-linear rgb."""
    return hexlin(h) * 2.0 ** ev


def apply_fog(img, depth, density, colour_lin, sky_mask=None):
    f = np.exp(-np.maximum(depth, 0) * density)[..., None]
    out = img * f + colour_lin[None, None] * (1 - f)
    if sky_mask is not None:
        out[sky_mask] = img[sky_mask]
    return out


def to_codes(img, sid, bloom=True):
    p = profile(sid)
    x = np.maximum(img.astype(np.float64), 0)
    if bloom:
        x = x + LD.bloom_layer(x, LD.full(p))
    if sid not in _LUTS:
        _LUTS[sid] = E.bake_lut(p)
    return E.codes(x, p, _LUTS[sid])


def luma(codes):
    return codes[..., :3] @ np.array([0.2126, 0.7152, 0.0722])


def lab(codes):
    s = np.clip(codes / 255.0, 0, 1)
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = l @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return L, a, b


def metrics(codes, regions=None):
    y = luma(codes)
    L, a, b = lab(codes)
    C = np.hypot(a, b)
    h = (np.degrees(np.arctan2(b, a)) + 360) % 360
    m = dict(APL=float(y.mean()), luma_p50=float(np.median(y)), luma_p99=float(np.percentile(y, 99)))
    k = max(1, int(0.001 * y.size))
    idx = np.argsort(y.ravel())[-k:]
    H, W = y.shape
    ys, xs = np.unravel_index(idx, y.shape)
    m['brightest_0.1pct_centroid_xy'] = [float(xs.mean() / W), float(ys.mean() / H)]
    m['brightest_0.1pct_spread'] = [float(xs.std() / W), float(ys.std() / H)]
    dark = y < 20
    warm_dark = dark & (h > 30) & (h < 90) & (C > 8)
    m['warm_in_shadow_pct'] = float(100 * warm_dark.sum() / max(dark.sum(), 1))
    purple = (h > 290) & (h < 325) & (C > 15)
    m['purple_pct'] = float(100 * purple.mean())
    if regions:
        for name, mask in regions.items():
            if mask is None or mask.sum() == 0:
                continue
            c = np.median(codes[mask], axis=0)
            m['region_' + name] = '#%02X%02X%02X' % tuple(int(round(v)) for v in np.clip(c, 0, 255))
            m['region_' + name + '_luma'] = float(np.median(y[mask]))
            m['region_' + name + '_px'] = int(mask.sum())
    return m


def save_png(codes, path, thumb=None):
    from PIL import Image
    im = Image.fromarray(np.clip(np.round(codes), 0, 255).astype(np.uint8))
    im.save(path, optimize=True)
    if thumb:
        w = 640
        im.resize((w, int(im.height * w / im.width)), Image.LANCZOS).save(thumb, optimize=True)
    return path


def grade(rgb, depth, sid, fog=None, sky_mask=None, out=None, regions=None, thumb=None):
    """rgb: (H, W, 3) scene-linear (Unity units). depth: (H, W) metres (inf for sky)."""
    img = rgb
    if fog is not None:
        dens, col = fog
        cl = hexlin(col) if isinstance(col, str) else np.asarray(col)
        img = apply_fog(img, np.where(np.isfinite(depth), depth, 1e6), dens, cl, sky_mask)
    codes = to_codes(img, sid)
    m = metrics(codes, regions)
    if out:
        save_png(codes, out, thumb)
    return codes, m


if __name__ == '__main__':
    # self-test: the calib fills must come out at their screen targets
    for sid, fh, ev, tgt in (('S2', '#FF7B00', 1.14, '#EDAD77'), ('S11', '#FF8003', 0.19, '#D08A59'), ('S11', '#0F283C', 0, '#0F2438'),
                             ('S1', '#E7FEFF', 1.03, '#EEF5F7'), ('S2', '#0D0F15', 0, '#0A0F18')):
        c = to_codes(fill(fh, ev)[None, None], sid, bloom=False)[0, 0]
        print(sid, fh, '@%+.2f' % ev, '->', '#%02X%02X%02X' % tuple(int(round(v)) for v in c), 'target', tgt)
