# -*- coding: utf-8 -*-
"""第 8 幕参考帧（numpy）：天空会话的三个预设（CPU 版 Lanbai/Sky 渲成的等距柱状图：dusk_8i、dusk_8ii（日线 10°）、blue_hour，
按驱动的时间表混合）+ 海之天花的替身（Lanbai/Sea CEILING 的算术：菲涅耳、玫瑰金镜、2.7 km 软边、溶化、宫殿金点）+ 云卡（cardshade）
+ 车壳（标准台 bible_v2 的角度窗；车顶与上墙按侵蚀打开）+ 雾（LanbaiFog 模型 B，预设的数），按 S7b → S8 → S8b 调色 + 驱动报的 ΔEV。
用法：~/bpy/bin/python act08_ref.py --t 929.11 940.36 --cam hero door_d12 [--w 960] [--dev auto|0]
暮组的卡没渲完之前，用晨组同形状的卡当替身（颜色仍是暮的），json 里记 cards_standin。"""
import os
import sys
import json
import math
import argparse
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'Clouds_v2', 'Source'))
import lb_common as C  # noqa: E402
import cardshade as CS  # noqa: E402
import act08_layout as AL  # noqa: E402

LAYOUT = json.load(open(os.path.join(KIT, 'Act08_Layout.json')))
B = LAYOUT['beats']
HARNESS = os.path.join(REPO, 'Engineering', 'render_harness')
CAMS = json.load(open(os.path.join(HARNESS, 'cameras.json')))
CAMS = CAMS.get('cameras', CAMS)
CAMS['door_d12'] = dict(eye=[0.55, 1.7, 2.05], yaw_deg=30.0, pitch_deg=0.0, hfov_deg=90.0, res=[1920, 1080],
                        note='the door view: the Zhuangzi block (+21.8 .. +48.2) and its mirror')
CAMS['hero_up'] = dict(eye=[0.55, 1.7, 2.05], yaw_deg=0.0, pitch_deg=35.0, hfov_deg=90.0, res=[1920, 1080],
                       note='the ceiling overhead (8-i) / the open sky (8-ii)')
CAMS['hero_down'] = dict(eye=[0.55, 1.7, 2.05], yaw_deg=0.0, pitch_deg=-30.0, hfov_deg=90.0, res=[1920, 1080],
                         note='the lower hemisphere: the mirrored dusk (8-i) / the other sky (8-ii)')
CAMS['vr_up'] = dict(eye=[0.55, 1.7, 2.05], yaw_deg=0.0, pitch_deg=60.0, hfov_deg=97.3, res=[1832, 1920],
                     note='D-09: VR single eye looking up (the roof is gone from ~950)')
CAMS['side_left'] = dict(eye=[0.55, 1.7, 2.05], yaw_deg=-90.0, pitch_deg=-5.0, hfov_deg=90.0, res=[1920, 1080],
                        note='the left side windows: the dusk wisps pass under the ceiling (922.36 -> 956.36)')
CAMS['side_right'] = dict(eye=[0.55, 1.7, 2.05], yaw_deg=110.0, pitch_deg=-5.0, hfov_deg=90.0, res=[1920, 1080],
                         note='the right side windows (behind the door group): the dusk wisps')
SHELL = json.load(open(os.path.join(HARNESS, 'bus_shell.json')))['presets']['bible_v2']
WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')
EYE = np.array(AL.EYE)
CARDJ = json.load(open(os.path.join(REPO, 'Clouds_v2', 'Textures', 'cards_v2.json')))
FOGP = {a['preset']: a for a in json.load(open(os.path.join(REPO, 'Sky', 'FogPresets.json')))['acts'] if 'preset' in a}
SKYS = {}


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def sky_img(name):
    if name not in SKYS:
        # the 8-ii line (_Udon_SunDisc.z 10 deg) is thinner than a 1024 px column: that one at 4096
        W = 4096 if 'line10' in name and os.path.exists(os.path.join(WORK, f'sky_{name}_4096.hdr')) else 1024
        SKYS[name] = C.read_hdr(os.path.join(WORK, f'sky_{name}_{W}.hdr')).astype(np.float64)
    return SKYS[name]


def weights(t):
    """(w8ii, wblue): the sky schedule (Apply / ApplyBlend smoothstep), as the driver"""
    return float(ss((t - B['F10e']) / 8.0)), float(ss((t - B['F12']) / 6.0))


SKY_AT = os.environ.get('LB_SKY_AT', '/tmp/lb/sky2')   # time keys (Tools~/sky_equirect.py --at), the sky session's state(t)
_AT = None


def _at_keys():
    global _AT
    if _AT is None:
        import glob
        import re
        _AT = {}
        for f in glob.glob(os.path.join(SKY_AT, 'sky_at*_*.hdr')):
            m = re.match(r'sky_at([0-9.]+)_(\d+)\.hdr', os.path.basename(f))
            if m:
                t, w = float(m.group(1)), int(m.group(2))
                if w > _AT.get(t, (0, ''))[0]:
                    _AT[t] = (w, f)
    return _AT


def _at_img(t):
    w, f = _at_keys()[t]
    k = ('at', t)
    if k not in SKYS:
        SKYS[k] = C.read_hdr(f).astype(np.float64)
    return SKYS[k]


def sky(V, t):
    """(pkg/sky d69940e on) the time keys when there are any: the nearest key for stills (rendered at the stills' own t),
    a lerp of the two neighbouring keys (0.5 s apart in the dissolve / F12) for sequences"""
    ks = sorted(_at_keys())
    if ks:
        if KEYED_NEAREST or t <= ks[0] or t >= ks[-1]:
            return C.sample_equirect(_at_img(min(ks, key=lambda k: abs(k - t))), V, 0.0)
        i = int(np.searchsorted(ks, t))
        t0, t1 = ks[i - 1], ks[i]
        x = (t - t0) / (t1 - t0)
        return C.sample_equirect(_at_img(t0), V, 0.0) * (1 - x) + C.sample_equirect(_at_img(t1), V, 0.0) * x
    return sky_presets(V, t)


def sky_presets(V, t):
    w2, wb = weights(t)
    a = C.sample_equirect(sky_img('dusk_8i'), V, 0.0)
    if 0 < w2 < 1:
        # dusk_8i.ApplyBlend(dusk_8ii) in parameter space too (the line grows with it), keys .25 / .5 / .75
        keys = [(0.0, 'dusk_8i'), (0.25, 'dusk_8i_to_dusk_8ii_0.25'), (0.5, 'dusk_8i_to_dusk_8ii_0.50'),
                (0.75, 'dusk_8i_to_dusk_8ii_0.75'), (1.0, 'dusk_8ii_line10_el0')]
        a = _keyed(keys, w2, V)
    elif w2 >= 1:
        a = C.sample_equirect(sky_img('dusk_8ii_line10_el0'), V, 0.0)
    if wb > 0:
        # dusk_8ii.ApplyBlend(blue_hour) in PARAMETER space (Tools~/sky_equirect.py --blend: the sky shader and its purple
        # guard run on the blended numbers, as in Unity), keyed at w = 0, .25, .5, .75, 1; between keys an image lerp
        keys = [(0.0, 'dusk_8ii_line10_el0'), (0.25, 'dusk_8ii_to_blue_hour_0.25'), (0.5, 'dusk_8ii_to_blue_hour_0.50'),
                (0.75, 'dusk_8ii_to_blue_hour_0.75'), (0.85, 'dusk_8ii_to_blue_hour_0.85'),
                (0.95, 'dusk_8ii_to_blue_hour_0.95'), (1.0, 'blue_hour')]
        return _keyed(keys, wb, V)
    return a


def _keyed(keys, w, V):
    """the nearest parameter-space blend key (an image lerp between two keys is NOT the blend: it made 4-9 % lilac
    that the real blend does not have)"""
    if KEYED_NEAREST:
        best = min(keys, key=lambda k: abs(k[0] - w))
        return C.sample_equirect(sky_img(best[1]), V, 0.0)
    for (w0, n0), (w1, n1) in zip(keys[:-1], keys[1:]):     # sequences (flashcheck): smooth in time, colours approximate
        if w <= w1:
            x = (w - w0) / (w1 - w0)
            return C.sample_equirect(sky_img(n0), V, 0.0) * (1 - x) + C.sample_equirect(sky_img(n1), V, 0.0) * x
    return C.sample_equirect(sky_img(keys[-1][1]), V, 0.0)


POEM_ON = True                             # the Zhuangzi stand-in on stills (act08_ink.py / flash turn it off)
KEYED_NEAREST = True                       # stills: the nearest true blend; act08_flash.py sets False


# ---- LanbaiFog model B with the presets' numbers (Common/Shaders/LanbaiSky.cginc LanbaiHorizonGradient)
def fog_params(t):
    w2, wb = weights(t)
    keys = ('near', 'far', 'zenith', 'nadir', 'width', 'shape', 'below')
    out = {}
    for k in keys:
        a = np.array(FOGP['dusk_8i'][k], float)
        b = np.array(FOGP['dusk_8ii'][k], float)
        c = np.array(FOGP['blue_hour'][k], float)
        out[k] = (a * (1 - w2) + b * w2) * (1 - wb) + c * wb
    out['band_dir'] = FOGP['dusk_8i']['band_dir']
    return out


def horizon_b(V, F):
    near, far, zen, nad = F['near'], F['far'], F['zenith'], F['nadir']
    el = np.degrees(np.arcsin(np.clip(V[:, 1], -1, 1)))
    T = np.array(F['band_dir'][:3])
    th = T[[0, 2]] + np.array([1e-5, 0.0]); th /= np.linalg.norm(th)
    vh = V[:, [0, 2]] + np.array([1e-5, 0.0]); vh /= np.linalg.norm(vh, axis=-1, keepdims=True)
    az = np.degrees(np.arccos(np.clip(vh @ th, -1, 1)))
    hz = near[None] + (far - near)[None] * ss(az / max(float(F['width']), 1.0))[:, None]
    sh, be = F['shape'], F['below']
    lo, hi = sh[0], min(max(sh[1], sh[0] + 0.1), 90.0)
    x = np.clip((el - lo) / max(hi - lo, 1e-4), 0, 1)
    up = (x * x * (3 - 2 * x)) ** (sh[2] if sh[2] > 0 else 1.0)
    dn = ss((el - be[1]) / (min(be[0], be[1] - 0.1) - be[1])) ** (be[2] if be[2] > 0 else 1.0)
    fl = 1e-3 * np.maximum(hz.max(-1, keepdims=True), zen.max()) + 1e-7
    c = np.exp2(np.log2(np.maximum(hz, fl)) * (1 - up)[:, None] + np.log2(np.maximum(zen[None], fl)) * up[:, None])
    return c * (1 - dn)[:, None] + nad[None] * dn[:, None]


def fog_apply(col, V, dist, t, cap=1.0):
    f = np.minimum(1 - np.exp(-AL.fog_density(t) * dist), cap)          # LanbaiFog: min(f, _FogCap)
    return col * (1 - f)[:, None] + horizon_b(V, fog_params(t)) * f[:, None]


# ---- the sea ceiling (Sea/README_Sea接口 §2.4: Lanbai/Sea CEILING; the arithmetic, not the shader)
WATER = np.array([0.0116, 0.0296, 0.0683])
MIRROR_TINT, REFL_GAIN = np.array([1.25, 1.3, 1.25]), 1.5


def ceiling(V, t, h):
    """colour (N,3), alpha (N,), distance (N,) of the ceiling (plane h above the eye, radius 2.7 km soft edge)"""
    n = len(V)
    col = np.zeros((n, 3)); al = np.zeros(n); dist = np.full(n, np.inf)
    if t >= LAYOUT['ceiling']['dissolve_end'] or t < B['exit']:
        return col, al, dist
    h = max(h, 0.05)                         # the exit frame: the plane is at the eye, it already covers the upper half
    up = V[:, 1] > 1e-5
    tt = np.where(up, h / np.maximum(V[:, 1], 1e-5), np.inf)
    p = EYE[None] + V * tt[:, None]
    d = np.hypot(p[:, 0], p[:, 2])
    a = np.where(up, AL.ceiling_alpha(d), 0.0)
    F = 0.02 + 0.98 * (1 - np.clip(V[:, 1], 0, 1)) ** 5
    refl = sky_lower(V * np.array([1, -1, 1]))
    c = WATER[None] * (1 - F)[:, None] + refl * (MIRROR_TINT * REFL_GAIN)[None] * F[:, None]
    c = fog_apply(c, V, np.where(up, tt, 0.0), t)
    tau = t - B['F10e']
    if tau > 0:
        el = np.degrees(np.arcsin(np.clip(V[:, 1], -1, 1)))
        pr = np.clip((tau - 4.0 * el / 90.0) / 5.0, 0, 1)
        behind = sky(V, t)
        c = np.exp2(np.log2(np.maximum(c, 1e-6)) * (1 - pr)[:, None] + np.log2(np.maximum(behind, 1e-6)) * pr[:, None])
        a = np.where(pr >= 1, 0.0, a)          # the colour has walked to the sky behind it (EV-linear per pixel)
    col[up] = c[up]; al[up] = a[up]; dist[up] = tt[up]
    return col, al, dist


def sky_lower(Vr):
    """what ReflCube_DuskLower holds: the dusk sky's lower hemisphere (8-i, mirrored elevation)"""
    return C.sample_equirect(sky_img('dusk_8i'), Vr, 0.0)


SPK = None


def specks(V, img, t, h, pix):
    global SPK
    S = LAYOUT['specks']
    if SPK is None:
        rng = np.random.default_rng(S['seed'])
        r = S['r_max'] * np.sqrt(rng.random(S['count']))
        th = rng.random(S['count']) * 2 * np.pi
        y = rng.uniform(*S['y_above'], S['count'])
        SPK = np.stack([r * np.sin(th), y, r * np.cos(th)], -1)
    if t >= LAYOUT['ceiling']['dissolve_end'] or t < B['exit']:
        return
    P = SPK + np.array([0.0, h + AL.EYE[1], 0.0])            # world: above the ceiling plane
    D = P - EYE[None]
    dist = np.linalg.norm(D, axis=-1)
    Dn = D / dist[:, None]
    gold = np.array(S['colour_linear'])
    tau = t - B['F10e']
    for k in range(len(P)):
        cosang = V @ Dn[k]
        ang = np.arccos(np.clip(cosang, -1, 1))
        sig = max(pix * 0.8, math.radians(0.02))
        w = np.exp(-0.5 * (ang / sig) ** 2)
        el = math.degrees(math.asin(Dn[k][1]))
        pr = float(np.clip((tau - 4.0 * el / 90.0) / 5.0, 0, 1)) if tau > 0 else 0.0
        pl = float(np.clip((pr - 0.3) / 0.7, 0, 1))
        path = max(P[k][1] - (h + AL.EYE[1]), 0) / max(Dn[k][1], 0.05)
        att = np.exp(-np.array([0.024, 0.020, 0.017]) * path)
        img += (w * (1 - pl))[:, None] * (gold * att * 1.2)[None]


# ---- cards
_CARD = {}
STANDIN = set()
F12_DIP, DIP_P, DIP_Q = LAYOUT['beats']['cards'].get('f12_dip', [0.0, 1.0, 1.0])   # (final r2) act08_layout.py


def f12_dip_shape(wb):
    return float(np.sin(math.pi * min(max(wb, 0.0), 1.0) ** DIP_P)) ** DIP_Q
AMB_OVERRIDE = {}                          # act08_shadow.py: group -> trial NEAR_AMB
COVER = {}                                 # per group: the cards' combined alpha per pixel (the last render)


def card_tex(name):
    real = name
    if not os.path.exists(os.path.join(REPO, 'Clouds_v2', 'Textures', name + '_K.png')):
        shape = name.split('_')[1]
        real = 'CloudV2_%s_dawn' % shape
        STANDIN.add(name)
    if real not in _CARD:
        cj = CARDJ['cards'][real]
        k = np.asarray(Image.open(os.path.join(REPO, 'Clouds_v2', 'Textures', real + '_K.png')).convert('RGBA')).astype(np.float32) / 255
        s = np.asarray(Image.open(os.path.join(REPO, 'Clouds_v2', 'Textures', real + '_S.png')).convert('RGB')).astype(np.float32) / 255
        _CARD[real] = (C.srgb_dec(k[..., :3]) * cj['kscale'], C.srgb_dec(s[..., :2]) * cj['sscale'], k[..., 3], cj)
    return _CARD[real]


def colours(group, t, amb=None):
    """the cards' light (D-25: colours per act). Solved values from cards_v2.json colours.<set> when they exist, else the
    design stand-in (sun = the preset's disc fill, sky / ground = the preset's zenith / nadir x 4, like the dawn solve)"""
    key = 'duskD' if group == 'lower' else 'duskU'
    c = CARDJ.get('colours', {}).get(key)
    if c:
        sc, sk, gd = np.array(c['SunColor']), np.array(c['SkyUpColor']), np.array(c['GroundColor'])
    else:
        sc = np.array([6.681, 1.892, 0.9061]) * 0.55
        sk = np.array([0.1139, 0.178, 0.469]) * 4.0
        gd = np.array([0.0437, 0.0685, 0.1878]) * 4.0
    if amb is not None:                       # (D-42 #1) the near layer: the dusk sky / ground light only
        sk, gd = sk * np.array(amb), gd * np.array(amb)
    bh = LAYOUT['blue_colours']
    wb = float(ss((t - B['F12']) / 6.0))
    sc = sc * (1 - wb)
    sk = sk * (1 - wb) + np.array(bh['SkyUpColor']) * wb
    gd = gd * (1 - wb) + np.array(bh['GroundColor']) * wb
    return sc, sk, gd


def card_list(t, h):
    out = []
    w2 = float(ss((t - B['F10e']) / 8.0))
    dark = 2.0 ** (-6.0 * float(np.clip((t - B['end8']) / 8.0, 0, 1)))
    lo_edge = math.atan(max(h, 0.05) / (LAYOUT['ceiling']['radius'] + 0.5 * LAYOUT['ceiling']['band']))
    diss = float(ss((t - B['F10e']) / 5.0))
    for c in LAYOUT['cards']:
        if c['show_from'] == '8i':
            # 8-i: only while the card's top is under the gap's lower edge (0.5 deg soft), then with the dissolve
            top = math.atan((c.get('top_y_local', c['position_local'][1]) + h - EYE[1]) / c['dist'])
            a = max(float(ss((lo_edge - top) / math.radians(0.5))), diss)
        else:
            a = w2
        if a <= 0:
            continue
        p = np.array(c['position_local'], float) + np.array([0.0, h, 0.0])
        out.append(dict(c, pivot=p, gain_t=c['gain'] * dark, alpha_t=a))
    wo = LAYOUT['beats']['cards']['wisp_out']
    aw = 1.0 - float(ss((t - wo[0]) / (wo[1] - wo[0])))
    if aw > 0:
        for w in LAYOUT['wisps']:
            p = np.array(w['position_local'], float) + np.array(w['tangent']) * w['drift'] * (t - B['exit']) + np.array([0.0, h, 0.0])
            out.append(dict(w, pivot=p, gain_t=w['gain'], alpha_t=aw, show_from='8i'))
    return out


def draw_cards(V, img, depth, t, h, pix):
    sun = np.array(LAYOUT['sun']['dir'])
    cards = card_list(t, h)
    cards.sort(key=lambda c: -np.linalg.norm(c['pivot'] - EYE))
    for c in cards:
        K, S, A, cj = card_tex(c['card'])
        hgt, wid = A.shape
        aspect = hgt / wid
        W = c['width_m']
        piv = c['pivot'].copy()
        if c.get('group') == 'lower':
            piv[1] -= (cj['opaque_bbox_uv'][3] - cj['cloud_base_v']) * aspect * W     # its top at the given elevation
        f = EYE - piv
        fxz = f[[0, 2]] / max(np.linalg.norm(f[[0, 2]]), 1e-6)
        right = np.array([-fxz[1], 0.0, fxz[0]])
        nrm = np.array([fxz[0], 0.0, fxz[1]])
        denom = V @ nrm
        with np.errstate(divide='ignore', invalid='ignore'):
            tt = ((piv - EYE) @ nrm) / denom
        ok = (tt > 0) & np.isfinite(tt)
        P = EYE + V * np.where(ok, tt, 0)[:, None]
        u = ((P - piv) @ right) / W + 0.5
        v = (P[:, 1] - piv[1]) / (W * aspect) + cj['cloud_base_v']
        bb = cj.get('bbox_uv', [0, 0, 1, 1])
        ok &= (u >= bb[0]) & (u <= bb[2]) & (v >= bb[1]) & (v <= bb[3]) & (tt < depth)
        if not ok.any():
            continue
        rel, left = CS.rel_angle(-f[[0, 2]], sun[[0, 2]])
        uu = np.where(left, 1 - u[ok], u[ok])
        # bilinear (r2: the review saw the nearest-neighbour texels)
        fx = np.clip(uu * wid - 0.5, 0, wid - 1.001); fy = np.clip((1 - v[ok]) * hgt - 0.5, 0, hgt - 1.001)
        x0 = fx.astype(int); y0 = fy.astype(int); ax = (fx - x0)[:, None]; ay = (fy - y0)[:, None]

        def bil(T):
            T2 = T.reshape(hgt, wid, -1)
            r = (T2[y0, x0] * (1 - ax) * (1 - ay) + T2[y0, x0 + 1] * ax * (1 - ay) + T2[y0 + 1, x0] * (1 - ax) * ay
                 + T2[y0 + 1, x0 + 1] * ax * ay)
            return r
        w0, w1, w2 = CS.key_weights(rel)
        Kb = bil(K)
        k = Kb[:, 0] * w0 + Kb[:, 1] * w1 + Kb[:, 2] * w2
        a = bil(A[..., None])[:, 0]
        Sb = bil(S)
        sc, sk, gd = colours(c.get('group', 'upper'), t, AMB_OVERRIDE.get(c.get('group')) if c.get('amb') and AMB_OVERRIDE else c.get('amb'))
        col = k[:, None] * sc + Sb[:, 0:1] * sk + Sb[:, 1:2] * gd
        if c.get('tint'):
            col = col * np.array(c['tint'])
        col *= c['gain_t']
        # (final r2) the F12 blend swings the lit cards from warm (h 40) to blue (h 283) through the D-21 band: the light
        # leaves first, so they are under L* 40 when the hue crosses (the driver's same dip, cardDipF12)
        _, wbx = weights(t)
        col *= 1.0 - F12_DIP * f12_dip_shape(wbx)
        mt = c.get('melt', [-0.02, 0.10, 0, 0])
        a = a * c['alpha_t'] * CS.melt(np.ones_like(a), v[ok], cj['cloud_base_v'], (mt[0], mt[1]))
        col = fog_apply(col, V[ok], tt[ok], t, c.get('fog_cap', 1.0))
        idx = np.nonzero(ok)[0]
        img[idx] = img[idx] * (1 - a)[:, None] + col * a[:, None]
        g = c.get('group', 'wisp')
        if g not in COVER or len(COVER[g]) != len(V):
            COVER[g] = np.zeros(len(V))
        COVER[g][idx] = 1 - (1 - COVER[g][idx]) * (1 - a)
        lk = 'L:' + c.get('layer', 'far')
        if lk not in COVER or len(COVER[lk]) != len(V):
            COVER[lk] = np.zeros(len(V))
        COVER[lk][idx] = 1 - (1 - COVER[lk][idx]) * (1 - a)


# ---- the cabin (bible_v2 angular shell); the roof and upper walls go with the erosion (0.25 -> 0.65, 922.36 -> 962.26)
DOOR_GROUP_AZ = (21.0, 50.0)                # the stand-in shell's door post + frame, inside the poem's +21.8 .. +48.2


DOOR_FADE = (957.40, 965.40)


def door_alpha(t):
    return float(ss((t - DOOR_FADE[0]) / (DOOR_FADE[1] - DOOR_FADE[0])))


def door_region(az):
    return (az >= DOOR_GROUP_AZ[0]) & (az <= DOOR_GROUP_AZ[1])


def window_mask(V, t, door='bible_v2', with_door=True):
    az, el = C.azel_from_dir(V)
    m = np.zeros(len(V), bool)
    for wdw in SHELL['windows']:
        a0, a1 = wdw['az']
        azz = az if a1 <= 180 else np.where(az < 0, az + 360, az)
        m |= (azz >= a0) & (azz <= a1) & (el >= wdw['el'][0]) & (el <= wdw['el'][1])
    for mu in SHELL.get('mullions', []):
        m &= ~((np.abs(az - mu['az']) < mu['width_deg'] / 2) & (el >= mu['el'][0]) & (el <= mu['el'][1]))
    e = float(np.clip((t - B['exit']) / (962.26 - B['exit']), 0, 1))
    open_el = 60.0 - 48.0 * e                    # the roof (el > 60) is gone early, the upper walls down to +12 by 962
    m |= el > open_el
    # D-33 #7a, as the bus built it (pkg/bus a0775dd): the whole door group (door frame / post / grab pole between the
    # windscreen and the door glass) fades out together, soft, 957.40 -> 965.40. Boolean users (cover, ink, poem) count it
    # open from half way; render() composites the soft fade (door_alpha)
    if with_door and door_alpha(t) >= 0.5:
        m |= door_region(az)
    return m


def exposure(t):
    g = LAYOUT.get('grade')
    if not g:
        return 0.0
    return float(np.interp(t, g['t'], g['dev']))


def grade_profile(t):
    if t < B['exit'] + 8.0:
        return C.lerp_profile('S7b', 'S8', float(ss((t - B['exit']) / 8.0)))
    if t < B['F12']:
        return 'S8'
    if t < B['end8']:
        return C.lerp_profile('S8', 'S8b', float(ss((t - B['F12']) / 8.0)))
    return C.lerp_profile('S8b', 'S9a', float(ss((t - B['end8']) / 8.0)))


def rays(cam, w):
    hf = math.radians(cam['hfov_deg'])
    rw, rh = cam['res']
    hh = int(round(w * rh / rw))
    tx = math.tan(hf / 2)
    ty = tx * hh / w
    xs = ((np.arange(w) + 0.5) / w * 2 - 1) * tx
    ys = (1 - (np.arange(hh) + 0.5) / hh * 2) * ty
    X, Y = np.meshgrid(xs, ys)
    d = np.stack([X, Y, np.ones_like(X)], -1)
    p, y = math.radians(cam['pitch_deg']), math.radians(cam['yaw_deg'])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), math.sin(p)], [0, -math.sin(p), math.cos(p)]])
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    d = d @ Rx.T @ Ry.T
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return d.reshape(-1, 3), hh, 2 * tx / w


# ---- the Zhuangzi lines (a stand-in for LanbaiPoemDriver, composition only): Fonts/README_Fonts §4.7 column: above the
# horizon L1, L3' (mirror) ; below L3, L1' ; 2.2 deg per character (CJK line spacing 1.6 em, half a gap either side of the
# horizon), centred on az +35, el 0; ink #27304A (D-33 #4), mirrors alpha 0.5 softness 0.3; L1 971.4, L3 976.4, out 989 -> 993
POEM_L1, POEM_L3 = '天之苍苍，其正色邪？', '其视下也，亦若是则已矣'
_POEM = {}


def _poem_canvas(line, mirror, ppd=40):
    from PIL import ImageDraw, ImageFont, ImageFilter
    key = (line, mirror)
    if key not in _POEM:
        font = ImageFont.truetype(os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf'), int(2.2 * ppd))
        w = int(len(line) * 2.2 * ppd + ppd); hgt = int(2.2 * ppd * 1.3)
        im = Image.new('L', (w, hgt), 0)
        ImageDraw.Draw(im).text((ppd // 2, int(0.1 * hgt)), line, fill=255, font=font)
        if mirror:
            im = im.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(0.3 * ppd * 0.25))
        _POEM[key] = np.asarray(im).astype(np.float32) / 255.0
    return _POEM[key]


def poem_overlay(codes, V, t, ppd=40):
    if not (971.4 <= t < 993.0):
        return codes
    az, el = C.azel_from_dir(V)
    ink = C.hex_rgb('#27304A') * 255.0
    lh = 2.2 * 1.6                                           # line pitch (deg)
    rows = [('L1', POEM_L1, False, 0.5 * lh + 0.5 * lh * 0.6 + lh, 971.4), ('L3m', POEM_L3, True, 0.5 * lh * 0.6 + 0.5 * lh, 976.4),
            ('L3', POEM_L3, False, -(0.5 * lh * 0.6 + 0.5 * lh), 976.4), ('L1m', POEM_L1, True, -(0.5 * lh + 0.5 * lh * 0.6 + lh), 971.4)]
    out = codes.reshape(-1, 3).copy()
    drift = max(0.0, t - 989.0) / 4.0
    for name, line, mirror, elc, t_on in rows:
        if t < t_on:
            continue
        cv = _poem_canvas(line, mirror, ppd)
        hgt, w = cv.shape
        a_w, e_h = w / ppd, hgt / ppd
        e_off = elc + (3.0 * drift if not name.endswith('m') == (elc > 0) else -3.0 * drift)
        x = (az - (35.0 - 0.5 * a_w)) * ppd
        y = ((e_off + 0.5 * e_h) - el) * ppd
        m = (x >= 0) & (x < w - 1) & (y >= 0) & (y < hgt - 1)
        if not m.any():
            continue
        cov = cv[y[m].astype(int), x[m].astype(int)] * (0.5 if mirror else 1.0) * (1.0 - drift)
        out[m] = out[m] * (1 - cov[:, None]) + ink[None] * cov[:, None]
    return out.reshape(codes.shape)


def purple_share(codes):
    """D-21: h_ab 290-330, C* > 8, L* > 40 (the bible's palette colours pass: they are all < 290 or L* <= 40)"""
    L, hh, cc = C.hue_chroma(codes.reshape(-1, 3))
    return float(((hh >= 290) & (hh <= 330) & (cc > 8) & (L > 40)).mean())


def render(t, cam_name, w=960, door='bible_v2', out_dir=None, tag='', dev=None):
    cam = dict(CAMS[cam_name])
    V, hh, pix = rays(cam, w)
    h = AL.motion(t)[0]
    img = sky(V, t)
    depth = np.full(len(V), np.inf)
    cc, ca, cd = ceiling(V, t, h)
    # cards first (behind the ceiling's opaque inner disc where it is nearer), then the ceiling over them
    draw_cards(V, img, np.where(ca > 0.999, cd, depth), t, h, pix)
    img = img * (1 - ca)[:, None] + cc * ca[:, None]
    specks(V, img, t, h, pix)
    win = window_mask(V, t, door)
    interior = C.hex_lin('#1A1F2A')
    da = door_alpha(t)
    if 0 < da < 1:
        # the door group mid-fade: the base shell's window mask (no door), the door region blended by its fade
        az_, _ = C.azel_from_dir(V)
        dr = door_region(az_) & ~window_mask(V, t, door, with_door=False)
        base = img.copy()
        img[~win] = interior
        img[dr] = interior * (1 - da) + base[dr] * da
    else:
        img[~win] = interior
    lin = img.reshape(hh, w, 3)
    ev = exposure(t) if dev is None else dev
    codes = C.grade(lin, grade_profile(t), bloom=True, ev=ev)
    if POEM_ON:
        codes = np.where(win.reshape(hh, w, 1), poem_overlay(codes, V, t).reshape(hh, w, 3), codes)
    luma = codes @ C.LUMA
    thr = np.percentile(luma, 99.9)
    ys, xs = np.nonzero(luma >= thr)
    # the ceiling pixels carry the sea's own purple guard in Unity (Lanbai/Sea, D-17 / D-21, README_Sea接口 §2.7), which
    # this stand-in does not model: the D-21 share is also given without them
    nc = (ca.reshape(hh, w) < 0.5) & win.reshape(hh, w)
    m = dict(t=t, cam=cam_name, door=door, h=round(h, 1), dEV=round(ev, 3), APL=round(float(luma.mean()), 1),
             purple_D21=round(purple_share(codes), 4),
             purple_D21_no_ceiling=round(purple_share(codes[nc]) * float(nc.mean()), 4) if nc.any() else 0.0, brightest_px=[round(float(xs.mean() / w), 3), round(float(ys.mean() / hh), 3)],
             reveal=round(AL.disc_reveal(t), 3), cards_standin=sorted(STANDIN), width=w)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.join(out_dir, f'{tag}{cam_name}_t{t:.2f}')
        Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(base + '.png')
        json.dump(m, open(base + '.json', 'w'), indent=1)
    return codes, m, lin


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--t', type=float, nargs='+', default=[940.36])
    ap.add_argument('--cam', nargs='+', default=['hero'])
    ap.add_argument('--w', type=int, default=960)
    ap.add_argument('--door', default='bible_v2')
    ap.add_argument('--out', default='/tmp/lb/act08')
    ap.add_argument('--tag', default='')
    ap.add_argument('--dev', type=float, default=None)
    a = ap.parse_args()
    for t in a.t:
        for c in a.cam:
            _, m, _ = render(t, c, a.w, a.door, a.out, a.tag, a.dev)
            print(json.dumps(m, ensure_ascii=False))
