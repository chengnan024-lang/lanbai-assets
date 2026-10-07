# -*- coding: utf-8 -*-
"""Verifier's feasibility probe for B1 (NOT shipping data): how small is the fix?

For every non-neutral profile it keeps everything in grades_final.json and re-solves ONLY the trackball lift
(x, y, 1, w) in the PPv2-source Neutral model of ppv2_neutral_check.py, so that
  * input 0 lands on the black the art simulator intended for that profile (S1/S2/S11: #02060C, bible 1.3.5), and
  * the four darkest test-card patches stay close to calib section C.
Then it reports section C (max codes, 33^3 LUT) and the section B non-blooming targets with those lifts.

The numbers it prints are a pointer for the art side (make_grades.py), not values to paste: the art side must
first give its simulator a Neutral branch, then re-solve and regenerate section B / C / D, LUTs and previews.
Usage: python3 lift_resolve_hint.py      (about 1-2 minutes on one core)
"""
import os, re, sys
import numpy as np
from scipy.optimize import minimize
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ppv2_neutral_check as M
sys.path.insert(0, os.path.join(M.ART, 'lens_cine'))
import ppv2 as ART  # the art simulator (ACES-branch spaces): only used for the intended black point

KS = np.arange(-6, 5)
P = np.vstack([np.zeros((1, 3)), np.stack([0.18 * 2.0 ** KS] * 3, -1)])   # row 0 = input 0, rows 1..11 = section C


def codes(q, lin):  # float sRGB codes without LUT quantisation (optimiser only)
    v = np.clip(M.grade(np.clip(M.lin2logc(lin * 2.0 ** q['postExposure']), 0, 1), q), 0, 1)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1 / 2.4) - 0.055) * 255


def engine(q, lin, lut=None):  # 33^3 ARGBHalf LUT, trilinear: what PPv2 renders
    lut = M.lut3d(q) if lut is None else lut
    return M.srgb8(M.sample3d(lut, np.clip(M.lin2logc(np.asarray(lin) * 2.0 ** q['postExposure']), 0, 1)))


def with_lift(p, x):
    q = dict(p); q['lift'] = [float(x[0]), float(x[1]), 1.0, float(x[2])]; return q


def section_b(prof_of):
    tot = bad = 0; worst = []; luts = {}
    for e in M.CAL['unlit']:
        if e['xT0'] >= 0.9 or e['scene'] not in M.G['profiles']: continue
        m = re.match(r'#([0-9A-Fa-f]{6})(?: @ \+?(-?[\d.]+))?', e['set'].strip())
        if not m: continue
        q = prof_of(e['scene'])
        if e['scene'] not in luts: luts[e['scene']] = M.lut3d(q)
        lin = M.s2l(M.hex_raw('#' + m.group(1))) * 2.0 ** float(m.group(2) or 0)
        d = int(np.abs(engine(q, lin[None, :], luts[e['scene']])[0] - M.hex8(e['display'])).max())
        tot += 1; bad += d > 3; worst.append((d, e['scene'], e['element']))
    worst.sort(reverse=True)
    return tot, bad, worst[:6]


def main():
    solved = {}
    print('id    intended black | shipped: engine black, section C max | lift-only: lift (x, y, 1, w) -> engine black, section C max')
    for sid in M.G['profiles']:
        p = M.prof(sid); tgt = np.array([M.hex8(h) for h in M.CAL['ramp'][sid]])
        black = ART.lin_to_hex(ART.grade_lut(np.zeros(3), ART.full(dict(p)))); T = M.hex8(black)
        g0 = engine(p, P)
        if sid == 'S10':
            print('%-4s  %s        | #%02X%02X%02X  %2d  (neutral: unchanged)' % (sid, black, *g0[0], np.abs(g0[1:] - tgt).max())); continue
        f = lambda x: np.sum((codes(with_lift(p, x), P[:1])[0] - T) ** 2) + 0.05 * np.sum((codes(with_lift(p, x), P[1:5]) - tgt[:4]) ** 2)
        starts = ([p['lift'][0], p['lift'][1], p['lift'][3] + 0.014], [0.9845, 0.9905, 0.0224], [0.99, 0.993, 0.012])
        r = min((minimize(f, s, method='Nelder-Mead', options=dict(maxiter=4000, xatol=1e-7, fatol=1e-6)) for s in starts), key=lambda r: r.fun)
        q = with_lift(p, r.x); solved[sid] = q; g = engine(q, P)
        print('%-4s  %s        | #%02X%02X%02X  %2d               | (%.4f, %.4f, 1, %.4f) -> #%02X%02X%02X  %d'
              % (sid, black, *g0[0], np.abs(g0[1:] - tgt).max(), r.x[0], r.x[1], r.x[2], *g[0], np.abs(g[1:] - tgt).max()))
    for tag, fn in (('shipped', M.prof), ('lift-only', lambda s: solved.get(s, M.prof(s)))):
        tot, bad, worst = section_b(fn)
        print('section B non-blooming targets, %-9s: %d of %d off by > 3 codes; worst %s' % (tag, bad, tot, worst))


if __name__ == '__main__':
    main()
