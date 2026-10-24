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
# review r1 R4: the lower-dome light is capped at 1.2 x the act's Trilight ground colour (the solve had pushed it to 3.07 x,
# lighting the flat bases from below as a pale blue line)
# front-lit base term: TRIED in the act 6 window with weight 30 -> base #C5B4B0 (C* 6.7) but the tops fell to #E9DAD1
# (sun 3111 K, the palette's peach #F6DCC4 lost). Under front light the base is SUNLIT, not a shadow (bible 1.3 rule 2
# is about shadows), so the palette wins: weight 0 (README_CloudsV2 §7, Act06 README §6).
BASE_W = 0.0
TARGETS = {
    # shadow: bible; top: dawn = palette 06 'cloud tops peach'; dusk = 设计值 (between the slot amber and the rose band)
    'dawn': dict(set='dawn', grade='S6', shadow='#8593AA', top='#F6DCC4', ground='#8FA0BE', rel=70.0, K0=3000, Kmin=2400, Kmax=3600, gnd_max=1.2),
    'dusk': dict(set='duskU', grade='S8', shadow='#363D59', top='#F0A878', ground='#4C5577', rel=70.0, K0=2400, Kmin=2000, Kmax=3000, gnd_max=1.2),
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


def base_mask(a):
    """the flat base: opaque pixels in the lowest 6 % of the card's opaque rows"""
    rows = np.nonzero((a > 0.5).mean(1) > 0.02)[0]
    lo = rows[-1] - max(int(0.06 * (rows[-1] - rows[0])), 2)
    m = np.zeros_like(a, bool)
    m[lo:rows[-1] + 1] = True
    return m & (a > 0.9)


def measure_base(K, S, a, rel, cols, grade, base):
    c, _ = CS.shade(K[base][None], S[base][None], a[base][None], rel, cols['sun'], cols['sky'], cols['gnd'])
    return C.grade(np.median(c[0], 0)[None, None], grade, bloom=False)[0, 0]


def colours_from_x(x, T):
    return dict(sun=sun_rgb(x[1], x[0]), sky=np.array(x[2:5]), gnd=C.hex_lin(T['ground']) * x[5])


def measure(K, S, a, rel, cols, grade, sel):
    sh, tp = sel                                     # shade only the selected pixels (same maths as cardshade.shade)
    m = []
    for msk in (sh, tp):
        c, _ = CS.shade(K[msk][None], S[msk][None], a[msk][None], rel, cols['sun'], cols['sky'], cols['gnd'])
        m.append(np.median(c[0], 0))
    m = np.stack(m)
    return C.grade(m[None], grade, bloom=False)[0]


def solve(which, card='Cumulus'):
    T = TARGETS[which]
    K, S, a = CS.load_card(os.path.join(WORK, f'CloudV2_{card}_{T["set"]}_ch.npz'))
    sel = selections(K, S, a)
    base = base_mask(a)
    tsh, ttp = C.hex_rgb(T['shadow']) * 255, C.hex_rgb(T['top']) * 255
    h_t = C.hue_chroma(tsh)[1]

    def f(x):
        if x[0] <= 0 or not T['Kmin'] <= x[1] <= T['Kmax'] or (np.asarray(x[2:]) < 0).any() or x[5] > T['gnd_max']:
            return 1e9
        cs = measure(K, S, a, T['rel'], colours_from_x(x, T), T['grade'], sel)
        h, c = C.hue_chroma(cs[0])[1:]
        dh = ((h - h_t + 180) % 360) - 180
        # review r1 R5: the BACKLIT shadow (rel 15) must stay blue too: penalise h beyond 280 (toward lilac)
        hb, cb = C.hue_chroma(measure(K, S, a, 15.0, colours_from_x(x, T), T['grade'], sel)[0])[1:]
        pb = max(0.0, (((hb - h_t + 180) % 360) - 180) - 8.0) * min(cb / 8, 1)
        # (act 6 window, review r2 leftover) the FRONT-lit flat base (rel 150) must not go pink-brown: chroma of warm
        # base pixels above 6 is penalised (bible 1.3 rule 2: no warm in the shadowed underside)
        cbase = measure_base(K, S, a, 150.0, colours_from_x(x, T), T['grade'], base)
        hz, cz = C.hue_chroma(cbase)[1:]
        pz = max(0.0, cz - 6.0) * (1.0 if (hz < 120 or hz > 340) else 0.0)
        return float(((cs[0] - tsh) ** 2).sum() + 0.5 * ((cs[1] - ttp) ** 2).sum() + 2 * dh ** 2 * min(c / 10, 1)
                     + 20 * pb ** 2 + BASE_W * pz ** 2)
    best = None
    for x0 in ([3.0, T['K0'], 1.0, 1.1, 1.6, 1.0], [5.0, T['K0'] + 600, 1.2, 1.3, 1.8, 0.6], [2.0, T['K0'] - 300, 0.8, 0.9, 1.3, 1.15]):
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
    bz = measure_base(K, S, a, 150.0, cols, T['grade'], base_mask(a))
    res['base_front_lit'] = dict(hex=C.to_hex(bz), hC=[round(float(v), 1) for v in C.hue_chroma(bz)[1:]])
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
        from PIL import Image
        al = np.asarray(Image.open(f[:-5] + '_K.png'))[..., 3].astype(np.float64) / 255.0
        hh, ww = al.shape
        ys, xs = np.nonzero(al > 1.5 / 255)
        mg = 2                                              # texel margin (bilinear / mip footprint)
        c['bbox_uv'] = [round(max(xs.min() - mg, 0) / ww, 4), round(max(1 - (ys.max() + 1 + mg) / hh, 0), 4),
                        round(min((xs.max() + 1 + mg) / ww, 1), 4), round(min(1 - (ys.min() - mg) / hh, 1), 4)]
        c['coverage_of_quad'] = round(float(al.mean()), 3)
        cards[c['name']] = {k: c[k] for k in ('set', 'shape', 'size', 'cloud_base_v', 'opaque_bbox_uv', 'kscale', 'sscale',
                                              'key_angles', 'sun_el', 'pitch', 'clipped_K', 'clipped_S', 'bbox_uv', 'coverage_of_quad') if k in c}
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
