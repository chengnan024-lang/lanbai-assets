# -*- coding: utf-8 -*-
"""Purple-guard ceiling (final review #7, D-17): bake + prove.

Rule proved here: after LanbaiPurpleGuard, under the grade(s) each sea material lives in (Grading's PPv2 engine model,
no bloom), NO colour displays with CIELab h_ab in [290, 330] and C* > 8.
  The review asked for 285..330. 285..290 is where the bible's own dusk sky lives: S8 zenith #3D4A80 displays h_ab 289.2
  C* 34, other-sky nadir / 7c window indigo #2E3C66 286.3 C* 28 (ART_BIBLE M5 put them there on purpose). Guarding
  from 285 would grey the bible's sky in the sea mirror, which the same item forbids ("护栏只管紫，不碰圣经指定的蓝").
  290 is the bible's own §1.3.4 violet edge. Everything 290..330 is held to C* <= 8 (D-17's number, stricter than §1.3.4's 15).

How: for every OKLab hue (0.5 deg) and lightness L (0.0125, 0..3 = linear 0..27) and for each grade separately, the
largest SATURATION s = C/L that never displays violet (first violet s along the ray, minus one 0.002 step), the scan
using a slightly stricter test (h_ab 289.7..330.5, C* > 7.0: margin for bloom and 8-bit rounding) so thin violet islands between scan points are covered.
Baked into Sea/Textures/Sea_PurpleCeiling.png (360 x 121 RGBA8, linear): R = S6, G = S7a, B = S7b, A = S8;
value / 255 * 0.8 = max s. Texel (i, j) is hue i + 0.5 deg, L 0.025 j; each texel holds the MINIMUM of the fine scan over
its whole bilinear footprint (+-1 texel), rounded DOWN, so the GPU's bilinear lookup is never above the true ceiling.
A material picks its grades with _PurpleGuard (x on, plus _PurpleMask = which channels; the minimum of the picked ones):
  act 6  (M_06_Sea)                           R         S6
  act 7a (M_07a_SeaSurface)                   G + B     S7a, and S7b because 7a cross-fades S7a -> S7b (474.36..558.86)
  7c     (M_07c_SeaMirror)                    B         S7b
  act 8  (M_08_*)                             A         S8   (the grade cuts S7b -> S8 at the exit 922.36, under the bus)
  act 11 (M_11_SeaHanging)                    R         S11 (= S2), from its own texture Sea_PurpleCeiling_S11.png
The shader scales OKLab chroma down to s_max * L (hue and L kept): a colour under its ceiling is returned untouched.
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

CHANNELS = ('S6', 'S7a', 'S7b', 'S8', 'S11')      # the first four -> Sea_PurpleCeiling.png RGBA, S11 -> Sea_PurpleCeiling_S11.png
H_LO, H_HI, CSTAR = 290.0, 330.0, 8.0               # the rule (verification)
SCAN_LO, SCAN_HI, SCAN_C = 289.7, 330.5, 7.0        # the bake is stricter (margin for thin violet islands between scan points)
W, H = 360, 121
L_STEP, H_STEP = 0.025, 1.0
S_MAX = 0.8
FH, FL, FS = 0.5, 0.0125, 0.002
S_STEPS = np.arange(0.0, S_MAX + 1e-9, FS)
MATERIALS = {  # name: (channel mask, grades proved)
    'M_06_Sea': ((1, 0, 0, 0), ('S6',)),
    'M_07a_SeaSurface': ((0, 1, 1, 0), ('S7a', 'S7b')),
    'M_07c_SeaMirror': ((0, 0, 1, 0), ('S7b',)),
    'M_08_SeaCeiling*': ((0, 0, 0, 1), ('S8',)),
    'M_11_SeaHanging': ((1, 0, 0, 0), ('S11',)),     # with Sea_PurpleCeiling_S11.png (R = S11)
}
TEXTURE_OF = {'M_11_SeaHanging': 'S11'}
_P = {}


def params(sid):
    if sid not in _P:
        _P[sid] = G.engine_params(sid)
    return _P[sid]


def violet(lin, sid, lo=H_LO, hi=H_HI, cs=CSTAR):
    codes = G.E.codes_direct(np.maximum(lin, 0.0), params(sid))
    L, a, b = G.lab(np.clip(codes, 0, 255))
    h = (np.degrees(np.arctan2(b, a)) + 360) % 360
    return (h >= lo) & (h <= hi) & (np.hypot(a, b) > cs)


def oklab_raw_to_lin(o):
    M1 = np.array([[1.0, 0.3963377774, 0.2158037573], [1.0, -0.1055613458, -0.0638541728], [1.0, -0.0894841775, -1.2914855480]])
    M2 = np.array([[4.0767416621, -3.3077115913, 0.2309699292], [-1.2684380046, 2.6097574011, -0.3413193965], [-0.0041960863, -0.7034186147, 1.7076147010]])
    return (o @ M1.T) ** 3 @ M2.T


def lsh(L, s, h):
    r = np.radians(h)
    return np.stack([L, s * L * np.cos(r), s * L * np.sin(r)], -1)


FINE_L = np.maximum(np.arange(0.0, 3.0 + 1e-9, FL), 0.004)


def scan_hue(h):
    """per grade: max safe s for every fine L at hue h"""
    LL, SS = np.meshgrid(FINE_L, S_STEPS, indexing='ij')
    lin = S.oklab_to_lin(lsh(LL.ravel(), SS.ravel(), np.full(LL.size, h)))
    caps = []
    for sid in CHANNELS:
        bad = violet(lin, sid, SCAN_LO, SCAN_HI, SCAN_C).reshape(LL.shape)
        first = np.where(bad.any(-1), np.argmax(bad, -1), len(S_STEPS))
        c = S_STEPS[np.maximum(first - 2, 0)]            # one extra step of margin
        c[first <= 1] = 0.0
        caps.append(c)
    return np.stack(caps, -1)                             # [nL, 4]


def bake(cap):
    """cap [nH_fine, nL_fine, 4] -> texture [H, W, 4] uint8"""
    nh = cap.shape[0]
    tex = np.zeros((H, W, cap.shape[-1]))
    fh = np.arange(nh) * FH
    for i in range(W):
        hc = i + 0.5
        d = (fh - hc + 180) % 360 - 180
        hm = np.abs(d) <= H_STEP + 1e-9
        sub = cap[hm].min(0)                              # [nL, 4]
        for j in range(H):
            Lc = j * L_STEP
            lm = (FINE_L >= Lc - L_STEP - 1e-9) & (FINE_L <= Lc + L_STEP + 1e-9)
            tex[j, i] = sub[lm].min(0)
    return np.floor(tex / S_MAX * 255.0).astype(np.uint8)


def sample(tex8, L, h, mask):
    """GPU bilinear: U wraps (hue), V clamps (L); texel i centre u = (i + 0.5) / W"""
    t = tex8.astype(np.float64) / 255.0 * S_MAX
    m = np.array(mask, bool)
    t = np.where(m[None, None, :], t, np.inf).min(-1)
    u = h / H_STEP - 0.5
    v = np.clip(L / L_STEP, 0, H - 1)
    i0 = np.floor(u).astype(int); fu = u - i0
    j0 = np.clip(np.floor(v).astype(int), 0, H - 2); fv = v - j0
    i0 %= W; i1 = (i0 + 1) % W
    a = t[j0, i0] * (1 - fu) + t[j0, i1] * fu
    b = t[j0 + 1, i0] * (1 - fu) + t[j0 + 1, i1] * fu
    return a * (1 - fv) + b * fv


def sample_gpu(tex8, L, h, mask):
    """what the shader does: bilinear-filter each channel, THEN take the min of the picked channels (<= sample())"""
    t = tex8.astype(np.float64) / 255.0 * S_MAX
    u = h / H_STEP - 0.5
    v = np.clip(L / L_STEP, 0, H - 1)
    i0 = np.floor(u).astype(int); fu = (u - i0)[:, None]
    j0 = np.clip(np.floor(v).astype(int), 0, H - 2); fv = (v - j0)[:, None]
    i0 %= W; i1 = (i0 + 1) % W
    a = t[j0, i0] * (1 - fu) + t[j0, i1] * fu
    b = t[j0 + 1, i0] * (1 - fu) + t[j0 + 1, i1] * fu
    c = a * (1 - fv) + b * fv
    m = np.array(mask, bool)
    return np.where(m[None, :], c, np.inf).min(-1)


def guard(lin, tex8, mask):
    """numpy copy of LanbaiPurpleGuard"""
    o = S.lin_to_oklab(lin)
    L = o[..., 0]
    C = np.hypot(o[..., 1], o[..., 2])
    h = (np.degrees(np.arctan2(o[..., 2], o[..., 1])) + 360) % 360
    cmax = sample_gpu(tex8, L, h, mask) * np.maximum(L, 0.0)
    k = np.where(C > cmax, cmax / np.maximum(C, 1e-9), 1.0)
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
        binding = [h for h in np.arange(FH / 2, 360, FH) if min(sample(tex8, np.array([L]), np.array([h]), mask)[0] for L in (0.2, 0.5, 0.9)) < S_MAX - 0.01]
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
        cap = np.stack(p.map(scan_hue, hues))             # [720, nL, 4]
    tex = bake(cap)
    texs = dict(main=tex[..., :4], S11=np.repeat(tex[..., 4:5], 4, -1))
    from PIL import Image
    Image.fromarray(np.flipud(texs['main']), 'RGBA').save(os.path.join(KIT, 'Textures', 'Sea_PurpleCeiling.png'))   # v = 0 (L = 0) at the bottom
    Image.fromarray(np.flipud(texs['S11']), 'RGBA').save(os.path.join(KIT, 'Textures', 'Sea_PurpleCeiling_S11.png'))
    with Pool(4, initializer=_init, initargs=(texs,)) as p:
        ver = verify(texs, p)
    bib = bible_check(texs)
    out = dict(rule='after the guard, no colour displays h_ab %g..%g with C* > %g, under the grade(s) of its material' % (H_LO, H_HI, CSTAR),
               why_290_not_285='bible S8 zenith #3D4A80 displays h_ab 289.2 C* 34 and the other-sky nadir / 7c window indigo #2E3C66 286.3 C* 28 '
                               '(ART_BIBLE M5); guarding from 285 would grey the bible sky in the sea mirror',
               scan_margin='baked against h_ab %g..%g, C* > %g (stricter than the rule)' % (SCAN_LO, SCAN_HI, SCAN_C),
               texture='Sea/Textures/Sea_PurpleCeiling_S11.png: the same, all four channels = S11 (act 11). Sea/Textures/Sea_PurpleCeiling.png %dx%d RGBA8 linear (R S6, G S7a, B S7b, A S8): value/255*%g = max OKLab C/L; '
                       'u = hue/360 (repeat), v = (L/%g + 0.5)/%d (clamp)' % (W, H, S_MAX, L_STEP, H),
               materials={k: dict(channels=''.join('RGBA'[i] for i in range(4) if v[0][i]), grades=v[1]) for k, v in MATERIALS.items()},
               verification=ver, bible_colours=bib)
    json.dump(out, open(os.path.join(KIT, 'Docs~', 'purple_scan.json'), 'w'), indent=1, ensure_ascii=False)
    for k, v in bib.items():
        print(k, v)


if __name__ == '__main__':
    main()
