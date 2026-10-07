# -*- coding: utf-8 -*-
"""calib_final (sections A, B, D) checked through the ENGINE with the engine grades, and the fills re-solved where the
engine misses a screen target by >= RESOLVE_AT codes (bible law 1: the target stays, the 填值 changes).

Inputs : Tools~/inputs/grades_engine.json (solve_engine_grades.py), Tools~/inputs/calib_final.json (art, unchanged)
Output : Tools~/inputs/calib_engine.json
           lights  : every section A reading as the engine shows it (targets unchanged; lights are tuned by the grey card)
           unlit   : every section B fill: engine display of the calib fill; "set_engine" where it had to be re-solved
           overlay : every section D overlay fill, same
           bloom_t0: per profile, the luma a neutral grey shows at the bloom knee start T0 in the engine (bible: 228)
           blacks  : per profile, the target and the engine value at input 0
           colour_patches: the test card's second row (8 saturated scene-linear colours that carry the look: the sign's
                     indigo, the wound violet, tail-light red, sodium orange, sea blue, dusk rose, leaf green, Lichtchen
                     warm white) as the LOOK shows them under every profile (art simulator). Not bible targets: a check
                     that PPv2 in Unity treats saturated colours the way the engine model says (MeasureAll).
Usage  : python3 engine_calib.py
"""
import copy
import hashlib
import json
import os
import re
import sys

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ART = os.path.normpath(os.path.join(TOOLS, '..', '..', '..', 'art'))
sys.path.insert(0, HERE)
import ppv2_engine as E  # noqa: E402

COLOUR_PATCHES = E.COLOUR_PATCHES   # test-card colour row (single source: ppv2_engine.py)

RESOLVE_AT = 3          # codes: re-solve a fill when the engine misses its target by this much or more


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def parse_set(s):
    m = re.match(r'\s*#([0-9A-Fa-f]{6})(?:\s*@\s*\+?(-?[\d.]+))?', s)
    return E.srgb_decode(E.hex_raw('#' + m.group(1))) * 2.0 ** float(m.group(2) or 0.0)


def set_str(x):
    """Same notation as calib_final.md: plain hex, or '#RRGGBB @ +n' = HDR colour (base hex x 2^n)."""
    x = np.maximum(np.asarray(x, np.float64), 1e-7)
    m = x.max()
    if m <= 1.0:
        return E.to_hex(E.srgb_encode(x) * 255.0)
    return '%s @ +%.2f' % (E.to_hex(E.srgb_encode(x / m) * 255.0), np.log2(m))


def engine_profile(G, sid, saturation=None):
    P = G['profiles'][sid]['ppv2']
    p = {k: copy.deepcopy(P[k]) for k in ('postExposure', 'temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain', 'mixer')
         if k in P}
    p.update(colorFilter=G['common']['colorFilter'], hueShift=G['common']['hueShift'])
    if saturation is not None:
        p['saturation'] = saturation        # a helper that overrides saturation absolutely (WHITE_SAT at weight 1)
    return p


def grade_of(G, name):
    """calib section D names the live grade, e.g. 'S9b + WHITE_SAT(1)'."""
    m = re.match(r'(S\w+)(?:\s*\+\s*WHITE_SAT\(1\))?$', name.strip())
    sid = m.group(1)
    sat = G['helpers']['WHITE_SAT']['ppv2']['saturation'] if 'WHITE_SAT' in name else None
    return sid, engine_profile(G, sid, sat)


def smooth_codes(lin, p):
    g = np.stack(np.meshgrid(E.GRID1, E.GRID1, E.GRID1, indexing='ij'), -1)
    L = np.maximum(E.color_grade(g, p), 0.0)
    return E.srgb_encode(E.sample_lut(L, E.uvw_of(lin, p))) * 255.0


def solve_fill(target_hex, p, start, keep_intensity=False):
    """Scene-linear fill whose engine screen value is target_hex (log-space least squares, 33^3 LUT).
    keep_intensity: for HDR emitters, also hold the brightest channel at the calib fill's value (1 code per 0.05 EV), so
    the bloom it makes (bloom works on the scene-linear fill, before the grade) stays what the bible planned; targets
    with a clipped channel (e.g. #8AC6FF) leave that freedom."""
    t = E.hex8(target_hex)
    L = np.maximum(E.color_grade(np.stack(np.meshgrid(E.GRID1, E.GRID1, E.GRID1, indexing='ij'), -1), p), 0.0)
    m0 = np.log2(np.max(start))

    def f(z):
        r = E.srgb_encode(E.sample_lut(L, E.uvw_of(np.exp(z)[None, :], p)))[0] * 255.0 - t
        if keep_intensity:
            r = np.append(r, (np.log2(np.exp(z).max()) - m0) / 0.05)
        return r
    starts = [np.log(np.maximum(start, 1e-7))]
    for sc in (0.5, 2.0):
        starts.append(np.log(np.maximum(start * sc, 1e-7)))
    lo, hi = np.log(1e-7), np.log(80.0)
    best = None
    for z0 in starts:
        r = least_squares(f, np.clip(z0, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), xtol=1e-12, ftol=1e-12)
        if best is None or r.cost < best.cost:
            best = r
    x = np.exp(best.x)
    # the written notation quantises to 8-bit hex: evaluate what the implementer will actually type
    s = set_str(x)
    got = np.round(E.codes(parse_set(s)[None, :], p)[0])
    return s, E.to_hex(got), int(np.abs(got - t).max())


def main():
    G = json.load(open(os.path.join(TOOLS, 'inputs', 'grades_engine.json'), encoding='utf-8'))
    C = json.load(open(os.path.join(TOOLS, 'inputs', 'calib_final.json'), encoding='utf-8'))
    luts = {}

    def lut(key, p):
        if key not in luts:
            luts[key] = E.bake_lut(p)
        return luts[key]

    out = {'_what': ('calib_final sections A / B / D through the PPv2 3.x Neutral path with the engine grades '
                     '(grades_engine.json). Screen targets are those of calib_final (unchanged). "set_engine" = the fill '
                     'to type in Unity INSTEAD of calib_final "set" (only where the engine missed by >= %d codes).' % RESOLVE_AT),
           'source_grades_engine_sha256': sha256(os.path.join(TOOLS, 'inputs', 'grades_engine.json')),
           'source_calib_sha256': sha256(os.path.join(TOOLS, 'inputs', 'calib_final.json')),
           'resolve_at_codes': RESOLVE_AT, 'lights': [], 'unlit': [], 'overlay': [], 'bloom_t0': {}, 'blacks': {}}

    for L in C['lights']:
        p = engine_profile(G, L['scene'])
        alb = 0.80 if '白卡' in L['role'] else 0.18
        lin = alb * E.srgb_decode(E.hex_raw(L['colour'])) * L['E']
        got = np.round(E.codes(lin[None, :], p, lut(L['scene'], p))[0])
        d = int(np.abs(got - E.hex8(L['reads'])).max())
        out['lights'].append(dict(scene=L['scene'], role=L['role'], target=L['reads'], engine=E.to_hex(got), codes=d))

    for U in C['unlit']:
        sid = U['scene']
        p = engine_profile(G, sid)
        x = parse_set(U['set'])
        got = np.round(E.codes(x[None, :], p, lut(sid, p))[0])
        d = int(np.abs(got - E.hex8(U['display'])).max())
        row = dict(scene=sid, element=U['element'], target=U['display'], set=U['set'], engine=E.to_hex(got), codes=d)
        if d >= RESOLVE_AT:
            t0 = G['profiles'][sid]['bloom_T0_scene_linear']
            s, g2, d2 = solve_fill(U['display'], p, x)
            if '@' in U['set']:
                # HDR emitter: its bloom is made from the scene-linear fill (before the grade), so prefer the fill
                # that keeps its brightest channel. If that cannot get within 2 codes and the calib fill is
                # already within the +-3 tolerance, keep the calib fill: the glow the bible planned beats 1 code.
                s_k, g_k, d_k = solve_fill(U['display'], p, x, keep_intensity=True)
                if d_k <= 2:
                    s, g2, d2 = s_k, g_k, d_k
                elif d <= 3:
                    s, g2, d2 = None, None, None
                    row['kept'] = 'calib fill kept: within 3 codes, and the re-solve would cut its bloom (xT0 %.2f -> %.2f)' % (
                        U['xT0'], parse_set(solve_fill(U['display'], p, x)[0]).max() / t0)
            if s is not None:
                row.update(set_engine=s, engine_after=g2, codes_after=d2, xT0=round(float(U['xT0']), 2),
                           xT0_engine=round(float(parse_set(s).max() / t0), 2))
        out['unlit'].append(row)

    for O in C['overlay']:
        sid, p = grade_of(G, O['grade'])
        x = parse_set(O['set'])
        got = np.round(E.codes(x[None, :], p, lut(O['grade'], p))[0])
        d = int(np.abs(got - E.hex8(O['display'])).max())
        row = dict(when=O['when'], grade=O['grade'], role=O['role'], target=O['display'], set=O['set'], engine=E.to_hex(got), codes=d)
        if d >= RESOLVE_AT:
            s, g2, d2 = solve_fill(O['display'], p, x)
            row.update(set_engine=s, engine_after=g2, codes_after=d2)
        out['overlay'].append(row)

    rep = G['_engine']['report']
    for sid, P in G['profiles'].items():
        p = engine_profile(G, sid)
        t0 = P['bloom_T0_scene_linear']
        c = E.codes(np.full((1, 3), t0), p, lut(sid, p))[0]
        out['bloom_t0'][sid] = round(float(c @ E.LUMA709_UTIL), 1)
        out['blacks'][sid] = dict(target=rep[sid]['black']['target'], engine=rep[sid]['black']['engine'])

    # colour row of the test card: what the LOOK shows (art simulator, look-definition numbers) under each profile
    sys.path.insert(0, os.path.join(ART, 'lens_cine'))
    sys.path.insert(0, os.path.join(ART, 'bible_work'))
    import ppv2 as LD
    from lutlib_core import patch_ppv2
    patch_ppv2(LD)
    lin = np.array([c for _, c in COLOUR_PATCHES], np.float64)
    out['colour_patches'] = {'names': [n for n, _ in COLOUR_PATCHES], 'linear': [list(c) for _, c in COLOUR_PATCHES], 'look': {}, 'engine': {}}
    worst_cp = 0
    for sid, P in G['profiles'].items():
        q = dict(P['ppv2_lookdef'])
        q.update(postExposure=P['ppv2']['postExposure'], colorFilter=G['common']['colorFilter'], hueShift=G['common']['hueShift'])
        qq = LD.full(q)
        look = np.round(LD.lin_to_srgb(LD.grade_lut(lin * 2.0 ** qq['postExposure'], qq)) * 255.0)
        p = engine_profile(G, sid)
        eng = np.round(E.codes(lin, p, lut(sid, p)))
        out['colour_patches']['look'][sid] = [E.to_hex(c) for c in look]
        out['colour_patches']['engine'][sid] = [E.to_hex(c) for c in eng]
        worst_cp = max(worst_cp, int(np.abs(look - eng).max()))

    with open(os.path.join(TOOLS, 'inputs', 'calib_engine.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print('A. light readings: max %d codes' % max(r['codes'] for r in out['lights']))
    for r in out['lights']:
        if r['codes'] > 2:
            print('   %-4s %s  target %s engine %s (%d)' % (r['scene'], r['role'], r['target'], r['engine'], r['codes']))
    for sect in ('unlit', 'overlay'):
        rows = out[sect]
        res = [r for r in rows if 'set_engine' in r]
        print('%s. %d fills; engine with the calib fill: max %d codes; re-solved %d:' % ('B' if sect == 'unlit' else 'D', len(rows), max(r['codes'] for r in rows), len(res)))
        for r in res:
            print('   %-4s %-28s target %s  calib %-18s -> engine %s (%d)  | set_engine %-18s -> %s (%d)%s' % (
                r.get('scene', r.get('grade')), r.get('element', r.get('role')), r['target'], r['set'], r['engine'], r['codes'],
                r['set_engine'], r['engine_after'], r['codes_after'],
                ('  xT0 %.2f -> %.2f' % (r['xT0'], r['xT0_engine'])) if 'xT0' in r else ''))
        print('   after re-solve: max %d codes' % max(r.get('codes_after', r['codes']) for r in rows))
    print('bloom knee T0 displays at luma (bible: 228):', out['bloom_t0'])
    print('test-card colour row: engine vs look, worst %d codes over 15 profiles x %d colours' % (worst_cp, len(COLOUR_PATCHES)))
    print('wrote', os.path.join(TOOLS, 'inputs', 'calib_engine.json'))


if __name__ == '__main__':
    main()
