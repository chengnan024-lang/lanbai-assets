# -*- coding: utf-8 -*-
"""Reference-render grading = what Unity shows (CONTROL §2.5):
   scene-linear frame  ->  + PPv2 bloom (art simulator's corrected bloom: lutlib_core.patch_ppv2, threshold/knee/clamp
   in gamma space, pyramid for a 1920-wide screen)  ->  PPv2 Neutral HDR path with the GRADING KIT'S ENGINE parameters
   (Grading/Tools~/engine/ppv2_engine.py + Grading/Tools~/inputs/grades_engine.json; the 33^3 float16 LUT, trilinear).
Also: metrics used in every README (APL = mean Rec.709 luma of the 8-bit sRGB frame incl. bloom, bible §1.5; brightest
2000 px box; purple share h_ab 290-325 & C* > 15 (bible §1.3.4); share of luma < 12).
usage as a module: grade(img_lin, 'S7a') -> uint8 sRGB;  metrics(uint8) -> dict"""
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
_LUT = {}


def engine_params(sid):
    P = copy.deepcopy(GE['profiles'][sid]['ppv2'])
    P['colorFilter'] = GE['common']['colorFilter']
    P['hueShift'] = GE['common']['hueShift']
    return P


def bloom_params(sid):
    P = engine_params(sid)
    b = dict(P['bloom'])
    b.setdefault('diffusion', 7.0)
    return LD.full(dict(bloom=b))


def grade(img_lin, sid, extra_ev=0.0):
    """img_lin: [H, W, 3] scene-linear (before postExposure). extra_ev: the EXPO_UP/DOWN helper's net EV (b + ΔEV)."""
    x = np.asarray(img_lin, np.float64)
    x = x + LD.bloom_layer(x, bloom_params(sid))
    p = engine_params(sid)
    if extra_ev:
        p = dict(p); p['postExposure'] = p['postExposure'] + extra_ev
    key = (sid, round(extra_ev, 4))
    if key not in _LUT:
        _LUT[key] = E.bake_lut(p)
    codes = E.codes(x, p, _LUT[key])
    return np.clip(np.round(codes), 0, 255).astype(np.uint8)


def screen_of(lin_rgb, sid):
    """display hex of one scene-linear colour (no bloom)"""
    return E.screen_hex(np.asarray(lin_rgb, np.float64), engine_params(sid))


def srgb_to_lin(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lab(rgb8):
    lin = srgb_to_lin(rgb8 / 255.0)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return L, a, b


def metrics(rgb8, mask=None):
    luma = rgb8[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    m = np.ones(luma.shape, bool) if mask is None else mask
    L, a, b = lab(rgb8[..., :3].astype(np.float64))
    C = np.hypot(a, b)
    h = (np.degrees(np.arctan2(b, a)) + 360) % 360
    purple = (h >= 290) & (h <= 325) & (C > 15)
    flat = np.argsort(luma.ravel())[-2000:]
    ys, xs = np.unravel_index(flat, luma.shape)
    return dict(APL=round(float(luma[m].mean()), 1), luma_lt12=round(float((luma[m] < 12).mean() * 100), 1),
                purple_pct=round(float(purple[m].mean() * 100), 2), max_luma=round(float(luma.max()), 1),
                brightest2000_box=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                brightest2000_centre=[round(float(xs.mean()), 1), round(float(ys.mean()), 1)])


if __name__ == '__main__':
    for sid in ('S6', 'S7a', 'S7b', 'S8'):
        print(sid, '18% grey ->', screen_of([0.18] * 3, sid), ' black ->', screen_of([0, 0, 0], sid))


def hex_codes(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float64)


def fill_for(target_hex, sid, iters=40):
    """scene-linear rgb whose engine screen value is target_hex under profile sid (no bloom), by per-channel bisection
    in log space with the other channels coupled (repeated sweeps)."""
    p = engine_params(sid)
    tgt = hex_codes(target_hex)
    lin = np.maximum(srgb_to_lin(tgt / 255.0), 1e-4)
    for _ in range(6):
        for c in range(3):
            lo, hi = np.log2(1e-5), np.log2(64.0)
            for _ in range(iters):
                mid = 0.5 * (lo + hi)
                x = lin.copy(); x[c] = 2.0 ** mid
                v = E.codes_direct(x[None, :], p)[0][c]
                if v < tgt[c]:
                    lo = mid
                else:
                    hi = mid
            lin[c] = 2.0 ** (0.5 * (lo + hi))
    return lin
