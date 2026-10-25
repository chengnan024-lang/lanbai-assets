# -*- coding: utf-8 -*-
"""总导演终审 r1 #1：云卡在正前画面里占多少（按组：upper / lower / wisp；alpha > 0.3 的像素占整帧的比例，车壳里的像素不算）。
写 Docs~/cover.json。"""
import os
import sys
import json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import act08_ref as R  # noqa: E402

R.POEM_ON = False


def main():
    out = {}
    for t in (958.0, 965.4, 971.4, 987.06, 995.0):
        for cam in ('hero', 'door_d12'):
            R.COVER.clear()
            codes, m, lin = R.render(t, cam, 480, 'bible_v2')
            V, hh, pix = R.rays(dict(R.CAMS[cam]), 480)
            win = R.window_mask(V, t)
            r = {g: round(float(((a > 0.3) & win).mean()), 4) for g, a in R.COVER.items()}
            out['%s_%.2f' % (cam, t)] = r
            print(cam, t, r, flush=True)
    json.dump(out, open(os.path.join(KIT, 'Docs~', 'cover.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
