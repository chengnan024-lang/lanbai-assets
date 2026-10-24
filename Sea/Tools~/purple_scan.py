# -*- coding: utf-8 -*-
"""Purple-guard ceiling (final review #7, D-17): bake + prove.

Rule proved here (Art/总导演裁决.md D-17 + D-21): after LanbaiPurpleGuard, under the grade(s) each sea material lives
in (Grading's PPv2 engine model, no bloom), NO colour displays with CIELab h_ab in [290, 330], C* > 8 and L* > 40.
  D-21 (revised, main 4dacb19): the bible's own palette always passes (mid sky #808AB2 h 284.3, cabin #828BAA, zenith
  #3D4A80 h 289.2, #2E3C66 h 286.3 all sit under 290); the deep indigo L* <= 40 passes; the mid-tone lilac is stopped.

How: for every OKLab hue (0.5 deg) and lightness L (0.0125, 0..3 = linear 0..27) and for each grade separately, the
largest SATURATION s = C/L that never displays violet (first violet s along the ray, minus one 0.002 step), the scan
using a slightly stricter test (h_ab 289.7..330.5, C* > 7.0, L* > 39: margin for bloom and 8-bit rounding) so thin violet islands between scan points are covered.
Some rays leave the violet band again at higher saturation (under S8 the DESATURATED versions of the bible's mid sky
#808AB2 read lilac, the colour itself does not), so each texel stores the band: lo = largest safe s below it, hi = top of it.
A ray can even hold TWO violet bands with a safe gap between them (#808AB2 under S8: s 0.04-0.065 and 0.17-, the colour
itself at 0.12), so each texel stores both: band 1 = (lo1, hi1], band 2 = (lo2, hi2] (runs beyond the second merged in).
Baked into Sea/Textures/Sea_PurpleCeiling.png (360 x 484 RGBA8, linear): R = S6, G = S7a + the 7a cross-fade, B = S7b, A = S8; four quarters of
121 rows: lo1, hi1, lo2, hi2 (lo = footprint MIN rounded down, hi = footprint MAX rounded up; bands that touch merge);
value / 255 * 0.8 = s. Texel (i, j) is hue i + 0.5 deg, L 0.025 j; POINT sampled (no blending between texels, so two
bands never mix into a false gap), each texel answering for its own +-0.5 texel (+ one fine step).
A material picks its grades with _PurpleGuard (x on, plus _PurpleMask = which channels; the minimum of the picked ones):
  act 6  (M_06_Sea)                           R         S6
  act 7a (M_07a_SeaSurface)                   G + B     S7a, and S7b because 7a cross-fades S7a -> S7b (474.36..558.86)
  7c     (M_07c_SeaMirror)                    B         S7b
  act 8  (M_08_*)                             A         S8   (the grade cuts S7b -> S8 at the exit 922.36, under the bus)
  act 11 (M_11_SeaHanging)                    R         S11 (= S2), from its own texture Sea_PurpleCeiling_S11.png
The shader scales a colour inside band 1 down to s = lo1, inside band 2 down to s = lo2 (hue and L kept); the rest is untouched.
Proof (written to Sea/Docs~/purple_scan.json): per material, (1) 2 000 000 random in-gamut HDR colours, (2) a dense grid
OFFSET half a step from the scan grid (0.5 deg x 0.0125 L x 0.002 s, hues where any ceiling binds), through a numpy copy of
the exact shader path (bilinear on the 8-bit texture) and the material's grades -> violet count must be 0;
(3) the bible's blues through their own material -> how far the guard moves them (dE76 on screen).
Run: ~/bpy/bin/python Sea/Tools~/purple_scan.py   (~15 min on 4 cores)"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import grade as G  # noqa: E402
import sea_numpy as S  # noqa: E402

CHANNELS = ('S6', 'S7a~', 'S7b', 'S8', 'S11')     # the first four -> Sea_PurpleCeiling.png RGBA, S11 -> Sea_PurpleCeiling_S11.png
# 'S7a~' = S7a AND the whole 7a cross-fade S7a -> S7b (F3e -> F5, PPv2 volume blending, weights 0.05 .. 0.95): the two ends
# alone leave up to 0.27 % violet in the middle (Sea/Docs~/purple_transition.json, first run)
BLEND_W = [round(w, 2) for w in np.arange(0.05, 0.96, 0.05)]
H_LO, H_HI, CSTAR, LSTAR = 290.0, 330.0, 8.0, 40.0   # the rule (verification), D-21 revised (main 4dacb19)
SCAN_LO, SCAN_HI, SCAN_C, SCAN_L = 289.7, 330.5, 7.0, 39.0   # the bake is stricter (margin for thin violet islands between scan points)
W, H = 360, 121
L_STEP, H_STEP = 0.025, 1.0
S_MAX = 0.8
FH, FL, FS = 0.5, 0.0125, 0.002
S_STEPS = np.arange(0.0, S_MAX + 1e-9, FS)
MATERIALS = {  # name: (channel mask, grades proved)
    'M_06_Sea': ((1, 0, 0, 0), ('S6',)),
    'M_07a_SeaSurface': ((0, 1, 1, 0), ('S7a', 'S7a+S7b=0.25', 'S7a+S7b=0.50', 'S7a+S7b=0.75', 'S7b')),
    'M_07c_SeaMirror': ((0, 0, 1, 0), ('S7b',)),
    'M_08_SeaCeiling*': ((0, 0, 0, 1), ('S8',)),
    'M_11_SeaHanging': ((1, 0, 0, 0), ('S11',)),     # with Sea_PurpleCeiling_S11.png (R = S11)
}
TEXTURE_OF = {'M_11_SeaHanging': 'S11'}
_P = {}


def params(sid):
    if sid not in _P:
        if sid.startswith('S7a+S7b='):
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'Engineering', 'render_harness'))
            from lbh import grade as LG
            st = LG.blend({'S7a': 1.0, 'S7b': float(sid.split('=')[1])})
            st['colorFilter'] = G.GE['common']['colorFilter']; st['hueShift'] = G.GE['common']['hueShift']
            _P[sid] = st
        else:
            _P[sid] = G.engine_params(sid)
    return _P[sid]


def violet(lin, sid, lo=H_LO, hi=H_HI, cs=CSTAR, ls=LSTAR):
    if sid == 'S7a~':
        v = violet(lin, 'S7a', lo, hi, cs, ls)
        for w in BLEND_W:
            v |= violet(lin, 'S7a+S7b=%.2f' % w, lo, hi, cs, ls)
        return v
    codes = G.E.codes_direct(np.maximum(lin, 0.0), params(sid))
    L, a, b = G.lab(np.clip(codes, 0, 255))
    h = (np.degrees(np.arctan2(b, a)) + 360) % 360
    return (h >= lo) & (h <= hi) & (np.hypot(a, b) > cs) & (L > ls)


def oklab_raw_to_lin(o):
    M1 = np.array([[1.0, 0.3963377774, 0.2158037573], [1.0, -0.1055613458, -0.0638541728], [1.0, -0.0894841775, -1.2914855480]])
    M2 = np.array([[4.0767416621, -3.3077115913, 0.2309699292], [-1.2684380046, 2.6097574011, -0.3413193965], [-0.0041960863, -0.7034186147, 1.7076147010]])
    return (o @ M1.T) ** 3 @ M2.T


def lsh(L, s, h):
    r = np.radians(h)
    return np.stack([L, s * L * np.cos(r), s * L * np.sin(r)], -1)


FINE_L = np.maximum(np.arange(0.0, 3.0 + 1e-9, FL), 0.004)


def runs(bad_row):
    """violet runs along one saturation ray -> (lo1, hi1, lo2, hi2) in step indices (None = absent)"""
    idx = np.where(bad_row)[0]
    if len(idx) == 0:
        return None
    breaks = np.where(np.diff(idx) > 1)[0]
    r1_end = idx[breaks[0]] if len(breaks) else idx[-1]
    if len(breaks) == 0:
        return idx[0], r1_end, None, None
    return idx[0], r1_end, idx[breaks[0] + 1], idx[-1]           # runs 2.. merged into one (conservative)


def scan_hue(h):
    """per grade and fine L at hue h: the violet samples along the saturation ray (bool [nL, grades, nS])"""
    LL, SS = np.meshgrid(FINE_L, S_STEPS, indexing='ij')
    lin = S.oklab_to_lin(lsh(LL.ravel(), SS.ravel(), np.full(LL.size, h)))
    return np.stack([violet(lin, sid, SCAN_LO, SCAN_HI, SCAN_C, SCAN_L).reshape(LL.shape) for sid in CHANNELS], 1)


def bands_of(union):
    """violet samples of one texel (the UNION over its footprint) -> s of (lo1, hi1, lo2, hi2), one step of margin each
    side; runs beyond the second merge into it; no violet = (S_MAX, 0, S_MAX, 0)"""
    n = len(S_STEPS)
    r = runs(union)
    if r is None:
        return S_MAX, 0.0, S_MAX, 0.0
    f1, e1, f2, e2 = r
    lo1 = S_STEPS[max(f1 - 2, 0)] if f1 > 1 else 0.0
    hi1 = S_STEPS[min(e1 + 1, n - 1)]
    if f2 is None:
        return lo1, hi1, S_MAX, 0.0
    lo2 = S_STEPS[max(f2 - 2, 0)]
    hi2 = S_STEPS[min(e2 + 1, n - 1)]
    if lo2 <= hi1:
        return lo1, hi2, S_MAX, 0.0
    return lo1, hi1, lo2, hi2


def bake(bad):
    """bad [nH_fine, nL_fine, grades, nS] -> texture [4H, W, grades] uint8, quarters lo1, hi1, lo2, hi2. Each texel takes the
    UNION of the violet samples over its own +-0.5 texel (+ one fine step) -- exact for point sampling -- and stores its
    first two violet runs (lo rounded down, hi rounded up; a gap under one code merges the bands)."""
    nh = bad.shape[0]
    G_ = bad.shape[2]
    q = np.zeros((4, H, W, G_))
    fh = np.arange(nh) * FH
    for i in range(W):
        hc = i + 0.5
        d = (fh - hc + 180) % 360 - 180
        hm = np.abs(d) <= 0.5 * H_STEP + FH + 1e-9
        sub = bad[hm].any(0)                              # [nL, grades, nS]
        for j in range(H):
            Lc = j * L_STEP
            lm = (FINE_L >= Lc - 0.5 * L_STEP - FL - 1e-9) & (FINE_L <= Lc + 0.5 * L_STEP + FL + 1e-9)
            un = sub[lm].any(0)                           # [grades, nS]
            for g in range(G_):
                q[:, j, i, g] = bands_of(un[g])
    lo1, hi1, lo2, hi2 = (np.floor(q[0] / S_MAX * 255), np.ceil(q[1] / S_MAX * 255), np.floor(q[2] / S_MAX * 255), np.ceil(q[3] / S_MAX * 255))
    merge = (lo2 <= hi1 + 1) & (hi2 > 0)
    hi1 = np.where(merge, np.maximum(hi1, hi2), hi1)
    lo2 = np.where(merge, 255, lo2); hi2 = np.where(merge, 0, hi2)
    return np.concatenate([lo1, hi1, lo2, hi2], 0).astype(np.uint8)


def bilinear(t, L, h, half):
    """GPU POINT sampling of one quarter (the importer sets Point): texel i = floor(hue), row = round(L / 0.025) clamped"""
    i = np.floor(h / H_STEP).astype(int) % W
    j = np.clip(np.floor(L / L_STEP + 0.5).astype(int), 0, H - 1) + half * H
    return t[j, i]


def bands(tex8, L, h, mask):
    """what the shader does: per quarter bilinear; lo = min of the picked grades, hi = max"""
    t = tex8.astype(np.float64) / 255.0 * S_MAX
    m = np.array(mask, bool)
    lo1 = np.where(m[None, :], bilinear(t, L, h, 0), np.inf).min(-1)
    hi1 = np.where(m[None, :], bilinear(t, L, h, 1), -np.inf).max(-1)
    lo2 = np.where(m[None, :], bilinear(t, L, h, 2), np.inf).min(-1)
    hi2 = np.where(m[None, :], bilinear(t, L, h, 3), -np.inf).max(-1)
    return lo1, hi1, lo2, hi2


def guard(lin, tex8, mask):
    """numpy copy of LanbaiPurpleGuard: a colour inside band 1 goes down to s = lo1, inside band 2 down to s = lo2 (the top
    of the safe gap); a band reaching the top of the table (hi >= 0.8) is open-ended; hue and L kept, the rest untouched"""
    o = S.lin_to_oklab(lin)
    L = np.maximum(o[..., 0], 0.0)
    C = np.hypot(o[..., 1], o[..., 2])
    h = (np.degrees(np.arctan2(o[..., 2], o[..., 1])) + 360) % 360
    lo1, hi1, lo2, hi2 = bands(tex8, L, h, mask)
    s = C / np.maximum(L, 1e-6)
    top = S_MAX - 1e-3
    in1 = (s > lo1) & ((s <= hi1 + 1e-4) | (hi1 >= top))
    in2 = (s > lo2) & ((s <= hi2 + 1e-4) | (hi2 >= top))
    tgt = np.where(in1, lo1, np.where(in2, lo2, s))
    k = np.where((L > 1e-5) & (tgt < s), tgt / np.maximum(s, 1e-9), 1.0)
    o2 = o.copy(); o2[..., 1:] *= k[..., None]
    return S.oklab_to_lin(o2)


TEX = None


def _init(tex8):
    global TEX
    TEX = tex8


def verify_hue(args):
    h, mask, grades, which = args
    LL, SS = np.meshgrid(np.arange(FL / 2, 3.0, FL), np.arange(FS / 2, S_MAX, FS), indexing='ij')
    lin = oklab_raw_to_lin(lsh(LL.ravel(), SS.ravel(), np.full(LL.size, h)))
    ok = (lin >= 0).all(-1)
    g = guard(lin[ok], TEX[which], mask)
    return int(ok.sum()), {sid: int(violet(g, sid).sum()) for sid in grades}


def verify(texs, pool):
    global TEX
    rng = np.random.default_rng(7)
    res = {}
    for name, (mask, grades) in MATERIALS.items():
        tex8 = texs[TEXTURE_OF.get(name, 'main')]
        binding = [h for h in np.arange(FH / 2, 360, FH) if min(bands(tex8, np.array([L]), np.array([h]), mask)[0][0] for L in (0.2, 0.5, 0.9)) < S_MAX - 0.01]
        n_tot, left = 0, {s: 0 for s in grades}
        for _ in range(5):
            N = 400000
            o = lsh(rng.uniform(0.01, 3.2, N), rng.uniform(0, S_MAX, N), rng.uniform(0, 360, N))
            lin = oklab_raw_to_lin(o)
            ok = (lin >= 0).all(-1)
            g = guard(lin[ok], tex8, mask)
            n_tot += int(ok.sum())
            for sid in grades:
                left[sid] += int(violet(g, sid).sum())
        out = pool.map(verify_hue, [(h, mask, grades, TEXTURE_OF.get(name, 'main')) for h in binding])
        n2 = sum(o_[0] for o_ in out)
        left2 = {sid: sum(o_[1][sid] for o_ in out) for sid in grades}
        res[name] = dict(channels=''.join('RGBA'[i] for i in range(4) if mask[i]), grades=grades,
                         random_2M=dict(in_gamut=n_tot, violet_left=left),
                         offset_grid=dict(in_gamut=n2, hues=len(binding), violet_left=left2))
        print(name, res[name], flush=True)
    return res


BIBLE = [  # (name, hex, material, grade, 'screen' = display target reverse-solved | 'fill' = the linear value itself)
    ('6 dawn zenith fill', '#5B7ED7', 'M_06_Sea', 'S6', 'fill'), ('6 far sea fill', '#304F7A', 'M_06_Sea', 'S6', 'fill'),
    ('7a dark mirror', '#11395E', 'M_07a_SeaSurface', 'S7a', 'screen'), ('7a TIR fill', '#294B72', 'M_07a_SeaSurface', 'S7a', 'fill'),
    ('7a fog fill', '#77A0D2', 'M_07a_SeaSurface', 'S7a', 'fill'), ('7a window core', '#E6F3F8', 'M_07a_SeaSurface', 'S7a', 'screen'),
    ('7c window indigo', '#2E3C66', 'M_07c_SeaMirror', 'S7b', 'screen'), ('7c fog', '#2E2228', 'M_07c_SeaMirror', 'S7b', 'screen'),
    ('8 zenith', '#3D4A80', 'M_08_SeaCeiling*', 'S8', 'screen'), ('8 other-sky nadir', '#2E3C66', 'M_08_SeaCeiling*', 'S8', 'screen'),
    ('8 mid sky', '#808AB2', 'M_08_SeaCeiling*', 'S8', 'screen'), ('8 cabin', '#828BAA', 'M_08_SeaCeiling*', 'S8', 'screen'),
    ('8 ceiling water', '#10263F', 'M_08_SeaCeiling*', 'S8', 'screen'), ('8 ceiling water fill', '#1C304B', 'M_08_SeaCeiling*', 'S8', 'fill'),
    ('11 water', '#0F283C', 'M_11_SeaHanging', 'S11', 'fill'),
]


def bible_check(texs):
    res = {}
    for name, hx, mat, sid, kind in BIBLE:
        lin = G.fill_for(hx, sid) if kind == 'screen' else G.srgb_to_lin(G.hex_codes(hx) / 255.0)
        lin = np.asarray(lin, np.float64)[None, :]
        g = guard(lin, texs[TEXTURE_OF.get(mat, 'main')], MATERIALS[mat][0])
        a = np.clip(G.E.codes_direct(lin, params(sid)), 0, 255)
        b = np.clip(G.E.codes_direct(g, params(sid)), 0, 255)
        La, aa, ba = G.lab(a); Lb, ab, bb = G.lab(b)
        dE = float(np.sqrt((La - Lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2)[0])
        res[name] = dict(hex=hx, material=mat, grade=sid, kind=kind, screen_h_ab=round(float((np.degrees(np.arctan2(ba, aa)) % 360)[0]), 1),
                         screen_C=round(float(np.hypot(aa, ba)[0]), 1), dE_by_guard=round(dE, 2))
    return res


def main():
    hues = np.arange(0, 360, FH)
    with Pool(4) as p:
        cap = np.stack(p.map(scan_hue, hues))             # [720, nL, grades, nS] violet samples
    tex = bake(cap)                                       # [4H, W, 5]
    texs = dict(main=tex[..., :4], S11=np.repeat(tex[..., 4:5], 4, -1))
    from PIL import Image
    Image.fromarray(np.flipud(texs['main']), 'RGBA').save(os.path.join(KIT, 'Textures', 'Sea_PurpleCeiling.png'))   # v = 0 (L = 0) at the bottom
    Image.fromarray(np.flipud(texs['S11']), 'RGBA').save(os.path.join(KIT, 'Textures', 'Sea_PurpleCeiling_S11.png'))
    with Pool(4, initializer=_init, initargs=(texs,)) as p:
        ver = verify(texs, p)
    bib = bible_check(texs)
    out = dict(rule='after the guard, no colour displays h_ab %g..%g with C* > %g and L* > %g, under the grade(s) of its material (D-17 + D-21)' % (H_LO, H_HI, CSTAR, LSTAR),
               d21='the deep bible indigo (L* <= 40: #3D4A80, #2E3C66) passes; the mid-tone lilac is stopped -- the same rule as the Sky',
               scan_margin='baked against h_ab %g..%g, C* > %g, L* > %g (stricter than the rule)' % (SCAN_LO, SCAN_HI, SCAN_C, SCAN_L),
               texture='Sea/Textures/Sea_PurpleCeiling.png %dx%d RGBA8 linear (R S6, G S7a, B S7b, A S8; Sea_PurpleCeiling_S11.png: all = S11): '
                       'value/255*%g = OKLab C/L; quarters of %d rows: lo1, hi1, lo2, hi2; u = hue/360 (repeat), v = (clamp(L/%g, 0, %d) + 0.5 + q*%d) / %d' % (W, 4 * H, S_MAX, H, L_STEP, H - 1, H, 4 * H),
               materials={k: dict(channels=''.join('RGBA'[i] for i in range(4) if v[0][i]), grades=v[1]) for k, v in MATERIALS.items()},
               verification=ver, bible_colours=bib)
    json.dump(out, open(os.path.join(KIT, 'Docs~', 'purple_scan.json'), 'w'), indent=1, ensure_ascii=False)
    for k, v in bib.items():
        print(k, v)


if __name__ == '__main__':
    main()
