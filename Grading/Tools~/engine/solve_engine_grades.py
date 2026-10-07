# -*- coding: utf-8 -*-
"""Re-solve the PPv2 colour-grading parameters so that the REAL engine (ppv2_engine.py, PPv2 3.x Neutral path)
shows the screen targets the ART BIBLE and calib_final define.  (verify.md B1; bible law 1: 屏幕目标值是法律，参数只是起点.)

  look definition  = art/grades_final.json run through the art simulator (art/lens_cine/ppv2.py + bible_work/lutlib_core.py).
                     Every screen target in calib_final (section A reads, B displays, C test card, D overlay displays)
                     was made with it. It is NOT changed here.
  engine           = Tools~/engine/ppv2_engine.py (PPv2 source: LogC contrast, then white balance / lift-gamma-gain /
                     saturation in linear Rec.709, 33^3 float16 LUT, trilinear).
  this script      = for every scene profile, finds temperature, tint, saturation, contrast, the three trackballs and
                     the channel mixer (a 3x3 in linear 709 that emulates the look's AP1 working space for saturated
                     colours: the sign's indigo, the wound rims, tail lights) such that engine(x) ~= look(x) over
                       * the grey ramp 0, 0.18*2^k (k = -9..+5, quarter stops)  incl. the 11 calib section C patches,
                       * input 0 (the black point; S7a uses the bible's stated #030B0F, see BLACK_OVERRIDE),
                       * every calib section A light reading, section B fill and section D overlay fill of that profile,
                       * ~4000 pixels of the art pipeline's own preview test frame for that profile (previews/),
                       * ~1000 of that frame's most saturated pixels (weight W_SAT): the colours that carry the look,
                       * (--neighbours) frames of the scenes it crossfades with (bible 6.x), at W_NEIGHBOUR,
                       * 800 random colours (keeps the general look, e.g. for textures nobody listed).
                     postExposure, every bloom parameter, colorFilter, hueShift, mixer and curves are NOT touched
                     (so the Director's b, the EXPO weights of table B3 and every bloom T0 stay exactly as in the bible).
Writes Tools~/inputs/grades_engine.json = grades_final.json with each scene profile's colour parameters replaced by the
engine solution (the look-definition values kept under "ppv2_lookdef" for traceability) + an "_engine" report block.

Usage:  python3 solve_engine_grades.py [--frames frames.npz] [--only S1,S7b] [--tier all|lgg|lift]
        (--frames: scene-linear preview frames dumped from art/bible_work/make_previews.SOURCES; without it the fit
         uses the listed targets + random colours only.)  About 1-3 minutes per profile on one core.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import sys
import time

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
KIT = os.path.dirname(TOOLS)
ART = os.path.normpath(os.path.join(KIT, '..', '..', 'art'))
sys.path.insert(0, HERE)
import ppv2_engine as E  # noqa: E402

# ------------------------------------------------------------------ look definition (art simulator, read-only use)
sys.path.insert(0, os.path.join(ART, 'lens_cine'))
sys.path.insert(0, os.path.join(ART, 'bible_work'))
import ppv2 as LD  # noqa: E402
from lutlib_core import patch_ppv2  # noqa: E402
patch_ppv2(LD)

COLOUR_KEYS = ('temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain')   # the look definition's
ENGINE_KEYS = COLOUR_KEYS + ('mixer',)                                                       # what the engine solve sets
MIXER_IDENTITY = [100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0, 100.0]
# The bible's text states S7a's black explicitly (section 6 / 7a: "lift ... (黑 → #030B0F，红不再为 0)") and rejects
# #00070B as "数码青" in 1.4 -- but the look simulator's input-0 value for S7a IS #00070B (#030B0F is its k-6 patch).
# Law 1: the hex written in the bible wins.
BLACK_OVERRIDE = {'S7a': '#030B0F'}
# bible 1.3.5 / 1.4: night grades lift input 0 to blue-black and NEVER crush red to 0. The look simulator's red at input 0
# is 0.9-1.9 codes; the fit aims at no less than RED_FLOOR so the 8-bit screen value cannot round to 0.
RED_FLOOR = 1.3
NIGHT = {'S1', 'S2', 'S3', 'S4', 'S4c', 'S7a', 'S7b', 'S8b', 'S9a', 'S9b', 'S11', 'S12'}
W_KEY, W_RAMP, W_BLACK, W_FRAME, W_RANDOM = 25.0, 100.0, 20000.0, 1.0, 0.25
W_LIGHT = 60.0         # calib section A readings: lights are tuned by these, a hue error cannot be fixed by intensity
# Visible crossfades (bible 6.x): while profile X rises, the neighbouring scene's content is still on screen under X's
# grade. Those frames enter X's fit at W_NEIGHBOUR x W_FRAME so the crossfade middle stays on the look too.
# (Hard cuts under a full overlay -- S4c->S6, S9b->S10, S10->S11, S11->S12 -- have no such moment.)
NEIGHBOURS = {'S1': ['S2'], 'S2': ['S1', 'S3'], 'S3': ['S2', 'S4'], 'S4': ['S3', 'S4c'], 'S4c': ['S4'],
              'S6': ['S7a'], 'S7a': ['S6', 'S7b'], 'S7b': ['S7a', 'S8'], 'S8': ['S7b', 'S8b'], 'S8b': ['S8', 'S9a'],
              'S9a': ['S8b', 'S9b'], 'S9b': ['S9a'], 'S12': []}
W_NEIGHBOUR = 0.0      # set by --neighbours
W_SAT = 2.0            # x W_FRAME: the most saturated pixels of the profile's own frame


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def look_codes(lin, p):
    """Screen codes (float) of the LOOK DEFINITION (art simulator, no bloom)."""
    q = LD.full(p)
    x = np.asarray(lin, np.float64) * 2.0 ** q['postExposure']
    return LD.lin_to_srgb(LD.grade_lut(x, q)) * 255.0


def parse_set(s):
    m = re.match(r'\s*#([0-9A-Fa-f]{6})(?:\s*@\s*\+?(-?[\d.]+))?', s)
    if not m:
        raise ValueError('cannot parse fill %r' % s)
    return E.srgb_decode(E.hex_raw('#' + m.group(1))) * 2.0 ** float(m.group(2) or 0.0)


def key_samples(sid, G, C):
    """(label, scene-linear rgb, kind) for every listed target of profile sid."""
    out = [('black (input 0)', np.zeros(3), 'black')]
    for k in np.arange(-9, 7.001, 0.25):     # up to +7: EXPO_UP pushes S9b another +2.4 EV in the white swell
        out.append(('grey 0.18*2^%+.2f' % k, np.full(3, 0.18 * 2.0 ** k), 'ramp'))
    for L in C['lights']:
        if L['scene'] == sid:
            alb = 0.80 if '白卡' in L['role'] else 0.18
            out.append(('§A ' + L['role'], alb * E.srgb_decode(E.hex_raw(L['colour'])) * L['E'], 'A'))
    for name, rgb in E.COLOUR_PATCHES:      # the test card's colour row: designed saturated colours, every profile
        out.append(('colour row ' + name, np.array(rgb, np.float64), 'colour'))
    for U in C['unlit']:
        if U['scene'] == sid:
            out.append(('§B ' + U['element'], parse_set(U['set']), 'B'))
    for O in C['overlay']:
        if O['grade'] == sid:
            out.append(('§D ' + O['when'] + ' ' + O['role'], parse_set(O['set']), 'D'))
    return out


def frame_samples(frames, sid, n=4000, seed=7):
    if frames is None or sid not in frames:
        return np.zeros((0, 3))
    f = np.asarray(frames[sid], np.float64).reshape(-1, 3)
    f = f[np.all(np.isfinite(f), 1)]
    f = np.maximum(f, 0.0)
    rng = np.random.default_rng(seed)
    # stratify by luminance so the few dark / bright pixels are represented
    lum = f @ E.LUMA709_UTIL
    bins = np.quantile(lum, np.linspace(0, 1, 21))
    idx = []
    for a, b in zip(bins[:-1], bins[1:]):
        cand = np.nonzero((lum >= a) & (lum <= b))[0]
        if len(cand):
            idx.append(rng.choice(cand, size=min(len(cand), n // 20), replace=False))
    return f[np.concatenate(idx)]


def saturated_samples(frames, sid, n=1000, seed=17):
    """The frame's saturated pixels ((max - min) / max > 0.6, max > 0.01): few in number, but they carry the look
    (the sign's indigo, the wound rims, tail lights, sodium lamps). Luminance-stratified sampling misses them."""
    if frames is None or sid not in frames:
        return np.zeros((0, 3))
    f = np.maximum(np.asarray(frames[sid], np.float64).reshape(-1, 3), 0.0)
    f = f[np.all(np.isfinite(f), 1)]
    mx, mn = f.max(1), f.min(1)
    cand = np.nonzero(((mx - mn) / np.maximum(mx, 1e-6) > 0.6) & (mx > 0.01))[0]
    if len(cand) == 0:
        return np.zeros((0, 3))
    rng = np.random.default_rng(seed)
    return f[rng.choice(cand, size=min(len(cand), n), replace=False)]


def random_samples(n=800, seed=11):
    rng = np.random.default_rng(seed)
    hue = rng.uniform(0, 1, n)
    sat = rng.uniform(0, 0.95, n) ** 0.7
    val = 0.18 * 2.0 ** rng.uniform(-8, 3.5, n)
    hsv = np.stack([hue, sat, np.ones(n)], -1)
    rgb = E.hsv_to_rgb(hsv)
    rgb = rgb / np.maximum(rgb @ E.LUMA709_UTIL, 1e-6)[:, None] * val[:, None]
    return rgb


# ------------------------------------------------------------------ parameter vector
TIERS = {
    'lift': ['lift'],
    'lgg': ['lift', 'gamma', 'gain'],
    'nomix': ['temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain'],
    'all': ['temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain', 'mixer'],
}
# prior: how far a parameter may wander from its look-definition value before it costs as much as REG_COST
# (~ a uniform 0.3-code error over every sample). Keeps the solution a sane, crossfade-friendly grade instead of a
# degenerate combination (e.g. temperature -40 cancelled by a blue gain of 0.17) that only fits the sampled colours.
SCALE = {'temperature': 10.0, 'tint': 10.0, 'saturation': 8.0, 'contrast': 25.0,
         ('lift', 'c'): 0.02, ('lift', 'w'): 0.05, ('gamma', 'c'): 0.03, ('gamma', 'w'): 0.3,
         ('gain', 'c'): 0.03, ('gain', 'w'): 0.4, 'mixer': 5.0}
# mixer entries are percentages (identity 100 / 0); 5 points off identity cost as much as the other priors' scales.
# contrast and the gamma / gain OFFSETS may trade freely: gain * x^(1/gamma) pivoted at 0.18 IS pure-log contrast, which
# is what the look (ACEScc, no toe) does and what PPv2's LogC contrast (toe at ~0.009 linear) cannot do near black.
# White balance and the trackball COLOURS stay close to the look values.
REG_COST = 1000.0


def pack(p, names):
    x = []
    for n in names:
        if n in ('lift', 'gamma', 'gain'):
            v = np.asarray(p[n], np.float64)
            v3 = v[:3] - v[2] + 1.0             # gauge: z = 1 (the result only sees xyz - lum(xyz))
            x += [v3[0], v3[1], v[3]]
        elif n == 'mixer':
            x += [float(v) for v in p.get('mixer', MIXER_IDENTITY)]
        else:
            x.append(float(p[n]))
    return np.array(x, np.float64)


def unpack(x, base, names):
    p = copy.deepcopy(base)
    i = 0
    for n in names:
        if n in ('lift', 'gamma', 'gain'):
            v = np.array([x[i], x[i + 1], 1.0])
            v = v + (1.0 - v.max())             # PPv2 trackball convention: max channel = 1 (same grade)
            p[n] = [float(v[0]), float(v[1]), float(v[2]), float(x[i + 2])]
            i += 3
        elif n == 'mixer':
            p[n] = [float(v) for v in x[i:i + 9]]
            i += 9
        else:
            p[n] = float(x[i])
            i += 1
    return p


def reg_scale(names):
    s = []
    for n in names:
        s += ([SCALE[(n, 'c')], SCALE[(n, 'c')], SCALE[(n, 'w')]] if n in ('lift', 'gamma', 'gain')
              else [SCALE['mixer']] * 9 if n == 'mixer' else [SCALE[n]])
    return np.array(s)


def smooth_codes(lin, p):
    """Engine through the 33^3 LUT but without float16 storage: smooth in the parameters (optimiser only)."""
    g = np.stack(np.meshgrid(E.GRID1, E.GRID1, E.GRID1, indexing='ij'), -1)
    L = np.maximum(E.color_grade(g, p), 0.0)
    return E.srgb_encode(E.sample_lut(L, E.uvw_of(lin, p))) * 255.0


def round_params(p):
    q = copy.deepcopy(p)
    for n in ('temperature', 'tint', 'saturation', 'contrast'):
        q[n] = round(float(q[n]), 2)
    for n in ('lift', 'gamma', 'gain'):
        q[n] = [round(float(v), 4) for v in q[n]]
    if 'mixer' in q:
        q['mixer'] = [round(float(v), 2) for v in q['mixer']]
    return q


def solve_profile(sid, G, C, frames, tier, log=print):
    look = G['profiles'][sid]['ppv2']
    base = {k: copy.deepcopy(look[k]) for k in ('postExposure',) + COLOUR_KEYS}
    base.update(colorFilter=G['common']['colorFilter'], hueShift=G['common']['hueShift'])
    look_p = dict(base)                      # the look definition has no mixer (identity)
    base['mixer'] = list(MIXER_IDENTITY)
    keys = key_samples(sid, G, C)
    K_lin = np.array([k[1] for k in keys])
    K_tgt = look_codes(K_lin, look_p)
    if sid in BLACK_OVERRIDE:
        K_tgt[0] = E.hex8(BLACK_OVERRIDE[sid])
    if sid in NIGHT:
        K_tgt[0, 0] = max(K_tgt[0, 0], RED_FLOOR)
    Fr = frame_samples(frames, sid)
    Nb = np.zeros((0, 3))
    if W_NEIGHBOUR > 0:
        nbs = [frame_samples(frames, n, n=2000, seed=13) for n in NEIGHBOURS.get(sid, [])]
        nbs = [x for x in nbs if len(x)]
        if nbs:
            Nb = np.vstack(nbs)
    Sa = saturated_samples(frames, sid)
    Rn = random_samples()
    F_tgt = look_codes(Fr, look_p) if len(Fr) else np.zeros((0, 3))
    N_tgt = look_codes(Nb, look_p) if len(Nb) else np.zeros((0, 3))
    S_tgt = look_codes(Sa, look_p) if len(Sa) else np.zeros((0, 3))
    R_tgt = look_codes(Rn, look_p)
    wk = np.array([W_BLACK if k[2] == 'black' else W_RAMP if k[2] == 'ramp' else W_LIGHT if k[2] == 'A' else W_KEY for k in keys])
    lin_all = np.vstack([K_lin, Fr, Nb, Sa, Rn])
    tgt_all = np.vstack([K_tgt, F_tgt, N_tgt, S_tgt, R_tgt])
    w_all = np.concatenate([wk, np.full(len(Fr), W_FRAME), np.full(len(Nb), W_FRAME * W_NEIGHBOUR),
                            np.full(len(Sa), W_FRAME * W_SAT), np.full(len(Rn), W_RANDOM)])
    sw = np.sqrt(w_all)[:, None]
    names = TIERS[tier]
    x0 = pack(base, names)
    rs = reg_scale(names)

    def resid(x):
        p = unpack(x, base, names)
        r = (smooth_codes(lin_all, p) - tgt_all) * sw
        return np.concatenate([r.ravel(), np.sqrt(2.0 * REG_COST) * (x - x0) / rs])

    t = time.time()
    # warm start for the lift offset: the LogC contrast pushes linear black below 0 (verify.md B1)
    starts = [x0]
    if 'lift' in names:
        i = names.index('lift')
        off = sum(3 if n in ('lift', 'gamma', 'gain') else 1 for n in names[:i]) + 2
        for dw in (0.012, 0.02):
            s = x0.copy()
            s[off] += dw
            starts.append(s)
    best = None
    for s in starts:
        r = least_squares(resid, s, method='trf', x_scale=rs, max_nfev=400, xtol=1e-10, ftol=1e-10)
        if best is None or r.cost < best.cost:
            best = r
    p = round_params(unpack(best.x, base, names))
    log('   %-4s tier %-4s  %d samples (%d key, %d frame, %d neighbour, %d saturated, %d random)  cost %.0f -> %.0f  %.0fs'
        % (sid, tier, len(lin_all), len(keys), len(Fr), len(Nb), len(Sa), len(Rn), 0.5 * np.sum(resid(x0) ** 2), best.cost, time.time() - t))
    return p, dict(keys=keys, K_tgt=K_tgt, Fr=Fr, F_tgt=F_tgt, Nb=Nb, N_tgt=N_tgt, Sa=Sa, S_tgt=S_tgt, Rn=Rn, R_tgt=R_tgt)


def evaluate(sid, p, data, C):
    """Engine numbers with the real float16 LUT, rounded to 8-bit like a screenshot."""
    L = E.bake_lut(p)
    out = {}
    K = np.round(E.codes(np.array([k[1] for k in data['keys']]), p, L))
    dk = np.abs(K - np.round(data['K_tgt'])).max(1)
    rows = []
    for (label, lin, kind), got, want, d in zip(data['keys'], K, data['K_tgt'], dk):
        rows.append(dict(label=label, kind=kind, engine=E.to_hex(got), target=E.to_hex(want), codes=int(d)))
    ramp = C['ramp'][sid]
    P = np.stack([np.full(3, 0.18 * 2.0 ** k) for k in range(-6, 5)])
    got = np.round(E.codes(P, p, L))
    out['sectionC'] = [dict(k=k, engine=E.to_hex(g), target=h, codes=int(np.abs(g - E.hex8(h)).max()))
                       for k, g, h in zip(range(-6, 5), got, ramp)]
    out['sectionC_max'] = max(r['codes'] for r in out['sectionC'])
    out['black'] = rows[0]
    by = {}
    for r in rows:
        by.setdefault(r['kind'], []).append(r)
    out['max_by_kind'] = {k: max(r['codes'] for r in v) for k, v in by.items()}
    out['worst_listed'] = sorted([r for r in rows if r['kind'] in ('A', 'B', 'D')], key=lambda r: -r['codes'])[:6]
    for tag, name in (('F', 'frame'), ('N', 'neighbour'), ('S', 'saturated'), ('R', 'random')):
        lin, tgt = data.get({'F': 'Fr', 'N': 'Nb', 'S': 'Sa', 'R': 'Rn'}[tag]), data.get(tag + '_tgt')
        if lin is None or tgt is None or len(lin) == 0:
            continue
        d = np.abs(np.round(E.codes(lin, p, L)) - np.round(tgt)).max(1)
        out[name] = dict(mean=round(float(d.mean()), 3), p99=float(np.percentile(d, 99)), max=int(d.max()))
    return out


_JOB = None


def _solve_job(sid):
    G, C, frames, tier = _JOB
    return solve_profile(sid, G, C, frames, tier)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grades', default=os.path.join(ART, 'grades_final.json'))
    ap.add_argument('--calib', default=os.path.join(ART, 'calib_final.json'))
    ap.add_argument('--frames', default=None)
    ap.add_argument('--only', default=None)
    ap.add_argument('--tier', default='all', choices=sorted(TIERS))
    ap.add_argument('--out', default=os.path.join(TOOLS, 'inputs', 'grades_engine.json'))
    ap.add_argument('--dry', action='store_true', help='print, do not write')
    ap.add_argument('--neighbours', type=float, default=0.0,
                    help='weight (x W_FRAME) of the crossfade neighbours\' frames in each profile\'s fit (needs --frames)')
    ap.add_argument('--jobs', type=int, default=1, help='solve this many profiles in parallel (same result as 1)')
    a = ap.parse_args()
    global W_NEIGHBOUR
    W_NEIGHBOUR = a.neighbours
    G = json.load(open(a.grades, encoding='utf-8'))
    C = json.load(open(a.calib, encoding='utf-8'))
    frames = np.load(a.frames) if a.frames else None
    if frames is not None:
        frames = {k: np.asarray(frames[k]) for k in frames.files}
    ids = [s for s in sorted(G['profiles'], key=lambda s: G['profiles'][s]['priority'])]
    only = set(a.only.split(',')) if a.only else None

    def is_neutral(sid):
        look = G['profiles'][sid]['ppv2']
        n = all(look[k] == v for k, v in (('temperature', 0), ('tint', 0), ('saturation', 0), ('contrast', 0)))
        return n and all(list(look[k]) == [1, 1, 1, 0] for k in ('lift', 'gamma', 'gain'))

    def is_s2_copy(sid):
        return sid == 'S11' and G['profiles']['S11']['ppv2'] == G['profiles']['S2']['ppv2']

    pre = {}
    todo = [s for s in ids if (not only or s in only) and not is_neutral(s) and not is_s2_copy(s)]
    if a.jobs > 1 and len(todo) > 1:
        import multiprocessing as mp
        global _JOB
        _JOB = (G, C, frames, a.tier)
        with mp.get_context('fork').Pool(min(a.jobs, len(todo))) as pool:
            for sid, res in zip(todo, pool.map(_solve_job, todo)):
                pre[sid] = res

    OUT = copy.deepcopy(G)
    report = {}
    solved = {}
    for sid in ids:
        if only and sid not in only:
            continue
        look = G['profiles'][sid]['ppv2']
        if is_neutral(sid):            # S10: every grading parameter at the PPv2 default -> engine == look already
            p = {k: copy.deepcopy(look[k]) for k in COLOUR_KEYS}
            p.update(postExposure=look['postExposure'], colorFilter=G['common']['colorFilter'], hueShift=G['common']['hueShift'],
                     mixer=list(MIXER_IDENTITY))
            data = dict(keys=key_samples(sid, G, C), Fr=np.zeros((0, 3)), F_tgt=None, Rn=random_samples(), R_tgt=None)
            data['K_tgt'] = look_codes(np.array([k[1] for k in data['keys']]), p)
            data['R_tgt'] = look_codes(data['Rn'], p)
            tier = 'unchanged (neutral)'
        elif is_s2_copy(sid) and 'S2' in solved:
            p, data = solved['S2']        # bible: S11 = S2 exactly ("normality is the lie")
            tier = 'copy of S2'
        elif sid in pre:
            p, data = pre[sid]
            tier = a.tier
        else:
            p, data = solve_profile(sid, G, C, frames, a.tier)
            tier = a.tier
        solved[sid] = (p, data)
        ev = evaluate(sid, p, data, C)
        ev['tier'] = tier
        report[sid] = ev
        print('%-4s %-18s §C max %d  black %s (target %s)  maxA/B/D %s  frame %s  neighbour %s  saturated %s  random %s' % (
            sid, tier, ev['sectionC_max'], ev['black']['engine'], ev['black']['target'],
            '/'.join(str(ev['max_by_kind'].get(k, '-')) for k in 'ABD'), ev.get('frame'), ev.get('neighbour'), ev.get('saturated'),
            ev.get('random')), flush=True)
        for w in ev['worst_listed'][:3]:
            print('       worst listed: %-2s %s  engine %s target %s (%d)' % (w['kind'], w['label'], w['engine'], w['target'], w['codes']))
        new = {k: p[k] for k in ENGINE_KEYS}
        OUT['profiles'][sid]['ppv2_lookdef'] = {k: copy.deepcopy(look[k]) for k in COLOUR_KEYS}
        OUT['profiles'][sid]['ppv2'].update(new)

    if a.dry or only:
        print('(dry run / partial: nothing written)')
        return
    OUT['_engine'] = {
        'what': ('Engine realisation of the look. profiles.*.ppv2 = the numbers PPv2 3.x (HDR, Neutral) needs to SHOW the '
                 'bible / calib_final screen targets; profiles.*.ppv2_lookdef = the look-definition numbers of '
                 'art/grades_final.json (bible appendix B1), which only mean the right thing in the art simulator '
                 '(ACES working spaces). Screen targets are unchanged (bible law 1). ppv2.mixer = PPv2 channel mixer, 9 '
                 'percentages row-major (mixerRedOutRedIn ... mixerBlueOutBlueIn). postExposure, bloom, colorFilter, '
                 'hueShift, helpers: identical to grades_final.json.'),
        'solver': 'Tools~/engine/solve_engine_grades.py (tier %s, crossfade neighbours %g)' % (a.tier, a.neighbours),
        'engine_model': 'Tools~/engine/ppv2_engine.py (PPv2 3.0.2 / 3.6.0 source: LogC contrast, linear Rec.709 WB/LGG/sat, 33^3 half LUT)',
        'source_grades_sha256': sha256(a.grades),
        'source_calib_sha256': sha256(a.calib),
        'black_override': BLACK_OVERRIDE,
        'report': report,
    }
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
