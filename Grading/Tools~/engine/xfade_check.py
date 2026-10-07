# -*- coding: utf-8 -*-
"""Crossfades and helpers with the ENGINE numbers vs the LOOK (bible 1.4 / B2 / B3).

PPv2 interpolates every overridden parameter of two volumes linearly (lift / gamma / gain / mixer included), so the
middle of a crossfade is a grade nobody solved directly. This script lerps the engine parameters exactly as PPv2 does,
lerps the look-definition parameters the same way through the art simulator, and compares the two on the preview
frames of BOTH scenes (codes per pixel, max channel). It also stacks the helpers (EXPO_UP / EXPO_DOWN / WHITE_SAT) at
the weights of table B3 on top of their scene.

Usage: python3 xfade_check.py --frames frames.npz      (frames = art/bible_work/make_previews.SOURCES, scene-linear)
"""
import argparse
import copy
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
KIT = os.path.dirname(TOOLS)
ART = os.path.normpath(os.path.join(KIT, '..', '..', 'art'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ART, 'lens_cine'))
sys.path.insert(0, os.path.join(ART, 'bible_work'))
import ppv2_engine as E  # noqa: E402
import ppv2 as LD  # noqa: E402
from lutlib_core import patch_ppv2  # noqa: E402
patch_ppv2(LD)

KEYS = ('postExposure', 'temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain', 'mixer')
# visible crossfades (bible 6.x); the hard cuts under a full overlay (S4c->S6, S9b->S10, S10->S11, S11->S12) have no middle
PAIRS = [('S1', 'S2'), ('S2', 'S3'), ('S3', 'S4'), ('S4', 'S4c'), ('S6', 'S7a'), ('S7a', 'S7b'), ('S7b', 'S8'),
         ('S8', 'S8b'), ('S8b', 'S9a'), ('S9a', 'S9b'), ('S9b', 'S10')]
CASES = [('S3', [('EXPO_UP', 0.102)]), ('S4', [('EXPO_UP', 0.062)]), ('S4c', [('EXPO_UP', 0.306)]), ('S6', [('EXPO_DOWN', 0.154)]),
         ('S7a', [('EXPO_DOWN', 0.156)]), ('S7b', [('EXPO_DOWN', 0.675)]), ('S8', [('EXPO_UP', 0.111)]), ('S9a', [('EXPO_UP', 0.095)]),
         ('S9b', [('WHITE_SAT', 0.42), ('EXPO_UP', 0.270)]), ('S9b', [('WHITE_SAT', 1.0), ('EXPO_UP', 0.649)]),
         ('S11', [('EXPO_UP', 0.241)]), ('S12', [('EXPO_UP', 0.200)])]


def prof(G, sid, lookdef=False):
    P = G['profiles'][sid]
    src = dict(P['ppv2'])
    if lookdef and 'ppv2_lookdef' in P:
        src.update(P['ppv2_lookdef'])
        src.pop('mixer', None)
    p = {k: copy.deepcopy(src[k]) for k in KEYS if k in src}
    if 'mixer' not in p:
        p['mixer'] = list(E.MIXER_IDENTITY)
    p.update(colorFilter='#FFFFFF', hueShift=0.0)
    return p


def lerp(a, b, w):
    out = {}
    for k in a:
        if k == 'colorFilter':
            out[k] = a[k]
        elif isinstance(a[k], list):
            out[k] = [x + (y - x) * w for x, y in zip(a[k], b.get(k, a[k]))]
        else:
            out[k] = a[k] + (b.get(k, a[k]) - a[k]) * w
    return out


def look(lin, p):
    q = LD.full({k: v for k, v in p.items() if k != 'mixer'})
    return LD.lin_to_srgb(LD.grade_lut(np.asarray(lin) * 2.0 ** q['postExposure'], q)) * 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', required=True)
    a = ap.parse_args()
    G = json.load(open(os.path.join(TOOLS, 'inputs', 'grades_engine.json'), encoding='utf-8'))
    F = np.load(a.frames)
    rng = np.random.default_rng(5)

    def samp(sid, n=6000):
        f = np.maximum(np.asarray(F[sid], np.float64).reshape(-1, 3), 0.0)
        return f[rng.choice(len(f), n, replace=False)]

    worst = 0.0
    print('crossfade (old at 1, new rising): engine lerp vs look lerp, frames of both scenes, codes per pixel (max channel)')
    for x, y in PAIRS:
        lin = np.vstack([samp(x), samp(y)])
        res = []
        for w in (0.0, 0.25, 0.5, 0.75, 1.0):
            d = np.abs(np.round(E.codes(lin, lerp(prof(G, x), prof(G, y), w)))
                       - np.round(look(lin, lerp(prof(G, x, True), prof(G, y, True), w)))).max(1)
            p99 = np.percentile(d, 99)
            worst = max(worst, p99)
            res.append('w %.2f mean %.2f p99 %.0f' % (w, d.mean(), p99))
        print('  %-4s -> %-4s  %s' % (x, y, ' | '.join(res)))
    print('helpers on top of their scene (weights of table B3 / B2)')
    H = G['helpers']
    for sid, hs in CASES:
        pe, pl = prof(G, sid), prof(G, sid, True)
        for h, w in hs:
            tgt = {k: v for k, v in H[h]['ppv2'].items() if k in KEYS}
            pe, pl = lerp(pe, {**pe, **tgt}, w), lerp(pl, {**pl, **tgt}, w)
        lin = samp(sid, 12000)
        d = np.abs(np.round(E.codes(lin, pe)) - np.round(look(lin, pl))).max(1)
        worst = max(worst, np.percentile(d, 99))
        print('  %-4s + %-34s mean %.2f p99 %.0f max %.0f' % (sid, ', '.join('%s %.3g' % t for t in hs), d.mean(), np.percentile(d, 99), d.max()))
    print('worst p99 over all cases: %.0f codes' % worst)


if __name__ == '__main__':
    main()
