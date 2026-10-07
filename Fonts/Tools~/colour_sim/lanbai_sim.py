# -*- coding: utf-8 -*-
"""The art bible's PPv2 look simulator, vendored so the Fonts kit can solve its fills anywhere (verify r3 m2).

Source of truth: art/bible_work/calib_final.py (solve, disp_hex, set_str), art/bible_work/lutlib_core.py (patch),
art/lens_cine/ppv2.py, art/grades_final.json. Those four are copied here UNCHANGED except this file, which repeats
calib_final's three functions with a params dict instead of a profile name, so a poem can be solved under a
PPv2 volume BLEND (PPv2 overrides are absolute: param = lerp(lower volume, higher volume, weight), bible §1.4).
lanbai_color.py prefers art/bible_work when it exists and checks that both give identical fills.
"""
import os, sys, copy, json
import numpy as np
from scipy.optimize import minimize, least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ppv2                                   # noqa: E402  (art/lens_cine/ppv2.py, unchanged)
from lutlib_core import patch_ppv2, g2l      # noqa: E402  (art/bible_work/lutlib_core.py, unchanged)
patch_ppv2(ppv2)

GRADES_PATH = os.path.join(HERE, 'grades_final.json')
GF = json.load(open(GRADES_PATH, encoding='utf-8'))
PROF = {k: v['ppv2'] for k, v in GF['profiles'].items()}


def disp_hex(lin, params):
    return ppv2.srgb_to_hex(ppv2.display_of(np.asarray(lin, float), params))


def solve(target_hex, params):
    """calib_final.solve, verbatim, with params instead of PROF[prof]."""
    t_s = np.array([int(target_hex[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    t = ppv2.srgb_to_lin(t_s)
    f = lambda x: (ppv2.display_of(np.exp(x), params) - t_s) * 255
    cost = lambda x: float((f(x) ** 2).sum())
    starts = [np.log(np.maximum((t * (1 - m) + t.mean() * m) * sc, 1e-6)) for m in (0, .3, .6) for sc in (.5, 1, 2, 4)]
    x0 = min(starts, key=cost)
    r = minimize(cost, x0, method='Nelder-Mead', options=dict(xatol=1e-6, fatol=1e-5, maxiter=5000))
    r2 = least_squares(f, np.clip(r.x, np.log(1e-7) + 1e-6, np.log(80) - 1e-6), bounds=(np.log(1e-7), np.log(80)))
    x = np.exp(r2.x)
    return x, np.abs(f(r2.x)).max()


def set_str(x):
    m = x.max()
    return ppv2.lin_to_hex(x) if m <= 1.0 else '%s @ +%.2f' % (ppv2.lin_to_hex(x / m), np.log2(m))


def _lerp(a, b, w):
    if isinstance(a, dict):
        return {k: _lerp(a[k], b[k], w) for k in a}
    if isinstance(a, (list, tuple)):
        return [_lerp(x, y, w) for x, y in zip(a, b)]
    if isinstance(a, str):                    # bloom colour (no effect on display_of); PPv2 lerps it too
        ca, cb = ppv2.hex_to_lin(a), ppv2.hex_to_lin(b)
        return ppv2.lin_to_hex(ca + (cb - ca) * w)
    return a + (b - a) * w


def params_of(spec, prof=None):
    """'S8' -> PROF['S8'];  ('S2', 'S3', 0.3) -> the PPv2 blend with the S3 volume at weight 0.3 over S2."""
    P = PROF if prof is None else prof
    if isinstance(spec, str):
        return copy.deepcopy(P[spec])
    a, b, w = spec
    return _lerp(P[a], P[b], float(w))


def spec_name(spec):
    return spec if isinstance(spec, str) else '%s→%s@%.3f' % (spec[0], spec[1], spec[2])
