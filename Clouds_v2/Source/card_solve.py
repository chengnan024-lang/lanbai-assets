# -*- coding: utf-8 -*-
"""云卡 v2 的材质颜色求解（通道格式）：让代表卡（积云）在侧光（rel 70°）下
  阴影体（alpha > 0.97 里亮度 10–30 百分位的中位）→ 云影目标，受光顶（98 百分位）→ 云顶目标（调色后的屏幕码）。
未知数：日色 = 黑体色温 K × 增益（Unity 的 E 叠在里面）、天光 RGB、地光 = 该幕 Trilight 地色 × 增益。
同一组的所有卡用同一组颜色（光是一致的，不逐卡调）。结果写 Textures/cards_v2.json 的 colours.<组>。
用法：python card_solve.py dawn | dusk"""
import os
import sys
import json
import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lb_common as C  # noqa: E402
import cardshade as CS  # noqa: E402

WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')
TARGETS = {
    # shadow: bible; top: dawn = palette 06 'cloud tops peach'; dusk = 设计值 (between the slot amber and the rose band)
    'dawn': dict(set='dawn', grade='S6', shadow='#8593AA', top='#F6DCC4', ground='#8FA0BE', rel=70.0, K0=3000, Kmin=2400, Kmax=3600),
    'dusk': dict(set='duskU', grade='S8', shadow='#363D59', top='#F0A878', ground='#4C5577', rel=70.0, K0=2400, Kmin=2000, Kmax=3000),
}


def sun_rgb(K, gain):
    k = C.LD.kelvin_lin(K)
    return gain * k / (k @ C.LUMA)            # luminance = gain


def selections(K, S, a):
    neutral = K[..., 1] + S[..., 0] + S[..., 1]
    body = a > 0.97
    lb = neutral[body]
    lo, hi = np.percentile(lb, [10, 30])
    sh = body & (neutral >= lo) & (neutral <= hi)
    lit = K[..., 1]
    tp = body & (lit >= np.percentile(lit[body], 98))
    return sh, tp


def colours_from_x(x, T):
    return dict(sun=sun_rgb(x[1], x[0]), sky=np.array(x[2:5]), gnd=C.hex_lin(T['ground']) * x[5])


def measure(K, S, a, rel, cols, grade, sel):
    c, _ = CS.shade(K, S, a, rel, cols['sun'], cols['sky'], cols['gnd'])
    sh, tp = sel
    m = np.stack([np.median(c[sh], 0), np.median(c[tp], 0)])
    return C.grade(m[None], grade, bloom=False)[0]


def solve(which, card='Cumulus'):
    T = TARGETS[which]
    K, S, a = CS.load_card(os.path.join(WORK, f'CloudV2_{card}_{T["set"]}_ch.npz'))
    sel = selections(K, S, a)
    tsh, ttp = C.hex_rgb(T['shadow']) * 255, C.hex_rgb(T['top']) * 255
    h_t = C.hue_chroma(tsh)[1]

    def f(x):
        if x[0] <= 0 or not T['Kmin'] <= x[1] <= T['Kmax'] or (np.asarray(x[2:]) < 0).any():
            return 1e9
        cs = measure(K, S, a, T['rel'], colours_from_x(x, T), T['grade'], sel)
        h, c = C.hue_chroma(cs[0])[1:]
        dh = ((h - h_t + 180) % 360) - 180
        return float(((cs[0] - tsh) ** 2).sum() + 0.5 * ((cs[1] - ttp) ** 2).sum() + 2 * dh ** 2 * min(c / 10, 1))
    best = None
    for x0 in ([3.0, T['K0'], 0.4, 0.5, 0.8, 0.5], [5.0, T['K0'] + 600, 0.3, 0.4, 0.7, 0.3], [2.0, T['K0'] - 300, 0.5, 0.6, 0.9, 0.8]):
        r = minimize(f, x0, method='Nelder-Mead', options=dict(xatol=1e-4, fatol=1e-3, maxiter=4000))
        if best is None or r.fun < best.fun:
            best = r
    x = best.x
    cols = colours_from_x(x, T)
    res = dict(set=T['set'], grade=T['grade'], solved_on=f'CloudV2_{card}_{T["set"]} at rel {T["rel"]}',
               sun_K=round(float(x[1])), sun_luminance=round(float(x[0]), 4),
               SunColor=[round(float(v), 5) for v in cols['sun']],
               SkyUpColor=[round(float(v), 5) for v in cols['sky']],
               GroundColor=[round(float(v), 5) for v in cols['gnd']],
               targets=dict(shadow=T['shadow'], top=T['top']))
    for rel in (15.0, 45.0, 70.0, 110.0, 150.0, 170.0):
        cs = measure(K, S, a, rel, cols, T['grade'], sel)
        res[f'rel{int(rel)}'] = dict(shadow=C.to_hex(cs[0]), top=C.to_hex(cs[1]),
                                     shadow_hC=[round(float(v), 1) for v in C.hue_chroma(cs[0])[1:]])
    return res


def index_cards(J):
    """cards_v2.json 'cards': one entry per rendered card (from Textures/<card>.json, written by make_clouds_v2.finish)."""
    import glob
    J['format'] = ('v2 channel cards: _K RGBA = sun 15/80/150 deg right of the view (white light, Unity E 1) + coverage, '
                   '_S RG = uniform white upper / lower dome; stored sRGB(value / kscale or sscale). Colours per group '
                   'in colours.<group> (linear; SunColor includes E). Shader Lanbai/CloudCard, numpy port Source/cardshade.py.')
    cards = {}
    for f in sorted(glob.glob(os.path.join(HERE, '..', 'Textures', 'Cloud*V2_*.json'))):
        c = json.load(open(f))
        cards[c['name']] = {k: c[k] for k in ('set', 'shape', 'size', 'cloud_base_v', 'opaque_bbox_uv', 'kscale', 'sscale',
                                              'key_angles', 'sun_el', 'pitch', 'clipped_K', 'clipped_S') if k in c}
    J['cards'] = cards


if __name__ == '__main__':
    out = os.path.join(HERE, '..', 'Textures', 'cards_v2.json')
    J = json.load(open(out)) if os.path.exists(out) else {}
    if sys.argv[1:] == ['--index']:
        index_cards(J)
        json.dump(J, open(out, 'w'), indent=1, ensure_ascii=False)
        sys.exit(0)
    index_cards(J)
    for w in sys.argv[1:] or ['dawn']:
        r = solve(w)
        J.setdefault('colours', {})[w] = r
        print(json.dumps(r, ensure_ascii=False, indent=1))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(J, open(out, 'w'), indent=1, ensure_ascii=False)
