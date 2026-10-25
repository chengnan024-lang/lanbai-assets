# -*- coding: utf-8 -*-
"""第 8 幕终审 A5：蓝时的卡色（D-25：按幕解）。蓝时里没有太阳，云只被蓝时的天照着：
  - 云体 L* 不高于同仰角的天（不比天亮），C* 不高于天的 C*（不比天艳）；
  - F12 的增益只往下走、不回弹：gain x lerp(1, g, smoothstep(0, w_end, wb))（act08_layout BLUE_FADE）。
在 995 和 1001.21（蓝时已满，wb = 1）的正前、车门帧里，每张看得见的卡：云体（覆盖 > 0.9）的 L*、C* 中值，对比同仰角
（±1°）、左右 ±12° 内没有卡的天的中值。g 二分到 max(L卡 − L天) ≤ −1；去饱和 desat 二分到 max(C卡 − C天) ≤ 0。
写 Docs~/blue_cards.json；数抄回 act08_layout.py 的 BLUE_FADE / BLUE_DESAT（不自动改源码）。"""
import os
import sys
import json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import act08_ref as R  # noqa: E402
R.POEM_ON = False
import lb_common as C  # noqa: E402

W = 480
VIEWS = [(995.0, 'hero'), (995.0, 'door_d12'), (1001.21, 'hero'), (1001.21, 'door_d12')]
BASE_BLUE = {k: list(R.LAYOUT['blue_colours']['raw'][k]) for k in ('SkyUpColor', 'GroundColor')}   # undesaturated


def set_blue(g, desat):
    R.BLUE_FADE[0] = g
    for k, v in BASE_BLUE.items():
        m = 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]      # about the luminance (= act08_layout._desat)
        R.LAYOUT['blue_colours'][k] = [m + (x - m) * desat for x in v]


def measure():
    worst_dL, worst_dC, rows = -99.0, -99.0, []
    for t, cam in VIEWS:
        R.COVER.clear()
        codes, m, lin = R.render(t, cam, W, 'bible_v2')
        V, hh, pix = R.rays(dict(R.CAMS[cam]), W)
        az, el = C.azel_from_dir(V)
        win = R.window_mask(V, t)
        px = codes.reshape(-1, 3)
        L, hue, cc = C.hue_chroma(px)
        allc = np.max(np.stack([v for k, v in R.COVER.items() if k.startswith('C:')]), 0) if R.COVER else np.zeros(len(V))
        for k, cov in R.COVER.items():
            if not k.startswith('C:'):
                continue
            body = (cov > 0.9) & win
            if body.sum() < 30:
                continue
            e0, a0 = float(np.median(el[body])), float(np.median(az[body]))
            ring = win & (allc < 0.02) & (np.abs(el - e0) < 1.0) & (np.abs(az - a0) < 12.0)
            if ring.sum() < 30:
                continue
            dL = float(np.median(L[body]) - np.median(L[ring]))
            dC = float(np.median(cc[body]) - np.median(cc[ring]))
            worst_dL, worst_dC = max(worst_dL, dL), max(worst_dC, dC)
            rows.append(dict(t=t, cam=cam, card=k[2:], el=round(e0, 1), az=round(a0, 1), L_card=round(float(np.median(L[body])), 1),
                             L_sky=round(float(np.median(L[ring])), 1), C_card=round(float(np.median(cc[body])), 1),
                             C_sky=round(float(np.median(cc[ring])), 1)))
    return worst_dL, worst_dC, rows


def main():
    g, desat = 1.0, 1.0
    set_blue(g, desat)
    dL0, dC0, rows0 = measure()
    print('start: worst dL %.1f dC %.1f' % (dL0, dC0), flush=True)
    lo, hi = 0.5, 0.8
    for _ in range(6):
        g = 0.5 * (lo + hi)
        set_blue(g, desat)
        dL, dC, _ = measure()
        print('g %.3f dL %.1f dC %.1f' % (g, dL, dC), flush=True)
        if dL <= -1.0:
            lo = g
        else:
            hi = g
    g = lo
    lo, hi = 0.0, 1.0
    for _ in range(6):
        desat = 0.5 * (lo + hi)
        set_blue(g, desat)
        dL, dC, _ = measure()
        print('desat %.3f dL %.1f dC %.1f' % (desat, dL, dC), flush=True)
        if dC <= 0.0:
            lo = desat
        else:
            hi = desat
    desat = lo
    for _ in range(4):                          # the grade is not linear: put L back under the sky if desat moved it
        set_blue(g, desat)
        dL, dC, _ = measure()
        print('touch-up g %.3f dL %.1f' % (g, dL), flush=True)
        if dL <= -1.0:
            break
        g *= 0.95
    set_blue(g, desat)
    dL, dC, rows = measure()
    res = dict(blue_fade_gain=round(g, 3), desat=round(desat, 3), worst_dL=round(dL, 1), worst_dC=round(dC, 1),
               before=dict(worst_dL=round(dL0, 1), worst_dC=round(dC0, 1), cards=rows0), after=rows,
               rule='final review A5 / D-25: card body L* <= the sky at its elevation (margin 1), C* <= the sky')
    print(json.dumps({k: v for k, v in res.items() if k not in ('before', 'after')}), flush=True)
    json.dump(res, open(os.path.join(KIT, 'Docs~', 'blue_cards.json'), 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
