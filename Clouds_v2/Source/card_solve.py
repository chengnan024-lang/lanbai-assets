# -*- coding: utf-8 -*-
"""给一张卡（两遍渲染）解 (g_sun, g_sky, shadow_cool)，让阴影体 → 阴影目标、受光顶 → 云顶目标（调色后的屏幕码）。
目标函数在调色后的 sRGB 码上；阴影的色相另加一项（远离薰衣草）。"""
import os
import sys
import json
import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lb_common as C  # noqa: E402
import card_check as K  # noqa: E402

WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')


def load(base):
    import make_clouds_v2 as V
    ps, a1 = V.load_prem(os.path.join(WORK, 'exr', f'_{base}__sun.exr'))
    pk, a2 = V.load_prem(os.path.join(WORK, 'exr', f'_{base}__sky.exr'))
    meta = json.load(open(os.path.join(WORK, 'exr', f'_{base}.json')))
    return ps, pk, 0.5 * (a1 + a2), meta


def combine(ps, pk, a, gs, gk, cool):
    if cool > 0:
        ls = ps @ C.LUMA
        body = a > 0.9
        ref = np.percentile(ls[body] / np.maximum(a[body], 1e-6), 97)
        lit = np.clip(ls / np.maximum(a, 1e-6) / ref, 0, 1)
        k = (cool * (1 - lit) ** 1.5)[..., None]
        ps = ps * (1 - k) + ls[..., None] * k
    return (ps * np.asarray(gs, np.float64) + pk * np.asarray(gk, np.float64)) / np.maximum(a, 1e-6)[..., None]


def sun_rgb(gain, K, base_hex='#FFC47A'):
    """Sun-pass multiplier: the lamp was rendered with base_hex; re-colour it to a black body K (same luminance x gain)."""
    k = C.LD.kelvin_lin(K)
    k = k / (k @ C.LUMA)
    b = C.hex_lin(base_hex)
    b = b / (b @ C.LUMA)
    return gain * k / b


def solve(base, targets=None, fix_cool=None, verbose=True):
    ps, pk, a, meta = load(base)
    T = dict(K.TARGET[meta['preset']])
    if targets:
        T.update(targets)
    body = a > 0.97
    # selections from the physical (1,1) mix, fixed during the solve
    lum0 = combine(ps, pk, a, 1, 1, 0) @ C.LUMA
    lb = lum0[body]
    lo, hi = np.percentile(lb, [10, 30])
    s_sh = body & (lum0 >= lo) & (lum0 <= hi)
    s_tp = body & (lum0 >= np.percentile(lb, 98))
    bg = K.sky_backdrop(meta['preset'], T['sun_az'] - meta['sun_rel_az'], 4, 4)[1, 1]
    tsh, ttp = C.hex_rgb(T['shadow']) * 255, C.hex_rgb(T['top']) * 255
    _, h_t, _ = C.hue_chroma(tsh)

    def measure(x):
        gs, gk, cool = sun_rgb(x[0], x[1]), x[2:5], (fix_cool if fix_cool is not None else 0.0)
        st = combine(ps, pk, a, gs, gk, cool)
        sh = np.median(st[s_sh], 0)
        tp = np.median(st[s_tp], 0)
        cs = C.grade(np.stack([sh, tp])[None], T['grade'], bloom=False)[0]
        return cs[0], cs[1]

    def f(x):
        if (x <= 0).any() or not 1500 <= x[1] <= 6000:
            return 1e6
        sh, tp = measure(x)
        _, h, c = C.hue_chroma(sh)
        dh = ((h - h_t + 180) % 360) - 180
        return float(((sh - tsh) ** 2).sum() + 0.5 * ((tp - ttp) ** 2).sum() + 2.0 * dh ** 2 * min(c / 10, 1))
    best = None
    for x0 in ([1.0, 3200, 1.0, 1.0, 1.0], [1.5, 2600, 0.9, 1.0, 1.2], [2.0, 2200, 0.8, 1.0, 1.3]):
        r = minimize(f, x0, method='Nelder-Mead', options=dict(xatol=1e-4, fatol=1e-3, maxiter=2000))
        if best is None or r.fun < best.fun:
            best = r
    sh, tp = measure(best.x)
    out = dict(base=base, g_sun=[round(float(v), 4) for v in sun_rgb(best.x[0], best.x[1])], sun_K=round(float(best.x[1])), sun_gain=round(float(best.x[0]), 4), g_sky=[round(float(v), 4) for v in best.x[2:5]],
               cool=fix_cool or 0.0, shadow=C.to_hex(sh), top=C.to_hex(tp),
               shadow_hC=[round(float(v), 1) for v in C.hue_chroma(sh)[1:]], top_hC=[round(float(v), 1) for v in C.hue_chroma(tp)[1:]])
    if verbose:
        print(json.dumps(out))
    return out


if __name__ == '__main__':
    for b in sys.argv[1:]:
        solve(b)
