# -*- coding: utf-8 -*-
"""The purple guard in the MIDDLE of 7a's grade cross-fade (S7a -> S7b linear F3e -> F5): purple_scan.py proves the two
ends; this checks the blended grades in between (PPv2 volume blending = Engineering/render_harness lbh.grade.blend), for
M_07a_SeaSurface (mask G + B, the material that lives through the fade). 1 000 000 random in-gamut HDR colours per
weight w = 0.1 .. 0.9, through the guard (Sea_PurpleCeiling.png, point-sampled) -> violet left under the blended grade.
Writes Sea/Docs~/purple_transition.json.   ~/bpy/bin/python Sea/Tools~/purple_transition.py"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'Engineering', 'render_harness'))
import grade as G  # noqa: E402
import purple_scan as P  # noqa: E402
from lbh import grade as LG  # noqa: E402
from PIL import Image  # noqa: E402


def main():
    tex = np.flipud(np.asarray(Image.open(os.path.join(os.path.dirname(HERE), 'Textures', 'Sea_PurpleCeiling.png')).convert('RGBA')))
    rng = np.random.default_rng(11)
    out = {}
    for w in np.round(np.arange(0.1, 0.91, 0.1), 2):
        st = LG.blend({'S7a': 1.0, 'S7b': float(w)})
        st['colorFilter'] = G.GE['common']['colorFilter']; st['hueShift'] = G.GE['common']['hueShift']
        P._P['S7a+S7b=%.2f' % w] = st
        left, n = 0, 0
        for _ in range(5):
            N = 400000
            o = P.lsh(rng.uniform(0.01, 3.2, N), rng.uniform(0, P.S_MAX, N), rng.uniform(0, 360, N))
            lin = P.oklab_raw_to_lin(o)
            ok = (lin >= 0).all(-1)
            g = P.guard(lin[ok], tex, (0, 1, 1, 0))
            n += int(ok.sum())
            left += int(P.violet(g, 'S7a+S7b=%.2f' % w).sum())
        out['%.1f' % w] = dict(in_gamut=n, violet_left=left)
        print(w, out['%.1f' % w], flush=True)
    json.dump(dict(about=__doc__.split('\n')[0], rule='h_ab 290..330, C* > 8, L* > 40 (D-21 revised)', weights=out),
              open(os.path.join(os.path.dirname(HERE), 'Docs~', 'purple_transition.json'), 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
